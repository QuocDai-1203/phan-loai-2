r"""Thí nghiệm 02 - bộ luật tách trang đã sửa (src/splitting/rules_v2.py). Không huấn luyện gì; tham số chọn tay trên phạm vi dev.

Chạy từ gốc repo:
    .venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/02_rule_v2/run.py
    .venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/02_rule_v2/run.py --scope all --final-test
"""
import dataclasses
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import expcommon as ec  # noqa: E402
import splitlib as sl  # noqa: E402
from src.splitting.rules_v2 import DEFAULT_CONFIG, RuleConfig, rule_starts  # noqa: E402


def make_method(cfg):
    def f(doc_id, doc):
        fl = rule_starts([p.full_text for p in doc.pages], cfg)
        return {doc.pages[i].page_number for i, x in enumerate(fl) if x and i > 0}
    return f


def main():
    args = ec.common_args(__doc__).parse_args()
    gold, ids, docs = ec.setup(args)
    base_df, _ = ec.baseline_eval(ids, docs, gold)
    t0 = time.perf_counter()
    df, preds = sl.evaluate_method(make_method(DEFAULT_CONFIG), ids, docs, gold)
    dt = time.perf_counter() - t0

    # ablation: tắt từng thành phần / chỉ bật một thành phần (mô tả, không có CI)
    off = dict(use_min_chars=False, use_signature_veto=False, use_page_no_veto=False, use_repeat_header_veto=False,
               motto_top_only=False, title_at_line_start=False)
    comps = {"min_chars (>=50 ký tự)": "use_min_chars", "trang chỉ chữ ký/trống": "use_signature_veto", "đánh số trang n/m, n>=2": "use_page_no_veto",
             "tiêu đề lặp ở trang ngắn": "use_repeat_header_veto", "quốc hiệu chỉ ở đầu trang": "motto_top_only", "tiêu đề phải đầu dòng": "title_at_line_start"}
    abl_rows = []

    def counts(cfg):
        d, _ = sl.evaluate_method(make_method(cfg), ids, docs, gold)
        r = {}
        for g in sl.GROUPS:
            s = d[d.group == g]
            r[g] = f"{int(s.tp.sum())}/{int(s.fp.sum())}/{int(s.fn.sum())}"
        return r

    abl = ["| cấu hình | mixed (TP/FP/FN) | same_other | same_bb | negative (FP) |", "|---|---|---|---|---|"]
    def line(name, cfg):
        r = counts(cfg)
        abl.append(f"| {name} | {r['mixed']} | {r['same_other']} | {r['same_bb']} | {r['negative'].split('/')[1]} |")
    line("đủ mọi thành phần (mặc định)", DEFAULT_CONFIG)
    for label, field in comps.items():
        line(f"bỏ: {label}", dataclasses.replace(DEFAULT_CONFIG, **{field: False}))
    line("không thành phần nào (chỉ khung)", RuleConfig(**off))
    for label, field in comps.items():
        line(f"chỉ bật: {label}", RuleConfig(**{**off, field: True}))
    for hl in (4, 6, 8, 10):
        line(f"nhạy cảm: head_lines={hl}", dataclasses.replace(DEFAULT_CONFIG, head_lines=hl))
    for mc in (50, 150, 300):
        line(f"nhạy cảm: min_chars={mc}", dataclasses.replace(DEFAULT_CONFIG, min_chars=mc))

    print(sl.summary_table_md({"rule hiện có": base_df, "rule v2": df}, args.boot))
    print("\n".join(abl))
    if args.no_write:
        return
    scope = args.scope
    ec.save_per_file(HERE, "rule_v2", df, preds, scope)
    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-02"
    for r in ec.results_rows("02_rule_v2", df, scope, run_id, "luật v2 mặc định"):
        ec.append_results_table(r)
    cmd = r".venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/02_rule_v2/run.py" + (" --scope all --final-test" if scope == "all" else "")
    pos_only = df[df.group != "negative"]
    out = [f"# 02 - Bộ luật đã sửa (rule v2) - phạm vi `{scope}`", "",
           ec.reproduce_header(HERE, cmd, args, {"mã đo": "`src/splitting/rules_v2.py::rule_starts` với `DEFAULT_CONFIG` (sha1[:10] của tệp: `%s`)" % ec.sha10(Path(sl.REPO) / 'src' / 'splitting' / 'rules_v2.py'),
                                                 "thời gian chạy": f"{dt:.1f} s cho {len(df)} tệp (máy đang bận, chỉ tham khảo)"}),
           "", "## Kết quả theo nhóm (so với baseline)", "",
           "Mỗi ô: điểm [CI 95% bootstrap theo tệp]. Tham số mặc định (`head_lines=6`, `min_chars=50`) được chọn tay SAU KHI xem lỗi của baseline trên phạm vi dev, nên số trên dev hơi lạc quan.",
           sl.summary_table_md({"rule hiện có (01)": base_df, "rule v2": df}, args.boot), "",
           "## So sánh ghép cặp với baseline", "", sl.paired_table_md(df, base_df, "rule v2", "rule cũ", args.boot), "",
           "## Ablation (TP/FP/FN theo nhóm; không có CI, chỉ để thấy thành phần nào làm việc)", "", "\n".join(abl), "",
           "## Phân tích lỗi còn lại của rule v2 (5 kiểu đông nhất)", "", ec.error_table(df, preds, gold, ec.reason_v2, docs, 5), "",
           "### Chỉ trong các nhóm composite (sót / tách nhầm)", "", ec.error_table(df[df.group != 'negative'], {k: v for k, v in preds.items() if k in set(pos_only.doc_id)}, gold, ec.reason_v2, docs, 5), ""]
    notes = HERE / "notes.md"
    if notes.exists() and scope == "dev":
        out.append(notes.read_text(encoding="utf-8"))
    ec.results_path(HERE, scope).write_text("\n".join(out), encoding="utf-8")
    print("đã ghi", ec.results_path(HERE, scope))


if __name__ == "__main__":
    main()
