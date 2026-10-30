## Kết quả TEST (MỘT lần, cấu hình đóng băng = **S10**: {"name": "S10", "base": "model", "tau": 0.7, "merge": true, "band": null, "keep": 0.99})

n = 59 tệp TEST: tệp 1 trang 21, nhiều trang, không ghép 36, BB_LAY_MAU 2. Không có composite khác loại và composite cùng loại ngoài BB_LAY_MAU trong TEST.

| biến thể | tệp đúng hoàn toàn (c) | Clopper-Pearson 95% | tự xử lý | sai lặng lẽ / tự xử lý (CP 95%) | tự xử lý và đúng | lời gọi LLM | lát cắt |
|---|---|---|---|---|---|---|---|
| S0 | 56/59 = 94,9% | [85,9%; 98,9%] | 59/59 | 3/59 [1,1%; 14,1%] | 56/59 | 4 | 59 |
| CHOSEN | 56/59 = 94,9% | [85,9%; 98,9%] | 58/59 | 2/58 [0,4%; 11,9%] | 56/59 | 5 | 70 |

**(c) theo nhóm**

| biến thể | tệp 1 trang (n=21) | nhiều trang, không ghép (n=36) | BB_LAY_MAU (n=2) | **toàn bộ, theo cơ cấu tệp thật** |
|---|---|---|---|---|
| S0 | 20/21 = 95% [86%; 100%] | 36/36 = 100% [100%; 100%] | 0/2 = 0% [0%; 0%] | **96,1% [93,1%; 97,6%]** |
| CHOSEN | 20/21 = 95% [86%; 100%] | 34/36 = 94% [86%; 100%] | 2/2 = 100% [100%; 100%] | **94,8% [88,1%; 100,0%]** |

| biến thể | tự xử lý hoàn toàn | tự xử lý VÀ đúng | sai lặng lẽ (tự xử lý mà sai) | sai lặng lẽ / tự xử lý | thô: tự xử lý / tệp | thô: sai / tự xử lý (Clopper-Pearson 95%) |
|---|---|---|---|---|---|---|
| S0 | 100,0% [100,0%; 100,0%] | 96,1% [93,1%; 97,6%] | 3,92% [2,41%; 6,95%] | 3,92% [2,41%; 6,95%] | 59/59 | 3/59 = 5,08% [1,06%; 14,15%] |
| CHOSEN | 98,2% [94,5%; 100,0%] | 94,8% [88,1%; 100,0%] | 3,34% [0,00%; 8,83%] | 3,40% [0,00%; 8,83%] | 58/59 | 2/58 = 3,45% [0,42%; 11,91%] |

| biến thể | tài liệu đáp án giao ĐÚNG và tự động | tài liệu đáp án (tổng) | trong đó của các nhóm composite (n tài liệu) |
|---|---|---|---|
| S0 | 56/68 = 82,4% [60,5%; 100,0%] | 68 | 0/11 |
| CHOSEN | 65/68 = 95,6% [89,8%; 100,0%] | 68 | 11/11 |

Mỗi ô: (tệp S0 đúng hoàn toàn mà biến thể làm hỏng) hỏng / (tệp S0 sai mà biến thể sửa được) sửa.

| biến thể | tệp 1 trang | nhiều trang, không ghép | BB_LAY_MAU | hiệu có trọng số (biến thể - S0) của (c), CI ghép cặp | kết luận |
|---|---|---|---|---|---|
| CHOSEN | 0 hỏng / 0 sửa | 2 hỏng / 0 sửa | 0 hỏng / 2 sửa | -1.2 điểm [-6.7; +2.4] | không tách được |