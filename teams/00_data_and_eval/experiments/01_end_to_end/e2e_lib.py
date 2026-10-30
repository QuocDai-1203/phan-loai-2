"""e2e_lib.py - Thư viện của thí nghiệm end-to-end (tách trang -> phân loại từng lát cắt), CP3 của docs/PARALLEL_RESEARCH_PLAN.md.

Đơn vị phân tích = TỆP (tài liệu duy nhất). Mọi thành phần có học chỉ chấm trên tệp nó CHƯA THẤY:
  * bộ phân loại cặp trang (S3...): dự đoán cross-fitted theo nhóm biểu mẫu, đúng mã của teams/team2_splitting/cvlib.py (5 fold, seed 0,
    gộp 5 bộ chứng từ BSR cùng nhà cung cấp vào một nhóm; composite tổng hợp chỉ từ tài liệu đơn DEV của các nhóm huấn luyện);
  * TF-IDF của tầng 2 cascade: huấn luyện lại theo fold DEV của data/splits/splits.csv (như 03_src_cascade), tài liệu không thuộc DEV
    (8 composite khác loại) dùng mô hình huấn luyện trên DEV bỏ các tài liệu cùng `group`;
  * tầng LLM: zero-shot (không huấn luyện), qua đĩa cache; luật: không huấn luyện.
Artefact lưu ở models/ và teams/team2_splitting/models/ đã thấy mọi tài liệu dev: chỉ dùng để chấm TEST (triển khai), không dùng để chấm dev.
"""
from __future__ import annotations

import json
import math
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
for _p in (REPO, REPO / "teams" / "team2_splitting", REPO / "teams" / "00_data_and_eval" / "eval"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import cvlib  # noqa: E402  (teams/team2_splitting)
import splitlib as sl  # noqa: E402
from harness import load_benchmark, load_documents, load_or_make_splits  # noqa: E402

from src.classification.doc_classifier import (DEFAULT_SELECTION_PATH, DEFAULT_SOURCE, DocumentClassifier,  # noqa: E402
                                               load_cascade_config, text_for_classification)
from src.classification.llm_backends import DEFAULT_SPEC_ID, LLM_SPECS, OllamaBackend  # noqa: E402
from src.classification.llm_cache import DiskCache  # noqa: E402
from src.classification.tfidf_classifier import TfidfClassifier  # noqa: E402
from src.common.contracts import DocumentSlice, OCRDocumentResult, SplitResult  # noqa: E402
from src.splitting.boundary_detector import _build_result, split_document  # noqa: E402
from src.splitting.learned import fit_pair_model  # noqa: E402
from src.splitting.type_merge import load_one_sheet_types, merge_same_type  # noqa: E402

BOOT_N = 2000
BOOT_SEED = sl.BOOT_SEED
CACHE_OWN = HERE / "_cache" / "ollama"
CACHE_EXTRA = [REPO / "teams" / "team3_classification" / "experiments" / "02_llm_and_cascade" / "_cache" / "ollama",
               REPO / "cache" / "llm" / "ollama"]
FILE_GROUPS = ["single_page", "negative", "mixed", "same_other", "same_bb"]
GROUP_VI = {"single_page": "tệp 1 trang", "negative": "nhiều trang, không ghép", "mixed": "composite khác loại",
            "same_other": "composite cùng loại (ngoài BB_LAY_MAU)", "same_bb": "BB_LAY_MAU"}


# ---------------------------------------------------------------------------
# Dữ liệu
# ---------------------------------------------------------------------------
@dataclass
class Case:
    doc_id: str
    group: str
    split: str                       # DEV | EXCLUDED_COMPOSITE | TEST
    doc: OCRDocumentResult
    gsegs: List[Tuple[int, int, str]]
    fold: int                        # fold DEV (seed 0) hoặc -1
    sgroup: str                      # cột `group` của splits.csv
    n_avail: int = 0


def load_cases(scope: str) -> Tuple[List[Case], pd.DataFrame]:
    """scope 'dev' (DEV + EXCLUDED_COMPOSITE) hoặc 'test' (chỉ TEST). Trả (danh sách Case, bảng gold)."""
    gold = sl.load_gold()
    meta = gold.drop_duplicates("doc_id").set_index("doc_id")
    sp = pd.read_csv(sl.SPLITS_CSV, dtype={"doc_id": str, "group": str}).set_index("doc_id")
    want = {"dev": ("DEV", "EXCLUDED_COMPOSITE"), "test": ("TEST",)}[scope]
    ids = sorted(d for d in meta.index if meta.loc[d, "split"] in want)
    docs = sl.load_documents(ids)
    cases = []
    for d in ids:
        g = sl.gold_for_doc(gold, d, len(docs[d].pages))
        cases.append(Case(d, meta.loc[d, "eval_group"], meta.loc[d, "split"], docs[d], sl.gold_segments(g), int(sp.loc[d, "fold"]),
                          str(sp.loc[d, "group"]), len(docs[d].pages)))
    return cases, gold


def population_weights(gold: pd.DataFrame) -> Dict[str, float]:
    """Tỉ trọng nhóm theo kho mẫu 304 tệp duy nhất (composite ~7%): dùng cho trung bình có trọng số 'theo cơ cấu tệp thật'."""
    c = gold.drop_duplicates("doc_id").eval_group.value_counts()
    tot = float(c.sum())
    return {g: float(c.get(g, 0)) / tot for g in FILE_GROUPS}


# ---------------------------------------------------------------------------
# Điểm cặp trang cross-fitted
# ---------------------------------------------------------------------------
def crossfit_pair_scores(gold: pd.DataFrame, cases: Sequence[Case], cache_path: Path) -> Dict[str, List[Optional[float]]]:
    """Điểm thô 'trang i mở tài liệu mới' cho mọi tệp nhiều trang của phạm vi dev, bởi mô hình KHÔNG thấy nhóm biểu mẫu của tệp.
    Đúng quy trình cvlib.run_cv (kind='gb', seed 0, syn_seed 100+fold). Lưu cache JSON (tính ~5-10 phút)."""
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))
    dev_ids = [c.doc_id for c in cases]
    docs = {c.doc_id: c.doc for c in cases}
    groups = cvlib.cv_group_map(gold, dev_ids, True)
    fold = cvlib.fold_assignment(gold, dev_ids, cvlib.N_FOLDS, cvlib.FOLD_SEED, True)
    meta = gold.drop_duplicates("doc_id").set_index("doc_id")
    out: Dict[str, List[Optional[float]]] = {}
    for k in range(cvlib.N_FOLDS):
        held = [d for d in dev_ids if fold[d] == k]
        train = [d for d in dev_ids if fold[d] != k]
        td = cvlib.build_train_data(gold, docs, train, groups, syn_seed=100 + k)
        m = fit_pair_model(td.page_text, td.page_type, td.page_group, td.pairs, kind="gb", seed=0)
        print(f"[cross-fit fold {k}] giữ lại {len(held)} tệp, huấn luyện {len(train)}; cặp thật {td.n_real_pairs}, đường nối tổng hợp {td.n_syn_pairs}", flush=True)
        for d in held:
            if meta.loc[d, "eval_group"] in sl.GROUPS:
                s = m.doc_scores([p.full_text for p in docs[d].pages])
                out[d] = [None if x != x else float(x) for x in s]
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(out), encoding="utf-8")
    return out


def final_pair_scores(gold: pd.DataFrame, dev_cases: Sequence[Case], test_cases: Sequence[Case]) -> Dict[str, List[Optional[float]]]:
    """Mô hình huấn luyện trên TOÀN BỘ dev (như save_model.py / mục final_test của cvlib.run_cv), chấm tệp TEST. Chỉ gọi ở bước chấm TEST."""
    dev_ids = [c.doc_id for c in dev_cases]
    docs = {c.doc_id: c.doc for c in dev_cases}
    groups = cvlib.cv_group_map(gold, dev_ids, True)
    td = cvlib.build_train_data(gold, docs, dev_ids, groups, syn_seed=99)
    m = fit_pair_model(td.page_text, td.page_type, td.page_group, td.pairs, kind="gb", seed=0)
    out = {}
    for c in test_cases:
        if c.group in sl.GROUPS:
            s = m.doc_scores([p.full_text for p in c.doc.pages])
            out[c.doc_id] = [None if x != x else float(x) for x in s]
    return out


class ScoreStub:
    """Giả PairBoundaryModel cho split_document(method='model', model=...): trả điểm đã tính sẵn, ngưỡng tùy chọn."""

    def __init__(self, scores: Sequence[Optional[float]], threshold: float):
        self.s = np.array([np.nan if x is None else x for x in scores], dtype=float)
        self.threshold = threshold

    def doc_scores(self, texts):
        assert len(texts) == len(self.s)
        return self.s


# ---------------------------------------------------------------------------
# Biến thể tách
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Variant:
    name: str
    base: str                        # none | rule | rule_v2 | model
    tau: float = 0.5                 # ngưỡng cho base == model
    merge: bool = False              # gộp lát cắt liền kề cùng loại (trừ loại một-tờ)
    band: Optional[Tuple[float, float]] = None   # [lo, hi): điểm cặp trang trong khoảng này => tệp 'splitter không chắc' => người
    keep: Optional[float] = None     # với merge: ranh giới có điểm >= keep được giữ dù hai lát cắt cùng loại
    note: str = ""

    def uses_scores(self) -> bool:
        return self.base == "model"


def base_split(doc: OCRDocumentResult, v: Variant, scores: Optional[Sequence[Optional[float]]]) -> SplitResult:
    n = len(doc.pages)
    if v.base == "none":
        return _build_result(doc, [True] + [False] * (n - 1), [1.0] * n, "none")
    if v.base in ("rule", "rule_v2"):
        return split_document(doc, v.base)
    if v.base == "model":
        if scores is None:   # tệp 1 trang: không có vị trí để chấm, một lát cắt
            return _build_result(doc, [True] + [False] * (n - 1), [1.0] * n, "model")
        return split_document(doc, "model", model=ScoreStub(scores, v.tau))
    raise ValueError(v.base)


def is_unsure(v: Variant, scores: Optional[Sequence[Optional[float]]]) -> bool:
    if v.band is None or scores is None:
        return False
    lo, hi = v.band
    return any(x is not None and lo <= x < hi for x in scores[1:])


# ---------------------------------------------------------------------------
# Phân loại từng lát cắt
# ---------------------------------------------------------------------------
class LayeredCache(DiskCache):
    """Đọc cache của mình rồi tới các cache sẵn có (thí nghiệm 02, cache pipeline); ghi CHỈ vào cache của mình.
    mode 'record': thiếu khóa thì KHÔNG gọi mô hình, trả lỗi 'deferred' (để gom danh sách văn bản cần gọi); 'readonly': trả 'not_in_cache'."""

    def __init__(self, own: Path, extras: Sequence[Path], mode: str = "live"):
        super().__init__(own)
        self.extras = [DiskCache(p) for p in extras]
        assert mode in ("live", "record", "readonly")
        self.mode = mode          # live: gọi Ollama khi thiếu; record: gom văn bản thiếu; readonly: thiếu -> lỗi 'not_in_cache' (về người)

    def get(self, key):
        rec = super().get(key)
        if rec is None:
            for c in self.extras:
                rec = c.get(key)
                if rec is not None:
                    break
        return rec

    def cached(self, key, fn, *, retry_errors: bool = False):
        rec = self.get(key)
        if rec is not None and not (retry_errors and rec.get("error")):
            self.hits += 1
            return rec
        self.misses += 1
        if self.mode == "record":
            return {"error": "deferred", "latency_ms": 0.0}
        if self.mode == "readonly":
            return {"error": "not_in_cache", "latency_ms": 0.0}
        rec = fn()
        self.put(key, rec)
        return rec


class RecordingBackend:
    """Bọc backend LLM: ghi lại văn bản nào bị 'deferred' (chưa có trong cache)."""

    def __init__(self, inner: OllamaBackend, sink: set):
        self.inner, self.sink = inner, sink
        self.spec, self.tier_name = inner.spec, inner.tier_name

    @property
    def model_name(self):
        return self.inner.model_name

    def answer(self, text: str):
        a = self.inner.answer(text)
        if not a.parse_ok and a.error == "deferred":
            self.sink.add(text)
        return a


@dataclass
class Cls:
    tier: str
    label: str                  # nhãn được NHẬN ('' nếu về người)
    reason: str
    llm: bool                   # có chạy tầng LLM (kể cả lấy từ cache)
    suggested: str = ""


class Classifiers:
    """Một DocumentClassifier cho mỗi (mô hình TF-IDF): fold DEV 0-4, 'excl:<group>' cho tệp không thuộc DEV, hoặc 'artefact' (TEST)."""

    def __init__(self, bench, splits, source: str = DEFAULT_SOURCE, record_sink: Optional[set] = None, timeout: float = 120.0,
                 mode: str = "live"):
        self.bench, self.splits, self.source = bench, splits, source
        self.dev_docs = load_documents(bench, splits, source, "DEV")
        self.cfg = load_cascade_config(DEFAULT_SELECTION_PATH, source, DEFAULT_SPEC_ID, 0.01)
        assert self.cfg.measured, self.cfg.note
        self.tax_json = json.loads((REPO / "data" / "taxonomy_v2.json").read_text(encoding="utf-8"))
        self.record_sink = record_sink
        self.cache = LayeredCache(CACHE_OWN, CACHE_EXTRA, mode="record" if record_sink is not None else mode)
        inner = OllamaBackend(LLM_SPECS[DEFAULT_SPEC_ID], self.tax_json, self.cache, timeout=timeout)
        self.backend = RecordingBackend(inner, record_sink) if record_sink is not None else inner
        self._clf: Dict[str, DocumentClassifier] = {}
        self._memo: Dict[tuple, Cls] = {}

    def model_key(self, c: Case) -> str:
        if c.split == "TEST":
            return "artefact"
        return f"fold{c.fold}" if c.fold >= 0 else f"excl:{c.sgroup}"

    def clf(self, key: str) -> DocumentClassifier:
        if key not in self._clf:
            if key == "artefact":
                tf = TfidfClassifier.load()
                assert tf.meta.train_split == "DEV"
            else:
                if key.startswith("fold"):
                    tr = [d for d in self.dev_docs if d.folds[0] != int(key[4:])]
                else:
                    g = key[5:]
                    tr = [d for d in self.dev_docs if d.group != g]
                tf = TfidfClassifier(self.bench.s_classes).fit([d.text for d in tr], [d.label_s for d in tr])
            self._clf[key] = DocumentClassifier(tf, self.backend, self.cfg)
        return self._clf[key]

    def classify(self, c: Case, sl_: DocumentSlice) -> Cls:
        key = self.model_key(c)
        text = text_for_classification(sl_)
        mk = (key, text, tuple(sl_.ocr_errors))
        if mk not in self._memo:
            res, tr = self.clf(key).classify_text(text, sl_.slice_id, list(sl_.ocr_errors))
            self._memo[mk] = Cls(res.tier, "" if res.tier == "human" else res.predicted_category, res.abstain_reason or "",
                                 "llm" in tr.stages_run, res.suggested_category or "")
        return self._memo[mk]


# ---------------------------------------------------------------------------
# Chấm một tệp
# ---------------------------------------------------------------------------
def score_case(c: Case, v: Variant, scores, clfs: Classifiers, one_sheet) -> dict:
    split = base_split(c.doc, v, scores)
    cls = [clfs.classify(c, s) for s in split.slices]
    n_llm_base = sum(x.llm for x in cls)
    if v.merge and len(split.slices) > 1:
        split, groups = merge_same_type(split, [x.label or None for x in cls], one_sheet, v.keep)
        cls = [cls[g[0]] for g in groups]      # lát cắt gộp giữ kết quả của lát cắt đầu (cùng nhãn, không gọi lại LLM)
    psegs = [(s.start_page, s.end_page) for s in split.slices]
    exact = int([(a, b) for a, b, _ in c.gsegs] == psegs)
    ok = []
    for a, b, typ in c.gsegs:
        best, best_ov = None, 0
        for i, (pa, pb) in enumerate(psegs):
            ov = max(0, min(b, pb) - max(a, pa) + 1)
            if ov > best_ov:
                best, best_ov = i, ov
        ok.append(int(best is not None and cls[best].label == typ))
    types_ok = int(all(ok))
    docs_ok = sum(int(any(pa == a and pb == b and cls[i].label == typ for i, (pa, pb) in enumerate(psegs))) for a, b, typ in c.gsegs)
    unsure = is_unsure(v, scores)
    all_accepted = all(x.label for x in cls)
    auto = int(all_accepted and not unsure)
    full = int(exact and types_ok)
    return dict(doc_id=c.doc_id, group=c.group, variant=v.name, n_slices=len(psegs), n_gold_seg=len(c.gsegs), exact=exact,
                types_ok=types_ok, seg_types_ok=sum(ok), docs_ok=docs_ok, docs_total=len(c.gsegs), docs_ok_auto=docs_ok * auto, full=full, auto=auto, silent_err=int(auto and not full),
                n_llm=n_llm_base, abstain=int(not all_accepted), unsure=int(unsure),
                tiers="/".join(x.tier for x in cls), pred_segs=";".join(f"{a}-{b}:{x.label or '?'}" for (a, b), x in zip(psegs, cls)))


# ---------------------------------------------------------------------------
# Thống kê: trung bình có trọng số theo nhóm, bootstrap phân tầng, Clopper-Pearson, Wilson
# ---------------------------------------------------------------------------
def cp_interval(k: int, n: int, alpha: float = 0.05) -> Tuple[float, float]:
    """Khoảng nhị thức chính xác (Clopper-Pearson)."""
    from scipy.stats import beta
    if n == 0:
        return (float("nan"), float("nan"))
    lo = 0.0 if k == 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return lo, hi


class Boot:
    """Bootstrap phân tầng theo nhóm (lấy mẫu lại TỆP trong từng nhóm), cùng chỉ số cho mọi biến thể => so sánh ghép cặp."""

    def __init__(self, n_per_group: Dict[str, int], weights: Dict[str, float], B: int = BOOT_N, seed: int = BOOT_SEED):
        self.groups = [g for g in FILE_GROUPS if n_per_group.get(g, 0) > 0]
        self.n = n_per_group
        rng = np.random.default_rng(seed)
        self.idx = {g: rng.integers(0, n_per_group[g], size=(B, n_per_group[g])) for g in self.groups}
        w = np.array([weights[g] for g in self.groups])
        self.w = dict(zip(self.groups, w / w.sum()))      # chuẩn hóa lại trên các nhóm có mặt

    def weighted(self, vals: Dict[str, np.ndarray]) -> Tuple[float, np.ndarray]:
        point = sum(self.w[g] * float(np.mean(vals[g])) for g in self.groups)
        bt = sum(self.w[g] * vals[g][self.idx[g]].mean(axis=1) for g in self.groups)
        return float(point), bt

    def group(self, g: str, v: np.ndarray) -> Tuple[float, float, float]:
        bt = v[self.idx[g]].mean(axis=1)
        lo, hi = np.percentile(bt, [2.5, 97.5])
        return float(np.mean(v)), float(lo), float(hi)


def ci95(bt: np.ndarray) -> Tuple[float, float]:
    lo, hi = np.percentile(bt, [2.5, 97.5])
    return float(lo), float(hi)


def by_group(df: pd.DataFrame, col: str, order: Sequence[str]) -> Dict[str, np.ndarray]:
    """{nhóm: vector theo doc_id đã sắp} của cột `col` (cho cùng một biến thể)."""
    return {g: df[df.group == g].sort_values("doc_id")[col].to_numpy(dtype=float) for g in order}
