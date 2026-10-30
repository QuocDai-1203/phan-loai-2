"""ios_ocr_client.py - Client kết nối máy chủ Apple Vision OCR (iOS-OCR-Server / Mac).

Hỗ trợ gọi API HTTP /upload của thiết bị Apple (iPhone / iPad / Mac M-series):
- Nhận diện chữ in và chữ viết tay (handwriting) tiếng Việt cực tốt.
- Trả về OCRPageResult tuân thủ contracts.py.

Lỗi kết nối / lỗi server được ghi vào trường `error`; `full_text` để rỗng (không nhét thông báo lỗi vào văn bản).
"""

import logging
import requests
from typing import Optional
from src.common.contracts import BoundingBox, OCRPageResult
from src.ocr.page_heuristics import detect_keyword_flags

logger = logging.getLogger(__name__)


class AppleVisionOCRClient:
    """Client giao tiếp với iOS-OCR-Server (https://github.com/riddleling/iOS-OCR-Server)."""

    def __init__(self, server_url: str = "http://127.0.0.1:8000/upload", timeout: int = 30):
        self.server_url = server_url
        self.timeout = timeout

    def _error_page(self, page_number: int, message: str) -> OCRPageResult:
        """Trang lỗi: văn bản rỗng, lý do nằm ở `error`."""
        logger.warning(message)
        return OCRPageResult(
            page_number=page_number,
            width=0,
            height=0,
            full_text="",
            ocr_engine="apple_vision",
            source="ocr",
            error=message,
        )

    def process_image(self, image_bytes: bytes, page_number: int = 1) -> OCRPageResult:
        """Gửi ảnh dạng byte sang Apple Vision OCR Server."""
        files = {"file": ("page.png", image_bytes, "image/png")}
        headers = {"Accept": "application/json"}

        try:
            response = requests.post(self.server_url, files=files, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as e:
            return self._error_page(
                page_number, f"Lỗi kết nối iOS-OCR-Server ({self.server_url}): {type(e).__name__}: {e}"
            )

        if not data.get("success", False):
            reason = data.get("error") or data.get("message") or "không rõ lý do"
            return self._error_page(page_number, f"iOS-OCR-Server trả về success=false: {reason}")

        width = int(data.get("image_width", 0))
        height = int(data.get("image_height", 0))
        full_text = str(data.get("ocr_result", "")).strip()

        boxes = []
        for b in data.get("ocr_boxes", []):
            try:
                rect = b.get("rect", {})
                poly = None
                if rect:
                    poly = [
                        [rect.get("topLeft_x", 0), rect.get("topLeft_y", 0)],
                        [rect.get("topRight_x", 0), rect.get("topRight_y", 0)],
                        [rect.get("bottomRight_x", 0), rect.get("bottomRight_y", 0)],
                        [rect.get("bottomLeft_x", 0), rect.get("bottomLeft_y", 0)],
                    ]

                boxes.append(
                    BoundingBox(
                        text=str(b.get("text", "")),
                        x=float(b.get("x", 0)),
                        y=float(b.get("y", 0)),
                        w=float(b.get("w", 0)),
                        h=float(b.get("h", 0)),
                        confidence=1.0,
                        polygon=poly,
                    )
                )
            except (AttributeError, TypeError, ValueError) as e:
                # Box lỗi định dạng: bỏ qua riêng box đó (văn bản trang vẫn nằm ở full_text)
                logger.debug("Bỏ qua ocr_box sai định dạng: %s", e)
                continue

        # Cờ heuristic khớp từ khóa (không phải phát hiện con dấu/chữ ký thật trên ảnh)
        has_seal, has_sig = detect_keyword_flags(full_text)

        return OCRPageResult(
            page_number=page_number,
            width=width,
            height=height,
            full_text=full_text,
            boxes=boxes,
            has_header_seal=has_seal,
            has_signature_box=has_sig,
            ocr_engine="apple_vision",
            source="ocr",
        )
