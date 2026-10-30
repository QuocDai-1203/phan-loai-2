"""make_sheets.py - T2: dung danh sach trang can gan huong va ghep thanh TO TIEP XUC (contact sheet) de nguoi/mo hinh xem.

Ba tap trang (chi lay trang cua tai lieu DUY NHAT; ban trung byte `copied_from_exact_duplicate` thua huong tu ban dai dien):
  rotated : moi trang co co `rotated_*` trong flags cua data/ocr_v2.jsonl (50 trang tinh ca ban trung)
  landscape: moi trang cua cac loai hay nam ngang (muc 7.6 cua 02_taxonomy_design.md: so PCCC, bao hiem chay no, dang kiem ghe, ban ve)
  random  : mau ngau nhien trang KHONG bi xoay (ngoai hai tap tren), seed co dinh
Anh la anh GOC chua xoay (page.get_pixmap theo dung huong luu trong PDF - dung thu engine OCR nhin thay), thu nho de xem huong.
Dau ra: `_sheets/sheet_NN.png` (chua anh giay to -> da .gitignore), `sample_pages.csv` (idx, sheet, o, doc_id, page, tap, huong ocr_v2 da ap, so ky tu).

Chay:  .venv\\Scripts\\python.exe -X utf8 teams\\team1_ocr\\experiments\\05_rotation\\make_sheets.py [--seed 20261015 --n-random 100]
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

LANDSCAPE_TYPES = {"HO_SO_QUAN_LY_PCCC", "GCN_BAO_HIEM", "GCN_ATKT_BVMT_PT", "BAN_VE_KY_THUAT"}
CELL, COLS, ROWS = 496, 3, 3


def applied_rot(pg) -> int:
    for f in pg.get("flags", []) or []:
        if f.startswith("rotated_"):
            return int(f.split("_")[1])
    return 0


def build_sample(seed: int, n_random: int):
    labs = {r["doc_id"]: r["doc_type"] for r in csv.DictReader(open(REPO / "data" / "labels_v2.csv", encoding="utf-8-sig"))}
    recs = [json.loads(l) for l in open(REPO / "data" / "ocr_v2.jsonl", encoding="utf-8")]
    rows = []
    for r in recs:
        dup = any((pg.get("flags") or []) and any(f.startswith("copied_from_exact_duplicate") for f in pg["flags"]) for pg in r["pages"])
        for pg in r["pages"]:
            rows.append(dict(doc_id=r["doc_id"], rel=r["relative_path"], page=pg["page"], n_chars=pg["n_chars"], rot=applied_rot(pg),
                             source=pg["source"], dtype=labs.get(r["doc_id"], ""), dup=dup))
    uniq = [x for x in rows if not x["dup"]]
    sel, seen = [], set()

    def add(x, tap):
        k = (x["doc_id"], x["page"])
        if k not in seen:
            seen.add(k)
            sel.append(dict(x, tap=tap))
    for x in uniq:
        if x["rot"]:
            add(x, "rotated")
    for x in uniq:
        if x["dtype"] in LANDSCAPE_TYPES:
            add(x, "landscape")
    pool = [x for x in uniq if (x["doc_id"], x["page"]) not in seen and not x["rot"]]
    rng = random.Random(seed)
    for x in rng.sample(pool, min(n_random, len(pool))):
        add(x, "random")
    return sel, dict(n_pages_total=len(rows), n_rotated_all=sum(1 for x in rows if x["rot"]), n_uniq=len(uniq), pool=len(pool))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20261015)
    ap.add_argument("--n-random", type=int, default=100)
    a = ap.parse_args()
    import fitz
    from PIL import Image, ImageDraw, ImageFont
    from build_ocr_dataset import CORPUS, list_pdfs
    pdfs = list_pdfs(CORPUS)
    sel, info = build_sample(a.seed, a.n_random)
    print(info, "| chon", len(sel), {t: sum(1 for x in sel if x["tap"] == t) for t in ("rotated", "landscape", "random")})
    out = HERE / "_sheets"
    out.mkdir(exist_ok=True)
    for f in out.glob("sheet_*.png"):
        f.unlink()
    try:
        font = ImageFont.truetype("arialbd.ttf", 30)
    except Exception:
        font = ImageFont.load_default()
    per = COLS * ROWS
    docs = {}
    rows = []
    for i0 in range(0, len(sel), per):
        sh = Image.new("RGB", (COLS * CELL, ROWS * CELL), (200, 200, 205))
        d = ImageDraw.Draw(sh)
        for j, x in enumerate(sel[i0:i0 + per]):
            idx = i0 + j + 1
            pdf = pdfs[x["rel"]]
            doc = docs.get(pdf) or docs.setdefault(pdf, fitz.open(str(pdf)))
            pg = doc[x["page"] - 1]
            z = (CELL - 12) / max(pg.rect.width, pg.rect.height)
            pix = pg.get_pixmap(matrix=fitz.Matrix(z, z), alpha=False)
            im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            cx, cy = (j % COLS) * CELL + 6, (j // COLS) * CELL + 6
            sh.paste(im, (cx, cy))
            d.rectangle([cx - 1, cy - 1, cx + im.width, cy + im.height], outline=(220, 40, 40), width=1)
            d.rectangle([cx, cy, cx + 62, cy + 34], fill=(255, 255, 0))
            d.text((cx + 4, cy + 1), str(idx), fill=(0, 0, 0), font=font)
            rows.append(dict(idx=idx, sheet=i0 // per + 1, cell=j + 1, doc_id=x["doc_id"], page=x["page"], tap=x["tap"],
                             applied_rot=x["rot"], n_chars=x["n_chars"], source=x["source"], doc_type=x["dtype"]))
        sh.save(out / f"sheet_{i0 // per + 1:02d}.png")
    with open(HERE / "sample_pages.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("so to:", (len(sel) + per - 1) // per, "->", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
