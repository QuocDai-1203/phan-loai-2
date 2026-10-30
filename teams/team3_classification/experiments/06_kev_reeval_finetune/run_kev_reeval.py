"""run_kev_reeval.py - Thí nghiệm 06: đo lại Kev-0.8B (máy chủ mới, /v1/models) trên DEV, so cặp với Kev cũ và Qwen3.5-4B.

Giai đoạn:
  run      gọi Kev (có DiskCache) cho các biến thể trên 237 tài liệu DEV (ocr_v2_p12, 2000 ký tự, như thí nghiệm 02) và 28 lát cắt đáp án của 8 tệp ghép (05).
  analyze  tính số đo + ghi bảng vào results/06_kev_reeval_finetune/tables và in Markdown.
KHÔNG mở TEST. Biến thể `name_kw` và `perm_name` chỉ được chọn/đánh giá trên DEV (đánh dấu trong RESULTS.md).
Chạy (gốc repo): .venv\\Scripts\\python.exe -X utf8 teams\\team3_classification\\experiments\\06_kev_reeval_finetune\\run_kev_reeval.py --stage run|analyze
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
EXP02 = HERE.parent / "02_llm_and_cascade"
EXP05 = HERE.parent / "05_composite_slices"
for p in (REPO, EXP02):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import requests  # noqa: E402

from common import Data, dump_json, load_taxonomy_json, log  # noqa: E402  (thí nghiệm 02)
from src.classification.llm_cache import DiskCache, make_key  # noqa: E402
from src.classification.zero_shot import INSTR_VI, KevClient, build_label_set, clean_prompt_text, kev_answer  # noqa: E402

BASE = "http://127.0.0.1:8009"
URL = f"{BASE}/v1/systemone"
PERM_URL = f"{BASE}/v1/systemone/permute"
TAG = "kev-0.8b-srv20261016"          # khác tag cũ ("kev-0.8b") để KHÔNG dùng lại cache của lần đo giai đoạn 1
SOURCE = "ocr_v2_p12"
CHARS = 2000
N_PERM = 6
OUT = REPO / "teams" / "team3_classification" / "results" / "06_kev_reeval_finetune"
TABLES = OUT / "tables"
CACHE = HERE / "_cache"
for d in (TABLES, CACHE):
    d.mkdir(parents=True, exist_ok=True)
VARIANTS = ["name", "name_kw", "perm_name"]


def server_info() -> dict:
    j = requests.get(f"{BASE}/v1/models", timeout=30).json()
    m = j["models"][0]
    return {k: m.get(k) for k in ("name", "run", "base", "lora", "temperature", "release_date", "dtype", "backend")}


def criteria(variant: str) -> dict:
    tax = load_taxonomy_json()
    ls = build_label_set(tax, "name")
    if variant in ("name", "perm_name"):
        return {i: ls.desc[i] for i in ls.ids}
    kw = {c["id"]: c.get("keywords") or [] for c in tax["classes"]}
    out = {}
    for i in ls.ids:
        ks = [str(k)[:40] for k in kw[i][:4]]
        out[i] = f"{ls.desc[i]} (từ khóa: {'; '.join(ks)})" if ks else ls.desc[i]
    return out


def call_perm(cache: DiskCache, text: str, crit: dict) -> dict:
    req = {"state": text, "model": "kev-latest", "questions": {"q": {"type": "choice", "instructions": INSTR_VI, "criteria": crit}}}
    body = {"request": req, "question": "q", "n_perm": N_PERM, "seed": 0}
    key = make_key("kev-permute", TAG, body)

    def call():
        t0 = time.perf_counter()
        try:
            r = requests.post(PERM_URL, json=body, timeout=300)
            lat = (time.perf_counter() - t0) * 1000
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}: {r.text[:200]}", "latency_ms": lat}
            d = r.json()
            return {"runs": d.get("runs"), "latency_ms": lat, "error": ""}
        except requests.RequestException as e:
            return {"error": f"{type(e).__name__}: {e}", "latency_ms": (time.perf_counter() - t0) * 1000}

    return cache.cached(key, call, retry_errors=True)


def perm_to_record(rec: dict, crit: dict) -> dict:
    """Gộp N_PERM thứ tự: xác suất trung bình theo tên tùy chọn; chọn = argmax trung bình; ghi lại độ bất ổn theo thứ tự."""
    if rec.get("error") or not rec.get("runs"):
        return {"error": rec.get("error") or "no runs", "latency_ms": rec.get("latency_ms", 0.0)}
    ids = list(crit)
    P = np.array([[r["probabilities"].get(i, 0.0) for i in ids] for r in rec["runs"]])
    mean = P.mean(0)
    mean = mean / max(mean.sum(), 1e-9)
    choices = [r["choice"] for r in rec["runs"]]
    return {"choice": ids[int(mean.argmax())], "probabilities": {i: float(p) for i, p in zip(ids, mean)}, "latency_ms": rec["latency_ms"],
            "perm_choices": choices, "first_choice": choices[0], "error": ""}


def run_variant(variant: str, text: str, kc: KevClient, cache: DiskCache):
    crit = criteria(variant)
    if variant == "perm_name":
        rec = perm_to_record(call_perm(cache, text, crit), crit)
        return kev_answer(rec, crit), rec
    a = kc.choose(text, crit, INSTR_VI)
    return a, None


def stage_run(args):
    info = server_info()
    log("Kev:", info)
    if info["run"] != "jaredpalmer/kev-0.8b":
        raise SystemExit(f"Máy chủ đang giữ {info['run']}, không phải kev-0.8b: dừng.")
    dump_json(TABLES / "server_info.json", info)
    cache = DiskCache(CACHE / "kev")
    kc = KevClient(cache, url=URL, tag=TAG)
    D = Data()
    docs = D.docs(SOURCE, "DEV")
    log("DEV docs:", len(docs))
    rows, probs = [], {}
    for v in VARIANTS:
        for d in docs:
            text = clean_prompt_text(d.text, CHARS)
            if len(text) < 25:
                rows.append(dict(set="DEV", variant=v, doc_id=d.doc_id, true=d.label, label="UNKNOWN", conf=np.nan, latency_ms=0.0, parse_ok=False, error="short"))
                continue
            a, extra = run_variant(v, text, kc, cache)
            rows.append(dict(set="DEV", variant=v, doc_id=d.doc_id, true=d.label, label=a.label, conf=a.conf, latency_ms=a.latency_ms,
                             parse_ok=a.parse_ok, error=a.error, server_ms=(a.extra or {}).get("server_latency_ms"),
                             perm_choices="|".join(extra["perm_choices"]) if extra else "", first_choice=extra["first_choice"] if extra else ""))
            if a.probs:
                probs[f"DEV|{v}|{d.doc_id}"] = a.probs
        log("xong biến thể", v, "DEV")
    # lát cắt đáp án của 8 tệp ghép (một nhà cung cấp; chẩn đoán)
    sys.path.insert(0, str(EXP05))
    import common05 as C5  # noqa: E402

    ocr = C5.load_ocr()
    sl = C5.oracle_slices(ocr)
    for v in VARIANTS:
        for s in sl:
            text = clean_prompt_text(s["slice"].combined_text, CHARS)
            sid = f'{s["doc_id"]}#{s["seg_idx"]}'
            if len(text) < 25:
                rows.append(dict(set="SLICE", variant=v, doc_id=sid, true=s["true"], label="UNKNOWN", conf=np.nan, latency_ms=0.0, parse_ok=False, error="short"))
                continue
            a, extra = run_variant(v, text, kc, cache)
            rows.append(dict(set="SLICE", variant=v, doc_id=sid, true=s["true"], label=a.label, conf=a.conf, latency_ms=a.latency_ms, parse_ok=a.parse_ok,
                             error=a.error, server_ms=(a.extra or {}).get("server_latency_ms"),
                             perm_choices="|".join(extra["perm_choices"]) if extra else "", first_choice=extra["first_choice"] if extra else ""))
            if a.probs:
                probs[f"SLICE|{v}|{sid}"] = a.probs
        log("xong biến thể", v, "SLICE", len(sl))
    pd.DataFrame(rows).to_csv(OUT / "preds_kev_new.csv", index=False)
    (OUT / "probs_kev_new.json").write_text(json.dumps(probs, ensure_ascii=False), encoding="utf-8")
    log("cache hits/misses:", cache.hits, cache.misses)


# ---------------------------------------------------------------------------
# Phân tích
# ---------------------------------------------------------------------------
def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (c - h, c + h)


def mcnemar_exact(a_ok: np.ndarray, b_ok: np.ndarray):
    from scipy.stats import binomtest

    b = int((a_ok & ~b_ok).sum())
    c = int((~a_ok & b_ok).sum())
    p = binomtest(b, b + c, 0.5).pvalue if b + c else 1.0
    return b, c, float(p)


def paired_boot(a_ok: np.ndarray, b_ok: np.ndarray, n_boot: int = 2000, seed: int = 0):
    rng = np.random.default_rng(seed)
    n = len(a_ok)
    diff = a_ok.astype(float) - b_ok.astype(float)
    bs = [diff[rng.integers(0, n, n)].mean() for _ in range(n_boot)]
    return float(diff.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def temper(P: np.ndarray, factor: float) -> np.ndarray:
    """Giả thiết p ∝ exp(z/T): p' ∝ p**factor ứng với nhiệt độ T' = T/factor."""
    L = np.log(np.clip(P, 1e-12, None)) * factor
    L -= L.max(1, keepdims=True)
    E = np.exp(L)
    return E / E.sum(1, keepdims=True)


def stage_analyze(args):
    from evalz import aurc, calib_scores, z_scores  # noqa: E402

    D = Data()
    bench = D.bench
    docs = D.docs(SOURCE, "DEV")
    by_id = {d.doc_id: d for d in docs}
    new = pd.read_csv(OUT / "preds_kev_new.csv", dtype={"doc_id": str})
    probs = json.loads((OUT / "probs_kev_new.json").read_text(encoding="utf-8"))
    info = json.loads((TABLES / "server_info.json").read_text(encoding="utf-8"))
    P02 = REPO / "teams" / "team3_classification" / "results" / "02_llm_and_cascade" / "preds"
    old = pd.read_csv(P02 / f"zs_kev_s1_name_c2000__{SOURCE}__DEV.csv", dtype={"doc_id": str}).set_index("doc_id")
    q35 = pd.read_csv(P02 / f"zs_q35_s1_short_c2000__{SOURCE}__DEV.csv", dtype={"doc_id": str}).set_index("doc_id")
    ids = [d.doc_id for d in docs]
    y = np.array([d.label for d in docs])
    out = {"server": info}
    res_rows, ok = [], {}
    lab = {}
    for v in VARIANTS:
        s = new[(new.set == "DEV") & (new.variant == v)].set_index("doc_id").loc[ids]
        pred = s["label"].fillna("UNKNOWN").to_numpy()
        lab[v] = pred
        corr = pred == y
        ok[v] = corr
        z = z_scores(bench, y, pred)
        lo, hi = wilson(int(corr.sum()), len(corr))
        conf = s["conf"].to_numpy(float)
        cs = calib_scores(conf, corr, list(pred))
        res_rows.append(dict(variant=v, n=len(y), correct=int(corr.sum()), accuracy=corr.mean(), wilson_lo=lo, wilson_hi=hi, macro_f1=z["macro_f1"],
                             macro_f1_lo=z["macro_f1_lo"], macro_f1_hi=z["macro_f1_hi"], rare_recall=z["rare_recall"], freq_recall=z["freq_recall"],
                             ece=cs["ece"], auroc=cs["auroc_correct"], aurc=cs["aurc"], mean_conf=cs["mean_conf"],
                             autofile_1pct=cs["autofile_1pct"], errs_1pct=cs["errors_1pct"], acc_1pct_n=cs["n_accepted_1pct"],
                             wall_ms_median=float(s.latency_ms.median()), wall_ms_p95=float(s.latency_ms.quantile(0.95)),
                             server_ms_median=float(pd.to_numeric(s.get("server_ms"), errors="coerce").median())))
    # đối chứng cũ
    for name, df in (("kev_old_name(gd1)", old), ("q35_short(02)", q35)):
        pred = df.loc[ids, "label"].fillna("UNKNOWN").to_numpy()
        corr = pred == y
        ok[name] = corr
        lab[name] = pred
        z = z_scores(bench, y, pred)
        lo, hi = wilson(int(corr.sum()), len(corr))
        cs = calib_scores(df.loc[ids, "conf"].to_numpy(float), corr, list(pred))
        res_rows.append(dict(variant=name, n=len(y), correct=int(corr.sum()), accuracy=corr.mean(), wilson_lo=lo, wilson_hi=hi, macro_f1=z["macro_f1"],
                             macro_f1_lo=z["macro_f1_lo"], macro_f1_hi=z["macro_f1_hi"], rare_recall=z["rare_recall"], freq_recall=z["freq_recall"],
                             ece=cs["ece"], auroc=cs["auroc_correct"], aurc=cs["aurc"], mean_conf=cs["mean_conf"],
                             autofile_1pct=cs["autofile_1pct"], errs_1pct=cs["errors_1pct"], acc_1pct_n=cs["n_accepted_1pct"],
                             wall_ms_median=float(df.loc[ids, "latency_ms"].median()), wall_ms_p95=float(df.loc[ids, "latency_ms"].quantile(0.95)), server_ms_median=float("nan")))
    R = pd.DataFrame(res_rows)
    R.to_csv(TABLES / "dev_summary.csv", index=False)
    # cặp
    pair_rows = []
    pairs = [("name", "kev_old_name(gd1)"), ("name", "q35_short(02)"), ("name_kw", "name"), ("perm_name", "name"), ("name_kw", "q35_short(02)"), ("perm_name", "q35_short(02)"),
             ("kev_old_name(gd1)", "q35_short(02)")]
    for a, b in pairs:
        n10, n01, p = mcnemar_exact(ok[a], ok[b])
        d, lo, hi = paired_boot(ok[a], ok[b])
        pair_rows.append(dict(A=a, B=b, A_only_correct=n10, B_only_correct=n01, mcnemar_p=p, diff=d, diff_lo=lo, diff_hi=hi))
    pd.DataFrame(pair_rows).to_csv(TABLES / "dev_pairs.csv", index=False)
    # nhất quán với lần đo cũ (cùng mô hình/nhiệt độ?)
    sname = new[(new.set == "DEV") & (new.variant == "name")].set_index("doc_id").loc[ids]
    agree_old = float((sname["label"].to_numpy() == old.loc[ids, "label"].to_numpy()).mean())
    conf_diff = float(np.nanmax(np.abs(sname["conf"].to_numpy(float) - old.loc[ids, "conf"].to_numpy(float))))
    conf_med = float(np.nanmedian(np.abs(sname["conf"].to_numpy(float) - old.loc[ids, "conf"].to_numpy(float))))
    out["agree_with_old_labels"] = agree_old
    out["max_abs_conf_diff_vs_old"] = conf_diff
    out["median_abs_conf_diff_vs_old"] = conf_med
    # thiên vị thứ tự (permute)
    pm = new[(new.set == "DEV") & (new.variant == "perm_name")].set_index("doc_id").loc[ids]
    choices = pm["perm_choices"].fillna("").str.split("|")
    unstable = np.array([len(set(c)) > 1 for c in choices])
    first_ok = (pm["first_choice"].to_numpy() == y)
    out["perm_unstable_share"] = float(unstable.mean())
    out["perm_first_order_accuracy"] = float(first_ok.mean())
    out["perm_mean_accuracy"] = float(ok["perm_name"].mean())
    pa = np.mean([[c == t for c in cs_] for cs_, t in zip(choices, y)], axis=0)
    out["perm_accuracy_per_order"] = [float(x) for x in pa]
    # nhiệt độ: ECE theo hệ số làm nóng/lạnh phân phối (cross-fit theo fold DEV)
    classes = list(criteria("name"))
    PM = np.array([[probs[f"DEV|name|{i}"].get(c, 0.0) for c in classes] for i in ids])
    PM = PM / PM.sum(1, keepdims=True)
    yi = np.array([classes.index(t) if t in classes else -1 for t in y])
    pred_i = PM.argmax(1)
    corr = pred_i == yi
    from eval_metrics import ece as ece_fn  # noqa: E402

    temp_rows = []
    for f in (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 2.35, 3.0, 4.0):
        Q = temper(PM, f)
        nll = float(-np.mean(np.log(np.clip(Q[np.arange(len(ids)), np.clip(yi, 0, None)], 1e-12, None))))
        temp_rows.append(dict(factor=f, T_equiv=info["temperature"] / f, ece=float(ece_fn(Q.max(1), corr.astype(float))), nll=nll, mean_conf=float(Q.max(1).mean())))
    pd.DataFrame(temp_rows).to_csv(TABLES / "dev_temperature.csv", index=False)
    # cross-fit: chọn factor tối thiểu NLL trên 4 fold, áp lên fold còn lại
    folds = np.array([by_id[i].fold for i in ids])
    qcf = np.zeros_like(PM)
    grid = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0]
    chosen = []
    for fo in sorted(set(folds)):
        tr, te = folds != fo, folds == fo
        best = min(grid, key=lambda f: -np.mean(np.log(np.clip(temper(PM[tr], f)[np.arange(tr.sum()), np.clip(yi[tr], 0, None)], 1e-12, None))))
        chosen.append(best)
        qcf[te] = temper(PM[te], best)
    out["crossfit_factor_chosen"] = chosen
    out["crossfit_ece"] = float(ece_fn(qcf.max(1), corr.astype(float)))
    out["served_ece"] = float(ece_fn(PM.max(1), corr.astype(float)))
    # lỗi
    tpl = {d.doc_id: d.template_group for d in docs}
    err_rows = []
    for i, d in enumerate(ids):
        if not ok["name"][i] or not ok["name_kw"][i] or not ok["perm_name"][i]:
            err_rows.append(dict(doc_id=d, true=y[i], name=lab["name"][i], name_kw=lab["name_kw"][i], perm=lab["perm_name"][i], old_kev=lab["kev_old_name(gd1)"][i],
                                 q35=lab["q35_short(02)"][i], conf_name=float(sname.loc[d, "conf"]) if not np.isnan(sname.loc[d, "conf"]) else np.nan,
                                 template_group=tpl[d], group=by_id[d].group))
    E = pd.DataFrame(err_rows)
    lbl = pd.read_csv(REPO / "data" / "labels_v2.csv", dtype=str, encoding="utf-8-sig").set_index("doc_id")
    E["label_conf"] = E.doc_id.map(lbl["confidence"])
    E["review_status"] = E.doc_id.map(lbl["review_status"])
    E["q35_agrees_kev_not_label"] = (E.q35 == E.name) & (E.name != E.true)
    E.to_csv(OUT / "errors_dev.csv", index=False)
    # cặp nhầm, tập trung
    e1 = E[E.name != E.true]
    cp = e1.groupby(["true", "name"]).size().sort_values(ascending=False).reset_index(name="n")
    cp.to_csv(TABLES / "dev_confusion_pairs_name.csv", index=False)
    per_true = pd.DataFrame({"n": pd.Series(y).value_counts()}).join(e1.groupby("true").size().rename("err")).fillna(0)
    per_true["err"] = per_true["err"].astype(int)
    per_true["recall"] = 1 - per_true.err / per_true.n
    per_true.sort_values("err", ascending=False).to_csv(TABLES / "dev_per_type_name.csv")
    # tập trung theo cặp / nhóm mẫu
    out["n_err_name"] = int(len(e1))
    out["n_pairs_name"] = int(len(cp))
    out["pairs_with_ge2"] = int((cp.n >= 2).sum())
    out["err_in_repeated_pairs"] = int(cp[cp.n >= 2].n.sum())
    tg = e1[e1.template_group != ""].groupby("template_group").size()
    out["err_in_template_groups_ge2"] = int(tg[tg >= 2].sum())
    out["err_with_template_group"] = int((e1.template_group != "").sum())
    out["share_dev_in_template_group"] = float(np.mean([tpl[i] != "" for i in ids]))
    # lát cắt
    sl = new[new.set == "SLICE"]
    srows = []
    for v in VARIANTS:
        s = sl[sl.variant == v]
        c = (s.label == s.true).to_numpy()
        lo, hi = wilson(int(c.sum()), len(c))
        srows.append(dict(variant=v, n=len(s), correct=int(c.sum()), accuracy=c.mean(), wilson_lo=lo, wilson_hi=hi, wrong=";".join(f"{a}->{b}" for a, b in zip(s.true[~c], s.label[~c]))))
    pd.DataFrame(srows).to_csv(TABLES / "slices_summary.csv", index=False)
    dump_json(OUT / "analysis.json", out)
    with pd.option_context("display.width", 250, "display.max_columns", 40, "display.float_format", "{:.3f}".format):
        print(R.drop(columns=["n"]).to_string())
        print(pd.DataFrame(pair_rows).to_string())
        print(json.dumps(out, ensure_ascii=False, indent=1))
        print(pd.DataFrame(temp_rows).to_string())
        print(cp.head(15).to_string())
        print(per_true.sort_values("err", ascending=False).head(15).to_string())
        print(pd.DataFrame(srows).to_string())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["run", "analyze"], required=True)
    a = ap.parse_args()
    {"run": stage_run, "analyze": stage_analyze}[a.stage](a)
