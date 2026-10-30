"""run_all.py - Điểm vào duy nhất của thí nghiệm 02: embedding (E1), zero-shot LLM/Kev (E2), calibration (E3), cascade (E4), nguồn văn bản (E5).

Chạy từ thư mục gốc repo (Windows):
    .venv\\Scripts\\python.exe -X utf8 teams\\team3_classification\\experiments\\02_llm_and_cascade\\run_all.py --stage embed
    ... --stage zeroshot [--family kev|ollama] [--sources ocr_v2_p12 ...] [--methods id ...] [--max-docs N]
    ... --stage calib
    ... --stage cascade
    ... --stage latency          # đo lại độ trễ + VRAM khi máy rảnh (bỏ qua cache)
    ... --stage report           # vẽ lại các khối bảng trong RESULTS.md từ CSV
    ... --final-test             # chấm TEST (khóa) đúng một lần cho các cấu hình đã chốt trên DEV (dev_selection_02.json)

DEV: mọi lựa chọn (prompt, độ dài đầu vào, ngưỡng) chỉ dùng DEV (TF-IDF/embedding: dự đoán out-of-fold; LLM zero-shot: trực tiếp).
Mọi lời gọi mô hình được cache trên đĩa (`_cache/`, git-ignored): chạy lại miễn phí và tất định. Không gửi gì ra ngoài máy.
"""

import os

for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse  # noqa: E402
import datetime as dt  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from dataclasses import asdict, replace  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import requests  # noqa: E402

from common import (FIGS, HERE, LABELS, MIN_TEXT_CHARS, OUT, PREDS, REG02, SEL02, SOURCE_VI, SOURCES_MAIN, TABLES, Data,  # noqa: E402
                    dump_json, log, md_table)
from harness import (POOL, UNKNOWN, append_result_row as _append_result_row, cross_validate, latency_summary, new_run_id, paired_bootstrap,  # noqa: E402
                     score_predictions, summarize_folds)
from eval_metrics import BOOT_N, BOOT_SEED, apply_threshold, bootstrap_metrics, clopper_pearson_upper, fmt_ci, risk_coverage_curve  # noqa: E402
from evalz import aurc, calib_scores, per_type_recall, z_scores  # noqa: E402
from predictors import EmbCentroid, EmbKNN, EmbLR, EmbZeroShot, EmbeddingStore, ZeroShotPredictor  # noqa: E402
import signals as SG  # noqa: E402
from src.classification.cascade import (AGREE_MODES, NEVER_AUTO, CascadeParams, Signals, run_cascade, selective_counts,  # noqa: E402
                                        tier_shares, tune)

SMOKE = os.environ.get("EXP02_SMOKE") == "1"      # chạy thử đường TEST trên tài liệu DEV (KHÔNG mở TEST; không ghi bảng chung, không ghi sổ đăng ký)
RESULTS_MD = HERE / "RESULTS.md"
from common import REPO as _REPO  # noqa: E402
REPO_T01_TABLES = _REPO / "teams" / "team3_classification" / "results" / "01_classical_baselines" / "tables"
RESULTS_TABLE_PATH = None   # mặc định: harness.RESULTS_TABLE
OLLAMA = "http://127.0.0.1:11434"
KEV_STATUS = "http://127.0.0.1:8009/api/status"
EMB_CHARS = (512, 2000)

# --- lưới phương pháp zero-shot (đã cắt gọn, xem RESULTS.md mục "đã cắt gì") ---------------------------------------------
M = lambda id_, engine, **kw: dict(id=id_, engine=engine, **kw)
KEV_GRID = [
    M("kev_s1_short_c2000", "kev", stages=1, desc="short", chars=2000),
    M("kev_s1_long_c2000", "kev", stages=1, desc="long", chars=2000),
    M("kev_s2_short_c2000", "kev", stages=2, desc="short", chars=2000),
    M("kev_s2_long_c2000", "kev", stages=2, desc="long", chars=2000),
    M("kev_s1_short_c800", "kev", stages=1, desc="short", chars=800),
    M("kev_s2_short_c800", "kev", stages=2, desc="short", chars=800),
    M("kev_s1_name_c2000", "kev", stages=1, desc="name", chars=2000),          # chỉ TÊN loại, không mô tả (chẩn đoán: kết quả có phụ thuộc mô tả viết sau khi xem tài liệu?)
    M("kev_s2_name_c2000", "kev", stages=2, desc="name", chars=2000),
    M("kev_s1_name_c800", "kev", stages=1, desc="name", chars=800),
]
OLLAMA_GRID = [
    M("q35_s1_short_c2000", "ollama", model="qwen3.5:4b", stages=1, desc="short", chars=2000),
    M("q35_s1_long_c2000", "ollama", model="qwen3.5:4b", stages=1, desc="long", chars=2000),
    M("q35_s2_short_c2000", "ollama", model="qwen3.5:4b", stages=2, desc="short", chars=2000),
    M("q35_s1_short_c2000_icl1", "ollama", model="qwen3.5:4b", stages=1, desc="short", chars=2000, icl=1),
    M("q25_s1_short_c2000", "ollama", model="qwen2.5:3b", stages=1, desc="short", chars=2000),
    M("q25_s1_long_c2000", "ollama", model="qwen2.5:3b", stages=1, desc="long", chars=2000),
    M("q35_s1_name_c2000", "ollama", model="qwen3.5:4b", stages=1, desc="name", chars=2000),
    M("q35_s1_short_c800", "ollama", model="qwen3.5:4b", stages=1, desc="short", chars=800),
]
SPECS = {m["id"]: m for m in KEV_GRID + OLLAMA_GRID}
FAMILY = {"kev": "kev", "q35": "ollama", "q25": "ollama"}      # tiền tố id -> engine
FAM_OF = lambda mid: mid.split("_")[0]
GRID_SOURCE = "ocr_v2_p12"          # nguồn dùng để CHỌN prompt (điều kiện triển khai)


# ---------------------------------------------------------------------------
# Tiện ích
# ---------------------------------------------------------------------------
def append_result_row(row: dict) -> None:
    if not SMOKE:
        _append_result_row(row)


def load_sel() -> dict:
    return json.loads(SEL02.read_text(encoding="utf-8")) if SEL02.exists() else {}


def save_sel(sel: dict) -> None:
    dump_json(SEL02, sel)


def update_block(name: str, content: str) -> None:
    if SMOKE or not RESULTS_MD.exists():
        return
    s = RESULTS_MD.read_text(encoding="utf-8")
    b, e = f"<!-- BEGIN:{name} -->", f"<!-- END:{name} -->"
    if b not in s or e not in s:
        return
    i, j = s.index(b) + len(b), s.index(e)
    RESULTS_MD.write_text(s[:i] + "\n" + content.strip() + "\n" + s[j:], encoding="utf-8")


def save_csv(df: pd.DataFrame, name: str) -> Path:
    p = TABLES / f"{'smoke_' if SMOKE else ''}{name}.csv"
    df.to_csv(p, index=False, encoding="utf-8")
    return p


def pred_path(kind: str, source: str, split: str) -> Path:
    return PREDS / f"{kind}__{source}__{split}.csv"


def save_preds(kind, source, split, docs, labels, conf, lat, answers=None, extra=None) -> pd.DataFrame:
    df = pd.DataFrame({"doc_id": [d.doc_id for d in docs], "true": [d.label for d in docs], "label": labels,
                       "conf": np.asarray(conf, float), "latency_ms": np.asarray(lat, float)})
    if answers is not None:
        df["parse_ok"] = [bool(a.parse_ok) for a in answers]
        df["error"] = [a.error for a in answers]
    if extra is not None:
        for k, v in extra.items():
            df[k] = v
    df.to_csv(pred_path(kind, source, split), index=False, encoding="utf-8")
    return df


def load_preds(kind, source, split="DEV") -> pd.DataFrame | None:
    p = pred_path(kind, source, split)
    return pd.read_csv(p, keep_default_na=False, dtype={"doc_id": str}).assign(conf=lambda d: pd.to_numeric(d["conf"], errors="coerce")) if p.exists() else None


def vram_snapshot() -> dict:
    out = {"kev_vram_mb": None, "kev_model": None, "ollama": {}}
    try:
        k = requests.get(KEV_STATUS, timeout=5).json()
        out["kev_vram_mb"], out["kev_model"] = k.get("vram_allocated_mb"), k.get("current_model")
    except Exception:
        pass
    try:
        for m in requests.get(f"{OLLAMA}/api/ps", timeout=5).json().get("models", []):
            out["ollama"][m["name"]] = round(m.get("size_vram", 0) / 2**20)
    except Exception:
        pass
    return out


def kev_model_name() -> str:
    """Tên mô hình Kev đang nạp. Server Kev xử lý tuần tự (chặn cả /api/status khi đang bận) nên thử lại với timeout dài."""
    for _ in range(6):
        try:
            return requests.get(KEV_STATUS, timeout=120).json().get("current_model") or "unknown"
        except Exception:
            time.sleep(5)
    return "unknown"


# ---------------------------------------------------------------------------
# E1 - embedding
# ---------------------------------------------------------------------------
def fold_row(cvs, key="macro_f1"):
    sc = [s for cv in cvs for s in cv.fold_scores]
    st = summarize_folds(sc, ("accuracy", "macro_f1"))
    return st


def stage_embed(args):
    D = Data()
    bench = D.bench
    rows, fs_rows, rare_rows = [], [], []
    sel = load_sel()
    sel.setdefault("embed", {})
    for source in args.sources:
        dev = D.docs(source, "DEV")
        best_s, best_z = None, None
        for n in EMB_CHARS:
            store = EmbeddingStore(n)
            t0 = time.time()
            store.get(dev)
            log(f"embedding {source} n={n}: {len(dev)} tài liệu trong {time.time() - t0:.0f}s")
            # --- Track S: LR / centroid / kNN
            S = D.s_classes
            facs = {f"lr_C{c:g}": (lambda c=c: EmbLR(store, S, c)) for c in (1.0, 10.0, 100.0)}
            facs["centroid"] = lambda: EmbCentroid(store, S, "S", 1)
            facs["knn1"] = lambda: EmbKNN(store, S, "S", 1)
            facs["knn3"] = lambda: EmbKNN(store, S, "S", 3)
            for name, fac in facs.items():
                cvs = [cross_validate(fac, dev, S, "S", seed) for seed in (0, 1, 2)]
                st = fold_row(cvs)
                oof = cvs[0].oof
                pr_sc = score_predictions(oof["y_true"], oof["y_pred"], S, cvs[0].proba if cvs[0].classes == S else None)
                rows.append(dict(source=source, n_chars=n, method=name, track="S", macro_f1_mean=st["macro_f1_mean"], macro_f1_std=st["macro_f1_std"],
                                 accuracy_mean=st["accuracy_mean"], ece_oof_seed0=pr_sc["ece"]))
                if best_s is None or st["macro_f1_mean"] > best_s[0]:
                    best_s = (st["macro_f1_mean"], dict(n_chars=n, method=name))
            # --- Track Z few-shot (centroid min_train=2) và zero-shot theo mô tả
            Z = D.z_classes
            for mt in (2,):
                fac = lambda mt=mt: EmbCentroid(store, Z, "Z", mt)
                cvs = [cross_validate(fac, dev, Z, "Z", seed, min_support=3, abstain_label=UNKNOWN) for seed in (0, 1, 2)]
                st = fold_row(cvs)
                oof = cvs[0].oof
                zs = z_scores(bench, oof["y_true"], oof["y_pred"], boot=True)
                tr_counts = {}
                reach = []
                for d in dev:
                    n_other = sum(1 for e in dev if e.label == d.label and e.folds[0] != d.folds[0])
                    reach.append(n_other >= mt)
                reach = np.array(reach)
                fs_rows.append(dict(source=source, n_chars=n, method=f"centroid_min{mt}", macro_f1_fold_mean=st["macro_f1_mean"], macro_f1_fold_std=st["macro_f1_std"],
                                    **{f"oof_{k}": v for k, v in zs.items()}, reachable_share=float(reach.mean())))
                save_preds(f"embfs_n{n}", source, "DEV", [d for d in dev], oof.set_index("doc_id").loc[[d.doc_id for d in dev]]["y_pred"].tolist(),
                           oof.set_index("doc_id").loc[[d.doc_id for d in dev]]["conf"].to_numpy(), np.zeros(len(dev)))
                if best_z is None or zs["macro_f1"] > best_z[0]:
                    best_z = (zs["macro_f1"], dict(n_chars=n, method=f"centroid_min{mt}"))
            for desc in ("short",):
                p = EmbZeroShot(store, Z, desc)
                pr = p.predict(dev)
                zs = z_scores(bench, [d.label for d in dev], pr.labels)
                fs_rows.append(dict(source=source, n_chars=n, method=f"zeroshot_{desc}", macro_f1_fold_mean=np.nan, macro_f1_fold_std=np.nan,
                                    **{f"oof_{k}": v for k, v in zs.items()}, reachable_share=1.0))
                save_preds(f"embzs_n{n}", source, "DEV", dev, pr.labels, pr.confidence, np.zeros(len(dev)))
        sel["embed"][source] = dict(S=best_s[1], Z=best_z[1])
        log(f"E1 {source}: S tốt nhất {best_s}, Z few-shot tốt nhất {best_z}")
    df = pd.DataFrame(rows)
    save_csv(df, "e1_embed_track_s_dev")
    fs = pd.DataFrame(fs_rows)
    save_csv(fs, "e1_embed_track_z_dev")
    save_sel(sel)
    # bảng dùng trong RESULTS.md
    piv = df.assign(v=[f"{a:.3f} ± {b:.3f}" for a, b in zip(df.macro_f1_mean, df.macro_f1_std)]).pivot_table(
        index=["method", "n_chars"], columns="source", values="v", aggfunc="first").reset_index()
    update_block("e1_s", md_table(piv))
    f2 = fs.assign(macro_f1_ci=[f"{a:.3f} [{b:.3f}; {c:.3f}]" for a, b, c in zip(fs.oof_macro_f1, fs.oof_macro_f1_lo, fs.oof_macro_f1_hi)])
    f2 = f2[["source", "n_chars", "method", "macro_f1_ci", "oof_n_types_scored", "oof_accuracy", "oof_rare_recall", "oof_freq_recall", "reachable_share"]]
    update_block("e1_z", md_table(f2))


# ---------------------------------------------------------------------------
# E2 - zero-shot
# ---------------------------------------------------------------------------
def run_method(D: Data, spec: dict, source: str, max_docs: int | None = None, tag: str = "kev-0.8b") -> pd.DataFrame:
    dev = D.docs(source, "DEV")
    if max_docs:
        dev = dev[:max_docs]
    t0 = time.time()
    if spec.get("icl"):
        labels, conf, lat, answers = SG.icl_cv_signals(D, source, spec, tag=tag)
        dev = D.docs(source, "DEV")
    else:
        labels, conf, lat, answers = SG.llm_signals(D, source, "DEV", spec, tag=tag) if not max_docs else _llm_subset(D, source, spec, dev, tag)
    if max_docs:      # chạy thử: KHÔNG ghi file dự đoán (tránh file thiếu bị coi là kết quả đầy đủ)
        df = pd.DataFrame({"doc_id": [d.doc_id for d in dev], "true": [d.label for d in dev], "label": labels, "conf": np.asarray(conf, float),
                           "latency_ms": np.asarray(lat, float), "parse_ok": [bool(a.parse_ok) for a in answers], "error": [a.error for a in answers]})
    else:
        df = save_preds(f"zs_{spec['id']}", source, "DEV", dev, labels, conf, lat, answers)
    log(f"  {spec['id']} / {source}: {len(dev)} tài liệu, {time.time() - t0:.0f}s, parse_fail={float((~df.parse_ok).mean()):.3f}")
    return df


def _llm_subset(D, source, spec, docs, tag):
    p = ZeroShotPredictor(spec, D.z_classes, tag=tag)
    pr = p.predict(docs)
    conf = np.array([np.nan if (a.conf is None or not a.parse_ok) else a.conf for a in p.answers])
    return pr.labels, conf, pr.latency_ms, p.answers


def zs_summary_row(D: Data, spec: dict, source: str, df: pd.DataFrame, vram: dict | None = None) -> dict:
    bench = D.bench
    zs = z_scores(bench, df["true"].tolist(), df["label"].tolist())
    correct = (df["true"] == df["label"]).to_numpy()
    cal = calib_scores(df["conf"].to_numpy(), correct, df["label"].tolist())
    lat = latency_summary(df["latency_ms"][df["latency_ms"] > 0])
    row = dict(method=spec["id"], source=source, engine=spec["engine"], model=spec.get("model", "kev-0.8b"), stages=spec.get("stages", 1),
               desc=spec.get("desc"), chars=spec.get("chars"), icl=spec.get("icl", 0),
               parse_fail=float((~df.parse_ok).mean()) if "parse_ok" in df else np.nan, **zs,
               ece=cal["ece"], auroc=cal["auroc_correct"], latency_ms_median=lat["median_ms"], latency_ms_p95=lat["p95_ms"])
    if vram:
        row["vram_mb"] = vram.get("kev_vram_mb") if spec["engine"] == "kev" else vram.get("ollama", {}).get(spec.get("model"))
    return row


def stage_zeroshot(args):
    D = Data()
    ids = args.methods or [m["id"] for m in (KEV_GRID if args.family == "kev" else OLLAMA_GRID if args.family == "ollama" else KEV_GRID + OLLAMA_GRID)]
    kev_tag = f"kev-0.8b"
    if any(SPECS[i]["engine"] == "kev" for i in ids):
        mn = kev_model_name()
        log("Kev server đang giữ mô hình:", mn)
        if mn != "jaredpalmer/kev-0.8b":
            raise SystemExit(f"Server Kev đang giữ {mn}, không phải kev-0.8b: dừng để không ghi nhãn mô hình sai.")
    rows = []
    for source in args.sources:
        for mid in ids:
            spec = SPECS[mid]
            p = pred_path(f"zs_{mid}", source, "DEV")
            df = load_preds(f"zs_{mid}", source) if (p.exists() and not args.force and not args.max_docs) else None
            if df is not None and len(df) != len(D.docs(source, "DEV")):
                df = None
            if df is None:
                df = run_method(D, spec, source, args.max_docs, kev_tag)
            vr = vram_snapshot()
            rows.append(zs_summary_row(D, spec, source, df, vr))
    res = pd.DataFrame(rows)
    old = TABLES / "e2_zeroshot_dev.csv"
    if old.exists() and not args.max_docs:
        prev = pd.read_csv(old)
        res = pd.concat([prev[~prev.set_index(["method", "source"]).index.isin(res.set_index(["method", "source"]).index)], res], ignore_index=True)
    if not args.max_docs:
        save_csv(res, "e2_zeroshot_dev")
        select_best_zeroshot(res)
        render_e2()
    else:
        print(md_table(res[["method", "source", "n", "accuracy", "macro_f1", "rare_recall", "parse_fail", "latency_ms_median"]]))


def select_best_zeroshot(res: pd.DataFrame) -> None:
    """Chọn prompt tốt nhất mỗi họ mô hình trên GRID_SOURCE bằng macro-F1 DEV (hòa -> accuracy)."""
    sel = load_sel()
    sel.setdefault("zeroshot_best", {})
    g = res[res.source == GRID_SOURCE]
    for fam in ("kev", "q35", "q25"):
        sub = g[g.method.map(FAM_OF) == fam]
        if len(sub):
            best = sub.sort_values(["macro_f1", "accuracy"], ascending=False).iloc[0]
            sel["zeroshot_best"][fam] = best["method"]
    save_sel(sel)


def render_e2():
    p = TABLES / "e2_zeroshot_dev.csv"
    if not p.exists():
        return
    r = pd.read_csv(p)
    r = r.assign(macro_f1_ci=[f"{a:.3f} [{b:.3f}; {c:.3f}]" for a, b, c in zip(r.macro_f1, r.macro_f1_lo, r.macro_f1_hi)],
                 accuracy_ci=[f"{a:.3f} [{b:.3f}; {c:.3f}]" for a, b, c in zip(r.accuracy, r.accuracy_lo, r.accuracy_hi)])
    cols = ["method", "source", "accuracy_ci", "macro_f1_ci", "n_types_scored", "coverage", "rare_recall", "freq_recall", "parse_fail", "ece",
            "latency_ms_median", "latency_ms_p95"]
    t = r[cols].copy()
    t["latency_ms_median"] = t["latency_ms_median"].round(0)
    t["latency_ms_p95"] = t["latency_ms_p95"].round(0)
    update_block("e2", md_table(t))


def render_e1():
    f = TABLES / "e1_embed_track_s_dev.csv"
    if f.exists():
        df = pd.read_csv(f)
        piv = df.assign(v=[f"{a:.3f} ± {b:.3f}" for a, b in zip(df.macro_f1_mean, df.macro_f1_std)]).pivot_table(
            index=["method", "n_chars"], columns="source", values="v", aggfunc="first").reset_index()
        update_block("e1_s", md_table(piv))
    f = TABLES / "e1_embed_track_z_dev.csv"
    if f.exists():
        fs = pd.read_csv(f)
        f2 = fs.assign(macro_f1_ci=[f"{a:.3f} [{b:.3f}; {c:.3f}]" for a, b, c in zip(fs.oof_macro_f1, fs.oof_macro_f1_lo, fs.oof_macro_f1_hi)])
        update_block("e1_z", md_table(f2[["source", "n_chars", "method", "macro_f1_ci", "oof_n_types_scored", "oof_accuracy", "oof_rare_recall", "oof_freq_recall", "reachable_share"]]))


def render_e3():
    cal = pd.read_csv(TABLES / "e3_calibration_dev.csv") if (TABLES / "e3_calibration_dev.csv").exists() else None
    ag = pd.read_csv(TABLES / "e3_agreement_dev.csv") if (TABLES / "e3_agreement_dev.csv").exists() else None
    if cal is not None:
        t = cal[["source", "method", "accuracy", "conf_available", "ece", "auroc_correct", "aurc", "autofile_1pct", "autofile_2pct", "errors_1pct"]]
        update_block("e3_calib", md_table(t[t.source == GRID_SOURCE]))
    if ag is not None:
        update_block("e3_agree", md_table(ag[ag.source == GRID_SOURCE]))
    f = TABLES / "e2_rare_per_type_dev.csv"
    if f.exists():
        rr = pd.read_csv(f).drop(columns=["kev_s1_short_c2000", "kev_s2_short_c2000", "q35_s1_name_c2000"], errors="ignore")
        update_block("e2_rare", md_table(rr.round(2)))


def render_curated():
    import curated as C

    for name, fn in (("c_e1", C.c_e1), ("c_e2_dev", C.c_e2_dev), ("c_e2_src", C.c_e2_src), ("c_e2_rare", C.c_e2_rare), ("c_e3", C.c_e3), ("c_e3_agree", C.c_e3_agree),
                     ("c_e4_dev", lambda: C.c_e4(False)), ("c_e4_dev_ocr_2pct", lambda: C.c_e4(False, tol=0.02)), ("c_e4_test", lambda: C.c_e4(True)), ("c_e4_test_haiku", lambda: C.c_e4(True, "haiku_p12")),
                     ("c_e4_test_legacy", lambda: C.c_e4(True, "legacy_p1")), ("c_e4_test_2pct", lambda: C.c_e4(True, tol=0.02)), ("c_e4_pair", C.c_e4_pair), ("c_cost", C.c_cost)):
        try:
            update_block(name, fn())
        except Exception as e:   # bảng nào thiếu dữ liệu thì bỏ qua, báo lỗi
            log(f"curated {name}: {type(e).__name__}: {e}")


def render_e5():
    """Bảng E5: cùng một cấu hình trên ba nguồn văn bản (DEV; TEST nếu đã có). Đọc từ CSV đã lưu, không tính lại."""
    sel = load_sel()
    t01 = REPO_T01_TABLES
    allcfg = pd.read_csv(t01 / "dev_all_configs.csv")
    rg = pd.read_csv(t01 / "rule_gate_dev.csv")
    e2 = pd.read_csv(TABLES / "e2_zeroshot_dev.csv")
    e1z = pd.read_csv(TABLES / "e1_embed_track_z_dev.csv")
    e4 = pd.read_csv(TABLES / "e4_cascade_dev.csv")
    e4t = pd.read_csv(TABLES / "e4_cascade_test.csv") if (TABLES / "e4_cascade_test.csv").exists() else None
    e2t = pd.read_csv(TABLES / "e2_zeroshot_test.csv") if (TABLES / "e2_zeroshot_test.csv").exists() else None
    main = sel.get("cascade_main_t3", "q35_s1_short_c2000")
    kev = sel.get("zeroshot_best", {}).get("kev", "kev_s1_name_c2000")
    rows = []
    for src in SOURCES_MAIN:
        sub = allcfg[(allcfg.source == src) & allcfg.family.isin(["word_lr", "char_lr", "char_svc", "word_cnb"])].sort_values(["macro_f1_mean", "accuracy_mean"], ascending=False).iloc[0]
        r = dict(source=src, tfidf_macroF1_S=f"{sub.macro_f1_mean:.3f}", rule_gate_coverage=f"{float(rg[rg.source == src].z_coverage.iloc[0]):.3f}")
        z = e2[(e2.source == src) & (e2.method == main)]
        k = e2[(e2.source == src) & (e2.method == kev)]
        r[f"{main} macroF1_Z"] = f"{z.macro_f1.iloc[0]:.3f}" if len(z) else ""
        r[f"{kev} macroF1_Z"] = f"{k.macro_f1.iloc[0]:.3f}" if len(k) else ""
        ef = e1z[(e1z.source == src) & (e1z.n_chars == 2000) & (e1z.method == "centroid_min2")]
        r["emb few-shot macroF1_Z"] = f"{ef.oof_macro_f1.iloc[0]:.3f}" if len(ef) else ""
        c = e4[(e4.source == src) & (e4.max_error == 0.01) & (e4.name == f"full[{main}]")]
        if len(c):
            r["cascade DEV cross-fit auto-file@1%"] = f"{c.cf_coverage.iloc[0]:.3f} ({int(c.cf_errors.iloc[0])} sai)"
        c = e4[(e4.source == src) & (e4.max_error == 0.01) & (e4.name == "tfidf_only(classical)")]
        if len(c):
            r["classical DEV cross-fit"] = f"{c.cf_coverage.iloc[0]:.3f} ({int(c.cf_errors.iloc[0])} sai)"
        c = e4[(e4.source == src) & (e4.max_error == 0.01) & (e4.name == "no_rule")]
        if len(c):
            r["cascade bỏ luật, DEV cross-fit"] = f"{c.cf_coverage.iloc[0]:.3f} ({int(c.cf_errors.iloc[0])} sai)"
        if e4t is not None:
            c = e4t[(e4t.source == src) & (e4t.max_error == 0.01) & (e4t.name == f"full[{main}]")]
            if len(c):
                r["cascade TEST auto-file@1% [CI]"] = fmt_ci(c.coverage.iloc[0], c.coverage_lo.iloc[0], c.coverage_hi.iloc[0]) + f" ({int(c.errors.iloc[0])} sai)"
            c = e4t[(e4t.source == src) & (e4t.max_error == 0.01) & (e4t.name == "tfidf_only(classical)")]
            if len(c):
                r["classical TEST auto-file@1% [CI]"] = fmt_ci(c.coverage.iloc[0], c.coverage_lo.iloc[0], c.coverage_hi.iloc[0]) + f" ({int(c.errors.iloc[0])} sai)"
        rows.append(r)
    df = pd.DataFrame(rows)
    save_csv(df, "e5_sources")
    update_block("e5", md_table(df))


def best_ids(source_for_selection: str = GRID_SOURCE) -> dict:
    sel = load_sel()
    return sel.get("zeroshot_best", {})


def stage_zeroshot_sources(args):
    """E5: chạy các cấu hình tốt nhất của mỗi họ trên nguồn khác (haiku_p12, legacy_p1) + prompt thứ hai (short/long) cho self-consistency."""
    best = best_ids()
    ids = []
    for fam in ("kev", "q35", "q25"):
        if fam in best:
            ids.append(best[fam])
            ids.append(partner(best[fam]))
    ids += CASCADE_EXTRA
    args.methods = [i for i in dict.fromkeys(ids) if i in SPECS]
    args.sources = [s for s in ("haiku_p12", "legacy_p1")]
    stage_zeroshot(args)


def partner(mid: str) -> str:
    """Prompt thứ hai cho self-consistency (cùng mô hình): đổi một bước <-> hai bước (cùng mô tả và độ dài)."""
    if "_s1_" in mid or "_s2_" in mid:      # Kev và Ollama: đổi một bước <-> hai bước (cùng mô tả, cùng độ dài)
        c = mid.replace("_s1_", "_s2_") if "_s1_" in mid else mid.replace("_s2_", "_s1_")
    elif "_short_" in mid:
        c = mid.replace("_short_", "_long_")
    else:
        c = mid.replace("_long_", "_short_")
    return c if c in SPECS else mid


# ---------------------------------------------------------------------------
# E3 - calibration / abstention / agreement
# ---------------------------------------------------------------------------
AGREE_COMBOS = [("rule", "tfidf"), ("tfidf", "kev"), ("tfidf", "q35"), ("kev", "q35"), ("kev", "q35", "tfidf"), ("tfidf", "emb"), ("kev", "emb"),
                ("q35", "emb"), ("rule", "kev"), ("rule", "q35"), ("tfidf", "kev", "emb"), ("tfidf", "q35", "emb")]


def agreement_rows(source: str, lab_of: dict, y: np.ndarray, extra_combos=()) -> list:
    """Chấp nhận khi MỌI nguồn trong tổ hợp cùng một nhãn (không phải OTHER/UNKNOWN/RARE_OR_OTHER). Không dùng ngưỡng."""
    rows = []
    for combo in list(extra_combos) + AGREE_COMBOS:
        if not all(c in lab_of for c in combo):
            continue
        first = np.array(lab_of[combo[0]], dtype=object)
        ok = np.ones(len(y), bool)
        for c in combo[1:]:
            ok &= first == np.array(lab_of[c], dtype=object)
        ok &= ~np.isin(first, NEVER_AUTO) & ~np.isin(first, ["", POOL])
        k, err = int(ok.sum()), int((first[ok] != y[ok]).sum())
        rows.append(dict(source=source, agree_all_of="+".join(combo), n_accepted=k, coverage=k / len(y), errors=err, error_rate=(err / k) if k else np.nan,
                         risk_upper95_exact=clopper_pearson_upper(err, k) if k else np.nan))
    return rows


def collect_dev_methods(D: Data, source: str) -> dict:
    """{tên: DataFrame preds DEV} cho mọi phương pháp có dự đoán cho nguồn này (đồng bộ thứ tự tài liệu)."""
    dev = D.docs(source, "DEV")
    ids = [d.doc_id for d in dev]
    out = {}
    for mid in SPECS:
        df = load_preds(f"zs_{mid}", source)
        if df is not None and len(df) == len(dev):
            out[mid] = df.set_index("doc_id").loc[ids].reset_index()
    return out


def tfidf_frame(D: Data, source: str, split: str = "DEV", final_test: bool = False) -> pd.DataFrame:
    docs = D.docs(source, split, final_test=final_test)
    labels, conf, lat, cfg = SG.tfidf_signals(D, source, split, final_test)
    df = pd.DataFrame({"doc_id": [d.doc_id for d in docs], "true": [d.label for d in docs], "s_label": labels, "conf": conf, "latency_ms": lat})
    # Track Z: RARE_OR_OTHER = abstain
    df["label"] = [UNKNOWN if l == POOL else l for l in labels]
    df.attrs["config"] = cfg
    return df


def stage_calib(args):
    D = Data()
    bench = D.bench
    rows, agree_rows = [], []
    figs = {}
    for source in args.sources:
        dev = D.docs(source, "DEV")
        methods = collect_dev_methods(D, source)
        tf = tfidf_frame(D, source)
        rule_lab, rule_lat = SG.rule_signals(dev)
        y = np.array([d.label for d in dev])
        methods["tfidf_best"] = tf
        sel = load_sel()
        e = sel.get("embed", {}).get(source)
        if e:
            for kind in (f"embfs_n{e['Z']['n_chars']}", f"embzs_n{e['Z']['n_chars']}"):
                df = load_preds(kind, source)
                if df is not None:
                    methods[kind] = df.set_index("doc_id").loc[[d.doc_id for d in dev]].reset_index()
        for name, df in methods.items():
            lab = df["label"].tolist()
            correct = (df["true"] == df["label"]).to_numpy()
            cs = calib_scores(df["conf"].to_numpy(), correct, lab)
            rows.append(dict(source=source, method=name, **cs))
            figs[(source, name)] = df
        # luật: một điểm duy nhất
        rl = np.array(rule_lab)
        acc_m = rl != ""
        rows.append(dict(source=source, method="rule_gate", n=len(dev), conf_available=0.0, accuracy=float((rl == y).mean()),
                         autofile_1pct=float(acc_m.mean()), autofile_2pct=float(acc_m.mean()),
                         errors_1pct=int((rl[acc_m] != y[acc_m]).sum()), n_accepted_1pct=int(acc_m.sum())))
        # --- đồng thuận giữa các phương pháp (không dùng ngưỡng): chấp nhận khi >= 2 nguồn cùng một nhãn (và nhãn không phải NEVER_AUTO/UNKNOWN)
        lab_of = {"rule": rl.tolist(), "tfidf": tf["label"].tolist()}
        for fam, mid in best_ids().items():
            if mid in methods:
                lab_of[fam] = methods[mid]["label"].tolist()
        if e and f"embfs_n{e['Z']['n_chars']}" in methods:
            lab_of["emb"] = methods[f"embfs_n{e['Z']['n_chars']}"]["label"].tolist()
        selfc = []
        for fam, mid in best_ids().items():
            pm_ = partner(mid)
            if pm_ != mid and pm_ in methods and mid in methods:
                lab_of[pm_] = methods[pm_]["label"].tolist()
                selfc.append((mid, pm_))              # self-consistency: cùng mô hình, hai prompt (mô tả ngắn / dài)
        agree_rows += agreement_rows(source, lab_of, y, selfc)
    ag_ = None
    # --- recall từng LOẠI HIẾM (giai thoại: mỗi loại 1-9 tài liệu) trên nguồn chính
    if GRID_SOURCE in args.sources:
        ms = {}
        for name, df in figs.items():
            if name[0] != GRID_SOURCE:
                continue
            nm = name[1]
            if nm in ("kev_s1_name_c2000", "kev_s1_short_c2000", "kev_s2_short_c2000", "q35_s1_short_c2000", "q35_s2_short_c2000", "q35_s1_name_c2000", "q25_s1_short_c2000", "tfidf_best")                     or nm.startswith(("embfs_n", "embzs_n")):
                ms[nm] = df["label"].tolist()
        yt = figs[next(k for k in figs if k[0] == GRID_SOURCE)]["true"].tolist()
        pt = per_type_recall(bench, yt, ms, only_rare=True)
        save_csv(pt, "e2_rare_per_type_dev")
        agg = pd.DataFrame([dict(method=k, rare_docs=int(sum(1 for t in yt if t in set(bench.pool_types))),
                                 rare_recall=float(np.mean([a == t for a, t in zip(v, yt) if t in set(bench.pool_types)]))) for k, v in ms.items()])
        save_csv(agg, "e2_rare_summary_dev")
        update_block("e2_rare", md_table(pt.round(2)))
    cal = pd.DataFrame(rows)
    save_csv(cal, "e3_calibration_dev")
    ag = pd.DataFrame(agree_rows)
    save_csv(ag, "e3_agreement_dev")
    make_calib_figs(figs, args.sources)
    t = cal[["source", "method", "accuracy", "conf_available", "ece", "auroc_correct", "aurc", "autofile_1pct", "autofile_2pct", "errors_1pct"]]
    update_block("e3_calib", md_table(t[t.source == GRID_SOURCE] if GRID_SOURCE in set(t.source) else t))
    update_block("e3_agree", md_table(ag[ag.source == GRID_SOURCE] if GRID_SOURCE in set(ag.source) else ag))


def make_calib_figs(figs: dict, sources) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    for source in sources:
        fig, ax = plt.subplots(figsize=(7, 4.4))
        for (s, name), df in figs.items():
            if s != source or name.startswith(("kev_s1_long", "kev_s2_long", "q25_s1_long")):
                continue
            conf = df["conf"].to_numpy()
            correct = (df["true"] == df["label"]).to_numpy()
            elig = np.array([l not in NEVER_AUTO and l != POOL for l in df["label"]]) & ~np.isnan(conf)
            if elig.sum() < 5:
                continue
            c = risk_coverage_curve(conf, correct, elig)
            ax.plot(c.coverage, c.risk, lw=1.2, label=name)
        for y in (0.01, 0.02):
            ax.axhline(y, color="#999", ls="--", lw=0.7)
        ax.set_ylim(0, 0.2)
        ax.set_xlabel("Coverage (tỉ lệ tài liệu được tự nhận / mọi tài liệu DEV)")
        ax.set_ylabel("Tỉ lệ sai trên phần được nhận")
        ax.set_title(f"Risk-coverage trên Track Z, DEV, nguồn {source}")
        ax.legend(fontsize=6, ncol=2)
        fig.tight_layout()
        fig.savefig(FIGS / f"risk_coverage_zs_{source}.png", dpi=130)
        plt.close(fig)


# ---------------------------------------------------------------------------
# E4 / E5 - cascade
# ---------------------------------------------------------------------------
def build_signals(D: Data, source: str, split: str, t3: str, final_test: bool = False, emb_n: int = 512, cache: dict | None = None) -> Signals:
    """Tín hiệu đầy đủ cho cascade: luật, TF-IDF, tầng-3 (t3 = id zero-shot hoặc 'embfs'), embedding few-shot (để đồng thuận)."""
    cache = cache if cache is not None else {}
    key = (source, split)
    docs = D.docs(source, split, final_test=final_test)
    if key not in cache:
        r_lab, r_lat = SG.rule_signals(docs)
        s_lab, s_conf, s_lat, cfg = SG.tfidf_signals(D, source, split, final_test)
        store = EmbeddingStore(emb_n)
        e_lab, e_conf, e_lat = SG.emb_fewshot_signals(D, source, split, store, final_test)
        cache[key] = dict(r=(r_lab, r_lat), s=(s_lab, s_conf, s_lat), e=(e_lab, e_conf, e_lat), cfg=cfg)
    c = cache[key]
    if t3 == "embfs":
        l_lab, l_conf, l_lat = [("" if x == UNKNOWN else x) for x in c["e"][0]], np.asarray(c["e"][1], float), np.asarray(c["e"][2], float)
    else:
        spec = SPECS[t3]
        if split == "DEV" and spec.get("icl"):
            l_lab, l_conf, l_lat, _ = SG.icl_cv_signals(D, source, spec)
        else:
            l_lab, l_conf, l_lat, _ = SG.llm_signals(D, source, split, spec, final_test)
        l_lab = ["" if x == UNKNOWN else x for x in l_lab]
    return Signals(rule=c["r"][0], s_label=c["s"][0], s_conf=np.asarray(c["s"][1], float), llm_label=l_lab, llm_conf=np.asarray(l_conf, float),
                   emb_label=[("" if x == UNKNOWN else x) for x in c["e"][0]], emb_conf=np.asarray(c["e"][1], float),
                   lat_rule=c["r"][1], lat_s=c["s"][2], lat_llm=np.asarray(l_lat, float), lat_emb=np.asarray(c["e"][2], float))


def entry_variants(main_t3: str, candidates: list[str]) -> list[dict]:
    """Các cấu hình cascade cần đo: đầy đủ với mỗi tầng-3 ứng viên + ablation (bỏ từng tầng) trên tầng-3 chính + baseline cổ điển."""
    ents = []
    for t3 in candidates:
        ents.append(dict(name=f"full[{t3}]", t3=t3, base=dict(use_rule=True, use_tfidf=True, use_llm=True)))
    ents += [
        dict(name="no_rule", t3=main_t3, base=dict(use_rule=False, use_tfidf=True, use_llm=True)),
        dict(name="no_tfidf", t3=main_t3, base=dict(use_rule=True, use_tfidf=False, use_llm=True)),
        dict(name="no_llm(rule+tfidf)", t3=main_t3, base=dict(use_rule=True, use_tfidf=True, use_llm=False)),
        dict(name="llm_only", t3=main_t3, base=dict(use_rule=False, use_tfidf=False, use_llm=True)),
        dict(name="tfidf_only(classical)", t3=main_t3, base=dict(use_rule=False, use_tfidf=True, use_llm=False)),
        dict(name="rule_only", t3=main_t3, base=dict(use_rule=True, use_tfidf=False, use_llm=False)),
    ]
    return ents


def quiet_latency_table() -> dict:
    """Độ trễ trung vị đo lúc máy rảnh (latency_vram_quiet.csv): rule, tfidf, và tầng-3 một bước của từng họ mô hình."""
    f = TABLES / "latency_vram_quiet.csv"
    if not f.exists():
        return {}
    q = pd.read_csv(f)
    g = lambda pre: float(q[q.method.astype(str).str.startswith(pre)].latency_ms_median.iloc[0]) if q.method.astype(str).str.startswith(pre).any() else np.nan
    return {"rule": g("rule_gate"), "tfidf": g("tfidf"), "kev_s1": g("kev_s1_name"), "q35_s1": g("q35_s1_short"), "q25_s1": g("q25_s1_short"), "embfs": g("bge-m3")}


def add_quiet_latency(df: pd.DataFrame) -> pd.DataFrame:
    """Cột `latency_quiet_est_ms`: ước tính độ trễ trung bình/tài liệu = tổng (tỉ lệ tài liệu tới tầng) x (độ trễ trung vị tầng đó đo lúc rảnh).
    Chỉ tính được khi tầng-3 là mô hình một bước đã đo (kev_s1_*, q35_s1_*, q25_s1_*, embfs); các dòng còn lại để trống.
    Độ trễ `latency_ms_*` đo trực tiếp khi gọi lần đầu có thể bị phồng bởi việc nhiều tiến trình dùng chung GPU."""
    ql = quiet_latency_table()
    out = []
    for _, r in df.iterrows():
        prm = json.loads(r["params"]) if isinstance(r["params"], str) else {}
        t3 = str(r["t3"])
        key = "embfs" if t3 == "embfs" else ("kev_s1" if t3.startswith("kev_s1") else "q35_s1" if t3.startswith("q35_s1") else "q25_s1" if t3.startswith("q25_s1") else None)
        v = 0.0
        ok = bool(ql)
        if prm.get("use_rule"):
            v += ql.get("rule", np.nan)
        if prm.get("use_tfidf"):
            v += (1 - (r["share_rule"] if prm.get("use_rule") else 0.0)) * ql.get("tfidf", np.nan)
        if prm.get("use_llm"):
            if key is None:
                ok = False
            else:
                reach = 1 - (r["share_rule"] if prm.get("use_rule") else 0.0) - (r["share_tfidf"] if prm.get("use_tfidf") else 0.0)
                v += reach * ql.get(key, np.nan)
        out.append(v if ok else np.nan)
    df = df.copy()
    df["latency_quiet_est_ms"] = out
    return df


def eval_cascade(sig: Signals, y: np.ndarray, p: CascadeParams, bench, boot=True) -> dict:
    res = run_cascade(sig, p)
    pred = np.where(res["accepted"], res["label"], UNKNOWN)
    correct = (res["label"].to_numpy() == y) & res["accepted"].to_numpy()
    cov, risk, k, err = selective_counts(res["accepted"].to_numpy(), res["label"].to_numpy() == y)
    zs = z_scores(bench, y.tolist(), pred.tolist(), boot=boot)
    ts = tier_shares(res, y)
    out = dict(coverage=cov, risk=risk, n_accepted=k, errors=err, risk_upper95_exact=clopper_pearson_upper(err, k) if k else np.nan,
               accuracy=zs["accuracy"], macro_f1=zs["macro_f1"], n_types_scored=zs["n_types_scored"], rare_recall=zs["rare_recall"],
               latency_ms_mean=float(res["latency_ms"].mean()), latency_ms_p95=float(np.percentile(res["latency_ms"], 95)),
               human_share=1 - cov, **{f"share_{r.tier}": r.share for r in ts.itertuples()},
               **{f"wrong_{r.tier}": r.wrong for r in ts.itertuples() if r.tier != "human"})
    if boot:
        out.update({k2: zs[k2] for k2 in ("accuracy_lo", "accuracy_hi", "macro_f1_lo", "macro_f1_hi")})
    return out, res, pred


def crossfit(sig: Signals, docs, y: np.ndarray, base: CascadeParams, tol: float, modes, seed: int = 0) -> dict:
    """Ước lượng trung thực trên DEV: ngưỡng chọn trên 4 fold, áp lên fold còn lại; gộp 5 fold."""
    folds = np.array([d.folds[seed] for d in docs])
    acc = np.zeros(len(docs), bool)
    corr = np.zeros(len(docs), bool)
    for f in sorted(set(folds)):
        tr, te = np.where(folds != f)[0], np.where(folds == f)[0]
        p, _ = tune(sig.take(tr), y[tr], base, tol, modes)
        r = run_cascade(sig.take(te), p)
        acc[te] = r["accepted"].to_numpy()
        corr[te] = r["label"].to_numpy() == y[te]
    cov, risk, k, err = selective_counts(acc, corr)
    return dict(cf_coverage=cov, cf_risk=risk, cf_n_accepted=k, cf_errors=err)


# ứng viên tầng-3 ngoài "tốt nhất mỗi họ": biến thể hai bước cho confidence có thông tin (xem E3)
CASCADE_EXTRA = ["q35_s2_short_c2000", "kev_s2_short_c2000"]


def candidate_t3(source: str) -> list[str]:
    best = best_ids()
    c = [best[f] for f in ("kev", "q35", "q25") if f in best] + CASCADE_EXTRA
    c = [m for m in dict.fromkeys(c) if pred_path(f"zs_{m}", source, "DEV").exists()]
    return c + ["embfs"]


def stage_cascade(args):
    D = Data()
    bench = D.bench
    sel = load_sel()
    sel.setdefault("cascade", {})
    all_rows = []
    cache: dict = {}
    for source in args.sources:
        dev = D.docs(source, "DEV")
        y = np.array([d.label for d in dev])
        cands = candidate_t3(source)
        if not cands:
            log(f"bỏ qua {source}: chưa có dự đoán zero-shot")
            continue
        # tầng-3 CHÍNH (dùng cho ablation và so sánh): chọn MỘT lần, theo macro-F1 DEV của chính mô hình đó đứng một mình (E2/E1) trên nguồn triển khai GRID_SOURCE,
        # KHÔNG theo kết quả cascade (các ứng viên hòa nhau trong cascade vì cổng luật + TF-IDF đã quyết định ~95% tài liệu). Nguồn khác dùng lại cùng lựa chọn.
        e2all = pd.read_csv(TABLES / "e2_zeroshot_dev.csv")
        e1z = pd.read_csv(TABLES / "e1_embed_track_z_dev.csv")
        standalone = {m: float(e2all[(e2all.method == m) & (e2all.source == GRID_SOURCE)].macro_f1.iloc[0]) for m in cands if m != "embfs" and len(e2all[(e2all.method == m) & (e2all.source == GRID_SOURCE)])}
        n_emb = sel.get("embed", {}).get(GRID_SOURCE, {}).get("Z", {}).get("n_chars", args.emb_n)
        standalone["embfs"] = float(e1z[(e1z.source == GRID_SOURCE) & (e1z.n_chars == n_emb) & (e1z.method == "centroid_min2")].oof_macro_f1.iloc[0])
        global_main = max((m for m in cands if m in standalone), key=lambda m: standalone[m])
        entries = entry_variants(global_main, cands)
        emb_n = sel.get("embed", {}).get(source, {}).get("Z", {}).get("n_chars", args.emb_n)
        sigs = {t3: build_signals(D, source, "DEV", t3, False, emb_n, cache) for t3 in {e["t3"] for e in entries}}
        chosen = []
        full_scores = {}
        for tol in (0.01, 0.02):
            for e in entries:
                sig = sigs[e["t3"]]
                base = CascadeParams(**e["base"])
                modes = ("none", "s", "emb", "s_or_emb") if (base.use_llm and e["t3"] != "embfs") else (("none", "s") if base.use_llm else ("none",))
                p, st = tune(sig, y, base, tol, modes)
                m, res, pred = eval_cascade(sig, y, p, bench)
                cf = crossfit(sig, dev, y, base, tol, modes)
                row = dict(source=source, name=e["name"], t3=e["t3"], max_error=tol, params=json.dumps(_params_dict(p)), **m, **cf)
                all_rows.append(row)
                chosen.append(dict(source=source, name=e["name"], t3=e["t3"], max_error=tol, base=e["base"], params=_params_dict(p)))
                if e["name"].startswith("full[") and tol == 0.01:
                    full_scores[e["t3"]] = (round(cf["cf_coverage"], 3), -cf["cf_risk"] if cf["cf_risk"] == cf["cf_risk"] else 0.0, -m["latency_ms_mean"])
        main_t3 = global_main
        sel["cascade_main_t3"] = main_t3
        sel.setdefault("cascade_standalone_macro_f1", {})[source] = standalone
        if False:
            all_rows = [r for r in all_rows if not (r["source"] == source and not r["name"].startswith("full["))]
            chosen = [c for c in chosen if not (c["source"] == source and not c["name"].startswith("full["))]
            for tol in (0.01, 0.02):
                for e in [x for x in entry_variants(main_t3, cands) if not x["name"].startswith("full[")]:
                    sig = sigs[e["t3"]] if e["t3"] in sigs else build_signals(D, source, "DEV", e["t3"], False, emb_n, cache)
                    base = CascadeParams(**e["base"])
                    modes = ("none", "s", "emb", "s_or_emb") if (base.use_llm and e["t3"] != "embfs") else (("none", "s") if base.use_llm else ("none",))
                    p, st = tune(sig, y, base, tol, modes)
                    m, res, pred = eval_cascade(sig, y, p, bench)
                    cf = crossfit(sig, dev, y, base, tol, modes)
                    all_rows.append(dict(source=source, name=e["name"], t3=e["t3"], max_error=tol, params=json.dumps(_params_dict(p)), **m, **cf))
                    chosen.append(dict(source=source, name=e["name"], t3=e["t3"], max_error=tol, base=e["base"], params=_params_dict(p)))
        sel["cascade"][source] = dict(main_t3=main_t3, entries=chosen, tfidf_config=cache[(source, "DEV")]["cfg"], emb_n=emb_n)
        log(f"E4 {source}: tầng-3 chính = {main_t3}")
    df = add_quiet_latency(pd.DataFrame(all_rows))
    save_csv(df, "e4_cascade_dev")
    save_sel(sel)
    render_e4_dev()
    make_cascade_fig("e4_cascade_dev", "cascade_tier_shares_dev.png", "Cascade trên DEV (mức sai <= 1%): tầng nào quyết định bao nhiêu tài liệu")


def make_cascade_fig(csv_name: str, fig_name: str, title: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    f = TABLES / f"{csv_name}.csv"
    if not f.exists():
        return
    r = pd.read_csv(f)
    r = r[(r.max_error == 0.01)]
    srcs = [x for x in SOURCES_MAIN if x in set(r.source)]
    fig, axes = plt.subplots(1, len(srcs), figsize=(5.2 * len(srcs), 4.2), squeeze=False)
    cols = {"share_rule": "#1b9e77", "share_tfidf": "#7570b3", "share_llm": "#d95f02", "share_human": "#999999"}
    labs = {"share_rule": "tầng 1 luật", "share_tfidf": "tầng 2 TF-IDF", "share_llm": "tầng 3 LLM/embedding", "share_human": "tầng 4 người"}
    for ax, src in zip(axes[0], srcs):
        g = r[r.source == src].reset_index(drop=True)
        bottom = np.zeros(len(g))
        for c in cols:
            ax.barh(range(len(g)), g[c].to_numpy(), left=bottom, color=cols[c], label=labs[c])
            bottom += g[c].to_numpy()
        ax.set_yticks(range(len(g)))
        ax.set_yticklabels(g["name"].tolist(), fontsize=6)
        ax.invert_yaxis()
        ax.set_xlim(0, 1)
        ax.set_title(src, fontsize=9)
        ax.set_xlabel("Tỉ lệ tài liệu được từng tầng quyết định")
    axes[0][0].legend(fontsize=6, loc="lower left")
    fig.suptitle(title, fontsize=9)
    fig.tight_layout()
    fig.savefig(FIGS / fig_name, dpi=130)
    plt.close(fig)


def _params_dict(p: CascadeParams) -> dict:
    d = asdict(p)
    for k in ("th_s", "th_llm"):
        d[k] = None if not np.isfinite(d[k]) else float(d[k])
    return d


def _params_from(d: dict) -> CascadeParams:
    d = dict(d)
    for k in ("th_s", "th_llm"):
        if d.get(k) is None:
            d[k] = float("inf")
    return CascadeParams(**d)


def render_e4_dev():
    p = TABLES / "e4_cascade_dev.csv"
    if not p.exists():
        return
    r = pd.read_csv(p)
    t = r.copy()
    t["auto-file (DEV, ngưỡng chọn trên chính DEV)"] = t.coverage
    cols = ["source", "name", "max_error", "coverage", "risk", "errors", "n_accepted", "cf_coverage", "cf_risk", "cf_errors", "macro_f1", "accuracy",
            "share_rule", "share_tfidf", "share_llm", "share_human", "latency_quiet_est_ms"]
    update_block("e4_dev", md_table(t[cols]))


# ---------------------------------------------------------------------------
# Độ trễ + VRAM khi máy rảnh (bỏ qua cache bằng tag/muối riêng)
# ---------------------------------------------------------------------------
def stage_latency(args):
    D = Data()
    source = GRID_SOURCE
    dev = D.docs(source, "DEV")[:40]
    best = best_ids()
    ids = [best[f] for f in ("kev", "q35", "q25") if f in best]
    rows = []
    for mid in ids:
        spec = SPECS[mid]
        tag = f"latency-bench-{int(time.time())}"
        p = ZeroShotPredictor(spec, D.z_classes, tag=tag)
        if spec.get("icl"):
            p.fit(D.docs(source, "DEV")[40:])
        p.predict(dev[:2])       # khởi động (nạp mô hình)
        pr = p.predict(dev[2:])
        lat = np.asarray(pr.latency_ms)
        vr = vram_snapshot()
        ls = latency_summary(lat[lat > 0])
        rows.append(dict(method=mid, n_timed=len(lat), latency_ms_median=ls["median_ms"], latency_ms_p95=ls["p95_ms"],
                         vram_mb=(vr["kev_vram_mb"] if spec["engine"] == "kev" else vr["ollama"].get(spec["model"])), at=dt.datetime.now().isoformat(timespec="seconds")))
        log("latency", rows[-1])
    store = EmbeddingStore(512, cache_name=f"emb_lat_{int(time.time())}")
    store.get(dev[:2])
    store.get(dev[2:])
    el = np.array([store.doc_latency_ms(d) for d in dev[2:]])
    ls = latency_summary(el)
    vr = vram_snapshot()
    rows.append(dict(method="bge-m3 embedding (n=512)", n_timed=len(el), latency_ms_median=ls["median_ms"], latency_ms_p95=ls["p95_ms"], vram_mb=vr["ollama"].get("bge-m3:latest"),
                     at=dt.datetime.now().isoformat(timespec="seconds")))
    # TF-IDF + luật
    s_lab, s_conf, s_lat, cfg = SG.tfidf_signals(D, source, "DEV")
    r_lab, r_lat = SG.rule_signals(dev)
    rows.append(dict(method=f"tfidf ({cfg})", n_timed=len(s_lat), latency_ms_median=float(np.median(s_lat)), latency_ms_p95=float(np.percentile(s_lat, 95)), vram_mb=0))
    rows.append(dict(method="rule_gate", n_timed=len(r_lat), latency_ms_median=float(np.median(r_lat)), latency_ms_p95=float(np.percentile(r_lat, 95)), vram_mb=0))
    save_csv(pd.DataFrame(rows), "latency_vram_quiet")


def stage_devrows(args):
    """Thêm các dòng DEV của thí nghiệm 02 vào results_table.csv (chỉ một lần; dấu vết ở tables/dev_rows_appended.json)."""
    marker = TABLES / "dev_rows_appended.json"
    if marker.exists() and not args.force:
        raise SystemExit("Các dòng DEV đã được thêm vào results_table.csv (dùng --force nếu thật sự muốn thêm lần nữa).")
    bench = Data().bench
    run_id = new_run_id()
    n = 0
    kw = dict(labels_file=LABELS.name, labels_sha=bench.labels_sha)
    e1s = pd.read_csv(TABLES / "e1_embed_track_s_dev.csv")
    sel = load_sel()
    for src, e in sel.get("embed", {}).items():
        r = e1s[(e1s.source == src) & (e1s.n_chars == e["S"]["n_chars"]) & (e1s.method == e["S"]["method"])].iloc[0]
        append_result_row(dict(run_id=run_id, method=f"bge-m3 n={r.n_chars} {r.method}", track="S", text_source=src, split="DEV_CV", n=237, accuracy=r.accuracy_mean,
                               macro_f1=r.macro_f1_mean, macro_f1_std=r.macro_f1_std, notes="E1; mean±std over 3 seeds x 5 folds; best of 12 embedding configs on DEV", **kw)); n += 1
    e1z = pd.read_csv(TABLES / "e1_embed_track_z_dev.csv")
    for _, r in e1z.iterrows():
        append_result_row(dict(run_id=run_id, method=f"bge-m3 n={r.n_chars} {r.method}", track="Z", text_source=r.source, split="DEV_ALL", n=int(r.oof_n),
                               accuracy=r.oof_accuracy, accuracy_ci_lo=r.oof_accuracy_lo, accuracy_ci_hi=r.oof_accuracy_hi, macro_f1=r.oof_macro_f1, macro_f1_ci_lo=r.oof_macro_f1_lo,
                               macro_f1_ci_hi=r.oof_macro_f1_hi, coverage=r.oof_coverage, acc_on_covered=r.oof_acc_on_covered,
                               notes=f"E1 Track Z; out-of-fold seed 0; macro-F1 over {int(r.oof_n_types_scored)} types >=3 docs; rare recall {r.oof_rare_recall:.3f}", **kw)); n += 1
    e2 = pd.read_csv(TABLES / "e2_zeroshot_dev.csv")
    for _, r in e2.iterrows():
        append_result_row(dict(run_id=run_id, method=f"zeroshot:{r.method}", track="Z", text_source=r.source, split="DEV_ALL", n=int(r.n), accuracy=r.accuracy, accuracy_ci_lo=r.accuracy_lo,
                               accuracy_ci_hi=r.accuracy_hi, macro_f1=r.macro_f1, macro_f1_ci_lo=r.macro_f1_lo, macro_f1_ci_hi=r.macro_f1_hi, coverage=r.coverage,
                               acc_on_covered=r.acc_on_covered, latency_ms_median=r.latency_ms_median, latency_ms_p95=r.latency_ms_p95,
                               notes=f"E2 zero-shot full taxonomy; {int(r.n_types_scored)} types >=3 docs; rare recall {r.rare_recall:.3f}; model={r.model}; latency under shared load", **kw)); n += 1
    e4 = pd.read_csv(TABLES / "e4_cascade_dev.csv")
    for _, r in e4[e4.max_error == 0.01].iterrows():
        append_result_row(dict(run_id=run_id, method=f"cascade:{r['name']}@err1%", track="Z", text_source=r.source, split="DEV_ALL", n=len(Data().docs(r.source, "DEV")),
                               accuracy=r.accuracy, accuracy_ci_lo=r.accuracy_lo, accuracy_ci_hi=r.accuracy_hi, macro_f1=r.macro_f1, macro_f1_ci_lo=r.macro_f1_lo, macro_f1_ci_hi=r.macro_f1_hi,
                               coverage=r.coverage, acc_on_covered=1 - r.risk if r.risk == r.risk else "", latency_ms_p95=r.latency_ms_p95,
                               notes=f"E4 cascade; thresholds tuned ON this DEV set (in-sample); cross-fit coverage {r.cf_coverage:.3f} risk {r.cf_risk:.3f}; mean latency {r.latency_ms_mean:.0f} ms", **kw)); n += 1
    dump_json(marker, dict(run_id=run_id, rows=n, time=dt.datetime.now().isoformat(timespec="seconds")))
    log(f"đã thêm {n} dòng DEV vào results_table.csv")


def stage_cost(args):
    from cost_table import build_cost_table

    df = build_cost_table(GRID_SOURCE)
    save_csv(df, "cost_privacy")
    show = df[["design", "on_prem", "labelled_data", "new_type_no_retrain", "vram_gb", "latency_ms_median", "latency_ms_p95", "docs_per_hour", "quality", "services"]].copy()
    for c, d in (("vram_gb", 2), ("latency_ms_median", 0), ("latency_ms_p95", 0), ("docs_per_hour", 0)):
        show[c] = show[c].round(d)
    update_block("cost", md_table(show))


# ---------------------------------------------------------------------------
# TEST (khóa)
# ---------------------------------------------------------------------------
def final_test(args):
    sel = load_sel()
    if not sel.get("cascade"):
        raise SystemExit("Chưa có dev_selection_02.json (chạy các giai đoạn DEV trước).")
    D = Data()
    bench = D.bench
    if SMOKE:
        _orig = D.docs
        D.docs = lambda source, split="DEV", final_test=False: _orig(source, "DEV" if split == "TEST" else split)
        log("SMOKE: đường TEST chạy trên tài liệu DEV (không đọc TEST)")
    reg = json.loads(REG02.read_text(encoding="utf-8")) if REG02.exists() else {}
    if bench.labels_sha in reg and not args.allow_rescore and not SMOKE:
        raise SystemExit(f"TEST đã được chấm cho bộ nhãn {bench.labels_sha} lúc {reg[bench.labels_sha]['time']}; từ chối chấm lại.")
    run_id = new_run_id()
    kev_name = kev_model_name()
    if kev_name != "jaredpalmer/kev-0.8b":
        raise SystemExit(f"Server Kev đang giữ {kev_name}; cần kev-0.8b để chấm TEST nhất quán với DEV.")
    log("TEST: chấm một lần các cấu hình đã chốt trên DEV")
    rows, zs_rows, preds_store, agree_test = [], [], {}, []
    cache: dict = {}
    for source, cfgd in sel["cascade"].items():
        test = D.docs(source, "TEST", final_test=True)
        y = np.array([d.label for d in test])
        t3s = sorted({e["t3"] for e in cfgd["entries"]})
        sigs = {t3: build_signals(D, source, "TEST", t3, True, cfgd["emb_n"], cache) for t3 in t3s}
        # zero-shot đơn lẻ (E2 TEST) cho các id được chốt
        for t3 in t3s:
            if t3 == "embfs":
                continue
            s = sigs[t3]
            lab = ["UNKNOWN" if l == "" else l for l in s.llm_label]
            zs = z_scores(bench, y.tolist(), lab)
            zs_rows.append(dict(method=t3, source=source, **zs, latency_ms_median=float(np.median(s.lat_llm[s.lat_llm > 0])) if (s.lat_llm > 0).any() else np.nan,
                                latency_ms_p95=float(np.percentile(s.lat_llm[s.lat_llm > 0], 95)) if (s.lat_llm > 0).any() else np.nan))
            save_preds(f"zs_{t3}", source, "TEST", test, lab, s.llm_conf, s.lat_llm)
        # đồng thuận (không ngưỡng) trên TEST cho các tổ hợp đã định sẵn ở DEV (E3)
        any_sig = next(iter(sigs.values()))
        lab_t = {"rule": list(any_sig.rule), "tfidf": [("" if l == POOL else l) for l in any_sig.s_label]}
        if any_sig.emb_label is not None:
            lab_t["emb"] = list(any_sig.emb_label)
        for fam, mid in best_ids().items():
            if mid in sigs:
                lab_t[fam] = list(sigs[mid].llm_label)
        agree_test += agreement_rows(source, lab_t, y)
        for e in cfgd["entries"]:
            sig = sigs[e["t3"]]
            p = _params_from(e["params"])
            m, res, pred = eval_cascade(sig, y, p, bench)
            acc = res["accepted"].to_numpy()
            correct = res["label"].to_numpy() == y
            ap = apply_threshold(acc.astype(float), correct, np.ones(len(y), bool), 1.0)   # coverage/risk kèm CI bootstrap
            rows.append(dict(source=source, name=e["name"], t3=e["t3"], max_error=e["max_error"], n_docs=len(y), params=json.dumps(e["params"]), **m,
                             coverage_lo=ap["coverage_lo"], coverage_hi=ap["coverage_hi"], risk_lo=ap["risk_lo"], risk_hi=ap["risk_hi"]))
            preds_store[(source, e["name"], e["max_error"])] = (pred, acc, correct)
    # --- E1 trên TEST: embedding tốt nhất theo DEV (Track S: LR/centroid/kNN; Track Z: few-shot centroid)
    e1_rows = []
    for source, e in sel.get("embed", {}).items():
        dev, test = D.docs(source, "DEV"), D.docs(source, "TEST", final_test=True)
        S, m = D.s_classes, e["S"]["method"]
        store = EmbeddingStore(e["S"]["n_chars"])
        pred = (EmbLR(store, S, float(m[4:])) if m.startswith("lr_C") else EmbCentroid(store, S, "S", 1) if m == "centroid" else EmbKNN(store, S, "S", int(m[3:])))
        pr = pred.fit(dev).predict(test)
        yt = [d.label_s for d in test]
        bm = bootstrap_metrics(yt, pr.labels, S)
        e1_rows.append(dict(source=source, track="S", method=f"bge-m3 n={e['S']['n_chars']} {m}", n=len(test), accuracy=bm["accuracy"][0], accuracy_lo=bm["accuracy"][1],
                            accuracy_hi=bm["accuracy"][2], macro_f1=bm["macro_f1"][0], macro_f1_lo=bm["macro_f1"][1], macro_f1_hi=bm["macro_f1"][2]))
        labs, conf_, _ = SG.emb_fewshot_signals(D, source, "TEST", EmbeddingStore(e["Z"]["n_chars"]), True)
        zs = z_scores(bench, [d.label for d in test], labs)
        e1_rows.append(dict(source=source, track="Z", method=f"bge-m3 n={e['Z']['n_chars']} few-shot centroid (>=2 mẫu/loại)", n=len(test), accuracy=zs["accuracy"],
                            accuracy_lo=zs["accuracy_lo"], accuracy_hi=zs["accuracy_hi"], macro_f1=zs["macro_f1"], macro_f1_lo=zs["macro_f1_lo"], macro_f1_hi=zs["macro_f1_hi"],
                            n_types_scored=zs["n_types_scored"], rare_recall=zs["rare_recall"]))
    save_csv(pd.DataFrame(e1_rows), "e1_embed_test")
    update_block("e1_test", md_table(pd.DataFrame([{**r, "macro_f1 [CI]": fmt_ci(r["macro_f1"], r["macro_f1_lo"], r["macro_f1_hi"]),
                                                    "accuracy [CI]": fmt_ci(r["accuracy"], r["accuracy_lo"], r["accuracy_hi"])} for r in e1_rows])
                                  [["source", "track", "method", "n", "macro_f1 [CI]", "accuracy [CI]", "n_types_scored", "rare_recall"]]))
    for r in e1_rows:
        append_result_row(dict(run_id=run_id, method=r["method"], track=r["track"], text_source=r["source"], split="TEST", n=r["n"], accuracy=r["accuracy"],
                               accuracy_ci_lo=r["accuracy_lo"], accuracy_ci_hi=r["accuracy_hi"], macro_f1=r["macro_f1"], macro_f1_ci_lo=r["macro_f1_lo"],
                               macro_f1_ci_hi=r["macro_f1_hi"], labels_file=LABELS.name, labels_sha=bench.labels_sha, notes="E1 embedding bge-m3 (Ollama); config chosen on DEV"))
    ag_t = pd.DataFrame(agree_test)
    save_csv(ag_t, "e3_agreement_test")
    update_block("e3_agree_test", md_table(ag_t[ag_t.source == GRID_SOURCE]))
    df = add_quiet_latency(pd.DataFrame(rows))
    save_csv(df, "e4_cascade_test")
    make_cascade_fig("e4_cascade_test", "cascade_tier_shares_test.png", "Cascade trên TEST (ngưỡng chọn trên DEV, mức sai <= 1%)")
    zt = pd.DataFrame(zs_rows)
    save_csv(zt, "e2_zeroshot_test")
    zt2 = zt.assign(**{"accuracy [CI]": [fmt_ci(a_, l_, h_) for a_, l_, h_ in zip(zt.accuracy, zt.accuracy_lo, zt.accuracy_hi)],
                       "macro-F1 [CI]": [fmt_ci(a_, l_, h_) for a_, l_, h_ in zip(zt.macro_f1, zt.macro_f1_lo, zt.macro_f1_hi)]})
    update_block("e2_test", md_table(zt2[["method", "source", "n", "accuracy [CI]", "macro-F1 [CI]", "n_types_scored", "coverage", "rare_recall", "freq_recall", "latency_ms_median", "latency_ms_p95"]]))
    # --- so sánh ghép cặp: cascade chính vs mô hình cổ điển tốt nhất (TF-IDF + ngưỡng) cùng nguồn, cùng mức sai
    pair_rows = []
    for source, cfgd in sel["cascade"].items():
        y = np.array([d.label for d in D.docs(source, "TEST", final_test=True)])
        for tol, main in [(t_, e_["name"]) for t_ in (0.01, 0.02) for e_ in cfgd["entries"] if e_["name"].startswith("full[") and e_["max_error"] == t_]:
            a, b = preds_store[(source, main, tol)], preds_store[(source, "tfidf_only(classical)", tol)]
            r = paired_bootstrap(y.tolist(), a[0].tolist(), b[0].tolist(), bench.z_classes, min_support=3)
            rng = np.random.default_rng(BOOT_SEED)
            idx = rng.integers(0, len(y), size=(BOOT_N, len(y)))
            d_cov, d_ok, d_err = [], [], []
            for ib in idx:
                d_cov.append(a[1][ib].mean() - b[1][ib].mean())
                d_ok.append((a[1][ib] & a[2][ib]).mean() - (b[1][ib] & b[2][ib]).mean())
                d_err.append((a[1][ib] & ~a[2][ib]).mean() - (b[1][ib] & ~b[2][ib]).mean())
            q = lambda v: (float(np.mean(v)), float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5)))
            pair_rows.append(dict(source=source, max_error=tol, A=main, B="tfidf_only(classical)",
                                  d_macro_f1=r["macro_f1"]["diff"], d_macro_f1_lo=r["macro_f1"]["ci_lo"], d_macro_f1_hi=r["macro_f1"]["ci_hi"], macro_f1_p=r["macro_f1"]["p_value"],
                                  d_accuracy=r["accuracy"]["diff"], d_accuracy_lo=r["accuracy"]["ci_lo"], d_accuracy_hi=r["accuracy"]["ci_hi"], accuracy_p=r["accuracy"]["p_value"],
                                  d_autofile=float(a[1].mean() - b[1].mean()), d_autofile_lo=q(d_cov)[1], d_autofile_hi=q(d_cov)[2],
                                  d_correct_autofiled=float((a[1] & a[2]).mean() - (b[1] & b[2]).mean()), d_correct_lo=q(d_ok)[1], d_correct_hi=q(d_ok)[2],
                                  d_wrong_autofiled=float((a[1] & ~a[2]).mean() - (b[1] & ~b[2]).mean()), d_wrong_lo=q(d_err)[1], d_wrong_hi=q(d_err)[2]))
    save_csv(pd.DataFrame(pair_rows), "e4_cascade_test_paired")
    # --- bảng kết quả chung
    for r in rows:
        if r["max_error"] != 0.01:
            continue
        append_result_row(dict(run_id=run_id, method=f"cascade:{r['name']}@err1%", track="Z", text_source=r["source"], split="TEST", n=int(r["n_docs"]),
                               accuracy=r["accuracy"], accuracy_ci_lo=r["accuracy_lo"], accuracy_ci_hi=r["accuracy_hi"], macro_f1=r["macro_f1"],
                               macro_f1_ci_lo=r["macro_f1_lo"], macro_f1_ci_hi=r["macro_f1_hi"], coverage=r["coverage"], acc_on_covered=1 - r["risk"] if r["risk"] == r["risk"] else "",
                               latency_ms_median="", latency_ms_p95=r["latency_ms_p95"], labels_file=LABELS.name, labels_sha=bench.labels_sha,
                               notes=f"E4 cascade full taxonomy; t3={r['t3']}; thresholds from DEV OOF; mean latency {r['latency_ms_mean']:.0f} ms/doc; Kev={kev_name}"))
    for r in zs_rows:
        append_result_row(dict(run_id=run_id, method=f"zeroshot:{r['method']}", track="Z", text_source=r["source"], split="TEST", n=r["n"], accuracy=r["accuracy"],
                               accuracy_ci_lo=r["accuracy_lo"], accuracy_ci_hi=r["accuracy_hi"], macro_f1=r["macro_f1"], macro_f1_ci_lo=r["macro_f1_lo"],
                               macro_f1_ci_hi=r["macro_f1_hi"], coverage=r["coverage"], acc_on_covered=r["acc_on_covered"],
                               latency_ms_median=r["latency_ms_median"], latency_ms_p95=r["latency_ms_p95"], labels_file=LABELS.name, labels_sha=bench.labels_sha,
                               notes=f"E2 zero-shot full taxonomy; macro-F1 over {r['n_types_scored']} types >=3 docs; Kev={kev_name}"))
    if not SMOKE:
        reg[bench.labels_sha] = dict(time=dt.datetime.now().isoformat(timespec="seconds"), run_id=run_id, sources=list(sel["cascade"].keys()), kev_model=kev_name)
        dump_json(REG02, reg)
    render_e4_test()
    log("TEST xong.")


def render_e4_test():
    p = TABLES / "e4_cascade_test.csv"
    if not p.exists():
        return
    r = pd.read_csv(p)
    from cost_table import _cp

    r["auto-file [CI bootstrap]"] = [fmt_ci(a, l, h) for a, l, h in zip(r.coverage, r.coverage_lo, r.coverage_hi)]
    r["auto-file [Clopper-Pearson]"] = [fmt_ci(k / n, *_cp(int(k), int(n))) for k, n in zip(r.n_accepted, r.n_docs)]
    r["sai/được nhận [CI]"] = [fmt_ci(a, l, h) if a == a else "n/a" for a, l, h in zip(r.risk, r.risk_lo, r.risk_hi)]
    r["macro-F1 [CI]"] = [fmt_ci(a, l, h) for a, l, h in zip(r.macro_f1, r.macro_f1_lo, r.macro_f1_hi)]
    cols = ["source", "name", "max_error", "auto-file [CI bootstrap]", "auto-file [Clopper-Pearson]", "errors", "n_accepted", "risk_upper95_exact", "macro-F1 [CI]", "accuracy",
            "share_rule", "share_tfidf", "share_llm", "share_human", "latency_ms_mean", "latency_ms_p95", "latency_quiet_est_ms"]
    update_block("e4_test", md_table(r[cols]))
    pp = TABLES / "e4_cascade_test_paired.csv"
    if pp.exists():
        q = pd.read_csv(pp)
        q["Δ auto-file [CI]"] = [fmt_ci(a, l, h) for a, l, h in zip(q.d_autofile, q.d_autofile_lo, q.d_autofile_hi)]
        q["Δ đúng được tự xếp [CI]"] = [fmt_ci(a, l, h) for a, l, h in zip(q.d_correct_autofiled, q.d_correct_lo, q.d_correct_hi)]
        q["Δ sai được tự xếp [CI]"] = [fmt_ci(a, l, h) for a, l, h in zip(q.d_wrong_autofiled, q.d_wrong_lo, q.d_wrong_hi)]
        q["Δ macro-F1 [CI]"] = [fmt_ci(a, l, h) for a, l, h in zip(q.d_macro_f1, q.d_macro_f1_lo, q.d_macro_f1_hi)]
        update_block("e4_paired", md_table(q[["source", "max_error", "A", "B", "Δ macro-F1 [CI]", "macro_f1_p", "Δ auto-file [CI]", "Δ đúng được tự xếp [CI]", "Δ sai được tự xếp [CI]"]]))


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", choices=["embed", "zeroshot", "zeroshot_sources", "calib", "cascade", "latency", "devrows", "cost", "report"], help="giai đoạn DEV")
    ap.add_argument("--final-test", action="store_true", help="chấm TEST khóa (một lần) cho các cấu hình đã chốt")
    ap.add_argument("--allow-rescore", action="store_true")
    ap.add_argument("--sources", nargs="*", default=None)
    ap.add_argument("--family", choices=["kev", "ollama", "all"], default="all")
    ap.add_argument("--methods", nargs="*", default=None)
    ap.add_argument("--max-docs", type=int, default=None, help="chạy thử trên N tài liệu đầu (không ghi bảng)")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--emb-n", type=int, default=512, help="số ký tự embedding dùng trong cascade")
    args = ap.parse_args()
    if args.sources is None:
        args.sources = [GRID_SOURCE] if args.stage in ("zeroshot",) else list(SOURCES_MAIN)
    if args.final_test:
        final_test(args)
    elif args.stage == "embed":
        stage_embed(args)
    elif args.stage == "zeroshot":
        stage_zeroshot(args)
    elif args.stage == "zeroshot_sources":
        stage_zeroshot_sources(args)
    elif args.stage == "calib":
        stage_calib(args)
    elif args.stage == "cascade":
        stage_cascade(args)
    elif args.stage == "latency":
        stage_latency(args)
    elif args.stage == "devrows":
        stage_devrows(args)
    elif args.stage == "cost":
        stage_cost(args)
    elif args.stage == "report":
        render_curated()
        render_e5()
        render_e1()
        render_e3()
        render_e2()
        render_e4_dev()
        render_e4_test()
        stage_cost(args)
    else:
        ap.error("chọn --stage hoặc --final-test")


if __name__ == "__main__":
    main()
