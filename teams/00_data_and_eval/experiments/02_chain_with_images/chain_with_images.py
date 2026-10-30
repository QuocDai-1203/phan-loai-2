r"""Chuỗi tới ngày hết hạn trên DEV (82 đơn vị như 01_end_to_end/chain_extraction.py), SO SÁNH không ảnh trang và có ảnh trang (VLM).

    .venv\Scripts\python.exe -X utf8 teams/00_data_and_eval/experiments/02_chain_with_images/chain_with_images.py [--limit N]

* Chuỗi (tách S10 -> cascade -> lát cắt trùng nhiều trang nhất -> loại dự đoán) dựng GIỐNG HỆT chain_extraction.py; chỉ phần trích xuất khác:
  - `old`: `DocumentPipeline.extract_fields(slice, loại, filename)` không ảnh (cấu hình sản xuất cũ; lời gọi LLM văn bản qua cache đĩa của nhóm 4);
  - `new`: cùng lời gọi nhưng có `page_images` do chính hàm của pipeline dựng (`choose_vlm_pages` + `render_pages_for_vlm`, PyMuPDF 200 dpi, thư mục tạm, xóa ngay).
* Lời gọi VLM qua kho kết quả riêng (_cache/vlm_store.json, ghi độ trễ của lần gọi thật đầu tiên; GPU dùng chung); có thử lại 1 lần khi LlmError. Ảnh giấy tờ chỉ ở thư mục tạm.
* KHÔNG chạy TEST. Đáp án = fields_silver_v1.jsonl (máy làm, chưa người kiểm).
Đầu ra: results/chain_with_images.json, results/chain_with_images_per_field.csv (chứa doc_id: chỉ dùng nội bộ).
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
E2E = HERE.parent / "01_end_to_end"
sys.path.insert(0, str(E2E))
import chain_extraction as CE  # noqa: E402
import e2e_lib as L  # noqa: E402
from run import SELECTION, variant_of  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RES = HERE / "results"
SAMPLES = L.REPO / "docs" / "_chot_samples_phanloaitailieu"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cache-dir", type=Path, default=CE.TEAM4 / "_cache" / "ollama")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    RES.mkdir(exist_ok=True)
    from harness import load_benchmark, load_or_make_splits
    from src.extraction import field_vlm
    from src.extraction.field_extractor import ExtractConfig, FieldExtractor
    from src.extraction.field_llm import LlmError
    from src.extraction.schemas import SUPPORTED_TYPES, field_specs
    from src.pipeline import DocumentPipeline
    from src.splitting.type_merge import load_one_sheet_types, merge_same_type

    bench = load_benchmark(L.REPO / "data" / "labels_v2.csv")
    splits = load_or_make_splits(bench)
    one_sheet = load_one_sheet_types()
    sel = json.loads(SELECTION.read_text(encoding="utf-8"))
    v = variant_of(dict(sel["specs"][sel["chosen"]], name="CHOSEN"))
    cases, _ = L.load_cases("dev")
    cm = {c.doc_id: c for c in cases}
    scores = json.loads((E2E / "results" / "pair_scores_dev.json").read_text(encoding="utf-8"))
    clfs = L.Classifiers(bench, splits, mode="readonly")
    man = pd.read_csv(L.REPO / "data" / "manifest.csv", dtype=str, keep_default_na=False).set_index("doc_id")
    silver = CE.load_silver()
    pdf_index = {unicodedata.normalize("NFC", p.relative_to(SAMPLES).as_posix()): p for p in SAMPLES.rglob("*.pdf")}

    raw_vlm = field_vlm.ollama_vlm_client(cache_dir=None, timeout=180.0)
    vlm_log = []

    store_path = HERE / "_cache" / "vlm_store.json"            # _cache/ nằm trong .gitignore (chứa giá trị trường đọc từ giấy tờ)
    store_path.parent.mkdir(exist_ok=True)
    store = json.loads(store_path.read_text(encoding="utf-8")) if store_path.exists() else {}

    def timed_vlm(system, user, schema, images):
        """Kho kết quả riêng để chạy lại/tiếp tục được; độ trễ ghi là độ trễ của lần gọi THẬT đầu tiên (không phải lần đọc kho)."""
        import hashlib
        key = hashlib.sha256((user + json.dumps(schema, sort_keys=True) + "".join(hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in images)).encode()).hexdigest()
        if key in store:
            vlm_log.append(store[key]["ms"])
            return store[key]["data"]
        for attempt in (1,):
            t0 = time.perf_counter()
            try:
                out = raw_vlm(system, user, schema, images)
                ms = (time.perf_counter() - t0) * 1000
                store[key] = {"data": out, "ms": ms}
                store_path.write_text(json.dumps(store, ensure_ascii=False), encoding="utf-8")
                vlm_log.append(ms)
                return out
            except LlmError:
                if attempt == 1:
                    raise
    ex_old = FieldExtractor(ExtractConfig(cache_dir=a.cache_dir, timeout_s=300.0))
    ex_new = FieldExtractor(ExtractConfig(cache_dir=a.cache_dir, timeout_s=300.0), vlm_client=timed_vlm)
    pipe_old = DocumentPipeline(extractor=ex_old, use_vlm=False)
    pipe_new = DocumentPipeline(extractor=ex_new, use_vlm=True)

    units = [u for u in CE.load_units() if u["doc_id"] in cm and u["doc_type"] in SUPPORTED_TYPES and u["unit_id"] in silver]
    if a.limit:
        units = units[: a.limit]
    print(f"{len(units)} đơn vị dev có schema")

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

    rows, unit_rows = [], []
    t_start = time.time()
    for i, u in enumerate(units, 1):
        did, true_t = u["doc_id"], u["doc_type"]
        pages = sorted(int(p) for p in u["pages"].split(";"))
        rel = man.loc[did, "relative_path"]
        fname = Path(rel).name
        exp_fields = [f["name"] for f in field_specs(true_t) if f.get("is_expiry")]
        refs = CE.ref_dates(silver[u["unit_id"]], exp_fields)
        split, cls = chain_for(did)
        best = max(range(len(split.slices)), key=lambda j: len(set(range(split.slices[j].start_page, split.slices[j].end_page + 1)) & set(pages)))
        sl_, pred_t = split.slices[best], cls[best].label
        if not (pred_t and not sl_.ocr_errors and pred_t in SUPPORTED_TYPES):
            continue
        t0 = time.perf_counter()
        old = pipe_old.extract_fields(sl_, pred_t, filename=fname)
        old_ms = (time.perf_counter() - t0) * 1000
        pdf = pdf_index[unicodedata.normalize("NFC", rel)]
        render_ms, n_img, new_ms, vlm_ms = 0.0, 0, 0.0, None
        with tempfile.TemporaryDirectory(prefix="chain_img_") as tmp:
            imgs = None
            if pipe_new._wants_page_images(pred_t):
                t0 = time.perf_counter()
                imgs = pipe_new._render_slice_images(pdf, sl_, Path(tmp)) or None
                render_ms = (time.perf_counter() - t0) * 1000
                n_img = len(imgs or [])
            n_calls = len(vlm_log)
            t0 = time.perf_counter()
            new = pipe_new.extract_fields(sl_, pred_t, filename=fname, **({"page_images": imgs} if imgs else {}))
            new_ms = (time.perf_counter() - t0) * 1000
            vlm_ms = vlm_log[-1] if len(vlm_log) > n_calls else None
        unit_rows.append(dict(unit_id=u["unit_id"], true_type=true_t, pred_type=pred_t, n_images=n_img, render_ms=render_ms, old_extract_ms=old_ms,
                              new_extract_ms=new_ms, vlm_ms=vlm_ms, new_status=new.status, old_status=old.status))
        for n, ref in refs.items():
            oa, na = old.entity_dict.get(n), new.entity_dict.get(n)
            rows.append(dict(unit_id=u["unit_id"], doc_id=did, true_type=true_t, pred_type=pred_t, field=n, ref=ref, old_acc=oa, new_acc=na,
                             old_out=CE.outcome(oa, ref), new_out=CE.outcome(na, ref),
                             old_state=(old.entity_dict.get("_expiry") or {}).get(n), new_state=(new.entity_dict.get("_expiry") or {}).get(n),
                             new_sugg=(new.entity_dict.get("_expiry_suggestion") or {}).get(n), new_status=new.status))
        if i % 10 == 0 or i == len(units):
            print(f"  {i}/{len(units)} đơn vị ({time.time() - t_start:.0f} s)", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(RES / "chain_with_images_per_field.csv", index=False, encoding="utf-8")
    n_failed_units = int((pd.DataFrame(unit_rows).new_status != "ok").sum())
    n_failed_fields = int((df.new_status != "ok").sum())
    df = df[df.new_status == "ok"].copy()          # lần gọi VLM hỏng (GPU dùng chung kẹt/hết giờ): bỏ khỏi so sánh ghép cặp, báo riêng; chạy lại script sẽ lấp từ kho
    pd.DataFrame(unit_rows).to_csv(RES / "chain_with_images_per_unit.csv", index=False, encoding="utf-8")

    from scipy.stats import beta

    def cp_upper(k, n, conf=0.95):
        return 1.0 if k == n else float(beta.ppf(conf, k + 1, n - k)) if n else float("nan")

    def summ(col):
        c, w, e = (int((df[col] == s).sum()) for s in ("correct", "wrong", "empty"))
        n = len(df)
        return dict(n=n, correct=c, wrong=w, empty=e, auto_share=(c + w) / n, correct_share=c / n, wrong_upper95=cp_upper(w, c + w) if c + w else None)

    # --- bootstrap ghép cặp, lấy mẫu lại theo ĐƠN VỊ (các trường cùng đơn vị tương quan)
    rng = np.random.default_rng(20261015)
    uids = df.unit_id.unique()
    by = {k: g for k, g in df.groupby("unit_id")}
    stats = {k: (int((g.old_out == "correct").sum()), int((g.new_out == "correct").sum()), int((g.old_out == "wrong").sum()),
                 int((g.new_out == "wrong").sum()), len(g)) for k, g in by.items()}
    S = np.array([stats[k] for k in uids])
    diffs, dw = [], []
    for _ in range(5000):
        idx = rng.integers(0, len(uids), len(uids))
        s = S[idx].sum(axis=0)
        diffs.append((s[1] - s[0]) / s[4])
        dw.append((s[3] - s[2]) / s[4])
    ci = lambda x: [float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))]
    flips = dict(gained=int(((df.old_out != "correct") & (df.new_out == "correct")).sum()), lost=int(((df.old_out == "correct") & (df.new_out != "correct")).sum()),
                 wrong_to_correct=int(((df.old_out == "wrong") & (df.new_out == "correct")).sum()), became_wrong=int(((df.old_out != "wrong") & (df.new_out == "wrong")).sum()))
    U = pd.DataFrame(unit_rows)
    U = U[U.new_status == "ok"]
    vl = U.vlm_ms.dropna()
    out = dict(n_units=len(U), n_fields=len(df), vlm_failed_units_excluded=n_failed_units, vlm_failed_fields_excluded=n_failed_fields, old=summ("old_out"), new=summ("new_out"), flips=flips,
               paired_bootstrap_by_unit=dict(B=5000, correct_share_diff=float(np.mean(diffs)), correct_share_diff_ci95=ci(diffs),
                                             wrong_share_diff=float(np.mean(dw)), wrong_share_diff_ci95=ci(dw)),
               by_type={t: dict(n=len(g), old_correct=int((g.old_out == "correct").sum()), new_correct=int((g.new_out == "correct").sum()),
                                old_wrong=int((g.old_out == "wrong").sum()), new_wrong=int((g.new_out == "wrong").sum())) for t, g in df.groupby("true_type")},
               latency_ms=dict(note="GPU RTX 3060 dùng chung; VLM không cache; num_ctx 12288 khác client khác (32768) nên có thể nạp lại mô hình",
                               vlm_calls=int(len(vl)), vlm_median=float(vl.median()) if len(vl) else None, vlm_p90=float(vl.quantile(0.9)) if len(vl) else None,
                               vlm_max=float(vl.max()) if len(vl) else None, render_median=float(U[U.n_images > 0].render_ms.median()),
                               render_p90=float(U[U.n_images > 0].render_ms.quantile(0.9)), images_median=float(U[U.n_images > 0].n_images.median()),
                               new_extract_median_all_units=float(U.new_extract_ms.median()), units_with_vlm_call=int((U.n_images > 0).sum()),
                               new_status_counts=U.new_status.value_counts().to_dict()))
    (RES / "chain_with_images.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
