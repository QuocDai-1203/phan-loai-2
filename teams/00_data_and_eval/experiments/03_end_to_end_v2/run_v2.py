r"""Thí nghiệm 03 (Data & Eval) - toàn trình v2: S10 so với S10 + quy tắc "bản khác" (id) + gỡ mơ hồ theo tiêu đề (tiebreak), theo TỆP.

Chạy từ gốc repo:
    .venv\Scripts\python.exe -X utf8 teams/00_data_and_eval/experiments/03_end_to_end_v2/run_v2.py --stage dev [--call-llm]
    .venv\Scripts\python.exe -X utf8 teams/00_data_and_eval/experiments/03_end_to_end_v2/run_v2.py --stage test --final-test [--call-llm]   # MỘT lần
    .venv\Scripts\python.exe -X utf8 teams/00_data_and_eval/experiments/03_end_to_end_v2/run_v2.py --stage assemble

Dùng lại thư viện của thí nghiệm 01 (cùng 245 tệp dev, cùng thước đo, cùng điểm cặp trang cross-fit, cùng bootstrap/seed). Quy tắc chọn nằm trong
dev_selection_v2.json (ghi TRƯỚC khi chạy dev). Văn bản = data/ocr_v2.jsonl (không OCR lại). Lời gọi LLM phân loại: cache có sẵn, lời gọi mới ghi cache đĩa riêng.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
E2E = HERE.parent / "01_end_to_end"
sys.path.insert(0, str(E2E))
import e2e_lib as L  # noqa: E402
import run as R  # noqa: E402  (thí nghiệm 01: Summary, bảng, định dạng)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RES = HERE / "results"
SELECTION = HERE / "dev_selection_v2.json"
REGISTRY = E2E / "test_run_registry.json"
OWN_CACHE = HERE / "_cache" / "ollama"
# lời gọi LLM mới ghi vào cache của thí nghiệm này; cache của 01 (đã có ~100 lời gọi) chỉ đọc
L.CACHE_EXTRA = [L.CACHE_OWN] + list(L.CACHE_EXTRA)
L.CACHE_OWN = OWN_CACHE


@dataclass(frozen=True)
class V2(L.Variant):
    id_rule: bool = False         # quy tắc "bản khác" THÊM ranh giới điểm 1,0 (src/splitting/learned_id.py)
    tiebreak: bool = False        # DocumentClassifier.rule_title_tiebreak


S10 = dict(base="model", tau=0.7, merge=True, keep=0.99)
VARIANTS = [V2("S10", **S10), V2("S10+id", **S10, id_rule=True), V2("S10+tb", **S10, tiebreak=True), V2("S10+id+tb", **S10, id_rule=True, tiebreak=True),
            V2("S9", "none", 0.5, False, (0.3, 1.01)), V2("S0", "none")]
CANDIDATES = ["S10", "S10+id", "S10+tb", "S10+id+tb"]
DESC = {"S10": "mô hình tau=0,7 + gộp cùng loại trừ điểm >= 0,99 (mặc định hiện tại)", "S10+id": "S10 + quy tắc 'bản khác' (model+merge+id)",
        "S10+tb": "S10 + gỡ mơ hồ theo tiêu đề (rule_title_tiebreak)", "S10+id+tb": "S10 + id + tiebreak",
        "S9": "không tách; điểm cặp trang >= 0,3 -> người (triage, đối chiếu)", "S0": "không tách (đối chiếu)"}


class TBClassifiers(L.Classifiers):
    """Như Classifiers nhưng mọi DocumentClassifier bật rule_title_tiebreak."""

    def clf(self, key):
        c = super().clf(key)
        c.rule_title_tiebreak = True
        return c


def make_clfs(bench, splits, sink=None, timeout=120.0, mode="live"):
    return {False: L.Classifiers(bench, splits, record_sink=sink, timeout=timeout, mode=mode),
            True: TBClassifiers(bench, splits, record_sink=sink, timeout=timeout, mode=mode)}


_ID_MEMO: dict = {}


def bumped_scores(c: L.Case, scores):
    """Điểm cặp trang sau quy tắc id: trang được cờ nhận điểm 1,0 (đúng như src/splitting/policy.split_with_policy)."""
    if scores is None:
        return None
    if c.doc_id not in _ID_MEMO:
        from src.splitting.learned_id import id_rule_pages
        _ID_MEMO[c.doc_id] = id_rule_pages([p.full_text for p in c.doc.pages])
    fl = _ID_MEMO[c.doc_id]
    return [1.0 if fl[i] else s for i, s in enumerate(scores)]


def score_v2(c, v: V2, scores, clfs, one_sheet) -> dict:
    sc = bumped_scores(c, scores) if v.id_rule else scores
    return L.score_case(c, v, sc, clfs[v.tiebreak], one_sheet)


def score_all(cases, scores, variants, clfs, one_sheet) -> pd.DataFrame:
    return pd.DataFrame([score_v2(c, v, scores.get(c.doc_id), clfs, one_sheet) for c in cases for v in variants])


def ensure_llm(cases, scores, variants, bench, splits, one_sheet, call_llm, timeout, label, strict=False) -> dict:
    sink: set = set()
    rec = make_clfs(bench, splits, sink=sink)
    t0 = time.perf_counter()
    for c in cases:
        for v in variants:
            score_v2(c, v, scores.get(c.doc_id), rec, one_sheet)
    print(f"[{label}] pha ghi nhận: {len(sink)} văn bản LLM chưa có trong cache ({time.perf_counter() - t0:.0f} s CPU)", flush=True)
    lat, errs = [], 0
    if sink:
        if not call_llm:
            print("Thiếu lời gọi LLM. Chạy lại với --call-llm (cần Ollama + qwen3.5:4b).")
            sys.exit(3)
        real = L.Classifiers(bench, splits, record_sink=None, timeout=timeout)
        for i, t in enumerate(sorted(sink), 1):
            a = real.backend.answer(t)
            lat.append(a.latency_ms)
            errs += int(not a.parse_ok)
            if i % 5 == 0 or i == len(sink):
                print(f"  LLM {i}/{len(sink)} (lỗi {errs}; độ trễ trung vị {np.median(lat):.0f} ms, max {max(lat):.0f} ms)", flush=True)
        if errs:
            print(f"CẢNH BÁO: {errs} lời gọi LLM lỗi/hết giờ; chạy lại --call-llm để thử lại.")
            if strict:
                print("Dừng TRƯỚC khi chấm TEST (không để lời gọi lỗi làm hỏng lần chấm duy nhất).")
                sys.exit(4)
    return dict(n_new_llm_texts=len(sink), llm_errors=errs, llm_latency_ms=lat)


# ---------------------------------------------------------------------------
def raw_counts(df: pd.DataFrame) -> dict:
    """{biến thể: dict đếm thô trên mọi tệp}."""
    out = {}
    for v, s in df.groupby("variant"):
        out[v] = dict(n=len(s), full=int(s.full.sum()), auto=int(s.auto.sum()), silent=int(s.silent_err.sum()), docs_auto=int(s.docs_ok_auto.sum()),
                      docs_total=int(s.docs_total.sum()), n_llm=int(s.n_llm.sum()), n_slices=int(s.n_slices.sum()))
    return out


def options_on(name: str) -> int:
    return int("+id" in name) + int("+tb" in name)


def apply_rule(cnt: dict) -> tuple:
    """Quy tắc dev (ghi trong dev_selection_v2.json). -> (chosen, bảng hợp lệ)."""
    b = cnt["S10"]
    table = []
    for v in CANDIDATES:
        x = cnt[v]
        ok = v == "S10" or (x["full"] >= b["full"] and x["silent"] <= b["silent"] and x["docs_auto"] >= b["docs_auto"])
        table.append(dict(variant=v, valid=bool(ok), **x))
    valid = [t for t in table if t["valid"]]
    best = sorted(valid, key=lambda t: (-t["docs_auto"], -t["full"], options_on(t["variant"])))[0]
    return best["variant"], table


def flips(df: pd.DataFrame, a: str, b: str) -> dict:
    """Tệp có (c) khác nhau giữa a và b, theo nhóm: (a đúng, b sai) / (a sai, b đúng)."""
    x = df[df.variant == a].set_index("doc_id")
    y = df[df.variant == b].set_index("doc_id")
    out = {}
    for g in L.FILE_GROUPS:
        ids = x.index[x.group == g]
        out[g] = (int(((x.loc[ids, "full"] == 1) & (y.loc[ids, "full"] == 0)).sum()), int(((x.loc[ids, "full"] == 0) & (y.loc[ids, "full"] == 1)).sum()))
    return out


def stage_dev(args, bench, splits, one_sheet):
    sel = json.loads(SELECTION.read_text(encoding="utf-8"))
    assert sel["status"] in ("rule_frozen_before_dev_run", "dev_done"), sel["status"]
    cases, gold = L.load_cases("dev")
    weights = L.population_weights(gold)
    scores = L.crossfit_pair_scores(gold, cases, E2E / "results" / "pair_scores_dev.json")
    n = {}
    for c in cases:
        n[c.group] = n.get(c.group, 0) + 1
    print("số tệp dev theo nhóm:", n)
    info = ensure_llm(cases, scores, VARIANTS, bench, splits, one_sheet, args.call_llm, args.timeout, "dev")
    clfs = make_clfs(bench, splits, mode="readonly")
    df = score_all(cases, scores, VARIANTS, clfs, one_sheet)
    df.to_csv(RES / "per_file_dev.csv", index=False, encoding="utf-8")       # chứa doc_id: nội bộ
    names = [v.name for v in VARIANTS]
    S = R.Summary(df, weights, names)
    cnt = raw_counts(df)
    chosen, table = apply_rule(cnt)
    print("CHỌN:", chosen)
    print(pd.DataFrame(table).to_string())
    # kiểm: S10 ở đây phải trùng thí nghiệm 01 (cùng biến thể, cùng cache)
    old = pd.read_csv(E2E / "results" / "per_file_dev.csv", dtype=str, keep_default_na=False)
    old = old[old.variant == "S10"].set_index("doc_id")
    new = df[df.variant == "S10"].set_index("doc_id")
    same = int(sum(old.loc[d, "pred_segs"] == new.loc[d, "pred_segs"] for d in new.index if d in old.index))
    print(f"S10 trùng 01 ở {same}/{len(new)} tệp (pred_segs)")

    lab = lambda v: f"{v} ({DESC[v]})"
    parts = [f"## Kết quả trên phạm vi dev (n = {sum(n.values())} tệp: " + ", ".join(f"{L.GROUP_VI[g]} {n[g]}" for g in S.groups) + ")", "",
             f"Kiểm tái lập: S10 ở đây trùng thí nghiệm 01 (pred_segs) ở {same}/{len(new)} tệp.", "",
             S.table_metric("full", "(c) Tệp đúng hoàn toàn = (a) tách đúng ∧ (b) mọi tài liệu đáp án có đúng loại", lab), "",
             S.table_metric("exact", "(a) Tách đúng hoàn toàn", lab), "",
             S.table_metric("types_ok", "(b) Mọi segment đáp án được TỰ NHẬN đúng loại", lab), "",
             "### (d) Định tuyến: tự xử lý hoàn toàn và sai lặng lẽ", "", S.table_routing(lab), "",
             "### Cấp tài liệu", "", S.table_docs(lab), "",
             "### (e) Hại / sửa so với S10 (mỗi ô: tệp S10 đúng mà biến thể làm hỏng / tệp S10 sai mà biến thể sửa)", "", S.harm("S10", lab), "",
             "### Số lời gọi LLM và số lát cắt mỗi tệp", "", S.table_cost(lab), ""]
    pr = ["### So sánh ghép cặp với S10 (hiệu của (c) có trọng số, CI 95% bootstrap ghép cặp theo tệp) và hiệu cấp tài liệu", "",
          "| cặp | hiệu (c) | CI | kết luận | hiệu tài liệu giao đúng và tự động | CI |", "|---|---|---|---|---|---|"]
    for a in ("S10+id", "S10+tb", "S10+id+tb", "S9", "S0"):
        d, lo, hi = S.paired(a, "S10")
        dd, dlo, dhi = S.doc_diff(a, "S10")
        pr.append(f"| {a} - S10 | {100 * d:+.1f} điểm | [{100 * lo:+.1f}; {100 * hi:+.1f}] | {'không tách được' if lo <= 0 <= hi else 'tách được'} | "
                  f"{100 * dd:+.1f} điểm | [{100 * dlo:+.1f}; {100 * dhi:+.1f}] |")
    parts += pr + [""]
    fl = ["### Tệp đổi kết quả (c) so với S10, theo nhóm: (S10 đúng -> X sai) / (S10 sai -> X đúng)", "",
          "| biến thể | " + " | ".join(L.GROUP_VI[g] for g in L.FILE_GROUPS) + " |", "|---|" + "---|" * len(L.FILE_GROUPS)]
    for a in ("S10+id", "S10+tb", "S10+id+tb"):
        f = flips(df, "S10", a)
        fl.append(f"| {a} | " + " | ".join(f"{f[g][0]} hỏng / {f[g][1]} sửa" for g in L.FILE_GROUPS) + " |")
    parts += fl + [""]
    parts += ["### Đếm thô và áp quy tắc chọn trên dev", "", "Quy tắc (nguyên văn từ `dev_selection_v2.json`): " + sel["rule_dev"], "",
              "| biến thể | hợp lệ | tệp đúng hoàn toàn | tự xử lý | sai lặng lẽ | tài liệu giao đúng và tự động | tài liệu đáp án | lời gọi LLM | lát cắt |", "|---|---|---|---|---|---|---|---|---|"]
    for t in table:
        parts.append(f"| {t['variant']} | {'có' if t['valid'] else 'không'} | {t['full']}/{t['n']} | {t['auto']}/{t['n']} | {t['silent']} | {t['docs_auto']}/{t['docs_total']} | {t['docs_total']} | {t['n_llm']} | {t['n_slices']} |")
    parts += ["", f"**Chọn trên dev: {chosen}.**", ""]
    (RES / "dev_report.md").write_text("\n".join(parts), encoding="utf-8")
    sel.update(status="dev_done", dev_done_at=datetime.now(timezone.utc).isoformat(timespec="seconds"), chosen=chosen, counts=cnt, rule_table=table,
               specs={v.name: dict(base=v.base, tau=v.tau, merge=v.merge, band=list(v.band) if v.band else None, keep=v.keep, id_rule=v.id_rule, tiebreak=v.tiebreak)
                      for v in VARIANTS}, n_dev_files=n, new_llm_texts_dev=info["n_new_llm_texts"], llm_errors_dev=info["llm_errors"], s10_same_as_01=[same, len(new)])
    SELECTION.write_text(json.dumps(sel, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print("đã ghi", RES / "dev_report.md")


def stage_test(args, bench, splits, one_sheet):
    dry = args.dry_run
    if not args.final_test and not dry:
        raise SystemExit("--stage test cần --final-test")
    sel = json.loads(SELECTION.read_text(encoding="utf-8"))
    if sel["status"] != "dev_done":
        raise SystemExit("chạy --stage dev trước (dev_selection_v2.json chưa có kết quả dev).")
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if "run2" in reg and not dry:
        raise SystemExit("lần chạy TEST thứ hai đã được ghi trong sổ đăng ký; từ chối chạy lại.")
    if sel["labels_sha1_10"] != bench.labels_sha:
        raise SystemExit("nhãn đã đổi kể từ khi chọn trên dev; không chấm TEST.")
    chosen = sel["chosen"]
    byname = {v.name: v for v in VARIANTS}
    run_vars = [byname["S10"]] + ([byname[chosen]] if chosen != "S10" else [])
    dev_cases, gold = L.load_cases("dev")
    weights = L.population_weights(gold)
    if dry:
        test_cases = dev_cases[::6]
        scores = json.loads((E2E / "results" / "pair_scores_dev.json").read_text(encoding="utf-8"))
    else:
        test_cases, _ = L.load_cases("test")
        assert all(c.split == "TEST" for c in test_cases) and not ({c.doc_id for c in test_cases} & {c.doc_id for c in dev_cases})
        scores = L.final_pair_scores(gold, dev_cases, test_cases)
    info = ensure_llm(test_cases, scores, run_vars, bench, splits, one_sheet, args.call_llm, args.timeout, "test", strict=not dry)
    clfs = make_clfs(bench, splits, mode="readonly")
    df = score_all(test_cases, scores, run_vars, clfs, one_sheet)
    pre = "dryrun_" if dry else ""
    df.to_csv(RES / f"{pre}per_file_test.csv", index=False, encoding="utf-8")
    n = df[df.variant == "S10"].group.value_counts().to_dict()
    S = R.Summary(df, weights, [v.name for v in run_vars])
    cnt = raw_counts(df)
    out = [f"## Kết quả TEST (lần thứ HAI của thí nghiệm toàn trình; MỘT lần cho cấu hình mới; cấu hình đóng băng = **{chosen}**)", "",
           f"Lý do chạy lần hai: {sel['test_run_reason']}. n = {len(test_cases)} tệp TEST: " + ", ".join(f"{L.GROUP_VI[g]} {n[g]}" for g in L.FILE_GROUPS if g in n) + ".", "",
           "| biến thể | tệp đúng hoàn toàn (c) | Clopper-Pearson 95% | tự xử lý | sai lặng lẽ / tự xử lý (CP 95%) | tài liệu giao đúng và tự động | lời gọi LLM | lát cắt |", "|---|---|---|---|---|---|---|---|"]
    for v in S.names:
        c = cnt[v]
        lo, hi = L.cp_interval(c["full"], c["n"])
        cl, ch = L.cp_interval(c["silent"], c["auto"])
        out.append(f"| {v} | {c['full']}/{c['n']} = {R.pc(c['full'] / c['n'])} | [{R.pc(lo)}; {R.pc(hi)}] | {c['auto']}/{c['n']} | {c['silent']}/{c['auto']} [{R.pc(cl)}; {R.pc(ch)}] | "
                   f"{c['docs_auto']}/{c['docs_total']} | {c['n_llm']} | {c['n_slices']} |")
    out += ["", S.table_metric("full", "(c) theo nhóm", lambda v: v), "", S.table_routing(), "", S.table_docs(), ""]
    if len(S.names) > 1:
        out += [S.harm("S10"), ""]
        d, lo, hi = S.paired(chosen, "S10")
        out += [f"Hiệu (c) {chosen} - S10 trên TEST: {100 * d:+.1f} điểm, CI ghép cặp [{100 * lo:+.1f}; {100 * hi:+.1f}] ({'không tách được' if lo <= 0 <= hi else 'tách được'}).", ""]
        b, x = cnt["S10"], cnt[chosen]
        ok = x["full"] >= b["full"] and x["silent"] <= b["silent"]
        out += [f"Kiểm quy tắc đổi mặc định (ii): tệp đúng {x['full']} so với {b['full']} (>=), sai lặng lẽ {x['silent']} so với {b['silent']} (<=) -> **{'đạt' if ok else 'KHÔNG đạt'}**.", ""]
    (RES / f"{pre}test_report.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))
    if dry:
        return
    assert all(c.split == "TEST" for c in test_cases)
    reg["run2"] = dict(created=datetime.now(timezone.utc).isoformat(timespec="seconds"), chosen=chosen, n=len(test_cases), n_by_group=n, labels_sha1_10=bench.labels_sha,
                       dev_selection_v2_sha1_10=R.sha10(SELECTION), new_llm_texts=info["n_new_llm_texts"], counts=cnt,
                       reason=sel["test_run_reason"],
                       note="Lần chạy TEST thứ hai của thí nghiệm toàn trình (experiments/03_end_to_end_v2): chấm MỘT lần cấu hình đóng băng trên dev và S10 cũ để đặt cạnh nhau; không dùng để chỉnh gì.")
    REGISTRY.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
    print("đã cập nhật", REGISTRY)


def assemble():
    parts = []
    for name in ("header.md", "results/dev_report.md", "results/test_report.md", "notes.md"):
        p = HERE / name
        parts.append(p.read_text(encoding="utf-8") if p.exists() else f"({name} chưa có)")
    (HERE / "RESULTS.md").write_text("\n\n".join(parts), encoding="utf-8")
    print("đã ghi", HERE / "RESULTS.md")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", choices=["dev", "test", "assemble"], default="dev")
    ap.add_argument("--call-llm", action="store_true")
    ap.add_argument("--final-test", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="--stage test chạy thử trên một phần DEV (không mở TEST, không ghi sổ đăng ký)")
    ap.add_argument("--timeout", type=float, default=120.0)
    args = ap.parse_args()
    RES.mkdir(exist_ok=True)
    if args.stage == "assemble":
        return assemble()
    from harness import load_benchmark, load_or_make_splits
    bench = load_benchmark(L.REPO / "data" / "labels_v2.csv")
    splits = load_or_make_splits(bench)
    one_sheet = L.load_one_sheet_types()
    return (stage_dev if args.stage == "dev" else stage_test)(args, bench, splits, one_sheet)


if __name__ == "__main__":
    main()
