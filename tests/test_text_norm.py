"""Kiểm thử bộ chuẩn hóa văn bản dùng chung (src/common/text_norm.py)."""

from src.common.text_norm import NormalizedText, contains_keyword, normalize_text, squash_text


def test_normalize_strips_marks_and_d_bar():
    assert normalize_text("ĐƠN  ĐẶT\nHÀNG") == "don dat hang"
    assert normalize_text(None) == ""


def test_accented_unaccented_and_glued_all_match():
    keyword = "ĐƠN ĐẶT HÀNG"
    assert contains_keyword("ĐƠN ĐẶT HÀNG số 12", keyword)        # có dấu
    assert contains_keyword("DON DAT HANG so 12", keyword)        # mất dấu
    assert contains_keyword("don   dat\nhang", keyword)           # lệch khoảng trắng
    assert contains_keyword("CONG TY DONDATHANG so 12", keyword)  # chữ dính do OCR


def test_non_matching_text_does_not_match():
    assert not contains_keyword("PHIEU XUAT KHO", "ĐƠN ĐẶT HÀNG")


def test_short_keywords_do_not_use_glued_matching():
    # 'dkkd' (4 ký tự) chỉ khớp ở dạng có khoảng trắng, tránh trùng ngẫu nhiên giữa các từ
    assert contains_keyword("giay DKKD", "DKKD")
    assert NormalizedText("ab cd kk dx").match_mode("dkkd") is None


def test_match_mode_distinguishes_exact_and_glued():
    norm = NormalizedText("HỢP ĐỒNG THUÊKHO")
    assert norm.match_mode("hợp đồng") == "exact"
    assert norm.match_mode("hợp đồng thuê kho") == "glued"


def test_squash_removes_spaces_and_punctuation():
    assert squash_text("Ký, ghi rõ họ tên") == "kyghirohoten"
