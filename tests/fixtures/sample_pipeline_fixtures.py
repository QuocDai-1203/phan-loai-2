"""sample_pipeline_fixtures.py - Dữ liệu mẫu giả lập chuẩn (Mock Fixtures).

Cung cấp sẵn dữ liệu đầu vào chuẩn hóa (Ground Truth Fixtures) cho cả 4 nhóm:
- Nhóm 2 (Splitting) có thể dùng MOCK_OCR_DOCUMENT để code ngay mà không cần đợi Nhóm 1.
- Nhóm 3 (Classification) có thể dùng MOCK_SPLIT_RESULT để code ngay mà không cần đợi Nhóm 2.
- Nhóm 4 (Extraction) có thể dùng MOCK_CLASSIFICATION để code ngay mà không cần đợi Nhóm 3.
"""

from src.common.contracts import (
    BoundingBox,
    OCRPageResult,
    OCRDocumentResult,
    DocumentSlice,
    SplitResult,
    ClassificationResult,
    ExtractedEntity,
    ExtractedTable,
    ExtractionResult,
)

# -------------------------------------------------------------
# 1. FIXTURE CHO NHÓM 2: KẾT QUẢ OCR 5 TRANG CỦA FILE BSR
# -------------------------------------------------------------
MOCK_OCR_PAGE_1 = OCRPageResult(
    page_number=1,
    width=1654,
    height=2339,
    full_text="TONG CONG TY LOC HOA DAU VIET NAM\nPHIEU XUAT KHO THANH PHAM\nSo: 2629763\nKy hieu: BSR/PXK/DO\nKho: Tram xuat xebon NMLD Dung Quat\nXuat tai bon so: TK-5207B\nLenh xuat hang: 7309/LXHXB-DO-061026-55-0",
    boxes=[
        BoundingBox(text="PHIEU XUAT KHO THANH PHAM", x=500, y=200, w=650, h=40, confidence=0.98),
        BoundingBox(text="So: 2629763", x=1200, y=250, w=200, h=30, confidence=0.99),
        BoundingBox(text="TK-5207B", x=400, y=550, w=150, h=30, confidence=0.97),
    ],
    has_header_seal=True,
    has_signature_box=False,
)

MOCK_OCR_PAGE_2 = OCRPageResult(
    page_number=2,
    width=1654,
    height=2339,
    full_text="PHIEU XUAT KHO THANH PHAM\nNguoi lap phieu: Ngo Thi Hong Sa\nDai dien ben giao: Nguyen Khanh Phuong\nDai dien ben nhan: Tran Van Nam (Ky, ghi ro ho ten)",
    boxes=[
        BoundingBox(text="Nguoi lap phieu", x=200, y=1800, w=250, h=30, confidence=0.95),
        BoundingBox(text="Nguyen Khanh Phuong", x=600, y=1900, w=300, h=30, confidence=0.92, is_handwritten=True),
    ],
    has_header_seal=False,
    has_signature_box=True,  # Bảng chữ ký kết thúc tài liệu
)

MOCK_OCR_PAGE_3 = OCRPageResult(
    page_number=3,
    width=1654,
    height=2339,
    full_text="PETROVIETNAM BSR\nCHUNG THU CHAT LUONG\nCertificate of Quality\nNHIEN LIEU DIEZEN (DO 0,05S) MUC 2\nKy hieu lo: DLO-TK5207B-204-261005",
    boxes=[
        BoundingBox(text="CHUNG THU CHAT LUONG", x=450, y=300, w=700, h=45, confidence=0.99),
        BoundingBox(text="DLO-TK5207B-204-261005", x=600, y=600, w=350, h=35, confidence=0.98),
    ],
    has_header_seal=True,
    has_signature_box=True,
)

MOCK_OCR_PAGE_4 = OCRPageResult(
    page_number=4,
    width=1654,
    height=2339,
    full_text="CONG HOA XA HOI CHU NGHIA VIET NAM\nCONG TY CO PHAN HOA DAU QUAN DOI (MIPEC)\nBIEN BAN GIAO NHAN HANG\nHom nay, ngay 06 thang 10 nam 2026. Chung toi gom:\nBen Giao hang: MIPEC\nBen Nhan hang: Cong ty CP TM DV Hiep Hoa",
    boxes=[
        BoundingBox(text="BIEN BAN GIAO NHAN HANG", x=400, y=350, w=800, h=40, confidence=0.97),
        BoundingBox(text="06/10/2026", x=900, y=450, w=150, h=30, confidence=0.94, is_handwritten=True),
    ],
    has_header_seal=True,
    has_signature_box=True,
)

MOCK_OCR_PAGE_5 = OCRPageResult(
    page_number=5,
    width=1654,
    height=2339,
    full_text="Mau 1.BBLM-NP-CKCL theo TT 15/2015/TT-BKHCN\nBIEN BAN LAY MAU, NIEM PHONG, BAN GIAO MAU VA CAM KET CHAT LUONG\nTen loai xang dau: Dau Diezen 0.05S\nSo luong mau: 03 chai 1000ml",
    boxes=[
        BoundingBox(text="BIEN BAN LAY MAU, NIEM PHONG", x=300, y=400, w=900, h=35, confidence=0.96),
    ],
    has_header_seal=True,
    has_signature_box=True,
)

MOCK_OCR_DOCUMENT_BSR = OCRDocumentResult(
    file_name="BSR-2629763-HH 10-06-2026 20-10-37.pdf",
    total_pages=5,
    pages=[MOCK_OCR_PAGE_1, MOCK_OCR_PAGE_2, MOCK_OCR_PAGE_3, MOCK_OCR_PAGE_4, MOCK_OCR_PAGE_5],
    processing_time_ms=850.0,
)


# -------------------------------------------------------------
# 2. FIXTURE CHO NHÓM 3: KẾT QUẢ PHÂN ĐOẠN 4 LÁT CẮT (SPLIT RESULT)
# -------------------------------------------------------------
MOCK_SPLIT_RESULT_BSR = SplitResult(
    source_file="BSR-2629763-HH 10-06-2026 20-10-37.pdf",
    total_pages=5,
    slices=[
        DocumentSlice(
            slice_id="slice_001",
            start_page=1,
            end_page=2,
            page_count=2,
            combined_text=MOCK_OCR_PAGE_1.full_text + "\n" + MOCK_OCR_PAGE_2.full_text,
            pages=[MOCK_OCR_PAGE_1, MOCK_OCR_PAGE_2],
            boundary_confidence=0.97,
        ),
        DocumentSlice(
            slice_id="slice_002",
            start_page=3,
            end_page=3,
            page_count=1,
            combined_text=MOCK_OCR_PAGE_3.full_text,
            pages=[MOCK_OCR_PAGE_3],
            boundary_confidence=0.99,
        ),
        DocumentSlice(
            slice_id="slice_003",
            start_page=4,
            end_page=4,
            page_count=1,
            combined_text=MOCK_OCR_PAGE_4.full_text,
            pages=[MOCK_OCR_PAGE_4],
            boundary_confidence=0.98,
        ),
        DocumentSlice(
            slice_id="slice_004",
            start_page=5,
            end_page=5,
            page_count=1,
            combined_text=MOCK_OCR_PAGE_5.full_text,
            pages=[MOCK_OCR_PAGE_5],
            boundary_confidence=0.96,
        ),
    ],
    processing_time_ms=120.0,
)


# -------------------------------------------------------------
# 3. FIXTURE CHO NHÓM 4: KẾT QUẢ PHÂN LOẠI DANH MỤC
# -------------------------------------------------------------
MOCK_CLASSIFICATION_PXK = ClassificationResult(
    slice_id="slice_001",
    predicted_category="_PHIẾU XUẤT KHO MUA HÀNG 2026",
    confidence=0.96,
    probabilities={"_PHIẾU XUẤT KHO MUA HÀNG 2026": 0.96, "_Biên bản giao nhận 2026": 0.03},
    model_name="kev-4b",
    tier="kev",
    confidence_kind="model",
    requires_human_review=False,
    processing_time_ms=180.0,
)

MOCK_CLASSIFICATION_BBGN = ClassificationResult(
    slice_id="slice_003",
    predicted_category="_Biên bản giao nhận 2026",
    confidence=0.95,
    probabilities={"_Biên bản giao nhận 2026": 0.95, "_PHIẾU XUẤT KHO MUA HÀNG 2026": 0.04},
    model_name="kev-4b",
    tier="kev",
    confidence_kind="model",
    requires_human_review=False,
    processing_time_ms=175.0,
)
