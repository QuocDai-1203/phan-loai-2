"""lib.py - Hạ tầng chạy và chấm các phương pháp trích xuất trên đáp án silver (Nhóm 4, T4).

* `load_gold()`   đáp án silver đã gộp (`gold/fields_silver_v1.jsonl`) -> {unit: {trường: {value, status, review_status, ink, page}}}.
                  Trường chỉ-ghi-thời-hạn (`chi_ghi_thoi_han`, không có ngày cụ thể) coi là not_present cho trường ngày.
* `run_config()`  chạy một cấu hình `phương_pháp@nguồn_văn_bản` trên danh sách đơn vị, ghi dần vào `_cache/preds/<cấu hình>.jsonl`
                  (chạy lại thì dùng tiếp; `force=True` xóa làm lại). Dự đoán có thể chứa họ tên: thư mục `_cache/` bị .gitignore.
* `score_*`       chấm bằng `eval/field_metrics.py` (4 chế độ so sánh) theo loại tài liệu / kiểu trường / mực viết.
KHÔNG đọc nội dung TEST bằng mắt: mọi hàm ở đây chỉ trả số tổng hợp.
"""

from __future__ import annotations

import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
TEAM = HERE.parents[1]
REPO = TEAM.parents[1]
for _p in (str(TEAM), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from eval.field_metrics import FieldSpec, compare_field, load_specs, score  # noqa: E402
from eval.normalize import fold_text, normalize_value  # noqa: E402
from methods.common import MethodResult, Unit, load_units  # noqa: E402

GOLD_JSONL = TEAM / "gold" / "fields_silver_v1.jsonl"
PRED_DIR = HERE / "_cache" / "preds"
SOURCES = ("ocr_v2", "ocr_llm_haiku", "text_layer")


# --------------------------------------------------------------------------------------------------
# Đáp án
# --------------------------------------------------------------------------------------------------
def load_gold(path: Path = GOLD_JSONL, specs: Optional[Dict[str, List[FieldSpec]]] = None,
              review_statuses: Optional[Iterable[str]] = None) -> Tuple[Dict[str, Dict[str, Dict[str, Any]]], Dict[str, str], Dict[str, str]]:
    """-> (gold, unit_types, unit_split). `review_statuses`: chỉ giữ trường có `review_status` thuộc tập này (còn lại: bị loại khỏi điểm)."""
    specs = specs or load_specs()
    keep = set(review_statuses) if review_statuses else None
    gold: Dict[str, Dict[str, Dict[str, Any]]] = {}
    types: Dict[str, str] = {}
    split: Dict[str, str] = {}
    for line in open(path, encoding="utf-8"):
        m = json.loads(line)
        uid = m["unit_id"]
        types[uid], split[uid] = m["doc_type"], m["split"]
        sp = {s.name: s for s in specs[m["doc_type"]]}
        g: Dict[str, Dict[str, Any]] = {}
        for name, r in m["fields"].items():
            if name not in sp:
                continue
            status, value = r.get("status"), r.get("value")
            if status is None or (keep is not None and r["review_status"] not in keep):
                status, value = "illegible", None          # không có đáp án đáng tin: loại khỏi điểm
            elif r.get("note") and "chi_ghi_thoi_han" in str(r["note"]) and sp[name].type == "date":
                status, value = "not_present", None        # giấy chỉ ghi thời hạn, không có ngày cụ thể
            g[name] = {"value": value, "status": status, "review_status": r["review_status"], "ink": r.get("ink"), "page": r.get("page")}
        # "từ ngày ký": ngày bắt đầu hiệu lực = ngày ký; quy về giá trị ngày của trường ngay_ky để so được với phương pháp trả ngày cụ thể
        for name, r in g.items():
            if sp[name].type == "date" and r["status"] == "ok" and r["value"] and "ngay_ky" in g and g["ngay_ky"]["status"] == "ok":
                nv = normalize_value(r["value"], "date")
                if nv and nv.startswith("~raw:") and re.search(r"ngay k[yi]", fold_text(r["value"])):
                    r["value"] = g["ngay_ky"]["value"]
        # giá trị ngày/số/mã chỉ đọc được một phần ("[?]"): không có đáp án đầy đủ -> loại khỏi điểm (như illegible)
        for name, r in g.items():
            if sp[name].type in ("date", "number", "id") and r["status"] == "ok" and r["value"] and "[?]" in r["value"]:
                r["status"], r["value"] = "illegible", None
        # trường ngày mà người chú thích chỉ chép cụm không có ngày cụ thể (vd. "05 năm kể từ ngày cấp"): coi là KHÔNG có ngày cụ thể
        for name, r in g.items():
            if sp[name].type == "date" and r["status"] == "ok" and r["value"]:
                nv = normalize_value(r["value"], "date")
                if nv and nv.startswith("~raw:") and "..." not in r["value"]:
                    r["status"], r["value"] = "not_present", None
        gold[uid] = g
    return gold, types, split


def restrict_gold_pages(gold: Dict[str, Dict[str, Dict[str, Any]]], max_page: int) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Cho nguồn văn bản chỉ có `max_page` trang đầu (bản chép Haiku: 2 trang): trường có đáp án ở trang > max_page bị loại khỏi điểm."""
    out = {}
    for uid, g in gold.items():
        out[uid] = {n: ({**r, "status": "illegible", "value": None} if (r["status"] == "ok" and (r.get("page") or 0) > max_page) else r)
                    for n, r in g.items()}
    return out


# --------------------------------------------------------------------------------------------------
# Chạy phương pháp
# --------------------------------------------------------------------------------------------------
def make_method(name: str, source: str, **kw: Any):
    if name == "regex":
        from methods.regex_rules import RegexRules
        return RegexRules(source, **kw)
    if name == "filename":
        from methods.filename_date import FilenameDate
        return FilenameDate(**kw)
    if name == "gliner":
        from methods.gliner_fields import GlinerFields
        return GlinerFields(source, **kw)
    if name == "llm":
        from methods.local_llm_json import LocalLlmJson
        return LocalLlmJson(source, **kw)
    if name == "vlm":
        from methods.local_vlm_json import LocalVlmJson
        return LocalVlmJson(**kw)
    raise ValueError(f"phương pháp không biết: {name}")


def cfg_name(method: str, source: str) -> str:
    return method if method in ("filename", "vlm") else f"{method}@{source}"


def _load_rows(path: Path) -> Dict[str, Dict[str, Any]]:
    rows: Dict[str, Dict[str, Any]] = {}
    if path.exists():
        for line in open(path, encoding="utf-8"):
            r = json.loads(line)
            rows[r["unit_id"]] = r
    return rows


def run_config(method: str, source: str, units: List[Unit], tag: str = "", force: bool = False, verbose: bool = True, **kw: Any) -> Dict[str, Dict[str, Any]]:
    """Chạy `method` trên `units` (dùng tiếp phần đã có). Trả {unit_id: bản ghi}. `tag`: hậu tố tên tệp cho các biến thể (vd. 'v2')."""
    PRED_DIR.mkdir(parents=True, exist_ok=True)
    path = PRED_DIR / f"{cfg_name(method, source)}{('.' + tag) if tag else ''}.jsonl"
    if force and path.exists():
        path.unlink()
    rows = _load_rows(path)
    todo = [u for u in units if u.unit_id not in rows]
    if not todo:
        return {u.unit_id: rows[u.unit_id] for u in units}
    m = make_method(method, source, **kw)
    t0 = time.time()
    with open(path, "a", encoding="utf-8") as f:
        for i, u in enumerate(todo, 1):
            r: MethodResult = m.run(u)
            lc = getattr(m, "last_call", {}) or {}
            rec = {"unit_id": u.unit_id, "doc_type": u.doc_type, "status": r.status, "error": r.error, "latency_ms": r.latency_ms,
                   "orig_latency_ms": lc.get("latency_ms", r.latency_ms), "fields": r.fields,
                   "meta": {k: lc.get(k) for k in ("cached", "prompt_eval_count", "eval_count", "n_images_sent", "total_duration", "load_duration")}}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            rows[u.unit_id] = rec
            if verbose and (i % 10 == 0 or i == len(todo)):
                print(f"  [{cfg_name(method, source)}] {i}/{len(todo)} ({time.time() - t0:.0f}s) last status={r.status}", flush=True)
    return {u.unit_id: rows[u.unit_id] for u in units}


def sanitize_rows(rows: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Ngày/số không phân tích được -> null (cùng quy tắc với methods.common.set_value; áp lại khi đọc để các bản chạy cũ cũng nhất quán)."""
    specs = load_specs()
    for r in rows.values():
        typ = {s.name: s.type for s in specs.get(r.get("doc_type"), [])}
        for name, f in (r.get("fields") or {}).items():
            n = f.get("normalized")
            if typ.get(name) in ("date", "number") and isinstance(n, str) and n.startswith("~raw:"):
                f.update({"value": None, "normalized": None, "page": None, "rejected_unparseable": True})
    return rows


def load_preds(method: str, source: str, tag: str = "") -> Dict[str, Dict[str, Any]]:
    return sanitize_rows(_load_rows(PRED_DIR / f"{cfg_name(method, source)}{('.' + tag) if tag else ''}.jsonl"))


def to_pred(rows: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Bản ghi chạy -> dạng cho bộ chấm: đơn vị lỗi/bỏ qua = {"_status": ...} (bị chấm như dự đoán toàn null và đếm ở n_failed)."""
    return {uid: ({"_status": "ok", "fields": r["fields"]} if r["status"] == "ok" else {"_status": r["status"]}) for uid, r in rows.items()}


# --------------------------------------------------------------------------------------------------
# Chấm
# --------------------------------------------------------------------------------------------------
def sub(d: Dict[str, Any], keep: Iterable[str]) -> Dict[str, Any]:
    ks = set(keep)
    return {k: v for k, v in d.items() if k in ks}


def score_cfg(gold, pred, types, units: Iterable[str], mode: str = "normalized", n_boot: int = 1000, specs=None, **kw: Any) -> Dict[str, Any]:
    us = [u for u in units if u in gold]
    return score(sub(gold, us), sub(pred, us), sub(types, us), specs or load_specs(), mode=mode, n_boot=n_boot, **kw)


def by_ink(gold, pred, types, units: Iterable[str], mode: str = "normalized", specs=None) -> Dict[str, Dict[str, int]]:
    """Theo mực viết của đáp án silver (printed / handwritten / under_stamp): số trường có đáp án, đúng, bỏ trống, SAI GIÁ TRỊ. Không gồm PII."""
    specs = specs or load_specs()
    out: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for uid in units:
        if uid not in gold:
            continue
        sp = {s.name: s for s in specs[types[uid]]}
        p = pred.get(uid)
        pf = (p.get("fields", p) if isinstance(p, dict) and p.get("_status", "ok") == "ok" else {}) or {}
        for name, g in gold[uid].items():
            s = sp.get(name)
            if not s or not s.scored or s.is_pii or g["status"] != "ok":
                continue
            res = compare_field(g, pf.get(name), s, mode)
            ink = g.get("ink") or "unknown"
            out[ink]["n"] += 1
            out[ink][{"tp": "correct", "empty": "empty", "wrong": "wrong"}.get(res, res)] += 1
    return {k: dict(v) for k, v in out.items()}


def field_outcomes(gold, pred, types, units: Iterable[str], mode: str = "normalized", specs=None) -> Dict[Tuple[str, str], str]:
    """{(unit, trường): 'tp'|'wrong'|'empty'|'spurious'|'tn'|'skip'} cho mọi trường không PII (dùng để so ghép cặp, phân tích từ chối)."""
    specs = specs or load_specs()
    out = {}
    for uid in units:
        if uid not in gold:
            continue
        sp = {s.name: s for s in specs[types[uid]]}
        p = pred.get(uid)
        pf = (p.get("fields", p) if isinstance(p, dict) and p.get("_status", "ok") == "ok" else {}) or {}
        for name, g in gold[uid].items():
            s = sp.get(name)
            if s and s.scored and not s.is_pii:
                out[(uid, name)] = compare_field(g, pf.get(name), s, mode)
    return out
