"""Bộ công cụ silver v2 (giai đoạn 3): hàm dựng đơn vị/lô (không cần ảnh), merge/adjudication chạy cho v2, và tính toàn vẹn của sản phẩm nếu đã sinh."""
import csv
import json
import random
from collections import Counter
from pathlib import Path

import pytest

from gold import build_adjudication as BA
from gold import merge_silver as MS
from gold.v2 import build_units_v2 as V2
from schema.build_schema import PHASE3_TYPES

V2DIR = Path(__file__).resolve().parents[1] / "gold" / "v2"
SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schema"
HAVE = (V2DIR / "units_v2.csv").exists() and (V2DIR / "batches_v2_second.json").exists()
needs_kit = pytest.mark.skipif(not HAVE, reason="chưa chạy gold/v2/build_units_v2.py")


# --------------------------------------------------------------------------- hàm thuần
def test_target_types_v2_are_phase3_and_disjoint_from_v1():
    from gold.build_units import TARGET_TYPES
    assert V2.TARGET_TYPES_V2 == PHASE3_TYPES and not set(V2.TARGET_TYPES_V2) & set(TARGET_TYPES)


def test_collect_candidates_handles_duplicates_composites_and_other_types():
    labels = {
        "a": dict(doc_type="GPLX", is_duplicate_of="", segments=""),
        "b": dict(doc_type="GPLX", is_duplicate_of="a", segments=""),                      # trùng -> bỏ
        "c": dict(doc_type="PHIEU_XUAT_KHO", is_duplicate_of="", segments=""),             # loại v1 -> bỏ
        "d": dict(doc_type="composite_mixed", is_duplicate_of="", segments="1-2:HD_VAN_CHUYEN;3:PHIEU_XUAT_KHO;4:GCN_BAO_HIEM"),
    }
    manifest = {k: {"page_count": "3"} for k in labels}
    got = V2.collect_candidates(labels, manifest, V2.TARGET_TYPES_V2)
    assert [(c["doc_id"], c["seg_idx"], c["doc_type"], c["composite"]) for c in got] == [
        ("a", 0, "GPLX", 0), ("d", 0, "HD_VAN_CHUYEN", 1), ("d", 2, "GCN_BAO_HIEM", 1)]
    assert got[0]["pages"] == [1, 2, 3] and got[1]["pages"] == [1, 2]


def test_unit_split_rules_match_v1():
    assert V2.unit_split("DEV", 0) == "DEV" and V2.unit_split("TEST", 0) == "TEST"
    assert V2.unit_split("EXCLUDED_composite", 0) == "EXCLUDED" and V2.unit_split("DEV", 1) == "EXCLUDED"


def _fake_units(n=40):
    types = PHASE3_TYPES[:5]
    return [{"unit_id": f"u{i}_0", "doc_id": f"u{i}", "seg_idx": 0, "doc_type": types[i % 5], "split": "DEV", "pages": [1, 2],
             "n_pages": 2, "shown_pages": [1, 2], "n_images": 2 + (i % 4), "images": [f"p0{k}.png" for k in range(2 + (i % 4))],
             "template_group": "", "is_scanned": "True", "composite": 0, "relative_path": "x.pdf"} for i in range(n)]


def test_write_batches_cover_all_units_for_both_annotators_with_absolute_paths(tmp_path):
    units = _fake_units()
    res = V2.write_batches(units, tmp_path / "b", tmp_path / "second.json")
    first = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((tmp_path / "b").glob("batch_*.json"))]
    second = json.loads((tmp_path / "second.json").read_text(encoding="utf-8"))["batches"]
    assert len(first) == res["n_batches"] and len(second) == res["n_second_batches"]
    for batches in (first, second):
        ids = [u["unit_id"] for b in batches for u in b["units"]]
        assert sorted(ids) == sorted(u["unit_id"] for u in units)                    # mỗi đơn vị đúng một lần, người thứ hai cũng đọc hết
        assert all(b["n_images"] <= 24 for b in batches)
        assert all(b["n_images"] == sum(len(u["images"]) for u in b["units"]) for b in batches)
        for b in batches:
            assert Path(b["instructions"]).is_absolute() and Path(b["instructions"]).name == "SILVER_PROMPT_v2.md"
            assert "gold" in b["output_dir_template"] and "v2" in b["output_dir_template"]
            for u in b["units"]:
                assert Path(u["schema_path"]).is_absolute() and Path(u["schema_path"]).name == f"{u['doc_type']}.json"
                assert all(Path(i["path"]).is_absolute() and "pages_v2" in i["path"] for i in u["images"])
    assert [u["unit_id"] for b in first for u in b["units"]] != [u["unit_id"] for b in second for u in b["units"]]   # thứ tự khác nhau
    assert sum(1 for b in first[:-1] if len({u["doc_type"] for u in b["units"]}) >= 2) == len(first) - 1                # trộn loại


def test_write_batches_does_not_touch_v1_files(tmp_path):
    gold = V2DIR.parent
    before = {p.name: p.stat().st_mtime for p in [gold / "units.csv", gold / "batches_second_annotator.json"] if p.exists()}
    V2.write_batches(_fake_units(10), tmp_path / "b", tmp_path / "s.json")
    after = {p.name: p.stat().st_mtime for p in [gold / "units.csv", gold / "batches_second_annotator.json"] if p.exists()}
    assert before == after


def test_units_csv_roundtrip_has_v1_columns(tmp_path):
    p = tmp_path / "u.csv"
    V2.write_units_csv(_fake_units(3), p)
    rows = MS.load_units(p)
    assert set(rows) == {"u0_0", "u1_0", "u2_0"} and rows["u1_0"]["shown_pages"] == "1;2" and rows["u0_0"]["split"] == "DEV"


def test_gitignore_covers_v2_page_images():
    root = V2DIR.parents[3]
    lines = (root / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "teams/team4_extraction/gold/pages/" in lines and "teams/team4_extraction/gold/v2/pages_v2/" in lines


def test_prompt_v2_keeps_the_hard_rules():
    t = (V2DIR / "SILVER_PROMPT_v2.md").read_text(encoding="utf-8")
    for needle in ("QUY TẮC DỪNG", "withhold_value", "illegible", "under_stamp", "12 từ", "DONE units=", "gold/v2/silver_raw", "Ảnh trắng", "tên tệp",
                   "khong_thoi_han", "x-expiry_fields"):
        assert needle in t, needle


# --------------------------------------------------------------------------- merge/adjudication cho v2
def test_merge_version_defaults_point_to_v2_and_v1_unchanged():
    d2, d1 = MS.version_defaults("v2"), MS.version_defaults("v1")
    assert d2["units"].name == "units_v2.csv" and d2["out"].name == "fields_silver_v2.jsonl" and d2["report"].name == "silver_report_v2.md"
    assert d2["raw"].parent.name == "v2"
    assert d1["units"].name == "units.csv" and d1["out"].name == "fields_silver_v1.jsonl" and d1["report"].name == "silver_report.md"


def _blank(status="not_present"):
    return {"value": None, "normalized": None, "page": None, "evidence": None, "ink": None, "status": status, "note": None}


def _raw(dt, uid, annotator, **over):
    sch = json.loads((SCHEMA_DIR / f"{dt}.json").read_text(encoding="utf-8"))
    fields = {}
    for f in sch["x-fields"]:
        if f["silver_policy"] == "withhold_value":
            fields[f["name"]] = {**_blank("ok"), "page": 1, "ink": "printed"}
        else:
            fields[f["name"]] = _blank()
    fields.update(over)
    return {"unit_id": uid, "annotator": annotator, "doc_type": dt, "pages_seen": [1], "fields": fields, "unit_note": None}


def test_merge_cli_v2_end_to_end_on_gplx_without_images(tmp_path):
    units = tmp_path / "units_v2.csv"
    V2.write_units_csv([{"unit_id": "g1_0", "doc_id": "g1", "seg_idx": 0, "doc_type": "GPLX", "split": "DEV", "pages": [1], "n_pages": 1,
                         "shown_pages": [1], "n_images": 2, "template_group": "", "is_scanned": "True", "composite": 0, "relative_path": "x.pdf"}], units)
    raw = tmp_path / "silver_raw"
    exp = {"value": "01/02/2030", "normalized": "2030-02-01", "page": 1, "evidence": "Có giá trị đến 01/02/2030", "ink": "printed", "status": "ok", "note": None}
    for a in ("haiku", "sonnet"):
        (raw / a).mkdir(parents=True)
        (raw / a / "g1_0.json").write_text(json.dumps(_raw("GPLX", "g1_0", a, ngay_het_han=exp), ensure_ascii=False), encoding="utf-8")
    out, rep = tmp_path / "f.jsonl", tmp_path / "r.md"
    rc = MS.main(["--version", "v2", "--raw", str(raw), "--units", str(units), "--out", str(out), "--report", str(rep),
                  "--manifest", str(tmp_path / "none.csv"), "--adjudication", str(tmp_path / "noadj")])
    assert rc == 0
    rec = json.loads(out.read_text(encoding="utf-8").splitlines()[0])
    f = rec["fields"]
    assert f["ngay_het_han"]["normalized"] == "2030-02-01" and f["ngay_het_han"]["review_status"] == "agreed_unverified"
    assert f["so_gplx"]["value"] is None and f["so_gplx"]["value_withheld"] is True and f["ngay_sinh"]["value_withheld"] is True
    text = rep.read_text(encoding="utf-8")
    assert "silver v2" in text and "01/02/2030" not in text


def test_build_adjudication_v2_paths_and_prompt(tmp_path):
    units = tmp_path / "units_v2.csv"
    V2.write_units_csv([{"unit_id": "g1_0", "doc_id": "g1", "seg_idx": 0, "doc_type": "GPLX", "split": "DEV", "pages": [1], "n_pages": 1,
                         "shown_pages": [1], "n_images": 1, "template_group": "", "is_scanned": "True", "composite": 0, "relative_path": "x.pdf"}], units)
    raw = tmp_path / "silver_raw"
    a = {"value": "01/02/2030", "normalized": "2030-02-01", "page": 1, "evidence": "đến 01/02/2030", "ink": "printed", "status": "ok", "note": None}
    b = dict(a, value="01/02/2031", normalized="2031-02-01")
    for who, v in (("haiku", a), ("sonnet", b)):
        (raw / who).mkdir(parents=True)
        (raw / who / "g1_0.json").write_text(json.dumps(_raw("GPLX", "g1_0", who, ngay_het_han=v), ensure_ascii=False), encoding="utf-8")
    pages = tmp_path / "pages_v2" / "g1_0"
    pages.mkdir(parents=True)
    (pages / "p01.png").write_bytes(b"x")
    prompt = tmp_path / "PROMPT.md"
    res = BA.build(raw, units, SCHEMA_DIR, tmp_path / "none.csv", tmp_path / "adj", "haiku", pages_dir=tmp_path / "pages_v2", prompt_path=prompt)
    assert res["n_items"] == 1 and res["by_reason"] == {"needs_human": 1}
    qb = json.loads((tmp_path / "adj" / "queue_batch_01.json").read_text(encoding="utf-8"))
    assert qb["instructions"] == str(prompt) and "pages_v2" in qb["units"][0]["images"][0]


# --------------------------------------------------------------------------- sản phẩm thật (nếu đã sinh)
def _read_units():
    with open(V2DIR / "units_v2.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@needs_kit
def test_real_units_cover_only_phase3_types_and_valid_splits():
    rows = _read_units()
    assert {r["doc_type"] for r in rows} <= set(PHASE3_TYPES)
    assert {r["split"] for r in rows} <= {"DEV", "TEST", "EXCLUDED"}
    assert len({r["unit_id"] for r in rows}) == len(rows)
    for r in rows:
        assert 1 <= int(r["n_shown_pages"]) <= 6 and int(r["n_images"]) >= int(r["n_shown_pages"])


@needs_kit
def test_real_batches_cover_every_unit_once_for_both_annotators_and_images_listed_exist_in_csv_counts():
    rows = _read_units()
    ids = sorted(r["unit_id"] for r in rows)
    first = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((V2DIR / "batches_v2").glob("batch_*.json"))]
    second = json.loads((V2DIR / "batches_v2_second.json").read_text(encoding="utf-8"))["batches"]
    for batches in (first, second):
        assert sorted(u["unit_id"] for b in batches for u in b["units"]) == ids
        assert all(b["n_images"] <= 24 for b in batches)
    n_img = {r["unit_id"]: int(r["n_images"]) for r in rows}
    assert all(len(u["images"]) == n_img[u["unit_id"]] for b in first for u in b["units"])
    assert Counter(r["doc_type"] for r in rows)["HD_VAN_CHUYEN"] >= 20


@needs_kit
def test_real_image_files_exist_if_rendered():
    pages = V2DIR / "pages_v2"
    if not pages.exists():
        pytest.skip("ảnh chưa render (thư mục bị .gitignore)")
    first = json.loads((V2DIR / "batches_v2" / "batch_01.json").read_text(encoding="utf-8"))
    for u in first["units"]:
        for im in u["images"]:
            assert Path(im["path"]).exists(), im["path"]
