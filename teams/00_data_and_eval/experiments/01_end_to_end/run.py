r"""Thí nghiệm 01 (Data & Eval) - end-to-end: tách trang -> phân loại từng lát cắt, theo TỆP (CP3 của docs/PARALLEL_RESEARCH_PLAN.md).

Chạy từ gốc repo:
    .venv\Scripts\python.exe -X utf8 teams/00_data_and_eval/experiments/01_end_to_end/run.py --stage dev                 # đếm lời gọi LLM còn thiếu, dừng nếu thiếu
    .venv\Scripts\python.exe -X utf8 teams/00_data_and_eval/experiments/01_end_to_end/run.py --stage dev --call-llm      # gọi Ollama cho văn bản thiếu (qua cache đĩa)
    .venv\Scripts\python.exe -X utf8 teams/00_data_and_eval/experiments/01_end_to_end/run.py --stage test --final-test   # MỘT lần, cấu hình đã đóng băng trong dev_selection.json
    .venv\Scripts\python.exe -X utf8 teams/00_data_and_eval/experiments/01_end_to_end/run.py --stage assemble            # ghép RESULTS.md
Phạm vi dev = DEV + EXCLUDED_COMPOSITE (được nhìn lỗi, chọn biến thể / ngưỡng). TEST chỉ ở --stage test.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import e2e_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RES = HERE / "results"
SELECTION = HERE / "dev_selection.json"
REGISTRY = HERE / "test_run_registry.json"
TAU_GRID = (0.5, 0.7, 0.9, 0.95, 0.98)
FLAG_GRID = (0.3, 0.5, 0.7, 0.9, 0.95)
BAND_LO = (0.02, 0.05, 0.1, 0.2, 0.3)
BAND_HI = (0.6, 0.7, 0.8, 0.9, 0.95)
MAX_ERR = 0.01          # mức sai lặng lẽ tối đa trong số tệp tự xử lý (giao thức đánh giá §7: 1%); độ nhạy 2% in kèm


def sha10(p: Path) -> str:
    return hashlib.sha1(Path(p).read_bytes()).hexdigest()[:10]


def pc(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f}%".replace(".", ",")


def fmt_ci(p, lo, hi, d: int = 1) -> str:
    return f"{pc(p, d)} [{pc(lo, d)}; {pc(hi, d)}]"


V = L.Variant


def raw_variants():
    vs = [V("S0", "none"), V("S1", "rule"), V("S2", "rule_v2"), V("S5", "rule_v2", merge=True)]
    for t in TAU_GRID:
        vs += [V(f"M{t}", "model", t), V(f"M{t}+m", "model", t, merge=True)]
    for t in (0.5, 0.7):
        for k in (0.9, 0.95, 0.98, 0.99):
            vs.append(V(f"K{t}/{k}+m", "model", t, True, None, k))
    return vs


def spec_of(v: L.Variant) -> dict:
    return dict(name=v.name, base=v.base, tau=v.tau, merge=v.merge, band=list(v.band) if v.band else None, keep=v.keep)


def variant_of(d: dict) -> L.Variant:
    return V(d["name"], d["base"], d["tau"], d["merge"], tuple(d["band"]) if d.get("band") else None, d.get("keep"))


# ---------------------------------------------------------------------------
# Chạy: 2 pha (gom văn bản LLM còn thiếu -> gọi -> chấm lại từ cache)
# ---------------------------------------------------------------------------
def ensure_llm(cases, scores, variants, bench, splits, one_sheet, call_llm: bool, timeout: float, label: str, strict: bool = False) -> dict:
    sink: set = set()
    rec = L.Classifiers(bench, splits, record_sink=sink)
    t0 = time.perf_counter()
    for c in cases:
        for v in variants:
            L.score_case(c, v, scores.get(c.doc_id), rec, one_sheet)
    print(f"[{label}] pha ghi nhận: {len(sink)} văn bản LLM chưa có trong cache ({time.perf_counter() - t0:.0f} s CPU); cache hit {rec.cache.hits}", flush=True)
    lat = []
    errs = 0
    if sink:
        if not call_llm:
            print("Thiếu lời gọi LLM. Chạy lại với --call-llm (cần Ollama + qwen3.5:4b; kiểm /api/ps trước).")
            sys.exit(3)
        real = L.Classifiers(bench, splits, record_sink=None, timeout=timeout)
        for i, t in enumerate(sorted(sink), 1):
            a = real.backend.answer(t)
            lat.append(a.latency_ms)
            errs += int(not a.parse_ok)
            if i % 10 == 0 or i == len(sink):
                print(f"  LLM {i}/{len(sink)}  (lỗi {errs}; độ trễ trung vị {np.median(lat):.0f} ms, max {max(lat):.0f} ms)", flush=True)
        if errs:
            print(f"CẢNH BÁO: {errs} lời gọi LLM lỗi/hết giờ; chạy lại --call-llm để thử lại (cache không nhớ lỗi).")
            if strict:
                print("Dừng TRƯỚC khi chấm: không để lời gọi LLM lỗi làm hỏng lần chấm TEST duy nhất. Chạy lại cùng lệnh (các lời gọi đã xong nằm trong cache).")
                sys.exit(4)
    return dict(n_new_llm_texts=len(sink), llm_errors=errs, llm_latency_ms=lat)


def score_all(cases, scores, variants, clfs, one_sheet) -> pd.DataFrame:
    return pd.DataFrame([L.score_case(c, v, scores.get(c.doc_id), clfs, one_sheet) for c in cases for v in variants])


# ---------------------------------------------------------------------------
# Tổng hợp
# ---------------------------------------------------------------------------
class Summary:
    def __init__(self, df: pd.DataFrame, weights, names, B=L.BOOT_N):
        self.df, self.names = df, list(names)
        base = df[df.variant == self.names[0]]
        self.n = base.group.value_counts().to_dict()
        self.boot = L.Boot(self.n, weights, B)
        self.groups = self.boot.groups
        self.vec = {}
        for v in self.names:
            sub = df[df.variant == v]
            for col in ("exact", "types_ok", "full", "auto", "silent_err", "abstain", "n_llm", "n_slices", "unsure", "docs_ok", "docs_total", "docs_ok_auto"):
                self.vec[(v, col)] = L.by_group(sub, col, self.groups)
        # chỉ số tệp toàn cục (bootstrap theo tệp, không phân tầng) cho tỉ lệ cấp tài liệu
        ids = sorted(base.doc_id)
        self.gidx = np.random.default_rng(L.BOOT_SEED + 1).integers(0, len(ids), size=(B, len(ids)))
        self.gids = ids

    def wavg(self, v: str, col: str):
        return self.boot.weighted(self.vec[(v, col)])

    def aut_corr(self, v: str):
        """Trọng số: tệp tự xử lý hoàn toàn VÀ đúng hoàn toàn."""
        a = {g: self.vec[(v, "auto")][g] * self.vec[(v, "full")][g] for g in self.groups}
        return self.boot.weighted(a)

    def cell(self, v: str, col: str, g: str) -> str:
        """k/n = p [Clopper-Pearson 95%]: khoảng nhị thức chính xác cho nhóm nhỏ (bootstrap suy biến thành [0;0] khi k = 0 hoặc n)."""
        x = self.vec[(v, col)][g]
        k, n = int(x.sum()), len(x)
        lo, hi = L.cp_interval(k, n)
        return f"{k}/{n} = {fmt_ci(k / n, lo, hi, 0)}"

    def table_metric(self, col: str, title: str, label=lambda v: v) -> str:
        head = "| biến thể | " + " | ".join(f"{L.GROUP_VI[g]} (n={self.n[g]})" for g in self.groups) + " | **toàn bộ, theo cơ cấu tệp thật** |"
        out = [f"**{title}**", "", head, "|---|" + "---|" * (len(self.groups) + 1)]
        for v in self.names:
            p, bt = self.wavg(v, col)
            lo, hi = L.ci95(bt)
            out.append(f"| {label(v)} | " + " | ".join(self.cell(v, col, g) for g in self.groups) + f" | **{fmt_ci(p, lo, hi)}** |")
        return "\n".join(out)

    def routing_numbers(self, v: str):
        pa, ba = self.wavg(v, "auto")
        ps, bs = self.wavg(v, "silent_err")
        pac, bac = self.aut_corr(v)
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.where(ba > 0, bs / ba, np.nan)
        return dict(auto=(pa, *L.ci95(ba)), silent=(ps, *L.ci95(bs)), autocorr=(pac, *L.ci95(bac)),
                    err_auto=(ps / pa if pa else float("nan"), *np.nanpercentile(ratio, [2.5, 97.5])))

    def table_routing(self, label=lambda v: v) -> str:
        out = ["| biến thể | tự xử lý hoàn toàn | tự xử lý VÀ đúng | sai lặng lẽ (tự xử lý mà sai) | sai lặng lẽ / tự xử lý | thô: tự xử lý / tệp | thô: sai / tự xử lý (Clopper-Pearson 95%) |",
               "|---|---|---|---|---|---|---|"]
        N = sum(self.n.values())
        for v in self.names:
            r = self.routing_numbers(v)
            na = int(sum(self.vec[(v, "auto")][g].sum() for g in self.groups))
            ns = int(sum(self.vec[(v, "silent_err")][g].sum() for g in self.groups))
            cl, ch = L.cp_interval(ns, na)
            out.append(f"| {label(v)} | {fmt_ci(*r['auto'])} | {fmt_ci(*r['autocorr'])} | {fmt_ci(*r['silent'], d=2)} | {fmt_ci(*r['err_auto'], d=2)} | "
                       f"{na}/{N} | {ns}/{na} = {fmt_ci(ns / na if na else float('nan'), cl, ch, 2)} |")
        return "\n".join(out)

    def doc_rate(self, v: str, col: str = "docs_ok_auto"):
        sub = self.df[self.df.variant == v].set_index("doc_id").loc[self.gids]
        k, t = sub[col].to_numpy(float), sub["docs_total"].to_numpy(float)
        pt = k.sum() / t.sum()
        bt = k[self.gidx].sum(axis=1) / t[self.gidx].sum(axis=1)
        return pt, *L.ci95(bt), int(k.sum()), int(t.sum())

    def doc_diff(self, a: str, b: str, col: str = "docs_ok_auto"):
        """Hiệu a - b của tỉ lệ tài liệu đáp án giao đúng và tự động, bootstrap ghép cặp theo tệp."""
        ta = self.df[self.df.variant == a].set_index("doc_id").loc[self.gids]
        tb = self.df[self.df.variant == b].set_index("doc_id").loc[self.gids]
        t = ta["docs_total"].to_numpy(float)
        ka, kb = ta[col].to_numpy(float), tb[col].to_numpy(float)
        d = (ka.sum() - kb.sum()) / t.sum()
        bt = (ka[self.gidx].sum(axis=1) - kb[self.gidx].sum(axis=1)) / t[self.gidx].sum(axis=1)
        return d, *L.ci95(bt)

    def table_docs(self, label=lambda v: v) -> str:
        out = ["| biến thể | tài liệu đáp án giao ĐÚNG và tự động | tài liệu đáp án (tổng) | trong đó của các nhóm composite (n tài liệu) |", "|---|---|---|---|"]
        for v in self.names:
            p, lo, hi, k, t = self.doc_rate(v)
            comp = self.df[(self.df.variant == v) & self.df.group.isin(["mixed", "same_other", "same_bb"])]
            out.append(f"| {label(v)} | {k}/{t} = {fmt_ci(p, lo, hi)} | {t} | {int(comp.docs_ok_auto.sum())}/{int(comp.docs_total.sum())} |")
        return "\n".join(out)

    def table_cost(self, label=lambda v: v) -> str:
        out = ["| biến thể | " + " | ".join(L.GROUP_VI[g] for g in self.groups) + " | tổng lời gọi LLM / tổng lát cắt |", "|---|" + "---|" * (len(self.groups) + 1)]
        for v in self.names:
            cells = [f"{self.vec[(v, 'n_llm')][g].mean():.2f} LLM, {self.vec[(v, 'n_slices')][g].mean():.2f} lát" for g in self.groups]
            tl = int(sum(self.vec[(v, "n_llm")][g].sum() for g in self.groups))
            ts = int(sum(self.vec[(v, "n_slices")][g].sum() for g in self.groups))
            out.append(f"| {label(v)} | " + " | ".join(cells) + f" | {tl} / {ts} |")
        return "\n".join(out)

    def harm(self, ref: str = "S0", label=lambda v: v) -> str:
        out = [f"Mỗi ô: (tệp {ref} đúng hoàn toàn mà biến thể làm hỏng) hỏng / (tệp {ref} sai mà biến thể sửa được) sửa.", "",
               "| biến thể | " + " | ".join(L.GROUP_VI[g] for g in self.groups) + f" | hiệu có trọng số (biến thể - {ref}) của (c), CI ghép cặp | kết luận |",
               "|---|" + "---|" * (len(self.groups) + 2)]
        p0, b0 = self.wavg(ref, "full")
        for v in self.names:
            if v == ref:
                continue
            cells = []
            for g in self.groups:
                r, x = self.vec[(ref, "full")][g], self.vec[(v, "full")][g]
                cells.append(f"{int(((r == 1) & (x == 0)).sum())} hỏng / {int(((r == 0) & (x == 1)).sum())} sửa")
            p1, b1 = self.wavg(v, "full")
            lo, hi = L.ci95(b1 - b0)
            verdict = "không tách được" if lo <= 0 <= hi else ("tách được: tốt hơn" if p1 - p0 > 0 else "tách được: kém hơn")
            out.append(f"| {label(v)} | " + " | ".join(cells) + f" | {100 * (p1 - p0):+.1f} điểm [{100 * lo:+.1f}; {100 * hi:+.1f}] | {verdict} |")
        return "\n".join(out)

    def paired(self, a: str, b: str, col: str = "full"):
        pa, ba = self.wavg(a, col)
        pb, bb = self.wavg(b, col)
        lo, hi = L.ci95(ba - bb)
        return pa - pb, lo, hi


# ---------------------------------------------------------------------------
# Quy tắc chọn trên dev (đặt SAU khi xem số dev; không dùng TEST). Một quy tắc cho mọi lựa chọn (tau, dải, mặc định cuối).
# ---------------------------------------------------------------------------
def point_stats(df: pd.DataFrame, weights, n) -> dict:
    """{variant: (tự xử lý và đúng, sai lặng lẽ / tự xử lý, lời gọi LLM trung bình mỗi tệp)} (điểm, có trọng số theo cơ cấu tệp thật)."""
    out = {}
    w = L.Boot(n, weights, 2).w
    for v, sub in df.groupby("variant"):
        ac = sum(w[g] * float(((s.auto == 1) & (s.full == 1)).mean()) for g, s in sub.groupby("group") if g in w)
        au = sum(w[g] * float(s.auto.mean()) for g, s in sub.groupby("group") if g in w)
        si = sum(w[g] * float(s.silent_err.mean()) for g, s in sub.groupby("group") if g in w)
        ll = sum(w[g] * float(s.n_llm.mean()) for g, s in sub.groupby("group") if g in w)
        out[v] = dict(auto=au, autocorr=ac, silent=si, err_auto=si / au if au else 1.0, llm=ll)
    return out


def rule_pick(stats: dict, names, max_err: float = MAX_ERR):
    """Trong các biến thể có sai lặng lẽ/tự xử lý <= max_err (có trọng số), chọn cái có 'tự xử lý và đúng' lớn nhất (hòa trong 0,2 điểm -> ít lời gọi LLM hơn).
    Không biến thể nào đạt -> chọn cái có sai lặng lẽ/tự xử lý thấp nhất."""
    ok = [v for v in names if stats[v]["err_auto"] <= max_err + 1e-12]
    if not ok:
        return min(names, key=lambda v: (stats[v]["err_auto"], -stats[v]["autocorr"])), False
    best = max(stats[v]["autocorr"] for v in ok)
    near = [v for v in ok if stats[v]["autocorr"] >= best - 0.002]
    return min(near, key=lambda v: (stats[v]["llm"], v)), True


def md_df(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join((f"{x:.4f}" if isinstance(x, (float, np.floating)) else str(x)) for x in r) + " |")
    return "\n".join(out)


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", choices=["dev", "test", "assemble"], default="dev")
    ap.add_argument("--call-llm", action="store_true", help="được phép gọi Ollama cho văn bản chưa có trong cache")
    ap.add_argument("--final-test", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="--stage test chạy thử TOÀN BỘ đường mã trên tệp DEV (không mở TEST, không ghi sổ đăng ký)")
    ap.add_argument("--timeout", type=float, default=120.0, help="giây cho MỖI lời gọi LLM")
    args = ap.parse_args()
    RES.mkdir(exist_ok=True)
    if args.stage == "assemble":
        return assemble()
    from harness import load_benchmark, load_or_make_splits
    bench = load_benchmark(L.REPO / "data" / "labels_v2.csv")
    splits = load_or_make_splits(bench)
    one_sheet = L.load_one_sheet_types()
    print("loại 'một tờ = một tài liệu' suy ra từ taxonomy:", sorted(one_sheet))
    if args.stage == "dev":
        return stage_dev(args, bench, splits, one_sheet)
    return stage_test(args, bench, splits, one_sheet)


DELTA = 0.03            # cổng 'không hại tệp thường': cận dưới CI 95% ghép cặp của (c) so với S0 phải >= -DELTA
KAPPA_GRID = (0.9, 0.95, 0.98, 0.99)
KTAU_GRID = (0.5, 0.7)


def gate_rows(S: Summary, names, ref: str = "S0", delta: float = DELTA) -> pd.DataFrame:
    """Với mỗi biến thể: Δ(c) so với ref (CI ghép cặp), sai lặng lẽ / tự xử lý, tài liệu giao đúng tự động (cấp tài liệu), lời gọi LLM mỗi tệp."""
    rows = []
    r_ref = S.routing_numbers(ref)["err_auto"][0]
    for v in names:
        d, lo, hi = S.paired(v, ref) if v != ref else (0.0, 0.0, 0.0)
        r = S.routing_numbers(v)
        pt, dlo, dhi, k, t = S.doc_rate(v)
        llm = sum(S.boot.w[g] * float(S.vec[(v, "n_llm")][g].mean()) for g in S.groups)
        rows.append(dict(name=v, d_full=d, d_lo=lo, d_hi=hi, err_auto=r["err_auto"][0], doc_auto=pt, doc_k=k, llm=llm,
                         gate_file=bool(v == ref or lo >= -delta), gate_silent=bool(r["err_auto"][0] <= r_ref + 1e-9)))
    return pd.DataFrame(rows)


def complexity(v: L.Variant) -> int:
    """Số 'núm' của biến thể (để phá hòa theo nguyên tắc đơn giản hơn)."""
    return ({"none": 0, "rule": 1, "rule_v2": 1, "model": 2}[v.base] + int(v.base == "model" and v.tau != 0.5) + int(v.merge)
            + int(v.keep is not None) + int(v.band is not None))


def pick_by_gate(S: Summary, names, cx: dict, ref: str = "S0", silent_gate: bool = True):
    """Quy tắc chọn trên dev (đặt SAU khi xem số dev; không dùng TEST):
    (1) cổng tệp thường: cận dưới CI 95% ghép cặp của Δ(c) so với S0 >= -3 điểm; (2) cổng an toàn: sai lặng lẽ / tự xử lý không cao hơn S0;
    (3) trong các biến thể qua cổng, chọn biến thể giao đúng-và-tự-động nhiều TÀI LIỆU đáp án nhất; các biến thể mà hiệu cấp tài liệu so với biến thể tốt nhất
    có CI ghép cặp chứa 0 ("không tách được") coi là hòa -> ít núm điều chỉnh hơn, rồi ít lời gọi LLM hơn.
    `silent_gate=False` bỏ cổng an toàn (dùng cho S6, hiệu chỉnh chỉ-ngưỡng)."""
    g = gate_rows(S, names, ref)
    g["núm"] = g["name"].map(cx)
    ok = g[g.gate_file & (g.gate_silent | (not silent_gate))]
    if ok.empty:
        return ref, g
    best = str(ok.sort_values("doc_auto", ascending=False).iloc[0]["name"])
    tied = [best] + [v for v in ok["name"] if v != best and (lambda d: d[1] <= 0 <= d[2])(S.doc_diff(v, best))]
    t = ok[ok["name"].isin(tied)]
    return str(t.sort_values(["núm", "llm", "name"]).iloc[0]["name"]), g


def stage_dev(args, bench, splits, one_sheet):
    cases, gold = L.load_cases("dev")
    weights = L.population_weights(gold)
    scores = L.crossfit_pair_scores(gold, cases, RES / "pair_scores_dev.json")
    n = {}
    for c in cases:
        n[c.group] = n.get(c.group, 0) + 1
    print("số tệp dev theo nhóm:", n, "| trọng số:", {k: round(v, 3) for k, v in weights.items()})

    variants = raw_variants()
    info = ensure_llm(cases, scores, variants, bench, splits, one_sheet, args.call_llm, args.timeout, "dev")
    clf = L.Classifiers(bench, splits, mode="readonly")                 # từ đây KHÔNG gọi mô hình nữa
    df_raw = score_all(cases, scores, variants, clf, one_sheet)
    raw_names = [v.name for v in variants]
    S_raw = Summary(df_raw, weights, raw_names)
    # --- chọn tau cho S6 (không gộp), tau cho S7 (có gộp), (tau, kappa) cho S10 bằng CÙNG quy tắc
    cx_raw = {v.name: complexity(v) for v in variants}
    p6, g6 = pick_by_gate(S_raw, [f"M{t}" for t in TAU_GRID], cx_raw, silent_gate=False)
    p7, g7 = pick_by_gate(S_raw, [f"M{t}+m" for t in TAU_GRID], cx_raw)
    p10, g10 = pick_by_gate(S_raw, [f"K{t}/{k}+m" for t in KTAU_GRID for k in KAPPA_GRID], cx_raw)
    print("S6 =", p6, "| S7 =", p7, "| S10 =", p10)
    t6 = float(p6[1:])
    t7 = float(p7[1:].replace("+m", ""))
    t10, k10 = (float(x) for x in p10[1:].replace("+m", "").split("/"))

    # --- S8: dải 'splitter không chắc' trên S7;  S9: không tách, cờ 'nghi composite' khi điểm cặp trang cao
    band_stats = {}
    for lo in BAND_LO:
        for hi in BAND_HI:
            v = V(f"B{lo}-{hi}", "model", t7, True, (lo, hi))
            band_stats[v.name] = (v, score_all(cases, scores, [v], clf, one_sheet))
    bn = list(band_stats)
    bst = point_stats(pd.concat([band_stats[b][1] for b in bn]), weights, n)
    b_pick, b_ok = rule_pick(bst, bn, 0.02)
    S8 = band_stats[b_pick][0]
    flag_stats = {}
    for f in FLAG_GRID:
        v = V(f"F{f}", "none", 0.5, False, (f, 1.01))
        flag_stats[v.name] = (v, score_all(cases, scores, [v], clf, one_sheet))
    fn = list(flag_stats)
    fst = point_stats(pd.concat([flag_stats[b][1] for b in fn]), weights, n)
    f_pick, f_ok = rule_pick(fst, fn, 0.02)
    S9 = flag_stats[f_pick][0]
    print("S8 dải:", S8.band, "(<=2%)" if b_ok else "(không đạt 2%)", "| S9 cờ:", S9.band[0], "(<=2%)" if f_ok else "(không đạt 2%)")

    final = [("S0", V("S0", "none")), ("S1", V("S1", "rule")), ("S2", V("S2", "rule_v2")), ("S3", V("S3", "model", 0.5)),
             ("S4", V("S4", "model", 0.5, True)), ("S5", V("S5", "rule_v2", merge=True)), ("S6", V("S6", "model", t6)),
             ("S7", V("S7", "model", t7, True)), ("S10", V("S10", "model", t10, True, None, k10)),
             ("S8", V("S8", "model", t7, True, S8.band)), ("S9", V("S9", "none", 0.5, False, S9.band))]
    desc = {"S0": "không tách (cả tệp = một tài liệu)", "S1": "luật cũ", "S2": "luật v2", "S3": "mô hình cặp trang, ngưỡng 0,5",
            "S4": "S3 + gộp lát cắt liền kề cùng loại (trừ loại một-tờ)", "S5": "S2 + gộp lát cắt liền kề cùng loại",
            "S6": f"mô hình, ngưỡng tau6={t6} chọn trên dev", "S7": f"mô hình, ngưỡng tau7={t7} + gộp cùng loại",
            "S10": f"mô hình tau={t10} + gộp cùng loại TRỪ ranh giới có điểm >= {k10}",
            "S8": f"S7 + tệp có điểm cặp trang trong [{S8.band[0]}; {S8.band[1]}) -> người (splitter không chắc)",
            "S9": f"không tách; tệp có điểm cặp trang >= {S9.band[0]} -> người (nghi composite)"}
    df = score_all(cases, scores, [v for _, v in final], clf, one_sheet)
    df.to_csv(RES / "per_file_dev.csv", index=False, encoding="utf-8")        # chứa doc_id: chỉ dùng nội bộ
    names = [k for k, _ in final]
    S = Summary(df, weights, names)
    pick, gf = pick_by_gate(S, names, {k: complexity(v) for k, v in final})
    print("MẶC ĐỊNH CHỌN:", pick)
    print(gf.to_string())
    chk = sanity_vs_03(df, cases)

    sel = dict(created=datetime.now(timezone.utc).isoformat(timespec="seconds"), labels_sha1_10=bench.labels_sha,
               gold_sha1_10=sha10(L.sl.GOLD_CSV), ocr_sha1_10=sha10(L.sl.OCR_JSONL), splits_sha1_10=sha10(L.sl.SPLITS_CSV),
               rule=("(1) cổng tệp thường: cận dưới CI 95% ghép cặp của hiệu (c) so với S0 >= -3 điểm; (2) cổng an toàn: sai lặng lẽ / tự xử lý không cao hơn S0 (không áp dụng khi chọn S6); "
                     "(3) trong các biến thể qua cổng, giao đúng và tự động nhiều tài liệu đáp án nhất; hòa (hiệu cấp tài liệu so với tốt nhất có CI ghép cặp chứa 0) -> ít núm điều chỉnh hơn, rồi ít lời gọi LLM hơn. "
                     "Quy tắc đặt SAU khi xem số dev (mục tiêu ban đầu 1% sai lặng lẽ không biến thể nào đạt); không dùng TEST."),
               delta=DELTA, chosen=pick, one_sheet_types=sorted(one_sheet), specs={k: spec_of(v) for k, v in final},
               gate_table=gf.to_dict("records"), tau6=t6, tau7=t7, tau10=t10, kappa10=k10, band_s8=list(S8.band), flag_s9=S9.band[0],
               grid_gate_tau6=g6.to_dict("records"), grid_gate_tau7=g7.to_dict("records"), grid_gate_s10=g10.to_dict("records"),
               band_grid_stats=bst, flag_grid_stats=fst, n_dev_files=n, cascade_selection_sha1_10=sha10(Path(L.DEFAULT_SELECTION_PATH)),
               sanity_vs_03={k: v for k, v in chk.items() if k != "text"})
    if REGISTRY.exists() and SELECTION.exists():
        # lựa chọn đã ĐÓNG BĂNG (TEST đã chấm): chỉ kiểm lại rằng dev tái lập đúng lựa chọn, KHÔNG ghi đè dev_selection.json
        old = json.loads(SELECTION.read_text(encoding="utf-8"))
        assert old["chosen"] == sel["chosen"] and old["specs"] == sel["specs"], "dev không còn tái lập lựa chọn đã đóng băng"
        print("dev_selection.json đã đóng băng và khớp lần chạy này; không ghi đè.")
    else:
        SELECTION.write_text(json.dumps(sel, ensure_ascii=False, indent=1, default=float), encoding="utf-8")

    lab = lambda v: f"{v} ({desc[v]})"
    parts = [f"## Kết quả trên phạm vi dev (n = {sum(n.values())} tệp: " + ", ".join(f"{L.GROUP_VI[g]} {n[g]}" for g in S.groups) + ")", "",
             S.table_metric("full", "(c) Tệp đúng hoàn toàn = (a) tách đúng ∧ (b) mọi tài liệu đáp án có đúng loại", lab), "",
             S.table_metric("exact", "(a) Tách đúng hoàn toàn (các lát cắt = đúng các segment đáp án)", lab), "",
             S.table_metric("types_ok", "(b) Mọi segment đáp án khớp một lát cắt (trùng nhiều trang nhất) được TỰ NHẬN đúng loại", lab), "",
             "### (d) Định tuyến: tự xử lý hoàn toàn và sai lặng lẽ", "", S.table_routing(lab), "",
             "### Cấp tài liệu (cho thấy thứ mà file-level che giấu)", "", S.table_docs(lab), "",
             "### (e) Phân tích hại so với S0", "", S.harm("S0", lab), "",
             "### Số lời gọi LLM và số lát cắt mỗi tệp", "", S.table_cost(lab), ""]
    pr = ["### So sánh ghép cặp (hiệu của (c) có trọng số, CI 95% bootstrap ghép cặp)", "", "| cặp | hiệu | CI | kết luận |", "|---|---|---|---|"]
    for a, b in (("S4", "S3"), ("S10", "S4"), ("S10", "S7"), ("S7", "S6"), ("S4", "S5"), ("S3", "S2"), ("S2", "S1"), ("S10", "S0"), ("S7", "S0")):
        d, lo, hi = S.paired(a, b)
        pr.append(f"| {a} - {b} | {100 * d:+.1f} điểm | [{100 * lo:+.1f}; {100 * hi:+.1f}] | {'không tách được' if lo <= 0 <= hi else 'tách được'} |")
    parts += pr + [""]
    ren = {"name": "biến thể", "d_full": "Δ(c) so S0", "d_lo": "CI lo", "d_hi": "CI hi", "err_auto": "sai lặng lẽ/tự xử lý", "doc_auto": "tài liệu đúng+tự động",
           "doc_k": "tài liệu (số)", "llm": "LLM/tệp", "gate_file": "cổng tệp thường", "gate_silent": "cổng an toàn"}
    bg = pd.DataFrame([dict(dải=k[1:], tự_xử_lý=v["auto"], tự_xử_lý_và_đúng=v["autocorr"], sai_lặng_lẽ_trên_tự_xử_lý=v["err_auto"]) for k, v in bst.items()])
    fg = pd.DataFrame([dict(cờ_tối_thiểu=k[1:], tự_xử_lý=v["auto"], tự_xử_lý_và_đúng=v["autocorr"], sai_lặng_lẽ_trên_tự_xử_lý=v["err_auto"]) for k, v in fst.items()])
    grids = []
    for title, g in (("S6: tau, không gộp", g6), ("S7: tau, có gộp", g7), ("S10: (tau, kappa), có gộp trừ ranh giới điểm >= kappa", g10)):
        grids += [f"#### {title}", "", md_df(g.rename(columns=ren)), ""]
    parts += ["## Lưới chọn tham số trên dev (cùng một quy tắc cho mọi lựa chọn)", "", f"**Quy tắc:** {sel['rule']}", ""] + grids + [
        "### Dải S8 (trên S7; chọn: tự xử lý và đúng lớn nhất với sai lặng lẽ <= 2%, không đạt thì sai thấp nhất)", "", md_df(bg), "",
        "### Cờ S9 (trên S0; cùng cách chọn)", "", md_df(fg), "",
        f"**Chọn:** S6 = {p6}, S7 = {p7}, S10 = {p10}, S8 dải {S8.band}, S9 cờ {S9.band[0]}.", "",
        "### Chọn mặc định cuối trong S0..S10", "", md_df(gf.rename(columns=ren)), "", f"**Mặc định chọn trên dev: {pick}.**", "",
        "### Kiểm tra: S0 có trùng thí nghiệm 03_src_cascade không?", "", chk["text"], ""]
    (RES / "dev_report.md").write_text("\n".join(parts), encoding="utf-8")
    json.dump(dict(info={k: v for k, v in info.items() if k != "llm_latency_ms"}, llm_latency_ms=info["llm_latency_ms"]),
              open(RES / "dev_stage_state.json", "w", encoding="utf-8"), default=float)
    print("đã ghi", RES / "dev_report.md")


def sanity_vs_03(df: pd.DataFrame, cases) -> dict:
    p = L.REPO / "teams" / "team3_classification" / "results" / "03_src_cascade" / "regress_dev_per_doc.csv"
    if not p.exists():
        return dict(text="(không có regress_dev_per_doc.csv của 03)", n=0, match=0)
    r = pd.read_csv(p, dtype=str, keep_default_na=False).set_index("doc_id")
    s0 = df[df.variant == "S0"].set_index("doc_id")
    n = m = 0
    bad = []
    for d in r.index:
        if d not in s0.index:
            continue
        n += 1
        pred = s0.loc[d, "pred_segs"].split(":", 1)[1]
        pred = "" if pred == "?" else pred
        ok = s0.loc[d, "tiers"] == r.loc[d, "new_tier"] and pred == r.loc[d, "new_label"]
        m += int(ok)
        if not ok:
            bad.append(d)
    return dict(n=n, match=m, bad=bad, text=f"S0 (cả tệp = một lát cắt, văn bản = 2 trang đầu) trùng bộ ba (tầng, nhãn) với `regress_dev_per_doc.csv` của 03 trên {m}/{n} tài liệu DEV.")


# ---------------------------------------------------------------------------
def stage_test(args, bench, splits, one_sheet):
    dry = args.dry_run
    if not args.final_test and not dry:
        raise SystemExit("--stage test cần --final-test (cấu hình đã đóng băng trong dev_selection.json).")
    if not SELECTION.exists():
        raise SystemExit("thiếu dev_selection.json: chạy --stage dev trước.")
    if REGISTRY.exists() and not dry:
        raise SystemExit(f"TEST đã được chấm cho cấu hình này; từ chối chạy lại. Sổ đăng ký: {REGISTRY}")
    sel = json.loads(SELECTION.read_text(encoding="utf-8"))
    if sel["labels_sha1_10"] != bench.labels_sha:
        raise SystemExit("nhãn đã đổi kể từ khi chọn trên dev; không chấm TEST (xem giao thức §4).")
    chosen = variant_of(dict(sel["specs"][sel["chosen"]], name="CHOSEN"))
    ref = V("S0", "none")
    dev_cases, gold = L.load_cases("dev")
    weights = L.population_weights(gold)
    if dry:
        test_cases = dev_cases[::6]                                  # chạy thử trên một phần dev
        scores = json.loads((RES / "pair_scores_dev.json").read_text(encoding="utf-8"))
    else:
        test_cases, _ = L.load_cases("test")
        assert all(c.split == "TEST" for c in test_cases) and not ({c.doc_id for c in test_cases} & {c.doc_id for c in dev_cases})
        scores = L.final_pair_scores(gold, dev_cases, test_cases)        # mô hình huấn luyện trên toàn dev, chấm tệp TEST
    pre = "dryrun_" if dry else ""
    variants = [ref, chosen] if sel["chosen"] != "S0" else [ref]
    info = ensure_llm(test_cases, scores, variants, bench, splits, one_sheet, args.call_llm, args.timeout, "test", strict=not dry)
    clf = L.Classifiers(bench, splits, mode="readonly")
    df = score_all(test_cases, scores, variants, clf, one_sheet)
    df.to_csv(RES / f"{pre}per_file_test.csv", index=False, encoding="utf-8")
    n = df[df.variant == "S0"].group.value_counts().to_dict()
    S = Summary(df, weights, [v.name for v in variants])
    rows = []
    for v in S.names:
        sub = df[df.variant == v]
        k = int(sub.full.sum())
        lo, hi = L.cp_interval(k, len(sub))
        na = int(sub.auto.sum())
        ns = int(sub.silent_err.sum())
        cl, ch = L.cp_interval(ns, na)
        rows.append((v, k, len(sub), lo, hi, na, ns, cl, ch, int(sub.n_llm.sum()), int(sub.n_slices.sum()), int((sub.auto * sub.full).sum())))
    out = [f"## Kết quả TEST (MỘT lần, cấu hình đóng băng = **{sel['chosen']}**: {json.dumps(sel['specs'][sel['chosen']], ensure_ascii=False)})", "",
           f"n = {len(test_cases)} tệp TEST: " + ", ".join(f"{L.GROUP_VI[g]} {n[g]}" for g in L.FILE_GROUPS if g in n) + ". Không có composite khác loại và composite cùng loại ngoài BB_LAY_MAU trong TEST.", "",
           "| biến thể | tệp đúng hoàn toàn (c) | Clopper-Pearson 95% | tự xử lý | sai lặng lẽ / tự xử lý (CP 95%) | tự xử lý và đúng | lời gọi LLM | lát cắt |", "|---|---|---|---|---|---|---|---|"]
    for v, k, nn, lo, hi, na, ns, cl, ch, nl, nsl, ac in rows:
        out.append(f"| {v} | {k}/{nn} = {pc(k / nn)} | [{pc(lo)}; {pc(hi)}] | {na}/{nn} | {ns}/{na} [{pc(cl)}; {pc(ch)}] | {ac}/{nn} | {nl} | {nsl} |")
    out += ["", S.table_metric("full", "(c) theo nhóm", lambda v: v), "", S.table_routing(), "", S.table_docs(), "", S.harm("S0") if len(S.names) > 1 else ""]
    (RES / f"{pre}test_report.md").write_text("\n".join(out), encoding="utf-8")
    if dry:                      # chạy thử trên DEV: không bao giờ ghi sổ đăng ký TEST
        print("\n".join(out))
        return
    assert not dry and all(c.split == "TEST" for c in test_cases)
    REGISTRY.write_text(json.dumps(dict(created=datetime.now(timezone.utc).isoformat(timespec="seconds"), chosen=sel["chosen"],
                                        spec=sel["specs"][sel["chosen"]], n=len(test_cases), n_by_group=n, labels_sha1_10=bench.labels_sha,
                                        dev_selection_sha1_10=sha10(SELECTION), new_llm_texts=info["n_new_llm_texts"],
                                        note="Chấm TEST MỘT lần, cấu hình đóng băng trên dev; không dùng để chỉnh gì. Khác lần mở TEST phân loại (đã dùng ở 02/03)."),
                                   ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(out))


def assemble():
    dev = (RES / "dev_report.md").read_text(encoding="utf-8")
    notes = (HERE / "notes.md").read_text(encoding="utf-8") if (HERE / "notes.md").exists() else ""
    test = (RES / "test_report.md").read_text(encoding="utf-8") if (RES / "test_report.md").exists() else "(TEST chưa chấm)"
    head = (HERE / "header.md").read_text(encoding="utf-8") if (HERE / "header.md").exists() else "# 01 - End-to-end"
    (HERE / "RESULTS.md").write_text("\n\n".join([head, dev, test, notes]), encoding="utf-8")
    print("đã ghi", HERE / "RESULTS.md")


if __name__ == "__main__":
    main()
