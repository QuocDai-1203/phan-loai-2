"""conftest.py - Cấu hình pytest gốc: đưa project root vào sys.path để `import src...` hoạt động khi chạy `pytest` từ root."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
