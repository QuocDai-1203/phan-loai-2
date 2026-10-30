"""zero_shot.py - Phân loại zero-shot toàn taxonomy bằng mô hình cục bộ (Kev `Choice`, Ollama JSON có ràng buộc, bge-m3).

Mọi lời gọi đi qua `DiskCache` (khóa = mô hình + yêu cầu) nên chạy lại miễn phí và tất định. Không gửi gì ra ngoài máy:
Kev ở http://127.0.0.1:8009, Ollama ở http://127.0.0.1:11434.

Thành phần:
- `build_label_set`  : chọn lớp + mô tả (ngắn/dài) từ taxonomy, nhóm theo `group` cho chế độ hai bước.
- `KevClient.choose` : một câu hỏi `Choice` -> nhãn + xác suất mỗi tiêu chí (Kev trả `probabilities`).
- `OllamaClient.choose` : chat với `format` = JSON schema (enum nhãn), temperature 0, `think=False`;
  độ tin cậy lấy từ logprob của các token trả lời (nếu server trả), ngược lại None.
- `OllamaClient.embed` : bge-m3 qua /api/embed.
- `two_stage` : nhóm -> loại trong nhóm, ghép độ tin cậy = p(nhóm) * p(loại | nhóm).
"""

from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

import requests

from src.classification.llm_cache import DiskCache, make_key

KEV_URL = "http://127.0.0.1:8009/v1/systemone"
OLLAMA_URL = "http://127.0.0.1:11434"
MIN_TEXT_CHARS = 25            # dưới ngưỡng này coi như "không đọc được" -> chuyển cho người, không gọi mô hình
NO_ANSWER = "NO_ANSWER"        # mô hình không trả nhãn hợp lệ (lỗi phân tích) -> tính là abstain/sai
# Nhãn không bao giờ được tự động xếp hồ sơ: người phải xem
NEVER_AUTO = ("OTHER", "UNREADABLE", NO_ANSWER)


def fetch_kev_model_name(base_url: str, timeout=3.0) -> Optional[str]:
    """Tên mô hình MÁY CHỦ Kev đang nạp. Máy chủ mới (2026-10) báo ở `GET /v1/models` (`models[0].run`, vd 'jaredpalmer/kev-0.8b');
    máy chủ demo cũ báo ở `GET /api/status` (`current_model`). Thử /v1/models trước, rồi /api/status; không hỏi được -> None."""
    base = base_url.split("/v1/")[0].rstrip("/")
    try:
        r = requests.get(f"{base}/v1/models", timeout=timeout)
        if getattr(r, "status_code", 200) != 200:
            raise ValueError(f"HTTP {r.status_code}")
        models = (r.json() or {}).get("models") or []
        if models and isinstance(models[0], dict) and (models[0].get("run") or models[0].get("name")):
            return str(models[0].get("run") or models[0].get("name"))
    except (requests.RequestException, ValueError, AttributeError):
        pass
    try:
        r = requests.get(f"{base}/api/status", timeout=timeout)
        if getattr(r, "status_code", 200) != 200:
            return None
        return (r.json() or {}).get("current_model") or None
    except (requests.RequestException, ValueError, AttributeError):
        return None


def clean_prompt_text(text: str, n_chars: Optional[int] = None) -> str:
    """Gộp khoảng trắng thừa (giữ xuống dòng đơn), cắt n ký tự đầu. Văn bản gửi cho mô hình.
    Giống `clean_text` của teams/.../02_llm_and_cascade/common.py (khóa cache của thí nghiệm 02 phụ thuộc vào chuỗi này)."""
    t = re.sub(r"[ \t\u00a0]+", " ", text or "")
    t = re.sub(r"\n\s*\n+", "\n", t).strip()
    return t[:n_chars] if n_chars else t


# ---------------------------------------------------------------------------
# Tập nhãn + mô tả
# ---------------------------------------------------------------------------
@dataclass
class LabelSet:
    ids: List[str]
    desc: Dict[str, str]                       # id -> mô tả (ngắn hoặc dài)
    group_of: Dict[str, str]                   # id -> group
    groups: List[str]
    group_desc: Dict[str, str]
    desc_kind: str = "short"

    def members(self, group: str) -> List[str]:
        return [i for i in self.ids if self.group_of[i] == group]


def build_label_set(taxonomy_json: Dict[str, Any], desc: str = "short", exclude: Sequence[str] = ("UNREADABLE",)) -> LabelSet:
    """`desc` = 'short' (short_description), 'long' (description) hoặc 'name' (name_vi). Bỏ các id trong `exclude`.
    Mô tả dạng 'long' gồm cả `deciding_cue` (gợi ý phân biệt với lớp dễ nhầm) nếu có."""
    ids, d, gof = [], {}, {}
    for c in taxonomy_json["classes"]:
        if c["id"] in exclude:
            continue
        ids.append(c["id"])
        gof[c["id"]] = c["group"]
        if desc == "short":
            d[c["id"]] = c.get("short_description") or c.get("name_vi") or c["id"]
        elif desc == "long":
            txt = c.get("description") or c.get("name_vi") or c["id"]
            cue = c.get("deciding_cue")
            d[c["id"]] = f"{txt} Gợi ý phân biệt: {cue}" if cue else txt
        elif desc == "name":
            d[c["id"]] = c.get("name_vi") or c["id"]
        else:
            raise ValueError(desc)
    groups = [g["id"] for g in taxonomy_json["groups"] if any(gof[i] == g["id"] for i in ids)]
    gdesc = {g["id"]: f'{g["name_vi"]}: {g["description"]}' for g in taxonomy_json["groups"]}
    return LabelSet(ids, d, gof, groups, gdesc, desc)


# ---------------------------------------------------------------------------
# Kết quả một câu hỏi
# ---------------------------------------------------------------------------
@dataclass
class Answer:
    label: str
    conf: Optional[float]                       # xác suất/độ tin cậy của nhãn chọn (None nếu mô hình không báo)
    probs: Optional[Dict[str, float]] = None    # phân phối trên các nhãn (Kev) hoặc None
    latency_ms: float = 0.0
    parse_ok: bool = True
    error: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Kev
# ---------------------------------------------------------------------------
class KevClient:
    def __init__(self, cache: DiskCache, url: str = KEV_URL, model: str = "kev-latest", tag: str = "kev-0.8b", timeout: float = 300.0):
        self.cache, self.url, self.model, self.tag, self.timeout = cache, url, model, tag, timeout

    def choose(self, text: str, criteria: Dict[str, str], instructions: str) -> Answer:
        payload = {"state": text, "model": self.model,
                   "questions": {"q": {"type": "choice", "instructions": instructions, "criteria": criteria}}}
        key = make_key("kev", self.tag, payload)

        def call() -> Dict[str, Any]:
            t0 = time.perf_counter()
            try:
                r = requests.post(self.url, json=payload, timeout=self.timeout)
                lat = (time.perf_counter() - t0) * 1000
                if r.status_code != 200:
                    return {"error": f"HTTP {r.status_code}: {r.text[:200]}", "latency_ms": lat}
                data = r.json()
                a = (data.get("answers") or {}).get("q") or {}
                return {"choice": a.get("choice"), "confidence": a.get("confidence"), "probabilities": a.get("probabilities") or {},
                        "usage": data.get("usage"), "server_latency_ms": data.get("latency_ms"), "latency_ms": lat, "error": ""}
            except requests.RequestException as e:
                return {"error": f"{type(e).__name__}: {e}", "latency_ms": (time.perf_counter() - t0) * 1000}

        rec = self.cache.cached(key, call, retry_errors=True)
        return kev_answer(rec, criteria)


def kev_answer(rec: Dict[str, Any], criteria: Dict[str, str]) -> Answer:
    lat = float(rec.get("latency_ms") or 0.0)
    if rec.get("error"):
        return Answer(NO_ANSWER, None, None, lat, False, rec["error"])
    choice = rec.get("choice")
    probs = {k: float(v) for k, v in (rec.get("probabilities") or {}).items() if k in criteria}
    if choice not in criteria:
        return Answer(NO_ANSWER, None, probs or None, lat, False, f"nhãn không hợp lệ: {choice!r}")
    # xác suất của nhãn chọn trong phân phối `probabilities` (cùng thang với các nhãn khác); `confidence` của server là đại lượng riêng
    p = probs.get(choice)
    return Answer(choice, p, probs or None, lat, True, "", {"server_confidence": rec.get("confidence"), "usage": rec.get("usage"),
                                                                       "server_latency_ms": rec.get("server_latency_ms")})


# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------
class OllamaClient:
    def __init__(self, cache: DiskCache, url: str = OLLAMA_URL, timeout: float = 180.0):
        self.cache, self.url, self.timeout = cache, url, timeout

    def choose(self, model: str, system: str, user: str, labels: Sequence[str], num_ctx: int = 8192, keep_alive: str = "10m") -> Answer:
        schema = {"type": "object", "properties": {"type": {"type": "string", "enum": list(labels)}}, "required": ["type"]}
        body = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "stream": False, "think": False, "format": schema, "keep_alive": keep_alive,
                "options": {"temperature": 0, "seed": 0, "num_ctx": num_ctx}, "logprobs": True, "top_logprobs": 3}
        key = make_key("ollama-chat", body)          # khóa KHÔNG gồm num_predict (chỉ là lưới an toàn chống sinh vô hạn khoảng trắng trong JSON)
        send = {**body, "options": {**body["options"], "num_predict": 96}}

        def call() -> Dict[str, Any]:
            t0 = time.perf_counter()
            try:
                r = requests.post(f"{self.url}/api/chat", json=send, timeout=self.timeout)
                lat = (time.perf_counter() - t0) * 1000
                if r.status_code != 200:
                    return {"error": f"HTTP {r.status_code}: {r.text[:200]}", "latency_ms": lat}
                d = r.json()
                return {"content": (d.get("message") or {}).get("content", ""), "logprobs": d.get("logprobs"),
                        "prompt_eval_count": d.get("prompt_eval_count"), "eval_count": d.get("eval_count"),
                        "total_duration_ms": (d.get("total_duration") or 0) / 1e6, "latency_ms": lat, "error": ""}
            except requests.RequestException as e:
                return {"error": f"{type(e).__name__}: {e}", "latency_ms": (time.perf_counter() - t0) * 1000}

        return ollama_answer(self.cache.cached(key, call, retry_errors=True), labels)     # lỗi truyền tải/timeout KHÔNG bị nhớ vĩnh viễn

    def embed(self, model: str, texts: Sequence[str], keep_alive: str = "10m") -> List[Dict[str, Any]]:
        """Một bản ghi/văn bản: {'embedding': [...], 'latency_ms': ...}. Cache theo từng văn bản."""
        out: List[Optional[Dict[str, Any]]] = []
        for t in texts:
            key = make_key("ollama-embed", model, t)

            def call(t=t) -> Dict[str, Any]:
                t0 = time.perf_counter()
                r = requests.post(f"{self.url}/api/embed", json={"model": model, "input": t, "keep_alive": keep_alive, "truncate": True}, timeout=self.timeout)
                lat = (time.perf_counter() - t0) * 1000
                r.raise_for_status()
                return {"embedding": r.json()["embeddings"][0], "latency_ms": lat}

            out.append(self.cache.cached(key, call))
        return out  # type: ignore[return-value]


def ollama_answer(rec: Dict[str, Any], labels: Sequence[str]) -> Answer:
    import json

    lat = float(rec.get("latency_ms") or 0.0)
    if rec.get("error"):
        return Answer(NO_ANSWER, None, None, lat, False, rec["error"])
    try:
        label = json.loads(rec.get("content") or "")["type"]
    except (ValueError, KeyError, TypeError):
        return Answer(NO_ANSWER, None, None, lat, False, f"JSON hỏng: {str(rec.get('content'))[:80]!r}")
    if label not in labels:
        return Answer(NO_ANSWER, None, None, lat, False, f"nhãn ngoài enum: {label!r}")
    conf = answer_logprob_conf(rec.get("logprobs"), label)
    return Answer(label, conf, None, lat, True, "", {"eval_count": rec.get("eval_count"), "prompt_eval_count": rec.get("prompt_eval_count")})


def answer_logprob_conf(logprobs: Any, label: str) -> Optional[float]:
    """Xác suất của chuỗi token tạo nên giá trị nhãn trong JSON `{"type": "<label>"}` = tích p(token) trên các token nằm trong nhãn.
    Ollama trả logprobs theo token sinh ra (nếu có); không có -> None. Đây là xác suất TRƯỚC khi chuẩn hóa lại trên các nhãn hợp lệ,
    nên là thước đo độ chắc chắn của mô hình, không phải xác suất hiệu chỉnh."""
    if not logprobs:
        return None
    toks = logprobs if isinstance(logprobs, list) else logprobs.get("content") or logprobs.get("tokens") or []
    if not toks:
        return None
    # ghép token để tìm đoạn chứa nhãn
    pieces = [(t.get("token", ""), t.get("logprob")) for t in toks]
    if any(lp is None for _, lp in pieces):
        return None
    text = "".join(p for p, _ in pieces)
    start = text.find(label)
    if start < 0:
        return None
    end = start + len(label)
    pos, total = 0, 0.0
    for p, lp in pieces:
        a, b = pos, pos + len(p)
        pos = b
        if b > start and a < end:
            total += float(lp)
    return float(math.exp(total))


# ---------------------------------------------------------------------------
# Lời nhắc
# ---------------------------------------------------------------------------
INSTR_VI = "Xác định loại của tài liệu (văn bản OCR của trang đầu) thuộc loại nào trong danh sách."


def kev_one_stage(client: KevClient, text: str, ls: LabelSet, instructions: str = INSTR_VI) -> Answer:
    return client.choose(text, {i: ls.desc[i] for i in ls.ids}, instructions)


def kev_two_stage(client: KevClient, text: str, ls: LabelSet, instructions: str = INSTR_VI) -> Answer:
    """Bước 1: chọn nhóm (<= 8 nhóm); bước 2: chọn loại trong nhóm. conf = p(nhóm) * p(loại | nhóm)."""
    g = client.choose(text, {gid: ls.group_desc[gid] for gid in ls.groups}, instructions + " (chọn nhóm tài liệu)")
    if not g.parse_ok:
        return g
    members = ls.members(g.label)
    if len(members) == 1:
        a = Answer(members[0], g.conf, None, g.latency_ms, True, "", {"group": g.label, "group_conf": g.conf})
        return a
    t = client.choose(text, {i: ls.desc[i] for i in members}, instructions + " (chọn loại trong nhóm)")
    lat = g.latency_ms + t.latency_ms
    if not t.parse_ok:
        return Answer(NO_ANSWER, None, None, lat, False, t.error, {"group": g.label})
    conf = None if (g.conf is None or t.conf is None) else g.conf * t.conf
    return Answer(t.label, conf, None, lat, True, "", {"group": g.label, "group_conf": g.conf, "type_conf": t.conf})


OLLAMA_SYSTEM = ("Bạn là hệ thống phân loại tài liệu cho một công ty kinh doanh xăng dầu tại Việt Nam. "
                 "Đọc văn bản OCR của trang đầu tài liệu rồi chọn ĐÚNG MỘT loại trong danh sách. "
                 "Chỉ dựa vào dòng tiêu đề và nội dung chính; nếu không loại nào phù hợp hãy chọn OTHER. "
                 'Trả lời bằng JSON: {"type": "<mã loại>"}.')


def ollama_user_prompt(ls: LabelSet, text: str, ids: Optional[Sequence[str]] = None, examples: Optional[Dict[str, List[str]]] = None) -> str:
    """Danh sách loại ĐỨNG TRƯỚC, văn bản tài liệu ĐỨNG SAU: phần đầu giống nhau giữa các tài liệu nên Ollama dùng lại KV-cache."""
    ids = list(ids or ls.ids)
    lines = ["Danh sách loại tài liệu (mã: mô tả):"]
    for i in ids:
        lines.append(f"- {i}: {ls.desc[i]}")
    if examples:
        lines.append("\nVí dụ (đầu văn bản -> loại):")
        for i, exs in examples.items():
            for e in exs:
                lines.append(f"* \"{e}\" -> {i}")
    lines.append("\nVăn bản tài liệu cần phân loại:\n\"\"\"\n" + text + "\n\"\"\"")
    return "\n".join(lines)


def ollama_one_stage(client: OllamaClient, model: str, text: str, ls: LabelSet, num_ctx: int, examples=None) -> Answer:
    return client.choose(model, OLLAMA_SYSTEM, ollama_user_prompt(ls, text, None, examples), ls.ids, num_ctx)


def ollama_two_stage(client: OllamaClient, model: str, text: str, ls: LabelSet, num_ctx: int) -> Answer:
    gl = LabelSet(ls.groups, ls.group_desc, {g: g for g in ls.groups}, ls.groups, ls.group_desc, ls.desc_kind)
    g = client.choose(model, OLLAMA_SYSTEM.replace("loại trong danh sách", "nhóm trong danh sách").replace("OTHER", "VAN_BAN_KHAC"),
                      ollama_user_prompt(gl, text), ls.groups, num_ctx)
    if not g.parse_ok:
        return g
    members = ls.members(g.label)
    if len(members) == 1:
        return Answer(members[0], g.conf, None, g.latency_ms, True, "", {"group": g.label})
    t = client.choose(model, OLLAMA_SYSTEM, ollama_user_prompt(ls, text, members), members, num_ctx)
    lat = g.latency_ms + t.latency_ms
    if not t.parse_ok:
        return Answer(NO_ANSWER, None, None, lat, False, t.error, {"group": g.label})
    conf = None if (g.conf is None or t.conf is None) else g.conf * t.conf
    return Answer(t.label, conf, None, lat, True, "", {"group": g.label, "group_conf": g.conf, "type_conf": t.conf})
