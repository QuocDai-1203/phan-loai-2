r"""Thí nghiệm 01 - đo bộ luật tách trang HIỆN CÓ (src/splitting/boundary_detector.py::split_document), không sửa luật.

Chạy từ gốc repo:
    .venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/01_rule_baseline/run.py            # phạm vi dev
    .venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/01_rule_baseline/run.py --scope all --final-test   # thêm TEST (một lần)
"""
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import expcommon as ec  # noqa: E402
import splitlib as sl  # noqa: E402
from src.common.text_norm import NormalizedText  # noqa: E402
from src.splitting.boundary_detector import TITLE_KEYWORDS, split_document  # noqa: E402


def baseline_starts(doc_id, doc):
    return {s.start_page for s in split_document(doc).slices if s.start_page >= 2}


def reason(doc, page_number):
    """Dấu hiệu mà luật cũ dùng trên trang đó (để gom lỗi). Không chứa định danh cá nhân."""
    page = next(p for p in doc.pages if p.page_number == page_number)
    if NormalizedText(page.full_text).contains("CỘNG HÒA XÃ HỘI"):
        return "quốc hiệu (bất kỳ đâu trong trang)"
    lines = [x.strip() for x in page.full_text.split("\n") if x.strip()]
    head = NormalizedText(" ".join(lines[:6]))
    for kw in TITLE_KEYWORDS:
        if head.contains(kw):
            return f"tiêu đề '{kw}' trong 6 dòng đầu"
    n = len(page.full_text.strip())
    return "không có dấu hiệu luật (trang trống)" if n < 20 else "không có dấu hiệu luật"


def main():
    args = ec.common_args(__doc__).parse_args()
    gold, ids, docs = ec.setup(args)
    t0 = time.perf_counter()
    df, preds = sl.evaluate_method(baseline_starts, ids, docs, gold)
    dt = time.perf_counter() - t0
    scope = args.scope
    print(sl.summary_table_md({"rule hiện có": df}, args.boot))
    if args.no_write:
        return
    ec.save_per_file(HERE, "rule_baseline", df, preds, scope)
    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()) + "-01"
    for r in ec.results_rows("01_rule_baseline", df, scope, run_id, "luật hiện có, không sửa"):
        ec.append_results_table(r)

    cmd = r".venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/01_rule_baseline/run.py" + (" --scope all --final-test" if scope == "all" else "")
    meta = gold.drop_duplicates("doc_id").set_index("doc_id")
    trunc = [(d, meta.loc[d, "eval_group"], docs[d].total_pages, len(docs[d].pages)) for d in ids if len(docs[d].pages) < docs[d].total_pages]
    trunc_md = ["| doc_id | nhóm | số trang thật | số trang có văn bản (được chấm) | ranh giới thật bị bỏ ngoài phép chấm |", "|---|---|---|---|---|"]
    for d, grp, tot, av in trunc:
        g = gold[(gold.doc_id == d) & (gold.page > av) & (gold.page >= 2)]
        trunc_md.append(f"| {d} | {grp} | {tot} | {av} | {int(g.is_start.sum())} / {len(g)} vị trí |")
    pos_ids = [d for d in ids if meta.loc[d, "eval_group"] != "negative"]
    out = [f"# 01 - Đo bộ luật tách trang hiện có (baseline) - phạm vi `{scope}`", "",
           ec.reproduce_header(HERE, cmd, args, {"mã đo": "`src/splitting/boundary_detector.py::split_document` (không sửa), cổng luật `CascadedClassifier(kev_endpoint=None)` để chấm loại",
                                                 "thời gian chạy": f"{dt:.1f} s cho {len(df)} tệp (máy đang bận bởi tiến trình khác, chỉ mang tính tham khảo)"}),
           "", "## Kết quả theo nhóm", "",
           "Mỗi ô: điểm [CI 95% bootstrap theo tệp]. Kèm tử/mẫu thô. `loại segment` = tỉ lệ segment đáp án mà cổng luật gán đúng loại trên lát cắt dự đoán khớp nhiều trang nhất; `oracle` = cùng phép đo khi cắt đúng đáp án (trần của cổng luật).",
           sl.summary_table_md({"rule hiện có": df}, args.boot), "",
           "## Phân tích lỗi (5 kiểu lỗi đông nhất)", "",
           ec.error_table(df, preds, gold, reason, docs, 5), "",
           "### Chỉ trong ba nhóm composite (nơi có ranh giới thật)", "",
           ec.error_table(df[df.group != "negative"], {k: v for k, v in preds.items() if k in set(pos_ids)}, gold, reason, docs, 5), "",
           "## Tệp bị cắt cụt (văn bản OCR chỉ tới trang 30)", "",
           "`data/ocr_v2.jsonl` chỉ có văn bản tới trang 30. Với các tệp dưới đây phép chấm chỉ dùng các trang có văn bản (cả dự đoán lẫn đáp án bị cắt ở đó); `exact-segment` của tệp là 'đúng trên phần có văn bản'. Không sửa `ocr_v2.jsonl`.", "",
           "\n".join(trunc_md), ""]
    notes = HERE / "notes.md"
    if notes.exists() and scope == "dev":
        out.append(notes.read_text(encoding="utf-8"))
    ec.results_path(HERE, scope).write_text("\n".join(out), encoding="utf-8")
    print("đã ghi", ec.results_path(HERE, scope))


if __name__ == "__main__":
    main()
