"""Kiểm thử nới kiểm hợp lệ (mức trường), so sánh mềm, và hàng đợi/áp dụng phân xử của người đọc thứ ba."""
import csv
import json
from pathlib import Path

import pytest

from gold import build_adjudication as BA
from gold import merge_silver as MS

TEAM = Path(__file__).resolve().parents[1]
SCHEMA_DIR = TEAM / "schema"
DT = "CC_TAP_HUAN_VC_HNH"


def blank(status="not_present"):
    return {"value": None, "normalized": None, "page": None, "evidence": None, "ink": None, "status": status, "note": None}


def ok(value, page=2, ink="printed", evidence="trích dẫn"):
    return {"value": value, "normalized": None, "page": page, "evidence": evidence, "ink": ink, "status": "ok", "note": None}


def raw_file(uid, annotator, **over):
    schema = json.loads((SCHEMA_DIR / f"{DT}.json").read_text(encoding="utf-8"))
    fields = {f["name"]: blank() for f in schema["x-fields"]}
    fields["nam_sinh"] = {"value": None, "normalized": None, "page": 2, "evidence": None, "ink": "printed", "status": "ok", "note": None}
    fields.update(over)
    return {"unit_id": uid, "annotator": annotator, "doc_type": DT, "pages_seen": [1, 2], "fields": fields, "unit_note": None}


@pytest.fixture()
def kit(tmp_path):
    cols = ["unit_id", "doc_id", "segment_idx", "doc_type", "split", "pages", "n_pages", "shown_pages", "n_shown_pages", "n_images",
            "template_group", "is_scanned", "composite", "relative_path"]
    units = tmp_path / "units.csv"
    with open(units, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for i in (1, 2, 3):
            w.writerow([f"d{i}_0", f"d{i}", 0, DT, "DEV", "1;2", 2, "1;2", 2, 4, "T001", "True", 0, f"x/{i}.pdf"])
    manifest = tmp_path / "manifest.csv"
    with open(manifest, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["doc_id", "file_name"])
        w.writerow(["d1", "15. GCN Ten (12-5-24).pdf"])
        w.writerow(["d2", "16. GCN Ten (1-1-30).pdf"])
        w.writerow(["d3", "17. GCN Ten (2-2-31).pdf"])
    raw = tmp_path / "silver_raw"
    for a in ("haiku", "sonnet"):
        (raw / a).mkdir(parents=True)

    def put(a, uid, obj):
        (raw / a / f"{uid}.json").write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")

    put("haiku", "d1_0", raw_file("d1_0", "haiku", ngay_het_han=ok("12/05/2024"), ngay_cap=ok("12 tháng 05 năm 2022"),
                                  so_gcn=ok("51/2022-GCN"), nghe_nghiep=ok("Thủ kho", ink="handwritten")))
    put("sonnet", "d1_0", raw_file("d1_0", "sonnet", ngay_het_han=ok("12/05/2024"), ngay_cap=ok("12 tháng 06 năm 2022"),
                                   so_gcn=blank(), nghe_nghiep=ok("thủ kho", ink="handwritten")))
    put("haiku", "d2_0", raw_file("d2_0", "haiku", ngay_het_han=ok("01/01/2030")))
    put("haiku", "d3_0", raw_file("d3_0", "haiku", ngay_het_han=ok("01/01/2031")))
    put("sonnet", "d3_0", raw_file("d3_0", "sonnet", ngay_het_han=ok("01/01/2031")))
    return tmp_path, units, manifest, raw


# ---------------------------------------------------------------------------------------------- nới kiểm hợp lệ
def test_cosmetic_violations_are_counted_warnings_not_unit_loss(kit):
    _tmp, units_csv, _m, raw = kit
    long_ev = " ".join(f"tu{i}" for i in range(30))
    obj = raw_file("d1_0", "haiku", ngay_het_han=ok("12/05/2024", evidence=long_ev), so_gcn={**ok("51/2022-GCN"), "ink": "nhin_thay_la"})
    (raw / "haiku" / "d1_0.json").write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    valid, stat, problems, _issues, warns = MS.collect(raw, MS.load_units(units_csv), MS.load_schemas(SCHEMA_DIR))
    assert "haiku" in valid["d1_0"] and not [p for p in problems if p[1] == "d1_0"]
    assert warns["haiku"]["evidence_too_long"] == 1 and warns["haiku"]["bad_ink"] == 1
    kept = valid["d1_0"]["haiku"]["fields"]
    assert len(kept["ngay_het_han"]["evidence"].split()) == 12 and kept["so_gcn"]["ink"] is None


def test_page_not_shown_drops_only_that_field(kit):
    _tmp, units_csv, _m, raw = kit
    obj = raw_file("d1_0", "haiku", so_gcn=ok("51/2022-GCN", page=9), ngay_cap=ok("12/05/2022"))
    (raw / "haiku" / "d1_0.json").write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    valid, _s, problems, issues, _w = MS.collect(raw, MS.load_units(units_csv), MS.load_schemas(SCHEMA_DIR))
    assert ("haiku", "d1_0", "so_gcn", "page_not_shown") in issues and not problems
    assert "so_gcn" not in valid["d1_0"]["haiku"]["fields"] and "ngay_cap" in valid["d1_0"]["haiku"]["fields"]


def test_fatal_problems_still_drop_the_unit(kit):
    _tmp, units_csv, _m, raw = kit
    (raw / "haiku" / "d1_0.json").write_text("{không phải json", encoding="utf-8")
    (raw / "sonnet" / "d1_0.json").write_text(json.dumps({"unit_id": "d9_0", "fields": {}}), encoding="utf-8")
    valid, _s, problems, _i, _w = MS.collect(raw, MS.load_units(units_csv), MS.load_schemas(SCHEMA_DIR))
    assert "d1_0" not in valid and {(a, u) for a, u, _ in problems} >= {("haiku", "d1_0"), ("sonnet", "d1_0")}


# ---------------------------------------------------------------------------------------------- so sánh mềm
def test_lenient_text_agreement_is_reported_beside_strict(kit):
    tmp, units_csv, manifest, raw = kit
    for a, v in (("haiku", "Công ty CP Hiệp Hòa; MST 4100668616"), ("sonnet", "CONG TY CP HIEP HOA")):
        obj = raw_file("d1_0", a, don_vi_cap=ok(v), ngay_cap=ok("12 tháng 05 năm 2022"))
        (raw / a / "d1_0.json").write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    units, schemas = MS.load_units(units_csv), MS.load_schemas(SCHEMA_DIR)
    valid, *_ = MS.collect(raw, units, schemas)
    m = MS.merge_unit(units["d1_0"], schemas[DT], valid["d1_0"], "haiku")
    f = m["fields"]["don_vi_cap"]
    assert f["review_status"] == "agreed_unverified" and f["agreement"] == "lenient"      # không còn bị đẩy sang needs_human
    assert m["fields"]["ngay_cap"]["agreement"] == "strict"
    md_path = tmp / "r.md"
    MS.run(raw, units_csv, SCHEMA_DIR, tmp / "f.jsonl", md_path, manifest, "haiku", tmp / "none")
    md = md_path.read_text(encoding="utf-8")
    row = next(line for line in md.splitlines() if line.startswith("| text"))
    cells = [c.strip() for c in row.strip("|").split("|")]
    assert float(cells[2].split()[0]) < float(cells[3].split()[0])                        # chặt < mềm ở kiểu text


def test_lenient_never_merges_different_tax_codes_or_names():
    from eval.normalize import lenient_text_equal as eq
    assert eq("Công ty A; MST 0301234567", "công ty a")
    assert not eq("Công ty A; MST 0301234567", "Công ty A; MST 0301234568")
    assert not eq("Công ty A", "Công ty B")
    assert not eq("abc", "abcd")
    assert eq("Thủ kho.", "thu kho")


# ---------------------------------------------------------------------------------------------- phân xử
def build_queue(kit):
    tmp, units_csv, manifest, raw = kit
    pages = tmp / "pages"
    for uid in ("d1_0", "d2_0", "d3_0"):
        (pages / uid).mkdir(parents=True, exist_ok=True)
        for n in ("p01_a.png", "p01_b.png", "p02_a.png", "p02_b.png"):
            (pages / uid / n).write_bytes(b"x")
    out = tmp / "adjudication"
    res = BA.build(raw, units_csv, SCHEMA_DIR, manifest, out, "haiku", pages_dir=pages)
    return res, out


def test_queue_contents_randomisation_and_privacy(kit):
    _res, out = build_queue(kit)
    q = json.loads((out / "queue.json").read_text(encoding="utf-8"))
    key = json.loads((out / "key.json").read_text(encoding="utf-8"))
    items = {i["item_id"]: i for i in q["items"]}
    assert {"d1_0__so_gcn", "d1_0__ngay_cap", "d1_0__nghe_nghiep", "d3_0__ngay_het_han"} <= set(items)
    assert key["d1_0__so_gcn"]["reasons"] == ["needs_human"] and "ink_risk" in key["d1_0__nghe_nghiep"]["reasons"]
    assert key["d3_0__ngay_het_han"]["reasons"] == ["filename_mismatch"]
    assert "d2_0__ngay_het_han" not in items                                              # d2 khớp tên tệp, chỉ một người: không vào hàng đợi
    fm = items["d3_0__ngay_het_han"]
    blob = json.dumps(fm)
    assert fm["single_candidate"] and fm["candidate_y"] is None and "2-2-31" not in blob and "Ten" not in blob
    assert sorted(key["d1_0__ngay_cap"]["candidate_x"] + key["d1_0__ngay_cap"]["candidate_y"]) == ["haiku", "sonnet"]
    for p in [out / "queue.json", *out.glob("queue_batch_*.json")]:
        txt = p.read_text(encoding="utf-8")
        assert "haiku" not in txt and "sonnet" not in txt and "filename" not in txt
    for p in out.glob("queue_batch_*.json"):
        b = json.loads(p.read_text(encoding="utf-8"))
        assert b["n_images"] <= 24 and all(Path(i).is_absolute() for u in b["units"] for i in u["images"])
    # trường PII chỉ có trạng thái, không có giá trị
    assert all(i["candidate_x"]["value"] is None for i in items.values() if i["silver_policy"] == "withhold_value")
    # tất định: dựng lại cho cùng thứ tự x/y
    _r2, out2 = build_queue(kit)
    assert json.loads((out2 / "key.json").read_text(encoding="utf-8")) == key


def write_verdicts(out, verdicts):
    (out / "out").mkdir(exist_ok=True)
    for iid, v in verdicts.items():
        (out / "out" / f"{iid}.json").write_text(json.dumps({"item_id": iid, **v}, ensure_ascii=False), encoding="utf-8")


def test_adjudication_is_model_adjudicated_never_human_verified_and_scores_annotators(kit):
    _res, out = build_queue(kit)
    key = json.loads((out / "key.json").read_text(encoding="utf-8"))
    tmp, units_csv, manifest, raw = kit

    def haiku_right(iid):
        return "x_correct" if key[iid]["candidate_x"] == ["haiku"] else "y_correct"

    def rec(value, **k):
        return {"value": value, "normalized": None, "page": 2, "ink": "printed", "status": "ok", "reason": "doc ro", **k}

    write_verdicts(out, {
        "d1_0__ngay_cap": {**rec("12 tháng 05 năm 2022"), "verdict": haiku_right("d1_0__ngay_cap")},
        "d1_0__so_gcn": {**rec("51/2022-GCN"), "verdict": haiku_right("d1_0__so_gcn")},
        "d1_0__nghe_nghiep": {**rec("Thủ kho", ink="handwritten"), "verdict": "both_equivalent"},
        "d3_0__ngay_het_han": {**rec("ngày 01 tháng 01 năm 2032"), "verdict": "neither"},
    })
    md_path, out_path = tmp / "r.md", tmp / "f.jsonl"
    res = MS.run(raw, units_csv, SCHEMA_DIR, out_path, md_path, manifest, "haiku", out)
    assert res["n_adjudicated"] == 4
    rows = {json.loads(line)["unit_id"]: json.loads(line) for line in out_path.read_text(encoding="utf-8").splitlines()}
    f = rows["d1_0"]["fields"]["ngay_cap"]
    assert f["review_status"] == "model_adjudicated" and f["normalized"] == "2022-05-12" and f["adjudication"]["verdict"] in ("x_correct", "y_correct")
    assert rows["d3_0"]["fields"]["ngay_het_han"]["normalized"] == "2032-01-01"          # giá trị của người phân xử thay silver
    assert "human_verified" not in out_path.read_text(encoding="utf-8")
    md = md_path.read_text(encoding="utf-8")
    assert "## 6." in md and "Wilson" in md and "model_adjudicated" in md
    verdicts, _items, key2, probs = MS.load_adjudication(out)
    assert not probs
    st = MS.adjudication_stats(verdicts, key2)

    def wrong(a):
        return sum(x[0] for x in st[a].values()), sum(x[1] for x in st[a].values())

    # mục hạn d3 chỉ có MỘT bản đọc silver mà cả hai người cùng đọc: phán quyết "neither" tính sai cho cả hai.
    # haiku: 4 bản đọc, sai 1 (hạn d3); sonnet: 4 bản đọc, sai 3 (ngay_cap, so_gcn, hạn d3)
    assert wrong("haiku") == (1, 4) and wrong("sonnet") == (3, 4)
    assert "2022" not in md and "Thủ kho" not in md and "2032" not in md                  # báo cáo không in giá trị


def test_invalid_adjudication_files_are_ignored_and_listed(kit):
    _res, out = build_queue(kit)
    write_verdicts(out, {
        "d1_0__ngay_cap": {"verdict": "chac_chan_x", "value": "x", "normalized": None, "page": 1, "ink": "printed", "status": "ok"},
        "d3_0__ngay_het_han": {"verdict": "y_correct", "value": "x", "normalized": None, "page": 1, "ink": "printed", "status": "ok"},
    })
    verdicts, _i, _k, probs = MS.load_adjudication(out)
    assert verdicts == {} and {i for i, _ in probs} == {"d1_0__ngay_cap", "d3_0__ngay_het_han"}   # mục 1 bản đọc không có phán quyết y


def test_pii_withheld_item_must_not_carry_a_value():
    item = {"item_id": "d1_0__nam_sinh", "silver_policy": "withhold_value"}
    key = {"single_candidate": False}
    bad = {"item_id": "d1_0__nam_sinh", "verdict": "both_equivalent", "value": "22/01/1981", "normalized": None, "page": 2, "ink": "printed", "status": "ok"}
    assert "pii_value_present" in MS.validate_adjudication(bad, item, key)
    good = {**bad, "value": None}
    assert MS.validate_adjudication(good, item, key) == []
