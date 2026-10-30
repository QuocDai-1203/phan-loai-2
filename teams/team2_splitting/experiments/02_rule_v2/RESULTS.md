# 02 - Bộ luật đã sửa (rule v2) - phạm vi `dev`

- **ngày chạy (UTC):** 2026-10-12 02:16
- **lệnh:** `.venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/02_rule_v2/run.py`
- **đáp án:** `teams/team2_splitting/gold/boundary_gold_v0.csv` sha1[:10] = `d9a30b5896` (v0, máy, CHƯA người kiểm)
- **nhãn:** `data/labels_v2.csv` sha1[:10] = `eb3348713a`
- **văn bản:** `data/ocr_v2.jsonl` (OCR cục bộ, tối đa 30 trang/tài liệu) sha1[:10] = `ac87a66c25`
- **phạm vi:** **dev** = DEV + EXCLUDED_COMPOSITE (không có tài liệu TEST)
- **bootstrap:** 2000 lần lấy mẫu lại theo TỆP, seed 20260711, percentile 95%
- **máy:** Windows-11-10.0.26100-SP0, Python 3.13.14
- **mã đo:** `src/splitting/rules_v2.py::rule_starts` với `DEFAULT_CONFIG` (sha1[:10] của tệp: `4d6d094e62`)
- **thời gian chạy:** 5.1 s cho 174 tệp (máy đang bận, chỉ tham khảo)

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

**composite BB_LAY_MAU** (5 tệp, 46 vị trí, 46 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment (tệp nguyên vẹn) | tách nhầm / 100 vị trí | loại segment (cổng luật) |
|---|---|---|---|---|---|---|
| rule hiện có (01) | 1.000 [1.000; 1.000] (46/46) | 1.000 [1.000; 1.000] (46/46) | 1.000 [1.000; 1.000] | 5/5 = 1.000 (Wilson 0.566; 1.000) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| rule v2 | 1.000 [1.000; 1.000] (46/46) | 1.000 [1.000; 1.000] (46/46) | 1.000 [1.000; 1.000] | 5/5 = 1.000 (Wilson 0.566; 1.000) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |

**mẫu âm (nhiều trang, không composite)** (155 tệp, 501 vị trí, 0 ranh giới thật)

| phương pháp | tách nhầm / 100 vị trí | tệp có >= 1 tách nhầm | exact-segment (tệp nguyên vẹn) | loại segment (cổng luật) |
|---|---|---|---|---|
| rule hiện có (01) | 46.71 [41.35; 52.80] (234/501) | 105/155 = 0.677 [0.606; 0.755] | 50/155 = 0.323 (Wilson 0.254; 0.400) | 0.768 [0.697; 0.832] (oracle 0.819) |
| rule v2 | 30.14 [23.37; 36.44] (151/501) | 70/155 = 0.452 [0.374; 0.529] | 85/155 = 0.548 (Wilson 0.470; 0.625) | 0.748 [0.677; 0.813] (oracle 0.819) |

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
| composite BB_LAY_MAU (n=5) | f1 | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | recall | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | exact_rate | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=155) | false_split_per100 | -16.567 | [-23.667; -11.131] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=155) | files_with_false_split | -0.226 | [-0.290; -0.161] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=155) | exact_rate | +0.226 | [+0.161; +0.290] | tách được: tốt hơn |

## Ablation (TP/FP/FN theo nhóm; không có CI, chỉ để thấy thành phần nào làm việc)

| cấu hình | mixed (TP/FP/FN) | same_other | same_bb | negative (FP) |
|---|---|---|---|---|
| đủ mọi thành phần (mặc định) | 19/0/1 | 4/1/3 | 46/0/0 | 151 |
| bỏ: min_chars (>=50 ký tự) | 19/0/1 | 4/2/3 | 46/0/0 | 152 |
| bỏ: trang chỉ chữ ký/trống | 19/0/1 | 4/1/3 | 46/0/0 | 151 |
| bỏ: đánh số trang n/m, n>=2 | 19/0/1 | 4/1/3 | 46/0/0 | 155 |
| bỏ: tiêu đề lặp ở trang ngắn | 19/0/1 | 4/1/3 | 46/0/0 | 151 |
| bỏ: quốc hiệu chỉ ở đầu trang | 19/0/1 | 4/1/3 | 46/0/0 | 151 |
| bỏ: tiêu đề phải đầu dòng | 19/1/1 | 4/1/3 | 46/0/0 | 214 |
| không thành phần nào (chỉ khung) | 19/2/1 | 4/2/3 | 46/0/0 | 234 |
| chỉ bật: min_chars (>=50 ký tự) | 19/2/1 | 4/1/3 | 46/0/0 | 233 |
| chỉ bật: trang chỉ chữ ký/trống | 19/1/1 | 4/2/3 | 46/0/0 | 234 |
| chỉ bật: đánh số trang n/m, n>=2 | 19/1/1 | 4/2/3 | 46/0/0 | 215 |
| chỉ bật: tiêu đề lặp ở trang ngắn | 19/2/1 | 4/2/3 | 46/0/0 | 234 |
| chỉ bật: quốc hiệu chỉ ở đầu trang | 19/2/1 | 4/2/3 | 46/0/0 | 234 |
| chỉ bật: tiêu đề phải đầu dòng | 19/1/1 | 4/2/3 | 46/0/0 | 156 |
| nhạy cảm: head_lines=4 | 13/0/7 | 4/1/3 | 46/0/0 | 145 |
| nhạy cảm: head_lines=6 | 19/0/1 | 4/1/3 | 46/0/0 | 151 |
| nhạy cảm: head_lines=8 | 20/1/0 | 4/1/3 | 46/0/0 | 160 |
| nhạy cảm: head_lines=10 | 20/1/0 | 4/1/3 | 46/0/0 | 162 |
| nhạy cảm: min_chars=50 | 19/0/1 | 4/1/3 | 46/0/0 | 151 |
| nhạy cảm: min_chars=150 | 19/0/1 | 4/0/3 | 46/0/0 | 150 |
| nhạy cảm: min_chars=300 | 19/0/1 | 4/0/3 | 46/0/0 | 149 |

## Phân tích lỗi còn lại của rule v2 (5 kiểu đông nhất)

| # | loại lỗi | nhóm | lý do (dấu hiệu trên trang) | loại trang | số lần | ví dụ (doc_id:trang) |
|---|---|---|---|---|---|---|
| 1 | tách nhầm (FP) | negative | quốc hiệu ở đầu trang | HO_SO_QUAN_LY_PCCC | 66 | 1983c7d32e67:2, 1983c7d32e67:3, 1983c7d32e67:5 |
| 2 | tách nhầm (FP) | negative | quốc hiệu ở đầu trang, tiêu đề đầu dòng 'GIẤY CHỨNG NHẬN' | CC_TAP_HUAN_VC_HNH | 14 | 10bea683d0fd:2, 1195238c05fa:2, 233f9b02a4c3:2 |
| 3 | tách nhầm (FP) | negative | quốc hiệu ở đầu trang, tiêu đề đầu dòng 'BIÊN BẢN' | HO_SO_QUAN_LY_PCCC | 14 | 1983c7d32e67:23, 1983c7d32e67:25, 1983c7d32e67:27 |
| 4 | tách nhầm (FP) | negative | tiêu đề đầu dòng 'GIẤY CHỨNG NHẬN' | GCN_DDK_BAN_LE_XD | 11 | 13b82b3e383e:2, 41265fcefd36:2, 547141773252:2 |
| 5 | tách nhầm (FP) | negative | tiêu đề đầu dòng 'BIÊN BẢN' | HD_MUON_BON | 8 | 3376b0c936f1:3, 3376b0c936f1:5, 5b84a6c30d75:3 |

(tổng: 152 tách nhầm, 4 sót; 26 kiểu lỗi khác nhau; bảng liệt kê 5 kiểu đông nhất)

### Chỉ trong các nhóm composite (sót / tách nhầm)

| # | loại lỗi | nhóm | lý do (dấu hiệu trên trang) | loại trang | số lần | ví dụ (doc_id:trang) |
|---|---|---|---|---|---|---|
| 1 | sót ranh giới (FN) | same_other | không có dấu hiệu luật | BIEN_NHAN_THE_CHAP_PT | 2 | 4ad1c01d6262:2, 898572a6f361:2 |
| 2 | sót ranh giới (FN) | same_other | không có dấu hiệu luật | HOA_DON | 1 | 36aff038b19e:3 |
| 3 | tách nhầm (FP) | same_other | quốc hiệu ở đầu trang, tiêu đề đầu dòng 'GIẤY CHỨNG NHẬN' | CC_NGHIEP_VU_BVMT | 1 | 72449aceeff3:2 |
| 4 | sót ranh giới (FN) | mixed | không có dấu hiệu luật | BB_LAY_MAU | 1 | 9c00a14eed6b:3 |

(tổng: 1 tách nhầm, 4 sót; 4 kiểu lỗi khác nhau; bảng liệt kê 4 kiểu đông nhất)

## Cách đọc kết quả (nhận xét của người viết, mọi số lấy từ các bảng trên)

1. **Cải thiện thật nhưng chỉ trên mẫu âm.** Tách nhầm giảm từ 46,71 xuống 30,14 trên 100 vị trí; chênh ghép cặp -16,6 [-23,7; -11,1] điểm, CI không chứa 0, nên đây là cải thiện **tách được**. Số tệp nguyên vẹn (exact-segment) tăng 50/155 lên 85/155. Phần lớn lợi ích đến từ MỘT thay đổi: tiêu đề phải mở đầu một dòng trong 6 dòng đầu (ablation: tắt riêng thành phần này làm FP của mẫu âm từ 151 lên 214; chỉ bật riêng thành phần này đưa FP từ 234 xuống 156).
2. **Trên các nhóm composite thì KHÔNG tách được** (tất cả CI ghép cặp chứa 0, vì chỉ 8 / 6 / 5 tệp và 20 / 7 / 46 ranh giới): composite khác loại F1 0,927 lên 0,974 (tách nhầm 2 lần về 0 lần, tức trang chữ ký "2/2" của `9f4c4dae0c73` và `87c88bf6d0f1` trang 2 đã hết bị tách), nhóm cùng loại ngoài BB_LAY_MAU vẫn 4/7 ranh giới, nhóm BB_LAY_MAU không đổi (46/46).
3. **Bốn "van" còn lại (>= 50 ký tự, trang chỉ chữ ký, đánh số trang n/m với n >= 2, tiêu đề lặp ở trang ngắn) không có tác dụng đo được riêng lẻ** trên dữ liệu dev (ablation: bỏ từng cái thay đổi tối đa 4 FP trong 501 vị trí; chúng chồng lấn nhau, ví dụ trang "2/2" bị chặn bởi cả van đánh số trang lẫn van trang chữ ký). Tôi giữ chúng vì chúng là quy tắc của hướng dẫn gán nhãn (mục 7.2) và có test đơn vị (`tests/test_boundary_detector.py`), không vì số đo trên dev chứng minh chúng.
4. **Phần lỗi còn lại không sửa được bằng luật cục bộ.** 66 + 14 trong 152 tách nhầm còn lại nằm ở tập hồ sơ PCCC (`HO_SO_QUAN_LY_PCCC`: mỗi tiêu đề con có quốc hiệu và tiêu đề riêng ở đầu trang), 14 ở mặt trong thẻ chứng chỉ có quốc hiệu (`CC_TAP_HUAN_VC_HNH`). Về hình thức các trang này giống hệt trang mở đầu của một giấy `BB_LAY_MAU` trong tệp ghép: muốn phân biệt phải biết LOẠI tài liệu (tập hồ sơ thì không tách, biên bản lấy mẫu thì tách), tức cần thông tin ngoài một trang. Đây là lý do có phương pháp (b) và (c) ở các thí nghiệm sau.
5. **Nhóm cùng loại ngoài BB_LAY_MAU vẫn sót 3/7** (2 giấy biên nhận thế chấp, 1 hóa đơn): hai trang cùng mẫu không có dấu hiệu luật nào để tách. Một tách nhầm mới xuất hiện ở đó với `min_chars = 50` (`72449aceeff3` trang 2, mặt trong thẻ dài 114 ký tự, bị tách; với `min_chars = 150` hoặc 300 thì không, xem dòng "nhạy cảm"). Không chọn lại ngưỡng theo con số này: sự khác biệt là một vị trí.

### Giới hạn

- Tham số (`head_lines = 6`, `min_chars = 50`, bộ từ khóa tiêu đề giữ nguyên bản cũ) được chọn tay SAU KHI xem lỗi của baseline trên phạm vi dev; không có tập giữ ngoài cho luật. Con số trên dev hơi lạc quan; lần chấm một lần có TEST là `--scope all --final-test` (`RESULTS_all_incl_test_docs.md`).
- Bộ luật đã sửa cho `boundary_method = "rule_v2"`; `boundary_confidence` vẫn là cờ luật 0,95, không phải xác suất.
- Đáp án là `boundary_gold_v0` (chưa người kiểm, xem `gold/README.md`).
