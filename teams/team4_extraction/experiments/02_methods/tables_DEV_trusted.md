### Kết quả DEV (đáp án: `trusted`)

Số đơn vị: 76 (CC_TAP_HUAN_VC_HNH 19, GCN_DDK_BAN_LE_XD 21, HD_MUA_BAN 26, PHIEU_XUAT_KHO 10). Khoảng tin cậy 95%: bootstrap percentile theo đơn vị. `F1 chặt` = so sánh sau chuẩn hóa; `F1 mềm` = như chặt nhưng văn bản bỏ dấu/dấu câu, chứa nhau, 'tên + MST' khớp theo tên. 

#### A. Tổng quan theo phương pháp × nguồn văn bản

| cấu hình | n | F1 chặt (toàn bộ trường) | F1 mềm | F1 ngày | F1 số | F1 mã | F1 văn bản chặt | F1 văn bản mềm | đúng mọi trường bắt buộc (chặt) | (mềm) | hạn: đúng | hạn: bỏ trống | hạn: **sai giá trị** | n hạn |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| regex@ocr_v2 | 76 | 0.65 [0.56; 0.72] | 0.84 [0.78; 0.89] | 0.90 | 0.86 | 0.94 | 0.35 | 0.76 | 0.22 (7/32) | 0.56 | 0.88 [0.73; 1.00] | 0.08 [0.00; 0.21] | 0.04 [0.00; 0.14] | 25 |
| regex@ocr_llm_haiku | 76 | 0.69 [0.64; 0.73] | 0.89 [0.85; 0.92] | 0.96 | n/a | 0.82 | 0.54 | 0.95 | 0.38 (12/32) | 0.69 | 1.00 [1.00; 1.00] | 0.00 [0.00; 0.00] | 0.00 [0.00; 0.00] | 25 |
| regex@text_layer | 10 | 0.84 [0.76; 0.90] | 0.96 [0.89; 1.00] | 1.00 | 0.86 | 0.99 | 0.66 | 1.00 | 0.00 (0/7) | 1.00 | n/a | n/a | n/a | 0 |
| filename | 76 | 0.10 [0.06; 0.14] | 0.10 [0.06; 0.14] | 0.36 | n/a | n/a | n/a | n/a | 0.03 (1/32) | 0.03 | 0.60 [0.41; 0.79] | 0.36 [0.18; 0.54] | 0.04 [0.00; 0.13] | 25 |
| gliner@ocr_v2 | 76 | 0.33 [0.26; 0.40] | 0.43 [0.38; 0.48] | 0.94 | n/a | n/a | 0.01 | 0.24 | 0.00 (0/32) | 0.00 | 0.88 [0.73; 1.00] | 0.08 [0.00; 0.21] | 0.04 [0.00; 0.14] | 25 |
| gliner@ocr_llm_haiku | 76 | 0.34 [0.28; 0.40] | 0.45 [0.41; 0.49] | 0.76 | n/a | n/a | 0.17 | 0.42 | 0.03 (1/32) | 0.03 | 0.68 [0.50; 0.86] | 0.00 [0.00; 0.00] | 0.32 [0.14; 0.50] | 25 |
| gliner@text_layer | 10 | 0.12 [0.12; 0.12] | 0.35 [0.35; 0.35] | 1.00 | n/a | n/a | n/a | 0.57 | 0.00 (0/7) | 0.00 | n/a | n/a | n/a | 0 |
| llm@ocr_v2 | 76 | 0.70 [0.60; 0.79] | 0.87 [0.80; 0.92] | 0.89 | 0.86 | 0.95 | 0.48 | 0.82 | 0.41 (13/32) | 0.59 | 0.88 [0.73; 1.00] | 0.08 [0.00; 0.21] | 0.04 [0.00; 0.14] | 25 |
| llm@ocr_llm_haiku | 76 | 0.76 [0.70; 0.82] | 0.90 [0.87; 0.93] | 0.96 | 0.10 | 0.97 | 0.68 | 0.96 | 0.62 (20/32) | 0.88 | 1.00 [1.00; 1.00] | 0.00 [0.00; 0.00] | 0.00 [0.00; 0.00] | 25 |
| llm@text_layer | 10 | 0.92 [0.85; 0.97] | 0.97 [0.91; 1.00] | 1.00 | 0.86 | 1.00 | 0.86 | 1.00 | 0.86 (6/7) | 1.00 | n/a | n/a | n/a | 0 |
| vlm | 76 | 0.77 [0.70; 0.82] | 0.91 [0.88; 0.94] | 0.99 | 1.00 | 0.90 | 0.57 | 0.86 | 0.47 (15/32) | 0.72 | 1.00 [1.00; 1.00] | 0.00 [0.00; 0.00] | 0.00 [0.00; 0.00] | 25 |
| cascade regex→llm @ocr_v2 | 76 | 0.66 [0.57; 0.73] | 0.87 [0.80; 0.92] | 0.89 | 0.86 | 0.95 | 0.39 | 0.82 | 0.25 (8/32) | 0.62 | 0.88 [0.73; 1.00] | 0.08 [0.00; 0.21] | 0.04 [0.00; 0.14] | 25 |
| cascade llm→regex @ocr_v2 | 76 | 0.71 [0.61; 0.79] | 0.87 [0.81; 0.92] | 0.86 | 0.86 | 0.95 | 0.51 | 0.85 | 0.41 (13/32) | 0.59 | 0.88 [0.73; 1.00] | 0.08 [0.00; 0.21] | 0.04 [0.00; 0.14] | 25 |
| cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | 76 | 0.72 [0.62; 0.79] | 0.88 [0.82; 0.93] | 0.89 | 0.86 | 0.95 | 0.51 | 0.85 | 0.44 (14/32) | 0.62 | 0.88 [0.73; 1.00] | 0.08 [0.00; 0.21] | 0.04 [0.00; 0.14] | 25 |
| cascade regex→llm→vlm @ocr_v2 | 76 | 0.67 [0.58; 0.74] | 0.87 [0.81; 0.92] | 0.91 | 0.86 | 0.95 | 0.40 | 0.83 | 0.28 (9/32) | 0.66 | 0.96 [0.86; 1.00] | 0.00 [0.00; 0.00] | 0.04 [0.00; 0.14] | 25 |
| cascade + từ chối hạn [any-model=filename] | 76 | 0.70 [0.60; 0.78] | 0.87 [0.81; 0.92] | 0.84 | 0.86 | 0.95 | 0.51 | 0.85 | 0.47 (15/32) | 0.66 | 0.60 [0.41; 0.79] | 0.40 [0.21; 0.59] | 0.00 [0.00; 0.00] | 25 |
| ORACLE: VLM chỉ ở ô mà đáp án ghi viết tay/dưới dấu (không triển khai được) | 76 | 0.74 [0.65; 0.82] | 0.90 [0.85; 0.94] | 0.93 | 0.86 | 0.97 | 0.54 | 0.87 | 0.47 (15/32) | 0.66 | 0.92 [0.79; 1.00] | 0.04 [0.00; 0.13] | 0.04 [0.00; 0.14] | 25 |
| regex@ocr_v2 (cùng tập đơn vị với text_layer) | 10 | 0.84 [0.76; 0.90] | 0.96 [0.89; 1.00] | 1.00 | 0.86 | 0.99 | 0.66 | 1.00 | 0.00 (0/7) | 1.00 | n/a | n/a | n/a | 0 |
| gliner@ocr_v2 (cùng tập đơn vị với text_layer) | 10 | 0.12 [0.12; 0.12] | 0.35 [0.35; 0.35] | 1.00 | n/a | n/a | n/a | 0.57 | 0.00 (0/7) | 0.00 | n/a | n/a | n/a | 0 |
| llm@ocr_v2 (cùng tập đơn vị với text_layer) | 10 | 0.92 [0.85; 0.97] | 0.97 [0.91; 1.00] | 1.00 | 0.86 | 1.00 | 0.86 | 1.00 | 0.86 (6/7) | 1.00 | n/a | n/a | n/a | 0 |

Ghi chú: `F1 ngày` gộp mọi trường kiểu ngày (hạn, ngày cấp, ngày ký...). `n hạn` = số trường hạn có đáp án. `đúng mọi trường bắt buộc` dùng so sánh chặt.

#### B. Theo loại tài liệu (so sánh chặt; trong ngoặc: F1 mềm)

> `CC_TAP_HUAN_VC_HNH` và `PHIEU_XUAT_KHO` gần như MỘT biểu mẫu duy nhất (và phiếu xuất kho là bản số hóa sạch): điểm cao ở hai loại này lạc quan, không suy ra cho biểu mẫu mới.

| loại | cấu hình | n | F1 chặt (mềm) | đúng mọi trường bắt buộc | hạn: đúng / bỏ trống / **sai** (n) |
|---|---|---|---|---|---|
| CC_TAP_HUAN_VC_HNH | regex@ocr_v2 | 19 | 0.65 (0.80) | 0.88 (7/8); mềm 0.88 | 1.00 / 0.00 / 0.00 (8) |
| CC_TAP_HUAN_VC_HNH | gliner@ocr_v2 | 19 | 0.57 (0.62) | 0.00 (0/8); mềm 0.00 | 1.00 / 0.00 / 0.00 (8) |
| CC_TAP_HUAN_VC_HNH | llm@ocr_v2 | 19 | 0.78 (0.91) | 0.88 (7/8); mềm 0.88 | 1.00 / 0.00 / 0.00 (8) |
| CC_TAP_HUAN_VC_HNH | vlm | 19 | 0.98 (0.98) | 1.00 (8/8); mềm 1.00 | 1.00 / 0.00 / 0.00 (8) |
| CC_TAP_HUAN_VC_HNH | cascade regex→llm @ocr_v2 | 19 | 0.73 (0.91) | 1.00 (8/8); mềm 1.00 | 1.00 / 0.00 / 0.00 (8) |
| CC_TAP_HUAN_VC_HNH | cascade llm→regex @ocr_v2 | 19 | 0.78 (0.91) | 0.88 (7/8); mềm 0.88 | 1.00 / 0.00 / 0.00 (8) |
| CC_TAP_HUAN_VC_HNH | cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | 19 | 0.80 (0.93) | 1.00 (8/8); mềm 1.00 | 1.00 / 0.00 / 0.00 (8) |
| CC_TAP_HUAN_VC_HNH | cascade regex→llm→vlm @ocr_v2 | 19 | 0.75 (0.93) | 1.00 (8/8); mềm 1.00 | 1.00 / 0.00 / 0.00 (8) |
| CC_TAP_HUAN_VC_HNH | cascade + từ chối hạn [any-model=filename] | 19 | 0.79 (0.92) | 0.88 (7/8); mềm 0.88 | 0.88 / 0.12 / 0.00 (8) |
| GCN_DDK_BAN_LE_XD | regex@ocr_v2 | 21 | 0.37 (0.66) | 0.00 (0/9); mềm 0.00 | 0.67 / 0.22 / 0.11 (9) |
| GCN_DDK_BAN_LE_XD | gliner@ocr_v2 | 21 | 0.24 (0.27) | 0.00 (0/9); mềm 0.00 | 0.67 / 0.22 / 0.11 (9) |
| GCN_DDK_BAN_LE_XD | llm@ocr_v2 | 21 | 0.40 (0.70) | 0.00 (0/9); mềm 0.00 | 0.67 / 0.22 / 0.11 (9) |
| GCN_DDK_BAN_LE_XD | vlm | 21 | 0.62 (0.87) | 0.67 (6/9); mềm 0.78 | 1.00 / 0.00 / 0.00 (9) |
| GCN_DDK_BAN_LE_XD | cascade regex→llm @ocr_v2 | 21 | 0.37 (0.67) | 0.00 (0/9); mềm 0.00 | 0.67 / 0.22 / 0.11 (9) |
| GCN_DDK_BAN_LE_XD | cascade llm→regex @ocr_v2 | 21 | 0.40 (0.70) | 0.00 (0/9); mềm 0.00 | 0.67 / 0.22 / 0.11 (9) |
| GCN_DDK_BAN_LE_XD | cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | 21 | 0.41 (0.71) | 0.00 (0/9); mềm 0.00 | 0.67 / 0.22 / 0.11 (9) |
| GCN_DDK_BAN_LE_XD | cascade regex→llm→vlm @ocr_v2 | 21 | 0.39 (0.68) | 0.11 (1/9); mềm 0.11 | 0.89 / 0.00 / 0.11 (9) |
| GCN_DDK_BAN_LE_XD | cascade + từ chối hạn [any-model=filename] | 21 | 0.41 (0.71) | 0.22 (2/9); mềm 0.22 | 0.67 / 0.33 / 0.00 (9) |
| HD_MUA_BAN | regex@ocr_v2 | 26 | 0.64 (0.87) | 0.00 (0/8); mềm 0.50 | 1.00 / 0.00 / 0.00 (8) |
| HD_MUA_BAN | gliner@ocr_v2 | 26 | 0.47 (0.52) | 0.00 (0/8); mềm 0.00 | 1.00 / 0.00 / 0.00 (8) |
| HD_MUA_BAN | llm@ocr_v2 | 26 | 0.64 (0.85) | 0.00 (0/8); mềm 0.62 | 1.00 / 0.00 / 0.00 (8) |
| HD_MUA_BAN | vlm | 26 | 0.62 (0.91) | 0.12 (1/8); mềm 1.00 | 1.00 / 0.00 / 0.00 (8) |
| HD_MUA_BAN | cascade regex→llm @ocr_v2 | 26 | 0.63 (0.89) | 0.00 (0/8); mềm 0.62 | 1.00 / 0.00 / 0.00 (8) |
| HD_MUA_BAN | cascade llm→regex @ocr_v2 | 26 | 0.67 (0.89) | 0.00 (0/8); mềm 0.62 | 1.00 / 0.00 / 0.00 (8) |
| HD_MUA_BAN | cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | 26 | 0.67 (0.89) | 0.00 (0/8); mềm 0.62 | 1.00 / 0.00 / 0.00 (8) |
| HD_MUA_BAN | cascade regex→llm→vlm @ocr_v2 | 26 | 0.63 (0.89) | 0.00 (0/8); mềm 0.62 | 1.00 / 0.00 / 0.00 (8) |
| HD_MUA_BAN | cascade + từ chối hạn [any-model=filename] | 26 | 0.60 (0.84) | 0.00 (0/8); mềm 0.62 | 0.25 / 0.75 / 0.00 (8) |
| PHIEU_XUAT_KHO | regex@ocr_v2 | 10 | 0.84 (0.96) | 0.00 (0/7); mềm 1.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | gliner@ocr_v2 | 10 | 0.12 (0.35) | 0.00 (0/7); mềm 0.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | llm@ocr_v2 | 10 | 0.92 (0.97) | 0.86 (6/7); mềm 1.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | vlm | 10 | 0.84 (0.90) | 0.00 (0/7); mềm 0.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | cascade regex→llm @ocr_v2 | 10 | 0.85 (0.97) | 0.00 (0/7); mềm 1.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | cascade llm→regex @ocr_v2 | 10 | 0.92 (0.97) | 0.86 (6/7); mềm 1.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | 10 | 0.92 (0.97) | 0.86 (6/7); mềm 1.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | cascade regex→llm→vlm @ocr_v2 | 10 | 0.85 (0.97) | 0.00 (0/7); mềm 1.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | cascade + từ chối hạn [any-model=filename] | 10 | 0.92 (0.97) | 0.86 (6/7); mềm 1.00 | (không có trường hạn) |

#### C. Cái giá của OCR: cùng phương pháp, khác nguồn văn bản

`ocr_llm_haiku` chỉ có 2 trang đầu của tệp và đáp án ở trang > 2 bị loại khỏi điểm (cho công bằng); nguồn này KHÔNG chạy được on-premise (cận trên). `text_layer` chỉ có ở trang số hóa nên chấm trên tập con các đơn vị có chữ thật; cột cuối là chính phương pháp đó trên OCR cục bộ ở CÙNG tập con.

| phương pháp | nguồn | n | F1 chặt | F1 mềm | F1 ngày | F1 mã | F1 văn bản mềm | hạn đúng / **sai** (n) |
|---|---|---|---|---|---|---|---|---|
| regex | ocr_v2 | 76 | 0.65 [0.56; 0.72] | 0.84 [0.78; 0.89] | 0.90 | 0.94 | 0.76 | 0.88 / 0.04 (25) |
| regex | ocr_llm_haiku | 76 | 0.69 [0.64; 0.73] | 0.89 [0.85; 0.92] | 0.96 | 0.82 | 0.95 | 1.00 / 0.00 (25) |
| regex | text_layer | 10 | 0.84 [0.76; 0.90] | 0.96 [0.89; 1.00] | 1.00 | 0.99 | 1.00 | n/a / n/a (0) |
| regex | ocr_v2 (cùng tập đơn vị với text_layer) | 10 | 0.84 [0.76; 0.90] | 0.96 [0.89; 1.00] | 1.00 | 0.99 | 1.00 | n/a / n/a (0) |
| gliner | ocr_v2 | 76 | 0.33 [0.26; 0.40] | 0.43 [0.38; 0.48] | 0.94 | n/a | 0.24 | 0.88 / 0.04 (25) |
| gliner | ocr_llm_haiku | 76 | 0.34 [0.28; 0.40] | 0.45 [0.41; 0.49] | 0.76 | n/a | 0.42 | 0.68 / 0.32 (25) |
| gliner | text_layer | 10 | 0.12 [0.12; 0.12] | 0.35 [0.35; 0.35] | 1.00 | n/a | 0.57 | n/a / n/a (0) |
| gliner | ocr_v2 (cùng tập đơn vị với text_layer) | 10 | 0.12 [0.12; 0.12] | 0.35 [0.35; 0.35] | 1.00 | n/a | 0.57 | n/a / n/a (0) |
| llm | ocr_v2 | 76 | 0.70 [0.60; 0.79] | 0.87 [0.80; 0.92] | 0.89 | 0.95 | 0.82 | 0.88 / 0.04 (25) |
| llm | ocr_llm_haiku | 76 | 0.76 [0.70; 0.82] | 0.90 [0.87; 0.93] | 0.96 | 0.97 | 0.96 | 1.00 / 0.00 (25) |
| llm | text_layer | 10 | 0.92 [0.85; 0.97] | 0.97 [0.91; 1.00] | 1.00 | 1.00 | 1.00 | n/a / n/a (0) |
| llm | ocr_v2 (cùng tập đơn vị với text_layer) | 10 | 0.92 [0.85; 0.97] | 0.97 [0.91; 1.00] | 1.00 | 1.00 | 1.00 | n/a / n/a (0) |

#### D. Theo mực viết của đáp án silver (trường có đáp án; so sánh mềm)

Mực do người chú thích ghi (Haiku là chính), nên có thể sai. Chỉ tính trường có giá trị trong đáp án.

| cấu hình | mực | n trường | đúng | bỏ trống | **sai giá trị** |
|---|---|---|---|---|---|
| regex@ocr_v2 | printed | 259 | 0.83 | 0.10 | 0.07 |
| regex@ocr_v2 | handwritten | 16 | 0.56 | 0.19 | 0.25 |
| regex@ocr_v2 | under_stamp | 10 | 0.50 | 0.30 | 0.20 |
| gliner@ocr_v2 | printed | 259 | 0.29 | 0.68 | 0.04 |
| gliner@ocr_v2 | handwritten | 16 | 0.44 | 0.50 | 0.06 |
| gliner@ocr_v2 | under_stamp | 10 | 0.00 | 1.00 | 0.00 |
| llm@ocr_v2 | printed | 259 | 0.87 | 0.05 | 0.08 |
| llm@ocr_v2 | handwritten | 16 | 0.56 | 0.00 | 0.44 |
| llm@ocr_v2 | under_stamp | 10 | 0.70 | 0.10 | 0.20 |
| vlm | printed | 259 | 0.88 | 0.06 | 0.05 |
| vlm | handwritten | 16 | 0.81 | 0.00 | 0.19 |
| vlm | under_stamp | 10 | 1.00 | 0.00 | 0.00 |
| cascade regex→llm @ocr_v2 | printed | 259 | 0.90 | 0.02 | 0.09 |
| cascade regex→llm @ocr_v2 | handwritten | 16 | 0.56 | 0.00 | 0.44 |
| cascade regex→llm @ocr_v2 | under_stamp | 10 | 0.60 | 0.10 | 0.30 |
| cascade llm→regex @ocr_v2 | printed | 259 | 0.90 | 0.02 | 0.08 |
| cascade llm→regex @ocr_v2 | handwritten | 16 | 0.56 | 0.00 | 0.44 |
| cascade llm→regex @ocr_v2 | under_stamp | 10 | 0.70 | 0.10 | 0.20 |
| cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | printed | 259 | 0.90 | 0.02 | 0.08 |
| cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | handwritten | 16 | 0.62 | 0.00 | 0.38 |
| cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | under_stamp | 10 | 0.70 | 0.10 | 0.20 |
| cascade regex→llm→vlm @ocr_v2 | printed | 259 | 0.91 | 0.00 | 0.09 |
| cascade regex→llm→vlm @ocr_v2 | handwritten | 16 | 0.56 | 0.00 | 0.44 |
| cascade regex→llm→vlm @ocr_v2 | under_stamp | 10 | 0.70 | 0.00 | 0.30 |
| cascade + từ chối hạn [any-model=filename] | printed | 259 | 0.88 | 0.04 | 0.08 |
| cascade + từ chối hạn [any-model=filename] | handwritten | 16 | 0.44 | 0.19 | 0.38 |
| cascade + từ chối hạn [any-model=filename] | under_stamp | 10 | 0.80 | 0.00 | 0.20 |
| ORACLE: VLM chỉ ở ô mà đáp án ghi viết tay/dưới dấu (không triển khai được) | printed | 259 | 0.90 | 0.02 | 0.08 |
| ORACLE: VLM chỉ ở ô mà đáp án ghi viết tay/dưới dấu (không triển khai được) | handwritten | 16 | 0.81 | 0.00 | 0.19 |
| ORACLE: VLM chỉ ở ô mà đáp án ghi viết tay/dưới dấu (không triển khai được) | under_stamp | 10 | 1.00 | 0.00 | 0.00 |

#### E. Trường hạn: quy tắc tự nhận / từ chối

Mỗi quy tắc chỉ TỰ NHẬN một ngày khi các nguồn đồng thuận, ngược lại từ chối (chuyển người duyệt). `sai` gồm cả trường hợp giấy không ghi hạn mà quy tắc vẫn ra ngày. Cận trên là Clopper-Pearson MỘT PHÍA 95% của tỉ lệ sai trong số đã tự nhận. Để KHẲNG ĐỊNH tỉ lệ sai <= 1% với 0 lỗi quan sát cần tối thiểu 299 lần tự nhận đúng (<= 2%: 149; <= 5%: 59).

Quy tắc được chọn trên DEV: **any-model=filename**.

| quy tắc | tự nhận | đúng | sai | trong đó 'giấy không có hạn' | tự động hóa (đúng / có hạn thật) | tỉ lệ sai | cận trên 95% |
|---|---|---|---|---|---|---|---|
| regex | 23 | 22 | 1 | 0 | 0.88 (22/25) | 0.04 | 0.19 |
| llm | 23 | 22 | 1 | 0 | 0.88 (22/25) | 0.04 | 0.19 |
| vlm | 25 | 25 | 0 | 0 | 1.00 (25/25) | 0.00 | 0.11 |
| filename | 17 | 15 | 2 | 1 | 0.60 (15/25) | 0.12 | 0.33 |
| regex=llm | 23 | 22 | 1 | 0 | 0.88 (22/25) | 0.04 | 0.19 |
| llm=vlm | 22 | 22 | 0 | 0 | 0.88 (22/25) | 0.00 | 0.13 |
| regex=vlm | 22 | 22 | 0 | 0 | 0.88 (22/25) | 0.00 | 0.13 |
| regex=llm=vlm | 22 | 22 | 0 | 0 | 0.88 (22/25) | 0.00 | 0.13 |
| 2-of-3 (regex,llm,vlm) | 23 | 22 | 1 | 0 | 0.88 (22/25) | 0.04 | 0.19 |
| vlm=filename | 15 | 15 | 0 | 0 | 0.60 (15/25) | 0.00 | 0.18 |
| llm=filename | 12 | 12 | 0 | 0 | 0.48 (12/25) | 0.00 | 0.22 |
| regex=filename | 12 | 12 | 0 | 0 | 0.48 (12/25) | 0.00 | 0.22 |
| 2-of-4 (regex,llm,vlm,filename) | 24 | 24 | 0 | 0 | 0.96 (24/25) | 0.00 | 0.12 |
| (llm=vlm) or (any-two incl. filename) | 24 | 24 | 0 | 0 | 0.96 (24/25) | 0.00 | 0.12 |
| (regex=vlm) or (llm=vlm) or (any OCR-method = filename) | 22 | 22 | 0 | 0 | 0.88 (22/25) | 0.00 | 0.13 |
| **any-model=filename** | 15 | 15 | 0 | 0 | 0.60 (15/25) | 0.00 | 0.18 |
| (llm=vlm) or any-model=filename | 25 | 25 | 0 | 0 | 1.00 (25/25) | 0.00 | 0.11 |

Chuyển người duyệt theo quy tắc đã chọn: 11 trường hạn (trong đó 10 có hạn thật); có gợi ý (luật, rồi LLM, rồi VLM): 10, gợi ý đúng 10; gợi ý ra ngày dù giấy không ghi hạn: 0. Người duyệt chỉ cần xác nhận/sửa chứ không phải đọc từ đầu.

#### F. Độ trễ mỗi đơn vị (đo khi GPU/Ollama đang dùng chung với việc khác)

`toàn bộ` gồm cả thời gian Ollama nạp lại mô hình (bị đẩy ra khi tiến trình khác dùng Ollama); `chỉ suy luận` = tổng - nạp mô hình (nếu có ghi).

| cấu hình | n | toàn bộ: trung vị (ms) | p95 (ms) | chỉ suy luận: trung vị (ms) | p95 (ms) |
|---|---|---|---|---|---|
| regex@ocr_v2 | 76 | 8 | 29 | n/a | n/a |
| regex@ocr_llm_haiku | 76 | 5 | 11 | n/a | n/a |
| regex@text_layer | 10 | 4 | 5 | n/a | n/a |
| filename | 76 | 0 | 0 | n/a | n/a |
| gliner@ocr_v2 | 76 | 15432 | 36074 | n/a | n/a |
| gliner@ocr_llm_haiku | 76 | 14831 | 24536 | n/a | n/a |
| gliner@text_layer | 10 | 9089 | 12358 | n/a | n/a |
| llm@ocr_v2 | 76 | 7221 | 56872 | 5485 | 8772 |
| llm@ocr_llm_haiku | 76 | 4488 | 7092 | 4401 | 7064 |
| llm@text_layer | 10 | 8125 | 9941 | 8100 | 9930 |
| vlm | 76 | 11813 | 49692 | 11277 | 14828 |
| regex@ocr_v2 (cùng tập đơn vị với text_layer) | 10 | 5 | 19 | n/a | n/a |
| gliner@ocr_v2 (cùng tập đơn vị với text_layer) | 10 | 10638 | 14220 | n/a | n/a |
| llm@ocr_v2 (cùng tập đơn vị với text_layer) | 10 | 8125 | 9941 | 8100 | 9930 |

VRAM (nvidia-smi toàn GPU, `ollama ps`), đo sau mỗi cấu hình; GPU còn chạy việc của nhóm khác nên số 'toàn GPU' không phải của riêng phương pháp:

* `llm@ocr_v2` (DEV): GPU dùng 6820 -> 6901 MiB; ollama ps: {"bge-m3:latest": {"size_vram_mib": 633, "size_mib": 633, "context_length": 4096}, "qwen3.5:4b": {"size_vram_mib": 3119, "size_mib": 3119, "context_length": 6144}}
* `gliner@ocr_v2` (DEV): GPU dùng 7714 -> 7197 MiB; ollama ps: {"bge-m3:latest": {"size_vram_mib": 633, "size_mib": 633, "context_length": 4096}, "qwen3.5:4b": {"size_vram_mib": 3323, "size_mib": 3323, "context_length": 12288}}
* `gliner@ocr_llm_haiku` (DEV): GPU dùng 7197 -> 2949 MiB; ollama ps: {"bge-m3:latest": {"size_vram_mib": 633, "size_mib": 633, "context_length": 4096}}
* `gliner@text_layer` (DEV): GPU dùng 3689 -> 7149 MiB; ollama ps: {"bge-m3:latest": {"size_vram_mib": 633, "size_mib": 633, "context_length": 4096}, "qwen3.5:4b": {"size_vram_mib": 3323, "size_mib": 3323, "context_length": 12288}}
* `vlm` (DEV): GPU dùng 6901 -> 7137 MiB; ollama ps: {"qwen3.5:4b": {"size_vram_mib": 3323, "size_mib": 3323, "context_length": 12288}, "bge-m3:latest": {"size_vram_mib": 633, "size_mib": 633, "context_length": 4096}}
* `llm@ocr_llm_haiku` (DEV): GPU dùng 7137 -> 6833 MiB; ollama ps: {"bge-m3:latest": {"size_vram_mib": 633, "size_mib": 633, "context_length": 4096}, "qwen3.5:4b": {"size_vram_mib": 3119, "size_mib": 3119, "context_length": 6144}}
* `llm@text_layer` (DEV): GPU dùng 6833 -> 6833 MiB; ollama ps: {"bge-m3:latest": {"size_vram_mib": 633, "size_mib": 633, "context_length": 4096}, "qwen3.5:4b": {"size_vram_mib": 3119, "size_mib": 3119, "context_length": 6144}}
