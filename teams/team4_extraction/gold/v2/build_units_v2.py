"""build_units_v2.py - Bộ công cụ silver v2 (giai đoạn 3): 17 loại còn lại có trường hạn (Nhóm 4).

Chạy (từ gốc repo, ~2-4 phút):
    .venv\\Scripts\\python.exe -X utf8 teams\\team4_extraction\\gold\\v2\\build_units_v2.py [--no-render] [--drop-blank]

Tách biệt với v1 (không ghi vào gold/units.csv, gold/pages, gold/batches...). Sinh trong gold/v2/:
    units_v2.csv                     mọi đơn vị (doc_id, segment_idx) của các loại giai đoạn 3 (cùng cột với units.csv v1)
    pages_v2/<unit_id>/pNN.png       ảnh trang (cùng quy tắc chọn trang/render với v1: <= 6 trang, 200 dpi, cắt đôi trang dọc, <= 1600 px)
    batches_v2/batch_NN.json         lô cho người chú thích thứ nhất (mọi đơn vị), <= 24 ảnh/lô, trộn loại
    batches_v2_second.json           lô cho người chú thích thứ hai: CŨNG mọi đơn vị (cỡ mẫu nhỏ nên cả hai đọc hết), thứ tự lô khác
    batch_manifest_v2.json           tóm tắt số lượng (không chứa đường dẫn PDF)

Hàm chọn trang, render, chia lô lấy bằng import từ gold/build_units.py (không chép). Split theo data/splits/ như v1:
tệp ghép (composite) và EXCLUDED* -> EXCLUDED. KHÔNG đọc nội dung TEST bằng mắt (script chỉ dùng OCR TEST để tìm từ khóa chọn trang).
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

HERE = Path(__file__).resolve().parent          # gold/v2
GOLD = HERE.parent
TEAM = GOLD.parent
REPO = TEAM.parents[1]
for _p in (str(TEAM), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from gold.build_units import (  # noqa: E402
    DATA, MAX_IMAGES_PER_BATCH, SAMPLES, choose_pages, interleave_batches, load_ocr_pages, parse_segments, read_csv, render_unit,
)
from schema.build_schema import PHASE3_TYPES  # noqa: E402

TARGET_TYPES_V2: List[str] = list(PHASE3_TYPES)
SEED_FIRST = 20261015
SEED_SECOND = 20261016
PROMPT = HERE / "SILVER_PROMPT_v2.md"
CSV_COLS = ["unit_id", "doc_id", "segment_idx", "doc_type", "split", "pages", "n_pages", "shown_pages", "n_shown_pages", "n_images",
            "template_group", "is_scanned", "composite", "relative_path"]


def collect_candidates(labels: Dict[str, Dict[str, str]], manifest: Dict[str, Dict[str, str]], types: List[str]) -> List[dict]:
    """Đơn vị ứng viên từ labels_v2 (chỉ tài liệu duy nhất). Tệp ghép: mỗi segment thuộc `types` là một đơn vị; tệp thường: một đơn vị."""
    cand: List[dict] = []
    for doc_id, r in labels.items():
        if r["is_duplicate_of"]:
            continue
        n_pdf = int(manifest[doc_id]["page_count"])
        if r["segments"].strip():
            for idx, (pages, typ) in enumerate(parse_segments(r["segments"])):
                if typ in types:
                    cand.append(dict(doc_id=doc_id, seg_idx=idx, doc_type=typ, pages=pages, composite=1))
        elif r["doc_type"] in types:
            cand.append(dict(doc_id=doc_id, seg_idx=0, doc_type=r["doc_type"], pages=list(range(1, n_pdf + 1)), composite=0))
    return cand


def unit_split(split_raw: str, composite: int) -> str:
    return "EXCLUDED" if split_raw.startswith("EXCLUDED") or composite else split_raw


def batch_json_v2(batch_id: str, units: List[dict], note: str) -> dict:
    """Như batch_json của v1 nhưng trỏ tới prompt/ảnh/đầu ra của v2. Mọi đường dẫn tuyệt đối."""
    return {
        "batch_id": batch_id,
        "instructions": str(PROMPT),
        "output_dir_template": str(HERE / "silver_raw" / "<annotator>" / "<unit_id>.json"),
        "note": note,
        "n_units": len(units),
        "n_images": sum(u["n_images"] for u in units),
        "units": [
            {
                "unit_id": u["unit_id"],
                "doc_type": u["doc_type"],
                "schema_path": str(TEAM / "schema" / f"{u['doc_type']}.json"),
                "shown_pages": u["shown_pages"],
                "n_pages": u["n_pages"],
                "images": [{"file": f, "path": str(HERE / "pages_v2" / u["unit_id"] / f)} for f in u["images"]],
            }
            for u in units
        ],
    }


def write_units_csv(units: List[dict], path: Path) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(CSV_COLS)
        for u in units:
            w.writerow([u["unit_id"], u["doc_id"], u["seg_idx"], u["doc_type"], u["split"], ";".join(map(str, u["pages"])), u["n_pages"],
                        ";".join(map(str, u["shown_pages"])), len(u["shown_pages"]), u["n_images"], u["template_group"], u["is_scanned"],
                        u["composite"], u["relative_path"]])


def summarize(units: List[dict]) -> Dict[str, Dict[str, int]]:
    s: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for u in units:
        s[u["doc_type"]][u["split"]] += 1
        s[u["doc_type"]]["units"] += 1
        s[u["doc_type"]]["images"] += u["n_images"]
        s[u["doc_type"]]["shown_pages"] += len(u["shown_pages"])
    return {k: dict(v) for k, v in s.items()}


def write_batches(units: List[dict], out_first: Path, out_second: Path, limit: int = MAX_IMAGES_PER_BATCH) -> dict:
    """Lô cho người thứ nhất (thư mục `out_first`/batch_NN.json) và người thứ hai (một tệp `out_second`, khóa `batches`). Cả hai bao mọi đơn vị."""
    out_first.mkdir(parents=True, exist_ok=True)
    for old in out_first.glob("batch_*.json"):
        old.unlink()
    b1 = interleave_batches([dict(u) for u in units], random.Random(SEED_FIRST), limit)
    for i, b in enumerate(b1, 1):
        bj = batch_json_v2(f"v2_batch_{i:02d}", b, "Chú thích thứ nhất v2: mọi đơn vị.")
        (out_first / f"batch_{i:02d}.json").write_text(json.dumps(bj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    b2 = interleave_batches([dict(u) for u in units], random.Random(SEED_SECOND), limit)
    second = {"description": "Lô cho người chú thích thứ hai v2: mọi đơn vị (cỡ mẫu nhỏ), thứ tự/trộn lô khác người thứ nhất.",
              "seed": SEED_SECOND, "n_units": len(units), "n_images": sum(u["n_images"] for u in units),
              "batches": [batch_json_v2(f"v2_second_{i:02d}", b, "Chú thích thứ hai v2: mọi đơn vị.") for i, b in enumerate(b2, 1)]}
    out_second.write_text(json.dumps(second, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return {"n_batches": len(b1), "n_second_batches": len(b2)}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-render", action="store_true", help="chỉ dựng units_v2.csv và lô (giả định ảnh đã có)")
    ap.add_argument("--drop-blank", action="store_true", help="khi render: bỏ nửa trang trắng nếu nửa kia có mực (mặc định tắt, như v1)")
    args = ap.parse_args(argv)

    labels = {r["doc_id"]: r for r in read_csv(DATA / "labels_v2.csv")}
    manifest = {r["doc_id"]: r for r in read_csv(DATA / "manifest.csv")}
    splits = {r["doc_id"]: r["split"] for r in read_csv(DATA / "splits" / "splits.csv")}

    cand = collect_candidates(labels, manifest, TARGET_TYPES_V2)
    ocr = load_ocr_pages(DATA / "ocr_v2.jsonl", {c["doc_id"] for c in cand})
    index = {unicodedata.normalize("NFC", p.relative_to(SAMPLES).as_posix()): p for p in SAMPLES.rglob("*.pdf")}

    units: List[dict] = []
    for c in sorted(cand, key=lambda x: (x["doc_type"], x["doc_id"], x["seg_idx"])):
        m = manifest[c["doc_id"]]
        shown = choose_pages(c["pages"], ocr.get(c["doc_id"], {}))
        units.append(dict(c, unit_id=f"{c['doc_id']}_{c['seg_idx']}", split=unit_split(splits.get(c["doc_id"], ""), c["composite"]),
                          n_pages=len(c["pages"]), shown_pages=shown, template_group=m.get("template_group", ""),
                          relative_path=m["relative_path"], is_scanned=m.get("is_scanned", ""), images=[]))

    for i, u in enumerate(units):
        outdir = HERE / "pages_v2" / u["unit_id"]
        if args.no_render:
            u["images"] = sorted(p.name for p in outdir.glob("p*.png"))
        else:
            pdf = index[unicodedata.normalize("NFC", u["relative_path"])]
            u["images"] = render_unit(pdf, u["shown_pages"], outdir, args.drop_blank)
        u["n_images"] = len(u["images"])
        if (i + 1) % 20 == 0:
            print(f"  render {i + 1}/{len(units)}", flush=True)

    write_units_csv(units, HERE / "units_v2.csv")
    nb = write_batches(units, HERE / "batches_v2", HERE / "batches_v2_second.json")
    meta = {"n_units": len(units), "n_images": sum(u["n_images"] for u in units), **nb, "by_type": summarize(units)}
    (HERE / "batch_manifest_v2.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
