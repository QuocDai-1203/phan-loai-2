"""error_analysis.py - Phân tích lỗi của cấu hình zero-tuning, CHỈ trên DEV (TEST/EXCLUDED giữ nguyên chưa xem từng đơn vị).

    .venv\\Scripts\\python.exe -X utf8 teams\\team4_extraction\\experiments\\03_unseen_types\\error_analysis.py [--cfg cascade|llm|vlm|regex] [--mode lenient|normalized]

In bảng gộp theo (loại, trường, kiểu, kết quả) và danh sách lỗi theo đơn vị KHÔNG kèm giá trị (chỉ cờ: nguồn nào đúng, mực viết, trang).
Ghi `errors_dev.json` (cùng nội dung) để dựng RESULTS.md.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict

import common3 as C
import combine as CB
import lib
from eval.field_metrics import compare_field, load_specs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cfg", default="cascade")
    ap.add_argument("--mode", default="lenient")
    ap.add_argument("--regex-tag", default="")
    a = ap.parse_args()
    specs = load_specs()
    gold, types, split = C.gold_v2()
    dev = sorted(u for u in gold if split[u] == "DEV")
    ftypes = {dt: {x.name: x.type for x in sp} for dt, sp in specs.items()}
    spec_of = {(dt, s.name): s for dt, sp in specs.items() for s in sp}
    rows = {"regex": lib.load_preds("regex", "ocr_v2", a.regex_tag), "llm": lib.load_preds("llm", "ocr_v2"), "vlm": lib.load_preds("vlm", ""),
            "filename": lib.load_preds("filename", "")}
    rows["cascade"] = CB.cascade_typed(rows["regex"], rows["llm"], ftypes, dev)
    pred = lib.to_pred(rows[a.cfg])
    per_src = {k: lib.to_pred(v) for k, v in rows.items()}
    agg = Counter()
    detail = []
    for u in dev:
        dt = types[u]
        for name, g in gold[u].items():
            s = spec_of[(dt, name)]
            if not s.scored or s.is_pii:
                continue
            p = (pred.get(u) or {}).get("fields", {}).get(name)
            res = compare_field(g, p, s, a.mode)
            if res not in ("wrong", "empty", "spurious"):
                continue
            ok = [k for k, pp in per_src.items() if k != a.cfg and compare_field(g, (pp.get(u) or {}).get("fields", {}).get(name), s, a.mode) == "tp"]
            agg[(dt, name, s.type, res)] += 1
            detail.append({"unit_id": u, "doc_type": dt, "field": name, "type": s.type, "expiry": s.is_expiry, "outcome": res, "ink": g.get("ink"),
                           "gold_page": g.get("page"), "n_pages": None, "other_sources_correct": ok})
    print(f"{a.cfg} / {a.mode} / DEV: {len(detail)} lỗi")
    by_type = Counter((d["type"], d["outcome"]) for d in detail)
    print("theo kiểu trường/kết quả:", dict(by_type))
    print("theo mực:", dict(Counter((d["ink"], d["outcome"]) for d in detail)))
    for (dt, name, ty, res), n in sorted(agg.items(), key=lambda kv: -kv[1])[:40]:
        print(f"{n:3d}  {dt:24s} {name:24s} {ty:6s} {res}")
    (C.HERE / f"errors_dev_{a.cfg}.json").write_text(json.dumps(detail, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
