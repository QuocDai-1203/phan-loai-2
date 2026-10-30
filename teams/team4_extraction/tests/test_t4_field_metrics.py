"""Kiểm thử bộ chấm trường trên dữ liệu giả có đáp án biết trước (eval/field_metrics.py)."""
import math

import pytest

from eval.field_metrics import (FieldSpec, compare_field, list_errors, load_specs, render_markdown, score, score_all_modes,
                                wilson_interval)

SPECS = {"T": [
    FieldSpec("het_han", "date", is_expiry=True, required=True),
    FieldSpec("so", "id", id_kind="document_no", required=True),
    FieldSpec("ten", "text"),
    FieldSpec("qty", "number"),
    FieldSpec("ho_ten", "text", is_pii=True),
]}

GOLD = {
    "u1": {"het_han": "ngày 12 tháng 01 năm 2028", "so": "12/HD", "ten": "Công ty A", "qty": "10.000", "ho_ten": "SECRET-NAME-1"},
    "u2": {"het_han": "01/02/2029", "so": "34", "ten": None, "qty": "5,5", "ho_ten": "SECRET-NAME-2"},
    "u3": {"het_han": None, "so": "56", "ten": "B", "qty": {"value": None, "status": "illegible"}, "ho_ten": None},
    "u4": {"het_han": "05/05/2030", "so": "78", "ten": "D", "qty": "1", "ho_ten": "SECRET-NAME-4"},
}
PRED = {
    "u1": {"het_han": "12.1.28", "so": "Số 12/hđ", "ten": "công ty a", "qty": "10000", "ho_ten": "WRONG-NAME"},
    "u2": {"het_han": "01/02/2028", "so": None, "ten": "Z", "qty": "5.5", "ho_ten": None},
    "u3": {"het_han": "01/01/2030", "so": "56", "ten": None, "qty": "3", "ho_ten": None},
    # u4 thiếu hẳn: phương pháp lỗi
}
TYPES = {u: "T" for u in GOLD}


def row(res, field):
    return next(r for r in res["per_field"] if r["field"] == field)


@pytest.fixture(scope="module")
def res():
    return score(GOLD, PRED, TYPES, SPECS, n_boot=300, seed=1)


def test_per_field_counts_follow_the_readme_convention(res):
    h = row(res, "het_han")      # TP u1; wrong u2 (FP+FN); spurious u3 (FP); empty u4 (FN)
    assert (h["tp"], h["fp"], h["fn"]) == (1, 2, 2)
    assert h["precision"] == pytest.approx(1 / 3) and h["recall"] == pytest.approx(1 / 3) and h["f1"] == pytest.approx(1 / 3)
    s = row(res, "so")
    assert (s["tp"], s["fp"], s["fn"]) == (2, 0, 2) and s["precision"] == 1.0 and s["recall"] == 0.5
    t = row(res, "ten")
    assert (t["tp"], t["fp"], t["fn"]) == (1, 1, 2)
    q = row(res, "qty")          # u3 illegible bị loại khỏi điểm
    assert (q["tp"], q["fp"], q["fn"]) == (2, 0, 1) and q["n_illegible"] == 1


def test_per_type_pooling(res):
    pt = {r["type"]: r for r in res["per_type"]}
    assert (pt["date"]["tp"], pt["date"]["fp"], pt["date"]["fn"]) == (1, 2, 2)
    assert (pt["id"]["tp"], pt["id"]["fn"]) == (2, 2)
    assert (pt["text"]["tp"], pt["text"]["fp"], pt["text"]["fn"]) == (1, 1, 2)
    assert (pt["number"]["tp"], pt["number"]["fn"]) == (2, 1)


def test_document_level_requires_every_required_field(res):
    d = res["doc_level"]
    assert d["n_evaluated"] == 4 and d["n_all_required_correct"] == 1 and d["rate"] == pytest.approx(0.25)


def test_expiry_correct_empty_wrong_and_spurious(res):
    e = next(r for r in res["expiry"] if r["field"] == "T.het_han")
    assert e["n_gold_present"] == 3 and e["n_gold_absent"] == 1
    assert e["correct_rate"] == pytest.approx(1 / 3) and e["empty_rate"] == pytest.approx(1 / 3)
    assert e["wrong_rate"] == pytest.approx(1 / 3)        # u2: ra SAI giá trị — nguy hiểm hơn bỏ trống
    assert e["spurious_rate"] == pytest.approx(1.0)       # u3: giấy không có hạn mà máy bịa ra
    allr = next(r for r in res["expiry"] if r["field"] == "ALL_EXPIRY")
    assert allr["wrong_rate"] == pytest.approx(1 / 3)


def test_failed_units_counted_separately_and_penalised(res):
    assert res["counts"]["n_failed"] == 1 and res["counts"]["failed_units"] == ["u4"]
    assert row(res, "qty")["fn"] == 1   # u4 bị chấm như dự đoán toàn null


def test_error_marker_counts_as_failed():
    pred = dict(PRED, u4={"_status": "error", "fields": {"so": "78"}})
    r = score(GOLD, pred, TYPES, SPECS, n_boot=0)
    assert r["counts"]["n_failed"] == 1 and row(r, "so")["tp"] == 2     # trường của bản ghi lỗi KHÔNG được tính


def test_pii_fields_are_not_scored_or_reported_by_default(res):
    assert all(r["field"] != "ho_ten" for r in res["per_field"])
    r2 = score(GOLD, PRED, TYPES, SPECS, n_boot=0, include_pii=True)
    assert any(r["field"] == "ho_ten" for r in r2["per_field"])


def test_report_and_error_list_never_contain_field_values(res):
    md = render_markdown(res)
    blob = md + str(list_errors(res))
    for secret in ("SECRET-NAME", "WRONG-NAME", "Công ty A", "12/HD", "2028"):
        assert secret not in blob
    assert "u2" in str(list_errors(res)) and "wrong" in str(list_errors(res))


def test_three_comparison_modes_are_reported_separately():
    spec = FieldSpec("ten", "text")
    assert compare_field("Công ty A", "công ty a", spec, "exact") == "wrong"
    assert compare_field("Công ty A", "công ty a", spec, "normalized") == "tp"
    assert compare_field("Công ty A", "Cong ty A", spec, "normalized") == "wrong"
    assert compare_field("Công ty A", "Cong ty A", spec, "nodiac") == "tp"
    g = {"u": {"ten": "Công ty A"}}
    p = {"u": {"ten": "Cong ty A"}}
    modes = score_all_modes(g, p, {"u": "T"}, {"T": [spec]}, n_boot=0)
    assert [modes[m]["per_field"][0]["tp"] for m in ("exact", "normalized", "nodiac")] == [0, 0, 1]


def test_all_correct_gives_perfect_scores_and_tight_ci():
    g = {f"u{i}": {"het_han": "01/01/2030", "so": str(i)} for i in range(20)}
    r = score(g, {u: dict(v) for u, v in g.items()}, {u: "T" for u in g},
              {"T": SPECS["T"][:2]}, n_boot=200, seed=3)
    h = row(r, "het_han")
    assert h["f1"] == 1.0 and h["f1_ci_lo"] == 1.0 and h["f1_ci_hi"] == 1.0
    assert r["doc_level"]["rate"] == 1.0


def test_bootstrap_is_deterministic_and_brackets_the_estimate(res):
    r2 = score(GOLD, PRED, TYPES, SPECS, n_boot=300, seed=1)
    assert r2["doc_level"] == res["doc_level"]
    d = res["doc_level"]
    assert d["ci_lo"] <= d["rate"] <= d["ci_hi"]
    h = row(res, "so")
    assert h["recall_ci_lo"] <= h["recall"] <= h["recall_ci_hi"]


def test_both_null_is_true_negative_not_counted_in_prf():
    g = {"u": {"het_han": None, "so": "1"}}
    p = {"u": {"het_han": None, "so": "1"}}
    r = score(g, p, {"u": "T"}, {"T": SPECS["T"][:2]}, n_boot=0)
    h = row(r, "het_han")
    assert (h["tp"], h["fp"], h["fn"]) == (0, 0, 0) and math.isnan(h["precision"])
    assert r["doc_level"]["rate"] == 1.0          # nhưng vẫn "đúng" ở cấp tài liệu


def test_value_dict_shape_is_accepted():
    spec = FieldSpec("so", "id", id_kind="document_no")
    assert compare_field({"value": "12/HD", "status": "ok"}, {"value": "12/hd"}, spec) == "tp"
    assert compare_field({"value": None, "status": "not_present"}, {"value": None}, spec) == "tn"


def test_wilson_interval():
    lo, hi = wilson_interval(9, 10)
    assert 0.55 < lo < 0.60 and 0.97 < hi < 0.99
    assert math.isnan(wilson_interval(0, 0)[0])


def test_load_specs_from_schema_dir():
    specs = load_specs()
    assert {"GCN_DDK_BAN_LE_XD", "CC_TAP_HUAN_VC_HNH", "HD_MUA_BAN", "PHIEU_XUAT_KHO"} <= set(specs)      # + 17 loại giai đoạn 3
    assert {"GPLX", "HD_VAN_CHUYEN", "GCN_BAO_HIEM"} <= set(specs)
    exp = [f.name for f in specs["GCN_DDK_BAN_LE_XD"] if f.is_expiry]
    assert exp == ["ngay_het_han"]
    assert any(f.name == "ho_ten" and f.is_pii for f in specs["CC_TAP_HUAN_VC_HNH"])
