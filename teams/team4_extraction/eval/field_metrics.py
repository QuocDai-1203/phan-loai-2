"""field_metrics.py - Bộ chấm trường (Nhóm 4, việc T3).

Quy ước TP/FP/FN cho MỖI (tài liệu, trường) — đúng theo README nhóm 4, T3:

    dự đoán không null và đúng                 -> TP
    dự đoán không null nhưng sai               -> FP + FN   ("sai giá trị", wrong)
    dự đoán null, đáp án có giá trị            -> FN        ("bỏ trống", empty)
    dự đoán không null, đáp án null            -> FP        ("thừa", spurious)
    cả hai null                                -> không tính vào P/R (nhưng vẫn "đúng" ở mức tài liệu)

Đáp án có `status`: `ok` (có giá trị), `not_present` (giấy không ghi -> null), `illegible` (không đọc được -> trường
bị LOẠI khỏi điểm, đếm riêng). Đơn vị đánh giá = (doc_id, segment) = `unit_id`.

Ba chế độ so sánh (báo riêng, không trộn): `exact` (chuỗi thô, chỉ bỏ khoảng trắng hai đầu), `normalized` (chính: ngày/số/mã
chuẩn hóa, chữ hoa/thường, khoảng trắng, NFC) `nodiac` (như normalized nhưng văn bản không phân biệt dấu tiếng Việt) và `lenient` (kiểu text: bỏ dấu, bỏ dấu câu, chứa nhau, "tên + MST" khớp theo tên;
các kiểu khác như normalized).

Chỉ số:
  * theo từng trường (doc_type, field) và gộp theo KIỂU trường (date/number/id/text) và theo "expiry": P/R/F1;
  * cấp tài liệu: tỉ lệ đơn vị có MỌI trường bắt buộc đúng (cả hai null cũng là đúng);
  * trường hạn: đúng / bỏ trống / SAI GIÁ TRỊ trên đơn vị có đáp án; và "thừa" trên đơn vị đáp án null;
  * khoảng tin cậy bootstrap percentile 95%, lấy mẫu lại THEO TÀI LIỆU (đơn vị), seed cố định.

Đơn vị mà phương pháp lỗi/không có đầu ra (`pred[unit]` thiếu hoặc `None`) được tính như dự đoán toàn null (phạt recall) và
được đếm ở `n_failed`; báo cáo luôn in `n_failed` riêng — "rỗng" không phải "thành công".

Báo cáo (`render_markdown`, `list_errors`) chỉ chứa số tổng hợp và mã đơn vị/tên trường, KHÔNG BAO GIỜ chứa giá trị trường.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

try:  # chạy được cả khi import như package lẫn như module phẳng
    from .normalize import lenient_text_equal, normalize_value
except ImportError:  # pragma: no cover
    from normalize import lenient_text_equal, normalize_value  # type: ignore

BOOT_N = 2000
BOOT_SEED = 20261012
MODES = ("normalized", "exact", "nodiac", "lenient")
FIELD_TYPES = ("date", "number", "id", "text")
SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schema"

# ma trận đếm cho mỗi (đơn vị, nhóm): [tp, fp, fn]; hạn: [correct, empty, wrong, correct_null, spurious]
_PRF = 3
_EXP = 5


@dataclass(frozen=True)
class FieldSpec:
    name: str
    type: str                      # date | number | id | text
    id_kind: Optional[str] = None  # tax_code | plate | document_no | generic (chỉ khi type == id)
    is_expiry: bool = False
    required: bool = False
    is_pii: bool = False
    scored: bool = True            # False: trường dẫn xuất/không có trên giấy (vd. vai_tro_cong_ty) -> không chấm


def load_specs(schema_dir: Path | str = SCHEMA_DIR) -> Dict[str, List[FieldSpec]]:
    """Đọc `schema/<DOC_TYPE>.json` -> {doc_type: [FieldSpec...]} (theo `x-fields`)."""
    out: Dict[str, List[FieldSpec]] = {}
    for p in sorted(Path(schema_dir).glob("*.json")):
        if p.name == "pii_fields.json":
            continue
        sch = json.loads(p.read_text(encoding="utf-8"))
        if "x-fields" not in sch:
            continue
        out[sch["x-doc_type"]] = [
            FieldSpec(name=f["name"], type=f["type"], id_kind=f.get("id_kind"), is_expiry=bool(f.get("is_expiry")),
                      required=bool(f.get("required")), is_pii=bool(f.get("is_pii")),
                      scored=f.get("annotate", True) is not False)
            for f in sch["x-fields"]
        ]
    return out


# --------------------------------------------------------------------------------------------------
# Một cặp (đáp án, dự đoán)
# --------------------------------------------------------------------------------------------------
def _val(x: Any) -> Optional[str]:
    """Rút giá trị chuỗi từ str | None | {"value": ...}; chuỗi rỗng -> None."""
    if isinstance(x, Mapping):
        x = x.get("value")
    if x is None:
        return None
    s = str(x).strip()
    return s or None


def _gold_status(x: Any) -> str:
    if isinstance(x, Mapping):
        st = x.get("status")
        if st in ("ok", "not_present", "illegible"):
            return st
    return "ok" if _val(x) is not None else "not_present"


def _norm(v: Optional[str], spec: FieldSpec, mode: str) -> Optional[str]:
    if v is None:
        return None
    if mode == "exact":
        return v
    return normalize_value(v, spec.type, spec.id_kind, strip_diacritics=(mode == "nodiac"))  # "lenient" khác normalized chỉ ở kiểu text (xem compare_field)


def compare_field(gold: Any, pred: Any, spec: FieldSpec, mode: str = "normalized") -> str:
    """Kết quả cho một trường: 'tp' | 'wrong' | 'empty' | 'spurious' | 'tn' | 'skip' (đáp án illegible)."""
    if mode not in MODES:
        raise ValueError(f"mode phải thuộc {MODES}")
    st = _gold_status(gold)
    if st == "illegible":
        return "skip"
    g = _val(gold) if st == "ok" else None
    p = _val(pred)
    if g is None and p is None:
        return "tn"
    if g is None:
        return "spurious"
    if p is None:
        return "empty"
    if mode == "lenient" and spec.type == "text":
        return "tp" if lenient_text_equal(g, p) else "wrong"
    return "tp" if _norm(g, spec, mode) == _norm(p, spec, mode) else "wrong"


# --------------------------------------------------------------------------------------------------
# Chấm toàn bộ
# --------------------------------------------------------------------------------------------------
def _prf(tp: float, fp: float, fn: float) -> Tuple[float, float, float]:
    p = tp / (tp + fp) if (tp + fp) > 0 else math.nan
    r = tp / (tp + fn) if (tp + fn) > 0 else math.nan
    f = 2 * p * r / (p + r) if (not math.isnan(p) and not math.isnan(r) and (p + r) > 0) else math.nan
    return p, r, f


def _pred_for(pred: Mapping[str, Any], uid: str) -> Optional[Mapping[str, Any]]:
    rec = pred.get(uid)
    if rec is None:
        return None
    if isinstance(rec, Mapping) and rec.get("_status") not in (None, "ok"):
        return None
    return rec.get("fields", rec) if isinstance(rec, Mapping) and isinstance(rec.get("fields"), Mapping) else rec


def score(gold: Mapping[str, Mapping[str, Any]], pred: Mapping[str, Any], unit_types: Mapping[str, str],
          specs: Optional[Mapping[str, Sequence[FieldSpec]]] = None, mode: str = "normalized",
          n_boot: int = BOOT_N, seed: int = BOOT_SEED, include_pii: bool = False) -> Dict[str, Any]:
    """Chấm `pred` theo `gold`.

    gold      {unit_id: {field: giá_trị | {"value","status"}}}  (đáp án)
    pred      {unit_id: {field: giá_trị | {"value"}}}; thiếu unit_id / None / {"_status": "error"} = phương pháp lỗi
    unit_types{unit_id: doc_type}
    specs     {doc_type: [FieldSpec]} (mặc định đọc từ schema/)
    include_pii  False (mặc định): trường PII bị bỏ khỏi bảng điểm (không có giá trị nào bị in, nhưng cũng không chấm).
    Trả dict: per_field, per_type, expiry, doc_level, counts, meta (mọi thứ đều có `ci_lo`/`ci_hi` nếu n_boot > 0).
    """
    specs = specs or load_specs()
    units = [u for u in gold if u in unit_types]
    units.sort()
    n_units = len(units)
    if n_units == 0:
        raise ValueError("Không có đơn vị nào để chấm (gold rỗng hoặc thiếu unit_types)")

    # nhóm
    fkeys: List[Tuple[str, str]] = []           # (doc_type, field)
    for dt in sorted({unit_types[u] for u in units}):
        for sp in specs[dt]:
            if sp.scored and (include_pii or not sp.is_pii):
                fkeys.append((dt, sp.name))
    f_idx = {k: i for i, k in enumerate(fkeys)}
    spec_of = {(dt, sp.name): sp for dt in specs for sp in specs[dt]}
    tkeys = list(FIELD_TYPES)
    exp_keys = sorted({(dt, sp.name) for (dt, _n) in fkeys for sp in [spec_of[(dt, _n)]] if sp.is_expiry})
    e_idx = {k: i for i, k in enumerate(exp_keys)}

    C_f = np.zeros((n_units, len(fkeys), _PRF))
    C_t = np.zeros((n_units, len(tkeys), _PRF))
    C_e = np.zeros((n_units, max(1, len(exp_keys)), _EXP))
    doc_ok = np.zeros(n_units)
    doc_eval = np.zeros(n_units)
    illeg = np.zeros((n_units, len(fkeys)))
    failed = np.zeros(n_units)
    mistakes: List[Dict[str, str]] = []

    for ui, uid in enumerate(units):
        dt = unit_types[uid]
        prec = _pred_for(pred, uid)
        if prec is None:
            failed[ui] = 1
            prec = {}
        all_req_ok = True
        any_req = False
        for sp in specs[dt]:
            if not sp.scored or (sp.is_pii and not include_pii):
                continue
            k = (dt, sp.name)
            res = compare_field(gold[uid].get(sp.name), prec.get(sp.name), sp, mode)
            fi = f_idx[k]
            if res == "skip":
                illeg[ui, fi] = 1
                continue
            tp, fp, fn = {"tp": (1, 0, 0), "wrong": (0, 1, 1), "empty": (0, 0, 1), "spurious": (0, 1, 0), "tn": (0, 0, 0)}[res]
            C_f[ui, fi] += (tp, fp, fn)
            ti = tkeys.index(sp.type)
            C_t[ui, ti] += (tp, fp, fn)
            if sp.is_expiry:
                ei = e_idx[k]
                C_e[ui, ei, {"tp": 0, "empty": 1, "wrong": 2, "tn": 3, "spurious": 4}[res]] += 1
            if sp.required:
                any_req = True
                if res not in ("tp", "tn"):
                    all_req_ok = False
            if res in ("wrong", "empty", "spurious"):
                mistakes.append({"unit_id": uid, "doc_type": dt, "field": sp.name, "kind": res})
        if any_req:
            doc_eval[ui] = 1
            doc_ok[ui] = 1 if all_req_ok else 0

    def point(idx: np.ndarray) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        sf = C_f[idx].sum(0)
        st = C_t[idx].sum(0)
        se = C_e[idx].sum(0)
        out["f"] = np.array([_prf(*sf[i]) for i in range(len(fkeys))]).reshape(len(fkeys), 3) if fkeys else np.zeros((0, 3))
        out["t"] = np.array([_prf(*st[i]) for i in range(len(tkeys))])
        out["a"] = np.array([_prf(*st.sum(0))])           # gộp mọi kiểu trường (micro)
        # tổng hợp "expiry" (gộp mọi trường hạn) và từng trường hạn
        exp_rows = []
        for i in range(len(exp_keys)):
            c, e, w, cn, sp_ = se[i]
            n_gold = c + e + w
            n_abs = cn + sp_
            exp_rows.append([c / n_gold if n_gold else math.nan, e / n_gold if n_gold else math.nan,
                             w / n_gold if n_gold else math.nan, sp_ / n_abs if n_abs else math.nan,
                             (w + sp_) / (n_gold + n_abs) if (n_gold + n_abs) else math.nan])
        tot = se[: len(exp_keys)].sum(0) if exp_keys else np.zeros(_EXP)
        c, e, w, cn, sp_ = tot
        n_gold, n_abs = c + e + w, cn + sp_
        exp_rows.append([c / n_gold if n_gold else math.nan, e / n_gold if n_gold else math.nan,
                         w / n_gold if n_gold else math.nan, sp_ / n_abs if n_abs else math.nan,
                         (w + sp_) / (n_gold + n_abs) if (n_gold + n_abs) else math.nan])
        out["e"] = np.array(exp_rows)
        de = doc_eval[idx].sum()
        out["d"] = np.array([doc_ok[idx].sum() / de if de else math.nan])
        out["_sf"], out["_st"], out["_se"] = sf, st, se
        return out

    base = point(np.arange(n_units))
    boots: List[Dict[str, Any]] = []
    if n_boot > 0:
        rng = np.random.default_rng(seed)
        for _ in range(n_boot):
            boots.append(point(rng.integers(0, n_units, n_units)))

    def ci(key: str, shape_idx: Tuple[int, ...]) -> Tuple[float, float]:
        if not boots:
            return (math.nan, math.nan)
        v = np.array([b[key][shape_idx] for b in boots], dtype=float)
        v = v[~np.isnan(v)]
        if v.size == 0:
            return (math.nan, math.nan)
        return float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))

    per_field = []
    for (dt, name), i in f_idx.items():
        sp = spec_of[(dt, name)]
        tp, fp, fn = base["_sf"][i]
        row = {"doc_type": dt, "field": name, "type": sp.type, "is_expiry": sp.is_expiry, "required": sp.required,
               "tp": int(tp), "fp": int(fp), "fn": int(fn), "n_gold": int(tp + fn), "n_illegible": int(illeg[:, i].sum())}
        for j, m in enumerate(("precision", "recall", "f1")):
            row[m] = float(base["f"][i][j])
            lo, hi = ci("f", (i, j))
            row[m + "_ci_lo"], row[m + "_ci_hi"] = lo, hi
        per_field.append(row)

    per_type = []
    for ti, tname in enumerate(tkeys):
        tp, fp, fn = base["_st"][ti]
        row = {"type": tname, "tp": int(tp), "fp": int(fp), "fn": int(fn), "n_gold": int(tp + fn)}
        for j, m in enumerate(("precision", "recall", "f1")):
            row[m] = float(base["t"][ti][j])
            lo, hi = ci("t", (ti, j))
            row[m + "_ci_lo"], row[m + "_ci_hi"] = lo, hi
        per_type.append(row)

    tp, fp, fn = base["_st"].sum(0)
    overall = {"tp": int(tp), "fp": int(fp), "fn": int(fn), "n_gold": int(tp + fn)}
    for j, m in enumerate(("precision", "recall", "f1")):
        overall[m] = float(base["a"][0][j])
        overall[m + "_ci_lo"], overall[m + "_ci_hi"] = ci("a", (0, j))

    expiry = []
    labels = [f"{dt}.{n}" for dt, n in exp_keys] + ["ALL_EXPIRY"]
    for ei, lab in enumerate(labels):
        se = base["_se"][ei] if ei < len(exp_keys) else base["_se"][: len(exp_keys)].sum(0) if exp_keys else np.zeros(_EXP)
        row = {"field": lab, "n_gold_present": int(se[0] + se[1] + se[2]), "n_gold_absent": int(se[3] + se[4])}
        for j, m in enumerate(("correct_rate", "empty_rate", "wrong_rate", "spurious_rate", "bad_total_rate")):
            row[m] = float(base["e"][ei][j])
            lo, hi = ci("e", (ei, j))
            row[m + "_ci_lo"], row[m + "_ci_hi"] = lo, hi
        expiry.append(row)

    dlo, dhi = ci("d", (0,))
    doc_level = {"rate": float(base["d"][0]), "ci_lo": dlo, "ci_hi": dhi, "n_evaluated": int(doc_eval.sum()),
                 "n_all_required_correct": int(doc_ok.sum())}

    counts = {"n_units": n_units, "n_failed": int(failed.sum()), "failed_units": [u for u, f in zip(units, failed) if f],
              "n_illegible_fields": int(illeg.sum())}
    return {"mode": mode, "overall": overall, "per_field": per_field, "per_type": per_type, "expiry": expiry, "doc_level": doc_level,
            "counts": counts, "mistakes": mistakes,
            "meta": {"n_boot": n_boot, "seed": seed, "include_pii": include_pii, "ci": "percentile 95%, bootstrap theo đơn vị"}}


def score_all_modes(gold, pred, unit_types, specs=None, **kw) -> Dict[str, Dict[str, Any]]:
    """Chấm cả các chế độ (exact / normalized / nodiac / lenient) để báo riêng."""
    return {m: score(gold, pred, unit_types, specs, mode=m, **kw) for m in MODES}


def list_errors(result: Mapping[str, Any]) -> List[Dict[str, str]]:
    """Danh sách lỗi theo (unit_id, field, kind) — KHÔNG kèm giá trị (an toàn cho báo cáo)."""
    return list(result["mistakes"])


# --------------------------------------------------------------------------------------------------
# Báo cáo
# --------------------------------------------------------------------------------------------------
def _f(x: float, ci_lo: float = None, ci_hi: float = None) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    s = f"{x:.3f}"
    if ci_lo is not None and not math.isnan(ci_lo):
        s += f" [{ci_lo:.3f}; {ci_hi:.3f}]"
    return s


def render_markdown(result: Mapping[str, Any], title: str = "Kết quả chấm trường") -> str:
    """Bảng Markdown. Chỉ số tổng hợp, không có giá trị trường."""
    L = [f"## {title}", "",
         f"Chế độ so sánh: `{result['mode']}`; CI: {result['meta']['ci']} ({result['meta']['n_boot']} lần, seed {result['meta']['seed']}).",
         f"Số đơn vị: {result['counts']['n_units']}; **lỗi/không có đầu ra: {result['counts']['n_failed']}** "
         f"(chấm như dự đoán toàn null); trường không đọc được bị loại: {result['counts']['n_illegible_fields']}.", ""]
    dl = result["doc_level"]
    L += ["### Cấp tài liệu", "",
          f"Tỉ lệ đơn vị đúng mọi trường bắt buộc: {_f(dl['rate'], dl['ci_lo'], dl['ci_hi'])} "
          f"({dl['n_all_required_correct']}/{dl['n_evaluated']}).", ""]
    L += ["### Trường hạn (expiry)", "",
          "| trường | n có đáp án | đúng | bỏ trống | **sai giá trị** | thừa (đáp án null) |", "|---|---|---|---|---|---|"]
    for r in result["expiry"]:
        L.append(f"| {r['field']} | {r['n_gold_present']} | {_f(r['correct_rate'], r['correct_rate_ci_lo'], r['correct_rate_ci_hi'])} | "
                 f"{_f(r['empty_rate'], r['empty_rate_ci_lo'], r['empty_rate_ci_hi'])} | "
                 f"{_f(r['wrong_rate'], r['wrong_rate_ci_lo'], r['wrong_rate_ci_hi'])} | "
                 f"{_f(r['spurious_rate'], r['spurious_rate_ci_lo'], r['spurious_rate_ci_hi'])} (n={r['n_gold_absent']}) |")
    L += ["", "### Theo kiểu trường", "", "| kiểu | TP | FP | FN | P | R | F1 |", "|---|---|---|---|---|---|---|"]
    for r in result["per_type"]:
        L.append(f"| {r['type']} | {r['tp']} | {r['fp']} | {r['fn']} | {_f(r['precision'], r['precision_ci_lo'], r['precision_ci_hi'])} | "
                 f"{_f(r['recall'], r['recall_ci_lo'], r['recall_ci_hi'])} | {_f(r['f1'], r['f1_ci_lo'], r['f1_ci_hi'])} |")
    L += ["", "### Theo từng trường", "", "| loại | trường | kiểu | n đáp án | TP | FP | FN | P | R | F1 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in result["per_field"]:
        L.append(f"| {r['doc_type']} | {r['field']} | {r['type']} | {r['n_gold']} | {r['tp']} | {r['fp']} | {r['fn']} | "
                 f"{_f(r['precision'])} | {_f(r['recall'])} | {_f(r['f1'], r['f1_ci_lo'], r['f1_ci_hi'])} |")
    return "\n".join(L) + "\n"


def wilson_interval(k: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """Khoảng tin cậy Wilson cho một tỉ lệ k/n (dùng ở báo cáo đồng thuận silver)."""
    if n <= 0:
        return (math.nan, math.nan)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)
