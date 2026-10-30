# Cấu hình trích xuất đóng băng dùng cho loại tài liệu mới (Nhóm 4, giai đoạn 3, thí nghiệm 03)

> Bản tự sinh bởi `build_results3_md.py` từ `results3_base.json`, `results3_improved.json`, `causes_DEV_cascade.json`. Tiếng Việt, viết cho sinh viên năm cuối ngành AI.
> `data/labels_v2.csv` sha1[:10] = `eb3348713a`; silver v2 `fields_silver_v2.jsonl` sha1[:10] = `45d6384f3d`; ngày chạy 2026-10-16.
> Tái lập một dòng: `run_zero_tuning.py` → `make_results3.py --set base` → `dev_iterate.py` → `freeze3.py` → `run_zero_tuning`-giống-lệnh luật chung (xem mục 9) → `make_results3.py --set improved --final-test` → `classify_errors.py` → `build_results3_md.py`.
> Nguồn văn bản: `data/ocr_v2.jsonl` (OCR cục bộ) cho luật và LLM; ảnh trang `gold/v2/pages_v2/` cho VLM; tên tệp (`relative_path` trong `gold/v2/units_v2.csv`) cho ngày trong tên tệp. Đáp án: silver v2 (Haiku + Sonnet đọc ảnh, Opus phân xử mù 135 mục), **không có người kiểm**: mọi số là "so với đáp án máy".

## 0. Tóm tắt

**Câu hỏi.** Cấu hình đóng băng ở giai đoạn 2 (luật cho ngày/số/mã + LLM `qwen3.5:4b` cho văn bản; quy tắc tự nhận hạn `any-model=filename`) dùng ngay cho 17 loại tài liệu có trường hạn mà ta CHƯA từng chỉnh luật thì được bao nhiêu, và hỏng ở đâu?

* **Luật giai đoạn 2 không có gì cho loại mới.** `src/extraction/field_rules.py` chỉ có luật cho 4 loại cũ; với 17 loại mới luật trả toàn null (84/84 đơn vị, `status=ok` nhưng rỗng). Cascade "luật→LLM" thực chất chỉ còn là LLM. Ngoài ra `src/extraction/schemas.py` chỉ liệt kê 4 loại (`SUPPORTED_TYPES`): sản phẩm hiện tại trả `UnsupportedDocType` (status `error`) cho 17 loại này, nên thí nghiệm này đo *phương pháp* chứ không phải đường ống sản xuất.
* **Zero-tuning, cascade (= LLM) trên 84 đơn vị**: F1 mềm 0.75 [0.70; 0.79], F1 chặt 0.56 [0.51; 0.61] (so với giai đoạn 2 trên 4 loại cũ: TEST 0.90 mềm / 0.72 chặt; hai tập khác loại nên chỉ đặt cạnh nhau). VLM đọc ảnh tốt hơn LLM-trên-OCR: F1 mềm 0.83 [0.80; 0.86].
* **Trường hạn (62 trường có đáp án hạn thật, gộp DEV+TEST+EXCLUDED)**: cascade đúng 52, bỏ trống 8, **sai giá trị 2** (cận trên 95% 0.10); VLM đúng 58, bỏ trống 4, sai 0 (cận trên 0.05).
* **Quy tắc tự nhận hạn giai đoạn 2 (`any-model=filename`) gần như không dùng được cho loại mới**: tự nhận 24/62 trường hạn thật (39%), sai 0 (cận trên 95% 0.12). Giai đoạn 2 (4 loại cũ): DEV 37/64 = 58%, TEST 12/16 = 75%, 0 sai (cận trên 8% và 22%). Lý do: ngày trong tên tệp của loại mới KHÔNG luôn là ngày hết hạn (đứng một mình sai 17/40 lần có ngày ở DEV, 14 trong số đó là giấy không có hạn), nên quy tắc đòi một mô hình đọc trùng tên tệp chỉ nhận được phần nhỏ; 10 đơn vị EXCLUDED là tệp ghép nên không có ngày tên tệp áp dụng.
* **Một vòng cải tiến chung chỉnh trên DEV**: thêm luật ngày chung (`methods/generic_date_rules.py`: nhãn hạn/hiệu lực/ngày ký/ngày cấp dùng chung cho mọi loại, từ chối "không thời hạn"), chọn quy tắc tự nhận `regex=llm` trên DEV. Trên phần KHÔNG chỉnh (TEST + EXCLUDED, 22 đơn vị, chạy MỘT lần): quy tắc mới tự nhận 12/17 trường hạn thật (71%), **sai 0** (cận trên 95% 0.22); quy tắc cũ cùng tập: 3/17 (18%). F1 các trường khác gần như không đổi (luật chung chỉ phủ trường ngày, LLM vẫn là nguồn chính).
* **Chưa chứng minh** tỉ lệ sai ≤ 1% (cần ≥ 299 lần tự nhận đúng liên tiếp; ta có 47 trên cả 84 đơn vị, trong đó chỉ 12 là ngoài mẫu chỉnh). Mọi con số là so với đáp án máy chưa có người kiểm; tập TEST ở đây chỉ là *thêm mẫu* cho cấu hình không chỉnh (không có gì được chỉnh nên TEST không bị "khóa" theo nghĩa giai đoạn 2); chỉ ở mục 5 TEST+EXCLUDED mới là phần ngoài mẫu chỉnh (và tổng hợp zero-tuning của hai tập này đã được xem trước khi chọn cải tiến, dù không xem từng đơn vị).

## 1. Thiết lập

* **Đơn vị chấm** = `(doc_id, segment)`; 84 đơn vị thuộc 17 loại: DEV 62, TEST 12, EXCLUDED 10 (EXCLUDED = tệp ghép/loại khỏi chia DEV/TEST của nhóm 00: **không đại diện** cho tệp riêng lẻ; báo riêng, không gộp vào con số chính). Loại thiếu mẫu: nhiều loại chỉ có 1–3 đơn vị DEV (xem bảng theo loại).
* **Một biểu mẫu, nhiều tài liệu**: `HD_VAN_CHUYEN` (20 đơn vị DEV, cùng một mẫu hợp đồng) chiếm 1/3 DEV nên kéo điểm gộp theo mẫu đó; kết luận theo loại cho loại 1–3 đơn vị chỉ là minh họa.
* **Cấu hình**: đúng như giai đoạn 2: luật `src/extraction/field_rules.py` (trống cho loại mới), LLM `qwen3.5:4b` prompt `v1` trên `ocr_v2` (`num_ctx` 6144, 4B Q4_K_M), VLM cùng mô hình trên 4 ảnh đầu của `gold/v2/pages_v2`, ngày trong tên tệp, cascade theo kiểu (văn bản: LLM→luật; ngày/số/mã: luật→LLM), tự nhận hạn `any-model=filename`. Chỉ trường PII không được hỏi/chấm (`so_dinh_danh`, `so_gplx`, `ngay_sinh`, `nam_sinh`); `ho_ten` có chấm.
* **Chấm**: `eval/field_metrics.py` (4 chế độ so sánh; bảng dùng *chặt* và *mềm*), `lib.load_gold` giữ nguyên quy ước giai đoạn 2 (trường chỉ ghi thời hạn/cụm không phải ngày → không có ngày cụ thể; `[?]` → loại khỏi điểm). CI 95% = bootstrap percentile 1000 lần theo đơn vị; cận trên của tỉ lệ sai là Clopper–Pearson MỘT phía 95% (khi 0 sai trên n: ≈ 3/n). Luật "F1 của luật rỗng" = 0 (không TP, recall 0).
* **Tham số đường dẫn v2**: `lib.load_gold(path)` và `load_units(path=...)` đã có sẵn tham số; thêm `pages_dir` cho `LocalVlmJson` và `generic` cho `RegexRules` (mặc định giữ hành vi v1; 104 đơn vị v1 cho kết quả luật giống hệt cache giai đoạn 2).
* **Cache đĩa**: mọi lời gọi LLM/VLM nằm ở `teams/team4_extraction/_cache/ollama/` (chạy lại miễn phí, tất định); dự đoán ở `03_unseen_types/_cache/preds/` (không commit: có thể chứa họ tên).

## 2. Kết quả zero-tuning (cấu hình giai đoạn 2, chưa chỉnh gì)

Tập TEST/EXCLUDED ở đây chỉ là mẫu thêm (không có gì được chỉnh nên không thể rò rỉ); các tập báo riêng vì cỡ mẫu nhỏ và EXCLUDED là tệp ghép.

| tập (n đơn vị) | phương pháp | F1 chặt [CI 95%] | F1 mềm [CI] | đúng mọi trường bắt buộc (mềm) | hạn: đúng / bỏ trống / **sai** (n; cận trên 95% của tỉ lệ sai) | hạn: thừa khi giấy không có hạn |
|---|---|---|---|---|---|---|
| DEV (62) | luật/regex giai đoạn 2 (không có luật cho loại mới) | 0.00 (luật rỗng) | 0.00 (luật rỗng) | 0.00 | 0/45/**0** (n=45; sai ≤ 0.06) | 0/17 |
| DEV (62) | LLM cục bộ (văn bản OCR) | 0.52 [0.47; 0.58] | 0.74 [0.68; 0.80] | 0.50 | 35/8/**2** (n=45; sai ≤ 0.13) | 2/17 |
| DEV (62) | VLM cục bộ (ảnh trang) | 0.65 [0.61; 0.69] | 0.82 [0.79; 0.86] | 0.68 | 41/4/**0** (n=45; sai ≤ 0.06) | 1/17 |
| DEV (62) | ngày trong tên tệp | 0.11 [0.07; 0.14] | 0.11 [0.07; 0.14] | 0.00 | 23/19/**3** (n=45; sai ≤ 0.16) | 14/17 |
| DEV (62) | cascade theo kiểu (= LLM, vì luật rỗng) | 0.52 [0.47; 0.58] | 0.74 [0.68; 0.80] | 0.50 | 35/8/**2** (n=45; sai ≤ 0.13) | 2/17 |
| DEV (62) | cascade + tự nhận hạn `any-model=filename` (cấu hình giai đoạn 2) | 0.50 [0.45; 0.55] | 0.72 [0.66; 0.78] | 0.47 | 21/24/**0** (n=45; sai ≤ 0.06) | 0/17 |
| TEST (12) | luật/regex giai đoạn 2 (không có luật cho loại mới) | 0.00 (luật rỗng) | 0.00 (luật rỗng) | 0.00 | 0/8/**0** (n=8; sai ≤ 0.31) | 0/4 |
| TEST (12) | LLM cục bộ (văn bản OCR) | 0.55 [0.39; 0.67] | 0.71 [0.60; 0.80] | 0.08 | 8/0/**0** (n=8; sai ≤ 0.31) | 0/4 |
| TEST (12) | VLM cục bộ (ảnh trang) | 0.67 [0.57; 0.77] | 0.88 [0.81; 0.95] | 0.75 | 8/0/**0** (n=8; sai ≤ 0.31) | 0/4 |
| TEST (12) | ngày trong tên tệp | 0.07 [0.02; 0.15] | 0.07 [0.02; 0.15] | 0.00 | 3/5/**0** (n=8; sai ≤ 0.31) | 2/4 |
| TEST (12) | cascade theo kiểu (= LLM, vì luật rỗng) | 0.55 [0.39; 0.67] | 0.71 [0.60; 0.80] | 0.08 | 8/0/**0** (n=8; sai ≤ 0.31) | 0/4 |
| TEST (12) | cascade + tự nhận hạn `any-model=filename` (cấu hình giai đoạn 2) | 0.50 [0.34; 0.64] | 0.67 [0.56; 0.76] | 0.08 | 3/5/**0** (n=8; sai ≤ 0.31) | 0/4 |
| EXCLUDED (10) | luật/regex giai đoạn 2 (không có luật cho loại mới) | 0.00 (luật rỗng) | 0.00 (luật rỗng) | 0.00 | 0/9/**0** (n=9; sai ≤ 0.28) | 0/1 |
| EXCLUDED (10) | LLM cục bộ (văn bản OCR) | 0.72 [0.61; 0.79] | 0.80 [0.74; 0.84] | 0.40 | 9/0/**0** (n=9; sai ≤ 0.28) | 0/1 |
| EXCLUDED (10) | VLM cục bộ (ảnh trang) | 0.70 [0.57; 0.81] | 0.83 [0.70; 0.93] | 0.60 | 9/0/**0** (n=9; sai ≤ 0.28) | 0/1 |
| EXCLUDED (10) | ngày trong tên tệp | 0.00 (luật rỗng) | 0.00 (luật rỗng) | 0.00 | 0/9/**0** (n=9; sai ≤ 0.28) | 0/1 |
| EXCLUDED (10) | cascade theo kiểu (= LLM, vì luật rỗng) | 0.72 [0.61; 0.79] | 0.80 [0.74; 0.84] | 0.40 | 9/0/**0** (n=9; sai ≤ 0.28) | 0/1 |
| EXCLUDED (10) | cascade + tự nhận hạn `any-model=filename` (cấu hình giai đoạn 2) | 0.65 [0.53; 0.72] | 0.73 [0.66; 0.78] | 0.10 | 0/9/**0** (n=9; sai ≤ 0.28) | 0/1 |
| TEST+EXCLUDED (22) | luật/regex giai đoạn 2 (không có luật cho loại mới) | 0.00 (luật rỗng) | 0.00 (luật rỗng) | 0.00 | 0/17/**0** (n=17; sai ≤ 0.16) | 0/5 |
| TEST+EXCLUDED (22) | LLM cục bộ (văn bản OCR) | 0.64 [0.54; 0.72] | 0.76 [0.70; 0.81] | 0.23 | 17/0/**0** (n=17; sai ≤ 0.16) | 0/5 |
| TEST+EXCLUDED (22) | VLM cục bộ (ảnh trang) | 0.68 [0.59; 0.76] | 0.85 [0.78; 0.92] | 0.68 | 17/0/**0** (n=17; sai ≤ 0.16) | 0/5 |
| TEST+EXCLUDED (22) | ngày trong tên tệp | 0.04 [0.01; 0.08] | 0.04 [0.01; 0.08] | 0.00 | 3/14/**0** (n=17; sai ≤ 0.16) | 2/5 |
| TEST+EXCLUDED (22) | cascade theo kiểu (= LLM, vì luật rỗng) | 0.64 [0.54; 0.72] | 0.76 [0.70; 0.81] | 0.23 | 17/0/**0** (n=17; sai ≤ 0.16) | 0/5 |
| TEST+EXCLUDED (22) | cascade + tự nhận hạn `any-model=filename` (cấu hình giai đoạn 2) | 0.57 [0.47; 0.66] | 0.70 [0.64; 0.76] | 0.09 | 3/14/**0** (n=17; sai ≤ 0.16) | 0/5 |

**Theo kiểu trường** (F1 theo kiểu; n = số trường có đáp án):

| tập | phương pháp | ngày (n) | số (n) | mã (n) | văn bản chặt / mềm (n) |
|---|---|---|---|---|---|
| DEV | LLM cục bộ (văn bản OCR) | 0.84 (116) | 0.62 (13) | 0.71 (67) | 0.26 / 0.70 (194) |
| DEV | VLM cục bộ (ảnh trang) | 0.91 (116) | 0.85 (13) | 0.82 (67) | 0.41 / 0.77 (194) |
| TEST | LLM cục bộ (văn bản OCR) | 0.86 (22) | 1.00 (2) | 0.69 (13) | 0.32 / 0.63 (43) |
| TEST | VLM cục bộ (ảnh trang) | 0.90 (22) | 1.00 (2) | 0.92 (13) | 0.44 / 0.85 (43) |
| EXCLUDED | LLM cục bộ (văn bản OCR) | 0.97 (19) | n/a (0) | 0.70 (29) | 0.60 / 0.79 (37) |
| EXCLUDED | VLM cục bộ (ảnh trang) | 0.84 (19) | n/a (0) | 0.68 (29) | 0.63 / 0.93 (37) |
| TEST+EXCLUDED | LLM cục bộ (văn bản OCR) | 0.91 (41) | 1.00 (2) | 0.70 (42) | 0.45 / 0.71 (80) |
| TEST+EXCLUDED | VLM cục bộ (ảnh trang) | 0.88 (41) | 1.00 (2) | 0.76 (42) | 0.53 / 0.89 (80) |

* Ngày và mã tốt hơn văn bản chặt: văn bản dài (tên bên + mã số thuế, đoạn tuyến/giá cước) lệch ranh giới nên F1 chặt thấp (0.2–0.4), mềm cao hơn nhiều (0.6–0.9). Con số mềm là con số nên nhìn khi nói về "đọc đúng nội dung"; con số chặt cho biết còn bao xa mới nhập thẳng vào ERP.
* VLM hơn LLM-trên-OCR ở hầu hết kiểu trường, cùng chiều với giai đoạn 2; lưu ý bắt buộc 3 của giai đoạn 2 vẫn đúng (VLM và người chú thích cùng đọc ảnh).

**Theo loại tài liệu** (gộp DEV+TEST+EXCLUDED, vì không có chỉnh sửa nào; n đơn vị mỗi loại 1–25 nên CI rất rộng, đọc như minh họa; trường hạn: đúng/bỏ trống/**sai** trên số trường hạn có đáp án):

| loại | n đơn vị (DEV/TEST/EXCL) | F1 mềm: LLM (=cascade zero-tuning) | F1 mềm: VLM | hạn, cascade zero-tuning: đúng/trống/**sai** (n) | hạn, VLM | hạn, cascade+luật chung+`regex=llm` |
|---|---|---|---|---|---|---|
| BIEN_NHAN_THE_CHAP_PT | 0/0/4 | 0.81 [0.80; 0.82] | 0.78 [0.56; 0.95] | 4/0/**0** (4) | 4/0/**0** (4) | 4/0/**0** (4) |
| CCCD | 1/0/0 | 0.67 [0.67; 0.67] | 0.67 [0.67; 0.67] | 1/0/**0** (1) | 1/0/**0** (1) | 1/0/**0** (1) |
| CC_HUAN_LUYEN_PCCC | 3/0/0 | 0.53 [0.20; 0.77] | 0.67 [0.60; 0.80] | không có trường hạn có đáp án | không có trường hạn có đáp án | không có trường hạn có đáp án |
| CC_NGHIEP_VU_BVMT | 4/1/2 | 0.66 [0.45; 0.83] | 0.94 [0.83; 1.00] | 1/1/**0** (2) | 2/0/**0** (2) | 1/1/**0** (2) |
| DANG_KY_PHUONG_TIEN | 3/0/0 | 0.69 [0.53; 0.78] | 0.69 [0.46; 0.80] | 1/0/**0** (1) | 1/0/**0** (1) | 1/0/**0** (1) |
| GCN_ATKT_BVMT_PT | 1/0/0 | 1.00 [1.00; 1.00] | 0.77 [0.77; 0.77] | 1/0/**0** (1) | 1/0/**0** (1) | 1/0/**0** (1) |
| GCN_BAO_HIEM | 7/0/0 | 0.33 [0.17; 0.54] | 0.72 [0.60; 0.87] | 1/4/**2** (7) | 6/1/**0** (7) | 1/6/**0** (7) |
| GCN_KIEM_DINH_DO_LUONG | 0/1/3 | 0.83 [0.72; 0.89] | 0.96 [0.94; 0.99] | 4/0/**0** (4) | 4/0/**0** (4) | 0/4/**0** (4) |
| GIAY_UY_QUYEN | 3/0/0 | 0.83 [0.74; 1.00] | 0.87 [0.71; 1.00] | 1/0/**0** (1) | 1/0/**0** (1) | 1/0/**0** (1) |
| GPLX | 4/1/0 | 0.54 [0.31; 0.74] | 0.88 [0.86; 0.94] | 4/1/**0** (5) | 5/0/**0** (5) | 4/1/**0** (5) |
| GP_KD_VAN_TAI | 0/1/0 | 0.17 [0.17; 0.17] | 0.83 [0.83; 0.83] | không có trường hạn có đáp án | không có trường hạn có đáp án | không có trường hạn có đáp án |
| GP_VC_HANG_NGUY_HIEM | 2/0/0 | 0.62 [0.57; 0.67] | 0.87 [0.80; 0.93] | 2/0/**0** (2) | 2/0/**0** (2) | 2/0/**0** (2) |
| GXN_THUONG_NHAN_XD | 2/0/0 | 0.96 [0.92; 1.00] | 0.89 [0.86; 0.92] | 2/0/**0** (2) | 2/0/**0** (2) | 2/0/**0** (2) |
| HD_MUON_BON | 7/2/0 | 0.82 [0.78; 0.86] | 0.92 [0.84; 0.98] | không có trường hạn có đáp án | không có trường hạn có đáp án | không có trường hạn có đáp án |
| HD_NHUONG_QUYEN_DAI_LY | 5/0/0 | 0.94 [0.92; 0.97] | 1.00 [1.00; 1.00] | 5/0/**0** (5) | 5/0/**0** (5) | 5/0/**0** (5) |
| HD_THUE_TAI_SAN | 0/1/0 | 0.71 [0.71; 0.71] | 1.00 [1.00; 1.00] | 1/0/**0** (1) | 1/0/**0** (1) | 0/1/**0** (1) |
| HD_VAN_CHUYEN | 20/5/1 | 0.81 [0.75; 0.87] | 0.78 [0.74; 0.82] | 24/2/**0** (26) | 23/3/**0** (26) | 24/2/**0** (26) |

Cột 'đúng mọi trường bắt buộc' ở các bảng trên phụ thuộc mạnh vào số trường văn bản dài bắt buộc của từng loại (chưa phân rã); đọc F1 và cột hạn trước.

## 3. Trường hạn: tự nhận hay từ chối (zero-tuning, quy tắc giai đoạn 2)

| tập | quy tắc | số tự nhận | đúng | **sai** | có hạn thật (n) | tự động hóa (đúng/n) | cận trên 95% (Clopper-Pearson một phía) của tỉ lệ sai |
|---|---|---|---|---|---|---|---|
| DEV | any-model=filename | 21 | 21 | 0 | 45 | 21/45 = 0.47 | 0.13 |
| TEST | any-model=filename | 3 | 3 | 0 | 8 | 3/8 = 0.38 | 0.63 |
| EXCLUDED | any-model=filename | 0 | 0 | 0 | 9 | 0/9 = 0.00 | n/a (không tự nhận) |
| TEST+EXCLUDED | any-model=filename | 3 | 3 | 0 | 17 | 3/17 = 0.18 | 0.63 |
| gộp 84 | any-model=filename | 24 | 24 | 0 | 62 | 24/62 = 0.39 | 0.12 |

Đặt cạnh giai đoạn 2 trên 4 loại cũ (khác loại, khác tên tệp, KHÔNG kiểm định ghép cặp): DEV 37/64 = 58% (0 sai, cận trên 8%), TEST 12/16 = 75% (0 sai, cận trên 22%). Ở loại mới: DEV 21/45, TEST 3/8, EXCLUDED 0/9. Không có lần tự nhận sai nào (gộp 84: 24 tự nhận, 0 sai, cận trên 0.12): quy tắc giữ được **tính an toàn**, nhưng mất phần lớn **tự động hóa**; phần còn lại vào hàng duyệt tay kèm gợi ý (38 trường hạn thật vào hàng duyệt, gợi ý đúng 36/37).

Các quy tắc khác (đủ bảng ở `results3_base.json`): VLM một mình ra 58/62 đúng, 1 sai gộp (thừa khi đáp án không có hạn); `llm=vlm` cũng 1 sai. Ngoài VLM và tên tệp không có nguồn thứ hai độc lập với OCR cho loại mới, mà tên tệp lại không đáng tin cho loại mới (xem trên).

## 4. Phân tích lỗi (chỉ DEV; TEST/EXCLUDED không xem từng đơn vị để giữ phần không chỉnh sạch)

Cấu hình cascade zero-tuning (= LLM), so sánh mềm, trên DEV: 125 lỗi ở các trường không PII. Nguyên nhân gán bằng đặc trưng tự động (`classify_errors.py`: chuỗi đáp án có trong OCR/đoạn đưa LLM không, mực viết, độ trùng từ), không phải đọc từng ca:

| nguyên nhân | bỏ trống | sai giá trị | thừa | tổng |
|---|---|---|---|---|
| LLM 4B bỏ trống hoặc đọc lệch dù chuỗi đáp án CÓ trong văn bản đưa vào | 21 | 21 | 0 | 42 |
| ranh giới trường khác đáp án (kèm/thiếu mã số thuế, địa chỉ, chức danh) | 0 | 21 | 0 | 21 |
| chữ viết tay (OCR hỏng gần hết, LLM bịa hoặc bỏ trống) | 14 | 19 | 0 | 33 |
| OCR không có chuỗi đáp án (đọc nhầm chữ số, mờ, bóng chữ mặt sau) | 6 | 8 | 0 | 14 |
| thừa: đáp án ghi không có; có thể do định nghĩa trường mơ hồ hoặc đáp án thiếu (cần người kiểm) | 0 | 0 | 14 | 14 |
| chuỗi có trong OCR nhưng nằm ngoài đoạn đưa cho LLM | 0 | 1 | 0 | 1 |
| **tổng** | 41 | 70 | 14 | 125 |

15 nhóm lỗi lớn nhất (loại × trường × kết quả):

| # | loại | trường | kết quả | số lỗi (DEV) | nguyên nhân chính | ghi chú |
|---|---|---|---|---|---|---|
| 1 | HD_VAN_CHUYEN | tuyen_van_chuyen | empty | 7 | LLM 4B bỏ trống hoặc đọc lệch dù chuỗi đáp án CÓ trong văn bản đưa vào | trường là đoạn văn dài; mô hình trả null dù đoạn có trong văn bản |
| 2 | HD_VAN_CHUYEN | gia_cuoc | empty | 6 | LLM 4B bỏ trống hoặc đọc lệch dù chuỗi đáp án CÓ trong văn bản đưa vào | như trên; một biểu mẫu hợp đồng (20 đơn vị DEV) nên lỗi lặp lại |
| 3 | HD_MUON_BON | ngay_nhan_bon | spurious | 5 | thừa: đáp án ghi không có; có thể do định nghĩa trường mơ hồ hoặc đáp án thiếu | biên bản nhận bồn có một ngày trong OCR nhưng đáp án ghi không có: cần người kiểm xem đáp án hay LLM đúng |
| 4 | HD_VAN_CHUYEN | ben_chu_hang | wrong | 5 | ranh giới trường khác đáp án | LLM chép tên kèm '(BÊN CHỦ HÀNG)' hoặc cắt mất 'Mã số thuế'; một số có chữ số mã số thuế đọc nhầm |
| 5 | GCN_BAO_HIEM | doi_tuong_bao_hiem | wrong | 5 | chữ viết tay | bản quét chữ viết tay (biển số/đối tượng); OCR chèn dấu chấm giữa ký tự |
| 6 | GCN_BAO_HIEM | phi_bao_hiem | wrong | 5 | chữ viết tay | số tiền viết tay bị OCR đọc sai chữ số (một số tiền khác bậc cỡ) |
| 7 | GCN_BAO_HIEM | hieu_luc_tu | empty | 5 | chữ viết tay | ngày viết tay: OCR không đọc được |
| 8 | HD_NHUONG_QUYEN_DAI_LY | cua_hang | spurious | 4 | thừa: đáp án ghi không có; có thể do định nghĩa trường mơ hồ hoặc đáp án thiếu | LLM điền tên/địa chỉ cửa hàng lấy ở đoạn khác; đáp án ghi không có |
| 9 | GCN_BAO_HIEM | so_tien_bao_hiem | wrong | 4 | chữ viết tay | 3/4 ca là chữ viết tay, 1 ca lệch ranh giới; hiện tượng 'nhiều mức tiền' chưa được kiểm riêng |
| 10 | GCN_BAO_HIEM | ngay_het_han | empty | 4 | chữ viết tay | ngày viết tay: OCR không đọc được; đây là CHÍNH trường hạn |
| 11 | HD_VAN_CHUYEN | tuyen_van_chuyen | wrong | 4 | ranh giới trường khác đáp án | trường là đoạn văn dài; mô hình trả null dù đoạn có trong văn bản |
| 12 | HD_VAN_CHUYEN | ben_van_chuyen | wrong | 3 | ranh giới trường khác đáp án |  |
| 13 | GCN_BAO_HIEM | cong_ty_bao_hiem | wrong | 3 | ranh giới trường khác đáp án |  |
| 14 | GPLX | noi_cap | empty | 3 | LLM 4B bỏ trống hoặc đọc lệch dù chuỗi đáp án CÓ trong văn bản đưa vào |  |
| 15 | GCN_BAO_HIEM | so_gcn_bao_hiem | wrong | 3 | LLM 4B bỏ trống hoặc đọc lệch dù chuỗi đáp án CÓ trong văn bản đưa vào |  |

**Riêng trường hạn (DEV, cascade zero-tuning)**: 12 lỗi hạn — chữ viết tay: 4 (empty), LLM 4B bỏ trống hoặc đọc lệch dù chuỗi đáp án CÓ trong văn bản đưa vào: 2 (empty), OCR không có chuỗi đáp án: 2 (empty), chữ viết tay: 2 (wrong), thừa: đáp án ghi không có; có thể do định nghĩa trường mơ hồ hoặc đáp án thiếu: 2 (spurious). Một nửa (6/12) là chữ viết tay trên giấy chứng nhận bảo hiểm (OCR không đọc được; LLM bỏ trống hoặc đọc sai); còn lại là OCR thiếu chuỗi, LLM bỏ sót, hoặc điền hạn khi giấy không có (2). Với chữ in, hạn đúng gần hết.

Nhận xét theo các hiện tượng brief nêu:

* **Luật thiếu mẫu ngày/nhãn của loại mới**: đúng là lý do duy nhất để luật 0 điểm (không có luật), và sửa được bằng luật nhãn chung (mục 5): luật chung đạt đúng 36/45 hạn DEV (xem mục 5) chỉ nhờ vài nhãn ("có giá trị đến", "hiệu lực từ ngày ký đến", "Đến: giờ, ngày").
* **"Không thời hạn"**: 0/62 đơn vị DEV có cụm "không thời hạn"/"vô thời hạn" trong OCR (GPLX/CCCD trong bộ này đều in ngày hết hạn): hiện tượng này CHƯA được kiểm bằng dữ liệu ở đây. Luật chung có chặn (không nhảy sang ngày cấp khi gặp cụm đó) và có test tổng hợp, nhưng chưa có số đo thật.
* **"Kể từ ngày ký"**: 15 hợp đồng vận chuyển DEV có hạn kiểu "có hiệu lực từ ngày ký đến ngày …" (luật chung đọc đúng); 7 biên bản mượn bồn có "từ ngày ký" nhưng không có ngày kết thúc (đáp án không có hạn): luật không bịa ngày, nhưng LLM điền `ngay_nhan_bon` ở 5 ca (xem bảng).
* **Nhiều mức tiền**: `so_tien_bao_hiem` sai ở 4 ca (3 viết tay, 1 lệch ranh giới) và `phi_bao_hiem` sai ở 5 ca (cả 5 viết tay); lỗi "chọn nhầm giữa nhiều mức tiền" KHÔNG phải nguyên nhân thấy được trong các ca này (chữ viết tay che mất nó).
* **OCR mờ/bóng chữ mặt sau**: chiếm một phần nhỏ (8 sai + 6 bỏ trống trong tổng) và chủ yếu là mã/số (chữ số đọc nhầm, vd. mã số thuế, số giấy); nằm ở `ocr_missing`.
* **Chữ viết tay**: nguyên nhân lớn nhất theo kiểu trường (33 lỗi, gồm 12 ngày, 6 mã, 5 số, 10 văn bản) và tập trung ở một loại (giấy chứng nhận bảo hiểm); đây là chỗ cần VLM hoặc người duyệt.
* **Khác**: LLM 4B bỏ trống ở trường văn bản dài dù chuỗi có trong prompt (nhóm `llm_miss`: 21 bỏ trống + 21 sai); đây là điểm chung với giai đoạn 2 (mô hình nhỏ quá thận trọng khi bị yêu cầu "không chắc thì null").

## 5. Một vòng cải tiến chung (chỉ chỉnh trên DEV)

**Cái đã làm** (`methods/generic_date_rules.py`, bật bằng `RegexRules(generic=True)`; loại có luật riêng không bị đụng): luật ngày chung theo tên trường — hạn (`ngay_het_han`, `hieu_luc_den`, `thoi_han_thue_den`): câu hiệu lực của hợp đồng/giấy ủy quyền ("có hiệu lực [kể] từ ngày ký|<ngày> đến [hết] <ngày>"), "có giá trị đến [Expires] <ngày>", "thời hạn/hết hạn: <ngày>", "Đến: <giờ>, ngày <ngày>" của giấy bảo hiểm; `hieu_luc_tu`/`thoi_han_thue_tu`, `ngay_ky` ("Hôm nay, ngày …", "Ký ngày …"), `ngay_cap` ("<nơi>, ngày … tháng … năm …" ở cuối trang cuối). Từ chối khi giữa nhãn và ngày có "không/vô thời hạn", "ngày cấp", "ngày sinh". Hai lỗi thấy trên DEV được sửa (cụm "Từ ngày … Đến ngày …" của KHÓA HỌC bị nhận là hạn; đã đòi giờ đi kèm cho dạng "Đến:"). Quy tắc tự nhận: chọn trên DEV `regex=llm` (không sai trường nào trên DEV, tự nhận nhiều nhất trong các quy tắc cần ≥ 2 nguồn).

**Phạm vi phủ**: trong 17 trường hạn không chỉnh, 5 trường bị từ chối là toàn bộ của hai loại KHÔNG có đơn vị DEV nào (`GCN_KIEM_DINH_DO_LUONG` 0/4, `HD_THUE_TAI_SAN` 0/1 ở bảng theo loại mục 2): luật chung chỉ bắt được cách ghi hạn đã thấy trên DEV; loại có cách ghi mới thì luật im lặng (an toàn) và LLM/VLM vẫn đọc đúng nhưng không được tự nhận. Ta không xem văn bản của hai loại này để vá (giữ phần không chỉnh sạch): đó là việc của vòng sau.

**Đóng băng**: `dev_selection3.json` (băm của luật chung, bộ bọc, luật cũ, quy tắc hạn, silver v2) ghi TRƯỚC khi sinh dự đoán luật chung cho TEST+EXCLUDED và chấm (`make_results3.py --set improved --final-test`, một lần). LLM, VLM, prompt, ngày trong tên tệp không đổi.

**DEV (đã chỉnh trên chính các đơn vị này nên LẠC QUAN):**

| tập (n đơn vị) | phương pháp | F1 chặt [CI 95%] | F1 mềm [CI] | đúng mọi trường bắt buộc (mềm) | hạn: đúng / bỏ trống / **sai** (n; cận trên 95% của tỉ lệ sai) | hạn: thừa khi giấy không có hạn |
|---|---|---|---|---|---|---|
| DEV (62) | luật chung (mới) | 0.35 [0.30; 0.40] | 0.35 [0.30; 0.40] | 0.06 | 36/9/**0** (n=45; sai ≤ 0.06) | 0/17 |
| DEV (62) | cascade theo kiểu: luật chung → LLM | 0.52 [0.47; 0.57] | 0.74 [0.68; 0.80] | 0.50 | 36/7/**2** (n=45; sai ≤ 0.13) | 2/17 |
| DEV (62) | cascade + tự nhận hạn `regex=llm` | 0.52 [0.47; 0.58] | 0.74 [0.68; 0.80] | 0.50 | 35/10/**0** (n=45; sai ≤ 0.06) | 0/17 |
| DEV (62) | cascade + tự nhận hạn `any-model=filename` (giai đoạn 2) | 0.50 [0.45; 0.55] | 0.72 [0.66; 0.77] | 0.47 | 21/24/**0** (n=45; sai ≤ 0.06) | 0/17 |

**Phần KHÔNG chỉnh (TEST+EXCLUDED, chạy một lần):**

| tập (n đơn vị) | phương pháp | F1 chặt [CI 95%] | F1 mềm [CI] | đúng mọi trường bắt buộc (mềm) | hạn: đúng / bỏ trống / **sai** (n; cận trên 95% của tỉ lệ sai) | hạn: thừa khi giấy không có hạn |
|---|---|---|---|---|---|---|
| TEST (12) | luật chung (mới) | 0.29 [0.17; 0.40] | 0.29 [0.17; 0.40] | 0.00 | 6/2/**0** (n=8; sai ≤ 0.31) | 0/4 |
| TEST (12) | cascade theo kiểu: luật chung → LLM | 0.55 [0.39; 0.67] | 0.71 [0.60; 0.80] | 0.08 | 8/0/**0** (n=8; sai ≤ 0.31) | 0/4 |
| TEST (12) | cascade + tự nhận hạn `regex=llm` | 0.53 [0.37; 0.67] | 0.70 [0.58; 0.79] | 0.08 | 6/2/**0** (n=8; sai ≤ 0.31) | 0/4 |
| TEST (12) | cascade + tự nhận hạn `any-model=filename` (giai đoạn 2) | 0.50 [0.34; 0.64] | 0.67 [0.56; 0.76] | 0.08 | 3/5/**0** (n=8; sai ≤ 0.31) | 0/4 |
| EXCLUDED (10) | luật chung (mới) | 0.28 [0.22; 0.34] | 0.28 [0.22; 0.34] | 0.00 | 6/3/**0** (n=9; sai ≤ 0.28) | 0/1 |
| EXCLUDED (10) | cascade theo kiểu: luật chung → LLM | 0.72 [0.61; 0.79] | 0.80 [0.74; 0.84] | 0.40 | 9/0/**0** (n=9; sai ≤ 0.28) | 0/1 |
| EXCLUDED (10) | cascade + tự nhận hạn `regex=llm` | 0.70 [0.59; 0.76] | 0.78 [0.73; 0.81] | 0.10 | 6/3/**0** (n=9; sai ≤ 0.28) | 0/1 |
| EXCLUDED (10) | cascade + tự nhận hạn `any-model=filename` (giai đoạn 2) | 0.65 [0.53; 0.72] | 0.73 [0.66; 0.78] | 0.10 | 0/9/**0** (n=9; sai ≤ 0.28) | 0/1 |
| TEST+EXCLUDED (22) | luật chung (mới) | 0.29 [0.22; 0.35] | 0.29 [0.22; 0.35] | 0.00 | 12/5/**0** (n=17; sai ≤ 0.16) | 0/5 |
| TEST+EXCLUDED (22) | cascade theo kiểu: luật chung → LLM | 0.64 [0.54; 0.72] | 0.76 [0.70; 0.81] | 0.23 | 17/0/**0** (n=17; sai ≤ 0.16) | 0/5 |
| TEST+EXCLUDED (22) | cascade + tự nhận hạn `regex=llm` | 0.61 [0.52; 0.69] | 0.74 [0.68; 0.79] | 0.09 | 12/5/**0** (n=17; sai ≤ 0.16) | 0/5 |
| TEST+EXCLUDED (22) | cascade + tự nhận hạn `any-model=filename` (giai đoạn 2) | 0.57 [0.47; 0.66] | 0.70 [0.64; 0.76] | 0.09 | 3/14/**0** (n=17; sai ≤ 0.16) | 0/5 |

**Quy tắc tự nhận hạn sau cải tiến (mọi quy tắc đồng thuận, cùng dự đoán):**

| tập | quy tắc | số tự nhận | đúng | **sai** | có hạn thật (n) | tự động hóa (đúng/n) | cận trên 95% (Clopper-Pearson một phía) của tỉ lệ sai |
|---|---|---|---|---|---|---|---|
| DEV | regex=llm | 35 | 35 | 0 | 45 | 35/45 = 0.78 | 0.08 |
| DEV | any-model=filename | 21 | 21 | 0 | 45 | 21/45 = 0.47 | 0.13 |
| DEV | regex | 36 | 36 | 0 | 45 | 36/45 = 0.80 | 0.08 |
| DEV | vlm | 42 | 41 | 1 | 45 | 41/45 = 0.91 | 0.11 |
| DEV | llm=vlm | 34 | 33 | 1 | 45 | 33/45 = 0.73 | 0.13 |
| DEV | regex=vlm | 34 | 34 | 0 | 45 | 34/45 = 0.76 | 0.08 |
| DEV | regex=llm=vlm | 33 | 33 | 0 | 45 | 33/45 = 0.73 | 0.09 |
| TEST | regex=llm | 6 | 6 | 0 | 8 | 6/8 = 0.75 | 0.39 |
| TEST | any-model=filename | 3 | 3 | 0 | 8 | 3/8 = 0.38 | 0.63 |
| TEST | regex | 6 | 6 | 0 | 8 | 6/8 = 0.75 | 0.39 |
| TEST | vlm | 8 | 8 | 0 | 8 | 8/8 = 1.00 | 0.31 |
| TEST | llm=vlm | 8 | 8 | 0 | 8 | 8/8 = 1.00 | 0.31 |
| TEST | regex=vlm | 6 | 6 | 0 | 8 | 6/8 = 0.75 | 0.39 |
| TEST | regex=llm=vlm | 6 | 6 | 0 | 8 | 6/8 = 0.75 | 0.39 |
| EXCLUDED | regex=llm | 6 | 6 | 0 | 9 | 6/9 = 0.67 | 0.39 |
| EXCLUDED | any-model=filename | 0 | 0 | 0 | 9 | 0/9 = 0.00 | n/a (không tự nhận) |
| EXCLUDED | regex | 6 | 6 | 0 | 9 | 6/9 = 0.67 | 0.39 |
| EXCLUDED | vlm | 9 | 9 | 0 | 9 | 9/9 = 1.00 | 0.28 |
| EXCLUDED | llm=vlm | 9 | 9 | 0 | 9 | 9/9 = 1.00 | 0.28 |
| EXCLUDED | regex=vlm | 6 | 6 | 0 | 9 | 6/9 = 0.67 | 0.39 |
| EXCLUDED | regex=llm=vlm | 6 | 6 | 0 | 9 | 6/9 = 0.67 | 0.39 |
| TEST+EXCLUDED | regex=llm | 12 | 12 | 0 | 17 | 12/17 = 0.71 | 0.22 |
| TEST+EXCLUDED | any-model=filename | 3 | 3 | 0 | 17 | 3/17 = 0.18 | 0.63 |
| TEST+EXCLUDED | regex | 12 | 12 | 0 | 17 | 12/17 = 0.71 | 0.22 |
| TEST+EXCLUDED | vlm | 17 | 17 | 0 | 17 | 17/17 = 1.00 | 0.16 |
| TEST+EXCLUDED | llm=vlm | 17 | 17 | 0 | 17 | 17/17 = 1.00 | 0.16 |
| TEST+EXCLUDED | regex=vlm | 12 | 12 | 0 | 17 | 12/17 = 0.71 | 0.22 |
| TEST+EXCLUDED | regex=llm=vlm | 12 | 12 | 0 | 17 | 12/17 = 0.71 | 0.22 |
| gộp 84 | regex=llm | 47 | 47 | 0 | 62 | 47/62 = 0.76 | 0.06 |
| gộp 84 | any-model=filename | 24 | 24 | 0 | 62 | 24/62 = 0.39 | 0.12 |
| gộp 84 | regex | 48 | 48 | 0 | 62 | 48/62 = 0.77 | 0.06 |
| gộp 84 | vlm | 59 | 58 | 1 | 62 | 58/62 = 0.94 | 0.08 |
| gộp 84 | llm=vlm | 51 | 50 | 1 | 62 | 50/62 = 0.81 | 0.09 |
| gộp 84 | regex=vlm | 46 | 46 | 0 | 62 | 46/62 = 0.74 | 0.06 |
| gộp 84 | regex=llm=vlm | 45 | 45 | 0 | 62 | 45/62 = 0.73 | 0.06 |

* **Có đáng giữ không?** Có, với hai lưu ý. Trên phần không chỉnh, tự nhận hạn tăng từ 3/17 (18%) lên 12/17 (71%) mà vẫn 0 sai (cận trên 95% 0.22; chỉ 12 lần tự nhận nên khoảng còn rất rộng). Trên DEV (đã chỉnh): 35/45 (78%), 0 sai. Chênh lệch DEV → không chỉnh (78% → 71%) là cỡ nhiễu của n=17, không tách được.
* **Phương án thay thế**: `llm=vlm` tự nhận 17/17 ngoài mẫu chỉnh (cao hơn `regex=llm`), nhưng sai 1 trên DEV (thừa khi giấy không có hạn) và cần ảnh + ~19 s/đơn vị VLM; `regex=llm` rẻ hơn nhiều (CPU + một lời gọi LLM đã có). Chọn `regex=llm` là theo quy tắc chọn đã ghi trước trên DEV, không phải vì tốt nhất trên phần không chỉnh.
* **Lưu ý 1**: F1 toàn bộ trường KHÔNG đổi so với cascade zero-tuning (cột F1 của 'cascade: luật chung → LLM' bằng cột của 'cascade' ở mục 2 trên cả DEV và TEST+EXCLUDED: LLM đã đọc ngày khá tốt, ngày F1 0.84 trước và sau; hàng 'cascade + tự nhận' thấp hơn vì các hạn bị từ chối bị tính là bỏ trống); lợi ích thật nằm ở **tính độc lập của nguồn thứ hai**: trước đó `regex=llm` rỗng (luật rỗng) và không có nguồn nào ngoài tên tệp/VLM để đối chiếu hạn.
* **Lưu ý 2**: luật chung và LLM cùng đọc một bản OCR, nên chung lỗi khi OCR sai chữ số (bài học giai đoạn 2: hạn sai do '22' thay '12'); `regex=llm` chưa sai trường nào trong 47 lần tự nhận (DEV 35 + ngoài mẫu 12) nhưng 47 mẫu chưa nói được gì về mức 1%.

## 6. Đề xuất đưa vào `src/extraction/` (KHÔNG tự sửa; agent khác đang sửa `field_extractor.py`)

1. `schemas.py`: thêm 17 loại vào `SUPPORTED_TYPES` và sao 17 tệp `teams/team4_extraction/schema/<LOẠI>.json` vào `schema_data/` (test `tests/test_extraction_fields.py` hiện kiểm hai bản giống nhau; cần mở rộng danh sách). Không có bước này thì sản phẩm trả `UnsupportedDocType` cho loại mới.
2. `field_rules.py`: trong `apply_rules`, loại không có luật riêng gọi `generic_rules(tên_trường, Doc(pages))` (chép `methods/generic_date_rules.py`, chỉ phụ thuộc `Doc`, `D_VN`, `D_NUM`, `DATE`, `_clean` của chính tệp đó). Hành vi 4 loại cũ không đổi (đã kiểm: 104 đơn vị v1 cho luật giống hệt cache giai đoạn 2).
3. `field_extractor.py`: đặt quy tắc hạn mặc định `regex=llm` cho loại không có luật riêng khi có luật chung; giữ `any-model=filename` cho 4 loại cũ (đã chứng minh trên đó) hoặc đo lại. Quy tắc `regex=llm` đã có sẵn trong `expiry_rules.EXPIRY_RULES`.
4. Cần thêm test cho mã mới (đã có test ở phía nhóm: `teams/team4_extraction/tests/test_t4_generic_date_rules.py`); khi chuyển vào `src/` thì thêm test tương ứng ở `tests/`.
5. Chưa nên bật tự nhận hạn không có người duyệt cho loại mới: 47 lần tự nhận đúng liên tiếp chỉ chứng minh sai ≤ 6% (một phía 95%).

## 7. Độ trễ và tài nguyên (GPU RTX 3060 dùng chung; số đo KHÔNG sạch)

GPU và Ollama đang được client khác dùng chung (client khác giữ `qwen3.5:4b` với `num_ctx` 32768; gọi với `num_ctx` 6144/12288 làm Ollama nạp lại mô hình: lời gọi đầu tiên mỗi lượt mất vài phút do chờ/nạp lại). Trung vị tính theo `orig_latency_ms` của lời gọi gốc (cache giữ số gốc); cột 'chỉ suy luận' trừ thời gian nạp.

| phương pháp | n | trung vị toàn bộ (ms) | p95 toàn bộ (ms) | trung vị chỉ suy luận (ms) | VRAM Ollama |
|---|---|---|---|---|---|
| regex | 84 | 0.02 | 0 | n/a | 0 (CPU) |
| llm | 84 | 4246 | 10074 | 4222 | ~3,1 GB (ctx 6144) |
| vlm | 84 | 19075 | 21958 | 18843 | ~3,3 GB (ctx 12288) |

Luật + LLM ≈ 4–10 giây/đơn vị khi mô hình đã nạp; thêm VLM ≈ 19 giây/đơn vị (4 ảnh). Cải tiến ở mục 5 chỉ thêm vài mili giây (luật) và cho phép bỏ VLM khỏi tự nhận hạn (`regex=llm` không cần ảnh). Đuôi p95 lớn ở tập EXCLUDED (hàng trăm giây) là lúc Ollama nạp lại mô hình do client khác, không phải độ trễ suy luận. Chạy tuần tự, toàn bộ 84 đơn vị: LLM ~640 s, VLM ~1735 s (đồng hồ treo tường, GPU dùng chung).

## 8. Hạn chế và việc còn lại

* **Đáp án máy, chưa có người kiểm** (silver v2: Haiku/Sonnet cùng họ có thể cùng sai; Opus phân xử 135 mục mà vẫn là mô hình). Ví dụ `ngay_nhan_bon` và `cua_hang` ở bảng lỗi: cần người xem đáp án hay LLM đúng.
* **Cỡ mẫu nhỏ**: 62 trường hạn có đáp án (DEV 45, TEST 8, EXCLUDED 9), nhiều loại chỉ 1–3 đơn vị; CI rộng; chênh lệch giữa tập DEV/TEST/EXCLUDED phần lớn là nhiễu. 10 đơn vị EXCLUDED là tệp ghép không đại diện.
* Phần "không chỉnh" chỉ có 17 trường hạn có đáp án (TEST 8 + EXCLUDED 9): đủ để thấy luật chung không vỡ ngay, chưa đủ để nói về mức sai thấp.
* **Một biểu mẫu thống trị** (`HD_VAN_CHUYEN`: 26 đơn vị cả ba tập) nên luật chung phần lớn được kiểm trên một mẫu hợp đồng; các loại khác 1–7 đơn vị.
* Chưa đo: hiện tượng "không thời hạn"; thẻ nhiều mặt có ảnh nửa trắng; VLM với > 4 ảnh (hợp đồng dài chỉ thấy trang đầu); trường `ho_ten` có chấm nhưng là dữ liệu cá nhân (không in giá trị).
* Không thử cải tiến phía LLM (prompt theo loại, gợi ý trường dài): chỉ một vòng chung theo đề bài; đây là hướng tiếp theo cho nhóm `llm_miss` (42 lỗi DEV).

## 9. Chạy lại

```powershell
# từ gốc repo; Ollama ở 127.0.0.1:11434 (không pull/xóa/khởi động lại mô hình)
.venv\Scripts\python.exe -X utf8 teams\team4_extraction\experiments\03_unseen_types\run_zero_tuning.py --configs regex@ocr_v2,filename,llm@ocr_v2,vlm
.venv\Scripts\python.exe -X utf8 teams\team4_extraction\experiments\03_unseen_types\make_results3.py --set base
.venv\Scripts\python.exe -X utf8 teams\team4_extraction\experiments\03_unseen_types\classify_errors.py       # DEV, nguyên nhân lỗi
.venv\Scripts\python.exe -X utf8 teams\team4_extraction\experiments\03_unseen_types\dev_iterate.py --errors   # vòng cải tiến, CHỈ DEV
.venv\Scripts\python.exe -X utf8 teams\team4_extraction\experiments\03_unseen_types\freeze3.py               # ghi dev_selection3.json, một lần
# dự đoán luật chung cho mọi đơn vị (CPU): lib.run_config('regex','ocr_v2',units_v2(),tag='v2',force=True,generic=True) (xem common3.py)
.venv\Scripts\python.exe -X utf8 teams\team4_extraction\experiments\03_unseen_types\make_results3.py --set improved --final-test
.venv\Scripts\python.exe -X utf8 teams\team4_extraction\experiments\03_unseen_types\build_results3_md.py
```

Test: `.venv\Scripts\python.exe -X utf8 -m pytest teams\team4_extraction\tests -q` (có `test_t4_generic_date_rules.py`).

