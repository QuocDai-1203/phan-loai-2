"""run_all.py - Điểm vào duy nhất của thí nghiệm 01 (baseline cổ điển CPU) cho Nhóm 3.

Chạy (từ thư mục gốc repo):
    .venv\\Scripts\\python.exe -X utf8 teams\\team3_classification\\experiments\\01_classical_baselines\\run_all.py
        [--labels data\\labels_v2.csv] [--jobs 16]            # giai đoạn DEV: mọi bảng, KHÔNG đụng TEST
    .venv\\Scripts\\python.exe -X utf8 teams\\team3_classification\\experiments\\01_classical_baselines\\run_all.py --final-test
                                                              # giai đoạn TEST: chấm các cấu hình đã chốt trên DEV, đúng 1 lần

Giai đoạn DEV: sinh splits (data/splits), CV 5-fold x 3 seed cho mọi cấu hình x mọi nguồn văn bản, ablation, learning curve,
rò rỉ chia ngây thơ, risk-coverage, phân tích lỗi, độ trễ; ghi `dev_selection.json` (cấu hình + ngưỡng đã chốt).
Giai đoạn --final-test chỉ ĐỌC dev_selection.json, huấn luyện lại trên toàn DEV rồi chấm TEST kèm CI bootstrap.
"""

import os

# 1 luồng BLAS/OpenMP: đo độ trễ single-thread và kết quả không phụ thuộc số lõi (phải đặt trước khi import numpy)
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_v] = "1"

import argparse  # noqa: E402
import datetime as dt  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
os.environ["PYTHONPATH"] = os.pathsep.join([str(HERE), str(REPO), str(REPO / "teams" / "00_data_and_eval" / "eval"), os.environ.get("PYTHONPATH", "")])
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from joblib import Parallel, delayed  # noqa: E402

import exp_lib as X  # noqa: E402
from exp_lib import *  # noqa: E402,F401,F403
from harness import *  # noqa: E402,F401,F403
from methods import (RuleGatePredictor, VecCache, build_predictor, build_visual_cache, text_configs,  # noqa: E402
                     visual_configs)

OUT = REPO / "teams" / "team3_classification" / "results" / "01_classical_baselines"
TABLES = OUT / "tables"
FIGS = OUT / "figs"
RESULTS_MD = HERE / "RESULTS.md"

FAMILY_VI = {
    "word_lr": "TF-IDF từ 1-2 + LogisticRegression",
    "char_lr": "TF-IDF ký tự 2-5 + LogisticRegression",
    "char_svc": "TF-IDF ký tự 2-5 + LinearSVC (hiệu chỉnh)",
    "word_cnb": "TF-IDF từ 1-2 + ComplementNB",
}
SOURCE_VI = {
    "legacy_p1": "RapidOCR cũ, trang 1",
    "haiku_p1": "LLM-vision (Haiku), trang 1",
    "haiku_p12": "LLM-vision (Haiku), trang 1-2",
    "ocr_v2_p1": "OCR local v2, trang 1",
    "ocr_v2_p12": "OCR local v2, trang 1-2",
}
LENGTHS = [300, 600, 1000, 2000, None]
KS = [3, 5, 10, 15, None]


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


# ---------------------------------------------------------------------------
# Tiện ích định dạng
# ---------------------------------------------------------------------------
def md_table(df: pd.DataFrame, floatfmt: str = "{:.3f}") -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, (float, np.floating)):
                cells.append("" if np.isnan(v) else floatfmt.format(v))
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def pm(mean, std, d=3):
    return f"{mean:.{d}f} ± {std:.{d}f}" if not np.isnan(std) else f"{mean:.{d}f}"


def update_block(path: Path, name: str, content: str):
    """Thay nội dung giữa <!-- BEGIN:name --> và <!-- END:name --> trong RESULTS.md (nếu tệp và cặp dấu tồn tại)."""
    if not path.exists():
        return
    s = path.read_text(encoding="utf-8")
    b, e = f"<!-- BEGIN:{name} -->", f"<!-- END:{name} -->"
    if b not in s or e not in s:
        return
    i, j = s.index(b) + len(b), s.index(e)
    path.write_text(s[:i] + "\n" + content.strip() + "\n" + s[j:], encoding="utf-8")


def save(df: pd.DataFrame, name: str):
    TABLES.mkdir(parents=True, exist_ok=True)
    df.to_csv(TABLES / f"{name}.csv", index=False, encoding="utf-8")


def to_json(o):
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) or np.isinf(o) else float(o)
    if isinstance(o, float):
        return None if (o != o or o in (float("inf"), float("-inf"))) else o
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(type(o))


def fold_stats(rows, metric):
    v = np.array([r[metric] for r in rows], dtype=float)
    return float(np.nanmean(v)), (float(np.nanstd(v, ddof=1)) if np.isfinite(v).sum() > 1 else float("nan"))


# ---------------------------------------------------------------------------
# GIAI ĐOẠN DEV
# ---------------------------------------------------------------------------
def run_dev(args):
    t_start = time.time()
    ctx = {"labels": str(args.labels), "min_docs": args.min_docs}
    OUT.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(exist_ok=True)
    FIGS.mkdir(exist_ok=True)
    run_id = new_run_id()

    # --- 0. dữ liệu + splits -------------------------------------------------
    bench = load_benchmark(args.labels, args.min_docs)
    # data/splits/* là tập chia đã khóa: mặc định chỉ đọc (sinh mới nếu chưa có); chia lại phải có --rebuild-splits
    splits = load_or_make_splits(bench, rebuild=args.rebuild_splits)
    log("benchmark:", {k: v for k, v in bench.summary().items() if k != "track_s_types"})
    if bench.dup_conflicts:
        log("CẢNH BÁO: nhóm bản sao có nhãn mâu thuẫn:", bench.dup_conflicts)

    sources = [s for s in (args.sources or available_sources()) if s in TEXT_SOURCES and source_available(s)]
    log("nguồn văn bản:", sources)
    primary = "haiku_p12" if "haiku_p12" in sources else sources[0]
    onprem = "ocr_v2_p12" if "ocr_v2_p12" in sources else ("legacy_p1" if "legacy_p1" in sources else sources[0])

    # bảng dữ liệu
    sp_rep = splits[(splits.is_rep == 1) & (splits.split.isin(["DEV", "TEST"]))].set_index("doc_id")
    reps = bench.reps.set_index("doc_id")
    lab_s = reps["doc_type"].map(bench.label_s)
    ds = pd.DataFrame({"label_s": lab_s, "split": sp_rep["split"]}).dropna()
    ds_tab = pd.crosstab(ds.label_s, ds.split).reindex(bench.s_classes).fillna(0).astype(int)
    ds_tab["total"] = ds_tab.sum(axis=1)
    ds_tab = ds_tab.reset_index().rename(columns={"label_s": "class"})
    save(ds_tab, "dataset_track_s")
    ztab = pd.crosstab(reps["doc_type"], sp_rep["split"]).reindex(bench.z_classes).fillna(0).astype(int)
    ztab["total"] = ztab.sum(axis=1)
    save(ztab.reset_index().rename(columns={"doc_type": "type"}), "dataset_track_z")
    summ = bench.summary()
    summ["dev"] = int((ds.split == "DEV").sum())
    summ["test"] = int((ds.split == "TEST").sum())
    summ["labels_sha"] = bench.labels_sha
    (TABLES / "dataset.json").write_text(json.dumps(summ, indent=2, ensure_ascii=False, default=to_json), encoding="utf-8")

    # --- 1. CV mọi cấu hình --------------------------------------------------
    tcfg = text_configs()
    chunks = {}
    for c in tcfg:
        chunks.setdefault((c["vec"], c["fold"]), []).append(c)
    chunk_list = list(chunks.values())
    chunk_list[0] = chunk_list[0] + [dict(family="majority", name="majority")]
    seeds = list(range(args.seeds))
    jobs = []
    for s in sources:
        for seed in seeds:
            for ch in chunk_list:
                jobs.append((s, seed, ch))
    for seed in seeds:
        jobs.append(("image_p1", seed, visual_configs()))
    log(f"CV: {len(jobs)} tác vụ, jobs={args.jobs}")
    # đặt cache ảnh trước (tránh nhiều tiến trình cùng ghi)
    test_like = load_documents(bench, splits, primary, "ALL", include_duplicates=True)
    build_visual_cache(test_like, X.VISUAL_CACHE)

    def run_job(job):
        s, seed, ch = job
        src = primary if s == "image_p1" else s
        return (s, seed, X.cv_task(ctx, src, seed, ch))

    res = Parallel(n_jobs=args.jobs, verbose=0)(delayed(run_job)(j) for j in jobs)
    cv = {}   # (source, config) -> {"rows": [...], "oof": df seed0, "proba", "classes"}
    for s, seed, out in res:
        for name, r in out.items():
            e = cv.setdefault((s, name), {"rows": [], "oof": None, "proba": None, "classes": None})
            e["rows"] += r["fold_scores"]
            if seed == 0:
                e["oof"], e["proba"], e["classes"] = r["oof"], r["proba"], r["classes"]
    log("CV xong", round(time.time() - t_start), "s")

    cfg_by_name = {c["name"]: c for c in tcfg}
    cfg_by_name["majority"] = dict(family="majority", name="majority")
    for c in visual_configs():
        cfg_by_name[c["name"]] = c

    allrows = []
    for (s, name), e in sorted(cv.items()):
        m, sd = fold_stats(e["rows"], "macro_f1")
        a, asd = fold_stats(e["rows"], "accuracy")
        w, _ = fold_stats(e["rows"], "weighted_f1")
        sc = score_predictions(e["oof"]["y_true"], e["oof"]["y_pred"], bench.s_classes, e["proba"] if e["classes"] == bench.s_classes else None)
        cfg = cfg_by_name[name]
        allrows.append(dict(source=s, config=name, family=cfg["family"], fold_diacritics=cfg.get("fold", ""), C=cfg.get("c", ""),
                            macro_f1_mean=m, macro_f1_std=sd, accuracy_mean=a, accuracy_std=asd, weighted_f1_mean=w,
                            n_fold_scores=len(e["rows"]), ece_oof_seed0=sc["ece"], brier_oof_seed0=sc["brier"],
                            macro_f1_oof_seed0=sc["macro_f1"], accuracy_oof_seed0=sc["accuracy"]))
    dev_all = pd.DataFrame(allrows)
    save(dev_all, "dev_all_configs")

    # --- 2. chọn cấu hình tốt nhất (CHỈ dựa trên DEV) ---------------------------
    text_only = dev_all[dev_all.family.isin(FAMILY_VI)]
    best_per = (text_only.sort_values(["macro_f1_mean", "accuracy_mean", "config"], ascending=[False, False, True])
                .groupby(["source", "family", "fold_diacritics"], as_index=False).head(1))
    best_per = best_per.sort_values(["source", "family", "fold_diacritics"])
    save(best_per, "dev_best_C_per_method")
    ranking = {s: text_only[text_only.source == s].sort_values(["macro_f1_mean", "accuracy_mean", "config"], ascending=[False, False, True]) for s in sources}
    top = {s: ranking[s].config.tolist()[:2] for s in sources}
    vis = dev_all[dev_all.source == "image_p1"].sort_values("macro_f1_mean", ascending=False)
    vis_best = vis.config.iloc[0]

    # --- 2b. chênh lệch ghép cặp theo fold giữa các nguồn / giữa văn bản và ảnh (cùng fold => ghép cặp được) ----
    def fold_vec(key):
        return {(r["seed"], r["fold"]): r["macro_f1"] for r in cv[key]["rows"]}

    pairs = []
    ref = (primary, top[primary][0])
    for key, tag in [((s, top[s][0]), f"{primary} vs {s}") for s in sources if s != primary] + [(("image_p1", vis_best), f"{primary} vs ảnh trang 1")]:
        a, b = fold_vec(ref), fold_vec(key)
        ks = sorted(set(a) & set(b))
        d = np.array([a[k] - b[k] for k in ks])
        pairs.append(dict(comparison=tag, A=f"{ref[0]}:{ref[1]}", B=f"{key[0]}:{key[1]}", n_fold_scores=len(d), mean_diff_macro_f1=d.mean(), std_diff=d.std(ddof=1),
                          se_naive=d.std(ddof=1) / np.sqrt(len(d)), folds_A_better=int((d > 0).sum()), folds_tie=int((d == 0).sum()), folds_B_better=int((d < 0).sum())))
    save(pd.DataFrame(pairs), "dev_paired_fold_differences")

    # --- 3. cổng luật --------------------------------------------------------
    rg = Parallel(n_jobs=min(args.jobs, len(sources)))(delayed(X.rule_gate_dev_task)(ctx, s) for s in sources)
    rg_rows = []
    for s, r in zip(sources, rg):
        z = r["rule_gate"]["pooled"]
        mp = r["rule_gate_mapped_to_S"]
        m, sd = fold_stats(mp["fold_scores"], "macro_f1")
        a, asd = fold_stats(mp["fold_scores"], "accuracy")
        rg_rows.append(dict(source=s, z_n=z["n"], z_accuracy=z["accuracy"], z_macro_f1_types_ge3=z["macro_f1"], z_types_scored=z["n_classes_scored"],
                            z_coverage=z["coverage"], z_accuracy_on_covered=z["accuracy_on_covered"],
                            s_macro_f1_mean=m, s_macro_f1_std=sd, s_accuracy_mean=a, s_accuracy_std=asd))
        pd.DataFrame({"doc_id": r["rule_gate"]["doc_ids"], "y_true": r["rule_gate"]["y_true"], "y_pred": r["rule_gate"]["y_pred"]}).to_csv(
            TABLES / f"rule_gate_dev_predictions_{s}.csv", index=False)
        r["rule_gate"]["per_class"].to_csv(TABLES / f"rule_gate_dev_per_class_{s}.csv", index=False)
    rg_df = pd.DataFrame(rg_rows)
    save(rg_df, "rule_gate_dev")

    # --- 4. bảng chính -------------------------------------------------------
    rows = []

    def add_row(label, getter):
        r = {"method": label}
        for s in sources:
            r[s] = getter(s)
        rows.append(r)

    mj = lambda s: pm(*fold_stats(cv[(s, "majority")]["rows"], "macro_f1")) if (s, "majority") in cv else ""
    add_row("majority", mj)
    add_row("rule gate -> Track S (không huấn luyện)", lambda s: pm(float(rg_df[rg_df.source == s].s_macro_f1_mean.iloc[0]), float(rg_df[rg_df.source == s].s_macro_f1_std.iloc[0])))
    for fam in FAMILY_VI:
        for fd in (True, False):
            def g(s, fam=fam, fd=fd):
                b = best_per[(best_per.source == s) & (best_per.family == fam) & (best_per.fold_diacritics == fd)]
                return pm(b.macro_f1_mean.iloc[0], b.macro_f1_std.iloc[0]) + f" (C={b.C.iloc[0]:g})"
            add_row(f"{FAMILY_VI[fam]} [{'bỏ dấu' if fd else 'giữ dấu'}]", g)
    main_dev = pd.DataFrame(rows)
    vrows = []
    for _, v in vis.iterrows():
        vrows.append({"method": f"ảnh trang 1: {v.config}", **{s: (pm(v.macro_f1_mean, v.macro_f1_std) if s == primary else "-") for s in sources}})
    main_dev_full = pd.concat([main_dev, pd.DataFrame(vrows)], ignore_index=True)
    save(main_dev_full, "dev_main_macro_f1")

    # --- 5. ablation: nguồn văn bản ----------------------------------------------
    abl = []
    for s in sources:
        b = ranking[s].iloc[0]
        abl.append(dict(source=s, mo_ta=SOURCE_VI[s], best_config=b.config, macro_f1=pm(b.macro_f1_mean, b.macro_f1_std),
                        accuracy=pm(b.accuracy_mean, b.accuracy_std),
                        rule_gate_acc_Z=float(rg_df[rg_df.source == s].z_accuracy.iloc[0]),
                        rule_gate_coverage=float(rg_df[rg_df.source == s].z_coverage.iloc[0])))
    abl_df = pd.DataFrame(abl)
    save(abl_df, "ablation_text_source")

    # --- 6. ablation: độ dài đầu vào & learning curve & rò rỉ ------------------
    p1_sources = [s for s in ("haiku_p1", "legacy_p1", "ocr_v2_p1") if s in sources]
    cfg_top1 = lambda s: cfg_by_name[top[s][0]]
    len_jobs = [delayed(X.length_task)(ctx, s, cfg_top1(s), LENGTHS, seeds) for s in p1_sources]
    lc_sources = list(dict.fromkeys([primary, onprem]))
    lc_jobs = [delayed(X.learning_curve_task)(ctx, s, cfg_top1(s), KS, [0, 1, 2], cp) for s in lc_sources for cp in (True, False)]
    lk_sources = list(dict.fromkeys([primary, onprem, "legacy_p1" if "legacy_p1" in sources else primary]))
    lk_jobs = [delayed(X.leakage_task)(ctx, s, cfg_top1(s), seeds) for s in lk_sources]
    log("ablation độ dài / learning curve / rò rỉ ...")
    out = Parallel(n_jobs=args.jobs)(len_jobs + lc_jobs + lk_jobs)
    len_rows = sum(out[: len(len_jobs)], [])
    lc_out = out[len(len_jobs): len(len_jobs) + len(lc_jobs)]
    lk_out = out[len(len_jobs) + len(lc_jobs):]
    lk_rows = sum([o["rows"] for o in lk_out], [])
    lk_pc = pd.concat([o["per_class"] for o in lk_out], ignore_index=True)
    save(lk_pc, "leakage_per_class_oof_seed0")

    ldf = pd.DataFrame(len_rows)
    lg = ldf.groupby(["source", "config", "n_chars"], sort=False).agg(macro_f1_mean=("macro_f1", "mean"), macro_f1_std=("macro_f1", "std"),
                                                                      accuracy_mean=("accuracy", "mean")).reset_index()
    save(lg, "ablation_input_length")
    lk = pd.DataFrame(lk_rows)
    lkg = lk.groupby(["source", "scheme"], sort=False).agg(n_docs=("n_docs", "first"), macro_f1_mean=("macro_f1", "mean"), macro_f1_std=("macro_f1", "std"),
                                                           accuracy_mean=("accuracy", "mean")).reset_index()
    save(lkg, "leakage_naive_vs_grouped")

    lc_tabs, lc_rec = [], []
    for o in lc_out:
        r = o["runs"]
        t = r.groupby("k", sort=False).agg(macro_f1_mean=("macro_f1", "mean"), macro_f1_std=("macro_f1", "std"), accuracy_mean=("accuracy", "mean"),
                                           n_runs=("macro_f1", "size"), mean_n_train=("n_train", "mean")).reset_index()
        t.insert(0, "source", o["source"])
        t.insert(1, "variant", o["variant"])
        t.insert(2, "config", o["config"])
        lc_tabs.append(t)
        rc = o["recalls"].groupby(["k", "cls"], sort=False).recall.mean().unstack("k")
        rc = rc[[k for k in ["3", "5", "10", "15", "all"] if k in rc.columns]]
        rc.insert(0, "variant", o["variant"])
        rc.insert(0, "source", o["source"])
        lc_rec.append(rc.reset_index())
    lc_df = pd.concat(lc_tabs, ignore_index=True)
    save(lc_df, "learning_curve")
    lc_rec_df = pd.concat(lc_rec, ignore_index=True)
    save(lc_rec_df, "learning_curve_per_class_recall")

    # --- 7. risk-coverage & auto-file (ngưỡng chốt trên DEV OOF) ----------------
    selective = {}
    sel_rows = []
    curves = {}
    for s in sources:
        selective[s] = {}
        for name in top[s]:
            e = cv[(s, name)]
            oof = e["oof"]
            correct = (oof.y_true == oof.y_pred).to_numpy()
            conf = oof.conf.to_numpy()
            elig = (oof.y_pred != POOL).to_numpy()
            curve = risk_coverage_curve(conf, correct, elig)
            if name == top[s][0]:
                curves[s] = curve
                curve.to_csv(TABLES / f"risk_coverage_dev_{s}.csv", index=False)
            selective[s][name] = {}
            for tag, tol in (("1pct", 0.01), ("2pct", 0.02)):
                ch = choose_threshold(conf, correct, elig, tol)
                selective[s][name][tag] = ch
                if name == top[s][0]:
                    sel_rows.append(dict(source=s, config=name, max_error=tol, threshold=ch["threshold"], dev_auto_file_rate=ch["coverage"],
                                         dev_error_on_accepted=ch["risk"], n_accepted=ch["n_accepted"], errors=ch["errors"],
                                         ceiling_non_pool=float(np.mean(oof.y_true != POOL)), accuracy_all=float(correct.mean())))
    sel_df = pd.DataFrame(sel_rows)
    save(sel_df, "selective_dev")

    # --- 8. phân tích lỗi DEV-OOF -------------------------------------------------
    patt_all = {}
    for s in sources:
        name = top[s][0]
        docs = load_documents(bench, splits, s, "DEV")
        err = X.error_table(cv[(s, name)]["oof"], docs)
        err.to_csv(TABLES / f"errors_dev_oof_{s}.csv", index=False, encoding="utf-8")
        wrong = err[err.correct == 0]
        pat = X.error_patterns(err)
        patt_all[s] = pat
        for k, v in pat.items():
            v.to_csv(TABLES / f"error_patterns_{k}_{s}.csv", index=False)
        cm = confusion_matrix_df(cv[(s, name)]["oof"].y_true, cv[(s, name)]["oof"].y_pred, bench.s_classes)
        cm.to_csv(TABLES / f"confusion_dev_oof_{s}.csv", encoding="utf-8")
        top_conf = top_confusions(cv[(s, name)]["oof"].y_true, cv[(s, name)]["oof"].y_pred, 10)
        top_conf.to_csv(TABLES / f"top_confusions_dev_oof_{s}.csv", index=False)
        sc = score_predictions(cv[(s, name)]["oof"].y_true, cv[(s, name)]["oof"].y_pred, bench.s_classes)
        sc["per_class"].to_csv(TABLES / f"per_class_dev_oof_{s}.csv", index=False)

    # --- 9. độ trễ & kích thước mô hình --------------------------------------------
    log("đo độ trễ (single-thread) ...")
    lat_rows = []
    vcache_dummy = None
    dev_docs_by_src = {}
    for s in sources:
        dev_docs_by_src[s] = load_documents(bench, splits, s, "DEV")
    lat_targets = [("majority", primary, cfg_by_name["majority"]), ("rule_gate_Z", primary, dict(family="rule_gate_Z", name="rule_gate"))]
    for s in sources:
        lat_targets.append((top[s][0], s, cfg_by_name[top[s][0]]))
    lat_targets.append((vis_best, primary, cfg_by_name[vis_best]))
    for label, s, cfg in lat_targets:
        docs = dev_docs_by_src[s]
        p = build_predictor(cfg, bench.s_classes, None, None)   # KHÔNG dùng cache -> đo cả trích đặc trưng
        t0 = time.perf_counter()
        p.fit(docs)
        fit_s = time.perf_counter() - t0
        sample = docs[:80]
        p.predict(sample[:3])   # khởi động
        lat = time_single_doc(p, sample)
        ls = latency_summary(lat)
        lat_rows.append(dict(config=label, source=("image_p1" if cfg["family"] == "visual" else s), fit_seconds_full_dev=fit_s,
                             latency_ms_median=ls["median_ms"], latency_ms_p95=ls["p95_ms"], n_timed=len(sample),
                             model_size_kb=p.size_bytes() / 1024.0))
    lat_df = pd.DataFrame(lat_rows)
    save(lat_df, "latency_and_size")

    # --- 10. chốt cấu hình cho TEST + biểu đồ + bảng chung -------------------------
    selection = {
        "labels_file": str(Path(args.labels)), "labels_sha": bench.labels_sha, "min_docs": args.min_docs, "run_id": run_id,
        "created": dt.datetime.now().isoformat(timespec="seconds"), "sources": sources, "primary_source": primary, "onprem_source": onprem,
        "final_configs": top, "visual_best": vis_best, "selective": selective,
        "seeds": seeds, "note": "Chọn hoàn toàn từ CV trên DEV (macro-F1 trung bình trên 3 seed x 5 fold).",
    }
    (TABLES / "dev_selection.json").write_text(json.dumps(selection, indent=2, ensure_ascii=False, default=to_json), encoding="utf-8")
    make_figures(curves, lc_df, lg, sources, top)

    if not args.no_results_table:
        for _, r in dev_all.iterrows():
            if r.source != "image_p1" and r.config not in top.get(r.source, []) and r.config != "majority":
                continue
            if args.results_sources and r.source not in args.results_sources:
                continue
            lt = lat_df[(lat_df.config == r.config)]
            append_result_row(dict(run_id=run_id, method=r.config, track="S", text_source=r.source, split="DEV_CV", n=int(bench_dev_n(ds)),
                                   accuracy=r.accuracy_mean, macro_f1=r.macro_f1_mean, macro_f1_std=r.macro_f1_std,
                                   latency_ms_median=(lt.latency_ms_median.iloc[0] if len(lt) else ""), latency_ms_p95=(lt.latency_ms_p95.iloc[0] if len(lt) else ""),
                                   labels_file=Path(args.labels).name, labels_sha=bench.labels_sha,
                                   notes="mean±std over 3 seeds x 5 folds; DEV only"))
        for _, r in rg_df.iterrows():
            if args.results_sources and r.source not in args.results_sources:
                continue
            append_result_row(dict(run_id=run_id, method="rule_gate", track="Z", text_source=r.source, split="DEV_ALL", n=int(r.z_n),
                                   accuracy=r.z_accuracy, macro_f1=r.z_macro_f1_types_ge3, coverage=r.z_coverage, acc_on_covered=r.z_accuracy_on_covered,
                                   labels_file=Path(args.labels).name, labels_sha=bench.labels_sha, notes=f"macro-F1 over {int(r.z_types_scored)} types with >=3 docs; Kev off"))
    render_dev_markdown(bench, ds_tab, summ, sources, primary, onprem, main_dev_full, abl_df, lg, lc_df, lc_rec_df, lkg, sel_df, rg_df, lat_df, patt_all, top, dev_all)
    log(f"DEV xong trong {time.time() - t_start:.0f}s. Cấu hình chốt:", {s: top[s][0] for s in sources})


def bench_dev_n(ds):
    return (ds.split == "DEV").sum()


# ---------------------------------------------------------------------------
# Biểu đồ
# ---------------------------------------------------------------------------
def make_figures(curves, lc_df, lg, sources, top):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = ["#1f77b4", "#d95f02", "#1b9e77", "#7570b3", "#e7298a"]
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    for i, (s, c) in enumerate(curves.items()):
        ax.plot(c.coverage, c.risk, label=SOURCE_VI.get(s, s), color=colors[i % 5], lw=1.6)
    for y in (0.01, 0.02):
        ax.axhline(y, color="#888", ls="--", lw=0.8)
    ax.set_xlabel("Tỉ lệ tự động xử lý (coverage, trên mọi tài liệu)")
    ax.set_ylabel("Tỉ lệ sai trên phần được nhận (risk)")
    ax.set_title("Risk-coverage trên DEV (out-of-fold)")
    ax.set_ylim(0, 0.12)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGS / "risk_coverage_dev.png", dpi=140)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    for i, ((s, vr), g) in enumerate(lc_df.groupby(["source", "variant"], sort=False)):
        xs = [3, 5, 10, 15, 25]
        lab = {"3": 3, "5": 5, "10": 10, "15": 15, "all": 25}
        y = [g[g.k.astype(str) == k].macro_f1_mean.iloc[0] for k in lab]
        e = [g[g.k.astype(str) == k].macro_f1_std.iloc[0] for k in lab]
        ax.errorbar(xs, y, yerr=e, marker="o", ms=4, capsize=2, ls="-" if vr == "cap_all" else "--",
                    label=f"{SOURCE_VI.get(s, s)} ({'cắt mọi lớp' if vr == 'cap_all' else 'lớp gộp giữ đủ'})", color=colors[(i // 2) % 5])
    ax.set_xticks([3, 5, 10, 15, 25])
    ax.set_xticklabels(["3", "5", "10", "15", "tất cả"])
    ax.set_xlabel("Số tài liệu huấn luyện tối đa mỗi lớp")
    ax.set_ylabel("Macro-F1 (DEV, CV)")
    ax.set_title("Learning curve")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGS / "learning_curve.png", dpi=140)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    order = ["300", "600", "1000", "2000", "full"]
    for i, (s, g) in enumerate(lg.groupby("source", sort=False)):
        g = g.assign(n=g.n_chars.astype(str)).set_index("n")
        ax.errorbar(range(len(order)), [g.loc[o].macro_f1_mean for o in order], yerr=[g.loc[o].macro_f1_std for o in order], marker="o", ms=4,
                    capsize=2, label=SOURCE_VI.get(s, s), color=colors[i % 5])
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels(["300", "600", "1000", "2000", "toàn bộ"])
    ax.set_xlabel("Số ký tự đầu của trang 1")
    ax.set_ylabel("Macro-F1 (DEV, CV)")
    ax.set_title("Ablation độ dài đầu vào")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGS / "input_length.png", dpi=140)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Markdown (khối trong RESULTS.md)
# ---------------------------------------------------------------------------
def render_dev_markdown(bench, ds_tab, summ, sources, primary, onprem, main_dev, abl_df, lg, lc_df, lc_rec_df, lkg, sel_df, rg_df, lat_df, patt_all, top, dev_all):
    ds_md = md_table(ds_tab.rename(columns={"class": "lớp (Track S)", "DEV": "DEV", "TEST": "TEST", "total": "tổng"}))
    stats = (f"- File PDF: {summ['files']}; tài liệu duy nhất: {summ['unique_docs']}; loại bỏ composite hỗn hợp: {summ['composites_mixed_unique']}; "
             f"**benchmark: {summ['benchmark_docs']} tài liệu** ({summ['types_total']} loại, trước khi loại composite).\n"
             f"- Track S: {len(bench.s_classes) - 1} lớp có >= {bench.min_docs} tài liệu + lớp gộp `RARE_OR_OTHER` "
             f"({summ['pool_types']} loại, {summ['pool_docs']} tài liệu).\n"
             f"- DEV = {summ['dev']} tài liệu, TEST (khóa) = {summ['test']} tài liệu. Xung đột nhãn giữa các bản sao: {len(summ['dup_conflicts'])}.\n"
             f"- Nhãn: `{Path(bench.labels_path).name}` (sha1[:10] = `{bench.labels_sha}`).")
    update_block(RESULTS_MD, "dataset", stats + "\n\n" + ds_md)
    cols = ["method"] + sources
    ren = {s: f"{s}" for s in sources}
    update_block(RESULTS_MD, "dev_main", md_table(main_dev[cols].rename(columns=ren)))
    update_block(RESULTS_MD, "ablation_source", md_table(abl_df))
    lg2 = lg.copy()
    lg2["macro_f1"] = [pm(a, b) for a, b in zip(lg2.macro_f1_mean, lg2.macro_f1_std)]
    pv = lg2.assign(n_chars=lg2.n_chars.astype(str)).pivot(index="source", columns="n_chars", values="macro_f1")
    pv = pv[[c for c in ["300", "600", "1000", "2000", "full"] if c in pv.columns]].reset_index()
    update_block(RESULTS_MD, "ablation_length", md_table(pv))
    lc2 = lc_df.assign(macro_f1=[pm(a, b) for a, b in zip(lc_df.macro_f1_mean, lc_df.macro_f1_std)])
    lcp = lc2.pivot(index=["source", "variant"], columns="k", values="macro_f1")
    lcp = lcp[[c for c in ["3", "5", "10", "15", "all"] if c in lcp.columns]].reset_index()
    update_block(RESULTS_MD, "learning_curve", md_table(lcp))
    rec = lc_rec_df.copy()
    update_block(RESULTS_MD, "learning_curve_recall", md_table(rec[(rec.source == primary) & (rec.variant == "pool_full")].drop(columns=["source", "variant"]).rename(columns={"cls": "lớp"})))
    lk2 = lkg.assign(macro_f1=[pm(a, b) for a, b in zip(lkg.macro_f1_mean, lkg.macro_f1_std)])
    lkp = lk2.pivot(index="source", columns="scheme", values="macro_f1")
    lkp = lkp[[c for c in ["naive_files", "naive_unique", "grouped_capped", "grouped_strict"] if c in lkp.columns]].reset_index()
    update_block(RESULTS_MD, "leakage", md_table(lkp))
    update_block(RESULTS_MD, "selective_dev", md_table(sel_df[["source", "config", "max_error", "threshold", "dev_auto_file_rate", "dev_error_on_accepted", "n_accepted", "errors", "ceiling_non_pool", "accuracy_all"]]))
    rg2 = rg_df[["source", "z_n", "z_accuracy", "z_macro_f1_types_ge3", "z_types_scored", "z_coverage", "z_accuracy_on_covered"]]
    update_block(RESULTS_MD, "rule_gate_z", md_table(rg2))
    update_block(RESULTS_MD, "latency", md_table(lat_df))
    pd_path = TABLES / "dev_paired_fold_differences.csv"
    if pd_path.exists():
        update_block(RESULTS_MD, "paired_dev", md_table(pd.read_csv(pd_path)[["comparison", "mean_diff_macro_f1", "std_diff", "folds_A_better", "folds_tie", "folds_B_better"]]))
    lpc = TABLES / "leakage_per_class_oof_seed0.csv"
    if lpc.exists():
        l = pd.read_csv(lpc)
        l = l[l.source == primary].pivot(index="class", columns="scheme", values="recall")
        l = l[[c for c in ["naive_files", "naive_unique", "grouped_capped", "grouped_strict"] if c in l.columns]].reset_index()
        update_block(RESULTS_MD, "leakage_per_class", md_table(l))
    update_block(RESULTS_MD, "best_c", md_table(pd.read_csv(TABLES / "dev_best_C_per_method.csv")[["source", "config", "macro_f1_mean", "macro_f1_std", "accuracy_mean", "ece_oof_seed0", "brier_oof_seed0"]]))
    # mẫu lỗi
    lines = []
    for s in (primary, onprem):
        if s not in patt_all:
            continue
        lines.append(f"**{s}** (`{top[s][0]}`)\n")
        for k, title in (("by_true_type", "Theo loại thật"), ("by_scanned", "Bản quét (1) / số hóa (0)"), ("by_length", "Theo độ dài văn bản"), ("by_template", "Có biểu mẫu chung (1) hay không (0)")):
            lines.append(f"{title}:\n\n" + md_table(patt_all[s][k]) + "\n")
    update_block(RESULTS_MD, "error_patterns", "\n".join(lines))


# ---------------------------------------------------------------------------
# GIAI ĐOẠN TEST
# ---------------------------------------------------------------------------
def run_final(args):
    sel_path = TABLES / "dev_selection.json"
    if not sel_path.exists():
        raise SystemExit("Chưa có dev_selection.json: chạy giai đoạn DEV trước (không kèm --final-test).")
    sel = json.loads(sel_path.read_text(encoding="utf-8"))
    bench = load_benchmark(args.labels, args.min_docs)
    if sel["labels_sha"] != bench.labels_sha or sel["min_docs"] != args.min_docs:
        raise SystemExit("Nhãn / min_docs đã đổi so với lúc chốt trên DEV -> chạy lại giai đoạn DEV trước.")
    reg_path = TABLES / "test_scored.json"
    reg = json.loads(reg_path.read_text(encoding="utf-8")) if reg_path.exists() else {}
    only = list(args.final_sources or [])
    if only:
        bad = [s for s in only if s not in sel["sources"]]
        if bad:
            raise SystemExit(f"Nguồn {bad} chưa có trong dev_selection.json: chạy giai đoạn DEV (kèm nguồn đó) trước.")
        scored = set((reg.get(bench.labels_sha) or {}).get("sources_scored") or (reg.get(bench.labels_sha) or {}).get("configs", {}).keys())
        again = [s for s in only if s in scored]
        if again and not args.allow_rescore:
            raise SystemExit(f"TEST đã được chấm cho nguồn {again} (nhãn {bench.labels_sha}); từ chối chấm lại.")
    elif bench.labels_sha in reg and not args.allow_rescore:
        raise SystemExit(f"TEST đã được chấm cho bộ nhãn {bench.labels_sha} lúc {reg[bench.labels_sha]['time']}. "
                         "Chấm lại = nhìn TEST nhiều lần; chỉ dùng --allow-rescore khi có lý do chính đáng và ghi vào báo cáo. "
                         "Muốn chấm thêm nguồn văn bản MỚI mà không đụng nguồn cũ: --final-sources <nguồn mới>.")
    splits = load_or_make_splits(bench)
    run_id = new_run_id()
    all_sources = sel["sources"]
    sources = only or all_sources
    primary, onprem = sel["primary_source"], sel["onprem_source"]
    cfgs = {c["name"]: c for c in text_configs()}
    cfgs["majority"] = dict(family="majority", name="majority")
    for c in visual_configs():
        cfgs[c["name"]] = c
    vcache = build_visual_cache(load_documents(bench, splits, primary, "ALL", include_duplicates=True), X.VISUAL_CACHE)

    rows, preds, pair_rows, sel_rows, err_frames = [], {}, [], [], {}
    classes = bench.s_classes
    log("TEST: huấn luyện lại trên toàn DEV rồi chấm đúng 1 lần ...")
    dev_n = None
    for s in sources:
        dev = load_documents(bench, splits, s, "DEV")
        test = load_documents(bench, splits, s, "TEST", final_test=True)
        dev_n = len(dev)
        yt = [d.label_s for d in test]
        targets = [(n, cfgs[n]) for n in sel["final_configs"][s]]
        targets.append(("rule_gate_mapped_to_S", dict(family="rule_gate_S", name="rule_gate_mapped_to_S")))
        if s == primary:
            targets += [("majority", cfgs["majority"]), (sel["visual_best"], cfgs[sel["visual_best"]])]
        for name, cfg in targets:
            p = build_predictor(cfg, classes, None, vcache).fit(dev)
            pr = p.predict(test)
            preds[(s, name)] = (pr, yt, test)
            bm = bootstrap_metrics(yt, pr.labels, classes)
            sc = score_predictions(yt, pr.labels, classes, pr.proba if pr.classes == classes else None)
            rows.append(dict(source=("image_p1" if cfg["family"] == "visual" else s), config=name, rank=(sel["final_configs"][s].index(name) + 1 if name in sel["final_configs"][s] else ""),
                             n=len(test), accuracy=bm["accuracy"][0], acc_lo=bm["accuracy"][1], acc_hi=bm["accuracy"][2],
                             macro_f1=bm["macro_f1"][0], f1_lo=bm["macro_f1"][1], f1_hi=bm["macro_f1"][2], weighted_f1=sc["weighted_f1"], ece=sc["ece"], brier=sc["brier"]))
            pc = sc["per_class"]
            pc.to_csv(TABLES / f"per_class_test_{s}_{name}.csv", index=False)
    def merge_saved(name, new_df, key="source"):
        path = TABLES / f"{name}.csv"
        if only and path.exists():
            old = pd.read_csv(path)
            new_df = pd.concat([old[~old[key].isin(only)], new_df], ignore_index=True)
        return new_df

    # Track Z: cổng luật trên TEST (nguồn chính và on-prem)
    z_rows = []
    for s in dict.fromkeys(sources):
        test = load_documents(bench, splits, s, "TEST", final_test=True)
        pr = RuleGatePredictor("Z").predict(test)
        yt = [d.label for d in test]
        sc = score_predictions(yt, pr.labels, bench.z_classes, None, min_support=3, abstain_label=UNKNOWN)
        z_rows.append(dict(source=s, n=len(test), accuracy=sc["accuracy"], macro_f1_types_ge3=sc["macro_f1"], types_scored=sc["n_classes_scored"],
                           coverage=sc["coverage"], accuracy_on_covered=sc["accuracy_on_covered"]))
    z_df_all = merge_saved("rule_gate_test_track_z", pd.DataFrame(z_rows))
    save(z_df_all, "rule_gate_test_track_z")

    # chế độ --final-sources: các nguồn đã chấm trước đó chỉ được ĐỌC lại từ errors_test_<nguồn>.csv (dự đoán đã lưu), không chấm lại
    for s in all_sources:
        if s in sources:
            continue
        name = sel["final_configs"][s][0]
        e = pd.read_csv(TABLES / f"errors_test_{s}.csv", dtype={"doc_id": str})
        preds[(s, name)] = (Prediction(e["predicted"].tolist()), e["true"].tolist(), None)

    test_df = pd.DataFrame(rows)
    test_df = merge_saved("test_main", test_df)
    save(test_df, "test_main")

    # so sánh ghép cặp
    def pair(a, b, tag):
        (pa, yt_a, _), (pb, yt_b, _) = preds[a], preds[b]
        if yt_a != yt_b:   # khác nguồn nhưng cùng tập TEST (cùng thứ tự doc_id)
            raise AssertionError("TEST không cùng thứ tự")
        r = paired_bootstrap(yt_a, pa.labels, pb.labels, classes)
        pair_rows.append(dict(comparison=tag, A=f"{a[0]}:{a[1]}", B=f"{b[0]}:{b[1]}",
                              **{f"{m}_{k}": v for m in ("macro_f1", "accuracy") for k, v in r[m].items()}))

    for s in sources:
        c = sel["final_configs"][s]
        if len(c) > 1:
            pair((s, c[0]), (s, c[1]), f"{s}: top1 vs top2 (DEV)")
        pair((s, c[0]), (s, "rule_gate_mapped_to_S"), f"{s}: top1 vs rule gate")
        if s != primary:
            pair((primary, sel["final_configs"][primary][0]), (s, c[0]), f"nguồn {primary} vs {s} (top1 mỗi nguồn)")
    if primary in sources:
        pair((primary, sel["final_configs"][primary][0]), (primary, sel["visual_best"]), "văn bản vs ảnh (nguồn chính)")
    pair_df = pd.DataFrame(pair_rows)
    if only and (TABLES / "test_paired_bootstrap.csv").exists():
        old = pd.read_csv(TABLES / "test_paired_bootstrap.csv")
        pair_df = pd.concat([old[~old["comparison"].isin(pair_df["comparison"])], pair_df], ignore_index=True)
    save(pair_df, "test_paired_bootstrap")

    # selective prediction: áp ngưỡng chốt trên DEV
    for s in sources:
        for name in sel["final_configs"][s]:
            pr, yt, test = preds[(s, name)]
            correct = np.array([a == b for a, b in zip(yt, pr.labels)])
            elig = np.array([l != POOL for l in pr.labels])
            conf = pr.confidence
            for tag in ("1pct", "2pct"):
                th = sel["selective"][s][name][tag]["threshold"]
                th = float("inf") if th is None else th
                ap = apply_threshold(conf, correct, elig, th)
                sel_rows.append(dict(source=s, config=name, max_error=0.01 if tag == "1pct" else 0.02, dev_threshold=th,
                                     dev_auto_file_rate=sel["selective"][s][name][tag]["coverage"], **{f"test_{k}": v for k, v in ap.items()},
                                     test_ceiling_non_pool=float(np.mean([t != POOL for t in yt]))))
    sel_test = merge_saved("selective_test", pd.DataFrame(sel_rows))
    save(sel_test, "selective_test")

    # lỗi + ma trận nhầm lẫn TEST (mô hình tốt nhất mỗi nguồn)
    for s in sources:
        name = sel["final_configs"][s][0]
        pr, yt, test = preds[(s, name)]
        oof = pd.DataFrame({"doc_id": [d.doc_id for d in test], "y_true": yt, "y_pred": pr.labels, "conf": pr.confidence})
        err = X.error_table(oof, test)
        err.to_csv(TABLES / f"errors_test_{s}.csv", index=False, encoding="utf-8")
        confusion_matrix_df(yt, pr.labels, classes).to_csv(TABLES / f"confusion_test_{s}.csv", encoding="utf-8")
        top_confusions(yt, pr.labels, 10).to_csv(TABLES / f"top_confusions_test_{s}.csv", index=False)
        for k, v in X.error_patterns(err).items():
            v.to_csv(TABLES / f"error_patterns_test_{k}_{s}.csv", index=False)

    # bảng chung
    if not args.no_results_table:
        for r in rows:
            append_result_row(dict(run_id=run_id, method=r["config"], track="S", text_source=r["source"], split="TEST", n=r["n"], accuracy=r["accuracy"],
                                   accuracy_ci_lo=r["acc_lo"], accuracy_ci_hi=r["acc_hi"], macro_f1=r["macro_f1"], macro_f1_ci_lo=r["f1_lo"], macro_f1_ci_hi=r["f1_hi"],
                                   labels_file=Path(args.labels).name, labels_sha=bench.labels_sha, notes="final config chosen on DEV; bootstrap 2000"))
        for r in z_rows:
            if args.results_sources and r["source"] not in args.results_sources:
                continue
            append_result_row(dict(run_id=run_id, method="rule_gate", track="Z", text_source=r["source"], split="TEST", n=r["n"], accuracy=r["accuracy"],
                                   macro_f1=r["macro_f1_types_ge3"], coverage=r["coverage"], acc_on_covered=r["accuracy_on_covered"],
                                   labels_file=Path(args.labels).name, labels_sha=bench.labels_sha, notes=f"macro-F1 over {r['types_scored']} types with >=3 docs in TEST; Kev off"))

    prev = reg.get(bench.labels_sha) or {}
    done = sorted(set(prev.get("sources_scored") or prev.get("configs", {}).keys()) | set(sources))
    reg[bench.labels_sha] = {"time": prev.get("time") if only and prev else dt.datetime.now().isoformat(timespec="seconds"),
                             "run_id": prev.get("run_id") if only and prev else run_id,
                             "configs": sel["final_configs"] if not only else {**prev.get("configs", {}), **{s: sel["final_configs"][s] for s in sources}},
                             "sources_scored": done,
                             "scored_log": (prev.get("scored_log") or []) + [{"time": dt.datetime.now().isoformat(timespec="seconds"), "run_id": run_id, "sources": sources}]}
    reg_path.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")
    render_test_markdown(test_df, pair_df, sel_test, z_df_all, all_sources, primary, onprem, sel)
    log("TEST xong.")
    print(md_table(test_df))


def render_test_markdown(test_df, pair_df, sel_test, z_df, sources, primary, onprem, sel):
    t = test_df.copy()
    t["accuracy"] = [fmt_ci(a, l, h) for a, l, h in zip(t.accuracy, t.acc_lo, t.acc_hi)]
    t["macro_f1 [CI 95%]"] = [fmt_ci(a, l, h) for a, l, h in zip(t.macro_f1, t.f1_lo, t.f1_hi)]
    t["rank"] = [("" if pd.isna(v) or v == "" else str(int(float(v)))) for v in t["rank"]]
    t = t[["source", "config", "rank", "n", "macro_f1 [CI 95%]", "accuracy", "weighted_f1", "ece", "brier"]]
    update_block(RESULTS_MD, "test_main", md_table(t))
    p = pair_df.copy()
    p["Δ macro-F1 [CI]"] = [fmt_ci(d, l, h) for d, l, h in zip(p.macro_f1_diff, p.macro_f1_ci_lo, p.macro_f1_ci_hi)]
    p["Δ accuracy [CI]"] = [fmt_ci(d, l, h) for d, l, h in zip(p.accuracy_diff, p.accuracy_ci_lo, p.accuracy_ci_hi)]
    p = p[["comparison", "Δ macro-F1 [CI]", "macro_f1_p_value", "macro_f1_separable", "Δ accuracy [CI]", "accuracy_p_value", "accuracy_separable"]]
    update_block(RESULTS_MD, "test_pairs", md_table(p))
    s = sel_test.copy()
    s["test_auto_file [CI]"] = [fmt_ci(a, l, h) for a, l, h in zip(s.test_coverage, s.test_coverage_lo, s.test_coverage_hi)]
    s["test_error_on_accepted [CI bootstrap]"] = [fmt_ci(a, l, h) for a, l, h in zip(s.test_risk, s.test_risk_lo, s.test_risk_hi)]
    if "test_risk_upper95_exact" not in s.columns:     # tính từ số đếm (k lỗi / n được nhận), không cần chấm lại TEST
        s["test_risk_upper95_exact"] = [clopper_pearson_upper(int(k), int(n)) for k, n in zip(s.test_errors, s.test_n_accepted)]
    s = s[["source", "config", "max_error", "dev_threshold", "dev_auto_file_rate", "test_n_accepted", "test_errors", "test_auto_file [CI]",
           "test_error_on_accepted [CI bootstrap]", "test_risk_upper95_exact", "test_ceiling_non_pool"]]
    update_block(RESULTS_MD, "selective_test", md_table(s))
    update_block(RESULTS_MD, "rule_gate_z_test", md_table(z_df))


def render_dev_only(args):
    """Vẽ lại các khối DEV của RESULTS.md từ tables/*.csv (không tính lại gì)."""
    sel = json.loads((TABLES / "dev_selection.json").read_text(encoding="utf-8"))
    bench = load_benchmark(args.labels, args.min_docs)
    rd = lambda n: pd.read_csv(TABLES / f"{n}.csv")
    src = sel["sources"]
    patt = {s: {k: rd(f"error_patterns_{k}_{s}") for k in ("by_true_type", "by_scanned", "by_length", "by_template")} for s in src}
    summ = json.loads((TABLES / "dataset.json").read_text(encoding="utf-8"))
    render_dev_markdown(bench, rd("dataset_track_s"), summ, src, sel["primary_source"], sel["onprem_source"], rd("dev_main_macro_f1"),
                        rd("ablation_text_source"), rd("ablation_input_length"), rd("learning_curve"), rd("learning_curve_per_class_recall"),
                        rd("leakage_naive_vs_grouped"), rd("selective_dev"), rd("rule_gate_dev"), rd("latency_and_size"), patt,
                        sel["final_configs"], rd("dev_all_configs"))


def render_test_only(args):
    """Vẽ lại các khối TEST trong RESULTS.md từ tables/*.csv đã có (KHÔNG chạm vào dữ liệu TEST, không chấm lại)."""
    sel = json.loads((TABLES / "dev_selection.json").read_text(encoding="utf-8"))
    rd = lambda n: pd.read_csv(TABLES / f"{n}.csv")
    render_test_markdown(rd("test_main"), rd("test_paired_bootstrap"), rd("selective_test"), rd("rule_gate_test_track_z"),
                         sel["sources"], sel["primary_source"], sel["onprem_source"], sel)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--labels", default=str(DEFAULT_LABELS), help="CSV nhãn (doc_id, doc_type, composite_mixed, ...). Mặc định data/labels_v2.csv")
    ap.add_argument("--min-docs", type=int, default=10, help="Track S: loại có >= số này tài liệu duy nhất mới là một lớp riêng")
    ap.add_argument("--final-test", action="store_true", help="Chấm TEST khóa (đúng 1 lần) bằng các cấu hình đã chốt trên DEV")
    ap.add_argument("--render-dev-only", action="store_true", help="Chỉ vẽ lại khối DEV của RESULTS.md từ bảng đã lưu")
    ap.add_argument("--render-test-only", action="store_true", help="Chỉ vẽ lại khối TEST của RESULTS.md từ bảng đã lưu (không chấm lại)")
    ap.add_argument("--allow-rescore", action="store_true", help="Cho phép chấm TEST lần thứ hai cho cùng bộ nhãn (phải ghi lý do trong báo cáo)")
    ap.add_argument("--jobs", type=int, default=min(16, os.cpu_count() or 1))
    ap.add_argument("--seeds", type=int, default=3, help="Số seed gán fold DEV (mặc định 3)")
    ap.add_argument("--sources", nargs="*", help="Giới hạn nguồn văn bản (mặc định: mọi nguồn có file)")
    ap.add_argument("--final-sources", nargs="*", help="Với --final-test: chỉ chấm các nguồn văn bản này (nguồn MỚI chưa từng chấm TEST); nguồn cũ không bị chấm lại")
    ap.add_argument("--results-sources", nargs="*", help="Chỉ thêm vào results_table.csv các dòng của những nguồn này (tránh trùng dòng cũ khi chạy lại)")
    ap.add_argument("--keep-splits", action="store_true", help="Không còn tác dụng (giữ splits đã là mặc định); còn nhận để lệnh cũ chạy được")
    ap.add_argument("--rebuild-splits", action="store_true",
                    help="Giai đoạn DEV: chia lại và GHI ĐÈ data/splits/* - TEST đổi, mọi số TEST cũ phải chấm lại")
    ap.add_argument("--no-results-table", action="store_true", help="Không ghi vào results_table.csv chung")
    args = ap.parse_args()
    args.labels = Path(args.labels)
    if args.render_dev_only:
        render_dev_only(args)
    elif args.render_test_only:
        render_test_only(args)
    elif args.final_test:
        run_final(args)
    else:
        run_dev(args)


if __name__ == "__main__":
    main()
