r"""Thí nghiệm 06 (T5) - nhiều bản cùng loại trong một tệp: đặc trưng "bản khác" (số hiệu / ngày / mẫu giống) trên c2 và trên `model+merge`.

Chạy từ gốc repo (CPU; cross-fit c2+id ~6-8 phút lần đầu, sau đó dùng cache results/pair_scores_id_dev.json):
    .venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/06_same_type/run.py
Chỉ phạm vi dev (DEV + EXCLUDED_COMPOSITE); không mở TEST.
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lib06 as L  # noqa: E402
import cvlib  # noqa: E402
import expcommon as ec  # noqa: E402
import splitlib as sl  # noqa: E402
from src.splitting.learned_id import fit_pair_model_id, id_rule_pages  # noqa: E402

SUMMARY = """## Tóm tắt (đọc trước)

- **Câu hỏi:** nhóm "nhiều bản cùng loại trong một tệp" (T5) bị `model+merge` bỏ sót gần hết (0/7 ranh giới ngoài `BB_LAY_MAU` trên dev: bộ gộp cùng loại xóa ranh giới, và mô hình cặp trang cho điểm thấp khi hai tờ cùng mẫu). Có đặc trưng "bản khác" nào bắt được chúng mà không làm tăng tách nhầm trên 155 tệp nhiều trang bình thường không?
- **Kết quả:** một quy tắc không tham số, "đầu trang giống nhau (jaccard >= 0,7) VÀ số hiệu 'Số ...' ở đầu cả hai trang khác nhau", thêm ranh giới điểm 1,0 (nên không bị gộp lại theo loại), nâng cùng loại ngoài BB từ **0/7 lên 4/7** ranh giới (recall +0,571, CI bootstrap ghép cặp theo tệp [0,167; 0,889], n = 6 tệp) và **không đổi gì** ở ba nhóm còn lại: mẫu âm vẫn 9 tách nhầm trên 501 vị trí (6/155 tệp), khác loại 19/20, `BB_LAY_MAU` 40/46. Đưa vào `src/splitting/` làm tùy chọn `model+merge+id` (không phải mặc định).
- **Không thành công:** đặc trưng định danh trong bộ phân loại cặp trang (c2+id, cross-fit): 1/7, không tách được khỏi nền; VLM `qwen3.5:4b` nhìn hai ảnh: 3/7 nhưng thêm 7 tách nhầm ở mẫu âm (tách được: kém hơn), không dùng.
- **Hạn chế chính:** quy tắc được nghĩ ra sau khi đọc các tệp cùng loại của dev (4 ranh giới bắt được nằm ở 3 tệp), và TEST không có tệp cùng loại ngoài `BB_LAY_MAU` nào để kiểm giữ ngoài; **TEST không được chạy**. Phần "không hại mẫu âm" mạnh hơn (0/448 cặp mẫu âm bị kích hoạt). 3/7 ranh giới còn lại (OCR hỏng, mẫu không có "Số", hai giấy khác mẫu) chưa phương pháp nào bắt được.
- **Cách đo:** mô phỏng ngoại tuyến `model+merge` (điểm cặp trang c2 cross-fit 5 fold theo nhóm biểu mẫu của thí nghiệm 01 end-to-end; nhãn lát cắt của S10), tái lập đúng 174/174 tệp nhiều trang của S10. "Nền" = chính `model+merge`.
"""
SCORES_ID = HERE / "results" / "pair_scores_id_dev.json"
BASE = "model+merge (S10, nền)"


def crossfit_id_scores(gold, ids, docs):
    """Cùng quy trình cvlib.run_cv / e2e crossfit_pair_scores (5 fold theo nhóm biểu mẫu, syn_seed 100+k, gb, seed 0) nhưng có đặc trưng định danh."""
    if SCORES_ID.exists():
        return json.loads(SCORES_ID.read_text(encoding="utf-8"))
    groups = cvlib.cv_group_map(gold, ids, True)
    fold = cvlib.fold_assignment(gold, ids, cvlib.N_FOLDS, cvlib.FOLD_SEED, True)
    meta = gold.drop_duplicates("doc_id").set_index("doc_id")
    out = {}
    for k in range(cvlib.N_FOLDS):
        held = [d for d in ids if fold[d] == k]
        train = [d for d in ids if fold[d] != k]
        td = cvlib.build_train_data(gold, docs, train, groups, syn_seed=100 + k)
        m = fit_pair_model_id(td.page_text, td.page_type, td.page_group, td.pairs, kind="gb", seed=0)
        print(f"[cross-fit id fold {k}] giữ lại {len(held)}, huấn luyện {len(train)}; cặp thật {td.n_real_pairs}, đường nối tổng hợp {td.n_syn_pairs}", flush=True)
        for d in held:
            if meta.loc[d, "eval_group"] in sl.GROUPS:
                s = m.doc_scores([p.full_text for p in docs[d].pages])
                out[d] = [None if x != x else float(x) for x in s]
    SCORES_ID.parent.mkdir(exist_ok=True)
    SCORES_ID.write_text(json.dumps(out), encoding="utf-8")
    return out


def vlm_flags(docs, ids, meta):
    """Cờ theo trang từ `results/vlm_pairs_dev.csv` (VLM nói DIFFERENT_COPY). Trang không được hỏi: False. None nếu chưa chạy vlm_pairs.py."""
    f = HERE / "results" / "vlm_pairs_dev.csv"
    if not f.exists():
        return None
    import pandas as pd
    df = pd.read_csv(f, dtype={"doc_id": str}, keep_default_na=False)
    out = {d: [False] * len(docs[d].pages) for d in ids if meta.loc[d, "eval_group"] in sl.GROUPS}
    for r in df[df.vlm_label == "DIFFERENT_COPY"].itertuples():
        pages = [p.page_number for p in docs[r.doc_id].pages]
        out[r.doc_id][pages.index(int(r.page))] = True
    return out


def build_variants(ids, docs, meta, segs, sc_old, sc_id):
    flags = {d: id_rule_pages([p.full_text for p in docs[d].pages]) for d in ids if meta.loc[d, "eval_group"] in sl.GROUPS}
    vf = vlm_flags(docs, ids, meta)
    V = {}
    specs = [
        (BASE, sc_old, None, True, True),
        ("model+merge + quy tắc: chỉ chặn gộp", sc_old, flags, False, True),
        ("model+merge + quy tắc: thêm ranh giới + chặn gộp  (=`model+merge+id`)", sc_old, flags, True, True),
        ("c2+đặc trưng id, model+merge", sc_id, None, True, True),
        ("c2+đặc trưng id + quy tắc thêm/chặn, model+merge", sc_id, flags, True, True),
    ]
    if vf is not None:
        orf = {d: [a or b for a, b in zip(flags[d], vf[d])] for d in flags}
        specs += [("model+merge + VLM qwen3.5:4b (thêm/chặn trên cặp được hỏi)", sc_old, vf, True, True),
                  ("model+merge + quy tắc HOẶC VLM", sc_old, orf, True, True)]
    for name, sc, fl, add, block in specs:
        pred = {}
        for d in flags:
            pages = [p.page_number for p in docs[d].pages]
            pred[d] = L.simulate(sc[d], pages, segs[d], 0.7, 0.99, True, fl[d] if fl else None, add, block)
        V[name] = pred
    return V, flags


def main():
    ap = ec.common_args(__doc__)
    args = ap.parse_args()
    gold = sl.load_gold()
    ids = sl.scope_doc_ids(gold, "dev")
    docs = sl.load_documents(ids)
    meta = gold.drop_duplicates("doc_id").set_index("doc_id")
    segs, sc_old = L.load_s10_labels(), L.load_scores()
    t0 = time.perf_counter()
    sc_id = crossfit_id_scores(gold, ids, docs)
    print(f"cross-fit id: {time.perf_counter() - t0:.0f} s")
    V, flags = build_variants(ids, docs, meta, segs, sc_old, sc_id)
    dfs = {n: L.evaluate(p, ids, docs, gold) for n, p in V.items()}
    summ = sl.summary_table_md(dfs, args.boot)
    print(summ)
    base = dfs[BASE]
    paired = []
    for n in dfs:
        if n != BASE:
            paired += [f"### {n} - {BASE}", "", sl.paired_table_md(dfs[n], base, "mới", "nền", args.boot), ""]
    print(chr(10).join(paired))
    vt = vlm_table()
    print(vt)
    if args.no_write:
        return
    for k, (n, df) in enumerate(dfs.items()):
        ec.save_per_file(HERE, f"v{k}", df, V[n], "dev")      # v0 = nền; thứ tự biến thể như bảng trong RESULTS.md
    cmd = r".venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/06_same_type/run.py"
    header = ec.reproduce_header(HERE, cmd, args, {
        "mã đo": f"`src/splitting/identity.py` (sha1[:10] `{ec.sha10(sl.REPO / 'src' / 'splitting' / 'identity.py')}`), `src/splitting/learned_id.py` (`{ec.sha10(sl.REPO / 'src' / 'splitting' / 'learned_id.py')}`), mô phỏng `model+merge` ngoại tuyến `lib06.py`",
        "điểm cặp trang nền": "`teams/00_data_and_eval/experiments/01_end_to_end/results/pair_scores_dev.json` (c2 cross-fit 5 fold theo nhóm biểu mẫu); nhãn lát cắt: `per_file_dev.csv` biến thể S10",
        "điểm c2+id": f"cross-fit cùng quy trình (cvlib, 5 fold, syn_seed 100+fold) lưu ở `results/pair_scores_id_dev.json`; {time.strftime('%Y-%m-%d')}"})
    notes = HERE / "notes.md"
    out = ["# 06 - Nhiều bản cùng loại trong một tệp (T5): dấu hiệu 'bản khác'", "", header, "",
           SUMMARY,
           "## Kết quả theo nhóm (phạm vi dev, mô phỏng `model+merge` = S10 ngưỡng 0,7, giữ ranh giới điểm >= 0,99)", "", summ, "",
           "## So sánh ghép cặp với `model+merge` hiện tại (bootstrap theo tệp)", "", *paired,
           "## VLM qwen3.5:4b nhìn hai ảnh trang liền kề", "", vt, ""]
    if notes.exists():
        out.append(notes.read_text(encoding="utf-8"))
    (HERE / "RESULTS.md").write_text(chr(10).join(out), encoding="utf-8")
    print("đã ghi", HERE / "RESULTS.md")


def vlm_table():
    f = HERE / "results" / "vlm_pairs_dev.csv"
    if not f.exists():
        return "(chưa chạy vlm_pairs.py)"
    import numpy as np
    import pandas as pd
    df = pd.read_csv(f, dtype={"doc_id": str}, keep_default_na=False)
    lines = [f"{len(df)} lời gọi (giới hạn 300), lỗi/hết giờ: {int((df.error != '').sum())}; độ trễ trung vị {df.latency_ms.median() / 1000:.1f} s/cặp (GPU dùng chung, chỉ tham khảo).", "",
             "| nhóm | đáp án | số cặp | VLM nói DIFFERENT_COPY | tỉ lệ [Wilson 95%] |", "|---|---|---|---|---|"]
    for (g, y), sub in df.groupby(["group", "y"]):
        k, n = int((sub.vlm_label == "DIFFERENT_COPY").sum()), len(sub)
        p, lo, hi = sl.wilson(k, n)
        lines.append(f"| {sl.GROUP_TITLES[g]} | {'ranh giới thật' if y == 1 else 'không phải ranh giới'} | {n} | {k} | {p:.2f} [{lo:.2f}; {hi:.2f}] |")
    lines += ["", "Không báo AUC: Ollama trả logprob của phân phối KHÔNG ràng buộc theo schema (token đầu của câu trả lời không phải nhãn được chọn), nên cột `p_diff` trong CSV chỉ để tham khảo, KHÔNG dùng làm điểm."]
    return chr(10).join(lines)


if __name__ == "__main__":
    main()
