"""rapid_ocr.py - [LEGACY - KHÔNG DÙNG ĐỂ TẠO SỐ LIỆU MỚI] Module OCR cục bộ sử dụng PyMuPDF và RapidOCR (ONNX Runtime).

CẢNH BÁO: đây là engine CŨ (`rapidocr_onnxruntime` 1.2.3), từ điển nhận dạng chỉ có 9/67 chữ cái thường có dấu tiếng Việt nên MẤT DẤU
(teams/team1_ocr/experiments/01_engine_bakeoff/RESULTS.md mục 3). Engine đã chọn nằm ở `src/ocr/vietocr_engine.py` +
`src/ocr/pdf_ocr.py` (hàm `ocr_pdf`). Module này giữ lại chỉ để các test/script cũ còn import được và để làm đối chứng;
gọi `extract_document` sẽ phát `DeprecationWarning`.

Kế thừa và nâng cấp từ Z:\\projects\\vocvach\\barb-1-ie-vi\\pdf_ocr.py:
- Ưu tiên đọc lớp chữ số (Digital Text Layer) với chi phí 0đ, độ trễ 0ms.
- Fallback sang RapidOCR cho các trang scan ảnh.
- Xuất ra đối tượng chuẩn hóa OCRDocumentResult / OCRPageResult theo contracts.py.

Lỗi (thiếu RapidOCR, OCR hỏng) được ghi vào trường `error` của trang; `full_text` luôn để rỗng
(hoặc chỉ chứa văn bản thật) để không bao giờ có chuyện thông báo lỗi bị đem đi phân loại như văn bản tài liệu.
"""

import logging
import os
import time
import warnings
from typing import Optional, List
import fitz  # PyMuPDF
import numpy as np

from src.common.contracts import BoundingBox, OCRPageResult, OCRDocumentResult
from src.ocr.page_heuristics import detect_keyword_flags

logger = logging.getLogger(__name__)

_ocr_init_error: Optional[str] = None
try:
    from rapidocr_onnxruntime import RapidOCR
    _ocr_engine = RapidOCR()
except Exception as e:
    _ocr_engine = None
    _ocr_init_error = f"{type(e).__name__}: {e}"
    logger.warning("Không khởi tạo được RapidOCR: %s", _ocr_init_error)


def process_single_page(page: fitz.Page, page_num: int, dpi: int = 150) -> OCRPageResult:
    """Xử lý OCR cho 1 trang PDF."""
    rect = page.rect
    width = int(rect.width)
    height = int(rect.height)
    digital_text = page.get_text("text").strip()

    # 1. Trường hợp có text layer số chất lượng cao
    if len(digital_text) >= 50:
        return OCRPageResult(
            page_number=page_num,
            width=width,
            height=height,
            full_text=digital_text,
            boxes=[],
            has_header_seal=False,
            has_signature_box=False,
            ocr_engine="digital",
            source="text_layer",
        )

    # 2. Trường hợp là ảnh scan -> Render & RapidOCR
    if _ocr_engine is None:
        # Giữ lại phần text layer ngắn (nếu có) vì đó là văn bản thật; lý do lỗi nằm ở trường error
        return OCRPageResult(
            page_number=page_num,
            width=width,
            height=height,
            full_text=digital_text,
            ocr_engine="rapid_ocr",
            source="text_layer" if digital_text else "ocr",
            error=f"RapidOCR không khả dụng: {_ocr_init_error or 'chưa cài đặt'}",
        )

    try:
        pix = page.get_pixmap(dpi=dpi)
        img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
        res, _ = _ocr_engine(img_np)
    except Exception as e:
        logger.exception("RapidOCR lỗi ở trang %s", page_num)
        return OCRPageResult(
            page_number=page_num,
            width=width,
            height=height,
            full_text="",
            ocr_engine="rapid_ocr",
            source="ocr",
            error=f"RapidOCR lỗi khi xử lý: {type(e).__name__}: {e}",
        )

    boxes: List[BoundingBox] = []
    lines: List[str] = []

    if res:
        for item in res:
            if item and len(item) >= 3:
                poly = item[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                text = str(item[1]).strip()
                score = float(item[2])
                xs = [p[0] for p in poly]
                ys = [p[1] for p in poly]
                x_min, x_max = min(xs), max(xs)
                y_min, y_max = min(ys), max(ys)

                boxes.append(
                    BoundingBox(
                        text=text,
                        x=float(x_min),
                        y=float(y_min),
                        w=float(x_max - x_min),
                        h=float(y_max - y_min),
                        confidence=score,
                        polygon=poly,
                    )
                )
                lines.append(text)

    combined_text = "\n".join(lines).strip()

    # Cờ heuristic khớp từ khóa (không phải phát hiện con dấu/chữ ký thật trên ảnh)
    has_seal, has_sig = detect_keyword_flags(combined_text)

    return OCRPageResult(
        page_number=page_num,
        width=width,
        height=height,
        full_text=combined_text,
        boxes=boxes,
        has_header_seal=has_seal,
        has_signature_box=has_sig,
        ocr_engine="rapid_ocr",
        source="ocr",
    )


def extract_document(pdf_path: str, max_pages: int = 10, dpi: int = 150) -> OCRDocumentResult:
    """OCR toàn bộ tài liệu PDF và trả về OCRDocumentResult (lỗi từng trang được tóm tắt ở trường `error`)."""
    warnings.warn("src.ocr.rapid_ocr là engine cũ (mất dấu tiếng Việt); dùng src.ocr.pdf_ocr.ocr_pdf", DeprecationWarning, stacklevel=2)
    start_time = time.time()
    file_name = os.path.basename(pdf_path)

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Không tìm thấy tệp: {pdf_path}")

    doc = fitz.open(pdf_path)
    total_pages = min(len(doc), max_pages)
    page_results: List[OCRPageResult] = []

    for idx in range(total_pages):
        page_res = process_single_page(doc[idx], idx + 1, dpi=dpi)
        page_results.append(page_res)

    doc.close()
    elapsed_ms = (time.time() - start_time) * 1000
    page_errors = [f"Trang {p.page_number}: {p.error}" for p in page_results if p.error]

    return OCRDocumentResult(
        file_name=file_name,
        total_pages=total_pages,
        pages=page_results,
        processing_time_ms=elapsed_ms,
        error="; ".join(page_errors) or None,
    )
