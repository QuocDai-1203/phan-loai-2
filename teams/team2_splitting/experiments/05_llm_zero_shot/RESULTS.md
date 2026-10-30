# 05 - Zero-shot 'trang này có mở tài liệu mới không?' bằng qwen3.5:4b cục bộ - phạm vi `dev`

- **ngày chạy (UTC):** 2026-10-12 02:27
- **lệnh:** `.venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/05_llm_zero_shot/run.py --neg-files 20`
- **đáp án:** `teams/team2_splitting/gold/boundary_gold_v0.csv` sha1[:10] = `d9a30b5896` (v0, máy, CHƯA người kiểm)
- **nhãn:** `data/labels_v2.csv` sha1[:10] = `eb3348713a`
- **văn bản:** `data/ocr_v2.jsonl` (OCR cục bộ, tối đa 30 trang/tài liệu) sha1[:10] = `ac87a66c25`
- **phạm vi:** **dev** = DEV + EXCLUDED_COMPOSITE (không có tài liệu TEST)
- **bootstrap:** 2000 lần lấy mẫu lại theo TỆP, seed 20260711, percentile 95%
- **máy:** Windows-11-10.0.26100-SP0, Python 3.13.14
- **mô hình:** `qwen3.5:4b` qua Ollama `http://127.0.0.1:11434` (đang nạp: bge-m3:latest (context 4096)); `think=False`, temperature 0, seed 0, đầu ra bị ràng buộc theo JSON schema enum ['NEW_DOCUMENT', 'SAME_DOCUMENT']; `num_ctx=32768`. Chạy on-premise, không gửi gì ra ngoài.
- **tệp được chấm:** 19 tệp composite + 20 tệp âm (lấy mẫu ngẫu nhiên seed 7 từ 155)
- **độ trễ (NHIỄU: GPU/CPU dùng chung với agent khác):** 136 cặp; độ trễ mỗi cặp (đo lúc gọi thật, lưu trong cache): n=136, median 1207 ms, p95 16041 ms; tổng 0 s
- **lỗi phân tích đầu ra:** 0 cặp (tính là SAME_DOCUMENT)

## Kết quả theo nhóm (cùng tập tệp cho cả ba phương pháp)

Không có huấn luyện nên không cần cross-fitting. Prompt `rules`:

> Bạn là trợ lý tách tài liệu quét. Bạn nhận hai trang LIÊN TIẾP của cùng một tệp PDF (văn bản OCR, có thể sai chính tả, mất dấu). Hãy quyết định trang B có MỞ ĐẦU MỘT TÀI LIỆU MỚI (NEW_DOCUMENT) hay là phần tiếp theo của tài liệu chứa trang A (SAME_DOCUMENT).
> Quy tắc: các trường hợp sau là SAME_DOCUMENT: trang chỉ có chữ ký/con dấu, trang trắng, mặt sau, trang đánh số '2/2', phụ lục/bảng kê/danh mục đính kèm, các điều khoản hoặc phần con bên trong cùng một hợp đồng hoặc hồ sơ (kể cả khi trang đó lặp lại tiêu đề hay quốc hiệu). NEW_DOCUMENT khi trang B là một giấy tờ riêng: khác loại với trang A, hoặc cùng loại nhưng là BẢN KHÁC (khác số, khác ngày, khác người hoặc khác xe).


**composite khác loại** (8 tệp, 26 vị trí, 20 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment (tệp nguyên vẹn) | tách nhầm / 100 vị trí | loại segment (cổng luật) |
|---|---|---|---|---|---|---|
| rule cũ (01) | 0.905 [0.778; 1.000] (19/21) | 0.950 [0.850; 1.000] (19/20) | 0.927 [0.850; 1.000] | 5/8 = 0.625 (Wilson 0.306; 0.863) | 7.69 [0.00; 14.29] (2) | 0.643 [0.500; 0.767] (oracle 0.679) |
| rule v2 (02) | 1.000 [1.000; 1.000] (19/19) | 0.950 [0.850; 1.000] (19/20) | 0.974 [0.919; 1.000] | 7/8 = 0.875 (Wilson 0.529; 0.978) | 0.00 [0.00; 0.00] (0) | 0.643 [0.500; 0.767] (oracle 0.679) |
| d Qwen3.5-4B zero-shot (prompt rules) | n/a (0/0) | 0.000 [0.000; 0.000] (0/20) | 0.000 [0.000; 0.000] | 0/8 = 0.000 (Wilson 0.000; 0.324) | 0.00 [0.00; 0.00] (0) | 0.214 [0.125; 0.292] (oracle 0.679) |

**composite cùng loại, ngoài BB_LAY_MAU** (6 tệp, 11 vị trí, 7 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment (tệp nguyên vẹn) | tách nhầm / 100 vị trí | loại segment (cổng luật) |
|---|---|---|---|---|---|---|
| rule cũ (01) | 0.667 [0.333; 1.000] (4/6) | 0.571 [0.167; 0.889] (4/7) | 0.615 [0.222; 0.875] | 2/6 = 0.333 (Wilson 0.097; 0.700) | 18.18 [0.00; 42.90] (2) | 0.615 [0.250; 0.933] (oracle 0.615) |
| rule v2 (02) | 0.800 [0.500; 1.000] (4/5) | 0.571 [0.167; 0.889] (4/7) | 0.667 [0.250; 0.889] | 2/6 = 0.333 (Wilson 0.097; 0.700) | 9.09 [0.00; 21.45] (1) | 0.615 [0.250; 0.933] (oracle 0.615) |
| d Qwen3.5-4B zero-shot (prompt rules) | n/a (0/0) | 0.000 [0.000; 0.000] (0/7) | 0.000 [0.000; 0.000] | 0/6 = 0.000 (Wilson 0.000; 0.390) | 0.00 [0.00; 0.00] (0) | 0.692 [0.333; 1.000] (oracle 0.615) |

**composite BB_LAY_MAU** (5 tệp, 46 vị trí, 46 ranh giới thật)

| phương pháp | precision | recall | F1 | exact-segment (tệp nguyên vẹn) | tách nhầm / 100 vị trí | loại segment (cổng luật) |
|---|---|---|---|---|---|---|
| rule cũ (01) | 1.000 [1.000; 1.000] (46/46) | 1.000 [1.000; 1.000] (46/46) | 1.000 [1.000; 1.000] | 5/5 = 1.000 (Wilson 0.566; 1.000) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| rule v2 (02) | 1.000 [1.000; 1.000] (46/46) | 1.000 [1.000; 1.000] (46/46) | 1.000 [1.000; 1.000] | 5/5 = 1.000 (Wilson 0.566; 1.000) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |
| d Qwen3.5-4B zero-shot (prompt rules) | 1.000 [1.000; 1.000] (1/1) | 0.022 [0.000; 0.091] (1/46) | 0.043 [0.000; 0.167] | 0/5 = 0.000 (Wilson 0.000; 0.434) | 0.00 [0.00; 0.00] (0) | 1.000 [1.000; 1.000] (oracle 1.000) |

**mẫu âm (nhiều trang, không composite)** (20 tệp, 63 vị trí, 0 ranh giới thật)

| phương pháp | tách nhầm / 100 vị trí | tệp có >= 1 tách nhầm | exact-segment (tệp nguyên vẹn) | loại segment (cổng luật) |
|---|---|---|---|---|
| rule cũ (01) | 55.56 [48.28; 72.73] (35/63) | 15/20 = 0.750 [0.550; 0.900] | 5/20 = 0.250 (Wilson 0.112; 0.469) | 0.900 [0.750; 1.000] (oracle 0.900) |
| rule v2 (02) | 39.68 [22.22; 50.00] (25/63) | 11/20 = 0.550 [0.349; 0.750] | 9/20 = 0.450 (Wilson 0.258; 0.658) | 0.850 [0.700; 1.000] (oracle 0.900) |
| d Qwen3.5-4B zero-shot (prompt rules) | 11.11 [0.00; 16.43] (7/63) | 3/20 = 0.150 [0.000; 0.300] | 17/20 = 0.850 (Wilson 0.640; 0.948) | 0.950 [0.850; 1.000] (oracle 0.900) |

## So sánh ghép cặp với rule cũ và rule v2

| nhóm | chỉ số | Qwen - rule cũ | CI 95% (bootstrap ghép cặp theo tệp) | kết luận |
|---|---|---|---|---|
| composite khác loại (n=8) | f1 | -0.927 | [-1.000; -0.850] | tách được: kém hơn |
| composite khác loại (n=8) | recall | -0.950 | [-1.000; -0.850] | tách được: kém hơn |
| composite khác loại (n=8) | precision | +nan | [+nan; +nan] | không tính được (mẫu số bằng 0 ở nhiều lần lấy mẫu lại) |
| composite khác loại (n=8) | exact_rate | -0.625 | [-1.000; -0.250] | tách được: kém hơn |
| composite khác loại (n=8) | false_split_per100 | -7.692 | [-14.286; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | f1 | -0.615 | [-0.875; -0.222] | tách được: kém hơn |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | recall | -0.571 | [-0.889; -0.167] | tách được: kém hơn |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | precision | +nan | [+nan; +nan] | không tính được (mẫu số bằng 0 ở nhiều lần lấy mẫu lại) |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | exact_rate | -0.333 | [-0.667; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | false_split_per100 | -18.182 | [-42.897; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | f1 | -0.957 | [-1.000; -0.833] | tách được: kém hơn |
| composite BB_LAY_MAU (n=5) | recall | -0.978 | [-1.000; -0.909] | tách được: kém hơn |
| composite BB_LAY_MAU (n=5) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | exact_rate | -1.000 | [-1.000; -1.000] | tách được: kém hơn |
| composite BB_LAY_MAU (n=5) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=20) | false_split_per100 | -44.444 | [-67.570; -34.211] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=20) | files_with_false_split | -0.600 | [-0.850; -0.350] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=20) | exact_rate | +0.600 | [+0.350; +0.850] | tách được: tốt hơn |

| nhóm | chỉ số | Qwen - rule v2 | CI 95% (bootstrap ghép cặp theo tệp) | kết luận |
|---|---|---|---|---|
| composite khác loại (n=8) | f1 | -0.974 | [-1.000; -0.919] | tách được: kém hơn |
| composite khác loại (n=8) | recall | -0.950 | [-1.000; -0.850] | tách được: kém hơn |
| composite khác loại (n=8) | precision | +nan | [+nan; +nan] | không tính được (mẫu số bằng 0 ở nhiều lần lấy mẫu lại) |
| composite khác loại (n=8) | exact_rate | -0.875 | [-1.000; -0.625] | tách được: kém hơn |
| composite khác loại (n=8) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | f1 | -0.667 | [-0.889; -0.250] | tách được: kém hơn |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | recall | -0.571 | [-0.889; -0.167] | tách được: kém hơn |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | precision | +nan | [+nan; +nan] | không tính được (mẫu số bằng 0 ở nhiều lần lấy mẫu lại) |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | exact_rate | -0.333 | [-0.667; +0.000] | không tách được |
| composite cùng loại, ngoài BB_LAY_MAU (n=6) | false_split_per100 | -9.091 | [-21.448; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | f1 | -0.957 | [-1.000; -0.833] | tách được: kém hơn |
| composite BB_LAY_MAU (n=5) | recall | -0.978 | [-1.000; -0.909] | tách được: kém hơn |
| composite BB_LAY_MAU (n=5) | precision | +0.000 | [+0.000; +0.000] | không tách được |
| composite BB_LAY_MAU (n=5) | exact_rate | -1.000 | [-1.000; -1.000] | tách được: kém hơn |
| composite BB_LAY_MAU (n=5) | false_split_per100 | +0.000 | [+0.000; +0.000] | không tách được |
| mẫu âm (nhiều trang, không composite) (n=20) | false_split_per100 | -28.571 | [-40.000; -15.514] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=20) | files_with_false_split | -0.400 | [-0.650; -0.150] | tách được: tốt hơn |
| mẫu âm (nhiều trang, không composite) (n=20) | exact_rate | +0.400 | [+0.150; +0.650] | tách được: tốt hơn |

## Cách đọc kết quả (nhận xét của người viết, mọi số lấy từ các bảng trên)

1. **Với prompt đã viết (`rules`), Qwen3.5-4B zero-shot gần như không bao giờ nói "tài liệu mới"**: 0/20 ranh giới ở composite khác loại, 0/7 ở nhóm cùng loại, 1/46 ở `BB_LAY_MAU` (recall 0,022). Ngược lại nó tách nhầm ít: 7/63 vị trí mẫu âm (11,1 / 100 vị trí, 17/20 tệp âm nguyên vẹn). Tức là mô hình nghiêng hẳn về "cùng tài liệu" nên tránh được lỗi cắt vụn nhưng không tách được gì, và về mặt chức năng là không dùng được làm bộ tách. Chênh ghép cặp với rule cũ trên các nhóm composite là "tách được: kém hơn" (recall -0,95 / -0,57 / -0,98), còn trên mẫu âm là "tách được: tốt hơn" (nhưng chỉ 20 tệp âm được chấm, nên CI rộng và so với phương pháp (c) trên 155 tệp không so trực tiếp được).
2. **Có thể do prompt, không chỉ do mô hình.** Prompt liệt kê nhiều ngoại lệ "không phải tài liệu mới" (trang chữ ký, phụ lục, kể cả khi lặp tiêu đề...) và có thể đẩy mô hình về SAME_DOCUMENT. Tôi định thử một prompt trung tính thứ hai (`--prompt neutral`, mã còn trong `run.py`) nhưng **chưa chạy xong**: giữa chừng Ollama dùng chung bị agent khác nạp lại `qwen3.5:4b` với `num_ctx` 6144 trong khi tôi gửi 32768, nên yêu cầu của tôi sẽ buộc Ollama nạp lại mô hình (mất 52 s ở cặp đầu) và có thể làm gián đoạn agent kia; tôi dừng tiến trình của mình. Vì vậy **chưa có bằng chứng về giới hạn của phương pháp zero-shot nói chung**, chỉ về một prompt với mô hình 4B này. Không có số đo cho prompt `neutral`.
3. **Độ trễ (nhiễu, GPU/CPU dùng chung):** 136 cặp, median 1,2 s mỗi cặp, p95 khoảng 16 s (p95 bị kéo bởi lúc mô hình bị nạp lại / bị tranh GPU), tổng khoảng 9 phút cho 39 tệp. Cặp trang là đơn vị, một tệp N trang cần N-1 lời gọi: tệp 30 trang khoảng 30-40 s ở median, chưa tính tranh chấp. Chạy lại từ cache gần như tức thời (2 s).
4. **Phạm vi:** chỉ chấm 19 tệp composite (tất cả trong dev) + 20 tệp âm lấy mẫu ngẫu nhiên (seed 7) vì mỗi cặp tốn vài giây trên GPU dùng chung; **không chấm tài liệu TEST** bằng phương pháp này. On-premise: chạy hoàn toàn cục bộ (`127.0.0.1:11434`), không gửi nội dung ra ngoài. Chưa thử Kev `Noul` (mục "Chưa đo" của README): chưa kiểm tra máy chủ Kev nhận kiểu nhị phân thế nào và không được cấu hình lại máy chủ ở `:8009`.
