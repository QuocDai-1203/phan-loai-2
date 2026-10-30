"""Schema 4 loại phải khớp taxonomy; siêu dữ liệu đầy đủ và hợp lệ."""
import json
from pathlib import Path

import pytest

from schema.build_schema import M, PHASE3_TYPES, TARGET_TYPES, build_schema, load_taxonomy

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schema"
TAX = load_taxonomy()
CLASSES = {c["id"]: c for c in TAX["classes"]}
ALL_TYPES = TARGET_TYPES + PHASE3_TYPES


@pytest.mark.parametrize("dt", ALL_TYPES)
def test_schema_matches_taxonomy_key_fields(dt):
    sch = json.loads((SCHEMA_DIR / f"{dt}.json").read_text(encoding="utf-8"))
    tax_fields = CLASSES[dt]["key_fields"]
    assert [f["name"] for f in tax_fields] == [f["name"] for f in sch["x-fields"]] == list(sch["properties"]) == sch["required"]
    for tf, sf in zip(tax_fields, sch["x-fields"]):
        assert tf["is_expiry"] == sf["is_expiry"] and tf["desc"] == sf["desc"]


@pytest.mark.parametrize("dt", ALL_TYPES)
def test_committed_schema_is_up_to_date_with_the_builder(dt):
    """Nếu taxonomy hoặc bảng siêu dữ liệu đổi mà chưa chạy lại build_schema.py thì test này đỏ."""
    committed = json.loads((SCHEMA_DIR / f"{dt}.json").read_text(encoding="utf-8"))
    assert committed == build_schema(CLASSES[dt], str(TAX.get("version")))


@pytest.mark.parametrize("dt", ALL_TYPES)
def test_field_metadata_is_valid(dt):
    sch = json.loads((SCHEMA_DIR / f"{dt}.json").read_text(encoding="utf-8"))
    for f in sch["x-fields"]:
        assert f["type"] in {"date", "number", "id", "text"}
        assert f["typical_ink"] in {"printed", "handwritten", "under_stamp", "unknown"}
        assert f["silver_policy"] in {"transcribe", "withhold_value", "skip"}
        assert isinstance(f["required"], bool) and isinstance(f["is_pii"], bool)
        if f["type"] == "id":
            assert f["id_kind"] in {"tax_code", "plate", "document_no", "generic"}
        if f["is_pii"]:
            assert f["pii_category"] in {"personal_id", "birth_date", "personal_name"}
        # tên trường ASCII (quy ước taxonomy)
        assert f["name"].isascii()
    assert sch["additionalProperties"] is False and set(sch["x-missing_value_convention"]["null_with_reason"]) == {"not_present", "not_found", "illegible"}


def test_expiry_fields_are_the_ones_the_readme_promises():
    exp = {dt: [f["name"] for f in json.loads((SCHEMA_DIR / f"{dt}.json").read_text(encoding="utf-8"))["x-fields"] if f["is_expiry"]]
           for dt in TARGET_TYPES}
    assert exp == {"GCN_DDK_BAN_LE_XD": ["ngay_het_han"], "CC_TAP_HUAN_VC_HNH": ["ngay_het_han"],
                   "HD_MUA_BAN": ["hieu_luc_den"], "PHIEU_XUAT_KHO": []}
    for dt, names in exp.items():       # trường hạn phải là kiểu ngày và nằm trong số bắt buộc trừ hợp đồng (có thể không ghi hạn)
        for n in names:
            assert M[dt][n]["type"] == "date"


def test_derived_routing_field_is_not_annotated():
    sch = json.loads((SCHEMA_DIR / "HD_MUA_BAN.json").read_text(encoding="utf-8"))
    f = next(x for x in sch["x-fields"] if x["name"] == "vai_tro_cong_ty")
    assert f["annotate"] is False and f["silver_policy"] == "skip" and f["enum"] == ["ben_ban", "ben_mua"]


def test_builder_refuses_to_guess_unknown_fields():
    cls = json.loads(json.dumps(CLASSES["PHIEU_XUAT_KHO"]))
    cls["key_fields"].append({"name": "truong_moi", "desc": "x", "is_expiry": False})
    with pytest.raises(SystemExit):
        build_schema(cls, "2.0")


def test_ink_is_unknown_unless_verified():
    for dt in TARGET_TYPES:
        sch = json.loads((SCHEMA_DIR / f"{dt}.json").read_text(encoding="utf-8"))
        for f in sch["x-fields"]:
            if f["typical_ink"] != "unknown":
                assert f.get("typical_ink_verified_on"), "mực chỉ được ghi khi đã xác minh trên trang mẫu"


def test_phase3_types_are_the_17_expected_and_all_have_expiry_fields():
    assert len(PHASE3_TYPES) == 17 and not set(PHASE3_TYPES) & set(TARGET_TYPES)
    for dt in PHASE3_TYPES:
        assert dt in CLASSES, dt
        assert any(f.get("is_expiry") for f in CLASSES[dt]["key_fields"]), f"{dt} không có trường hạn trong taxonomy"


@pytest.mark.parametrize("dt", PHASE3_TYPES)
def test_phase3_expiry_fields_are_declared_dates_and_match_taxonomy(dt):
    sch = json.loads((SCHEMA_DIR / f"{dt}.json").read_text(encoding="utf-8"))
    tax_exp = [f["name"] for f in CLASSES[dt]["key_fields"] if f.get("is_expiry")]
    assert sch["x-expiry_fields"] == tax_exp and tax_exp
    for n in tax_exp:
        assert M[dt][n]["type"] == "date"
        assert M[dt][n].get("annotate", True) is True                     # trường hạn luôn được chú thích
        assert M[dt][n]["hint"], "trường hạn phải có gợi ý cho người chú thích"


@pytest.mark.parametrize("dt", ["GPLX", "CCCD", "CC_HUAN_LUYEN_PCCC", "CC_NGHIEP_VU_BVMT"])
def test_personal_ids_and_birth_dates_are_withheld_in_silver(dt):
    sch = json.loads((SCHEMA_DIR / f"{dt}.json").read_text(encoding="utf-8"))
    by = {f["name"]: f for f in sch["x-fields"]}
    for n in ("so_gplx", "so_dinh_danh", "ngay_sinh", "nam_sinh"):
        if n in by:
            assert by[n]["is_pii"] and by[n]["silver_policy"] == "withhold_value" and by[n]["required"] is False
    assert by["ngay_het_han"]["silver_policy"] == "transcribe"           # hạn không phải PII


def test_routing_and_classification_fields_are_not_annotated():
    for dt, n in (("HD_VAN_CHUYEN", "vai_tro_cong_ty"), ("GXN_THUONG_NHAN_XD", "loai_thuong_nhan"), ("GCN_BAO_HIEM", "loai_bao_hiem")):
        sch = json.loads((SCHEMA_DIR / f"{dt}.json").read_text(encoding="utf-8"))
        f = next(x for x in sch["x-fields"] if x["name"] == n)
        assert f["annotate"] is False and f["silver_policy"] == "skip" and f["enum"]


def test_pii_fields_json_covers_phase3_personal_fields():
    pii = json.loads((SCHEMA_DIR / "pii_fields.json").read_text(encoding="utf-8"))
    names = {f["name"] for f in pii["fields"]}
    assert {"so_gplx", "so_dinh_danh", "ngay_sinh", "nam_sinh", "ho_ten"} <= names
