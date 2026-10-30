r"""Thí nghiệm 04 - (c) bộ phân loại cặp trang (trang i-1 hiệu dụng, trang i) -> "trang i mở tài liệu mới".

Huấn luyện bằng cặp thật của tài liệu dev ngoài fold + cặp "đường nối" của composite TỔNG HỢP (gold/make_synthetic.py, chỉ từ tài liệu đơn DEV
của các nhóm huấn luyện). Cross-fitting có nhóm 5 fold (cvlib.py). Chạy từ gốc repo:
    .venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/04_pair_classifier/run.py                      # ~6 phút
    .venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/04_pair_classifier/run.py --scope all --final-test
    .venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/04_pair_classifier/run.py --no-family-merge     # độ nhạy: KHÔNG gộp 5 bộ BSR vào một nhóm
    .venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/04_pair_classifier/save_model.py                # huấn luyện lại trên toàn bộ dev, ghi models/
"""
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import cvlib  # noqa: E402
import expcommon as ec  # noqa: E402
import splitlib as sl  # noqa: E402
from src.splitting.learned import fit_pair_model  # noqa: E402

THRESHOLDS = (0.3, 0.5, 0.7, 0.9)
BASE = ("c1 hồi quy logistic", "c2 gradient boosting")


def make_fit(kind):
    def fit(td: cvlib.TrainData):
        m = fit_pair_model(td.page_text, td.page_type, td.page_group, td.pairs, kind=kind, seed=0)
        return {("" if t == 0.5 else f" @{t}"): (lambda texts, t=t: m.predict_flags(texts, t)) for t in THRESHOLDS}
    return fit


def main():
    ap = ec.common_args(__doc__)
    ap.add_argument("--no-family-merge", action="store_true", help="độ nhạy: mỗi bộ chứng từ BSR theo template_group riêng (có thể nằm train và test cùng lúc)")
    args = ap.parse_args()
    gold, ids, docs = ec.setup(args)
    dev_ids = sl.scope_doc_ids(gold, "dev")
    test_ids = [d for d in ids if d not in set(dev_ids)]
    METHODS = {BASE[0]: make_fit("lr"), BASE[1]: make_fit("gb")}
    t0 = time.perf_counter()
    preds, preds_syn, syn_gold, syn_docs, final_test, fold = cvlib.run_cv(METHODS, gold, docs, dev_ids, test_ids, merge_family=not args.no_family_merge)
    dt = time.perf_counter() - t0
    names = sorted(preds)
    for name in names:
        preds[name].update(final_test.get(name, {}))
    base_df, _ = ec.baseline_eval(ids, docs, gold)
    v2_df, _ = sl.evaluate_method(ec.rule_v2_starts, ids, docs, gold)
    dfs = {n: sl.evaluate_method(None, ids, docs, gold, prediction_cache=preds[n])[0] for n in names}
    per = {"rule cũ (01)": base_df, "rule v2 (02)": v2_df, **{n: dfs[n] for n in BASE}}
    sens = {n: dfs[n] for n in names if n.startswith(BASE[1])}
    syn_per = {}
    for label, fn in (("rule cũ", ec.baseline_starts), ("rule v2", ec.rule_v2_starts)):
        syn_per[label] = cvlib.eval_synthetic({s: fn(s, d) for s, d in syn_docs.items()}, syn_gold, syn_docs)
    for n in BASE:
        syn_per[n] = cvlib.eval_synthetic(preds_syn[n], syn_gold, syn_docs)
    best = BASE[1]
    err = ec.error_table(dfs[best], preds[best], gold, ec.reason_v2, docs, 5)
    print(sl.summary_table_md(per, args.boot))
    print(ec.syn_summary_md(syn_per, args.boot))
    print(err)
    if args.no_write:
        return
    scope = args.scope
    cmd = r".venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/04_pair_classifier/run.py" + (
        " --scope all --final-test" if scope == "all" else "") + (" --no-family-merge" if args.no_family_merge else "")
    header = ec.reproduce_header(HERE, cmd, args, {
        "mã đo": f"`src/splitting/learned.py::fit_pair_model` (sha1[:10] `{ec.sha10(sl.REPO / 'src' / 'splitting' / 'learned.py')}`), cross-fitting `teams/team2_splitting/cvlib.py` ({cvlib.N_FOLDS} fold theo nhóm biểu mẫu, seed {cvlib.FOLD_SEED}, " + ("KHÔNG gộp bộ BSR" if args.no_family_merge else "5 bộ BSR cùng chuỗi loại gộp một nhóm") + ")",
        "huấn luyện": "mỗi fold: cặp thật của tài liệu dev ngoài fold + cặp đường nối của 400 composite tổng hợp (seed 100+fold) từ tài liệu đơn DEV ngoài fold; xác suất loại trang cho tầng cặp là OOF theo nhóm. Không dùng TEST. Số liệu trên composite thật là CROSS-VALIDATED (dev-like), KHÔNG phải tập TEST khóa; ngưỡng cố định 0,5 (không chỉnh trên số liệu này)",
        "thời gian chạy": f"{dt:.0f} s toàn bộ CV (máy dùng chung, chỉ tham khảo)"})
    if args.no_family_merge:
        out = [f"# 04 - Độ nhạy: không gộp bộ BSR thành một nhóm - phạm vi `{scope}`", "", header, "",
               "Ở chế độ này, một bộ chứng từ BSR bị giữ lại có thể có bộ BSR khác (cùng nhà cung cấp, cùng bố cục) trong tập huấn luyện: đo mức 'nhớ bố cục' (bẫy 7 của README).", "",
               sl.summary_table_md(per, args.boot)]
        (HERE / "RESULTS_family_sensitivity.md").write_text("\n".join(out), encoding="utf-8")
        print("đã ghi", HERE / "RESULTS_family_sensitivity.md")
        return
    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-04"
    for name in BASE:
        ec.save_per_file(HERE, name.split()[0], dfs[name], preds[name], scope)
        for r in ec.results_rows("04_" + name.split()[0], dfs[name], scope, run_id, "cross-fitted theo nhóm; " + name):
            ec.append_results_table(r)
    out = [f"# 04 - Bộ phân loại cặp trang (c) - phạm vi `{scope}`", "", header,
           "", "## Kết quả trên composite THẬT, theo nhóm", "",
           "Mỗi ô: điểm [CI 95% bootstrap theo tệp]. `boundary_confidence` của phương pháp này là điểm thô của bộ phân loại, chưa hiệu chỉnh.",
           sl.summary_table_md(per, args.boot), "",
           "## So sánh ghép cặp trên composite thật", ""]
    for name in BASE:
        out += [f"### {name} - rule cũ", "", sl.paired_table_md(dfs[name], base_df, name, "rule cũ", args.boot), ""]
    for name in BASE:
        out += [f"### {name} - rule v2", "", sl.paired_table_md(dfs[name], v2_df, name, "rule v2", args.boot), ""]
    out += [f"### {BASE[1]} - {BASE[0]}", "", sl.paired_table_md(dfs[BASE[1]], dfs[BASE[0]], "c2", "c1", args.boot), "",
            "## Độ nhạy theo ngưỡng (c2; mô tả, ngưỡng 0,5 là cấu hình chính, không chọn lại theo bảng này)", "", sl.summary_table_md(sens, args.boot), "",
            "## Trên composite TỔNG HỢP (giữ lại theo fold)", "",
            f"{len(syn_docs)} composite; seed đánh giá `1000+fold`. Ranh giới tổng hợp thường dễ hơn thật.", ec.syn_summary_md(syn_per, args.boot), "",
            "## Phân tích lỗi (c2, 5 kiểu đông nhất)", "", err, ""]
    notes = HERE / "notes.md"
    if notes.exists() and scope == "dev":
        out.append(notes.read_text(encoding="utf-8"))
    ec.results_path(HERE, scope).write_text("\n".join(out), encoding="utf-8")
    print("đã ghi", ec.results_path(HERE, scope))


if __name__ == "__main__":
    main()
