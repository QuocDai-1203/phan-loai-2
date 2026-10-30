"""build_adjudication.py - Dựng hàng đợi phân xử cho người đọc thứ ba (mô hình mạnh hơn) từ các đáp án silver đã gộp (Nhóm 4, T2).

Chạy (từ gốc repo, sau khi `silver_raw/` đã có hai người chú thích):
    .venv\\Scripts\\python.exe -X utf8 teams\\team4_extraction\\gold\\build_adjudication.py

Một MỤC = một (đơn vị, trường) thuộc ít nhất một nhóm:
  * `needs_human`  trong tập hai-người-chú-thích sau khi đã so sánh MỀM (bất đồng thật, hoặc một bên null);
  * `ink_risk`     trong tập hai-người-chú-thích (chữ viết tay/dưới con dấu theo ít nhất một người), kể cả khi hai bên đồng thuận;
  * `filename_mismatch`  trường hạn mà ngày silver khác ngày trong tên tệp (mọi đơn vị, kể cả chỉ một người chú thích).
Mỗi mục chỉ xuất hiện MỘT lần dù thuộc nhiều nhóm.

Sinh (trong gold/adjudication/):
  queue.json              mọi mục: item_id, unit_id, doc_type, field, mô tả/gợi ý của schema, đường dẫn TUYỆT ĐỐI các ảnh của đơn vị,
                          `candidate_x` / `candidate_y` (thứ tự x/y NGẪU NHIÊN có hạt giống; không lộ ai đọc gì)
  key.json                item_id -> người chú thích nào là x/y, lý do vào hàng đợi. NGƯỜI PHÂN XỬ ĐƯỢC DẶN KHÔNG MỞ tệp này
  queue_batch_NN.json     lô cho người phân xử, <= 24 ảnh mỗi lô (các mục cùng đơn vị nằm chung một lô; ảnh đếm một lần cho mỗi đơn vị)
  ADJUDICATION_PROMPT.md  (viết tay, không do script này sinh)
Mục "lệch tên tệp" chỉ có MỘT bản đọc (`candidate_x`, `candidate_y = null`) và KHÔNG có thông tin về tên tệp.
Trường PII `withhold_value`: bản đọc chỉ gồm status/page/ink (không có giá trị).
KHÔNG đọc bằng mắt nội dung TEST: script chỉ chạy bằng máy, báo cáo chỉ in số lượng.
"""

from __future__ import annotations

import csv
import json
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
TEAM = HERE.parent
REPO = TEAM.parents[1]
sys.path.insert(0, str(TEAM))

from gold import merge_silver as MS  # noqa: E402
from gold.build_units import interleave_batches  # noqa: E402
from methods.filename_date import filename_date  # noqa: E402

ADJ = HERE / "adjudication"
SEED = 20261012
MAX_IMAGES = 24


def reading(rec: Dict[str, Any], f: Dict[str, Any]) -> Dict[str, Any]:
    """Bản đọc của một người chú thích cho một trường, dạng đưa cho người phân xử (không có tên người)."""
    withheld = f.get("silver_policy") == "withhold_value"
    return {"status": rec["status"], "value": None if withheld else rec.get("value"), "page": rec.get("page"),
            "ink": rec.get("ink"), "evidence": None if withheld else rec.get("evidence"), "note": rec.get("note")}


def filename_mismatch_fields(merged: List[Dict[str, Any]], units: Dict[str, Dict[str, str]], schemas: Dict[str, Any], names: Dict[str, str]) -> Dict[str, str]:
    """{unit_id: tên trường hạn} cho các đơn vị mà ngày hạn silver khác ngày trong tên tệp (cùng quy tắc với mục 4 của báo cáo)."""
    out: Dict[str, str] = {}
    for m in merged:
        u = units[m["unit_id"]]
        exp = [x["name"] for x in schemas[m["doc_type"]]["x-fields"] if x.get("is_expiry") and x["name"] in m["fields"]]
        if u.get("composite") == "1" or not exp:
            continue
        fd = filename_date(names.get(u["doc_id"], ""))
        r = m["fields"][exp[0]]
        if fd and r["status"] == "ok" and r["normalized"] and r["normalized"] != fd:
            out[m["unit_id"]] = exp[0]
    return out


def build(raw_dir: Path = HERE / "silver_raw", units_csv: Path = HERE / "units.csv", schema_dir: Path = TEAM / "schema",
          manifest_csv: Path = REPO / "data" / "manifest.csv", out_dir: Path = ADJ, primary: str = "haiku", seed: int = SEED,
          pages_dir: Path = HERE / "pages", prompt_path: Optional[Path] = None) -> Dict[str, Any]:
    units = MS.load_units(units_csv)
    schemas = MS.load_schemas(schema_dir)
    valid, _stat, _prob, _fi, _w = MS.collect(raw_dir, units, schemas)
    merged = [MS.merge_unit(units[u], schemas[units[u]["doc_type"]], valid[u], primary) for u in sorted(valid)]
    names: Dict[str, str] = {}
    if manifest_csv.exists():
        with open(manifest_csv, encoding="utf-8-sig", newline="") as f:
            names = {r["doc_id"]: r["file_name"] for r in csv.DictReader(f)}
    fn_mis = filename_mismatch_fields(merged, units, schemas, names)

    items: List[Dict[str, Any]] = []
    key: Dict[str, Any] = {}
    for m in merged:
        uid, dt = m["unit_id"], m["doc_type"]
        sch = {f["name"]: f for f in schemas[dt]["x-fields"]}
        imgs = sorted(str(p.resolve()) for p in (pages_dir / uid).glob("p*.png"))
        for name, r in m["fields"].items():
            f = sch[name]
            reasons: List[str] = []
            annotators = list(r["by_annotator"])
            two = len(annotators) >= 2
            if two and r["review_status"] == "needs_human":
                reasons.append("needs_human")
            if two and "ink_risk" in r["review_reasons"]:
                reasons.append("ink_risk")
            if fn_mis.get(uid) == name:
                reasons.append("filename_mismatch")
            if not reasons:
                continue
            item_id = f"{uid}__{name}"
            rng = random.Random(f"{seed}:{item_id}")
            single = not (two and ({"needs_human", "ink_risk"} & set(reasons)))
            recs = valid[uid]
            if single:
                # một bản đọc: bản của người chính (hoặc bản đồng thuận); key ghi mọi người có bản đọc giống nó
                a0 = annotators[0]
                cx, cy = reading(recs[a0]["fields"][name], f), None
                kx, ky = ([a for a in annotators if MS.agreement_level([recs[a0]["fields"][name], recs[a]["fields"][name]], f)] or [a0]), []
                if a0 not in kx:
                    kx = [a0] + kx
            else:
                a, b = annotators[0], annotators[1]
                ca, cb = reading(recs[a]["fields"][name], f), reading(recs[b]["fields"][name], f)
                if rng.random() < 0.5:
                    cx, cy, kx, ky = ca, cb, [a], [b]
                else:
                    cx, cy, kx, ky = cb, ca, [b], [a]
            items.append({
                "item_id": item_id, "unit_id": uid, "doc_type": dt, "field": name, "field_type": f["type"],
                "field_desc": f["desc"], "field_hint": f.get("annotator_hint", ""), "is_expiry": bool(f.get("is_expiry")),
                "silver_policy": f.get("silver_policy", "transcribe"), "shown_pages": [int(x) for x in m["shown_pages"].split(";") if x],
                "images": imgs, "candidate_x": cx, "candidate_y": cy, "single_candidate": single,
            })
            key[item_id] = {"unit_id": uid, "field": name, "type": f["type"], "withheld": f.get("silver_policy") == "withhold_value",
                            "candidate_x": kx, "candidate_y": ky, "reasons": reasons, "single_candidate": single}

    # lô: gom mục theo đơn vị, rồi chia theo số ảnh
    by_unit: Dict[str, List[Dict[str, Any]]] = {}
    for it in items:
        by_unit.setdefault(it["unit_id"], []).append(it)
    groups = [{"unit_id": u, "doc_type": its[0]["doc_type"], "n_images": len(its[0]["images"]), "items": its} for u, its in sorted(by_unit.items())]
    batches = interleave_batches(groups, random.Random(seed), MAX_IMAGES) if groups else []

    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("queue_batch_*.json"):
        old.unlink()
    qb = []
    for i, b in enumerate(batches, 1):
        bj = {
            "batch_id": f"queue_batch_{i:02d}",
            "instructions": str(prompt_path or (out_dir / "ADJUDICATION_PROMPT.md")),
            "output_dir": str(out_dir / "out"),
            "do_not_open": str(out_dir / "key.json"),
            "n_units": len(b), "n_items": sum(len(g["items"]) for g in b), "n_images": sum(g["n_images"] for g in b),
            "units": [{"unit_id": g["unit_id"], "doc_type": g["doc_type"],
                       "schema_path": str(TEAM / "schema" / f"{g['doc_type']}.json"), "images": g["items"][0]["images"],
                       "items": [{k: v for k, v in it.items() if k not in ("images", "unit_id", "doc_type")} for it in g["items"]]} for g in b],
        }
        (out_dir / f"queue_batch_{i:02d}.json").write_text(json.dumps(bj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        qb.append(bj)
    n_img = sum(b["n_images"] for b in qb)
    queue = {"description": "Hàng đợi phân xử (người đọc thứ ba). Thứ tự x/y ngẫu nhiên, hạt giống " + str(seed) + ".", "seed": seed,
             "n_items": len(items), "n_units": len(groups), "n_batches": len(qb), "n_images_total": n_img, "items": items}
    (out_dir / "queue.json").write_text(json.dumps(queue, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (out_dir / "key.json").write_text(json.dumps(key, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    rc = Counter(r for k in key.values() for r in k["reasons"])
    return {"n_items": len(items), "n_units": len(groups), "n_batches": len(qb), "n_images_total": n_img, "by_reason": dict(rc),
            "by_split": dict(Counter(units[it["unit_id"]]["split"] for it in items)), "single_candidate": sum(it["single_candidate"] for it in items)}


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", choices=("v1", "v2"), default="v1", help="v1: gold/ (mặc định); v2: gold/v2/ (giai đoạn 3)")
    a = ap.parse_args(argv)
    if a.version == "v2":
        v2 = HERE / "v2"
        res = build(raw_dir=v2 / "silver_raw", units_csv=v2 / "units_v2.csv", out_dir=v2 / "adjudication", pages_dir=v2 / "pages_v2",
                    prompt_path=ADJ / "ADJUDICATION_PROMPT.md")      # dùng lại lời nhắc phân xử của v1 (không phụ thuộc loại)
    else:
        res = build()
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
