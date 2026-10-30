# 03 - Toàn trình v2: quy tắc "bản khác" (id) và gỡ mơ hồ theo tiêu đề (tiebreak) đặt cạnh S10, kèm chi phí có OCR thật

> `labels_v2.csv` sha1[:10] = `eb3348713a` | ngày 2026-10-16 | tái lập: `.venv\Scripts\python.exe -X utf8 teams/00_data_and_eval/experiments/03_end_to_end_v2/run_v2.py --stage dev --call-llm` (rồi `--stage test --final-test`, `--stage assemble`; chi phí: `cost_sample_v2.py`, `bench_render.py`) | văn bản: `data/ocr_v2.jsonl` (không OCR lại cho phần chấm), PDF trong `docs/_chot_samples_phanloaitailieu/` (chỉ đọc, dùng cho phần chi phí).
> Viết cho sinh viên năm cuối ngành AI. **Đáp án ranh giới và loại là đáp án máy** (`boundary_gold_v0.csv`, `labels_v2.csv`), chưa người của công ty kiểm: mọi "đúng" là "đúng so với đáp án máy". Không có định danh cá nhân trong tệp này; tài liệu được nhắc bằng nhóm, không bằng tên.

## Tóm tắt (đọc mục này trước)

* **Câu hỏi.** Giai đoạn 3 thêm hai tùy chọn, đều tắt: `id` (quy tắc "bản khác": bắt nhiều bản cùng loại trong một tệp) và `tb` (`rule_title_tiebreak`: cổng luật gỡ mơ hồ theo vị trí tiêu đề). Đặt cạnh S10 (cấu hình mặc định của thí nghiệm 01) trên cùng 245 tệp dev, cùng thước đo, chúng có làm tăng tệp đúng hoàn toàn mà không tăng lỗi âm thầm không?
* **Dev (n = 245 tệp).** S10: 223/245 tệp đúng hoàn toàn, 14 sai lặng lẽ, 279/318 tài liệu giao đúng và tự động. S10+id+tb: **232/245**, **5** sai lặng lẽ, **293/318**. Mọi thay đổi đều ở tệp composite: id sửa 3 tệp composite cùng loại (0/6 -> 3/6), tb sửa 6 tệp composite khác loại (2/8 -> 8/8); **0 tệp bị làm hỏng** ở 155 tệp nhiều trang thường, 71 tệp một trang và 5 tệp `BB_LAY_MAU`. Hiệu (c) có trọng số theo cơ cấu tệp thật so với S10: **+3,0 điểm, CI ghép cặp [+2,0; +3,9]**; hiệu cấp tài liệu +4,4 điểm [+1,7; +7,8]. Lưu ý lớn: cả hai tùy chọn được thiết kế sau khi nhìn chính các tệp composite này, nên con số dev là "sửa đúng thứ đã thấy", không phải ước lượng giữ ngoài.
* **Chọn theo quy tắc ghi trước** (`dev_selection_v2.json`, ghi trước khi chạy dev): **S10+id+tb** (cả bốn biến thể đều hợp lệ; S10+id+tb có nhiều tài liệu giao đúng nhất). Triage S9 chỉ để đối chiếu: sai lặng lẽ 4/189 tự xử lý nhưng chỉ 77,9% tệp tự xử lý và giao đúng 185/318 tài liệu.
* **TEST (lần thứ hai của thí nghiệm toàn trình, 59 tệp, chấm MỘT lần): giống hệt S10**: 56/59 tệp đúng hoàn toàn cả hai (94,9%), 2 sai lặng lẽ cả hai, 65/68 tài liệu cả hai, 0 tệp đổi kết quả. TEST không có composite khác loại hay cùng loại ngoài `BB_LAY_MAU` (chỉ 2 tệp `BB_LAY_MAU`), nên TEST chỉ kiểm được "không hại tệp thường": đạt. Nó **không** xác nhận lợi ích.
* **Đổi mặc định: có** (quy tắc ghi trước cho phép: dev chọn khác S10 và TEST không hại): pipeline mặc định là `model+merge+id` với `title_tiebreak` bật (`--splitter model+merge`, `--no-title-tiebreak` trả về hành vi cũ). Rủi ro cần chủ phiên biết ở mục "Mặc định mới và rủi ro".
* **Chi phí (30 tệp dev, 90 trang, OCR thật, trích xuất và VLM bật, GPU dùng chung):** OCR chiếm 45% thời gian, trích xuất (LLM + VLM) 52%; tách, phân loại, dựng ảnh cộng lại dưới 3%. Trung vị 32,6 s/tệp, p95 49,3 s; ước lượng **~500 trang/giờ** cho một máy RTX 3060 với cơ cấu tệp thật (khoảng 250 đến 860 tùy tỉ lệ tệp có trường hạn). VRAM đỉnh 6,6 GiB tổng (cả GPU, gồm Ollama), tăng 1,6 GiB so với mức nền.
* **Dựng ảnh nhanh hơn 4 lần, cùng điểm ảnh:** PNG `optimize=True` -> `compress_level=1`: trung vị 3,62 s -> 0,89 s mỗi lát cắt (40 lát, 154 ảnh, 154/154 giống hệt điểm ảnh). Khóa cache VLM trước đây băm **byte tệp PNG** nên đổi nén sẽ làm lỡ cache; đã đổi sang băm **điểm ảnh** (mục "Dựng ảnh").


## Kết quả trên phạm vi dev (n = 245 tệp: tệp 1 trang 71, nhiều trang, không ghép 155, composite khác loại 8, composite cùng loại (ngoài BB_LAY_MAU) 6, BB_LAY_MAU 5)

Kiểm tái lập: S10 ở đây trùng thí nghiệm 01 (pred_segs) ở 245/245 tệp.

**(c) Tệp đúng hoàn toàn = (a) tách đúng ∧ (b) mọi tài liệu đáp án có đúng loại**

| biến thể | tệp 1 trang (n=71) | nhiều trang, không ghép (n=155) | composite khác loại (n=8) | composite cùng loại (ngoài BB_LAY_MAU) (n=6) | BB_LAY_MAU (n=5) | **toàn bộ, theo cơ cấu tệp thật** |
|---|---|---|---|---|---|---|
| S10 (mô hình tau=0,7 + gộp cùng loại trừ điểm >= 0,99 (mặc định hiện tại)) | 70/71 = 99% [92%; 100%] | 148/155 = 95% [91%; 98%] | 2/8 = 25% [3%; 65%] | 0/6 = 0% [0%; 46%] | 3/5 = 60% [15%; 95%] | **91,9% [89,2%; 94,4%]** |
| S10+id (S10 + quy tắc 'bản khác' (model+merge+id)) | 70/71 = 99% [92%; 100%] | 148/155 = 95% [91%; 98%] | 2/8 = 25% [3%; 65%] | 3/6 = 50% [12%; 88%] | 3/5 = 60% [15%; 95%] | **92,9% [90,0%; 95,4%]** |
| S10+tb (S10 + gỡ mơ hồ theo tiêu đề (rule_title_tiebreak)) | 70/71 = 99% [92%; 100%] | 148/155 = 95% [91%; 98%] | 8/8 = 100% [63%; 100%] | 0/6 = 0% [0%; 46%] | 3/5 = 60% [15%; 95%] | **93,8% [91,3%; 96,2%]** |
| S10+id+tb (S10 + id + tiebreak) | 70/71 = 99% [92%; 100%] | 148/155 = 95% [91%; 98%] | 8/8 = 100% [63%; 100%] | 3/6 = 50% [12%; 88%] | 3/5 = 60% [15%; 95%] | **94,8% [92,1%; 97,3%]** |
| S9 (không tách; điểm cặp trang >= 0,3 -> người (triage, đối chiếu)) | 70/71 = 99% [92%; 100%] | 154/155 = 99% [96%; 100%] | 0/8 = 0% [0%; 37%] | 0/6 = 0% [0%; 46%] | 0/5 = 0% [0%; 52%] | **92,3% [91,0%; 93,1%]** |
| S0 (không tách (đối chiếu)) | 70/71 = 99% [92%; 100%] | 154/155 = 99% [96%; 100%] | 0/8 = 0% [0%; 37%] | 0/6 = 0% [0%; 46%] | 0/5 = 0% [0%; 52%] | **92,3% [91,0%; 93,1%]** |

**(a) Tách đúng hoàn toàn**

| biến thể | tệp 1 trang (n=71) | nhiều trang, không ghép (n=155) | composite khác loại (n=8) | composite cùng loại (ngoài BB_LAY_MAU) (n=6) | BB_LAY_MAU (n=5) | **toàn bộ, theo cơ cấu tệp thật** |
|---|---|---|---|---|---|---|
| S10 (mô hình tau=0,7 + gộp cùng loại trừ điểm >= 0,99 (mặc định hiện tại)) | 71/71 = 100% [95%; 100%] | 149/155 = 96% [92%; 99%] | 7/8 = 88% [47%; 100%] | 0/6 = 0% [0%; 46%] | 3/5 = 60% [15%; 95%] | **94,3% [91,9%; 96,4%]** |
| S10+id (S10 + quy tắc 'bản khác' (model+merge+id)) | 71/71 = 100% [95%; 100%] | 149/155 = 96% [92%; 99%] | 7/8 = 88% [47%; 100%] | 3/6 = 50% [12%; 88%] | 3/5 = 60% [15%; 95%] | **95,3% [92,7%; 97,6%]** |
| S10+tb (S10 + gỡ mơ hồ theo tiêu đề (rule_title_tiebreak)) | 71/71 = 100% [95%; 100%] | 149/155 = 96% [92%; 99%] | 8/8 = 100% [63%; 100%] | 0/6 = 0% [0%; 46%] | 3/5 = 60% [15%; 95%] | **94,7% [92,2%; 96,8%]** |
| S10+id+tb (S10 + id + tiebreak) | 71/71 = 100% [95%; 100%] | 149/155 = 96% [92%; 99%] | 8/8 = 100% [63%; 100%] | 3/6 = 50% [12%; 88%] | 3/5 = 60% [15%; 95%] | **95,7% [93,2%; 97,9%]** |
| S9 (không tách; điểm cặp trang >= 0,3 -> người (triage, đối chiếu)) | 71/71 = 100% [95%; 100%] | 155/155 = 100% [98%; 100%] | 0/8 = 0% [0%; 37%] | 0/6 = 0% [0%; 46%] | 0/5 = 0% [0%; 52%] | **93,1% [93,1%; 93,1%]** |
| S0 (không tách (đối chiếu)) | 71/71 = 100% [95%; 100%] | 155/155 = 100% [98%; 100%] | 0/8 = 0% [0%; 37%] | 0/6 = 0% [0%; 46%] | 0/5 = 0% [0%; 52%] | **93,1% [93,1%; 93,1%]** |

**(b) Mọi segment đáp án được TỰ NHẬN đúng loại**

| biến thể | tệp 1 trang (n=71) | nhiều trang, không ghép (n=155) | composite khác loại (n=8) | composite cùng loại (ngoài BB_LAY_MAU) (n=6) | BB_LAY_MAU (n=5) | **toàn bộ, theo cơ cấu tệp thật** |
|---|---|---|---|---|---|---|
| S10 (mô hình tau=0,7 + gộp cùng loại trừ điểm >= 0,99 (mặc định hiện tại)) | 70/71 = 99% [92%; 100%] | 153/155 = 99% [95%; 100%] | 2/8 = 25% [3%; 65%] | 6/6 = 100% [54%; 100%] | 5/5 = 100% [48%; 100%] | **96,8% [95,2%; 98,4%]** |
| S10+id (S10 + quy tắc 'bản khác' (model+merge+id)) | 70/71 = 99% [92%; 100%] | 153/155 = 99% [95%; 100%] | 2/8 = 25% [3%; 65%] | 6/6 = 100% [54%; 100%] | 5/5 = 100% [48%; 100%] | **96,8% [95,2%; 98,4%]** |
| S10+tb (S10 + gỡ mơ hồ theo tiêu đề (rule_title_tiebreak)) | 70/71 = 99% [92%; 100%] | 153/155 = 99% [95%; 100%] | 8/8 = 100% [63%; 100%] | 6/6 = 100% [54%; 100%] | 5/5 = 100% [48%; 100%] | **98,8% [97,1%; 100,0%]** |
| S10+id+tb (S10 + id + tiebreak) | 70/71 = 99% [92%; 100%] | 153/155 = 99% [95%; 100%] | 8/8 = 100% [63%; 100%] | 6/6 = 100% [54%; 100%] | 5/5 = 100% [48%; 100%] | **98,8% [97,1%; 100,0%]** |
| S9 (không tách; điểm cặp trang >= 0,3 -> người (triage, đối chiếu)) | 70/71 = 99% [92%; 100%] | 154/155 = 99% [96%; 100%] | 0/8 = 0% [0%; 37%] | 6/6 = 100% [54%; 100%] | 5/5 = 100% [48%; 100%] | **96,5% [95,3%; 97,4%]** |
| S0 (không tách (đối chiếu)) | 70/71 = 99% [92%; 100%] | 154/155 = 99% [96%; 100%] | 0/8 = 0% [0%; 37%] | 6/6 = 100% [54%; 100%] | 5/5 = 100% [48%; 100%] | **96,5% [95,3%; 97,4%]** |

### (d) Định tuyến: tự xử lý hoàn toàn và sai lặng lẽ

| biến thể | tự xử lý hoàn toàn | tự xử lý VÀ đúng | sai lặng lẽ (tự xử lý mà sai) | sai lặng lẽ / tự xử lý | thô: tự xử lý / tệp | thô: sai / tự xử lý (Clopper-Pearson 95%) |
|---|---|---|---|---|---|---|
| S10 (mô hình tau=0,7 + gộp cùng loại trừ điểm >= 0,99 (mặc định hiện tại)) | 96,8% [94,4%; 98,8%] | 91,9% [89,2%; 94,4%] | 4,94% [3,37%; 6,49%] | 5,11% [3,48%; 6,69%] | 237/245 | 14/237 = 5,91% [3,27%; 9,71%] |
| S10+id (S10 + quy tắc 'bản khác' (model+merge+id)) | 96,8% [94,4%; 98,8%] | 92,9% [90,0%; 95,4%] | 3,96% [2,38%; 5,60%] | 4,09% [2,46%; 5,78%] | 237/245 | 11/237 = 4,64% [2,34%; 8,15%] |
| S10+tb (S10 + gỡ mơ hồ theo tiêu đề (rule_title_tiebreak)) | 96,8% [94,4%; 98,8%] | 93,8% [91,3%; 96,2%] | 2,97% [1,64%; 4,35%] | 3,07% [1,69%; 4,54%] | 237/245 | 8/237 = 3,38% [1,47%; 6,54%] |
| S10+id+tb (S10 + id + tiebreak) | 96,8% [94,4%; 98,8%] | 94,8% [92,1%; 97,3%] | 1,98% [0,66%; 3,58%] | 2,05% [0,67%; 3,67%] | 237/245 | 5/237 = 2,11% [0,69%; 4,85%] |
| S9 (không tách; điểm cặp trang >= 0,3 -> người (triage, đối chiếu)) | 77,9% [73,1%; 82,3%] | 76,5% [72,0%; 80,9%] | 1,45% [0,33%; 2,57%] | 1,86% [0,43%; 3,30%] | 189/245 | 4/189 = 2,12% [0,58%; 5,33%] |
| S0 (không tách (đối chiếu)) | 99,6% [98,7%; 100,0%] | 92,3% [91,0%; 93,1%] | 7,31% [6,91%; 8,12%] | 7,34% [6,91%; 8,19%] | 244/245 | 20/244 = 8,20% [5,08%; 12,38%] |

### Cấp tài liệu

| biến thể | tài liệu đáp án giao ĐÚNG và tự động | tài liệu đáp án (tổng) | trong đó của các nhóm composite (n tài liệu) |
|---|---|---|---|
| S10 (mô hình tau=0,7 + gộp cùng loại trừ điểm >= 0,99 (mặc định hiện tại)) | 279/318 = 87,7% [83,2%; 92,6%] | 318 | 61/92 |
| S10+id (S10 + quy tắc 'bản khác' (model+merge+id)) | 286/318 = 89,9% [85,8%; 94,5%] | 318 | 68/92 |
| S10+tb (S10 + gỡ mơ hồ theo tiêu đề (rule_title_tiebreak)) | 286/318 = 89,9% [85,2%; 94,9%] | 318 | 68/92 |
| S10+id+tb (S10 + id + tiebreak) | 293/318 = 92,1% [87,7%; 96,6%] | 318 | 75/92 |
| S9 (không tách; điểm cặp trang >= 0,3 -> người (triage, đối chiếu)) | 185/318 = 58,2% [46,2%; 70,8%] | 318 | 0/92 |
| S0 (không tách (đối chiếu)) | 224/318 = 70,4% [56,3%; 84,7%] | 318 | 0/92 |

### (e) Hại / sửa so với S10 (mỗi ô: tệp S10 đúng mà biến thể làm hỏng / tệp S10 sai mà biến thể sửa)

Mỗi ô: (tệp S10 đúng hoàn toàn mà biến thể làm hỏng) hỏng / (tệp S10 sai mà biến thể sửa được) sửa.

| biến thể | tệp 1 trang | nhiều trang, không ghép | composite khác loại | composite cùng loại (ngoài BB_LAY_MAU) | BB_LAY_MAU | hiệu có trọng số (biến thể - S10) của (c), CI ghép cặp | kết luận |
|---|---|---|---|---|---|---|---|
| S10+id (S10 + quy tắc 'bản khác' (model+merge+id)) | 0 hỏng / 0 sửa | 0 hỏng / 0 sửa | 0 hỏng / 0 sửa | 0 hỏng / 3 sửa | 0 hỏng / 0 sửa | +1.0 điểm [+0.3; +1.6] | tách được: tốt hơn |
| S10+tb (S10 + gỡ mơ hồ theo tiêu đề (rule_title_tiebreak)) | 0 hỏng / 0 sửa | 0 hỏng / 0 sửa | 0 hỏng / 6 sửa | 0 hỏng / 0 sửa | 0 hỏng / 0 sửa | +2.0 điểm [+1.0; +2.6] | tách được: tốt hơn |
| S10+id+tb (S10 + id + tiebreak) | 0 hỏng / 0 sửa | 0 hỏng / 0 sửa | 0 hỏng / 6 sửa | 0 hỏng / 3 sửa | 0 hỏng / 0 sửa | +3.0 điểm [+2.0; +3.9] | tách được: tốt hơn |
| S9 (không tách; điểm cặp trang >= 0,3 -> người (triage, đối chiếu)) | 0 hỏng / 0 sửa | 0 hỏng / 6 sửa | 2 hỏng / 0 sửa | 0 hỏng / 0 sửa | 3 hỏng / 0 sửa | +0.4 điểm [-1.9; +2.9] | không tách được |
| S0 (không tách (đối chiếu)) | 0 hỏng / 0 sửa | 0 hỏng / 6 sửa | 2 hỏng / 0 sửa | 0 hỏng / 0 sửa | 3 hỏng / 0 sửa | +0.4 điểm [-1.9; +2.9] | không tách được |

### Số lời gọi LLM và số lát cắt mỗi tệp

| biến thể | tệp 1 trang | nhiều trang, không ghép | composite khác loại | composite cùng loại (ngoài BB_LAY_MAU) | BB_LAY_MAU | tổng lời gọi LLM / tổng lát cắt |
|---|---|---|---|---|---|---|
| S10 (mô hình tau=0,7 + gộp cùng loại trừ điểm >= 0,99 (mặc định hiện tại)) | 0.06 LLM, 1.00 lát | 0.15 LLM, 1.06 lát | 0.25 LLM, 3.38 lát | 0.83 LLM, 1.17 lát | 0.00 LLM, 9.00 lát | 35 / 314 |
| S10+id (S10 + quy tắc 'bản khác' (model+merge+id)) | 0.06 LLM, 1.00 lát | 0.15 LLM, 1.06 lát | 0.25 LLM, 3.38 lát | 1.17 LLM, 1.83 lát | 0.00 LLM, 9.00 lát | 37 / 318 |
| S10+tb (S10 + gỡ mơ hồ theo tiêu đề (rule_title_tiebreak)) | 0.06 LLM, 1.00 lát | 0.11 LLM, 1.06 lát | 0.25 LLM, 3.50 lát | 0.50 LLM, 1.17 lát | 0.00 LLM, 9.00 lát | 26 / 315 |
| S10+id+tb (S10 + id + tiebreak) | 0.06 LLM, 1.00 lát | 0.11 LLM, 1.06 lát | 0.25 LLM, 3.50 lát | 0.50 LLM, 1.83 lát | 0.00 LLM, 9.00 lát | 26 / 319 |
| S9 (không tách; điểm cặp trang >= 0,3 -> người (triage, đối chiếu)) | 0.06 LLM, 1.00 lát | 0.04 LLM, 1.00 lát | 0.12 LLM, 1.00 lát | 0.50 LLM, 1.00 lát | 0.00 LLM, 1.00 lát | 14 / 245 |
| S0 (không tách (đối chiếu)) | 0.06 LLM, 1.00 lát | 0.04 LLM, 1.00 lát | 0.12 LLM, 1.00 lát | 0.50 LLM, 1.00 lát | 0.00 LLM, 1.00 lát | 14 / 245 |

### So sánh ghép cặp với S10 (hiệu của (c) có trọng số, CI 95% bootstrap ghép cặp theo tệp) và hiệu cấp tài liệu

| cặp | hiệu (c) | CI | kết luận | hiệu tài liệu giao đúng và tự động | CI |
|---|---|---|---|---|---|
| S10+id - S10 | +1.0 điểm | [+0.3; +1.6] | tách được | +2.2 điểm | [+0.0; +5.1] |
| S10+tb - S10 | +2.0 điểm | [+1.0; +2.6] | tách được | +2.2 điểm | [+0.7; +4.1] |
| S10+id+tb - S10 | +3.0 điểm | [+2.0; +3.9] | tách được | +4.4 điểm | [+1.7; +7.8] |
| S9 - S10 | +0.4 điểm | [-1.9; +2.9] | không tách được | -29.6 điểm | [-39.8; -19.1] |
| S0 - S10 | +0.4 điểm | [-1.9; +2.9] | không tách được | -17.3 điểm | [-29.4; -5.0] |

### Tệp đổi kết quả (c) so với S10, theo nhóm: (S10 đúng -> X sai) / (S10 sai -> X đúng)

| biến thể | tệp 1 trang | nhiều trang, không ghép | composite khác loại | composite cùng loại (ngoài BB_LAY_MAU) | BB_LAY_MAU |
|---|---|---|---|---|---|
| S10+id | 0 hỏng / 0 sửa | 0 hỏng / 0 sửa | 0 hỏng / 0 sửa | 0 hỏng / 3 sửa | 0 hỏng / 0 sửa |
| S10+tb | 0 hỏng / 0 sửa | 0 hỏng / 0 sửa | 0 hỏng / 6 sửa | 0 hỏng / 0 sửa | 0 hỏng / 0 sửa |
| S10+id+tb | 0 hỏng / 0 sửa | 0 hỏng / 0 sửa | 0 hỏng / 6 sửa | 0 hỏng / 3 sửa | 0 hỏng / 0 sửa |

### Đếm thô và áp quy tắc chọn trên dev

Quy tắc (nguyên văn từ `dev_selection_v2.json`): Một biến thể X khác S10 là HỢP LỆ khi, so với S10 trên 245 tệp dev: (a) số tệp đúng hoàn toàn (c) của X >= của S10; (b) số tệp sai lặng lẽ (tự xử lý mà sai) của X <= của S10; (c) số tài liệu đáp án giao đúng và tự động của X >= của S10. Trong các biến thể hợp lệ chọn biến thể có nhiều tài liệu giao đúng và tự động nhất; hòa thì nhiều tệp đúng hoàn toàn hơn; hòa nữa thì ÍT tùy chọn bật hơn (S10 thắng mọi hòa). Không biến thể nào hợp lệ hơn S10 thì giữ S10. S9 (triage) và S0 chỉ để đối chiếu, không ứng viên mặc định.

| biến thể | hợp lệ | tệp đúng hoàn toàn | tự xử lý | sai lặng lẽ | tài liệu giao đúng và tự động | tài liệu đáp án | lời gọi LLM | lát cắt |
|---|---|---|---|---|---|---|---|---|
| S10 | có | 223/245 | 237/245 | 14 | 279/318 | 318 | 35 | 314 |
| S10+id | có | 226/245 | 237/245 | 11 | 286/318 | 318 | 37 | 318 |
| S10+tb | có | 229/245 | 237/245 | 8 | 286/318 | 318 | 26 | 315 |
| S10+id+tb | có | 232/245 | 237/245 | 5 | 293/318 | 318 | 26 | 319 |

**Chọn trên dev: S10+id+tb.**


## Kết quả TEST (lần thứ HAI của thí nghiệm toàn trình; MỘT lần cho cấu hình mới; cấu hình đóng băng = **S10+id+tb**)

Lý do chạy lần hai: cấu hình mới (model+merge+id và/hoặc rule_title_tiebreak), khác cấu hình đã chấm ở lần TEST thứ nhất của thí nghiệm toàn trình (S10). n = 59 tệp TEST: tệp 1 trang 21, nhiều trang, không ghép 36, BB_LAY_MAU 2.

| biến thể | tệp đúng hoàn toàn (c) | Clopper-Pearson 95% | tự xử lý | sai lặng lẽ / tự xử lý (CP 95%) | tài liệu giao đúng và tự động | lời gọi LLM | lát cắt |
|---|---|---|---|---|---|---|---|
| S10 | 56/59 = 94,9% | [85,9%; 98,9%] | 58/59 | 2/58 [0,4%; 11,9%] | 65/68 | 5 | 70 |
| S10+id+tb | 56/59 = 94,9% | [85,9%; 98,9%] | 58/59 | 2/58 [0,4%; 11,9%] | 65/68 | 5 | 70 |

**(c) theo nhóm**

| biến thể | tệp 1 trang (n=21) | nhiều trang, không ghép (n=36) | BB_LAY_MAU (n=2) | **toàn bộ, theo cơ cấu tệp thật** |
|---|---|---|---|---|
| S10 | 20/21 = 95% [76%; 100%] | 34/36 = 94% [81%; 99%] | 2/2 = 100% [16%; 100%] | **94,8% [88,1%; 100,0%]** |
| S10+id+tb | 20/21 = 95% [76%; 100%] | 34/36 = 94% [81%; 99%] | 2/2 = 100% [16%; 100%] | **94,8% [88,1%; 100,0%]** |

| biến thể | tự xử lý hoàn toàn | tự xử lý VÀ đúng | sai lặng lẽ (tự xử lý mà sai) | sai lặng lẽ / tự xử lý | thô: tự xử lý / tệp | thô: sai / tự xử lý (Clopper-Pearson 95%) |
|---|---|---|---|---|---|---|
| S10 | 98,2% [94,5%; 100,0%] | 94,8% [88,1%; 100,0%] | 3,34% [0,00%; 8,83%] | 3,40% [0,00%; 8,83%] | 58/59 | 2/58 = 3,45% [0,42%; 11,91%] |
| S10+id+tb | 98,2% [94,5%; 100,0%] | 94,8% [88,1%; 100,0%] | 3,34% [0,00%; 8,83%] | 3,40% [0,00%; 8,83%] | 58/59 | 2/58 = 3,45% [0,42%; 11,91%] |

| biến thể | tài liệu đáp án giao ĐÚNG và tự động | tài liệu đáp án (tổng) | trong đó của các nhóm composite (n tài liệu) |
|---|---|---|---|
| S10 | 65/68 = 95,6% [89,8%; 100,0%] | 68 | 11/11 |
| S10+id+tb | 65/68 = 95,6% [89,8%; 100,0%] | 68 | 11/11 |

Mỗi ô: (tệp S10 đúng hoàn toàn mà biến thể làm hỏng) hỏng / (tệp S10 sai mà biến thể sửa được) sửa.

| biến thể | tệp 1 trang | nhiều trang, không ghép | BB_LAY_MAU | hiệu có trọng số (biến thể - S10) của (c), CI ghép cặp | kết luận |
|---|---|---|---|---|---|
| S10+id+tb | 0 hỏng / 0 sửa | 0 hỏng / 0 sửa | 0 hỏng / 0 sửa | +0.0 điểm [+0.0; +0.0] | không tách được |

Hiệu (c) S10+id+tb - S10 trên TEST: +0.0 điểm, CI ghép cặp [+0.0; +0.0] (không tách được).

Kiểm quy tắc đổi mặc định (ii): tệp đúng 56 so với 56 (>=), sai lặng lẽ 2 so với 2 (<=) -> **đạt**.


## Thiết lập và quy tắc chọn (ghi trước khi chạy dev)

* **Đơn vị, dữ liệu, thước đo, bootstrap, điểm cặp trang cross-fit, TF-IDF cross-fit**: đúng như thí nghiệm 01 (dùng lại `e2e_lib.py` và `Summary` của 01; điểm cặp trang đọc từ `01_end_to_end/results/pair_scores_dev.json`). Kiểm tái lập: biến thể S10 ở đây trùng thí nghiệm 01 (chuỗi lát cắt và nhãn) ở **245/245 tệp**.
* **Biến thể.** S10 = `model` ngưỡng 0,7 + gộp cùng loại trừ ranh giới điểm >= 0,99. `+id`: trước khi tách, các trang được quy tắc "bản khác" (đầu trang giống nhau jaccard >= 0,7 và số hiệu "Số ..." ở đầu hai trang khác nhau) nhận điểm 1,0 (đúng như `split_with_policy`); điểm 1,0 >= 0,99 nên không bị gộp lại. `+tb`: `DocumentClassifier.rule_title_tiebreak = True`. S9 (triage, cờ 0,3) và S0 (không tách) chỉ để đối chiếu.
* **Quy tắc ghi trong `dev_selection_v2.json` TRƯỚC khi chạy dev** (trạng thái `rule_frozen_before_dev_run`, sau đó script ghi kết quả vào cùng tệp và đổi trạng thái thành `dev_done`): biến thể X khác S10 hợp lệ khi, trên 245 tệp dev, (a) số tệp đúng hoàn toàn >= S10, (b) số tệp sai lặng lẽ <= S10, (c) số tài liệu giao đúng và tự động >= S10; trong các biến thể hợp lệ lấy cái giao đúng nhiều tài liệu nhất, hòa thì nhiều tệp đúng hơn, hòa nữa thì ít tùy chọn hơn. Quy tắc đổi mặc định: dev chọn khác S10 **và** trên TEST số tệp đúng >= S10 cũ, số sai lặng lẽ <= S10 cũ. Quy tắc này đơn giản hơn quy tắc của thí nghiệm 01 (không dùng CI) vì ở đây mọi biến thể chỉ khác S10 ở vài tệp composite.
* **Lời gọi LLM phân loại**: cache có sẵn của 01/02 (chỉ đọc); lời gọi mới (4 văn bản ở dev, 0 ở TEST) ghi cache đĩa riêng `_cache/ollama` (không commit), 0 lỗi.

## Đọc kết quả dev

1. **Mỗi tùy chọn sửa đúng nhóm nó nhắm tới và không động vào nhóm khác.** Bảng "Tệp đổi kết quả": id sửa 3 tệp composite cùng loại (đúng như thí nghiệm 06: 3/6 tệp nguyên vẹn), tb sửa 6 tệp composite khác loại (2/8 -> 8/8, đúng như thí nghiệm 05), gộp hai thì cộng lại (không giẫm lên nhau): 232 = 223 + 3 + 6. **0 tệp hỏng** ở mọi nhóm, kể cả 155 tệp nhiều trang không ghép (nơi tách nhầm là rủi ro chính; số tách nhầm của nhóm này không đổi so với S10).
2. **Sai lặng lẽ giảm 14 -> 5** (5,9% -> 2,1% số tệp tự xử lý, Clopper-Pearson [0,7%; 4,9%]), vì phần lớn lỗi âm thầm cũ là tệp composite bị gán nhầm loại. Vẫn **chưa đạt** mục tiêu 1% của giao thức (§7).
3. **Số lời gọi LLM phân loại giảm** 35 -> 26 trên 245 tệp, vì tb cho cổng luật quyết định thay cho TF-IDF/LLM ở một số tài liệu (kiểm hồi quy của thí nghiệm 05: 25/237 tài liệu đơn, cùng nhãn).
4. **Mức độ chắc của "+3,0 điểm [+2,0; +3,9]".** CI hẹp vì chỉ 14 tệp composite thay đổi, tất cả cùng một cách (hỏng 0, sửa 14), nên bootstrap không có biến thiên; đừng đọc nó như độ chắc tổng quát hóa. Hai tùy chọn được nghĩ ra sau khi đọc chính các tệp này (06 và 05 nói rõ), nên đây là mức **trần lạc quan**. Hiệu id ở cấp tài liệu (+2,2 điểm, CI [+0,0; +5,1]) sát 0.
5. **S9 (triage) khác bản chất**: giữ tệp thường nguyên vẹn (155/155) và sai lặng lẽ thấp (4), nhưng trả bằng việc chuyển 22% tệp về người và bỏ rơi tệp ghép (185/318 tài liệu giao đúng). Nếu doanh nghiệp coi sai lặng lẽ đắt hơn nhân sự duyệt, triage vẫn là lựa chọn thay thế (`--splitter triage`).

## Kết quả TEST: đọc đúng nghĩa

Cấu hình đóng băng S10+id+tb cho đúng kết quả của S10 trên 59 tệp (0 tệp đổi). Điều đó nhất quán với việc TEST không có composite khác loại hay cùng loại ngoài `BB_LAY_MAU` để hai tùy chọn tác động; số lời gọi LLM (5) và số lát cắt (70) cũng không đổi, tức tb không đổi quyết định nào ở 59 tệp. TEST vì vậy chỉ trả lời "không hại tệp thường" (đạt, 0 hỏng), **không** xác nhận mức +3 điểm của dev. Lần chạy này ghi là `run2` trong `01_end_to_end/test_run_registry.json` (lần TEST thứ hai của thí nghiệm toàn trình, lý do: cấu hình mới; lần thứ nhất của S10 giữ nguyên).

## Dựng ảnh cho VLM: nén nhanh và khóa cache

* **Vì sao chậm.** Ảnh PNG lưu với `optimize=True` (thí nghiệm 02: trung vị 4,2 s/lát cắt). Đo thẳng (`bench_render.py`, 40 đơn vị dev có trường hạn, 154 ảnh, cùng PyMuPDF 200 dpi, cắt đôi trang, cạnh dài <= 1600 px): `optimize=True` trung vị **3,62 s** (p90 4,32) so với `compress_level=1` **0,89 s** (p90 1,17), nhanh hơn **4,0 lần**. Tệp ảnh to hơn khoảng 40% (23,2 MB so với 16,5 MB trên 16 ảnh thử), không đáng kể vì ảnh chỉ ở thư mục tạm.
* **Điểm ảnh không đổi**: PNG nén không mất; so sánh mảng điểm ảnh RGB của hai cách lưu: **154/154 ảnh giống hệt** (và có test `tests/test_pipeline_options_v2.py`). VLM nhận cùng điểm ảnh.
* **Khóa cache.** Kiểm lại `ollama_vlm_client`: khóa cache trước đây băm **byte của tệp PNG**, nên đổi mức nén sẽ làm lỡ cache dù ảnh giống hệt. Đã đổi sang `image_content_hash` (băm kích thước + điểm ảnh RGB; không giải mã được thì băm byte), tag khóa `t4-src-vlm-v1` -> `v2`. **Hệ quả một lần**: các câu trả lời VLM đã cache dưới khóa cũ (cache của nhóm 4 và `vlm_store.json` của thí nghiệm 02) không còn khớp; lần chạy sau tính lại và cache lại. Số liệu thí nghiệm 02 không đổi vì ảnh/pixel không đổi.
* Trong lúc chạy cả pipeline (mục dưới), `render_ms` của lát cắt có VLM: trung vị **0,92 s**, p95 1,18 s (12 lát).

## Chi phí của cấu hình đã chọn, có OCR thật (`cost_sample_v2.py`)

Mẫu **30 tệp dev, 90 trang** (OCR 30 trang đầu mỗi tệp; mẫu dài nhất 10 trang): 10 tệp loại có trường hạn (3/4/3 theo loại, <= 12 trang) cộng 20 tệp ngẫu nhiên theo nhóm (hạn ngạch 6 một trang, 10 nhiều trang, 2 composite khác loại, 1 cùng loại, 1 `BB_LAY_MAU`), seed cố định; tính chung cả mẫu: 7 một trang, 19 nhiều trang không ghép, 2 composite khác loại, 1 cùng loại, 1 `BB_LAY_MAU`. Chạy qua `DocumentPipeline` thật: `model+merge+id`, `title_tiebreak`, trích xuất bật, VLM bật, OCR VietOCR trên `cuda:0`, cache LLM/VLM là thư mục tạm trống (mọi lời gọi là thật). **GPU RTX 3060 12 GB dùng chung** (Ollama có client khác; Kev không chạy), độ trễ phụ thuộc tải. Cả 30 tệp ra `auto_file`, 0 cảnh báo.

| giai đoạn | trung vị / tệp | p95 / tệp | trung vị / trang | p95 / trang | tỉ trọng tổng thời gian |
|---|---|---|---|---|---|
| OCR (không tính nạp mô hình 6,8 s, một lần) | 8,6 s | 32,2 s | 4,26 s | 6,27 s | 45% |
| tách | 0,25 s | 0,40 s | 0,12 s | 0,22 s | 1,0% |
| phân loại | 8 ms | 25 ms | 4 ms | 7 ms | 0,04% |
| dựng ảnh (chỉ lát cắt có VLM) | 0 (12/30 tệp có), 0,92 s ở các tệp đó | 1,18 s | 0 | 0,47 s | 1,3% |
| trích xuất (LLM + VLM) | 6 ms (12/30 tệp có VLM) | 36,2 s | 6 ms | 25,3 s | 52% |
| **tổng** | **32,6 s** | **49,3 s** | **6,8 s** | **30,5 s** | |

Tệp có VLM (12 tệp): tổng trung vị 42,6 s; tệp không có VLM (18 tệp): 11,2 s. Cả mẫu 809 s cho 90 trang = 400 trang/giờ, nhưng mẫu cố ý nhiều tệp có trường hạn (12/30 = 40%, quần thể 27%).

**Số lời gọi mỗi tệp** (30 tệp): LLM phân loại **0** (0/30; trên 245 tệp dev đếm được 26 lời gọi = 0,11/tệp); LLM trích xuất 14 (0,47/tệp); VLM 12 (0,40/tệp). Độ trễ mỗi lời gọi: LLM trích xuất trung vị 13,3 s (p95 14,7 s), VLM trung vị 20,9 s (p95 22,5 s).

**VRAM** (nvidia-smi 0,5 s/lần, 1296 mẫu, tổng của cả GPU gồm Ollama `qwen3.5:4b` đang nạp): nền trước khi chạy 4,93 GiB, trung vị 5,70 GiB, **đỉnh 6,58 GiB** (+1,65 GiB so với nền: mô hình OCR và ngữ cảnh VLM 12288). Còn dư ~5,7 GiB trên thẻ 12 GiB.

**Ước lượng số trang/giờ cho một máy RTX 3060 12 GB** (xử lý tuần tự từng tệp, như pipeline hiện tại): thời gian một tệp = trang × (OCR 4,04 + tách 0,13 + phân loại ~0) s + 0,273 × 33,9 s (tệp loại có trường hạn: trích xuất LLM+VLM + dựng ảnh, 83/304 = 27,3% tài liệu duy nhất) + 0,069 × 13,3 s (phiếu xuất kho: một lời gọi LLM, 21/304, suy từ độ trễ LLM đo được, không có VLM). Trung bình 3,36 trang/tệp theo cơ cấu tệp thật -> **24,2 s/tệp -> khoảng 500 trang/giờ** (~150 tệp/giờ). Chặn hai đầu: không trích xuất 860 trang/giờ; mọi tệp đều loại có VLM 250 trang/giờ. **Đây là ước lượng từ mẫu 30 tệp một mô hình tuyến tính, không phải đo trên ngày làm việc thật**; nút cổ chai là OCR (4 s/trang) và lời gọi Qwen3.5-4B (13 s + 21 s). Chưa thử chạy OCR của tệp kế tiếp song song với trích xuất của tệp trước (GPU tranh nhau), hướng tăng thông lượng rõ nhất.

## Mặc định mới và rủi ro

> **Cập nhật sau review độc lập (2026-10-16): mặc định đã được ĐỔI LẠI về S10** (`DEFAULT_PRESET = "model+merge"`, `DEFAULT_TITLE_TIEBREAK = False`). Lý do (báo cáo [04](../../reports/04_phase3_review_and_deployment.md)): hai tùy chọn được thiết kế từ chính các tệp composite dùng để đo, và TEST không có composite nên cổng "TEST không hại" không thể trượt. Hai quy tắc nay chạy ở chế độ **ghi bóng**: `tiebreak` ghi nhãn nó sẽ chọn vào `routing[i].shadow`; quy tắc `id` khi muốn thêm ranh giới thì chuyển cả tệp cho người duyệt (`id_rule_boundary`). Đoạn dưới đây giữ nguyên như lúc thí nghiệm để đối chiếu.

Quy tắc ghi trước cho phép đổi mặc định, và đã đổi: `DEFAULT_PRESET = "model+merge+id"` (`src/splitting/policy.py`), `DEFAULT_TITLE_TIEBREAK = True` (`src/pipeline.py`); CLI `--splitter model+merge`, `--no-title-tiebreak` trả về hành vi cũ. Các test khẳng định mặc định cũ trong `tests/test_pipeline.py`, `tests/test_splitting_type_merge.py`, `tests/test_splitting_id.py` được sửa theo (3 dòng khẳng định tên preset). Rủi ro cần chủ phiên cân nhắc, vì bằng chứng TEST là rỗng:

* **tiebreak cho luật quyết định ở 25/237 tài liệu đơn dev** mà trước đây luật bỏ qua (cùng nhãn, 25/25 đúng, nhưng cận trên 95% của tỉ lệ sai là 11,3%). Luật không có độ tin cậy cảnh báo: biểu mẫu chưa thấy có tên loại khác nằm ở vùng tiêu đề có thể nhận sai âm thầm. Chưa đo trên biểu mẫu lạ; thí nghiệm 05 từng đề nghị chờ thêm mẫu BB/PXK từ nhiều nhà cung cấp trước khi bật. Nếu chủ phiên thấy quá sớm: đặt `DEFAULT_TITLE_TIEBREAK = False` (một dòng), id vẫn giữ.
* **id** chỉ có bằng chứng ở 6 tệp composite cùng loại, quy tắc được nghĩ ra sau khi đọc chính chúng (0/448 cặp mẫu âm kích hoạt, 0 tách nhầm thêm trên 155 tệp nhiều trang).

## Chưa chứng minh

1. Đáp án máy, chưa người kiểm; 5 tệp `check_composite` rủi ro cao nhất.
2. Lợi ích của id và tb nằm ở **14 tệp composite dev của vài nhà cung cấp**, đã dùng để nghĩ ra hai tùy chọn; không có giữ ngoài. TEST không chứa composite nào ngoài `BB_LAY_MAU` nên không kiểm được; muốn kiểm cần thêm mẫu ghép từ nguồn khác.
3. Quy tắc chọn ghi trước nhưng ngưỡng của từng tùy chọn (0,7 cho id; 400/300 ký tự cho tb) chọn ở các thí nghiệm 05/06 sau khi xem dev.
4. Sai lặng lẽ vẫn 5/237 (2,1%) trên dev; mục tiêu 1% chưa đạt; chưa đo trên mẫu ngẫu nhiên phần tự xử lý.
5. Chi phí: mẫu 30 tệp, GPU dùng chung (độ trễ thay đổi theo tải; lần chạy này không bị nạp lại mô hình rõ rệt), ước lượng 500 trang/giờ là mô hình tuyến tính trên mẫu cố ý nhiều tệp có trường hạn; OCR giới hạn 30 trang/tệp; không đo nhiều tiến trình song song.
6. Đổi khóa cache VLM làm mất cache cũ một lần (xem trên); chưa chạy lại thí nghiệm 02 để kiểm kết quả VLM giống hệt sau khi đổi khóa (ảnh giống hệt điểm ảnh nên kết quả đáng lẽ giống, nhưng đó là suy luận, VLM chưa được gọi lại trên 82 đơn vị).

## Thay đổi mã

* `src/pipeline.py`: tham số `title_tiebreak` (`DEFAULT_TITLE_TIEBREAK = True`), gán `rule_title_tiebreak` cho bộ phân loại có thuộc tính này (không sửa `doc_classifier.py`).
* `src/splitting/policy.py`: `DEFAULT_PRESET = "model+merge+id"` (chỉ đổi mặc định; preset đã có từ thí nghiệm 06).
* `scripts/run_pipeline.py`: `--splitter` nhận `model+merge+id` (lấy từ `PRESETS`), `--title-tiebreak/--no-title-tiebreak`.
* `src/extraction/field_vlm.py`: `PNG_COMPRESS_LEVEL = 1`, `image_content_hash`, khóa cache `t4-src-vlm-v2`.
* Test mới `tests/test_pipeline_options_v2.py` (CLI, tiebreak truyền xuống bộ phân loại, ảnh giống hệt điểm ảnh, khóa theo điểm ảnh, mặc định mới); 3 khẳng định mặc định cũ được cập nhật ở các tệp test hiện có. Toàn bộ `pytest -q` 285 qua; `teams/00_data_and_eval/tests` + `teams/team4_extraction/tests` 256 qua.
* Thí nghiệm: `run_v2.py`, `cost_sample_v2.py`, `bench_render.py`, `dev_selection_v2.json`, `results/*` (CSV từng tệp chứa `doc_id`, chỉ dùng nội bộ); `01_end_to_end/test_run_registry.json` thêm mục `run2`.
