"""normalize.py - tương thích ngược: cài đặt chuẩn nằm ở `src/extraction/normalize.py` (được thăng cấp sau khi chấm trên DEV).

`from eval.normalize import ...` vẫn dùng được như trước; mọi tên công khai được xuất lại.
"""
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parents[3])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.extraction.normalize import *  # noqa: F401,F403,E402
from src.extraction.normalize import _is_blank, _year, canonical_decimal  # noqa: F401,E402
