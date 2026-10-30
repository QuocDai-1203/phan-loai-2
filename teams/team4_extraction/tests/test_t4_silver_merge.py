"""Kiểm thử gold/merge_silver.py: kiểm hợp lệ, gộp hai người chú thích, trạng thái trường, báo cáo không lộ giá trị/PII."""
import csv
import json
from pathlib import Path

import pytest

from gold import merge_silver as MS

TEAM = Path(__file__).resolve().parents[1]
SCHEMA_DIR = TEAM / "schema"
DT = "CC_TAP_HUAN_VC_HNH"
SECRET_NAME = "NGUYEN VAN BIMAT"
SECRET_BIRTH = "22/01/1981"


def blank(status="not_present"):
    return {"value": None, "normalized": None, "page": None, "evidence": None, "ink": None, "status": status, "note": None}


def ok(value, page=2, ink="printed", norm=None, evidence="trích dẫn"):
    return {"value": value, "normalized": norm, "page": page, "evidence": evidence, "ink": ink, "status": "ok", "note": None}


def raw_file(uid, annotator, **over):
    schema = json.loads((SCHEMA_DIR / f"{DT}.json").read_text(encoding="utf-8"))
    fields = {f["name"]: blank() for f in schema["x-fields"]}
    # nam_sinh: có trên giấy nhưng KHÔNG chép giá trị (quy tắc 7)
    fields["nam_sinh"] = {"value": None, "normalized": None, "page": 2, "evidence": None, "ink": "printed", "status": "ok", "note": None}
    fields.update(over)
    return {"unit_id": uid, "annotator": annotator, "doc_type": DT, "pages_seen": [1, 2], "fields": fields, "unit_note": None}


@pytest.fixture()
def kit(tmp_path):
    units = tmp_path / "units.csv"
    cols = ["unit_id", "doc_id", "segment_idx", "doc_type", "split", "pages", "n_pages", "shown_pages", "n_shown_pages", "n_images",
            "template_group", "is_scanned", "composite", "relative_path"]
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

    # d1: hai người hợp lệ
    put("haiku", "d1_0", raw_file("d1_0", "haiku", **{
        "ngay_het_han": ok("ngày 12 tháng 05 năm 2024"), "ngay_cap": ok("12 tháng 05 năm 2022"), "so_gcn": ok("51/2022-GCN"),
        "nghe_nghiep": ok("Thủ kho", ink="handwritten"), "ho_ten": ok(SECRET_NAME)}))
    put("sonnet", "d1_0", raw_file("d1_0", "sonnet", **{
        "ngay_het_han": ok("12/05/2024"), "ngay_cap": ok("12 tháng 06 năm 2022"), "so_gcn": blank(),
        "nghe_nghiep": ok("thủ kho", ink="handwritten"), "ho_ten": ok(SECRET_NAME)}))
    # d2: haiku ghi bản ghi lỗi (quy tắc dừng), sonnet hợp lệ
    put("haiku", "d2_0", {"unit_id": "d2_0", "error": "không mở được p02_a.png (số 0123456789 trong lời nhắn phải bị che)"})
    put("sonnet", "d2_0", raw_file("d2_0", "sonnet", ngay_het_han=ok("01/01/2030")))
    # d3: haiku vi phạm quy tắc PII ở MỘT trường (chép ngày sinh) -> chỉ trường đó bị loại; hạn 2031 lệch tên tệp (2-2-31)
    bad = raw_file("d3_0", "haiku", ngay_het_han=ok("01/01/2031"))
    bad["fields"]["nam_sinh"] = ok(SECRET_BIRTH, page=2)
    put("haiku", "d3_0", bad)
    put("sonnet", "d3_0", raw_file("d3_0", "sonnet", ngay_het_han=ok("01/01/2031")))
    return tmp_path, units, manifest, raw


def run_merge(kit):
    tmp, units, manifest, raw = kit
    out, md = tmp / "fields.jsonl", tmp / "report.md"
    res = MS.run(raw, units, SCHEMA_DIR, out, md, manifest, "haiku")
    rows = {json.loads(l)["unit_id"]: json.loads(l) for l in out.read_text(encoding="utf-8").splitlines()}
    return res, rows, md.read_text(encoding="utf-8"), out.read_text(encoding="utf-8")


def test_field_statuses_follow_the_spec(kit):
    _res, rows, _md, _out = run_merge(kit)
    f = rows["d1_0"]["fields"]
    assert f["ngay_het_han"]["review_status"] == "agreed_unverified"                 # khác cách viết, bằng nhau sau chuẩn hóa
    assert f["ngay_het_han"]["normalized"] == "2024-05-12"
    assert f["ngay_cap"]["review_status"] == "needs_human"                            # hai ngày khác nhau
    assert f["so_gcn"]["review_status"] == "needs_human" and "one_null" in f["so_gcn"]["review_reasons"]
    assert f["nghe_nghiep"]["review_status"] == "agreed_unverified" and "ink_risk" in f["nghe_nghiep"]["review_reasons"]
    assert f["don_vi_cap"]["review_status"] == "agreed_unverified"                    # cùng not_present
    assert rows["d1_0"]["annotators"] == ["haiku", "sonnet"]


def test_single_annotator_when_the_other_errored_or_invalid(kit):
    _res, rows, _md, _out = run_merge(kit)
    assert rows["d2_0"]["annotators"] == ["sonnet"]
    assert all(v["review_status"] == "single_annotator" for v in rows["d2_0"]["fields"].values())
    assert rows["d2_0"]["fields"]["ngay_het_han"]["normalized"] == "2030-01-01"
    # d3: lỗi PII ở một trường KHÔNG làm mất cả đơn vị; chỉ nam_sinh còn một người
    assert rows["d3_0"]["annotators"] == ["haiku", "sonnet"]
    assert rows["d3_0"]["fields"]["nam_sinh"]["review_status"] == "single_annotator"
    assert rows["d3_0"]["fields"]["ngay_het_han"]["review_status"] == "agreed_unverified"


def test_pii_values_never_reach_the_merged_file_or_report(kit):
    _res, rows, md, out = run_merge(kit)
    for blob in (md, out):
        assert SECRET_NAME not in blob and SECRET_BIRTH not in blob and "0123456789" not in blob
    assert rows["d1_0"]["fields"]["ho_ten"]["value"] is None and rows["d1_0"]["fields"]["ho_ten"]["value_withheld"] is True
    assert rows["d1_0"]["fields"]["nam_sinh"]["status"] == "ok"                       # biết là CÓ trên giấy, không có giá trị


def test_annotator_that_violates_pii_rule_loses_only_that_field_and_is_listed(kit):
    res, _rows, md, _out = run_merge(kit)
    assert "pii_value_present" in md and "haiku/d3_0/nam_sinh:pii_value_present" in md
    assert res["n_field_issues"] == 1
    assert "error_record" in md and "d2_0" in md


def test_report_has_counts_agreement_ci_and_filename_crosscheck(kit):
    _res, _rows, md, _out = run_merge(kit)
    assert "Wilson" in md and "agreed_unverified" in md and "ink_risk" in md
    assert "khớp: 2" in md and "lệch: 1" in md                                        # d1, d2 khớp; d3 lệch (2031 so với tên tệp 2-2-31)
    assert "Ten" not in md and ".pdf" not in md                                       # không in tên tệp
    # độ đồng thuận: có ít nhất một dòng kiểu 'date' có CI
    assert any(line.startswith("| date") and "[" in line for line in md.splitlines())
    assert "CHẶT và MỀM" in md


def test_validate_rejects_bad_files(kit):
    tmp, units_csv, _m, _raw = kit
    units = MS.load_units(units_csv)
    schemas = MS.load_schemas(SCHEMA_DIR)
    u, s = units["d1_0"], schemas[DT]
    good = raw_file("d1_0", "haiku", ngay_het_han=ok("12/05/2024"))
    assert MS.validate_unit(good, s, u) == ([], False)
    cases = {
        "status_xau": ("ngay_het_han", {**ok("12/05/2024"), "status": "chac_chan"}, "bad_status"),
        "ok_khong_gia_tri": ("ngay_het_han", {**blank("ok")}, "ok_without_value"),
        "gia_tri_khi_not_present": ("so_gcn", {**blank(), "value": "51/2022"}, "value_with_nonok_status"),
        "trang_khong_duoc_xem": ("so_gcn", ok("51/2022", page=9), "page_not_shown"),
    }
    for _name, (fld, rec, expect) in cases.items():
        bad = raw_file("d1_0", "haiku")
        bad["fields"][fld] = rec
        probs, _ = MS.validate_unit(bad, s, u)
        assert any(expect in p for p in probs), (_name, probs)
    missing = raw_file("d1_0", "haiku")
    del missing["fields"]["so_gcn"]
    assert "missing_field:so_gcn" in MS.validate_unit(missing, s, u)[0]
    assert MS.validate_unit({"unit_id": "khac_0", "fields": {}}, s, u)[0][0] == "unit_id_mismatch"
    assert MS.validate_unit({"unit_id": "d1_0", "doc_type": DT}, s, u)[0] == ["fields_missing"]
    assert MS.validate_unit({"unit_id": "d1_0", "error": "ảnh hỏng"}, s, u) == ([], True)


def test_annotator_normalized_mismatch_is_counted_not_trusted(kit):
    tmp, units_csv, _m, _raw = kit
    units, schemas = MS.load_units(units_csv), MS.load_schemas(SCHEMA_DIR)
    r = raw_file("d1_0", "haiku", ngay_het_han=ok("12/05/2024", norm="2025-01-01"))
    merged = MS.merge_unit(units["d1_0"], schemas[DT], {"haiku": r}, "haiku")
    assert merged["fields"]["ngay_het_han"]["normalized"] == "2024-05-12"             # theo script, không theo người chú thích
    assert merged["fields"]["ngay_het_han"]["by_annotator"]["haiku"]["norm_mismatch"] is True
