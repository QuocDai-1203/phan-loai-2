# 04 - Độ nhạy: không gộp bộ BSR thành một nhóm - phạm vi `dev`

- **ngày chạy (UTC):** 2026-10-12 02:11
- **lệnh:** `.venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/04_pair_classifier/run.py --no-family-merge`
- **đáp án:** `teams/team2_splitting/gold/boundary_gold_v0.csv` sha1[:10] = `d9a30b5896` (v0, máy, CHƯA người kiểm)
- **nhãn:** `data/labels_v2.csv` sha1[:10] = `eb3348713a`
- **văn bản:** `data/ocr_v2.jsonl` (OCR cục bộ, tối đa 30 trang/tài liệu) sha1[:10] = `ac87a66c25`
- **phạm vi:** **dev** = DEV + EXCLUDED_COMPOSITE (không có tài liệu TEST)
- **bootstrap:** 2000 lần lấy mẫu lại theo TỆP, seed 20260711, percentile 95%
- **máy:** Windows-11-10.0.26100-SP0, Python 3.13.14
- **mã đo:** `src/splitting/learned.py::fit_pair_model` (sha1[:10] `307193c424`), cross-fitting `teams/team2_splitting/cvlib.py` (5 fold theo nhóm biểu mẫu, seed 0, KHÔNG gộp bộ BSR)
- **huấn luyện:** mỗi fold: cặp thật của tài liệu dev ngoài fold + cặp đường nối của 400 composite tổng hợp (seed 100+fold) từ tài liệu đơn DEV ngoài fold; xác suất loại trang cho tầng cặp là OOF theo nhóm. Không dùng TEST. Số liệu trên composite thật là CROSS-VALIDATED (dev-like), KHÔNG phải tập TEST khóa; ngưỡng cố định 0,5 (không chỉnh trên số liệu này)
- **thời gian chạy:** 936 s toàn bộ CV (máy dùng chung, chỉ tham khảo)

Ở chế độ này, một bộ chứng từ BSR bị giữ lại có thể có bộ BSR khác (cùng nhà cung cấp, cùng bố cục) trong tập huấn luyện: đo mức 'nhớ bố cục' (bẫy 7 của README).


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
| c1 hồi quy logistic | 0.667 [0.333; 1.000] (4/6) | 0.571 [0.167; 0.889] (4/7) | 0.615 [0.222; 0.875] | 2/6 = 0.333 (Wilson 0.097; 0.700) | 18.18 [0.00; 42.90] (2) | 0.615 [0.250; 0.933] (oracle 0.615) |
| c2 gradient boosting | 0.667 [0.333; 1.000] (4/6) | 0.571 [0.167; 0.889] (4/7) | 0.615 [0.222; 0.875] | 2/6 = 0.333 (Wilson 0.097; 0.700) | 18.18 [0.00; 42.90] (2) | 0.615 [0.250; 0.933] (oracle 0.615) |

**composite BB_LAY_MAU** (5 tệp, 46 vị trí, 46 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment (tệp nguyên vẹn) | tách nhầm / 100 vị trí | loại segment (cổng luật) |
|---|---|---|---|---|---|---|
| rule cũ (01) | 1.000 [1.000; 1.000] (46/46) | 1.000 [1.000; 1.000] (46/46) | 1.000 [1.000; 1.000] | 5/5 = 1.000 (Wilson 0.566; 1.000) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| rule v2 (02) | 1.000 [1.000; 1.000] (46/46) | 1.000 [1.000; 1.000] (46/46) | 1.000 [1.000; 1.000] | 5/5 = 1.000 (Wilson 0.566; 1.000) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| c1 hồi quy logistic | 1.000 [1.000; 1.000] (42/42) | 0.913 [0.545; 0.980] (42/46) | 0.955 [0.706; 0.990] | 2/5 = 0.400 (Wilson 0.118; 0.769) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| c2 gradient boosting | 1.000 [1.000; 1.000] (41/41) | 0.891 [0.500; 0.985] (41/46) | 0.943 [0.667; 0.992] | 2/5 = 0.400 (Wilson 0.118; 0.769) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |

**mẫu âm (nhiều trang, không composite)** (155 tệp, 501 vị trí, 0 ranh giới thật)

| phương pháp | tách nhầm / 100 vị trí | tệp có >= 1 tách nhầm | exact-segment (tệp nguyên vẹn) | loại segment (cổng luật) |
|---|---|---|---|---|
| rule cũ (01) | 46.71 [41.35; 52.80] (234/501) | 105/155 = 0.677 [0.606; 0.755] | 50/155 = 0.323 (Wilson 0.254; 0.400) | 0.768 [0.697; 0.832] (oracle 0.819) |
| rule v2 (02) | 30.14 [23.37; 36.44] (151/501) | 70/155 = 0.452 [0.374; 0.529] | 85/155 = 0.548 (Wilson 0.470; 0.625) | 0.748 [0.677; 0.813] (oracle 0.819) |
| c1 hồi quy logistic | 15.37 [12.02; 19.71] (77/501) | 57/155 = 0.368 [0.297; 0.445] | 98/155 = 0.632 (Wilson 0.554; 0.704) | 0.755 [0.684; 0.819] (oracle 0.819) |
| c2 gradient boosting | 10.58 [6.50; 15.06] (53/501) | 28/155 = 0.181 [0.123; 0.245] | 127/155 = 0.819 (Wilson 0.751; 0.872) | 0.781 [0.716; 0.845] (oracle 0.819) |