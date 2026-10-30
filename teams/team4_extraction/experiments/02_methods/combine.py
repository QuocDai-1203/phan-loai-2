"""combine.py - Ghép các phương pháp (không gọi thêm mô hình) và phân tích "tự nhận / từ chối" cho trường hạn (Nhóm 4, T4).

Mọi hàm nhận các "bản ghi chạy" `{unit_id: {"status", "fields": {trường: {value, normalized, page}}, "doc_type", ...}}` và trả bản ghi cùng dạng,
nên dùng chung bộ chấm. Không có dữ liệu đáp án trong các hàm ghép (trừ `oracle_ink_route`, được gắn nhãn rõ là KHÔNG triển khai được).

  cascade(a, b, c...)         giá trị đầu tiên khác null theo thứ tự ưu tiên (vd. luật rồi LLM cho trường luật bỏ trống)
  expiry_rule(name, ...)      chỉ cho trường hạn: tự nhận một ngày khi quy tắc `name` thỏa, ngược lại TỪ CHỐI (null)
  EXPIRY_RULES                các quy tắc đồng thuận giữa nguồn {regex, llm, vlm, filename}
  abstention_table(...)       với từng quy tắc: số tự nhận, đúng, SAI GIÁ TRỊ, cận trên nhị thức Clopper-Pearson của tỉ lệ sai
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import sys
from pathlib import Path

from scipy.stats import beta

_REPO = str(Path(__file__).resolve().parents[4])
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

Rows = Dict[str, Dict[str, Any]]


def _fields(r: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return (r or {}).get("fields", {}) if (r or {}).get("status") == "ok" else {}


def cascade(*row_sets: Rows, units: Optional[Iterable[str]] = None) -> Rows:
    """Với mỗi (đơn vị, trường): lấy giá trị của nguồn đầu tiên trong danh sách có giá trị. Trạng thái `ok` nếu có nguồn nào `ok`."""
    uids = list(units) if units is not None else sorted(set().union(*[set(r) for r in row_sets]))
    out: Rows = {}
    for u in uids:
        recs = [r.get(u) for r in row_sets]
        okr = [r for r in recs if r and r["status"] == "ok"]
        if not okr:
            first = next((r for r in recs if r), {"doc_type": None})
            out[u] = {"unit_id": u, "doc_type": first.get("doc_type"), "status": (first or {}).get("status", "error"), "fields": {}}
            continue
        merged: Dict[str, Any] = {}
        for name in okr[0]["fields"]:
            chosen = None
            for r in okr:
                f = r["fields"].get(name)
                if f and f.get("value"):
                    chosen = {**f, "from": r.get("_tag", "")}
                    break
            merged[name] = chosen or {"value": None, "normalized": None, "page": None}
        out[u] = {"unit_id": u, "doc_type": okr[0].get("doc_type"), "status": "ok", "fields": merged}
    return out


def tag(rows: Rows, name: str) -> Rows:
    for r in rows.values():
        r["_tag"] = name
    return rows


# --------------------------------------------------------------------------------------------------
# Quy tắc tự nhận cho trường hạn
# --------------------------------------------------------------------------------------------------
from src.extraction.expiry_rules import EXPIRY_RULES, full_date as _full  # noqa: E402  (cài đặt chuẩn nằm trong src/)


def candidates(unit: str, field: str, sources: Dict[str, Rows]) -> Dict[str, Optional[str]]:
    """{nguồn: ngày ISO đầy đủ | None} cho một (đơn vị, trường hạn)."""
    return {s: _full(((_fields(rows.get(unit)).get(field)) or {}).get("normalized")) for s, rows in sources.items()}


def expiry_rule(name: str, sources: Dict[str, Rows], base: Rows, expiry_fields: Dict[str, List[str]]) -> Rows:
    """Bản sao của `base` trong đó MỌI trường hạn được thay bằng kết quả quy tắc `name` (ngày, hoặc null = từ chối).
    `expiry_fields`: {doc_type: [tên trường hạn]}."""
    rule = EXPIRY_RULES[name]
    out: Rows = {}
    for u, r in base.items():
        rr = {**r, "fields": {k: dict(v) for k, v in r.get("fields", {}).items()}}
        for f in expiry_fields.get(r.get("doc_type"), []):
            v = rule(candidates(u, f, sources))
            rr["fields"][f] = {"value": v, "normalized": v, "page": None} if v else {"value": None, "normalized": None, "page": None}
        out[u] = rr
    return out


def cp_upper(k: int, n: int, alpha: float = 0.05) -> float:
    """Cận trên Clopper-Pearson MỘT PHÍA (1 - alpha) của tỉ lệ khi quan sát k "sai" trong n. n = 0 -> 1.0."""
    if n <= 0:
        return 1.0
    return 1.0 if k >= n else float(beta.ppf(1 - alpha, k + 1, n - k))


def n_needed(upper: float = 0.01, k: int = 0, alpha: float = 0.05) -> int:
    """Số mẫu tối thiểu để với k lần sai quan sát, cận trên một phía 95% <= `upper` (k = 0: ~ ln(alpha)/ln(1-upper) = 299 cho 1%)."""
    n = max(k + 1, 1)
    while cp_upper(k, n, alpha) > upper:
        n += 1
        if n > 100000:
            break
    return n


def abstention_table(gold: Dict[str, Dict[str, Dict[str, Any]]], types: Dict[str, str], units: Sequence[str], sources: Dict[str, Rows],
                     expiry_fields: Dict[str, List[str]], rules: Optional[Sequence[str]] = None) -> List[Dict[str, Any]]:
    """Cho mỗi quy tắc: trên mọi (đơn vị, trường hạn) có đáp án ok/not_present (illegible bị loại).
    n_emitted = số lần quy tắc TỰ NHẬN một ngày; n_correct; n_wrong = SAI GIÁ TRỊ (kể cả khi giấy không có hạn mà quy tắc vẫn ra ngày);
    n_gold = số trường có hạn thật; automation = n_correct / n_gold; wrong_upper = cận trên 95% một phía của n_wrong / n_emitted."""
    from eval.normalize import normalize_date
    rows: List[Dict[str, Any]] = []
    for name in (rules or EXPIRY_RULES):
        rule = EXPIRY_RULES[name]
        n_all = n_gold = emitted = correct = wrong = spurious = 0
        wrong_units: List[str] = []
        for u in units:
            if u not in gold:
                continue
            for f in expiry_fields.get(types[u], []):
                g = gold[u].get(f)
                if not g or g["status"] == "illegible":
                    continue
                n_all += 1
                gv = normalize_date(g["value"]) if g["status"] == "ok" and g["value"] else None
                n_gold += int(gv is not None)
                v = rule(candidates(u, f, sources))
                if not v:
                    continue
                emitted += 1
                if gv is not None and v == gv:
                    correct += 1
                else:
                    wrong += 1
                    spurious += int(gv is None)
                    wrong_units.append(u)
        rows.append({"rule": name, "n_fields": n_all, "n_gold_present": n_gold, "n_emitted": emitted, "n_correct": correct, "n_wrong": wrong,
                     "n_spurious": spurious, "automation": (correct / n_gold) if n_gold else math.nan,
                     "emit_share": (emitted / n_all) if n_all else math.nan,
                     "wrong_rate": (wrong / emitted) if emitted else math.nan, "wrong_upper95": cp_upper(wrong, emitted) if emitted else math.nan,
                     "wrong_units": sorted(set(wrong_units))})
    return rows


def cascade_typed(regex: Rows, llm: Rows, ftypes: Dict[str, Dict[str, str]], units: Iterable[str], llm_first: Sequence[str] = ("text",)) -> Rows:
    """Ghép theo KIỂU trường: kiểu trong `llm_first` (mặc định: văn bản) ưu tiên LLM rồi mới luật; các kiểu khác (ngày/số/mã) ưu tiên luật rồi mới LLM."""
    out: Rows = {}
    for u in units:
        r, l = regex.get(u), llm.get(u)
        okr = [x for x in (r, l) if x and x["status"] == "ok"]
        if not okr:
            first = r or l or {"doc_type": None}
            out[u] = {"unit_id": u, "doc_type": first.get("doc_type"), "status": first.get("status", "error"), "fields": {}}
            continue
        dt = okr[0].get("doc_type")
        merged: Dict[str, Any] = {}
        for name in okr[0]["fields"]:
            typ = ftypes.get(dt, {}).get(name, "text")
            order = [l, r] if typ in llm_first else [r, l]
            chosen = None
            for x in order:
                f = ((x or {}).get("fields") or {}).get(name) if x and x["status"] == "ok" else None
                if f and f.get("value"):
                    chosen = dict(f)
                    break
            merged[name] = chosen or {"value": None, "normalized": None, "page": None}
        out[u] = {"unit_id": u, "doc_type": dt, "status": "ok", "fields": merged}
    return out


def review_queue_stats(gold, types, units, sources, expiry_fields, rule_name: str) -> Dict[str, int]:
    """Với quy tắc `rule_name`: các trường hạn KHÔNG được tự nhận (chuyển người duyệt) — bao nhiêu có đáp án hạn thật, bao nhiêu có gợi ý
    (ngày đầu tiên tìm được theo thứ tự luật, LLM, VLM), và gợi ý đó đúng bao nhiêu lần."""
    from eval.normalize import normalize_date
    rule = EXPIRY_RULES[rule_name]
    n_review = n_gold = n_sug = n_sug_ok = n_nogold_sug = 0
    for u in units:
        if u not in gold:
            continue
        for f in expiry_fields.get(types[u], []):
            g = gold[u].get(f)
            if not g or g["status"] == "illegible":
                continue
            c = candidates(u, f, sources)
            if rule(c):
                continue
            n_review += 1
            gv = normalize_date(g["value"]) if g["status"] == "ok" and g["value"] else None
            n_gold += int(gv is not None)
            sug = next((c[k] for k in ("regex", "llm", "vlm") if c.get(k)), None)
            if sug:
                n_sug += 1
                n_sug_ok += int(gv is not None and sug == gv)
                n_nogold_sug += int(gv is None)
    return {"n_review": n_review, "n_review_gold_present": n_gold, "n_with_suggestion": n_sug, "n_suggestion_correct": n_sug_ok,
            "n_suggestion_where_no_expiry": n_nogold_sug}
