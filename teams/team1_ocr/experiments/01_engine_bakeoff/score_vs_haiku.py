"""score_vs_haiku.py - cham cac engine local tren trang scan THAT theo ban chep 'bac' cua Haiku (gold/silver_llm/haiku).
Xoa ky hieu [..] va '|' (clean_llm cua 03_llm_silver) truoc khi cham.  Metric chinh: bag-of-words (khong phu thuoc thu tu doc);
CER la CER toan chuoi (nhay cam voi thu tu doc va chu viet tay -> chi mang tinh tham khao).
Chay: .venv/Scripts/python.exe -X utf8 score_vs_haiku.py   -> results_vs_haiku.csv, results_vs_haiku_pages.csv
"""
import csv, json, re, sys, unicodedata
from collections import Counter
from pathlib import Path
import pandas as pd
from ocrlib import nfc, norm, all_metrics

HERE = Path(__file__).parent
T1 = HERE.parents[1]
MARK = re.compile(r"\[[^\]\n]{0,200}\]")
clean_llm = lambda t: MARK.sub(" ", t).replace("|", " ")

pages = [r for r in csv.DictReader(open(T1 / "experiments" / "03_llm_silver" / "pages.csv", encoding="utf-8")) if r["kind"] == "scan_sample"]
ref = {(nfc(r["relative_path"]), int(r["page0"])): clean_llm((T1 / "gold" / "silver_llm" / "haiku" / f"{r['page_id']}.txt").read_text(encoding="utf-8")) for r in pages}

def bag(g, h):
    cg = Counter(nfc(norm(g).casefold()).split()); ch = Counter(nfc(norm(h).casefold()).split())
    ov = sum((cg & ch).values()); p = ov / max(sum(ch.values()), 1); r = ov / max(sum(cg.values()), 1)
    return dict(bag_recall=r, bag_precision=p, bag_f1=2 * p * r / (p + r) if p + r else 0.0)

rows = []
for f in sorted((HERE / "_cache" / "raw").glob("*__scan__200__main.jsonl")):
    for line in f.open(encoding="utf-8"):
        r = json.loads(line); k = (nfc(r["relative_path"]), r["page"])
        if k not in ref:
            continue
        m = all_metrics(ref[k], r["text"]); b = bag(ref[k], r["text"])
        rows.append(dict(engine=r["engine"], relative_path=k[0], page=k[1], cer=m["cer"], cer_nodiac=m["cer_nodiac"], diac_recall=m["diac_recall"], **b))
d = pd.DataFrame(rows); d.to_csv(HERE / "results_vs_haiku_pages.csv", index=False, encoding="utf-8")
keys = {e: set(zip(g.relative_path, g.page)) for e, g in d.groupby("engine") if len(g) >= 14}
common = set.intersection(*keys.values())
d["key"] = list(zip(d.relative_path, d.page))
out = []
for subset, dd in (("all", d), ("common%d" % len(common), d[d.key.isin(common)])):
    for e, g in dd.groupby("engine"):
        out.append(dict(subset=subset, engine=e, n_pages=len(g), bag_recall=g.bag_recall.mean(), bag_precision=g.bag_precision.mean(), bag_f1=g.bag_f1.mean(),
                        cer=g.cer.mean(), cer_nodiac=g.cer_nodiac.mean(), diac_recall=g.diac_recall.mean()))
o = pd.DataFrame(out); o.to_csv(HERE / "results_vs_haiku.csv", index=False, encoding="utf-8", float_format="%.4f")
pd.set_option("display.width", 220); print(o.round(3).to_string())
