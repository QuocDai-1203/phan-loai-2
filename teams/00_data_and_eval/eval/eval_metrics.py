"""eval_metrics.py - Chỉ số, khoảng tin cậy bootstrap, risk-coverage cho mọi thí nghiệm phân loại.

Quy ước (xem teams/00_data_and_eval/reports/03_evaluation_protocol.md):
- Nhãn là chuỗi. `classes` là danh sách nhãn hợp lệ của track; nhãn dự đoán ngoài `classes`
  (vd. "UNKNOWN" khi bộ luật abstain) luôn tính là SAI và không có cột trong ma trận nhầm lẫn riêng.
- Macro-F1 = trung bình F1 trên các lớp có support >= `min_support` trong nhãn THẬT của tập đang chấm
  (Track S: min_support=1; Track Z: min_support=3). Lớp chỉ xuất hiện ở phía dự đoán không được tính.
- Bootstrap: percentile, resample theo tài liệu (đơn vị đánh giá), seed cố định -> tái lập.
Chỉ phụ thuộc numpy/pandas để chạy nhanh khi lặp 2000 lần.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

BOOT_N = 2000
BOOT_SEED = 20260711


# ---------------------------------------------------------------------------
# Mã hóa nhãn -> chỉ số
# ---------------------------------------------------------------------------
def encode(y_true: Sequence[str], y_pred: Sequence[str], classes: Sequence[str]) -> Tuple[np.ndarray, np.ndarray]:
    """Nhãn -> chỉ số lớp; nhãn ngoài `classes` -> -1 (luôn sai)."""
    idx = {c: i for i, c in enumerate(classes)}
    t = np.array([idx.get(v, -1) for v in y_true], dtype=np.int64)
    p = np.array([idx.get(v, -1) for v in y_pred], dtype=np.int64)
    return t, p


def _prf_counts(t: np.ndarray, p: np.ndarray, k: int):
    """tp, fp, fn, support theo lớp (nhãn -1 không thuộc lớp nào)."""
    tp = np.bincount(t[(t == p) & (t >= 0)], minlength=k)[:k]
    pred_cnt = np.bincount(p[p >= 0], minlength=k)[:k]
    sup = np.bincount(t[t >= 0], minlength=k)[:k]
    fp = pred_cnt - tp
    fn = sup - tp
    return tp, fp, fn, sup


def _f1_from_counts(tp, fp, fn):
    denom = 2 * tp + fp + fn
    with np.errstate(divide="ignore", invalid="ignore"):
        f1 = np.where(denom > 0, 2 * tp / denom, 0.0)
    return f1


def macro_f1_idx(t: np.ndarray, p: np.ndarray, k: int, min_support: int = 1) -> float:
    tp, fp, fn, sup = _prf_counts(t, p, k)
    keep = sup >= min_support
    if not keep.any():
        return float("nan")
    return float(_f1_from_counts(tp, fp, fn)[keep].mean())


def accuracy_idx(t: np.ndarray, p: np.ndarray) -> float:
    return float(((t == p) & (t >= 0)).mean()) if len(t) else float("nan")


def macro_f1(y_true, y_pred, classes, min_support: int = 1) -> float:
    t, p = encode(y_true, y_pred, classes)
    return macro_f1_idx(t, p, len(classes), min_support)


def accuracy(y_true, y_pred) -> float:
    yt = np.asarray(list(y_true), dtype=object)
    yp = np.asarray(list(y_pred), dtype=object)
    return float((yt == yp).mean()) if len(yt) else float("nan")


# ---------------------------------------------------------------------------
# Hiệu chỉnh xác suất
# ---------------------------------------------------------------------------
def ece(confidence: np.ndarray, correct: np.ndarray, n_bins: int = 10) -> float:
    """Expected Calibration Error (top-label, 10 bin đều)."""
    confidence = np.asarray(confidence, dtype=float)
    correct = np.asarray(correct, dtype=float)
    if len(confidence) == 0:
        return float("nan")
    bins = np.minimum((confidence * n_bins).astype(int), n_bins - 1)
    total = 0.0
    for b in range(n_bins):
        m = bins == b
        if m.any():
            total += m.mean() * abs(correct[m].mean() - confidence[m].mean())
    return float(total)


def brier(proba: np.ndarray, t: np.ndarray) -> float:
    """Brier đa lớp: trung bình theo tài liệu của tổng bình phương sai khác với one-hot (nhãn -1 => bỏ qua)."""
    proba = np.asarray(proba, dtype=float)
    ok = t >= 0
    if not ok.any():
        return float("nan")
    onehot = np.zeros_like(proba[ok])
    onehot[np.arange(ok.sum()), t[ok]] = 1.0
    return float(((proba[ok] - onehot) ** 2).sum(axis=1).mean())


# ---------------------------------------------------------------------------
# Chấm điểm đầy đủ
# ---------------------------------------------------------------------------
def per_class_table(y_true, y_pred, classes, extra_labels: Sequence[str] = ()) -> pd.DataFrame:
    t, p = encode(y_true, y_pred, classes)
    k = len(classes)
    tp, fp, fn, sup = _prf_counts(t, p, k)
    prec = np.where(tp + fp > 0, tp / np.maximum(tp + fp, 1), 0.0)
    rec = np.where(sup > 0, tp / np.maximum(sup, 1), 0.0)
    f1 = _f1_from_counts(tp, fp, fn)
    return pd.DataFrame({"class": list(classes), "precision": prec, "recall": rec, "f1": f1, "support": sup})


def confusion_matrix_df(y_true, y_pred, classes, abstain_label: Optional[str] = None) -> pd.DataFrame:
    """Hàng = thật, cột = dự đoán. Nhãn dự đoán ngoài `classes` gom vào cột `abstain_label` hoặc '<OUT_OF_LABEL_SPACE>'."""
    out_col = abstain_label or "<OUT_OF_LABEL_SPACE>"
    cols = list(classes) + [out_col]
    idx = {c: i for i, c in enumerate(cols)}
    rows = {c: i for i, c in enumerate(classes)}
    m = np.zeros((len(classes), len(cols)), dtype=int)
    for a, b in zip(y_true, y_pred):
        if a not in rows:
            continue
        m[rows[a], idx.get(b, len(cols) - 1)] += 1
    return pd.DataFrame(m, index=list(classes), columns=cols)


def top_confusions(y_true, y_pred, top: int = 10) -> pd.DataFrame:
    from collections import Counter

    c = Counter((a, b) for a, b in zip(y_true, y_pred) if a != b)
    rows = [{"true": a, "predicted": b, "count": n} for (a, b), n in c.most_common(top)]
    return pd.DataFrame(rows, columns=["true", "predicted", "count"])


def score_predictions(
    y_true: Sequence[str],
    y_pred: Sequence[str],
    classes: Sequence[str],
    proba: Optional[np.ndarray] = None,
    min_support: int = 1,
    abstain_label: Optional[str] = None,
) -> Dict:
    """Toàn bộ chỉ số trên một tập: accuracy, macro/weighted-F1, per-class, ECE/Brier (nếu có xác suất), coverage.

    `abstain_label`: nhãn dự đoán nghĩa là "không quyết định" (vd. UNKNOWN); coverage = tỉ lệ không abstain,
    accuracy_on_covered chỉ tính trên phần đó. Khi None: coverage = 1.
    """
    y_true = list(y_true)
    y_pred = list(y_pred)
    t, p = encode(y_true, y_pred, classes)
    k = len(classes)
    n = len(y_true)
    tp, fp, fn, sup = _prf_counts(t, p, k)
    f1 = _f1_from_counts(tp, fp, fn)
    keep = sup >= min_support
    res: Dict = {
        "n": n,
        "accuracy": accuracy_idx(t, p),
        "macro_f1": float(f1[keep].mean()) if keep.any() else float("nan"),
        "weighted_f1": float((f1 * sup).sum() / sup.sum()) if sup.sum() else float("nan"),
        "n_classes_scored": int(keep.sum()),
    }
    if abstain_label is not None:
        cov = np.array([v != abstain_label for v in y_pred])
        res["coverage"] = float(cov.mean()) if n else float("nan")
        res["accuracy_on_covered"] = float((t[cov] == p[cov]).mean()) if cov.any() else float("nan")
    else:
        res["coverage"] = 1.0
        res["accuracy_on_covered"] = res["accuracy"]
    if proba is not None:
        proba = np.asarray(proba, dtype=float)
        conf = proba.max(axis=1)
        res["ece"] = ece(conf, (t == p).astype(float))
        res["brier"] = brier(proba, t)
    else:
        res["ece"] = float("nan")
        res["brier"] = float("nan")
    res["per_class"] = per_class_table(y_true, y_pred, classes)
    return res


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
def _boot_indices(n: int, n_boot: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, n, size=(n_boot, n))


def bootstrap_metrics(
    y_true, y_pred, classes, min_support: int = 1, n_boot: int = BOOT_N, seed: int = BOOT_SEED, alpha: float = 0.05
) -> Dict[str, Tuple[float, float, float]]:
    """Percentile bootstrap 95% CI cho accuracy và macro-F1. Trả về {metric: (điểm, lo, hi)}."""
    t, p = encode(y_true, y_pred, classes)
    k = len(classes)
    n = len(t)
    out = {"accuracy": (accuracy_idx(t, p), np.nan, np.nan), "macro_f1": (macro_f1_idx(t, p, k, min_support), np.nan, np.nan)}
    if n == 0:
        return out
    idx = _boot_indices(n, n_boot, seed)
    acc = np.empty(n_boot)
    mf = np.empty(n_boot)
    for b in range(n_boot):
        tb, pb = t[idx[b]], p[idx[b]]
        acc[b] = accuracy_idx(tb, pb)
        mf[b] = macro_f1_idx(tb, pb, k, min_support)
    q = [100 * alpha / 2, 100 * (1 - alpha / 2)]
    for name, arr in (("accuracy", acc), ("macro_f1", mf)):
        arr = arr[~np.isnan(arr)]
        lo, hi = np.percentile(arr, q) if len(arr) else (np.nan, np.nan)
        out[name] = (out[name][0], float(lo), float(hi))
    return out


def paired_bootstrap(
    y_true, pred_a, pred_b, classes, min_support: int = 1, n_boot: int = BOOT_N, seed: int = BOOT_SEED, alpha: float = 0.05
) -> Dict[str, Dict[str, float]]:
    """Bootstrap ghép cặp (cùng tập tài liệu resample cho cả hai mô hình) cho hiệu A - B.

    p-value hai phía = 2 * min(P(diff <= 0), P(diff >= 0)) (gần đúng, bootstrap); `separable` = CI 95% không chứa 0.
    """
    t, pa = encode(y_true, pred_a, classes)
    _, pb = encode(y_true, pred_b, classes)
    k = len(classes)
    n = len(t)
    idx = _boot_indices(n, n_boot, seed)
    res = {}
    for name, fn in (
        ("accuracy", lambda a, b, c: accuracy_idx(a, b) - accuracy_idx(a, c)),
        ("macro_f1", lambda a, b, c: macro_f1_idx(a, b, k, min_support) - macro_f1_idx(a, c, k, min_support)),
    ):
        diffs = np.array([fn(t[i], pa[i], pb[i]) for i in idx])
        diffs = diffs[~np.isnan(diffs)]
        point = fn(t, pa, pb)
        lo, hi = np.percentile(diffs, [100 * alpha / 2, 100 * (1 - alpha / 2)])
        p_two = min(1.0, 2 * min((diffs <= 0).mean(), (diffs >= 0).mean()))
        res[name] = {
            "diff": float(point),
            "ci_lo": float(lo),
            "ci_hi": float(hi),
            "p_value": float(p_two),
            "separable": bool(lo > 0 or hi < 0),
        }
    return res


def fmt_ci(point: float, lo: float, hi: float, digits: int = 3) -> str:
    if any(np.isnan(v) for v in (point, lo, hi)):
        return f"{point:.{digits}f}" if not np.isnan(point) else "n/a"
    return f"{point:.{digits}f} [{lo:.{digits}f}; {hi:.{digits}f}]"


# ---------------------------------------------------------------------------
# Selective prediction (risk-coverage, auto-file rate)
# ---------------------------------------------------------------------------
def risk_coverage_curve(confidence: np.ndarray, correct: np.ndarray, eligible: Optional[np.ndarray] = None) -> pd.DataFrame:
    """Đường risk-coverage. Mỗi hàng: ngưỡng t (nhận khi conf >= t và eligible), coverage = n_nhận / N (N = TẤT CẢ tài liệu),
    risk = tỉ lệ sai trong số được nhận. `eligible=False` (vd. dự đoán RARE_OR_OTHER) không bao giờ được nhận tự động."""
    confidence = np.asarray(confidence, dtype=float)
    correct = np.asarray(correct, dtype=bool)
    n = len(confidence)
    elig = np.ones(n, dtype=bool) if eligible is None else np.asarray(eligible, dtype=bool)
    rows = []
    for t in sorted(set(confidence[elig].tolist()), reverse=True):
        m = elig & (confidence >= t)
        acc_n = int(m.sum())
        err = int((~correct[m]).sum())
        rows.append({"threshold": t, "n_accepted": acc_n, "coverage": acc_n / n, "errors": err, "risk": err / acc_n})
    return pd.DataFrame(rows, columns=["threshold", "n_accepted", "coverage", "errors", "risk"])


def choose_threshold(confidence, correct, eligible, max_error: float) -> Dict[str, float]:
    """Ngưỡng làm coverage lớn nhất mà tỉ lệ sai trên tập được nhận <= max_error (chọn trên DEV OOF).
    Không khả thi -> threshold=inf, coverage=0."""
    curve = risk_coverage_curve(confidence, correct, eligible)
    ok = curve[curve["risk"] <= max_error + 1e-12]
    if ok.empty:
        return {"threshold": float("inf"), "coverage": 0.0, "risk": float("nan"), "n_accepted": 0, "errors": 0}
    best = ok.sort_values(["coverage", "threshold"], ascending=[False, False]).iloc[0]
    return {k: float(best[k]) for k in ("threshold", "coverage", "risk", "n_accepted", "errors")}


def clopper_pearson_upper(k: int, n: int, alpha: float = 0.05) -> float:
    """Cận trên 1 phía (1 - alpha) chính xác (Clopper-Pearson) cho tỉ lệ sai k/n. Quan trọng khi k = 0: bootstrap cho CI [0, 0]
    (sai lầm), còn cận đúng ~ 3/n ("quy tắc ba")."""
    from scipy.stats import beta

    if n <= 0:
        return float("nan")
    if k >= n:
        return 1.0
    return float(beta.ppf(1 - alpha, k + 1, n - k))


def apply_threshold(
    confidence, correct, eligible, threshold: float, n_boot: int = BOOT_N, seed: int = BOOT_SEED
) -> Dict[str, float]:
    """Áp ngưỡng đã chọn (trên DEV) lên một tập khác (TEST): coverage và risk kèm CI percentile bootstrap."""
    confidence = np.asarray(confidence, dtype=float)
    correct = np.asarray(correct, dtype=bool)
    elig = np.asarray(eligible, dtype=bool)
    n = len(confidence)
    acc_mask = elig & (confidence >= threshold)

    def stats(mask, corr):
        k = mask.sum()
        return mask.mean(), ((~corr[mask]).mean() if k else np.nan)

    cov, risk = stats(acc_mask, correct)
    idx = _boot_indices(n, n_boot, seed)
    covs = np.empty(n_boot)
    risks = np.empty(n_boot)
    for b in range(n_boot):
        covs[b], risks[b] = stats(acc_mask[idx[b]], correct[idx[b]])
    rr = risks[~np.isnan(risks)]
    return {
        "n": int(n),
        "n_accepted": int(acc_mask.sum()),
        "errors": int((~correct[acc_mask]).sum()),
        "coverage": float(cov),
        "coverage_lo": float(np.percentile(covs, 2.5)),
        "coverage_hi": float(np.percentile(covs, 97.5)),
        "risk": float(risk) if not np.isnan(risk) else float("nan"),
        "risk_lo": float(np.percentile(rr, 2.5)) if len(rr) else float("nan"),
        "risk_hi": float(np.percentile(rr, 97.5)) if len(rr) else float("nan"),
        "risk_upper95_exact": clopper_pearson_upper(int((~correct[acc_mask]).sum()), int(acc_mask.sum())),
    }


# ---------------------------------------------------------------------------
# Latency
# ---------------------------------------------------------------------------
def latency_summary(latency_ms: Sequence[float]) -> Dict[str, float]:
    a = np.asarray(list(latency_ms), dtype=float)
    if len(a) == 0:
        return {"median_ms": float("nan"), "p95_ms": float("nan")}
    return {"median_ms": float(np.median(a)), "p95_ms": float(np.percentile(a, 95))}
