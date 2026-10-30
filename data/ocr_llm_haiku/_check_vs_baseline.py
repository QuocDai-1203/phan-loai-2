r"""Kiểm tra chéo bản chép trang 1 của LLM với OCR baseline cũ (độc lập, không dấu) để phát hiện bản chép bịa.
So theo 4-gram ký tự đã bỏ dấu và bỏ khoảng trắng: bản chép thật phải phủ được phần lớn nội dung baseline."""
import collections, json, re, sys, unicodedata
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

def fold(s):
    s = unicodedata.normalize("NFD", s.replace("đ", "d").replace("Đ", "D"))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "", s)

def grams(s):
    return collections.Counter(s[i:i + 4] for i in range(len(s) - 3))

m = pd.read_csv(ROOT / "data/manifest.csv", encoding="utf-8-sig", dtype=str).fillna("")
rel2id = {unicodedata.normalize("NFC", r.relative_path): r.doc_id for r in m.itertuples()}
base = {}
for l in open(ROOT / "data/baseline_ocr_335.jsonl", encoding="utf-8"):
    j = json.loads(l)
    rp = unicodedata.normalize("NFC", j["relative_path"].replace(chr(92), "/"))
    for k, v in rel2id.items():
        if rp.endswith(k):
            base[v] = j["ocr_text"]
            break
flag = set(sys.argv[1:])
rows = []
for p in sorted((ROOT / "data/ocr_llm_haiku/pages").glob("*_p1.txt")):
    did = p.name[:12]
    if did not in base:
        continue
    h = fold(re.sub(r"\[[^\]\n]{0,200}\]", " ", p.read_text(encoding="utf-8")))
    b = fold(base[did])
    gb, gh = grams(b), grams(h)
    ov = sum((gb & gh).values())
    rows.append((p.stem, ov / max(sum(gb.values()), 1), ov / max(sum(gh.values()), 1), len(b), len(h), p.stem in flag))
d = pd.DataFrame(rows, columns=["page", "recall_base", "prec", "n_base", "n_llm", "flagged"])
d.to_csv(ROOT / "data/ocr_llm_haiku/_check_vs_baseline.csv", index=False)
print("baseline mapped", len(base), "| pages checked", len(d))
if flag:
    print(d[d.flagged].round(2).to_string(index=False))
print("quantiles recall (not flagged):", d[~d.flagged].recall_base.quantile([.01, .05, .1, .25, .5]).round(2).to_dict())
print("lowest 30 not flagged:")
print(d[~d.flagged].sort_values("recall_base").head(30).round(2).to_string(index=False))
