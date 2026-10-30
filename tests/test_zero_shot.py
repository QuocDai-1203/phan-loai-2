"""Kiểm thử phần thuần của zero_shot.py và llm_cache.py (không gọi mạng)."""
import json
import math

from src.classification.llm_cache import DiskCache, make_key
from src.classification.zero_shot import (NO_ANSWER, Answer, answer_logprob_conf, build_label_set, kev_answer, ollama_answer,
                                          ollama_user_prompt)

TAX = {"groups": [{"id": "G1", "name_vi": "Nhóm 1", "description": "mô tả nhóm 1"}, {"id": "G2", "name_vi": "Nhóm 2", "description": "d2"}],
       "classes": [{"id": "A", "name_vi": "Loại A", "group": "G1", "description": "mô tả dài A", "short_description": "ngắn A", "deciding_cue": "cue A"},
                   {"id": "B", "name_vi": "Loại B", "group": "G1", "description": "mô tả dài B", "short_description": "ngắn B"},
                   {"id": "OTHER", "name_vi": "Khác", "group": "G2", "description": "khác", "short_description": "khác"},
                   {"id": "UNREADABLE", "name_vi": "Hỏng", "group": "G2", "description": "x", "short_description": "x"}]}


def test_cache_roundtrip_and_hits(tmp_path):
    c = DiskCache(tmp_path)
    calls = []
    k = make_key("m", {"a": 1, "b": "đ"})
    assert k == make_key("m", {"b": "đ", "a": 1})            # thứ tự khóa không ảnh hưởng
    f = lambda: calls.append(1) or {"x": 1, "latency_ms": 5.0}
    assert c.cached(k, f)["x"] == 1 and c.cached(k, f)["latency_ms"] == 5.0
    assert len(calls) == 1 and c.hits == 1 and c.misses == 1


def test_cache_retry_errors(tmp_path):
    c = DiskCache(tmp_path)
    c.put("ab" + "0" * 62, {"error": "boom"})
    n = []
    assert c.cached("ab" + "0" * 62, lambda: n.append(1) or {"ok": 1}, retry_errors=True)["ok"] == 1 and n


def test_label_set_short_long_and_exclude():
    s = build_label_set(TAX, "short")
    assert s.ids == ["A", "B", "OTHER"] and s.desc["A"] == "ngắn A" and s.groups == ["G1", "G2"]
    l = build_label_set(TAX, "long")
    assert "cue A" in l.desc["A"] and l.desc["B"] == "mô tả dài B"
    assert s.members("G1") == ["A", "B"]


def test_kev_answer_uses_probability_of_choice():
    crit = {"A": "a", "B": "b"}
    ans = kev_answer({"choice": "A", "confidence": 0.5, "probabilities": {"A": 0.7, "B": 0.3}, "latency_ms": 12.0, "error": ""}, crit)
    assert ans.label == "A" and abs(ans.conf - 0.7) < 1e-9 and ans.parse_ok and ans.latency_ms == 12.0
    bad = kev_answer({"choice": "ZZZ", "probabilities": {}, "latency_ms": 1.0, "error": ""}, crit)
    assert bad.label == NO_ANSWER and not bad.parse_ok
    assert kev_answer({"error": "HTTP 500", "latency_ms": 3.0}, crit).label == NO_ANSWER


def test_ollama_parse_and_logprob_conf():
    toks = [{"token": '{"', "logprob": -0.1}, {"token": "type", "logprob": -0.0}, {"token": '":"', "logprob": -0.0},
            {"token": "HD", "logprob": math.log(0.5)}, {"token": "_MUA", "logprob": math.log(0.8)}, {"token": '"}', "logprob": -0.0}]
    assert abs(answer_logprob_conf(toks, "HD_MUA") - 0.4) < 1e-9
    assert answer_logprob_conf(None, "A") is None
    rec = {"content": json.dumps({"type": "A"}), "logprobs": None, "latency_ms": 7.0, "error": ""}
    a = ollama_answer(rec, ["A", "B"])
    assert a.label == "A" and a.conf is None and a.parse_ok
    assert ollama_answer({"content": "not json", "latency_ms": 1.0, "error": ""}, ["A"]).label == NO_ANSWER
    assert ollama_answer({"content": '{"type":"Z"}', "latency_ms": 1.0, "error": ""}, ["A"]).label == NO_ANSWER


def test_prompt_puts_labels_before_document_for_kv_cache():
    s = build_label_set(TAX, "short")
    p1 = ollama_user_prompt(s, "văn bản 1")
    p2 = ollama_user_prompt(s, "văn bản 2")
    i = p1.index("Văn bản tài liệu")
    assert p1[:i] == p2[:p2.index("Văn bản tài liệu")]          # phần đầu giống hệt -> tái dùng KV-cache
    assert "- A: ngắn A" in p1


class _Resp:
    def __init__(self, payload, status=200):
        self._p, self.status_code = payload, status

    def json(self):
        return self._p


def test_fetch_kev_model_name_new_and_old_server(monkeypatch):
    import requests as rq

    from src.classification.zero_shot import fetch_kev_model_name

    new = {"models": [{"name": "kev-latest", "run": "jaredpalmer/kev-0.8b"}]}

    def get_new(url, timeout=None):
        assert url.endswith("/v1/models")
        return _Resp(new)

    monkeypatch.setattr(rq, "get", get_new)
    assert fetch_kev_model_name("http://h:8009/v1/systemone") == "jaredpalmer/kev-0.8b"

    def get_old(url, timeout=None):                       # máy chủ demo cũ: /v1/models 404, /api/status có current_model
        return _Resp({}, 404) if url.endswith("/v1/models") else _Resp({"current_model": "jaredpalmer/kev-4b"})

    monkeypatch.setattr(rq, "get", get_old)
    assert fetch_kev_model_name("http://h:8009") == "jaredpalmer/kev-4b"

    def boom(url, timeout=None):
        raise rq.ConnectionError("down")

    monkeypatch.setattr(rq, "get", boom)
    assert fetch_kev_model_name("http://h:8009") is None
