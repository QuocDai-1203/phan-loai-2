"""T5: ExtractionResult mặc định và log không chứa trường dữ liệu cá nhân (số định danh, ngày sinh); họ tên không vào log."""
import json

from src.extraction.field_result import safe_summary, to_extraction_result

BIRTH = "22/01/1981"
GPLX = "790123456789"
NAME = "Nguyen Van Bimat"

FIELDS = {
    "so_gcn": {"value": "51/2022-GCN", "normalized": "51/2022-GCN", "page": 2},
    "ho_ten": {"value": NAME, "normalized": NAME.lower(), "page": 2},
    "nam_sinh": {"value": BIRTH, "normalized": "1981-01-22", "page": 2},
    "so_gplx": {"value": GPLX, "normalized": GPLX, "page": 2},
    "ngay_het_han": {"value": "ngày 12 tháng 05 năm 2024", "normalized": "2024-05-12", "page": 2},
    "hieu_luc_tu": {"value": None, "normalized": None, "page": None},
}


def test_default_result_has_no_birth_date_or_personal_id():
    res = to_extraction_result("s1", "CC_TAP_HUAN_VC_HNH", FIELDS)
    dumped = res.model_dump_json()
    assert BIRTH not in dumped and "1981" not in dumped and GPLX not in dumped
    assert "nam_sinh" not in res.entity_dict and "so_gplx" not in res.entity_dict
    assert res.entity_dict["dropped_pii_fields"] == ["nam_sinh", "so_gplx"]               # chỉ tên trường, không giá trị
    assert res.entity_dict["ngay_het_han"] == "2024-05-12" and res.entity_dict["hieu_luc_tu"] is None
    assert {e.label for e in res.entities} == {"so_gcn", "ho_ten", "ngay_het_han"}
    assert res.status == "ok" and res.error is None


def test_flag_store_personal_ids_true_keeps_them():
    res = to_extraction_result("s1", "CC_TAP_HUAN_VC_HNH", FIELDS, store_personal_ids=True)
    assert res.entity_dict["nam_sinh"] == "1981-01-22" and res.entity_dict["so_gplx"] == GPLX
    assert "dropped_pii_fields" not in res.entity_dict


def test_names_can_be_dropped_too():
    res = to_extraction_result("s1", "CC_TAP_HUAN_VC_HNH", FIELDS, store_personal_names=False)
    assert NAME not in res.model_dump_json() and "ho_ten" in res.entity_dict["dropped_pii_fields"]


def test_log_summary_contains_no_values_at_all(caplog):
    import logging
    for flag in (False, True):
        res = to_extraction_result("s1", "CC_TAP_HUAN_VC_HNH", FIELDS, store_personal_ids=flag)
        logging.getLogger("t4.test").info("kết quả: %s", safe_summary(res))
    for secret in (BIRTH, GPLX, NAME, "2024-05-12", "51/2022-GCN"):
        assert secret not in caplog.text
        assert secret not in safe_summary(res)
    assert "ngay_het_han" in safe_summary(res)


def test_plain_string_values_and_json_roundtrip():
    res = to_extraction_result("s2", "HD_MUA_BAN", {"so_hop_dong": "04/2020", "ngay_ky": None})
    assert json.loads(res.model_dump_json())["entity_dict"] == {"so_hop_dong": "04/2020", "ngay_ky": None}
