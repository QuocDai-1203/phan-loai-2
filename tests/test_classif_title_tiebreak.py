"""Kiểm thử tùy chọn `rule_title_tiebreak` của DocumentClassifier (gỡ thế mơ hồ của cổng luật theo vị trí tiêu đề). Mặc định tắt."""
from src.classification.doc_classifier import DocumentClassifier, resolve_ambiguous_by_title
from tests.test_classif_doc_classifier import FILLER, FakeLlm, answer, make

PAD = " " + "chữ đệm bình thường không phải từ khóa " * 20          # ~ 780 ký tự


def ambiguous_text(title_first: str, mention: str, pad: str = PAD) -> str:
    return f"{title_first} số 5 ngày 1" + pad + f" cột {mention} số lượng" + FILLER


def rules_of(clf: DocumentClassifier):
    return clf.rules._rules


def test_default_off_ambiguous_rule_does_not_decide(tmp_path):
    clf = make(tmp_path, FakeLlm(answer("HD_MUA_BAN", 0.9)))
    assert clf.rule_title_tiebreak is False
    res, tr = clf.classify_text(ambiguous_text("ĐƠN ĐẶT HÀNG", "hợp đồng mua bán"), "s1")
    assert res.tier != "rule" and tr.rule_ambiguous == ["DON_DAT_HANG", "HD_MUA_BAN"] and tr.rule_tiebreak is False


def test_tiebreak_resolves_title_first_class_in_rule_tier(tmp_path):
    clf = make(tmp_path, FakeLlm(answer("HD_MUA_BAN", 0.9)))
    clf.rule_title_tiebreak = True
    res, tr = clf.classify_text(ambiguous_text("ĐƠN ĐẶT HÀNG", "hợp đồng mua bán"), "s1")
    assert (res.tier, res.predicted_category, res.model_name) == ("rule", "DON_DAT_HANG", "keyword_rule_gate")
    assert tr.rule_tiebreak and res.evidence and "HD_MUA_BAN" in res.evidence and res.requires_human_review is False
    assert tr.stages_run == ["rule"]                       # không gọi TF-IDF/LLM


def test_tiebreak_keeps_ambiguous_when_other_class_is_close_or_title_is_late():
    rules = [("A", "tiêu đề a"), ("B", "tiêu đề b")]
    near = "tiêu đề a " + "x" * 100 + " tiêu đề b"                          # B chỉ cách 110 ký tự < 300
    assert resolve_ambiguous_by_title(near, ["A", "B"], rules) is None
    late = "x" * 500 + " tiêu đề a " + "x" * 600 + " tiêu đề b"            # từ khóa sớm nhất nằm ngoài vùng tiêu đề (400)
    assert resolve_ambiguous_by_title(late, ["A", "B"], rules) is None
    ok = "tiêu đề a " + "x" * 400 + " tiêu đề b"
    assert resolve_ambiguous_by_title(ok, ["A", "B"], rules)[0] == "A"
    assert resolve_ambiguous_by_title("tiêu đề a", ["A"], rules) is None    # chỉ một lớp: không phải tình huống mơ hồ


def test_tiebreak_ignores_diacritics_and_only_looks_at_ambiguous_classes():
    rules = [("A", "đơn đặt hàng"), ("B", "hợp đồng mua bán"), ("C", "phiếu xuất kho")]
    t = "DON DAT HANG " + "x" * 450 + " HOP DONG MUA BAN " + "y" * 10 + " PHIEU XUAT KHO"
    assert resolve_ambiguous_by_title(t, ["A", "B"], rules)[0] == "A"       # C không nằm trong danh sách mơ hồ
    assert resolve_ambiguous_by_title(t, ["B", "C"], rules) is None         # B ở 463, C ở 481: không cách đủ 300


def test_tiebreak_does_not_touch_unambiguous_rule_or_tfidf_path(tmp_path):
    clf = make(tmp_path, FakeLlm(answer("HD_MUA_BAN", 0.9)))
    clf.rule_title_tiebreak = True
    res, tr = clf.classify_text("PHIẾU XUẤT KHO số 5" + FILLER, "s1")
    assert res.tier == "rule" and not tr.rule_tiebreak
    res, tr = clf.classify_text("mẫu hàng hóa xăng dầu kho xuất" + FILLER, "s2")
    assert res.tier == "tfidf" and not tr.rule_tiebreak
