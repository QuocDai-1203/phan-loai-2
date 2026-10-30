r"""Phân tích độ trễ lời gọi Ollama đã lưu trong các cache đĩa (chỉ ĐỌC): vì sao lần chạy thử pipeline tốn ~195 s để phân loại một tệp ghép?

    .venv\Scripts\python.exe -X utf8 teams/00_data_and_eval/experiments/01_end_to_end/stall_analysis.py

Mỗi bản ghi cache lưu `latency_ms` (đo ở phía máy khách) và `total_duration_ms` (phía máy chủ Ollama); nếu hai số ~ bằng nhau thì thời gian nằm ở MÁY CHỦ
(hàng đợi, nạp lại mô hình, GPU bị tranh), không phải ở mạng/máy khách. `prompt_eval_count` và `eval_count` cho biết kích thước việc phải làm.
"""
import glob
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
CACHES = {
    "pipeline smoke run (cache/llm/ollama)": REPO / "cache" / "llm" / "ollama",
    "thí nghiệm 02 (Team 3, 4367 lời gọi)": REPO / "teams/team3_classification/experiments/02_llm_and_cascade/_cache/ollama",
    "thí nghiệm 05 (Team 2, num_ctx 32768)": REPO / "teams/team2_splitting/experiments/05_llm_zero_shot/_cache",
    "thí nghiệm này (01_end_to_end)": HERE / "_cache" / "ollama",
}
BUCKETS = [(0, 3000, "< 3 s (mô hình đang nạp, GPU rảnh)"), (3000, 15000, "3-15 s (GPU bị tranh)"), (15000, 40000, "15-40 s (~ một lần nạp lại mô hình)"),
           (40000, 200000, "40-200 s (xếp hàng sau việc khác)"), (200000, 1e12, "> 200 s")]

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    out = {}
    for name, root in CACHES.items():
        recs = []
        for f in glob.glob(str(root / "**" / "*.json"), recursive=True):
            try:
                r = json.loads(Path(f).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if "latency_ms" in r:
                recs.append((os.path.getmtime(f), r))
        if not recs:
            continue
        ok = [r for _, r in recs if not r.get("error") and r.get("content") is not None]
        err = [r for _, r in recs if r.get("error")]
        lat = np.array([r["latency_ms"] for r in ok])
        srv = np.array([r.get("total_duration_ms") or np.nan for r in ok])
        b = Counter()
        for x in lat:
            for lo, hi, lab in BUCKETS:
                if lo <= x < hi:
                    b[lab] += 1
        slow = [r for r in ok if r["latency_ms"] >= 15000]
        out[name] = dict(
            n_ok=len(ok), n_error=len(err), errors=sorted({e["error"].split(":")[0] for e in err}),
            error_latency_s=sorted(round(e["latency_ms"] / 1000) for e in err), median_ms=float(np.median(lat)), p90_ms=float(np.percentile(lat, 90)),
            p99_ms=float(np.percentile(lat, 99)), max_ms=float(lat.max()), buckets={lab: b.get(lab, 0) for _, _, lab in BUCKETS},
            slow_calls_client_minus_server_ms_median=float(np.nanmedian([r["latency_ms"] - (r.get("total_duration_ms") or np.nan) for r in slow])) if slow else None,
            slow_calls_prompt_tokens_median=float(np.median([r.get("prompt_eval_count") or 0 for r in slow])) if slow else None,
            slow_calls_output_tokens_median=float(np.median([r.get("eval_count") or 0 for r in slow])) if slow else None,
            warm_calls_prompt_tokens_median=float(np.median([r.get("prompt_eval_count") or 0 for r in ok if r["latency_ms"] < 3000])) if (lat < 3000).any() else None)
    # chuỗi liên tiếp ~20 s (mỗi lời gọi một lần nạp lại?) trong cache 02, theo thời gian
    recs = []
    for f in glob.glob(str(CACHES["thí nghiệm 02 (Team 3, 4367 lời gọi)"] / "**" / "*.json"), recursive=True):
        try:
            r = json.loads(Path(f).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if r.get("content") is not None and not r.get("error"):
            recs.append((os.path.getmtime(f), r["latency_ms"]))
    recs.sort()
    runs, cur = [], []
    for _, l in recs:
        if 15000 <= l < 40000:
            cur.append(l)
        else:
            if len(cur) >= 5:
                runs.append(cur)
            cur = []
    if len(cur) >= 5:
        runs.append(cur)
    out["chuỗi liên tiếp 15-40 s (>= 5 lời gọi) trong cache 02"] = [dict(n=len(r), median_s=round(float(np.median(r)) / 1000, 1), min_s=round(min(r) / 1000, 1), max_s=round(max(r) / 1000, 1)) for r in runs]
    (HERE / "results" / "stall_latency.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
