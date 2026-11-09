"""doc_classifier.py - Bộ phân loại đầu-cuối `DocumentSlice -> ClassificationResult`: luật -> TF-IDF -> LLM -> người.

Đây là cascade ĐÃ ĐO ở thí nghiệm 02 (teams/team3_classification/experiments/02_llm_and_cascade/RESULTS.md mục 7, 10) đưa vào `src/`:

  1. rule : cổng luật từ khóa tiêu đề (`CascadedClassifier.match_rules`, Kev tắt).
  2. tfidf: `TfidfClassifier` (Track S). Nhận khi nhãn != RARE_OR_OTHER và độ tin cậy >= th_s.
  3. llm  : LLM cục bộ zero-shot toàn taxonomy (Ollama Qwen3.5-4B mặc định; Kev chọn được) qua `zero_shot.py`, cache đĩa.
            Nhận khi nhãn không thuộc OTHER/UNREADABLE/không trả lời và độ tin cậy >= th_llm.
  4. human: phần còn lại -> `tier="human"`, `predicted_category=UNKNOWN`, `requires_human_review=True`, kèm GỢI Ý
            (`suggested_category`, `suggested_confidence`, `suggestion_source`). Không bao giờ tự xếp hồ sơ theo gợi ý.

Quyết định nhận/từ chối do `cascade.run_cascade` đưa ra (cùng hàm với thí nghiệm); ngưỡng `th_s`, `th_llm`, `agree` đọc từ
`results/02_llm_and_cascade/tables/dev_selection_02.json` (chọn CHỈ trên DEV). Lớp này chỉ gọi tầng sau khi tầng trước từ chối, nên
kết quả của `run_cascade` trên tín hiệu từng phần giống hệt chạy trên đủ tín hiệu (một tầng chỉ xét tài liệu các tầng trước chưa nhận).

Trung thực về lỗi: LLM/Kev không khả dụng -> `tier="human"`, `abstain_reason="llm_error"`, `error=<lý do>`; không có nhãn thay thế âm thầm.
Chưa tắt được cổng luật hay TF-IDF "im lặng": thiếu mô hình TF-IDF ném `TfidfModelError` khi dựng lớp.

Cách dùng:
    clf = DocumentClassifier.from_defaults()              # nạp models/classification/..., ngưỡng từ dev_selection_02.json, Ollama Qwen3.5
    res = clf.classify_slice(doc_slice)                   # -> ClassificationResult
    DocumentClassifier.from_defaults(llm_backend="kev")   # tầng 3 = Kev (chỉ có tên loại làm tiêu chí; xem CascadeConfig.measured)
    DocumentClassifier.from_defaults(use_llm=False)       # chỉ luật + TF-IDF; phần còn lại -> người (abstain_reason="llm_disabled")
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

from src.classification.cascade import NEVER_AUTO, POOL, CascadeParams, Signals, audit_flags, run_cascade
from src.classification.llm_backends import DEFAULT_SPEC_ID, LLM_SPECS, LlmBackend, make_backend
from src.classification.system_one_classifier import HEADER_WINDOW_CHARS, RULE_SCORE_EXACT, CascadedClassifier, RuleMatch
from src.classification.taxonomy import Taxonomy, load_taxonomy
from src.classification.tfidf_classifier import CONFIG_NAME as TFIDF_CONFIG, DEFAULT_DIR as TFIDF_DEFAULT_DIR, TfidfClassifier
from src.classification.zero_shot import MIN_TEXT_CHARS, NO_ANSWER, Answer, clean_prompt_text
from src.common.contracts import UNKNOWN_CATEGORY, ClassificationResult, DocumentSlice
from src.common.text_norm import NormalizedText, normalize_text

logger = logging.getLogger(__name__)

REPO = Path(__file__).resolve().parent.parent.parent
DEFAULT_SELECTION_PATH = (REPO / "teams" / "team3_classification" / "results" / "02_llm_and_cascade" / "tables" / "dev_selection_02.json")
DEFAULT_SOURCE = "ocr_v2_p12"          # nguồn văn bản của cấu hình triển khai: OCR local, trang 1-2
DEFAULT_MAX_ERROR = 0.01
TITLE_ZONE_CHARS = 400                 # tùy chọn rule_title_tiebreak: từ khóa tiêu đề phải nằm trong 400 ký tự đầu (đã chuẩn hóa)
TITLE_GAP_CHARS = 300                  # ... và các lớp còn lại chỉ xuất hiện sau từ khóa tiêu đề ít nhất 300 ký tự
TEXT_PAGES = 2                         # số trang đầu của lát cắt đưa vào bộ phân loại (đúng nguồn ocr_v2_p12 đã đo)


def text_for_classification(sl: DocumentSlice, max_pages: int = TEXT_PAGES) -> str:
    """Văn bản đưa vào cascade: `max_pages` trang đầu của lát cắt, bỏ trang rỗng, nối bằng '\\n' (đúng cách dựng nguồn `ocr_v2_p12`).
    Lát cắt không có `pages` -> dùng `combined_text` (toàn bộ, không cắt trang)."""
    if sl.pages:
        pages = sorted(sl.pages, key=lambda p: p.page_number)[:max_pages]
        return "\n".join(p.full_text for p in pages if (p.full_text or "").strip())
    return sl.combined_text or ""


def audit_key(file_key: Optional[str], slice_id: str, text: str = "") -> str:
    """Khóa băm của kiểm mẫu: định danh tệp + chỉ số lát cắt. `slice_id` ('slice_000'...) lặp lại ở mọi tệp nên KHÔNG được dùng một mình
    (xem báo cáo 04, T1). Không có định danh tệp -> dùng sha1 của văn bản lát cắt (vẫn khác nhau giữa các tài liệu)."""
    return f"{file_key}:{slice_id}" if file_key else f"{hashlib.sha1((text or '').encode('utf-8')).hexdigest()}:{slice_id}"


def resolve_ambiguous_by_title(text: str, ambiguous: Sequence[str], rules: Sequence[tuple], zone: int = TITLE_ZONE_CHARS,
                               gap: int = TITLE_GAP_CHARS, window: int = HEADER_WINDOW_CHARS) -> Optional[tuple]:
    """Gỡ thế "mơ hồ" của cổng luật theo vị trí tiêu đề (hiện thực hóa `deciding_cue` của taxonomy: tiêu đề quyết định loại).
    Khi >= 2 lớp cùng khớp từ khóa trong `window` ký tự đầu: nếu từ khóa SỚM NHẤT của một lớp nằm trong `zone` ký tự đầu (vùng tiêu đề)
    và mọi lớp còn lại chỉ xuất hiện sau nó ít nhất `gap` ký tự (chỉ là nhắc tên, ví dụ tên cột bảng) thì chọn lớp đó.
    `rules`: danh sách (class_id, từ khóa). Trả (class_id, từ khóa) hoặc None (vẫn mơ hồ)."""
    norm = NormalizedText(text[:window])
    first: Dict[str, tuple] = {}
    for cid, kw in rules:
        if cid not in ambiguous:
            continue
        k = normalize_text(kw)
        i = norm.spaced.find(k) if k else -1
        if i >= 0 and (cid not in first or i < first[cid][0]):
            first[cid] = (i, kw)
    if len(first) < 2:
        return None
    order = sorted(first.items(), key=lambda kv: kv[1][0])
    (c0, (p0, kw0)), (_, (p1, _kw1)) = order[0], order[1]
    return (c0, kw0) if (p0 <= zone and p1 - p0 >= gap) else None


# --------------------------------------------------------------------------------------- cấu hình
@dataclass(frozen=True)
class CascadeConfig:
    params: CascadeParams
    source: str
    t3: str
    max_error: float
    measured: bool                      # True: đúng cấu hình đã đo (ngưỡng + chế độ đồng thuận như dev_selection_02.json)
    selection_path: str
    selection_sha1_10: str
    note: str = ""

    def describe(self) -> Dict[str, Any]:
        return {"source": self.source, "t3": self.t3, "max_error": self.max_error, "params": self.params.describe(),
                "measured": self.measured, "selection": self.selection_path, "selection_sha1_10": self.selection_sha1_10, "note": self.note}


def load_cascade_config(path: Path | str = DEFAULT_SELECTION_PATH, source: str = DEFAULT_SOURCE, t3: str = DEFAULT_SPEC_ID,
                        max_error: float = DEFAULT_MAX_ERROR) -> CascadeConfig:
    """Đọc ngưỡng `full[<t3>]` của `source` ở mức sai `max_error` từ dev_selection_02.json.

    Chế độ đồng thuận `emb`/`s_or_emb` cần embedding few-shot (chưa đưa vào src): chuyển sang `none` (CHẶT hơn: chỉ nhận theo ngưỡng
    độ tin cậy, tập được nhận là tập con của cấu hình đã đo) và đánh dấu `measured=False`."""
    path = Path(path)
    raw = path.read_bytes()
    sel = json.loads(raw.decode("utf-8"))
    try:
        entries = sel["cascade"][source]["entries"]
    except KeyError as e:
        raise KeyError(f"{path} không có cascade[{source!r}]") from e
    hit = [e for e in entries if e["name"] == f"full[{t3}]" and abs(float(e["max_error"]) - max_error) < 1e-12]
    if not hit:
        raise KeyError(f"{path}: không có mục full[{t3}] với max_error={max_error}")
    p = hit[0]["params"]
    agree = p.get("agree", "none")
    measured, note = True, ""
    if agree in ("emb", "s_or_emb"):
        measured, note = False, (f"agree={agree!r} đã đo với embedding few-shot, chưa đưa vào src: dùng agree='none' với cùng ngưỡng "
                                 "(chặt hơn, KHÔNG phải cấu hình đã đo)")
        agree = "none"
    params = CascadeParams(use_rule=bool(p["use_rule"]), use_tfidf=bool(p["use_tfidf"]), use_llm=bool(p["use_llm"]),
                           th_s=float(p["th_s"]), th_llm=float(p["th_llm"]), agree=agree)
    return CascadeConfig(params, source, t3, max_error, measured, str(path), hashlib.sha1(raw).hexdigest()[:10], note)


# --------------------------------------------------------------------------------------- vết (cho kiểm hồi quy)
@dataclass
class Trace:
    rule_label: str = ""
    rule_ambiguous: List[str] = field(default_factory=list)
    s_label: Optional[str] = None
    s_conf: Optional[float] = None
    llm_label: Optional[str] = None
    llm_conf: Optional[float] = None
    llm_error: Optional[str] = None
    llm2_label: Optional[str] = None
    audit: bool = False
    rule_tiebreak: bool = False
    cascade_label: str = ""
    cascade_tier: str = "human"
    stages_run: List[str] = field(default_factory=list)


# --------------------------------------------------------------------------------------- bộ phân loại
class DocumentClassifier:
    def __init__(self, tfidf: Optional[TfidfClassifier], llm: Optional[LlmBackend], config: CascadeConfig,
                 taxonomy: Optional[Taxonomy] = None, rules: Optional[CascadedClassifier] = None, *,
                 llm2: Optional[LlmBackend] = None, audit_rate: float = 0.0, audit_seed: int = 0,
                 decision_log: Optional[Path | str] = None, rule_title_tiebreak: bool = False):
        """Tùy chọn an toàn (TẤT CẢ tắt mặc định, không đổi hành vi đã đo):
        - `config.params.consensus` in {"s","llm2","s_llm2"}: tầng LLM chỉ nhận khi TF-IDF và/hoặc LLM thứ hai (`llm2`) cùng nhãn.
        - `audit_rate` (0..1): tỉ lệ kiểm mẫu ngẫu nhiên (tất định theo `audit_seed` + định danh tệp + slice_id; xem `audit_key`) trên phần TỰ NHẬN: tài liệu được chọn vẫn
          mang nhãn và tier của mô hình nhưng `requires_human_review=True`, `abstain_reason="audit_sample"`.
        - `rule_title_tiebreak` (tắt mặc định): khi cổng luật "mơ hồ" (>= 2 lớp cùng khớp), chọn lớp có từ khóa nằm ở vùng tiêu đề và các lớp
          kia chỉ được nhắc sau đó >= 300 ký tự (`resolve_ambiguous_by_title`). Xem teams/team3_classification/experiments/05_composite_slices.
        - `decision_log`: đường dẫn JSONL; mỗi lần phân loại ghi một dòng (id, tier, nhãn, độ tin cậy, nhận/từ chối, audit), không ghi văn bản."""
        if not 0.0 <= audit_rate <= 1.0:
            raise ValueError("audit_rate phải trong [0, 1]")
        self.llm2 = llm2
        self.file_key: Optional[str] = None
        self.rule_title_tiebreak = bool(rule_title_tiebreak)
        self.audit_rate, self.audit_seed = float(audit_rate), int(audit_seed)
        self.decision_log = Path(decision_log) if decision_log else None
        self.config = config
        self.taxonomy = taxonomy if taxonomy is not None else load_taxonomy()
        # cổng luật dùng đúng lớp của thí nghiệm (Kev TẮT); không có đường nào từ lớp này tới Kev
        self.rules = rules or CascadedClassifier(kev_endpoint=None, taxonomy=self.taxonomy)
        p = config.params
        if p.use_tfidf and tfidf is None:
            raise ValueError("cấu hình cascade dùng TF-IDF nhưng chưa có mô hình TF-IDF (TfidfClassifier.load hoặc train_tfidf_classifier.py)")
        self.tfidf = tfidf
        self.llm = llm
        self._class_ids = set(self.taxonomy.class_ids)
        if p.consensus in ("llm2", "s_llm2") and llm2 is None:
            raise ValueError("consensus 'llm2' cần llm2 (LlmBackend thứ hai: mô hình hoặc prompt khác)")
        if p.consensus in ("s", "s_llm2") and tfidf is None:
            raise ValueError("consensus 's' cần mô hình TF-IDF")

    SAFE_TH_S = 0.60                        # Ngưỡng an toàn khuyến nghị cho TF-IDF (tránh nhận ẩu ở mức 0.28-0.55)

    @classmethod
    def from_defaults(cls, *, use_llm: bool = True, llm_backend: str = "ollama", spec_id: Optional[str] = None,
                      tfidf_dir: Path | str = TFIDF_DEFAULT_DIR, selection_path: Path | str = DEFAULT_SELECTION_PATH,
                      max_error: float = DEFAULT_MAX_ERROR, cache_dir: Optional[Path | str] = None,
                      rule_title_tiebreak: bool = True,
                      th_s: Optional[float] = None, th_llm: Optional[float] = None,
                      consensus: Optional[str] = None,
                      llm2: Optional[Any] = None) -> "DocumentClassifier":
        """Cấu hình đã đo: Qwen3.5-4B qua Ollama, mô tả ngắn, ngưỡng 1%. `llm_backend='kev'` chọn Kev-... (tên loại làm tiêu chí).
        `use_llm=False`: không dựng backend (tầng 3 tắt, tài liệu chưa nhận -> người).
        `rule_title_tiebreak=True`: gỡ thế mơ hồ của cổng luật theo vị trí tiêu đề (bật mặc định khi dùng from_defaults).
        `th_s`: ghi đè ngưỡng nhận của tầng TF-IDF (mặc định đọc từ dev_selection_02.json; khuyến nghị th_s=0.60 để tránh nhận ẩu).
        `consensus`: ghi đè chế độ đồng thuận ('none' | 's' | 'llm2' | 's_llm2'; 's' yêu cầu tầng LLM đồng thuận với TF-IDF mới tự nhận)."""
        sid = spec_id or ("kev_s1_name_c2000" if llm_backend == "kev" else DEFAULT_SPEC_ID)
        if LLM_SPECS[sid].engine != ("kev" if llm_backend == "kev" else "ollama"):
            raise ValueError(f"{sid} không thuộc backend {llm_backend}")
        cfg = load_cascade_config(selection_path, DEFAULT_SOURCE, sid, max_error)
        if th_s is not None or th_llm is not None or consensus is not None:
            new_params = replace(cfg.params,
                                 th_s=float(th_s) if th_s is not None else cfg.params.th_s,
                                 th_llm=float(th_llm) if th_llm is not None else cfg.params.th_llm,
                                 consensus=str(consensus) if consensus is not None else cfg.params.consensus)
            cfg = replace(cfg, params=new_params)
        tfidf = TfidfClassifier.load(tfidf_dir) if cfg.params.use_tfidf or cfg.params.agree in ("s", "s_or_emb") or cfg.params.consensus in ("s", "s_llm2") else None
        backend = make_backend(sid, cache_dir=Path(cache_dir) if cache_dir else None) if use_llm else None
        return cls(tfidf, backend, cfg, rule_title_tiebreak=rule_title_tiebreak, llm2=llm2)

    def describe(self) -> Dict[str, Any]:
        return {"cascade": self.config.describe(), "tfidf": None if self.tfidf is None else {"config": self.tfidf.name,
                "meta": None if self.tfidf.meta is None else {"labels_sha1_10": self.tfidf.meta.labels_sha1_10, "n_train": self.tfidf.meta.n_train,
                                                              "text_source": self.tfidf.meta.text_source, "created_at": self.tfidf.meta.created_at}},
                "llm": None if self.llm is None else {"spec": self.llm.spec.id, "model": self.llm.model_name}}

    # --- API chính
    def set_file_key(self, key: Optional[str]) -> None:
        """Định danh tệp đang xử lý (sha256 nội dung hoặc tên tệp) dùng làm một phần khóa kiểm mẫu; pipeline gọi trước mỗi tệp."""
        self.file_key = key or None

    def shadow_title_tiebreak(self, text: str) -> Optional[str]:
        """Chế độ BÓNG của `rule_title_tiebreak`: nhãn mà tùy chọn SẼ chọn nếu bật (cổng luật mơ hồ và tiêu đề phân định được), None nếu không áp dụng.
        Chỉ chạy luật từ khóa (rẻ, KHÔNG gọi LLM); không đổi quyết định nào."""
        if self.rule_title_tiebreak or not self.config.params.use_rule or not (text or "").strip():
            return None
        rule = self.rules.match_rules(text)
        if rule.category is not None or not rule.ambiguous:
            return None
        hit = resolve_ambiguous_by_title(text, rule.ambiguous, self.rules._rules)
        return hit[0] if (hit is not None and hit[0] in self._class_ids) else None

    def classify_slice(self, sl: DocumentSlice) -> ClassificationResult:
        return self.classify_text(text_for_classification(sl), sl.slice_id, list(sl.ocr_errors))[0]

    def classify_text(self, text: str, slice_id: str = "doc", ocr_errors: Optional[Sequence[str]] = None):
        """-> (ClassificationResult, Trace). Thêm kiểm mẫu (audit) và nhật ký nếu được bật; mặc định không làm gì thêm."""
        res, tr = self._classify_core(text, slice_id, ocr_errors)
        if self.audit_rate > 0 and not res.requires_human_review and bool(audit_flags([audit_key(self.file_key, slice_id, text)], self.audit_rate, self.audit_seed)[0]):
            tr.audit = True
            res = res.model_copy(update=dict(requires_human_review=True, abstain_reason="audit_sample"))
        if self.decision_log is not None:
            rec = dict(id=slice_id, tier=res.tier, label=res.predicted_category, confidence=res.confidence if res.confidence_kind == "model" else None,
                       accepted=res.tier != "human", audit=tr.audit, abstain_reason=res.abstain_reason, stages=tr.stages_run)
            self.decision_log.parent.mkdir(parents=True, exist_ok=True)
            with self.decision_log.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return res, tr

    def _classify_core(self, text: str, slice_id: str = "doc", ocr_errors: Optional[Sequence[str]] = None):
        t0 = time.perf_counter()
        tr = Trace()

        def finish(**kw) -> ClassificationResult:
            return ClassificationResult(slice_id=slice_id, processing_time_ms=(time.perf_counter() - t0) * 1000, **kw)

        def human(reason: str, *, error: Optional[str] = None, evidence: Optional[str] = None, sugg: Optional[tuple] = None) -> ClassificationResult:
            kw: Dict[str, Any] = {}
            if sugg:
                kw = dict(suggested_category=sugg[0], suggested_confidence=sugg[1], suggestion_source=sugg[2])
            return finish(predicted_category=UNKNOWN_CATEGORY, confidence=0.0, model_name="none", tier="human", confidence_kind="none",
                          requires_human_review=True, abstain_reason=reason, evidence=evidence, error=error, **kw)

        if not (text or "").strip():
            return human("empty_text", error="; ".join(ocr_errors or []) or None), tr
        if len(clean_prompt_text(text)) < MIN_TEXT_CHARS:
            return human("text_too_short"), tr

        p = self.config.params
        # --- tầng 1: luật
        rule: RuleMatch = self.rules.match_rules(text) if p.use_rule else RuleMatch()
        if self.rule_title_tiebreak and p.use_rule and rule.category is None and rule.ambiguous:
            hit = resolve_ambiguous_by_title(text, rule.ambiguous, self.rules._rules)
            if hit is not None and hit[0] in self._class_ids:
                tr.rule_tiebreak = True
                rule = RuleMatch(category=hit[0], evidence=f"{hit[1]} (tiêu đề đứng trước {'|'.join(c for c in rule.ambiguous if c != hit[0])})",
                                 score=RULE_SCORE_EXACT * 0.9)
        rule_label = rule.category if rule.category in self._class_ids else ""
        tr.rule_label, tr.rule_ambiguous = rule_label, list(rule.ambiguous)
        sig = _signals(rule_label, POOL, 0.0, "", float("nan"))
        if p.use_rule:
            tr.stages_run.append("rule")
            res = run_cascade(sig, replace(p, use_tfidf=False, use_llm=False)).iloc[0]
            if res["accepted"]:
                tr.cascade_label, tr.cascade_tier = res["label"], "rule"
                return finish(predicted_category=res["label"], confidence=rule.score, model_name="keyword_rule_gate", tier="rule",
                              confidence_kind="heuristic", requires_human_review=False, evidence=rule.evidence), tr

        # --- tầng 2: TF-IDF
        s_label, s_conf, s_proba = POOL, 0.0, {}
        if self.tfidf is not None:
            tr.stages_run.append("tfidf")
            pr = self.tfidf.predict([text])
            s_label, s_conf = pr.labels[0], float(pr.confidence[0])
            order = np.argsort(-pr.proba[0])[:5]
            s_proba = {pr.classes[i]: round(float(pr.proba[0, i]), 6) for i in order if pr.proba[0, i] > 0}
            tr.s_label, tr.s_conf = s_label, s_conf
            sig = _signals(rule_label, s_label, s_conf, "", float("nan"))
            res = run_cascade(sig, replace(p, use_llm=False)).iloc[0]
            if p.use_tfidf and res["accepted"] and res["tier"] == "tfidf":
                tr.cascade_label, tr.cascade_tier = res["label"], "tfidf"
                return finish(predicted_category=res["label"], confidence=s_conf, probabilities=s_proba, model_name=self.tfidf.name,
                              tier="tfidf", confidence_kind="model", requires_human_review=False), tr

        # --- tầng 3: LLM
        tfidf_sugg = (s_label, s_conf, "tfidf") if (self.tfidf is not None and s_label != POOL) else None
        evid = _evidence(rule, s_label if self.tfidf is not None else None, s_conf)
        if not p.use_llm or self.llm is None:
            return human("llm_disabled", evidence=evid, sugg=tfidf_sugg), tr
        tr.stages_run.append("llm")
        ans: Answer = self.llm.answer(text)
        llm_label = ans.label if (ans.parse_ok and ans.label != NO_ANSWER) else ""
        llm_conf = float("nan") if (ans.conf is None or not ans.parse_ok) else float(ans.conf)
        tr.llm_label, tr.llm_conf, tr.llm_error = llm_label, (None if llm_conf != llm_conf else llm_conf), (ans.error or None)
        sig = _signals(rule_label, s_label, s_conf, llm_label, llm_conf)
        if p.consensus in ("llm2", "s_llm2") and llm_label not in NEVER_AUTO and self.llm2 is not None:
            ans2: Answer = self.llm2.answer(text)           # chỉ hỏi nguồn thứ hai khi nguồn thứ nhất có nhãn có thể tự nhận
            tr.llm2_label = ans2.label if (ans2.parse_ok and ans2.label != NO_ANSWER) else ""
            sig.llm2_label = [tr.llm2_label]
        res = run_cascade(sig, p).iloc[0]
        if res["accepted"] and res["tier"] == "llm":
            tr.cascade_label, tr.cascade_tier = res["label"], "llm"
            kind = "kev" if self.llm.tier_name == "kev" else "llm"
            return finish(predicted_category=res["label"], confidence=llm_conf, probabilities=dict(ans.probs or {}),
                          model_name=self.llm.model_name, tier=kind, confidence_kind="model" if llm_conf == llm_conf else "none",
                          requires_human_review=False, evidence=evid), tr

        # --- người: nêu rõ vì sao + gợi ý
        if not ans.parse_ok:
            reason, err = "llm_error", ans.error or "LLM không trả lời"
            return human(reason, error=err, evidence=evid, sugg=tfidf_sugg), tr
        sugg = (ans.label, None if llm_conf != llm_conf else llm_conf, self.llm.tier_name)
        reason = "llm_other" if ans.label in NEVER_AUTO else ("llm_no_consensus" if (llm_conf == llm_conf and llm_conf >= p.th_llm and p.consensus != "none") else "llm_low_confidence")
        return human(reason, evidence=f"{evid}; llm:{ans.label}({llm_conf:.3f})" if llm_conf == llm_conf else f"{evid}; llm:{ans.label}",
                     sugg=sugg), tr


def _signals(rule: str, s_label: str, s_conf: float, llm_label: str, llm_conf: float) -> Signals:
    return Signals(rule=[rule], s_label=[s_label], s_conf=np.array([s_conf], float), llm_label=[llm_label], llm_conf=np.array([llm_conf], float))


def _evidence(rule: RuleMatch, s_label: Optional[str], s_conf: float) -> str:
    parts = []
    if rule.ambiguous:
        parts.append("rule:mơ hồ " + "|".join(rule.ambiguous))
    else:
        parts.append("rule:không khớp")
    if s_label is not None:
        parts.append(f"tfidf:{s_label}({s_conf:.3f})")
    return "; ".join(parts)
