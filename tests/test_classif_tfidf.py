"""Kiểm thử TfidfClassifier: huấn luyện / dự đoán / lưu / nạp và các lỗi phải nói ra (không HTTP, không GPU)."""

import json

import numpy as np
import pytest

from src.classification.tfidf_classifier import CONFIG_NAME, POOL, TfidfClassifier, TfidfModelError, raw_norm

CLASSES = ["PHIEU_XUAT_KHO", "DON_DAT_HANG", POOL]
TEXTS = (["phiếu xuất kho số hàng hóa xăng dầu kho"] * 3 + ["đơn đặt hàng mua xăng dầu bên bán"] * 3 + ["văn bản khác lạ hoàn toàn"] * 3)
LABELS = ["PHIEU_XUAT_KHO"] * 3 + ["DON_DAT_HANG"] * 3 + [POOL] * 3


def trained() -> TfidfClassifier:
    return TfidfClassifier(CLASSES).fit(TEXTS, LABELS)


def test_config_name_is_the_one_chosen_in_experiment_01():
    assert CONFIG_NAME == "tfidf_word_cnb_raw_C0.1"
    assert trained().name == CONFIG_NAME


def test_raw_norm_keeps_diacritics_but_folds_case_and_spaces():
    assert raw_norm("  PHIẾU\n XUẤT\tKHO ") == "phiếu xuất kho"


def test_predict_returns_label_confidence_and_proba_aligned_with_classes():
    clf = trained()
    pr = clf.predict(["PHIẾU XUẤT KHO số 12 hàng hóa", "đơn đặt hàng mua xăng dầu"])
    assert pr.labels == ["PHIEU_XUAT_KHO", "DON_DAT_HANG"]
    assert pr.classes == CLASSES and pr.proba.shape == (2, 3)
    assert np.allclose(pr.confidence, pr.proba.max(axis=1))
    assert np.allclose(pr.proba.sum(axis=1), 1.0)


def test_unknown_training_label_is_rejected():
    with pytest.raises(ValueError, match="ngoài danh sách lớp"):
        TfidfClassifier(CLASSES).fit(TEXTS, LABELS[:-1] + ["LOP_LA"])


def test_predict_before_fit_is_an_error_not_a_default_label():
    with pytest.raises(TfidfModelError):
        TfidfClassifier(CLASSES).predict(["x"])


def test_save_load_round_trip_keeps_predictions_and_metadata(tmp_path):
    clf = trained()
    meta = clf.save(tmp_path / "m", labels_file="data/labels_v2.csv", labels_sha1_10="abc1234567", text_source="ocr_v2_p12",
                    train_doc_ids=[f"d{i}" for i in range(9)], train_labels=LABELS)
    assert meta.train_split == "DEV" and meta.n_train == 9 and meta.labels_sha1_10 == "abc1234567"
    assert meta.class_counts == {"DON_DAT_HANG": 3, "PHIEU_XUAT_KHO": 3, POOL: 3}
    assert meta.sklearn_version and meta.created_at and meta.model_sha256
    back = TfidfClassifier.load(tmp_path / "m")
    q = ["phiếu xuất kho hàng hóa", "đơn đặt hàng mua"]
    assert back.predict(q).labels == clf.predict(q).labels
    assert np.allclose(back.predict(q).proba, clf.predict(q).proba)
    assert back.meta.train_doc_ids == sorted(f"d{i}" for i in range(9))


def test_load_missing_directory_explains_how_to_train(tmp_path):
    with pytest.raises(TfidfModelError, match="train_tfidf_classifier.py"):
        TfidfClassifier.load(tmp_path / "khong_co")


def test_load_detects_corrupted_model_file(tmp_path):
    trained().save(tmp_path / "m", labels_file="x", labels_sha1_10="y", text_source="s", train_doc_ids=["a"], train_labels=["a"])
    with open(tmp_path / "m" / "model.joblib", "ab") as f:
        f.write(b"corrupt")
    with pytest.raises(TfidfModelError, match="checksum"):
        TfidfClassifier.load(tmp_path / "m")


def test_sklearn_version_mismatch_warns_or_fails_when_strict(tmp_path, caplog):
    trained().save(tmp_path / "m", labels_file="x", labels_sha1_10="y", text_source="s", train_doc_ids=["a"], train_labels=["a"])
    jp = tmp_path / "m" / "meta.json"
    meta = json.loads(jp.read_text(encoding="utf-8"))
    meta["sklearn_version"] = "0.0.1"
    jp.write_text(json.dumps(meta), encoding="utf-8")
    with caplog.at_level("WARNING"):
        TfidfClassifier.load(tmp_path / "m")
    assert any("scikit-learn" in r.getMessage() for r in caplog.records)
    with pytest.raises(TfidfModelError, match="scikit-learn"):
        TfidfClassifier.load(tmp_path / "m", strict_versions=True)
