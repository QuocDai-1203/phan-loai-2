# 03 - Phân loại loại từng trang rồi gộp (b) - phạm vi `all`

- **ngày chạy (UTC):** 2026-10-12 02:06
- **lệnh:** `.venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/03_type_merge/run.py --scope all --final-test`
- **đáp án:** `teams/team2_splitting/gold/boundary_gold_v0.csv` sha1[:10] = `d9a30b5896` (v0, máy, CHƯA người kiểm)
- **nhãn:** `data/labels_v2.csv` sha1[:10] = `eb3348713a`
- **văn bản:** `data/ocr_v2.jsonl` (OCR cục bộ, tối đa 30 trang/tài liệu) sha1[:10] = `ac87a66c25`
- **phạm vi:** **all** = cả tài liệu TEST, chấm MỘT lần với cấu hình đã đóng băng
- **bootstrap:** 2000 lần lấy mẫu lại theo TỆP, seed 20260711, percentile 95%
- **máy:** Windows-11-10.0.26100-SP0, Python 3.13.14
- **mã đo:** `src/splitting/learned.py::TypeMergeSplitter` (sha1[:10] `307193c424`), cross-fitting `teams/team2_splitting/cvlib.py` (5 fold theo nhóm biểu mẫu, seed 0, bộ BSR gộp một nhóm)
- **huấn luyện:** mỗi fold: trang của tài liệu dev ngoài fold (nhãn loại = loại segment trong `boundary_gold_v0.csv`); không dùng TEST. Số liệu trên composite thật là CROSS-VALIDATED (dev-like), KHÔNG phải tập TEST khóa
- **thời gian chạy:** 322 s toàn bộ CV (máy dùng chung, chỉ tham khảo)

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

**composite BB_LAY_MAU** (7 tệp, 55 vị trí, 55 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment (tệp nguyên vẹn) | tách nhầm / 100 vị trí | loại segment (cổng luật) |
|---|---|---|---|---|---|---|
| rule cũ (01) | 1.000 [1.000; 1.000] (55/55) | 1.000 [1.000; 1.000] (55/55) | 1.000 [1.000; 1.000] | 7/7 = 1.000 (Wilson 0.646; 1.000) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| rule v2 (02) | 1.000 [1.000; 1.000] (55/55) | 1.000 [1.000; 1.000] (55/55) | 1.000 [1.000; 1.000] | 7/7 = 1.000 (Wilson 0.646; 1.000) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| b0 chỉ đổi loại | n/a (0/0) | 0.000 [0.000; 0.000] (0/55) | 0.000 [0.000; 0.000] | 0/7 = 0.000 (Wilson 0.000; 0.354) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| b1 đổi loại + bản khác | 1.000 [1.000; 1.000] (47/47) | 0.855 [0.632; 0.950] (47/55) | 0.922 [0.774; 0.974] | 3/7 = 0.429 (Wilson 0.158; 0.750) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |

**mẫu âm (nhiều trang, không composite)** (191 tệp, 575 vị trí, 0 ranh giới thật)

| phương pháp | tách nhầm / 100 vị trí | tệp có >= 1 tách nhầm | exact-segment (tệp nguyên vẹn) | loại segment (cổng luật) |
|---|---|---|---|---|
| rule cũ (01) | 48.00 [42.63; 53.99] (276/575) | 125/191 = 0.654 [0.586; 0.717] | 66/191 = 0.346 (Wilson 0.282; 0.415) | 0.764 [0.707; 0.822] (oracle 0.817) |
| rule v2 (02) | 30.26 [23.80; 36.20] (174/575) | 80/191 = 0.419 [0.356; 0.492] | 111/191 = 0.581 (Wilson 0.510; 0.649) | 0.754 [0.696; 0.812] (oracle 0.817) |
| b0 chỉ đổi loại | 1.04 [0.19; 2.23] (6/575) | 5/191 = 0.026 [0.005; 0.052] | 186/191 = 0.974 (Wilson 0.940; 0.989) | 0.817 [0.759; 0.869] (oracle 0.817) |
| b1 đổi loại + bản khác | 28.00 [22.18; 33.40] (161/575) | 76/191 = 0.398 [0.330; 0.466] | 115/191 = 0.602 (Wilson 0.531; 0.669) | 0.759 [0.702; 0.817] (oracle 0.817) |

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
| composite BB_LAY_MAU (n=7) | f1 | -1.000 | [-1.000; -1.000] | tách được: kém hơn |
| composite BB_LAY_MAU (n=7) | recall | -1.000 | [-1.000; -1.000] | tách được: kém hơn |
| composite BB_LAY_MAU (n=7) | precision | +nan | [+nan; +nan] | không tính được (mẫu số bằng 0 ở nhiều lần lấy mẫu lại) |
| composite BB_LAY_MAU (n=7) | exact_rate | -1.000 | [-1.000; -1.000] | tách được: kém hơn |
| composite BB_LAY_MAU (n=7) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=191) | false_split_per100 | -46.957 | [-52.876; -41.493] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=191) | files_with_false_split | -0.628 | [-0.696; -0.560] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=191) | exact_rate | +0.628 | [+0.560; +0.696] | tách được: tốt hơn |

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
| composite BB_LAY_MAU (n=7) | f1 | -0.078 | [-0.226; -0.026] | tách được: kém hơn |
| composite BB_LAY_MAU (n=7) | recall | -0.145 | [-0.368; -0.050] | tách được: kém hơn |
| composite BB_LAY_MAU (n=7) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=7) | exact_rate | -0.571 | [-0.857; -0.143] | tách được: kém hơn |
| composite BB_LAY_MAU (n=7) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=191) | false_split_per100 | -20.000 | [-26.570; -14.977] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=191) | files_with_false_split | -0.257 | [-0.319; -0.194] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=191) | exact_rate | +0.257 | [+0.194; +0.319] | tách được: tốt hơn |

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
| composite BB_LAY_MAU (n=7) | f1 | -0.078 | [-0.226; -0.026] | tách được: kém hơn |
| composite BB_LAY_MAU (n=7) | recall | -0.145 | [-0.368; -0.050] | tách được: kém hơn |
| composite BB_LAY_MAU (n=7) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=7) | exact_rate | -0.571 | [-0.857; -0.143] | tách được: kém hơn |
| composite BB_LAY_MAU (n=7) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=191) | false_split_per100 | -2.261 | [-3.945; -0.582] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=191) | files_with_false_split | -0.021 | [-0.047; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=191) | exact_rate | +0.021 | [+0.000; +0.047] | không tách được |

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
| 1 | tách nhầm (FP) | negative | quốc hiệu ở đầu trang | HO_SO_QUAN_LY_PCCC | 74 | 1983c7d32e67:2, 1983c7d32e67:3, 1983c7d32e67:5 |
| 2 | tách nhầm (FP) | negative | quốc hiệu ở đầu trang, tiêu đề đầu dòng 'GIẤY CHỨNG NHẬN' | CC_TAP_HUAN_VC_HNH | 19 | 10bea683d0fd:2, 1195238c05fa:2, 233f9b02a4c3:2 |
| 3 | tách nhầm (FP) | negative | tiêu đề đầu dòng 'GIẤY CHỨNG NHẬN' | GCN_DDK_BAN_LE_XD | 13 | 41265fcefd36:2, 547141773252:2, 73d0edb4d618:2 |
| 4 | tách nhầm (FP) | negative | quốc hiệu ở đầu trang, tiêu đề đầu dòng 'BIÊN BẢN' | HO_SO_QUAN_LY_PCCC | 11 | 1983c7d32e67:23, 297c0d94ec78:24, 297c0d94ec78:30 |
| 5 | tách nhầm (FP) | negative | tiêu đề đầu dòng 'BIÊN BẢN' | HD_MUON_BON | 6 | 3376b0c936f1:3, 67788b715358:3, 5b84a6c30d75:3 |

(tổng: 162 tách nhầm, 19 sót; 32 kiểu lỗi khác nhau; bảng liệt kê 5 kiểu đông nhất)
