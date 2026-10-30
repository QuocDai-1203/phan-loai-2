"""field_llm.py - LLM cục bộ (Ollama) trích trường theo JSON Schema ràng buộc. CHỈ gọi dịch vụ chạy trên máy này (127.0.0.1).

Dùng chung giữa `src/extraction/field_extractor.py` (sản xuất) và `teams/team4_extraction/methods/local_llm_json.py` (thí nghiệm), để prompt được chấm
trên DEV/TEST đúng là prompt đang chạy thật. Đổi prompt = đổi `PROMPT_VERSION` và phải chấm lại.

Mọi lỗi (Ollama tắt, hết bộ nhớ, JSON hỏng) -> `LlmError` với thông điệp rõ; người gọi đưa vào `ExtractionResult.status/error`.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.extraction.normalize import normalize_value
from src.extraction.schemas import field_specs, load_schema
from src.extraction.field_result import pii_category, DROPPED_BY_DEFAULT

OLLAMA_URL = "http://127.0.0.1:11434"
MODEL = "qwen3.5:4b"
PROMPT_VERSION = "v1"

SYSTEM = (
    "Bạn là bộ trích xuất trường dữ liệu từ giấy tờ doanh nghiệp tiếng Việt. Chỉ dùng thông tin CÓ TRONG tài liệu được cung cấp. "
    "Với mỗi trường: chép NGUYÊN VĂN giá trị như in (ví dụ ngày giữ dạng 'ngày 12 tháng 01 năm 2028' hoặc '12/01/2028'). "
    "Nếu tài liệu không có hoặc bạn không đọc chắc được trường đó, trả null. Tuyệt đối không bịa, không suy ngày từ chỗ khác, "
    "không tự cộng/trừ ngày, không điền giá trị 'cho hợp lý'. Trả đúng một đối tượng JSON theo schema, không giải thích."
)

# neo từ khóa để chọn đoạn liên quan khi văn bản dài (thay cho "4000 ký tự đầu")
WINDOW_ANCHORS = [
    r"het\s+ngay", r"gia\s+tri\s+den", r"hieu\s+luc", r"\bden\s+ngay", r"\btu\s+ngay", r"ben\s+ban", r"ben\s+mua",
    r"\bben\s+a\b", r"\bben\s+b\b", r"ben\s+giao", r"ben\s+nhan", r"thuoc\s+so\s+huu", r"ten\s+thuong\s+nhan",
    r"cua\s+hang\s+ban\s+l", r"ho\s+va\s+ten", r"ngay\s+sinh", r"don\s+vi\s+cong\s+tac", r"hom\s+nay", r"giam\s+doc\s+so",
    r"\bphuong\s+tien\s*:", r"m3\s+thuc\s+te", r"ma\s+so\s+thue", r"nghe\s+nghiep", r"to\s+chuc\s+tu", r"han\s+muc",
    r"so\s+chung\s+thu",
]
WIN_BEFORE, WIN_AFTER, WIN_MAX, MAX_WINDOWS = 150, 450, 900, 12


class LlmError(RuntimeError):
    """Gọi LLM cục bộ thất bại (kết nối, HTTP, JSON hỏng)."""


def build_windows(pages: Dict[int, str], max_windows: int = MAX_WINDOWS, win_max: int = WIN_MAX):
    from src.extraction.normalize import fold_keep_len
    wins = []
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
    """Văn bản đưa cho LLM: nguyên văn mọi trang nếu ngắn; nếu dài thì các cửa sổ quanh neo từ khóa (mỗi đoạn có đầu '[trang N]')."""
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


def fields_for(doc_type: str, store_personal_ids: bool) -> List[Dict[str, Any]]:
    """Các trường sẽ hỏi mô hình: bỏ trường dẫn xuất và (mặc định) số định danh/ngày sinh — không hỏi thì không trích."""
    return [f for f in field_specs(doc_type) if store_personal_ids or pii_category(f["name"]) not in DROPPED_BY_DEFAULT]


def json_schema(fields: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"type": "object", "properties": {f["name"]: {"type": ["string", "null"]} for f in fields},
            "required": [f["name"] for f in fields], "additionalProperties": False}


def field_instructions(fields: List[Dict[str, Any]]) -> str:
    return "\n".join(f"- {f['name']}: {f['desc']}." + (f" {f['annotator_hint']}" if f.get("annotator_hint") else "") for f in fields)


def build_user_prompt(doc_type: str, fields: List[Dict[str, Any]], pages: Dict[int, str], max_chars: int = 6000) -> str:
    title = load_schema(doc_type)["title"]
    return (f"Loại tài liệu: {title}\n\nCác trường cần trích:\n{field_instructions(fields)}\n\n"
            f"Văn bản OCR (có thể sai chính tả/dấu; mỗi đoạn có đầu '[trang N]'):\n<<<\n{passages_text(pages, max_chars)}\n>>>")


def prompt_fingerprint() -> str:
    """Băm của prompt hệ thống + phiên bản (ghi vào dev_selection.json để chứng minh TEST dùng đúng prompt đã đóng băng)."""
    return hashlib.sha256((PROMPT_VERSION + "\n" + SYSTEM).encode("utf-8")).hexdigest()[:16]


LlmClient = Callable[[str, str, Dict[str, Any]], Dict[str, Any]]      # (system, user, json_schema) -> dict {trường: chuỗi | None}


def ollama_client(model: str = MODEL, url: str = OLLAMA_URL, timeout: float = 600.0, cache_dir: Optional[Path] = None,
                  num_ctx: int = 6144, num_predict: int = 900) -> LlmClient:
    """Tạo hàm gọi Ollama cục bộ với `format` = JSON Schema (structured outputs), temperature 0, có cache đĩa tùy chọn (`DiskCache`)."""
    import requests  # nhập muộn: import module không đụng mạng

    cache = None
    if cache_dir is not None:
        from src.classification.llm_cache import DiskCache, make_key
        cache = DiskCache(cache_dir)

    def call(system: str, user: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        opts = {"temperature": 0, "num_ctx": num_ctx, "num_predict": num_predict}

        def real() -> Dict[str, Any]:
            body = {"model": model, "stream": False, "think": False, "format": schema, "options": opts, "keep_alive": "5m",
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
            t0 = time.perf_counter()
            try:
                r = requests.post(f"{url}/api/chat", json=body, timeout=timeout)
            except requests.RequestException as e:
                raise LlmError(f"không gọi được Ollama tại {url}: {type(e).__name__}: {e}") from e
            if r.status_code != 200:
                raise LlmError(f"Ollama trả HTTP {r.status_code}: {r.text[:300]}")
            return {"raw": (r.json().get("message") or {}).get("content", ""), "latency_ms": (time.perf_counter() - t0) * 1000, "error": None}

        if cache is not None:
            from src.classification.llm_cache import make_key
            rec = cache.cached(make_key("t4-src-v1", model, system, user, schema, opts), real)
        else:
            rec = real()
        try:
            data = json.loads(rec["raw"])
            if not isinstance(data, dict):
                raise ValueError("không phải đối tượng JSON")
        except ValueError as e:
            raise LlmError(f"Ollama trả JSON không hợp lệ ({e}): {re.sub(r'[0-9]{5,}', '#', rec['raw'][:160])!r}") from e
        return data

    return call
