"""Kiểm thử nạp taxonomy (src/classification/taxonomy.py)."""

import json

import pytest

from src.classification.system_one_classifier import CATEGORIES_19, CascadedClassifier
from src.classification.taxonomy import legacy_taxonomy, load_taxonomy, load_taxonomy_file

TAXONOMY = {
    "version": "2.0",
    "classes": [
        {"id": "GCN_DKKD", "name_vi": "Giấy chứng nhận ĐKKD", "description": "Giấy đăng ký doanh nghiệp",
         "keywords": ["giấy chứng nhận đăng ký doanh nghiệp"], "legacy_folders": ["_1. Giay DKKD khach hang"]},
        {"id": "PXK", "name_vi": "Phiếu xuất kho", "description": "Phiếu xuất kho hàng",
         "keywords": ["phiếu xuất kho"], "legacy_folders": ["_PHIẾU XUẤT KHO MUA HÀNG 2026"]},
    ],
}


def _write(tmp_path, obj):
    path = tmp_path / "taxonomy_v2.json"
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return path


def test_legacy_taxonomy_has_19_classes():
    tax = legacy_taxonomy()
    assert tax.class_ids == CATEGORIES_19 and len(tax.classes) == 19


def test_load_from_file_uses_id_description_keywords(tmp_path):
    tax = load_taxonomy(_write(tmp_path, TAXONOMY))
    assert tax.version == "2.0" and tax.class_ids == ["GCN_DKKD", "PXK"]
    assert tax.classes[0].criteria_text == "Giấy đăng ký doanh nghiệp"
    assert tax.legacy_to_id == {"_1. Giay DKKD khach hang": "GCN_DKKD", "_PHIẾU XUẤT KHO MUA HÀNG 2026": "PXK"}


def test_classifier_uses_taxonomy_ids_as_labels(tmp_path):
    clf = CascadedClassifier(kev_endpoint=None, taxonomy_path=_write(tmp_path, TAXONOMY))
    assert clf.fast_header_gate("PHIEU XUAT KHO so 1") == "PXK"
    assert clf.fast_header_gate("GIAY CHUNG NHAN DANG KY DOANH NGHIEP") == "GCN_DKKD"


def test_default_path_falls_back_to_legacy_when_file_missing(monkeypatch, tmp_path):
    import src.classification.taxonomy as tx
    monkeypatch.setattr(tx, "DEFAULT_TAXONOMY_PATH", tmp_path / "khong_ton_tai.json")
    assert load_taxonomy().source == "builtin_legacy_19"


def test_default_path_loads_taxonomy_v2_when_present(monkeypatch, tmp_path):
    import src.classification.taxonomy as tx
    monkeypatch.setattr(tx, "DEFAULT_TAXONOMY_PATH", _write(tmp_path, TAXONOMY))
    assert load_taxonomy().class_ids == ["GCN_DKKD", "PXK"]


@pytest.mark.parametrize("bad", [{"classes": []}, {"classes": [{"name_vi": "thiếu id"}]},
                                 {"classes": [{"id": "A"}, {"id": "A"}]}, []])
def test_malformed_taxonomy_raises_instead_of_silent_fallback(tmp_path, bad):
    with pytest.raises(ValueError):
        load_taxonomy_file(_write(tmp_path, bad))
