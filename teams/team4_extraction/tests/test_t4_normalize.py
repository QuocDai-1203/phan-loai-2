"""Kiểm thử chuẩn hóa ngày/số/mã/văn bản tiếng Việt (eval/normalize.py)."""
import pytest

from eval.normalize import (RAW_PREFIX, extract_tax_codes, find_dates, fold_text, is_raw, normalize_date, normalize_id,
                            normalize_number, normalize_tax_code, normalize_text, normalize_value)


@pytest.mark.parametrize("raw,iso", [
    ("ngày 12 tháng 01 năm 2028", "2028-01-12"),
    ("Có giá trị đến hết ngày 12 tháng 1 năm 2028.", "2028-01-12"),
    ("NGÀY 05 THÁNG 11 NĂM 2024", "2024-11-05"),
    ("12/1/28", "2028-01-12"),
    ("12.1.28", "2028-01-12"),
    ("12-5-24", "2024-05-12"),
    ("12 / 01 / 2028", "2028-01-12"),
    ("2028-01-12", "2028-01-12"),
    ("31/12/1999", "1999-12-31"),
    ("15/03/85", "1985-03-15"),         # năm hai chữ số >= 70 -> 19xx
    ("tháng 01 năm 2028", "2028-01"),
    ("01/2028", "2028-01"),
    ("năm 2028", "2028"),
    ("1985", "1985"),
])
def test_dates(raw, iso):
    assert normalize_date(raw) == iso


def test_impossible_date_is_raw_not_a_date():
    n = normalize_date("31/02/2028")
    assert is_raw(n) and n.startswith(RAW_PREFIX)
    assert normalize_date("ngày … tháng … năm …") .startswith(RAW_PREFIX)


def test_empty_is_none_but_garbage_is_not():
    for blank in (None, "", "   ", "\n"):
        assert normalize_value(blank, "date") is None and normalize_value(blank, "text") is None
    assert normalize_value("abc", "date") is not None   # rác != vắng


def test_find_dates_returns_all_in_order():
    s = "ký ngày 01/02/2025, có giá trị đến hết ngày 12 tháng 01 năm 2028"
    assert [d for d, _ in find_dates(s)] == ["2025-02-01", "2028-01-12"]


@pytest.mark.parametrize("raw,num", [
    ("10.000,5", "10000.5"),
    ("10.000", "10000"),
    ("1.234.567", "1234567"),
    ("5,500", "5.5"),                   # quy ước VN: một dấu phẩy là thập phân
    ("0,25", "0.25"),
    ("10,000.5", "10000.5"),            # kiểu Anh vẫn đọc đúng khi có cả hai dấu
    ("12 345", "12345"),
    ("20.000 lít", "20000"),
    ("15,5 tấn", "15.5"),
    ("-3,0", "-3"),
    ("0.250", "0.25"),
    ("7", "7"),
])
def test_numbers(raw, num):
    assert normalize_number(raw) == num


def test_number_garbage_is_raw():
    assert is_raw(normalize_number("không rõ"))


def test_tax_codes():
    assert normalize_tax_code("MST: 0301234567") == "0301234567"
    assert normalize_tax_code("0301234567-001") == "0301234567001"
    assert normalize_tax_code("03 0123 4567") == "0301234567"
    assert extract_tax_codes("Công ty A, MST 0301234567; Công ty B MST 0312345678-002") == ["0301234567", "0312345678002"]


def test_ids():
    assert normalize_id("Số: 12/HĐ-HH", "document_no") == "12/HD-HH"
    assert normalize_id("số 12 / hđ - hh", "document_no") == "12/HD-HH"
    assert normalize_id("51C-123.45", "plate") == "51C12345"
    assert normalize_id("51c 123 45; 51R-001.23", "plate") == "51C1234551R00123"
    assert normalize_id(" ABC 001 ", "generic") == "ABC001"


def test_text_variants():
    a = normalize_text("  Công   ty TNHH  Hiệp Hòa. ")
    assert a == "công ty tnhh hiệp hòa"
    # NFD và NFC giống nhau
    import unicodedata
    assert normalize_text(unicodedata.normalize("NFD", "Hiệp Hòa")) == normalize_text("Hiệp Hòa")
    # so sánh không dấu là chế độ riêng
    assert normalize_text("Hiệp Hòa") != normalize_text("Hiep Hoa")
    assert normalize_text("Hiệp Hòa", strip_diacritics=True) == normalize_text("Hiep Hoa", strip_diacritics=True) == "hiep hoa"
    assert fold_text("Đường") == "duong"


def test_invalid_type_rejected():
    with pytest.raises(ValueError):
        normalize_value("x", "money")
