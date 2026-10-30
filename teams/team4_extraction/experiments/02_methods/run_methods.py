"""run_methods.py - Chạy các cấu hình phương pháp trên một tập đơn vị và ghi dự đoán vào `_cache/preds/` (Nhóm 4, T4).

    .venv\\Scripts\\python.exe -X utf8 teams\\team4_extraction\\experiments\\02_methods\\run_methods.py --split DEV --configs regex@ocr_v2,llm@ocr_v2,vlm
    .venv\\Scripts\\python.exe -X utf8 ... --split TEST --final-test --configs ...      # CHỈ sau khi đã đóng băng cấu hình (dev_selection.json)

TEST bị chặn: cần `--final-test` VÀ tệp `dev_selection.json` đã tồn tại (đóng băng trước). Gọi Ollama tuần tự, có cache đĩa.
Cấu hình: `phương_pháp@nguồn` với phương pháp thuộc regex|filename|gliner|llm|vlm, nguồn thuộc ocr_v2|ocr_llm_haiku|text_layer (filename, vlm: không có nguồn).
`--tag` đặt hậu tố tệp cho biến thể prompt; `--prompt-variant` chọn biến thể prompt LLM/VLM (xem methods/local_llm_json.py::PROMPT_VARIANTS).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from lib import PRED_DIR, cfg_name, run_config  # noqa: E402
from methods.common import load_units  # noqa: E402


def gpu_used_mib() -> int | None:
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=10)
        return int(out.stdout.strip().splitlines()[0])
    except Exception:  # noqa: BLE001
        return None


def ollama_vram() -> dict:
    try:
        import requests
        ps = requests.get("http://127.0.0.1:11434/api/ps", timeout=5).json().get("models", [])
        return {m["name"]: {"size_vram_mib": round(m.get("size_vram", 0) / 2**20), "size_mib": round(m.get("size", 0) / 2**20),
                            "context_length": m.get("context_length")} for m in ps}
    except Exception:  # noqa: BLE001
        return {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True, choices=["DEV", "TEST"])
    ap.add_argument("--configs", required=True)
    ap.add_argument("--final-test", action="store_true")
    ap.add_argument("--tag", default="")
    ap.add_argument("--prompt-variant", default=None)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if a.split == "TEST" and not (a.final_test and (HERE / "dev_selection.json").exists()):
        raise SystemExit("TEST bị khóa: cần --final-test và dev_selection.json (đóng băng cấu hình trên DEV trước).")
    units = load_units(a.split)
    res_path = HERE / "_cache" / "resources.jsonl"
    res_path.parent.mkdir(parents=True, exist_ok=True)
    for cfg in a.configs.split(","):
        method, _, source = cfg.partition("@")
        kw = {}
        if a.prompt_variant and method in ("llm", "vlm"):
            kw["variant"] = a.prompt_variant
        before = gpu_used_mib()
        run_config(method, source or "ocr_v2", units, tag=a.tag, force=a.force, **kw)
        rec = {"config": cfg_name(method, source or "ocr_v2") + (("." + a.tag) if a.tag else ""), "split": a.split, "gpu_used_mib_before": before,
               "gpu_used_mib_after": gpu_used_mib(), "ollama_ps": ollama_vram()}
        with open(res_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
