r"""Độ trễ theo tệp CÓ TRÍCH XUẤT, qua lớp thật của pipeline (chính sách tách mặc định), trên ~14 tệp dev có đơn vị thuộc 4 loại có schema.

    .venv\Scripts\python.exe -X utf8 teams/00_data_and_eval/experiments/01_end_to_end/cost_sample_extract.py

OCR không chạy lại (giả `ocr` đọc ocr_v2.jsonl). Cache LLM (phân loại và trích xuất) là thư mục tạm TRỐNG => mọi lời gọi LLM là thật. GPU/Ollama dùng chung.
Tên tệp thật được truyền vào pipeline (nguồn độc lập của ngày hết hạn).
"""
from __future__ import annotations

import csv
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

PER_TYPE = 3
SEED = 20261012


def main():
    from src.pipeline import DocumentPipeline
    cases, _ = L.load_cases("dev")
    cm = {c.doc_id: c for c in cases}
    man = pd.read_csv(L.REPO / "data" / "manifest.csv", dtype=str, keep_default_na=False).set_index("doc_id")
    units = [r for r in csv.DictReader(open(L.REPO / "teams/team4_extraction/gold/units.csv", encoding="utf-8-sig")) if r["split"] in ("DEV", "EXCLUDED") and r["doc_id"] in cm]
    rng = np.random.default_rng(SEED)
    pick = []
    for t in sorted({u["doc_type"] for u in units}):
        pool = sorted({u["doc_id"] for u in units if u["doc_type"] == t and u["split"] == "DEV" and len(cm[u["doc_id"]].doc.pages) <= 12})
        pick += [pool[i] for i in sorted(rng.choice(len(pool), size=min(PER_TYPE, len(pool)), replace=False))]
    comp = sorted({u["doc_id"] for u in units if u["split"] == "EXCLUDED"})
    pick += [comp[i] for i in sorted(rng.choice(len(comp), size=2, replace=False))]
    root = Path(tempfile.mkdtemp(prefix="e2e_cost_x_"))
    cur = {}
    pipe = DocumentPipeline(ocr=lambda p: cur["doc"], split_policy=None, run_extraction=True, cache_dir=root, llm_timeout_s=45.0, llm_file_budget_s=90.0,
                            extract_timeout_s=120.0)
    from src.splitting.learned import load_default_model
    pipe._split_model = load_default_model()
    pipe._get_classifier()
    pipe._get_extractor()
    rows = []
    for did in pick:
        cur["doc"] = cm[did].doc
        res = pipe.run(Path(man.loc[did, "relative_path"]).name)
        fr = res.file_routing
        rows.append(dict(doc_id=did, group=cm[did].group, pages=len(cm[did].doc.pages), slices=fr.n_slices, decision=fr.decision, n_field_review=fr.n_field_review,
                         llm_calls=fr.n_llm_calls, extracted=sum(r.extraction_status == "ok" for r in res.routing),
                         no_schema=sum(bool(r.extraction_note and r.extraction_note.startswith("no_schema")) for r in res.routing),
                         split_ms=res.stage_timings_ms["split"], classify_ms=res.stage_timings_ms["classify"], extract_ms=res.stage_timings_ms["extract"],
                         total_ms=res.total_processing_time_ms))
        print(rows[-1], flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(HERE / "results" / "cost_sample_extract_per_file.csv", index=False, encoding="utf-8")
    q = lambda s: dict(median=float(s.median()), p95=float(s.quantile(0.95)), max=float(s.max()))
    summ = dict(n_files=len(df), split_ms=q(df.split_ms), classify_ms=q(df.classify_ms), extract_ms=q(df.extract_ms), total_ms=q(df.total_ms),
                files_with_extraction=int((df.extracted > 0).sum()), extract_ms_per_extracted_slice=float(df.extract_ms.sum() / max(1, df.extracted.sum())),
                note="OCR không chạy lại; cache LLM trống => lời gọi thật; GPU/Ollama dùng chung")
    (HERE / "results" / "cost_sample_extract.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summ, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
