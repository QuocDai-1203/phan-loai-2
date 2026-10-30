"""Kiểm thử hạ tầng giai đoạn 2: quy tắc tự nhận hạn, ghép phương pháp, cận nhị thức, quy ước đáp án, đồng bộ prompt thí nghiệm <-> sản xuất."""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1] / "experiments" / "02_methods"
sys.path.insert(0, str(HERE))

import combine as C  # noqa: E402
import lib  # noqa: E402
from eval.field_metrics import FieldSpec, compare_field  # noqa: E402
from src.extraction import expiry_rules as ER  # noqa: E402


def rows(**f):
    return {"u1": {"unit_id": "u1", "doc_type": "T", "status": "ok",
                   "fields": {k: ({"value": v, "normalized": v, "page": None} if v else {"value": None, "normalized": None, "page": None}) for k, v in f.items()}}}


def test_clopper_pearson_and_samples_needed():
    assert C.cp_upper(0, 299) < 0.01 <= C.cp_upper(0, 298)
    assert C.n_needed(0.01, 0) == 299 and C.n_needed(0.05, 0) == 59
    assert C.cp_upper(1, 10) > C.cp_upper(0, 10) and C.cp_upper(0, 0) == 1.0
    assert C.n_needed(0.01, 1) > 299                                   # một lỗi quan sát đòi nhiều mẫu hơn


def test_expiry_rules_require_agreement_and_never_guess():
    R = ER.EXPIRY_RULES
    c = {"regex": "2028-01-22", "llm": "2028-01-22", "vlm": None, "filename": "2028-01-12"}
    assert R["regex=llm"](c) == "2028-01-22"                         # hai nguồn cùng một OCR đồng thuận SAI: lý do cần nguồn độc lập
    assert R["any-model=filename"](c) is None                        # tên tệp khác mọi mô hình -> từ chối
    assert R["any-model=filename"]({**c, "vlm": "2028-01-12"}) == "2028-01-12"
    assert R["2-of-3 (regex,llm,vlm)"]({"regex": "A", "llm": "B", "vlm": None}) is None   # hòa phiếu -> từ chối
    assert ER.full_date("2028-01") is None and ER.full_date("~raw:x") is None and ER.full_date("2028-01-12") == "2028-01-12"
    assert all(R[k]({}) is None for k in R)                          # không có nguồn nào -> không bao giờ tự nhận


def test_abstention_table_counts_wrong_values_and_spurious():
    gold = {"u1": {"het": {"value": "12/01/2028", "status": "ok"}}, "u2": {"het": {"value": None, "status": "not_present"}},
            "u3": {"het": {"value": "01/01/2030", "status": "ok"}}}
    types = {u: "T" for u in gold}
    ex = {"T": ["het"]}

    def src(d):
        return {"regex": {u: {"status": "ok", "fields": {"het": {"normalized": v}}} for u, v in d.items()}}

    t = C.abstention_table(gold, types, ["u1", "u2", "u3"], src({"u1": "2028-01-12", "u2": "2029-05-05", "u3": "2030-01-02"}), ex, ["regex"])[0]
    assert (t["n_gold_present"], t["n_emitted"], t["n_correct"], t["n_wrong"], t["n_spurious"]) == (2, 3, 1, 2, 1)   # u2: giấy không có hạn mà máy ra ngày = sai
    assert t["wrong_upper95"] > t["wrong_rate"]


def test_cascade_typed_prefers_llm_for_text_and_rules_for_ids():
    regex = rows(so="R-1", ten="r ten")
    llm = rows(so="L-1", ten="l ten")
    out = C.cascade_typed(regex, llm, {"T": {"so": "id", "ten": "text"}}, ["u1"])
    assert out["u1"]["fields"]["so"]["value"] == "R-1" and out["u1"]["fields"]["ten"]["value"] == "l ten"
    out2 = C.cascade_typed(rows(so=None, ten=None), llm, {"T": {"so": "id", "ten": "text"}}, ["u1"])
    assert out2["u1"]["fields"]["so"]["value"] == "L-1"             # nguồn ưu tiên trống thì lấy nguồn còn lại


def test_lenient_mode_differs_from_normalized_only_for_text():
    t = FieldSpec("ten", "text")
    d = FieldSpec("ngay", "date")
    assert compare_field("Công ty A; MST 0301234567", "CONG TY A", t, "normalized") == "wrong"
    assert compare_field("Công ty A; MST 0301234567", "CONG TY A", t, "lenient") == "tp"
    assert compare_field("12/01/2028", "13/01/2028", d, "lenient") == "wrong"
    assert compare_field("12/01/2028", "ngày 12 tháng 1 năm 2028", d, "lenient") == "tp"


def test_gold_conventions(tmp_path):
    def rec(value, status="ok", note=None, ink="printed", page=1):
        return {"value": value, "status": status, "review_status": "single_annotator", "note": note, "ink": ink, "page": page}
    m = {"unit_id": "h1", "doc_type": "HD_MUA_BAN", "split": "DEV",
         "fields": {"ngay_ky": rec("29 tháng 04 năm 2022"), "hieu_luc_tu": rec("từ ngày ký"), "hieu_luc_den": rec("12 tháng 05 năm 202[?]"),
                    "so_hop_dong": rec("12/HĐ[?]"), "mat_hang": rec("xăng dầu"), "ben_ban": rec(None, "not_present", ink=None, page=None),
                    "han_muc_cong_no": rec("thời hạn 12 tháng", note="khong_ngay_cu_the")}}
    p = tmp_path / "g.jsonl"
    p.write_text(json.dumps(m, ensure_ascii=False) + "\n", encoding="utf-8")
    g, types, split = lib.load_gold(p)
    f = g["h1"]
    assert f["hieu_luc_tu"]["value"] == "29 tháng 04 năm 2022"        # 'từ ngày ký' quy về ngày ký
    assert f["hieu_luc_den"]["status"] == "illegible" and f["so_hop_dong"]["status"] == "illegible"   # đọc một phần: loại khỏi điểm
    assert f["ben_ban"]["status"] == "not_present" and f["mat_hang"]["status"] == "ok"
    g2, *_ = lib.load_gold(p, review_statuses=["agreed_unverified"])
    assert all(v["status"] == "illegible" for v in g2["h1"].values())  # lọc theo độ tin cậy: loại khỏi điểm, không coi là 'not_present'


def test_restrict_gold_pages_drops_only_later_pages():
    g = {"u": {"a": {"value": "x", "status": "ok", "page": 3}, "b": {"value": "y", "status": "ok", "page": 1}, "c": {"value": None, "status": "not_present", "page": None}}}
    r = lib.restrict_gold_pages(g, 2)["u"]
    assert r["a"]["status"] == "illegible" and r["b"]["status"] == "ok" and r["c"]["status"] == "not_present"


def test_experiment_prompt_is_identical_to_production_prompt():
    """Prompt đã chấm (methods/local_llm_json.py) phải đúng là prompt chạy thật (src/extraction/field_llm.py)."""
    from methods import local_llm_json as exp
    from methods.common import Unit
    from src.extraction import field_llm as prod
    assert exp.SYSTEM == prod.SYSTEM
    for dt in ("GCN_DDK_BAN_LE_XD", "CC_TAP_HUAN_VC_HNH", "HD_MUA_BAN", "PHIEU_XUAT_KHO"):
        u = Unit("x_0", "x", dt, "DEV", [1], [1])
        ef = exp.fields_for(u, False)
        pf = prod.fields_for(dt, False)
        assert [f["name"] for f in ef] == [f["name"] for f in pf]
        assert exp.json_schema(ef) == prod.json_schema(pf)
        assert exp.field_instructions(ef) == prod.field_instructions(pf)


def test_vlm_experiment_prompt_matches_production():
    from methods import local_vlm_json as exp
    from src.extraction import field_vlm as prod
    assert exp.SYSTEM_VLM == prod.SYSTEM_VLM


def test_frozen_selection_if_present_matches_code():
    sel = HERE / "dev_selection.json"
    if not sel.exists():
        pytest.skip("chưa đóng băng")
    import hashlib
    s = json.loads(sel.read_text(encoding="utf-8"))
    root = Path(__file__).resolve().parents[3]
    for key, rel in (("regex_rules", "src/extraction/field_rules.py"), ("normalize", "src/extraction/normalize.py"),
                     ("expiry_rules", "src/extraction/expiry_rules.py"), ("llm_prompt_module", "src/extraction/field_llm.py")):
        assert hashlib.sha256((root / rel).read_bytes()).hexdigest()[:16] == s["code_hashes"][key], f"{rel} đã đổi sau khi đóng băng"
