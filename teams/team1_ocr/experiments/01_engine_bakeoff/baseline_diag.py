"""Chan doan baseline_ocr_335.jsonl: moi ban ghi den tu text layer hay tu RapidOCR, va ty le chu cai co dau.
Chay: .venv/Scripts/python.exe -X utf8 baseline_diag.py   (can _cache/survey_pages.csv tu survey_pdfs.py)
"""
import json, unicodedata, collections
import pandas as pd
ACC = set("àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ")
nfc = lambda s: unicodedata.normalize("NFC", s)
def acc_ratio(t):
    L = [c for c in nfc(t) if c.isalpha()]
    return sum(c.lower() in ACC for c in L) / len(L) if L else 0.0
s = pd.read_csv("_cache/survey_pages.csv"); s["rel"] = s.rel.map(nfc)
p1 = s[s.page == 0].set_index("rel")
rows = []
for l in open("../../../../data/baseline_ocr_335.jsonl", encoding="utf-8"):
    r = json.loads(l); rel = nfc(r["relative_path"]); t = r["ocr_text"]
    f = p1.loc[rel]
    layer = int(f.n_chars) >= 50  # dung tieu chi cua generate_baseline_ocr.py
    kind = "OCR(RapidOCR)" if not layer else ("text layer vo hinh/khong dau (scanner)" if f.invis_chars > f.vis_chars else "text layer born-digital")
    rows.append(dict(rel=rel, folder=r["category_label"], kind=kind, acc_ratio=acc_ratio(t), n_chars=len(t)))
d = pd.DataFrame(rows)
print("so ban ghi baseline:", len(d))
g = d.groupby("kind").agg(n=("rel", "size"), acc_ratio_mean=("acc_ratio", "mean"), acc_ratio_max=("acc_ratio", "max"))
print(g.round(4).to_string())
d.to_csv("baseline_diacritics_diag.csv", index=False, encoding="utf-8")
# so trang toan kho
print("\nToan bo 1246 trang cua 336 PDF:")
s["kind"] = "khong co text layer (scan thuan)"
s.loc[s.n_chars >= 50, "kind"] = "text layer born-digital"
s.loc[(s.n_chars >= 50) & (s.invis_chars > s.vis_chars), "kind"] = "text layer vo hinh (OCR nhung cua may scan)"
print(s.kind.value_counts().to_string())
inv = s[s.kind.str.startswith("text layer vo hinh")]
print("tai lieu co lop chu vo hinh:", inv.rel.nunique(), "| trang:", len(inv), "| ty le chu cai co dau cua lop chu do: %.4f" % inv.acc_ratio.mean())
