"""Kiểm thử harness đánh giá (teams/00_data_and_eval/eval): chia dữ liệu không rò rỉ nhóm, TEST bị khóa, chỉ số trên ví dụ nhỏ,
tính tất định, ghi bảng kết quả.

Chạy: .venv\\Scripts\\python.exe -X utf8 -m pytest teams/00_data_and_eval/tests/test_harness.py -q
Các test dùng dữ liệu thật cần data/labels_v2.csv + data/manifest.csv (bị bỏ qua nếu thiếu).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "teams" / "00_data_and_eval" / "eval"))

import eval_metrics as M  # noqa: E402
import eval_splits as S  # noqa: E402
import harness as H  # noqa: E402

HAVE_DATA = H.DEFAULT_LABELS.exists() and H.MANIFEST.exists()
needs_data = pytest.mark.skipif(not HAVE_DATA, reason="thiếu data/labels_v2.csv hoặc manifest.csv")


# ---------------------------------------------------------------- dữ liệu tổng hợp
def toy_frames(n_per_class=20, n_classes=4, group_size=4):
    rows = []
    for c in range(n_classes):
        for i in range(n_per_class):
            did = f"c{c}_{i:03d}"
            tg = f"T{c}_{i // group_size}" if i % 3 != 2 else ""      # 2/3 tài liệu thuộc nhóm biểu mẫu
            rows.append(dict(doc_id=did, doc_type=f"TYPE{c}", template_group=tg))
    reps = pd.DataFrame(rows)
    files = reps.assign(rep_doc_id=reps.doc_id, composite_mixed=False)[["doc_id", "rep_doc_id", "composite_mixed"]]
    return reps, files


def test_splits_no_group_leak_and_disjoint():
    reps, files = toy_frames()
    sp = S.make_splits(reps, files, max_group_size=None)
    assert S.check_no_group_leak(sp) == []
    test_ids = set(sp[sp.split == "TEST"].doc_id)
    dev_ids = set(sp[sp.split == "DEV"].doc_id)
    assert test_ids and dev_ids and not (test_ids & dev_ids)
    assert len(test_ids) + len(dev_ids) == len(reps)
    assert 0.12 <= len(test_ids) / len(reps) <= 0.30
    assert set(sp[sp.split == "DEV"].fold) == {0, 1, 2, 3, 4}
    assert (sp[sp.split == "TEST"].fold == -1).all()


def test_capped_groups_respect_cap():
    reps, files = toy_frames(group_size=10)
    g = S.effective_groups(reps, max_group_size=3)
    assert g.value_counts().max() <= 3
    g2 = S.effective_groups(reps, max_group_size=None)
    assert g2.value_counts().max() > 3


def test_splits_deterministic():
    reps, files = toy_frames()
    a = S.make_splits(reps, files)
    b = S.make_splits(reps.sample(frac=1, random_state=3), files.sample(frac=1, random_state=4))
    pd.testing.assert_frame_equal(a.sort_values("doc_id").reset_index(drop=True), b.sort_values("doc_id").reset_index(drop=True))


def test_duplicates_follow_representative_and_composites_excluded():
    reps, files = toy_frames()
    extra = pd.DataFrame([dict(doc_id="dup_of_c0_000", rep_doc_id="c0_000", composite_mixed=False),
                          dict(doc_id="comp1", rep_doc_id="comp1", composite_mixed=True)])
    files2 = pd.concat([files, extra], ignore_index=True)
    sp = S.make_splits(reps, files2).set_index("doc_id")
    assert sp.loc["dup_of_c0_000", "split"] == sp.loc["c0_000", "split"]
    assert sp.loc["dup_of_c0_000", "fold"] == sp.loc["c0_000", "fold"]
    assert sp.loc["comp1", "split"] == "EXCLUDED_COMPOSITE"


def test_check_no_group_leak_detects_violation():
    reps, files = toy_frames()
    sp = S.make_splits(reps, files)
    bad = sp.copy()
    g = bad[bad.split == "DEV"].group.iloc[0]
    idx = bad[(bad.group == g)].index
    if len(idx) == 1:  # tạo nhóm 2 phần tử rồi đẩy sang TEST
        other = bad[(bad.split == "TEST")].index[0]
        bad.loc[other, "group"] = g
    else:
        bad.loc[idx[0], "split"] = "TEST"
    assert S.check_no_group_leak(bad) != []


def test_naive_split_ignores_groups():
    labels = ["a"] * 20 + ["b"] * 20
    f = S.naive_folds(labels, 5, 0)
    assert sorted(set(f)) == [0, 1, 2, 3, 4]
    assert (np.bincount(f) == 8).all()


# ---------------------------------------------------------------- chỉ số
def test_metrics_toy():
    yt = ["a", "a", "b", "b"]
    yp = ["a", "b", "b", "b"]
    sc = M.score_predictions(yt, yp, ["a", "b", "c"])
    assert sc["accuracy"] == pytest.approx(0.75)
    assert sc["macro_f1"] == pytest.approx((2 / 3 + 0.8) / 2)       # lớp c không có support -> bỏ
    assert sc["weighted_f1"] == pytest.approx((2 / 3 * 2 + 0.8 * 2) / 4)
    pc = sc["per_class"].set_index("class")
    assert pc.loc["a", "recall"] == 0.5 and pc.loc["a", "precision"] == 1.0 and pc.loc["b", "support"] == 2


def test_unknown_prediction_counts_wrong_and_coverage():
    sc = M.score_predictions(["a", "a", "b", "b"], ["a", "UNKNOWN", "b", "b"], ["a", "b"], abstain_label="UNKNOWN")
    assert sc["accuracy"] == pytest.approx(0.75)
    assert sc["coverage"] == pytest.approx(0.75)
    assert sc["accuracy_on_covered"] == pytest.approx(1.0)


def test_min_support_filters_classes():
    yt = ["a"] * 5 + ["b"] * 2
    yp = ["a"] * 5 + ["a", "b"]
    assert M.macro_f1(yt, yp, ["a", "b"], min_support=3) == pytest.approx(M.per_class_table(yt, yp, ["a", "b"]).set_index("class").loc["a", "f1"])


def test_ece_and_brier_toy():
    assert M.ece(np.array([1, 1, .5, .5]), np.array([1, 0, 1, 1])) == pytest.approx(0.5)
    assert M.brier(np.array([[1, 0], [0, 1.0]]), np.array([0, 0])) == pytest.approx(1.0)
    assert M.ece(np.array([1.0, 1.0]), np.array([1, 1])) == 0.0


def test_bootstrap_ci_contains_point_and_is_deterministic():
    rng = np.random.default_rng(0)
    yt = list(rng.choice(["a", "b", "c"], 80))
    yp = [t if rng.random() < 0.8 else "a" for t in yt]
    r1 = M.bootstrap_metrics(yt, yp, ["a", "b", "c"], n_boot=300)
    r2 = M.bootstrap_metrics(yt, yp, ["a", "b", "c"], n_boot=300)
    assert r1 == r2
    for k in ("accuracy", "macro_f1"):
        p, lo, hi = r1[k]
        assert lo <= p <= hi


def test_paired_bootstrap_identical_models_and_clear_winner():
    yt = ["a", "b"] * 40
    good = list(yt)
    bad = ["a"] * 80
    same = M.paired_bootstrap(yt, good, good, ["a", "b"], n_boot=200)
    assert same["accuracy"]["diff"] == 0 and not same["accuracy"]["separable"]
    win = M.paired_bootstrap(yt, good, bad, ["a", "b"], n_boot=200)
    assert win["accuracy"]["separable"] and win["accuracy"]["ci_lo"] > 0 and win["accuracy"]["p_value"] < 0.05


def test_risk_coverage_and_threshold():
    conf = np.array([0.99, 0.95, 0.9, 0.8, 0.6, 0.5])
    correct = np.array([1, 1, 1, 0, 1, 0], dtype=bool)
    elig = np.array([1, 1, 1, 1, 1, 0], dtype=bool)        # tài liệu cuối không đủ điều kiện (vd. dự đoán RARE_OR_OTHER)
    ch = M.choose_threshold(conf, correct, elig, 0.0)
    assert ch["threshold"] == pytest.approx(0.9) and ch["coverage"] == pytest.approx(3 / 6) and ch["risk"] == 0
    ch2 = M.choose_threshold(conf, correct, elig, 0.25)     # nhận 5 tài liệu, 1 sai = 20% <= 25%
    assert ch2["n_accepted"] == 5 and ch2["errors"] == 1 and ch2["threshold"] == pytest.approx(0.6)
    assert M.choose_threshold(conf, ~correct, elig, 0.0)["coverage"] == 0.0     # không khả thi
    ap = M.apply_threshold(conf, correct, elig, 0.9, n_boot=100)
    assert ap["n_accepted"] == 3 and ap["errors"] == 0 and ap["coverage"] == pytest.approx(0.5)


def test_clopper_pearson_upper_rule_of_three():
    assert M.clopper_pearson_upper(0, 38) == pytest.approx(1 - 0.05 ** (1 / 38))      # ~ 3/n
    assert 0.07 < M.clopper_pearson_upper(0, 38) < 0.08
    assert M.clopper_pearson_upper(5, 5) == 1.0
    assert M.clopper_pearson_upper(1, 100) > 0.01


# ---------------------------------------------------------------- bảng kết quả & khóa TEST
def test_append_result_row(tmp_path):
    p = tmp_path / "t.csv"
    base = dict(run_id="r1", method="m", track="S", text_source="x", split="DEV_CV", labels_sha="abc")
    H.append_result_row(dict(base, n=10, accuracy=0.9, macro_f1=float("nan")), p)
    H.append_result_row(dict(base, n=11, accuracy=0.8), p)
    df = pd.read_csv(p)
    assert list(df.columns) == H.RESULT_COLUMNS and len(df) == 2
    assert df.loc[0, "accuracy"] == pytest.approx(0.9) and pd.isna(df.loc[0, "macro_f1"])
    with pytest.raises(KeyError):
        H.append_result_row(dict(method="m"), p)


def test_run_id_unique():
    assert H.new_run_id() != H.new_run_id()


@needs_data
def test_real_benchmark_properties():
    b = H.load_benchmark()
    assert b.dup_conflicts == []
    assert len(b.reps) == len(set(b.reps.doc_id))
    assert not b.reps.composite_mixed.any()
    assert H.POOL in b.s_classes and b.s_classes[-1] == H.POOL
    assert all(b.type_counts[c] >= b.min_docs for c in b.s_classes if c != H.POOL)
    assert all(b.type_counts[t] < b.min_docs for t in b.pool_types)


@needs_data
def test_real_splits_leak_free_and_test_locked(tmp_path):
    b = H.load_benchmark()
    for cap in (H.DEFAULT_MAX_GROUP, None):
        sp = H.build_splits(b, cap)
        assert S.check_no_group_leak(sp) == []
        # mọi file trừ composite có split; bản sao cùng split với đại diện
        m = sp.set_index("doc_id")
        for d, r in m.iterrows():
            if r.split != "EXCLUDED_COMPOSITE":
                assert m.loc[r.rep_doc_id, "split"] == r.split
    # template_group gốc không bị tách (chế độ nghiêm ngặt)
    sp = H.build_splits(b, None)
    reps = b.reps.set_index("doc_id")
    u = sp[(sp.is_rep == 1) & (sp.split != "EXCLUDED_COMPOSITE")].set_index("doc_id")
    u["tg"] = reps.loc[u.index, "template_group"]
    for tg, sub in u[u.tg != ""].groupby("tg"):
        assert sub.split.nunique() == 1


@needs_data
def test_real_test_split_is_locked():
    b = H.load_benchmark()
    sp = H.build_splits(b)
    src = next((s for s in H.TEXT_SOURCES if H.source_available(s)), None)
    if src is None:
        pytest.skip("không có nguồn văn bản")
    with pytest.raises(PermissionError):
        H.load_documents(b, sp, src, "TEST")
    dev = {d.doc_id for d in H.load_documents(b, sp, src, "DEV")}
    test = {d.doc_id for d in H.load_documents(b, sp, src, "TEST", final_test=True)}
    assert dev and test and not (dev & test)
    assert dev | test == set(b.reps.doc_id)


# ---------------------------------------------------------------- tập chia đã khóa
@needs_data
def test_frozen_splits_survive_label_edits_and_refuse_unassigned_docs(tmp_path, monkeypatch):
    import dataclasses
    import warnings

    b = H.load_benchmark()
    monkeypatch.setattr(H, "SPLITS_DIR", tmp_path)
    first = H.load_or_make_splits(b)                       # chưa có -> sinh mới
    stamp = (tmp_path / "splits.csv").read_bytes()

    relabeled = dataclasses.replace(b, labels_sha="0000000000")   # nhãn được sửa, tập tài liệu không đổi
    with pytest.warns(UserWarning, match="giữ nguyên"):
        again = H.load_or_make_splits(relabeled)
    assert (tmp_path / "splits.csv").read_bytes() == stamp
    pd.testing.assert_frame_equal(first, again)

    with warnings.catch_warnings():                         # nhãn không đổi -> không cảnh báo
        warnings.simplefilter("error")
        H.load_or_make_splits(b)

    extra = b.reps.iloc[[0]].assign(doc_id="tai_lieu_moi")  # tài liệu chưa từng được gán DEV/TEST
    grown = dataclasses.replace(b, reps=pd.concat([b.reps, extra]))
    with pytest.raises(H.SplitsOutOfDateError):
        H.load_or_make_splits(grown)
    assert (tmp_path / "splits.csv").read_bytes() == stamp


@needs_data
def test_relabelled_mixed_composite_is_dropped_even_if_frozen_split_says_dev():
    b = H.load_benchmark()
    sp = H.build_splits(b)
    src = next((s for s in H.TEXT_SOURCES if H.source_available(s)), None)
    if src is None:
        pytest.skip("không có nguồn văn bản")
    victim = H.load_documents(b, sp, src, "DEV")[0].doc_id
    files = b.files.copy()
    files.loc[files.doc_id == victim, "composite_mixed"] = True
    import dataclasses
    b2 = dataclasses.replace(b, files=files)
    assert victim not in {d.doc_id for d in H.load_documents(b2, sp, src, "DEV")}
