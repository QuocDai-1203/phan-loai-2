"""Kiểm thử các tùy chọn an toàn của cascade (T3): đồng thuận hai nguồn, kiểm mẫu ngẫu nhiên, nhật ký quyết định. Mặc định phải tắt."""
import json

import numpy as np
import pytest

from src.classification.cascade import (POOL, CascadeParams, Signals, apply_audit, audit_flags, decision_records, run_cascade, tune)
from tests.test_classif_doc_classifier import FILLER, PARAMS, FakeLlm, answer, make


def sig(**kw):
    base = dict(rule=["", "", ""], s_label=[POOL, "B", POOL], s_conf=np.array([0.0, 0.1, 0.0]),
                llm_label=["A", "B", "C"], llm_conf=np.array([0.9, 0.9, 0.9]))
    base.update(kw)
    return Signals(**base)


def test_consensus_is_off_by_default_and_does_not_change_behaviour():
    assert CascadeParams().consensus == "none"
    r = run_cascade(sig(), CascadeParams(th_s=0.9, th_llm=0.5))
    assert list(r["tier"]) == ["llm", "llm", "llm"]
    assert "consensus" not in CascadeParams().describe()


def test_consensus_llm2_requires_same_label_and_never_auto_label():
    s = sig(llm2_label=["A", "X", "OTHER"])
    r = run_cascade(s, CascadeParams(th_s=0.9, th_llm=0.5, consensus="llm2"))
    assert list(r["tier"]) == ["llm", "human", "human"]


def test_consensus_missing_second_source_accepts_nothing():
    r = run_cascade(sig(), CascadeParams(th_s=0.9, th_llm=0.5, consensus="llm2"))
    assert list(r["tier"]) == ["human"] * 3


def test_consensus_s_needs_tfidf_label_equal_and_not_pool():
    r = run_cascade(sig(), CascadeParams(th_s=0.9, th_llm=0.5, consensus="s"))
    assert list(r["tier"]) == ["human", "llm", "human"]       # chỉ tài liệu 1 có TF-IDF cùng nhãn B (conf thấp nên không tự nhận ở tầng 2)


def test_consensus_s_llm2_is_and_of_both():
    s = sig(llm2_label=["A", "X", "C"])
    r = run_cascade(s, CascadeParams(th_s=0.9, th_llm=0.5, consensus="s_llm2"))
    assert list(r["tier"]) == ["human"] * 3
    s = sig(llm2_label=["A", "B", "C"])
    assert list(run_cascade(s, CascadeParams(th_s=0.9, th_llm=0.5, consensus="s_llm2"))["tier"]) == ["human", "llm", "human"]


def test_consensus_low_confidence_still_blocked_and_invalid_mode_raises():
    s = sig(llm2_label=["A", "B", "C"], llm_conf=np.array([0.1, 0.1, 0.1]))
    assert list(run_cascade(s, CascadeParams(th_s=0.9, th_llm=0.5, consensus="llm2"))["tier"]) == ["human"] * 3
    with pytest.raises(ValueError):
        run_cascade(sig(), CascadeParams(consensus="bogus"))


def test_consensus_survives_take_and_tune():
    s = sig(llm2_label=["A", "B", "X"])
    assert s.take([1, 2]).llm2_label == ["B", "X"]
    y = np.array(["A", "B", "Z"])                        # llm sai ở tài liệu 2 và nguồn thứ hai bất đồng với nó
    p, st = tune(s, y, CascadeParams(consensus="llm2"), 0.0)
    assert p.consensus == "llm2" and st["errors"] == 0 and st["n_accepted"] == 2
    p0, st0 = tune(s, y, CascadeParams(), 0.0)           # không có consensus: phải hy sinh cả tầng LLM để tránh lỗi
    assert st0["n_accepted"] < 2 or st0["errors"] == 0


def test_audit_flags_deterministic_rate_and_order_independent():
    ids = [f"d{i}" for i in range(2000)]
    a = audit_flags(ids, 0.1, seed=3)
    assert np.array_equal(a, audit_flags(ids, 0.1, seed=3))
    assert 0.07 < a.mean() < 0.13
    assert not np.array_equal(a, audit_flags(ids, 0.1, seed=4))
    assert np.array_equal(audit_flags(ids[::-1], 0.1, seed=3), a[::-1])
    assert not audit_flags(ids, 0.0).any() and audit_flags(ids, 1.0).all()
    with pytest.raises(ValueError):
        audit_flags(ids, 1.5)


def test_apply_audit_only_flags_accepted_docs_and_log_has_tier_and_confidence():
    r = run_cascade(sig(), CascadeParams(th_s=0.9, th_llm=0.95))                     # llm_conf 0.9 < 0.95 -> cả ba về người
    out = apply_audit(r, ["a", "b", "c"], 1.0)
    assert not out["audit"].any() and not out["final_accepted"].any()
    r = run_cascade(sig(), CascadeParams(th_s=0.9, th_llm=0.5))
    out = apply_audit(r, ["a", "b", "c"], 1.0)
    assert out["audit"].all() and not out["final_accepted"].any()
    rec = decision_records(out, ["a", "b", "c"], [0.9, 0.9, float("nan")])
    assert rec[0] == dict(id="a", tier="llm", label="A", confidence=0.9, accepted=True, audit=True)
    assert rec[2]["confidence"] is None


def test_classifier_default_has_no_audit_and_no_log(tmp_path):
    clf = make(tmp_path, FakeLlm(answer("HD_MUA_BAN", 0.9)))
    res, tr = clf.classify_text("PHIẾU XUẤT KHO số 5" + FILLER, "s1")
    assert res.requires_human_review is False and res.abstain_reason is None and tr.audit is False
    assert clf.decision_log is None and clf.audit_rate == 0.0


def test_classifier_audit_marks_for_review_keeps_label_and_logs(tmp_path):
    log = tmp_path / "logs" / "decisions.jsonl"
    clf = make(tmp_path, FakeLlm(answer("HD_MUA_BAN", 0.9)))
    clf.audit_rate, clf.audit_seed, clf.decision_log = 1.0, 0, log
    res, tr = clf.classify_text("PHIẾU XUẤT KHO số 5" + FILLER, "s1")
    assert tr.audit and res.requires_human_review and res.abstain_reason == "audit_sample"
    assert res.tier == "rule" and res.predicted_category == "PHIEU_XUAT_KHO"
    res2, _ = clf.classify_text("", "s2")                                           # đã về người: không phải audit
    lines = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]
    assert [x["id"] for x in lines] == ["s1", "s2"]
    assert lines[0]["tier"] == "rule" and lines[0]["accepted"] and lines[0]["audit"]
    assert lines[1]["accepted"] is False and lines[1]["audit"] is False and lines[1]["abstain_reason"] == "empty_text"
    assert "PHIẾU" not in log.read_text(encoding="utf-8")                           # nhật ký không chứa văn bản


def test_classifier_audit_rate_validation(tmp_path):
    clf = make(tmp_path, None)
    from src.classification.doc_classifier import DocumentClassifier
    with pytest.raises(ValueError):
        DocumentClassifier(clf.tfidf, None, clf.config, taxonomy=clf.taxonomy, audit_rate=2.0)


def test_classifier_consensus_llm2_needs_backend_and_requires_agreement(tmp_path):
    from dataclasses import replace
    from src.classification.doc_classifier import CascadeConfig, DocumentClassifier
    base = make(tmp_path, FakeLlm(answer("HD_MUA_BAN", 0.9)))
    params = replace(PARAMS, consensus="llm2")
    cfg = CascadeConfig(params, base.config.source, base.config.t3, 0.01, True, "t.json", "0")
    with pytest.raises(ValueError):
        DocumentClassifier(base.tfidf, base.llm, cfg, taxonomy=base.taxonomy)
    text = "văn bản khác lạ hoàn toàn riêng biệt" + FILLER
    agree = DocumentClassifier(base.tfidf, base.llm, cfg, taxonomy=base.taxonomy, llm2=FakeLlm(answer("HD_MUA_BAN", 0.1)))
    res, tr = agree.classify_text(text, "s1")
    assert res.tier == "llm" and tr.llm2_label == "HD_MUA_BAN"
    split = DocumentClassifier(base.tfidf, base.llm, cfg, taxonomy=base.taxonomy, llm2=FakeLlm(answer("DON_DAT_HANG", 0.9)))
    res, _ = split.classify_text(text, "s1")
    assert res.tier == "human" and res.abstain_reason == "llm_no_consensus" and res.suggested_category == "HD_MUA_BAN"
    err = DocumentClassifier(base.tfidf, base.llm, cfg, taxonomy=base.taxonomy, llm2=FakeLlm(answer("", 0.0, ok=False, error="down")))
    assert err.classify_text(text, "s1")[0].tier == "human"
