"""evaluate_rotation.py - T2: do do chinh xac buoc tu xoay trang cua `data/ocr_v2.jsonl` so voi dap an huong do MO HINH xem anh.

Doc `sample_pages.csv` (make_sheets.py) + `gold_annotations.py` -> ghi `orientation_gold.csv`, `rotation_summary.json`, in bang.
Dap an la do mo hinh (Claude) xem to tiep xuc va ghi, KHONG phai nguoi; xem chu thich trong gold_annotations.py.

Chay:  .venv\\Scripts\\python.exe -X utf8 teams\\team1_ocr\\experiments\\05_rotation\\evaluate_rotation.py
"""
from __future__ import annotations

import csv
import json
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(HERE))
import gold_annotations as ga  # noqa: E402


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def boot_cluster(rows, key, flag, B: int = 4000, seed: int = 1):
    """Bootstrap khoang tin cay 95% cua ty le `flag(row)` khi lay mau lai theo TAI LIEU (cac trang cung tai lieu khong doc lap)."""
    by = defaultdict(list)
    for r in rows:
        by[key(r)].append(1 if flag(r) else 0)
    docs = list(by.values())
    rng = random.Random(seed)
    vals = []
    for _ in range(B):
        s = [rng.choice(docs) for _ in docs]
        n = sum(len(x) for x in s)
        vals.append(sum(sum(x) for x in s) / n if n else float("nan"))
    vals.sort()
    return vals[int(0.025 * B)], vals[int(0.975 * B) - 1]


def fmt(k, n):
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {k / n:.3f} [Wilson {lo:.3f}; {hi:.3f}]" if n else "0/0"


def main() -> int:
    samp = list(csv.DictReader(open(HERE / "sample_pages.csv", encoding="utf-8-sig")))
    recs = {}
    for l in open(REPO / "data" / "ocr_v2.jsonl", encoding="utf-8"):
        j = json.loads(l)
        recs[j["doc_id"]] = j
    rows = []
    for s in samp:
        idx = int(s["idx"])
        gold = ga.gold_orientation(idx)
        blank = ga.is_blank(idx)
        app = int(s["applied_rot"])
        rows.append(dict(idx=idx, doc_id=s["doc_id"], page=int(s["page"]), tap=s["tap"], doc_type=s["doc_type"],
                         gold_deg=gold, applied_deg=app, near_blank_gold=int(blank), n_chars_ocr_v2=int(s["n_chars"]),
                         correct=int(gold == app), source=s["source"]))
    # ban trung byte cua trang bi xoay: thua nhan do cua ban dai dien
    byk = {(r["doc_id"], r["page"]): r for r in rows}
    extra = []
    for did, j in recs.items():
        for pg in j["pages"]:
            fl = pg.get("flags") or []
            dup = [f.split(":")[1] for f in fl if f.startswith("copied_from_exact_duplicate:")]
            rot = [int(f.split("_")[1]) for f in fl if f.startswith("rotated_")]
            if dup and rot and (dup[0], pg["page"]) in byk:
                src = byk[(dup[0], pg["page"])]
                extra.append(dict(idx="", doc_id=did, page=pg["page"], tap="rotated_dup", doc_type=src["doc_type"],
                                  gold_deg=src["gold_deg"], applied_deg=rot[0], near_blank_gold=src["near_blank_gold"],
                                  n_chars_ocr_v2=pg["n_chars"], correct=int(src["gold_deg"] == rot[0]), source=pg["source"]))
    allrows = rows + extra
    with open(HERE / "orientation_gold.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(allrows[0]))
        w.writeheader()
        w.writerows(allrows)

    out = {}
    nb = [r for r in rows if not r["near_blank_gold"]]
    bl = [r for r in rows if r["near_blank_gold"]]
    key = lambda r: r["doc_id"]  # noqa: E731
    out["n_viewed"] = len(rows)
    out["n_blank_gold"] = len(bl)
    out["n_nonblank"] = len(nb)
    print(f"Trang da xem: {len(rows)} (gan trong: {len(bl)}, co chu: {len(nb)}); them {len(extra)} ban trung byte cua trang bi xoay")
    print("Phan bo huong dap an (trang co chu):", dict(Counter(r["gold_deg"] for r in nb)))

    print("\n== Do chinh xac huong tren trang CO CHU (khop huong ocr_v2 da ap) ==")
    for name, sel in [("tat ca trang da xem", nb), ("tap 'bi xoay'", [r for r in nb if r["tap"] == "rotated"]),
                      ("tap 'loai hay nam ngang' (toan bo)", [r for r in nb if r["tap"] == "landscape"]),
                      ("tap 'ngau nhien khong xoay'", [r for r in nb if r["tap"] == "random"])]:
        k = sum(r["correct"] for r in sel)
        bc = boot_cluster(sel, key, lambda r: r["correct"]) if sel else (float("nan"),) * 2
        print(f"  {name}: {fmt(k, len(sel))}  | bootstrap theo tai lieu [{bc[0]:.3f}; {bc[1]:.3f}] ({len({r['doc_id'] for r in sel})} tai lieu)")
        out[name] = dict(k=k, n=len(sel), wilson=wilson(k, len(sel)), boot_doc=bc)

    # --- phan loai loi tren cac trang co chu
    rot = [r for r in nb if r["applied_deg"] != 0]
    unr = [r for r in nb if r["applied_deg"] == 0]
    print("\n== Trang ocr_v2 DA xoay (co chu) ==")
    right = [r for r in rot if r["correct"]]
    wrongdir = [r for r in rot if not r["correct"] and r["gold_deg"] != 0]
    false = [r for r in rot if r["gold_deg"] == 0]
    print(f"  xoay dung huong: {fmt(len(right), len(rot))}")
    print(f"  xoay SAI huong (can xoay nhung chon nguoc 90/270): {len(wrongdir)}  -> doc_id/trang: "
          + ", ".join(f"{r['doc_id']}p{r['page']}({r['applied_deg']} thay vi {r['gold_deg']})" for r in wrongdir))
    print(f"  xoay thua (trang da thang): {len(false)}  -> " + ", ".join(f"{r['doc_id']}p{r['page']}({r['applied_deg']})" for r in false))
    print("\n== Trang ocr_v2 KHONG xoay (co chu) ==")
    missed = [r for r in unr if r["gold_deg"] != 0]
    land_u = [r for r in unr if r["tap"] == "landscape"]
    rnd_u = [r for r in unr if r["tap"] == "random"]
    print(f"  can xoay ma khong xoay (sot): {len(missed)}/{len(unr)} trong {len(land_u)} trang loai-nam-ngang (toan bo) + {len(rnd_u)} trang ngau nhien")
    for r in missed:
        print(f"    sot: {r['doc_id']} p{r['page']} can {r['gold_deg']} ({r['doc_type']}, tap {r['tap']})")
    k_l = sum(1 for r in land_u if r["gold_deg"] != 0)
    k_r = sum(1 for r in rnd_u if r["gold_deg"] != 0)
    print(f"  ty le sot: loai-nam-ngang {fmt(k_l, len(land_u))}; ngau nhien {fmt(k_r, len(rnd_u))}")
    out["missed"] = dict(landscape=(k_l, len(land_u)), random=(k_r, len(rnd_u)))
    out["rotated_summary"] = dict(n=len(rot), right=len(right), wrongdir=len(wrongdir), false=len(false))

    print("\n== Trang gan trong (gold) ==")
    blr = [r for r in bl if r["applied_deg"] != 0]
    print(f"  {len(bl)} trang gan trong da xem; ocr_v2 da XOAY {len(blr)} trang ({len(blr)}/{len(bl)}), "
          f"n_chars cua cac trang bi xoay nham: {sorted(r['n_chars_ocr_v2'] for r in blr)}")
    print(f"  trong do cac trang gan trong thuoc tap 'bi xoay': {sum(1 for r in bl if r['tap'] == 'rotated')}; "
          f"tap khac (nam ngang/ngau nhien) bi xoay: {sum(1 for r in blr if r['tap'] != 'rotated')}")
    out["blank"] = dict(n=len(bl), rotated=len(blr), n_chars_rotated=[r["n_chars_ocr_v2"] for r in blr],
                        n_chars_all=sorted(r["n_chars_ocr_v2"] for r in bl))
    print("  n_chars cua MOI trang gan trong (ocr_v2):", sorted(r["n_chars_ocr_v2"] for r in bl))

    # tat ca trang bi xoay trong ocr_v2 (ke ca ban trung): thong ke tong
    ex_rot = [r for r in extra]
    all_rot_n = sum(1 for r in rows if r["applied_deg"]) + len(ex_rot)
    print(f"\nTong trang co co `rotated_*` trong ocr_v2: {all_rot_n} (duy nhat {sum(1 for r in rows if r['applied_deg'])} + trung byte {len(ex_rot)})")
    wrong_all = [r for r in allrows if r["applied_deg"] and r["gold_deg"] != r["applied_deg"] and not r["near_blank_gold"]]
    blank_rot_all = [r for r in allrows if r["applied_deg"] and r["near_blank_gold"]]
    print(f"  trong do sai (co chu, ke ca ban trung): {len(wrong_all)}; gan trong bi xoay nham (ke ca ban trung): {len(blank_rot_all)}")
    out["all_rotated"] = dict(total=all_rot_n, wrong_text=len(wrong_all), blank=len(blank_rot_all))

    json.dump(out, open(HERE / "rotation_summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=list)
    return 0


if __name__ == "__main__":
    sys.exit(main())
