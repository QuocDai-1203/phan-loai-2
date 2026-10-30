"""T5: mặc định không xuất số định danh/ngày sinh; log và báo cáo không chứa giá trị PII."""
import json
import logging
from pathlib import Path

from schema import pii_policy as P
from schema.build_schema import M, TARGET_TYPES, pii_category, load_taxonomy

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schema"

FIELDS = {"so_gcn": "AB-123456", "ho_ten": "Nguyen Van Secret", "nam_sinh": "15/03/1985", "so_gplx": "790123456789",
          "so_dinh_danh": "079123456789", "ngay_het_han": "2028-01-12", "don_vi_cap": "Cong ty X"}


def test_pii_file_covers_every_pii_looking_field_in_the_whole_taxonomy():
    pii = json.loads((SCHEMA_DIR / "pii_fields.json").read_text(encoding="utf-8"))
    names = {f["name"] for f in pii["fields"]}
    expected = {f["name"] for c in load_taxonomy()["classes"] for f in c.get("key_fields", []) if pii_category(f["name"])}
    assert names == expected
    assert {"so_dinh_danh", "so_gplx", "ngay_sinh", "nam_sinh", "ho_ten"} <= names
    assert pii["config_defaults"]["store_personal_ids"] is False


def test_default_output_drops_ids_and_birth_dates():
    out = P.filter_output(FIELDS)
    assert "nam_sinh" not in out and "so_gplx" not in out and "so_dinh_danh" not in out
    assert out["ngay_het_han"] == "2028-01-12" and out["so_gcn"] == "AB-123456"     # trường hạn/số giấy vẫn còn
    assert out["ho_ten"] == "Nguyen Van Secret"                                      # họ tên: tạm giữ, nhưng không vào log
    on = P.filter_output(FIELDS, store_personal_ids=True)
    assert on["nam_sinh"] == "15/03/1985" and on["so_gplx"] == "790123456789"
    assert "ho_ten" not in P.filter_output(FIELDS, store_personal_names=False)


def test_log_view_redacts_every_pii_value():
    safe = P.redact_for_log(FIELDS)
    text = P.safe_repr(FIELDS)
    for secret in ("Nguyen Van Secret", "15/03/1985", "790123456789", "079123456789"):
        assert secret not in text and secret not in json.dumps(safe)
    assert safe["ho_ten"] == P.REDACTED and safe["ngay_het_han"] == "2028-01-12"
    assert P.redact_for_log({"nam_sinh": None})["nam_sinh"] is None      # trường vắng không bị biến thành [REDACTED]


def test_logging_filter_scrubs_registered_values(caplog):
    logger = logging.getLogger("t4.pii.test")
    flt = P.RedactingFilter()
    flt.register(FIELDS)
    logger.addFilter(flt)
    with caplog.at_level(logging.INFO, logger="t4.pii.test"):
        logger.info("đọc xong, họ tên là %s, sinh %s", FIELDS["ho_ten"], FIELDS["nam_sinh"])
    logger.removeFilter(flt)
    assert "Nguyen Van Secret" not in caplog.text and "15/03/1985" not in caplog.text and P.REDACTED in caplog.text


def test_schema_marks_pii_and_silver_withholds_id_and_birthdate():
    sch = json.loads((SCHEMA_DIR / "CC_TAP_HUAN_VC_HNH.json").read_text(encoding="utf-8"))
    f = {x["name"]: x for x in sch["x-fields"]}
    assert f["nam_sinh"]["is_pii"] and f["nam_sinh"]["silver_policy"] == "withhold_value" and not f["nam_sinh"]["required"]
    assert f["ho_ten"]["is_pii"] and f["ho_ten"]["pii_category"] == "personal_name"
    assert not f["ngay_het_han"]["is_pii"]


def test_no_required_field_is_dropped_by_default_policy():
    """Trường bắt buộc không được là trường mà đầu ra mặc định loại bỏ (nếu không tài liệu không thể 'đúng' cấp tài liệu)."""
    for dt in TARGET_TYPES:
        sch = json.loads((SCHEMA_DIR / f"{dt}.json").read_text(encoding="utf-8"))
        for fld in sch["x-fields"]:
            if fld["required"]:
                assert P.pii_category(fld["name"]) not in P.DROPPED_BY_DEFAULT
