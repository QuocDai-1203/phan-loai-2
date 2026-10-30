"""common05.py - Dựng lát cắt theo đáp án (segments) của 8 tệp ghép khác loại và chạy bộ phân loại lên từng lát. CHỈ chẩn đoán.

8 tệp đều của MỘT nhà cung cấp, nên mọi con số ở thí nghiệm 05 là chẩn đoán/giả thuyết, không phải ước lượng tổng quát.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
E2E = REPO / "teams" / "00_data_and_eval" / "experiments" / "01_end_to_end"
EXP02 = HERE.parent / "02_llm_and_cascade"
for p in (REPO, REPO / "teams" / "00_data_and_eval" / "eval", HERE.parent / "01_classical_baselines", EXP02, E2E):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import pandas as pd  # noqa: E402

from src.common.contracts import DocumentSlice, OCRPageResult  # noqa: E402

OUT = REPO / "teams" / "team3_classification" / "results" / "05_composite_slices"
CACHE_OWN = HERE / "_cache" / "ollama"
CACHE_EXTRA = [E2E / "_cache" / "ollama", EXP02 / "_cache" / "ollama", REPO / "cache" / "llm" / "ollama"]


def parse_segments(s: str) -> List[Tuple[int, int, str]]:
    out = []
    for part in s.split(";"):
        pg, lab = part.split(":")
        a, _, b = pg.partition("-")
        out.append((int(a), int(b or a), lab))
    return out


def load_ocr() -> Dict[str, dict]:
    ocr = {}
    for line in open(REPO / "data" / "ocr_v2.jsonl", encoding="utf-8"):
        r = json.loads(line)
        ocr[r["doc_id"]] = r
    return ocr


def composites() -> pd.DataFrame:
    return pd.read_csv(REPO / "data" / "splits" / "excluded_composites.csv")


def make_slice(rec: dict, a: int, b: int, sid: str) -> DocumentSlice:
    pages = []
    for p in rec["pages"]:
        if a <= p["page"] <= b:
            pages.append(OCRPageResult(page_number=p["page"], width=0, height=0, full_text=p.get("text") or "", ocr_engine=p.get("engine", ""),
                                       source=p.get("source", "ocr"), error=p.get("error")))
    return DocumentSlice(slice_id=sid, start_page=a, end_page=b, page_count=b - a + 1,
                         combined_text="\n".join(p.full_text for p in pages), pages=pages, boundary_method="oracle")


def oracle_slices(ocr: Dict[str, dict]) -> List[dict]:
    """Mọi lát cắt đáp án của 8 tệp: dict(file_idx, doc_id, seg_idx, true, a, b, slice)."""
    rows = []
    for fi, r in composites().iterrows():
        for si, (a, b, lab) in enumerate(parse_segments(r["segments"])):
            rows.append(dict(file_idx=fi, doc_id=r["doc_id"], seg_idx=si, true=lab, a=a, b=b, slice=make_slice(ocr[r["doc_id"]], a, b, f"{fi}.{si}")))
    return rows
