"""Báo cáo review 04: chế độ bóng (id, tiebreak), kiểm mẫu theo khóa tệp, tệp bị cắt trang. Không GPU, không mạng."""
import pytest

from src.classification.cascade import audit_flags
from src.classification.doc_classifier import audit_key
from src.pipeline import AUTO_FILE, NEEDS_HUMAN, REASON_ID_BOUNDARY, REASON_TRUNCATED
from tests.test_classif_doc_classifier import FILLER, FakeLlm, answer, make as make_clf
from tests.test_classif_title_tiebreak import ambiguous_text
from tests.test_pipeline import NAN, KeywordClassifier, fake_ocr, make, page, pipe_with


# --------------------------------------------------------------------------------------- T1: khóa kiểm mẫu
@pytest.mark.parametrize("rate,lo,hi", [(0.05, 30, 70), (0.10, 70, 130)])
def test_audit_sampling_rate_over_1000_files_with_slice_000(rate, lo, hi):
    keys = [audit_key(f"sha256-{i:04d}", "slice_000") for i in range(1000)]
    n = int(audit_flags(keys, rate, seed=0).sum())
    assert lo <= n <= hi, n                                   # nhị thức(1000, rate): khoảng ~3 độ lệch chuẩn
    n1 = int(audit_flags(keys, rate, seed=1).sum())
    assert lo <= n1 <= hi, n1


def test_audit_key_depends_on_file_and_slice_and_falls_back_to_text():
    assert audit_key("a", "slice_000") != audit_key("b", "slice_000") != audit_key("b", "slice_001")
    assert audit_key(None, "slice_000", "văn bản 1") != audit_key(None, "slice_000", "văn bản 2")
    assert audit_key(None, "slice_000", "x") == audit_key(None, "slice_000", "x")        # tất định


def test_classifier_audit_uses_file_key(tmp_path):
    clf = make_clf(tmp_path, FakeLlm(answer("HD_MUA_BAN", 0.9)))
    clf.audit_rate = 0.1
    text = "PHIẾU XUẤT KHO số 5" + FILLER
    picked = 0
    for i in range(400):
        clf.set_file_key(f"sha-{i}")
        res, tr = clf.classify_text(text, "slice_000")
        picked += tr.audit
    assert 15 <= picked <= 70, picked                         # trước khi sửa: 0 hoặc 400


# --------------------------------------------------------------------------------------- T2: cắt trang
def test_truncated_file_goes_to_human_with_warning_and_shadow():
    res = make([page(1, "TỰ NHẬN")], ocr=fake_ocr([page(1, "TỰ NHẬN")], total=5)).run("a.pdf")
    assert any("trang 2-5" in w and REASON_TRUNCATED in w for w in res.warnings)
    assert [r.decision for r in res.routing] == [NEEDS_HUMAN] and REASON_TRUNCATED in res.routing[0].reasons
    assert res.file_routing.decision == NEEDS_HUMAN and REASON_TRUNCATED in res.file_routing.reasons
    assert res.file_routing.shadow["truncated_pages"] == [2, 3, 4, 5]
    assert res.extractions == []                              # không trích xuất khi chưa xếp hồ sơ


def test_complete_file_is_not_flagged_as_truncated():
    res = make([page(1, "TỰ NHẬN")]).run("a.pdf")
    assert res.file_routing.decision == AUTO_FILE and "truncated_pages" not in res.file_routing.shadow


# --------------------------------------------------------------------------------------- bóng của quy tắc id
def _force_id(monkeypatch, flags):
    import src.splitting.learned_id as lid
    monkeypatch.setattr(lid, "id_rule_pages", lambda texts: list(flags))


def test_id_rule_shadow_flags_for_review_without_splitting(monkeypatch):
    _force_id(monkeypatch, [False, True])
    res = pipe_with([page(1, "PXK trang 1"), page(2, "PXK bản khác")], [NAN, 0.1]).run("a.pdf")      # preset mặc định model+merge
    assert len(res.split_result.slices) == 1                  # KHÔNG tách
    assert res.file_routing.shadow["id_rule_extra_boundaries"] == [2]
    assert res.routing[0].decision == NEEDS_HUMAN and REASON_ID_BOUNDARY in res.routing[0].reasons
    assert res.routing[0].suggested_category == "PHIEU_XUAT_KHO"
    assert any("quy tắc `id`" in w for w in res.warnings)


def test_id_rule_shadow_silent_when_model_already_splits_or_rule_is_on(monkeypatch):
    _force_id(monkeypatch, [False, True])
    already = pipe_with([page(1, "PXK trang 1"), page(2, "LM bản khác")], [NAN, 0.9]).run("a.pdf")     # mô hình đã tách ở trang 2
    assert len(already.split_result.slices) == 2 and "id_rule_extra_boundaries" not in already.file_routing.shadow
    on = pipe_with([page(1, "PXK trang 1"), page(2, "PXK bản khác")], [NAN, 0.1], policy="model+merge+id").run("a.pdf")
    assert len(on.split_result.slices) == 2 and "id_rule_extra_boundaries" not in on.file_routing.shadow


def test_no_id_flag_means_file_stays_auto(monkeypatch):
    _force_id(monkeypatch, [False, False])
    res = pipe_with([page(1, "PXK trang 1"), page(2, "PXK trang 2")], [NAN, 0.1]).run("a.pdf")
    assert res.file_routing.decision == AUTO_FILE and res.file_routing.shadow == {}


# --------------------------------------------------------------------------------------- bóng của tiebreak
def test_classifier_shadow_title_tiebreak_matches_what_the_option_would_choose(tmp_path):
    clf = make_clf(tmp_path, FakeLlm(answer("HD_MUA_BAN", 0.9)))
    text = ambiguous_text("ĐƠN ĐẶT HÀNG", "hợp đồng mua bán")
    assert clf.shadow_title_tiebreak(text) == "DON_DAT_HANG"
    res_off, _ = clf.classify_text(text, "s1")
    assert res_off.tier != "rule"                             # bóng không đổi quyết định
    clf.rule_title_tiebreak = True
    assert clf.shadow_title_tiebreak(text) is None            # đã bật thì không còn là bóng
    assert make_clf(tmp_path, FakeLlm(answer("HD_MUA_BAN", 0.9))).shadow_title_tiebreak("PHIẾU XUẤT KHO số 5" + FILLER) is None


class ShadowClf(KeywordClassifier):
    def __init__(self, label):
        super().__init__()
        self.label = label

    def shadow_title_tiebreak(self, text):
        return self.label


def test_pipeline_records_tiebreak_shadow_only_when_option_is_off():
    pages = [page(1, "PXK trang 1")]
    off = make(pages, classifier=ShadowClf("BB_LAY_MAU")).run("a.pdf")
    assert off.routing[0].shadow["title_tiebreak_label"] == "BB_LAY_MAU" and off.routing[0].shadow["title_tiebreak_differs"] is True
    assert off.routing[0].category == "PHIEU_XUAT_KHO"        # quyết định giữ nguyên
    on = make(pages, classifier=ShadowClf("BB_LAY_MAU"), title_tiebreak=True).run("a.pdf")
    assert "title_tiebreak_label" not in on.routing[0].shadow
    same = make(pages, classifier=ShadowClf("PHIEU_XUAT_KHO")).run("a.pdf")
    assert same.routing[0].shadow["title_tiebreak_differs"] is False
    none = make(pages, classifier=ShadowClf(None)).run("a.pdf")
    assert "title_tiebreak_label" not in none.routing[0].shadow
