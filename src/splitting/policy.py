"""policy.py - Chính sách tách trang của pipeline: chọn phương pháp tách + hiệu chỉnh nhận biết loại, chọn trên bằng chứng end-to-end.

Số đo và lý do chọn mặc định: teams/00_data_and_eval/experiments/01_end_to_end/RESULTS.md (thí nghiệm 01 của Data & Eval, trên đáp án máy,
chưa người kiểm). Tóm tắt: tách trang chưa làm tăng tỉ lệ TỆP đúng hoàn toàn so với không tách (92% tệp là tài liệu đơn/nhiều trang không ghép),
nhưng giao đúng nhiều TÀI LIỆU hơn nhiều khi có tệp ghép; vì vậy mặc định là `model+merge` (S10): bộ phân loại cặp trang + gộp lát cắt liền kề cùng loại.
`model+merge+id` (thêm quy tắc "bản khác") là tùy chọn, chưa là mặc định (báo cáo 04 N1).

Một chính sách gồm 3 phần:
  1. `method`: "none" | "rule" | "rule_v2" | "model" -> `split_document`;
  2. `merge_same_type` (+ `keep_above`): SAU khi phân loại từng lát cắt, gộp lát cắt liền kề cùng loại (src/splitting/type_merge.py) -
     việc này do pipeline làm vì cần kết quả phân loại;
  3. `flag_min` (tùy chọn): tệp có điểm cặp trang >= flag_min bị đánh dấu "nghi composite" -> cả tệp chuyển cho người (chế độ `triage`).
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import List, Optional, Sequence, Tuple, Union

from src.common.contracts import OCRDocumentResult, SplitResult
from src.splitting.boundary_detector import METHODS, split_document


@dataclass(frozen=True)
class SplitPolicy:
    name: str = "model+merge"
    method: str = "model"
    threshold: Optional[float] = None       # ngưỡng điểm cặp trang cho method="model"; None = ngưỡng của chính mô hình (0,5)
    merge_same_type: bool = False
    keep_above: Optional[float] = None      # với merge: ranh giới có điểm >= keep_above được giữ dù hai lát cắt cùng loại
    flag_min: Optional[float] = None        # điểm cặp trang >= flag_min => cả tệp chuyển cho người (lý do possible_composite)
    id_rule: bool = False                   # T5: quy tắc "bản khác" (cùng mẫu, số hiệu đầu trang khác) THÊM ranh giới điểm 1,0 (src/splitting/learned_id.py)

    def __post_init__(self):
        if self.method not in METHODS:
            raise ValueError(f"method phải thuộc {METHODS}, nhận {self.method!r}")
        if self.keep_above is not None and not self.merge_same_type:
            raise ValueError("keep_above chỉ có nghĩa khi merge_same_type=True")
        if self.id_rule and self.method != "model":
            raise ValueError("id_rule chỉ dùng với method='model'")

    @property
    def needs_model(self) -> bool:
        return self.method == "model" or self.flag_min is not None


# Các giá trị 0,7 / 0,99 / 0,3 được CHỌN TRÊN DEV (dev_selection.json của thí nghiệm 01_end_to_end); không chỉnh theo TEST.
PRESETS = {
    "none": SplitPolicy("none", "none"),                                                       # S0: không tách
    "rule": SplitPolicy("rule", "rule"),                                                       # S1
    "rule_v2": SplitPolicy("rule_v2", "rule_v2"),                                              # S2
    "model": SplitPolicy("model", "model", None),                                              # S3
    "model+merge": SplitPolicy("model+merge", "model", 0.7, True, 0.99),                       # S10: mặc định cũ (thí nghiệm 01)
    "triage": SplitPolicy("triage", "none", flag_min=0.3),                                     # S9: không tách, nghi composite -> người
    # T5 (teams/team2_splitting/experiments/06_same_type): như model+merge, thêm quy tắc "bản khác" (dev 245 tệp: +3 tệp composite cùng loại đúng, 0 hỏng; TEST không đổi).
    # KHÔNG phải mặc định (báo cáo 04, N1: bằng chứng nằm trong mẫu thiết kế, TEST không có composite loại này): bật bằng --splitter model+merge+id.
    # Khi dùng `model+merge`, quy tắc `id` vẫn chạy ở chế độ BÓNG (xem `PolicyInfo.id_extra_pages`): không tách, chỉ chuyển người.
    "model+merge+id": SplitPolicy("model+merge+id", "model", 0.7, True, 0.99, id_rule=True),
}
DEFAULT_PRESET = "model+merge"                   # S10; quay về mặc định an toàn của chạy bóng (báo cáo 04, mục 7)


def resolve_policy(p: Union[None, str, SplitPolicy]) -> SplitPolicy:
    if p is None:
        return PRESETS[DEFAULT_PRESET]
    if isinstance(p, SplitPolicy):
        return p
    if p not in PRESETS:
        raise ValueError(f"chính sách tách không biết: {p!r}; có: {sorted(PRESETS)}")
    return PRESETS[p]


class ScoredModel:
    """Giả PairBoundaryModel với điểm đã tính sẵn (tính điểm một lần cho cả việc tách lẫn việc đánh dấu 'nghi composite')."""

    def __init__(self, scores: Sequence[float], threshold: float):
        self.s = scores
        self.threshold = threshold

    def doc_scores(self, texts):
        return self.s


@dataclass
class PolicyInfo:
    scores: Optional[List[float]] = None    # điểm thô của mô hình cặp trang (NaN: trang 1/trống); None nếu chính sách không dùng mô hình
    flagged: bool = False                   # chính sách `flag_min` và tệp có điểm >= flag_min
    max_score: Optional[float] = None
    id_extra_pages: Optional[List[int]] = None  # CHẾ ĐỘ BÓNG của quy tắc `id`: số trang (1-based) mà quy tắc SẼ thêm làm ranh giới nhưng chính sách hiện tại không tách; None nếu không tính


def split_with_policy(ocr_doc: OCRDocumentResult, policy: SplitPolicy, model: Optional[object] = None) -> Tuple[SplitResult, PolicyInfo]:
    """Tách theo `policy.method` (chưa gộp theo loại - việc đó cần kết quả phân loại). `model`: PairBoundaryModel đã nạp (None -> nạp mặc định khi cần)."""
    info = PolicyInfo()
    if not policy.needs_model or not ocr_doc.pages:
        return split_document(ocr_doc, policy.method), info
    if model is None:
        from src.splitting.learned import load_default_model
        model = load_default_model()
    scores = [float(x) for x in model.doc_scores([p.full_text for p in ocr_doc.pages])]
    info.scores = scores
    real = [x for x in scores[1:] if x == x]
    info.max_score = max(real) if real else None
    if policy.flag_min is not None:
        info.flagged = bool(real and max(real) >= policy.flag_min)
    if policy.method == "model":
        thr = policy.threshold if policy.threshold is not None else model.threshold
        if policy.id_rule:
            # trang được quy tắc "bản khác" bật nhận điểm 1,0: thành ranh giới và (>= keep_above) không bị gộp lại theo loại
            from src.splitting.learned_id import id_rule_pages
            fl = id_rule_pages([p.full_text for p in ocr_doc.pages])
            scores = [1.0 if fl[i] else s for i, s in enumerate(scores)]
        else:
            # bóng: tính (rẻ, không LLM) trang nào quy tắc `id` sẽ thêm ranh giới; KHÔNG đổi cách tách
            from src.splitting.learned_id import id_rule_pages
            fl = id_rule_pages([p.full_text for p in ocr_doc.pages])
            info.id_extra_pages = [ocr_doc.pages[i].page_number for i, f in enumerate(fl) if f and not (scores[i] == scores[i] and scores[i] >= thr)]
        return split_document(ocr_doc, "model", model=ScoredModel(scores, thr)), info
    return split_document(ocr_doc, policy.method), info
