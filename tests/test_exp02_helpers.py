"""Kiểm thử phần thuần của thí nghiệm 02 (evalz, predictor embedding với store giả, chuyển Answer -> Prediction). Không gọi mạng."""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "teams" / "team3_classification" / "experiments" / "02_llm_and_cascade"
for p in (ROOT, ROOT / "teams" / "00_data_and_eval" / "eval", ROOT / "teams" / "team3_classification" / "experiments" / "01_classical_baselines", EXP):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import evalz  # noqa: E402
import predictors as P  # noqa: E402
from harness import Doc  # noqa: E402
from src.classification.zero_shot import Answer  # noqa: E402


def test_aurc_perfect_ranking_is_lower():
    correct = np.array([1, 1, 1, 0, 0], bool)
    good = np.array([0.9, 0.8, 0.7, 0.2, 0.1])
    bad = good[::-1]
    assert evalz.aurc(good, correct) < evalz.aurc(bad, correct)
    assert abs(evalz.aurc(np.array([0.5] * 5), np.ones(5, bool))) < 1e-12


def test_calib_scores_never_auto_and_nan():
    conf = np.array([0.99, 0.95, 0.9, 0.6, np.nan, 0.97])
    correct = np.array([1, 1, 1, 0, 0, 0], bool)
    labels = ["A", "A", "B", "C", "A", "OTHER"]          # OTHER (conf cao, sai) không được tính vào auto-file
    cs = evalz.calib_scores(conf, correct, labels)
    assert cs["conf_available"] == 5 / 6
    assert cs["autofile_1pct"] == 3 / 6 and cs["errors_1pct"] == 0
    assert 0 <= cs["ece"] <= 1 and cs["auroc_correct"] > 0.5


class FakeStore:
    n_chars = 512

    def __init__(self, vecs):
        self.vecs = vecs

    def get(self, docs):
        return np.vstack([self.vecs[d.doc_id] for d in docs])

    def get_texts(self, texts):
        return np.vstack([self.vecs[t] for t in texts])


def mk(doc_id, label, label_s=None):
    return Doc(doc_id=doc_id, file_name=doc_id, relative_path=doc_id, label=label, label_s=label_s or label)


def test_centroid_fewshot_only_classes_with_min_train():
    unit = lambda *v: np.array(v, np.float32) / np.linalg.norm(v)
    vecs = {"a1": unit(1, 0, 0), "a2": unit(1, .1, 0), "b1": unit(0, 1, 0), "b2": unit(0, 1, .1), "c1": unit(0, 0, 1), "q": unit(.9, .2, 0), "qc": unit(0, 0, 1)}
    train = [mk("a1", "A"), mk("a2", "A"), mk("b1", "B"), mk("b2", "B"), mk("c1", "C")]       # C chỉ 1 mẫu -> không có tâm
    classes = ["A", "B", "C"]
    m = P.EmbCentroid(FakeStore(vecs), classes, "Z", min_train=2).fit(train)
    assert m.names == ["A", "B"]
    pr = m.predict([mk("q", "A"), mk("qc", "C")])
    assert pr.labels[0] == "A" and pr.labels[1] in ("A", "B")        # C không thể được dự đoán
    assert np.allclose(pr.proba.sum(axis=1), 1.0) and pr.proba[:, 2].sum() == 0


def test_knn_vote_and_lr_shapes():
    unit = lambda *v: np.array(v, np.float32) / np.linalg.norm(v)
    vecs = {f"a{i}": unit(1, .05 * i, 0) for i in range(3)} | {f"b{i}": unit(0, 1, .05 * i) for i in range(3)} | {"q": unit(1, .3, 0)}
    train = [mk(f"a{i}", "A") for i in range(3)] + [mk(f"b{i}", "B") for i in range(3)]
    st = FakeStore(vecs)
    knn = P.EmbKNN(st, ["A", "B"], "Z", k=3).fit(train)
    assert knn.predict([mk("q", "A")]).labels == ["A"]
    lr = P.EmbLR(st, ["A", "B"], 10).fit(train)
    assert lr.predict([mk("q", "A")]).labels == ["A"]


def test_answers_to_prediction_unknown_and_proba():
    ans = [Answer("A", 0.7, {"A": 0.7, "B": 0.3}, 10.0), Answer("NO_ANSWER", None, None, 5.0, False, "x"), Answer("B", 0.6, None, 7.0)]
    pr = P.answers_to_prediction(ans, ["A", "B", "C"])
    assert pr.labels == ["A", "UNKNOWN", "B"]
    assert np.isnan(pr.proba[1]).all() and abs(pr.proba[0].sum() - 1) < 1e-9 and abs(pr.proba[2, 1] - 0.6) < 1e-9
    assert list(pr.latency_ms) == [10.0, 5.0, 7.0]
