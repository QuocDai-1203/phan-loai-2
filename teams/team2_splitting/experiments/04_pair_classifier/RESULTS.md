# 04 - Bộ phân loại cặp trang (c) - phạm vi `dev`

- **ngày chạy (UTC):** 2026-10-12 02:26
- **lệnh:** `.venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/04_pair_classifier/run.py`
- **đáp án:** `teams/team2_splitting/gold/boundary_gold_v0.csv` sha1[:10] = `d9a30b5896` (v0, máy, CHƯA người kiểm)
- **nhãn:** `data/labels_v2.csv` sha1[:10] = `eb3348713a`
- **văn bản:** `data/ocr_v2.jsonl` (OCR cục bộ, tối đa 30 trang/tài liệu) sha1[:10] = `ac87a66c25`
- **phạm vi:** **dev** = DEV + EXCLUDED_COMPOSITE (không có tài liệu TEST)
- **bootstrap:** 2000 lần lấy mẫu lại theo TỆP, seed 20260711, percentile 95%
- **máy:** Windows-11-10.0.26100-SP0, Python 3.13.14
- **mã đo:** `src/splitting/learned.py::fit_pair_model` (sha1[:10] `307193c424`), cross-fitting `teams/team2_splitting/cvlib.py` (5 fold theo nhóm biểu mẫu, seed 0, 5 bộ BSR cùng chuỗi loại gộp một nhóm)
- **huấn luyện:** mỗi fold: cặp thật của tài liệu dev ngoài fold + cặp đường nối của 400 composite tổng hợp (seed 100+fold) từ tài liệu đơn DEV ngoài fold; xác suất loại trang cho tầng cặp là OOF theo nhóm. Không dùng TEST. Số liệu trên composite thật là CROSS-VALIDATED (dev-like), KHÔNG phải tập TEST khóa; ngưỡng cố định 0,5 (không chỉnh trên số liệu này)
- **thời gian chạy:** 706 s toàn bộ CV (máy dùng chung, chỉ tham khảo)

## Kết quả trên composite THẬT, theo nhóm

Mỗi ô: điểm [CI 95% bootstrap theo tệp]. `boundary_confidence` của phương pháp này là điểm thô của bộ phân loại, chưa hiệu chỉnh.

**composite khác loại** (8 tệp, 26 vị trí, 20 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment (tệp nguyên vẹn) | tách nhầm / 100 vị trí | loại segment (cổng luật) |
|---|---|---|---|---|---|---|
| rule cũ (01) | 0.905 [0.778; 1.000] (19/21) | 0.950 [0.850; 1.000] (19/20) | 0.927 [0.850; 1.000] | 5/8 = 0.625 (Wilson 0.306; 0.863) | 7.69 [0.00; 14.29] (2) | 0.643 [0.500; 0.767] (oracle 0.679) |
| rule v2 (02) | 1.000 [1.000; 1.000] (19/19) | 0.950 [0.850; 1.000] (19/20) | 0.974 [0.919; 1.000] | 7/8 = 0.875 (Wilson 0.529; 0.978) | 0.00 [0.00; 0.00] (0) | 0.643 [0.500; 0.767] (oracle 0.679) |
| c1 hồi quy logistic | 1.000 [1.000; 1.000] (20/20) | 1.000 [1.000; 1.000] (20/20) | 1.000 [1.000; 1.000] | 8/8 = 1.000 (Wilson 0.676; 1.000) | 0.00 [0.00; 0.00] (0) | 0.679 [0.500; 0.786] (oracle 0.679) |
| c2 gradient boosting | 1.000 [1.000; 1.000] (20/20) | 1.000 [1.000; 1.000] (20/20) | 1.000 [1.000; 1.000] | 8/8 = 1.000 (Wilson 0.676; 1.000) | 0.00 [0.00; 0.00] (0) | 0.679 [0.500; 0.786] (oracle 0.679) |

**composite cùng loại, ngoài BB_LAY_MAU** (6 tệp, 11 vị trí, 7 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment (tệp nguyên vẹn) | tách nhầm / 100 vị trí | loại segment (cổng luật) |
|---|---|---|---|---|---|---|
| rule cũ (01) | 0.667 [0.333; 1.000] (4/6) | 0.571 [0.167; 0.889] (4/7) | 0.615 [0.222; 0.875] | 2/6 = 0.333 (Wilson 0.097; 0.700) | 18.18 [0.00; 42.90] (2) | 0.615 [0.250; 0.933] (oracle 0.615) |
| rule v2 (02) | 0.800 [0.500; 1.000] (4/5) | 0.571 [0.167; 0.889] (4/7) | 0.667 [0.250; 0.889] | 2/6 = 0.333 (Wilson 0.097; 0.700) | 9.09 [0.00; 21.45] (1) | 0.615 [0.250; 0.933] (oracle 0.615) |
| c1 hồi quy logistic | 0.500 [0.000; 1.000] (2/4) | 0.286 [0.000; 0.667] (2/7) | 0.364 [0.000; 0.800] | 1/6 = 0.167 (Wilson 0.030; 0.564) | 18.18 [0.00; 42.90] (2) | 0.615 [0.250; 0.933] (oracle 0.615) |
| c2 gradient boosting | 0.600 [0.000; 1.000] (3/5) | 0.429 [0.000; 0.778] (3/7) | 0.500 [0.000; 0.875] | 2/6 = 0.333 (Wilson 0.097; 0.700) | 18.18 [0.00; 42.90] (2) | 0.615 [0.250; 0.933] (oracle 0.615) |

**composite BB_LAY_MAU** (5 tệp, 46 vị trí, 46 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment (tệp nguyên vẹn) | tách nhầm / 100 vị trí | loại segment (cổng luật) |
|---|---|---|---|---|---|---|
| rule cũ (01) | 1.000 [1.000; 1.000] (46/46) | 1.000 [1.000; 1.000] (46/46) | 1.000 [1.000; 1.000] | 5/5 = 1.000 (Wilson 0.566; 1.000) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| rule v2 (02) | 1.000 [1.000; 1.000] (46/46) | 1.000 [1.000; 1.000] (46/46) | 1.000 [1.000; 1.000] | 5/5 = 1.000 (Wilson 0.566; 1.000) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| c1 hồi quy logistic | 1.000 [1.000; 1.000] (41/41) | 0.891 [0.545; 0.965] (41/46) | 0.943 [0.706; 0.982] | 2/5 = 0.400 (Wilson 0.118; 0.769) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| c2 gradient boosting | 1.000 [1.000; 1.000] (44/44) | 0.957 [0.625; 1.000] (44/46) | 0.978 [0.769; 1.000] | 4/5 = 0.800 (Wilson 0.376; 0.964) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |

**mẫu âm (nhiều trang, không composite)** (155 tệp, 501 vị trí, 0 ranh giới thật)

| phương pháp | tách nhầm / 100 vị trí | tệp có >= 1 tách nhầm | exact-segment (tệp nguyên vẹn) | loại segment (cổng luật) |
|---|---|---|---|---|
| rule cũ (01) | 46.71 [41.35; 52.80] (234/501) | 105/155 = 0.677 [0.606; 0.755] | 50/155 = 0.323 (Wilson 0.254; 0.400) | 0.768 [0.697; 0.832] (oracle 0.819) |
| rule v2 (02) | 30.14 [23.37; 36.44] (151/501) | 70/155 = 0.452 [0.374; 0.529] | 85/155 = 0.548 (Wilson 0.470; 0.625) | 0.748 [0.677; 0.813] (oracle 0.819) |
| c1 hồi quy logistic | 12.57 [9.64; 16.48] (63/501) | 48/155 = 0.310 [0.239; 0.387] | 107/155 = 0.690 (Wilson 0.614; 0.758) | 0.774 [0.710; 0.839] (oracle 0.819) |
| c2 gradient boosting | 9.58 [6.34; 12.73] (48/501) | 26/155 = 0.168 [0.110; 0.226] | 129/155 = 0.832 (Wilson 0.766; 0.883) | 0.794 [0.729; 0.858] (oracle 0.819) |

## So sánh ghép cặp trên composite thật

### c1 hồi quy logistic - rule cũ

| nhóm | chỉ số | c1 hồi quy logistic - rule cũ | CI 95% (bootstrap ghép cặp theo tệp) | kết luận |
|---|---|---|---|---|
| composite khác loại (n=8) | f1 | +0.073 | [+0.000; +0.150] | không tách được |
| composite khác loại (n=8) | recall | +0.050 | [+0.000; +0.150] | không tách được |
| composite khác loại (n=8) | precision | +0.095 | [+0.000; +0.222] | không tách được |
| composite khác loại (n=8) | exact_rate | +0.375 | [+0.000; +0.750] | không tách được |
| composite khác loại (n=8) | false_split_per100 | -7.692 | [-14.286; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | f1 | -0.252 | [-0.667; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | recall | -0.286 | [-0.667; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | precision | -0.167 | [-0.600; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | exact_rate | -0.167 | [-0.500; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | f1 | -0.057 | [-0.294; -0.018] | tách được: kém hơn |
| composite BB_LAY_MAU (n=5) | recall | -0.109 | [-0.455; -0.035] | tách được: kém hơn |
| composite BB_LAY_MAU (n=5) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | exact_rate | -0.600 | [-1.000; -0.200] | tách được: kém hơn |
| composite BB_LAY_MAU (n=5) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=155) | false_split_per100 | -34.132 | [-39.193; -29.262] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=155) | files_with_false_split | -0.368 | [-0.452; -0.284] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=155) | exact_rate | +0.368 | [+0.284; +0.452] | tách được: tốt hơn |

### c2 gradient boosting - rule cũ

| nhóm | chỉ số | c2 gradient boosting - rule cũ | CI 95% (bootstrap ghép cặp theo tệp) | kết luận |
|---|---|---|---|---|
| composite khác loại (n=8) | f1 | +0.073 | [+0.000; +0.150] | không tách được |
| composite khác loại (n=8) | recall | +0.050 | [+0.000; +0.150] | không tách được |
| composite khác loại (n=8) | precision | +0.095 | [+0.000; +0.222] | không tách được |
| composite khác loại (n=8) | exact_rate | +0.375 | [+0.000; +0.750] | không tách được |
| composite khác loại (n=8) | false_split_per100 | -7.692 | [-14.286; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | f1 | -0.115 | [-0.346; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | recall | -0.143 | [-0.500; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | precision | -0.067 | [-0.333; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | exact_rate | +0.000 | [+0.000; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | f1 | -0.022 | [-0.231; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | recall | -0.043 | [-0.375; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | exact_rate | -0.200 | [-0.600; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=155) | false_split_per100 | -37.126 | [-43.903; -32.000] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=155) | files_with_false_split | -0.510 | [-0.600; -0.426] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=155) | exact_rate | +0.510 | [+0.426; +0.600] | tách được: tốt hơn |

### c1 hồi quy logistic - rule v2

| nhóm | chỉ số | c1 hồi quy logistic - rule v2 | CI 95% (bootstrap ghép cặp theo tệp) | kết luận |
|---|---|---|---|---|
| composite khác loại (n=8) | f1 | +0.026 | [+0.000; +0.081] | không tách được |
| composite khác loại (n=8) | recall | +0.050 | [+0.000; +0.150] | không tách được |
| composite khác loại (n=8) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite khác loại (n=8) | exact_rate | +0.125 | [+0.000; +0.375] | không tách được |
| composite khác loại (n=8) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | f1 | -0.303 | [-0.668; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | recall | -0.286 | [-0.667; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | precision | -0.300 | [-0.750; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | exact_rate | -0.167 | [-0.500; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | false_split_per100 | +9.091 | [+0.000; +21.448] | không tách được |
| composite BB_LAY_MAU (n=5) | f1 | -0.057 | [-0.294; -0.018] | tách được: kém hơn |
| composite BB_LAY_MAU (n=5) | recall | -0.109 | [-0.455; -0.035] | tách được: kém hơn |
| composite BB_LAY_MAU (n=5) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | exact_rate | -0.600 | [-1.000; -0.200] | tách được: kém hơn |
| composite BB_LAY_MAU (n=5) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=155) | false_split_per100 | -17.565 | [-24.337; -10.268] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=155) | files_with_false_split | -0.142 | [-0.213; -0.077] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=155) | exact_rate | +0.142 | [+0.077; +0.213] | tách được: tốt hơn |

### c2 gradient boosting - rule v2

| nhóm | chỉ số | c2 gradient boosting - rule v2 | CI 95% (bootstrap ghép cặp theo tệp) | kết luận |
|---|---|---|---|---|
| composite khác loại (n=8) | f1 | +0.026 | [+0.000; +0.081] | không tách được |
| composite khác loại (n=8) | recall | +0.050 | [+0.000; +0.150] | không tách được |
| composite khác loại (n=8) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite khác loại (n=8) | exact_rate | +0.125 | [+0.000; +0.375] | không tách được |
| composite khác loại (n=8) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | f1 | -0.167 | [-0.462; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | recall | -0.143 | [-0.500; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | precision | -0.200 | [-0.500; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | exact_rate | +0.000 | [+0.000; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | false_split_per100 | +9.091 | [+0.000; +21.448] | không tách được |
| composite BB_LAY_MAU (n=5) | f1 | -0.022 | [-0.231; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | recall | -0.043 | [-0.375; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | exact_rate | -0.200 | [-0.600; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=155) | false_split_per100 | -20.559 | [-25.926; -15.520] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=155) | files_with_false_split | -0.284 | [-0.361; -0.206] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=155) | exact_rate | +0.284 | [+0.206; +0.361] | tách được: tốt hơn |

### c2 gradient boosting - c1 hồi quy logistic

| nhóm | chỉ số | c2 - c1 | CI 95% (bootstrap ghép cặp theo tệp) | kết luận |
|---|---|---|---|---|
| composite khác loại (n=8) | f1 | +0.000 | [+0.000; +0.000] | không tách được |
| composite khác loại (n=8) | recall | +0.000 | [+0.000; +0.000] | không tách được |
| composite khác loại (n=8) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite khác loại (n=8) | exact_rate | +0.000 | [+0.000; +0.000] | không tách được |
| composite khác loại (n=8) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | f1 | +0.136 | [+0.000; +0.500] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | recall | +0.143 | [+0.000; +0.500] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | precision | +0.100 | [+0.000; +0.500] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | exact_rate | +0.167 | [+0.000; +0.500] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | f1 | +0.035 | [+0.000; +0.096] | không tách được |
| composite BB_LAY_MAU (n=5) | recall | +0.065 | [+0.000; +0.143] | không tách được |
| composite BB_LAY_MAU (n=5) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | exact_rate | +0.400 | [+0.000; +0.800] | không tách được |
| composite BB_LAY_MAU (n=5) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=155) | false_split_per100 | -2.994 | [-8.501; +1.611] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=155) | files_with_false_split | -0.142 | [-0.213; -0.071] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=155) | exact_rate | +0.142 | [+0.071; +0.213] | tách được: tốt hơn |

## Độ nhạy theo ngưỡng (c2; mô tả, ngưỡng 0,5 là cấu hình chính, không chọn lại theo bảng này)


**composite khác loại** (8 tệp, 26 vị trí, 20 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment (tệp nguyên vẹn) | tách nhầm / 100 vị trí | loại segment (cổng luật) |
|---|---|---|---|---|---|---|
| c2 gradient boosting | 1.000 [1.000; 1.000] (20/20) | 1.000 [1.000; 1.000] (20/20) | 1.000 [1.000; 1.000] | 8/8 = 1.000 (Wilson 0.676; 1.000) | 0.00 [0.00; 0.00] (0) | 0.679 [0.500; 0.786] (oracle 0.679) |
| c2 gradient boosting @0.3 | 1.000 [1.000; 1.000] (20/20) | 1.000 [1.000; 1.000] (20/20) | 1.000 [1.000; 1.000] | 8/8 = 1.000 (Wilson 0.676; 1.000) | 0.00 [0.00; 0.00] (0) | 0.679 [0.500; 0.786] (oracle 0.679) |
| c2 gradient boosting @0.7 | 1.000 [1.000; 1.000] (20/20) | 1.000 [1.000; 1.000] (20/20) | 1.000 [1.000; 1.000] | 8/8 = 1.000 (Wilson 0.676; 1.000) | 0.00 [0.00; 0.00] (0) | 0.679 [0.500; 0.786] (oracle 0.679) |
| c2 gradient boosting @0.9 | 1.000 [1.000; 1.000] (19/19) | 0.950 [0.812; 1.000] (19/20) | 0.974 [0.897; 1.000] | 7/8 = 0.875 (Wilson 0.529; 0.978) | 0.00 [0.00; 0.00] (0) | 0.679 [0.500; 0.786] (oracle 0.679) |

**composite cùng loại, ngoài BB_LAY_MAU** (6 tệp, 11 vị trí, 7 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment (tệp nguyên vẹn) | tách nhầm / 100 vị trí | loại segment (cổng luật) |
|---|---|---|---|---|---|---|
| c2 gradient boosting | 0.600 [0.000; 1.000] (3/5) | 0.429 [0.000; 0.778] (3/7) | 0.500 [0.000; 0.875] | 2/6 = 0.333 (Wilson 0.097; 0.700) | 18.18 [0.00; 42.90] (2) | 0.615 [0.250; 0.933] (oracle 0.615) |
| c2 gradient boosting @0.3 | 0.600 [0.000; 1.000] (3/5) | 0.429 [0.000; 0.778] (3/7) | 0.500 [0.000; 0.875] | 2/6 = 0.333 (Wilson 0.097; 0.700) | 18.18 [0.00; 42.90] (2) | 0.615 [0.250; 0.933] (oracle 0.615) |
| c2 gradient boosting @0.7 | 0.600 [0.000; 1.000] (3/5) | 0.429 [0.000; 0.778] (3/7) | 0.500 [0.000; 0.875] | 2/6 = 0.333 (Wilson 0.097; 0.700) | 18.18 [0.00; 42.90] (2) | 0.615 [0.250; 0.933] (oracle 0.615) |
| c2 gradient boosting @0.9 | 0.600 [0.000; 1.000] (3/5) | 0.429 [0.000; 0.778] (3/7) | 0.500 [0.000; 0.875] | 2/6 = 0.333 (Wilson 0.097; 0.700) | 18.18 [0.00; 42.90] (2) | 0.615 [0.250; 0.933] (oracle 0.615) |

**composite BB_LAY_MAU** (5 tệp, 46 vị trí, 46 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment (tệp nguyên vẹn) | tách nhầm / 100 vị trí | loại segment (cổng luật) |
|---|---|---|---|---|---|---|
| c2 gradient boosting | 1.000 [1.000; 1.000] (44/44) | 0.957 [0.625; 1.000] (44/46) | 0.978 [0.769; 1.000] | 4/5 = 0.800 (Wilson 0.376; 0.964) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| c2 gradient boosting @0.3 | 1.000 [1.000; 1.000] (44/44) | 0.957 [0.625; 1.000] (44/46) | 0.978 [0.769; 1.000] | 4/5 = 0.800 (Wilson 0.376; 0.964) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| c2 gradient boosting @0.7 | 1.000 [1.000; 1.000] (40/40) | 0.870 [0.625; 1.000] (40/46) | 0.930 [0.769; 1.000] | 3/5 = 0.600 (Wilson 0.231; 0.882) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| c2 gradient boosting @0.9 | 1.000 [1.000; 1.000] (12/12) | 0.261 [0.059; 0.700] (12/46) | 0.414 [0.111; 0.824] | 0/5 = 0.000 (Wilson 0.000; 0.434) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |

**mẫu âm (nhiều trang, không composite)** (155 tệp, 501 vị trí, 0 ranh giới thật)

| phương pháp | tách nhầm / 100 vị trí | tệp có >= 1 tách nhầm | exact-segment (tệp nguyên vẹn) | loại segment (cổng luật) |
|---|---|---|---|---|
| c2 gradient boosting | 9.58 [6.34; 12.73] (48/501) | 26/155 = 0.168 [0.110; 0.226] | 129/155 = 0.832 (Wilson 0.766; 0.883) | 0.794 [0.729; 0.858] (oracle 0.819) |
| c2 gradient boosting @0.3 | 17.17 [12.53; 21.79] (86/501) | 40/155 = 0.258 [0.187; 0.329] | 115/155 = 0.742 (Wilson 0.668; 0.804) | 0.768 [0.697; 0.832] (oracle 0.819) |
| c2 gradient boosting @0.7 | 5.19 [2.91; 7.71] (26/501) | 16/155 = 0.103 [0.058; 0.155] | 139/155 = 0.897 (Wilson 0.839; 0.935) | 0.800 [0.735; 0.865] (oracle 0.819) |
| c2 gradient boosting @0.9 | 2.20 [0.94; 3.76] (11/501) | 10/155 = 0.065 [0.032; 0.103] | 145/155 = 0.935 (Wilson 0.885; 0.965) | 0.813 [0.748; 0.871] (oracle 0.819) |

## Trên composite TỔNG HỢP (giữ lại theo fold)

400 composite; seed đánh giá `1000+fold`. Ranh giới tổng hợp thường dễ hơn thật.

**syn_bundle** (60 composite tổng hợp, 60 vị trí, 60 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment | tách nhầm / 100 vị trí |
|---|---|---|---|---|---|
| rule cũ | 1.000 [1.000; 1.000] | 1.000 [1.000; 1.000] | 1.000 [1.000; 1.000] | 60/60 = 1.000 | 0.00 [0.00; 0.00] |
| rule v2 | 1.000 [1.000; 1.000] | 1.000 [1.000; 1.000] | 1.000 [1.000; 1.000] | 60/60 = 1.000 | 0.00 [0.00; 0.00] |
| c1 hồi quy logistic | 1.000 [1.000; 1.000] | 1.000 [1.000; 1.000] | 1.000 [1.000; 1.000] | 60/60 = 1.000 | 0.00 [0.00; 0.00] |
| c2 gradient boosting | 1.000 [1.000; 1.000] | 1.000 [1.000; 1.000] | 1.000 [1.000; 1.000] | 60/60 = 1.000 | 0.00 [0.00; 0.00] |

**syn_contract** (56 composite tổng hợp, 233 vị trí, 56 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment | tách nhầm / 100 vị trí |
|---|---|---|---|---|---|
| rule cũ | 0.458 [0.404; 0.524] | 0.982 [0.929; 1.000] | 0.625 [0.571; 0.683] | 17/56 = 0.304 | 27.90 [23.26; 32.30] |
| rule v2 | 0.628 [0.545; 0.724] | 0.964 [0.911; 1.000] | 0.761 [0.687; 0.831] | 34/56 = 0.607 | 13.73 [9.76; 17.37] |
| c1 hồi quy logistic | 0.700 [0.602; 0.812] | 1.000 [1.000; 1.000] | 0.824 [0.752; 0.896] | 41/56 = 0.732 | 10.30 [5.91; 15.33] |
| c2 gradient boosting | 0.800 [0.718; 0.889] | 1.000 [1.000; 1.000] | 0.889 [0.836; 0.941] | 44/56 = 0.786 | 6.01 [3.20; 9.21] |

**syn_mixed** (146 composite tổng hợp, 1026 vị trí, 365 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment | tách nhầm / 100 vị trí |
|---|---|---|---|---|---|
| rule cũ | 0.534 [0.506; 0.562] | 0.915 [0.888; 0.942] | 0.674 [0.650; 0.699] | 14/146 = 0.096 | 28.46 [26.30; 30.45] |
| rule v2 | 0.625 [0.593; 0.659] | 0.910 [0.882; 0.937] | 0.741 [0.716; 0.767] | 30/146 = 0.205 | 19.40 [17.35; 21.31] |
| c1 hồi quy logistic | 0.784 [0.744; 0.825] | 0.945 [0.921; 0.968] | 0.857 [0.828; 0.885] | 79/146 = 0.541 | 9.26 [7.30; 11.41] |
| c2 gradient boosting | 0.843 [0.812; 0.875] | 0.956 [0.936; 0.975] | 0.896 [0.876; 0.917] | 86/146 = 0.589 | 6.34 [5.00; 7.72] |

**syn_same_type** (138 composite tổng hợp, 806 vị trí, 299 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment | tách nhầm / 100 vị trí |
|---|---|---|---|---|---|
| rule cũ | 0.490 [0.447; 0.537] | 0.936 [0.899; 0.967] | 0.643 [0.602; 0.686] | 40/138 = 0.290 | 36.23 [31.83; 40.48] |
| rule v2 | 0.608 [0.548; 0.671] | 0.933 [0.894; 0.965] | 0.736 [0.686; 0.785] | 54/138 = 0.391 | 22.33 [18.01; 26.87] |
| c1 hồi quy logistic | 0.754 [0.691; 0.819] | 0.759 [0.694; 0.818] | 0.757 [0.705; 0.806] | 65/138 = 0.471 | 9.18 [6.53; 12.24] |
| c2 gradient boosting | 0.850 [0.801; 0.897] | 0.722 [0.655; 0.789] | 0.781 [0.730; 0.830] | 65/138 = 0.471 | 4.71 [3.25; 6.26] |

## Phân tích lỗi (c2, 5 kiểu đông nhất)

| # | loại lỗi | nhóm | lý do (dấu hiệu trên trang) | loại trang | số lần | ví dụ (doc_id:trang) |
|---|---|---|---|---|---|---|
| 1 | tách nhầm (FP) | negative | quốc hiệu ở đầu trang | HO_SO_QUAN_LY_PCCC | 18 | 498cd5744268:3, 498cd5744268:5, 498cd5744268:6 |
| 2 | tách nhầm (FP) | negative | quốc hiệu ở đầu trang, tiêu đề đầu dòng 'BIÊN BẢN' | HO_SO_QUAN_LY_PCCC | 10 | 1983c7d32e67:29, 297c0d94ec78:30, 498cd5744268:27 |
| 3 | tách nhầm (FP) | negative | không có dấu hiệu luật | HD_NHUONG_QUYEN_DAI_LY | 3 | bfbfb743b8d5:10, 08256d7db7e0:10, 8db9cca49a9d:10 |
| 4 | sót ranh giới (FN) | same_bb | quốc hiệu ở đầu trang | BB_LAY_MAU | 2 | 0cf9aa186387:2, 0cf9aa186387:3 |
| 5 | tách nhầm (FP) | negative | quốc hiệu ở đầu trang, tiêu đề đầu dòng 'GIẤY XÁC NHẬN' | GCN_DKDN | 2 | e8e079283949:2, a8d26371c344:3 |

(tổng: 50 tách nhầm, 6 sót; 23 kiểu lỗi khác nhau; bảng liệt kê 5 kiểu đông nhất)

## Cách đọc kết quả (nhận xét của người viết, mọi số lấy từ các bảng trên)

1. **Phương pháp tốt nhất đã đo là c2 (gradient boosting trên cặp trang)**, và cái được là ở MẪU ÂM: tách nhầm 9,58 / 100 vị trí [6,34; 12,73] (48/501), 26/155 tệp có ít nhất một lần tách nhầm, 129/155 tệp nguyên vẹn. So với rule v2: -20,6 [-25,9; -15,5] điểm (tách được: tốt hơn); so với rule cũ: -37,1 [-43,9; -32,0] (tách được: tốt hơn). Đây là số đo gần nhất với "nhân viên nạp một tệp bình thường nhiều trang, hệ thống có cắt vụn không".
2. **Trên ba nhóm composite, c2 KHÔNG tách được khỏi rule v2 hay rule cũ** (mọi CI ghép cặp chứa 0): composite khác loại 20/20 ranh giới, 0 tách nhầm, 8/8 tệp nguyên vẹn (rule v2: 19/20, 7/8); `BB_LAY_MAU` 44/46 (rule v2: 46/46), 4/5 tệp nguyên vẹn; nhóm cùng loại ngoài `BB_LAY_MAU` 3/7 ranh giới và 2 tách nhầm (rule v2: 4/7 và 1). Cỡ mẫu (8 / 6 / 5 tệp, 20 / 7 / 46 ranh giới) không đủ để nói c2 tốt hơn hay kém hơn ở đó. Riêng điều này đáng ghi: c2 đạt 20/20 ở composite khác loại **khi cả 5 bộ chứng từ BSR cùng chuỗi loại bị giữ ra ngoài huấn luyện** (cùng điều kiện mà b0 ở thí nghiệm 03 chỉ đạt 13/20), nhưng sự khác biệt c2 so với rule v2 ở đó (+0,026 F1) cũng không tách được.
3. **c2 so với c1 (hồi quy logistic):** số tệp mẫu âm có tách nhầm giảm 14,2 điểm phần trăm [-21,3; -7,1] (tách được), còn tách nhầm trên 100 vị trí chênh -3,0 [-8,5; +1,6] (không tách được); các nhóm composite không tách được. Nên chọn c2 theo thứ tự "tách được ở số tệp có lỗi" chứ không phải vì thắng áp đảo.
4. **Ngưỡng 0,5 được đặt trước và không chỉnh.** Bảng độ nhạy cho thấy đánh đổi rõ: ngưỡng 0,7 giảm tách nhầm mẫu âm xuống 5,19 / 100 (26/501) giữ 20/20 ở composite khác loại nhưng `BB_LAY_MAU` còn 40/46 (recall 0,870); ngưỡng 0,9 giảm xuống 2,20 / 100 nhưng chỉ còn 12/46 ở `BB_LAY_MAU`. Đây là quyết định vận hành (sai theo hướng nào đắt hơn: cắt vụn hay dính hai giấy?), nên cần doanh nghiệp trả lời câu hỏi 1-3 của README trước khi chốt; bảng này không phải bằng chứng để chọn lại ngưỡng vì đọc trên cùng dữ liệu dev.
5. **Lỗi còn lại của c2** (bảng 5 kiểu): 28/48 tách nhầm vẫn nằm ở tập hồ sơ PCCC (`HO_SO_QUAN_LY_PCCC`); 20 tách nhầm còn lại rải ở nhiều loại (trong đó 3 ở `HD_NHUONG_QUYEN_DAI_LY` trang 10 của 3 tệp cùng mẫu, 2 ở `GCN_DKDN`). Hai ranh giới `BB_LAY_MAU` sót đều ở tệp 3 trang `0cf9aa186387` (trang 2 và 3), và nhóm cùng loại vẫn sót những cặp giấy gần giống hệt nhau (hai biên nhận thế chấp, một hóa đơn): c2 cũng chưa học được "bản khác" khi hai trang giống nhau về chữ.
6. **Trên composite tổng hợp** (cùng bảng): c2 vượt c1, rule v2 và rule cũ ở cả `syn_contract`, `syn_mixed`, `syn_same_type` về F1 và về tách nhầm (ví dụ `syn_mixed` F1 0,896 [0,876; 0,917] so với rule v2 0,741 [0,716; 0,767]); recall của c2 ở `syn_same_type` (0,722) thấp hơn rule v2 (0,933) đổi lấy tách nhầm 4,7 so với 22,3 / 100. Thứ tự giữa các phương pháp trên dữ liệu tổng hợp trùng với thứ tự trên mẫu âm thật, nhưng quần thể không giống nhau nên **không so trực tiếp giá trị tuyệt đối** giữa "tổng hợp" và "thật": tổng hợp ghép các trang từ lần quét độc lập (dễ hơn), mặt khác chỉ dùng 1-6 tài liệu/composite và không có `CHUNG_THU_CHAT_LUONG`.

### Giới hạn

- Số trên composite thật là **cross-validated (5 fold theo nhóm, seed 0, 5 bộ BSR cùng chuỗi loại gộp một nhóm)**, KHÔNG phải tập TEST khóa; không thử nhiều seed chia fold. Với 145 ranh giới thật (27 ngoài `BB_LAY_MAU`) và chỉ 21 composite, không thể có tập giữ ngoài riêng.
- `fit_pair_model` huấn luyện bằng cặp thật của tài liệu dev ngoài fold (khoảng 60 ranh giới dương thật, vì cả phạm vi dev chỉ có 73) cộng 684-854 cặp đường nối tổng hợp mỗi fold; ngưỡng, siêu tham số (độ sâu 3, 150 vòng, tốc độ 0,08) và danh sách 30 đặc trưng được đặt một lần, không tối ưu trên bảng kết quả này. Chưa chạy ablation đặc trưng.
- Đáp án là `boundary_gold_v0` (chưa người kiểm). Điểm `boundary_confidence` của lát cắt là điểm thô của bộ phân loại; chưa đo ECE nên KHÔNG được dùng nó như xác suất.
- Chỉ có một nhà cung cấp cho bộ chứng từ xuất kho (bẫy 7 của README); xem `RESULTS_family_sensitivity.md` cho độ nhạy khi các bộ BSR không bị gộp thành một nhóm (đo mức "nhớ bố cục").
