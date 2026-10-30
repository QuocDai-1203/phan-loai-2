"""boundary_detector.py - Module phát hiện ranh giới và phân đoạn tài liệu đa trang (Nhóm 2).

Nhiệm vụ:
- Nhận đầu vào là OCRDocumentResult (từ Nhóm 1 hoặc Mock).
- Áp dụng các quy tắc nhận diện trang bắt đầu (FIRST_PAGE) vs trang tiếp nối (CONTINUATION_PAGE).
- Xuất ra SplitResult chứa danh sách các DocumentSlice theo đúng contracts.py.

LƯU Ý: `DocumentSlice.boundary_confidence` ở đây là CỜ CỦA LUẬT (hằng số RULE_BOUNDARY_FLAG),
không phải xác suất đã hiệu chỉnh. Khớp từ khóa không phân biệt dấu/khoảng trắng (src.common.text_norm).

Bốn phương pháp chọn bằng `split_document(doc, method=...)` (mặc định "rule" = hành vi cũ, KHÔNG đổi):
  * "none"     - không tách: cả tệp là MỘT lát cắt (`boundary_method="none"`); dùng làm đối chứng và cho chính sách `none`/`triage`.
  * "rule"     - luật cũ ở `is_new_document_start` (đã đo: tách nhầm nhiều trên tài liệu nhiều trang không ghép).
  * "rule_v2"  - bộ luật đã sửa `src/splitting/rules_v2.py`; `boundary_confidence` vẫn là cờ luật 0,95.
  * "model"    - bộ phân loại cặp trang đã huấn luyện (`src/splitting/learned.py`, tệp ở teams/team2_splitting/models/);
                 `boundary_confidence` của lát cắt = ĐIỂM THÔ của mô hình tại trang mở lát cắt (chưa hiệu chỉnh, KHÔNG phải xác suất);
                 lát cắt đầu tiên luôn có 1.0 (trang 1 là trang đầu theo định nghĩa, không phải quyết định của mô hình).
Số đo của từng phương pháp: teams/team2_splitting/experiments/*/RESULTS.md.
"""

from typing import List, Optional, Sequence
from src.common.contracts import OCRDocumentResult, OCRPageResult, DocumentSlice, SplitResult
from src.common.text_norm import NormalizedText

# Giá trị cờ gán cho mọi ranh giới do luật tạo ra (KHÔNG phải xác suất)
RULE_BOUNDARY_FLAG = 0.95


# Danh sách các từ khóa tiêu đề chứng từ thường mở đầu văn bản mới
TITLE_KEYWORDS = [
    "HỢP ĐỒNG", "HOP DONG", "PHỤ LỤC", "PHU LUC", "THANH LÝ", "THANH LY",
    "PHIẾU XUẤT KHO", "PHIEU XUAT KHO", "BIÊN BẢN", "BIEN BAN",
    "CHỨNG THƯ CHẤT LƯỢNG", "CHUNG THU CHAT LUONG", "CERTIFICATE",
    "GIẤY CHỨNG NHẬN", "GIAY CHUNG NHAN", "ĐƠN ĐẶT HÀNG", "DON DAT HANG",
    "GIẤY XÁC NHẬN", "GIAY XAC NHAN", "HỒ SƠ", "HO SO"
]


def is_new_document_start(page: OCRPageResult, is_first_page_of_pdf: bool) -> bool:
    """Xác định xem trang này có phải là trang bắt đầu một chứng từ mới hay không."""
    if is_first_page_of_pdf:
        return True

    # Dấu hiệu 1: Có Quốc hiệu tiêu ngữ trong trang (so khớp không phân biệt dấu/khoảng trắng)
    if NormalizedText(page.full_text).contains("CỘNG HÒA XÃ HỘI"):
        return True

    # Dấu hiệu 2: Dòng đầu có tiêu đề lớn đặc trưng
    lines = [line.strip() for line in page.full_text.split("\n") if line.strip()]
    first_few_lines = NormalizedText(" ".join(lines[:6]))

    return first_few_lines.contains_any(TITLE_KEYWORDS)


METHODS = ("rule", "rule_v2", "model", "none")
DEFAULT_METHOD = "rule"


def _slice_text(pages: Sequence[OCRPageResult]) -> str:
    return "\n\n--- TIẾP THEO ---\n\n".join(p.full_text for p in pages)


def _build_result(ocr_doc: OCRDocumentResult, starts: Sequence[bool], confidences: Sequence[float], method: str) -> SplitResult:
    """Gom các trang thành lát cắt. starts[i] = True nếu trang thứ i (0-based) mở lát cắt mới (starts[0] luôn True).
    confidences[i] = giá trị boundary_confidence của lát cắt mở bởi trang i (chỉ dùng khi starts[i])."""
    slices: List[DocumentSlice] = []
    cur: List[OCRPageResult] = []
    cur_conf = confidences[0]
    counter = 1

    def close():
        nonlocal counter
        slices.append(
            DocumentSlice(
                slice_id=f"slice_{counter:03d}",
                start_page=cur[0].page_number,
                end_page=cur[-1].page_number,
                page_count=len(cur),
                combined_text=_slice_text(cur),
                pages=list(cur),
                boundary_confidence=cur_conf,
                boundary_method=method,
                ocr_errors=[p.error for p in cur if p.error],   # lỗi OCR của từng trang được truyền xuống lát cắt
            )
        )
        counter += 1

    for idx, page in enumerate(ocr_doc.pages):
        if starts[idx] and cur:
            close()
            cur = [page]
            cur_conf = confidences[idx]
        else:
            cur.append(page)
    if cur:
        close()
    return SplitResult(source_file=ocr_doc.file_name, total_pages=ocr_doc.total_pages, slices=slices)


def split_document(ocr_doc: OCRDocumentResult, method: str = DEFAULT_METHOD, model: Optional[object] = None) -> SplitResult:
    """Gom nhóm các trang liên tiếp thành từng lát cắt DocumentSlice.

    method: "rule" (mặc định, hành vi cũ) | "rule_v2" | "model" | "none". Với "model", `model` là PairBoundaryModel đã nạp
    (`src.splitting.learned.load_model`); nếu None thì nạp mô hình mặc định ở teams/team2_splitting/models/ (ném lỗi nếu thiếu,
    KHÔNG âm thầm quay về luật). `boundary_method` của mỗi lát cắt ghi đúng phương pháp đã chạy.
    """
    if method not in METHODS:
        raise ValueError(f"method phải thuộc {METHODS}, nhận {method!r}")
    if not ocr_doc.pages:
        return SplitResult(source_file=ocr_doc.file_name, total_pages=0, slices=[])
    pages = ocr_doc.pages
    if method == "none":
        return _build_result(ocr_doc, [True] + [False] * (len(pages) - 1), [1.0] * len(pages), "none")
    if method == "rule":
        starts = [is_new_document_start(p, i == 0) for i, p in enumerate(pages)]
        return _build_result(ocr_doc, starts, [RULE_BOUNDARY_FLAG] * len(pages), "rule")
    texts = [p.full_text for p in pages]
    if method == "rule_v2":
        from src.splitting.rules_v2 import rule_starts
        return _build_result(ocr_doc, rule_starts(texts), [RULE_BOUNDARY_FLAG] * len(pages), "rule_v2")
    # method == "model"
    from src.splitting.learned import load_default_model
    mdl = model if model is not None else load_default_model()
    scores = mdl.doc_scores(texts)
    thr = mdl.threshold
    starts = [True] + [bool(s == s and s >= thr) for s in scores[1:]]     # s == s: loại NaN (trang trống / chưa có trang trước)
    conf = [1.0] + [float(s) if s == s else 0.0 for s in scores[1:]]
    return _build_result(ocr_doc, starts, conf, "model")
