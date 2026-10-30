# 06 - Nhiều bản cùng loại trong một tệp (T5): dấu hiệu 'bản khác'

- **ngày chạy (UTC):** 2026-10-15 16:33
- **lệnh:** `.venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/06_same_type/run.py`
- **đáp án:** `teams/team2_splitting/gold/boundary_gold_v0.csv` sha1[:10] = `d9a30b5896` (v0, máy, CHƯA người kiểm)
- **nhãn:** `data/labels_v2.csv` sha1[:10] = `eb3348713a`
- **văn bản:** `data/ocr_v2.jsonl` (OCR cục bộ, tối đa 30 trang/tài liệu) sha1[:10] = `ac87a66c25`
- **phạm vi:** **dev** = DEV + EXCLUDED_COMPOSITE (không có tài liệu TEST)
- **bootstrap:** 2000 lần lấy mẫu lại theo TỆP, seed 20260711, percentile 95%
- **máy:** Windows-11-10.0.26100-SP0, Python 3.13.14
- **mã đo:** `src/splitting/identity.py` (sha1[:10] `40147046dd`), `src/splitting/learned_id.py` (`08c167cb99`), mô phỏng `model+merge` ngoại tuyến `lib06.py`
- **điểm cặp trang nền:** `teams/00_data_and_eval/experiments/01_end_to_end/results/pair_scores_dev.json` (c2 cross-fit 5 fold theo nhóm biểu mẫu); nhãn lát cắt: `per_file_dev.csv` biến thể S10
- **điểm c2+id:** cross-fit cùng quy trình (cvlib, 5 fold, syn_seed 100+fold) lưu ở `results/pair_scores_id_dev.json`; 2026-10-15

## Tóm tắt (đọc trước)

- **Câu hỏi:** nhóm "nhiều bản cùng loại trong một tệp" (T5) bị `model+merge` bỏ sót gần hết (0/7 ranh giới ngoài `BB_LAY_MAU` trên dev: bộ gộp cùng loại xóa ranh giới, và mô hình cặp trang cho điểm thấp khi hai tờ cùng mẫu). Có đặc trưng "bản khác" nào bắt được chúng mà không làm tăng tách nhầm trên 155 tệp nhiều trang bình thường không?
- **Kết quả:** một quy tắc không tham số, "đầu trang giống nhau (jaccard >= 0,7) VÀ số hiệu 'Số ...' ở đầu cả hai trang khác nhau", thêm ranh giới điểm 1,0 (nên không bị gộp lại theo loại), nâng cùng loại ngoài BB từ **0/7 lên 4/7** ranh giới (recall +0,571, CI bootstrap ghép cặp theo tệp [0,167; 0,889], n = 6 tệp) và **không đổi gì** ở ba nhóm còn lại: mẫu âm vẫn 9 tách nhầm trên 501 vị trí (6/155 tệp), khác loại 19/20, `BB_LAY_MAU` 40/46. Đưa vào `src/splitting/` làm tùy chọn `model+merge+id` (không phải mặc định).
- **Không thành công:** đặc trưng định danh trong bộ phân loại cặp trang (c2+id, cross-fit): 1/7, không tách được khỏi nền; VLM `qwen3.5:4b` nhìn hai ảnh: 3/7 nhưng thêm 7 tách nhầm ở mẫu âm (tách được: kém hơn), không dùng.
- **Hạn chế chính:** quy tắc được nghĩ ra sau khi đọc các tệp cùng loại của dev (4 ranh giới bắt được nằm ở 3 tệp), và TEST không có tệp cùng loại ngoài `BB_LAY_MAU` nào để kiểm giữ ngoài; **TEST không được chạy**. Phần "không hại mẫu âm" mạnh hơn (0/448 cặp mẫu âm bị kích hoạt). 3/7 ranh giới còn lại (OCR hỏng, mẫu không có "Số", hai giấy khác mẫu) chưa phương pháp nào bắt được.
- **Cách đo:** mô phỏng ngoại tuyến `model+merge` (điểm cặp trang c2 cross-fit 5 fold theo nhóm biểu mẫu của thí nghiệm 01 end-to-end; nhãn lát cắt của S10), tái lập đúng 174/174 tệp nhiều trang của S10. "Nền" = chính `model+merge`.

## Kết quả theo nhóm (phạm vi dev, mô phỏng `model+merge` = S10 ngưỡng 0,7, giữ ranh giới điểm >= 0,99)


**composite khác loại** (8 tệp, 26 vị trí, 20 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment (tệp nguyên vẹn) | tách nhầm / 100 vị trí | loại segment (cổng luật) |
|---|---|---|---|---|---|---|
| model+merge (S10, nền) | 1.000 [1.000; 1.000] (19/19) | 0.950 [0.850; 1.000] (19/20) | 0.974 [0.919; 1.000] | 7/8 = 0.875 (Wilson 0.529; 0.978) | 0.00 [0.00; 0.00] (0) | 0.679 [0.500; 0.786] (oracle 0.679) |
| model+merge + quy tắc: chỉ chặn gộp | 1.000 [1.000; 1.000] (19/19) | 0.950 [0.850; 1.000] (19/20) | 0.974 [0.919; 1.000] | 7/8 = 0.875 (Wilson 0.529; 0.978) | 0.00 [0.00; 0.00] (0) | 0.679 [0.500; 0.786] (oracle 0.679) |
| model+merge + quy tắc: thêm ranh giới + chặn gộp  (=`model+merge+id`) | 1.000 [1.000; 1.000] (19/19) | 0.950 [0.850; 1.000] (19/20) | 0.974 [0.919; 1.000] | 7/8 = 0.875 (Wilson 0.529; 0.978) | 0.00 [0.00; 0.00] (0) | 0.679 [0.500; 0.786] (oracle 0.679) |
| c2+đặc trưng id, model+merge | 1.000 [1.000; 1.000] (20/20) | 1.000 [1.000; 1.000] (20/20) | 1.000 [1.000; 1.000] | 8/8 = 1.000 (Wilson 0.676; 1.000) | 0.00 [0.00; 0.00] (0) | 0.679 [0.500; 0.786] (oracle 0.679) |
| c2+đặc trưng id + quy tắc thêm/chặn, model+merge | 1.000 [1.000; 1.000] (20/20) | 1.000 [1.000; 1.000] (20/20) | 1.000 [1.000; 1.000] | 8/8 = 1.000 (Wilson 0.676; 1.000) | 0.00 [0.00; 0.00] (0) | 0.679 [0.500; 0.786] (oracle 0.679) |
| model+merge + VLM qwen3.5:4b (thêm/chặn trên cặp được hỏi) | 1.000 [1.000; 1.000] (19/19) | 0.950 [0.850; 1.000] (19/20) | 0.974 [0.919; 1.000] | 7/8 = 0.875 (Wilson 0.529; 0.978) | 0.00 [0.00; 0.00] (0) | 0.679 [0.500; 0.786] (oracle 0.679) |
| model+merge + quy tắc HOẶC VLM | 1.000 [1.000; 1.000] (19/19) | 0.950 [0.850; 1.000] (19/20) | 0.974 [0.919; 1.000] | 7/8 = 0.875 (Wilson 0.529; 0.978) | 0.00 [0.00; 0.00] (0) | 0.679 [0.500; 0.786] (oracle 0.679) |

**composite cùng loại, ngoài BB_LAY_MAU** (6 tệp, 11 vị trí, 7 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment (tệp nguyên vẹn) | tách nhầm / 100 vị trí | loại segment (cổng luật) |
|---|---|---|---|---|---|---|
| model+merge (S10, nền) | 0.000 [0.000; 0.000] (0/1) | 0.000 [0.000; 0.000] (0/7) | 0.000 [0.000; 0.000] | 0/6 = 0.000 (Wilson 0.000; 0.390) | 9.09 [0.00; 21.45] (1) | 0.692 [0.333; 1.000] (oracle 0.615) |
| model+merge + quy tắc: chỉ chặn gộp | 0.667 [0.000; 1.000] (2/3) | 0.286 [0.000; 0.667] (2/7) | 0.400 [0.000; 0.800] | 1/6 = 0.167 (Wilson 0.030; 0.564) | 9.09 [0.00; 21.45] (1) | 0.692 [0.333; 1.000] (oracle 0.615) |
| model+merge + quy tắc: thêm ranh giới + chặn gộp  (=`model+merge+id`) | 0.800 [0.250; 1.000] (4/5) | 0.571 [0.167; 0.889] (4/7) | 0.667 [0.200; 0.941] | 3/6 = 0.500 (Wilson 0.188; 0.812) | 9.09 [0.00; 21.45] (1) | 0.692 [0.333; 1.000] (oracle 0.615) |
| c2+đặc trưng id, model+merge | 0.500 [0.000; 1.000] (1/2) | 0.143 [0.000; 0.333] (1/7) | 0.222 [0.000; 0.500] | 0/6 = 0.000 (Wilson 0.000; 0.390) | 9.09 [0.00; 21.45] (1) | 0.692 [0.333; 1.000] (oracle 0.615) |
| c2+đặc trưng id + quy tắc thêm/chặn, model+merge | 0.800 [0.250; 1.000] (4/5) | 0.571 [0.167; 0.889] (4/7) | 0.667 [0.200; 0.941] | 3/6 = 0.500 (Wilson 0.188; 0.812) | 9.09 [0.00; 21.45] (1) | 0.692 [0.333; 1.000] (oracle 0.615) |
| model+merge + VLM qwen3.5:4b (thêm/chặn trên cặp được hỏi) | 0.750 [0.250; 1.000] (3/4) | 0.429 [0.143; 0.714] (3/7) | 0.545 [0.182; 0.833] | 2/6 = 0.333 (Wilson 0.097; 0.700) | 9.09 [0.00; 21.45] (1) | 0.692 [0.333; 1.000] (oracle 0.615) |
| model+merge + quy tắc HOẶC VLM | 0.800 [0.250; 1.000] (4/5) | 0.571 [0.167; 0.889] (4/7) | 0.667 [0.200; 0.941] | 3/6 = 0.500 (Wilson 0.188; 0.812) | 9.09 [0.00; 21.45] (1) | 0.692 [0.333; 1.000] (oracle 0.615) |

**composite BB_LAY_MAU** (5 tệp, 46 vị trí, 46 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment (tệp nguyên vẹn) | tách nhầm / 100 vị trí | loại segment (cổng luật) |
|---|---|---|---|---|---|---|
| model+merge (S10, nền) | 1.000 [1.000; 1.000] (40/40) | 0.870 [0.625; 1.000] (40/46) | 0.930 [0.769; 1.000] | 3/5 = 0.600 (Wilson 0.231; 0.882) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| model+merge + quy tắc: chỉ chặn gộp | 1.000 [1.000; 1.000] (40/40) | 0.870 [0.625; 1.000] (40/46) | 0.930 [0.769; 1.000] | 3/5 = 0.600 (Wilson 0.231; 0.882) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| model+merge + quy tắc: thêm ranh giới + chặn gộp  (=`model+merge+id`) | 1.000 [1.000; 1.000] (40/40) | 0.870 [0.625; 1.000] (40/46) | 0.930 [0.769; 1.000] | 3/5 = 0.600 (Wilson 0.231; 0.882) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| c2+đặc trưng id, model+merge | 1.000 [1.000; 1.000] (42/42) | 0.913 [0.364; 0.988] (42/46) | 0.955 [0.533; 0.994] | 2/5 = 0.400 (Wilson 0.118; 0.769) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| c2+đặc trưng id + quy tắc thêm/chặn, model+merge | 1.000 [1.000; 1.000] (42/42) | 0.913 [0.364; 0.988] (42/46) | 0.955 [0.533; 0.994] | 2/5 = 0.400 (Wilson 0.118; 0.769) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| model+merge + VLM qwen3.5:4b (thêm/chặn trên cặp được hỏi) | 1.000 [1.000; 1.000] (42/42) | 0.913 [0.625; 1.000] (42/46) | 0.955 [0.769; 1.000] | 3/5 = 0.600 (Wilson 0.231; 0.882) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| model+merge + quy tắc HOẶC VLM | 1.000 [1.000; 1.000] (42/42) | 0.913 [0.625; 1.000] (42/46) | 0.955 [0.769; 1.000] | 3/5 = 0.600 (Wilson 0.231; 0.882) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |

**mẫu âm (nhiều trang, không composite)** (155 tệp, 501 vị trí, 0 ranh giới thật)

| phương pháp | tách nhầm / 100 vị trí | tệp có >= 1 tách nhầm | exact-segment (tệp nguyên vẹn) | loại segment (cổng luật) |
|---|---|---|---|---|
| model+merge (S10, nền) | 1.80 [0.47; 3.50] (9/501) | 6/155 = 0.039 [0.013; 0.071] | 149/155 = 0.961 (Wilson 0.918; 0.982) | 0.813 [0.748; 0.871] (oracle 0.819) |
| model+merge + quy tắc: chỉ chặn gộp | 1.80 [0.47; 3.50] (9/501) | 6/155 = 0.039 [0.013; 0.071] | 149/155 = 0.961 (Wilson 0.918; 0.982) | 0.813 [0.748; 0.871] (oracle 0.819) |
| model+merge + quy tắc: thêm ranh giới + chặn gộp  (=`model+merge+id`) | 1.80 [0.47; 3.50] (9/501) | 6/155 = 0.039 [0.013; 0.071] | 149/155 = 0.961 (Wilson 0.918; 0.982) | 0.813 [0.748; 0.871] (oracle 0.819) |
| c2+đặc trưng id, model+merge | 1.40 [0.40; 2.88] (7/501) | 6/155 = 0.039 [0.013; 0.071] | 149/155 = 0.961 (Wilson 0.918; 0.982) | 0.819 [0.755; 0.877] (oracle 0.819) |
| c2+đặc trưng id + quy tắc thêm/chặn, model+merge | 1.40 [0.40; 2.88] (7/501) | 6/155 = 0.039 [0.013; 0.071] | 149/155 = 0.961 (Wilson 0.918; 0.982) | 0.819 [0.755; 0.877] (oracle 0.819) |
| model+merge + VLM qwen3.5:4b (thêm/chặn trên cặp được hỏi) | 3.19 [1.50; 5.11] (16/501) | 10/155 = 0.065 [0.026; 0.103] | 145/155 = 0.935 (Wilson 0.885; 0.965) | 0.800 [0.735; 0.865] (oracle 0.819) |
| model+merge + quy tắc HOẶC VLM | 3.19 [1.50; 5.11] (16/501) | 10/155 = 0.065 [0.026; 0.103] | 145/155 = 0.935 (Wilson 0.885; 0.965) | 0.800 [0.735; 0.865] (oracle 0.819) |

## So sánh ghép cặp với `model+merge` hiện tại (bootstrap theo tệp)

### model+merge + quy tắc: chỉ chặn gộp - model+merge (S10, nền)

| nhóm | chỉ số | mới - nền | CI 95% (bootstrap ghép cặp theo tệp) | kết luận |
|---|---|---|---|---|
| composite khác loại (n=8) | f1 | +0.000 | [+0.000; +0.000] | không tách được |
| composite khác loại (n=8) | recall | +0.000 | [+0.000; +0.000] | không tách được |
| composite khác loại (n=8) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite khác loại (n=8) | exact_rate | +0.000 | [+0.000; +0.000] | không tách được |
| composite khác loại (n=8) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | f1 | +0.400 | [+0.000; +0.800] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | recall | +0.286 | [+0.000; +0.667] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | precision | +0.667 | [+0.000; +0.857] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | exact_rate | +0.167 | [+0.000; +0.500] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | f1 | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | recall | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | exact_rate | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=155) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=155) | files_with_false_split | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=155) | exact_rate | +0.000 | [+0.000; +0.000] | không tách được |

### model+merge + quy tắc: thêm ranh giới + chặn gộp  (=`model+merge+id`) - model+merge (S10, nền)

| nhóm | chỉ số | mới - nền | CI 95% (bootstrap ghép cặp theo tệp) | kết luận |
|---|---|---|---|---|
| composite khác loại (n=8) | f1 | +0.000 | [+0.000; +0.000] | không tách được |
| composite khác loại (n=8) | recall | +0.000 | [+0.000; +0.000] | không tách được |
| composite khác loại (n=8) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite khác loại (n=8) | exact_rate | +0.000 | [+0.000; +0.000] | không tách được |
| composite khác loại (n=8) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | f1 | +0.667 | [+0.200; +0.941] | tách được: tốt hơn |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | recall | +0.571 | [+0.167; +0.889] | tách được: tốt hơn |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | precision | +0.800 | [+0.000; +0.875] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | exact_rate | +0.500 | [+0.167; +0.833] | tách được: tốt hơn |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | f1 | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | recall | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | exact_rate | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=155) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=155) | files_with_false_split | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=155) | exact_rate | +0.000 | [+0.000; +0.000] | không tách được |

### c2+đặc trưng id, model+merge - model+merge (S10, nền)

| nhóm | chỉ số | mới - nền | CI 95% (bootstrap ghép cặp theo tệp) | kết luận |
|---|---|---|---|---|
| composite khác loại (n=8) | f1 | +0.026 | [+0.000; +0.081] | không tách được |
| composite khác loại (n=8) | recall | +0.050 | [+0.000; +0.150] | không tách được |
| composite khác loại (n=8) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite khác loại (n=8) | exact_rate | +0.125 | [+0.000; +0.375] | không tách được |
| composite khác loại (n=8) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | f1 | +0.222 | [+0.000; +0.500] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | recall | +0.143 | [+0.000; +0.333] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | precision | +0.500 | [+0.000; +0.750] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | exact_rate | +0.000 | [+0.000; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | f1 | +0.024 | [-0.244; +0.064] | không tách được |
| composite BB_LAY_MAU (n=5) | recall | +0.043 | [-0.286; +0.117] | không tách được |
| composite BB_LAY_MAU (n=5) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | exact_rate | -0.200 | [-0.800; +0.400] | không tách được |
| composite BB_LAY_MAU (n=5) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=155) | false_split_per100 | -0.399 | [-1.802; +0.598] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=155) | files_with_false_split | +0.000 | [-0.019; +0.019] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=155) | exact_rate | +0.000 | [-0.019; +0.019] | không tách được |

### c2+đặc trưng id + quy tắc thêm/chặn, model+merge - model+merge (S10, nền)

| nhóm | chỉ số | mới - nền | CI 95% (bootstrap ghép cặp theo tệp) | kết luận |
|---|---|---|---|---|
| composite khác loại (n=8) | f1 | +0.026 | [+0.000; +0.081] | không tách được |
| composite khác loại (n=8) | recall | +0.050 | [+0.000; +0.150] | không tách được |
| composite khác loại (n=8) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite khác loại (n=8) | exact_rate | +0.125 | [+0.000; +0.375] | không tách được |
| composite khác loại (n=8) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | f1 | +0.667 | [+0.200; +0.941] | tách được: tốt hơn |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | recall | +0.571 | [+0.167; +0.889] | tách được: tốt hơn |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | precision | +0.800 | [+0.000; +0.875] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | exact_rate | +0.500 | [+0.167; +0.833] | tách được: tốt hơn |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | f1 | +0.024 | [-0.244; +0.064] | không tách được |
| composite BB_LAY_MAU (n=5) | recall | +0.043 | [-0.286; +0.117] | không tách được |
| composite BB_LAY_MAU (n=5) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | exact_rate | -0.200 | [-0.800; +0.400] | không tách được |
| composite BB_LAY_MAU (n=5) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=155) | false_split_per100 | -0.399 | [-1.802; +0.598] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=155) | files_with_false_split | +0.000 | [-0.019; +0.019] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=155) | exact_rate | +0.000 | [-0.019; +0.019] | không tách được |

### model+merge + VLM qwen3.5:4b (thêm/chặn trên cặp được hỏi) - model+merge (S10, nền)

| nhóm | chỉ số | mới - nền | CI 95% (bootstrap ghép cặp theo tệp) | kết luận |
|---|---|---|---|---|
| composite khác loại (n=8) | f1 | +0.000 | [+0.000; +0.000] | không tách được |
| composite khác loại (n=8) | recall | +0.000 | [+0.000; +0.000] | không tách được |
| composite khác loại (n=8) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite khác loại (n=8) | exact_rate | +0.000 | [+0.000; +0.000] | không tách được |
| composite khác loại (n=8) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | f1 | +0.545 | [+0.182; +0.833] | tách được: tốt hơn |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | recall | +0.429 | [+0.143; +0.714] | tách được: tốt hơn |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | precision | +0.750 | [+0.000; +0.833] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | exact_rate | +0.333 | [+0.000; +0.667] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | f1 | +0.024 | [+0.000; +0.037] | không tách được |
| composite BB_LAY_MAU (n=5) | recall | +0.043 | [+0.000; +0.065] | không tách được |
| composite BB_LAY_MAU (n=5) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | exact_rate | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=155) | false_split_per100 | +1.397 | [+0.269; +2.453] | tách được: kém hơn |
| mẫu âm (nhiều trang, không composite) (n=155) | files_with_false_split | +0.026 | [+0.006; +0.052] | tách được: kém hơn |
| mẫu âm (nhiều trang, không composite) (n=155) | exact_rate | -0.026 | [-0.052; -0.006] | tách được: kém hơn |

### model+merge + quy tắc HOẶC VLM - model+merge (S10, nền)

| nhóm | chỉ số | mới - nền | CI 95% (bootstrap ghép cặp theo tệp) | kết luận |
|---|---|---|---|---|
| composite khác loại (n=8) | f1 | +0.000 | [+0.000; +0.000] | không tách được |
| composite khác loại (n=8) | recall | +0.000 | [+0.000; +0.000] | không tách được |
| composite khác loại (n=8) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite khác loại (n=8) | exact_rate | +0.000 | [+0.000; +0.000] | không tách được |
| composite khác loại (n=8) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | f1 | +0.667 | [+0.200; +0.941] | tách được: tốt hơn |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | recall | +0.571 | [+0.167; +0.889] | tách được: tốt hơn |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | precision | +0.800 | [+0.000; +0.875] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | exact_rate | +0.500 | [+0.167; +0.833] | tách được: tốt hơn |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | f1 | +0.024 | [+0.000; +0.037] | không tách được |
| composite BB_LAY_MAU (n=5) | recall | +0.043 | [+0.000; +0.065] | không tách được |
| composite BB_LAY_MAU (n=5) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | exact_rate | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=155) | false_split_per100 | +1.397 | [+0.269; +2.453] | tách được: kém hơn |
| mẫu âm (nhiều trang, không composite) (n=155) | files_with_false_split | +0.026 | [+0.006; +0.052] | tách được: kém hơn |
| mẫu âm (nhiều trang, không composite) (n=155) | exact_rate | -0.026 | [-0.052; -0.006] | tách được: kém hơn |

## VLM qwen3.5:4b nhìn hai ảnh trang liền kề

147 lời gọi (giới hạn 300), lỗi/hết giờ: 1; độ trễ trung vị 2.8 s/cặp (GPU dùng chung, chỉ tham khảo).

| nhóm | đáp án | số cặp | VLM nói DIFFERENT_COPY | tỉ lệ [Wilson 95%] |
|---|---|---|---|---|
| composite khác loại | không phải ranh giới | 6 | 0 | 0.00 [0.00; 0.39] |
| composite khác loại | ranh giới thật | 20 | 3 | 0.15 [0.05; 0.36] |
| mẫu âm (nhiều trang, không composite) | không phải ranh giới | 66 | 7 | 0.11 [0.05; 0.20] |
| composite BB_LAY_MAU | ranh giới thật | 46 | 13 | 0.28 [0.17; 0.43] |
| composite cùng loại, ngoài BB_LAY_MAU | không phải ranh giới | 2 | 1 | 0.50 [0.09; 0.91] |
| composite cùng loại, ngoài BB_LAY_MAU | ranh giới thật | 7 | 3 | 0.43 [0.16; 0.75] |

Không báo AUC: Ollama trả logprob của phân phối KHÔNG ràng buộc theo schema (token đầu của câu trả lời không phải nhãn được chọn), nên cột `p_diff` trong CSV chỉ để tham khảo, KHÔNG dùng làm điểm.

## Phân tích từng ranh giới cùng loại ngoài `BB_LAY_MAU` (7 ranh giới, 6 tệp; không ghi định danh)

Nguồn: `results/pair_signals_dev.csv` (sinh bởi `boundary_table.py`). "Nền" = `model+merge` (c2 cross-fit, ngưỡng 0,7, gộp cùng loại trừ điểm >= 0,99). Cờ định danh chỉ là khớp/khác, không lưu giá trị.

| doc_id : trang | loại | đầu trang giống trang trước (jaccard token) | số hiệu đầu trang cả hai trang có / khác | điểm c2 | nền | quy tắc "bản khác" | VLM | ghi chú |
|---|---|---|---|---|---|---|---|---|
| `898572a6f361`:2 | BIEN_NHAN_THE_CHAP_PT | 0,92 | có / khác | 0,06 | sót | bắt | bắt | hai biên nhận cùng mẫu, khác số hiệu (OCR còn lẫn sai 1-2 ký tự) |
| `4ad1c01d6262`:2 | BIEN_NHAN_THE_CHAP_PT | 0,93 | có / khác | 0,06 | sót | bắt | bắt | như trên |
| `6c50528f7f4f`:2 | GCN_KIEM_DINH_DO_LUONG | 0,96 | có / khác | 0,91 | sót (gộp lại vì điểm < 0,99) | bắt | sót | mô hình đã nhận ra nhưng bước gộp cùng loại xóa ranh giới |
| `6c50528f7f4f`:3 | GCN_KIEM_DINH_DO_LUONG | 0,89 | có / khác | 0,92 | sót (gộp lại) | bắt | bắt | như trên |
| `83f88be6530c`:2 | BB_GIAO_NHAN_HANG_HOA | 0,60 | không có số hiệu | 0,96 | sót (gộp lại) | sót | sót | bản khác chỉ ở ngày/số lượng viết tay; mẫu không có "Số" |
| `72449aceeff3`:3 | CC_NGHIEP_VU_BVMT | 0,47 | không có | 0,02 | sót | sót | sót | trang 2 là trang tiêu đề ngắn (114 ký tự) của giấy trước, trang 3 là giấy của cơ sở đào tạo khác (mẫu khác hẳn); cần ngữ nghĩa, không phải so số |
| `36aff038b19e`:3 | HOA_DON | 0,03 | không có | 0,02 | sót | sót | sót | OCR hỏng nặng (chữ không đọc được), trang 2 và 4 trống (mặt sau) |

Tách theo nguyên nhân: 4/7 ranh giới có "cùng mẫu + số hiệu đầu trang khác" (3 tệp); mô hình cặp trang đã cho điểm cao (0,91-0,92) ở 2 trong 4 nhưng bước gộp cùng loại xóa chúng, và cho điểm thấp (0,06) ở 2 trường hợp còn lại. 1/7 (hóa đơn) không có định danh đọc được. 1/7 (giao nhận hàng) không có "Số" trên mẫu. 1/7 (chứng chỉ BVMT) hai giấy khác mẫu, nên chỉ nhìn được bằng ngữ nghĩa. Một tách nhầm ở nhóm này (`72449aceeff3`:4, trang tiêu đề `GIẤY CHỨNG NHẬN` chỉ 46 ký tự, điểm 0,93) tồn tại ở mọi biến thể: dấu hiệu "bản khác" không giải quyết nó.

**Dấu hiệu khác của một "bản khác" mà số đo không ủng hộ** (đếm trên cặp trang hiệu dụng, phạm vi dev; xem `results/pair_signals_dev.csv`):

| dấu hiệu | 7 ranh giới cùng loại ngoài BB | 46 ranh giới `BB_LAY_MAU` | 20 ranh giới khác loại | 448 cặp mẫu âm |
|---|---|---|---|---|
| tiêu đề ở đầu dòng trong 6 dòng đầu của trang sau | 3 | 41 | 10 | 77 |
| đánh số "trang 1/m" lặp lại ở trang sau | 0 | 0 | 3 | 2 |
| trang trước có "n/n" (trang cuối của tài liệu trước) | 0 | 0 | 6 | 1 |
| trang sau chỉ có chữ ký/con dấu ("mặt sau") | 0 | 0 | 0 | 0 |
| đầu trang giống trang trước (jaccard >= 0,5) | 5 | 41 | 0 | 29 |
| số hiệu đầu trang cả hai có và khác nhau | 4 | 0 | 1 | 36 |
| ngày đầu trang cả hai có và khác nhau | 0 | 1 | 2 | 48 |

Đọc bảng: (1) tiêu đề lặp ở đầu trang và ngày/số hiệu khác đều xảy ra nhiều ở mẫu âm (77 và 36-48 trên 448 cặp), nên **từng dấu hiệu riêng lẻ không đủ**, ví dụ "số hiệu khác" một mình có 36 lần ở mẫu âm. (2) Chỉ **tổ hợp "đầu trang giống (mẫu cùng) VÀ số hiệu khác"** tách sạch trong dev: 4/7 ranh giới cùng loại, 0/448 cặp mẫu âm, 0/46 `BB_LAY_MAU`, 0/20 khác loại. (3) Ở `BB_LAY_MAU` mọi cặp đều giống nhau về mẫu (41/46) nhưng "số hiệu" ở đầu trang là số mẫu biểu mẫu, giống nhau giữa các tờ (0/46 khác), vì vậy quy tắc không can thiệp (và không cần: loại một-tờ vốn không bị gộp). (4) Đánh số "trang 1/m" lặp lại không có ở bất kỳ ranh giới cùng loại nào trong kho này, và không có ranh giới nào là trang "chỉ chữ ký" (mặt sau): hai giả thuyết đó không có dữ liệu để kiểm.

## Phương pháp đã thử và kết luận

1. **Quy tắc "cùng mẫu, số hiệu khác" (`src/splitting/learned_id.py::same_template_new_copy`)**: hai trang không trống liền kề có jaccard token của 6 dòng đầu >= 0,7, cả hai có "Số/No ..." trong 12 dòng đầu (regex), hai giá trị (bỏ dấu câu) khác nhau. Dùng để **thêm ranh giới điểm 1,0** ở trang đó và chặn gộp lại theo loại (điểm >= 0,99). Không có tham số học. Trên dev: cùng loại ngoài BB **4/7 ranh giới** (nền 0/7), recall +0,571 [0,167; 0,889], exact-segment +0,500 [0,167; 0,833] (tách được); tách nhầm ở mẫu âm **không đổi** (9/501, 6/155 tệp, hiệu 0 với CI [0; 0]); khác loại và `BB_LAY_MAU` không đổi. Chỉ dùng nửa chặn gộp mà không thêm ranh giới: 2/7 (không tách được khỏi nền).
2. **Đặc trưng định danh trong bộ phân loại cặp trang (c2+id, 40 đặc trưng, cross-fit 5 fold như thí nghiệm 04)**: cùng loại ngoài BB 1/7 (không tách được khỏi nền 0/7: hiệu recall +0,143 [0; 0,333]); mẫu âm 7/501 so với 9/501 (không tách được); `BB_LAY_MAU` 42/46 so với 40/46 (không tách được). Mô hình **không học được** quy tắc trên từ dữ liệu huấn luyện: cặp dương "cùng loại, cùng mẫu" thật gần như không có (chỉ 7 ranh giới cùng loại ngoài BB trong cả dev, và mỗi fold còn ít hơn), còn cặp đường nối tổng hợp là hai trang lấy từ hai tệp khác nhau nên số hiệu khác "hiển nhiên" và không giống tình huống thật (OCR sai 1-2 ký tự trong cùng một tờ). Thêm quy tắc lên trên c2+id cho đúng như quy tắc đơn lẻ (4/7).
3. **VLM `qwen3.5:4b` nhìn hai ảnh trang liền kề** (`vlm_pairs.py`; 147 lời gọi, một lời gọi lỗi vì tệp PDF không mở được; độ trễ trung vị 2,8 s/cặp lúc GPU rảnh, lần đầu 37 s do nạp mô hình; ảnh render PyMuPDF trong bộ nhớ, 100 dpi, không ghi đĩa): nói "DIFFERENT_COPY" ở 3/7 ranh giới cùng loại ngoài BB, 3/20 khác loại, 13/46 `BB_LAY_MAU`, nhưng cũng nói như vậy ở **7/66 cặp mẫu âm có đầu trang giống** và 1/2 cặp không-ranh-giới cùng loại. Dùng nhãn VLM để thêm ranh giới cho 4/7 -> 3/7 ranh giới nhưng tách nhầm ở mẫu âm tăng từ 9 lên 16/501 (+1,40 điểm / 100 vị trí, CI [0,27; 2,45], tách được: **kém hơn**), số tệp có tách nhầm 6 -> 10/155. **Không dùng.** Lưu ý kỹ thuật: logprob Ollama trả về là của phân phối không ràng buộc theo schema, không phải của nhãn được chọn, nên không có điểm tin cậy đáng tin để đặt ngưỡng; chỉ nhãn cứng được dùng. Chỉ hỏi các cặp ứng viên (mọi cặp composite, và cặp mẫu âm có jaccard >= 0,4), nên 7 lần sai trên mẫu âm là cận dưới của số lần sai nếu hỏi mọi cặp.

## Độ nhạy theo ngưỡng "cùng mẫu" (`sensitivity.py`; mô tả, ngưỡng 0,7 chọn sau khi xem bảng này nên là chọn trên dev)

| jaccard tối thiểu | cùng loại ngoài BB: bắt / 7 (FP) | mẫu âm: tách nhầm / 501 | khác loại: bắt / 20 (FP) | BB_LAY_MAU: bắt / 46 (FP) |
|---|---|---|---|---|
| 0,3 | 4/7 (1) | 16 | 19/20 (0) | 40/46 (0) |
| 0,4 | 4/7 (1) | 12 | 19/20 (0) | 40/46 (0) |
| 0,5 | 4/7 (1) | 9 | 19/20 (0) | 40/46 (0) |
| 0,6 - 0,8 | 4/7 (1) | 9 | 19/20 (0) | 40/46 (0) |
| 0,9 | 3/7 (1) | 9 | 19/20 (0) | 40/46 (0) |

Dưới 0,5 quy tắc bắt đầu thêm tách nhầm ở mẫu âm (+3 ở 0,4; +7 ở 0,3); trên 0,8 mất ranh giới. Chọn 0,7 (giữa vùng bằng phẳng 0,5-0,8) để có lề an toàn ở phía tách nhầm.

## Giới hạn (đọc trước khi dùng con số)

- **Chỉ có 7 ranh giới / 6 tệp** cùng loại ngoài `BB_LAY_MAU` trong dev, và 4 ranh giới được bắt nằm ở **3 tệp** (hai biên nhận thế chấp và một giấy chứng nhận kiểm định ba bản). CI của bootstrap theo tệp trên 6 tệp rất rộng; "tách được" ở đây nghĩa là CI không chứa 0 trên n = 6, không phải bằng chứng tổng quát hóa.
- **Quy tắc được thiết kế sau khi đọc các tệp cùng loại của dev** (số hiệu khác + đầu trang giống là chính thứ nhìn thấy ở các ranh giới đó); ngưỡng 0,7 chọn sau khi xem độ nhạy. Số 4/7 là **trên chính dữ liệu đã dùng để nghĩ ra quy tắc**, không phải số giữ ngoài. Không có tệp cùng loại ngoài BB nào trong TEST (0 tệp: 21 / 36 / 0 / 0 / 2), nên không thể kiểm giữ ngoài; **TEST không được chạy cho thí nghiệm này**. Phần "không làm hại mẫu âm" thì mạnh hơn: 0 lần kích hoạt trên 448 cặp mẫu âm (155 tệp) ở mọi ngưỡng 0,5-0,9.
- Nhãn lát cắt của bước gộp lấy từ kết quả S10 đã chạy (không phân loại lại lát cắt mới); với ranh giới thêm mới, lát cắt nhận nhãn của đoạn S10 chứa nó. Mô phỏng tái lập đúng 174/174 tệp nhiều trang của S10 (0 lệch) nên nền là đúng `model+merge` đang chạy; nhưng với `model+merge+id` thật, phân loại lại các lát cắt mới có thể cho nhãn khác.
- Đáp án là `boundary_gold_v0` (máy, chưa người kiểm); hai trong sáu tệp cùng loại là `check_composite` (`36aff038b19e`, `72449aceeff3`), tức nhãn chính chúng chưa chắc.
- Quy tắc cần số hiệu đọc được: OCR hỏng (hóa đơn) hay mẫu không có "Số" (biên bản giao nhận hàng) thì không kích hoạt. 3/7 ranh giới còn lại cần bằng chứng khác (người xem, hoặc một mô hình nhìn ảnh mạnh hơn); thử VLM 4B không giúp.
- Chưa trả lời câu hỏi 14 (biên bản lấy mẫu: mỗi biên bản một bản ghi?). Kết quả `BB_LAY_MAU` không thay đổi: 40/46 như nền.
