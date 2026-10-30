"""zoom_sheets.py - T2: phong to cac trang kho nhin huong tren to tiep xuc (so thu tu `idx` trong sample_pages.csv).

Ghep 2x2 trang, moi trang canh dai toi da 740 px, luu `_sheets/zoom_NN.png` (da .gitignore).
Chay:  .venv\\Scripts\\python.exe -X utf8 teams\\team1_ocr\\experiments\\05_rotation\\zoom_sheets.py 9 10 12 13 ...  [--cols 2 --cell 740]
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("idx", type=int, nargs="+")
    ap.add_argument("--cols", type=int, default=2)
    ap.add_argument("--cell", type=int, default=740)
    ap.add_argument("--prefix", default="zoom")
    a = ap.parse_args()
    import fitz
    from PIL import Image, ImageDraw, ImageFont
    import json
    from build_ocr_dataset import CORPUS, list_pdfs, make_doc_id
    pdfs = {make_doc_id(rel): p for rel, p in list_pdfs(CORPUS).items()}
    rows = {int(r["idx"]): r for r in csv.DictReader(open(HERE / "sample_pages.csv", encoding="utf-8-sig"))}
    out = HERE / "_sheets"
    for f in out.glob(f"{a.prefix}_*.png"):
        f.unlink()
    font = ImageFont.truetype("arialbd.ttf", 34)
    per = a.cols * 2
    for k, i0 in enumerate(range(0, len(a.idx), per)):
        grp = a.idx[i0:i0 + per]
        sh = Image.new("RGB", (a.cols * a.cell, 2 * a.cell), (200, 200, 205))
        d = ImageDraw.Draw(sh)
        for j, i in enumerate(grp):
            r = rows[i]
            doc = fitz.open(str(pdfs[r["doc_id"]]))
            pg = doc[int(r["page"]) - 1]
            z = (a.cell - 8) / max(pg.rect.width, pg.rect.height)
            pix = pg.get_pixmap(matrix=fitz.Matrix(z, z), alpha=False)
            im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            cx, cy = (j % a.cols) * a.cell + 4, (j // a.cols) * a.cell + 4
            sh.paste(im, (cx, cy))
            d.rectangle([cx - 1, cy - 1, cx + im.width, cy + im.height], outline=(220, 40, 40), width=1)
            d.rectangle([cx, cy, cx + 74, cy + 40], fill=(255, 255, 0))
            d.text((cx + 4, cy + 1), str(i), fill=(0, 0, 0), font=font)
            doc.close()
        sh.save(out / f"{a.prefix}_{k + 1:02d}.png")
    print("so to:", (len(a.idx) + per - 1) // per)
    return 0


if __name__ == "__main__":
    sys.exit(main())
