# results/ - Bảng kết quả của Nhóm 2 (tách tài liệu)

`results_table.csv` là bảng riêng của nhóm. Bảng chung `teams/team3_classification/results/results_table.csv` do giao thức đánh giá định nghĩa cho bài toán **phân loại** (cột `accuracy`, `macro_f1`...), không có chỗ cho precision/recall ranh giới theo nhóm, nên **không ghi vào đó**. Quy ước giữ nguyên tinh thần giao thức: mỗi dòng nêu nhãn + sha, phạm vi, cỡ mẫu; CI là bootstrap theo tệp.

Mỗi dòng = một (phương pháp, phạm vi, nhóm). Các `run.py` ghi bảng này; chạy lại cùng (`method`, `scope`, `group`) thì **thay** dòng cũ.

| Cột | Ý nghĩa |
|---|---|
| `run_id`, `timestamp` | Thời điểm UTC của lần chạy (+ số thí nghiệm) |
| `method` | `01_rule_baseline`, `02_rule_v2`, `03_b0`, `03_b1`, `04_c1`, `04_c2`, `05_qwen35_4b_zero_shot` |
| `scope` | `dev` = DEV + EXCLUDED_COMPOSITE (được nhìn lỗi / chỉnh); `all` = thêm tài liệu TEST, chấm một lần (`--scope all --final-test`). Dòng `all` trộn dự đoán out-of-fold của tài liệu dev với dự đoán của mô hình huấn luyện trên toàn bộ dev cho tài liệu TEST; số riêng cho tài liệu TEST: `../experiments/RESULTS_test_docs_only.md` |
| `group` | `mixed` (composite khác loại), `same_other` (cùng loại ngoài BB_LAY_MAU), `same_bb` (BB_LAY_MAU), `negative` (nhiều trang không composite) |
| `n_files`, `n_positions`, `n_true_boundaries` | Cỡ mẫu (vị trí = trang >= 2 có văn bản OCR) |
| `precision/recall/f1` + `_lo/_hi` | Gộp trong nhóm; CI 95% percentile bootstrap 2000 lần lấy mẫu lại theo tệp (rỗng nếu mẫu số bằng 0) |
| `exact_rate` + `_lo/_hi` | Tỉ lệ tệp có phân đoạn đúng toàn bộ; CI bootstrap |
| `false_splits`, `false_split_per100` | Số lần tách nhầm và tỉ lệ trên 100 vị trí (bắt buộc đọc ở nhóm `negative`) |
| `gold_sha`, `labels_sha` | sha1[:10] của `boundary_gold_v0.csv` và `data/labels_v2.csv` |
| `notes` | Ghi chú |

Đáp án là `v0` (máy, chưa người kiểm); số của phương pháp có học là cross-validated theo nhóm biểu mẫu. Không có dòng nào là tập TEST khóa theo nghĩa của giao thức (chỉ có 2 tệp composite trong TEST).
