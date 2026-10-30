r"""Tóm tắt RIÊNG cho tài liệu TEST từ các lần chấm một lần (`--scope all --final-test`) của thí nghiệm 01-04.

    .venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/test_docs_only.py

Chỉ ĐỌC các tệp results/per_file_*_all.csv đã sinh; ghi RESULTS_test_docs_only.md. Với tài liệu TEST, các phương pháp có học dùng mô hình
huấn luyện trên TOÀN BỘ phạm vi dev (không có TEST) - đúng quy trình 'huấn luyện lại trên DEV rồi chấm TEST một lần'.
Cỡ mẫu rất nhỏ (2 tệp BB_LAY_MAU, 36 tệp âm, 0 composite khác loại, 0 composite cùng loại ngoài BB_LAY_MAU): chỉ để kiểm tra không có
sai lệch lớn so với số trên dev, KHÔNG dùng để chọn lại phương pháp.
"""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import expcommon as ec  # noqa: E402
import splitlib as sl  # noqa: E402

FILES = {
    "rule cũ (01)": "01_rule_baseline/results/per_file_rule_baseline_all.csv",
    "rule v2 (02)": "02_rule_v2/results/per_file_rule_v2_all.csv",
    "b0 chỉ đổi loại (03)": "03_type_merge/results/per_file_b0_all.csv",
    "b1 đổi loại + bản khác (03)": "03_type_merge/results/per_file_b1_all.csv",
    "c1 hồi quy logistic (04)": "04_pair_classifier/results/per_file_c1_all.csv",
    "c2 gradient boosting (04)": "04_pair_classifier/results/per_file_c2_all.csv",
}


def main():
    gold = sl.load_gold()
    test_ids = set(gold[gold.split == "TEST"].doc_id)
    per = {}
    for name, rel in FILES.items():
        df = pd.read_csv(HERE / rel, dtype={"doc_id": str})
        df = df[df.doc_id.isin(test_ids)].drop(columns=["pred_starts"], errors="ignore")
        per[name] = df[sl.PER_FILE_COLS]
    md = ["# Tài liệu TEST - chấm một lần, cấu hình đã đóng băng trên dev", "",
          "Sinh bởi `.venv\\Scripts\\python.exe -X utf8 teams/team2_splitting/experiments/test_docs_only.py` từ các tệp `results/per_file_*_all.csv` "
          "(lệnh gốc: `... run.py --scope all --final-test` của từng thí nghiệm). Cỡ mẫu rất nhỏ; chỉ để kiểm tra nhất quán với dev.", "",
          sl.summary_table_md(per, sl.BOOT_N)]
    out = HERE / "RESULTS_test_docs_only.md"
    out.write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md)[:6000])
    print("đã ghi", out)


if __name__ == "__main__":
    main()
