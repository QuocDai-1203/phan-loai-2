"""bench_throughput.py - Do thong luong (trang/giay) cua src/ocr tren dung 24 tai lieu / 53 trang cua bao cao 02.

24 tai lieu = tap `build_ocr_dataset.py --limit 24` (lay deu moi 14 tai lieu tu kho 336 tai lieu da sap theo relative_path); tap nay co
dung 53 trang. Moi cau hinh chay build_ocr_dataset.py mot lan trong tien trinh con (cache va dau ra o `_scratch/`, KHONG dung vao
data/ocr_v2.jsonl), do thoi gian thuc cua tien trinh con (gom nap mo hinh) va lay mau nvidia-smi moi 1 giay (VRAM toan GPU, % su dung).
GPU DUNG CHUNG: nguoi khac cung dung nen so VRAM la tong toan GPU; ghi ca nen (truoc khi chay) va dinh.

Chay (tu goc repo):
  .venv\\Scripts\\python.exe -X utf8 teams\\team1_ocr\\experiments\\08_throughput\\bench_throughput.py --configs 6x2x16 4x2x16 --out-csv ...
Moi cau hinh la `workers x threads x batch`. Tong thoi gian GPU gioi han boi --budget-min (dung lai khi vuot).
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
SCRATCH = HERE / "_scratch"
PY = REPO / ".venv" / "Scripts" / "python.exe"


def smi() -> tuple[int, int]:
    try:
        o = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,utilization.gpu", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=10).stdout.strip().splitlines()[0]
        m, u = [int(x) for x in o.split(",")]
        return m, u
    except Exception:
        return -1, -1


class Sampler(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.stop = threading.Event()
        self.mem, self.util = [], []

    def run(self):
        while not self.stop.is_set():
            m, u = smi()
            if m >= 0:
                self.mem.append(m)
                self.util.append(u)
            self.stop.wait(1.0)


def run_cfg(workers: int, threads: int, batch: int, device: str, limit: int) -> dict:
    tag = f"w{workers}_t{threads}_b{batch}_{device.replace(':', '')}"
    out = SCRATCH / f"{tag}.jsonl"
    cache = SCRATCH / f"cache_{tag}"
    if cache.exists():
        for f in cache.glob("*"):
            f.unlink()
    cmd = [str(PY), "-X", "utf8", str(REPO / "scripts" / "build_ocr_dataset.py"), "--limit", str(limit), "--device", device,
           "--workers", str(workers), "--threads", str(threads), "--batch", str(batch), "--out", str(out), "--cache", str(cache)]
    base_mem, base_util = smi()
    s = Sampler()
    s.start()
    t0 = time.perf_counter()
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=REPO)
    wall = time.perf_counter() - t0
    s.stop.set()
    s.join(3)
    recs = [json.loads(l) for l in open(out, encoding="utf-8")] if out.exists() else []
    pages = [pg for r in recs for pg in r["pages"]]
    ocr_pages = [pg for pg in pages if pg.get("source") and "ocr" in pg["source"]]
    errs = sum(1 for pg in pages if pg.get("error"))
    return dict(config=tag, workers=workers, threads=threads, batch=batch, device=device, docs=len(recs), pages=len(pages),
                ocr_pages=len(ocr_pages), errors=errs, returncode=p.returncode, wall_s=round(wall, 1),
                pages_per_s=round(len(pages) / wall, 3), ocr_pages_per_s=round(len(ocr_pages) / wall, 3),
                gpu_mem_before_mib=base_mem, gpu_util_before_pct=base_util, gpu_mem_peak_mib=max(s.mem, default=-1),
                gpu_util_mean_pct=round(sum(s.util) / len(s.util), 1) if s.util else -1,
                text_hash=hash_text(pages), finished=datetime.now().isoformat(timespec="seconds"))


def hash_text(pages) -> str:
    import hashlib
    return hashlib.sha1("\x00".join(pg["text"] for pg in pages).encode("utf-8")).hexdigest()[:10]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", nargs="+", default=["6x2x16"], help="workers x threads x batch")
    ap.add_argument("--device", default="cuda:0")
    ap.add_argument("--limit", type=int, default=24)
    ap.add_argument("--budget-min", type=float, default=15.0, help="khong bat dau cau hinh moi neu tong thoi gian da vuot")
    ap.add_argument("--out-csv", type=Path, default=HERE / "throughput.csv")
    a = ap.parse_args()
    SCRATCH.mkdir(exist_ok=True)
    rows, t_all = [], time.perf_counter()
    for c in a.configs:
        if (time.perf_counter() - t_all) / 60 > a.budget_min:
            print(f"Het ngan sach {a.budget_min} phut, bo qua {c}")
            continue
        w, t, b = [int(x) for x in c.lower().split("x")]
        print(f"== {c} ==", flush=True)
        r = run_cfg(w, t, b, a.device, a.limit)
        print(json.dumps(r, ensure_ascii=False), flush=True)
        rows.append(r)
        with open(a.out_csv, "w", encoding="utf-8-sig", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=list(rows[0]))
            wr.writeheader()
            wr.writerows(rows)
    print(f"Tong thoi gian: {(time.perf_counter() - t_all) / 60:.1f} phut")
    return 0


if __name__ == "__main__":
    sys.exit(main())
