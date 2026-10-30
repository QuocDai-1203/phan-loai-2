"""merge_silver.py - Gộp đáp án silver của các người chú thích thành `fields_silver_v1.jsonl` + `silver_report.md` (Nhóm 4, T2).

Chạy (từ gốc repo, sau khi các người chú thích đã ghi `gold/silver_raw/<annotator>/<unit_id>.json`):
    .venv\\Scripts\\python.exe -X utf8 teams\\team4_extraction\\gold\\merge_silver.py [--primary haiku]

Việc làm:
  1. Kiểm từng tệp thô, theo MỨC TRƯỜNG khi có thể:
       * làm hỏng cả đơn vị (đơn vị bị bỏ khỏi người đó): JSON hỏng, sai unit_id/doc_type, thiếu khóa `fields`, bản ghi `error`;
       * làm hỏng MỘT TRƯỜNG (trường đó bị bỏ khỏi người đó, các trường còn lại giữ): thiếu trường, status lạ, `page` không nằm trong
         các trang được cho xem, ghi giá trị PII (vi phạm quy tắc 7), `ok` mà không có giá trị, có giá trị mà status không phải `ok`;
       * chỉ CẢNH BÁO (đếm, giữ nguyên dữ liệu): `evidence` quá 12 từ (cắt còn 12 từ), `ink` lạ (bỏ `ink`), `ok` mà không có `page`.
  2. Chuẩn hóa `value` bằng eval/normalize.py (KHÔNG tin `normalized` của người chú thích; chỉ đếm số lần lệch).
  3. Mỗi (đơn vị, trường), hai người cùng hợp lệ:
       * bằng nhau sau chuẩn hóa ("chặt")                           -> `agreed_unverified`, `agreement = strict`
       * kiểu `text`: bằng nhau theo so sánh MỀM (NFC, chữ thường, bỏ dấu tiếng Việt, bỏ dấu câu, chứa nhau, trường 'tên + MST')
                                                                     -> `agreed_unverified`, `agreement = lenient`
       * khác nhau hoặc một bên null                                 -> `needs_human`
       * chỉ một người                                               -> `single_annotator`
     Báo cáo in số liệu chặt và mềm cạnh nhau; định nghĩa "chặt" không đổi.
     Cờ `ink_risk` (chữ viết tay/dưới con dấu theo bất kỳ người nào) đánh dấu trường PHẢI được xem lại dù hai bên đồng thuận.
  4. Nếu có `gold/adjudication/out/` (do `build_adjudication.py` + người đọc thứ ba), trường đã phân xử được đặt
     `review_status = model_adjudicated` với giá trị của người phân xử — KHÔNG BAO GIỜ là `human_verified` (đó là việc của người thật).
  5. Ghi JSONL (mọi giá trị PII bị bỏ: `value_withheld = true`) và báo cáo Markdown (chỉ số tổng hợp + mã đơn vị; KHÔNG in giá trị trường nào).
     Kiểm chéo hạn với ngày trong tên tệp chỉ là KIỂM CHÉO (đếm khớp/lệch), không phải đáp án.

`agreed_unverified` và `model_adjudicated` KHÔNG phải sự thật: mô hình có thể cùng sai. Chỉ `human_verified` (bước kiểm tay, ngoài script này) là đáp án cuối.
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
TEAM = HERE.parent
REPO = TEAM.parents[1]
sys.path.insert(0, str(TEAM))

from eval.field_metrics import wilson_interval  # noqa: E402
from eval.normalize import lenient_text_equal, normalize_text, normalize_value  # noqa: E402
from methods.filename_date import filename_date  # noqa: E402

STATUSES = ("ok", "not_present", "illegible")
INKS = ("printed", "handwritten", "under_stamp")
FIELD_KEYS = ("value", "normalized", "page", "evidence", "ink", "status", "note")
DEFAULT_PRIMARY = "haiku"
MAX_EVIDENCE_WORDS = 12
VERDICTS_2 = ("x_correct", "y_correct", "both_equivalent", "neither")
VERDICTS_1 = ("x_correct", "neither")
ADJ_DIR = HERE / "adjudication"


# --------------------------------------------------------------------------------------------------
# Tải schema / đơn vị
# --------------------------------------------------------------------------------------------------
def load_schemas(schema_dir: Path) -> Dict[str, Dict[str, Any]]:
    out = {}
    for p in schema_dir.glob("*.json"):
        s = json.loads(p.read_text(encoding="utf-8"))
        if "x-fields" in s:
            out[s["x-doc_type"]] = s
    return out


def load_units(path: Path) -> Dict[str, Dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as f:
        return {r["unit_id"]: r for r in csv.DictReader(f)}


def _scrub(msg: str, limit: int = 120) -> str:
    """Rút gọn thông báo lỗi và che chuỗi số dài (phòng người chú thích lỡ đưa số định danh vào lời nhắn)."""
    return re.sub(r"\d{5,}", "#", str(msg))[:limit]


# --------------------------------------------------------------------------------------------------
# Kiểm hợp lệ (mức trường)
# --------------------------------------------------------------------------------------------------
def clean_unit(obj: Any, schema: Dict[str, Any], unit: Dict[str, str]
               ) -> Tuple[Optional[Dict[str, Any]], List[str], Dict[str, List[str]], List[str], bool]:
    """Trả (obj_sạch | None, lỗi_cả_đơn_vị, {trường: [lỗi]}, cảnh_báo, là_bản_ghi_lỗi).

    `obj_sạch` giữ các trường hợp lệ (đã cắt evidence, đã bỏ ink lạ); trường lỗi mức trường bị LOẠI khỏi obj_sạch."""
    warns: List[str] = []
    if not isinstance(obj, dict):
        return None, ["not_an_object"], {}, warns, False
    fatal: List[str] = []
    if obj.get("unit_id") != unit["unit_id"]:
        fatal.append("unit_id_mismatch")
    if "error" in obj:
        bad = not (isinstance(obj["error"], str) and obj["error"].strip())
        return None, (["empty_error"] if bad else []) + fatal, {}, warns, True
    if obj.get("doc_type") not in (None, unit["doc_type"]):
        fatal.append("doc_type_mismatch")
    fields = obj.get("fields")
    if not isinstance(fields, dict):
        return None, fatal + ["fields_missing"], {}, warns, False
    if fatal:
        return None, fatal, {}, warns, False
    shown = {int(x) for x in unit["shown_pages"].split(";") if x}
    keep: Dict[str, Any] = {}
    issues: Dict[str, List[str]] = {}
    for f in schema["x-fields"]:
        name, pol = f["name"], f.get("silver_policy", "transcribe")
        if name not in fields:
            if pol != "skip":
                issues.setdefault(name, []).append("missing_field")
            continue
        r = fields[name]
        bad: List[str] = []
        if not isinstance(r, dict):
            issues.setdefault(name, []).append("bad_field")
            continue
        if r.get("status") not in STATUSES:
            issues.setdefault(name, []).append("bad_status")
            continue
        r = dict(r)
        pg = r.get("page")
        if pg is not None and (isinstance(pg, bool) or not isinstance(pg, int)):
            bad.append("bad_page")
        elif isinstance(pg, int) and pg not in shown:
            bad.append("page_not_shown")
        val = r.get("value")
        if pol == "withhold_value":
            if val is not None or r.get("normalized") is not None or r.get("evidence") is not None:
                bad.append("pii_value_present")          # quy tắc 7
        elif pol != "skip":
            if r["status"] == "ok" and (val is None or not str(val).strip()):
                bad.append("ok_without_value")
            if r["status"] != "ok" and val is not None:
                bad.append("value_with_nonok_status")
        if bad:
            issues[name] = bad
            continue
        # chỉ cảnh báo
        if r.get("ink") not in INKS + (None,):
            warns.append("bad_ink")
            r["ink"] = None
        ev = r.get("evidence")
        if ev is not None:
            words = str(ev).split()
            if len(words) > MAX_EVIDENCE_WORDS:
                warns.append("evidence_too_long")
                r["evidence"] = " ".join(words[:MAX_EVIDENCE_WORDS])
        if r["status"] == "ok" and pg is None and pol != "skip":
            warns.append("ok_without_page")
        keep[name] = r
    out = dict(obj)
    out["fields"] = keep
    return out, [], issues, warns, False


def validate_unit(obj: Any, schema: Dict[str, Any], unit: Dict[str, str]) -> Tuple[List[str], bool]:
    """Tương thích ngược: (danh sách lỗi gồm cả lỗi mức trường dạng 'lỗi:trường', là_bản_ghi_lỗi). Chỉ để kiểm tra nhanh/test."""
    _o, fatal, issues, _w, is_err = clean_unit(obj, schema, unit)
    return fatal + [f"{r}:{n}" for n, rs in issues.items() for r in rs], is_err


# --------------------------------------------------------------------------------------------------
# Khóa so sánh
# --------------------------------------------------------------------------------------------------
def _key(rec: Dict[str, Any], f: Dict[str, Any]) -> str:
    """Khóa so sánh CHẶT của một bản ghi trường: chuỗi chuẩn hóa, hoặc '∅' (not_present), hoặc '?' (illegible)."""
    if rec["status"] == "not_present":
        return "∅"
    if rec["status"] == "illegible":
        return "?"
    if f.get("silver_policy") == "withhold_value":
        return "present"                                   # chỉ biết có mặt, không có giá trị để so
    if rec.get("note") and "chi_ghi_thoi_han" in str(rec["note"]):
        return "duration:" + (normalize_text(rec.get("value")) or "")
    return normalize_value(rec.get("value"), f["type"], f.get("id_kind")) or "∅"


def agreement_level(recs: List[Dict[str, Any]], f: Dict[str, Any]) -> Optional[str]:
    """'strict' | 'lenient' | None cho các bản ghi của cùng một trường (>= 2 bản)."""
    keys = [_key(r, f) for r in recs]
    if all(k == keys[0] for k in keys) and keys[0] != "?":
        return "strict"
    if (f["type"] == "text" and f.get("silver_policy") != "withhold_value" and all(r["status"] == "ok" for r in recs)
            and all(lenient_text_equal(recs[0].get("value"), r.get("value")) for r in recs[1:])):
        return "lenient"
    return None


def _norm_mismatch(rec: Dict[str, Any], f: Dict[str, Any]) -> bool:
    if rec["status"] != "ok" or f.get("is_pii") or f.get("silver_policy") == "withhold_value" or rec.get("normalized") is None:
        return False
    mine = normalize_value(rec.get("value"), f["type"], f.get("id_kind"))
    theirs = normalize_value(str(rec["normalized"]), f["type"], f.get("id_kind"))
    return mine != theirs


# --------------------------------------------------------------------------------------------------
# Gộp
# --------------------------------------------------------------------------------------------------
def merge_unit(unit: Dict[str, str], schema: Dict[str, Any], raws: Dict[str, Dict[str, Any]], primary: str) -> Dict[str, Any]:
    """raws: {annotator: tệp thô đã làm sạch (có 'fields')}. Trả bản ghi đã gộp (không có giá trị PII)."""
    names = sorted(raws, key=lambda a: (a != primary, a))
    out_fields: Dict[str, Any] = {}
    for f in schema["x-fields"]:
        name = f["name"]
        if f.get("silver_policy") == "skip":
            continue
        recs = {a: raws[a]["fields"][name] for a in names if name in raws[a]["fields"]}
        if not recs:
            out_fields[name] = {"value": None, "normalized": None, "status": None, "review_status": "no_valid_reading", "review_reasons": [],
                                "agreement": None, "page": None, "ink": None, "note": None, "value_withheld": bool(f.get("is_pii")),
                                "by_annotator": {}, "_keys": {}, "_agree": None}
            continue
        keys = {a: _key(r, f) for a, r in recs.items()}
        pa = next(iter(recs))
        pr = recs[pa]
        reasons: List[str] = []
        level: Optional[str] = None
        if len(recs) >= 2:
            level = agreement_level(list(recs.values()), f)
            if level:
                review = "agreed_unverified"
            else:
                review = "needs_human"
                nullish = [k in ("∅", "?") for k in keys.values()]
                reasons.append("one_null" if any(nullish) and not all(nullish) else "disagree")
        else:
            review = "single_annotator"
        inks = {r.get("ink") for r in recs.values() if r.get("ink")}
        if inks & {"handwritten", "under_stamp"}:
            reasons.append("ink_risk")
        pii = f.get("is_pii")
        value = None if pii else pr.get("value")
        if pr["status"] == "ok" and not pii and f.get("silver_policy") != "withhold_value":
            normalized = normalize_value(pr.get("value"), f["type"], f.get("id_kind"))
        else:
            normalized = None
        out_fields[name] = {
            "value": value, "normalized": normalized, "status": pr["status"], "review_status": review, "agreement": level,
            "review_reasons": reasons, "page": pr.get("page"),
            "ink": sorted(inks)[0] if len(inks) == 1 else ("|".join(sorted(inks)) or None),
            "note": pr.get("note"), "value_withheld": bool(pii),
            "by_annotator": {a: {"status": r["status"], "ink": r.get("ink"), "page": r.get("page"), "key_is_null": keys[a] in ("∅", "?"),
                                 "norm_mismatch": _norm_mismatch(r, f),
                                 "evidence": None if pii else r.get("evidence")} for a, r in recs.items()},
            "_keys": keys, "_agree": level,                  # chỉ dùng nội bộ để tính báo cáo, bị xóa trước khi ghi
        }
    return {"unit_id": unit["unit_id"], "doc_id": unit["doc_id"], "doc_type": unit["doc_type"], "split": unit["split"],
            "annotators": names, "primary": names[0], "shown_pages": unit["shown_pages"], "fields": out_fields}


def collect(raw_dir: Path, units: Dict[str, Dict[str, str]], schemas: Dict[str, Dict[str, Any]]):
    """Đọc silver_raw/*/ -> (valid {unit: {annotator: obj sạch}}, stat {annotator: Counter}, problems [(annotator, unit, lý do)] mức đơn vị,
    field_issues [(annotator, unit, trường, lý do)], warns {annotator: Counter})."""
    valid: Dict[str, Dict[str, Any]] = defaultdict(dict)
    stat: Dict[str, Counter] = {}
    problems: List[Tuple[str, str, str]] = []
    field_issues: List[Tuple[str, str, str, str]] = []
    warns: Dict[str, Counter] = {}
    if not raw_dir.exists():
        return valid, stat, problems, field_issues, warns
    for adir in sorted(p for p in raw_dir.iterdir() if p.is_dir()):
        a = adir.name
        c = stat.setdefault(a, Counter())
        wc = warns.setdefault(a, Counter())
        seen = set()
        for p in sorted(adir.glob("*.json")):
            uid = p.stem
            if uid not in units:
                c["unknown_unit_file"] += 1
                problems.append((a, uid, "unknown_unit"))
                continue
            seen.add(uid)
            try:
                obj = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                c["invalid"] += 1
                problems.append((a, uid, f"unreadable_json:{type(e).__name__}"))
                continue
            clean, fatal, issues, w, is_err = clean_unit(obj, schemas[units[uid]["doc_type"]], units[uid])
            if is_err and not fatal:
                c["error_record"] += 1
                problems.append((a, uid, "error_record:" + _scrub(obj["error"])))
            elif fatal or clean is None:
                c["invalid"] += 1
                problems.append((a, uid, "invalid:" + ",".join(fatal[:6])))
            else:
                c["ok"] += 1
                valid[uid][a] = clean
                for wn in w:
                    wc[wn] += 1
                if issues:
                    c["units_with_field_issues"] += 1
                for fld, rs in issues.items():
                    for r in rs:
                        field_issues.append((a, uid, fld, r))
        c["missing"] = len(set(units) - seen)
    return valid, stat, problems, field_issues, warns


# --------------------------------------------------------------------------------------------------
# Phân xử bởi người đọc thứ ba (mô hình mạnh hơn) — KHÔNG phải human_verified
# --------------------------------------------------------------------------------------------------
def validate_adjudication(obj: Any, item: Dict[str, Any], key: Dict[str, Any]) -> List[str]:
    """Lỗi của một tệp phân xử (rỗng nếu hợp lệ). `item` lấy từ queue.json, `key` từ key.json."""
    if not isinstance(obj, dict) or obj.get("item_id") != item["item_id"]:
        return ["item_id_mismatch"]
    if "error" in obj:
        return ["error_record"]
    probs: List[str] = []
    allowed = VERDICTS_1 if item.get("single_candidate") else VERDICTS_2
    if obj.get("verdict") not in allowed:
        probs.append("bad_verdict")
    if obj.get("status") not in STATUSES:
        probs.append("bad_status")
    if obj.get("ink") not in INKS + (None,):
        probs.append("bad_ink")
    pol = item.get("silver_policy")
    if pol == "withhold_value" and (obj.get("value") is not None or obj.get("normalized") is not None):
        probs.append("pii_value_present")
    elif pol != "withhold_value" and obj.get("status") == "ok" and not str(obj.get("value") or "").strip():
        probs.append("ok_without_value")
    if obj.get("status") in ("not_present", "illegible") and obj.get("value") is not None:
        probs.append("value_with_nonok_status")
    return probs


def load_adjudication(adj_dir: Path) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]], List[Tuple[str, str]]]:
    """-> (verdicts {item_id: obj hợp lệ}, items {item_id: item}, key {item_id: key}, problems [(item_id, lý do)]). Không có thư mục -> rỗng."""
    out_dir, q, k = adj_dir / "out", adj_dir / "queue.json", adj_dir / "key.json"
    if not out_dir.exists() or not q.exists() or not k.exists():
        return {}, {}, {}, []
    items = {i["item_id"]: i for i in json.loads(q.read_text(encoding="utf-8"))["items"]}
    key = json.loads(k.read_text(encoding="utf-8"))
    verdicts: Dict[str, Dict[str, Any]] = {}
    problems: List[Tuple[str, str]] = []
    for p in sorted(out_dir.glob("*.json")):
        iid = p.stem
        if iid not in items:
            problems.append((iid, "unknown_item"))
            continue
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            problems.append((iid, f"unreadable_json:{type(e).__name__}"))
            continue
        pr = validate_adjudication(obj, items[iid], key[iid])
        if pr:
            problems.append((iid, ",".join(pr)))
        else:
            verdicts[iid] = obj
    return verdicts, items, key, problems


def apply_adjudication(merged: List[Dict[str, Any]], schemas: Dict[str, Dict[str, Any]], verdicts: Dict[str, Dict[str, Any]],
                       items: Dict[str, Dict[str, Any]]) -> int:
    """Đặt `review_status = model_adjudicated` + giá trị của người phân xử cho các trường đã phân xử. Trả số trường đã áp dụng."""
    by_unit = {m["unit_id"]: m for m in merged}
    n = 0
    for iid, v in verdicts.items():
        it = items[iid]
        m = by_unit.get(it["unit_id"])
        if not m or it["field"] not in m["fields"]:
            continue
        f = next(x for x in schemas[m["doc_type"]]["x-fields"] if x["name"] == it["field"])
        r = m["fields"][it["field"]]
        pii = bool(f.get("is_pii")) or f.get("silver_policy") == "withhold_value"
        r["review_status"] = "model_adjudicated"
        r["adjudication"] = {"verdict": v["verdict"]}
        r["status"] = v["status"]
        r["value"] = None if (pii or v["status"] != "ok") else v.get("value")
        r["normalized"] = (None if r["value"] is None else normalize_value(r["value"], f["type"], f.get("id_kind")))
        r["page"] = v.get("page")
        r["ink"] = v.get("ink")
        n += 1
    return n


# --------------------------------------------------------------------------------------------------
# Báo cáo
# --------------------------------------------------------------------------------------------------
def _ci(k: int, n: int) -> str:
    if not n:
        return "n/a"
    lo, hi = wilson_interval(k, n)
    return f"{k / n:.3f} [{lo:.3f}; {hi:.3f}]"


def adjudication_stats(verdicts: Dict[str, Dict[str, Any]], key: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, List[int]]]:
    """{annotator: {kiểu trường: [số lần bị coi là SAI, số lần được xét]}} trên các mục đã phân xử.
    x_correct: người đọc y sai; y_correct: người đọc x sai; both_equivalent: cả hai đúng; neither: cả hai sai."""
    st: Dict[str, Dict[str, List[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for iid, v in verdicts.items():
        k = key[iid]
        ftype = k["type"] + ("*" if k.get("withheld") else "")
        wrong = {"x_correct": ("y",), "y_correct": ("x",), "both_equivalent": (), "neither": ("x", "y")}[v["verdict"]]
        for side in ("x", "y"):
            for a in k.get(f"candidate_{side}", []) or []:
                cell = st[a][ftype]
                cell[1] += 1
                cell[0] += int(side in wrong)
    return st


def build_report(merged: List[Dict[str, Any]], units: Dict[str, Dict[str, str]], schemas: Dict[str, Dict[str, Any]],
                 stat: Dict[str, Counter], problems: List[Tuple[str, str, str]], manifest_names: Dict[str, str],
                 field_issues: Optional[List[Tuple[str, str, str, str]]] = None, warns: Optional[Dict[str, Counter]] = None,
                 adj: Optional[Tuple[Dict, Dict, Dict, List]] = None, title: str = "Báo cáo silver v1 (tự sinh bởi merge_silver.py)") -> str:
    field_issues, warns = field_issues or [], warns or {}
    L: List[str] = ["# " + title, "",
                    "> Chỉ có số tổng hợp và mã đơn vị. **Không có giá trị trường nào** (kể cả không có giá trị cá nhân). "
                    "`agreed_unverified` nghĩa là hai người chú thích giống nhau, KHÔNG phải đã được xác minh.", ""]
    n_two = sum(1 for m in merged if len(m["annotators"]) >= 2)
    L += ["## 1. Phủ", "", f"Đơn vị cần chú thích: {len(units)}. Đơn vị đã gộp (có >= 1 người hợp lệ): {len(merged)}. "
          f"Đơn vị có >= 2 người hợp lệ: {n_two}.", "",
          "| người chú thích | hợp lệ | bản ghi lỗi (error) | tệp hỏng (cả đơn vị) | chưa có tệp | đơn vị có trường bị loại |",
          "|---|---|---|---|---|---|"]
    for a, c in sorted(stat.items()):
        L.append(f"| {a} | {c['ok']} | {c['error_record']} | {c['invalid'] + c['unknown_unit_file']} | {c['missing']} | {c['units_with_field_issues']} |")
    fi = Counter((a, r) for a, _u, _f, r in field_issues)
    L += ["", "Trường bị loại khỏi một người chú thích (mức trường; các trường còn lại của đơn vị vẫn được giữ): "
          + (", ".join(f"{a}:{r}={n}" for (a, r), n in sorted(fi.items())) or "không có"),
          "Cảnh báo chỉ đếm (dữ liệu giữ nguyên, evidence được cắt còn 12 từ): "
          + ("; ".join(f"{a}: " + ", ".join(f"{k}={v}" for k, v in sorted(c.items())) for a, c in sorted(warns.items()) if c) or "không có"), ""]

    by_status: Dict[str, Counter] = defaultdict(Counter)
    ink_ct: Counter = Counter()
    ink_risk_n = 0
    norm_mismatch = 0
    # kiểu -> [chặt, mềm, tổng] cho mọi cặp / cặp có ít nhất một bên có giá trị
    ag_all: Dict[str, List[int]] = defaultdict(lambda: [0, 0, 0])
    ag_pres: Dict[str, List[int]] = defaultdict(lambda: [0, 0, 0])
    for m in merged:
        sch = {f["name"]: f for f in schemas[m["doc_type"]]["x-fields"]}
        for name, r in m["fields"].items():
            by_status[m["doc_type"]][r["review_status"]] += 1
            if "ink_risk" in r["review_reasons"]:
                ink_risk_n += 1
            for _a, b in r["by_annotator"].items():
                if b["ink"]:
                    ink_ct[b["ink"]] += 1
                norm_mismatch += int(b["norm_mismatch"])
            ks = list(r["_keys"].values())
            if len(ks) >= 2:
                t = sch[name]["type"] + ("*" if sch[name].get("silver_policy") == "withhold_value" else "")
                lvl = r["_agree"]
                for tab, cond in ((ag_all, True), (ag_pres, any(k not in ("∅", "?") for k in ks))):
                    if cond:
                        tab[t][0] += int(lvl == "strict")
                        tab[t][1] += int(lvl in ("strict", "lenient"))
                        tab[t][2] += 1
    L += ["## 2. Trạng thái trường theo loại", "",
          "| loại | agreed_unverified | needs_human | single_annotator | model_adjudicated | không có bản đọc hợp lệ |", "|---|---|---|---|---|---|"]
    for dt, c in sorted(by_status.items()):
        L.append(f"| {dt} | {c['agreed_unverified']} | {c['needs_human']} | {c['single_annotator']} | {c['model_adjudicated']} | {c['no_valid_reading']} |")
    L += ["", "Ghi chú: `model_adjudicated` thay thế trạng thái trước đó của trường (xem mục 6); `agreed_unverified` gồm cả đồng thuận chặt lẫn mềm (mục 3).",
          f"Trường có cờ `ink_risk` (chữ viết tay hoặc dưới con dấu theo ít nhất một người): {ink_risk_n} — PHẢI được xem lại dù hai bên đồng thuận.",
          f"Số trường người chú thích tự ghi `normalized` lệch kết quả chuẩn hóa của script: {norm_mismatch}.", "",
          "Phân bố `ink` (theo người, trường có giá trị): " + (", ".join(f"{k}={v}" for k, v in sorted(ink_ct.items())) or "chưa có"), ""]

    L += ["## 3. Độ đồng thuận giữa hai người theo kiểu trường (Wilson 95%): CHẶT và MỀM cạnh nhau", "",
          "**Chặt** = bằng nhau sau chuẩn hóa ngày/số/mã/văn bản (NFC, chữ hoa/thường, khoảng trắng) — định nghĩa không đổi. "
          "**Mềm** (chỉ khác ở kiểu `text`) = thêm: bỏ dấu tiếng Việt, bỏ dấu câu, chuỗi ngắn nằm trọn trong chuỗi dài, trường 'tên + MST' khớp theo tên. "
          "Với date/number/id hai cột giống nhau. Kiểu có dấu `*` là trường PII chỉ ghi có/không. "
          "\"Mọi cặp\" gồm cả cặp cùng `not_present` (dễ phồng); \"ít nhất một bên có giá trị\" là con số nên nhìn.", "",
          "| kiểu | cặp (mọi) | chặt | mềm | cặp (ít nhất một bên có giá trị) | chặt | mềm |", "|---|---|---|---|---|---|---|"]
    for t in sorted(ag_all):
        a, p = ag_all[t], ag_pres.get(t, [0, 0, 0])
        L.append(f"| {t} | {a[2]} | {_ci(a[0], a[2])} | {_ci(a[1], a[2])} | {p[2]} | {_ci(p[0], p[2])} | {_ci(p[1], p[2])} |")
    if not ag_all:
        L.append("| (chưa có đơn vị nào được hai người chú thích) | | | | | | |")

    cc = Counter()
    mism: List[str] = []
    for m in merged:
        u = units[m["unit_id"]]
        exp = [n for n in m["fields"] if next(f for f in schemas[m["doc_type"]]["x-fields"] if f["name"] == n).get("is_expiry")]
        if u.get("composite") == "1" or not exp:
            continue
        fd = filename_date(manifest_names.get(u["doc_id"], ""))
        r = m["fields"][exp[0]]
        if fd is None:
            cc["no_date_in_filename"] += 1
        elif r["status"] != "ok" or not r["normalized"]:
            cc["no_silver_expiry"] += 1
        elif r["normalized"] == fd:
            cc["match"] += 1
        else:
            cc["mismatch"] += 1
            mism.append(m["unit_id"])
    L += ["", "## 4. Kiểm chéo hạn với ngày trong tên tệp (CHỈ kiểm chéo, không phải đáp án)", "",
          f"khớp: {cc['match']}; **lệch: {cc['mismatch']}**; tên tệp không có ngày: {cc['no_date_in_filename']}; "
          f"silver không có hạn đọc được: {cc['no_silver_expiry']}.", ""]
    if mism:
        L += ["Đơn vị lệch (xem lại cả tên tệp lẫn đáp án): " + ", ".join(sorted(mism)), ""]

    L += ["## 5. Đơn vị lỗi hoặc tệp hỏng (mức cả đơn vị)", ""]
    if problems:
        L += ["| người | đơn vị | lý do (đã rút gọn, đã che số dài) |", "|---|---|---|"]
        L += [f"| {a} | {u} | {w} |" for a, u, w in problems]
    else:
        L.append("Không có.")
    if field_issues:
        L += ["", "Trường bị loại (mức trường): " + "; ".join(f"{a}/{u}/{f}:{r}" for a, u, f, r in field_issues[:60])
              + (f" ... (+{len(field_issues) - 60})" if len(field_issues) > 60 else "")]

    L += ["", "## 6. Phân xử bởi người đọc thứ ba (mô hình mạnh hơn; KHÔNG phải người thật)", ""]
    verdicts, items, key, adj_problems = adj if adj else ({}, {}, {}, [])
    if not items:
        L.append("Chưa có kết quả phân xử (`gold/adjudication/out/` chưa có).")
    else:
        vc = Counter(v["verdict"] for v in verdicts.values())
        L += [f"Mục trong hàng đợi: {len(items)}; đã có phán quyết hợp lệ: {len(verdicts)}; tệp phân xử hỏng/không hợp lệ: {len(adj_problems)}. "
              "Phán quyết: " + ", ".join(f"{k}={vc[k]}" for k in VERDICTS_2) + ".", "",
              "Trường đã phân xử có `review_status = model_adjudicated` (giá trị của người phân xử, không phải `human_verified`).", "",
              "### Tỉ lệ đọc bị người phân xử coi là SAI, theo người chú thích và kiểu trường (Wilson 95%)", "",
              "Mẫu là các mục bị đưa vào hàng đợi (bất đồng, rủi ro mực, lệch tên tệp), KHÔNG phải mọi trường: đây là tỉ lệ sai CÓ ĐIỀU KIỆN. "
              "Cột \"ước lượng toàn bộ\" lấy số bản đọc bị coi sai chia cho TẤT CẢ bản đọc của người đó trong tập hai-người-chú-thích, "
              "coi mọi trường đồng thuận không phân xử là đúng — là cận DƯỚI của tỉ lệ sai thật (hai mô hình cùng họ có thể cùng sai).", ""]
        stats = adjudication_stats(verdicts, key)
        total_readings: Counter = Counter()
        for m in merged:
            if len(m["annotators"]) < 2:
                continue
            sch = {f["name"]: f for f in schemas[m["doc_type"]]["x-fields"]}
            for name, r in m["fields"].items():
                t = sch[name]["type"] + ("*" if sch[name].get("silver_policy") == "withhold_value" else "")
                for a in r["by_annotator"]:
                    total_readings[(a, t)] += 1
        L += ["| người chú thích | kiểu | bản đọc đã xét | bị coi sai (có điều kiện) | tổng bản đọc (tập hai người) | ước lượng toàn bộ (cận dưới) |", "|---|---|---|---|---|---|"]
        for a in sorted(stats):
            for t in sorted(stats[a]):
                w, n = stats[a][t]
                tot = total_readings[(a, t)]
                L.append(f"| {a} | {t} | {n} | {_ci(w, n)} ({w}/{n}) | {tot} | {_ci(w, tot)} ({w}/{tot}) |")
            w = sum(x[0] for x in stats[a].values())
            n = sum(x[1] for x in stats[a].values())
            tot = sum(v for (aa, _t), v in total_readings.items() if aa == a)
            L.append(f"| **{a}** | tất cả | {n} | {_ci(w, n)} ({w}/{n}) | {tot} | {_ci(w, tot)} ({w}/{tot}) |")
        if adj_problems:
            L += ["", "Tệp phân xử không hợp lệ: " + "; ".join(f"{i}:{r}" for i, r in adj_problems[:40])]
    return "\n".join(L) + "\n"


def run(raw_dir: Path, units_csv: Path, schema_dir: Path, out_jsonl: Path, out_md: Path, manifest_csv: Path, primary: str = DEFAULT_PRIMARY,
        adj_dir: Optional[Path] = None, title: str = "Báo cáo silver v1 (tự sinh bởi merge_silver.py)") -> Dict[str, Any]:
    units = load_units(units_csv)
    schemas = load_schemas(schema_dir)
    valid, stat, problems, field_issues, warns = collect(raw_dir, units, schemas)
    merged = [merge_unit(units[uid], schemas[units[uid]["doc_type"]], valid[uid], primary) for uid in sorted(valid)]
    adj = load_adjudication(adj_dir) if adj_dir else ({}, {}, {}, [])
    n_adj = apply_adjudication(merged, schemas, adj[0], adj[1]) if adj[1] else 0
    names: Dict[str, str] = {}
    if manifest_csv.exists():
        with open(manifest_csv, encoding="utf-8-sig", newline="") as f:
            names = {r["doc_id"]: r["file_name"] for r in csv.DictReader(f)}
    out_md.write_text(build_report(merged, units, schemas, stat, problems, names, field_issues, warns, adj, title), encoding="utf-8")
    with open(out_jsonl, "w", encoding="utf-8") as f:
        for m in merged:
            for r in m["fields"].values():
                r.pop("_keys", None)
                r.pop("_agree", None)
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    return {"n_merged": len(merged), "n_problems": len(problems), "n_field_issues": len(field_issues), "n_adjudicated": n_adj}


def version_defaults(version: str) -> Dict[str, Any]:
    """Đường dẫn mặc định theo phiên bản bộ silver: v1 (gold/) hoặc v2 (gold/v2/, giai đoạn 3)."""
    if version == "v2":
        base = HERE / "v2"
        return dict(raw=base / "silver_raw", units=base / "units_v2.csv", out=base / "fields_silver_v2.jsonl", report=base / "silver_report_v2.md",
                    adjudication=base / "adjudication", title="Báo cáo silver v2 - giai đoạn 3 (tự sinh bởi merge_silver.py --version v2)")
    return dict(raw=HERE / "silver_raw", units=HERE / "units.csv", out=HERE / "fields_silver_v1.jsonl", report=HERE / "silver_report.md",
                adjudication=ADJ_DIR, title="Báo cáo silver v1 (tự sinh bởi merge_silver.py)")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", choices=("v1", "v2"), default="v1", help="đặt đường dẫn mặc định cho v1 (gold/) hoặc v2 (gold/v2/); tham số tường minh ghi đè")
    pre, _rest = ap.parse_known_args(argv)
    d = version_defaults(pre.version)
    ap.add_argument("--raw", default=str(d["raw"]))
    ap.add_argument("--units", default=str(d["units"]))
    ap.add_argument("--schemas", default=str(TEAM / "schema"))
    ap.add_argument("--out", default=str(d["out"]))
    ap.add_argument("--report", default=str(d["report"]))
    ap.add_argument("--manifest", default=str(REPO / "data" / "manifest.csv"))
    ap.add_argument("--adjudication", default=str(d["adjudication"]), help="thư mục adjudication (có out/, queue.json, key.json); bỏ qua nếu thiếu")
    ap.add_argument("--primary", default=DEFAULT_PRIMARY, help="người chú thích có giá trị được dùng khi không đồng thuận")
    a = ap.parse_args(argv)
    res = run(Path(a.raw), Path(a.units), Path(a.schemas), Path(a.out), Path(a.report), Path(a.manifest), a.primary, Path(a.adjudication), d["title"])
    print(f"đã gộp {res['n_merged']} đơn vị; {res['n_problems']} đơn vị lỗi; {res['n_field_issues']} trường bị loại; "
          f"{res['n_adjudicated']} trường đã phân xử (xem báo cáo)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
