"""contracts.py - Hợp đồng dữ liệu trung gian chuẩn hóa (Interface Contracts).

Dùng làm kim chỉ nam giao tiếp giữa 4 nhóm nghiên cứu song song:
- Nhóm 1: OCR & Handwriting (xuất ra OCRDocumentResult)
- Nhóm 2: Document Splitting (nhận OCRDocumentResult, xuất ra SplitResult)
- Nhóm 3: Classification Engine (nhận DocumentSlice, xuất ra ClassificationResult)
- Nhóm 4: Information Extraction (nhận DocumentSlice + ClassificationResult, xuất ra ExtractionResult)
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


# ==========================================
# 1. HỢP ĐỒNG ĐẦU RA NHÓM 1 (OCR & HANDWRITING)
# ==========================================
class BoundingBox(BaseModel):
    """Tọa độ pixel của từng từ/dòng chữ được phát hiện."""
    text: str
    x: float
    y: float
    w: float
    h: float
    confidence: float = 1.0
    polygon: Optional[List[List[float]]] = None  # 4 góc xoay: [[x1, y1], [x2, y2], ...]
    is_handwritten: bool = False                 # Đánh dấu chữ viết tay hay chữ in


class OCRPageResult(BaseModel):
    """Kết quả OCR của một trang đơn lẻ.

    Quy ước lỗi: khi OCR thất bại, `full_text` PHẢI để rỗng và lý do ghi vào `error`
    (không bao giờ nhét thông báo lỗi vào `full_text` vì sẽ bị phân loại như văn bản thật).
    """
    page_number: int                             # Đánh số 1-indexed
    width: int
    height: int
    full_text: str = ""                          # Toàn văn bản của trang ghép lại ("" nếu lỗi)
    boxes: List[BoundingBox] = Field(default_factory=list)
    # LƯU Ý: hai cờ dưới chỉ là HEURISTIC khớp từ khóa trong văn bản OCR (không phát hiện con dấu/chữ ký thật trên ảnh).
    has_header_seal: bool = False                # Văn bản có từ khóa quốc hiệu/tiêu ngữ (CỘNG HÒA, VIỆT NAM...)
    has_signature_box: bool = False              # Văn bản có từ khóa ô ký tên (KÝ, GHI RÕ HỌ TÊN, ĐẠI DIỆN BÊN...)
    ocr_engine: str = "apple_vision"             # tên engine THỰC SỰ đã chạy: 'apple_vision' | 'rapid_ocr' | 'digital' | chuỗi đầy đủ của src/ocr/vietocr_engine (vd 'rapidocr-3.10.0/PP-OCRv5_det_mobile + vietocr-0.3.13/vgg_seq2seq@cpu') | 'pymupdf-<ver>/get_text'
    source: str = "ocr"                          # 'text_layer' (lớp chữ số tin cậy của PDF) | 'ocr' (nhận dạng từ ảnh) | 'embedded_ocr_layer+ocr' (PDF có lớp chữ nhúng bị loại vì không đáng tin, đã OCR lại ảnh)
    error: Optional[str] = None                  # None nếu OCR thành công; ngược lại là lý do thất bại
    # --- thêm ở thay đổi hợp đồng #1 (2026-10-12), tương thích ngược: có mặc định ---
    mean_conf: Optional[float] = None            # độ tin cậy trung bình của bộ nhận dạng (None nếu text layer / không có dòng). KHÔNG so được giữa các engine
    flags: List[str] = Field(default_factory=list)  # ghi chú của engine: 'bg_normalized', 'rotated_90|180|270', 'no_boxes', 'empty_text', 'embedded_layer_rejected:<lý do>'


class OCRDocumentResult(BaseModel):
    """Kết quả OCR của toàn bộ file PDF (Đầu ra Nhóm 1 -> Đầu vào Nhóm 2)."""
    file_name: str
    total_pages: int
    pages: List[OCRPageResult] = Field(default_factory=list)
    processing_time_ms: float = 0.0
    error: Optional[str] = None                  # Tóm tắt lỗi cấp tài liệu (vd: "Trang 2: ...") hoặc None


# ==========================================
# 2. HỢP ĐỒNG ĐẦU RA NHÓM 2 (DOCUMENT SPLITTING)
# ==========================================
class DocumentSlice(BaseModel):
    """Một lát cắt tài liệu đơn lẻ được tách ra từ file PDF đa trang."""
    slice_id: str                                # Ví dụ: "slice_001"
    start_page: int                              # Trang bắt đầu (1-indexed)
    end_page: int                                # Trang kết thúc (inclusive)
    page_count: int
    combined_text: str                           # Ghép text từ start_page đến end_page
    pages: List[OCRPageResult] = Field(default_factory=list)
    # Cờ của luật tách trang (rule flag), KHÔNG phải xác suất đã hiệu chỉnh: hiện là hằng số do boundary_detector đặt.
    boundary_confidence: float = 1.0
    # Phương pháp cho ra ranh giới: 'rule' (luật cũ, từ khóa tiêu đề) | 'rule_v2' (luật đã sửa) | 'model' (bộ phân loại cặp trang)
    # | 'none' (không tách, cả tệp một lát cắt). Hậu tố '+type_merge' = lát cắt này là kết quả gộp các lát cắt liền kề cùng loại (src/splitting/type_merge.py).
    boundary_method: str = "rule"

    ocr_errors: List[str] = Field(default_factory=list)  # Lỗi OCR của các trang trong lát cắt (nếu có)


class SplitResult(BaseModel):
    """Kết quả phân đoạn tài liệu đa trang (Đầu ra Nhóm 2 -> Đầu vào Nhóm 3)."""
    source_file: str
    total_pages: int
    slices: List[DocumentSlice] = Field(default_factory=list)
    processing_time_ms: float = 0.0


# ==========================================
# 3. HỢP ĐỒNG ĐẦU RA NHÓM 3 (CLASSIFICATION ENGINE)
# ==========================================
# Nhãn đặc biệt khi bộ phân loại từ chối quyết định (abstain) - KHÔNG phải một lớp thật
UNKNOWN_CATEGORY = "UNKNOWN"
# Các giá trị hợp lệ của ClassificationResult.tier. 'kev' là tầng Kev tùy chọn của CascadedClassifier (legacy);
# 'tfidf' | 'llm' | 'human' do DocumentClassifier (src/classification/doc_classifier.py) tạo ra. 'none' = không tầng nào quyết định.
CLASSIFICATION_TIERS = ("rule", "tfidf", "kev", "llm", "human", "none")


class ClassificationResult(BaseModel):
    """Kết quả phân loại một lát cắt tài liệu (Đầu ra Nhóm 3 -> Đầu vào Nhóm 4).

    Kết quả luôn nói thật tầng nào đã tạo ra nó (`tier`, `model_name`). Nếu không tầng nào quyết định được,
    `predicted_category == UNKNOWN_CATEGORY`, `confidence == 0.0`, `requires_human_review == True`.
    """
    slice_id: str
    predicted_category: str                      # Nhãn lớp (id taxonomy / tên thư mục chuẩn) hoặc UNKNOWN_CATEGORY
    confidence: float = 0.0                      # Ý nghĩa tùy `confidence_kind` (xem bên dưới), 0.0 nếu abstain
    probabilities: Dict[str, float] = Field(default_factory=dict) # Phân phối xác suất do MÔ HÌNH trả về (rỗng nếu không có)
    model_name: str = "none"                     # Engine thực sự đã chạy: 'keyword_rule_gate' | 'keyword_fallback' | tên bộ TF-IDF đã nạp | tên mô hình LLM/Kev mà máy chủ báo | 'none'
    requires_human_review: bool = False          # True nếu abstain, lỗi, dùng fallback hoặc confidence thấp
    processing_time_ms: float = 0.0
    tier: str = "none"                           # Tầng tạo ra kết quả: xem CLASSIFICATION_TIERS (thêm 'tfidf' | 'llm' | 'human' ở thay đổi #1)
    confidence_kind: str = "none"                # 'model' (do mô hình báo) | 'heuristic' (điểm luật, KHÔNG phải xác suất) | 'none'
    abstain_reason: Optional[str] = None         # Vì sao abstain/từ chối (vd: 'empty_text', 'no_rule_match', 'rule_ambiguous', 'kev_error', 'cascade_rejected', 'llm_error', 'llm_unavailable')
    evidence: Optional[str] = None               # Từ khóa luật đã khớp (nếu tầng 'rule')
    error: Optional[str] = None                  # Lỗi hạ tầng gặp phải (vd: Kev server không kết nối được); None nếu không có
    fallback_used: bool = False                  # True nếu caller bật heuristic fallback và kết quả đến từ đó
    # --- thêm ở thay đổi hợp đồng #1 (2026-10-12), tương thích ngược: có mặc định ---
    # Khi tier == 'human' (cascade từ chối): `predicted_category` vẫn là UNKNOWN, `confidence` vẫn 0.0; gợi ý cho nhân viên nằm ở đây.
    suggested_category: Optional[str] = None     # nhãn gợi ý của tầng cao nhất đã chạy (LLM, nếu không có thì TF-IDF); KHÔNG được tự xếp hồ sơ theo nhãn này
    suggested_confidence: Optional[float] = None # độ tin cậy mô hình báo cho gợi ý (không phải xác suất hiệu chỉnh)
    suggestion_source: Optional[str] = None      # 'llm' | 'tfidf' | 'kev': tầng đưa ra gợi ý


# ==========================================
# 4. HỢP ĐỒNG ĐẦU RA NHÓM 4 (INFORMATION EXTRACTION)
# ==========================================
class ExtractedEntity(BaseModel):
    """Một thực thể nghiệp vụ trích xuất được."""
    label: str                                   # Ví dụ: 'to_chuc', 'nguoi', 'ma_so_thue', 'xang_dau'
    text: str                                    # Giá trị trích xuất: 'PETROLIMEX GIA LAI'
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    confidence: float = 1.0


class ExtractedTable(BaseModel):
    """Bảng biểu hoặc danh mục hàng hóa (ví dụ dòng hàng xăng dầu, số lít)."""
    table_name: str                              # 'danh_muc_xang_dau' | 'chi_tiet_giao_nhan'
    headers: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    """Kết quả trích xuất cấu trúc cuối cùng đẩy vào hệ thống ERP / kế toán."""
    slice_id: str
    document_type: str
    entities: List[ExtractedEntity] = Field(default_factory=list)
    entity_dict: Dict[str, Any] = Field(default_factory=dict) # {"ben_a": "...", "mst": "..."}
    tables: List[ExtractedTable] = Field(default_factory=list)
    processing_time_ms: float = 0.0
    status: str = "ok"                           # 'ok' | 'error' (mô hình lỗi/không nạp được) | 'skipped' (không có văn bản)
    error: Optional[str] = None                  # Lý do khi status != 'ok'. KHÔNG được coi kết quả rỗng là thành công


# ==========================================
# 5. HỢP ĐỒNG TOÀN TRÌNH TÍCH HỢP (END-TO-END PIPELINE)
# ==========================================
class SliceRouting(BaseModel):
    """Quyết định xử lý tiếp theo của MỘT lát cắt (thêm ở thay đổi hợp đồng #1)."""
    slice_id: str
    decision: str                                # 'auto_file' (tự xếp hồ sơ) | 'needs_human' (chuyển nhân viên)
    category: str = UNKNOWN_CATEGORY             # loại sẽ xếp hồ sơ nếu auto_file; UNKNOWN nếu needs_human
    reasons: List[str] = Field(default_factory=list)   # vd 'classification:cascade_rejected', 'ocr_error', 'empty_text'; rỗng nếu auto_file
    suggested_category: Optional[str] = None     # gợi ý hiển thị cho nhân viên khi needs_human
    extraction_status: Optional[str] = None      # 'ok' | 'error' | 'skipped' | None nếu không chạy trích xuất ('skipped' + extraction_note 'no_schema...' = loại chưa có schema)
    # --- thêm ở thay đổi hợp đồng #3 (2026-10-12), tương thích ngược: có mặc định ---
    extraction_note: Optional[str] = None        # vd 'no_schema: ...' (loại chưa hỗ trợ trích xuất: KHÔNG phải lỗi), hoặc lý do bỏ qua
    expiry: Dict[str, str] = Field(default_factory=dict)             # {trường hạn: 'accepted' | 'needs_review' | 'not_found'} (quy tắc đóng băng any-model=filename)
    expiry_suggestion: Dict[str, str] = Field(default_factory=dict)  # {trường hạn: ngày ISO GỢI Ý cho người duyệt khi needs_review (không phải giá trị đã nhận)}
    field_review: bool = False                   # True nếu có trường hạn cần người duyệt (needs_review): lát cắt vẫn auto_file nhưng ngày hạn phải qua người
    # --- thêm ở giai đoạn 3 (chạy bóng), tương thích ngược ---
    shadow: Dict[str, Any] = Field(default_factory=dict)   # quyết định mà tùy chọn đang TẮT sẽ đưa ra, chỉ để đo: {"title_tiebreak_label": nhãn, "title_tiebreak_differs": bool, "expiry_would_accept": {trường: bool}}


class FileRoutingSummary(BaseModel):
    """Tóm tắt định tuyến CẤP TỆP (thêm ở thay đổi hợp đồng #2, tương thích ngược: có mặc định). Một tệp chỉ `auto_file` khi MỌI lát cắt tự xếp hồ sơ được."""
    decision: str = "needs_human"                # 'auto_file' | 'needs_human'
    n_slices: int = 0
    n_auto: int = 0
    n_needs_human: int = 0
    reasons: List[str] = Field(default_factory=list)          # lý do (không trùng) của các lát cắt cần người + lý do cấp tệp (vd 'possible_composite')
    splitter: str = ""                           # chính sách tách đã chạy (vd 'model+merge')
    n_slices_before_merge: int = 0               # số lát cắt trước khi gộp lát cắt liền kề cùng loại
    n_field_review: int = 0                      # số lát cắt có trường hạn cần người duyệt (field_review)
    n_llm_calls: int = 0                         # số lời gọi tầng LLM của tệp (kể cả lấy từ cache)
    llm_ms: float = 0.0                          # tổng thời gian chờ LLM (ms)
    shadow: Dict[str, Any] = Field(default_factory=dict)   # chạy bóng cấp tệp: {"id_rule_extra_boundaries": [số trang], "truncated_pages": [số trang không xử lý]}


class DocumentProcessingPipelineResult(BaseModel):
    """Đối tượng lưu trữ toàn diện kết quả xử lý của toàn bộ tệp PDF."""
    file_name: str
    total_pages: int
    is_composite_bundle: bool                    # True nếu bộ tách trả > 1 lát cắt (tệp ghép nhiều tài liệu)
    ocr_result: OCRDocumentResult
    split_result: SplitResult
    classifications: List[ClassificationResult] = Field(default_factory=list)
    extractions: List[ExtractionResult] = Field(default_factory=list)
    total_processing_time_ms: float = 0.0
    # --- thêm ở thay đổi hợp đồng #1 (2026-10-12), tương thích ngược: có mặc định ---
    routing: List[SliceRouting] = Field(default_factory=list)            # một dòng cho mỗi lát cắt, cùng thứ tự split_result.slices
    stage_timings_ms: Dict[str, float] = Field(default_factory=dict)     # 'ocr' | 'split' | 'classify' | 'extract' (+ 'ocr_model_load' ở lần chạy đầu); ms, đo lúc chạy, phụ thuộc tải máy; 'extract' gồm cả lần nạp lười mô hình ở lần gọi đầu
    warnings: List[str] = Field(default_factory=list)                    # lỗi không gây dừng (vd trích xuất lỗi, bước bị tắt bằng --no-llm)
    # --- thêm ở thay đổi hợp đồng #2 (2026-10-12), tương thích ngược: có mặc định ---
    file_routing: Optional[FileRoutingSummary] = None                    # tóm tắt định tuyến cấp tệp; None nếu kết quả do phiên bản cũ sinh ra
