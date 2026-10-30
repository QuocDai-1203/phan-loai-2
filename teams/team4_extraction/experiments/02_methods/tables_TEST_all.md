### Kết quả TEST (đáp án: `all`)

Số đơn vị: 22 (CC_TAP_HUAN_VC_HNH 5, GCN_DDK_BAN_LE_XD 6, HD_MUA_BAN 6, PHIEU_XUAT_KHO 5). Khoảng tin cậy 95%: bootstrap percentile theo đơn vị. `F1 chặt` = so sánh sau chuẩn hóa; `F1 mềm` = như chặt nhưng văn bản bỏ dấu/dấu câu, chứa nhau, 'tên + MST' khớp theo tên. 

#### A. Tổng quan theo phương pháp × nguồn văn bản

| cấu hình | n | F1 chặt (toàn bộ trường) | F1 mềm | F1 ngày | F1 số | F1 mã | F1 văn bản chặt | F1 văn bản mềm | đúng mọi trường bắt buộc (chặt) | (mềm) | hạn: đúng | hạn: bỏ trống | hạn: **sai giá trị** | n hạn |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| regex@ocr_v2 | 22 | 0.64 [0.51; 0.75] | 0.83 [0.74; 0.91] | 0.91 | 1.00 | 0.92 | 0.33 | 0.73 | 0.27 (6/22) | 0.59 | 0.81 [0.61; 1.00] | 0.12 [0.00; 0.29] | 0.06 [0.00; 0.20] | 16 |
| regex@ocr_llm_haiku | 22 | 0.67 [0.62; 0.71] | 0.87 [0.81; 0.92] | 0.97 | n/a | 0.80 | 0.52 | 0.92 | 0.36 (8/22) | 0.50 | 0.94 [0.80; 1.00] | 0.06 [0.00; 0.20] | 0.00 [0.00; 0.00] | 16 |
| regex@text_layer | 5 | 0.90 [0.87; 0.93] | 1.00 [1.00; 1.00] | 1.00 | 1.00 | 1.00 | 0.72 | 1.00 | 0.00 (0/5) | 1.00 | n/a | n/a | n/a | 0 |
| filename | 22 | 0.11 [0.07; 0.16] | 0.11 [0.07; 0.16] | 0.39 | n/a | n/a | n/a | n/a | 0.00 (0/22) | 0.00 | 0.75 [0.53; 0.94] | 0.12 [0.00; 0.31] | 0.12 [0.00; 0.31] | 16 |
| gliner@ocr_v2 | 22 | 0.31 [0.23; 0.41] | 0.46 [0.39; 0.52] | 0.93 | n/a | n/a | 0.02 | 0.33 | 0.00 (0/22) | 0.00 | 0.88 [0.70; 1.00] | 0.06 [0.00; 0.20] | 0.06 [0.00; 0.20] | 16 |
| gliner@ocr_llm_haiku | 22 | 0.32 [0.26; 0.41] | 0.46 [0.42; 0.51] | 0.77 | n/a | n/a | 0.15 | 0.45 | 0.00 (0/22) | 0.00 | 0.69 [0.47; 0.88] | 0.00 [0.00; 0.00] | 0.31 [0.12; 0.53] | 16 |
| gliner@text_layer | 5 | 0.12 [0.12; 0.12] | 0.35 [0.35; 0.35] | 1.00 | n/a | n/a | n/a | 0.57 | 0.00 (0/5) | 0.00 | n/a | n/a | n/a | 0 |
| llm@ocr_v2 | 22 | 0.71 [0.58; 0.81] | 0.89 [0.81; 0.95] | 0.90 | 1.00 | 0.95 | 0.46 | 0.84 | 0.50 (11/22) | 0.73 | 0.81 [0.60; 1.00] | 0.12 [0.00; 0.30] | 0.06 [0.00; 0.20] | 16 |
| llm@ocr_llm_haiku | 22 | 0.76 [0.69; 0.83] | 0.90 [0.86; 0.94] | 0.96 | 0.27 | 0.95 | 0.67 | 0.95 | 0.73 (16/22) | 0.91 | 0.94 [0.80; 1.00] | 0.06 [0.00; 0.20] | 0.00 [0.00; 0.00] | 16 |
| llm@text_layer | 5 | 0.94 [0.93; 0.97] | 1.00 [1.00; 1.00] | 1.00 | 1.00 | 1.00 | 0.84 | 1.00 | 1.00 (5/5) | 1.00 | n/a | n/a | n/a | 0 |
| vlm | 22 | 0.78 [0.70; 0.86] | 0.91 [0.88; 0.95] | 0.98 | 1.00 | 0.91 | 0.60 | 0.87 | 0.45 (10/22) | 0.68 | 1.00 [1.00; 1.00] | 0.00 [0.00; 0.00] | 0.00 [0.00; 0.00] | 16 |
| cascade regex→llm @ocr_v2 | 22 | 0.66 [0.54; 0.76] | 0.88 [0.80; 0.94] | 0.95 | 1.00 | 0.93 | 0.36 | 0.81 | 0.27 (6/22) | 0.73 | 0.88 [0.70; 1.00] | 0.06 [0.00; 0.20] | 0.06 [0.00; 0.20] | 16 |
| cascade llm→regex @ocr_v2 | 22 | 0.72 [0.59; 0.82] | 0.90 [0.83; 0.96] | 0.92 | 1.00 | 0.95 | 0.48 | 0.86 | 0.50 (11/22) | 0.73 | 0.88 [0.70; 1.00] | 0.06 [0.00; 0.20] | 0.06 [0.00; 0.20] | 16 |
| cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | 22 | 0.72 [0.59; 0.82] | 0.90 [0.83; 0.96] | 0.95 | 1.00 | 0.93 | 0.48 | 0.86 | 0.50 (11/22) | 0.73 | 0.88 [0.70; 1.00] | 0.06 [0.00; 0.20] | 0.06 [0.00; 0.20] | 16 |
| cascade regex→llm→vlm @ocr_v2 | 22 | 0.67 [0.55; 0.77] | 0.89 [0.81; 0.95] | 0.96 | 1.00 | 0.93 | 0.37 | 0.82 | 0.27 (6/22) | 0.73 | 0.94 [0.80; 1.00] | 0.00 [0.00; 0.00] | 0.06 [0.00; 0.20] | 16 |
| cascade + từ chối hạn [any-model=filename] | 22 | 0.71 [0.59; 0.81] | 0.90 [0.83; 0.95] | 0.93 | 1.00 | 0.93 | 0.48 | 0.86 | 0.50 (11/22) | 0.68 | 0.75 [0.53; 0.94] | 0.25 [0.06; 0.47] | 0.00 [0.00; 0.00] | 16 |
| ORACLE: VLM chỉ ở ô mà đáp án ghi viết tay/dưới dấu (không triển khai được) | 22 | 0.73 [0.61; 0.84] | 0.90 [0.83; 0.96] | 0.92 | 1.00 | 0.95 | 0.51 | 0.86 | 0.50 (11/22) | 0.73 | 0.88 [0.70; 1.00] | 0.06 [0.00; 0.20] | 0.06 [0.00; 0.20] | 16 |
| regex@ocr_v2 (cùng tập đơn vị với text_layer) | 5 | 0.90 [0.87; 0.93] | 1.00 [1.00; 1.00] | 1.00 | 1.00 | 1.00 | 0.72 | 1.00 | 0.00 (0/5) | 1.00 | n/a | n/a | n/a | 0 |
| gliner@ocr_v2 (cùng tập đơn vị với text_layer) | 5 | 0.12 [0.12; 0.12] | 0.35 [0.35; 0.35] | 1.00 | n/a | n/a | n/a | 0.57 | 0.00 (0/5) | 0.00 | n/a | n/a | n/a | 0 |
| llm@ocr_v2 (cùng tập đơn vị với text_layer) | 5 | 0.94 [0.93; 0.97] | 1.00 [1.00; 1.00] | 1.00 | 1.00 | 1.00 | 0.84 | 1.00 | 1.00 (5/5) | 1.00 | n/a | n/a | n/a | 0 |

Ghi chú: `F1 ngày` gộp mọi trường kiểu ngày (hạn, ngày cấp, ngày ký...). `n hạn` = số trường hạn có đáp án. `đúng mọi trường bắt buộc` dùng so sánh chặt.

#### B. Theo loại tài liệu (so sánh chặt; trong ngoặc: F1 mềm)

> `CC_TAP_HUAN_VC_HNH` và `PHIEU_XUAT_KHO` gần như MỘT biểu mẫu duy nhất (và phiếu xuất kho là bản số hóa sạch): điểm cao ở hai loại này lạc quan, không suy ra cho biểu mẫu mới.

| loại | cấu hình | n | F1 chặt (mềm) | đúng mọi trường bắt buộc | hạn: đúng / bỏ trống / **sai** (n) |
|---|---|---|---|---|---|
| CC_TAP_HUAN_VC_HNH | regex@ocr_v2 | 5 | 0.68 (0.77) | 1.00 (5/5); mềm 1.00 | 1.00 / 0.00 / 0.00 (5) |
| CC_TAP_HUAN_VC_HNH | gliner@ocr_v2 | 5 | 0.58 (0.69) | 0.00 (0/5); mềm 0.00 | 1.00 / 0.00 / 0.00 (5) |
| CC_TAP_HUAN_VC_HNH | llm@ocr_v2 | 5 | 0.87 (0.99) | 1.00 (5/5); mềm 1.00 | 1.00 / 0.00 / 0.00 (5) |
| CC_TAP_HUAN_VC_HNH | vlm | 5 | 1.00 (1.00) | 1.00 (5/5); mềm 1.00 | 1.00 / 0.00 / 0.00 (5) |
| CC_TAP_HUAN_VC_HNH | cascade regex→llm @ocr_v2 | 5 | 0.75 (0.90) | 1.00 (5/5); mềm 1.00 | 1.00 / 0.00 / 0.00 (5) |
| CC_TAP_HUAN_VC_HNH | cascade llm→regex @ocr_v2 | 5 | 0.87 (0.99) | 1.00 (5/5); mềm 1.00 | 1.00 / 0.00 / 0.00 (5) |
| CC_TAP_HUAN_VC_HNH | cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | 5 | 0.87 (0.99) | 1.00 (5/5); mềm 1.00 | 1.00 / 0.00 / 0.00 (5) |
| CC_TAP_HUAN_VC_HNH | cascade regex→llm→vlm @ocr_v2 | 5 | 0.77 (0.91) | 1.00 (5/5); mềm 1.00 | 1.00 / 0.00 / 0.00 (5) |
| CC_TAP_HUAN_VC_HNH | cascade + từ chối hạn [any-model=filename] | 5 | 0.87 (0.99) | 1.00 (5/5); mềm 1.00 | 1.00 / 0.00 / 0.00 (5) |
| GCN_DDK_BAN_LE_XD | regex@ocr_v2 | 6 | 0.34 (0.65) | 0.17 (1/6); mềm 0.17 | 0.67 / 0.17 / 0.17 (6) |
| GCN_DDK_BAN_LE_XD | gliner@ocr_v2 | 6 | 0.21 (0.35) | 0.00 (0/6); mềm 0.00 | 0.67 / 0.17 / 0.17 (6) |
| GCN_DDK_BAN_LE_XD | llm@ocr_v2 | 6 | 0.36 (0.73) | 0.17 (1/6); mềm 0.33 | 0.67 / 0.17 / 0.17 (6) |
| GCN_DDK_BAN_LE_XD | vlm | 6 | 0.56 (0.88) | 0.50 (3/6); mềm 0.67 | 1.00 / 0.00 / 0.00 (6) |
| GCN_DDK_BAN_LE_XD | cascade regex→llm @ocr_v2 | 6 | 0.34 (0.67) | 0.17 (1/6); mềm 0.33 | 0.67 / 0.17 / 0.17 (6) |
| GCN_DDK_BAN_LE_XD | cascade llm→regex @ocr_v2 | 6 | 0.36 (0.73) | 0.17 (1/6); mềm 0.33 | 0.67 / 0.17 / 0.17 (6) |
| GCN_DDK_BAN_LE_XD | cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | 6 | 0.38 (0.75) | 0.17 (1/6); mềm 0.33 | 0.67 / 0.17 / 0.17 (6) |
| GCN_DDK_BAN_LE_XD | cascade regex→llm→vlm @ocr_v2 | 6 | 0.37 (0.69) | 0.17 (1/6); mềm 0.33 | 0.83 / 0.00 / 0.17 (6) |
| GCN_DDK_BAN_LE_XD | cascade + từ chối hạn [any-model=filename] | 6 | 0.38 (0.76) | 0.17 (1/6); mềm 0.17 | 0.67 / 0.33 / 0.00 (6) |
| HD_MUA_BAN | regex@ocr_v2 | 6 | 0.53 (0.80) | 0.00 (0/6); mềm 0.33 | 0.80 / 0.20 / 0.00 (5) |
| HD_MUA_BAN | gliner@ocr_v2 | 6 | 0.47 (0.51) | 0.00 (0/6); mềm 0.00 | 1.00 / 0.00 / 0.00 (5) |
| HD_MUA_BAN | llm@ocr_v2 | 6 | 0.59 (0.81) | 0.00 (0/6); mềm 0.67 | 0.80 / 0.20 / 0.00 (5) |
| HD_MUA_BAN | vlm | 6 | 0.75 (0.92) | 0.33 (2/6); mềm 1.00 | 1.00 / 0.00 / 0.00 (5) |
| HD_MUA_BAN | cascade regex→llm @ocr_v2 | 6 | 0.57 (0.91) | 0.00 (0/6); mềm 0.67 | 1.00 / 0.00 / 0.00 (5) |
| HD_MUA_BAN | cascade llm→regex @ocr_v2 | 6 | 0.66 (0.89) | 0.00 (0/6); mềm 0.67 | 1.00 / 0.00 / 0.00 (5) |
| HD_MUA_BAN | cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | 6 | 0.64 (0.86) | 0.00 (0/6); mềm 0.67 | 1.00 / 0.00 / 0.00 (5) |
| HD_MUA_BAN | cascade regex→llm→vlm @ocr_v2 | 6 | 0.57 (0.91) | 0.00 (0/6); mềm 0.67 | 1.00 / 0.00 / 0.00 (5) |
| HD_MUA_BAN | cascade + từ chối hạn [any-model=filename] | 6 | 0.60 (0.84) | 0.00 (0/6); mềm 0.67 | 0.60 / 0.40 / 0.00 (5) |
| PHIEU_XUAT_KHO | regex@ocr_v2 | 5 | 0.90 (1.00) | 0.00 (0/5); mềm 1.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | gliner@ocr_v2 | 5 | 0.12 (0.35) | 0.00 (0/5); mềm 0.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | llm@ocr_v2 | 5 | 0.94 (1.00) | 1.00 (5/5); mềm 1.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | vlm | 5 | 0.86 (0.89) | 0.00 (0/5); mềm 0.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | cascade regex→llm @ocr_v2 | 5 | 0.90 (1.00) | 0.00 (0/5); mềm 1.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | cascade llm→regex @ocr_v2 | 5 | 0.94 (1.00) | 1.00 (5/5); mềm 1.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | 5 | 0.94 (1.00) | 1.00 (5/5); mềm 1.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | cascade regex→llm→vlm @ocr_v2 | 5 | 0.90 (1.00) | 0.00 (0/5); mềm 1.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | cascade + từ chối hạn [any-model=filename] | 5 | 0.94 (1.00) | 1.00 (5/5); mềm 1.00 | (không có trường hạn) |

#### C. Cái giá của OCR: cùng phương pháp, khác nguồn văn bản

`ocr_llm_haiku` chỉ có 2 trang đầu của tệp và đáp án ở trang > 2 bị loại khỏi điểm (cho công bằng); nguồn này KHÔNG chạy được on-premise (cận trên). `text_layer` chỉ có ở trang số hóa nên chấm trên tập con các đơn vị có chữ thật; cột cuối là chính phương pháp đó trên OCR cục bộ ở CÙNG tập con.

| phương pháp | nguồn | n | F1 chặt | F1 mềm | F1 ngày | F1 mã | F1 văn bản mềm | hạn đúng / **sai** (n) |
|---|---|---|---|---|---|---|---|---|
| regex | ocr_v2 | 22 | 0.64 [0.51; 0.75] | 0.83 [0.74; 0.91] | 0.91 | 0.92 | 0.73 | 0.81 / 0.06 (16) |
| regex | ocr_llm_haiku | 22 | 0.67 [0.62; 0.71] | 0.87 [0.81; 0.92] | 0.97 | 0.80 | 0.92 | 0.94 / 0.00 (16) |
| regex | text_layer | 5 | 0.90 [0.87; 0.93] | 1.00 [1.00; 1.00] | 1.00 | 1.00 | 1.00 | n/a / n/a (0) |
| regex | ocr_v2 (cùng tập đơn vị với text_layer) | 5 | 0.90 [0.87; 0.93] | 1.00 [1.00; 1.00] | 1.00 | 1.00 | 1.00 | n/a / n/a (0) |
| gliner | ocr_v2 | 22 | 0.31 [0.23; 0.41] | 0.46 [0.39; 0.52] | 0.93 | n/a | 0.33 | 0.88 / 0.06 (16) |
| gliner | ocr_llm_haiku | 22 | 0.32 [0.26; 0.41] | 0.46 [0.42; 0.51] | 0.77 | n/a | 0.45 | 0.69 / 0.31 (16) |
| gliner | text_layer | 5 | 0.12 [0.12; 0.12] | 0.35 [0.35; 0.35] | 1.00 | n/a | 0.57 | n/a / n/a (0) |
| gliner | ocr_v2 (cùng tập đơn vị với text_layer) | 5 | 0.12 [0.12; 0.12] | 0.35 [0.35; 0.35] | 1.00 | n/a | 0.57 | n/a / n/a (0) |
| llm | ocr_v2 | 22 | 0.71 [0.58; 0.81] | 0.89 [0.81; 0.95] | 0.90 | 0.95 | 0.84 | 0.81 / 0.06 (16) |
| llm | ocr_llm_haiku | 22 | 0.76 [0.69; 0.83] | 0.90 [0.86; 0.94] | 0.96 | 0.95 | 0.95 | 0.94 / 0.00 (16) |
| llm | text_layer | 5 | 0.94 [0.93; 0.97] | 1.00 [1.00; 1.00] | 1.00 | 1.00 | 1.00 | n/a / n/a (0) |
| llm | ocr_v2 (cùng tập đơn vị với text_layer) | 5 | 0.94 [0.93; 0.97] | 1.00 [1.00; 1.00] | 1.00 | 1.00 | 1.00 | n/a / n/a (0) |

#### D. Theo mực viết của đáp án silver (trường có đáp án; so sánh mềm)

Mực do người chú thích ghi (Haiku là chính), nên có thể sai. Chỉ tính trường có giá trị trong đáp án.

| cấu hình | mực | n trường | đúng | bỏ trống | **sai giá trị** |
|---|---|---|---|---|---|
| regex@ocr_v2 | printed | 193 | 0.79 | 0.12 | 0.08 |
| regex@ocr_v2 | handwritten | 2 | 0.50 | 0.00 | 0.50 |
| regex@ocr_v2 | under_stamp | 6 | 0.50 | 0.33 | 0.17 |
| gliner@ocr_v2 | printed | 193 | 0.31 | 0.66 | 0.03 |
| gliner@ocr_v2 | handwritten | 2 | 0.50 | 0.50 | 0.00 |
| gliner@ocr_v2 | under_stamp | 6 | 0.00 | 1.00 | 0.00 |
| llm@ocr_v2 | printed | 193 | 0.87 | 0.06 | 0.07 |
| llm@ocr_v2 | handwritten | 2 | 0.00 | 0.00 | 1.00 |
| llm@ocr_v2 | under_stamp | 6 | 1.00 | 0.00 | 0.00 |
| vlm | printed | 193 | 0.89 | 0.05 | 0.06 |
| vlm | handwritten | 2 | 0.50 | 0.00 | 0.50 |
| vlm | under_stamp | 6 | 1.00 | 0.00 | 0.00 |
| cascade regex→llm @ocr_v2 | printed | 193 | 0.88 | 0.03 | 0.10 |
| cascade regex→llm @ocr_v2 | handwritten | 2 | 0.50 | 0.00 | 0.50 |
| cascade regex→llm @ocr_v2 | under_stamp | 6 | 0.83 | 0.00 | 0.17 |
| cascade llm→regex @ocr_v2 | printed | 193 | 0.90 | 0.03 | 0.07 |
| cascade llm→regex @ocr_v2 | handwritten | 2 | 0.00 | 0.00 | 1.00 |
| cascade llm→regex @ocr_v2 | under_stamp | 6 | 1.00 | 0.00 | 0.00 |
| cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | printed | 193 | 0.90 | 0.03 | 0.08 |
| cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | handwritten | 2 | 0.50 | 0.00 | 0.50 |
| cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | under_stamp | 6 | 1.00 | 0.00 | 0.00 |
| cascade regex→llm→vlm @ocr_v2 | printed | 193 | 0.89 | 0.01 | 0.10 |
| cascade regex→llm→vlm @ocr_v2 | handwritten | 2 | 0.50 | 0.00 | 0.50 |
| cascade regex→llm→vlm @ocr_v2 | under_stamp | 6 | 0.83 | 0.00 | 0.17 |
| cascade + từ chối hạn [any-model=filename] | printed | 193 | 0.89 | 0.04 | 0.07 |
| cascade + từ chối hạn [any-model=filename] | handwritten | 2 | 0.50 | 0.00 | 0.50 |
| cascade + từ chối hạn [any-model=filename] | under_stamp | 6 | 1.00 | 0.00 | 0.00 |
| ORACLE: VLM chỉ ở ô mà đáp án ghi viết tay/dưới dấu (không triển khai được) | printed | 193 | 0.90 | 0.03 | 0.08 |
| ORACLE: VLM chỉ ở ô mà đáp án ghi viết tay/dưới dấu (không triển khai được) | handwritten | 2 | 0.50 | 0.00 | 0.50 |
| ORACLE: VLM chỉ ở ô mà đáp án ghi viết tay/dưới dấu (không triển khai được) | under_stamp | 6 | 1.00 | 0.00 | 0.00 |

#### E. Trường hạn: quy tắc tự nhận / từ chối

Mỗi quy tắc chỉ TỰ NHẬN một ngày khi các nguồn đồng thuận, ngược lại từ chối (chuyển người duyệt). `sai` gồm cả trường hợp giấy không ghi hạn mà quy tắc vẫn ra ngày. Cận trên là Clopper-Pearson MỘT PHÍA 95% của tỉ lệ sai trong số đã tự nhận. Để KHẲNG ĐỊNH tỉ lệ sai <= 1% với 0 lỗi quan sát cần tối thiểu 299 lần tự nhận đúng (<= 2%: 149; <= 5%: 59).

Quy tắc được chọn trên DEV: **any-model=filename**.

| quy tắc | tự nhận | đúng | sai | trong đó 'giấy không có hạn' | tự động hóa (đúng / có hạn thật) | tỉ lệ sai | cận trên 95% |
|---|---|---|---|---|---|---|---|
| regex | 14 | 13 | 1 | 0 | 0.81 (13/16) | 0.07 | 0.30 |
| llm | 14 | 13 | 1 | 0 | 0.81 (13/16) | 0.07 | 0.30 |
| vlm | 16 | 16 | 0 | 0 | 1.00 (16/16) | 0.00 | 0.17 |
| filename | 15 | 12 | 3 | 1 | 0.75 (12/16) | 0.20 | 0.44 |
| regex=llm | 13 | 12 | 1 | 0 | 0.75 (12/16) | 0.08 | 0.32 |
| llm=vlm | 13 | 13 | 0 | 0 | 0.81 (13/16) | 0.00 | 0.21 |
| regex=vlm | 13 | 13 | 0 | 0 | 0.81 (13/16) | 0.00 | 0.21 |
| regex=llm=vlm | 12 | 12 | 0 | 0 | 0.75 (12/16) | 0.00 | 0.22 |
| 2-of-3 (regex,llm,vlm) | 15 | 14 | 1 | 0 | 0.88 (14/16) | 0.07 | 0.28 |
| vlm=filename | 12 | 12 | 0 | 0 | 0.75 (12/16) | 0.00 | 0.22 |
| llm=filename | 9 | 9 | 0 | 0 | 0.56 (9/16) | 0.00 | 0.28 |
| regex=filename | 10 | 10 | 0 | 0 | 0.62 (10/16) | 0.00 | 0.26 |
| 2-of-4 (regex,llm,vlm,filename) | 15 | 15 | 0 | 0 | 0.94 (15/16) | 0.00 | 0.18 |
| (llm=vlm) or (any-two incl. filename) | 15 | 15 | 0 | 0 | 0.94 (15/16) | 0.00 | 0.18 |
| (regex=vlm) or (llm=vlm) or (any OCR-method = filename) | 14 | 14 | 0 | 0 | 0.88 (14/16) | 0.00 | 0.19 |
| **any-model=filename** | 12 | 12 | 0 | 0 | 0.75 (12/16) | 0.00 | 0.22 |
| (llm=vlm) or any-model=filename | 16 | 16 | 0 | 0 | 1.00 (16/16) | 0.00 | 0.17 |

Chuyển người duyệt theo quy tắc đã chọn: 5 trường hạn (trong đó 4 có hạn thật); có gợi ý (luật, rồi LLM, rồi VLM): 4, gợi ý đúng 4; gợi ý ra ngày dù giấy không ghi hạn: 0. Người duyệt chỉ cần xác nhận/sửa chứ không phải đọc từ đầu.

#### F. Độ trễ mỗi đơn vị (đo khi GPU/Ollama đang dùng chung với việc khác)

`toàn bộ` gồm cả thời gian Ollama nạp lại mô hình (bị đẩy ra khi tiến trình khác dùng Ollama); `chỉ suy luận` = tổng - nạp mô hình (nếu có ghi).

| cấu hình | n | toàn bộ: trung vị (ms) | p95 (ms) | chỉ suy luận: trung vị (ms) | p95 (ms) |
|---|---|---|---|---|---|
| regex@ocr_v2 | 22 | 5 | 24 | n/a | n/a |
| regex@ocr_llm_haiku | 22 | 4 | 8 | n/a | n/a |
| regex@text_layer | 5 | 3 | 3 | n/a | n/a |
| filename | 22 | 0 | 0 | n/a | n/a |
| gliner@ocr_v2 | 22 | 10389 | 21283 | n/a | n/a |
| gliner@ocr_llm_haiku | 22 | 10378 | 20513 | n/a | n/a |
| gliner@text_layer | 5 | 8837 | 9508 | n/a | n/a |
| llm@ocr_v2 | 22 | 4177 | 6526 | 4143 | 6493 |
| llm@ocr_llm_haiku | 22 | 4918 | 7951 | 4810 | 7668 |
| llm@text_layer | 5 | 6400 | 6538 | 6385 | 6500 |
| vlm | 22 | 10509 | 12340 | 10160 | 12243 |
| regex@ocr_v2 (cùng tập đơn vị với text_layer) | 5 | 3 | 7 | n/a | n/a |
| gliner@ocr_v2 (cùng tập đơn vị với text_layer) | 5 | 7328 | 7779 | n/a | n/a |
| llm@ocr_v2 (cùng tập đơn vị với text_layer) | 5 | 6400 | 6538 | 6385 | 6500 |

VRAM (nvidia-smi toàn GPU, `ollama ps`), đo sau mỗi cấu hình; GPU còn chạy việc của nhóm khác nên số 'toàn GPU' không phải của riêng phương pháp:

* `llm@ocr_v2` (TEST): GPU dùng 6833 -> 6855 MiB; ollama ps: {"bge-m3:latest": {"size_vram_mib": 633, "size_mib": 633, "context_length": 4096}, "qwen3.5:4b": {"size_vram_mib": 3119, "size_mib": 3119, "context_length": 6144}}
* `gliner@ocr_v2` (TEST): GPU dùng 6833 -> 7152 MiB; ollama ps: {"qwen3.5:4b": {"size_vram_mib": 3323, "size_mib": 3323, "context_length": 12288}, "bge-m3:latest": {"size_vram_mib": 633, "size_mib": 633, "context_length": 4096}}
* `vlm` (TEST): GPU dùng 6855 -> 7154 MiB; ollama ps: {"qwen3.5:4b": {"size_vram_mib": 3323, "size_mib": 3323, "context_length": 12288}, "bge-m3:latest": {"size_vram_mib": 633, "size_mib": 633, "context_length": 4096}}
* `llm@ocr_llm_haiku` (TEST): GPU dùng 7154 -> 6853 MiB; ollama ps: {"bge-m3:latest": {"size_vram_mib": 633, "size_mib": 633, "context_length": 4096}, "qwen3.5:4b": {"size_vram_mib": 3119, "size_mib": 3119, "context_length": 6144}}
* `llm@text_layer` (TEST): GPU dùng 6853 -> 6853 MiB; ollama ps: {"bge-m3:latest": {"size_vram_mib": 633, "size_mib": 633, "context_length": 4096}, "qwen3.5:4b": {"size_vram_mib": 3119, "size_mib": 3119, "context_length": 6144}}
* `gliner@ocr_llm_haiku` (TEST): GPU dùng 7152 -> 6853 MiB; ollama ps: {"bge-m3:latest": {"size_vram_mib": 633, "size_mib": 633, "context_length": 4096}, "qwen3.5:4b": {"size_vram_mib": 3119, "size_mib": 3119, "context_length": 6144}}
* `gliner@text_layer` (TEST): GPU dùng 6853 -> 6853 MiB; ollama ps: {"bge-m3:latest": {"size_vram_mib": 633, "size_mib": 633, "context_length": 4096}, "qwen3.5:4b": {"size_vram_mib": 3119, "size_mib": 3119, "context_length": 6144}}
