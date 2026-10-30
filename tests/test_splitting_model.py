"""Kiểm thử phương pháp tách trang CÓ HỌC (method="model"): nối đúng hợp đồng SplitResult, lưu/nạp có kiểm sha, không âm thầm quay về luật."""

import json

import pytest

from src.common.contracts import OCRDocumentResult, OCRPageResult
from src.splitting import learned
from src.splitting.boundary_detector import split_document
from src.splitting.learned import fit_pair_model, load_model, save_model


def _a(i):
    return (f"PHIEU XUAT KHO THANH PHAM\nSo: 26{i:05d}\nKy hieu: BSR/PXK/DO\nKho xuat: nha may loc dau so {i}\n"
            f"Nguoi nhan hang: xe {i} tai xe nguyen van {i}\nSan pham: dau diezen muc 2 so luong {1000 + i} lit\n" + "noi dung phieu xuat kho " * 6)


def _b(i):
    return (f"CONG HOA XA HOI CHU NGHIA VIET NAM\nBIEN BAN LAY MAU NIEM PHONG BAN GIAO MAU\nMau 1 BBLM-NP-CKCL so {i}\n"
            f"Thuong nhan xuat hang: cong ty so {i}\nPhuong tien: xe {i} niem phong {i * 7}\n" + "noi dung bien ban lay mau " * 6)


@pytest.fixture(scope="module")
def tiny_model():
    texts, types, groups, keys = {}, {}, {}, []
    for i in range(24):
        for t, fn in (("PXK", _a), ("BBLM", _b)):
            k = f"{t}{i}:1"
            texts[k], types[k], groups[k] = fn(i), t, f"g{i % 6}"
            keys.append((t, k))
    pairs = []
    for i in range(24):                       # đường nối PXK -> BBLM (nhãn 1) và BBLM -> PXK khác (nhãn 1)
        pairs.append((f"PXK{i}:1", f"BBLM{i}:1", 1))
        pairs.append((f"BBLM{i}:1", f"PXK{(i + 5) % 24}:1", 1))
    # cặp cùng tài liệu (nhãn 0): hai trang PXK của cùng một phiếu giả lập bằng cách ghép PXK i với "trang 2" cùng i
    for i in range(24):
        k2 = f"PXK{i}:2"
        texts[k2], types[k2], groups[k2] = "Nguoi lap phieu\nDai dien ben giao\nDai dien ben nhan\nky ten " + _a(i)[:60], "PXK", f"g{i % 6}"
        pairs.append((f"PXK{i}:1", k2, 0))
    return fit_pair_model(texts, types, groups, pairs, kind="lr", seed=0, inner_splits=3)


def _doc(texts, errors=None):
    errors = errors or {}
    pages = [OCRPageResult(page_number=i + 1, width=0, height=0, full_text=t, error=errors.get(i + 1)) for i, t in enumerate(texts)]
    return OCRDocumentResult(file_name="m.pdf", total_pages=len(pages), pages=pages)


def test_model_method_fills_contract_truthfully(tiny_model):
    doc = _doc([_a(100), _b(100), "", _a(101)], errors={3: "OCR hỏng"})
    r = split_document(doc, method="model", model=tiny_model)
    assert r.total_pages == 4 and [(s.start_page, s.end_page) for s in r.slices] == [(1, 1), (2, 3), (4, 4)]
    assert all(s.boundary_method == "model" for s in r.slices)
    assert r.slices[0].boundary_confidence == 1.0                      # trang 1: định nghĩa, không phải quyết định của mô hình
    assert all(0.0 <= s.boundary_confidence <= 1.0 for s in r.slices)
    assert all(s.boundary_confidence >= tiny_model.threshold for s in r.slices[1:])   # điểm thô >= ngưỡng vì đã tách ở đó
    assert r.slices[1].ocr_errors == ["OCR hỏng"] and r.slices[0].ocr_errors == []
    assert r.slices[1].combined_text.count("--- TIẾP THEO ---") == 1


def test_blank_page_is_continuation_and_first_nonblank_never_split(tiny_model):
    doc = _doc(["", _a(7), _b(7)])
    r = split_document(doc, method="model", model=tiny_model)
    assert [(s.start_page, s.end_page) for s in r.slices] == [(1, 2), (3, 3)]


def test_save_load_roundtrip_and_tamper_detection(tiny_model, tmp_path):
    p = save_model(tiny_model, tmp_path / "m.joblib", {"labels_sha1_10": "abc"})
    info = json.loads(p.with_suffix(".json").read_text(encoding="utf-8"))
    assert info["labels_sha1_10"] == "abc" and len(info["sha256"]) == 64 and info["threshold"] == 0.5
    m2 = load_model(p)
    doc = _doc([_a(100), _b(100)])
    assert split_document(doc, method="model", model=m2).slices[1].boundary_confidence == pytest.approx(
        split_document(doc, method="model", model=tiny_model).slices[1].boundary_confidence)
    p.write_bytes(p.read_bytes() + b"x")
    with pytest.raises(ValueError):
        load_model(p)


def test_missing_default_model_raises_instead_of_falling_back_to_rules(tmp_path, monkeypatch):
    monkeypatch.setattr(learned, "MODELS_DIR", tmp_path)
    with pytest.raises(FileNotFoundError):
        split_document(_doc([_a(1), _b(1)]), method="model")


def test_shipped_default_model_loads_and_splits_the_standard_fixture():
    """Kiểm tra artefact thật ở teams/team2_splitting/models/ (bỏ qua nếu chưa huấn luyện). Không phải phép đo hiệu năng."""
    if not (learned.MODELS_DIR / learned.DEFAULT_MODEL_FILE).exists():
        pytest.skip("chưa có models/pair_gb_v0.joblib (chạy experiments/04_pair_classifier/save_model.py)")
    from tests.fixtures.sample_pipeline_fixtures import MOCK_OCR_DOCUMENT_BSR as d
    info = json.loads((learned.MODELS_DIR / learned.DEFAULT_MODEL_FILE).with_suffix(".json").read_text(encoding="utf-8"))
    assert info["train_scope"].startswith("DEV") and "không TEST" in info["train_scope"] and info["n_train_docs"] > 0   # có ghi nhận phạm vi huấn luyện, không TEST
    r = split_document(d, method="model")
    assert [(s.start_page, s.end_page) for s in r.slices] == [(1, 2), (3, 3), (4, 4), (5, 5)]
    assert all(s.boundary_method == "model" and 0.0 <= s.boundary_confidence <= 1.0 for s in r.slices)
