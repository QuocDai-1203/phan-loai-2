"""splitlib.py - Thư viện dùng chung cho các thí nghiệm của Nhóm 2 (tách tài liệu).

Gồm: nạp OCR -> OCRDocumentResult, nạp đáp án mức trang, phạm vi đánh giá (DEV-like / all), các chỉ số
(precision/recall/F1 ranh giới, exact-segment match, tách nhầm trên mẫu âm, độ chính xác loại theo segment bằng cổng luật),
khoảng tin cậy Wilson và bootstrap theo TỆP, bootstrap ghép cặp.

Quy ước: trang đánh số từ 1; "vị trí" = trang >= 2 (câu hỏi: trang đó có mở tài liệu mới không?).
Không import gì từ nhóm khác ngoài bộ luật `CascadedClassifier(kev_endpoint=None)` (chỉ để chấm loại).
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.common.contracts import OCRDocumentResult, OCRPageResult  # noqa: E402

GOLD_CSV = HERE / "gold" / "boundary_gold_v0.csv"
OCR_JSONL = REPO / "data" / "ocr_v2.jsonl"
LABELS_CSV = REPO / "data" / "labels_v2.csv"
SPLITS_CSV = REPO / "data" / "splits" / "splits.csv"

BOOT_N = 2000
BOOT_SEED = 20260711          # cùng hằng số với teams/00_data_and_eval/eval/eval_metrics.py
GROUPS = ["mixed", "same_other", "same_bb", "negative"]
GROUP_TITLES = {
    "mixed": "composite khác loại",
    "same_other": "composite cùng loại, ngoài BB_LAY_MAU",
    "same_bb": "composite BB_LAY_MAU",
    "negative": "mẫu âm (nhiều trang, không composite)",
}


# ---------------------------------------------------------------------------
# Nạp dữ liệu
# ---------------------------------------------------------------------------
def load_gold(path: Path = GOLD_CSV) -> pd.DataFrame:
    g = pd.read_csv(path, dtype={"doc_id": str, "template_group": str, "split": str, "review_status": str}, keep_default_na=False,
                    encoding="utf-8-sig")
    return g


def scope_doc_ids(gold: pd.DataFrame, scope: str) -> List[str]:
    """scope='dev': DEV + EXCLUDED_COMPOSITE (được phép nhìn lỗi/chỉnh). scope='all': thêm TEST (chỉ chạy một lần cuối, cấu hình đã đóng băng)."""
    d = gold.drop_duplicates("doc_id")
    if scope == "dev":
        d = d[d.split.isin(["DEV", "EXCLUDED_COMPOSITE"])]
    elif scope != "all":
        raise ValueError(scope)
    return sorted(d.doc_id)


def load_ocr_pages(path: Path = OCR_JSONL, doc_ids: Optional[Iterable[str]] = None) -> Dict[str, dict]:
    """doc_id -> bản ghi thô của ocr_v2.jsonl (không sửa file)."""
    want = set(doc_ids) if doc_ids is not None else None
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if want is None or r["doc_id"] in want:
            out[r["doc_id"]] = r
    return out


def to_ocr_document(rec: dict) -> OCRDocumentResult:
    """ocr_v2 -> OCRDocumentResult. width/height = 0 vì ocr_v2.jsonl KHÔNG lưu kích thước trang.
    total_pages = số trang thật của PDF (page_count); `pages` chỉ gồm trang đã OCR (<= 30)."""
    pages = []
    for p in rec["pages"]:
        err = p.get("error") or None
        pages.append(OCRPageResult(
            page_number=int(p["page"]), width=0, height=0, full_text="" if err else (p.get("text") or ""),
            ocr_engine=str(p.get("engine", "")), source="text_layer" if p.get("source") == "text_layer" else "ocr", error=err,
        ))
    return OCRDocumentResult(file_name=rec["file_name"], total_pages=int(rec["page_count"]), pages=pages,
                             error=None)


def load_documents(doc_ids: Sequence[str]) -> Dict[str, OCRDocumentResult]:
    recs = load_ocr_pages(doc_ids=doc_ids)
    missing = [d for d in doc_ids if d not in recs]
    if missing:
        raise KeyError(f"thiếu OCR cho {len(missing)} doc_id: {missing[:5]}")
    return {d: to_ocr_document(recs[d]) for d in doc_ids}


def gold_for_doc(gold: pd.DataFrame, doc_id: str, n_avail: int) -> pd.DataFrame:
    """Đáp án của một tệp, cắt ở số trang có văn bản (n_avail)."""
    g = gold[gold.doc_id == doc_id].sort_values("page")
    return g[g.page <= n_avail]


# ---------------------------------------------------------------------------
# Từ tập trang bắt đầu -> phân đoạn
# ---------------------------------------------------------------------------
def partition(n_pages: int, starts: Iterable[int]) -> List[Tuple[int, int]]:
    """starts: các trang >= 2 mở tài liệu mới. Trả về [(a,b),...] phủ 1..n_pages."""
    st = sorted({int(s) for s in starts if 2 <= int(s) <= n_pages})
    cuts = [1] + st
    return [(a, (cuts[i + 1] - 1) if i + 1 < len(cuts) else n_pages) for i, a in enumerate(cuts)]


def gold_segments(g: pd.DataFrame) -> List[Tuple[int, int, str]]:
    segs = []
    for k, sub in g.groupby("segment_idx", sort=True):
        segs.append((int(sub.page.min()), int(sub.page.max()), str(sub.page_doc_type.iloc[0])))
    return segs


def slice_text(doc: OCRDocumentResult, a: int, b: int) -> str:
    return "\n\n--- TIẾP THEO ---\n\n".join(p.full_text for p in doc.pages if a <= p.page_number <= b)


# ---------------------------------------------------------------------------
# Cổng luật (chỉ để chấm loại theo segment)
# ---------------------------------------------------------------------------
_GATE = None
_GATE_CACHE: Dict[str, str] = {}


def rule_gate_type(text: str) -> str:
    """Loại do cổng luật tiêu đề (Kev tắt) cho `text`; 'UNKNOWN' nếu không khớp hoặc mơ hồ."""
    global _GATE
    if text in _GATE_CACHE:
        return _GATE_CACHE[text]
    if _GATE is None:
        from src.classification.system_one_classifier import CascadedClassifier
        _GATE = CascadedClassifier(kev_endpoint=None)
    _GATE_CACHE[text] = _GATE.match_rules(text).category or "UNKNOWN"
    return _GATE_CACHE[text]


# ---------------------------------------------------------------------------
# Chấm từng tệp
# ---------------------------------------------------------------------------
PER_FILE_COLS = ["doc_id", "group", "n_pos", "n_true", "n_pred", "tp", "fp", "fn", "exact", "n_seg", "seg_ok", "seg_ok_oracle",
                 "seg_ok_both"]


def score_file(doc_id: str, group: str, doc: OCRDocumentResult, g: pd.DataFrame, pred_starts: Set[int]) -> dict:
    """g: đáp án đã cắt ở số trang có văn bản. pred_starts: trang >= 2 dự đoán là mở tài liệu mới."""
    n = len(doc.pages)
    pos = g[g.page >= 2]
    true_starts = set(pos[pos.is_start == 1].page.astype(int))
    pred = {int(s) for s in pred_starts if 2 <= int(s) <= n}
    tp, fp, fn = len(pred & true_starts), len(pred - true_starts), len(true_starts - pred)
    gsegs = gold_segments(g)
    psegs = partition(n, pred)
    exact = int([(a, b) for a, b, _ in gsegs] == psegs)
    # loại theo segment: cổng luật trên lát cắt dự đoán khớp nhiều trang trùng nhất với segment đáp án
    seg_ok = seg_ok_oracle = seg_ok_both = 0
    for a, b, typ in gsegs:
        best, best_ov = None, 0
        for (pa, pb) in psegs:
            ov = max(0, min(b, pb) - max(a, pa) + 1)
            if ov > best_ov:
                best, best_ov = (pa, pb), ov
        pred_type = rule_gate_type(slice_text(doc, *best)) if best else "UNKNOWN"
        orc_type = rule_gate_type(slice_text(doc, a, b))
        seg_ok += int(pred_type == typ)
        seg_ok_oracle += int(orc_type == typ)
        seg_ok_both += int(pred_type == typ and orc_type == typ)
    return dict(doc_id=doc_id, group=group, n_pos=len(pos), n_true=len(true_starts), n_pred=len(pred), tp=tp, fp=fp, fn=fn,
                exact=exact, n_seg=len(gsegs), seg_ok=seg_ok, seg_ok_oracle=seg_ok_oracle, seg_ok_both=seg_ok_both)


def evaluate_method(predict_starts: Callable[[str, OCRDocumentResult], Set[int]], doc_ids: Sequence[str], docs: Dict[str, OCRDocumentResult],
                    gold: pd.DataFrame, prediction_cache: Optional[Dict[str, Set[int]]] = None) -> Tuple[pd.DataFrame, Dict[str, Set[int]]]:
    """Chạy phương pháp trên mọi tệp có vị trí (>= 2 trang có văn bản). Trả về bảng theo tệp + dict dự đoán."""
    rows, preds = [], {}
    meta = gold.drop_duplicates("doc_id").set_index("doc_id")
    for d in doc_ids:
        grp = meta.loc[d, "eval_group"]
        if grp not in GROUPS:
            continue
        doc = docs[d]
        g = gold_for_doc(gold, d, len(doc.pages))
        starts = set(prediction_cache[d]) if prediction_cache is not None else set(predict_starts(d, doc))
        preds[d] = starts
        rows.append(score_file(d, grp, doc, g, starts))
    return pd.DataFrame(rows, columns=PER_FILE_COLS), preds


# ---------------------------------------------------------------------------
# Thống kê: Wilson, bootstrap theo tệp
# ---------------------------------------------------------------------------
def wilson(k: int, n: int, z: float = 1.959964) -> Tuple[float, float, float]:
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, max(0.0, c - h), min(1.0, c + h)


def _ratio(num: np.ndarray, den: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(den > 0, num / den, np.nan)


def metric_vectors(df: pd.DataFrame, idx: Optional[np.ndarray] = None) -> Dict[str, np.ndarray]:
    """Các chỉ số gộp theo tệp. idx: (B, n) chỉ số lấy mẫu lại -> mỗi chỉ số là vector độ dài B. Không idx -> độ dài 1."""
    cols = ["n_pos", "n_true", "n_pred", "tp", "fp", "fn", "exact", "n_seg", "seg_ok", "seg_ok_oracle", "seg_ok_both"]
    a = {c: df[c].to_numpy(dtype=float) for c in cols}
    if idx is None:
        s = {c: np.array([a[c].sum()]) for c in cols}
        fs_files = np.array([(a["fp"] > 0).sum()])
        nfiles = np.array([len(df)], dtype=float)
    else:
        s = {c: a[c][idx].sum(axis=1) for c in cols}
        fs_files = (a["fp"][idx] > 0).sum(axis=1)
        nfiles = np.full(idx.shape[0], idx.shape[1], dtype=float)
    prec = _ratio(s["tp"], s["tp"] + s["fp"])
    rec = _ratio(s["tp"], s["tp"] + s["fn"])
    f1 = _ratio(2 * s["tp"], 2 * s["tp"] + s["fp"] + s["fn"])
    return dict(
        precision=prec, recall=rec, f1=f1,
        exact_rate=s["exact"] / nfiles,
        false_split_per100=100 * _ratio(s["fp"], s["n_pos"]),
        files_with_false_split=fs_files / nfiles,
        seg_type_acc=_ratio(s["seg_ok"], s["n_seg"]),
        seg_type_acc_oracle=_ratio(s["seg_ok_oracle"], s["n_seg"]),
        seg_type_retention=_ratio(s["seg_ok_both"], s["seg_ok_oracle"]),
    )


def boot_indices(n: int, n_boot: int = BOOT_N, seed: int = BOOT_SEED) -> np.ndarray:
    return np.random.default_rng(seed).integers(0, n, size=(n_boot, n))


def ci(arr: np.ndarray, alpha: float = 0.05) -> Tuple[float, float]:
    a = arr[~np.isnan(arr)]
    if len(a) < 20:
        return float("nan"), float("nan")
    lo, hi = np.percentile(a, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi)


def group_summary(df: pd.DataFrame, group: str, n_boot: int = BOOT_N) -> Dict[str, Tuple[float, float, float]]:
    """{metric: (điểm, lo, hi)} cho một nhóm, bootstrap lấy mẫu lại theo TỆP trong nhóm."""
    sub = df[df.group == group].reset_index(drop=True)
    if sub.empty:
        return {}
    point = {k: float(v[0]) for k, v in metric_vectors(sub).items()}
    bt = metric_vectors(sub, boot_indices(len(sub), n_boot))
    return {k: (point[k], *ci(bt[k])) for k in point}


def paired_diff(df_a: pd.DataFrame, df_b: pd.DataFrame, group: str, n_boot: int = BOOT_N) -> Dict[str, Dict[str, float]]:
    """Hiệu A - B theo từng chỉ số, bootstrap ghép cặp (cùng chỉ số tệp cho cả hai). `separable` = CI không chứa 0."""
    a = df_a[df_a.group == group].sort_values("doc_id").reset_index(drop=True)
    b = df_b[df_b.group == group].sort_values("doc_id").reset_index(drop=True)
    assert list(a.doc_id) == list(b.doc_id)
    if a.empty:
        return {}
    idx = boot_indices(len(a), n_boot)
    pa, pb = metric_vectors(a), metric_vectors(b)
    ba, bb = metric_vectors(a, idx), metric_vectors(b, idx)
    out = {}
    for k in pa:
        diff = float(pa[k][0] - pb[k][0])
        d = ba[k] - bb[k]
        lo, hi = ci(d)
        out[k] = dict(diff=diff, lo=lo, hi=hi, separable=bool(not math.isnan(lo) and (lo > 0 or hi < 0)), n_files=len(a))
    return out


# ---------------------------------------------------------------------------
# Định dạng Markdown
# ---------------------------------------------------------------------------
def fmt(t: Tuple[float, float, float], d: int = 3, pct: bool = False) -> str:
    p, lo, hi = t
    if p is None or (isinstance(p, float) and math.isnan(p)):
        return "n/a"
    m = 100 if pct else 1
    if math.isnan(lo):
        return f"{p * m:.{d}f}"
    return f"{p * m:.{d}f} [{lo * m:.{d}f}; {hi * m:.{d}f}]"


def group_counts(df: pd.DataFrame, group: str) -> str:
    s = df[df.group == group]
    return f"{len(s)} tệp, {int(s.n_pos.sum())} vị trí, {int(s.n_true.sum())} ranh giới thật"


def summary_table_md(per_method: Dict[str, pd.DataFrame], n_boot: int = BOOT_N) -> str:
    """Bảng Markdown theo nhóm cho nhiều phương pháp. Mỗi ô: điểm [CI 95% bootstrap theo tệp]."""
    out = []
    for grp in GROUPS:
        ref = next(iter(per_method.values()))
        if ref[ref.group == grp].empty:
            continue
        out.append(f"\n**{GROUP_TITLES[grp]}** ({group_counts(ref, grp)})\n")
        if grp == "negative":
            out.append("| phương pháp | tách nhầm / 100 vị trí | tệp có >= 1 tách nhầm | exact-segment (tệp nguyên vẹn) | loại segment (cổng luật) |")
            out.append("|---|---|---|---|---|")
            for name, df in per_method.items():
                s = group_summary(df, grp, n_boot)
                sub = df[df.group == grp]
                k_fs = int((sub.fp > 0).sum())
                w = wilson(len(sub) - k_fs, len(sub))
                out.append(f"| {name} | {fmt(s['false_split_per100'], 2)} ({int(sub.fp.sum())}/{int(sub.n_pos.sum())}) | "
                           f"{k_fs}/{len(sub)} = {fmt(s['files_with_false_split'], 3)} | "
                           f"{int(sub.exact.sum())}/{len(sub)} = {s['exact_rate'][0]:.3f} (Wilson {wilson(int(sub.exact.sum()), len(sub))[1]:.3f}; {wilson(int(sub.exact.sum()), len(sub))[2]:.3f}) | "
                           f"{fmt(s['seg_type_acc'], 3)} (oracle {s['seg_type_acc_oracle'][0]:.3f}) |")
        else:
            out.append("| phương pháp | precision | recall | F1 | exact-segment (tệp nguyên vẹn) | tách nhầm / 100 vị trí | loại segment (cổng luật) |")
            out.append("|---|---|---|---|---|---|---|")
            for name, df in per_method.items():
                s = group_summary(df, grp, n_boot)
                sub = df[df.group == grp]
                out.append(f"| {name} | {fmt(s['precision'])} ({int(sub.tp.sum())}/{int(sub.tp.sum() + sub.fp.sum())}) | "
                           f"{fmt(s['recall'])} ({int(sub.tp.sum())}/{int(sub.tp.sum() + sub.fn.sum())}) | {fmt(s['f1'])} | "
                           f"{int(sub.exact.sum())}/{len(sub)} = {s['exact_rate'][0]:.3f} (Wilson {wilson(int(sub.exact.sum()), len(sub))[1]:.3f}; {wilson(int(sub.exact.sum()), len(sub))[2]:.3f}) | {fmt(s['false_split_per100'], 2)} ({int(sub.fp.sum())}) | "
                           f"{fmt(s['seg_type_acc'], 3)} (oracle {s['seg_type_acc_oracle'][0]:.3f}) |")
    return "\n".join(out)


def paired_table_md(df_new: pd.DataFrame, df_base: pd.DataFrame, name_new: str, name_base: str, n_boot: int = BOOT_N) -> str:
    out = [f"| nhóm | chỉ số | {name_new} - {name_base} | CI 95% (bootstrap ghép cặp theo tệp) | kết luận |", "|---|---|---|---|---|"]
    for grp in GROUPS:
        if df_new[df_new.group == grp].empty:
            continue
        pdiff = paired_diff(df_new, df_base, grp, n_boot)
        keys = ["false_split_per100", "files_with_false_split", "exact_rate"] if grp == "negative" else ["f1", "recall", "precision", "exact_rate", "false_split_per100"]
        for k in keys:
            r = pdiff[k]
            if math.isnan(r["lo"]):
                verdict = "không tính được (mẫu số bằng 0 ở nhiều lần lấy mẫu lại)"
            elif r["separable"]:
                better = (r["diff"] < 0) if k in ("false_split_per100", "files_with_false_split") else (r["diff"] > 0)
                verdict = "tách được: " + ("tốt hơn" if better else "kém hơn")
            else:
                verdict = "không tách được"
            out.append(f"| {GROUP_TITLES[grp]} (n={r['n_files']}) | {k} | {r['diff']:+.3f} | [{r['lo']:+.3f}; {r['hi']:+.3f}] | {verdict} |")
    return "\n".join(out)
