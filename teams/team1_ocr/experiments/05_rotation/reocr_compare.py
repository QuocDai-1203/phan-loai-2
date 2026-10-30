"""reocr_compare.py - T2: chay lai OCR (engine that, GPU dung chung) tren cac trang bi xoay SAI / XOAY NHAM de so chu truoc/sau.

Trang duoc chon tu `orientation_gold.csv`: (a) trang co chu ma huong ocr_v2 da ap khac dap an; (b) trang gan trong bi xoay nham.
Voi moi trang so 3 cach:  "ocr_v2" = engine tu quyet dinh huong (nhu khi dung data/ocr_v2.jsonl),  "ep huong dap an" = ep xoay theo dap an
(0/90/270, giu nguyen phan con lai cua engine),  "luat moi" = src.ocr.pdf_ocr.ocr_page voi min_chars_for_rotation mac dinh.
Chi so chu: so ky tu, ty le token >=2 chu la co dang am tiet tieng Viet (luat chinh ta, `is_vn_syllable` cua 01_engine_bakeoff), ty le chu co dau.

Chay (GPU dung chung, ~1 phut):  .venv\\Scripts\\python.exe -X utf8 teams\\team1_ocr\\experiments\\05_rotation\\reocr_compare.py --device cuda:0
Ket qua: reocr_compare.csv (khong chua van ban, chi so dem).
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import time
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

_SYL = re.compile(r"^(ngh|ng|nh|ch|gh|gi|kh|ph|qu|th|tr|[bcdđghklmnpqrstvx])?([aăâeêioôơuưy]{1,3})(ng|nh|ch|[cmnpt])?$")
_TONES = {"̀": "huyen", "́": "sac", "̃": "nga", "̉": "hoi", "̣": "nang"}
_ACC = set("àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ")
_TOKEN = re.compile(r"[^\W\d_]+", re.UNICODE)


def is_vn_syllable(tok: str) -> bool:
    """Chep tu 01_engine_bakeoff/aggregate.py (luat chinh ta tieng Viet xap xi, khong dung tu dien)."""
    if not (1 <= len(tok) <= 7):
        return False
    nfd = unicodedata.normalize("NFD", tok)
    tones = [c for c in nfd if c in _TONES]
    if len(tones) > 1:
        return False
    base = unicodedata.normalize("NFC", "".join(c for c in nfd if c not in _TONES))
    m = _SYL.match(base)
    if not m:
        return False
    if m.group(1) == "qu" and not m.group(2):
        return False
    if m.group(3) in ("c", "ch", "p", "t") and tones and _TONES[tones[0]] not in ("sac", "nang"):
        return False
    return True


def text_stats(text: str) -> dict:
    t = unicodedata.normalize("NFC", text or "")
    toks = [x.lower() for x in _TOKEN.findall(t) if len(x) >= 2]
    letters = [c for c in t if c.isalpha()]
    return dict(n_chars=len(t.strip()), n_tokens=len(toks),
                valid_syl_rule=(sum(is_vn_syllable(x) for x in toks) / len(toks)) if toks else float("nan"),
                diac_ratio=(sum(c.lower() in _ACC for c in letters) / len(letters)) if letters else float("nan"))


def ocr_forced(engine, img, rot: int):
    """Giong VietOCREngine.ocr nhung EP huong xoay (rot in {0,90,270,180}) thay vi tu quyet dinh. Dung de do 'neu xoay dung thi sao'."""
    import numpy as np
    from src.ocr.vietocr_engine import bg_normalize, boxes_to_text, needs_bgnorm
    H, W = img.shape[:2]
    if needs_bgnorm(img):
        img = bg_normalize(img)
    boxes = engine._detect(img)
    if not boxes:
        return "", None
    rects = [(float(np.asarray(b)[:, 0].min()), float(np.asarray(b)[:, 1].min()),
              float(np.asarray(b)[:, 0].max()), float(np.asarray(b)[:, 1].max())) for b in boxes]
    crops = [engine._crop(img, b) for b in boxes]
    k = {0: 0, 90: 1, 180: 2, 270: 3}[rot]
    if k:
        crops = [np.rot90(c, k) for c in crops]
    res = engine._rec(crops)
    items = []
    for (x0, y0, x1, y1), (t, _) in zip(rects, res):
        if rot == 90:
            items.append((y0, W - x1, y1, W - x0, t))
        elif rot == 270:
            items.append((H - y1, x0, H - y0, x1, t))
        elif rot == 180:
            items.append((W - x1, H - y1, W - x0, H - y0, t))
        else:
            items.append((x0, y0, x1, y1, t))
    confs = [p for _, p in res if p == p]
    return boxes_to_text(items), (float(np.mean(confs)) if confs else None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--threads", type=int, default=4)
    a = ap.parse_args()
    import fitz
    from build_ocr_dataset import CORPUS, list_pdfs, make_doc_id
    from src.ocr.pdf_ocr import clean_text, ocr_page, render
    from src.ocr.vietocr_engine import VietOCREngine
    pdfs = {make_doc_id(r): p for r, p in list_pdfs(CORPUS).items()}
    gold = list(csv.DictReader(open(HERE / "orientation_gold.csv", encoding="utf-8-sig")))
    sel = [r for r in gold if r["tap"] != "rotated_dup" and int(r["applied_deg"]) != 0
           and (r["near_blank_gold"] == "1" or int(r["gold_deg"]) != int(r["applied_deg"]))]
    print(f"{len(sel)} trang can chay lai (sai huong co chu + gan trong bi xoay)")
    eng = VietOCREngine("vgg_seq2seq", a.device, a.threads, batch=16)
    rows = []
    for r in sel:
        doc = fitz.open(str(pdfs[r["doc_id"]]))
        pg = doc[int(r["page"]) - 1]
        img = render(pg, 200)
        t0 = time.perf_counter()
        txt, conf, flags = eng.ocr(img)
        base = text_stats(clean_text(txt))
        rot_flag = next((f for f in flags if f.startswith("rotated_")), "none")
        t1, c1 = ocr_forced(eng, img, int(r["gold_deg"]))
        forced = text_stats(clean_text(t1))
        new = ocr_page(pg, int(r["page"]) - 1, eng, 200)
        newst = text_stats(new.text)
        kind = "gan_trong_xoay_nham" if r["near_blank_gold"] == "1" else ("sai_huong" if int(r["gold_deg"]) else "xoay_thua")
        for name, st, extra in [("ocr_v2_tu_quyet_dinh", base, rot_flag), (f"ep_huong_dap_an_{r['gold_deg']}", forced, ""),
                                ("luat_moi_pdf_ocr", newst, ",".join(new.flags))]:
            rows.append(dict(kind=kind, doc_id=r["doc_id"], page=r["page"], gold_deg=r["gold_deg"], applied_deg=r["applied_deg"],
                             variant=name, flags=extra, **st))
        print(f"  {kind} {r['doc_id']} p{r['page']}: v2 {base['n_chars']} ky tu (am tiet {base['valid_syl_rule']:.2f}) | ep {forced['n_chars']} "
              f"({forced['valid_syl_rule']:.2f}) | luat moi {newst['n_chars']} {new.flags}  [{time.perf_counter() - t0:.1f}s]", flush=True)
        doc.close()
    with open(HERE / "reocr_compare.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
