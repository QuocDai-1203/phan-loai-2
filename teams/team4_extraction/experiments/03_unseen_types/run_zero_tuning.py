"""run_zero_tuning.py - Chạy KHÔNG chỉnh gì các phương pháp giai đoạn 2 trên 84 đơn vị silver v2 (17 loại mới).

    .venv\\Scripts\\python.exe -X utf8 teams\\team4_extraction\\experiments\\03_unseen_types\\run_zero_tuning.py [--configs regex@ocr_v2,filename,llm@ocr_v2,vlm]

Tuần tự, có cache đĩa (dự đoán ở `_cache/preds/`, lời gọi Ollama ở `teams/team4_extraction/_cache/ollama/`), chạy lại thì dùng tiếp.
Cấu hình đúng như đã đóng băng ở giai đoạn 2: luật `src/extraction/field_rules.py` (chỉ có luật cho 4 loại cũ -> loại mới trả toàn null),
LLM `qwen3.5:4b` prompt v1 trên `ocr_v2`, VLM cùng mô hình trên 4 ảnh đầu (`gold/v2/pages_v2`). Ghi tài nguyên vào `_cache/resources.jsonl`.
"""

from __future__ import annotations

import argparse
import json
import time

import common3 as C
import lib
from run_methods import gpu_used_mib, ollama_vram  # noqa: E402  (02_methods/run_methods.py)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", default="regex@ocr_v2,filename,llm@ocr_v2,vlm")
    ap.add_argument("--tag", default="")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    units = C.units_v2()
    print(f"{len(units)} đơn vị (DEV/TEST/EXCLUDED = " + "/".join(str(sum(u.split == s for u in units)) for s in C.SPLITS) + ")", flush=True)
    res_path = C.CACHE / "resources.jsonl"
    res_path.parent.mkdir(parents=True, exist_ok=True)
    for cfg in a.configs.split(","):
        method, _, source = cfg.partition("@")
        kw = {"pages_dir": C.PAGES_V2} if method == "vlm" else {}
        before, t0 = gpu_used_mib(), time.time()
        lib.run_config(method, source or "ocr_v2", units, tag=a.tag, force=a.force, **kw)
        rec = {"config": lib.cfg_name(method, source or "ocr_v2"), "wall_s": round(time.time() - t0, 1), "gpu_used_mib_before": before,
               "gpu_used_mib_after": gpu_used_mib(), "ollama_ps": ollama_vram()}
        with open(res_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
