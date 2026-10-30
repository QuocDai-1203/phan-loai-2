"""Đưa thư mục nhóm 4 và gốc repo vào sys.path để `import eval.normalize`, `import schema.build_schema`... chạy được."""
import sys
from pathlib import Path

TEAM = Path(__file__).resolve().parent
ROOT = TEAM.parents[1]
for p in (str(TEAM), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)
