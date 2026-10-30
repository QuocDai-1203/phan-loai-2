"""aggregate.py - doc _cache/raw/*.jsonl, tinh metric, ghi results.csv (+ results_pages.csv chi tiet tung trang).

Chay: .venv/Scripts/python.exe -X utf8 aggregate.py
- Tap gold (born-digital): CER, WER, CER_nodiac, CER_nospace, diac_recall, bag_f1, giay/trang  (trung binh macro theo trang)
- Tap scan (khong GT): ty le dau, ty le am tiet hop le, conf TB, giay/trang
"""
import json, re, unicodedata
from pathlib import Path
import numpy as np, pandas as pd
from ocrlib import *

HERE = Path(__file__).parent
CACHE = HERE / "_cache"
VN_ACCENT = set("àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ")
TOKEN = re.compile(r"[^\W\d_]+", re.UNICODE)


def syllable_vocab():
    """Tu dien am tiet tu text layer cua cac PDF born-digital (loai tru khong can thiet: lay tat ca trang co text hien thi
    & ty le dau > 10%). Tra ve (set am tiet lowercase NFC).  Luu cache."""
    f = CACHE / "syllables.txt"
    if f.exists():
        return set(f.read_text(encoding="utf-8").split())
    import pandas as pd, fitz
    s = pd.read_csv(CACHE / "survey_pages.csv")
    b = s[(s.n_chars >= 300) & (s.acc_ratio > 0.1) & (s.vis_chars > 0) & (s.img_cov < 0.8)]
    vocab = set()
    for rel, g in b.groupby("rel"):
        doc = open_pdf(rel)
        for p in g.page:
            for tok in TOKEN.findall(nfc(doc[int(p)].get_text("text")).lower()):
                vocab.add(tok)
    f.write_text("\n".join(sorted(vocab)), encoding="utf-8")
    return vocab


_SYL = re.compile(r"^(ngh|ng|nh|ch|gh|gi|kh|ph|qu|th|tr|[bcdđghklmnpqrstvx])?([aăâeêioôơuưy]{1,3})(ng|nh|ch|[cmnpt])?$")
_TONES = {"̀": "huyen", "́": "sac", "̃": "nga", "̉": "hoi", "̣": "nang"}


def is_vn_syllable(tok: str) -> bool:
    """Kiem tra am tiet tieng Viet theo luat chinh ta (xap xi): <=7 ky tu, 1 dau thanh, phu am dau + nguyen am + phu am cuoi
    hop le; am tiet ket thuc c/ch/p/t chi mang sac hoac nang. KHONG kiem tra tu dien nen cho qua ca mot so tu tieng Anh."""
    import unicodedata as ud
    if not (1 <= len(tok) <= 7):
        return False
    nfd = ud.normalize("NFD", tok)
    tones = [c for c in nfd if c in _TONES]
    if len(tones) > 1:
        return False
    base = ud.normalize("NFC", "".join(c for c in nfd if c not in _TONES))
    m = _SYL.match(base)
    if not m:
        return False
    if m.group(1) == "qu" and not m.group(2):
        return False
    if m.group(3) in ("c", "ch", "p", "t") and tones and _TONES[tones[0]] not in ("sac", "nang"):
        return False
    return True


def scan_proxy(text, vocab):
    toks = [t.lower() for t in TOKEN.findall(nfc(text))]
    letters = [c for c in nfc(text) if c.isalpha()]
    acc = sum(1 for c in letters if c.lower() in VN_ACCENT)
    long_ = [t for t in toks if len(t) >= 2]
    valid = sum(1 for t in long_ if t in vocab)
    valid_rule = sum(1 for t in long_ if is_vn_syllable(t))
    glued = sum(1 for t in toks if len(t) >= 12)  # tu dai bat thuong = dinh chu
    return dict(n_chars=len(text.strip()), diac_ratio=acc / len(letters) if letters else 0.0,
                valid_syl=valid / len(long_) if long_ else float("nan"),
                valid_rule=valid_rule / len(long_) if long_ else float("nan"), n_tokens=len(toks),
                glued_ratio=glued / len(toks) if toks else 0.0)


def load_raw():
    rows = []
    for f in sorted((CACHE / "raw").glob("*.jsonl")):
        for line in f.open(encoding="utf-8"):
            r = json.loads(line); r.setdefault("tag", "main"); rows.append(r)
    return pd.DataFrame(rows)


def main():
    raw_all = load_raw()
    timing = raw_all[raw_all.tag == "timing"]
    raw = raw_all[raw_all.tag != "timing"]
    vocab = syllable_vocab()
    print("vocab am tiet:", len(vocab))
    # ---- gold
    gold = raw[raw.set == "gold"].copy()
    docs = {}
    out_pages = []
    for r in gold.itertuples():
        key = (r.relative_path, r.page)
        if key not in docs:
            d = open_pdf(r.relative_path)
            docs[key] = gt_words_text(d[r.page])
        m = all_metrics(docs[key], r.text)
        out_pages.append(dict(engine=r.engine, set="gold", variant=r.variant, dpi=r.dpi, relative_path=r.relative_path, page=r.page,
                              seconds=r.seconds, device=r.device, mean_conf=r.mean_conf, error=r.error, **m))
    gp = pd.DataFrame(out_pages)
    # ---- scan
    scan = raw[raw.set == "scan"].copy()
    sp = []
    for r in scan.itertuples():
        m = scan_proxy(r.text, vocab)
        sp.append(dict(engine=r.engine, set="scan", variant="scan", dpi=r.dpi, relative_path=r.relative_path, page=r.page,
                       folder=r.folder, seconds=r.seconds, device=r.device, mean_conf=r.mean_conf, error=r.error, **m))
    spd = pd.DataFrame(sp)
    pd.concat([gp, spd]).to_csv(HERE / "results_pages.csv", index=False, encoding="utf-8")

    rows = []
    # tap chung "grid4": trang thu 0,4,8,... trong sample_gold_pages.csv (stride 4); cac engine chay stride 1/2/4 deu chua tap nay
    gcsv = pd.read_csv(HERE / "sample_gold_pages.csv")
    grid4 = set(zip(gcsv.relative_path.iloc[::4], gcsv.page.iloc[::4].astype(int)))
    scsv = pd.read_csv(HERE / "sample_scan_pages.csv")
    if len(gp):
        gp["key"] = list(zip(gp.relative_path, gp.page))
        for (eng, var, dpi), g in gp.groupby(["engine", "variant", "dpi"]):
            for subset, gg in (("all", g), ("grid4", g[g.key.isin(grid4)])):
                if subset == "grid4" and len(gg) < len(grid4):
                    continue  # engine khong du tap chung
                rows.append(dict(set="gold", subset=subset, engine=eng, variant=var, dpi=dpi, n_pages=len(gg), device=gg.device.iloc[0],
                                 cer=gg.cer.mean(), wer=gg.wer.mean(), cer_nodiac=gg.cer_nodiac.mean(), cer_nospace=gg.cer_nospace.mean(),
                                 cer_cs=gg.cer_cs.mean(), tok_ratio=gg.tok_ratio.mean(), diac_recall=gg.diac_recall.mean(), bag_f1=gg.bag_f1.mean(),
                                 sec_per_page_median=gg.seconds.median(), sec_per_page_mean=gg.seconds.mean(), n_errors=int(gg.error.notna().sum())))
    if len(spd):
        for (eng, dpi), g in spd.groupby(["engine", "dpi"]):
            rows.append(dict(set="scan", subset="all", engine=eng, variant="scan", dpi=dpi, n_pages=len(g), device=g.device.iloc[0],
                             diac_ratio=g.diac_ratio.mean(), valid_syl=g.valid_syl.mean(), valid_rule=g.valid_rule.mean(), glued_ratio=g.glued_ratio.mean(),
                             mean_conf=g.mean_conf.mean(), n_chars_mean=g.n_chars.mean(),
                             sec_per_page_median=g.seconds.median(), sec_per_page_mean=g.seconds.mean(), n_errors=int(g.error.notna().sum())))
        # tap scan chung: trang co mat o MOI engine chay >= 14 trang (de so sanh cong bang)
        keysets = {e: set(zip(g.relative_path, g.page)) for e, g in spd.groupby("engine") if len(g) >= 14}
        if keysets:
            common = set.intersection(*keysets.values())
            spd["key"] = list(zip(spd.relative_path, spd.page))
            for (eng, dpi), g in spd[spd.key.isin(common)].groupby(["engine", "dpi"]):
                if eng in keysets:
                    rows.append(dict(set="scan", subset="common", engine=eng, variant="scan", dpi=dpi, n_pages=len(g), device=g.device.iloc[0],
                                     diac_ratio=g.diac_ratio.mean(), valid_syl=g.valid_syl.mean(), valid_rule=g.valid_rule.mean(), glued_ratio=g.glued_ratio.mean(),
                                     mean_conf=g.mean_conf.mean(), n_chars_mean=g.n_chars.mean(),
                                     sec_per_page_median=g.seconds.median(), sec_per_page_mean=g.seconds.mean(), n_errors=int(g.error.notna().sum())))
    if len(timing):
        for (eng, st), g in timing.groupby(["engine", "set"]):
            rows.append(dict(set="timing_" + st, subset="alone", engine=eng, variant="clean" if st == "gold" else "scan", dpi=g.dpi.iloc[0],
                             n_pages=len(g), device=g.device.iloc[0], sec_per_page_median=g.seconds.median(), sec_per_page_mean=g.seconds.mean(),
                             n_errors=int(g.error.notna().sum())))
    res = pd.DataFrame(rows)
    res.to_csv(HERE / "results.csv", index=False, encoding="utf-8", float_format="%.4f")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(res.round(3).to_string())


if __name__ == "__main__":
    main()
