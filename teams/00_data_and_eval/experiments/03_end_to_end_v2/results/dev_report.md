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
