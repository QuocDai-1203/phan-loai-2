"""make_results.py - Chấm mọi cấu hình đã chạy + ghép + phân tích từ chối; ghi JSON và bảng Markdown (Nhóm 4, T4).

    .venv\\Scripts\\python.exe -X utf8 .../make_results.py --split DEV  --gold all      # trong lúc phát triển (chỉ DEV)
    .venv\\Scripts\\python.exe -X utf8 .../make_results.py --split TEST --gold all --final-test   # sau khi đóng băng

Ghi `results_<split>_<gold>.json` và `tables_<split>_<gold>.md` (cạnh tệp này). Chỉ số tổng hợp, KHÔNG có giá trị trường nào.
`--gold all` = mọi trường có đáp án (silver: Haiku là người chính, Sonnet 40 đơn vị, Opus phân xử các mục bất đồng/rủi ro);
`--gold trusted` = chỉ trường `agreed_unverified` hoặc `model_adjudicated` (độ tin cậy cao hơn, ít trường hơn).
TEST: cần `--final-test` và `dev_selection.json` (quy tắc từ chối chọn trên DEV được đọc từ đó, KHÔNG tính lại trên TEST).
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import combine as C  # noqa: E402
from lib import (PRED_DIR, by_ink, load_gold, load_preds, restrict_gold_pages, score_cfg, sub)  # noqa: E402
from eval.field_metrics import load_specs  # noqa: E402

BASE: List[Tuple[str, str]] = [("regex", "ocr_v2"), ("regex", "ocr_llm_haiku"), ("regex", "text_layer"), ("filename", ""),
                               ("gliner", "ocr_v2"), ("gliner", "ocr_llm_haiku"), ("gliner", "text_layer"),
                               ("llm", "ocr_v2"), ("llm", "ocr_llm_haiku"), ("llm", "text_layer"), ("vlm", "")]
TRUSTED = ("agreed_unverified", "model_adjudicated")
SELECTION = HERE / "dev_selection.json"


def name_of(m: str, s: str) -> str:
    return m if not s else f"{m}@{s}"


def collapse_ink(ink: Optional[str]) -> str:
    if not ink:
        return "unknown"
    return "under_stamp" if "under_stamp" in ink else "handwritten" if "handwritten" in ink else ink


def summarize(res: Dict[str, Any]) -> Dict[str, Any]:
    pt = {r["type"]: r for r in res["per_type"]}
    ex = next(r for r in res["expiry"] if r["field"] == "ALL_EXPIRY")
    return {"n_units": res["counts"]["n_units"], "n_failed": res["counts"]["n_failed"], "overall": res["overall"], "per_type": pt,
            "doc_level": res["doc_level"], "expiry_all": ex, "expiry_by_field": [r for r in res["expiry"] if r["field"] != "ALL_EXPIRY"]}


def latency(rows: Dict[str, Dict[str, Any]], units: List[str]) -> Dict[str, Any]:
    wall = [rows[u].get("orig_latency_ms") or rows[u]["latency_ms"] for u in units if u in rows and rows[u]["status"] == "ok" and (rows[u].get("orig_latency_ms") or rows[u].get("latency_ms"))]
    inf = []
    for u in units:
        m = (rows.get(u) or {}).get("meta") or {}
        if m.get("total_duration") and m.get("load_duration") is not None:
            inf.append((m["total_duration"] - m["load_duration"]) / 1e6)
    q = lambda xs, p: (sorted(xs)[min(len(xs) - 1, int(math.ceil(p * len(xs))) - 1)] if xs else None)  # noqa: E731
    return {"n": len(wall), "wall_median_ms": statistics.median(wall) if wall else None, "wall_p95_ms": q(wall, 0.95),
            "inference_only_median_ms": statistics.median(inf) if inf else None, "inference_only_p95_ms": q(inf, 0.95), "n_inference": len(inf)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True, choices=["DEV", "TEST"])
    ap.add_argument("--gold", default="all", choices=["all", "trusted"])
    ap.add_argument("--final-test", action="store_true")
    ap.add_argument("--n-boot", type=int, default=1000)
    a = ap.parse_args()
    if a.split == "TEST" and not (a.final_test and SELECTION.exists()):
        raise SystemExit("TEST bị khóa: cần --final-test và dev_selection.json")
    specs = load_specs()
    gold, types, split = load_gold(review_statuses=TRUSTED if a.gold == "trusted" else None)
    units = sorted(u for u in gold if split[u] == a.split)
    expiry_fields = {dt: [s.name for s in sp if s.is_expiry] for dt, sp in specs.items()}

    rows: Dict[str, Dict[str, Any]] = {}
    for m, s in BASE:
        r = load_preds(m, s)
        r = {u: x for u, x in r.items() if u in units}
        if r:
            rows[name_of(m, s)] = r
    missing = {n: [u for u in units if u not in r] for n, r in rows.items()}
    incomplete = {n: len(v) for n, v in missing.items() if v}
    if incomplete:
        print("CẢNH BÁO cấu hình chưa chạy đủ đơn vị:", incomplete, flush=True)

    # ---- ghép
    for n in rows:
        for r in rows[n].values():
            r["_tag"] = n
    combos: Dict[str, Dict[str, Any]] = {}
    if all(k in rows for k in ("regex@ocr_v2", "llm@ocr_v2")):
        combos["cascade regex→llm @ocr_v2"] = C.cascade(rows["regex@ocr_v2"], rows["llm@ocr_v2"], units=units)
        combos["cascade llm→regex @ocr_v2"] = C.cascade(rows["llm@ocr_v2"], rows["regex@ocr_v2"], units=units)
        ftypes = {dt: {x.name: x.type for x in sp} for dt, sp in specs.items()}
        combos["cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2"] = C.cascade_typed(rows["regex@ocr_v2"], rows["llm@ocr_v2"], ftypes, units)
        if "vlm" in rows:
            combos["cascade regex→llm→vlm @ocr_v2"] = C.cascade(rows["regex@ocr_v2"], rows["llm@ocr_v2"], rows["vlm"], units=units)
    # nguồn cho quy tắc từ chối (production: văn bản OCR cục bộ)
    srcs = {"regex": rows.get("regex@ocr_v2", {}), "llm": rows.get("llm@ocr_v2", {}), "vlm": rows.get("vlm", {}), "filename": rows.get("filename", {})}
    sel: Dict[str, Any] = json.loads(SELECTION.read_text(encoding="utf-8")) if SELECTION.exists() else {}
    abst = C.abstention_table(gold, types, units, srcs, expiry_fields)
    chosen_rule = sel.get("expiry_rule") if a.split == "TEST" else None
    if a.split == "DEV" and sel.get("expiry_rule"):
        chosen_rule = sel["expiry_rule"]            # đã đóng băng: KHÔNG chọn lại theo đáp án silver mới
    elif a.split == "DEV":
        zero = [r for r in abst if r["n_wrong"] == 0 and r["n_emitted"] >= 5]
        zero.sort(key=lambda r: (-r["n_correct"], r["rule"].count(",") + r["rule"].count("=")))
        chosen_rule = zero[0]["rule"] if zero else min(abst, key=lambda r: (r["wrong_rate"] if r["n_emitted"] else 9, -r["n_correct"]))["rule"]
    base_for_rule = combos.get("cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2")
    if base_for_rule is not None and chosen_rule:
        combos[f"cascade + từ chối hạn [{chosen_rule}]"] = C.expiry_rule(chosen_rule, srcs, base_for_rule, expiry_fields)
    # định tuyến "oracle" theo mực của đáp án (KHÔNG triển khai được: dùng đáp án để biết ô nào viết tay/dưới dấu)
    if "vlm" in rows and base_for_rule is not None:
        orc = {}
        for u, r in base_for_rule.items():
            rr = {**r, "fields": {k: dict(v) for k, v in r["fields"].items()}}
            for f, g in gold[u].items():
                if collapse_ink(g.get("ink")) in ("handwritten", "under_stamp") and rows["vlm"].get(u, {}).get("status") == "ok" and f in rr["fields"]:
                    rr["fields"][f] = rows["vlm"][u]["fields"].get(f, rr["fields"][f])
            orc[u] = rr
        combos["ORACLE: VLM chỉ ở ô mà đáp án ghi viết tay/dưới dấu (không triển khai được)"] = orc

    allrows = {**rows, **combos}
    # bản đối chứng cùng tập đơn vị: chấm lại phương pháp @ocr_v2 CHỈ trên các đơn vị có text layer (để so Δ nguồn văn bản)
    subset_of: Dict[str, List[str]] = {}
    for m in ("regex", "gliner", "llm"):
        tl, o2 = rows.get(f"{m}@text_layer"), rows.get(f"{m}@ocr_v2")
        if tl and o2:
            ids = [u for u in units if u in tl and tl[u]["status"] == "ok"]
            allrows[f"{m}@ocr_v2 (cùng tập đơn vị với text_layer)"] = {u: o2[u] for u in ids if u in o2}

    # ---- chấm
    out: Dict[str, Any] = {"split": a.split, "gold": a.gold, "n_units": len(units), "units_by_type": {t: sum(1 for u in units if types[u] == t) for t in sorted(set(types[u] for u in units))},
                           "incomplete": incomplete, "chosen_expiry_rule": chosen_rule, "configs": {}}
    from lib import to_pred
    for n, r in allrows.items():
        pr = to_pred(r)
        us = [u for u in units if u in r]
        g = gold
        if n.endswith("@ocr_llm_haiku"):
            g = restrict_gold_pages(gold, 2)
        if n.endswith("@text_layer"):
            us = [u for u in us if r[u]["status"] == "ok"]        # chỉ đơn vị có text layer
        if not us:
            continue
        cfg: Dict[str, Any] = {"units": len(us)}
        for mode in ("normalized", "lenient"):
            res = score_cfg(g, pr, types, us, mode, n_boot=a.n_boot, specs=specs)
            cfg[mode] = summarize(res)
            if mode == "normalized":
                cfg["by_doc_type"] = {}
                for t in sorted(set(types[u] for u in us)):
                    ut = [u for u in us if types[u] == t]
                    cfg["by_doc_type"][t] = {m: summarize(score_cfg(g, pr, types, ut, m, n_boot=min(a.n_boot, 500), specs=specs)) for m in ("normalized", "lenient")}
        cfg["by_ink"] = {m: by_ink(g, pr, types, us, m, specs) for m in ("normalized", "lenient")}
        for ik in cfg["by_ink"].values():
            pass
        # gộp mực (handwritten|printed -> handwritten...) cho bảng gọn
        for m in ("normalized", "lenient"):
            agg: Dict[str, Dict[str, int]] = {}
            for ink, d in cfg["by_ink"][m].items():
                k = collapse_ink(ink)
                tgt = agg.setdefault(k, {})
                for kk, vv in d.items():
                    tgt[kk] = tgt.get(kk, 0) + vv
            cfg["by_ink"][m] = agg
        cfg["latency"] = latency(r, us)
        out["configs"][n] = cfg
        print(f"  chấm xong {n} ({len(us)} đơn vị)", flush=True)
    out["abstention"] = abst
    out["review_queue"] = C.review_queue_stats(gold, types, units, srcs, expiry_fields, chosen_rule) if chosen_rule else {}
    out["expiry_universe"] = {"n_units": len(units)}
    (HERE / f"results_{a.split}_{a.gold}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float) + "\n", encoding="utf-8")
    print("đã ghi", HERE / f"results_{a.split}_{a.gold}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
