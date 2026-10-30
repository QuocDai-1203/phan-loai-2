# Báo cáo silver v2 - giai đoạn 3 (tự sinh bởi merge_silver.py --version v2)

> Chỉ có số tổng hợp và mã đơn vị. **Không có giá trị trường nào** (kể cả không có giá trị cá nhân). `agreed_unverified` nghĩa là hai người chú thích giống nhau, KHÔNG phải đã được xác minh.

## 1. Phủ

Đơn vị cần chú thích: 84. Đơn vị đã gộp (có >= 1 người hợp lệ): 84. Đơn vị có >= 2 người hợp lệ: 84.

| người chú thích | hợp lệ | bản ghi lỗi (error) | tệp hỏng (cả đơn vị) | chưa có tệp | đơn vị có trường bị loại |
|---|---|---|---|---|---|
| haiku | 84 | 0 | 0 | 0 | 0 |
| sonnet | 84 | 0 | 0 | 0 | 0 |

Trường bị loại khỏi một người chú thích (mức trường; các trường còn lại của đơn vị vẫn được giữ): không có
Cảnh báo chỉ đếm (dữ liệu giữ nguyên, evidence được cắt còn 12 từ): haiku: evidence_too_long=21; sonnet: evidence_too_long=81

## 2. Trạng thái trường theo loại

| loại | agreed_unverified | needs_human | single_annotator | model_adjudicated | không có bản đọc hợp lệ |
|---|---|---|---|---|---|
| BIEN_NHAN_THE_CHAP_PT | 40 | 0 | 0 | 4 | 0 |
| CCCD | 5 | 0 | 0 | 0 | 0 |
| CC_HUAN_LUYEN_PCCC | 17 | 0 | 0 | 7 | 0 |
| CC_NGHIEP_VU_BVMT | 24 | 0 | 0 | 32 | 0 |
| DANG_KY_PHUONG_TIEN | 29 | 0 | 0 | 4 | 0 |
| GCN_ATKT_BVMT_PT | 6 | 0 | 0 | 1 | 0 |
| GCN_BAO_HIEM | 20 | 0 | 0 | 36 | 0 |
| GCN_KIEM_DINH_DO_LUONG | 39 | 0 | 0 | 1 | 0 |
| GIAY_UY_QUYEN | 14 | 0 | 0 | 10 | 0 |
| GPLX | 30 | 0 | 0 | 5 | 0 |
| GP_KD_VAN_TAI | 6 | 0 | 0 | 1 | 0 |
| GP_VC_HANG_NGUY_HIEM | 11 | 0 | 0 | 5 | 0 |
| GXN_THUONG_NHAN_XD | 10 | 0 | 0 | 4 | 0 |
| HD_MUON_BON | 79 | 0 | 0 | 2 | 0 |
| HD_NHUONG_QUYEN_DAI_LY | 34 | 0 | 0 | 1 | 0 |
| HD_THUE_TAI_SAN | 6 | 0 | 0 | 2 | 0 |
| HD_VAN_CHUYEN | 188 | 0 | 0 | 20 | 0 |

Ghi chú: `model_adjudicated` thay thế trạng thái trước đó của trường (xem mục 6); `agreed_unverified` gồm cả đồng thuận chặt lẫn mềm (mục 3).
Trường có cờ `ink_risk` (chữ viết tay hoặc dưới con dấu theo ít nhất một người): 95 — PHẢI được xem lại dù hai bên đồng thuận.
Số trường người chú thích tự ghi `normalized` lệch kết quả chuẩn hóa của script: 31.

Phân bố `ink` (theo người, trường có giá trị): handwritten=166, printed=1064, under_stamp=4

## 3. Độ đồng thuận giữa hai người theo kiểu trường (Wilson 95%): CHẶT và MỀM cạnh nhau

**Chặt** = bằng nhau sau chuẩn hóa ngày/số/mã/văn bản (NFC, chữ hoa/thường, khoảng trắng) — định nghĩa không đổi. **Mềm** (chỉ khác ở kiểu `text`) = thêm: bỏ dấu tiếng Việt, bỏ dấu câu, chuỗi ngắn nằm trọn trong chuỗi dài, trường 'tên + MST' khớp theo tên. Với date/number/id hai cột giống nhau. Kiểu có dấu `*` là trường PII chỉ ghi có/không. "Mọi cặp" gồm cả cặp cùng `not_present` (dễ phồng); "ít nhất một bên có giá trị" là con số nên nhìn.

| kiểu | cặp (mọi) | chặt | mềm | cặp (ít nhất một bên có giá trị) | chặt | mềm |
|---|---|---|---|---|---|---|
| date | 224 | 0.920 [0.877; 0.949] | 0.920 [0.877; 0.949] | 173 | 0.896 [0.842; 0.933] | 0.896 [0.842; 0.933] |
| date* | 16 | 1.000 [0.806; 1.000] | 1.000 [0.806; 1.000] | 16 | 1.000 [0.806; 1.000] | 1.000 [0.806; 1.000] |
| id | 120 | 0.908 [0.843; 0.948] | 0.908 [0.843; 0.948] | 111 | 0.901 [0.831; 0.944] | 0.901 [0.831; 0.944] |
| id* | 6 | 1.000 [0.610; 1.000] | 1.000 [0.610; 1.000] | 6 | 1.000 [0.610; 1.000] | 1.000 [0.610; 1.000] |
| number | 16 | 0.875 [0.640; 0.965] | 0.875 [0.640; 0.965] | 16 | 0.875 [0.640; 0.965] | 0.875 [0.640; 0.965] |
| text | 311 | 0.543 [0.488; 0.598] | 0.923 [0.888; 0.948] | 304 | 0.536 [0.480; 0.591] | 0.924 [0.889; 0.949] |

## 4. Kiểm chéo hạn với ngày trong tên tệp (CHỈ kiểm chéo, không phải đáp án)

khớp: 26; **lệch: 5**; tên tệp không có ngày: 29; silver không có hạn đọc được: 14.

Đơn vị lệch (xem lại cả tên tệp lẫn đáp án): 1d3e3ebf2706_0, 46de162a60f9_0, 5139035b5c3f_0, deab4d6d4713_0, fb2902b6b028_0

## 5. Đơn vị lỗi hoặc tệp hỏng (mức cả đơn vị)

Không có.

## 6. Phân xử bởi người đọc thứ ba (mô hình mạnh hơn; KHÔNG phải người thật)

Mục trong hàng đợi: 135; đã có phán quyết hợp lệ: 135; tệp phân xử hỏng/không hợp lệ: 0. Phán quyết: x_correct=20, y_correct=18, both_equivalent=92, neither=5.

Trường đã phân xử có `review_status = model_adjudicated` (giá trị của người phân xử, không phải `human_verified`).

### Tỉ lệ đọc bị người phân xử coi là SAI, theo người chú thích và kiểu trường (Wilson 95%)

Mẫu là các mục bị đưa vào hàng đợi (bất đồng, rủi ro mực, lệch tên tệp), KHÔNG phải mọi trường: đây là tỉ lệ sai CÓ ĐIỀU KIỆN. Cột "ước lượng toàn bộ" lấy số bản đọc bị coi sai chia cho TẤT CẢ bản đọc của người đó trong tập hai-người-chú-thích, coi mọi trường đồng thuận không phân xử là đúng — là cận DƯỚI của tỉ lệ sai thật (hai mô hình cùng họ có thể cùng sai).

| người chú thích | kiểu | bản đọc đã xét | bị coi sai (có điều kiện) | tổng bản đọc (tập hai người) | ước lượng toàn bộ (cận dưới) |
|---|---|---|---|---|---|
| haiku | date | 44 | 0.250 [0.146; 0.394] (11/44) | 224 | 0.049 [0.028; 0.086] (11/224) |
| haiku | date* | 6 | 0.000 [0.000; 0.390] (0/6) | 16 | 0.000 [0.000; 0.194] (0/16) |
| haiku | id | 24 | 0.333 [0.180; 0.533] (8/24) | 120 | 0.067 [0.034; 0.126] (8/120) |
| haiku | number | 6 | 0.167 [0.030; 0.564] (1/6) | 16 | 0.062 [0.011; 0.283] (1/16) |
| haiku | text | 55 | 0.182 [0.102; 0.303] (10/55) | 311 | 0.032 [0.018; 0.058] (10/311) |
| **haiku** | tất cả | 135 | 0.222 [0.160; 0.299] (30/135) | 693 | 0.043 [0.030; 0.061] (30/693) |
| sonnet | date | 44 | 0.045 [0.013; 0.151] (2/44) | 224 | 0.009 [0.002; 0.032] (2/224) |
| sonnet | date* | 6 | 0.000 [0.000; 0.390] (0/6) | 16 | 0.000 [0.000; 0.194] (0/16) |
| sonnet | id | 24 | 0.167 [0.067; 0.359] (4/24) | 120 | 0.033 [0.013; 0.083] (4/120) |
| sonnet | number | 6 | 0.167 [0.030; 0.564] (1/6) | 16 | 0.062 [0.011; 0.283] (1/16) |
| sonnet | text | 55 | 0.182 [0.102; 0.303] (10/55) | 311 | 0.032 [0.018; 0.058] (10/311) |
| **sonnet** | tất cả | 135 | 0.126 [0.080; 0.192] (17/135) | 693 | 0.025 [0.015; 0.039] (17/693) |
