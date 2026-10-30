# 03 - Phân loại loại từng trang rồi gộp (b) - phạm vi `dev`

- **ngày chạy (UTC):** 2026-10-12 02:21
- **lệnh:** `.venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/03_type_merge/run.py`
- **đáp án:** `teams/team2_splitting/gold/boundary_gold_v0.csv` sha1[:10] = `d9a30b5896` (v0, máy, CHƯA người kiểm)
- **nhãn:** `data/labels_v2.csv` sha1[:10] = `eb3348713a`
- **văn bản:** `data/ocr_v2.jsonl` (OCR cục bộ, tối đa 30 trang/tài liệu) sha1[:10] = `ac87a66c25`
- **phạm vi:** **dev** = DEV + EXCLUDED_COMPOSITE (không có tài liệu TEST)
- **bootstrap:** 2000 lần lấy mẫu lại theo TỆP, seed 20260711, percentile 95%
- **máy:** Windows-11-10.0.26100-SP0, Python 3.13.14
- **mã đo:** `src/splitting/learned.py::TypeMergeSplitter` (sha1[:10] `307193c424`), cross-fitting `teams/team2_splitting/cvlib.py` (5 fold theo nhóm biểu mẫu, seed 0, bộ BSR gộp một nhóm)
- **huấn luyện:** mỗi fold: trang của tài liệu dev ngoài fold (nhãn loại = loại segment trong `boundary_gold_v0.csv`); không dùng TEST. Số liệu trên composite thật là CROSS-VALIDATED (dev-like), KHÔNG phải tập TEST khóa
- **thời gian chạy:** 222 s toàn bộ CV (máy dùng chung, chỉ tham khảo)

## Kết quả trên composite THẬT, theo nhóm

Mỗi ô: điểm [CI 95% bootstrap theo tệp]. b0 = tách khi loại dự đoán đổi (cả hai trang có xác suất loại >= 0,5). b1 = b0 + với chuỗi cùng loại, tách khi trang trông như trang đầu (luật v2) và số hiệu/ngày khác trang trước.

**composite khác loại** (8 tệp, 26 vị trí, 20 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment (tệp nguyên vẹn) | tách nhầm / 100 vị trí | loại segment (cổng luật) |
|---|---|---|---|---|---|---|
| rule cũ (01) | 0.905 [0.778; 1.000] (19/21) | 0.950 [0.850; 1.000] (19/20) | 0.927 [0.850; 1.000] | 5/8 = 0.625 (Wilson 0.306; 0.863) | 7.69 [0.00; 14.29] (2) | 0.643 [0.500; 0.767] (oracle 0.679) |
| rule v2 (02) | 1.000 [1.000; 1.000] (19/19) | 0.950 [0.850; 1.000] (19/20) | 0.974 [0.919; 1.000] | 7/8 = 0.875 (Wilson 0.529; 0.978) | 0.00 [0.00; 0.00] (0) | 0.643 [0.500; 0.767] (oracle 0.679) |
| b0 chỉ đổi loại | 1.000 [1.000; 1.000] (13/13) | 0.650 [0.556; 0.722] (13/20) | 0.788 [0.714; 0.839] | 1/8 = 0.125 (Wilson 0.022; 0.471) | 0.00 [0.00; 0.00] (0) | 0.464 [0.333; 0.583] (oracle 0.679) |
| b1 đổi loại + bản khác | 1.000 [1.000; 1.000] (14/14) | 0.700 [0.667; 0.786] (14/20) | 0.824 [0.800; 0.880] | 2/8 = 0.250 (Wilson 0.071; 0.591) | 0.00 [0.00; 0.00] (0) | 0.464 [0.333; 0.583] (oracle 0.679) |

**composite cùng loại, ngoài BB_LAY_MAU** (6 tệp, 11 vị trí, 7 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment (tệp nguyên vẹn) | tách nhầm / 100 vị trí | loại segment (cổng luật) |
|---|---|---|---|---|---|---|
| rule cũ (01) | 0.667 [0.333; 1.000] (4/6) | 0.571 [0.167; 0.889] (4/7) | 0.615 [0.222; 0.875] | 2/6 = 0.333 (Wilson 0.097; 0.700) | 18.18 [0.00; 42.90] (2) | 0.615 [0.250; 0.933] (oracle 0.615) |
| rule v2 (02) | 0.800 [0.500; 1.000] (4/5) | 0.571 [0.167; 0.889] (4/7) | 0.667 [0.250; 0.889] | 2/6 = 0.333 (Wilson 0.097; 0.700) | 9.09 [0.00; 21.45] (1) | 0.615 [0.250; 0.933] (oracle 0.615) |
| b0 chỉ đổi loại | n/a (0/0) | 0.000 [0.000; 0.000] (0/7) | 0.000 [0.000; 0.000] | 0/6 = 0.000 (Wilson 0.000; 0.390) | 0.00 [0.00; 0.00] (0) | 0.692 [0.333; 1.000] (oracle 0.615) |
| b1 đổi loại + bản khác | 0.667 [0.500; 1.000] (2/3) | 0.286 [0.000; 0.667] (2/7) | 0.400 [0.000; 0.714] | 1/6 = 0.167 (Wilson 0.030; 0.564) | 9.09 [0.00; 21.45] (1) | 0.615 [0.250; 0.933] (oracle 0.615) |

**composite BB_LAY_MAU** (5 tệp, 46 vị trí, 46 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment (tệp nguyên vẹn) | tách nhầm / 100 vị trí | loại segment (cổng luật) |
|---|---|---|---|---|---|---|
| rule cũ (01) | 1.000 [1.000; 1.000] (46/46) | 1.000 [1.000; 1.000] (46/46) | 1.000 [1.000; 1.000] | 5/5 = 1.000 (Wilson 0.566; 1.000) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| rule v2 (02) | 1.000 [1.000; 1.000] (46/46) | 1.000 [1.000; 1.000] (46/46) | 1.000 [1.000; 1.000] | 5/5 = 1.000 (Wilson 0.566; 1.000) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| b0 chỉ đổi loại | n/a (0/0) | 0.000 [0.000; 0.000] (0/46) | 0.000 [0.000; 0.000] | 0/5 = 0.000 (Wilson 0.000; 0.434) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| b1 đổi loại + bản khác | 1.000 [1.000; 1.000] (38/38) | 0.826 [0.364; 0.918] (38/46) | 0.905 [0.533; 0.957] | 1/5 = 0.200 (Wilson 0.036; 0.624) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |

**mẫu âm (nhiều trang, không composite)** (155 tệp, 501 vị trí, 0 ranh giới thật)

| phương pháp | tách nhầm / 100 vị trí | tệp có >= 1 tách nhầm | exact-segment (tệp nguyên vẹn) | loại segment (cổng luật) |
|---|---|---|---|---|
| rule cũ (01) | 46.71 [41.35; 52.80] (234/501) | 105/155 = 0.677 [0.606; 0.755] | 50/155 = 0.323 (Wilson 0.254; 0.400) | 0.768 [0.697; 0.832] (oracle 0.819) |
| rule v2 (02) | 30.14 [23.37; 36.44] (151/501) | 70/155 = 0.452 [0.374; 0.529] | 85/155 = 0.548 (Wilson 0.470; 0.625) | 0.748 [0.677; 0.813] (oracle 0.819) |
| b0 chỉ đổi loại | 1.00 [0.15; 2.22] (5/501) | 4/155 = 0.026 [0.006; 0.052] | 151/155 = 0.974 (Wilson 0.936; 0.990) | 0.819 [0.755; 0.877] (oracle 0.819) |
| b1 đổi loại + bản khác | 27.74 [21.81; 33.48] (139/501) | 66/155 = 0.426 [0.348; 0.503] | 89/155 = 0.574 (Wilson 0.495; 0.649) | 0.748 [0.677; 0.813] (oracle 0.819) |

## So sánh ghép cặp với baseline (rule cũ) trên composite thật

### b0 chỉ đổi loại - rule cũ

| nhóm | chỉ số | b0 chỉ đổi loại - rule cũ | CI 95% (bootstrap ghép cặp theo tệp) | kết luận |
|---|---|---|---|---|
| composite khác loại (n=8) | f1 | -0.139 | [-0.200; -0.075] | tách được: kém hơn |
| composite khác loại (n=8) | recall | -0.300 | [-0.438; -0.167] | tách được: kém hơn |
| composite khác loại (n=8) | precision | +0.095 | [+0.000; +0.222] | không tách được |
| composite khác loại (n=8) | exact_rate | -0.500 | [-0.875; -0.125] | tách được: kém hơn |
| composite khác loại (n=8) | false_split_per100 | -7.692 | [-14.286; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | f1 | -0.615 | [-0.875; -0.222] | tách được: kém hơn |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | recall | -0.571 | [-0.889; -0.167] | tách được: kém hơn |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | precision | +nan | [+nan; +nan] | không tính được (mẫu số bằng 0 ở nhiều lần lấy mẫu lại) |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | exact_rate | -0.333 | [-0.667; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | false_split_per100 | -18.182 | [-42.897; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | f1 | -1.000 | [-1.000; -1.000] | tách được: kém hơn |
| composite BB_LAY_MAU (n=5) | recall | -1.000 | [-1.000; -1.000] | tách được: kém hơn |
| composite BB_LAY_MAU (n=5) | precision | +nan | [+nan; +nan] | không tính được (mẫu số bằng 0 ở nhiều lần lấy mẫu lại) |
| composite BB_LAY_MAU (n=5) | exact_rate | -1.000 | [-1.000; -1.000] | tách được: kém hơn |
| composite BB_LAY_MAU (n=5) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=155) | false_split_per100 | -45.709 | [-51.667; -40.495] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=155) | files_with_false_split | -0.652 | [-0.729; -0.574] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=155) | exact_rate | +0.652 | [+0.574; +0.729] | tách được: tốt hơn |

### b1 đổi loại + bản khác - rule cũ

| nhóm | chỉ số | b1 đổi loại + bản khác - rule cũ | CI 95% (bootstrap ghép cặp theo tệp) | kết luận |
|---|---|---|---|---|
| composite khác loại (n=8) | f1 | -0.103 | [-0.180; +0.005] | không tách được |
| composite khác loại (n=8) | recall | -0.250 | [-0.333; -0.125] | tách được: kém hơn |
| composite khác loại (n=8) | precision | +0.095 | [+0.000; +0.222] | không tách được |
| composite khác loại (n=8) | exact_rate | -0.375 | [-0.875; +0.125] | không tách được |
| composite khác loại (n=8) | false_split_per100 | -7.692 | [-14.286; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | f1 | -0.215 | [-0.675; +0.100] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | recall | -0.286 | [-0.667; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | precision | +0.000 | [-0.214; +0.171] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | exact_rate | -0.167 | [-0.500; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | false_split_per100 | -9.091 | [-21.448; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | f1 | -0.095 | [-0.467; -0.043] | tách được: kém hơn |
| composite BB_LAY_MAU (n=5) | recall | -0.174 | [-0.636; -0.082] | tách được: kém hơn |
| composite BB_LAY_MAU (n=5) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | exact_rate | -0.800 | [-1.000; -0.400] | tách được: kém hơn |
| composite BB_LAY_MAU (n=5) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=155) | false_split_per100 | -18.962 | [-25.317; -13.972] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=155) | files_with_false_split | -0.252 | [-0.323; -0.181] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=155) | exact_rate | +0.252 | [+0.181; +0.323] | tách được: tốt hơn |

### b1 - rule v2

| nhóm | chỉ số | b1 - rule v2 | CI 95% (bootstrap ghép cặp theo tệp) | kết luận |
|---|---|---|---|---|
| composite khác loại (n=8) | f1 | -0.151 | [-0.200; -0.076] | tách được: kém hơn |
| composite khác loại (n=8) | recall | -0.250 | [-0.333; -0.125] | tách được: kém hơn |
| composite khác loại (n=8) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite khác loại (n=8) | exact_rate | -0.625 | [-1.000; -0.250] | tách được: kém hơn |
| composite khác loại (n=8) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | f1 | -0.267 | [-0.675; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | recall | -0.286 | [-0.667; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | precision | -0.133 | [-0.333; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | exact_rate | -0.167 | [-0.500; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | f1 | -0.095 | [-0.467; -0.043] | tách được: kém hơn |
| composite BB_LAY_MAU (n=5) | recall | -0.174 | [-0.636; -0.082] | tách được: kém hơn |
| composite BB_LAY_MAU (n=5) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | exact_rate | -0.800 | [-1.000; -0.400] | tách được: kém hơn |
| composite BB_LAY_MAU (n=5) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=155) | false_split_per100 | -2.395 | [-4.167; -0.704] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=155) | files_with_false_split | -0.026 | [-0.052; -0.006] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=155) | exact_rate | +0.026 | [+0.006; +0.052] | tách được: tốt hơn |

## Trên composite TỔNG HỢP (giữ lại theo fold, sinh từ tài liệu đơn DEV của đúng các nhóm giữ lại)

Seed sinh: huấn luyện `100+fold`, đánh giá `1000+fold` (`gold/make_synthetic.py`). 400 composite. Ranh giới tổng hợp thường dễ hơn thật (các trang đến từ lần quét độc lập).

**syn_bundle** (60 composite tổng hợp, 60 vị trí, 60 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment | tách nhầm / 100 vị trí |
|---|---|---|---|---|---|
| rule cũ | 1.000 [1.000; 1.000] | 1.000 [1.000; 1.000] | 1.000 [1.000; 1.000] | 60/60 = 1.000 | 0.00 [0.00; 0.00] |
| rule v2 | 1.000 [1.000; 1.000] | 1.000 [1.000; 1.000] | 1.000 [1.000; 1.000] | 60/60 = 1.000 | 0.00 [0.00; 0.00] |
| b0 chỉ đổi loại | 1.000 [1.000; 1.000] | 1.000 [1.000; 1.000] | 1.000 [1.000; 1.000] | 60/60 = 1.000 | 0.00 [0.00; 0.00] |
| b1 đổi loại + bản khác | 1.000 [1.000; 1.000] | 1.000 [1.000; 1.000] | 1.000 [1.000; 1.000] | 60/60 = 1.000 | 0.00 [0.00; 0.00] |

**syn_contract** (56 composite tổng hợp, 233 vị trí, 56 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment | tách nhầm / 100 vị trí |
|---|---|---|---|---|---|
| rule cũ | 0.458 [0.404; 0.524] | 0.982 [0.929; 1.000] | 0.625 [0.571; 0.683] | 17/56 = 0.304 | 27.90 [23.26; 32.30] |
| rule v2 | 0.628 [0.545; 0.724] | 0.964 [0.911; 1.000] | 0.761 [0.687; 0.831] | 34/56 = 0.607 | 13.73 [9.76; 17.37] |
| b0 chỉ đổi loại | 0.891 [0.800; 0.979] | 0.875 [0.786; 0.946] | 0.883 [0.817; 0.939] | 44/56 = 0.786 | 2.58 [0.46; 5.08] |
| b1 đổi loại + bản khác | 0.613 [0.521; 0.721] | 0.875 [0.786; 0.946] | 0.721 [0.638; 0.806] | 32/56 = 0.571 | 13.30 [9.09; 17.80] |

**syn_mixed** (146 composite tổng hợp, 1026 vị trí, 365 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment | tách nhầm / 100 vị trí |
|---|---|---|---|---|---|
| rule cũ | 0.534 [0.506; 0.562] | 0.915 [0.888; 0.942] | 0.674 [0.650; 0.699] | 14/146 = 0.096 | 28.46 [26.30; 30.45] |
| rule v2 | 0.625 [0.593; 0.659] | 0.910 [0.882; 0.937] | 0.741 [0.716; 0.767] | 30/146 = 0.205 | 19.40 [17.35; 21.31] |
| b0 chỉ đổi loại | 0.935 [0.899; 0.969] | 0.430 [0.370; 0.496] | 0.589 [0.530; 0.647] | 28/146 = 0.192 | 1.07 [0.49; 1.72] |
| b1 đổi loại + bản khác | 0.504 [0.462; 0.548] | 0.501 [0.444; 0.563] | 0.503 [0.457; 0.548] | 14/146 = 0.096 | 17.54 [15.48; 19.59] |

**syn_same_type** (138 composite tổng hợp, 806 vị trí, 299 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment | tách nhầm / 100 vị trí |
|---|---|---|---|---|---|
| rule cũ | 0.490 [0.447; 0.537] | 0.936 [0.899; 0.967] | 0.643 [0.602; 0.686] | 40/138 = 0.290 | 36.23 [31.83; 40.48] |
| rule v2 | 0.608 [0.548; 0.671] | 0.933 [0.894; 0.965] | 0.736 [0.686; 0.785] | 54/138 = 0.391 | 22.33 [18.01; 26.87] |
| b0 chỉ đổi loại | 0.333 [0.000; 1.000] | 0.007 [0.000; 0.017] | 0.013 [0.000; 0.033] | 0/138 = 0.000 | 0.50 [0.00; 1.22] |
| b1 đổi loại + bản khác | 0.596 [0.536; 0.659] | 0.839 [0.783; 0.890] | 0.697 [0.648; 0.745] | 42/138 = 0.304 | 21.09 [16.98; 25.52] |

## Phân tích lỗi (b1, 5 kiểu đông nhất)

| # | loại lỗi | nhóm | lý do (dấu hiệu trên trang) | loại trang | số lần | ví dụ (doc_id:trang) |
|---|---|---|---|---|---|---|
| 1 | tách nhầm (FP) | negative | quốc hiệu ở đầu trang | HO_SO_QUAN_LY_PCCC | 64 | 1983c7d32e67:2, 1983c7d32e67:3, 1983c7d32e67:5 |
| 2 | tách nhầm (FP) | negative | quốc hiệu ở đầu trang, tiêu đề đầu dòng 'GIẤY CHỨNG NHẬN' | CC_TAP_HUAN_VC_HNH | 14 | 10bea683d0fd:2, 1195238c05fa:2, 233f9b02a4c3:2 |
| 3 | tách nhầm (FP) | negative | tiêu đề đầu dòng 'GIẤY CHỨNG NHẬN' | GCN_DDK_BAN_LE_XD | 11 | 41265fcefd36:2, 547141773252:2, 73d0edb4d618:2 |
| 4 | tách nhầm (FP) | negative | quốc hiệu ở đầu trang, tiêu đề đầu dòng 'BIÊN BẢN' | HO_SO_QUAN_LY_PCCC | 8 | 1983c7d32e67:23, 297c0d94ec78:24, 297c0d94ec78:30 |
| 5 | tách nhầm (FP) | negative | tiêu đề đầu dòng 'GIẤY CHỨNG NHẬN' | GCN_BAO_HIEM | 6 | baebf72f798f:2, e59cf5cafa04:2, 61d855bda6e1:2 |

(tổng: 140 tách nhầm, 19 sót; 31 kiểu lỗi khác nhau; bảng liệt kê 5 kiểu đông nhất)

## Cách đọc kết quả (nhận xét của người viết, mọi số lấy từ các bảng trên)

1. **b0 (chỉ tách khi loại dự đoán đổi) gần như không bao giờ tách nhầm** (5/501 vị trí, 1,0 / 100; 151/155 tệp âm nguyên vẹn, so với 85/155 của rule v2): ghép trang theo loại đúng là cách chống "tập hồ sơ có nhiều tiêu đề con" mà luật không làm được. **Nhưng nó bỏ sót gần như mọi ranh giới còn lại**: chỉ bắt 0/46 ranh giới ở `BB_LAY_MAU`, 0/7 ở nhóm cùng loại (hai trang liên tiếp cùng loại thì "loại" không đổi, đúng hạn chế đã nêu trong README) và 13/20 ở composite khác loại.
2. **Sót của b0 ở composite khác loại tập trung ở trang `CHUNG_THU_CHAT_LUONG`.** Trong `results/per_file_b0_dev.csv`, 6 trong 7 ranh giới bị sót là ranh giới vào hoặc ra trang chứng thư chất lượng (loại này không có tài liệu đơn nào trong kho, chỉ xuất hiện như một segment trong bộ chứng từ, nên mô hình loại-trang gần như không có trang huấn luyện khi cả nhóm bộ chứng từ BSR bị giữ lại; ghi chú: đây là giải thích của tôi dựa trên danh sách trang sót, chưa chạy thí nghiệm riêng để chứng minh). Ranh giới sót còn lại là `87c88bf6d0f1` trang 3 (biên bản giao nhận sang biên bản thanh lý hợp đồng). Đây là rủi ro thật cho triển khai: loại tài liệu mới chưa từng có trang huấn luyện thì bộ gộp theo loại không nhìn thấy ranh giới của nó.
3. **b1 (thêm "dấu hiệu bản khác" cho chuỗi cùng loại) lấy lại một phần nhưng trả giá bằng tách nhầm**: bắt 38/46 ở `BB_LAY_MAU` (recall 0,826 [0,364; 0,918], exact-segment mới 1/5 tệp) và 2/7 ở nhóm cùng loại; trên mẫu âm tách nhầm lên 27,7 / 100 vị trí, **gần bằng rule v2 (30,1)**, chênh ghép cặp so với rule v2 là -2,4 [-4,2; -0,7] (tách được nhưng nhỏ). Lý do: luật "trang trông như trang đầu và số hiệu/ngày khác trang trước" cũng đúng với các trang đầu-đề con của tập hồ sơ cùng loại, giống hệt cách tập hồ sơ lừa luật. b1 **kém hơn** rule v2 và rule cũ trên `BB_LAY_MAU` (tách được: kém hơn) và kém hơn rule v2 ở composite khác loại.
4. **Kết luận cho nhóm này:** gộp theo loại là thành phần tốt cho "đừng tách" nhưng không thể là bộ tách duy nhất. Đặt nó thành một đặc trưng (xác suất loại của hai trang) cho bộ phân loại cặp trang là việc của thí nghiệm 04, nơi các tín hiệu được cân nhắc cùng nhau.
5. Trên composite tổng hợp (cùng bảng): b0 đạt tách nhầm thấp (0,5-2,6 / 100 vị trí) nhưng recall 0,43 ở `syn_mixed` và 0,007 ở `syn_same_type`, cùng hành vi như trên dữ liệu thật; b1 không cao hơn rule v2 ở `syn_contract` (F1 0,721 so với 0,761) và thấp hơn ở `syn_mixed` (0,503 so với 0,741). Hành vi khớp giữa tổng hợp và thật nên đủ tin dùng tổng hợp để chỉnh phương pháp, nhưng không dùng nó để báo hiệu năng.

### Giới hạn

- Cross-fitting có nhóm (5 fold, seed 0; 5 bộ chứng từ BSR cùng chuỗi loại gộp một nhóm nên luôn nằm cùng một fold và cùng bị giữ ngoài khi chấm): số trên composite thật là **cross-validated, không phải TEST khóa**. Không chạy lại nhiều seed fold nên không biết độ nhạy với cách chia fold.
- Các tham số `tau = 0,5` và `id_jaccard_max = 0,34` đặt trước, không chỉnh theo kết quả; b0/b1 là hai cấu hình duy nhất đã chạy.
- Nhóm nhỏ (8 / 6 / 5 tệp): hầu hết CI rộng; chỉ khẳng định "tách được" khi CI không chứa 0.
