"""dev_iterate.py - Vòng cải tiến luật chung: chạy luật `generic=True` và chấm CHỈ trên DEV (không đụng TEST/EXCLUDED).

    .venv\\Scripts\\python.exe -X utf8 teams\\team4_extraction\\experiments\\03_unseen_types\\dev_iterate.py [--errors]

In: số trường ngày đúng/bỏ trống/sai của luật gốc (v1: toàn null cho loại mới) và luật chung, riêng trường hạn, và (với --errors) danh sách lỗi
DEV theo (đơn vị, trường, loại lỗi) — không in giá trị.
"""

from __future__ import annotations

import argparse
import json

import common3 as C
import lib
from eval.field_metrics import load_specs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--errors", action="store_true")
    ap.add_argument("--tag", default="v2")
    a = ap.parse_args()
    specs = load_specs()
    gold, types, split = C.gold_v2()
    dev = [u for u in units_dev()]
    unit_objs = [u for u in C.units_v2("DEV")]
    lib.run_config("regex", "ocr_v2", unit_objs, tag=a.tag, force=True, verbose=False, generic=True)
    rows = lib.load_preds("regex", "ocr_v2", a.tag)
    pred = lib.to_pred(rows)
    out = lib.field_outcomes(gold, pred, types, dev, "normalized", specs)
    datef = {(dt, s.name) for dt, v in specs.items() for s in v if s.type == "date" and s.scored and not s.is_pii}
    expf = {(dt, s.name) for dt, v in specs.items() for s in v if s.is_expiry}
    from collections import Counter
    for label, keyset in (("date", datef), ("expiry", expf)):
        c = Counter(r for (u, f), r in out.items() if (types[u], f) in keyset)
        print(label, dict(c))
    if a.errors:
        for (u, f), r in sorted(out.items()):
            if r in ("wrong", "empty", "spurious") and (types[u], f) in datef:
                print(u, types[u], f, r, gold[u][f].get("ink"))
    return 0


def units_dev():
    return [u.unit_id for u in C.units_v2("DEV")]


if __name__ == "__main__":
    raise SystemExit(main())
