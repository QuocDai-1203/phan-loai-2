# 04 - Bộ phân loại cặp trang (c) - phạm vi `all`

- **ngày chạy (UTC):** 2026-10-12 02:12
- **lệnh:** `.venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/04_pair_classifier/run.py --scope all --final-test`
- **đáp án:** `teams/team2_splitting/gold/boundary_gold_v0.csv` sha1[:10] = `d9a30b5896` (v0, máy, CHƯA người kiểm)
- **nhãn:** `data/labels_v2.csv` sha1[:10] = `eb3348713a`
- **văn bản:** `data/ocr_v2.jsonl` (OCR cục bộ, tối đa 30 trang/tài liệu) sha1[:10] = `ac87a66c25`
- **phạm vi:** **all** = cả tài liệu TEST, chấm MỘT lần với cấu hình đã đóng băng
- **bootstrap:** 2000 lần lấy mẫu lại theo TỆP, seed 20260711, percentile 95%
- **máy:** Windows-11-10.0.26100-SP0, Python 3.13.14
- **mã đo:** `src/splitting/learned.py::fit_pair_model` (sha1[:10] `307193c424`), cross-fitting `teams/team2_splitting/cvlib.py` (5 fold theo nhóm biểu mẫu, seed 0, 5 bộ BSR cùng chuỗi loại gộp một nhóm)
- **huấn luyện:** mỗi fold: cặp thật của tài liệu dev ngoài fold + cặp đường nối của 400 composite tổng hợp (seed 100+fold) từ tài liệu đơn DEV ngoài fold; xác suất loại trang cho tầng cặp là OOF theo nhóm. Không dùng TEST. Số liệu trên composite thật là CROSS-VALIDATED (dev-like), KHÔNG phải tập TEST khóa; ngưỡng cố định 0,5 (không chỉnh trên số liệu này)
- **thời gian chạy:** 886 s toàn bộ CV (máy dùng chung, chỉ tham khảo)

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

**composite BB_LAY_MAU** (7 tệp, 55 vị trí, 55 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment (tệp nguyên vẹn) | tách nhầm / 100 vị trí | loại segment (cổng luật) |
|---|---|---|---|---|---|---|
| rule cũ (01) | 1.000 [1.000; 1.000] (55/55) | 1.000 [1.000; 1.000] (55/55) | 1.000 [1.000; 1.000] | 7/7 = 1.000 (Wilson 0.646; 1.000) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| rule v2 (02) | 1.000 [1.000; 1.000] (55/55) | 1.000 [1.000; 1.000] (55/55) | 1.000 [1.000; 1.000] | 7/7 = 1.000 (Wilson 0.646; 1.000) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| c1 hồi quy logistic | 1.000 [1.000; 1.000] (44/44) | 0.800 [0.400; 0.931] (44/55) | 0.889 [0.571; 0.964] | 2/7 = 0.286 (Wilson 0.082; 0.641) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| c2 gradient boosting | 1.000 [1.000; 1.000] (53/53) | 0.964 [0.760; 1.000] (53/55) | 0.981 [0.864; 1.000] | 6/7 = 0.857 (Wilson 0.487; 0.974) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |

**mẫu âm (nhiều trang, không composite)** (191 tệp, 575 vị trí, 0 ranh giới thật)

| phương pháp | tách nhầm / 100 vị trí | tệp có >= 1 tách nhầm | exact-segment (tệp nguyên vẹn) | loại segment (cổng luật) |
|---|---|---|---|---|
| rule cũ (01) | 48.00 [42.63; 53.99] (276/575) | 125/191 = 0.654 [0.586; 0.717] | 66/191 = 0.346 (Wilson 0.282; 0.415) | 0.764 [0.707; 0.822] (oracle 0.817) |
| rule v2 (02) | 30.26 [23.80; 36.20] (174/575) | 80/191 = 0.419 [0.356; 0.492] | 111/191 = 0.581 (Wilson 0.510; 0.649) | 0.754 [0.696; 0.812] (oracle 0.817) |
| c1 hồi quy logistic | 11.30 [8.59; 14.59] (65/575) | 50/191 = 0.262 [0.204; 0.325] | 141/191 = 0.738 (Wilson 0.672; 0.795) | 0.770 [0.712; 0.822] (oracle 0.817) |
| c2 gradient boosting | 9.22 [6.36; 12.13] (53/575) | 31/191 = 0.162 [0.110; 0.215] | 160/191 = 0.838 (Wilson 0.779; 0.883) | 0.791 [0.733; 0.848] (oracle 0.817) |

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
| composite BB_LAY_MAU (n=7) | f1 | -0.111 | [-0.429; -0.036] | tách được: kém hơn |
| composite BB_LAY_MAU (n=7) | recall | -0.200 | [-0.600; -0.069] | tách được: kém hơn |
| composite BB_LAY_MAU (n=7) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=7) | exact_rate | -0.714 | [-1.000; -0.429] | tách được: kém hơn |
| composite BB_LAY_MAU (n=7) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=191) | false_split_per100 | -36.696 | [-41.798; -31.767] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=191) | files_with_false_split | -0.393 | [-0.466; -0.319] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=191) | exact_rate | +0.393 | [+0.319; +0.466] | tách được: tốt hơn |

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
| composite BB_LAY_MAU (n=7) | f1 | -0.019 | [-0.136; +0.000] | không tách được |
| composite BB_LAY_MAU (n=7) | recall | -0.036 | [-0.240; +0.000] | không tách được |
| composite BB_LAY_MAU (n=7) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=7) | exact_rate | -0.143 | [-0.429; +0.000] | không tách được |
| composite BB_LAY_MAU (n=7) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=191) | false_split_per100 | -38.783 | [-45.285; -33.477] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=191) | files_with_false_split | -0.492 | [-0.571; -0.414] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=191) | exact_rate | +0.492 | [+0.414; +0.571] | tách được: tốt hơn |

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
| composite BB_LAY_MAU (n=7) | f1 | -0.111 | [-0.429; -0.036] | tách được: kém hơn |
| composite BB_LAY_MAU (n=7) | recall | -0.200 | [-0.600; -0.069] | tách được: kém hơn |
| composite BB_LAY_MAU (n=7) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=7) | exact_rate | -0.714 | [-1.000; -0.429] | tách được: kém hơn |
| composite BB_LAY_MAU (n=7) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=191) | false_split_per100 | -18.957 | [-25.404; -11.627] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=191) | files_with_false_split | -0.157 | [-0.220; -0.094] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=191) | exact_rate | +0.157 | [+0.094; +0.220] | tách được: tốt hơn |

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
| composite BB_LAY_MAU (n=7) | f1 | -0.019 | [-0.136; +0.000] | không tách được |
| composite BB_LAY_MAU (n=7) | recall | -0.036 | [-0.240; +0.000] | không tách được |
| composite BB_LAY_MAU (n=7) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=7) | exact_rate | -0.143 | [-0.429; +0.000] | không tách được |
| composite BB_LAY_MAU (n=7) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=191) | false_split_per100 | -21.043 | [-26.580; -15.771] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=191) | files_with_false_split | -0.257 | [-0.330; -0.188] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=191) | exact_rate | +0.257 | [+0.188; +0.330] | tách được: tốt hơn |

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
| composite BB_LAY_MAU (n=7) | f1 | +0.093 | [+0.026; +0.362] | tách được: tốt hơn |
| composite BB_LAY_MAU (n=7) | recall | +0.164 | [+0.049; +0.500] | tách được: tốt hơn |
| composite BB_LAY_MAU (n=7) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=7) | exact_rate | +0.571 | [+0.143; +0.857] | tách được: tốt hơn |
| composite BB_LAY_MAU (n=7) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=191) | false_split_per100 | -2.087 | [-6.478; +2.019] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=191) | files_with_false_split | -0.099 | [-0.162; -0.031] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=191) | exact_rate | +0.099 | [+0.031; +0.162] | tách được: tốt hơn |

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

**composite BB_LAY_MAU** (7 tệp, 55 vị trí, 55 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment (tệp nguyên vẹn) | tách nhầm / 100 vị trí | loại segment (cổng luật) |
|---|---|---|---|---|---|---|
| c2 gradient boosting | 1.000 [1.000; 1.000] (53/53) | 0.964 [0.760; 1.000] (53/55) | 0.981 [0.864; 1.000] | 6/7 = 0.857 (Wilson 0.487; 0.974) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| c2 gradient boosting @0.3 | 1.000 [1.000; 1.000] (53/53) | 0.964 [0.760; 1.000] (53/55) | 0.981 [0.864; 1.000] | 6/7 = 0.857 (Wilson 0.487; 0.974) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| c2 gradient boosting @0.7 | 1.000 [1.000; 1.000] (49/49) | 0.891 [0.757; 1.000] (49/55) | 0.942 [0.862; 1.000] | 5/7 = 0.714 (Wilson 0.359; 0.918) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| c2 gradient boosting @0.9 | 1.000 [1.000; 1.000] (21/21) | 0.382 [0.116; 0.854] (21/55) | 0.553 [0.208; 0.921] | 2/7 = 0.286 (Wilson 0.082; 0.641) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |

**mẫu âm (nhiều trang, không composite)** (191 tệp, 575 vị trí, 0 ranh giới thật)

| phương pháp | tách nhầm / 100 vị trí | tệp có >= 1 tách nhầm | exact-segment (tệp nguyên vẹn) | loại segment (cổng luật) |
|---|---|---|---|---|
| c2 gradient boosting | 9.22 [6.36; 12.13] (53/575) | 31/191 = 0.162 [0.110; 0.215] | 160/191 = 0.838 (Wilson 0.779; 0.883) | 0.791 [0.733; 0.848] (oracle 0.817) |
| c2 gradient boosting @0.3 | 16.00 [11.70; 20.16] (92/575) | 45/191 = 0.236 [0.178; 0.293] | 146/191 = 0.764 (Wilson 0.699; 0.819) | 0.770 [0.712; 0.822] (oracle 0.817) |
| c2 gradient boosting @0.7 | 5.04 [2.91; 7.23] (29/575) | 19/191 = 0.099 [0.058; 0.141] | 172/191 = 0.901 (Wilson 0.850; 0.935) | 0.796 [0.738; 0.848] (oracle 0.817) |
| c2 gradient boosting @0.9 | 2.26 [1.12; 3.73] (13/575) | 12/191 = 0.063 [0.031; 0.099] | 179/191 = 0.937 (Wilson 0.893; 0.964) | 0.806 [0.749; 0.859] (oracle 0.817) |

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
| 1 | tách nhầm (FP) | negative | quốc hiệu ở đầu trang | HO_SO_QUAN_LY_PCCC | 19 | 498cd5744268:3, 498cd5744268:5, 498cd5744268:6 |
| 2 | tách nhầm (FP) | negative | quốc hiệu ở đầu trang, tiêu đề đầu dòng 'BIÊN BẢN' | HO_SO_QUAN_LY_PCCC | 10 | 1983c7d32e67:29, 297c0d94ec78:30, 498cd5744268:27 |
| 3 | tách nhầm (FP) | negative | không có dấu hiệu luật | HD_NHUONG_QUYEN_DAI_LY | 3 | bfbfb743b8d5:10, 08256d7db7e0:10, 8db9cca49a9d:10 |
| 4 | sót ranh giới (FN) | same_bb | quốc hiệu ở đầu trang | BB_LAY_MAU | 2 | 0cf9aa186387:2, 0cf9aa186387:3 |
| 5 | tách nhầm (FP) | negative | quốc hiệu ở đầu trang, tiêu đề đầu dòng 'GIẤY XÁC NHẬN' | GCN_DKDN | 2 | e8e079283949:2, a8d26371c344:3 |

(tổng: 55 tách nhầm, 6 sót; 26 kiểu lỗi khác nhau; bảng liệt kê 5 kiểu đông nhất)
