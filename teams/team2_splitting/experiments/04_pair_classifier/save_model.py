r"""Huấn luyện lại bộ phân loại cặp trang (c2, gradient boosting) trên TOÀN BỘ phạm vi dev rồi ghi artefact vào teams/team2_splitting/models/.

    .venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/04_pair_classifier/save_model.py

Dữ liệu huấn luyện: trang + cặp thật của mọi tài liệu DEV và EXCLUDED_COMPOSITE (KHÔNG có TEST) + 400 composite tổng hợp (seed 99) từ tài liệu đơn DEV.
Số đo của mô hình NÀY không có trên dev (nó đã thấy mọi tài liệu dev); số đo trung thực là cross-fitting ở run.py và một lần chấm TEST (--scope all --final-test).
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
import cvlib  # noqa: E402
import expcommon as ec  # noqa: E402
import splitlib as sl  # noqa: E402
from src.splitting.learned import DEFAULT_MODEL_FILE, MODELS_DIR, fit_pair_model, save_model  # noqa: E402


def main():
    gold = sl.load_gold()
    dev_ids = sl.scope_doc_ids(gold, "dev")
    assert not (set(dev_ids) & set(gold[gold.split == "TEST"].doc_id)), "dev_ids chứa tài liệu TEST"
    docs = sl.load_documents(dev_ids)
    groups = cvlib.cv_group_map(gold, dev_ids)
    td = cvlib.build_train_data(gold, docs, dev_ids, groups, syn_seed=99)
    m = fit_pair_model(td.page_text, td.page_type, td.page_group, td.pairs, kind="gb", seed=0, threshold=0.5,
                       meta=dict(n_real_pairs=td.n_real_pairs, n_syn_pairs=td.n_syn_pairs, syn_seed=td.syn_seed, n_train_docs=len(dev_ids)))
    info = dict(
        name="pair_gb_v0", description="Bộ phân loại cặp trang (gradient boosting) + mô hình loại trang (TF-IDF + LR) cho src.splitting",
        labels_file="labels_v2.csv", labels_sha1_10=ec.sha10(sl.LABELS_CSV), gold_file="boundary_gold_v0.csv", gold_sha1_10=ec.sha10(sl.GOLD_CSV),
        splits_sha1_10=ec.sha10(sl.SPLITS_CSV), ocr_sha1_10=ec.sha10(sl.OCR_JSONL),
        train_doc_ids_sha1_10=hashlib.sha1(",".join(sorted(dev_ids)).encode()).hexdigest()[:10], n_train_docs=len(dev_ids),
        train_scope="DEV + EXCLUDED_COMPOSITE (không TEST)", synthetic=dict(generator="gold/make_synthetic.py", n=cvlib.N_SYN_TRAIN, seed=99),
        code_sha1_10=ec.sha10(sl.REPO / "src" / "splitting" / "learned.py"),
        caveat="Nhãn ranh giới là boundary_gold_v0 (một annotator AI, chưa người kiểm). Cross-validated, không phải TEST khóa.",
    )
    out = save_model(m, MODELS_DIR / DEFAULT_MODEL_FILE, info)
    print("đã ghi", out, "và", out.with_suffix(".json"))
    print(json.dumps({k: info[k] for k in ("labels_sha1_10", "gold_sha1_10", "train_doc_ids_sha1_10", "n_train_docs")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
