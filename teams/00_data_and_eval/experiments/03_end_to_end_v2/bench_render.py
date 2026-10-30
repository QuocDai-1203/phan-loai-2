r"""Đo thời gian dựng ảnh trang cho VLM: lưu PNG cũ (optimize=True) so với mới (compress_level=1) trên CÙNG các lát cắt, và kiểm điểm ảnh giống hệt.

    .venv\Scripts\python.exe -X utf8 teams/00_data_and_eval/experiments/03_end_to_end_v2/bench_render.py
Mẫu: 40 đơn vị DEV có schema trường hạn (units.csv), các trang theo choose_vlm_pages (tối đa 6). Ảnh chỉ ở thư mục tạm. Đầu ra: results/bench_render.json.
"""
from __future__ import annotations

import csv, json, sys, tempfile, time, unicodedata
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))
from src.extraction import field_vlm  # noqa: E402
from src.pipeline import choose_vlm_pages  # noqa: E402

S = REPO / "docs" / "_chot_samples_phanloaitailieu"
idx = {unicodedata.normalize("NFC", p.relative_to(S).as_posix()): p for p in S.rglob("*.pdf")}
rows = [r for r in csv.DictReader(open(REPO / "teams/team4_extraction/gold/units.csv", encoding="utf-8-sig")) if r["split"] == "DEV" and r["doc_type"] in ("CC_TAP_HUAN_VC_HNH", "GCN_DDK_BAN_LE_XD", "HD_MUA_BAN")]
rows = rows[:: max(1, len(rows) // 40)][:40]
orig_save = Image.Image.save
t_old, t_new, same, n = [], [], 0, 0
for r in rows:
    pdf = idx[unicodedata.normalize("NFC", r["relative_path"])]
    pages = choose_vlm_pages(sorted(int(p) for p in r["pages"].split(";")), {})
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        Image.Image.save = lambda self, fp, *x, **k: orig_save(self, fp, optimize=True)      # cách cũ
        t = time.perf_counter(); old = field_vlm.render_pages_for_vlm(pdf, pages, Path(a)); t_old.append(time.perf_counter() - t)
        Image.Image.save = orig_save
        t = time.perf_counter(); new = field_vlm.render_pages_for_vlm(pdf, pages, Path(b)); t_new.append(time.perf_counter() - t)
        for po, pn in zip(old, new):
            n += 1
            same += int(np.array_equal(np.asarray(Image.open(po).convert("RGB")), np.asarray(Image.open(pn).convert("RGB"))) and field_vlm.image_content_hash(po) == field_vlm.image_content_hash(pn))
q = lambda x: dict(p50=float(np.median(x)), p90=float(np.percentile(x, 90)), mean=float(np.mean(x)))
out = dict(n_slices=len(rows), n_images=n, pixel_identical=same, old_optimize_true_s=q(t_old), new_compress_level1_s=q(t_new), speedup_median=float(np.median(t_old) / np.median(t_new)))
(HERE / "results" / "bench_render.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out, indent=1))
