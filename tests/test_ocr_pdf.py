"""Kiểm thử src/ocr/pdf_ocr.py và vietocr_engine.py bằng engine giả (không GPU, không tải mô hình, không mạng)."""

import fitz
import pytest

from src.common.contracts import OCRDocumentResult, OCRPageResult
from src.ocr.pdf_ocr import assess_text_layer, clean_text, ocr_page, ocr_pdf, ocr_pdf_pages
from src.ocr.vietocr_engine import OcrModelsMissingError, VietOCREngine, resolve_model_paths

LONG = "PHIEU XUAT KHO so 123 hang hoa xang dau cua cong ty kinh doanh"   # ASCII: font Helvetica mặc định của PDF không có glyph tiếng Việt


class FakeEngine:
    name = "fake-engine@cpu"

    def __init__(self, text="văn bản OCR giả", conf=0.77, flags=None, fail_on=()):
        self.text, self.conf, self.flags, self.fail_on, self.calls = text, conf, flags or ["bg_normalized"], set(fail_on), 0

    def ocr(self, img):
        self.calls += 1
        if self.calls in self.fail_on:
            raise RuntimeError("OCR hỏng giả lập")
        assert img.ndim == 3 and img.shape[2] == 3          # ảnh BGR đã render
        return self.text, self.conf, list(self.flags)


def make_pdf(path, pages):
    """pages: list[(text|None, render_mode)]; None = trang trắng (không lớp chữ)."""
    doc = fitz.open()
    for text, mode in pages:
        pg = doc.new_page(width=300, height=400)
        if text:
            pg.insert_text((20, 50), text, fontsize=10, render_mode=mode)
    doc.save(str(path))
    doc.close()
    return path


def test_trusted_text_layer_is_used_without_calling_the_ocr_engine(tmp_path):
    pdf = make_pdf(tmp_path / "a.pdf", [(LONG, 0)])
    eng = FakeEngine()
    res = ocr_pdf(pdf, eng)
    p = res.pages[0]
    assert eng.calls == 0 and p.source == "text_layer" and p.full_text.startswith("PHIEU XUAT KHO")
    assert p.ocr_engine.startswith("pymupdf-") and p.error is None and p.mean_conf is None
    assert res.total_pages == 1 and res.error is None and (p.width, p.height) == (833, 1111)   # 300x400 pt ở 200 dpi


def test_scan_page_goes_through_engine_and_keeps_engine_name_conf_and_flags(tmp_path):
    pdf = make_pdf(tmp_path / "s.pdf", [(None, 0)])
    res = ocr_pdf(pdf, FakeEngine())
    p = res.pages[0]
    assert p.source == "ocr" and p.ocr_engine == "fake-engine@cpu" and p.full_text == "văn bản OCR giả"
    assert p.mean_conf == pytest.approx(0.77) and p.flags == ["bg_normalized"]


def test_invisible_embedded_layer_is_rejected_and_page_is_ocred_again(tmp_path):
    pdf = make_pdf(tmp_path / "e.pdf", [(LONG, 3)])        # render mode 3 = chữ vô hình của máy scan
    out = ocr_pdf_pages(pdf, FakeEngine())[1][0]
    assert out.source == "embedded_ocr_layer+ocr" and out.embedded_layer_rejected == "invisible_text(render_mode_3)"
    assert out.text == "văn bản OCR giả"                   # KHÔNG dùng lớp chữ nhúng
    contract = out.to_contract()
    assert contract.source == "embedded_ocr_layer+ocr" and "embedded_layer_rejected:invisible_text(render_mode_3)" in contract.flags


def test_engine_failure_is_recorded_on_the_page_never_swallowed_or_put_in_text(tmp_path):
    pdf = make_pdf(tmp_path / "f.pdf", [(None, 0), (None, 0), (None, 0)])
    res = ocr_pdf(pdf, FakeEngine(fail_on={2}))
    assert [p.error is None for p in res.pages] == [True, False, True]
    bad = res.pages[1]
    assert bad.full_text == "" and "RuntimeError" in bad.error and "hỏng" not in bad.full_text
    assert res.error.startswith("Trang 2: RuntimeError")
    assert res.pages[0].full_text and res.pages[2].full_text           # trang khác không bị ảnh hưởng


def test_unopenable_file_gives_document_level_error(tmp_path):
    bad = tmp_path / "hong.pdf"
    bad.write_bytes(b"day khong phai pdf")
    res = ocr_pdf(bad, FakeEngine())
    assert res.pages == [] and res.total_pages == 0 and "open_failed" in res.error


def test_max_pages_truncates_pages_but_keeps_true_total(tmp_path):
    pdf = make_pdf(tmp_path / "m.pdf", [(LONG, 0)] * 4)
    res = ocr_pdf(pdf, FakeEngine(), max_pages=2)
    assert res.total_pages == 4 and len(res.pages) == 2 and [p.page_number for p in res.pages] == [1, 2]


def test_empty_page_is_flagged_not_failed(tmp_path):
    pdf = make_pdf(tmp_path / "t.pdf", [(None, 0)])
    out = ocr_page(fitz.open(str(pdf))[0], 0, FakeEngine(text=""))
    assert out.error is None and out.text == "" and "empty_text" in out.flags


def test_record_has_same_keys_and_order_as_ocr_v2_jsonl_page():
    from src.ocr.pdf_ocr import PageOutcome
    rec = PageOutcome(page=1, source="ocr", engine="e", dpi=200, text="x", n_chars=1, mean_conf=0.5, seconds=1.0).to_record()
    assert list(rec) == ["page", "source", "engine", "dpi", "text", "n_chars", "mean_conf", "seconds", "error"]
    rec2 = PageOutcome(page=1, flags=["rotated_90"], embedded_layer_rejected="x").to_record()
    assert list(rec2)[-2:] == ["flags", "embedded_layer_rejected"]


def test_contract_json_round_trip_keeps_new_ocr_fields(tmp_path):
    pdf = make_pdf(tmp_path / "r.pdf", [(None, 0)])
    res = ocr_pdf(pdf, FakeEngine())
    back = OCRDocumentResult.model_validate_json(res.model_dump_json())
    assert back == res and isinstance(back.pages[0], OCRPageResult) and back.pages[0].mean_conf == pytest.approx(0.77)


def test_assess_text_layer_rejects_too_few_letters(tmp_path):
    pdf = make_pdf(tmp_path / "x.pdf", [("abc", 0)])
    info = assess_text_layer(fitz.open(str(pdf))[0])
    assert info["trusted"] is False and info["reason"].startswith("too_few_letters")


def test_clean_text_keeps_line_breaks_and_collapses_blank_runs():
    assert clean_text("a  b \r\n\r\n\r\n c d  \n") == "a b\n\nc d"


# ---------- mô hình OCR offline ----------
def test_missing_models_raise_one_error_listing_every_missing_file_with_instructions(tmp_path):
    with pytest.raises(OcrModelsMissingError) as ei:
        resolve_model_paths("vgg_seq2seq", tmp_path)
    msg = str(ei.value)
    assert "vgg_seq2seq.pth" in msg and "ch_PP-OCRv5_det_mobile.onnx" in msg
    assert "setup_ocr_models.py" in msg and "models/README.md" in msg and "SDH_OCR_MODELS_DIR" in msg


def test_engine_construction_fails_fast_without_downloading_anything(tmp_path):
    with pytest.raises(OcrModelsMissingError):
        VietOCREngine("vgg_seq2seq", "cpu", models_override=tmp_path)     # conftest chặn HTTP: nếu có tải ngầm test sẽ lỗi khác


def test_bundled_inference_config_is_found_without_models_dir_copy(tmp_path):
    (tmp_path / "vietocr").mkdir()
    (tmp_path / "vietocr" / "vgg_seq2seq.pth").write_bytes(b"x")
    (tmp_path / "rapidocr").mkdir()
    (tmp_path / "rapidocr" / "ch_PP-OCRv5_det_mobile.onnx").write_bytes(b"x")
    p = resolve_model_paths("vgg_seq2seq", tmp_path)
    assert p.vietocr_config.name == "vgg_seq2seq.yml" and p.vietocr_config.parent.name == "configs"
    import yaml
    cfg = yaml.safe_load(p.vietocr_config.read_text(encoding="utf-8"))
    assert len(cfg["vocab"]) == 229 and cfg["seq_modeling"] == "seq2seq"      # 229 = 233 dòng embedding - 4 token đặc biệt
