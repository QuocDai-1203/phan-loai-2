"""expcommon.py - Khung chạy chung cho các thí nghiệm của Nhóm 2: nạp dữ liệu, chấm, sinh bảng, phân tích lỗi, ghi RESULTS.md.

Mỗi thí nghiệm `experiments/NN_ten/run.py` chỉ cần khai báo các phương pháp {tên: hàm(doc_id, doc) -> set(trang bắt đầu >= 2)}.
Phần phân tích bằng lời do người viết giữ ở `experiments/NN_ten/notes.md` (được nối vào cuối RESULTS.md).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import platform
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import splitlib as sl  # noqa: E402

REPO = sl.REPO


def sha10(path: Path) -> str:
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()[:10]


def common_args(desc: str = "") -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=desc)
    ap.add_argument("--scope", default="dev", choices=["dev", "all"],
                    help="dev = DEV + EXCLUDED_COMPOSITE (mặc định, được nhìn lỗi). all = thêm tài liệu TEST (cần --final-test)")
    ap.add_argument("--final-test", action="store_true", help="xác nhận đây là lần chấm cuối, cấu hình đã đóng băng, để mở tài liệu TEST")
    ap.add_argument("--boot", type=int, default=sl.BOOT_N)
    ap.add_argument("--no-write", action="store_true", help="không ghi RESULTS.md / CSV")
    return ap


def check_scope(args) -> None:
    if args.scope == "all" and not args.final_test:
        raise SystemExit("scope=all mở tài liệu TEST: phải thêm --final-test (cấu hình đã đóng băng trên DEV).")


def setup(args):
    check_scope(args)
    gold = sl.load_gold()
    ids = sl.scope_doc_ids(gold, args.scope)
    docs = sl.load_documents(ids)
    return gold, ids, docs


def reproduce_header(exp_dir: Path, cmd: str, args, extra: Optional[Dict[str, str]] = None) -> str:
    meta = {
        "ngày chạy (UTC)": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "lệnh": f"`{cmd}`",
        "đáp án": f"`teams/team2_splitting/gold/boundary_gold_v0.csv` sha1[:10] = `{sha10(sl.GOLD_CSV)}` (v0, máy, CHƯA người kiểm)",
        "nhãn": f"`data/labels_v2.csv` sha1[:10] = `{sha10(sl.LABELS_CSV)}`",
        "văn bản": f"`data/ocr_v2.jsonl` (OCR cục bộ, tối đa 30 trang/tài liệu) sha1[:10] = `{sha10(sl.OCR_JSONL)}`",
        "phạm vi": ("**dev** = DEV + EXCLUDED_COMPOSITE (không có tài liệu TEST)" if args.scope == "dev"
                    else "**all** = cả tài liệu TEST, chấm MỘT lần với cấu hình đã đóng băng"),
        "bootstrap": f"{args.boot} lần lấy mẫu lại theo TỆP, seed {sl.BOOT_SEED}, percentile 95%",
        "máy": f"{platform.platform()}, Python {platform.python_version()}",
    }
    if extra:
        meta.update(extra)
    return "\n".join(f"- **{k}:** {v}" for k, v in meta.items())


# ---------------------------------------------------------------------------
# Phân tích lỗi
# ---------------------------------------------------------------------------
def error_table(df_methods: pd.DataFrame, preds: Dict[str, Set[int]], gold: pd.DataFrame, reason_fn: Optional[Callable] = None,
                docs: Optional[Dict] = None, top: int = 5) -> str:
    """Gom lỗi (tách nhầm FP / sót FN) theo (loại lỗi, nhóm, lý do, loại trang). `reason_fn(doc, page_number)` -> chuỗi (không chứa định danh cá nhân)."""
    meta = gold.drop_duplicates("doc_id").set_index("doc_id")
    cnt: Counter = Counter()
    ex: Dict[tuple, List[str]] = defaultdict(list)
    for d, pred in preds.items():
        if d not in meta.index:
            continue
        grp = meta.loc[d, "eval_group"]
        if grp not in sl.GROUPS:
            continue
        n = len(docs[d].pages) if docs else int(meta.loc[d, "n_pages"])
        g = sl.gold_for_doc(gold, d, n)
        pos = g[g.page >= 2].set_index("page")
        true = set(pos[pos.is_start == 1].index.astype(int))
        pr = {p for p in pred if 2 <= p <= n}
        for p in sorted(pr - true):
            r = reason_fn(docs[d], p) if (reason_fn and docs) else "?"
            key = ("tách nhầm (FP)", grp, r, str(pos.loc[p, "page_doc_type"]))
            cnt[key] += 1
            ex[key].append(f"{d}:{p}")
        for p in sorted(true - pr):
            r = reason_fn(docs[d], p) if (reason_fn and docs) else "?"
            key = ("sót ranh giới (FN)", grp, r, str(pos.loc[p, "page_doc_type"]))
            cnt[key] += 1
            ex[key].append(f"{d}:{p}")
    lines = [f"| # | loại lỗi | nhóm | lý do (dấu hiệu trên trang) | loại trang | số lần | ví dụ (doc_id:trang) |", "|---|---|---|---|---|---|---|"]
    for i, (key, c) in enumerate(cnt.most_common(top), 1):
        lines.append(f"| {i} | {key[0]} | {key[1]} | {key[2]} | {key[3]} | {c} | {', '.join(ex[key][:3])} |")
    total_fp = sum(c for k, c in cnt.items() if k[0].startswith("tách"))
    total_fn = sum(c for k, c in cnt.items() if k[0].startswith("sót"))
    lines.append(f"\n(tổng: {total_fp} tách nhầm, {total_fn} sót; {len(cnt)} kiểu lỗi khác nhau; bảng liệt kê {min(top, len(cnt))} kiểu đông nhất)")
    return "\n".join(lines)


def save_per_file(exp_dir: Path, name: str, df: pd.DataFrame, preds: Dict[str, Set[int]], scope: str) -> None:
    d = df.copy()
    d["pred_starts"] = d.doc_id.map(lambda x: " ".join(str(p) for p in sorted(preds[x])))
    out = exp_dir / "results"
    out.mkdir(exist_ok=True)
    d.to_csv(out / f"per_file_{name}_{scope}.csv", index=False)


def append_results_table(row: Dict, path: Path = sl.HERE / "results" / "results_table.csv") -> None:
    """Bảng kết quả riêng của Nhóm 2 (bảng chung của Nhóm 3 có cột accuracy/macro_f1 không hợp với bài toán tách). Chỉ thêm dòng; chạy lại cùng (method, scope, group) thì thay dòng đó."""
    path.parent.mkdir(exist_ok=True)
    new = pd.DataFrame([row]).astype(str)
    if path.exists():
        old = pd.read_csv(path, dtype=str, keep_default_na=False)
        # chạy lại cùng (method, scope, group) thì thay dòng cũ: bảng luôn là kết quả của lần chạy mới nhất, không trùng lặp
        key = ["method", "scope", "group"]
        mask = old[key].apply(tuple, axis=1).isin(new[key].apply(tuple, axis=1))
        new = pd.concat([old[~mask], new], ignore_index=True)
    new.to_csv(path, index=False, encoding="utf-8")


def results_rows(method: str, df: pd.DataFrame, scope: str, run_id: str, notes: str = "") -> List[Dict]:
    rows = []
    for grp in sl.GROUPS:
        sub = df[df.group == grp]
        if sub.empty:
            continue
        s = sl.group_summary(sub.assign(group=grp), grp)
        f = lambda k, i: ("" if (s[k][i] != s[k][i]) else f"{s[k][i]:.4f}")  # noqa: E731
        rows.append(dict(
            run_id=run_id, timestamp=_dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"), method=method, scope=scope, group=grp,
            n_files=len(sub), n_positions=int(sub.n_pos.sum()), n_true_boundaries=int(sub.n_true.sum()),
            precision=f("precision", 0), precision_lo=f("precision", 1), precision_hi=f("precision", 2),
            recall=f("recall", 0), recall_lo=f("recall", 1), recall_hi=f("recall", 2),
            f1=f("f1", 0), f1_lo=f("f1", 1), f1_hi=f("f1", 2),
            exact_rate=f("exact_rate", 0), exact_lo=f("exact_rate", 1), exact_hi=f("exact_rate", 2),
            false_splits=int(sub.fp.sum()), false_split_per100=f("false_split_per100", 0),
            gold_sha=sha10(sl.GOLD_CSV), labels_sha=sha10(sl.LABELS_CSV), notes=notes,
        ))
    return rows


# ---------------------------------------------------------------------------
# Baseline (luật cũ) dùng chung cho phép so sánh ghép cặp
# ---------------------------------------------------------------------------
def baseline_starts(doc_id, doc) -> Set[int]:
    from src.splitting.boundary_detector import split_document
    return {s.start_page for s in split_document(doc).slices if s.start_page >= 2}


def baseline_eval(ids, docs, gold):
    return sl.evaluate_method(baseline_starts, ids, docs, gold)


def reason_v2(doc, page_number) -> str:
    """Dấu hiệu của bộ luật v2 trên trang (để gom lỗi). Không chứa định danh cá nhân."""
    from src.splitting.page_features import page_feat
    from src.splitting.page_features import TITLE_KEYWORDS
    from src.common.text_norm import normalize_text
    page = next(p for p in doc.pages if p.page_number == page_number)
    f = page_feat(page.full_text)
    bits = []
    if f.motto_top:
        bits.append("quốc hiệu ở đầu trang")
    if f.title_at_line_start:
        lines = [normalize_text(x) for x in page.full_text.split("\n") if x.strip()][:6]
        kw = next((k for k in TITLE_KEYWORDS if any(l.lstrip("0123456789.-) ").startswith(normalize_text(k)) for l in lines)), "?")
        bits.append(f"tiêu đề đầu dòng '{kw}'")
    if f.page_no:
        bits.append(f"đánh số trang {f.page_no[0]}/{f.page_no[1]}")
    if f.signature_only:
        bits.append("chỉ chữ ký/trống")
    return ", ".join(bits) if bits else "không có dấu hiệu luật"


# ---------------------------------------------------------------------------
# Báo cáo cho phương pháp có học (03, 04)
# ---------------------------------------------------------------------------
def rule_v2_starts(doc_id, doc) -> Set[int]:
    from src.splitting.rules_v2 import rule_starts
    fl = rule_starts([p.full_text for p in doc.pages])
    return {doc.pages[i].page_number for i, x in enumerate(fl) if x and i > 0}


def syn_summary_md(per_method: Dict[str, pd.DataFrame], n_boot: int = sl.BOOT_N) -> str:
    out = []
    groups = sorted(next(iter(per_method.values())).group.unique())
    for grp in groups:
        ref = next(iter(per_method.values()))
        s = ref[ref.group == grp]
        out.append(f"\n**{grp}** ({len(s)} composite tổng hợp, {int(s.n_pos.sum())} vị trí, {int(s.n_true.sum())} ranh giới thật)\n")
        out.append("| phương pháp | precision | recall | F1 | exact-segment | tách nhầm / 100 vị trí |")
        out.append("|---|---|---|---|---|---|")
        for name, df in per_method.items():
            r = sl.group_summary(df, grp, n_boot)
            sub = df[df.group == grp]
            out.append(f"| {name} | {sl.fmt(r['precision'])} | {sl.fmt(r['recall'])} | {sl.fmt(r['f1'])} | "
                       f"{int(sub.exact.sum())}/{len(sub)} = {r['exact_rate'][0]:.3f} | {sl.fmt(r['false_split_per100'], 2)} |")
    return "\n".join(out)


def results_path(exp_dir: Path, scope: str) -> Path:
    """RESULTS.md cho phạm vi dev; phạm vi all (có tài liệu TEST, chấm một lần) ghi ra tệp riêng để không đè số dev."""
    return exp_dir / ("RESULTS.md" if scope == "dev" else "RESULTS_all_incl_test_docs.md")
