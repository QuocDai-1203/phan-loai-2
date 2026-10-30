"""classify_errors.py - Xếp lỗi DEV của cấu hình zero-tuning vào loại nguyên nhân bằng đặc trưng tự động (KHÔNG in giá trị trường).

    .venv\\Scripts\\python.exe -X utf8 teams\\team4_extraction\\experiments\\03_unseen_types\\classify_errors.py [--cfg cascade] [--mode lenient] [--regex-tag ""]

Nguyên nhân (thứ tự ưu tiên, mỗi lỗi một nhãn):
  no_rule          trường ngày/mã/số của loại CHƯA có luật nên luật trả null và LLM cũng bỏ trống (chỉ áp cho zero-tuning)
  ink              đáp án ghi chữ viết tay / dưới con dấu (OCR đọc sai gần hết)
  ocr_missing      chuỗi đáp án (đã chuẩn hóa) KHÔNG xuất hiện trong văn bản OCR của đơn vị (OCR mờ/bóng chữ mặt sau/đọc nhầm chữ số)
  truncated        có trong OCR nhưng không nằm trong đoạn văn bản đưa cho LLM (bị cắt do giới hạn 6000 ký tự/cửa sổ)
  extent           kiểu văn bản: LLM đọc đúng chỗ nhưng ranh giới khác đáp án (dài/ngắn hơn, thêm/bớt mã số thuế, địa chỉ); tỉ lệ trùng từ >= 0.5
  spurious_gold_absent   LLM/luật điền giá trị khi đáp án không có (thừa)
  llm_miss         chuỗi đáp án có trong đoạn đưa cho LLM nhưng LLM bỏ trống hoặc trả giá trị khác (đọc lệch, chọn nhầm ngày/số khác)
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter

import common3 as C
import combine as CB
import lib
from eval.field_metrics import compare_field, load_specs
from eval.normalize import find_dates, fold_text, normalize_value
from methods.common import TEXT, passages_text


def alnum(s: str) -> str:
    return re.sub(r"[^0-9a-z]", "", fold_text(s))


def tokens(s: str):
    return set(re.findall(r"[0-9a-z]+", fold_text(s)))


def present(gv: str, typ: str, text: str) -> bool:
    if typ == "date":
        n = normalize_value(gv, "date")
        return bool(n) and n in {iso for iso, _ in find_dates(text)}
    if typ == "text":                 # văn bản dài: coi là "có trong OCR" khi >= 80% từ của đáp án nằm trong văn bản (chịu được khác biệt khoảng trắng/thứ tự)
        gt = tokens(gv)
        return bool(gt) and len(gt & tokens(text)) / len(gt) >= 0.8
    a = alnum(gv)
    return bool(a) and a in alnum(text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cfg", default="cascade")
    ap.add_argument("--mode", default="lenient")
    ap.add_argument("--regex-tag", default="")
    ap.add_argument("--splits", default="DEV")
    a = ap.parse_args()
    specs = load_specs()
    gold, types, split = C.gold_v2()
    units = {u.unit_id: u for u in C.units_v2()}
    us = sorted(u for u in gold if split[u] in a.splits.split(","))
    ftypes = {dt: {x.name: x.type for x in sp} for dt, sp in specs.items()}
    spec_of = {(dt, s.name): s for dt, sp in specs.items() for s in sp}
    rows = {"regex": lib.load_preds("regex", "ocr_v2", a.regex_tag), "llm": lib.load_preds("llm", "ocr_v2")}
    rows["cascade"] = CB.cascade_typed(rows["regex"], rows["llm"], ftypes, us)
    pred = lib.to_pred(rows[a.cfg])
    cats = Counter()
    by_cat_type = Counter()
    listing = []
    for u in us:
        dt = types[u]
        pages = TEXT.pages(units[u], "ocr_v2")
        full = "\n".join(pages[p] for p in sorted(pages))
        prompt = passages_text(pages, 6000)
        for name, g in gold[u].items():
            s = spec_of[(dt, name)]
            if not s.scored or s.is_pii:
                continue
            p = (pred.get(u) or {}).get("fields", {}).get(name)
            res = compare_field(g, p, s, a.mode)
            if res not in ("wrong", "empty", "spurious"):
                continue
            pv = (p or {}).get("value") if isinstance(p, dict) else p
            gv = g.get("value")
            if res == "spurious":
                cat = "spurious_gold_absent"
            elif g.get("ink") in ("handwritten", "under_stamp"):
                cat = "ink"
            elif not present(gv, s.type, full):
                cat = "ocr_missing"
            elif not present(gv, s.type, prompt) and s.type == "text":
                cat = "truncated"
            elif s.type == "text" and pv and len(tokens(gv) & tokens(pv)) / max(1, len(tokens(gv) | tokens(pv))) >= 0.5:
                cat = "extent"
            elif s.type == "text" and not present(gv, "text", prompt):
                cat = "truncated"
            else:
                cat = "llm_miss"
            cats[(cat, res)] += 1
            by_cat_type[(cat, s.type)] += 1
            listing.append({"unit_id": u, "doc_type": dt, "field": name, "type": s.type, "outcome": res, "cause": cat, "ink": g.get("ink")})
    tot = sum(cats.values())
    print(f"{a.cfg}/{a.mode}/{a.splits}: {tot} lỗi")
    for (cat, res), n in sorted(cats.items(), key=lambda kv: -kv[1]):
        print(f"{n:4d}  {cat:22s} {res}")
    print("theo (nguyên nhân, kiểu):", dict(by_cat_type))
    (C.HERE / f"causes_{a.splits.replace(',', '_')}_{a.cfg}.json").write_text(json.dumps(listing, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
