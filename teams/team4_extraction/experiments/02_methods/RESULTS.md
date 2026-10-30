# Kết quả so sánh các phương pháp trích xuất trường (Nhóm 4, T4)

> Bản tự sinh bởi `build_results_md.py` từ `results_*.json` (số liệu) — đừng sửa tay các con số. Tiếng Việt, viết cho sinh viên năm cuối ngành AI.

## 0. Tóm tắt

**Câu hỏi.** Trong 4 loại tài liệu đã có schema (`GCN_DDK_BAN_LE_XD`, `CC_TAP_HUAN_VC_HNH`, `HD_MUA_BAN`, `PHIEU_XUAT_KHO`), phương pháp nào trích đúng các trường, đặc biệt **ngày hết hạn** (làm lịch nhắc), và có thể tự động nhận kết quả mà không để lọt ngày sai không?

**Kết quả chính trên TEST (22 đơn vị, chấm MỘT lần với cấu hình đã đóng băng trên DEV; đáp án = silver do mô hình đọc, KHÔNG phải người kiểm):**

| phương pháp (văn bản OCR cục bộ `ocr_v2`, trừ khi ghi khác) | F1 chặt [CI 95%] | F1 mềm [CI] | đúng mọi trường bắt buộc, mềm [CI] | hạn: đúng / bỏ trống / **sai giá trị** |
|---|---|---|---|---|
| luật/regex | 0.64 [0.51; 0.75] | 0.83 [0.74; 0.91] | 0.59 [0.41; 0.77] | 0.81 / 0.12 / **0.06** (n=16) |
| GLiNER + gán trường | 0.31 [0.23; 0.41] | 0.46 [0.39; 0.52] | 0.00 [0.00; 0.00] | 0.88 / 0.06 / **0.06** (n=16) |
| LLM cục bộ (văn bản OCR) | 0.71 [0.58; 0.81] | 0.89 [0.81; 0.95] | 0.73 [0.55; 0.91] | 0.81 / 0.12 / **0.06** (n=16) |
| VLM cục bộ (ảnh trang; xem lưu ý 3) | 0.78 [0.70; 0.86] | 0.91 [0.88; 0.95] | 0.68 [0.50; 0.86] | 1.00 / 0.00 / **0.00** (n=16) |
| ngày trong tên tệp (chỉ trường hạn) | 0.11 [0.07; 0.16] | 0.11 [0.07; 0.16] | 0.00 [0.00; 0.00] | 0.75 / 0.12 / **0.12** (n=16) |
| **ghép theo kiểu: LLM cho văn bản, luật cho ngày/số/mã** | 0.72 [0.59; 0.82] | 0.90 [0.83; 0.96] | 0.73 [0.55; 0.91] | 0.88 / 0.06 / **0.06** (n=16) |
| **ghép theo kiểu + tự nhận hạn khi `any-model=filename`** | 0.71 [0.59; 0.81] | 0.90 [0.83; 0.95] | 0.68 [0.50; 0.86] | 0.75 / 0.25 / **0.00** (n=16) |
| (tham chiếu, KHÔNG on-prem) LLM trên bản chép Haiku, chỉ trường ở trang <= 2 | 0.76 [0.69; 0.83] | 0.90 [0.86; 0.94] | 0.91 [0.77; 1.00] | 0.94 / 0.06 / **0.00** (n=16) |

*DEV (76 đơn vị; luật và quy tắc từ chối được chỉnh trên chính các đơn vị này nên số DEV lạc quan):*

| phương pháp (văn bản OCR cục bộ `ocr_v2`, trừ khi ghi khác) | F1 chặt [CI 95%] | F1 mềm [CI] | đúng mọi trường bắt buộc, mềm [CI] | hạn: đúng / bỏ trống / **sai giá trị** |
|---|---|---|---|---|
| luật/regex | 0.61 [0.56; 0.66] | 0.84 [0.80; 0.88] | 0.59 [0.47; 0.70] | 0.83 / 0.12 / **0.05** (n=64) |
| GLiNER + gán trường | 0.35 [0.31; 0.39] | 0.45 [0.42; 0.49] | 0.00 [0.00; 0.00] | 0.84 / 0.11 / **0.05** (n=64) |
| LLM cục bộ (văn bản OCR) | 0.67 [0.60; 0.72] | 0.85 [0.81; 0.89] | 0.59 [0.47; 0.70] | 0.81 / 0.12 / **0.06** (n=64) |
| VLM cục bộ (ảnh trang; xem lưu ý 3) | 0.73 [0.68; 0.78] | 0.89 [0.87; 0.92] | 0.75 [0.66; 0.84] | 0.88 / 0.09 / **0.03** (n=64) |
| ngày trong tên tệp (chỉ trường hạn) | 0.11 [0.08; 0.14] | 0.11 [0.08; 0.14] | 0.00 [0.00; 0.00] | 0.59 / 0.39 / **0.02** (n=64) |
| **ghép theo kiểu: LLM cho văn bản, luật cho ngày/số/mã** | 0.69 [0.63; 0.74] | 0.88 [0.83; 0.91] | 0.62 [0.50; 0.72] | 0.84 / 0.09 / **0.06** (n=64) |
| **ghép theo kiểu + tự nhận hạn khi `any-model=filename`** | 0.67 [0.61; 0.73] | 0.87 [0.82; 0.90] | 0.63 [0.53; 0.74] | 0.58 / 0.42 / **0.00** (n=64) |
| (tham chiếu, KHÔNG on-prem) LLM trên bản chép Haiku, chỉ trường ở trang <= 2 | 0.75 [0.71; 0.78] | 0.91 [0.89; 0.93] | 0.87 [0.79; 0.95] | 1.00 / 0.00 / **0.00** (n=58) |

* **Tốt nhất khi chỉ dùng OCR cục bộ:** ghép theo kiểu (F1 mềm TEST 0.90 [0.83; 0.96], DEV 0.88 [0.83; 0.91]). LLM đứng một mình gần bằng; luật mạnh ở ngày/mã/số nhưng yếu ở văn bản; GLiNER yếu (F1 mềm 0.46): chỉ đáng tin ở ngày.
* **VLM đọc ảnh** là phương pháp đơn lẻ mạnh nhất (F1 mềm TEST 0.91, hạn đúng 1.00) nhưng **con số này bị thổi phồng** (lưu ý 3) và cần ảnh trang.
* **Ngày hết hạn không thể tin vào một nguồn đơn lẻ:** các phương pháp dựa OCR ra SAI giá trị ở 0.05 (DEV) và 0.06 (TEST) số trường hạn có đáp án (đọc sai chữ số, chữ viết tay). Hai nguồn cùng đọc từ MỘT bản OCR sai chung lỗi, nên đồng thuận giữa luật và LLM không cứu được.
* **Quy tắc tự nhận `any-model=filename`** (chỉ nhận ngày khi một mô hình đọc trùng ngày trong tên tệp; chọn trên DEV vì không sai trường nào): DEV nhận 37/64 trường hạn thật (58%), **sai 0**, cận trên 95% của tỉ lệ sai 8%; TEST nhận 12/16 (75%), **sai 0**, cận trên 95% 22%. Phần còn lại (29 trường ở DEV, 5 ở TEST) chuyển người duyệt kèm ngày gợi ý (gợi ý đúng 22/24 ở DEV, 4/4 ở TEST). **Chưa chứng minh được 'sai <= 1%'**: với 0 lỗi cần tối thiểu 299 lần tự nhận đúng (<= 2%: 149; <= 5%: 59); ta mới có 49 (DEV+TEST).
* **Độ tin cậy của đáp án:** người chú thích chính (Haiku) bị người phân xử (Opus) coi là sai ở ~17% số mục bất đồng/rủi ro (xem mục 6), nên mọi con số ở đây có sai số do đáp án.

## 1. Thiết lập

* **Đơn vị chấm** = `(doc_id, segment)`; 4 loại, 104 đơn vị duy nhất: DEV 76, TEST 22 (+6 đơn vị phiếu xuất kho từ tệp ghép bị loại khỏi chấm). Chia DEV/TEST đóng băng của nhóm 00.
* **Đáp án (silver)**: `gold/fields_silver_v1.jsonl`. Haiku đọc ảnh cả 104 đơn vị, Sonnet đọc độc lập 40 đơn vị, Opus phân xử 58 trường bất đồng/rủi ro (ngày hết hạn lệch tên tệp, chữ viết tay/dưới dấu, bất đồng hai người). Chỉ `agreed_unverified` (hai mô hình giống nhau) hoặc `model_adjudicated`; **không có trường nào `human_verified`**. `--gold all` = mọi trường (phần lớn chỉ một người đọc: Haiku); `--gold trusted` = chỉ trường hai người đồng thuận hoặc đã phân xử (ít hơn nhiều: ở TEST chỉ 8 trường hạn).
* **Chuẩn hóa/so sánh**: `eval/normalize.py`; **chặt** = sau chuẩn hóa ngày/số/mã/văn bản (NFC, hoa-thường, khoảng trắng); **mềm** = văn bản bỏ dấu tiếng Việt và dấu câu, chuỗi ngắn nằm trọn trong chuỗi dài, 'tên + mã số thuế' khớp theo tên (hai mã số thuế khác nhau thì KHÔNG khớp). Hai cột luôn đi cạnh nhau; ngày/số/mã giống nhau ở hai chế độ. Trường PII (số định danh, ngày sinh, họ tên) **không được chấm**.
* **Quy ước TP/FP/FN** theo README T3 (đúng = TP; sai giá trị = FP+FN; bỏ trống = FN; thừa = FP; null-null không tính). Đơn vị phương pháp lỗi/không có văn bản chấm như dự đoán toàn null và đếm riêng (`n_failed`: 0 ở mọi cấu hình chính). CI 95% = bootstrap percentile 1000 lần theo đơn vị; khi một tỉ lệ là 0 hoặc 1 thì CI bootstrap suy biến, dùng cận nhị thức ở bảng E.
* **Đóng băng**: `dev_selection.json` (băm của luật regex, prompt, bộ chuẩn hóa, silver; quy tắc từ chối chọn trên DEV) được ghi TRƯỚC khi chạy TEST; TEST chạy một lần (`run_methods.py --final-test`). Đáp án ở DEV/TEST dùng bản silver SAU phân xử (thay đổi so với lúc phát triển: 58 trường).
* **Phương pháp**: luật (`src/extraction/field_rules.py`), ngày trong tên tệp, GLiNER `belumind/barb-1-ie-vi` + gán trường theo từ khóa bên trái (CPU), LLM `qwen3.5:4b` qua Ollama với đầu ra ràng buộc JSON Schema (prompt `v1`), VLM cùng mô hình đọc ảnh trang (4 ảnh đầu), và các cách ghép. Nguồn văn bản: `ocr_v2` (OCR cục bộ, **nguồn sản xuất**), `ocr_llm_haiku` (chỉ 2 trang đầu; không on-prem), `text_layer`.

### Lưu ý bắt buộc (đọc trước khi dùng con số)

1. **Đáp án là silver do mô hình LLM đọc, chưa có người kiểm.** Khi phương pháp và đáp án cùng sai thì được tính là đúng.
2. **Các mô hình họ Claude có thể chung lỗi** (cùng đọc ảnh theo cùng hướng dẫn); độ đồng thuận giữa Haiku và Sonnet không chứng minh đúng.
3. **VLM và người chú thích đều đọc ẢNH** nên độ khớp VLM-silver có thể cao hơn so với phương pháp dựa OCR (chung kiểu lỗi/đọc); đừng đọc 'VLM hơn OCR' thành lợi thế thật 1:1.
4. **Trường nằm ở trang không được cho annotator xem** (đơn vị > 4 trang chỉ cho xem tối đa 6 trang) có thể bị ghi `not_present`; phương pháp tìm thấy giá trị ở đó bị tính 'thừa'. Ảnh hưởng chủ yếu `HD_MUA_BAN` dài.
5. **Một biểu mẫu, nhiều tài liệu**: `CC_TAP_HUAN_VC_HNH` (23/24 cùng mẫu) và `PHIEU_XUAT_KHO` (biểu mẫu BSR số hóa) cho điểm cao giả tạo; chỉ `GCN_DDK_BAN_LE_XD` và `HD_MUA_BAN` có nhiều biến thể.
6. **Cỡ mẫu nhỏ**: TEST 22 đơn vị, 16 trường hạn có đáp án — CI rộng; nhiều so sánh giữa phương pháp 'không tách được'.
7. Luật và quy tắc từ chối được chỉnh trên DEV: số DEV là 'đã chỉnh trên chính các đơn vị này'; chỉ số TEST mới là ước lượng ngoài mẫu (và vẫn chỉ 22 đơn vị).

## 2. Theo loại tài liệu

Bảng B của từng tập (cuối tệp) có chi tiết. Tóm tắt F1 mềm của phương pháp ghép theo kiểu:

| loại | DEV (n) | TEST (n) | ghi chú |
|---|---|---|---|
| CC_TAP_HUAN_VC_HNH | 0.94 (19) | 0.99 (5) | một biểu mẫu thẻ duy nhất (23/24): lạc quan |
| GCN_DDK_BAN_LE_XD | 0.75 (21) | 0.75 (6) | bản quét, con dấu chứng thực đè lên hạn, chữ viết tay: khó nhất |
| HD_MUA_BAN | 0.88 (26) | 0.86 (6) | nhiều biến thể; hạn nằm trong điều khoản cuối, có hợp đồng không ghi hạn |
| PHIEU_XUAT_KHO | 0.98 (10) | 1.00 (5) | bản số hóa BSR (chữ thật): gần như hoàn hảo, một mẫu |

## 3. Cái giá của OCR (DEV)

So CÙNG phương pháp trên `ocr_v2` (OCR cục bộ) và trên bản chép của Haiku (LLM đọc ảnh: gần như 'OCR hoàn hảo'; **không có on-prem**, là cận trên). Chỉ chấm trường có đáp án ở trang <= 2. F1 mềm; mũi tên = ocr_v2 → bản chép Haiku.

| phương pháp | tất cả | ngày | mã | văn bản | số |
|---|---|---|---|---|---|
| regex | 0.84 → 0.92 | 0.91 → 0.98 | 0.95 → 0.86 | 0.76 → 0.94 | n/a |
| llm | 0.85 → 0.91 | 0.87 → 0.96 | 0.93 → 0.94 | 0.81 → 0.94 | 0.90 → 0.10 |

Theo mực viết của đáp án (silver; so sánh mềm), `đúng / sai giá trị`:

| phương pháp | mực | n trường | OCR cục bộ | bản chép Haiku | Δ đúng |
|---|---|---|---|---|---|
| luật | printed | 599 | 0.82 / 0.07 | 0.89 / 0.04 | +0.07 |
| luật | handwritten | 34 | 0.53 / 0.18 | 0.82 / 0.18 | +0.29 |
| luật | under_stamp | 20 | 0.35 / 0.20 | 0.95 / 0.05 | +0.60 |
| LLM | printed | 599 | 0.84 / 0.09 | 0.90 / 0.07 | +0.05 |
| LLM | handwritten | 34 | 0.59 / 0.41 | 0.79 / 0.21 | +0.21 |
| LLM | under_stamp | 20 | 0.65 / 0.25 | 0.95 / 0.05 | +0.30 |

VLM đọc ảnh (không qua OCR), cùng bảng: printed: 0.87 đúng / 0.06 sai (n=599); handwritten: 0.76 đúng / 0.24 sai (n=34); under_stamp: 0.95 đúng / 0.05 sai (n=20).

* OCR cục bộ mất nhiều nhất ở chữ **viết tay** và **dưới con dấu** (đúng thấp hơn rõ so với bản chép), còn chữ in chỉ mất ít. Đây là nơi cần đọc ảnh (VLM) hoặc người duyệt.
* **Text layer**: các trang số hóa (chủ yếu phiếu xuất kho) đã nằm trong `ocr_v2` với `source = text_layer`, nên so `text_layer` với `ocr_v2` trên các đơn vị đó cho kết quả GIỐNG HỆT (xem bảng C của từng tập); không thể đo 'OCR vs chữ thật' trên bộ này. Trên các đơn vị có chữ thật (DEV 10, TEST 5; đều là phiếu xuất kho) mọi phương pháp tốt hơn hẳn trên nguồn sạch này (LLM F1 mềm ~0,98-1,00).
* Dòng 'ORACLE' ở bảng D chỉ để minh họa: định tuyến VLM theo mực của đáp án (không triển khai được vì sản xuất không biết trước ô nào viết tay); lợi ích nhỏ so với dùng VLM toàn phần.

## 4. Ngày hết hạn: tự nhận hay từ chối

Chọn trên DEV trong 17 quy tắc đồng thuận giữa 4 nguồn {luật, LLM, VLM, tên tệp}: quy tắc **không sai trường nào trên DEV** và tự nhận nhiều nhất = **`any-model=filename`**. Bảng E của DEV/TEST liệt kê mọi quy tắc kèm cận trên Clopper-Pearson 95% một phía.

* Không quy tắc nào chỉ dựa vào văn bản OCR (luật=LLM) đạt 0 sai trên DEV, vì hai phương pháp đọc cùng một bản OCR nên cùng sai (ví dụ '22' thay vì '12', '24' thay vì '21' khi chữ viết tay).
* Mô hình đọc ảnh (VLM) là nguồn độc lập với OCR nhưng cũng đọc nhầm chữ viết tay (một trường DEV: luật, LLM và VLM cùng đọc 24, đáp án và tên tệp là 21): ngày trong tên tệp là tín hiệu độc lập hữu ích, **nhưng quy ước đặt tên chưa được công ty xác nhận** (câu hỏi 16) và đứng một mình nó sai ở 3/15 trường TEST. Quy tắc chỉ nhận khi một MÔ HÌNH đọc trùng tên tệp.
* Cái giá của an toàn: tự động hóa 58% (DEV) / 75% (TEST) số trường hạn thật; phần còn lại vào hàng duyệt tay, kèm ngày gợi ý.
* Để khẳng định tỉ lệ sai <= 1% (một phía 95%) với 0 lỗi quan sát cần ít nhất **299** lần tự nhận (ta có 37 + 12); với <= 5%: 59. Nếu quan sát 1 lỗi thì cần nhiều hơn nữa (xem `combine.n_needed`).

## 5. Độ trễ và VRAM

Đo khi GPU và Ollama đang được các việc khác dùng chung ('shared GPU load'): Ollama nhiều lần bị đẩy mô hình ra rồi nạp lại (30-45 s mỗi lần) nên độ trễ 'toàn bộ' có đuôi dài; cột 'chỉ suy luận' trừ thời gian nạp. VRAM lấy từ `ollama ps` (nvidia-smi toàn GPU không tách riêng được). Chi tiết ở bảng F.

| phương pháp | trung vị toàn bộ (ms) | trung vị chỉ suy luận (ms) | VRAM Ollama | ghi chú |
|---|---|---|---|---|
| luật (TEST) | 5 | n/a | 0 | CPU, vài ms |
| GLiNER (CPU) (TEST) | 10389 | n/a | 0 (CPU) | ~10-15 s/đơn vị trên CPU dùng chung; nạp mô hình ~40 s một lần |
| LLM văn bản (TEST) | 4177 | 4143 | ~3,1 GB (ctx 6144) | qwen3.5:4b Q4_K_M |
| VLM ảnh (TEST) | 10509 | 10160 | ~3,3 GB (ctx 12288) | 4 ảnh/đơn vị |

Toàn bộ quy trình đề xuất (luật + LLM + tùy chọn VLM cho hạn) ~ 5-16 giây/đơn vị khi mô hình đã nạp.

## 6. Độ tin cậy của đáp án: phân xử và ước lượng sai của người chú thích

###  Phân xử bởi người đọc thứ ba (mô hình mạnh hơn; KHÔNG phải người thật)

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


## 7. Khuyến nghị cho sản xuất (chỉ on-premise) và điều CHƯA chứng minh

**Khuyến nghị.** Dùng `src/extraction/field_extractor.py::extract_fields` (đã thăng cấp từ thí nghiệm này):
1. luật/regex trên văn bản OCR cục bộ; 2. LLM cục bộ `qwen3.5:4b` (JSON Schema) ghép theo kiểu (văn bản ưu tiên LLM; ngày/số/mã ưu tiên luật); 3. trường hạn: **tự nhận chỉ khi một mô hình đọc trùng ngày trong tên tệp** (`any-model=filename`; nếu có ảnh trang thì thêm VLM làm nguồn thứ ba), còn lại để null + `needs_review` + ngày gợi ý; 4. PII: mặc định bỏ số định danh và ngày sinh (T5). Không dùng GLiNER làm bộ trích trường (F1 thấp); không dùng ngày trong tên tệp một mình.

**Chưa chứng minh:**
* độ chính xác so với **đáp án do người kiểm** (mọi con số là so với silver LLM); tỉ lệ sai thật của hạn tự nhận (cần >= 299 mẫu đúng liên tiếp cho <= 1%);
* hiệu năng trên **biểu mẫu mới** ngoài 4 biểu mẫu hiện có (đặc biệt thẻ tập huấn, phiếu xuất kho một mẫu) và trên tài liệu viết tay nhiều;
* quy ước **ngày trong tên tệp = ngày hết hạn** (chưa được công ty xác nhận; rule sản xuất phụ thuộc vào nó — nếu không có tên tệp hợp lệ thì hầu hết hạn sẽ vào hàng duyệt tay);
* các trường nằm ở trang không được annotator xem; trường PII (không chấm); bảng hàng hóa (`dong_hang`, T6); định dạng ERP;
* độ trễ/VRAM trên máy không dùng chung (số ở đây đo khi GPU đang tải); thông lượng khi chạy hàng loạt;
* VLM có thực sự độc lập với OCR hơn là 'chung kiểu đọc ảnh với annotator' (lưu ý 3).

## 8. Bẫy đã gặp khi làm

* **Ollama thrash**: tiến trình khác dùng Ollama làm mô hình bị đẩy ra; mỗi lời gọi mất 30-45 s nạp lại. Đo độ trễ phải tách 'nạp' và 'suy luận'; chạy tuần tự có cache đĩa (`_cache/ollama`).
* **Cột bảng bị lệch**: LLM 4B đọc bảng số lượng của phiếu xuất kho trên bản chép Haiku bị dịch một cột (gán số thùng cho m3). Luật theo thứ tự cột không bị. Vì vậy ghép theo kiểu: số/mã/ngày ưu tiên luật.
* **LLM chép nguyên văn rác** khi OCR hỏng ('ngày 09 tháng dưng ...'): ngày/số không phân tích được bị chuyển thành null thay vì giá trị sai.
* **Hạn sai do chữ số OCR**: '22' thay '12', '24' thay '21' (viết tay), tháng '15'. Tháng không hợp lệ bị lọc; hai lỗi còn lại cần nguồn độc lập (ảnh/tên tệp).
* **Đáp án có chỗ không phải ngày** ('từ ngày ký', cụm thời hạn, '[?]'): được quy ước ở `lib.load_gold` (quy về ngày ký / không có ngày cụ thể / loại khỏi điểm) và áp dụng như nhau cho DEV và TEST.
* **Luật gần như đúng từng trường nhưng 'từ khóa không dấu' vẫn nhầm vào phần căn cứ pháp lý** ('hiệu lực từ ngày' của luật, số quyết định): phải neo vào cụm 'Hợp đồng ... có hiệu lực', 'GCN/SCT', 'Bên ... :' ở đầu.
* Một lỗi vặt tốn thời gian: chuỗi regex trong tệp bị chèn ký tự điều khiển `\x08` (backspace) khi vá bằng heredoc không-raw; đã quét toàn bộ mã.

## 9. Chạy lại

```powershell
# từ gốc repo; chạy tuần tự, có cache; DEV trước, TEST chỉ sau khi đã freeze
.venv\Scripts\python.exe -X utf8 teams\team4_extraction\experiments\02_methods\run_methods.py --split DEV --configs regex@ocr_v2,llm@ocr_v2,vlm,filename,gliner@ocr_v2
.venv\Scripts\python.exe -X utf8 teams\team4_extraction\experiments\02_methods\make_results.py --split DEV --gold all
.venv\Scripts\python.exe -X utf8 teams\team4_extraction\experiments\02_methods\freeze.py            # ghi dev_selection.json (một lần)
.venv\Scripts\python.exe -X utf8 teams\team4_extraction\experiments\02_methods\run_methods.py --split TEST --final-test --configs ...
.venv\Scripts\python.exe -X utf8 teams\team4_extraction\experiments\02_methods\make_results.py --split TEST --gold all --final-test
.venv\Scripts\python.exe -X utf8 teams\team4_extraction\experiments\02_methods\render_tables.py TEST all   # rồi build_results_md.py
```

## Phụ lục TEST / all

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


## Phụ lục TEST / trusted

### Kết quả TEST (đáp án: `trusted`)

Số đơn vị: 22 (CC_TAP_HUAN_VC_HNH 5, GCN_DDK_BAN_LE_XD 6, HD_MUA_BAN 6, PHIEU_XUAT_KHO 5). Khoảng tin cậy 95%: bootstrap percentile theo đơn vị. `F1 chặt` = so sánh sau chuẩn hóa; `F1 mềm` = như chặt nhưng văn bản bỏ dấu/dấu câu, chứa nhau, 'tên + MST' khớp theo tên. 

#### A. Tổng quan theo phương pháp × nguồn văn bản

| cấu hình | n | F1 chặt (toàn bộ trường) | F1 mềm | F1 ngày | F1 số | F1 mã | F1 văn bản chặt | F1 văn bản mềm | đúng mọi trường bắt buộc (chặt) | (mềm) | hạn: đúng | hạn: bỏ trống | hạn: **sai giá trị** | n hạn |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| regex@ocr_v2 | 22 | 0.76 [0.58; 0.88] | 0.93 [0.85; 0.98] | 0.93 | 1.00 | 0.95 | 0.51 | 0.90 | 0.30 (3/10) | 0.80 | 0.75 [0.40; 1.00] | 0.12 [0.00; 0.40] | 0.12 [0.00; 0.40] | 8 |
| regex@ocr_llm_haiku | 22 | 0.71 [0.65; 0.75] | 0.88 [0.82; 0.94] | 0.98 | n/a | 0.81 | 0.59 | 0.96 | 0.30 (3/10) | 0.50 | 0.88 [0.60; 1.00] | 0.12 [0.00; 0.40] | 0.00 [0.00; 0.00] | 8 |
| regex@text_layer | 5 | 0.93 [0.93; 0.93] | 1.00 [1.00; 1.00] | 1.00 | 1.00 | 1.00 | 0.80 | 1.00 | 0.00 (0/3) | 1.00 | n/a | n/a | n/a | 0 |
| filename | 22 | 0.10 [0.03; 0.18] | 0.10 [0.03; 0.18] | 0.36 | n/a | n/a | n/a | n/a | 0.00 (0/10) | 0.00 | 0.62 [0.25; 1.00] | 0.12 [0.00; 0.43] | 0.25 [0.00; 0.60] | 8 |
| gliner@ocr_v2 | 22 | 0.33 [0.21; 0.50] | 0.51 [0.42; 0.62] | 0.95 | n/a | n/a | 0.04 | 0.44 | 0.10 (1/10) | 0.10 | 0.88 [0.60; 1.00] | 0.00 [0.00; 0.00] | 0.12 [0.00; 0.40] | 8 |
| gliner@ocr_llm_haiku | 22 | 0.33 [0.22; 0.49] | 0.46 [0.41; 0.54] | 0.81 | n/a | n/a | 0.15 | 0.44 | 0.10 (1/10) | 0.10 | 0.75 [0.43; 1.00] | 0.00 [0.00; 0.00] | 0.25 [0.00; 0.57] | 8 |
| gliner@text_layer | 5 | 0.12 [0.12; 0.12] | 0.35 [0.35; 0.35] | 1.00 | n/a | n/a | n/a | 0.57 | 0.00 (0/3) | 0.00 | n/a | n/a | n/a | 0 |
| llm@ocr_v2 | 22 | 0.77 [0.59; 0.90] | 0.95 [0.87; 1.00] | 0.90 | 1.00 | 0.95 | 0.56 | 0.96 | 0.60 (6/10) | 0.90 | 0.88 [0.60; 1.00] | 0.00 [0.00; 0.00] | 0.12 [0.00; 0.40] | 8 |
| llm@ocr_llm_haiku | 22 | 0.75 [0.64; 0.86] | 0.90 [0.84; 0.97] | 0.95 | 0.33 | 0.95 | 0.62 | 0.97 | 0.60 (6/10) | 0.90 | 1.00 [1.00; 1.00] | 0.00 [0.00; 0.00] | 0.00 [0.00; 0.00] | 8 |
| llm@text_layer | 5 | 0.93 [0.93; 0.93] | 1.00 [1.00; 1.00] | 1.00 | 1.00 | 1.00 | 0.80 | 1.00 | 1.00 (3/3) | 1.00 | n/a | n/a | n/a | 0 |
| vlm | 22 | 0.84 [0.71; 0.93] | 0.93 [0.90; 0.97] | 0.95 | 1.00 | 0.92 | 0.70 | 0.90 | 0.50 (5/10) | 0.60 | 1.00 [1.00; 1.00] | 0.00 [0.00; 0.00] | 0.00 [0.00; 0.00] | 8 |
| cascade regex→llm @ocr_v2 | 22 | 0.77 [0.59; 0.88] | 0.95 [0.89; 0.99] | 0.95 | 1.00 | 0.95 | 0.52 | 0.94 | 0.30 (3/10) | 0.90 | 0.88 [0.60; 1.00] | 0.00 [0.00; 0.00] | 0.12 [0.00; 0.40] | 8 |
| cascade llm→regex @ocr_v2 | 22 | 0.79 [0.61; 0.91] | 0.96 [0.88; 1.00] | 0.90 | 1.00 | 0.95 | 0.59 | 0.99 | 0.60 (6/10) | 0.90 | 0.88 [0.60; 1.00] | 0.00 [0.00; 0.00] | 0.12 [0.00; 0.40] | 8 |
| cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | 22 | 0.80 [0.65; 0.91] | 0.97 [0.92; 1.00] | 0.95 | 1.00 | 0.95 | 0.59 | 0.99 | 0.60 (6/10) | 0.90 | 0.88 [0.60; 1.00] | 0.00 [0.00; 0.00] | 0.12 [0.00; 0.40] | 8 |
| cascade regex→llm→vlm @ocr_v2 | 22 | 0.77 [0.60; 0.89] | 0.96 [0.90; 1.00] | 0.95 | 1.00 | 0.95 | 0.54 | 0.95 | 0.30 (3/10) | 0.90 | 0.88 [0.60; 1.00] | 0.00 [0.00; 0.00] | 0.12 [0.00; 0.40] | 8 |
| cascade + từ chối hạn [any-model=filename] | 22 | 0.79 [0.64; 0.89] | 0.97 [0.93; 0.99] | 0.92 | 1.00 | 0.95 | 0.59 | 0.99 | 0.50 (5/10) | 0.70 | 0.62 [0.25; 1.00] | 0.38 [0.00; 0.75] | 0.00 [0.00; 0.00] | 8 |
| ORACLE: VLM chỉ ở ô mà đáp án ghi viết tay/dưới dấu (không triển khai được) | 22 | 0.82 [0.66; 0.94] | 0.97 [0.92; 1.00] | 0.90 | 1.00 | 1.00 | 0.64 | 0.99 | 0.60 (6/10) | 0.90 | 0.88 [0.60; 1.00] | 0.00 [0.00; 0.00] | 0.12 [0.00; 0.40] | 8 |
| regex@ocr_v2 (cùng tập đơn vị với text_layer) | 5 | 0.93 [0.93; 0.93] | 1.00 [1.00; 1.00] | 1.00 | 1.00 | 1.00 | 0.80 | 1.00 | 0.00 (0/3) | 1.00 | n/a | n/a | n/a | 0 |
| gliner@ocr_v2 (cùng tập đơn vị với text_layer) | 5 | 0.12 [0.12; 0.12] | 0.35 [0.35; 0.35] | 1.00 | n/a | n/a | n/a | 0.57 | 0.00 (0/3) | 0.00 | n/a | n/a | n/a | 0 |
| llm@ocr_v2 (cùng tập đơn vị với text_layer) | 5 | 0.93 [0.93; 0.93] | 1.00 [1.00; 1.00] | 1.00 | 1.00 | 1.00 | 0.80 | 1.00 | 1.00 (3/3) | 1.00 | n/a | n/a | n/a | 0 |

Ghi chú: `F1 ngày` gộp mọi trường kiểu ngày (hạn, ngày cấp, ngày ký...). `n hạn` = số trường hạn có đáp án. `đúng mọi trường bắt buộc` dùng so sánh chặt.

#### B. Theo loại tài liệu (so sánh chặt; trong ngoặc: F1 mềm)

> `CC_TAP_HUAN_VC_HNH` và `PHIEU_XUAT_KHO` gần như MỘT biểu mẫu duy nhất (và phiếu xuất kho là bản số hóa sạch): điểm cao ở hai loại này lạc quan, không suy ra cho biểu mẫu mới.

| loại | cấu hình | n | F1 chặt (mềm) | đúng mọi trường bắt buộc | hạn: đúng / bỏ trống / **sai** (n) |
|---|---|---|---|---|---|
| CC_TAP_HUAN_VC_HNH | regex@ocr_v2 | 5 | 0.72 (0.80) | 1.00 (2/2); mềm 1.00 | 1.00 / 0.00 / 0.00 (2) |
| CC_TAP_HUAN_VC_HNH | gliner@ocr_v2 | 5 | 0.64 (0.73) | 0.00 (0/2); mềm 0.00 | 1.00 / 0.00 / 0.00 (2) |
| CC_TAP_HUAN_VC_HNH | llm@ocr_v2 | 5 | 0.89 (0.96) | 1.00 (2/2); mềm 1.00 | 1.00 / 0.00 / 0.00 (2) |
| CC_TAP_HUAN_VC_HNH | vlm | 5 | 1.00 (1.00) | 1.00 (2/2); mềm 1.00 | 1.00 / 0.00 / 0.00 (2) |
| CC_TAP_HUAN_VC_HNH | cascade regex→llm @ocr_v2 | 5 | 0.74 (0.89) | 1.00 (2/2); mềm 1.00 | 1.00 / 0.00 / 0.00 (2) |
| CC_TAP_HUAN_VC_HNH | cascade llm→regex @ocr_v2 | 5 | 0.89 (0.96) | 1.00 (2/2); mềm 1.00 | 1.00 / 0.00 / 0.00 (2) |
| CC_TAP_HUAN_VC_HNH | cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | 5 | 0.89 (0.96) | 1.00 (2/2); mềm 1.00 | 1.00 / 0.00 / 0.00 (2) |
| CC_TAP_HUAN_VC_HNH | cascade regex→llm→vlm @ocr_v2 | 5 | 0.79 (0.93) | 1.00 (2/2); mềm 1.00 | 1.00 / 0.00 / 0.00 (2) |
| CC_TAP_HUAN_VC_HNH | cascade + từ chối hạn [any-model=filename] | 5 | 0.89 (0.96) | 1.00 (2/2); mềm 1.00 | 1.00 / 0.00 / 0.00 (2) |
| GCN_DDK_BAN_LE_XD | regex@ocr_v2 | 6 | 0.43 (0.81) | 0.33 (1/3); mềm 0.33 | 0.67 / 0.00 / 0.33 (3) |
| GCN_DDK_BAN_LE_XD | gliner@ocr_v2 | 6 | 0.29 (0.50) | 0.33 (1/3); mềm 0.33 | 0.67 / 0.00 / 0.33 (3) |
| GCN_DDK_BAN_LE_XD | llm@ocr_v2 | 6 | 0.42 (0.84) | 0.33 (1/3); mềm 0.67 | 0.67 / 0.00 / 0.33 (3) |
| GCN_DDK_BAN_LE_XD | vlm | 6 | 0.53 (0.95) | 0.33 (1/3); mềm 0.67 | 1.00 / 0.00 / 0.00 (3) |
| GCN_DDK_BAN_LE_XD | cascade regex→llm @ocr_v2 | 6 | 0.42 (0.84) | 0.33 (1/3); mềm 0.67 | 0.67 / 0.00 / 0.33 (3) |
| GCN_DDK_BAN_LE_XD | cascade llm→regex @ocr_v2 | 6 | 0.42 (0.84) | 0.33 (1/3); mềm 0.67 | 0.67 / 0.00 / 0.33 (3) |
| GCN_DDK_BAN_LE_XD | cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | 6 | 0.47 (0.89) | 0.33 (1/3); mềm 0.67 | 0.67 / 0.00 / 0.33 (3) |
| GCN_DDK_BAN_LE_XD | cascade regex→llm→vlm @ocr_v2 | 6 | 0.42 (0.84) | 0.33 (1/3); mềm 0.67 | 0.67 / 0.00 / 0.33 (3) |
| GCN_DDK_BAN_LE_XD | cascade + từ chối hạn [any-model=filename] | 6 | 0.44 (0.89) | 0.00 (0/3); mềm 0.00 | 0.33 / 0.67 / 0.00 (3) |
| HD_MUA_BAN | regex@ocr_v2 | 6 | 0.73 (0.97) | 0.00 (0/2); mềm 1.00 | 0.67 / 0.33 / 0.00 (3) |
| HD_MUA_BAN | gliner@ocr_v2 | 6 | 0.56 (0.64) | 0.00 (0/2); mềm 0.00 | 1.00 / 0.00 / 0.00 (3) |
| HD_MUA_BAN | llm@ocr_v2 | 6 | 0.69 (0.94) | 0.00 (0/2); mềm 1.00 | 1.00 / 0.00 / 0.00 (3) |
| HD_MUA_BAN | vlm | 6 | 0.94 (0.94) | 1.00 (2/2); mềm 1.00 | 1.00 / 0.00 / 0.00 (3) |
| HD_MUA_BAN | cascade regex→llm @ocr_v2 | 6 | 0.76 (1.00) | 0.00 (0/2); mềm 1.00 | 1.00 / 0.00 / 0.00 (3) |
| HD_MUA_BAN | cascade llm→regex @ocr_v2 | 6 | 0.76 (1.00) | 0.00 (0/2); mềm 1.00 | 1.00 / 0.00 / 0.00 (3) |
| HD_MUA_BAN | cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | 6 | 0.76 (1.00) | 0.00 (0/2); mềm 1.00 | 1.00 / 0.00 / 0.00 (3) |
| HD_MUA_BAN | cascade regex→llm→vlm @ocr_v2 | 6 | 0.76 (1.00) | 0.00 (0/2); mềm 1.00 | 1.00 / 0.00 / 0.00 (3) |
| HD_MUA_BAN | cascade + từ chối hạn [any-model=filename] | 6 | 0.73 (0.97) | 0.00 (0/2); mềm 1.00 | 0.67 / 0.33 / 0.00 (3) |
| PHIEU_XUAT_KHO | regex@ocr_v2 | 5 | 0.93 (1.00) | 0.00 (0/3); mềm 1.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | gliner@ocr_v2 | 5 | 0.12 (0.35) | 0.00 (0/3); mềm 0.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | llm@ocr_v2 | 5 | 0.93 (1.00) | 1.00 (3/3); mềm 1.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | vlm | 5 | 0.89 (0.89) | 0.00 (0/3); mềm 0.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | cascade regex→llm @ocr_v2 | 5 | 0.93 (1.00) | 0.00 (0/3); mềm 1.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | cascade llm→regex @ocr_v2 | 5 | 0.93 (1.00) | 1.00 (3/3); mềm 1.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | 5 | 0.93 (1.00) | 1.00 (3/3); mềm 1.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | cascade regex→llm→vlm @ocr_v2 | 5 | 0.93 (1.00) | 0.00 (0/3); mềm 1.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | cascade + từ chối hạn [any-model=filename] | 5 | 0.93 (1.00) | 1.00 (3/3); mềm 1.00 | (không có trường hạn) |

#### C. Cái giá của OCR: cùng phương pháp, khác nguồn văn bản

`ocr_llm_haiku` chỉ có 2 trang đầu của tệp và đáp án ở trang > 2 bị loại khỏi điểm (cho công bằng); nguồn này KHÔNG chạy được on-premise (cận trên). `text_layer` chỉ có ở trang số hóa nên chấm trên tập con các đơn vị có chữ thật; cột cuối là chính phương pháp đó trên OCR cục bộ ở CÙNG tập con.

| phương pháp | nguồn | n | F1 chặt | F1 mềm | F1 ngày | F1 mã | F1 văn bản mềm | hạn đúng / **sai** (n) |
|---|---|---|---|---|---|---|---|---|
| regex | ocr_v2 | 22 | 0.76 [0.58; 0.88] | 0.93 [0.85; 0.98] | 0.93 | 0.95 | 0.90 | 0.75 / 0.12 (8) |
| regex | ocr_llm_haiku | 22 | 0.71 [0.65; 0.75] | 0.88 [0.82; 0.94] | 0.98 | 0.81 | 0.96 | 0.88 / 0.00 (8) |
| regex | text_layer | 5 | 0.93 [0.93; 0.93] | 1.00 [1.00; 1.00] | 1.00 | 1.00 | 1.00 | n/a / n/a (0) |
| regex | ocr_v2 (cùng tập đơn vị với text_layer) | 5 | 0.93 [0.93; 0.93] | 1.00 [1.00; 1.00] | 1.00 | 1.00 | 1.00 | n/a / n/a (0) |
| gliner | ocr_v2 | 22 | 0.33 [0.21; 0.50] | 0.51 [0.42; 0.62] | 0.95 | n/a | 0.44 | 0.88 / 0.12 (8) |
| gliner | ocr_llm_haiku | 22 | 0.33 [0.22; 0.49] | 0.46 [0.41; 0.54] | 0.81 | n/a | 0.44 | 0.75 / 0.25 (8) |
| gliner | text_layer | 5 | 0.12 [0.12; 0.12] | 0.35 [0.35; 0.35] | 1.00 | n/a | 0.57 | n/a / n/a (0) |
| gliner | ocr_v2 (cùng tập đơn vị với text_layer) | 5 | 0.12 [0.12; 0.12] | 0.35 [0.35; 0.35] | 1.00 | n/a | 0.57 | n/a / n/a (0) |
| llm | ocr_v2 | 22 | 0.77 [0.59; 0.90] | 0.95 [0.87; 1.00] | 0.90 | 0.95 | 0.96 | 0.88 / 0.12 (8) |
| llm | ocr_llm_haiku | 22 | 0.75 [0.64; 0.86] | 0.90 [0.84; 0.97] | 0.95 | 0.95 | 0.97 | 1.00 / 0.00 (8) |
| llm | text_layer | 5 | 0.93 [0.93; 0.93] | 1.00 [1.00; 1.00] | 1.00 | 1.00 | 1.00 | n/a / n/a (0) |
| llm | ocr_v2 (cùng tập đơn vị với text_layer) | 5 | 0.93 [0.93; 0.93] | 1.00 [1.00; 1.00] | 1.00 | 1.00 | 1.00 | n/a / n/a (0) |

#### D. Theo mực viết của đáp án silver (trường có đáp án; so sánh mềm)

Mực do người chú thích ghi (Haiku là chính), nên có thể sai. Chỉ tính trường có giá trị trong đáp án.

| cấu hình | mực | n trường | đúng | bỏ trống | **sai giá trị** |
|---|---|---|---|---|---|
| regex@ocr_v2 | printed | 87 | 0.93 | 0.05 | 0.02 |
| regex@ocr_v2 | handwritten | 2 | 0.50 | 0.00 | 0.50 |
| regex@ocr_v2 | under_stamp | 3 | 0.33 | 0.33 | 0.33 |
| gliner@ocr_v2 | printed | 87 | 0.36 | 0.62 | 0.02 |
| gliner@ocr_v2 | handwritten | 2 | 0.50 | 0.50 | 0.00 |
| gliner@ocr_v2 | under_stamp | 3 | 0.00 | 1.00 | 0.00 |
| llm@ocr_v2 | printed | 87 | 0.95 | 0.03 | 0.01 |
| llm@ocr_v2 | handwritten | 2 | 0.00 | 0.00 | 1.00 |
| llm@ocr_v2 | under_stamp | 3 | 1.00 | 0.00 | 0.00 |
| vlm | printed | 87 | 0.91 | 0.06 | 0.03 |
| vlm | handwritten | 2 | 0.50 | 0.00 | 0.50 |
| vlm | under_stamp | 3 | 1.00 | 0.00 | 0.00 |
| cascade regex→llm @ocr_v2 | printed | 87 | 0.97 | 0.01 | 0.02 |
| cascade regex→llm @ocr_v2 | handwritten | 2 | 0.50 | 0.00 | 0.50 |
| cascade regex→llm @ocr_v2 | under_stamp | 3 | 0.67 | 0.00 | 0.33 |
| cascade llm→regex @ocr_v2 | printed | 87 | 0.98 | 0.01 | 0.01 |
| cascade llm→regex @ocr_v2 | handwritten | 2 | 0.00 | 0.00 | 1.00 |
| cascade llm→regex @ocr_v2 | under_stamp | 3 | 1.00 | 0.00 | 0.00 |
| cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | printed | 87 | 0.98 | 0.01 | 0.01 |
| cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | handwritten | 2 | 0.50 | 0.00 | 0.50 |
| cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | under_stamp | 3 | 1.00 | 0.00 | 0.00 |
| cascade regex→llm→vlm @ocr_v2 | printed | 87 | 0.98 | 0.00 | 0.02 |
| cascade regex→llm→vlm @ocr_v2 | handwritten | 2 | 0.50 | 0.00 | 0.50 |
| cascade regex→llm→vlm @ocr_v2 | under_stamp | 3 | 0.67 | 0.00 | 0.33 |
| cascade + từ chối hạn [any-model=filename] | printed | 87 | 0.95 | 0.05 | 0.00 |
| cascade + từ chối hạn [any-model=filename] | handwritten | 2 | 0.50 | 0.00 | 0.50 |
| cascade + từ chối hạn [any-model=filename] | under_stamp | 3 | 1.00 | 0.00 | 0.00 |
| ORACLE: VLM chỉ ở ô mà đáp án ghi viết tay/dưới dấu (không triển khai được) | printed | 87 | 0.98 | 0.01 | 0.01 |
| ORACLE: VLM chỉ ở ô mà đáp án ghi viết tay/dưới dấu (không triển khai được) | handwritten | 2 | 0.50 | 0.00 | 0.50 |
| ORACLE: VLM chỉ ở ô mà đáp án ghi viết tay/dưới dấu (không triển khai được) | under_stamp | 3 | 1.00 | 0.00 | 0.00 |

#### E. Trường hạn: quy tắc tự nhận / từ chối

Mỗi quy tắc chỉ TỰ NHẬN một ngày khi các nguồn đồng thuận, ngược lại từ chối (chuyển người duyệt). `sai` gồm cả trường hợp giấy không ghi hạn mà quy tắc vẫn ra ngày. Cận trên là Clopper-Pearson MỘT PHÍA 95% của tỉ lệ sai trong số đã tự nhận. Để KHẲNG ĐỊNH tỉ lệ sai <= 1% với 0 lỗi quan sát cần tối thiểu 299 lần tự nhận đúng (<= 2%: 149; <= 5%: 59).

Quy tắc được chọn trên DEV: **any-model=filename**.

| quy tắc | tự nhận | đúng | sai | trong đó 'giấy không có hạn' | tự động hóa (đúng / có hạn thật) | tỉ lệ sai | cận trên 95% |
|---|---|---|---|---|---|---|---|
| regex | 7 | 6 | 1 | 0 | 0.75 (6/8) | 0.14 | 0.52 |
| llm | 8 | 7 | 1 | 0 | 0.88 (7/8) | 0.12 | 0.47 |
| vlm | 8 | 8 | 0 | 0 | 1.00 (8/8) | 0.00 | 0.31 |
| filename | 7 | 5 | 2 | 0 | 0.62 (5/8) | 0.29 | 0.66 |
| regex=llm | 7 | 6 | 1 | 0 | 0.75 (6/8) | 0.14 | 0.52 |
| llm=vlm | 7 | 7 | 0 | 0 | 0.88 (7/8) | 0.00 | 0.35 |
| regex=vlm | 6 | 6 | 0 | 0 | 0.75 (6/8) | 0.00 | 0.39 |
| regex=llm=vlm | 6 | 6 | 0 | 0 | 0.75 (6/8) | 0.00 | 0.39 |
| 2-of-3 (regex,llm,vlm) | 8 | 7 | 1 | 0 | 0.88 (7/8) | 0.12 | 0.47 |
| vlm=filename | 5 | 5 | 0 | 0 | 0.62 (5/8) | 0.00 | 0.45 |
| llm=filename | 4 | 4 | 0 | 0 | 0.50 (4/8) | 0.00 | 0.53 |
| regex=filename | 4 | 4 | 0 | 0 | 0.50 (4/8) | 0.00 | 0.53 |
| 2-of-4 (regex,llm,vlm,filename) | 7 | 7 | 0 | 0 | 0.88 (7/8) | 0.00 | 0.35 |
| (llm=vlm) or (any-two incl. filename) | 7 | 7 | 0 | 0 | 0.88 (7/8) | 0.00 | 0.35 |
| (regex=vlm) or (llm=vlm) or (any OCR-method = filename) | 7 | 7 | 0 | 0 | 0.88 (7/8) | 0.00 | 0.35 |
| **any-model=filename** | 5 | 5 | 0 | 0 | 0.62 (5/8) | 0.00 | 0.45 |
| (llm=vlm) or any-model=filename | 8 | 8 | 0 | 0 | 1.00 (8/8) | 0.00 | 0.31 |

Chuyển người duyệt theo quy tắc đã chọn: 3 trường hạn (trong đó 3 có hạn thật); có gợi ý (luật, rồi LLM, rồi VLM): 3, gợi ý đúng 3; gợi ý ra ngày dù giấy không ghi hạn: 0. Người duyệt chỉ cần xác nhận/sửa chứ không phải đọc từ đầu.

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


## Phụ lục DEV / all

### Kết quả DEV (đáp án: `all`)

Số đơn vị: 76 (CC_TAP_HUAN_VC_HNH 19, GCN_DDK_BAN_LE_XD 21, HD_MUA_BAN 26, PHIEU_XUAT_KHO 10). Khoảng tin cậy 95%: bootstrap percentile theo đơn vị. `F1 chặt` = so sánh sau chuẩn hóa; `F1 mềm` = như chặt nhưng văn bản bỏ dấu/dấu câu, chứa nhau, 'tên + MST' khớp theo tên. 

#### A. Tổng quan theo phương pháp × nguồn văn bản

| cấu hình | n | F1 chặt (toàn bộ trường) | F1 mềm | F1 ngày | F1 số | F1 mã | F1 văn bản chặt | F1 văn bản mềm | đúng mọi trường bắt buộc (chặt) | (mềm) | hạn: đúng | hạn: bỏ trống | hạn: **sai giá trị** | n hạn |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| regex@ocr_v2 | 76 | 0.61 [0.56; 0.66] | 0.84 [0.80; 0.88] | 0.91 | 0.90 | 0.95 | 0.29 | 0.76 | 0.22 (17/76) | 0.59 | 0.83 [0.73; 0.92] | 0.12 [0.05; 0.21] | 0.05 [0.00; 0.10] | 64 |
| regex@ocr_llm_haiku | 76 | 0.68 [0.65; 0.71] | 0.92 [0.89; 0.94] | 0.98 | n/a | 0.86 | 0.49 | 0.94 | 0.41 (31/76) | 0.75 | 1.00 [1.00; 1.00] | 0.00 [0.00; 0.00] | 0.00 [0.00; 0.00] | 58 |
| regex@text_layer | 10 | 0.85 [0.79; 0.89] | 0.97 [0.92; 1.00] | 1.00 | 0.90 | 0.99 | 0.66 | 1.00 | 0.00 (0/10) | 1.00 | n/a | n/a | n/a | 0 |
| filename | 76 | 0.11 [0.08; 0.14] | 0.11 [0.08; 0.14] | 0.35 | n/a | n/a | n/a | n/a | 0.00 (0/76) | 0.00 | 0.59 [0.47; 0.71] | 0.39 [0.27; 0.52] | 0.02 [0.00; 0.05] | 64 |
| gliner@ocr_v2 | 76 | 0.35 [0.31; 0.39] | 0.45 [0.42; 0.49] | 0.91 | n/a | n/a | 0.01 | 0.23 | 0.00 (0/76) | 0.00 | 0.84 [0.75; 0.93] | 0.11 [0.04; 0.19] | 0.05 [0.00; 0.10] | 64 |
| gliner@ocr_llm_haiku | 76 | 0.35 [0.32; 0.39] | 0.47 [0.45; 0.50] | 0.75 | n/a | n/a | 0.17 | 0.42 | 0.00 (0/76) | 0.00 | 0.67 [0.55; 0.79] | 0.00 [0.00; 0.00] | 0.33 [0.21; 0.45] | 58 |
| gliner@text_layer | 10 | 0.12 [0.12; 0.12] | 0.35 [0.35; 0.35] | 1.00 | n/a | n/a | n/a | 0.57 | 0.00 (0/10) | 0.00 | n/a | n/a | n/a | 0 |
| llm@ocr_v2 | 76 | 0.67 [0.60; 0.72] | 0.85 [0.81; 0.89] | 0.87 | 0.90 | 0.93 | 0.44 | 0.81 | 0.36 (27/76) | 0.59 | 0.81 [0.71; 0.90] | 0.12 [0.05; 0.21] | 0.06 [0.01; 0.13] | 64 |
| llm@ocr_llm_haiku | 76 | 0.75 [0.71; 0.78] | 0.91 [0.89; 0.93] | 0.96 | 0.10 | 0.94 | 0.63 | 0.94 | 0.58 (44/76) | 0.87 | 1.00 [1.00; 1.00] | 0.00 [0.00; 0.00] | 0.00 [0.00; 0.00] | 58 |
| llm@text_layer | 10 | 0.94 [0.89; 0.98] | 0.98 [0.94; 1.00] | 1.00 | 0.90 | 1.00 | 0.88 | 1.00 | 0.90 (9/10) | 1.00 | n/a | n/a | n/a | 0 |
| vlm | 76 | 0.73 [0.68; 0.78] | 0.89 [0.87; 0.92] | 0.90 | 1.00 | 0.91 | 0.56 | 0.88 | 0.49 (37/76) | 0.75 | 0.88 [0.79; 0.95] | 0.09 [0.03; 0.17] | 0.03 [0.00; 0.08] | 64 |
| cascade regex→llm @ocr_v2 | 76 | 0.62 [0.56; 0.67] | 0.87 [0.83; 0.90] | 0.90 | 0.90 | 0.93 | 0.33 | 0.82 | 0.24 (18/76) | 0.62 | 0.84 [0.75; 0.93] | 0.09 [0.03; 0.17] | 0.06 [0.01; 0.13] | 64 |
| cascade llm→regex @ocr_v2 | 76 | 0.68 [0.62; 0.74] | 0.87 [0.83; 0.91] | 0.88 | 0.90 | 0.93 | 0.47 | 0.84 | 0.36 (27/76) | 0.59 | 0.84 [0.75; 0.93] | 0.09 [0.03; 0.17] | 0.06 [0.01; 0.13] | 64 |
| cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | 76 | 0.69 [0.63; 0.74] | 0.88 [0.83; 0.91] | 0.90 | 0.90 | 0.93 | 0.47 | 0.84 | 0.37 (28/76) | 0.62 | 0.84 [0.75; 0.93] | 0.09 [0.03; 0.17] | 0.06 [0.01; 0.13] | 64 |
| cascade regex→llm→vlm @ocr_v2 | 76 | 0.62 [0.57; 0.67] | 0.87 [0.83; 0.91] | 0.91 | 0.90 | 0.93 | 0.34 | 0.83 | 0.25 (19/76) | 0.64 | 0.89 [0.81; 0.97] | 0.05 [0.00; 0.11] | 0.06 [0.01; 0.13] | 64 |
| cascade + từ chối hạn [any-model=filename] | 76 | 0.67 [0.61; 0.73] | 0.87 [0.82; 0.90] | 0.85 | 0.90 | 0.93 | 0.47 | 0.84 | 0.37 (28/76) | 0.63 | 0.58 [0.45; 0.70] | 0.42 [0.30; 0.55] | 0.00 [0.00; 0.00] | 64 |
| ORACLE: VLM chỉ ở ô mà đáp án ghi viết tay/dưới dấu (không triển khai được) | 76 | 0.71 [0.65; 0.76] | 0.89 [0.86; 0.92] | 0.91 | 0.90 | 0.97 | 0.50 | 0.86 | 0.38 (29/76) | 0.64 | 0.88 [0.78; 0.95] | 0.06 [0.01; 0.13] | 0.06 [0.01; 0.13] | 64 |
| regex@ocr_v2 (cùng tập đơn vị với text_layer) | 10 | 0.85 [0.79; 0.89] | 0.97 [0.92; 1.00] | 1.00 | 0.90 | 0.99 | 0.66 | 1.00 | 0.00 (0/10) | 1.00 | n/a | n/a | n/a | 0 |
| gliner@ocr_v2 (cùng tập đơn vị với text_layer) | 10 | 0.12 [0.12; 0.12] | 0.35 [0.35; 0.35] | 1.00 | n/a | n/a | n/a | 0.57 | 0.00 (0/10) | 0.00 | n/a | n/a | n/a | 0 |
| llm@ocr_v2 (cùng tập đơn vị với text_layer) | 10 | 0.94 [0.89; 0.98] | 0.98 [0.94; 1.00] | 1.00 | 0.90 | 1.00 | 0.88 | 1.00 | 0.90 (9/10) | 1.00 | n/a | n/a | n/a | 0 |

Ghi chú: `F1 ngày` gộp mọi trường kiểu ngày (hạn, ngày cấp, ngày ký...). `n hạn` = số trường hạn có đáp án. `đúng mọi trường bắt buộc` dùng so sánh chặt.

#### B. Theo loại tài liệu (so sánh chặt; trong ngoặc: F1 mềm)

> `CC_TAP_HUAN_VC_HNH` và `PHIEU_XUAT_KHO` gần như MỘT biểu mẫu duy nhất (và phiếu xuất kho là bản số hóa sạch): điểm cao ở hai loại này lạc quan, không suy ra cho biểu mẫu mới.

| loại | cấu hình | n | F1 chặt (mềm) | đúng mọi trường bắt buộc | hạn: đúng / bỏ trống / **sai** (n) |
|---|---|---|---|---|---|
| CC_TAP_HUAN_VC_HNH | regex@ocr_v2 | 19 | 0.64 (0.80) | 0.89 (17/19); mềm 0.89 | 0.95 / 0.00 / 0.05 (19) |
| CC_TAP_HUAN_VC_HNH | gliner@ocr_v2 | 19 | 0.55 (0.66) | 0.00 (0/19); mềm 0.00 | 0.95 / 0.00 / 0.05 (19) |
| CC_TAP_HUAN_VC_HNH | llm@ocr_v2 | 19 | 0.82 (0.93) | 0.89 (17/19); mềm 0.89 | 0.95 / 0.00 / 0.05 (19) |
| CC_TAP_HUAN_VC_HNH | vlm | 19 | 0.99 (0.99) | 1.00 (19/19); mềm 1.00 | 1.00 / 0.00 / 0.00 (19) |
| CC_TAP_HUAN_VC_HNH | cascade regex→llm @ocr_v2 | 19 | 0.69 (0.92) | 0.95 (18/19); mềm 0.95 | 0.95 / 0.00 / 0.05 (19) |
| CC_TAP_HUAN_VC_HNH | cascade llm→regex @ocr_v2 | 19 | 0.82 (0.93) | 0.89 (17/19); mềm 0.89 | 0.95 / 0.00 / 0.05 (19) |
| CC_TAP_HUAN_VC_HNH | cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | 19 | 0.82 (0.94) | 0.95 (18/19); mềm 0.95 | 0.95 / 0.00 / 0.05 (19) |
| CC_TAP_HUAN_VC_HNH | cascade regex→llm→vlm @ocr_v2 | 19 | 0.71 (0.93) | 0.95 (18/19); mềm 0.95 | 0.95 / 0.00 / 0.05 (19) |
| CC_TAP_HUAN_VC_HNH | cascade + từ chối hạn [any-model=filename] | 19 | 0.82 (0.93) | 0.84 (16/19); mềm 0.84 | 0.84 / 0.16 / 0.00 (19) |
| GCN_DDK_BAN_LE_XD | regex@ocr_v2 | 21 | 0.39 (0.71) | 0.00 (0/21); mềm 0.05 | 0.67 / 0.24 / 0.10 (21) |
| GCN_DDK_BAN_LE_XD | gliner@ocr_v2 | 21 | 0.24 (0.31) | 0.00 (0/21); mềm 0.00 | 0.67 / 0.24 / 0.10 (21) |
| GCN_DDK_BAN_LE_XD | llm@ocr_v2 | 21 | 0.43 (0.74) | 0.00 (0/21); mềm 0.00 | 0.71 / 0.14 / 0.14 (21) |
| GCN_DDK_BAN_LE_XD | vlm | 21 | 0.59 (0.87) | 0.52 (11/21); mềm 0.62 | 0.90 / 0.00 / 0.10 (21) |
| GCN_DDK_BAN_LE_XD | cascade regex→llm @ocr_v2 | 21 | 0.39 (0.71) | 0.00 (0/21); mềm 0.05 | 0.71 / 0.14 / 0.14 (21) |
| GCN_DDK_BAN_LE_XD | cascade llm→regex @ocr_v2 | 21 | 0.43 (0.74) | 0.00 (0/21); mềm 0.00 | 0.71 / 0.14 / 0.14 (21) |
| GCN_DDK_BAN_LE_XD | cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | 21 | 0.44 (0.75) | 0.00 (0/21); mềm 0.05 | 0.71 / 0.14 / 0.14 (21) |
| GCN_DDK_BAN_LE_XD | cascade regex→llm→vlm @ocr_v2 | 21 | 0.41 (0.72) | 0.05 (1/21); mềm 0.14 | 0.86 / 0.00 / 0.14 (21) |
| GCN_DDK_BAN_LE_XD | cascade + từ chối hạn [any-model=filename] | 21 | 0.44 (0.75) | 0.10 (2/21); mềm 0.19 | 0.67 / 0.33 / 0.00 (21) |
| HD_MUA_BAN | regex@ocr_v2 | 26 | 0.61 (0.88) | 0.00 (0/26); mềm 0.65 | 0.88 / 0.12 / 0.00 (24) |
| HD_MUA_BAN | gliner@ocr_v2 | 26 | 0.44 (0.48) | 0.00 (0/26); mềm 0.00 | 0.92 / 0.08 / 0.00 (24) |
| HD_MUA_BAN | llm@ocr_v2 | 26 | 0.59 (0.81) | 0.04 (1/26); mềm 0.69 | 0.79 / 0.21 / 0.00 (24) |
| HD_MUA_BAN | vlm | 26 | 0.62 (0.85) | 0.27 (7/26); mềm 0.96 | 0.75 / 0.25 / 0.00 (24) |
| HD_MUA_BAN | cascade regex→llm @ocr_v2 | 26 | 0.60 (0.90) | 0.00 (0/26); mềm 0.69 | 0.88 / 0.12 / 0.00 (24) |
| HD_MUA_BAN | cascade llm→regex @ocr_v2 | 26 | 0.66 (0.88) | 0.04 (1/26); mềm 0.69 | 0.88 / 0.12 / 0.00 (24) |
| HD_MUA_BAN | cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | 26 | 0.66 (0.88) | 0.04 (1/26); mềm 0.69 | 0.88 / 0.12 / 0.00 (24) |
| HD_MUA_BAN | cascade regex→llm→vlm @ocr_v2 | 26 | 0.60 (0.90) | 0.00 (0/26); mềm 0.69 | 0.88 / 0.12 / 0.00 (24) |
| HD_MUA_BAN | cascade + từ chối hạn [any-model=filename] | 26 | 0.61 (0.84) | 0.04 (1/26); mềm 0.69 | 0.29 / 0.71 / 0.00 (24) |
| PHIEU_XUAT_KHO | regex@ocr_v2 | 10 | 0.85 (0.97) | 0.00 (0/10); mềm 1.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | gliner@ocr_v2 | 10 | 0.12 (0.35) | 0.00 (0/10); mềm 0.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | llm@ocr_v2 | 10 | 0.94 (0.98) | 0.90 (9/10); mềm 1.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | vlm | 10 | 0.83 (0.89) | 0.00 (0/10); mềm 0.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | cascade regex→llm @ocr_v2 | 10 | 0.86 (0.98) | 0.00 (0/10); mềm 1.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | cascade llm→regex @ocr_v2 | 10 | 0.94 (0.98) | 0.90 (9/10); mềm 1.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | 10 | 0.94 (0.98) | 0.90 (9/10); mềm 1.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | cascade regex→llm→vlm @ocr_v2 | 10 | 0.86 (0.98) | 0.00 (0/10); mềm 1.00 | (không có trường hạn) |
| PHIEU_XUAT_KHO | cascade + từ chối hạn [any-model=filename] | 10 | 0.94 (0.98) | 0.90 (9/10); mềm 1.00 | (không có trường hạn) |

#### C. Cái giá của OCR: cùng phương pháp, khác nguồn văn bản

`ocr_llm_haiku` chỉ có 2 trang đầu của tệp và đáp án ở trang > 2 bị loại khỏi điểm (cho công bằng); nguồn này KHÔNG chạy được on-premise (cận trên). `text_layer` chỉ có ở trang số hóa nên chấm trên tập con các đơn vị có chữ thật; cột cuối là chính phương pháp đó trên OCR cục bộ ở CÙNG tập con.

| phương pháp | nguồn | n | F1 chặt | F1 mềm | F1 ngày | F1 mã | F1 văn bản mềm | hạn đúng / **sai** (n) |
|---|---|---|---|---|---|---|---|---|
| regex | ocr_v2 | 76 | 0.61 [0.56; 0.66] | 0.84 [0.80; 0.88] | 0.91 | 0.95 | 0.76 | 0.83 / 0.05 (64) |
| regex | ocr_llm_haiku | 76 | 0.68 [0.65; 0.71] | 0.92 [0.89; 0.94] | 0.98 | 0.86 | 0.94 | 1.00 / 0.00 (58) |
| regex | text_layer | 10 | 0.85 [0.79; 0.89] | 0.97 [0.92; 1.00] | 1.00 | 0.99 | 1.00 | n/a / n/a (0) |
| regex | ocr_v2 (cùng tập đơn vị với text_layer) | 10 | 0.85 [0.79; 0.89] | 0.97 [0.92; 1.00] | 1.00 | 0.99 | 1.00 | n/a / n/a (0) |
| gliner | ocr_v2 | 76 | 0.35 [0.31; 0.39] | 0.45 [0.42; 0.49] | 0.91 | n/a | 0.23 | 0.84 / 0.05 (64) |
| gliner | ocr_llm_haiku | 76 | 0.35 [0.32; 0.39] | 0.47 [0.45; 0.50] | 0.75 | n/a | 0.42 | 0.67 / 0.33 (58) |
| gliner | text_layer | 10 | 0.12 [0.12; 0.12] | 0.35 [0.35; 0.35] | 1.00 | n/a | 0.57 | n/a / n/a (0) |
| gliner | ocr_v2 (cùng tập đơn vị với text_layer) | 10 | 0.12 [0.12; 0.12] | 0.35 [0.35; 0.35] | 1.00 | n/a | 0.57 | n/a / n/a (0) |
| llm | ocr_v2 | 76 | 0.67 [0.60; 0.72] | 0.85 [0.81; 0.89] | 0.87 | 0.93 | 0.81 | 0.81 / 0.06 (64) |
| llm | ocr_llm_haiku | 76 | 0.75 [0.71; 0.78] | 0.91 [0.89; 0.93] | 0.96 | 0.94 | 0.94 | 1.00 / 0.00 (58) |
| llm | text_layer | 10 | 0.94 [0.89; 0.98] | 0.98 [0.94; 1.00] | 1.00 | 1.00 | 1.00 | n/a / n/a (0) |
| llm | ocr_v2 (cùng tập đơn vị với text_layer) | 10 | 0.94 [0.89; 0.98] | 0.98 [0.94; 1.00] | 1.00 | 1.00 | 1.00 | n/a / n/a (0) |

#### D. Theo mực viết của đáp án silver (trường có đáp án; so sánh mềm)

Mực do người chú thích ghi (Haiku là chính), nên có thể sai. Chỉ tính trường có giá trị trong đáp án.

| cấu hình | mực | n trường | đúng | bỏ trống | **sai giá trị** |
|---|---|---|---|---|---|
| regex@ocr_v2 | printed | 599 | 0.82 | 0.11 | 0.07 |
| regex@ocr_v2 | handwritten | 34 | 0.53 | 0.29 | 0.18 |
| regex@ocr_v2 | under_stamp | 20 | 0.35 | 0.45 | 0.20 |
| gliner@ocr_v2 | printed | 599 | 0.31 | 0.65 | 0.04 |
| gliner@ocr_v2 | handwritten | 34 | 0.41 | 0.53 | 0.06 |
| gliner@ocr_v2 | under_stamp | 20 | 0.00 | 1.00 | 0.00 |
| llm@ocr_v2 | printed | 599 | 0.84 | 0.07 | 0.09 |
| llm@ocr_v2 | handwritten | 34 | 0.59 | 0.00 | 0.41 |
| llm@ocr_v2 | under_stamp | 20 | 0.65 | 0.10 | 0.25 |
| vlm | printed | 599 | 0.87 | 0.08 | 0.06 |
| vlm | handwritten | 34 | 0.76 | 0.00 | 0.24 |
| vlm | under_stamp | 20 | 0.95 | 0.00 | 0.05 |
| cascade regex→llm @ocr_v2 | printed | 599 | 0.89 | 0.03 | 0.09 |
| cascade regex→llm @ocr_v2 | handwritten | 34 | 0.56 | 0.00 | 0.44 |
| cascade regex→llm @ocr_v2 | under_stamp | 20 | 0.55 | 0.10 | 0.35 |
| cascade llm→regex @ocr_v2 | printed | 599 | 0.89 | 0.03 | 0.09 |
| cascade llm→regex @ocr_v2 | handwritten | 34 | 0.59 | 0.00 | 0.41 |
| cascade llm→regex @ocr_v2 | under_stamp | 20 | 0.65 | 0.10 | 0.25 |
| cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | printed | 599 | 0.89 | 0.03 | 0.08 |
| cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | handwritten | 34 | 0.62 | 0.00 | 0.38 |
| cascade theo kiểu (văn bản: llm→luật; ngày/số/mã: luật→llm) @ocr_v2 | under_stamp | 20 | 0.65 | 0.10 | 0.25 |
| cascade regex→llm→vlm @ocr_v2 | printed | 599 | 0.90 | 0.01 | 0.09 |
| cascade regex→llm→vlm @ocr_v2 | handwritten | 34 | 0.56 | 0.00 | 0.44 |
| cascade regex→llm→vlm @ocr_v2 | under_stamp | 20 | 0.65 | 0.00 | 0.35 |
| cascade + từ chối hạn [any-model=filename] | printed | 599 | 0.87 | 0.06 | 0.08 |
| cascade + từ chối hạn [any-model=filename] | handwritten | 34 | 0.53 | 0.15 | 0.32 |
| cascade + từ chối hạn [any-model=filename] | under_stamp | 20 | 0.75 | 0.00 | 0.25 |
| ORACLE: VLM chỉ ở ô mà đáp án ghi viết tay/dưới dấu (không triển khai được) | printed | 599 | 0.89 | 0.03 | 0.08 |
| ORACLE: VLM chỉ ở ô mà đáp án ghi viết tay/dưới dấu (không triển khai được) | handwritten | 34 | 0.76 | 0.00 | 0.24 |
| ORACLE: VLM chỉ ở ô mà đáp án ghi viết tay/dưới dấu (không triển khai được) | under_stamp | 20 | 0.95 | 0.00 | 0.05 |

#### E. Trường hạn: quy tắc tự nhận / từ chối

Mỗi quy tắc chỉ TỰ NHẬN một ngày khi các nguồn đồng thuận, ngược lại từ chối (chuyển người duyệt). `sai` gồm cả trường hợp giấy không ghi hạn mà quy tắc vẫn ra ngày. Cận trên là Clopper-Pearson MỘT PHÍA 95% của tỉ lệ sai trong số đã tự nhận. Để KHẲNG ĐỊNH tỉ lệ sai <= 1% với 0 lỗi quan sát cần tối thiểu 299 lần tự nhận đúng (<= 2%: 149; <= 5%: 59).

Quy tắc được chọn trên DEV: **any-model=filename**.

| quy tắc | tự nhận | đúng | sai | trong đó 'giấy không có hạn' | tự động hóa (đúng / có hạn thật) | tỉ lệ sai | cận trên 95% |
|---|---|---|---|---|---|---|---|
| regex | 55 | 53 | 2 | 0 | 0.83 (53/64) | 0.04 | 0.11 |
| llm | 55 | 52 | 3 | 0 | 0.81 (52/64) | 0.05 | 0.13 |
| vlm | 58 | 56 | 2 | 0 | 0.88 (56/64) | 0.03 | 0.10 |
| filename | 40 | 38 | 2 | 1 | 0.59 (38/64) | 0.05 | 0.15 |
| regex=llm | 53 | 51 | 2 | 0 | 0.80 (51/64) | 0.04 | 0.11 |
| llm=vlm | 52 | 51 | 1 | 0 | 0.80 (51/64) | 0.02 | 0.09 |
| regex=vlm | 51 | 50 | 1 | 0 | 0.78 (50/64) | 0.02 | 0.09 |
| regex=llm=vlm | 51 | 50 | 1 | 0 | 0.78 (50/64) | 0.02 | 0.09 |
| 2-of-3 (regex,llm,vlm) | 54 | 52 | 2 | 0 | 0.81 (52/64) | 0.04 | 0.11 |
| vlm=filename | 36 | 36 | 0 | 0 | 0.56 (36/64) | 0.00 | 0.08 |
| llm=filename | 31 | 31 | 0 | 0 | 0.48 (31/64) | 0.00 | 0.09 |
| regex=filename | 31 | 31 | 0 | 0 | 0.48 (31/64) | 0.00 | 0.09 |
| 2-of-4 (regex,llm,vlm,filename) | 58 | 57 | 1 | 0 | 0.89 (57/64) | 0.02 | 0.08 |
| (llm=vlm) or (any-two incl. filename) | 58 | 57 | 1 | 0 | 0.89 (57/64) | 0.02 | 0.08 |
| (regex=vlm) or (llm=vlm) or (any OCR-method = filename) | 53 | 52 | 1 | 0 | 0.81 (52/64) | 0.02 | 0.09 |
| **any-model=filename** | 37 | 37 | 0 | 0 | 0.58 (37/64) | 0.00 | 0.08 |
| (llm=vlm) or any-model=filename | 58 | 57 | 1 | 0 | 0.89 (57/64) | 0.02 | 0.08 |

Chuyển người duyệt theo quy tắc đã chọn: 29 trường hạn (trong đó 27 có hạn thật); có gợi ý (luật, rồi LLM, rồi VLM): 24, gợi ý đúng 22; gợi ý ra ngày dù giấy không ghi hạn: 0. Người duyệt chỉ cần xác nhận/sửa chứ không phải đọc từ đầu.

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


## Phụ lục DEV / trusted

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


