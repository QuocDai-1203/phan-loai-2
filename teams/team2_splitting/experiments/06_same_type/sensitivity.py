r"""Thí nghiệm 06 - độ nhạy của quy tắc "bản khác" theo ngưỡng mẫu giống (jaccard token đầu trang). Ngưỡng 0,7 của `TEMPLATE_JACCARD_MIN` được chọn SAU khi xem bảng này (giữa vùng bằng phẳng 0,5-0,8; dưới 0,5 có thêm tách nhầm ở mẫu âm), nên là chọn trên dev.
Chạy: .venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/06_same_type/sensitivity.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lib06 as L  # noqa: E402
import splitlib as sl  # noqa: E402
from src.splitting.learned_id import id_rule_pages  # noqa: E402


def main():
    gold = sl.load_gold()
    ids = sl.scope_doc_ids(gold, "dev")
    docs = sl.load_documents(ids)
    meta = gold.drop_duplicates("doc_id").set_index("doc_id")
    segs, sc = L.load_s10_labels(), L.load_scores()
    use = [d for d in ids if meta.loc[d, "eval_group"] in sl.GROUPS]
    print("| jaccard tối thiểu | cùng loại ngoài BB: bắt / 7 (FP) | mẫu âm: tách nhầm / 501 | composite khác loại: bắt / 20 (FP) | BB_LAY_MAU: bắt / 46 (FP) |")
    print("|---|---|---|---|---|")
    for jm in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
        pred = {}
        for d in use:
            pages = [p.page_number for p in docs[d].pages]
            fl = id_rule_pages([p.full_text for p in docs[d].pages], jm)
            pred[d] = L.simulate(sc[d], pages, segs[d], 0.7, 0.99, True, fl, True, True)
        df = L.evaluate(pred, ids, docs, gold)
        cell = lambda g: df[df.group == g]  # noqa: E731
        so, ng, mx, bb = cell("same_other"), cell("negative"), cell("mixed"), cell("same_bb")
        print(f"| {jm} | {int(so.tp.sum())}/{int(so.n_true.sum())} ({int(so.fp.sum())}) | {int(ng.fp.sum())}/{int(ng.n_pos.sum())} | "
              f"{int(mx.tp.sum())}/{int(mx.n_true.sum())} ({int(mx.fp.sum())}) | {int(bb.tp.sum())}/{int(bb.n_true.sum())} ({int(bb.fp.sum())}) |")


if __name__ == "__main__":
    main()
