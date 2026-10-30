# Báo cáo silver v1 (tự sinh bởi merge_silver.py)

> Chỉ có số tổng hợp và mã đơn vị. **Không có giá trị trường nào** (kể cả không có giá trị cá nhân). `agreed_unverified` nghĩa là hai người chú thích giống nhau, KHÔNG phải đã được xác minh.

## 1. Phủ

Đơn vị cần chú thích: 104. Đơn vị đã gộp (có >= 1 người hợp lệ): 104. Đơn vị có >= 2 người hợp lệ: 40.

| người chú thích | hợp lệ | bản ghi lỗi (error) | tệp hỏng (cả đơn vị) | chưa có tệp | đơn vị có trường bị loại |
|---|---|---|---|---|---|
| haiku | 104 | 0 | 0 | 0 | 0 |
| sonnet | 40 | 0 | 0 | 64 | 0 |

Trường bị loại khỏi một người chú thích (mức trường; các trường còn lại của đơn vị vẫn được giữ): không có
Cảnh báo chỉ đếm (dữ liệu giữ nguyên, evidence được cắt còn 12 từ): haiku: evidence_too_long=57; sonnet: evidence_too_long=91

## 2. Trạng thái trường theo loại

| loại | agreed_unverified | needs_human | single_annotator | model_adjudicated | không có bản đọc hợp lệ |
|---|---|---|---|---|---|
| CC_TAP_HUAN_VC_HNH | 83 | 0 | 126 | 7 | 0 |
| GCN_DDK_BAN_LE_XD | 66 | 0 | 151 | 26 | 0 |
| HD_MUA_BAN | 66 | 0 | 174 | 16 | 0 |
| PHIEU_XUAT_KHO | 131 | 0 | 154 | 9 | 0 |

Ghi chú: `model_adjudicated` thay thế trạng thái trước đó của trường (xem mục 6); `agreed_unverified` gồm cả đồng thuận chặt lẫn mềm (mục 3).
Trường có cờ `ink_risk` (chữ viết tay hoặc dưới con dấu theo ít nhất một người): 67 — PHẢI được xem lại dù hai bên đồng thuận.
Số trường người chú thích tự ghi `normalized` lệch kết quả chuẩn hóa của script: 94.

Phân bố `ink` (theo người, trường có giá trị): handwritten=50, printed=1304, under_stamp=29

## 3. Độ đồng thuận giữa hai người theo kiểu trường (Wilson 95%): CHẶT và MỀM cạnh nhau

**Chặt** = bằng nhau sau chuẩn hóa ngày/số/mã/văn bản (NFC, chữ hoa/thường, khoảng trắng) — định nghĩa không đổi. **Mềm** (chỉ khác ở kiểu `text`) = thêm: bỏ dấu tiếng Việt, bỏ dấu câu, chuỗi ngắn nằm trọn trong chuỗi dài, trường 'tên + MST' khớp theo tên. Với date/number/id hai cột giống nhau. Kiểu có dấu `*` là trường PII chỉ ghi có/không. "Mọi cặp" gồm cả cặp cùng `not_present` (dễ phồng); "ít nhất một bên có giá trị" là con số nên nhìn.

| kiểu | cặp (mọi) | chặt | mềm | cặp (ít nhất một bên có giá trị) | chặt | mềm |
|---|---|---|---|---|---|---|
| date | 90 | 0.944 [0.876; 0.976] | 0.944 [0.876; 0.976] | 90 | 0.944 [0.876; 0.976] | 0.944 [0.876; 0.976] |
| date* | 10 | 1.000 [0.722; 1.000] | 1.000 [0.722; 1.000] | 10 | 1.000 [0.722; 1.000] | 1.000 [0.722; 1.000] |
| id | 80 | 0.950 [0.878; 0.980] | 0.950 [0.878; 0.980] | 80 | 0.950 [0.878; 0.980] | 0.950 [0.878; 0.980] |
| number | 30 | 1.000 [0.886; 1.000] | 1.000 [0.886; 1.000] | 30 | 1.000 [0.886; 1.000] | 1.000 [0.886; 1.000] |
| text | 190 | 0.668 [0.599; 0.731] | 0.932 [0.886; 0.960] | 190 | 0.668 [0.599; 0.731] | 0.932 [0.886; 0.960] |

## 4. Kiểm chéo hạn với ngày trong tên tệp (CHỈ kiểm chéo, không phải đáp án)

khớp: 50; **lệch: 4**; tên tệp không có ngày: 28; silver không có hạn đọc được: 1.

Đơn vị lệch (xem lại cả tên tệp lẫn đáp án): 3f6ee29dea1a_0, 640b0f506936_0, 6ac314e2f770_0, 9f5884bcd428_0

## 5. Đơn vị lỗi hoặc tệp hỏng (mức cả đơn vị)

Không có.

## 6. Phân xử bởi người đọc thứ ba (mô hình mạnh hơn; KHÔNG phải người thật)

Mục trong hàng đợi: 58; đã có phán quyết hợp lệ: 58; tệp phân xử hỏng/không hợp lệ: 0. Phán quyết: x_correct=13, y_correct=8, both_equivalent=36, neither=1.

Trường đã phân xử có `review_status = model_adjudicated` (giá trị của người phân xử, không phải `human_verified`).

### Tỉ lệ đọc bị người phân xử coi là SAI, theo người chú thích và kiểu trường (Wilson 95%)

Mẫu là các mục bị đưa vào hàng đợi (bất đồng, rủi ro mực, lệch tên tệp), KHÔNG phải mọi trường: đây là tỉ lệ sai CÓ ĐIỀU KIỆN. Cột "ước lượng toàn bộ" lấy số bản đọc bị coi sai chia cho TẤT CẢ bản đọc của người đó trong tập hai-người-chú-thích, coi mọi trường đồng thuận không phân xử là đúng — là cận DƯỚI của tỉ lệ sai thật (hai mô hình cùng họ có thể cùng sai).

| người chú thích | kiểu | bản đọc đã xét | bị coi sai (có điều kiện) | tổng bản đọc (tập hai người) | ước lượng toàn bộ (cận dưới) |
|---|---|---|---|---|---|
| haiku | date | 21 | 0.286 [0.138; 0.500] (6/21) | 90 | 0.067 [0.031; 0.138] (6/90) |
| haiku | id | 9 | 0.333 [0.121; 0.646] (3/9) | 80 | 0.037 [0.013; 0.105] (3/80) |
| haiku | text | 28 | 0.036 [0.006; 0.177] (1/28) | 190 | 0.005 [0.001; 0.029] (1/190) |
| **haiku** | tất cả | 58 | 0.172 [0.096; 0.289] (10/58) | 400 | 0.025 [0.014; 0.045] (10/400) |
| sonnet | date | 17 | 0.000 [0.000; 0.184] (0/17) | 90 | 0.000 [0.000; 0.041] (0/90) |
| sonnet | id | 9 | 0.000 [0.000; 0.299] (0/9) | 80 | 0.000 [0.000; 0.046] (0/80) |
| sonnet | text | 28 | 0.286 [0.153; 0.471] (8/28) | 190 | 0.042 [0.021; 0.081] (8/190) |
| **sonnet** | tất cả | 54 | 0.148 [0.077; 0.266] (8/54) | 400 | 0.020 [0.010; 0.039] (8/400) |
