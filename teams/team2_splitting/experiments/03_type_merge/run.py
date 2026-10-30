r"""Thí nghiệm 03 - (b) phân loại LOẠI từng trang rồi gộp các trang liên tiếp cùng loại (+ dấu hiệu "bản khác" cho chuỗi cùng loại).

Cross-fitting có nhóm 5 fold trên phạm vi dev (xem teams/team2_splitting/cvlib.py). Chạy từ gốc repo:
    .venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/03_type_merge/run.py
    .venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/03_type_merge/run.py --scope all --final-test
"""
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import cvlib  # noqa: E402
import expcommon as ec  # noqa: E402
import splitlib as sl  # noqa: E402
from src.splitting.learned import PageTypeModel, TypeMergeConfig, TypeMergeSplitter  # noqa: E402


def make_fit(cfg):
    def fit(td: cvlib.TrainData):
        keys = sorted(td.page_text)
        tm = PageTypeModel().fit([td.page_text[k] for k in keys], [td.page_type[k] for k in keys])
        return TypeMergeSplitter(tm, cfg).predict_flags
    return fit


METHODS = {
    "b0 chỉ đổi loại": make_fit(TypeMergeConfig(use_copy_signal=False)),
    "b1 đổi loại + bản khác": make_fit(TypeMergeConfig(use_copy_signal=True)),
}


def main():
    args = ec.common_args(__doc__).parse_args()
    gold, ids, docs = ec.setup(args)
    dev_ids = sl.scope_doc_ids(gold, "dev")
    test_ids = [d for d in ids if d not in set(dev_ids)]
    t0 = time.perf_counter()
    preds, preds_syn, syn_gold, syn_docs, final_test, fold = cvlib.run_cv(METHODS, gold, docs, dev_ids, test_ids)
    dt = time.perf_counter() - t0
    for name in METHODS:
        preds[name].update(final_test[name])
    per = {}
    base_df, base_preds = ec.baseline_eval(ids, docs, gold)
    v2_df, _ = sl.evaluate_method(ec.rule_v2_starts, ids, docs, gold)
    per["rule cũ (01)"], per["rule v2 (02)"] = base_df, v2_df
    dfs = {}
    for name in METHODS:
        dfs[name], _ = sl.evaluate_method(None, ids, docs, gold, prediction_cache=preds[name])
        per[name] = dfs[name]
    print(sl.summary_table_md(per, args.boot))
    # trên tổng hợp
    syn_per = {}
    for label, fn in (("rule cũ", ec.baseline_starts), ("rule v2", ec.rule_v2_starts)):
        syn_per[label] = cvlib.eval_synthetic({s: fn(s, d) for s, d in syn_docs.items()}, syn_gold, syn_docs)
    for name in METHODS:
        syn_per[name] = cvlib.eval_synthetic(preds_syn[name], syn_gold, syn_docs)
    print(ec.syn_summary_md(syn_per, args.boot))
    if args.no_write:
        return
    scope = args.scope
    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-03"
    for name in METHODS:
        ec.save_per_file(HERE, name.split()[0], dfs[name], preds[name], scope)
        for r in ec.results_rows("03_" + name.split()[0], dfs[name], scope, run_id, "cross-fitted theo nhóm; " + name):
            ec.append_results_table(r)
    cmd = r".venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/03_type_merge/run.py" + (" --scope all --final-test" if scope == "all" else "")
    out = [f"# 03 - Phân loại loại từng trang rồi gộp (b) - phạm vi `{scope}`", "",
           ec.reproduce_header(HERE, cmd, args, {
               "mã đo": f"`src/splitting/learned.py::TypeMergeSplitter` (sha1[:10] `{ec.sha10(sl.REPO / 'src' / 'splitting' / 'learned.py')}`), cross-fitting `teams/team2_splitting/cvlib.py` ({cvlib.N_FOLDS} fold theo nhóm biểu mẫu, seed {cvlib.FOLD_SEED}, bộ BSR gộp một nhóm)",
               "huấn luyện": f"mỗi fold: trang của tài liệu dev ngoài fold (nhãn loại = loại segment trong `boundary_gold_v0.csv`); không dùng TEST. Số liệu trên composite thật là CROSS-VALIDATED (dev-like), KHÔNG phải tập TEST khóa",
               "thời gian chạy": f"{dt:.0f} s toàn bộ CV (máy dùng chung, chỉ tham khảo)"}),
           "", "## Kết quả trên composite THẬT, theo nhóm", "",
           "Mỗi ô: điểm [CI 95% bootstrap theo tệp]. b0 = tách khi loại dự đoán đổi (cả hai trang có xác suất loại >= 0,5). b1 = b0 + với chuỗi cùng loại, tách khi trang trông như trang đầu (luật v2) và số hiệu/ngày khác trang trước.",
           sl.summary_table_md(per, args.boot), "",
           "## So sánh ghép cặp với baseline (rule cũ) trên composite thật", ""]
    for name in METHODS:
        out += [f"### {name} - rule cũ", "", sl.paired_table_md(dfs[name], base_df, name, "rule cũ", args.boot), ""]
    out += ["### b1 - rule v2", "", sl.paired_table_md(dfs["b1 đổi loại + bản khác"], v2_df, "b1", "rule v2", args.boot), "",
            "## Trên composite TỔNG HỢP (giữ lại theo fold, sinh từ tài liệu đơn DEV của đúng các nhóm giữ lại)", "",
            f"Seed sinh: huấn luyện `100+fold`, đánh giá `1000+fold` (`gold/make_synthetic.py`). {len(syn_docs)} composite. Ranh giới tổng hợp thường dễ hơn thật (các trang đến từ lần quét độc lập).",
            ec.syn_summary_md(syn_per, args.boot), "",
            "## Phân tích lỗi (b1, 5 kiểu đông nhất)", "", ec.error_table(dfs["b1 đổi loại + bản khác"], preds["b1 đổi loại + bản khác"], gold, ec.reason_v2, docs, 5), ""]
    notes = HERE / "notes.md"
    if notes.exists() and scope == "dev":
        out.append(notes.read_text(encoding="utf-8"))
    ec.results_path(HERE, scope).write_text("\n".join(out), encoding="utf-8")
    print("đã ghi", ec.results_path(HERE, scope))


if __name__ == "__main__":
    main()
