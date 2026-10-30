"""evalz.py - Chỉ số Track Z (toàn taxonomy) dùng chung cho thí nghiệm 02. Gói quanh eval_metrics của harness, không tính lại gì khác.

Quy ước (protocol mục 2 và 5): abstain (UNKNOWN) tính là sai trong accuracy/macro-F1; macro-F1 chỉ trên các loại có >= 3 tài liệu thật
trong tập đang chấm; CI = percentile bootstrap 2000 lần theo tài liệu.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from common import POOL, UNKNOWN, Benchmark, bootstrap_metrics, ece, risk_coverage_curve, score_predictions
from eval_metrics import choose_threshold
from src.classification.cascade import NEVER_AUTO


def z_scores(bench: Benchmark, y_true: Sequence[str], y_pred: Sequence[str], boot: bool = True) -> Dict:
    classes = bench.z_classes
    sc = score_predictions(y_true, y_pred, classes, None, min_support=3, abstain_label=UNKNOWN)
    out = dict(n=sc["n"], accuracy=sc["accuracy"], macro_f1=sc["macro_f1"], n_types_scored=sc["n_classes_scored"],
               coverage=sc["coverage"], acc_on_covered=sc["accuracy_on_covered"])
    if boot:
        bm = bootstrap_metrics(y_true, y_pred, classes, min_support=3)
        out.update(accuracy_lo=bm["accuracy"][1], accuracy_hi=bm["accuracy"][2], macro_f1_lo=bm["macro_f1"][1], macro_f1_hi=bm["macro_f1"][2])
    rare = np.array([t in set(bench.pool_types) for t in y_true])
    yt, yp = np.asarray(y_true), np.asarray(y_pred)
    out["n_rare"] = int(rare.sum())
    out["rare_recall"] = float((yt[rare] == yp[rare]).mean()) if rare.any() else float("nan")
    out["freq_recall"] = float((yt[~rare] == yp[~rare]).mean()) if (~rare).any() else float("nan")
    return out


def per_type_recall(bench: Benchmark, y_true: Sequence[str], preds: Dict[str, Sequence[str]], only_rare: bool = True) -> pd.DataFrame:
    """Recall từng loại (giai thoại với loại hiếm: 1-9 tài liệu). preds: {tên phương pháp: nhãn dự đoán}."""
    yt = np.asarray(y_true)
    rows = []
    types = sorted(set(yt), key=lambda t: (-bench.type_counts.get(t, 0), t))
    for t in types:
        if only_rare and t not in set(bench.pool_types):
            continue
        m = yt == t
        row = dict(type=t, n_in_split=int(m.sum()), n_total=bench.type_counts.get(t, 0))
        for k, p in preds.items():
            row[k] = float((np.asarray(p)[m] == t).mean())
        rows.append(row)
    return pd.DataFrame(rows)


def aurc(conf: np.ndarray, correct: np.ndarray) -> float:
    """Area under risk-coverage (thấp hơn tốt hơn): trung bình tỉ lệ sai tích lũy khi nhận dần theo confidence giảm. nan -> thấp nhất."""
    c = np.where(np.isnan(conf), -1.0, conf)
    order = np.argsort(-c, kind="stable")
    err = (~np.asarray(correct, bool))[order].astype(float)
    return float((np.cumsum(err) / np.arange(1, len(err) + 1)).mean())


def calib_scores(conf: np.ndarray, correct: np.ndarray, labels: Sequence[str], dev_tols=(0.01, 0.02)) -> Dict:
    """Chất lượng confidence của một phương pháp: ECE (10 bin), AUROC (phân biệt đúng/sai), AURC, và auto-file rate tại
    ngưỡng chọn ngay trên tập này (DEV; `eligible` = nhãn không thuộc NEVER_AUTO)."""
    conf = np.asarray(conf, float)
    correct = np.asarray(correct, bool)
    has = ~np.isnan(conf)
    out = dict(n=len(conf), conf_available=float(has.mean()))
    out["ece"] = float(ece(conf[has], correct[has].astype(float))) if has.sum() else float("nan")
    try:
        from sklearn.metrics import roc_auc_score

        out["auroc_correct"] = float(roc_auc_score(correct[has], conf[has])) if has.sum() and 0 < correct[has].sum() < has.sum() else float("nan")
    except Exception:
        out["auroc_correct"] = float("nan")
    out["aurc"] = aurc(conf, correct)
    out["mean_conf"] = float(np.nanmean(conf)) if has.any() else float("nan")
    out["accuracy"] = float(correct.mean())
    elig = np.array([l not in NEVER_AUTO and l != POOL for l in labels]) & has
    for tol in dev_tols:
        ch = choose_threshold(np.where(has, conf, -1), correct, elig, tol)
        out[f"autofile_{int(tol * 100)}pct"] = ch["coverage"]
        out[f"threshold_{int(tol * 100)}pct"] = ch["threshold"]
        out[f"errors_{int(tol * 100)}pct"] = ch["errors"]
        out[f"n_accepted_{int(tol * 100)}pct"] = ch["n_accepted"]
    return out
