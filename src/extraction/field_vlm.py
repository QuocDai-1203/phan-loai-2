"""field_vlm.py - Mô hình thị giác cục bộ (Ollama, qwen3.5:4b có năng lực `vision`) đọc ẢNH trang để ĐỐI CHIẾU trường hạn. Chỉ gọi 127.0.0.1.

Vì sao: chữ viết tay và chữ dưới con dấu làm OCR hỏng; mô hình thị giác đọc thẳng ảnh nên là nguồn ĐỘC LẬP với OCR (xem RESULTS.md của thí nghiệm).
Prompt/schema giống hệt bản đã chấm (`teams/team4_extraction/methods/local_vlm_json.py`): hỏi mọi trường nhưng `field_extractor` chỉ dùng kết quả
của TRƯỜNG HẠN để đối chiếu. Ảnh: 200 dpi, trang dọc cắt đôi (`pNN_a`/`pNN_b`), cạnh dài <= 1600 px; gửi 4 ảnh đầu (xem `render_pages_for_vlm`).
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.extraction.field_llm import (MODEL, OLLAMA_URL, PROMPT_VERSION, SYSTEM, LlmError, field_instructions)
from src.extraction.schemas import load_schema

SYSTEM_VLM = SYSTEM.replace("từ giấy tờ", "từ ẢNH các trang giấy tờ")
VlmClient = Callable[[str, str, Dict[str, Any], List[Path]], Dict[str, Any]]      # (system, user, schema, ảnh) -> dict


def build_vlm_prompt(doc_type: str, fields: List[Dict[str, Any]]) -> str:
    title = load_schema(doc_type)["title"]
    return (f"Loại tài liệu: {title}\n\nCác ảnh đính kèm là các trang của tài liệu theo thứ tự "
            f"(tên tệp pNN_a/pNN_b là nửa trên/nửa dưới của trang NN).\n\nCác trường cần trích:\n{field_instructions(fields)}")


def vlm_fingerprint() -> str:
    return hashlib.sha256((PROMPT_VERSION + "\n" + SYSTEM_VLM).encode("utf-8")).hexdigest()[:16]


PNG_COMPRESS_LEVEL = 1          # nén nhanh (zlib mức 1), KHÔNG mất điểm ảnh; `optimize=True` chậm ~8 lần (đo ở teams/00_data_and_eval/experiments/03_end_to_end_v2)


def image_content_hash(path: Path) -> str:
    """Băm theo ĐIỂM ẢNH (kích thước + RGB), không theo byte của tệp: đổi mức nén PNG không làm lỡ cache VLM. Không giải mã được -> băm byte tệp."""
    p = Path(path)
    try:
        from PIL import Image
        with Image.open(p) as im:
            rgb = im.convert("RGB")
            return hashlib.sha256(f"{rgb.width}x{rgb.height}".encode() + rgb.tobytes()).hexdigest()[:16]
    except Exception:  # noqa: BLE001
        return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def ollama_vlm_client(model: str = MODEL, url: str = OLLAMA_URL, timeout: float = 900.0, cache_dir: Optional[Path] = None,
                      num_ctx: int = 12288, num_predict: int = 900) -> VlmClient:
    """Hàm gọi Ollama cục bộ kèm ảnh trang (base64), `format` = JSON Schema, temperature 0, có cache đĩa tùy chọn."""
    import requests

    cache = None
    if cache_dir is not None:
        from src.classification.llm_cache import DiskCache
        cache = DiskCache(cache_dir)

    def call(system: str, user: str, schema: Dict[str, Any], images: List[Path]) -> Dict[str, Any]:
        opts = {"temperature": 0, "num_ctx": num_ctx, "num_predict": num_predict}
        hashes = [image_content_hash(p) for p in images]

        def real() -> Dict[str, Any]:
            msgs = [{"role": "system", "content": system},
                    {"role": "user", "content": user, "images": [base64.b64encode(Path(p).read_bytes()).decode("ascii") for p in images]}]
            body = {"model": model, "stream": False, "think": False, "format": schema, "options": opts, "keep_alive": "5m", "messages": msgs}
            t0 = time.perf_counter()
            try:
                r = requests.post(f"{url}/api/chat", json=body, timeout=timeout)
            except requests.RequestException as e:
                raise LlmError(f"không gọi được Ollama (thị giác) tại {url}: {type(e).__name__}: {e}") from e
            if r.status_code != 200:
                raise LlmError(f"Ollama trả HTTP {r.status_code}: {r.text[:300]}")
            return {"raw": (r.json().get("message") or {}).get("content", ""), "latency_ms": (time.perf_counter() - t0) * 1000, "error": None}

        if cache is not None:
            from src.classification.llm_cache import make_key
            rec = cache.cached(make_key("t4-src-vlm-v2", model, system, user, schema, opts, hashes), real)
        else:
            rec = real()
        try:
            data = json.loads(rec["raw"])
            if not isinstance(data, dict):
                raise ValueError("không phải đối tượng JSON")
        except ValueError as e:
            snippet = re.sub(r"[0-9]{5,}", "#", rec["raw"][:160])
            raise LlmError(f"Ollama (thị giác) trả JSON không hợp lệ ({e}): {snippet!r}") from e
        return data

    return call


def render_pages_for_vlm(pdf_path: Path, pages: List[int], out_dir: Path, dpi: int = 200, max_side: int = 1600) -> List[Path]:
    """Render các trang PDF (1-indexed) thành ảnh như lúc chấm: 200 dpi RGB, trang dọc cắt đôi tại hàng ít mực nhất quanh giữa trang
    (`pNN_a.png` nửa trên, `pNN_b.png` nửa dưới), cạnh dài <= 1600 px. Trả danh sách đường dẫn ảnh theo thứ tự trang."""
    import fitz
    import numpy as np
    from PIL import Image

    out_dir.mkdir(parents=True, exist_ok=True)
    paths: List[Path] = []
    doc = fitz.open(pdf_path)
    try:
        for p in pages:
            pix = doc[p - 1].get_pixmap(dpi=dpi, colorspace=fitz.csRGB)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            if img.height / img.width > 1.2:
                g = np.asarray(img.convert("L"), dtype=np.float32)
                h = g.shape[0]
                lo, hi = int(h * 0.44), int(h * 0.56)
                cut = lo + int((255 - g[lo:hi]).sum(axis=1).argmin())
                parts = [("_a", img.crop((0, 0, img.width, cut))), ("_b", img.crop((0, cut, img.width, h)))]
            else:
                parts = [("", img)]
            for suf, im in parts:
                if max(im.size) > max_side:
                    k = max_side / max(im.size)
                    im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)
                f = out_dir / f"p{p:02d}{suf}.png"
                im.save(f, compress_level=PNG_COMPRESS_LEVEL)
                paths.append(f)
    finally:
        doc.close()
    return paths
