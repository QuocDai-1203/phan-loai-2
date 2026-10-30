"""Kiểm thử: module OCR phơi lỗi qua trường `error`, không nhét thông báo lỗi vào full_text."""

import fitz
import pytest
import requests

from src.ocr import ios_ocr_client, rapid_ocr
from src.ocr.ios_ocr_client import AppleVisionOCRClient
from src.ocr.page_heuristics import detect_keyword_flags


def make_pdf(path, text=None):
    """Tạo PDF 1 trang: có text layer nếu truyền `text`, ngược lại là trang trắng (giả lập bản scan)."""
    doc = fitz.open()
    page = doc.new_page()
    if text:
        page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()
    return path


def test_missing_rapidocr_sets_error_and_keeps_text_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(rapid_ocr, "_ocr_engine", None)
    monkeypatch.setattr(rapid_ocr, "_ocr_init_error", "ImportError: giả lập thiếu engine")
    result = rapid_ocr.extract_document(str(make_pdf(tmp_path / "scan.pdf")))
    page = result.pages[0]
    assert page.full_text == ""
    assert "RapidOCR không khả dụng" in page.error and "giả lập" in page.error
    assert page.source == "ocr" and page.ocr_engine == "rapid_ocr"
    assert result.error.startswith("Trang 1:")
    assert "[LỖI" not in page.full_text


def test_text_layer_page_records_source_and_has_no_error(tmp_path, monkeypatch):
    monkeypatch.setattr(rapid_ocr, "_ocr_engine", None)  # không cần OCR cho trang có text layer
    text = "HOP DONG KINH TE so 01 giua Ben A va Ben B ve viec mua ban"
    result = rapid_ocr.extract_document(str(make_pdf(tmp_path / "digital.pdf", text)))
    page = result.pages[0]
    assert page.source == "text_layer" and page.ocr_engine == "digital"
    assert page.error is None and result.error is None
    assert "HOP DONG" in page.full_text


def test_ocr_runtime_failure_is_reported_as_error(tmp_path, monkeypatch):
    def broken(_img):
        raise RuntimeError("onnx hỏng")

    monkeypatch.setattr(rapid_ocr, "_ocr_engine", broken)
    page = rapid_ocr.extract_document(str(make_pdf(tmp_path / "scan.pdf"))).pages[0]
    assert page.full_text == "" and "onnx hỏng" in page.error


def test_successful_ocr_records_source_and_keyword_flags(tmp_path, monkeypatch):
    poly = [[0, 0], [10, 0], [10, 5], [0, 5]]
    fake = lambda _img: ([[poly, "CONG HOA XA HOI CHU NGHIA VIET NAM", 0.9]], None)  # noqa: E731
    monkeypatch.setattr(rapid_ocr, "_ocr_engine", fake)
    page = rapid_ocr.extract_document(str(make_pdf(tmp_path / "scan.pdf"))).pages[0]
    assert page.source == "ocr" and page.ocr_engine == "rapid_ocr" and page.error is None
    assert page.has_header_seal is True and page.has_signature_box is False
    assert page.boxes[0].confidence == pytest.approx(0.9)


def test_keyword_flags_ignore_diacritics_and_spacing():
    assert detect_keyword_flags("Cộng hòa xã hội") == (True, False)
    assert detect_keyword_flags("KY, GHI RO HO TEN") == (False, True)
    assert detect_keyword_flags("noi dung khac") == (False, False)


# ---------- iOS-OCR-Server client ----------
def test_ios_client_connection_error_goes_to_error_field(monkeypatch):
    def boom(*a, **k):
        raise requests.ConnectionError("connection refused")

    monkeypatch.setattr(ios_ocr_client.requests, "post", boom)
    page = AppleVisionOCRClient().process_image(b"png", page_number=3)
    assert page.full_text == "" and page.page_number == 3
    assert "ConnectionError" in page.error and page.source == "ocr"


def test_ios_client_server_failure_goes_to_error_field(monkeypatch):
    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"success": False, "error": "model chưa sẵn sàng"}

    monkeypatch.setattr(ios_ocr_client.requests, "post", lambda *a, **k: Resp())
    page = AppleVisionOCRClient().process_image(b"png")
    assert page.full_text == "" and "model chưa sẵn sàng" in page.error


def test_ios_client_success_has_no_error(monkeypatch):
    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"success": True, "image_width": 100, "image_height": 200,
                    "ocr_result": "PHIEU XUAT KHO", "ocr_boxes": []}

    monkeypatch.setattr(ios_ocr_client.requests, "post", lambda *a, **k: Resp())
    page = AppleVisionOCRClient().process_image(b"png")
    assert page.error is None and page.full_text == "PHIEU XUAT KHO" and page.ocr_engine == "apple_vision"
