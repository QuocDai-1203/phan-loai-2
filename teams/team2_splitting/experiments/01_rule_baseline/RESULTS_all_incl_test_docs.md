# 01 - Đo bộ luật tách trang hiện có (baseline) - phạm vi `all`

- **ngày chạy (UTC):** 2026-10-12 01:57
- **lệnh:** `.venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/01_rule_baseline/run.py --scope all --final-test`
- **đáp án:** `teams/team2_splitting/gold/boundary_gold_v0.csv` sha1[:10] = `d9a30b5896` (v0, máy, CHƯA người kiểm)
- **nhãn:** `data/labels_v2.csv` sha1[:10] = `eb3348713a`
- **văn bản:** `data/ocr_v2.jsonl` (OCR cục bộ, tối đa 30 trang/tài liệu) sha1[:10] = `ac87a66c25`
- **phạm vi:** **all** = cả tài liệu TEST, chấm MỘT lần với cấu hình đã đóng băng
- **bootstrap:** 2000 lần lấy mẫu lại theo TỆP, seed 20260711, percentile 95%
- **máy:** Windows-11-10.0.26100-SP0, Python 3.13.14
- **mã đo:** `src/splitting/boundary_detector.py::split_document` (không sửa), cổng luật `CascadedClassifier(kev_endpoint=None)` để chấm loại
- **thời gian chạy:** 3.8 s cho 212 tệp (máy đang bận bởi tiến trình khác, chỉ mang tính tham khảo)

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

**composite BB_LAY_MAU** (7 tệp, 55 vị trí, 55 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment (tệp nguyên vẹn) | tách nhầm / 100 vị trí | loại segment (cổng luật) |
|---|---|---|---|---|---|---|
| rule hiện có | 1.000 [1.000; 1.000] (55/55) | 1.000 [1.000; 1.000] (55/55) | 1.000 [1.000; 1.000] | 7/7 = 1.000 (Wilson 0.646; 1.000) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |

**mẫu âm (nhiều trang, không composite)** (191 tệp, 575 vị trí, 0 ranh giới thật)

| phương pháp | tách nhầm / 100 vị trí | tệp có >= 1 tách nhầm | exact-segment (tệp nguyên vẹn) | loại segment (cổng luật) |
|---|---|---|---|---|
| rule hiện có | 48.00 [42.63; 53.99] (276/575) | 125/191 = 0.654 [0.586; 0.717] | 66/191 = 0.346 (Wilson 0.282; 0.415) | 0.764 [0.707; 0.822] (oracle 0.817) |

## Phân tích lỗi (5 kiểu lỗi đông nhất)

| # | loại lỗi | nhóm | lý do (dấu hiệu trên trang) | loại trang | số lần | ví dụ (doc_id:trang) |
|---|---|---|---|---|---|---|
| 1 | tách nhầm (FP) | negative | quốc hiệu (bất kỳ đâu trong trang) | HO_SO_QUAN_LY_PCCC | 93 | 1983c7d32e67:2, 1983c7d32e67:3, 1983c7d32e67:5 |
| 2 | tách nhầm (FP) | negative | quốc hiệu (bất kỳ đâu trong trang) | CC_TAP_HUAN_VC_HNH | 23 | 0a118292b06d:2, 0de59cef5b62:2, 10bea683d0fd:2 |
| 3 | tách nhầm (FP) | negative | tiêu đề 'GIẤY CHỨNG NHẬN' trong 6 dòng đầu | GCN_DDK_BAN_LE_XD | 23 | 13b82b3e383e:2, 151c0df87ab7:2, 27bc11619915:2 |
| 4 | tách nhầm (FP) | negative | tiêu đề 'HỢP ĐỒNG' trong 6 dòng đầu | HD_MUA_BAN | 20 | 2da681df11bc:3, 3f6ee29dea1a:3, 3f6ee29dea1a:7 |
| 5 | tách nhầm (FP) | negative | tiêu đề 'HỢP ĐỒNG' trong 6 dòng đầu | HD_NHUONG_QUYEN_DAI_LY | 17 | 08256d7db7e0:4, 08256d7db7e0:7, 08256d7db7e0:8 |

(tổng: 280 tách nhầm, 4 sót; 45 kiểu lỗi khác nhau; bảng liệt kê 5 kiểu đông nhất)

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
