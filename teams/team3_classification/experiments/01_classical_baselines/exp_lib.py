"""exp_lib.py - Hàm chạy trong tiến trình con (joblib) và hàm dùng chung cho run_all.py.

Mọi hàm `*_task` nhận một `ctx` (dict nhỏ: đường dẫn nhãn, min_docs) và tự nạp dữ liệu, để pickle gọn và tất định.
"""

from __future__ import annotations

import dataclasses
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import methods  # noqa: E402,F401  (đặt sys.path cho harness)
from harness import *  # noqa: E402,F401,F403
from harness import (POOL, UNKNOWN, Benchmark, Doc, cross_validate, effective_groups, grouped_folds, load_benchmark,
                     load_documents, load_or_make_splits, naive_folds, score_predictions, summarize_folds,
                     truncate_docs)
from methods import VecCache, build_predictor, build_visual_cache  # noqa: E402

VISUAL_CACHE = HERE / "_cache" / "visual.npz"


def load_ctx(ctx: dict):
    bench = load_benchmark(ctx["labels"], ctx["min_docs"])
    splits = load_or_make_splits(bench)
    return bench, splits


def _fold_row(s: Dict) -> Dict:
    return {k: s[k] for k in ("seed", "fold", "n", "accuracy", "macro_f1", "weighted_f1", "ece", "brier") if k in s}


def cv_task(ctx: dict, source: str, seed: int, configs: List[dict], keep_oof: bool = True) -> Dict:
    """CV 5-fold trên DEV cho nhiều cấu hình (dùng chung VecCache). Trả {config_name: {...}}."""
    bench, splits = load_ctx(ctx)
    dev = load_documents(bench, splits, source, "DEV")
    vc = VecCache()
    vis = build_visual_cache(dev, VISUAL_CACHE) if any(c["family"] == "visual" for c in configs) else None
    out = {}
    for cfg in configs:
        cv = cross_validate(lambda: build_predictor(cfg, bench.s_classes, vc, vis), dev, bench.s_classes, "S", seed)
        out[cfg["name"]] = {
            "fold_scores": [_fold_row(s) for s in cv.fold_scores],
            "oof": cv.oof if keep_oof else None,
            "proba": cv.proba if keep_oof else None,
            "classes": cv.classes,
        }
    return out


def rule_gate_dev_task(ctx: dict, source: str) -> Dict:
    """Cổng luật (không huấn luyện) trên DEV: Track Z và ánh xạ sang Track S; điểm theo từng fold (seed 0..2)."""
    bench, splits = load_ctx(ctx)
    dev = load_documents(bench, splits, source, "DEV")
    res = {}
    for track, cfg in (("Z", dict(family="rule_gate_Z", name="rule_gate")), ("S", dict(family="rule_gate_S", name="rule_gate_mapped_to_S"))):
        p = build_predictor(cfg, bench.s_classes)
        pred = p.predict(dev)
        labels = pred.labels
        rows = []
        for seed in (0, 1, 2):
            for f in sorted({d.folds[seed] for d in dev}):
                idx = [i for i, d in enumerate(dev) if d.folds[seed] == f]
                yt = [dev[i].target(track) for i in idx]
                yp = [labels[i] for i in idx]
                sc = score_predictions(yt, yp, bench.z_classes if track == "Z" else bench.s_classes,
                                       min_support=3 if track == "Z" else 1, abstain_label=UNKNOWN if track == "Z" else None)
                sc.pop("per_class")
                sc.update(seed=seed, fold=f)
                rows.append(_fold_row(sc) | {"coverage": sc["coverage"], "accuracy_on_covered": sc["accuracy_on_covered"]})
        yt = [d.target(track) for d in dev]
        allsc = score_predictions(yt, labels, bench.z_classes if track == "Z" else bench.s_classes,
                                  min_support=3 if track == "Z" else 1, abstain_label=UNKNOWN if track == "Z" else None)
        res[cfg["name"]] = {"fold_scores": rows, "pooled": {k: v for k, v in allsc.items() if k != "per_class"},
                            "per_class": allsc["per_class"], "y_true": yt, "y_pred": labels, "doc_ids": [d.doc_id for d in dev]}
    return res


def length_task(ctx: dict, source: str, cfg: dict, lengths: Sequence[Optional[int]], seeds: Sequence[int]) -> List[Dict]:
    """Ablation độ dài đầu vào: cắt n ký tự đầu của văn bản."""
    bench, splits = load_ctx(ctx)
    dev0 = load_documents(bench, splits, source, "DEV")
    rows = []
    for n in lengths:
        dev = truncate_docs(dev0, n)
        for seed in seeds:
            cv = cross_validate(lambda: build_predictor(cfg, bench.s_classes, VecCache()), dev, bench.s_classes, "S", seed)
            for s in cv.fold_scores:
                rows.append(dict(source=source, config=cfg["name"], n_chars="full" if n is None else n, **_fold_row(s)))
    return rows


def learning_curve_task(ctx: dict, source: str, cfg: dict, ks: Sequence[Optional[int]], sub_seeds: Sequence[int], cap_pool: bool = True) -> Dict:
    """Learning curve trên DEV (fold seed 0): huấn luyện với tối đa k tài liệu MỖI LỚP (k=None -> tất cả).
    cap_pool=False: lớp gộp RARE_OR_OTHER luôn được giữ đủ -> chỉ đo ảnh hưởng của số mẫu lên các loại đã biết."""
    bench, splits = load_ctx(ctx)
    dev = load_documents(bench, splits, source, "DEV")
    classes = bench.s_classes
    runs, recalls = [], []
    for f in sorted({d.folds[0] for d in dev}):
        tr_all = [d for d in dev if d.folds[0] != f]
        te = [d for d in dev if d.folds[0] == f]
        yt = [d.label_s for d in te]
        for k in ks:
            for s in (sub_seeds if k is not None else [0]):
                if k is None:
                    tr = tr_all
                else:
                    rng = np.random.default_rng(1000 * (s + 1) + f)
                    tr = []
                    for c in classes:
                        members = [d for d in tr_all if d.label_s == c]
                        if len(members) > k and (cap_pool or c != POOL):
                            members = [members[i] for i in rng.choice(len(members), k, replace=False)]
                        tr += members
                p = build_predictor(cfg, classes).fit(tr)
                yp = p.predict(te).labels
                sc = score_predictions(yt, yp, classes)
                runs.append(dict(k="all" if k is None else str(k), fold=f, sub_seed=s, accuracy=sc["accuracy"], macro_f1=sc["macro_f1"], n_train=len(tr)))
                pc = sc["per_class"]
                for _, r in pc[pc["support"] > 0].iterrows():
                    recalls.append(dict(k="all" if k is None else str(k), fold=f, sub_seed=s, cls=r["class"], recall=r["recall"]))
    return {"source": source, "config": cfg["name"], "variant": "cap_all" if cap_pool else "pool_full", "runs": pd.DataFrame(runs), "recalls": pd.DataFrame(recalls)}


def leakage_task(ctx: dict, source: str, cfg: dict, seeds: Sequence[int] = (0, 1, 2)) -> List[Dict]:
    """So sánh 4 cách chia trên CÙNG tập DEV: (1) ngây thơ trên file (bản sao + biểu mẫu rò rỉ), (2) ngây thơ trên tài liệu
    duy nhất, (3) nhóm theo biểu mẫu có cắt nhóm lớn (chính thức), (4) nhóm theo biểu mẫu nghiêm ngặt."""
    bench, splits = load_ctx(ctx)
    files = load_documents(bench, splits, source, "DEV", include_duplicates=True)
    is_rep = dict(zip(bench.files["doc_id"], bench.files["is_rep"]))
    reps = [d for d in files if is_rep[d.doc_id]]
    reps_df = bench.reps[bench.reps["doc_id"].isin([d.doc_id for d in reps])]
    strict_groups = effective_groups(reps_df, None)

    def with_folds(docs, fn):
        out = [dataclasses.replace(d, folds=dict(d.folds)) for d in docs]
        for s in seeds:
            f = fn(out, s)
            for d, v in zip(out, f):
                d.folds[s] = int(v)
        return out

    schemes = {
        "naive_files": with_folds(files, lambda ds, s: naive_folds([d.label_s for d in ds], 5, s)),
        "naive_unique": with_folds(reps, lambda ds, s: naive_folds([d.label_s for d in ds], 5, s)),
        "grouped_capped": reps,
        "grouped_strict": with_folds(reps, lambda ds, s: grouped_folds([d.label for d in ds], [strict_groups[d.doc_id] for d in ds], 5, 1000 * 42 + s)),
    }
    rows, percls = [], []
    for name, docs in schemes.items():
        for seed in seeds:
            cv = cross_validate(lambda: build_predictor(cfg, bench.s_classes, VecCache()), docs, bench.s_classes, "S", seed)
            for s in cv.fold_scores:
                rows.append(dict(source=source, config=cfg["name"], scheme=name, n_docs=len(docs), **_fold_row(s)))
            if seed == 0:
                pc = score_predictions(cv.oof["y_true"], cv.oof["y_pred"], bench.s_classes)["per_class"]
                pc.insert(0, "scheme", name)
                pc.insert(0, "source", source)
                percls.append(pc)
    return {"rows": rows, "per_class": pd.concat(percls, ignore_index=True)}


# ---------------------------------------------------------------------------
# Phân tích lỗi
# ---------------------------------------------------------------------------
def mask_digits(text: str, n: int = 150) -> str:
    t = re.sub(r"\s+", " ", (text or "")[:n])
    return re.sub(r"\d", "#", t)


def error_table(oof: pd.DataFrame, docs: Sequence[Doc], conf: Optional[np.ndarray] = None) -> pd.DataFrame:
    by = {d.doc_id: d for d in docs}
    rows = []
    for _, r in oof.iterrows():
        d = by[r["doc_id"]]
        rows.append(dict(doc_id=d.doc_id, file_name=d.file_name, true=r["y_true"], predicted=r["y_pred"],
                         confidence=r["conf"], correct=int(r["y_true"] == r["y_pred"]), is_scanned=int(d.is_scanned),
                         n_chars=len(d.text), has_template_group=int(bool(d.template_group)), true_type=d.label,
                         text_150_digits_masked=mask_digits(d.text)))
    return pd.DataFrame(rows)


def error_patterns(err: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Tỉ lệ sai theo: loại thật, quét/số hóa, độ dài văn bản, có biểu mẫu chung hay không."""
    err = err.copy()
    err["wrong"] = 1 - err["correct"]
    out = {}
    g = err.groupby("true_type").agg(n=("wrong", "size"), errors=("wrong", "sum")).assign(err_rate=lambda x: x.errors / x.n)
    out["by_true_type"] = g[g.errors > 0].sort_values("errors", ascending=False).reset_index()
    out["by_scanned"] = err.groupby("is_scanned").agg(n=("wrong", "size"), errors=("wrong", "sum")).assign(err_rate=lambda x: x.errors / x.n).reset_index()
    err["len_bucket"] = pd.cut(err["n_chars"], [-1, 200, 800, 1600, 10**9], labels=["<=200", "201-800", "801-1600", ">1600"])
    out["by_length"] = err.groupby("len_bucket", observed=True).agg(n=("wrong", "size"), errors=("wrong", "sum")).assign(err_rate=lambda x: x.errors / x.n).reset_index()
    out["by_template"] = err.groupby("has_template_group").agg(n=("wrong", "size"), errors=("wrong", "sum")).assign(err_rate=lambda x: x.errors / x.n).reset_index()
    return out
