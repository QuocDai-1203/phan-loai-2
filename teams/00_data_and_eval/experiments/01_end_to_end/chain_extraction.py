r"""Chuỗi đầy đủ trên các đơn vị DEV có schema trích xuất: tách (S10) -> loại cascade -> trích xuất theo loại ĐÃ DỰ ĐOÁN -> trường hạn.

    .venv\Scripts\python.exe -X utf8 teams/00_data_and_eval/experiments/01_end_to_end/chain_extraction.py [--cache-dir DIR]

* Đơn vị = `teams/team4_extraction/gold/units.csv` (DEV + EXCLUDED = phạm vi dev của thí nghiệm này; KHÔNG đụng TEST). Đáp án = `gold/fields_silver_v1.jsonl`
  (silver do LLM đọc ảnh, Opus phân xử 58 mục, KHÔNG có người kiểm).
* Tách và phân loại: dự đoán CROSS-FITTED như thí nghiệm chính (cặp trang theo nhóm biểu mẫu; TF-IDF theo fold DEV; LLM phân loại lấy từ cache đã có).
* Trích xuất: `src.extraction.field_extractor.FieldExtractor` (cấu hình sản xuất: luật + LLM cục bộ ghép theo kiểu, hạn chỉ tự nhận khi `any-model=filename`,
  PII tắt, không ảnh trang), tên tệp thật làm nguồn độc lập. Lời gọi LLM TUẦN TỰ qua cache đĩa của nhóm trích xuất (mặc định teams/team4_extraction/_cache/ollama).
* So với CÔ LẬP: cùng bộ trích xuất, nhưng đưa đúng các trang của đơn vị và đúng loại thật (giả định của thí nghiệm trích xuất).
* Luật/prompt của bộ trích xuất đã được CHỈNH trên chính các đơn vị DEV này: số ở đây lạc quan về phần trích xuất.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e2e_lib as L  # noqa: E402
from run import SELECTION, variant_of  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TEAM4 = L.REPO / "teams" / "team4_extraction"
RES = HERE / "results"


def load_units():
    rows = list(csv.DictReader(open(TEAM4 / "gold" / "units.csv", encoding="utf-8-sig")))
    return [r for r in rows if r["split"] in ("DEV", "EXCLUDED")]


def load_silver():
    out = {}
    for line in open(TEAM4 / "gold" / "fields_silver_v1.jsonl", encoding="utf-8"):
        m = json.loads(line)
        out[m["unit_id"]] = m
    return out


def ref_dates(silver_unit, expiry_fields):
    """{trường hạn: ngày ISO đáp án} chỉ cho trường có ngày cụ thể (bỏ not_present / illegible / chỉ-ghi-thời-hạn)."""
    out = {}
    for n in expiry_fields:
        f = silver_unit["fields"].get(n)
        if not f or f.get("status") != "ok" or not f.get("normalized"):
            continue
        if f.get("note") and "chi_ghi_thoi_han" in str(f["note"]):
            continue
        out[n] = f["normalized"]
    return out


def make_slice(doc, pages, sid="u"):
    from src.common.contracts import DocumentSlice
    ps = [p for p in doc.pages if p.page_number in pages]
    return DocumentSlice(slice_id=sid, start_page=min(pages), end_page=max(pages), page_count=len(ps), combined_text="\n".join(p.full_text for p in ps), pages=ps)


def outcome(acc, ref):
    if acc is None:
        return "empty"
    return "correct" if acc == ref else "wrong"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cache-dir", type=Path, default=TEAM4 / "_cache" / "ollama")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    from harness import load_benchmark, load_or_make_splits
    from src.extraction.field_extractor import ExtractConfig, FieldExtractor
    from src.extraction.schemas import SUPPORTED_TYPES, field_specs
    from src.splitting.type_merge import load_one_sheet_types

    bench = load_benchmark(L.REPO / "data" / "labels_v2.csv")
    splits = load_or_make_splits(bench)
    one_sheet = load_one_sheet_types()
    sel = json.loads(SELECTION.read_text(encoding="utf-8"))
    v = variant_of(dict(sel["specs"][sel["chosen"]], name="CHOSEN"))
    cases, _ = L.load_cases("dev")
    cm = {c.doc_id: c for c in cases}
    scores = json.loads((RES / "pair_scores_dev.json").read_text(encoding="utf-8"))
    clfs = L.Classifiers(bench, splits, mode="readonly")
    man = pd.read_csv(L.REPO / "data" / "manifest.csv", dtype=str, keep_default_na=False).set_index("doc_id")
    silver = load_silver()
    ex = FieldExtractor(ExtractConfig(cache_dir=a.cache_dir, timeout_s=300.0))
    units = [u for u in load_units() if u["doc_id"] in cm and u["doc_type"] in SUPPORTED_TYPES and u["unit_id"] in silver]
    if a.limit:
        units = units[: a.limit]
    print(f"{len(units)} đơn vị dev có schema; phương án tách = {sel['chosen']} {sel['specs'][sel['chosen']]}")

    from src.splitting.type_merge import merge_same_type
    file_cache = {}

    def chain_for(doc_id):
        if doc_id not in file_cache:
            c = cm[doc_id]
            split = L.base_split(c.doc, v, scores.get(doc_id))
            cls = [clfs.classify(c, s) for s in split.slices]
            if v.merge and len(split.slices) > 1:
                split, groups = merge_same_type(split, [x.label or None for x in cls], one_sheet, v.keep)
                cls = [cls[g[0]] for g in groups]
            file_cache[doc_id] = (split, cls)
        return file_cache[doc_id]

    rows = []
    t_start = time.time()
    for i, u in enumerate(units, 1):
        did, true_t = u["doc_id"], u["doc_type"]
        pages = sorted(int(p) for p in u["pages"].split(";"))
        c = cm[did]
        fname = Path(man.loc[did, "relative_path"]).name
        exp_fields = [f["name"] for f in field_specs(true_t) if f.get("is_expiry")]
        refs = ref_dates(silver[u["unit_id"]], exp_fields)
        # --- cô lập: đúng trang đơn vị, đúng loại thật
        t0 = time.perf_counter()
        iso = ex.extract(make_slice(c.doc, pages), true_t, filename=fname)
        iso_ms = (time.perf_counter() - t0) * 1000
        # --- chuỗi: lát cắt trùng nhiều trang nhất
        split, cls = chain_for(did)
        best, ov_best = None, 0
        for j, s in enumerate(split.slices):
            ov = len(set(range(s.start_page, s.end_page + 1)) & set(pages))
            if ov > ov_best:
                best, ov_best = j, ov
        sl_, cl_ = split.slices[best], cls[best]
        pred_t = cl_.label
        exact_range = (sl_.start_page, sl_.end_page) == (pages[0], pages[-1])
        auto = bool(pred_t) and not sl_.ocr_errors
        ch = None
        ch_ms = 0.0
        if auto and pred_t in SUPPORTED_TYPES:
            t0 = time.perf_counter()
            ch = ex.extract(sl_, pred_t, filename=fname)
            ch_ms = (time.perf_counter() - t0) * 1000
        for n, ref in refs.items():
            ia = iso.entity_dict.get(n)
            ca = ch.entity_dict.get(n) if (ch is not None and ch.entity_dict) else None
            ie = (iso.entity_dict.get("_expiry") or {}).get(n)
            ce = ((ch.entity_dict.get("_expiry") or {}).get(n) if ch is not None and ch.entity_dict else None)
            sug_i = (iso.entity_dict.get("_expiry_suggestion") or {}).get(n)
            sug_c = ((ch.entity_dict.get("_expiry_suggestion") or {}).get(n) if ch is not None and ch.entity_dict else None)
            rows.append(dict(unit_id=u["unit_id"], doc_id=did, split=u["split"], true_type=true_t, group=c.group, field=n, ref=ref,
                             pred_type=pred_t or "?", type_right=int(pred_t == true_t), exact_range=int(exact_range), n_slices=len(split.slices),
                             extracted_in_chain=int(ch is not None), chain_status=(ch.status if ch is not None else "not_run"),
                             iso_acc=ia, chain_acc=ca, iso_out=outcome(ia, ref), chain_out=outcome(ca, ref), iso_state=ie, chain_state=ce,
                             iso_sugg_ok=int(sug_i == ref) if ia is None and sug_i else -1, chain_sugg_ok=int(sug_c == ref) if ca is None and sug_c else -1,
                             iso_ms=iso_ms, chain_ms=ch_ms))
        if i % 10 == 0 or i == len(units):
            print(f"  {i}/{len(units)} đơn vị ({time.time() - t_start:.0f} s)", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(RES / "chain_extraction_per_field.csv", index=False, encoding="utf-8")        # chứa doc_id: nội bộ
    uni = pd.DataFrame([dict(unit_id=u["unit_id"], true_type=u["doc_type"], split=u["split"]) for u in units])
    # --- tổng hợp
    per_unit = df.drop_duplicates("unit_id")
    # đơn vị đủ cả các đơn vị KHÔNG có trường hạn có ngày (vẫn tính loại đúng): lấy từ vòng riêng
    out = {}
    type_rows = []
    for u in units:
        did = u["doc_id"]
        pages = sorted(int(p) for p in u["pages"].split(";"))
        split, cls = chain_for(did)
        best = max(range(len(split.slices)), key=lambda j: len(set(range(split.slices[j].start_page, split.slices[j].end_page + 1)) & set(pages)))
        s, k = split.slices[best], cls[best]
        type_rows.append(dict(unit_id=u["unit_id"], true_type=u["doc_type"], split=u["split"], group=cm[did].group, type_right=int(k.label == u["doc_type"]),
                              abstain=int(not k.label), exact_range=int((s.start_page, s.end_page) == (pages[0], pages[-1])), n_slices=len(split.slices),
                              pred=k.label or "?"))
    T = pd.DataFrame(type_rows)
    T.to_csv(RES / "chain_extraction_per_unit.csv", index=False, encoding="utf-8")
    from scipy.stats import beta

    def ub(k, n, conf=0.95):
        return 1.0 if k == n else float(beta.ppf(conf, k + 1, n - k)) if n else float("nan")

    def summ(col_out, col_state):
        n = len(df)
        c = int((df[col_out] == "correct").sum())
        w = int((df[col_out] == "wrong").sum())
        e = int((df[col_out] == "empty").sum())
        return dict(n=n, correct=c, wrong=w, empty=e, auto_accepted=c + w, auto_share=(c + w) / n if n else None,
                    wrong_among_auto=(w / (c + w) if c + w else None), wrong_upper95=ub(w, c + w) if c + w else None,
                    suggestions_right=int((df["chain_sugg_ok" if col_out == "chain_out" else "iso_sugg_ok"] == 1).sum()),
                    suggestions_given=int((df["chain_sugg_ok" if col_out == "chain_out" else "iso_sugg_ok"] >= 0).sum()))

    out["units"] = dict(n=len(T), by_type=dict(Counter(T.true_type)), type_right=int(T.type_right.sum()), abstain=int(T.abstain.sum()),
                        exact_range=int(T.exact_range.sum()), n_with_expiry_ref=int(per_unit.shape[0]),
                        type_right_by_group=T.groupby("group").type_right.agg(["sum", "count"]).to_dict("index"),
                        type_right_by_type=T.groupby("true_type").type_right.agg(["sum", "count"]).to_dict("index"))
    out["isolated"] = summ("iso_out", "iso_state")
    out["chain"] = summ("chain_out", "chain_state")
    sub = df[df.type_right == 1]
    out["chain_given_type_right"] = dict(n=len(sub), correct=int((sub.chain_out == "correct").sum()), wrong=int((sub.chain_out == "wrong").sum()),
                                         empty=int((sub.chain_out == "empty").sum()))
    out["chain_not_extracted"] = dict(n_fields=int((df.extracted_in_chain == 0).sum()), by_reason=dict(Counter(df[df.extracted_in_chain == 0].pred_type)))
    out["latency_ms_cached_or_live"] = dict(iso_median=float(df.iso_ms.median()), chain_median=float(df[df.extracted_in_chain == 1].chain_ms.median()),
                                            note="độ trễ khi lấy từ cache đĩa là nhỏ; số độ trễ thật xem cost_sample.json (--extract)")
    (RES / "chain_extraction.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
