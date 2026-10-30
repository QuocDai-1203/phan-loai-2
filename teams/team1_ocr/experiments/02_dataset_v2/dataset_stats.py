"""dataset_stats.py - thong ke data/ocr_v2.jsonl va so sanh voi baseline (trang 1) -> stats.json + in ra man hinh.
Chay: .venv/Scripts/python.exe -X utf8 dataset_stats.py
"""
import json, re, unicodedata, collections, statistics, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[4]
ACC = set("àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ")
nfc = lambda s: unicodedata.normalize("NFC", s)
TOK = re.compile(r"[^\W\d_]+", re.UNICODE)

def acc_ratio(t):
    L = [c for c in nfc(t) if c.isalpha()]
    return (sum(c.lower() in ACC for c in L), len(L))

def long_tok(t):
    toks = TOK.findall(nfc(t)); 
    return (sum(len(x) >= 12 for x in toks), len(toks))

v2 = [json.loads(l) for l in open(REPO / "data" / "ocr_v2.jsonl", encoding="utf-8")]
base = {nfc(json.loads(l)["relative_path"]): json.loads(l) for l in open(REPO / "data" / "baseline_ocr_335.jsonl", encoding="utf-8")}
pages = [(d, p) for d in v2 for p in d["pages"]]
out = {}
out["docs"] = len(v2); out["pages"] = len(pages)
out["pages_by_source"] = dict(collections.Counter(p["source"] for _, p in pages))
out["docs_truncated"] = sum(d["pages_truncated"] for d in v2)
out["errors"] = sum(1 for _, p in pages if p["error"])
out["near_empty_lt5"] = sum(1 for _, p in pages if not p["error"] and p["n_chars"] < 5)
out["near_empty_lt30"] = sum(1 for _, p in pages if not p["error"] and p["n_chars"] < 30)
flag = collections.Counter(f.split(":")[0] for _, p in pages for f in p.get("flags", []))
out["flags"] = dict(flag)
copied = sum(1 for _, p in pages if any(f.startswith("copied_from") for f in p.get("flags", [])))
out["pages_copied_from_exact_duplicates"] = copied
ocr = [p for _, p in pages if p["source"] and "ocr" in p["source"] and not any(f.startswith("copied_from") for f in p.get("flags", []))]
out["ocr_pages_actually_run"] = len(ocr)
out["ocr_seconds_sum"] = round(sum(p["seconds"] for p in ocr), 1)
out["ocr_sec_per_page_mean"] = round(out["ocr_seconds_sum"] / max(len(ocr), 1), 2)
out["ocr_sec_per_page_median"] = round(statistics.median(p["seconds"] for p in ocr), 2) if ocr else None
confs = [p["mean_conf"] for p in ocr if p["mean_conf"] is not None]
out["mean_conf_mean"] = round(statistics.mean(confs), 3) if confs else None
out["low_conf_lt0.6"] = sum(c < 0.6 for c in confs)
out["chars_total"] = sum(p["n_chars"] for _, p in pages)
# trang sinh loi nhieu nhat: do lech giua so ky tu
# ---- truoc/sau theo thu muc
fold = collections.defaultdict(lambda: dict(n=0, b_acc=0, b_let=0, a1_acc=0, a1_let=0, aa_acc=0, aa_let=0, b_long=0, b_tok=0, a_long=0, a_tok=0, pages=0))
for d in v2:
    f = d["folder_label"] or "(root)"
    F = fold[f]; F["n"] += 1; F["pages"] += d["pages_processed"]
    for p in d["pages"]:
        a, l = acc_ratio(p["text"]); F["aa_acc"] += a; F["aa_let"] += l
    p1 = d["pages"][0]["text"] if d["pages"] else ""
    a, l = acc_ratio(p1); F["a1_acc"] += a; F["a1_let"] += l
    lt, tk = long_tok(p1); F["a_long"] += lt; F["a_tok"] += tk
    b = base.get(nfc(d["relative_path"]))
    if b is not None:
        a, l = acc_ratio(b["ocr_text"]); F["b_acc"] += a; F["b_let"] += l
        lt, tk = long_tok(b["ocr_text"]); F["b_long"] += lt; F["b_tok"] += tk
rows = []
for f, F in sorted(fold.items()):
    rows.append(dict(folder=f, docs=F["n"], pages=F["pages"],
                     diac_before_p1=F["b_acc"] / F["b_let"] if F["b_let"] else None,
                     diac_after_p1=F["a1_acc"] / F["a1_let"] if F["a1_let"] else None,
                     diac_after_allpages=F["aa_acc"] / F["aa_let"] if F["aa_let"] else None,
                     longtok_before_p1=F["b_long"] / F["b_tok"] if F["b_tok"] else None,
                     longtok_after_p1=F["a_long"] / F["a_tok"] if F["a_tok"] else None))
out["per_folder"] = rows
tb = sum(F["b_acc"] for F in fold.values()), sum(F["b_let"] for F in fold.values())
ta = sum(F["a1_acc"] for F in fold.values()), sum(F["a1_let"] for F in fold.values())
out["diac_before_p1_all"] = tb[0] / tb[1]; out["diac_after_p1_all"] = ta[0] / ta[1]
out["longtok_before_p1_all"] = sum(F["b_long"] for F in fold.values()) / sum(F["b_tok"] for F in fold.values())
out["longtok_after_p1_all"] = sum(F["a_long"] for F in fold.values()) / sum(F["a_tok"] for F in fold.values())
# trang embedded layer
emb = [(d["relative_path"], p["page"], p.get("embedded_layer_rejected"), p["n_chars"], acc_ratio(p["text"])) for d, p in pages if p["source"] == "embedded_ocr_layer+ocr"]
out["embedded_layer_pages"] = [dict(rel=r, page=pg, rejected=why, n_chars=n, diac_ratio_new=(a / l if l else 0)) for r, pg, why, n, (a, l) in emb]
Path(__file__).with_name("stats.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if k not in ("per_folder",)}, ensure_ascii=False, indent=1))
print("%-45s %5s %5s  %-8s %-8s %-8s | longtok %-7s %-7s" % ("folder", "docs", "pages", "dBefore", "dAfter1", "dAfterAll", "before", "after"))
f = lambda x: "  -   " if x is None else "%.3f" % x
for r in rows:
    print("%-45s %5d %5d  %-8s %-8s %-8s | %-7s %-7s" % (r["folder"][:45], r["docs"], r["pages"], f(r["diac_before_p1"]), f(r["diac_after_p1"]), f(r["diac_after_allpages"]), f(r["longtok_before_p1"]), f(r["longtok_after_p1"])))
