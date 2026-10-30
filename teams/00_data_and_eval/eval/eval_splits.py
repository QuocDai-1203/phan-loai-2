"""eval_splits.py - Chia DEV / TEST có nhóm (group-aware), tất định theo seed.

Quy tắc (xem 03_evaluation_protocol.md):
- Đơn vị = tài liệu duy nhất (bản sao byte-giống-hệt đi cùng đại diện của chúng).
- group = template_group nếu có, ngược lại = doc_id -> các tài liệu cùng biểu mẫu không bao giờ nằm ở hai phía.
- Bước 1: StratifiedGroupKFold(5) -> một fold (~20%) làm TEST bị khóa. Phần còn lại (~80%) = DEV.
- Bước 2: DEV chia 5 fold StratifiedGroupKFold; lặp với 3 seed (cột fold, fold_s1, fold_s2).
- Nhóm quá lớn: một biểu mẫu có thể chiếm gần hết một lớp (vd. 23/24 chứng chỉ tập huấn cùng một mẫu). Chia nghiêm ngặt thì
  lớp đó chỉ nằm ở MỘT phía (không học được hoặc không có gì để chấm). `max_group_size` (mặc định 5) cắt nhóm lớn thành các
  nhóm con ngẫu nhiên-tất định <= 5 tài liệu; đổi lại có rò rỉ biểu mẫu nhẹ giữa các nhóm con. Muốn chia nghiêm ngặt tuyệt đối:
  max_group_size=None (file splits_strict.csv). Cả hai biến thể đều được xuất ra và so sánh trong RESULTS.md.
"""

from __future__ import annotations

import hashlib
import math
import warnings
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold

SPLIT_SEED = 42
TEST_FRACTION_FOLDS = 5  # 1 / 5 = 20%
N_DEV_FOLDS = 5
FOLD_SEEDS = (0, 1, 2)
DEFAULT_MAX_GROUP = 5


def _h(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def effective_groups(reps: pd.DataFrame, max_group_size: Optional[int] = DEFAULT_MAX_GROUP) -> pd.Series:
    """group cho từng tài liệu đại diện (index = doc_id). Nhóm > max_group_size bị cắt đều thành các nhóm con tất định."""
    grp = {}
    tg = reps.set_index("doc_id")["template_group"]
    for doc_id, g in tg.items():
        grp[doc_id] = g if isinstance(g, str) and g else doc_id
    s = pd.Series(grp)
    if max_group_size:
        for g, members in s.groupby(s).groups.items():
            members = sorted(members, key=_h)
            if len(members) > max_group_size:
                n_sub = math.ceil(len(members) / max_group_size)
                for i, d in enumerate(members):
                    s[d] = f"{g}.{i % n_sub}"
    return s


def _sgkf(n_splits: int, seed: int) -> StratifiedGroupKFold:
    return StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)


def _fold_assign(y: Sequence[str], groups: Sequence[str], n_splits: int, seed: int) -> np.ndarray:
    fold = np.full(len(y), -1, dtype=int)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # lớp hiếm có ít tài liệu hơn n_splits -> cảnh báo vô hại
        for k, (_, te) in enumerate(_sgkf(n_splits, seed).split(np.zeros(len(y)), list(y), list(groups))):
            fold[te] = k
    return fold


def make_splits(
    reps: pd.DataFrame,
    files: pd.DataFrame,
    max_group_size: Optional[int] = DEFAULT_MAX_GROUP,
    seed: int = SPLIT_SEED,
    fold_seeds: Sequence[int] = FOLD_SEEDS,
    n_dev_folds: int = N_DEV_FOLDS,
) -> pd.DataFrame:
    """Trả về bảng splits cho MỌI file trong `files`.

    reps: tài liệu duy nhất không-composite (cột doc_id, doc_type, template_group).
    files: mọi file (cột doc_id, rep_doc_id, composite_mixed).
    Cột kết quả: doc_id, split (DEV|TEST|EXCLUDED_COMPOSITE), fold, fold_s1, fold_s2, group, rep_doc_id, is_rep.
    """
    reps = reps.sort_values("doc_id").reset_index(drop=True)
    groups = effective_groups(reps, max_group_size)
    g = reps["doc_id"].map(groups).tolist()
    y = reps["doc_type"].tolist()

    test_fold = _fold_assign(y, g, TEST_FRACTION_FOLDS, seed)
    is_test = test_fold == 0
    reps["split"] = np.where(is_test, "TEST", "DEV")
    reps["group"] = g
    for c in ("fold", "fold_s1", "fold_s2"):
        reps[c] = -1

    dev = reps[reps["split"] == "DEV"]
    for col, s in zip(("fold", "fold_s1", "fold_s2"), fold_seeds):
        f = _fold_assign(dev["doc_type"].tolist(), dev["group"].tolist(), n_dev_folds, seed * 1000 + s)
        reps.loc[dev.index, col] = f

    by_rep = reps.set_index("doc_id")
    rows = []
    for _, r in files.sort_values("doc_id").iterrows():
        rep = r["rep_doc_id"]
        if bool(r["composite_mixed"]):
            rows.append(dict(doc_id=r["doc_id"], split="EXCLUDED_COMPOSITE", fold=-1, fold_s1=-1, fold_s2=-1,
                             group=r["doc_id"], rep_doc_id=rep, is_rep=int(r["doc_id"] == rep)))
            continue
        x = by_rep.loc[rep]
        rows.append(dict(doc_id=r["doc_id"], split=x["split"], fold=int(x["fold"]), fold_s1=int(x["fold_s1"]),
                         fold_s2=int(x["fold_s2"]), group=x["group"], rep_doc_id=rep, is_rep=int(r["doc_id"] == rep)))
    return pd.DataFrame(rows)


def naive_folds(labels: Sequence[str], n_splits: int = 5, seed: int = 0) -> np.ndarray:
    """Chia NGÂY THƠ: StratifiedKFold ngẫu nhiên, bỏ qua nhóm/bản sao. Chỉ để minh họa mức rò rỉ -- KHÔNG dùng để chọn mô hình."""
    fold = np.full(len(labels), -1, dtype=int)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for k, (_, te) in enumerate(StratifiedKFold(n_splits, shuffle=True, random_state=seed).split(np.zeros(len(labels)), list(labels))):
            fold[te] = k
    return fold


def grouped_folds(labels: Sequence[str], groups: Sequence[str], n_splits: int = 5, seed: int = 0) -> np.ndarray:
    return _fold_assign(labels, groups, n_splits, seed)


def check_no_group_leak(splits: pd.DataFrame) -> List[str]:
    """Trả về danh sách vi phạm (rỗng = ổn): nhóm nằm ở >1 split, hoặc nhóm nằm ở >1 fold trong DEV."""
    bad = []
    use = splits[splits["split"].isin(["DEV", "TEST"])]
    for g, sub in use.groupby("group"):
        if sub["split"].nunique() > 1:
            bad.append(f"group {g} xuất hiện ở nhiều split")
    dev = use[use["split"] == "DEV"]
    for col in ("fold", "fold_s1", "fold_s2"):
        for g, sub in dev.groupby("group"):
            if sub[col].nunique() > 1:
                bad.append(f"group {g} nằm ở nhiều fold ({col})")
    rep_split = use.groupby("rep_doc_id")["split"].nunique()
    bad += [f"bản sao của {r} nằm ở nhiều split" for r, n in rep_split.items() if n > 1]
    return bad
