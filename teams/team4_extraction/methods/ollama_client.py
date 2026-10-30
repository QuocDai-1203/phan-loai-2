"""ollama_client.py - Gọi Ollama cục bộ (127.0.0.1:11434) với đầu ra ràng buộc theo JSON Schema + bộ nhớ đệm đĩa (Nhóm 4).

Chỉ gọi dịch vụ chạy trên máy này (on-premise). Mọi lời gọi qua `chat_json`:
  * `format` = JSON Schema (Ollama >= 0.5 hỗ trợ "structured outputs"; `check_server()` ghi lại phiên bản và năng lực của mô hình).
  * Cache: `src/classification/llm_cache.py::DiskCache` ở `teams/team4_extraction/_cache/ollama/` (đã nằm trong .gitignore qua `_cache/`).
    Khóa = (mô hình, tin nhắn, schema, tùy chọn, băm ảnh). Bản ghi lỗi KHÔNG bị dùng lại.
  * Lỗi kết nối/timeout/hết bộ nhớ -> `MethodUnavailable` với thông điệp rõ (không trả kết quả rỗng giả).
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

TEAM = Path(__file__).resolve().parents[1]
REPO = TEAM.parents[1]
for _p in (str(TEAM), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import requests  # noqa: E402

from methods.common import MethodUnavailable  # noqa: E402
from src.classification.llm_cache import DiskCache, make_key  # noqa: E402

HOST = "http://127.0.0.1:11434"
CACHE = DiskCache(TEAM / "_cache" / "ollama")


def check_server(model: str = "qwen3.5:4b", host: str = HOST, timeout: float = 5.0) -> Dict[str, Any]:
    """Phiên bản Ollama, mô hình có cài không, năng lực (vision/thinking...). Ném MethodUnavailable nếu không kết nối được."""
    try:
        ver = requests.get(f"{host}/api/version", timeout=timeout).json().get("version")
        tags = requests.get(f"{host}/api/tags", timeout=timeout).json().get("models", [])
    except requests.RequestException as e:
        raise MethodUnavailable(f"Không kết nối được Ollama tại {host}: {type(e).__name__}: {e}") from e
    info = next((m for m in tags if m.get("name") == model or m.get("model") == model), None)
    caps: List[str] = []
    if info:
        try:
            caps = requests.post(f"{host}/api/show", json={"model": model}, timeout=timeout).json().get("capabilities", [])
        except requests.RequestException:
            pass
    return {"version": ver, "model_installed": info is not None, "capabilities": caps}


def _b64(path: Path) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


def chat_json(model: str, system: str, user: str, schema: Dict[str, Any], images: Optional[List[Path]] = None,
              options: Optional[Dict[str, Any]] = None, host: str = HOST, timeout: float = 600.0, use_cache: bool = True) -> Dict[str, Any]:
    """Một lời gọi /api/chat với `format=schema`. Trả {"data": dict, "raw": str, "latency_ms": float, "cached": bool, "stats": {...}}.

    JSON hỏng/không khớp schema -> MethodUnavailable (kèm 200 ký tự đầu của câu trả lời, đã che chuỗi số dài)."""
    opts = {"temperature": 0, "num_ctx": 6144, "num_predict": 900}
    opts.update(options or {})
    image_hashes = [hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16] for p in (images or [])]
    key = make_key("t4-ollama-v1", model, system, user, schema, opts, image_hashes)

    def call() -> Dict[str, Any]:
        msgs: List[Dict[str, Any]] = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        if images:
            msgs[1]["images"] = [_b64(Path(p)) for p in images]
        body = {"model": model, "stream": False, "think": False, "messages": msgs, "format": schema, "options": opts, "keep_alive": "5m"}
        t0 = time.perf_counter()
        try:
            r = requests.post(f"{host}/api/chat", json=body, timeout=timeout)
        except requests.RequestException as e:
            raise MethodUnavailable(f"Lỗi gọi Ollama: {type(e).__name__}: {e}") from e
        ms = (time.perf_counter() - t0) * 1000
        if r.status_code != 200:
            raise MethodUnavailable(f"Ollama trả HTTP {r.status_code}: {r.text[:300]}")
        j = r.json()
        raw = (j.get("message") or {}).get("content", "")
        return {"raw": raw, "latency_ms": ms, "error": None,
                "stats": {k: j.get(k) for k in ("total_duration", "load_duration", "prompt_eval_count", "eval_count")}}

    hits_before = CACHE.hits
    rec = CACHE.cached(key, call) if use_cache else call()
    cached = CACHE.hits > hits_before
    raw = rec["raw"]
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("không phải đối tượng JSON")
    except ValueError as e:
        snippet = re.sub(r"[0-9]{5,}", "#", raw[:200])
        raise MethodUnavailable(f"Ollama trả JSON không hợp lệ ({e}): {snippet!r}") from e
    return {"data": data, "raw": raw, "latency_ms": rec["latency_ms"], "stats": rec.get("stats", {}), "cached": cached}
