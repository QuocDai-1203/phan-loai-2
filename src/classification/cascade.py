"""cascade.py - Logic thuần (không gọi mô hình) của bộ phân loại nhiều tầng có từ chối, và tìm ngưỡng trên dữ liệu DEV.

Thiết kế (tầng chạy theo thứ tự, tài liệu được TẦNG ĐẦU TIÊN đủ tự tin nhận; không tầng nào nhận -> tầng người):
  1. rule : cổng luật từ khóa tiêu đề. Nhận khi luật quyết định được một lớp.
  2. tfidf: bộ phân loại có giám sát (Track S, có xác suất). Nhận khi dự đoán KHÔNG phải RARE_OR_OTHER và confidence >= th_s.
  3. llm  : LLM/Kev zero-shot toàn taxonomy (hoặc embedding few-shot). Nhận khi nhãn không thuộc NEVER_AUTO (OTHER/UNREADABLE/
            không trả lời) và (confidence >= th_llm HOẶC đồng thuận với tầng khác theo `agree`).
  4. human: phần còn lại.

Mọi tham số (th_s, th_llm, agree) chỉ được chọn trên dự đoán out-of-fold của DEV (`tune`), rồi áp nguyên cho TEST.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

POOL = "RARE_OR_OTHER"
UNKNOWN = "UNKNOWN"
NEVER_AUTO = ("OTHER", "UNREADABLE", "NO_ANSWER", UNKNOWN, "")
AGREE_MODES = ("none", "s", "emb", "s_or_emb")
CONSENSUS_MODES = ("none", "s", "llm2", "s_llm2")   # "hai nguồn đồng thuận": tầng LLM chỉ nhận khi nguồn thứ hai CÙNG nhãn (AND, khác `agree` là OR)
TIERS = ("rule", "tfidf", "llm", "human")


@dataclass
class Signals:
    """Tín hiệu của từng tầng cho n tài liệu (đã tính sẵn; cascade không gọi mô hình)."""
    rule: List[str]                                  # nhãn Z của cổng luật, '' nếu abstain
    s_label: List[str]                               # nhãn Track S (có thể là RARE_OR_OTHER)
    s_conf: np.ndarray
    llm_label: List[str]
    llm_conf: np.ndarray                             # nan nếu mô hình không báo độ tin cậy
    emb_label: Optional[List[str]] = None            # nhãn embedding few-shot (Z), dùng cho agree
    emb_conf: Optional[np.ndarray] = None
    lat_rule: Optional[np.ndarray] = None            # ms mỗi tài liệu
    lat_s: Optional[np.ndarray] = None
    lat_llm: Optional[np.ndarray] = None
    lat_emb: Optional[np.ndarray] = None
    llm2_label: Optional[List[str]] = None           # nguồn thứ hai (LLM/prompt khác) cho chế độ consensus 'llm2'
    llm2_conf: Optional[np.ndarray] = None
    lat_llm2: Optional[np.ndarray] = None

    def __len__(self) -> int:
        return len(self.rule)

    def take(self, idx: Sequence[int]) -> "Signals":
        idx = list(idx)
        pick = lambda a: None if a is None else (np.asarray(a)[idx] if isinstance(a, np.ndarray) else [a[i] for i in idx])
        return Signals(**{f: pick(getattr(self, f)) for f in ("rule", "s_label", "s_conf", "llm_label", "llm_conf", "emb_label", "emb_conf",
                                                              "lat_rule", "lat_s", "lat_llm", "lat_emb", "llm2_label", "llm2_conf", "lat_llm2")})


@dataclass(frozen=True)
class CascadeParams:
    use_rule: bool = True
    use_tfidf: bool = True
    use_llm: bool = True
    th_s: float = 0.9
    th_llm: float = 0.9
    agree: str = "none"                              # none | s | emb | s_or_emb : đồng thuận cũng đủ để tầng llm nhận
    consensus: str = "none"                          # none | s | llm2 | s_llm2 : tầng llm CHỈ nhận khi nguồn phụ cùng nhãn (tắt mặc định)

    def describe(self) -> str:
        tiers = "+".join(t for t, u in (("rule", self.use_rule), ("tfidf", self.use_tfidf), ("llm", self.use_llm)) if u) or "human"
        extra = "" if self.consensus == "none" else f" consensus={self.consensus}"
        return f"{tiers} th_s={self.th_s:.3g} th_llm={self.th_llm:.3g} agree={self.agree}{extra}"


def run_cascade(sig: Signals, p: CascadeParams) -> pd.DataFrame:
    """Trả DataFrame (n dòng): label ('' nếu về người), tier, accepted, latency_ms (cộng độ trễ của các tầng tài liệu đã đi qua)."""
    label, tier, lat = _cascade_arrays(sig, p)
    out = pd.DataFrame({"label": label, "tier": tier, "latency_ms": lat})
    out["accepted"] = out["tier"] != "human"
    return out


def _cascade_arrays(sig: Signals, p: CascadeParams):
    """Lõi vector hóa của run_cascade (tune gọi hàng nghìn lần nên tránh tạo DataFrame)."""
    n = len(sig)
    label = np.full(n, "", dtype=object)
    tier = np.full(n, "human", dtype=object)
    lat = np.zeros(n)
    z = np.zeros(n)
    lr, ls = (sig.lat_rule if sig.lat_rule is not None else z), (sig.lat_s if sig.lat_s is not None else z)
    ll, le = (sig.lat_llm if sig.lat_llm is not None else z), (sig.lat_emb if sig.lat_emb is not None else z)
    active = np.ones(n, dtype=bool)
    if p.use_rule:
        lat[active] += np.asarray(lr, float)[active]
        rule = np.array(sig.rule, dtype=object)
        m = active & ~np.isin(rule, ("", UNKNOWN))
        label[m], tier[m] = rule[m], "rule"
        active &= ~m
    if p.use_tfidf:
        lat[active] += np.asarray(ls, float)[active]
        sl = np.array(sig.s_label, dtype=object)
        m = active & (sl != POOL) & (np.asarray(sig.s_conf, float) >= p.th_s)
        label[m], tier[m] = sl[m], "tfidf"
        active &= ~m
    if p.use_llm:
        lat[active] += np.asarray(ll, float)[active]
        if p.agree in ("emb", "s_or_emb"):
            lat[active] += np.asarray(le, float)[active]
        lab = np.array(sig.llm_label, dtype=object)
        conf = np.asarray(sig.llm_conf, float)
        ok = ~np.isnan(conf) & (conf >= p.th_llm)
        if p.agree in ("s", "s_or_emb"):
            sl = np.array(sig.s_label, dtype=object)
            ok |= (sl == lab) & (lab != POOL)
        if p.agree in ("emb", "s_or_emb") and sig.emb_label is not None:
            ok |= np.array(sig.emb_label, dtype=object) == lab
        if p.consensus not in CONSENSUS_MODES:
            raise ValueError(f"consensus không hợp lệ: {p.consensus!r}")
        if p.consensus in ("s", "s_llm2"):
            ok &= (np.array(sig.s_label, dtype=object) == lab) & (lab != POOL)
        if p.consensus in ("llm2", "s_llm2"):
            if sig.llm2_label is None:                 # thiếu nguồn thứ hai -> không nhận gì (an toàn), không âm thầm bỏ yêu cầu
                ok &= False
            else:
                l2 = np.array(sig.llm2_label, dtype=object)
                ok &= (l2 == lab) & ~np.isin(l2, NEVER_AUTO)
                lat[active] += np.asarray(sig.lat_llm2 if sig.lat_llm2 is not None else z, float)[active]
        m = active & ok & ~np.isin(lab, NEVER_AUTO)
        label[m], tier[m] = lab[m], "llm"
    return label, tier, lat


def selective_counts(accepted: np.ndarray, correct: np.ndarray) -> Tuple[float, float, int, int]:
    """(coverage trên mọi tài liệu, tỉ lệ sai trên phần được nhận, n nhận, số sai)."""
    accepted, correct = np.asarray(accepted, bool), np.asarray(correct, bool)
    n = len(accepted)
    k = int(accepted.sum())
    err = int((~correct[accepted]).sum())
    return (k / n if n else float("nan")), (err / k if k else float("nan")), k, err


def _grid(values: np.ndarray, max_n: int = 40) -> List[float]:
    v = np.unique(values[~np.isnan(values)])
    if len(v) > max_n:
        v = np.unique(np.quantile(v, np.linspace(0, 1, max_n)))
    return sorted(set(float(x) for x in v) | {float("inf")})


def tune(sig: Signals, y_true: Sequence[str], base: CascadeParams, max_error: float,
         agree_modes: Sequence[str] = ("none",)) -> Tuple[CascadeParams, Dict[str, float]]:
    """Chọn (th_s, th_llm, agree) làm coverage lớn nhất mà tỉ lệ sai trên phần được nhận <= max_error (trên `sig` = DEV OOF).
    Hòa -> ngưỡng cao hơn (thận trọng hơn). Không có cấu hình khả thi -> mọi ngưỡng = inf (không tự nhận gì ngoài cổng luật)."""
    y = np.asarray(y_true)
    ths = _grid(np.asarray(sig.s_conf, float)) if base.use_tfidf else [float("inf")]
    thl = _grid(np.asarray(sig.llm_conf, float)) if base.use_llm else [float("inf")]
    modes = list(agree_modes) if base.use_llm else ["none"]
    best, best_key = None, None
    for a in modes:
        for ts in ths:
            for tl in thl:
                p = replace(base, th_s=ts, th_llm=tl, agree=a)
                label, tier, _ = _cascade_arrays(sig, p)
                cov, risk, k, err = selective_counts(tier != "human", label == y)
                if k == 0 or risk > max_error + 1e-12:
                    continue
                key = (cov, ts if np.isfinite(ts) else 1e9, tl if np.isfinite(tl) else 1e9, -modes.index(a))
                if best_key is None or key > best_key:
                    best_key, best = key, (p, dict(coverage=cov, risk=risk, n_accepted=k, errors=err))
    if best is None:
        p = replace(base, th_s=float("inf"), th_llm=float("inf"), agree="none")
        res = run_cascade(sig, p)
        cov, risk, k, err = selective_counts(res["accepted"].to_numpy(), res["label"].to_numpy() == y)
        return p, dict(coverage=cov, risk=risk, n_accepted=k, errors=err)
    return best


# ----------------------------------------------------------------------------- kiểm mẫu ngẫu nhiên + nhật ký
def audit_flags(ids: Sequence[str], rate: float, seed: int = 0) -> np.ndarray:
    """Cờ kiểm mẫu ngẫu nhiên, TẤT ĐỊNH theo (seed, id): băm sha1 -> số trong [0,1) < rate. Không phụ thuộc thứ tự xử lý
    (dùng được khi xử lý từng tài liệu một). rate=0 -> không ai bị chọn; rate=1 -> mọi tài liệu."""
    if not 0.0 <= rate <= 1.0:
        raise ValueError("audit rate phải trong [0, 1]")
    if rate == 0.0:
        return np.zeros(len(ids), dtype=bool)
    u = np.array([int(hashlib.sha1(f"{seed}:{i}".encode("utf-8")).hexdigest()[:12], 16) / float(16 ** 12) for i in ids])
    return u < rate


def apply_audit(res: pd.DataFrame, ids: Sequence[str], rate: float, seed: int = 0) -> pd.DataFrame:
    """Thêm cột `audit` (tài liệu ĐƯỢC TỰ NHẬN nhưng bị giữ lại cho người kiểm) và `final_accepted` (= accepted & ~audit)."""
    out = res.copy()
    out["audit"] = out["accepted"].to_numpy() & audit_flags(list(ids), rate, seed)
    out["final_accepted"] = out["accepted"].to_numpy() & ~out["audit"].to_numpy()
    return out


def decision_records(res: pd.DataFrame, ids: Sequence[str], confidence: Optional[Sequence[float]] = None) -> List[Dict[str, Any]]:
    """Nhật ký quyết định (không chứa văn bản): id, tầng, nhãn, độ tin cậy, nhận/từ chối, có bị kiểm mẫu không."""
    conf = [None] * len(res) if confidence is None else [None if (c is None or c != c) else float(c) for c in confidence]
    audit = res["audit"].to_numpy() if "audit" in res else np.zeros(len(res), bool)
    return [dict(id=str(i), tier=str(t), label=str(l), confidence=c, accepted=bool(a), audit=bool(u))
            for i, t, l, c, a, u in zip(ids, res["tier"], res["label"], conf, res["accepted"], audit)]


def tier_shares(res: pd.DataFrame, y_true: Sequence[str]) -> pd.DataFrame:
    """Chia sẻ tài liệu theo tầng: n, tỉ lệ, số đúng/sai trong số tài liệu tầng đó nhận."""
    y = np.asarray(y_true)
    rows = []
    for t in TIERS:
        m = (res["tier"] == t).to_numpy()
        n = int(m.sum())
        right = int((res["label"].to_numpy()[m] == y[m]).sum()) if t != "human" else 0
        rows.append(dict(tier=t, n=n, share=n / len(res) if len(res) else float("nan"),
                         correct=right, wrong=(n - right) if t != "human" else 0))
    return pd.DataFrame(rows)
