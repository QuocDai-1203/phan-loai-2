"""Kiểm thử bộ phân loại đa tầng: trung thực về tầng/model, abstain thay vì mặc định, lỗi Kev được phơi ra."""

import pytest
import requests

from src.classification import system_one_classifier as soc
from src.classification.system_one_classifier import CascadedClassifier
from src.common.contracts import UNKNOWN_CATEGORY, DocumentSlice

NO_TITLE = "noi dung khong co tieu de"
KEV = soc.DEFAULT_KEV_ENDPOINT   # Kev mặc định TẮT: các test về tầng Kev phải bật tường minh


def make_slice(text: str, **kw) -> DocumentSlice:
    return DocumentSlice(slice_id="s1", start_page=1, end_page=1, page_count=1, combined_text=text, **kw)


class FakeResponse:
    def __init__(self, payload=None, status_code=200, bad_json=False):
        self._payload, self.status_code, self._bad_json = payload, status_code, bad_json

    def json(self):
        if self._bad_json:
            raise ValueError("không phải JSON")
        return self._payload


@pytest.fixture
def kev_down(monkeypatch):
    calls = []

    def boom(*a, **k):
        calls.append(1)
        raise requests.ConnectionError("connection refused")

    monkeypatch.setattr(soc.requests, "post", boom)
    return calls


def kev_answer(choice, confidence=0.91):
    cat = {"choice": choice, "confidence": confidence, "probabilities": {choice: confidence}} if choice else {}
    return FakeResponse({"answers": {"category": cat}})


# ---------- Tầng luật ----------
@pytest.mark.parametrize("text,expected", [
    ("ĐƠN ĐẶT HÀNG số 01", "_Đơn đặt hàng - mua vào 2026"),
    ("DON DAT HANG so 01", "_Đơn đặt hàng - mua vào 2026"),
    ("DONDATHANG so 01", "_Đơn đặt hàng - mua vào 2026"),
    ("PHIEU  XUAT\nKHO", "_PHIẾU XUẤT KHO MUA HÀNG 2026"),
])
def test_rule_gate_is_diacritic_and_whitespace_insensitive(text, expected, kev_down):
    res = CascadedClassifier(kev_endpoint=KEV).classify_slice(make_slice(text))
    assert res.predicted_category == expected
    assert res.tier == "rule" and res.model_name == "keyword_rule_gate"
    assert res.confidence_kind == "heuristic" and res.evidence
    assert kev_down == []  # luật quyết định được thì không gọi Kev


def test_rule_with_two_matching_classes_is_ambiguous_not_first_wins(kev_down):
    text = "GIAY DANG KY DOANH NGHIEP kem theo PHIEU XUAT KHO"
    res = CascadedClassifier(kev_endpoint=KEV).classify_slice(make_slice(text))
    assert res.predicted_category == UNKNOWN_CATEGORY
    assert res.abstain_reason == "kev_error"  # Kev không chạy được nên không có ai phân xử
    assert "Luật mơ hồ" in res.evidence


def test_ambiguous_rule_without_kev_abstains():
    res = CascadedClassifier(kev_endpoint=None).classify_slice(
        make_slice("GIAY DANG KY DOANH NGHIEP kem theo PHIEU XUAT KHO"))
    assert res.predicted_category == UNKNOWN_CATEGORY and res.tier == "none"
    assert res.abstain_reason == "rule_ambiguous" and res.error is None   # Kev tắt: không có "lỗi Kev" giả


def test_kev_is_off_by_default_and_makes_no_http_call(kev_down):
    res = CascadedClassifier().classify_slice(make_slice(NO_TITLE))
    assert kev_down == [] and res.tier == "none" and res.abstain_reason == "no_rule_match" and res.error is None


def test_two_pccc_classes_share_text_so_rule_gate_reports_ambiguity():
    clf = CascadedClassifier(kev_endpoint=None)
    match = clf.match_rules("BIEN BAN TU KIEM TRA PCCC")
    assert match.category is None
    assert set(match.ambiguous) == {"TU K.TRA PCCC- VÂN", "8. CUA HANG - TU K.TRA PCCC- VÂN"}


# ---------- Abstain ----------
def test_unmatched_text_abstains_instead_of_defaulting_to_hop_dong_kinh_te(kev_down):
    res = CascadedClassifier(kev_endpoint=KEV).classify_slice(make_slice("lorem ipsum dolor sit amet"))
    assert res.predicted_category == UNKNOWN_CATEGORY
    assert res.confidence == 0.0 and res.requires_human_review is True
    assert res.tier == "none" and res.model_name == "none"
    assert res.confidence_kind == "none"


def test_empty_text_abstains_and_carries_ocr_errors():
    res = CascadedClassifier(kev_endpoint=KEV).classify_slice(make_slice("  ", ocr_errors=["Trang 1: RapidOCR không khả dụng"]))
    assert res.abstain_reason == "empty_text" and "RapidOCR" in res.error
    assert res.predicted_category == UNKNOWN_CATEGORY


# ---------- Tầng Kev ----------
def test_kev_failure_is_surfaced_and_never_attributed_to_kev(kev_down, caplog):
    with caplog.at_level("WARNING"):
        res = CascadedClassifier(kev_endpoint=KEV).classify_slice(make_slice(NO_TITLE))
    assert res.model_name == "none" and res.tier == "none"
    assert res.abstain_reason == "kev_error" and "ConnectionError" in res.error
    assert res.requires_human_review is True
    assert any("Kev" in r.getMessage() for r in caplog.records)


def test_kev_failure_is_not_retried_for_every_document(kev_down):
    clf = CascadedClassifier(kev_endpoint=KEV)
    for _ in range(3):
        res = clf.classify_slice(make_slice(NO_TITLE))
    assert len(kev_down) == 1  # trong thời gian cooldown không chờ timeout lại
    assert "Kev không khả dụng" in res.error  # nhưng vẫn báo lỗi trung thực


def fake_status(model="jaredpalmer/kev-0.8b"):
    return lambda url, timeout=None: FakeResponse({"current_model": model})


def test_kev_success_reports_kev_tier_server_model_and_model_confidence(monkeypatch):
    seen = {}

    def ok(url, json=None, timeout=None):
        seen["payload"] = json
        return kev_answer("_2. HOP DONG KINH TE", 0.93)

    monkeypatch.setattr(soc.requests, "post", ok)
    monkeypatch.setattr(soc.requests, "get", fake_status())
    clf = CascadedClassifier(kev_endpoint=KEV)
    res = clf.classify_slice(make_slice(NO_TITLE))
    assert res.predicted_category == "_2. HOP DONG KINH TE"
    # model_name là mô hình MÁY CHỦ báo, không đặt cứng 'kev-4b'
    assert res.tier == "kev" and res.model_name == "jaredpalmer/kev-0.8b"
    assert res.confidence == pytest.approx(0.93) and res.confidence_kind == "model"
    assert res.requires_human_review is False and res.error is None
    q = seen["payload"]["questions"]["category"]
    assert set(q["criteria"]) == set(clf.taxonomy.class_ids) - set(soc.KEV_EXCLUDE)


def test_kev_criteria_are_names_only_not_long_descriptions(monkeypatch):
    """Thí nghiệm 02 mục 5: mô tả dài làm Kev-0.8B sụp (0,300) còn chỉ-tên đạt 0,962 -> chỉ gửi TÊN loại."""
    clf = CascadedClassifier(kev_endpoint=KEV)
    crit = clf.kev_criteria()
    by_id = {c.id: c for c in clf.taxonomy.classes}
    assert all(crit[i] == (by_id[i].name_vi or i) for i in crit)
    if clf.taxonomy.source != "builtin_legacy_19":
        assert all(crit[i] != by_id[i].description for i in crit if by_id[i].description)
        assert "UNREADABLE" not in crit


def test_kev_model_name_is_flagged_unverified_when_status_unreachable(monkeypatch):
    monkeypatch.setattr(soc.requests, "post", lambda *a, **k: kev_answer("_2. HOP DONG KINH TE", 0.9))

    def boom(*a, **k):
        raise requests.ConnectionError("status down")

    monkeypatch.setattr(soc.requests, "get", boom)
    res = CascadedClassifier(kev_endpoint=KEV).classify_slice(make_slice(NO_TITLE))
    assert res.tier == "kev" and res.model_name == "kev-unverified"


def test_kev_low_confidence_requires_review(monkeypatch):
    monkeypatch.setattr(soc.requests, "get", fake_status())
    monkeypatch.setattr(soc.requests, "post", lambda *a, **k: kev_answer("_2. HOP DONG KINH TE", 0.4))
    res = CascadedClassifier(kev_endpoint=KEV).classify_slice(make_slice(NO_TITLE))
    assert res.tier == "kev" and res.requires_human_review is True


def test_kev_answer_without_choice_abstains_instead_of_defaulting(monkeypatch):
    monkeypatch.setattr(soc.requests, "post", lambda *a, **k: kev_answer(None))
    res = CascadedClassifier(kev_endpoint=KEV).classify_slice(make_slice(NO_TITLE))
    assert res.predicted_category == UNKNOWN_CATEGORY and res.model_name == "none"
    assert "choice" in res.error


def test_kev_choice_outside_taxonomy_is_rejected(monkeypatch):
    monkeypatch.setattr(soc.requests, "post", lambda *a, **k: kev_answer("NHAN_LA"))
    res = CascadedClassifier(kev_endpoint=KEV).classify_slice(make_slice(NO_TITLE))
    assert res.predicted_category == UNKNOWN_CATEGORY and "taxonomy" in res.error


@pytest.mark.parametrize("response", [FakeResponse(status_code=500), FakeResponse(bad_json=True)])
def test_kev_http_error_or_bad_json_is_reported(monkeypatch, response):
    monkeypatch.setattr(soc.requests, "post", lambda *a, **k: response)
    res = CascadedClassifier(kev_endpoint=KEV).classify_slice(make_slice(NO_TITLE))
    assert res.tier == "none" and res.abstain_reason == "kev_error" and res.error


# ---------- Heuristic fallback (opt-in) ----------
def test_heuristic_fallback_is_off_by_default_and_flagged_when_enabled(kev_down):
    # Từ khóa nằm ngoài 1500 ký tự đầu nên cổng luật không thấy, chỉ fallback quét rộng mới thấy
    text = ("x " * 1000) + "HOP DONG MUON BON"
    off = CascadedClassifier(kev_endpoint=KEV).classify_slice(make_slice(text))
    assert off.predicted_category == UNKNOWN_CATEGORY and off.fallback_used is False

    on = CascadedClassifier(kev_endpoint=KEV, allow_heuristic_fallback=True).classify_slice(make_slice(text))
    assert on.predicted_category == "6. HOP DONG MUON BON"
    assert on.fallback_used is True and on.model_name == "keyword_fallback"
    assert on.confidence_kind == "heuristic" and on.requires_human_review is True
    assert "ConnectionError" in on.error  # lỗi Kev vẫn được ghi lại
