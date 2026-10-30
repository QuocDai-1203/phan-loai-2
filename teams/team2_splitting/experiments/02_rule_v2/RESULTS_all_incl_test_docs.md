# 02 - Bộ luật đã sửa (rule v2) - phạm vi `all`

- **ngày chạy (UTC):** 2026-10-12 02:00
- **lệnh:** `.venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/02_rule_v2/run.py --scope all --final-test`
- **đáp án:** `teams/team2_splitting/gold/boundary_gold_v0.csv` sha1[:10] = `d9a30b5896` (v0, máy, CHƯA người kiểm)
- **nhãn:** `data/labels_v2.csv` sha1[:10] = `eb3348713a`
- **văn bản:** `data/ocr_v2.jsonl` (OCR cục bộ, tối đa 30 trang/tài liệu) sha1[:10] = `ac87a66c25`
- **phạm vi:** **all** = cả tài liệu TEST, chấm MỘT lần với cấu hình đã đóng băng
- **bootstrap:** 2000 lần lấy mẫu lại theo TỆP, seed 20260711, percentile 95%
- **máy:** Windows-11-10.0.26100-SP0, Python 3.13.14
- **mã đo:** `src/splitting/rules_v2.py::rule_starts` với `DEFAULT_CONFIG` (sha1[:10] của tệp: `4d6d094e62`)
- **thời gian chạy:** 5.5 s cho 212 tệp (máy đang bận, chỉ tham khảo)

## Kết quả theo nhóm (so với baseline)

Mỗi ô: điểm [CI 95% bootstrap theo tệp]. Tham số mặc định (`head_lines=6`, `min_chars=50`) được chọn tay SAU KHI xem lỗi của baseline trên phạm vi dev, nên số trên dev hơi lạc quan.

**composite khác loại** (8 tệp, 26 vị trí, 20 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment (tệp nguyên vẹn) | tách nhầm / 100 vị trí | loại segment (cổng luật) |
|---|---|---|---|---|---|---|
| rule hiện có (01) | 0.905 [0.778; 1.000] (19/21) | 0.950 [0.850; 1.000] (19/20) | 0.927 [0.850; 1.000] | 5/8 = 0.625 (Wilson 0.306; 0.863) | 7.69 [0.00; 14.29] (2) | 0.643 [0.500; 0.767] (oracle 0.679) |
| rule v2 | 1.000 [1.000; 1.000] (19/19) | 0.950 [0.850; 1.000] (19/20) | 0.974 [0.919; 1.000] | 7/8 = 0.875 (Wilson 0.529; 0.978) | 0.00 [0.00; 0.00] (0) | 0.643 [0.500; 0.767] (oracle 0.679) |

**composite cùng loại, ngoài BB_LAY_MAU** (6 tệp, 11 vị trí, 7 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment (tệp nguyên vẹn) | tách nhầm / 100 vị trí | loại segment (cổng luật) |
|---|---|---|---|---|---|---|
| rule hiện có (01) | 0.667 [0.333; 1.000] (4/6) | 0.571 [0.167; 0.889] (4/7) | 0.615 [0.222; 0.875] | 2/6 = 0.333 (Wilson 0.097; 0.700) | 18.18 [0.00; 42.90] (2) | 0.615 [0.250; 0.933] (oracle 0.615) |
| rule v2 | 0.800 [0.500; 1.000] (4/5) | 0.571 [0.167; 0.889] (4/7) | 0.667 [0.250; 0.889] | 2/6 = 0.333 (Wilson 0.097; 0.700) | 9.09 [0.00; 21.45] (1) | 0.615 [0.250; 0.933] (oracle 0.615) |

**composite BB_LAY_MAU** (7 tệp, 55 vị trí, 55 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment (tệp nguyên vẹn) | tách nhầm / 100 vị trí | loại segment (cổng luật) |
|---|---|---|---|---|---|---|
| rule hiện có (01) | 1.000 [1.000; 1.000] (55/55) | 1.000 [1.000; 1.000] (55/55) | 1.000 [1.000; 1.000] | 7/7 = 1.000 (Wilson 0.646; 1.000) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| rule v2 | 1.000 [1.000; 1.000] (55/55) | 1.000 [1.000; 1.000] (55/55) | 1.000 [1.000; 1.000] | 7/7 = 1.000 (Wilson 0.646; 1.000) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |

**mẫu âm (nhiều trang, không composite)** (191 tệp, 575 vị trí, 0 ranh giới thật)

| phương pháp | tách nhầm / 100 vị trí | tệp có >= 1 tách nhầm | exact-segment (tệp nguyên vẹn) | loại segment (cổng luật) |
|---|---|---|---|---|
| rule hiện có (01) | 48.00 [42.63; 53.99] (276/575) | 125/191 = 0.654 [0.586; 0.717] | 66/191 = 0.346 (Wilson 0.282; 0.415) | 0.764 [0.707; 0.822] (oracle 0.817) |
| rule v2 | 30.26 [23.80; 36.20] (174/575) | 80/191 = 0.419 [0.356; 0.492] | 111/191 = 0.581 (Wilson 0.510; 0.649) | 0.754 [0.696; 0.812] (oracle 0.817) |

## So sánh ghép cặp với baseline

| nhóm | chỉ số | rule v2 - rule cũ | CI 95% (bootstrap ghép cặp theo tệp) | kết luận |
|---|---|---|---|---|
| composite khác loại (n=8) | f1 | +0.048 | [+0.000; +0.121] | không tách được |
| composite khác loại (n=8) | recall | +0.000 | [+0.000; +0.000] | không tách được |
| composite khác loại (n=8) | precision | +0.095 | [+0.000; +0.222] | không tách được |
| composite khác loại (n=8) | exact_rate | +0.250 | [+0.000; +0.500] | không tách được |
| composite khác loại (n=8) | false_split_per100 | -7.692 | [-14.286; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | f1 | +0.051 | [+0.000; +0.115] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | recall | +0.000 | [+0.000; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | precision | +0.133 | [+0.000; +0.171] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | exact_rate | +0.000 | [+0.000; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | false_split_per100 | -9.091 | [-21.448; +0.000] | không tách được |
| composite BB_LAY_MAU (n=7) | f1 | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=7) | recall | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=7) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=7) | exact_rate | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=7) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=191) | false_split_per100 | -17.739 | [-24.558; -12.351] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=191) | files_with_false_split | -0.236 | [-0.293; -0.178] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=191) | exact_rate | +0.236 | [+0.178; +0.293] | tách được: tốt hơn |

## Ablation (TP/FP/FN theo nhóm; không có CI, chỉ để thấy thành phần nào làm việc)

| cấu hình | mixed (TP/FP/FN) | same_other | same_bb | negative (FP) |
|---|---|---|---|---|
| đủ mọi thành phần (mặc định) | 19/0/1 | 4/1/3 | 55/0/0 | 174 |
| bỏ: min_chars (>=50 ký tự) | 19/0/1 | 4/2/3 | 55/0/0 | 176 |
| bỏ: trang chỉ chữ ký/trống | 19/0/1 | 4/1/3 | 55/0/0 | 174 |
| bỏ: đánh số trang n/m, n>=2 | 19/0/1 | 4/1/3 | 55/0/0 | 179 |
| bỏ: tiêu đề lặp ở trang ngắn | 19/0/1 | 4/1/3 | 55/0/0 | 176 |
| bỏ: quốc hiệu chỉ ở đầu trang | 19/0/1 | 4/1/3 | 55/0/0 | 174 |
| bỏ: tiêu đề phải đầu dòng | 19/1/1 | 4/1/3 | 55/0/0 | 244 |
| không thành phần nào (chỉ khung) | 19/2/1 | 4/2/3 | 55/0/0 | 276 |
| chỉ bật: min_chars (>=50 ký tự) | 19/2/1 | 4/1/3 | 55/0/0 | 274 |
| chỉ bật: trang chỉ chữ ký/trống | 19/1/1 | 4/2/3 | 55/0/0 | 276 |
| chỉ bật: đánh số trang n/m, n>=2 | 19/1/1 | 4/2/3 | 55/0/0 | 248 |
| chỉ bật: tiêu đề lặp ở trang ngắn | 19/2/1 | 4/2/3 | 55/0/0 | 274 |
| chỉ bật: quốc hiệu chỉ ở đầu trang | 19/2/1 | 4/2/3 | 55/0/0 | 276 |
| chỉ bật: tiêu đề phải đầu dòng | 19/1/1 | 4/2/3 | 55/0/0 | 183 |
| nhạy cảm: head_lines=4 | 13/0/7 | 4/1/3 | 55/0/0 | 167 |
| nhạy cảm: head_lines=6 | 19/0/1 | 4/1/3 | 55/0/0 | 174 |
| nhạy cảm: head_lines=8 | 20/1/0 | 4/1/3 | 55/0/0 | 185 |
| nhạy cảm: head_lines=10 | 20/1/0 | 4/1/3 | 55/0/0 | 189 |
| nhạy cảm: min_chars=50 | 19/0/1 | 4/1/3 | 55/0/0 | 174 |
| nhạy cảm: min_chars=150 | 19/0/1 | 4/0/3 | 55/0/0 | 173 |
| nhạy cảm: min_chars=300 | 19/0/1 | 4/0/3 | 55/0/0 | 172 |

## Phân tích lỗi còn lại của rule v2 (5 kiểu đông nhất)

| # | loại lỗi | nhóm | lý do (dấu hiệu trên trang) | loại trang | số lần | ví dụ (doc_id:trang) |
|---|---|---|---|---|---|---|
| 1 | tách nhầm (FP) | negative | quốc hiệu ở đầu trang | HO_SO_QUAN_LY_PCCC | 76 | 1983c7d32e67:2, 1983c7d32e67:3, 1983c7d32e67:5 |
| 2 | tách nhầm (FP) | negative | quốc hiệu ở đầu trang, tiêu đề đầu dòng 'GIẤY CHỨNG NHẬN' | CC_TAP_HUAN_VC_HNH | 19 | 10bea683d0fd:2, 1195238c05fa:2, 233f9b02a4c3:2 |
| 3 | tách nhầm (FP) | negative | quốc hiệu ở đầu trang, tiêu đề đầu dòng 'BIÊN BẢN' | HO_SO_QUAN_LY_PCCC | 17 | 1983c7d32e67:23, 1983c7d32e67:25, 1983c7d32e67:27 |
| 4 | tách nhầm (FP) | negative | tiêu đề đầu dòng 'GIẤY CHỨNG NHẬN' | GCN_DDK_BAN_LE_XD | 13 | 13b82b3e383e:2, 27bc11619915:2, 41265fcefd36:2 |
| 5 | tách nhầm (FP) | negative | tiêu đề đầu dòng 'BIÊN BẢN' | HD_MUON_BON | 10 | 3376b0c936f1:3, 3376b0c936f1:5, 5b84a6c30d75:3 |

(tổng: 175 tách nhầm, 4 sót; 27 kiểu lỗi khác nhau; bảng liệt kê 5 kiểu đông nhất)

### Chỉ trong các nhóm composite (sót / tách nhầm)

| # | loại lỗi | nhóm | lý do (dấu hiệu trên trang) | loại trang | số lần | ví dụ (doc_id:trang) |
|---|---|---|---|---|---|---|
| 1 | sót ranh giới (FN) | same_other | không có dấu hiệu luật | BIEN_NHAN_THE_CHAP_PT | 2 | 4ad1c01d6262:2, 898572a6f361:2 |
| 2 | sót ranh giới (FN) | same_other | không có dấu hiệu luật | HOA_DON | 1 | 36aff038b19e:3 |
| 3 | tách nhầm (FP) | same_other | quốc hiệu ở đầu trang, tiêu đề đầu dòng 'GIẤY CHỨNG NHẬN' | CC_NGHIEP_VU_BVMT | 1 | 72449aceeff3:2 |
| 4 | sót ranh giới (FN) | mixed | không có dấu hiệu luật | BB_LAY_MAU | 1 | 9c00a14eed6b:3 |

(tổng: 1 tách nhầm, 4 sót; 4 kiểu lỗi khác nhau; bảng liệt kê 4 kiểu đông nhất)
