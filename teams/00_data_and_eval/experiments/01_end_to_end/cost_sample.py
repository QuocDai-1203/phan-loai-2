r"""Đo chi phí qua LỚP THẬT của pipeline (src/pipeline.py) trên ~20 tệp dev hỗn hợp, mỗi chính sách tách một lần.

    .venv\Scripts\python.exe -X utf8 teams/00_data_and_eval/experiments/01_end_to_end/cost_sample.py [--policies none rule model+merge] [--cache-root DIR]

* OCR KHÔNG chạy lại: giả `ocr` đọc `data/ocr_v2.jsonl` (thời gian OCR không có trong bảng này).
* Tách (mô hình cặp trang thật từ teams/team2_splitting/models/), phân loại (`DocumentClassifier.from_defaults`: luật + TF-IDF artefact + Ollama Qwen3.5-4B),
  gộp theo loại: lớp thật. Trích xuất TẮT (đang do nhóm khác hoàn thiện).
* Mỗi chính sách dùng một thư mục cache LLM RIÊNG, trống => mọi lời gọi LLM là lời gọi THẬT (độ trễ thật, không phải cache). GPU và Ollama DÙNG CHUNG
  với việc khác trong lúc đo: độ trễ chỉ có giá trị tương đối ("GPU dùng chung").
* Artefact TF-IDF / cặp trang đã thấy mọi tệp dev (dùng cho triển khai), nên bảng này chỉ nói về CHI PHÍ và SỰ KHỚP với thí nghiệm, không nói về độ đúng.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e2e_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

QUOTA = {"single_page": 4, "negative": 8, "mixed": 4, "same_other": 2, "same_bb": 2}
SEED = 20261012


def pick_sample(cases):
    rng = np.random.default_rng(SEED)
    out = []
    for g, k in QUOTA.items():
        pool = sorted((c for c in cases if c.group == g and len(c.doc.pages) <= 12), key=lambda c: c.doc_id)     # tệp 93 trang: bỏ (chỉ để gọn)
        idx = rng.choice(len(pool), size=min(k, len(pool)), replace=False)
        out += [pool[i] for i in sorted(idx)]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--policies", nargs="+", default=["none", "rule", "model+merge"])
    ap.add_argument("--cache-root", type=Path, default=None, help="thư mục gốc cache LLM trống (mặc định: thư mục tạm)")
    a = ap.parse_args()
    from src.classification.tfidf_classifier import TfidfClassifier  # noqa: F401
    from src.pipeline import DocumentPipeline
    from src.splitting.learned import load_default_model

    cases, _ = L.load_cases("dev")
    sample = pick_sample(cases)
    root = a.cache_root or Path(tempfile.mkdtemp(prefix="e2e_cost_"))
    exp = pd.read_csv(HERE / "results" / "per_file_dev.csv", dtype={"doc_id": str})
    exp10 = exp[exp.variant == "S10"].set_index("doc_id")
    exp0 = exp[exp.variant == "S0"].set_index("doc_id")
    rows, loads = [], {}
    for pol in a.policies:
        cur = {}
        pipe = DocumentPipeline(ocr=lambda p: cur["doc"], split_policy=pol, run_extraction=False, cache_dir=root / pol.replace("+", "_"),
                                llm_timeout_s=45.0, llm_file_budget_s=90.0)
        t = time.perf_counter()
        if pipe.policy.needs_model:
            pipe._split_model = load_default_model()
        t_model = (time.perf_counter() - t) * 1000
        t = time.perf_counter()
        pipe._get_classifier()
        t_clf = (time.perf_counter() - t) * 1000
        loads[pol] = dict(pair_model_load_ms=round(t_model), classifier_build_ms=round(t_clf))
        for c in sample:
            cur["doc"] = c.doc
            res = pipe.run(Path(c.doc_id + ".pdf"))
            fr = res.file_routing
            rows.append(dict(policy=pol, doc_id=c.doc_id, group=c.group, pages=len(c.doc.pages), slices_before=fr.n_slices_before_merge,
                             slices=fr.n_slices, decision=fr.decision, llm_calls=fr.n_llm_calls, llm_ms=fr.llm_ms,
                             split_ms=res.stage_timings_ms["split"], classify_ms=res.stage_timings_ms["classify"], total_ms=res.total_processing_time_ms,
                             pred=";".join(f"{s.start_page}-{s.end_page}:{k.predicted_category if k.tier != 'human' else '?'}"
                                           for s, k in zip(res.split_result.slices, res.classifications)),
                             reasons="|".join(fr.reasons)))
            print(pol, c.doc_id, c.group, f"{fr.n_slices_before_merge}->{fr.n_slices} lát, LLM {fr.n_llm_calls} ({fr.llm_ms:.0f} ms), classify {res.stage_timings_ms['classify']:.0f} ms",
                  flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(HERE / "results" / "cost_sample_per_file.csv", index=False, encoding="utf-8")        # chứa doc_id: nội bộ
    # sự khớp với thí nghiệm
    agree = {}
    for pol, sub in df.groupby("policy"):
        ref = exp10 if pol == "model+merge" else exp0 if pol == "none" else None
        if ref is None:
            continue
        m_seg = sum(r.pred.split(":")[0] == ref.loc[r.doc_id, "pred_segs"].split(":")[0] and r.slices == ref.loc[r.doc_id, "n_slices"] for r in sub.itertuples())
        m_all = sum(";".join(x.split(":")[0] for x in r.pred.split(";")) == ";".join(x.split(":")[0] for x in ref.loc[r.doc_id, "pred_segs"].split(";")) for r in sub.itertuples())
        m_lab = sum(r.pred == ref.loc[r.doc_id, "pred_segs"].replace("?", "?") for r in sub.itertuples())
        agree[pol] = dict(n=len(sub), same_slice_ranges=int(m_all), same_ranges_and_labels=int(m_lab))
    summ = {}
    for pol, sub in df.groupby("policy"):
        summ[pol] = dict(n_files=len(sub), llm_calls_total=int(sub.llm_calls.sum()), llm_calls_per_file=float(sub.llm_calls.mean()),
                         files_with_llm=int((sub.llm_calls > 0).sum()), llm_ms_median_per_call=(float(sub.llm_ms.sum() / sub.llm_calls.sum()) if sub.llm_calls.sum() else None),
                         split_ms_median=float(sub.split_ms.median()), split_ms_p95=float(sub.split_ms.quantile(0.95)),
                         classify_ms_median=float(sub.classify_ms.median()), classify_ms_p95=float(sub.classify_ms.quantile(0.95)),
                         classify_ms_max=float(sub.classify_ms.max()), total_ms_median=float(sub.total_ms.median()), total_ms_max=float(sub.total_ms.max()),
                         slices_per_file=float(sub.slices.mean()), slices_before_merge_per_file=float(sub.slices_before.mean()))
    (HERE / "results" / "cost_sample.json").write_text(json.dumps(dict(loads=loads, summary=summ, agreement_with_experiment=agree, quota=QUOTA, seed=SEED,
                                                                          note="GPU và Ollama dùng chung trong lúc đo"), ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(dict(loads=loads, summary=summ, agreement=agree), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
