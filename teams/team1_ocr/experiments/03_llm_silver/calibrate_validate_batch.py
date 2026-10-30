r"""calibrate_validate_batch.py - T6: do kha nang phat hien lo bia cua kiem cheo 4-gram (validate_batch.py) de dat nguong.

Lay 477 trang that cua lo Haiku cu (data/ocr_llm_haiku/pages) co OCR doc lap (ocr_v2, chi trang OCR that, >= 44 ky tu chu so):
  * "dung":  recall 4-gram cua ban chep dung trang;
  * "bia":   recall khi ban chep bi GAN NHAM sang mot trang khac (mo phong ban chep bia/khong lien quan toi anh). Trang cua cung loai
             tai lieu chia se 4-gram nen recall "bia" khong bang 0.
Mo phong lo N trang co f trang bia (mac dinh f = 12, nhu dot da phai lam lai): ty le lo bi bao KHONG HOP LE boi tieu chi kiem cheo
(trung vi < min_median_recall hoac ty le nghi van > max_suspect_share), va xac suat it nhat mot trang kiem (trang trang + trang da biet)
roi vao nhom trang bia (kiem soat boi tron ngau nhien).

Chay:  .venv\Scripts\python.exe -X utf8 teams\team1_ocr\experiments\03_llm_silver\calibrate_validate_batch.py
"""
from __future__ import annotations

import importlib.util
import json
import random
import re
import sys
from math import comb
from pathlib import Path
from statistics import median

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
spec = importlib.util.spec_from_file_location("validate_batch", HERE / "validate_batch.py")
vb = importlib.util.module_from_spec(spec)
sys.modules["validate_batch"] = vb
spec.loader.exec_module(vb)


def wilson(k, n, z=1.96):
    from math import sqrt
    if not n:
        return (float("nan"),) * 2
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0, c - h), min(1, c + h))


def main() -> int:
    th = vb.Thresholds()
    ocr = {}
    for l in open(REPO / "data" / "ocr_v2.jsonl", encoding="utf-8"):
        j = json.loads(l)
        for p in j["pages"]:
            if p["source"] in ("ocr", "embedded_ocr_layer+ocr"):
                ocr[(j["doc_id"], p["page"])] = p["text"]
    llm = {}
    for p in sorted((REPO / "data" / "ocr_llm_haiku" / "pages").glob("*.txt")):
        m = re.match(r"([0-9a-f]{12})_p(\d+)", p.stem)
        k = (m[1], int(m[2]))
        if k in ocr and len(vb.fold(ocr[k])) >= th.min_ocr_chars:
            llm[k] = vb.strip_markers(p.read_text(encoding="utf-8"))
    keys = sorted(llm)
    rng = random.Random(20261015)
    good = {k: vb.gram_recall(ocr[k], llm[k])["recall"] for k in keys}
    bad = {}
    for k in keys:
        o = rng.choice([x for x in keys if x != k])
        bad[k] = vb.gram_recall(ocr[k], llm[o])["recall"]
    g, b = sorted(good.values()), sorted(bad.values())
    q = lambda v, p: v[min(int(p * len(v)), len(v) - 1)]  # noqa: E731
    print(f"n = {len(keys)} trang that co OCR doc lap")
    print("recall 4-gram, ban chep DUNG: phan vi 1/5/25/50%:", [round(q(g, p), 3) for p in (.01, .05, .25, .5)])
    print("recall 4-gram, ban chep GAN NHAM: phan vi 50/90/95/99%:", [round(q(b, p), 3) for p in (.5, .9, .95, .99)])
    for thr in (0.2, 0.3, 0.4):
        kg = sum(1 for x in g if x < thr)
        kb = sum(1 for x in b if x < thr)
        print(f"  nguong trang nghi van {thr}: dung bi gan co {kg}/{len(g)} = {kg / len(g):.3f} [Wilson {wilson(kg, len(g))[0]:.3f}; {wilson(kg, len(g))[1]:.3f}]; "
              f"bia bi bat {kb}/{len(b)} = {kb / len(b):.3f} [{wilson(kb, len(b))[0]:.3f}; {wilson(kb, len(b))[1]:.3f}]")

    def batch_flag(rec):
        med = median(rec)
        share = sum(1 for x in rec if x < th.suspect_recall) / len(rec)
        return med < th.min_median_recall or share > th.max_suspect_share
    print(f"\nMo phong (nguong hien hanh: nghi van < {th.suspect_recall}; trung vi >= {th.min_median_recall}; ty le nghi van <= {th.max_suspect_share}; 4000 lo moi dong)")
    print("   N  f_bia | lo SACH bi bao sai | lo co f_bia bi bat (chi kiem cheo) | + xac suat roi trung it nhat 1 trang kiem (c=10 trang kiem)")
    out = []
    for N in (20, 30, 50, 100, 200, 400):
        for f in (0, 12):
            if f > N:
                continue
            hit = 0
            for _ in range(4000):
                idx = rng.sample(range(len(keys)), N)
                rec = [bad[keys[i]] if j < f else good[keys[i]] for j, i in enumerate(idx)]
                hit += batch_flag(rec)
            c = 10
            p_ctl = 1 - comb(N - f, c) / comb(N, c) if f and N >= c else float("nan")
            out.append(dict(N=N, f=f, flag_rate=hit / 4000, p_control=p_ctl))
            print(f"  {N:4d} {f:4d} | {hit / 4000:.3f}" + (f" | p(roi trung it nhat 1 trang kiem) = {p_ctl:.2f}" if f else " (lo sach)"))
    json.dump(dict(n=len(keys), good_q=[q(g, p) for p in (.01, .05, .25, .5)], bad_q=[q(b, p) for p in (.5, .9, .95, .99)], sim=out),
              open(HERE / "calibrate_validate_batch.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
