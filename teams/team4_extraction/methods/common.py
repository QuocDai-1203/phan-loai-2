"""common.py - Nền chung cho các phương pháp trích xuất (Nhóm 4): đơn vị, nguồn văn bản, định dạng đầu ra.

Giao diện thống nhất của mọi phương pháp:

    method = RegexRules(source="ocr_v2")          # hoặc GlinerFields, FilenameDate, LocalLlmJson, LocalVlmJson
    out = method.extract(unit)                    # {field: {"value": str | None, "normalized": str | None, "page": int | None}}

`out` luôn có MỌI trường của schema loại đó (giá trị vắng = value None). Nếu phương pháp không chạy được (mô hình không nạp, Ollama
tắt...) nó ném `MethodUnavailable` / trả `MethodResult(status="error")` — không bao giờ trả dict rỗng giả làm thành công.
`unit.pages` là các trang thuộc đơn vị (tệp ghép: chỉ các trang của segment); văn bản lấy từ `source`:

    ocr_v2          data/ocr_v2.jsonl (OCR cục bộ, mọi trang tới 30)
    ocr_llm_haiku   data/ocr_llm_haiku.jsonl (bản chép LLM, chỉ 2 trang đầu của tệp)  -- KHÔNG on-premise: chỉ là cận trên
    text_layer      các trang ocr_v2 có source == "text_layer" (PDF số hóa, chữ thật); trang scan để trống
"""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

TEAM = Path(__file__).resolve().parents[1]
REPO = TEAM.parents[1]
DATA = REPO / "data"
SCHEMA_DIR = TEAM / "schema"
UNITS_CSV = TEAM / "gold" / "units.csv"
for _p in (str(TEAM), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from eval.normalize import normalize_value  # noqa: E402

SOURCES = ("ocr_v2", "ocr_llm_haiku", "text_layer")


class MethodUnavailable(RuntimeError):
    """Phương pháp không chạy được trên máy này (thiếu mô hình/thư viện/dịch vụ). Thông điệp là lý do chính xác."""


@dataclass
class Unit:
    unit_id: str
    doc_id: str
    doc_type: str
    split: str
    pages: List[int]
    shown_pages: List[int]
    relative_path: str = ""
    segment_idx: int = 0
    composite: bool = False

    @property
    def file_name(self) -> str:
        return self.relative_path.replace("\\", "/").rsplit("/", 1)[-1]


def load_units(split: Optional[str] = None, doc_types: Optional[List[str]] = None, path: Path = UNITS_CSV) -> List[Unit]:
    """Đọc gold/units.csv. `split`: 'DEV' | 'TEST' | 'EXCLUDED' | None (tất cả). TEST chỉ nên mở ở lần chấm cuối."""
    out: List[Unit] = []
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if split and r["split"] != split:
                continue
            if doc_types and r["doc_type"] not in doc_types:
                continue
            out.append(Unit(
                unit_id=r["unit_id"], doc_id=r["doc_id"], doc_type=r["doc_type"], split=r["split"],
                pages=[int(x) for x in r["pages"].split(";") if x], shown_pages=[int(x) for x in r["shown_pages"].split(";") if x],
                relative_path=r["relative_path"], segment_idx=int(r["segment_idx"]), composite=r["composite"] == "1"))
    return out


_SCHEMAS: Dict[str, Dict[str, Any]] = {}


def load_schema(doc_type: str) -> Dict[str, Any]:
    if doc_type not in _SCHEMAS:
        _SCHEMAS[doc_type] = json.loads((SCHEMA_DIR / f"{doc_type}.json").read_text(encoding="utf-8"))
    return _SCHEMAS[doc_type]


def field_specs(doc_type: str) -> List[Dict[str, Any]]:
    """Các trường cần trích (bỏ trường dẫn xuất annotate=False)."""
    return [f for f in load_schema(doc_type)["x-fields"] if f.get("annotate", True) is not False]


class TextSources:
    """Nạp lười và cache văn bản từng trang theo nguồn: {doc_id: {page: text}}."""

    def __init__(self) -> None:
        self._cache: Dict[str, Dict[str, Dict[int, str]]] = {}

    def _load(self, source: str) -> Dict[str, Dict[int, str]]:
        if source in self._cache:
            return self._cache[source]
        fname = {"ocr_v2": "ocr_v2.jsonl", "text_layer": "ocr_v2.jsonl", "ocr_llm_haiku": "ocr_llm_haiku.jsonl"}.get(source)
        if fname is None:
            raise ValueError(f"nguồn văn bản không hợp lệ: {source!r} (cần một trong {SOURCES})")
        res: Dict[str, Dict[int, str]] = {}
        with open(DATA / fname, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                pg: Dict[int, str] = {}
                for p in r["pages"]:
                    if source == "text_layer" and p.get("source") != "text_layer":
                        continue
                    t = p.get("text") or ""
                    if t.strip():
                        pg[int(p["page"])] = t
                res[r["doc_id"]] = pg
        self._cache[source] = res
        return res

    def pages(self, unit: Unit, source: str) -> Dict[int, str]:
        """{trang: văn bản} cho các trang của đơn vị có trong nguồn. Trang thiếu bị bỏ (không điền rỗng giả)."""
        doc = self._load(source).get(unit.doc_id, {})
        return {p: doc[p] for p in unit.pages if p in doc}


TEXT = TextSources()


def empty_result(doc_type: str) -> Dict[str, Dict[str, Any]]:
    return {f["name"]: {"value": None, "normalized": None, "page": None} for f in field_specs(doc_type)}


def set_value(out: Dict[str, Dict[str, Any]], spec: Dict[str, Any], value: Optional[str], page: Optional[int] = None, **extra: Any) -> None:
    """Gán giá trị vào kết quả, tính `normalized` bằng bộ chuẩn hóa chung; chuỗi rỗng -> null."""
    if value is None or not str(value).strip():
        out[spec["name"]] = {"value": None, "normalized": None, "page": None, **extra}
        return
    v = str(value).strip()
    norm = normalize_value(v, spec["type"], spec.get("id_kind"))
    if spec["type"] in ("date", "number") and norm is not None and norm.startswith("~raw:"):
        # ngày/số KHÔNG phân tích được (OCR hỏng, mô hình chép rác): coi là không tìm thấy (null), không đưa một giá trị sai vào lịch nhắc/ERP
        out[spec["name"]] = {"value": None, "normalized": None, "page": None, "rejected_unparseable": True, **extra}
        return
    out[spec["name"]] = {"value": v, "normalized": norm, "page": page, **extra}


@dataclass
class MethodResult:
    """Kết quả một lần chạy trên một đơn vị (dùng khi cần status/độ trễ; `extract` thường chỉ trả `fields`)."""
    unit_id: str
    fields: Dict[str, Dict[str, Any]]
    status: str = "ok"            # ok | error | skipped
    error: Optional[str] = None
    latency_ms: float = 0.0
    meta: Dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------------------------------
# Đoạn văn bản liên quan (thay cho "4000 ký tự đầu"): cửa sổ quanh từ khóa neo trong MỌI trang
# --------------------------------------------------------------------------------------------------
import re  # noqa: E402

from eval.normalize import fold_keep_len  # noqa: E402

WINDOW_ANCHORS = [
    r"het\s+ngay", r"gia\s+tri\s+den", r"hieu\s+luc", r"\bden\s+ngay", r"\btu\s+ngay", r"ben\s+ban", r"ben\s+mua",
    r"\bben\s+a\b", r"\bben\s+b\b", r"ben\s+giao", r"ben\s+nhan", r"thuoc\s+so\s+huu", r"ten\s+thuong\s+nhan",
    r"cua\s+hang\s+ban\s+l", r"ho\s+va\s+ten", r"ngay\s+sinh", r"don\s+vi\s+cong\s+tac", r"hom\s+nay", r"giam\s+doc\s+so",
    r"\bphuong\s+tien\s*:", r"m3\s+thuc\s+te", r"ma\s+so\s+thue", r"nghe\s+nghiep", r"to\s+chuc\s+tu", r"han\s+muc",
    r"so\s+chung\s+thu",
]
WIN_BEFORE, WIN_AFTER, WIN_MAX, MAX_WINDOWS = 150, 450, 900, 12


def build_windows(pages: Dict[int, str], max_windows: int = MAX_WINDOWS, win_max: int = WIN_MAX) -> List[Tuple[int, int, int]]:
    """Cửa sổ (trang, đầu, cuối) quanh neo từ khóa trong mọi trang + cửa sổ đầu trang đầu; gộp phần giao nhau,
    mỗi cửa sổ <= `win_max` ký tự. Neo khớp trên văn bản không dấu nên chịu được lỗi dấu của OCR."""
    wins: List[Tuple[int, int, int]] = []
    order = sorted(pages)
    if order:
        wins.append((order[0], 0, min(win_max, len(pages[order[0]]))))
    rx = re.compile("|".join(WINDOW_ANCHORS), re.I)
    for p in order:
        f = fold_keep_len(pages[p])
        spans = sorted((max(0, m.start() - WIN_BEFORE), min(len(f), m.end() + WIN_AFTER)) for m in rx.finditer(f))
        merged: List[List[int]] = []
        for s, e in spans:
            if merged and s <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], e)
            else:
                merged.append([s, e])
        for s, e in merged:
            for a in range(s, e, win_max):
                wins.append((p, a, min(e, a + win_max)))
    seen, out = set(), []
    for w in wins:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out[:max_windows]


def passages_text(pages: Dict[int, str], max_chars: int = 6000) -> str:
    """Văn bản đưa cho LLM: nếu đơn vị ngắn thì nguyên văn mọi trang; nếu dài thì các cửa sổ liên quan (mỗi đoạn có đầu '[trang N]')."""
    total = sum(len(t) for t in pages.values())
    if total <= max_chars:
        return "\n\n".join(f"[trang {p}]\n{pages[p].strip()}" for p in sorted(pages))
    parts, used = [], 0
    for (p, a, b) in sorted(build_windows(pages, max_windows=40, win_max=1200)):
        seg = pages[p][a:b].strip()
        if used + len(seg) > max_chars:
            break
        parts.append(f"[trang {p}]\n{seg}")
        used += len(seg)
    return "\n\n".join(parts)


# --------------------------------------------------------------------------------------------------
# Lớp cơ sở: văn bản theo nguồn, bộ lọc PII mặc định, trạng thái lỗi/bỏ qua rõ ràng
# --------------------------------------------------------------------------------------------------
import time  # noqa: E402

from schema.pii_policy import filter_output, safe_repr  # noqa: E402,F401


class BaseMethod:
    """Lớp cơ sở. Lớp con cài `_extract(unit, pages)` trả {field: {value, normalized, page}} đủ mọi trường schema.

    `extract(unit)` = `_extract` rồi áp chính sách PII (T5): với `store_personal_ids=False` (mặc định) khóa số định danh và
    ngày sinh bị BỎ khỏi kết quả. `run(unit)` trả `MethodResult` với `status` ok | skipped (không có văn bản) | error (phương
    pháp không chạy được) và độ trễ — dùng cái này khi chấm để đếm riêng lỗi/bỏ qua.
    """

    name = "base"
    needs_text = True

    def __init__(self, source: str = "ocr_v2", store_personal_ids: bool = False) -> None:
        if self.needs_text and source not in SOURCES:
            raise ValueError(f"source phải thuộc {SOURCES}")
        self.source = source
        self.store_personal_ids = store_personal_ids

    def pages(self, unit: Unit) -> Dict[int, str]:
        return TEXT.pages(unit, self.source)

    def _extract(self, unit: Unit, pages: Dict[int, str]) -> Dict[str, Dict[str, Any]]:  # pragma: no cover - lớp con cài
        raise NotImplementedError

    def extract(self, unit: Unit) -> Dict[str, Dict[str, Any]]:
        pages = self.pages(unit) if self.needs_text else {}
        if self.needs_text and not pages:
            raise MethodUnavailable(f"không có văn bản nguồn '{self.source}' cho đơn vị này")
        fields = self._extract(unit, pages)
        return filter_output(fields, store_personal_ids=self.store_personal_ids)

    def run(self, unit: Unit) -> MethodResult:
        t0 = time.perf_counter()
        try:
            f = self.extract(unit)
            return MethodResult(unit.unit_id, f, "ok", None, (time.perf_counter() - t0) * 1000)
        except MethodUnavailable as e:
            st = "skipped" if "không có văn bản" in str(e) else "error"
            return MethodResult(unit.unit_id, {}, st, str(e), (time.perf_counter() - t0) * 1000)
        except Exception as e:  # noqa: BLE001 - mọi lỗi phải hiện ra, không nuốt
            return MethodResult(unit.unit_id, {}, "error", f"{type(e).__name__}: {e}", (time.perf_counter() - t0) * 1000)
