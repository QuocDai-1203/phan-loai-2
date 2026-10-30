"""Kiểm thử DocumentClassifier (luật -> TF-IDF -> LLM -> người) bằng đối tượng giả: không GPU, không mạng, không Ollama/Kev."""

import json

import pytest
import requests

import src.classification.zero_shot as zs
from src.classification import llm_backends as lb
from src.classification.cascade import POOL, CascadeParams
from src.classification.doc_classifier import (DEFAULT_SELECTION_PATH, CascadeConfig, DocumentClassifier, load_cascade_config,
                                               text_for_classification)
from src.classification.llm_cache import DiskCache
from src.classification.taxonomy import load_taxonomy_file
from src.classification.tfidf_classifier import TfidfClassifier
from src.classification.zero_shot import NO_ANSWER, Answer
from src.common.contracts import CLASSIFICATION_TIERS, DocumentSlice, OCRPageResult

TAXONOMY = {"version": "test", "groups": [{"id": "G", "name_vi": "Nhóm", "description": "d"}], "classes": [
    {"id": "PHIEU_XUAT_KHO", "name_vi": "Phiếu xuất kho", "description": "Mô tả rất dài " * 20, "short_description": "ngắn", "group": "G",
     "keywords": ["phiếu xuất kho"]},
    {"id": "DON_DAT_HANG", "name_vi": "Đơn đặt hàng", "description": "d", "short_description": "s", "group": "G", "keywords": ["đơn đặt hàng"]},
    {"id": "HD_MUA_BAN", "name_vi": "Hợp đồng mua bán", "description": "d", "short_description": "s", "group": "G", "keywords": ["hợp đồng mua bán"]},
    {"id": "OTHER", "name_vi": "Khác", "description": "d", "short_description": "s", "group": "G", "keywords": []},
    {"id": "UNREADABLE", "name_vi": "Không đọc được", "description": "d", "short_description": "s", "group": "G", "keywords": []},
]}
FILLER = " nội dung chung của văn bản để đủ dài cho bộ phân loại"
TFIDF_CLASSES = ["PHIEU_XUAT_KHO", "DON_DAT_HANG", POOL]
TEXTS = (["mẫu hàng hóa xăng dầu kho xuất"] * 3 + ["mẫu bên bán đơn mua xăng dầu"] * 3 + ["văn bản khác lạ hoàn toàn riêng biệt"] * 3)
LABELS = ["PHIEU_XUAT_KHO"] * 3 + ["DON_DAT_HANG"] * 3 + [POOL] * 3
PARAMS = CascadeParams(use_rule=True, use_tfidf=True, use_llm=True, th_s=0.6, th_llm=0.5, agree="none")


class FakeLlm:
    tier_name = "llm"
    model_name = "fake-model:1b"

    def __init__(self, answer):
        self.spec = lb.LLM_SPECS[lb.DEFAULT_SPEC_ID]
        self._answer, self.calls = answer, []

    def answer(self, text):
        self.calls.append(text)
        return self._answer


def make(tmp_path, llm=None, params=PARAMS):
    p = tmp_path / "tax.json"
    p.write_text(json.dumps(TAXONOMY, ensure_ascii=False), encoding="utf-8")
    cfg = CascadeConfig(params, "ocr_v2_p12", "q35_s1_short_c2000", 0.01, True, "test.json", "0000000000")
    tfidf = TfidfClassifier(TFIDF_CLASSES).fit(TEXTS, LABELS)
    return DocumentClassifier(tfidf, llm, cfg, taxonomy=load_taxonomy_file(p))


def answer(label, conf=0.9, ok=True, error=""):
    return Answer(label, conf, None, 10.0, ok, error)


def test_rule_tier_accepts_without_calling_tfidf_or_llm(tmp_path):
    llm = FakeLlm(answer("HD_MUA_BAN"))
    res, tr = make(tmp_path, llm).classify_text("PHIẾU XUẤT KHO số 5" + FILLER, "s1")
    assert (res.tier, res.predicted_category, res.model_name) == ("rule", "PHIEU_XUAT_KHO", "keyword_rule_gate")
    assert res.confidence_kind == "heuristic" and res.requires_human_review is False and res.evidence
    assert llm.calls == [] and tr.stages_run == ["rule"]


def test_tfidf_tier_accepts_above_threshold_and_names_the_trained_config(tmp_path):
    llm = FakeLlm(answer("HD_MUA_BAN"))
    res, tr = make(tmp_path, llm).classify_text("mẫu hàng hóa xăng dầu kho xuất" + FILLER, "s1")
    assert res.tier == "tfidf" and res.predicted_category == "PHIEU_XUAT_KHO"
    assert res.model_name == "tfidf_word_cnb_raw_C0.1" and res.confidence_kind == "model" and res.probabilities
    assert llm.calls == [] and tr.stages_run == ["rule", "tfidf"]


def test_pool_label_is_never_auto_filed_by_tfidf_and_falls_to_llm(tmp_path):
    llm = FakeLlm(answer("HD_MUA_BAN", 0.9))
    res, _ = make(tmp_path, llm).classify_text("văn bản khác lạ hoàn toàn riêng biệt" + FILLER, "s1")
    assert res.tier == "llm" and res.predicted_category == "HD_MUA_BAN"
    assert res.model_name == "fake-model:1b" and res.confidence == pytest.approx(0.9) and len(llm.calls) == 1


def test_low_llm_confidence_goes_to_human_with_suggestion_but_no_label(tmp_path):
    llm = FakeLlm(answer("HD_MUA_BAN", 0.2))
    res, _ = make(tmp_path, llm).classify_text("văn bản khác lạ hoàn toàn riêng biệt" + FILLER, "s1")
    assert res.tier == "human" and res.predicted_category == "UNKNOWN" and res.confidence == 0.0
    assert res.requires_human_review is True and res.abstain_reason == "llm_low_confidence"
    assert (res.suggested_category, res.suggestion_source) == ("HD_MUA_BAN", "llm") and res.suggested_confidence == pytest.approx(0.2)
    assert res.error is None


def test_llm_saying_other_is_never_auto_filed_even_when_confident(tmp_path):
    res, _ = make(tmp_path, FakeLlm(answer("OTHER", 0.99))).classify_text("văn bản khác lạ hoàn toàn riêng biệt" + FILLER, "s1")
    assert res.tier == "human" and res.abstain_reason == "llm_other" and res.suggested_category == "OTHER"


def test_llm_error_is_recorded_and_document_goes_to_human_without_silent_label(tmp_path):
    llm = FakeLlm(answer(NO_ANSWER, None, False, "ConnectionError: Ollama tắt"))
    res, tr = make(tmp_path, llm).classify_text("văn bản khác lạ hoàn toàn riêng biệt" + FILLER, "s1")
    assert res.tier == "human" and res.predicted_category == "UNKNOWN" and res.abstain_reason == "llm_error"
    assert "ConnectionError" in res.error and res.requires_human_review is True
    assert res.suggested_category is None            # TF-IDF cũng chỉ ra RARE_OR_OTHER nên không có gợi ý giả
    assert tr.llm_error


def test_llm_error_keeps_tfidf_suggestion_when_tfidf_had_a_real_label(tmp_path):
    llm = FakeLlm(answer(NO_ANSWER, None, False, "HTTP 500"))
    # th_s = 0.99 để TF-IDF không đủ tự tin nhưng vẫn có nhãn gợi ý khác RARE_OR_OTHER
    clf = make(tmp_path, llm, CascadeParams(True, True, True, 0.99, 0.5, "none"))
    res, _ = clf.classify_text("mẫu hàng hóa xăng dầu kho xuất" + FILLER, "s1")
    assert res.tier == "human" and res.abstain_reason == "llm_error"
    assert (res.suggested_category, res.suggestion_source) == ("PHIEU_XUAT_KHO", "tfidf")


def test_llm_disabled_sends_unaccepted_documents_to_human(tmp_path):
    res, _ = make(tmp_path, None).classify_text("văn bản khác lạ hoàn toàn riêng biệt" + FILLER, "s1")
    assert res.tier == "human" and res.abstain_reason == "llm_disabled"


def test_empty_and_too_short_text_never_reach_models(tmp_path):
    llm = FakeLlm(answer("HD_MUA_BAN"))
    clf = make(tmp_path, llm)
    empty, _ = clf.classify_text("   ", "s1", ocr_errors=["Trang 1: lỗi OCR"])
    short, _ = clf.classify_text("ngắn quá", "s2")
    assert empty.abstain_reason == "empty_text" and "lỗi OCR" in empty.error and empty.tier == "human"
    assert short.abstain_reason == "text_too_short" and llm.calls == []


def test_classify_slice_uses_first_two_pages_only(tmp_path):
    pages = [OCRPageResult(page_number=n, width=1, height=1, full_text=t) for n, t in ((3, "ba"), (1, "mot"), (2, "hai"), (4, "bon"))]
    sl = DocumentSlice(slice_id="s", start_page=1, end_page=4, page_count=4, combined_text="TOÀN BỘ", pages=pages)
    assert text_for_classification(sl) == "mot\nhai"
    no_pages = DocumentSlice(slice_id="s", start_page=1, end_page=1, page_count=1, combined_text="chỉ có combined")
    assert text_for_classification(no_pages) == "chỉ có combined"


def test_missing_tfidf_model_is_an_error_at_construction(tmp_path):
    cfg = CascadeConfig(PARAMS, "ocr_v2_p12", "q", 0.01, True, "t", "0")
    with pytest.raises(ValueError, match="TF-IDF"):
        DocumentClassifier(None, None, cfg, taxonomy=load_taxonomy_file(_write(tmp_path)))


def _write(tmp_path):
    p = tmp_path / "tax.json"
    p.write_text(json.dumps(TAXONOMY, ensure_ascii=False), encoding="utf-8")
    return p


def test_tiers_used_are_declared_in_the_contract():
    assert {"rule", "tfidf", "llm", "human", "kev", "none"} == set(CLASSIFICATION_TIERS)


# ---------- cấu hình / ngưỡng ----------
def _selection(tmp_path, agree="none", max_error=0.01):
    sel = {"cascade": {"ocr_v2_p12": {"entries": [{"name": "full[q35_s1_short_c2000]", "max_error": max_error,
                                                  "params": {"use_rule": True, "use_tfidf": True, "use_llm": True, "th_s": 0.3, "th_llm": 0.55, "agree": agree}}]}}}
    p = tmp_path / "sel.json"
    p.write_text(json.dumps(sel), encoding="utf-8")
    return p


def test_load_cascade_config_reads_thresholds_and_records_provenance(tmp_path):
    cfg = load_cascade_config(_selection(tmp_path), "ocr_v2_p12", "q35_s1_short_c2000", 0.01)
    assert (cfg.params.th_s, cfg.params.th_llm, cfg.params.agree) == (0.3, 0.55, "none") and cfg.measured
    assert len(cfg.selection_sha1_10) == 10


def test_embedding_agreement_mode_is_downgraded_and_flagged_not_measured(tmp_path):
    cfg = load_cascade_config(_selection(tmp_path, agree="emb"), "ocr_v2_p12", "q35_s1_short_c2000", 0.01)
    assert cfg.params.agree == "none" and cfg.measured is False and "chặt hơn" in cfg.note


def test_load_cascade_config_missing_entry_is_an_error(tmp_path):
    with pytest.raises(KeyError):
        load_cascade_config(_selection(tmp_path), "ocr_v2_p12", "q35_s1_short_c2000", 0.02)


@pytest.mark.skipif(not DEFAULT_SELECTION_PATH.exists(), reason="chưa có dev_selection_02.json")
def test_real_selection_file_gives_the_thresholds_reported_in_experiment_02():
    cfg = load_cascade_config()
    assert cfg.params.th_s == pytest.approx(0.2820278013328013) and cfg.params.th_llm == pytest.approx(0.5481234671053548)
    assert cfg.params.agree == "none" and cfg.measured and cfg.t3 == "q35_s1_short_c2000"


# ---------- backend thật với HTTP giả ----------
def test_ollama_backend_network_failure_becomes_explicit_error_not_a_label(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise requests.ConnectionError("refused")

    monkeypatch.setattr(zs.requests, "post", boom)
    be = lb.OllamaBackend(lb.LLM_SPECS[lb.DEFAULT_SPEC_ID], TAXONOMY, DiskCache(tmp_path / "c"))
    clf = make(tmp_path, be)
    res, _ = clf.classify_text("văn bản khác lạ hoàn toàn riêng biệt" + FILLER, "s1")
    assert res.tier == "human" and res.abstain_reason == "llm_error" and "ConnectionError" in res.error


def test_ollama_backend_is_cached_on_disk_and_error_records_are_retried(tmp_path, monkeypatch):
    calls = []

    def ok(url, json=None, timeout=None):
        calls.append(1)

        class R:
            status_code = 200

            def json(self_inner):
                return {"message": {"content": '{"type": "HD_MUA_BAN"}'}, "logprobs": None}
        return R()

    monkeypatch.setattr(zs.requests, "post", ok)
    cache = DiskCache(tmp_path / "c")
    be = lb.OllamaBackend(lb.LLM_SPECS[lb.DEFAULT_SPEC_ID], TAXONOMY, cache)
    a1 = be.answer("văn bản khác lạ hoàn toàn riêng biệt" + FILLER)
    a2 = be.answer("văn bản khác lạ hoàn toàn riêng biệt" + FILLER)
    assert a1.label == a2.label == "HD_MUA_BAN" and len(calls) == 1 and cache.hits == 1
    assert be.answer("quá ngắn").parse_ok is False and len(calls) == 1      # < 25 ký tự: không gọi mô hình


def test_kev_backend_uses_name_only_criteria_and_server_model_name(tmp_path, monkeypatch):
    seen = {}

    class R:
        status_code = 200

        def __init__(self, data):
            self._d = data

        def json(self):
            return self._d

        def raise_for_status(self):
            return None

    def post(url, json=None, timeout=None):
        seen["payload"] = json
        return R({"answers": {"q": {"choice": "HD_MUA_BAN", "confidence": 0.5, "probabilities": {"HD_MUA_BAN": 0.7, "DON_DAT_HANG": 0.2}}}})

    monkeypatch.setattr(zs.requests, "post", post)
    monkeypatch.setattr(lb.requests, "get", lambda url, timeout=None: R({"current_model": "jaredpalmer/kev-0.8b"}))
    spec = lb.LLM_SPECS["kev_s1_name_c2000"]
    be = lb.KevBackend(spec, TAXONOMY, DiskCache(tmp_path / "k"))
    assert be.model_name == "jaredpalmer/kev-0.8b"
    clf = make(tmp_path, be, CascadeParams(True, True, True, 0.99, 0.3, "none"))
    res, _ = clf.classify_text("văn bản khác lạ hoàn toàn riêng biệt" + FILLER, "s1")
    assert res.tier == "kev" and res.predicted_category == "HD_MUA_BAN" and res.model_name == "jaredpalmer/kev-0.8b"
    crit = seen["payload"]["questions"]["q"]["criteria"]
    assert crit["HD_MUA_BAN"] == "Hợp đồng mua bán" and "UNREADABLE" not in crit      # tên, không phải mô tả dài


def test_kev_backend_without_status_refuses_to_answer(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise requests.ConnectionError("down")

    monkeypatch.setattr(lb.requests, "get", boom)
    be = lb.KevBackend(lb.LLM_SPECS["kev_s1_name_c2000"], TAXONOMY, DiskCache(tmp_path / "k"))
    a = be.answer("văn bản khác lạ hoàn toàn riêng biệt" + FILLER)
    assert a.parse_ok is False and "Kev không khả dụng" in a.error and be.model_name == "kev-unverified"


def test_unknown_backend_spec_is_an_error():
    with pytest.raises(KeyError):
        lb.make_backend("khong_co", taxonomy_json=TAXONOMY)
