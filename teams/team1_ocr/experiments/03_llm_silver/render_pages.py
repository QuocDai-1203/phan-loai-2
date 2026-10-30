import csv, random, sys, unicodedata
from pathlib import Path
import fitz, numpy as np
from PIL import Image
R = Path(r"Z:\projects\sdh-phanloaitailieu")
SAMPLES = R / "docs" / "_chot_samples_phanloaitailieu"
T1 = R / "teams" / "team1_ocr"
OUT = Path(sys.argv[1])
rows = []
def load(p, kind):
    with open(p, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            rows.append((kind, unicodedata.normalize("NFC", r["relative_path"]), int(r["page"])))
load(T1 / "experiments/01_engine_bakeoff/sample_gold_pages.csv", "gold_textlayer")
load(T1 / "experiments/01_engine_bakeoff/sample_scan_pages.csv", "scan_sample")
load(T1 / "gold/gold_pages_todo.csv", "scan_todo")
seen, uniq = set(), []
for k, rel, pg in rows:
    if (rel, pg) in seen: continue
    seen.add((rel, pg)); uniq.append((k, rel, pg))
random.Random(20261011).shuffle(uniq)
index = {unicodedata.normalize("NFC", p.relative_to(SAMPLES).as_posix()): p for p in SAMPLES.rglob("*.pdf")}
with open(OUT / "pages.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f); w.writerow(["page_id", "kind", "relative_path", "page0", "n_parts"])
    for i, (k, rel, pg) in enumerate(uniq, 1):
        pid = f"P{i:03d}"
        doc = fitz.open(index[rel]); page = doc[pg]
        pix = page.get_pixmap(dpi=200, colorspace=fitz.csGRAY if False else fitz.csRGB)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        g = np.asarray(img.convert("L"), dtype=np.float32)
        h = g.shape[0]
        if h > g.shape[1]:  # trang doc: cat doi tai hang it muc nhat quanh giua trang
            lo, hi = int(h * 0.44), int(h * 0.56)
            ink = (255 - g[lo:hi]).sum(axis=1)
            cut = lo + int(ink.argmin())
            parts = [img.crop((0, 0, img.width, cut)), img.crop((0, cut, img.width, h))]
        else:
            parts = [img]
        for j, p in enumerate(parts):
            p.save(OUT / "img" / f"{pid}_{'ab'[j]}.png")
        w.writerow([pid, k, rel, pg, len(parts)])
        doc.close()
print(len(uniq), "pages")
