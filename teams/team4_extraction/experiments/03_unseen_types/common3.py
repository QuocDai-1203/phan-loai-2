"""common3.py - Nền chung cho thí nghiệm 03_unseen_types (Nhóm 4, giai đoạn 3): trỏ hạ tầng của 02_methods sang dữ liệu v2.

Không sửa `02_methods/lib.py`: ở đây chỉ (a) thêm đường dẫn `02_methods` vào sys.path, (b) đổi `lib.PRED_DIR` sang
`03_unseen_types/_cache/preds` (thư mục `_cache/` bị .gitignore: dự đoán có thể chứa họ tên), (c) cung cấp hàm đọc đáp án/đơn vị v2.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

HERE = Path(__file__).resolve().parent
TEAM = HERE.parents[1]
REPO = TEAM.parents[1]
M2 = TEAM / "experiments" / "02_methods"
for _p in (str(HERE), str(M2), str(TEAM), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import lib  # noqa: E402  (02_methods/lib.py)
from eval.field_metrics import load_specs  # noqa: E402
from methods.common import Unit, load_units  # noqa: E402

GOLD_V2 = TEAM / "gold" / "v2" / "fields_silver_v2.jsonl"
UNITS_V2 = TEAM / "gold" / "v2" / "units_v2.csv"
PAGES_V2 = TEAM / "gold" / "v2" / "pages_v2"
CACHE = HERE / "_cache"
lib.PRED_DIR = CACHE / "preds"
PRED_DIR = lib.PRED_DIR
TRUSTED = ("agreed_unverified", "model_adjudicated")
SPLITS = ("DEV", "TEST", "EXCLUDED")


def units_v2(split: str | None = None) -> List[Unit]:
    return load_units(split, path=UNITS_V2)


def gold_v2(review_statuses=None) -> Tuple[Dict[str, Dict[str, Dict[str, Any]]], Dict[str, str], Dict[str, str]]:
    """-> (gold, unit_types, unit_split) từ silver v2 (cùng quy ước `lib.load_gold` của giai đoạn 2)."""
    return lib.load_gold(GOLD_V2, load_specs(), review_statuses)


def expiry_fields() -> Dict[str, List[str]]:
    return {dt: [s.name for s in sp if s.is_expiry] for dt, sp in load_specs().items()}
