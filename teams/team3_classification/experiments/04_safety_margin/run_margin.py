"""run_margin.py - Thí nghiệm 04 (T3): hiệu chỉnh độ tin cậy + biên an toàn của cascade. CHỈ DEV; không mở TEST; không gọi mô hình mới.

Đầu vào: results/04_safety_margin/dev_signals.csv (do extract_signals.py tạo; tín hiệu out-of-fold, LLM từ cache của 02).
Đầu ra : results/04_safety_margin/{calibration.csv, risk_coverage.png, margin_ladder.csv, margin_pairwise.csv, audit.csv, summary.json}

  .venv\\Scripts\\python.exe -X utf8 teams\\team3_classification\\experiments\\04_safety_margin\\run_margin.py
"""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.stats import beta  # noqa: E402
from sklearn.isotonic import IsotonicRegression  # noqa: E402

from src.classification.cascade import (NEVER_AUTO, POOL, CascadeParams, Signals, _cascade_arrays, apply_audit, selective_counts, tune)  # noqa: E402

OUT = REPO / "teams" / "team3_classification" / "results" / "04_safety_margin"
rng_boot = 20261015
N_BOOT = 2000
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


# ------------------------------------------------------------------------------------------------ thống kê
def cp_upper(k: int, n: int, alpha: float = 0.05) -> float:
    return float("nan") if n <= 0 else (1.0 if k >= n else float(beta.ppf(1 - alpha, k + 1, n - k)))


def cp_interval(k: int, n: int, alpha: float = 0.05):
    if n <= 0:
        return float("nan"), float("nan")
    lo = 0.0 if k == 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return lo, hi


def ece(conf: np.ndarray, correct: np.ndarray, bins: int = 10) -> float:
    conf, correct = np.asarray(conf, float), np.asarray(correct, float)
    if len(conf) == 0:
        return float("nan")
    idx = np.minimum((conf * bins).astype(int), bins - 1)
    return float(sum(abs(correct[idx == b].mean() - conf[idx == b].mean()) * (idx == b).sum() for b in range(bins) if (idx == b).any()) / len(conf))


def risk_coverage(conf: np.ndarray, correct: np.ndarray):
    order = np.argsort(-conf, kind="stable")
    err = (~np.asarray(correct, bool))[order].astype(float)
    k = np.arange(1, len(err) + 1)
    return k / len(err), np.cumsum(err) / k


def aurc(conf, correct) -> float:
    return float(risk_coverage(np.asarray(conf, float), correct)[1].mean())


# ------------------------------------------------------------------------------------------------ hiệu chỉnh
def _logit(p):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def fit_temperature(conf, correct):
    """Một tham số T: p' = sigmoid(logit(conf) / T), tối thiểu NLL của (đúng/sai) trên lưới T. (Xấp xỉ nhiệt độ cho độ tin cậy lớp-đứng-đầu.)"""
    z, y = _logit(conf), np.asarray(correct, float)
    best, bt = None, 1.0
    for T in np.exp(np.linspace(np.log(0.2), np.log(20), 120)):
        p = np.clip(1 / (1 + np.exp(-z / T)), 1e-9, 1 - 1e-9)
        nll = -(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()
        if best is None or nll < best:
            best, bt = nll, float(T)
    return lambda c, T=bt: 1 / (1 + np.exp(-_logit(c) / T)), bt


def fit_isotonic(conf, correct):
    ir = IsotonicRegression(y_min=0.0, y_max=1.0, increasing=True, out_of_bounds="clip").fit(np.asarray(conf, float), np.asarray(correct, float))
    return lambda c: ir.predict(np.asarray(c, float))


def crossfit_calibrate(conf, correct, folds, method):
    """Hiệu chỉnh out-of-fold: bộ hiệu chỉnh của fold k chỉ học từ các fold khác. conf nan giữ nan."""
    conf = np.asarray(conf, float)
    out = np.full(len(conf), np.nan)
    ok = ~np.isnan(conf)
    for f in sorted(set(folds)):
        tr, te = ok & (folds != f), ok & (folds == f)
        if tr.sum() < 5:
            out[te] = conf[te]
            continue
        fn = fit_temperature(conf[tr], correct[tr])[0] if method == "temperature" else fit_isotonic(conf[tr], correct[tr])
        out[te] = fn(conf[te])
    return out


def boot_ci(fn, n, n_boot=N_BOOT, seed=rng_boot):
    r = np.random.default_rng(seed)
    v = np.array([fn(r.integers(0, n, n)) for _ in range(n_boot)])
    v = v[~np.isnan(v)]
    return float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))


# ------------------------------------------------------------------------------------------------ dữ liệu
def load():
    df = pd.read_csv(OUT / "dev_signals.csv", keep_default_na=False)
    for c in ("s_conf", "q35s1_conf", "q35s2_conf", "q25s1_conf"):
        df[c] = df[c].replace("", np.nan).astype(float)
    return df


def make_signals(df, llm="q35s1", llm2=None, s_conf=None, llm_conf=None):
    return Signals(rule=df["rule"].tolist(), s_label=df["s_label"].tolist(), s_conf=np.asarray(df["s_conf"] if s_conf is None else s_conf, float),
                   llm_label=df[f"{llm}_label"].tolist(), llm_conf=np.asarray(df[f"{llm}_conf"] if llm_conf is None else llm_conf, float),
                   llm2_label=None if llm2 is None else df[f"{llm2}_label"].tolist(),
                   llm2_conf=None if llm2 is None else df[f"{llm2}_conf"].to_numpy(float))


# ------------------------------------------------------------------------------------------------ (1) hiệu chỉnh
def calibration_report(df):
    folds = df["fold"].to_numpy()
    y = df["y"].to_numpy()
    rows, curves = [], {}
    sources = {
        "TF-IDF (OOF, chỉ dự đoán != RARE_OR_OTHER)": (df["s_conf"].to_numpy(float), (df["s_label"] == df["y"]).to_numpy(), (df["s_label"] != POOL).to_numpy()),
        "Qwen3.5-4B 1 bước (q35_s1)": (df["q35s1_conf"].to_numpy(float), (df["q35s1_label"] == df["y"]).to_numpy(), ~df["q35s1_label"].isin(NEVER_AUTO).to_numpy()),
        "Qwen3.5-4B 2 bước (q35_s2)": (df["q35s2_conf"].to_numpy(float), (df["q35s2_label"] == df["y"]).to_numpy(), ~df["q35s2_label"].isin(NEVER_AUTO).to_numpy()),
        "Qwen2.5-3B 1 bước (q25_s1)": (df["q25s1_conf"].to_numpy(float), (df["q25s1_label"] == df["y"]).to_numpy(), ~df["q25s1_label"].isin(NEVER_AUTO).to_numpy()),
    }
    for name, (conf, correct, elig) in sources.items():
        m = elig & ~np.isnan(conf)
        c, ok, fo = conf[m], correct[m], folds[m]
        n, n_err = int(m.sum()), int((~ok).sum())
        _, T = fit_temperature(c, ok)
        variants = {"thô": c, "nhiệt độ (cross-fit)": crossfit_calibrate(c, ok, fo, "temperature"), "isotonic (cross-fit)": crossfit_calibrate(c, ok, fo, "isotonic")}
        for vname, v in variants.items():
            e = ece(v, ok)
            lo, hi = boot_ci(lambda i: ece(v[i], ok[i]), n)
            rows.append(dict(source=name, calibration=vname, n=n, errors=n_err, ece=e, ece_ci_lo=lo, ece_ci_hi=hi, aurc=aurc(v, ok),
                             mean_conf=float(v.mean()), accuracy=float(ok.mean()), T_full=T if vname.startswith("nhiệt") else np.nan,
                             n_distinct=int(len(np.unique(np.round(v, 6))))))
        curves[name] = {k: risk_coverage(v, ok) for k, v in variants.items()}
    return pd.DataFrame(rows), curves


def plot_curves(curves, path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, len(curves), figsize=(4.2 * len(curves), 3.6), sharey=True)
    for ax, (name, cs) in zip(np.atleast_1d(axes), curves.items()):
        for k, (cov, risk) in cs.items():
            ax.step(cov, risk, where="post", label=k, lw=1.6 if k == "thô" else 1.0, alpha=1 if k == "thô" else 0.8)
        ax.set_title(name.split(" (")[0] if "OOF" not in name else "TF-IDF (OOF)", fontsize=9)
        ax.set_xlabel("độ phủ (tỉ lệ tài liệu được nhận)")
        ax.grid(alpha=.3)
    np.atleast_1d(axes)[0].set_ylabel("tỉ lệ sai trên phần được nhận")
    np.atleast_1d(axes)[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


# ------------------------------------------------------------------------------------------------ (4) thang biên
def tune_ub(sig, y, base, bound, agree="none"):
    """Như `tune` nhưng ràng buộc CẬN TRÊN Clopper-Pearson 95% của tỉ lệ sai trên phần được nhận <= bound (cần nhiều mẫu mới nhận được)."""
    from src.classification.cascade import _grid

    y = np.asarray(y)
    best, best_key = None, None
    for ts in _grid(np.asarray(sig.s_conf, float)):
        for tl in _grid(np.asarray(sig.llm_conf, float)):
            p = replace(base, th_s=ts, th_llm=tl, agree=agree)
            label, tier, _ = _cascade_arrays(sig, p)
            cov, risk, k, err = selective_counts(tier != "human", label == y)
            if k == 0 or cp_upper(err, k) > bound + 1e-12:
                continue
            key = (cov, ts if np.isfinite(ts) else 1e9, tl if np.isfinite(tl) else 1e9)
            if best_key is None or key > best_key:
                best_key, best = key, p
    return best if best is not None else replace(base, th_s=float("inf"), th_llm=float("inf"), agree=agree)


def calib_threshold(conf, correct, elig, target):
    """Ngưỡng thô nhỏ nhất sao cho xác suất đã hiệu chỉnh (isotonic, học trên chính tập huấn luyện) >= 1 - target. Không có -> inf."""
    m = elig & ~np.isnan(conf)
    if m.sum() < 5:
        return float("inf")
    fn = fit_isotonic(conf[m], correct[m])
    grid = np.unique(conf[m])
    ok = grid[fn(grid) >= 1 - target - 1e-12]
    return float(ok.min()) if len(ok) else float("inf")


LEVELS = [
    # (id, mô tả, cách chọn tham số trên tập huấn luyện)
    ("L0", "đang dùng: chọn ngưỡng sao cho sai <= 1% trên DEV (như 02)", dict(kind="tune", max_error=0.01)),
    ("L1", "ngưỡng chọn để KHÔNG có lỗi nào trên tập chọn (max_error = 0)", dict(kind="tune", max_error=0.0)),
    ("L2", "ngưỡng theo xác suất đã hiệu chỉnh (isotonic) >= 99% cho TF-IDF và LLM", dict(kind="calib", target=0.01)),
    ("L3", "cận trên Clopper-Pearson của tỉ lệ sai trên tập chọn <= 5%", dict(kind="ub", bound=0.05)),
    ("L4", "cận trên Clopper-Pearson của tỉ lệ sai trên tập chọn <= 2%", dict(kind="ub", bound=0.02)),
    ("C1", "L1 + LLM chỉ nhận khi q35_s2 (cùng mô hình, prompt hai bước) CÙNG nhãn", dict(kind="tune", max_error=0.0, consensus="llm2", llm2="q35s2")),
    ("C2", "L1 + LLM chỉ nhận khi q25_s1 (mô hình khác: Qwen2.5-3B) CÙNG nhãn", dict(kind="tune", max_error=0.0, consensus="llm2", llm2="q25s1")),
    ("C3", "L1 + LLM chỉ nhận khi TF-IDF cùng nhãn (hai mô hình khác họ)", dict(kind="tune", max_error=0.0, consensus="s")),
    ("C4", "L1 + LLM chỉ nhận khi TF-IDF VÀ q35_s2 cùng nhãn", dict(kind="tune", max_error=0.0, consensus="s_llm2", llm2="q35s2")),
]


def fit_level(df_tr, spec):
    """Chọn tham số cascade trên df_tr (các fold huấn luyện). Trả (CascadeParams, llm2 hoặc None)."""
    llm2 = spec.get("llm2")
    sig = make_signals(df_tr, llm2=llm2)
    base = CascadeParams(consensus=spec.get("consensus", "none"))
    y = df_tr["y"].to_numpy()
    if spec["kind"] == "tune":
        p, _ = tune(sig, y, base, spec["max_error"])
    elif spec["kind"] == "ub":
        p = tune_ub(sig, y, base, spec["bound"])
    else:
        s_c = df_tr["s_conf"].to_numpy(float)
        ts = calib_threshold(s_c, (df_tr["s_label"] == df_tr["y"]).to_numpy(), (df_tr["s_label"] != POOL).to_numpy(), spec["target"])
        l_c = df_tr["q35s1_conf"].to_numpy(float)
        tl = calib_threshold(l_c, (df_tr["q35s1_label"] == df_tr["y"]).to_numpy(), ~df_tr["q35s1_label"].isin(NEVER_AUTO).to_numpy(), spec["target"])
        p = replace(base, th_s=ts, th_llm=tl)
    return p, llm2


def run_level(df_eval, p, llm2):
    sig = make_signals(df_eval, llm2=llm2)
    label, tier, _ = _cascade_arrays(sig, p)
    return label, tier


def ladder(df):
    folds = df["fold"].to_numpy()
    y = df["y"].to_numpy()
    rows, accepted_cf, errors_cf = [], {}, {}
    for lid, desc, spec in LEVELS:
        # (a) chọn-và-chấm trên cùng DEV (lạc quan)
        p_all, l2 = fit_level(df, spec)
        lab, tier = run_level(df, p_all, l2)
        acc = tier != "human"
        k, err = int(acc.sum()), int((lab[acc] != y[acc]).sum())
        # (b) cross-fit: chọn trên 4 fold, chấm fold còn lại
        acc_cf, err_cf, tier_cf, params_cf = np.zeros(len(df), bool), np.zeros(len(df), bool), np.full(len(df), "", dtype=object), []
        for f in sorted(set(folds)):
            tr, te = folds != f, folds == f
            p, l2f = fit_level(df[tr].reset_index(drop=True), spec)
            lab_f, tier_f = run_level(df[te].reset_index(drop=True), p, l2f)
            acc_cf[te] = tier_f != "human"
            err_cf[te] = (tier_f != "human") & (lab_f != y[te])
            tier_cf[te] = tier_f
            params_cf.append(p.describe())
        kc, ec = int(acc_cf.sum()), int(err_cf.sum())
        accepted_cf[lid], errors_cf[lid] = acc_cf, err_cf
        lo, hi = cp_interval(kc, len(df))
        rows.append(dict(level=lid, mo_ta=desc, resub_nhan=k, resub_sai=err, resub_cov=k / len(df), resub_cp_upper=cp_upper(err, k),
                         cf_nhan=kc, cf_sai=ec, cf_cov=kc / len(df), cf_cov_cp_lo=lo, cf_cov_cp_hi=hi, cf_cp_upper=cp_upper(ec, kc),
                         cf_rule=int((tier_cf == "rule").sum()), cf_tfidf=int((tier_cf == "tfidf").sum()), cf_llm=int((tier_cf == "llm").sum()),
                         cf_human=int((tier_cf == "human").sum()), params_full=p_all.describe(), params_per_fold=" | ".join(params_cf)))
    return pd.DataFrame(rows), accepted_cf, errors_cf


def pairwise(accepted_cf, errors_cf, n):
    base_a, base_e = accepted_cf["L0"], errors_cf["L0"]
    rows = []
    r = np.random.default_rng(rng_boot)
    idx = r.integers(0, n, (N_BOOT, n))
    for lid in accepted_cf:
        if lid == "L0":
            continue
        da = accepted_cf[lid].astype(float) - base_a.astype(float)
        de = errors_cf[lid].astype(float) - base_e.astype(float)
        ca, ce = da[idx].mean(axis=1), de[idx].mean(axis=1)
        rows.append(dict(level=lid, d_cov=float(da.mean()), d_cov_lo=float(np.percentile(ca, 2.5)), d_cov_hi=float(np.percentile(ca, 97.5)),
                         d_err=float(de.mean()), d_err_lo=float(np.percentile(ce, 2.5)), d_err_hi=float(np.percentile(ce, 97.5)),
                         cov_separable=bool(np.percentile(ca, 2.5) > 0 or np.percentile(ca, 97.5) < 0)))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------ kiểm mẫu ngẫu nhiên
def audit_report(df, accepted_cf, errors_cf, level="L1", rates=(0.0, 0.05, 0.10), n_seeds=200):
    """Hiệu quả của kiểm mẫu ngẫu nhiên trên phần tự nhận (cross-fit) của một mức: cỡ mẫu kiểm, số lỗi bắt được, lỗi còn lọt, chi phí người."""
    acc, err = accepted_cf[level], errors_cf[level]
    ids = df["doc_id"].tolist()
    rows = []
    for rate in rates:
        k_final, caught, residual, audited = [], [], [], []
        for seed in range(n_seeds):
            res = pd.DataFrame({"tier": np.where(acc, "x", "human"), "label": "", "accepted": acc})
            out = apply_audit(res, ids, rate, seed)
            a = out["audit"].to_numpy()
            audited.append(int(a.sum()))
            caught.append(int((err & a).sum()))
            residual.append(int((err & ~a & acc).sum()))
            k_final.append(int(out["final_accepted"].sum()))
        n_acc = int(acc.sum())
        rows.append(dict(level=level, rate=rate, n_accepted=n_acc, audited_mean=float(np.mean(audited)), final_auto_mean=float(np.mean(k_final)),
                         final_auto_share=float(np.mean(k_final)) / len(df), errors_in_accepted=int(err.sum()), caught_mean=float(np.mean(caught)),
                         residual_mean=float(np.mean(residual)),
                         p_detect_if_1pct_error=float(1 - (1 - rate) ** max(1, round(0.01 * n_acc))) if rate else 0.0,
                         audit_n_to_see_1_error_if_1pct=(float(np.log(0.05) / np.log(0.99)) if rate else float("nan"))))
    return pd.DataFrame(rows)


def main() -> int:
    df = load()
    n = len(df)
    print(f"DEV n={n}; folds={sorted(df['fold'].unique())}")
    cal, curves = calibration_report(df)
    cal.to_csv(OUT / "calibration.csv", index=False)
    plot_curves(curves, OUT / "risk_coverage.png")
    print(cal.round(4).to_string())
    lad, acc_cf, err_cf = ladder(df)
    lad.to_csv(OUT / "margin_ladder.csv", index=False)
    pd.set_option("display.width", 250)
    print(lad.drop(columns=["mo_ta", "params_full", "params_per_fold"]).round(4).to_string())
    pw = pairwise(acc_cf, err_cf, n)
    pw.to_csv(OUT / "margin_pairwise.csv", index=False)
    print(pw.round(4).to_string())
    au = pd.concat([audit_report(df, acc_cf, err_cf, lv) for lv in ("L0", "L1", "C1")])
    au.to_csv(OUT / "audit.csv", index=False)
    print(au.round(3).to_string())
    for lid in ("L0", "L1", "C1", "C2", "C3", "C4"):
        e = err_cf[lid]
        if e.any():
            print(lid, "lỗi cross-fit:", [(df.loc[i, "y"], df.loc[i, "rule"] or "-", df.loc[i, "s_label"], round(df.loc[i, "s_conf"], 3), df.loc[i, "q35s1_label"],
                                            round(df.loc[i, "q35s1_conf"], 3)) for i in np.where(e)[0]])
    (OUT / "summary.json").write_text(json.dumps(dict(n=n, ladder=lad.to_dict("records"), pairwise=pw.to_dict("records")), ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
