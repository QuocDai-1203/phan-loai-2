"""Kiểm thử bộ trích xuất thực thể: lỗi nạp/dự đoán mô hình phải hiện ra, không được trả rỗng giả thành công."""

from src.common.contracts import DocumentSlice
from src.extraction import barb_extractor
from src.extraction.barb_extractor import BarbEntityExtractor


def make_slice(text="Công ty ABC ký hợp đồng ngày 01/01/2026"):
    return DocumentSlice(slice_id="s1", start_page=1, end_page=1, page_count=1, combined_text=text)


class FakeModel:
    def predict_entities(self, text, labels, threshold):
        return [{"label": "tổ chức", "text": "Công ty ABC", "start": 0, "end": 11, "score": 0.9}]


class BrokenModel:
    def predict_entities(self, text, labels, threshold):
        raise RuntimeError("CUDA hết bộ nhớ")


def test_model_load_failure_is_an_explicit_error_not_empty_success(monkeypatch, caplog):
    def fail(model_name):
        raise OSError("không có mạng để tải mô hình")

    monkeypatch.setattr(barb_extractor, "_load_gliner", fail)
    monkeypatch.setattr(barb_extractor, "_MODEL_CACHE", {})
    with caplog.at_level("ERROR"):
        res = BarbEntityExtractor().extract(make_slice(), "X")
    assert res.status == "error" and "Không nạp được mô hình" in res.error and "OSError" in res.error
    assert res.entities == []
    assert any("Không nạp được mô hình" in r.getMessage() for r in caplog.records)


def test_prediction_failure_is_an_explicit_error():
    res = BarbEntityExtractor(model=BrokenModel()).extract(make_slice(), "X")
    assert res.status == "error" and "CUDA hết bộ nhớ" in res.error


def test_empty_text_is_skipped_not_ok():
    res = BarbEntityExtractor(model=FakeModel()).extract(make_slice("   "), "X")
    assert res.status == "skipped" and res.error


def test_successful_extraction_has_ok_status():
    res = BarbEntityExtractor(model=FakeModel()).extract(make_slice(), "X")
    assert res.status == "ok" and res.error is None
    assert res.entity_dict == {"tổ chức": ["Công ty ABC"]}


def test_import_does_not_load_model():
    # Nạp lười: import module không được tải mô hình / gọi mạng
    assert BarbEntityExtractor().model is None
