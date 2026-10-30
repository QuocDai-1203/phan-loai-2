"""Kiểm thử logic cascade thuần (không cần mô hình / mạng)."""
import numpy as np

from src.classification.cascade import (POOL, CascadeParams, Signals, run_cascade, selective_counts, tier_shares, tune)


def make_sig():
    # 6 tài liệu: 0 rule; 1 tfidf tự tin; 2 tfidf thấp -> llm tự tin; 3 pool -> llm thấp, đồng thuận với emb; 4 llm trả OTHER; 5 llm thấp
    return Signals(
        rule=["A", "", "", "", "", ""],
        s_label=["A", "B", "B", POOL, POOL, POOL],
        s_conf=np.array([0.9, 0.95, 0.4, 0.8, 0.7, 0.6]),
        llm_label=["A", "B", "B", "C", "OTHER", "D"],
        llm_conf=np.array([0.9, 0.9, 0.8, 0.3, 0.99, 0.2]),
        emb_label=["A", "B", "B", "C", "E", "F"],
        lat_rule=np.full(6, 3.0), lat_s=np.full(6, 2.0), lat_llm=np.full(6, 1000.0), lat_emb=np.full(6, 50.0),
    )


def test_tiers_and_latency():
    r = run_cascade(make_sig(), CascadeParams(th_s=0.9, th_llm=0.7))
    assert list(r["tier"]) == ["rule", "tfidf", "llm", "human", "human", "human"]
    assert list(r["label"][:3]) == ["A", "B", "B"]
    # tài liệu 0 chỉ qua cổng luật; tài liệu 1 qua luật + tfidf; tài liệu 2 qua cả 3 tầng
    assert np.allclose(r["latency_ms"][:3], [3.0, 5.0, 1005.0])


def test_never_auto_other_even_if_confident():
    r = run_cascade(make_sig(), CascadeParams(th_s=0.9, th_llm=0.0))
    assert r["tier"][4] == "human"          # nhãn OTHER không bao giờ tự nhận


def test_agreement_accepts_low_confidence():
    base = CascadeParams(th_s=0.9, th_llm=0.9, agree="emb")
    r = run_cascade(make_sig(), base)
    assert r["tier"][3] == "llm" and r["label"][3] == "C"     # llm thấp (0.3) nhưng đồng thuận với embedding
    r2 = run_cascade(make_sig(), CascadeParams(th_s=0.9, th_llm=0.9, agree="none"))
    assert r2["tier"][3] == "human"


def test_ablation_flags():
    r = run_cascade(make_sig(), CascadeParams(use_rule=False, use_llm=False, th_s=0.5))
    assert list(r["tier"]) == ["tfidf", "tfidf", "human", "human", "human", "human"]
    assert run_cascade(make_sig(), CascadeParams(use_rule=False, use_tfidf=False, use_llm=False))["accepted"].sum() == 0


def test_tune_respects_max_error():
    sig = make_sig()
    y = np.array(["A", "B", "B", "X", "Z", "Q"])        # llm sai ở 3 và 5
    p, st = tune(sig, y, CascadeParams(), 0.0)
    r = run_cascade(sig, p)
    cov, risk, k, err = selective_counts(r["accepted"].to_numpy(), r["label"].to_numpy() == y)
    assert err == 0 and k == st["n_accepted"] and risk <= 0.0
    assert k == 3                                        # luật + tfidf + llm tự tin; hai tài liệu sai bị từ chối
    p2, st2 = tune(sig, y, CascadeParams(), 1.0)
    assert st2["coverage"] >= st["coverage"]


def test_tier_shares_sum_to_one():
    sig = make_sig()
    y = ["A", "B", "B", "C", "OTHER", "D"]
    t = tier_shares(run_cascade(sig, CascadeParams(th_s=0.9, th_llm=0.7)), y)
    assert abs(t["share"].sum() - 1.0) < 1e-9 and t.set_index("tier").loc["rule", "n"] == 1


def test_signals_take():
    s = make_sig().take([1, 3])
    assert s.rule == ["", ""] and s.s_label == ["B", POOL] and len(s) == 2
