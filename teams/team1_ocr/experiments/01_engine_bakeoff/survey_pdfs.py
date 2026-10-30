"""Khao sat toan bo trang cua 336 PDF: text layer, anh, chu vo hinh (render mode 3), ti le dau tieng Viet.
Chay: .venv/Scripts/python.exe -X utf8 survey_pdfs.py  -> _cache/survey_pages.csv
"""
import sys, csv, unicodedata, hashlib
from pathlib import Path
import fitz
ROOT = Path(r"Z:\projects\sdh-phanloaitailieu\docs\_chot_samples_phanloaitailieu")
OUT = Path(__file__).parent / "_cache"; OUT.mkdir(exist_ok=True)
VN_ACCENT = set("àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ")
def feat(page):
    txt = page.get_text("text")
    txt = unicodedata.normalize("NFC", txt)
    letters = [c for c in txt if c.isalpha()]
    acc = sum(1 for c in letters if c.lower() in VN_ACCENT)
    # image coverage
    area = page.rect.width * page.rect.height
    cov = 0.0; nimg = 0
    for info in page.get_image_info():
        r = fitz.Rect(info["bbox"]) & page.rect
        cov += r.width * r.height; nimg += 1
    cov = min(cov / area, 1.0) if area else 0
    # invisible vs visible chars
    vis = invis = 0
    try:
        for sp in page.get_texttrace():
            n = len(sp.get("chars", ()))
            if sp.get("type") == 3 or sp.get("opacity", 1) == 0: invis += n
            else: vis += n
    except Exception: pass
    fonts = len(page.get_fonts())
    return dict(n_chars=len(txt.strip()), n_letters=len(letters), acc_ratio=round(acc/len(letters),4) if letters else 0,
                n_images=nimg, img_cov=round(cov,3), vis_chars=vis, invis_chars=invis, n_fonts=fonts)
rows = []
pdfs = sorted(ROOT.rglob("*.pdf"), key=lambda p: unicodedata.normalize("NFC", p.relative_to(ROOT).as_posix()))
for p in pdfs:
    rel = unicodedata.normalize("NFC", p.relative_to(ROOT).as_posix())
    try: d = fitz.open(p)
    except Exception as e:
        print("ERR", rel, e); continue
    meta = d.metadata or {}
    for i, pg in enumerate(d):
        r = dict(rel=rel, page=i, npages=len(d), producer=(meta.get("producer") or "")[:40], creator=(meta.get("creator") or "")[:40])
        r.update(feat(pg)); rows.append(r)
with open(OUT/"survey_pages.csv","w",newline="",encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(len(pdfs), "pdfs", len(rows), "pages")
