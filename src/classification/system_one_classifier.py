"""system_one_classifier.py - Cổng luật tiêu đề + tầng Kev TÙY CHỌN (Nhóm 3). Bộ phân loại đầu-cuối mặc định là
`src/classification/doc_classifier.py::DocumentClassifier` (luật -> TF-IDF -> LLM -> người); lớp ở đây giữ lại làm (a) cổng luật
(`match_rules`) mà DocumentClassifier dùng và (b) đường Kev độc lập, KHÔNG bật mặc định.

Kế thừa từ kiến trúc Jev (TypeSafe AI) và Kev (jaredpalmer/kev):
- Tầng 1 ("rule"): Cổng luật tiêu đề - khớp từ khóa trên 1500 ký tự đầu, không phân biệt dấu/khoảng trắng.
- Tầng 2 ("kev"): Kev qua HTTP (System One `Choice`), chỉ chạy khi truyền `kev_endpoint`. Theo thí nghiệm 02 (mục 5):
  tiêu chí là TÊN loại (accuracy DEV 0,962; mô tả dài chỉ 0,300 với Kev-0.8B), độ tin cậy là xác suất của tiêu chí được chọn trong
  `probabilities`, và `model_name` là mô hình MÁY CHỦ báo ở `/v1/models` (hoặc `/api/status` của máy chủ cũ) (không đặt cứng 'kev-4b': máy chủ thực tế chạy Kev-0.8B).
- Không tầng nào quyết định được -> tier "none": trả về UNKNOWN (abstain), KHÔNG đoán một lớp mặc định.

Nguyên tắc trung thực của kết quả:
- `tier` / `model_name` luôn là tầng THỰC SỰ đã tạo ra dự đoán (tên mô hình Kev lấy từ máy chủ; không hỏi được thì ghi "kev-unverified").
- Điểm của cổng luật là heuristic (`confidence_kind="heuristic"`), không phải xác suất hiệu chỉnh.
- Lỗi kết nối Kev được ghi log và nằm trong `ClassificationResult.error`; chỉ khi caller bật
  `allow_heuristic_fallback=True` thì mới dùng heuristic thay thế (và kết quả được gắn cờ `fallback_used`).
"""

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import requests

from src.classification.taxonomy import (  # noqa: F401  (CATEGORIES_19 giữ lại để tương thích import cũ)
    CATEGORIES_19,
    Taxonomy,
    TaxonomyClass,
    load_taxonomy,
)
from src.classification.zero_shot import INSTR_VI, clean_prompt_text, fetch_kev_model_name
from src.common.contracts import UNKNOWN_CATEGORY, ClassificationResult, DocumentSlice
from src.common.text_norm import NormalizedText

logger = logging.getLogger(__name__)

# Số ký tự đầu văn bản được quét bởi cổng luật tiêu đề
HEADER_WINDOW_CHARS = 1500
# Số ký tự được quét khi caller bật heuristic fallback
FALLBACK_WINDOW_CHARS = 6000
# Số ký tự gửi cho Kev (sau khi gộp khoảng trắng, như thí nghiệm 02)
KEV_TEXT_CHARS = 2000
# Mã loại không đưa vào danh sách lựa chọn của Kev (như build_label_set)
KEV_EXCLUDE = ("UNREADABLE",)
DEFAULT_KEV_ENDPOINT = "http://127.0.0.1:8009/v1/systemone"

# Điểm heuristic của cổng luật (KHÔNG phải xác suất): khớp nguyên văn cao hơn khớp ở dạng chữ dính
RULE_SCORE_EXACT = 0.9
RULE_SCORE_GLUED = 0.7
FALLBACK_SCORE = 0.5

# Dưới ngưỡng này kết quả của Kev cần người duyệt
KEV_REVIEW_THRESHOLD = 0.65


@dataclass
class RuleMatch:
    """Kết quả quét luật: lớp duy nhất khớp, hoặc danh sách lớp mơ hồ, hoặc không khớp gì."""
    category: Optional[str] = None             # Lớp duy nhất khớp (None nếu không khớp hoặc mơ hồ)
    evidence: Optional[str] = None             # Từ khóa đã khớp
    score: float = 0.0                         # Điểm heuristic
    ambiguous: List[str] = field(default_factory=list)  # Các lớp cùng khớp (>=2) -> luật không quyết định


class CascadedClassifier:
    """Cổng luật tiêu đề + tầng Kev tùy chọn (mặc định TẮT) -> abstain (tùy chọn heuristic fallback)."""

    def __init__(
        self,
        kev_endpoint: Optional[str] = None,
        taxonomy: Optional[Taxonomy] = None,
        taxonomy_path: Optional[Union[str, Path]] = None,
        allow_heuristic_fallback: bool = False,
        kev_timeout: Tuple[float, float] = (0.5, 30.0),
        kev_retry_seconds: float = 30.0,
    ):
        """
        kev_endpoint: None (mặc định) = KHÔNG dùng Kev; truyền DEFAULT_KEV_ENDPOINT để bật tầng Kev tùy chọn.
        taxonomy / taxonomy_path: nguồn danh mục; mặc định data/taxonomy_v2.json nếu có, else 19 nhãn legacy.
        allow_heuristic_fallback: opt-in; khi Kev lỗi và luật không quyết định, dùng heuristic quét rộng hơn.
        kev_timeout: (connect, read) giây. Connect ngắn để fail-fast khi server tắt.
        kev_retry_seconds: sau khi Kev lỗi, bỏ qua gọi lại trong khoảng này (tránh chờ timeout mỗi tài liệu).
        """
        self.kev_endpoint = kev_endpoint
        self.taxonomy = taxonomy if taxonomy is not None else load_taxonomy(taxonomy_path)
        self.allow_heuristic_fallback = allow_heuristic_fallback
        self.kev_timeout = kev_timeout
        self.kev_retry_seconds = kev_retry_seconds
        self._class_ids = set(self.taxonomy.class_ids)
        self._last_kev_error: Optional[str] = None
        self._kev_failed_at: Optional[float] = None
        self._kev_model: Optional[str] = None
        # Chuẩn hóa từ khóa 1 lần: (class_id, từ khóa gốc)
        self._rules: List[Tuple[str, str]] = [
            (c.id, kw) for c in self.taxonomy.classes for kw in c.keywords if kw.strip()
        ]

    # ------------------------------------------------------------------
    # Tầng 1: cổng luật tiêu đề
    # ------------------------------------------------------------------
    def match_rules(self, text: str, window: int = HEADER_WINDOW_CHARS) -> RuleMatch:
        """Quét từ khóa trên `window` ký tự đầu; chỉ quyết định khi ĐÚNG MỘT lớp khớp (nhiều lớp -> mơ hồ)."""
        norm = NormalizedText(text[:window])
        hits: Dict[str, Tuple[str, str]] = {}  # class_id -> (từ khóa, mode) tốt nhất
        for cid, kw in self._rules:
            mode = norm.match_mode(kw)
            if mode is None:
                continue
            if cid not in hits or (mode == "exact" and hits[cid][1] == "glued"):
                hits[cid] = (kw, mode)

        if not hits:
            return RuleMatch()
        if len(hits) > 1:
            return RuleMatch(ambiguous=sorted(hits))
        cid, (kw, mode) = next(iter(hits.items()))
        return RuleMatch(
            category=cid,
            evidence=kw,
            score=RULE_SCORE_EXACT if mode == "exact" else RULE_SCORE_GLUED,
        )

    def fast_header_gate(self, text: str) -> Optional[str]:
        """Tầng 1: trả về nhãn nếu cổng luật quyết định được, ngược lại None (không khớp hoặc mơ hồ)."""
        return self.match_rules(text).category

    def _heuristic_fallback(self, text: str) -> RuleMatch:
        """Heuristic quét rộng (chỉ khi caller opt-in): lớp có nhiều từ khóa khác nhau khớp nhất; hòa -> không quyết định."""
        norm = NormalizedText(text[:FALLBACK_WINDOW_CHARS])
        counts: Dict[str, List[str]] = {}
        for cid, kw in self._rules:
            if norm.contains(kw):
                counts.setdefault(cid, []).append(kw)
        if not counts:
            return RuleMatch()
        best = max(len(v) for v in counts.values())
        winners = sorted(c for c, v in counts.items() if len(v) == best)
        if len(winners) > 1:
            return RuleMatch(ambiguous=winners)
        return RuleMatch(category=winners[0], evidence=", ".join(counts[winners[0]]), score=FALLBACK_SCORE)

    # ------------------------------------------------------------------
    # Tầng 2: Kev
    # ------------------------------------------------------------------
    def kev_criteria(self) -> Dict[str, str]:
        """Tiêu chí gửi cho Kev: {mã loại: TÊN loại}. Tên ngắn là cấu hình đo tốt nhất (02 mục 5); KHÔNG gửi mô tả dài."""
        return {c.id: (c.name_vi or c.id) for c in self.taxonomy.classes if c.id not in KEV_EXCLUDE}

    def kev_server_model(self) -> Optional[str]:
        """Tên mô hình máy chủ Kev đang nạp (`/v1/models` -> `run`, hoặc `/api/status` -> `current_model` của máy chủ cũ); None nếu không hỏi được."""
        if self._kev_model is None and self.kev_endpoint:
            self._kev_model = fetch_kev_model_name(self.kev_endpoint, timeout=self.kev_timeout)
            if self._kev_model is None:
                logger.warning("Không hỏi được mô hình của Kev (%s)", self.kev_endpoint)
        return self._kev_model

    def classify_with_kev(self, text: str) -> Dict[str, Any]:
        """Tầng 2: gọi Kev qua /v1/systemone với tiêu chí = TÊN loại (cấu hình đã đo).

        Trả về dict: category (None nếu Kev không quyết định được), confidence (xác suất của tiêu chí được chọn trong `probabilities`;
        None nếu server không báo), probabilities, model (tên mô hình máy chủ báo hoặc None), error (None nếu gọi thành công).
        KHÔNG có heuristic ngầm ở đây.
        """
        result: Dict[str, Any] = {"category": None, "confidence": None, "probabilities": {}, "model": None, "error": None}

        if not self.kev_endpoint:
            result["error"] = "Chưa cấu hình kev_endpoint"
            return result

        # Đã lỗi gần đây -> không chờ timeout lại cho từng tài liệu, nhưng vẫn báo lỗi trung thực
        if self._kev_failed_at is not None and (time.monotonic() - self._kev_failed_at) < self.kev_retry_seconds:
            result["error"] = f"Kev không khả dụng (lỗi gần nhất: {self._last_kev_error})"
            return result

        payload = {
            "state": clean_prompt_text(text, KEV_TEXT_CHARS),
            "model": "kev-latest",   # như thí nghiệm 02; mô hình thực sự do máy chủ quyết định (xem kev_server_model)
            "questions": {
                "category": {
                    "type": "choice",
                    "instructions": INSTR_VI,
                    "criteria": self.kev_criteria(),
                }
            },
        }

        try:
            resp = requests.post(self.kev_endpoint, json=payload, timeout=self.kev_timeout)
            if resp.status_code != 200:
                raise RuntimeError(f"Kev trả về HTTP {resp.status_code}")
            data = resp.json()
        except (requests.RequestException, RuntimeError, ValueError) as e:
            self._record_kev_failure(f"{type(e).__name__}: {e}")
            result["error"] = self._last_kev_error
            return result

        self._kev_failed_at = None
        self._last_kev_error = None

        cat_ans = (data.get("answers") or {}).get("category") or {}
        choice = cat_ans.get("choice")
        probs = {str(k): float(v) for k, v in (cat_ans.get("probabilities") or {}).items()}
        result["probabilities"] = probs

        if not choice:
            result["error"] = "Kev trả lời nhưng không có 'choice'"
            return result
        if choice not in self._class_ids:
            result["error"] = f"Kev trả về nhãn không thuộc taxonomy: {choice!r}"
            return result

        result["category"] = choice
        result["model"] = self.kev_server_model()      # chỉ hỏi khi Kev đã trả nhãn hợp lệ
        # thang xác suất của thí nghiệm 02: p(tiêu chí được chọn) trong `probabilities`; `confidence` của server là đại lượng riêng
        conf = probs.get(choice)
        if conf is None:
            conf = cat_ans.get("confidence")
        result["confidence"] = float(conf) if conf is not None else None
        return result

    def _record_kev_failure(self, message: str) -> None:
        """Ghi log lỗi Kev (cảnh báo khi trạng thái chuyển từ ổn sang lỗi hoặc đổi nguyên nhân)."""
        if message != self._last_kev_error:
            logger.warning("Kev (%s) lỗi: %s", self.kev_endpoint, message)
        self._last_kev_error = message
        self._kev_failed_at = time.monotonic()

    # ------------------------------------------------------------------
    # Điều phối
    # ------------------------------------------------------------------
    def classify_slice(self, doc_slice: DocumentSlice) -> ClassificationResult:
        """Phân loại toàn diện một DocumentSlice: rule -> kev -> (fallback tùy chọn) -> abstain."""
        start_t = time.time()
        text = doc_slice.combined_text or ""

        def done(**kwargs) -> ClassificationResult:
            return ClassificationResult(
                slice_id=doc_slice.slice_id,
                processing_time_ms=(time.time() - start_t) * 1000,
                **kwargs,
            )

        def abstain(reason: str, error: Optional[str] = None) -> ClassificationResult:
            return done(
                predicted_category=UNKNOWN_CATEGORY,
                confidence=0.0,
                model_name="none",
                tier="none",
                confidence_kind="none",
                requires_human_review=True,
                abstain_reason=reason,
                error=error,
            )

        if not text.strip():
            return abstain("empty_text", "; ".join(doc_slice.ocr_errors) or None)

        # 1. Cổng luật tiêu đề
        rule = self.match_rules(text)
        if rule.category:
            return done(
                predicted_category=rule.category,
                confidence=rule.score,
                model_name="keyword_rule_gate",
                tier="rule",
                confidence_kind="heuristic",
                requires_human_review=False,
                evidence=rule.evidence,
            )

        # 2. Kev (chỉ khi được cấu hình; mặc định TẮT -> không có lỗi Kev giả trong kết quả)
        kev = self.classify_with_kev(text) if self.kev_endpoint else {"category": None, "confidence": None, "probabilities": {}, "model": None, "error": None}
        if kev["category"]:
            conf = kev["confidence"]
            return done(
                predicted_category=kev["category"],
                confidence=conf if conf is not None else 0.0,
                probabilities=kev["probabilities"],
                model_name=kev["model"] or "kev-unverified",
                tier="kev",
                confidence_kind="model" if conf is not None else "none",
                requires_human_review=(conf is None or conf < KEV_REVIEW_THRESHOLD),
                error=None if conf is not None else "Kev không báo confidence",
            )

        # 3. Heuristic fallback - chỉ khi caller chủ động bật
        if self.allow_heuristic_fallback:
            fb = self._heuristic_fallback(text)
            if fb.category:
                return done(
                    predicted_category=fb.category,
                    confidence=fb.score,
                    model_name="keyword_fallback",
                    tier="rule",
                    confidence_kind="heuristic",
                    requires_human_review=True,
                    evidence=fb.evidence,
                    error=kev["error"],
                    fallback_used=True,
                )

        # 4. Không tầng nào quyết định được -> abstain
        if kev["error"]:
            reason = "kev_error"
        elif rule.ambiguous:
            reason = "rule_ambiguous"
        else:
            reason = "no_rule_match"
        result = abstain(reason, kev["error"])
        if rule.ambiguous:
            result.evidence = "Luật mơ hồ giữa: " + " | ".join(rule.ambiguous)
        return result
