"""common.py - Đường dẫn, nạp dữ liệu và tiện ích dùng chung của thí nghiệm 02 (LLM + embedding + cascade).

Dùng lại harness (chia dữ liệu, chỉ số, bootstrap, bảng kết quả) và `methods.py` của thí nghiệm 01; KHÔNG viết lại chỉ số.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Sequence

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
EXP01 = HERE.parent / "01_classical_baselines"
for p in (REPO, REPO / "teams" / "00_data_and_eval" / "eval", EXP01, HERE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from harness import *  # noqa: E402,F401,F403
from harness import (POOL, UNKNOWN, Benchmark, Doc, Prediction, Predictor, load_benchmark, load_documents,  # noqa: E402
                     load_or_make_splits)

from src.classification.llm_cache import DiskCache  # noqa: E402

OUT = REPO / "teams" / "team3_classification" / "results" / "02_llm_and_cascade"
TABLES = OUT / "tables"
FIGS = OUT / "figs"
PREDS = OUT / "preds"
CACHE_DIR = HERE / "_cache"
TAXONOMY = REPO / "data" / "taxonomy_v2.json"
SEL01 = REPO / "teams" / "team3_classification" / "results" / "01_classical_baselines" / "tables" / "dev_selection.json"
SEL02 = TABLES / "dev_selection_02.json"
REG02 = TABLES / "test_scored_02.json"

for d in (TABLES, FIGS, PREDS, CACHE_DIR):
    d.mkdir(parents=True, exist_ok=True)

LABELS = REPO / "data" / "labels_v2.csv"
# nguồn văn bản dùng cho LLM / embedding: trang 1-2 (ocr_v2, Haiku) và trang 1 (OCR cũ chỉ có trang 1)
SOURCES_MAIN = ["ocr_v2_p12", "haiku_p12", "legacy_p1"]
SOURCE_VI = {"ocr_v2_p12": "OCR local VietOCR (trang 1-2) - điều kiện on-premise",
             "haiku_p12": "LLM-vision Haiku (trang 1-2) - cận trên, KHÔNG on-premise",
             "legacy_p1": "RapidOCR cũ (trang 1)",
             "ocr_v2_p1": "OCR local VietOCR (trang 1)", "haiku_p1": "LLM-vision Haiku (trang 1)"}
MIN_TEXT_CHARS = 25          # dưới ngưỡng này coi như "không đọc được" -> chuyển cho người, không gọi LLM


def load_taxonomy_json() -> dict:
    return json.loads(TAXONOMY.read_text(encoding="utf-8"))


def clean_text(text: str, n_chars: int | None = None) -> str:
    """Gộp khoảng trắng thừa (giữ xuống dòng đơn), cắt n ký tự đầu. Văn bản gửi cho mô hình."""
    t = re.sub(r"[ \t ]+", " ", text or "")
    t = re.sub(r"\n\s*\n+", "\n", t).strip()
    return t[:n_chars] if n_chars else t


def get_cache(name: str = "llm") -> DiskCache:
    return DiskCache(CACHE_DIR / name)


class Data:
    """Benchmark + splits + tài liệu theo (nguồn, split). TEST chỉ mở khi final_test=True."""

    def __init__(self, labels: Path = LABELS, min_docs: int = 10):
        self.bench: Benchmark = load_benchmark(labels, min_docs)
        self.splits = load_or_make_splits(self.bench)
        self._docs: Dict[tuple, List[Doc]] = {}

    def docs(self, source: str, split: str = "DEV", final_test: bool = False) -> List[Doc]:
        k = (source, split)
        if k not in self._docs:
            self._docs[k] = load_documents(self.bench, self.splits, source, split, final_test=final_test)
        return self._docs[k]

    @property
    def z_classes(self) -> List[str]:
        return self.bench.z_classes

    @property
    def s_classes(self) -> List[str]:
        return self.bench.s_classes


def dump_json(path: Path, obj) -> None:
    def default(o):
        if isinstance(o, (np.floating,)):
            return None if np.isnan(o) or np.isinf(o) else float(o)
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        raise TypeError(type(o))

    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=default), encoding="utf-8")


def md_table(df: pd.DataFrame, floatfmt: str = "{:.3f}") -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, (float, np.floating)):
                cells.append("" if np.isnan(v) else floatfmt.format(v))
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def log(*a):
    import time
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)
