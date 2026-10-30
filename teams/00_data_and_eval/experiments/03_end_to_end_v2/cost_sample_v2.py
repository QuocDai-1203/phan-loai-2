r"""Chi phí của cấu hình đã chọn (model+merge+id, rule_title_tiebreak, trích xuất BẬT, VLM BẬT) qua lớp pipeline THẬT: OCR thật (VietOCR), tách, phân loại,
dựng ảnh, trích xuất, trên ~30 tệp DEV.

    .venv\Scripts\python.exe -X utf8 teams/00_data_and_eval/experiments/03_end_to_end_v2/cost_sample_v2.py [--device auto|cpu|cuda:0]

* Mẫu: 10 tệp thuộc loại có trường hạn (3 CC_TAP_HUAN_VC_HNH, 4 GCN_DDK_BAN_LE_XD, 3 HD_MUA_BAN; <= 12 trang) + 20 tệp ngẫu nhiên theo nhóm cơ cấu (seed cố định).
* Cache LLM/VLM là thư mục tạm TRỐNG => mọi lời gọi là thật. GPU RTX 3060 DÙNG CHUNG (Ollama có client khác); Kev không chạy.
* VRAM: nvidia-smi mỗi 0,5 s trong lúc chạy (tổng bộ nhớ đang dùng của cả GPU, gồm cả tiến trình khác) và mức nền trước khi chạy.
Đầu ra: results/cost_v2.json, results/cost_v2_per_file.csv (chứa doc_id: nội bộ).
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
E2E = HERE.parent / "01_end_to_end"
sys.path.insert(0, str(E2E))
import e2e_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SEED = 20261016
SAMPLES = L.REPO / "docs" / "_chot_samples_phanloaitailieu"
RES = HERE / "results"


def vram_mib() -> int | None:
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10).stdout
        return int(out.strip().splitlines()[0])
    except Exception:  # noqa: BLE001
        return None


class VramSampler(threading.Thread):
    def __init__(self, period=0.5):
        super().__init__(daemon=True)
        self.period, self.samples, self._halt = period, [], threading.Event()

    def run(self):
        while not self._halt.is_set():
            v = vram_mib()
            if v is not None:
                self.samples.append((time.time(), v))
            self._halt.wait(self.period)

    def stop(self):
        self._halt.set()


class Counting:
    """Bọc client LLM/VLM: đếm lời gọi và đo độ trễ từng lời gọi."""

    def __init__(self, inner):
        self.inner, self.ms = inner, []

    def __call__(self, *a, **k):
        t = time.perf_counter()
        try:
            return self.inner(*a, **k)
        finally:
            self.ms.append((time.perf_counter() - t) * 1000)


def pick_files(cm, man):
    rng = np.random.default_rng(SEED)
    units = [r for r in csv.DictReader(open(L.REPO / "teams/team4_extraction/gold/units.csv", encoding="utf-8-sig")) if r["split"] == "DEV" and r["doc_id"] in cm]
    take = {"CC_TAP_HUAN_VC_HNH": 3, "GCN_DDK_BAN_LE_XD": 4, "HD_MUA_BAN": 3}
    pick = []
    for t, k in take.items():
        pool = sorted({u["doc_id"] for u in units if u["doc_type"] == t and len(cm[u["doc_id"]].doc.pages) <= 12})
        pick += [pool[i] for i in sorted(rng.choice(len(pool), size=k, replace=False))]
    quota = {"single_page": 6, "negative": 10, "mixed": 2, "same_other": 1, "same_bb": 1}
    for g, k in quota.items():
        pool = sorted(d for d, c in cm.items() if c.group == g and d not in pick and len(c.doc.pages) <= 30)
        pick += [pool[i] for i in sorted(rng.choice(len(pool), size=min(k, len(pool)), replace=False))]
    return pick


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--device", default="auto")
    a = ap.parse_args()
    from src.extraction import field_llm, field_vlm
    from src.extraction.field_extractor import ExtractConfig, FieldExtractor
    from src.pipeline import DocumentPipeline, resolve_device

    cases, _ = L.load_cases("dev")
    cm = {c.doc_id: c for c in cases}
    man = pd.read_csv(L.REPO / "data" / "manifest.csv", dtype=str, keep_default_na=False).set_index("doc_id")
    pdf_index = {unicodedata.normalize("NFC", p.relative_to(SAMPLES).as_posix()): p for p in SAMPLES.rglob("*.pdf")}
    pick = pick_files(cm, man)
    print(len(pick), "tệp; thiết bị OCR:", resolve_device(a.device), flush=True)

    cache = Path(tempfile.mkdtemp(prefix="cost_v2_cache_"))
    cfg = ExtractConfig(use_llm=True, timeout_s=120.0, cache_dir=cache / "extraction")
    llm_c = Counting(field_llm.ollama_client(cfg.llm_model, cfg.ollama_url, cfg.timeout_s, cfg.cache_dir))
    vlm_c = Counting(field_vlm.ollama_vlm_client(cfg.llm_model, cfg.ollama_url, cfg.timeout_s, cfg.cache_dir))
    pipe = DocumentPipeline(extractor=FieldExtractor(cfg, llm_client=llm_c, vlm_client=vlm_c), split_policy="model+merge+id", title_tiebreak=True,
                            run_extraction=True, use_vlm=True, device=a.device, cache_dir=cache / "llm", llm_timeout_s=45.0, llm_file_budget_s=90.0, extract_timeout_s=120.0)
    baseline = vram_mib()
    samp = VramSampler()
    samp.start()
    rows = []
    t_all = time.perf_counter()
    for i, did in enumerate(pick, 1):
        pdf = pdf_index[unicodedata.normalize("NFC", man.loc[did, "relative_path"])]
        n_l, n_v = len(llm_c.ms), len(vlm_c.ms)
        t0 = time.perf_counter()
        res = pipe.run(pdf)
        wall = (time.perf_counter() - t0) * 1000
        tm, fr = res.stage_timings_ms, res.file_routing
        pages = len(res.ocr_result.pages)
        rows.append(dict(doc_id=did, group=cm[did].group, pages=pages, slices=fr.n_slices, decision=fr.decision, ocr_ms=tm.get("ocr", 0), ocr_model_load_ms=tm.get("ocr_model_load", 0),
                         split_ms=tm["split"], classify_ms=tm["classify"], render_ms=tm.get("render", 0), extract_ms=tm["extract"], total_ms=res.total_processing_time_ms, wall_ms=wall,
                         llm_cls_calls=fr.n_llm_calls, llm_ext_calls=len(llm_c.ms) - n_l, vlm_calls=len(vlm_c.ms) - n_v,
                         extracted=sum(r.extraction_status == "ok" for r in res.routing), n_warnings=len(res.warnings)))
        print(i, {k: (round(v) if isinstance(v, float) else v) for k, v in rows[-1].items() if k != "doc_id"}, flush=True)
    wall_all = time.perf_counter() - t_all
    samp.stop()
    samp.join(timeout=3)
    df = pd.DataFrame(rows)
    df.to_csv(RES / "cost_v2_per_file.csv", index=False, encoding="utf-8")
    q = lambda s: dict(p50=float(s.median()), p95=float(s.quantile(0.95)), mean=float(s.mean()), max=float(s.max()))
    vs = [v for _, v in samp.samples]
    pages = int(df.pages.sum())
    d = df.copy()
    d["ocr_model_excl_ms"] = d.total_ms - d.ocr_model_load_ms
    out = dict(n_files=len(df), n_pages=pages, wall_s_total=wall_all, pages_per_hour_wall=3600 * pages / wall_all,
               by_stage_ms_per_file={k: q(df[k]) for k in ("ocr_ms", "split_ms", "classify_ms", "render_ms", "extract_ms")},
               total_ms_per_file=q(df.total_ms), total_ms_per_page=q(df.total_ms / df.pages), stage_ms_per_page={k: q(df[k] / df.pages) for k in ("ocr_ms", "split_ms", "classify_ms", "render_ms", "extract_ms")},
               stage_share_of_total={k: float(df[k].sum() / df.total_ms.sum()) for k in ("ocr_ms", "split_ms", "classify_ms", "render_ms", "extract_ms")},
               calls_per_file=dict(llm_classify=q(df.llm_cls_calls), llm_extract=q(df.llm_ext_calls), vlm=q(df.vlm_calls),
                                   total_llm_classify=int(df.llm_cls_calls.sum()), total_llm_extract=int(df.llm_ext_calls.sum()), total_vlm=int(df.vlm_calls.sum())),
               call_latency_ms=dict(llm_extract=q(pd.Series(llm_c.ms)) if llm_c.ms else None, vlm=q(pd.Series(vlm_c.ms)) if vlm_c.ms else None),
               ocr_model_load_ms=float(df.ocr_model_load_ms.max()),
               vram_mib=dict(baseline_before=baseline, peak_total=max(vs) if vs else None, median_total=float(np.median(vs)) if vs else None, n_samples=len(vs),
                             peak_minus_baseline=(max(vs) - baseline) if vs and baseline is not None else None,
                             note="tổng bộ nhớ GPU đang dùng (gồm Ollama qwen3.5:4b và client khác); GPU dùng chung, Kev không chạy"),
               by_group=df.groupby("group").agg(files=("doc_id", "count"), pages=("pages", "sum"), total_ms_p50=("total_ms", "median")).reset_index().to_dict("records"),
               files_with_vlm=int((df.vlm_calls > 0).sum()), files_decision=df.decision.value_counts().to_dict())
    (RES / "cost_v2.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float))


if __name__ == "__main__":
    main()
