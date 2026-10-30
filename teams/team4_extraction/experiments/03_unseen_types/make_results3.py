"""make_results3.py - Chấm các phương pháp trên silver v2 (17 loại mới), báo riêng DEV / TEST / EXCLUDED / gộp (Nhóm 4, giai đoạn 3).

    # zero-tuning (cấu hình đóng băng của giai đoạn 2, chưa chỉnh gì):
    .venv\\Scripts\\python.exe -X utf8 teams\\team4_extraction\\experiments\\03_unseen_types\\make_results3.py --set base
    # sau một vòng cải tiến (luật chung chỉnh trên DEV):  phần không chỉnh (TEST+EXCLUDED) chỉ chấm MỘT lần, cần dev_selection3.json
    .venv\\Scripts\\python.exe -X utf8 teams\\team4_extraction\\experiments\\03_unseen_types\\make_results3.py --set improved --final-test

Ghi `results3_<set>.json` (cạnh tệp này). Chỉ số tổng hợp + mã đơn vị/tên trường; KHÔNG có giá trị trường nào.
Cấu hình chấm: regex, llm, vlm, filename, "cascade theo kiểu" (văn bản: LLM trước; ngày/số/mã: luật trước) và cascade + quy tắc tự nhận hạn đóng băng.
Với `--set improved`: dùng dự đoán luật có hậu tố `v2` (`regex@ocr_v2.v2.jsonl`) thay luật gốc; LLM/VLM/filename giữ nguyên.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from typing import Any, Dict, List

import common3 as C
import combine as CB
import lib
from eval.field_metrics import load_specs
import make_results as MR

CFG_MAIN = ["regex", "llm", "vlm", "filename", "cascade", "cascade+reject"]
FROZEN_RULE = json.loads((C.M2 / "dev_selection.json").read_text(encoding="utf-8"))["expiry_rule"]      # đóng băng ở giai đoạn 2
SEL3 = C.HERE / "dev_selection3.json"


def outcome_counts(gold, pred, types, units, mode: str = "normalized") -> Dict[str, Dict[str, int]]:
    """{'ALL': {n_gold, correct, empty, wrong, spurious, absent_ok}} cho trường hạn + theo trường hạn."""
    specs = load_specs()
    exp = {(dt, s.name) for dt, v in specs.items() for s in v if s.is_expiry}
    out = {"n_gold": 0, "correct": 0, "empty": 0, "wrong": 0, "spurious": 0, "n_absent": 0, "skip": 0}
    res = lib.field_outcomes(gold, pred, types, units, mode, specs)
    for (u, f), r in res.items():
        if (types[u], f) not in exp:
            continue
        if r == "tp":
            out["n_gold"] += 1; out["correct"] += 1
        elif r == "empty":
            out["n_gold"] += 1; out["empty"] += 1
        elif r == "wrong":
            out["n_gold"] += 1; out["wrong"] += 1
        elif r == "spurious":
            out["n_absent"] += 1; out["spurious"] += 1
        elif r == "tn":
            out["n_absent"] += 1
    out["wrong_upper95"] = CB.cp_upper(out["wrong"], out["n_gold"]) if out["n_gold"] else math.nan
    return out


def load_rows(units: List[str], regex_tag: str) -> Dict[str, Dict[str, Any]]:
    rows = {"regex": lib.load_preds("regex", "ocr_v2", regex_tag), "llm": lib.load_preds("llm", "ocr_v2"),
            "vlm": lib.load_preds("vlm", ""), "filename": lib.load_preds("filename", "")}
    return {k: {u: r for u, r in v.items() if u in units} for k, v in rows.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", default="base", choices=["base", "improved"])
    ap.add_argument("--rule", default=None, help="mặc định: base = quy tắc giai đoạn 2; improved = quy tắc trong dev_selection3.json")
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--final-test", action="store_true")
    a = ap.parse_args()
    if a.set == "improved" and not (a.final_test and SEL3.exists()):
        raise SystemExit("--set improved chấm cả TEST+EXCLUDED: cần --final-test và dev_selection3.json (đóng băng trước).")
    a.rule = a.rule or (json.loads(SEL3.read_text(encoding="utf-8"))["expiry_rule"] if a.set == "improved" else FROZEN_RULE)
    specs = load_specs()
    gold, types, split = C.gold_v2()
    all_units = sorted(gold)
    ftypes = {dt: {x.name: x.type for x in sp} for dt, sp in specs.items()}
    expf = C.expiry_fields()
    rows_all = load_rows(set(all_units), "v2" if a.set == "improved" else "")
    for n, r in rows_all.items():
        for x in r.values():
            x["_tag"] = n
        miss = [u for u in all_units if u not in r]
        if miss:
            print(f"CẢNH BÁO {n}: thiếu {len(miss)} đơn vị", flush=True)
    out: Dict[str, Any] = {"set": a.set, "rule": a.rule, "groups": {}}
    groups = {"DEV": [u for u in all_units if split[u] == "DEV"], "TEST": [u for u in all_units if split[u] == "TEST"],
              "EXCLUDED": [u for u in all_units if split[u] == "EXCLUDED"],
              "TEST+EXCLUDED": [u for u in all_units if split[u] in ("TEST", "EXCLUDED")], "ALL": all_units}
    for gname, units in groups.items():
        rows = {n: {u: r[u] for u in units if u in r} for n, r in rows_all.items()}
        srcs = {"regex": rows["regex"], "llm": rows["llm"], "vlm": rows["vlm"], "filename": rows["filename"]}
        casc = CB.cascade_typed(rows["regex"], rows["llm"], ftypes, units)
        rows["cascade"] = casc
        rows["cascade+reject"] = CB.expiry_rule(a.rule, srcs, casc, expf)
        cfgs = list(CFG_MAIN)
        if a.set == "improved" and a.rule != FROZEN_RULE:
            rows["cascade+reject(phase2 rule)"] = CB.expiry_rule(FROZEN_RULE, srcs, casc, expf)
            cfgs.append("cascade+reject(phase2 rule)")
        g: Dict[str, Any] = {"n_units": len(units), "units_by_type": {t: sum(1 for u in units if types[u] == t) for t in sorted({types[u] for u in units})},
                             "configs": {}}
        for name in cfgs:
            r = rows[name]
            pr = lib.to_pred(r)
            cfg: Dict[str, Any] = {}
            for mode in ("normalized", "lenient"):
                cfg[mode] = MR.summarize(lib.score_cfg(gold, pr, types, units, mode, n_boot=a.n_boot, specs=specs))
                cfg["expiry_counts_" + mode] = outcome_counts(gold, pr, types, units, mode)
            cfg["by_doc_type"] = {}
            if gname in ("DEV", "ALL"):
                for t in g["units_by_type"]:
                    ut = [u for u in units if types[u] == t]
                    cfg["by_doc_type"][t] = {"n_units": len(ut), **{m: MR.summarize(lib.score_cfg(gold, pr, types, ut, m, n_boot=300, specs=specs)) for m in ("normalized", "lenient")},
                                             "expiry_counts": outcome_counts(gold, pr, types, ut, "normalized")}
            by_ink = {m: lib.by_ink(gold, pr, types, units, m, specs) for m in ("normalized", "lenient")}
            for m in by_ink:
                agg: Dict[str, Dict[str, int]] = {}
                for ink, d in by_ink[m].items():
                    tgt = agg.setdefault(MR.collapse_ink(ink), {})
                    for kk, vv in d.items():
                        tgt[kk] = tgt.get(kk, 0) + vv
                by_ink[m] = agg
            cfg["by_ink"] = by_ink
            cfg["latency"] = MR.latency(r, units) if name in ("regex", "llm", "vlm") else None
            cfg["n_status"] = {s: sum(1 for x in r.values() if x["status"] == s) for s in ("ok", "skipped", "error")}
            g["configs"][name] = cfg
        g["abstention"] = CB.abstention_table(gold, types, units, srcs, expf, rules=list(dict.fromkeys([a.rule, FROZEN_RULE, "regex", "llm", "vlm", "filename", "llm=vlm", "regex=llm", "regex=vlm", "regex=llm=vlm", "llm=filename", "vlm=filename"])))
        g["review_queue"] = CB.review_queue_stats(gold, types, units, srcs, expf, a.rule)
        out["groups"][gname] = g
        print("xong", gname, len(units), flush=True)
    (C.HERE / f"results3_{a.set}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float) + "\n", encoding="utf-8")
    print("đã ghi", C.HERE / f"results3_{a.set}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
