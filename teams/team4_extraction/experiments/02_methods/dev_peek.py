"""dev_peek.py - Phân tích lỗi bằng mắt, CHỈ TRÊN DEV (tuyệt đối không dùng cho TEST). In giá trị đáp án và dự đoán của các trường sai.

    .venv\\Scripts\\python.exe -X utf8 .../dev_peek.py regex@ocr_v2 [--fields ngay_het_han,so_giay] [--types GCN_DDK_BAN_LE_XD] [--summary]
Trường PII không bao giờ được in. Từ chối chạy nếu có đơn vị TEST trong kết quả.
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import field_outcomes, load_gold, load_preds, to_pred  # noqa: E402
from eval.field_metrics import load_specs  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("cfg")
ap.add_argument("--fields", default="")
ap.add_argument("--types", default="")
ap.add_argument("--tag", default="")
ap.add_argument("--mode", default="normalized")
ap.add_argument("--summary", action="store_true")
a = ap.parse_args()
method, _, source = a.cfg.partition("@")
gold, types, split = load_gold()
rows = load_preds(method, source or "ocr_v2", a.tag)
assert all(split[u] != "TEST" for u in rows if u in split), "có đơn vị TEST: dừng"
pred = to_pred(rows)
dev = [u for u in rows if split.get(u) == "DEV"]
out = field_outcomes(gold, pred, types, dev, a.mode)
if a.summary:
    c = Counter()
    for (u, f), r in out.items():
        c[(types[u], f, r)] += 1
    for (t, f, r), n in sorted(c.items()):
        if r in ("wrong", "empty", "spurious"):
            print(t, f, r, n)
    raise SystemExit
fl = set(filter(None, a.fields.split(",")))
tl = set(filter(None, a.types.split(",")))
for (u, f), r in sorted(out.items()):
    if r not in ("wrong", "empty", "spurious") or (fl and f not in fl) or (tl and types[u] not in tl):
        continue
    g = gold[u][f]
    p = (rows[u]["fields"].get(f) or {}).get("value")
    print(f"{u} {f} [{r}] ink={g['ink']} gold={str(g['value'])[:80]!r} pred={str(p)[:80]!r}")
