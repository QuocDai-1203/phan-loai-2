"""Kiểm thử script đánh giá: đọc cả hai định dạng JSONL, tính metric, ghi file, cảnh báo khi Kev offline."""

import importlib.util
import json
from collections import Counter
from pathlib import Path

import pytest
import requests

from src.classification import system_one_classifier as soc

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "evaluate_classifier_baseline.py"
spec = importlib.util.spec_from_file_location("evaluate_classifier_baseline", SCRIPT)
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)

DKKD, PXK = "_1. Giay DKKD khach hang", "_PHIẾU XUẤT KHO MUA HÀNG 2026"


@pytest.fixture(autouse=True)
def kev_offline(monkeypatch):
    def boom(*a, **k):
        raise requests.ConnectionError("connection refused")

    monkeypatch.setattr(soc.requests, "post", boom)


def write_jsonl(path, rows):
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    return path


def test_load_records_supports_baseline_and_v2_formats(tmp_path):
    base = write_jsonl(tmp_path / "base.jsonl", [{"file_name": "a", "category_label": DKKD, "ocr_text": "xyz", "page_count": 2}])
    v2 = write_jsonl(tmp_path / "v2.jsonl", [{"file_name": "b", "folder_label": PXK,
                                              "pages": [{"page": 1, "text": "ab"}, {"page": 2, "text": "cd"}]}])
    assert ev.load_records(base)[0]["text"] == "xyz"
    rec = ev.load_records(v2)[0]
    assert rec["label"] == PXK and rec["text"] == "ab\n\ncd" and rec["page_count"] == 2
    custom = write_jsonl(tmp_path / "c.jsonl", [{"nhan": DKKD, "ocr_text": "t"}])
    assert ev.load_records(custom, label_field="nhan")[0]["label"] == DKKD


def test_load_records_without_label_fails_loudly(tmp_path):
    bad = write_jsonl(tmp_path / "bad.jsonl", [{"ocr_text": "t"}])
    with pytest.raises(ValueError):
        ev.load_records(bad)


def test_compute_metrics_counts_abstain_as_wrong_but_not_covered():
    y_true = [DKKD, DKKD, PXK, PXK]
    y_pred = [DKKD, "UNKNOWN", PXK, DKKD]
    m = ev.compute_metrics(y_true, y_pred, ["rule", "none", "rule", "rule"])
    assert m["accuracy"] == 0.5 and m["coverage"] == 0.75
    assert m["accuracy_on_covered"] == pytest.approx(2 / 3)
    assert m["tier_counts"] == {"rule": 3, "none": 1}
    assert m["per_class"][DKKD]["recall"] == 0.5 and m["per_class"][DKKD]["precision"] == 0.5
    assert 0.0 <= m["macro_f1"] <= 1.0


def test_run_evaluation_writes_outputs_and_flags_kev_offline(tmp_path, capsys):
    data = write_jsonl(tmp_path / "d.jsonl", [
        {"file_name": "1", "category_label": DKKD, "ocr_text": "GIAY DANG KY DOANH NGHIEP"},
        {"file_name": "2", "category_label": PXK, "ocr_text": "PHIEU XUAT KHO so 1"},
        {"file_name": "3", "category_label": PXK, "ocr_text": "khong co tieu de"},
    ])
    out = tmp_path / "out"
    summary = ev.run_evaluation(input_path=str(data), out_dir=str(out))
    assert summary["kev_online"] is False and summary["warning"]
    assert summary["tier_counts"] == {"rule": 2, "none": 1}
    assert summary["accuracy_on_covered"] == 1.0 and summary["coverage"] == pytest.approx(2 / 3)
    assert json.loads((out / "summary.json").read_text(encoding="utf-8"))["kev_online"] is False
    csv_text = (out / "confusion_matrix.csv").read_text(encoding="utf-8-sig")
    assert "UNKNOWN" in csv_text and DKKD in csv_text
    assert "KEV SERVER OFFLINE" in capsys.readouterr().out


def test_empty_folder_label_is_skipped_and_counted_not_fatal(tmp_path):
    data = write_jsonl(tmp_path / "v2.jsonl", [
        {"doc_id": "a", "file_name": "1", "folder_label": None, "pages": [{"page": 1, "text": "PHIEU XUAT KHO"}]},
        {"doc_id": "b", "file_name": "2", "folder_label": PXK, "pages": [{"page": 1, "text": "PHIEU XUAT KHO"}]},
    ])
    skipped = Counter()
    recs = ev.load_records(data, skipped=skipped)
    assert [r["file_name"] for r in recs] == ["2"] and skipped == {"nhan_rong": 1}


def test_labels_csv_replaces_folder_labels_and_drops_duplicates_and_mixed_composites(tmp_path):
    data = write_jsonl(tmp_path / "v2.jsonl", [
        {"doc_id": d, "file_name": d, "folder_label": None, "pages": [{"page": 1, "text": "PHIEU XUAT KHO so 1"}]}
        for d in ("goc", "ban_trung", "ghep")
    ])
    labels = tmp_path / "labels.csv"
    labels.write_text("doc_id,doc_type,composite_mixed,is_duplicate_of\n"
                      f"goc,{PXK},0,\nban_trung,{PXK},0,goc\nghep,{PXK},1,\n", encoding="utf-8-sig")
    summary = ev.run_evaluation(input_path=str(data), out_dir=str(tmp_path / "out"), labels_path=str(labels), verbose=False)
    assert summary["total"] == 1 and sum(summary["skipped_records"].values()) == 2
    assert summary["labels"] == str(labels)


def test_default_out_dir_never_points_at_historical_baseline(tmp_path, monkeypatch):
    monkeypatch.setattr(ev, "PROJECT_ROOT", tmp_path)
    data = write_jsonl(tmp_path / "d.jsonl", [{"file_name": "1", "category_label": DKKD, "ocr_text": "GIAY DANG KY DOANH NGHIEP"}])
    ev.run_evaluation(input_path=str(data), verbose=False)
    assert (tmp_path / "teams/team3_classification/results/rule_gate_runs/d__folder_labels/summary.json").exists()
