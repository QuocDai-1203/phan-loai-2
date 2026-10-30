"""llm_backends.py - Tầng 3 của cascade: LLM cục bộ (Ollama, mặc định) hoặc Kev (tùy chọn), qua `zero_shot.py` + `DiskCache`.

Mỗi backend nhận văn bản thô của tài liệu và trả `zero_shot.Answer`:
  * lỗi hạ tầng (máy chủ tắt, HTTP lỗi, hết thời gian) -> `Answer(NO_ANSWER, parse_ok=False, error=...)`: KHÔNG bao giờ đoán nhãn;
  * văn bản < 25 ký tự -> không gọi mô hình (`Answer(NO_ANSWER, ..., 'văn bản quá ngắn')`).

Cấu hình tầng 3 (`LLM_SPECS`) là bản sao nguyên văn các cấu hình đã đo ở thí nghiệm 02
(`teams/team3_classification/experiments/02_llm_and_cascade/run_all.py`: KEV_GRID, OLLAMA_GRID) - chỉ các cấu hình có ngưỡng trong
`dev_selection_02.json`. Khóa cache phụ thuộc đúng từng ký tự của lời nhắc, nên KHÔNG sửa prompt/tham số ở đây mà không đo lại.

Kev: chỉ TÊN loại làm tiêu chí (cấu hình đo tốt nhất; mô tả dài làm Kev-0.8B sụp từ 0,962 xuống 0,300). Tên mô hình ghi vào kết quả
lấy từ chính máy chủ (`/v1/models` -> `run`; máy chủ cũ: `/api/status` -> `current_model`), không đặt cứng.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Protocol

import requests

from src.classification.llm_cache import DiskCache
from src.classification.zero_shot import (KEV_URL, fetch_kev_model_name, MIN_TEXT_CHARS, NO_ANSWER, OLLAMA_URL, Answer, KevClient, LabelSet,
                                          OllamaClient, build_label_set, clean_prompt_text, kev_one_stage, kev_two_stage,
                                          ollama_one_stage, ollama_two_stage)

logger = logging.getLogger(__name__)

REPO = Path(__file__).resolve().parent.parent.parent
DEFAULT_CACHE_DIR = REPO / "cache" / "llm"
# Hết giờ MỖI lời gọi Ollama. Trước đây 180 s: một lát cắt kẹt hàng phút làm cả tệp đứng (xem teams/00_data_and_eval/experiments/01_end_to_end/RESULTS.md,
# mục "vì sao 195 s"). Lời gọi bình thường trung vị ~0,9 s, p99 ~5 s khi máy rảnh (4366 lời gọi đã cache); nạp lại mô hình ~20 s. 60 s đủ cho một lần nạp lại
# mà không treo tệp; pipeline còn có ngân sách LLM theo tệp và mạch ngắt (src/pipeline.py: GuardedLlm). KHÔNG đổi khóa cache (khóa không gồm timeout).
DEFAULT_OLLAMA_TIMEOUT_S = 60.0


@dataclass(frozen=True)
class LlmSpec:
    id: str
    engine: str                 # 'ollama' | 'kev'
    stages: int = 1
    desc: str = "short"         # 'short' | 'long' | 'name'
    chars: int = 2000
    model: Optional[str] = None  # tên mô hình Ollama


LLM_SPECS: Dict[str, LlmSpec] = {s.id: s for s in (
    LlmSpec("q35_s1_short_c2000", "ollama", 1, "short", 2000, "qwen3.5:4b"),     # MẶC ĐỊNH (tầng-3 chính của thí nghiệm 02)
    LlmSpec("q35_s2_short_c2000", "ollama", 2, "short", 2000, "qwen3.5:4b"),
    LlmSpec("q25_s1_short_c2000", "ollama", 1, "short", 2000, "qwen2.5:3b"),
    LlmSpec("kev_s1_name_c2000", "kev", 1, "name", 2000),                         # Kev chọn được: chỉ tên loại
    LlmSpec("kev_s2_short_c2000", "kev", 2, "short", 2000),
)}
DEFAULT_SPEC_ID = "q35_s1_short_c2000"


class LlmBackend(Protocol):
    spec: LlmSpec
    tier_name: str

    @property
    def model_name(self) -> str: ...
    def answer(self, text: str) -> Answer: ...


def _too_short(text: str) -> Answer:
    return Answer(NO_ANSWER, None, None, 0.0, False, "văn bản quá ngắn")


class OllamaBackend:
    tier_name = "llm"

    def __init__(self, spec: LlmSpec, taxonomy_json: Dict[str, Any], cache: DiskCache, url: str = OLLAMA_URL,
                 timeout: float = DEFAULT_OLLAMA_TIMEOUT_S):
        if spec.engine != "ollama" or not spec.model:
            raise ValueError(f"{spec.id} không phải cấu hình Ollama")
        self.spec = spec
        self.ls: LabelSet = build_label_set(taxonomy_json, spec.desc)
        self.client = OllamaClient(cache, url=url, timeout=timeout)
        self.url = url

    @property
    def model_name(self) -> str:
        return self.spec.model or "ollama"

    def num_ctx(self) -> int:
        return 18000 if self.spec.desc == "long" else 6144

    def available(self) -> Optional[str]:
        """None nếu Ollama trả lời và có mô hình; ngược lại lý do (để báo trước, không bắt buộc gọi)."""
        try:
            r = requests.get(f"{self.url}/api/tags", timeout=3)
            r.raise_for_status()
            names = {m.get("name") for m in r.json().get("models", [])}
        except (requests.RequestException, ValueError) as e:
            return f"Ollama không trả lời: {type(e).__name__}: {e}"
        return None if self.spec.model in names else f"Ollama chưa có mô hình {self.spec.model}"

    def answer(self, text: str) -> Answer:
        t = clean_prompt_text(text, self.spec.chars)
        if len(t) < MIN_TEXT_CHARS:
            return _too_short(t)
        if self.spec.stages == 2:
            return ollama_two_stage(self.client, self.spec.model, t, self.ls, self.num_ctx())
        return ollama_one_stage(self.client, self.spec.model, t, self.ls, self.num_ctx(), None)


class KevBackend:
    tier_name = "kev"

    def __init__(self, spec: LlmSpec, taxonomy_json: Dict[str, Any], cache: DiskCache, base_url: str = KEV_URL.rsplit("/v1/", 1)[0],
                 timeout: float = 300.0):
        if spec.engine != "kev":
            raise ValueError(f"{spec.id} không phải cấu hình Kev")
        self.spec = spec
        self.ls = build_label_set(taxonomy_json, spec.desc)
        self.cache, self.base_url, self.timeout = cache, base_url.rstrip("/"), timeout
        self._model: Optional[str] = None

    def server_model(self, refresh: bool = False) -> Optional[str]:
        """Tên mô hình MÁY CHỦ đang nạp (`/v1/models` -> `run`, hoặc `/api/status` của máy chủ cũ); None nếu không hỏi được."""
        if self._model is None or refresh:
            self._model = fetch_kev_model_name(self.base_url, timeout=3)
            if self._model is None:
                logger.warning("Không hỏi được mô hình của Kev (%s)", self.base_url)
        return self._model

    @property
    def model_name(self) -> str:
        return self.server_model() or "kev-unverified"

    def answer(self, text: str) -> Answer:
        t = clean_prompt_text(text, self.spec.chars)
        if len(t) < MIN_TEXT_CHARS:
            return _too_short(t)
        model = self.server_model()
        if model is None:
            return Answer(NO_ANSWER, None, None, 0.0, False, f"Kev không khả dụng: không đọc được {self.base_url}/v1/models (hoặc /api/status)")
        # khóa cache gồm tag mô hình: câu trả lời của mô hình khác không bao giờ được dùng lại
        client = KevClient(self.cache, url=f"{self.base_url}/v1/systemone", tag=model.split("/")[-1], timeout=self.timeout)
        return (kev_two_stage if self.spec.stages == 2 else kev_one_stage)(client, t, self.ls)


def make_backend(spec_id: str = DEFAULT_SPEC_ID, taxonomy_json: Optional[Dict[str, Any]] = None, cache_dir: Optional[Path] = None,
                 cache: Optional[DiskCache] = None, timeout: Optional[float] = None):
    """Dựng backend theo id cấu hình. `cache` (nếu truyền) thay cho thư mục `cache_dir/<engine>`. `timeout` (giây/lời gọi) ghi đè mặc định của backend."""
    import json
    from src.classification.taxonomy import DEFAULT_TAXONOMY_PATH
    if spec_id not in LLM_SPECS:
        raise KeyError(f"cấu hình tầng 3 không biết: {spec_id!r}; có: {sorted(LLM_SPECS)}")
    spec = LLM_SPECS[spec_id]
    tj = taxonomy_json or json.loads(DEFAULT_TAXONOMY_PATH.read_text(encoding="utf-8"))
    cache = cache or DiskCache((cache_dir or DEFAULT_CACHE_DIR) / spec.engine)
    kw = {} if timeout is None else {"timeout": float(timeout)}
    return (KevBackend if spec.engine == "kev" else OllamaBackend)(spec, tj, cache, **kw)
