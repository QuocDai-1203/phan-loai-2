"""Tao 2 danh sach mau co dinh (seed) tu _cache/survey_pages.csv:
  sample_gold_pages.csv  - ~40 trang born-digital (GT = text layer)
  sample_scan_pages.csv  - ~30 trang scan that (khong GT)
Chay: .venv/Scripts/python.exe -X utf8 make_samples.py   (can chay survey_pdfs.py truoc)
"""
import random
from pathlib import Path
import pandas as pd

HERE = Path(__file__).parent
d = pd.read_csv(HERE / "_cache" / "survey_pages.csv")
d["folder"] = d.rel.map(lambda r: r.split("/")[0] if "/" in r else "(root)")
rng = random.Random(20260101)

# ---- born-digital: text layer co dau, chu hien thi (khong phai lop chu vo hinh), khong phai anh toan trang
born = d[(d.n_chars >= 300) & (d.acc_ratio > 0.1) & (d.vis_chars > 0) & (d.img_cov < 0.8)].copy()
picks = []
for folder, g in born.groupby("folder"):
    docs = sorted(g.rel.unique())
    if len(docs) == 1:           # 1 hop dong 30 trang: lay 10 trang cach deu
        pages = sorted(g.page.unique())
        step = max(len(pages) // 10, 1)
        for p in pages[::step][:10]:
            picks.append((docs[0], int(p), folder))
    else:                        # nhieu van ban cung mau: lay toi da 15 van ban, trang 0
        chosen = rng.sample(docs, min(15, len(docs)))
        for r in sorted(chosen):
            picks.append((r, int(g[g.rel == r].page.min()), folder))
gold = pd.DataFrame(picks, columns=["relative_path", "page", "folder"])
gold.to_csv(HERE / "sample_gold_pages.csv", index=False, encoding="utf-8")
print("gold pages:", len(gold), gold.folder.value_counts().to_dict())

# ---- scan that: trang khong co text layer; phan bo deu theo thu muc, uu tien nhom kho (viet tay/con dau)
scan = d[(d.n_chars < 50) & (d.img_cov > 0.5)].copy()
hard = ["6. CUA HANG - BB MAU- VÂN", "8. CUA HANG - TU K.TRA PCCC- VÂN", "TU K.TRA PCCC- VÂN",
        "_Biên bản giao nhận 2026", "9. TỔNG HỢP HỒ SƠ CỬA HÀNG"]
sel = []
folders = sorted(scan.folder.unique())
for f in folders:
    g = scan[scan.folder == f]
    quota = 3 if f in hard else 1
    pool = sorted(set(zip(g.rel, g.page)))
    for rel, pg in rng.sample(pool, min(quota, len(pool))):
        sel.append((rel, int(pg), f))
# lam tron ~30 bang cach bo sung ngau nhien tu cac thu muc chua du
rest = sorted(set(zip(scan.rel, scan.page, scan.folder)) - set(sel))
rng.shuffle(rest)
while len(sel) < 30 and rest:
    sel.append(rest.pop())
sel = sel[:34]
sc = pd.DataFrame(sel, columns=["relative_path", "page", "folder"]).sort_values(["folder", "relative_path", "page"])
sc.to_csv(HERE / "sample_scan_pages.csv", index=False, encoding="utf-8")
print("scan pages:", len(sc), sc.folder.value_counts().to_dict())
