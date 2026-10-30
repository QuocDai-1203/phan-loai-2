"""build_units.py - Dựng tập đơn vị trích xuất, render ảnh trang và chia lô cho người chú thích silver (Nhóm 4, T2).

Chạy (từ gốc repo, ~1-3 phút):
    .venv\\Scripts\\python.exe -X utf8 teams\\team4_extraction\\gold\\build_units.py [--no-render]

Sinh (trong gold/):
    units.csv                       mọi đơn vị (doc_id, segment_idx) của 4 loại mục tiêu, kèm split, trang, trang được cho xem
    pages/<unit_id>/pNN.png         ảnh trang (hoặc pNN_a.png + pNN_b.png: nửa trên/nửa dưới của trang dọc), NN = số trang trong PDF gốc
    batches/batch_NN.json           lô cho người chú thích thứ nhất (mọi đơn vị), <= 24 ảnh/lô, trộn loại
    batches_second_annotator.json   mẫu phân tầng 40 đơn vị (10/loại, DEV+TEST) cho người chú thích thứ hai
    batch_manifest.json             tóm tắt số lượng (không chứa đường dẫn PDF)

Quy tắc:
  * Đơn vị = (doc_id, segment_idx). Tệp thường có 1 đơn vị (segment 0, mọi trang). Tệp ghép khác loại (`composite_mixed`) cho
    mỗi segment thuộc loại mục tiêu một đơn vị; các tệp này có split EXCLUDED (không vào DEV/TEST của phân loại).
  * Chỉ tài liệu duy nhất (`is_duplicate_of` rỗng).
  * Chọn trang cho xem: <= 4 trang -> tất cả; ngược lại 2 trang đầu + trang có từ khóa hiệu lực/hạn (không phân biệt dấu)
    + trang cuối, tối đa 6. Trang cho xem được ghi vào units.csv để một câu trả lời `not_present` có thể hiểu là
    "không có trên các trang đã cho xem".
  * Cách render theo `teams/team1_ocr/experiments/03_llm_silver/render_pages.py`: 200 dpi RGB; trang dọc cắt đôi tại hàng ít mực
    nhất quanh giữa trang (nửa nào cũng đọc được chữ nhỏ). Mỗi ảnh được thu nhỏ nếu cạnh dài > 1600 px.
KHÔNG đọc nội dung TEST bằng mắt; script chỉ dùng văn bản OCR của TEST để tìm từ khóa chọn trang.
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
from typing import Dict, List, Tuple

HERE = Path(__file__).resolve().parent
TEAM = HERE.parent
REPO = TEAM.parents[1]
sys.path.insert(0, str(TEAM))

from eval.normalize import fold_text  # noqa: E402

DATA = REPO / "data"
SAMPLES = REPO / "docs" / "_chot_samples_phanloaitailieu"
TARGET_TYPES = ["GCN_DDK_BAN_LE_XD", "CC_TAP_HUAN_VC_HNH", "HD_MUA_BAN", "PHIEU_XUAT_KHO"]
DPI = 200
MAX_SIDE = 1600
MAX_IMAGES_PER_BATCH = 24
MAX_SHOWN_PAGES = 6
KEYWORDS = ("hieu luc", "thoi han", "co gia tri den", "het han", "den het ngay", "hieu luc den", "het hieu luc")
SECOND_SEED = 20261012
SECOND_PER_TYPE = 10


def read_csv(path: Path) -> List[Dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def parse_segments(seg: str) -> List[Tuple[List[int], str]]:
    """'1-2:PHIEU_XUAT_KHO;3:CHUNG_THU_CHAT_LUONG' -> [([1,2], 'PHIEU_XUAT_KHO'), ([3], '...')] (theo thứ tự, segment_idx = vị trí)."""
    out = []
    for part in [p for p in seg.split(";") if p.strip()]:
        pages_s, _, typ = part.partition(":")
        pages: List[int] = []
        for tok in pages_s.split(","):
            if "-" in tok:
                a, b = tok.split("-")
                pages.extend(range(int(a), int(b) + 1))
            elif tok.strip():
                pages.append(int(tok))
        out.append((pages, typ.strip()))
    return out


def load_ocr_pages(path: Path, wanted: set) -> Dict[str, Dict[int, str]]:
    res: Dict[str, Dict[int, str]] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r["doc_id"] in wanted:
                res[r["doc_id"]] = {p["page"]: p.get("text") or "" for p in r["pages"]}
    return res


def choose_pages(pages: List[int], texts: Dict[int, str]) -> List[int]:
    if len(pages) <= 4:
        return list(pages)
    first2, last = pages[:2], pages[-1]
    keep = list(first2)
    if last not in keep:
        keep.append(last)
    hits = []
    for p in pages[2:-1]:
        t = fold_text(texts.get(p, ""))
        n = sum(t.count(k) for k in KEYWORDS)
        if n:
            hits.append((-n, p))
    for _, p in sorted(hits):
        if len(keep) >= MAX_SHOWN_PAGES:
            break
        keep.append(p)
    return sorted(keep)


BLANK_INK = 0.0005   # tỉ lệ điểm ảnh "có mực" (xám < 200) dưới ngưỡng này coi là giấy trắng


def ink_fraction(im) -> float:
    """Tỉ lệ điểm ảnh có mực (độ xám < 200) trong ảnh; ~0 nghĩa là nửa trang giấy trắng (thẻ nhỏ chỉ chiếm nửa trên tờ giấy)."""
    import numpy as np
    g = np.asarray(im.convert("L"))
    return float((g < 200).mean())


def render_unit(pdf: Path, shown: List[int], outdir: Path, drop_blank: bool = False) -> List[str]:
    """Render các trang `shown` (1-indexed) -> danh sách tên tệp ảnh. Cắt đôi trang dọc như render_pages.py.

    `drop_blank=True` (tùy chọn, mặc định TẮT; vòng 1 đã render KHÔNG dùng): bỏ nửa trang trắng (mực ~0%) khi nửa kia của trang có mực,
    vì người chú thích (Haiku) từng ghi lỗi dừng sai trên ảnh trắng. Trang trắng hoàn toàn vẫn giữ một ảnh để số trang khớp `shown_pages`."""
    import fitz
    import numpy as np
    from PIL import Image

    outdir.mkdir(parents=True, exist_ok=True)
    names: List[str] = []
    doc = fitz.open(pdf)
    try:
        for p in shown:
            page = doc[p - 1]
            pix = page.get_pixmap(dpi=DPI, colorspace=fitz.csRGB)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            if img.height / img.width > 1.2:   # trang dọc: cắt đôi tại hàng ít mực nhất quanh giữa trang
                g = np.asarray(img.convert("L"), dtype=np.float32)
                h = g.shape[0]
                lo, hi = int(h * 0.44), int(h * 0.56)
                cut = lo + int((255 - g[lo:hi]).sum(axis=1).argmin())
                parts = [("a", img.crop((0, 0, img.width, cut))), ("b", img.crop((0, cut, img.width, h)))]
            else:
                parts = [("", img)]
            if drop_blank and len(parts) == 2:
                inked = [ink_fraction(im) >= BLANK_INK for _suf, im in parts]
                if any(inked):
                    parts = [pt for pt, k in zip(parts, inked) if k]
            for suffix, im in parts:
                s = max(im.size)
                if s > MAX_SIDE:
                    k = MAX_SIDE / s
                    im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)
                name = f"p{p:02d}{('_' + suffix) if suffix else ''}.png"
                im.save(outdir / name, optimize=True)
                names.append(name)
    finally:
        doc.close()
    return names


def interleave_batches(units: List[dict], rng: random.Random, limit: int = MAX_IMAGES_PER_BATCH) -> List[List[dict]]:
    """Chia thành lô <= `limit` ảnh, mỗi lô trộn loại.

    Xếp hàng công bằng: trong mỗi loại xáo trộn rồi gán hạng (i + u)/n (u ngẫu nhiên trong [0,1)) và sắp toàn bộ theo hạng, nên mọi
    đoạn của dãy chứa các loại theo đúng tỉ lệ (không để loại nhiều ảnh dồn hết về các lô cuối). Sau đó đóng gói tuần tự; đơn vị
    kế tiếp không vừa thì thử vài đơn vị phía sau trước khi đóng lô."""
    by_type: Dict[str, List[dict]] = defaultdict(list)
    for u in units:
        by_type[u["doc_type"]].append(u)
    ranked: List[Tuple[float, dict]] = []
    for t in sorted(by_type):
        v = by_type[t]
        rng.shuffle(v)
        ranked += [((i + rng.random()) / len(v), u) for i, u in enumerate(v)]
    queue = [u for _r, u in sorted(ranked, key=lambda x: x[0])]
    batches: List[List[dict]] = []
    cur: List[dict] = []
    n = 0
    while queue:
        pick = next((k for k, u in enumerate(queue[:8]) if n + u["n_images"] <= limit), None)
        if pick is None:
            if not cur:
                raise ValueError("một đơn vị có nhiều ảnh hơn giới hạn lô")
            batches.append(cur)
            cur, n = [], 0
            continue
        u = queue.pop(pick)
        cur.append(u)
        n += u["n_images"]
    if cur:
        batches.append(cur)
    return batches


def batch_json(batch_id: str, units: List[dict], annotator_note: str) -> dict:
    return {
        "batch_id": batch_id,
        "instructions": str(HERE / "SILVER_PROMPT.md"),
        "output_dir_template": str(HERE / "silver_raw" / "<annotator>" / "<unit_id>.json"),
        "note": annotator_note,
        "n_units": len(units),
        "n_images": sum(u["n_images"] for u in units),
        "units": [
            {
                "unit_id": u["unit_id"],
                "doc_type": u["doc_type"],
                "schema_path": str(TEAM / "schema" / f"{u['doc_type']}.json"),
                "shown_pages": u["shown_pages"],
                "n_pages": u["n_pages"],
                "images": [{"file": f, "path": str(HERE / "pages" / u["unit_id"] / f)} for f in u["images"]],
            }
            for u in units
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-render", action="store_true", help="chỉ dựng units.csv và lô (giả định ảnh đã có)")
    ap.add_argument("--drop-blank", action="store_true", help="khi render: bỏ nửa trang trắng (mực < 0,05%%) nếu nửa kia có mực")
    args = ap.parse_args()

    labels = {r["doc_id"]: r for r in read_csv(DATA / "labels_v2.csv")}
    manifest = {r["doc_id"]: r for r in read_csv(DATA / "manifest.csv")}
    splits = {r["doc_id"]: r["split"] for r in read_csv(DATA / "splits" / "splits.csv")}

    cand: List[dict] = []
    for doc_id, r in labels.items():
        if r["is_duplicate_of"]:
            continue
        m = manifest[doc_id]
        n_pdf = int(m["page_count"])
        if r["segments"].strip():
            for idx, (pages, typ) in enumerate(parse_segments(r["segments"])):
                if typ in TARGET_TYPES:
                    cand.append(dict(doc_id=doc_id, seg_idx=idx, doc_type=typ, pages=pages, composite=1))
        elif r["doc_type"] in TARGET_TYPES:
            cand.append(dict(doc_id=doc_id, seg_idx=0, doc_type=r["doc_type"], pages=list(range(1, n_pdf + 1)), composite=0))

    wanted = {c["doc_id"] for c in cand}
    ocr = load_ocr_pages(DATA / "ocr_v2.jsonl", wanted)
    index = {unicodedata.normalize("NFC", p.relative_to(SAMPLES).as_posix()): p for p in SAMPLES.rglob("*.pdf")}

    units: List[dict] = []
    for c in sorted(cand, key=lambda x: (x["doc_type"], x["doc_id"], x["seg_idx"])):
        m = manifest[c["doc_id"]]
        uid = f"{c['doc_id']}_{c['seg_idx']}"
        sp = splits.get(c["doc_id"], "")
        split = "EXCLUDED" if sp.startswith("EXCLUDED") or c["composite"] else sp
        shown = choose_pages(c["pages"], ocr.get(c["doc_id"], {}))
        units.append(dict(c, unit_id=uid, split=split, n_pages=len(c["pages"]), shown_pages=shown,
                          template_group=m.get("template_group", ""), relative_path=m["relative_path"],
                          is_scanned=m.get("is_scanned", ""), images=[]))

    for i, u in enumerate(units):
        outdir = HERE / "pages" / u["unit_id"]
        if args.no_render:
            u["images"] = sorted(p.name for p in outdir.glob("p*.png"))
        else:
            pdf = index[unicodedata.normalize("NFC", u["relative_path"])]
            u["images"] = render_unit(pdf, u["shown_pages"], outdir, args.drop_blank)
        u["n_images"] = len(u["images"])
        if (i + 1) % 20 == 0:
            print(f"  render {i + 1}/{len(units)}", flush=True)

    cols = ["unit_id", "doc_id", "segment_idx", "doc_type", "split", "pages", "n_pages", "shown_pages", "n_shown_pages", "n_images",
            "template_group", "is_scanned", "composite", "relative_path"]
    with open(HERE / "units.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for u in units:
            pg = u["pages"]
            w.writerow([u["unit_id"], u["doc_id"], u["seg_idx"], u["doc_type"], u["split"],
                        ";".join(map(str, pg)), u["n_pages"], ";".join(map(str, u["shown_pages"])), len(u["shown_pages"]),
                        u["n_images"], u["template_group"], u["is_scanned"], u["composite"], u["relative_path"]])

    # --- lô cho người chú thích thứ nhất
    rng = random.Random(SECOND_SEED)
    (HERE / "batches").mkdir(exist_ok=True)
    for old in (HERE / "batches").glob("batch_*.json"):
        old.unlink()
    batches = interleave_batches(units, rng)
    for i, b in enumerate(batches, 1):
        bj = batch_json(f"batch_{i:02d}", b, "Chú thích thứ nhất: mọi đơn vị.")
        (HERE / "batches" / f"batch_{i:02d}.json").write_text(json.dumps(bj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    # --- mẫu phân tầng cho người chú thích thứ hai: 10/loại, phủ cả DEV và TEST (không lấy EXCLUDED)
    sample: List[dict] = []
    for t in TARGET_TYPES:
        pool = [u for u in units if u["doc_type"] == t and u["split"] in ("DEV", "TEST")]
        by_split = {s: [u for u in pool if u["split"] == s] for s in ("DEV", "TEST")}
        for v in by_split.values():
            rng.shuffle(v)
        n_test = min(len(by_split["TEST"]), max(2, round(SECOND_PER_TYPE * len(by_split["TEST"]) / max(1, len(pool)))))
        n_dev = min(len(by_split["DEV"]), SECOND_PER_TYPE - n_test)
        n_test = min(len(by_split["TEST"]), SECOND_PER_TYPE - n_dev)
        sample += by_split["TEST"][:n_test] + by_split["DEV"][:n_dev]
    sb = interleave_batches(sample, rng)
    second = {"description": "Mẫu phân tầng cho người chú thích thứ hai (khác họ/khác mô hình): 10 đơn vị mỗi loại, phủ DEV và TEST.",
              "seed": SECOND_SEED, "n_units": len(sample), "n_images": sum(u["n_images"] for u in sample),
              "batches": [batch_json(f"second_{i:02d}", b, "Chú thích thứ hai: mẫu 40 đơn vị.") for i, b in enumerate(sb, 1)]}
    (HERE / "batches_second_annotator.json").write_text(json.dumps(second, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    summary = defaultdict(lambda: defaultdict(int))
    for u in units:
        summary[u["doc_type"]][u["split"]] += 1
        summary[u["doc_type"]]["images"] += u["n_images"]
        summary[u["doc_type"]]["shown_pages"] += len(u["shown_pages"])
    meta = {"n_units": len(units), "n_images": sum(u["n_images"] for u in units), "n_batches": len(batches),
            "n_second_units": len(sample), "n_second_batches": len(sb), "n_second_images": second["n_images"],
            "by_type": {k: dict(v) for k, v in summary.items()}}
    (HERE / "batch_manifest.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
