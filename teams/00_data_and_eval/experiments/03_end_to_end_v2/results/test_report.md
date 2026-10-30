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
