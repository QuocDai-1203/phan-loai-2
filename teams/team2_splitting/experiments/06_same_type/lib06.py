"""lib06.py - Khung dùng chung của thí nghiệm 06 (T5: nhiều bản cùng loại trong một tệp).

Mô phỏng `model+merge` ngoại tuyến, KHÔNG gọi lại bộ phân loại / LLM:
* điểm cặp trang cross-fitted của c2 lấy từ `teams/00_data_and_eval/experiments/01_end_to_end/results/pair_scores_dev.json`;
* nhãn của từng lát cắt lấy từ kết quả S10 đã chạy (`per_file_dev.csv`, cột `pred_segs`): lát cắt cơ sở nhận nhãn của đoạn S10
  chứa trang đầu của nó. Với tách mới (thêm/bớt ranh giới) đây là XẤP XỈ: lát cắt mới không được phân loại lại.
Hàm `simulate_s10` phải tái lập đúng pred_segs của S10 (kiểm ở run_baseline_check).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
T2 = HERE.parents[1]
sys.path.insert(0, str(T2))
sys.path.insert(0, str(T2 / "gold"))
import expcommon as ec  # noqa: E402
import splitlib as sl  # noqa: E402
from src.splitting.type_merge import load_one_sheet_types, merge_groups  # noqa: E402

E2E = sl.REPO / "teams" / "00_data_and_eval" / "experiments" / "01_end_to_end" / "results"
ONE_SHEET = load_one_sheet_types()


def load_s10_labels() -> Dict[str, List[Tuple[int, int, str]]]:
    """doc_id -> [(a, b, nhãn)] các đoạn của S10 (nhãn '?' = bộ phân loại từ chối)."""
    pf = pd.read_csv(E2E / "per_file_dev.csv", dtype=str, keep_default_na=False)
    pf = pf[pf.variant == "S10"]
    out = {}
    for r in pf.itertuples():
        segs = []
        for s in r.pred_segs.split(";"):
            rng, lab = s.split(":", 1)
            a, _, b = rng.partition("-")
            segs.append((int(a), int(b or a), "" if lab == "?" else lab))
        out[r.doc_id] = segs
    return out


def load_scores() -> Dict[str, List[Optional[float]]]:
    return json.loads((E2E / "pair_scores_dev.json").read_text(encoding="utf-8"))


def label_at(segs: Sequence[Tuple[int, int, str]], page: int) -> str:
    for a, b, lab in segs:
        if a <= page <= b:
            return lab
    return ""


def base_starts(scores: Sequence[Optional[float]], pages: Sequence[int], tau: float) -> List[int]:
    """Chỉ số vị trí (0-based) mở lát cắt cơ sở: trang 0 và mọi trang có điểm >= tau."""
    return [0] + [i for i in range(1, len(pages)) if scores[i] is not None and scores[i] >= tau]


def simulate(scores: Sequence[Optional[float]], pages: Sequence[int], segs, tau: float = 0.7, keep_above: Optional[float] = 0.99,
             merge: bool = True, id_flags: Optional[Sequence[bool]] = None, id_add: bool = True, id_block: bool = True) -> Set[int]:
    """Tập trang >= 2 mở tài liệu mới sau tách (tau) + gộp cùng loại.
    `id_flags[i]` (i = chỉ số trang 0-based): quy tắc "bản khác" bật ở trang i. `id_add`: THÊM ranh giới ở trang đó dù điểm < tau;
    `id_block`: ranh giới đó KHÔNG bị gộp lại dù hai bên cùng loại."""
    st = base_starts(scores, pages, tau)
    forced = set()
    if id_flags is not None:
        forced = {i for i in range(1, len(pages)) if id_flags[i]}
        if id_add:
            st = sorted(set(st) | forced)
    if not merge:
        return {pages[i] for i in st if i > 0}
    labels = [label_at(segs, pages[i]) for i in st]
    conf = [1.0] + [float(scores[i]) if scores[i] is not None else 0.0 for i in st[1:]]
    if id_block:
        conf = [1.0 if (k > 0 and st[k] in forced) else c for k, c in enumerate(conf)]
    groups = merge_groups(labels, ONE_SHEET, conf, keep_above if keep_above is not None else 2.0)
    return {pages[st[g[0]]] for g in groups if st[g[0]] > 0}


def evaluate(pred: Dict[str, Set[int]], ids, docs, gold) -> pd.DataFrame:
    return sl.evaluate_method(None, ids, docs, gold, prediction_cache=pred)[0]
