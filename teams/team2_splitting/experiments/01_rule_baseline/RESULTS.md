# 01 - Đo bộ luật tách trang hiện có (baseline) - phạm vi `dev`

- **ngày chạy (UTC):** 2026-10-12 02:14
- **lệnh:** `.venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/01_rule_baseline/run.py`
- **đáp án:** `teams/team2_splitting/gold/boundary_gold_v0.csv` sha1[:10] = `d9a30b5896` (v0, máy, CHƯA người kiểm)
- **nhãn:** `data/labels_v2.csv` sha1[:10] = `eb3348713a`
- **văn bản:** `data/ocr_v2.jsonl` (OCR cục bộ, tối đa 30 trang/tài liệu) sha1[:10] = `ac87a66c25`
- **phạm vi:** **dev** = DEV + EXCLUDED_COMPOSITE (không có tài liệu TEST)
- **bootstrap:** 2000 lần lấy mẫu lại theo TỆP, seed 20260711, percentile 95%
- **máy:** Windows-11-10.0.26100-SP0, Python 3.13.14
- **mã đo:** `src/splitting/boundary_detector.py::split_document` (không sửa), cổng luật `CascadedClassifier(kev_endpoint=None)` để chấm loại
- **thời gian chạy:** 3.7 s cho 174 tệp (máy đang bận bởi tiến trình khác, chỉ mang tính tham khảo)

## Kết quả theo nhóm

Mỗi ô: điểm [CI 95% bootstrap theo tệp]. Kèm tử/mẫu thô. `loại segment` = tỉ lệ segment đáp án mà cổng luật gán đúng loại trên lát cắt dự đoán khớp nhiều trang nhất; `oracle` = cùng phép đo khi cắt đúng đáp án (trần của cổng luật).

**composite khác loại** (8 tệp, 26 vị trí, 20 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment (tệp nguyên vẹn) | tách nhầm / 100 vị trí | loại segment (cổng luật) |
|---|---|---|---|---|---|---|
| rule hiện có | 0.905 [0.778; 1.000] (19/21) | 0.950 [0.850; 1.000] (19/20) | 0.927 [0.850; 1.000] | 5/8 = 0.625 (Wilson 0.306; 0.863) | 7.69 [0.00; 14.29] (2) | 0.643 [0.500; 0.767] (oracle 0.679) |

**composite cùng loại, ngoài BB_LAY_MAU** (6 tệp, 11 vị trí, 7 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment (tệp nguyên vẹn) | tách nhầm / 100 vị trí | loại segment (cổng luật) |
|---|---|---|---|---|---|---|
| rule hiện có | 0.667 [0.333; 1.000] (4/6) | 0.571 [0.167; 0.889] (4/7) | 0.615 [0.222; 0.875] | 2/6 = 0.333 (Wilson 0.097; 0.700) | 18.18 [0.00; 42.90] (2) | 0.615 [0.250; 0.933] (oracle 0.615) |

**composite BB_LAY_MAU** (5 tệp, 46 vị trí, 46 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment (tệp nguyên vẹn) | tách nhầm / 100 vị trí | loại segment (cổng luật) |
|---|---|---|---|---|---|---|
| rule hiện có | 1.000 [1.000; 1.000] (46/46) | 1.000 [1.000; 1.000] (46/46) | 1.000 [1.000; 1.000] | 5/5 = 1.000 (Wilson 0.566; 1.000) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |

**mẫu âm (nhiều trang, không composite)** (155 tệp, 501 vị trí, 0 ranh giới thật)

| phương pháp | tách nhầm / 100 vị trí | tệp có >= 1 tách nhầm | exact-segment (tệp nguyên vẹn) | loại segment (cổng luật) |
|---|---|---|---|---|
| rule hiện có | 46.71 [41.35; 52.80] (234/501) | 105/155 = 0.677 [0.606; 0.755] | 50/155 = 0.323 (Wilson 0.254; 0.400) | 0.768 [0.697; 0.832] (oracle 0.819) |

## Phân tích lỗi (5 kiểu lỗi đông nhất)

| # | loại lỗi | nhóm | lý do (dấu hiệu trên trang) | loại trang | số lần | ví dụ (doc_id:trang) |
|---|---|---|---|---|---|---|
| 1 | tách nhầm (FP) | negative | quốc hiệu (bất kỳ đâu trong trang) | HO_SO_QUAN_LY_PCCC | 80 | 1983c7d32e67:2, 1983c7d32e67:3, 1983c7d32e67:5 |
| 2 | tách nhầm (FP) | negative | tiêu đề 'GIẤY CHỨNG NHẬN' trong 6 dòng đầu | GCN_DDK_BAN_LE_XD | 20 | 13b82b3e383e:2, 151c0df87ab7:2, 3d1e13a23a78:3 |
| 3 | tách nhầm (FP) | negative | quốc hiệu (bất kỳ đâu trong trang) | CC_TAP_HUAN_VC_HNH | 18 | 0a118292b06d:2, 0de59cef5b62:2, 10bea683d0fd:2 |
| 4 | tách nhầm (FP) | negative | tiêu đề 'HỢP ĐỒNG' trong 6 dòng đầu | HD_NHUONG_QUYEN_DAI_LY | 17 | 08256d7db7e0:4, 08256d7db7e0:7, 08256d7db7e0:8 |
| 5 | tách nhầm (FP) | negative | tiêu đề 'HỢP ĐỒNG' trong 6 dòng đầu | HD_MUA_BAN | 14 | 2da681df11bc:3, 4da3d98d6227:3, 4dd7e35bbd9a:3 |

(tổng: 238 tách nhầm, 4 sót; 42 kiểu lỗi khác nhau; bảng liệt kê 5 kiểu đông nhất)

### Chỉ trong ba nhóm composite (nơi có ranh giới thật)

| # | loại lỗi | nhóm | lý do (dấu hiệu trên trang) | loại trang | số lần | ví dụ (doc_id:trang) |
|---|---|---|---|---|---|---|
| 1 | sót ranh giới (FN) | same_other | không có dấu hiệu luật | BIEN_NHAN_THE_CHAP_PT | 2 | 4ad1c01d6262:2, 898572a6f361:2 |
| 2 | sót ranh giới (FN) | same_other | không có dấu hiệu luật | HOA_DON | 1 | 36aff038b19e:3 |
| 3 | tách nhầm (FP) | same_other | quốc hiệu (bất kỳ đâu trong trang) | CC_NGHIEP_VU_BVMT | 1 | 72449aceeff3:2 |
| 4 | tách nhầm (FP) | same_other | tiêu đề 'GIẤY CHỨNG NHẬN' trong 6 dòng đầu | CC_NGHIEP_VU_BVMT | 1 | 72449aceeff3:4 |
| 5 | tách nhầm (FP) | mixed | tiêu đề 'HỢP ĐỒNG' trong 6 dòng đầu | BB_GIAO_NHAN_HANG_HOA | 1 | 87c88bf6d0f1:2 |

(tổng: 4 tách nhầm, 4 sót; 7 kiểu lỗi khác nhau; bảng liệt kê 5 kiểu đông nhất)

## Tệp bị cắt cụt (văn bản OCR chỉ tới trang 30)

`data/ocr_v2.jsonl` chỉ có văn bản tới trang 30. Với các tệp dưới đây phép chấm chỉ dùng các trang có văn bản (cả dự đoán lẫn đáp án bị cắt ở đó); `exact-segment` của tệp là 'đúng trên phần có văn bản'. Không sửa `ocr_v2.jsonl`.

| doc_id | nhóm | số trang thật | số trang có văn bản (được chấm) | ranh giới thật bị bỏ ngoài phép chấm |
|---|---|---|---|---|
| 1983c7d32e67 | negative | 46 | 30 | 0 / 16 vị trí |
| 297c0d94ec78 | negative | 53 | 30 | 0 / 23 vị trí |
| 498cd5744268 | negative | 50 | 30 | 0 / 20 vị trí |
| 5aad587dd02b | negative | 50 | 30 | 0 / 20 vị trí |
| aba856a262ef | same_bb | 93 | 30 | 63 / 63 vị trí |

## Cách đọc kết quả (nhận xét của người viết, mọi số lấy từ các bảng trên)

1. **Bộ luật cũ gần như hoàn hảo ở nơi dễ và tệ ở nơi quan trọng nhất cho vận hành.** Trên 5 tệp `BB_LAY_MAU` (mọi trang đều có quốc hiệu ở đầu) nó bắt 46/46 ranh giới; trên 8 composite khác loại nó bắt 19/20. Nhưng trên 155 tệp nhiều trang KHÔNG ghép nó tách nhầm 234 lần trên 501 vị trí (46,7 lần / 100 vị trí; 105/155 tệp có ít nhất một lần tách nhầm). Nghĩa là gần 2/3 tệp bình thường bị cắt vụn nếu bật luật này làm bước tách tự động. Con số "F1 gộp" nếu tính sẽ trông ổn (vì 46 ranh giới BB_LAY_MAU được bắt hết) và che mất điều này, đó là lý do mọi bảng ở đây chia theo nhóm.
2. **Nguồn tách nhầm** (bảng 5 kiểu lỗi): quốc hiệu xuất hiện "ở bất kỳ đâu" trong trang trên các tập `HO_SO_QUAN_LY_PCCC` (nhiều tiêu đề con, mỗi tiêu đề có quốc hiệu: 80 trong 238 lần), tiêu đề "GIẤY CHỨNG NHẬN", "HỢP ĐỒNG", "ĐƠN ĐẶT HÀNG", "BIÊN BẢN" xuất hiện trong 6 dòng đầu của các trang tiếp nối (đúng bẫy 1 của README), và mặt trong của thẻ chứng chỉ có quốc hiệu (`CC_TAP_HUAN_VC_HNH`, 18 lần).
3. **Lỗi đã biết "trang chữ ký 2/2 lặp tiêu đề" có thật**: `9f4c4dae0c73` trang 2 bị tách nhầm (phiếu xuất kho trang 2/2). Trong nhóm composite khác loại còn một tách nhầm khác (`87c88bf6d0f1` trang 2, tiêu đề "HỢP ĐỒNG" trong biên bản nghiệm thu) và một sót (`9c00a14eed6b` trang 3: OCR làm hỏng quốc hiệu của biên bản lấy mẫu). Cả ba chỉ là 3 sự kiện: khoảng tin cậy của nhóm này rất rộng.
4. **Nhóm cùng loại ngoài BB_LAY_MAU** (6 tệp, 7 ranh giới): luật cũ bắt 4/7. Ba lần sót là các giấy cùng mẫu liên tiếp (hai giấy biên nhận thế chấp phương tiện, một hóa đơn) không có quốc hiệu và tiêu đề trong 6 dòng đầu; luật dựa vào từ khóa không thể thấy "bản khác" nếu hai trang giống nhau về tiêu đề.
5. **Loại segment bằng cổng luật** (`loại segment`): trần khi cắt đúng đáp án (cột `oracle`) đã chỉ là 0,679 (composite khác loại) và 0,819 (mẫu âm), do cổng luật tiêu đề không nhận ra mọi loại. Con số có ý nghĩa cho bộ tách là chênh giữa cột điểm và `oracle`: ở mẫu âm 0,768 so với 0,819, tức việc cắt vụn làm mất khoảng 5 điểm.

### Giới hạn của phép đo này

- Đáp án là `boundary_gold_v0` (một annotator AI xem đủ trang, CHƯA người kiểm; 5 tệp `check_composite` có thể sai). Trong phạm vi `dev` có 3 trong 5 tệp đó là composite khác loại và 2 là cùng loại, nên các nhóm nhỏ nhất chịu rủi ro nhãn nhiều nhất.
- Chỉ 27 ranh giới thật ngoài `BB_LAY_MAU` (trong phạm vi dev: 20 + 7 = 27, vì hai tệp TEST đều là `BB_LAY_MAU`): chênh dưới ~10-15 điểm giữa hai phương pháp không tách được.
- Tệp 93 trang (`aba856a262ef`): văn bản tới trang 30; 63 trong 92 ranh giới của tệp nằm sau trang 30 và KHÔNG được chấm. Số `exact-segment` của tệp đó là "đúng trên 30 trang đầu". Muốn chấm đủ cần chạy lại OCR cho tệp này (việc của nhóm 1 / `scripts/build_ocr_dataset.py`), tôi không sửa `data/ocr_v2.jsonl`.
- Mẫu âm không phải mẫu ngẫu nhiên của dòng chảy thật: nó có các tập hồ sơ PCCC nhiều trang (`HO_SO_QUAN_LY_PCCC`, 7 tài liệu đơn trong DEV; 4 tệp âm bị cắt ở trang 30 như bảng trên), nên tỉ lệ tách nhầm 46,7/100 phụ thuộc vào thành phần này; CI bootstrap theo tệp đã tính đến độ lệch giữa các tệp nhưng không tính đến việc kho mẫu có thể khác kho thật.
- Chưa mở tài liệu TEST ở bước này. Lần chấm một lần có cả tài liệu TEST (cấu hình đã đóng băng) là `--scope all --final-test`, ghi ra `RESULTS_all_incl_test_docs.md`.
