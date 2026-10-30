# Thí nghiệm 02 - Embedding, LLM/Kev zero-shot, calibration và cascade có từ chối (Nhóm 3)

> **Đọc trước.** (1) Nhãn là `data/labels_v2.csv` (sha1[:10] `eb3348713a`): do **hai lượt gán nhãn của các mô hình AI cùng họ** theo cùng một hướng dẫn, **chưa được nhân viên công ty kiểm chứng**.
> (2) Mô tả loại (`taxonomy_v2.json`) và từ khóa của cổng luật được viết *sau khi xem chính các tài liệu mẫu này*, và nhãn do mô hình gán theo chính các mô tả đó: điểm rất cao của LLM zero-shot có thể chỉ là
> **tái tạo lại cách gán nhãn bằng mô hình**, chưa chứng minh đúng với nhân viên hay với khách hàng mới (mục 3 và 11).
> (3) TEST chỉ có **59 tài liệu**; một lỗi = 1.7%. "0 lỗi" chỉ chứng minh được "sai < 5-8%", không phải "sai < 1%".
> (4) `haiku_p12` là phiên âm LLM-vision **đám mây - cận trên, không dùng được on-premise**; `ocr_v2_p12` (VietOCR chạy local) mới là *điều kiện triển khai*; `legacy_p1` (RapidOCR cũ) là đối chứng chất lượng thấp.
> Các bảng giữa dấu `<!-- BEGIN:... -->` được `run_all.py --stage report` sinh lại từ CSV; các đoạn "Đọc kết quả" do người viết dựa trên lần chạy ngày 2026-10-11 và cần rà lại nếu chạy lại với nhãn khác.
> **Đã đo** = số lấy từ phép đo trong tệp này; **Suy luận** = giải thích chưa được kiểm chứng.

## 0. Tóm tắt (cho người ra quyết định)

| # | Kết luận | Mức chắc chắn |
|---|---|---|
| 1 | Điều kiện triển khai thật (`ocr_v2_p12`): baseline cổ điển (TF-IDF) đạt macro-F1 DEV 0.977 ± 0.019 và **TEST 0.946 [0.847; 1.000]**, tự động xếp được **61.0% [49.2; 72.9]** tài liệu với sai <= 1% (TEST, 0 lỗi); không tách được khỏi cận trên Haiku (Δ = +0.028, CI [0.000; 0.109]). | Đã đo; CI rộng |
| 2 | Một LLM cục bộ **Qwen3.5-4B** chỉ đọc mô tả loại (không dữ liệu huấn luyện) phân loại cả 34 loại với accuracy DEV **0.996**, TEST **0.983 [0.949; 1.000]**, kể cả 24 loại hiếm (recall 62/63 DEV, 10/11 TEST) - trong khi TF-IDF không bao giờ nhận loại hiếm (recall 0). **Kev-0.8B** chỉ đạt 0.78-0.85 với mô tả ngắn, **sụp (0.30-0.40) với mô tả dài**, nhưng đạt 0.96 DEV / 0.93 TEST khi chỉ đưa **tên loại**. | Đã đo (xem cảnh báo vòng tròn nhãn/mô tả) |
| 3 | **Cascade** luật -> TF-IDF -> LLM -> người nâng tỉ lệ tự động xếp từ ~64% (TF-IDF đơn) lên **96.6-100%** trên TEST (Δ = +0.356 [0.237; 0.475] so với TF-IDF, cặp bootstrap), với 0-1 lỗi / 59; trên DEV (ước lượng cross-fit) 95-99%. Cổng luật quyết định ~76-85% tài liệu; LLM chỉ chạy cho ~5-7% tài liệu. | Đã đo; mẫu nhỏ, cổng luật có thể lạc quan |
| 4 | **Không thể chứng minh sai <= 1%** với dữ liệu hiện có: 1 lỗi / 59 ở TEST (cận trên 95% = 7.8%). Cần >= ~300 tài liệu tự nhận liên tiếp không lỗi. Ngưỡng chọn trên DEV rất *dễ dãi* (hầu như nhận mọi thứ) vì LLM gần như hoàn hảo trên DEV. | Đã đo |
| 5 | Mô hình **biết khi nào không biết** ở mức dùng được cho Kev (AUROC 0.96) và Qwen 2 bước (0.98), **không** cho xác suất một bước của Qwen (gần hằng số). **Đồng thuận của hai LLM (Kev + Qwen)** nhận 95.8% DEV / 94.9% TEST với 0 / 1 lỗi - cách từ chối không cần ngưỡng. | Đã đo |
| 6 | Chất lượng OCR quan trọng với LLM: `legacy_p1` làm Qwen3.5 tụt 0.996 -> 0.945 (DEV) và **Kev tụt 0.96 -> 0.50**; cổng luật + TF-IDF bền hơn. `ocr_v2` ~ Haiku (Qwen 0.996 vs 1.000). | Đã đo |
| 7 | Chi phí: cascade chạy ~3.5 ms (luật) + 2.7 ms (TF-IDF) cho 92-95% tài liệu, ~1.2 s (Qwen3.5-4B, 3.1 GB VRAM) cho phần còn lại: ~40-60 nghìn tài liệu/giờ/luồng **cho riêng bước phân loại**; **OCR (2.6-6 s/trang) mới là nút cổ chai**. Toàn bộ on-premise. | Đã đo |

## 1. Mục tiêu

Thí nghiệm 01 cho thấy mười loại tài liệu lớn gần như được giải quyết bằng TF-IDF (macro-F1 0.96-0.98, 2-3 ms/tài liệu). Phần chưa giải quyết là **(a)** 24 loại hiếm (74 tài liệu, 1-9 tài liệu mỗi loại) mà mô hình có giám sát không học được;
**(b)** biết khi nào nên từ chối (abstain) để chuyển cho người; **(c)** chi phí và quyền riêng tư. Thí nghiệm này trả lời bằng phép đo:

| # | Câu hỏi | Mục |
|---|---|---|
| E1 | Embedding bge-m3 (+ LR / tâm lớp / kNN) có học được từ ít mẫu, kể cả loại hiếm, không? | 4 |
| E2 | Một LLM/Kev cục bộ chỉ đọc mô tả loại (zero-shot) phân loại được bao nhiêu trên toàn taxonomy, đặc biệt loại hiếm? | 5 |
| E3 | Mô hình có *biết khi nào nó không biết* không (calibration, risk-coverage, đồng thuận)? | 6 |
| E4 | Cascade luật -> TF-IDF -> LLM/embedding -> người: bao nhiêu % tự động xếp với sai <= 1% / 2%, tải cho người, độ trễ, từng tầng đóng góp gì (ablation)? | 7 |
| E5 | Kết quả có giữ khi dùng OCR local (triển khai) thay phiên âm đám mây (cận trên) hay OCR cũ? | 8 |
| - | Chi phí / riêng tư / vận hành từng phương án; thiết kế đề xuất; việc cần làm tiếp | 9, 10 |

Đối tượng đọc: sinh viên năm cuối tiếp tục đề tài và ban điều hành. Quy tắc đánh giá (đơn vị = tài liệu duy nhất, chia theo nhóm biểu mẫu, DEV chọn - TEST khóa chấm một lần, CI bootstrap 2000 lần, bootstrap ghép cặp)
là `teams/00_data_and_eval/reports/03_evaluation_protocol.md`; harness dùng chung `teams/00_data_and_eval/eval/harness.py` (không viết lại chỉ số).

## 2. Lệnh chạy chính xác

```
# (0) dịch vụ cục bộ phải chạy sẵn: Kev http://127.0.0.1:8009 (kev-0.8b), Ollama http://127.0.0.1:11434 (qwen3.5:4b, qwen2.5:3b, bge-m3).
#     KHÔNG chạy song song Kev và Ollama (tranh GPU: Ollama treo hàng phút, xem mục 11); chạy tuần tự từng giai đoạn.
# (1) DEV - từng giai đoạn (mọi lời gọi mô hình được cache trong _cache/, chạy lại miễn phí và tất định)
.venv\Scripts\python.exe -X utf8 teams\team3_classification\experiments\02_llm_and_cascade\run_all.py --stage embed                       # E1
.venv\Scripts\python.exe -X utf8 teams\team3_classification\experiments\02_llm_and_cascade\run_all.py --stage zeroshot --family kev       # E2 (Kev, nguồn ocr_v2_p12)
.venv\Scripts\python.exe -X utf8 teams\team3_classification\experiments\02_llm_and_cascade\run_all.py --stage zeroshot --family ollama    # E2 (Ollama)
.venv\Scripts\python.exe -X utf8 teams\team3_classification\experiments\02_llm_and_cascade\run_all.py --stage zeroshot_sources           # E5: cấu hình tốt nhất trên haiku_p12, legacy_p1
.venv\Scripts\python.exe -X utf8 teams\team3_classification\experiments\02_llm_and_cascade\run_all.py --stage calib                       # E3
.venv\Scripts\python.exe -X utf8 teams\team3_classification\experiments\02_llm_and_cascade\run_all.py --stage cascade                     # E4/E5: chọn ngưỡng trên DEV out-of-fold + ablation
.venv\Scripts\python.exe -X utf8 teams\team3_classification\experiments\02_llm_and_cascade\run_all.py --stage latency                     # độ trễ + VRAM (bỏ qua cache; chạy khi máy rảnh)
.venv\Scripts\python.exe -X utf8 teams\team3_classification\experiments\02_llm_and_cascade\run_all.py --stage devrows                     # thêm dòng DEV vào results_table.csv (một lần)
# (2) TEST khóa - đúng MỘT lần cho các cấu hình đã chốt trong tables/dev_selection_02.json (từ chối chạy lại nếu đã chấm với bộ nhãn này)
.venv\Scripts\python.exe -X utf8 teams\team3_classification\experiments\02_llm_and_cascade\run_all.py --final-test
# (3) vẽ lại bảng trong tệp này từ CSV; kiểm thử
.venv\Scripts\python.exe -X utf8 teams\team3_classification\experiments\02_llm_and_cascade\run_all.py --stage report
.venv\Scripts\python.exe -X utf8 -m pytest -q ;  .venv\Scripts\python.exe -X utf8 -m pytest teams/00_data_and_eval/tests -q
# (4) lượt bổ sung của thí nghiệm 01 với nguồn ocr_v2 (xem 01/RESULTS.md mục 0): 01\run_all.py --keep-splits --results-sources ocr_v2_p1 ocr_v2_p12 ; rồi 01\run_all.py --final-test --final-sources ocr_v2_p1 ocr_v2_p12
```

Đầu ra: `teams/team3_classification/results/02_llm_and_cascade/{tables,figs,preds}/` (CSV từng bảng; `preds/` là dự đoán từng tài liệu - **chứa doc_id, đừng đưa ra ngoài repo nội bộ**) và các dòng thêm vào
`teams/team3_classification/results/results_table.csv` (dòng DEV và TEST). Mã tái dùng: `src/classification/{llm_cache,zero_shot,cascade}.py` (có test ở `tests/`).
Chạy thử đường TEST mà không mở TEST: `EXP02_SMOKE=1 ... --final-test` (dùng tài liệu DEV, không ghi bảng chung, không ghi sổ đăng ký).

## 3. Thiết lập (đọc trước khi đọc bảng)

**Nhãn và chia dữ liệu** (giống 01): `data/labels_v2.csv`; 296 tài liệu duy nhất (34 loại), chia nhóm biểu mẫu có cắt nhóm lớn (`data/splits/splits.csv`): **DEV 237** (chọn mọi thứ), **TEST 59** (khóa, chấm một lần).
Track S = 10 lớp có >= 10 tài liệu + `RARE_OR_OTHER` (24 loại, 74 tài liệu); **Track Z = cả 34 loại**; macro-F1 Track Z chỉ trên loại có >= 3 tài liệu *thật* trong tập đang chấm (DEV: 20 loại; TEST: 10 loại); abstain tính là sai.
"Loại hiếm" = 24 loại bị gộp ở Track S (DEV có 63 tài liệu hiếm, TEST 11). Chỉ dùng DEV để chọn prompt, độ dài đầu vào, cấu hình embedding, ngưỡng.

**Nguồn văn bản.** `ocr_v2_p12` = OCR local VietOCR, trang 1-2 (**điều kiện triển khai on-premise**, nguồn chính để *chọn* prompt/cấu hình); `haiku_p12` = phiên âm LLM-vision đám mây, trang 1-2 (**cận trên, không on-premise**);
`legacy_p1` = RapidOCR cũ, trang 1 (mất dấu, chữ dính). Kiểm tra `data/ocr_v2.jsonl`: 336 tài liệu, 1084 trang, **0 trang lỗi** (`error` rỗng ở mọi trang), nguồn trang `ocr` 1020 / `text_layer` 61 / `embedded_ocr_layer+ocr` 3,
không tài liệu nào rỗng (>= 549 ký tự ở trang 1-2; trang 1 ngắn nhất 38 ký tự); 57 trang gần trống là trang trắng thật (xem `teams/team1_ocr/experiments/02_dataset_v2/RESULTS.md`).

**Mô hình thực sự đã dùng** (mọi số đến từ các mô hình sau, chạy trên máy này, không gọi dịch vụ ngoài):

| Vai trò | Mô hình | Cách gọi |
|---|---|---|
| Kev | **`jaredpalmer/kev-0.8b`** (server `demo_app.py`, `http://127.0.0.1:8009`; `/api/status` được kiểm tra trước mỗi lượt chạy, code dừng nếu không phải mô hình này) | `/v1/systemone`, câu hỏi `Choice`, `criteria` = {mã loại: mô tả} |
| LLM chính | **`qwen3.5:4b`** (Ollama, 4.7B tham số, Q4_K_M) | `/api/chat`, `format` = JSON schema (enum mã loại), `temperature=0`, `seed=0`, `think=false`, `logprobs=true` |
| LLM nhỏ hơn | **`qwen2.5:3b`** (Ollama) | như trên |
| Embedding | **`bge-m3`** (Ollama, 1024 chiều, F16) | `/api/embed`, vector L2-chuẩn hóa |

**Kev kích thước khác (4B) - KHÔNG chạy.** `/api/predict` của server có tham số `model_name` và *thay mô hình toàn cục của server* (dùng chung cho mọi người; còn `/v1/systemone` luôn nạp lại 0.8B theo mã `demo_app.py`).
Tôi không xác nhận được trọng số `kev-4b` + nền `Qwen3.5-4B-Base` có đủ trong cache cục bộ (các tệp trong cache HF là liên kết tượng trưng, không đọc được kích thước), nên thử sẽ (i) đổi mô hình của máy chủ thử nghiệm của người dùng, (ii) có thể kích hoạt tải ~8 GB và cần ~8.4 GB VRAM
trong khi GPU 12 GB đang dùng chung (~6-7 GB bận). Tôi **không thử**. Mọi số "Kev" ở đây là **Kev-0.8B**.

**Giới hạn của Kev về số lượng/độ dài tiêu chí** (đo và đọc mã `Z:\projects\kev\kev\model.py`): server chặn *trạng thái* (văn bản) > 65 536 token và một hàng câu hỏi > 73 728 token (HTTP 422); ta không chạm giới hạn cứng nào
(35 tiêu chí mô tả ngắn ≈ 1.8-2.3k token; mô tả dài ≈ 10k token cho cả bài). Nhưng **chất lượng sụp ở mô tả dài** (mục 5), nên giới hạn thực tế là chất lượng, không phải kích thước. Cách xử lý: dùng mô tả ngắn hoặc chỉ tên loại, và thử chế độ **hai bước** (8 nhóm -> loại trong nhóm).
Server Kev xử lý tuần tự trong một luồng sự kiện: yêu cầu song song không nhanh hơn và làm chậm mọi người dùng (kể cả `/api/status`; quan sát: độ trễ treo tường 15-64 s dù thời gian mô hình 0.35 s khi ba tiến trình cùng gọi).

**Prompt.** Văn bản = `n` ký tự đầu (mặc định 2000) của văn bản trang 1-2 sau khi gộp khoảng trắng. Danh sách loại = 35 mã trong taxonomy trừ `UNREADABLE`; mô tả `short` = `short_description` (113 ký tự trung bình), `long` = `description` + `deciding_cue` (860 ký tự trung bình),
`name` = `name_vi` (chỉ tên, để thử độ phụ thuộc vào mô tả). `OTHER` là câu trả lời hợp lệ và **không bao giờ được tự xếp hồ sơ**; tài liệu < 25 ký tự văn bản chuyển thẳng cho người (không gọi mô hình). Với Ollama, danh sách loại đứng *trước* văn bản để tái dùng KV-cache;
ví dụ in-context (nếu có) chỉ lấy từ tài liệu của các fold huấn luyện. **Độ tin cậy:** Kev = xác suất của tiêu chí được chọn trong `probabilities`; Ollama = tích xác suất (logprob) của các token tạo nên mã loại (trước khi chuẩn hóa trên enum); hai bước = p(nhóm) x p(loại | nhóm).
Cache: mọi lời gọi lưu ở `_cache/` (khóa = mô hình + yêu cầu đầy đủ, kèm độ trễ đo ở lần gọi thật; git-ignored) nên chạy lại tất định và miễn phí. **Độ trễ trong bảng E2/E3 là độ trễ treo tường lúc chạy lưới khi GPU/CPU bận bởi nhiều tiến trình** (có lúc Ollama đứng hàng phút) -
chỉ dùng so sánh thô; số dùng cho bảng chi phí lấy từ lượt đo riêng khi máy rảnh (`--stage latency`, mục 9).

**Quan trọng - vòng tròn nhãn/mô tả.** `docs/LABELING_GUIDELINE.md` v1.1 ghi nhận phản hồi của người gán nhãn; `taxonomy_v2.json` (mô tả, `deciding_cue`, từ khóa) được viết/chỉnh *sau khi xem các tài liệu mẫu này*; nhãn do mô hình gán theo hướng dẫn đó.
Một LLM đọc *cùng các mô tả* có thể đạt điểm cao đơn giản vì **tái tạo cách gán nhãn bằng mô hình**. Cổng luật có cùng vấn đề (từ khóa viết sau khi xem tài liệu). Biện pháp giảm nhẹ trong thí nghiệm: (i) biến thể **chỉ-tên-loại** (không mô tả);
(ii) ablation **bỏ cổng luật**; (iii) nguồn OCR chất lượng thấp; (iv) ghi rõ ở mục 10 rằng khả năng tổng quát hóa sang loại mới / khách hàng mới **chưa được chứng minh**.

## 4. E1 - Embedding bge-m3 (LR, tâm lớp, kNN; Track S và Track Z few-shot)

Cấu hình thử (12 cho Track S): độ dài đầu vào {512, 2000} ký tự x {LR C=1/10/100, tâm lớp, 1-NN, 3-NN}, mỗi nguồn; chọn theo macro-F1 DEV (trung bình 3 seed x 5 fold). Track Z few-shot: mỗi loại có >= 2 tài liệu huấn luyện có một tâm (loại ít hơn không thể được dự đoán).

<!-- BEGIN:c_e1 -->
**Track S** (10 lớp + `RARE_OR_OTHER`; chọn 1 trong 12 cấu hình embedding theo macro-F1 DEV):

| nguồn | phương pháp (Track S, 11 lớp) | DEV macro-F1 (15 điểm) | TEST macro-F1 [CI] | đối chiếu TF-IDF (01): DEV |
|---|---|---|---|---|
| ocr_v2_p12 | bge-m3 2000 ký tự + lr_C100 | 0.955 ± 0.046 | 1.000 [1.000; 1.000] | 0.977 ± 0.019 |
| haiku_p12 | bge-m3 2000 ký tự + lr_C100 | 0.961 ± 0.048 | 0.987 [0.954; 1.000] | 0.976 ± 0.018 |
| legacy_p1 | bge-m3 2000 ký tự + lr_C100 | 0.925 ± 0.068 | 0.831 [0.733; 0.887] | 0.960 ± 0.026 |

**Track Z** (20 loại có >= 3 tài liệu được chấm ở DEV, 10 ở TEST; 92% tài liệu DEV có loại thật với >= 2 mẫu ở các fold huấn luyện = "với tới được"):

| nguồn | phương pháp (Track Z, 34 loại) | DEV macro-F1 [CI] | DEV accuracy | DEV recall loại hiếm | DEV recall loại thường | TEST macro-F1 [CI] | TEST recall loại hiếm |
|---|---|---|---|---|---|---|---|
| ocr_v2_p12 | few-shot: tâm lớp, >= 2 mẫu/loại (out-of-fold) | 0.894 [0.710; 0.937] | 0.895 | 0.667 | 0.977 | 0.913 [0.708; 0.978] | 0.55 |
| ocr_v2_p12 | zero-shot: so khớp mô tả loại (không mẫu) | 0.639 [0.551; 0.715] | 0.671 | 0.762 | 0.638 |  |  |
| haiku_p12 | few-shot: tâm lớp, >= 2 mẫu/loại (out-of-fold) | 0.911 [0.716; 0.948] | 0.899 | 0.698 | 0.971 | 0.910 [0.706; 0.977] | 0.55 |
| haiku_p12 | zero-shot: so khớp mô tả loại (không mẫu) | 0.610 [0.517; 0.680] | 0.612 | 0.778 | 0.552 |  |  |
| legacy_p1 | few-shot: tâm lớp, >= 2 mẫu/loại (out-of-fold) | 0.809 [0.646; 0.872] | 0.857 | 0.571 | 0.960 | 0.794 [0.611; 0.951] | 0.55 |
| legacy_p1 | zero-shot: so khớp mô tả loại (không mẫu) | 0.114 [0.074; 0.178] | 0.181 | 0.190 | 0.178 |  |  |
<!-- END:c_e1 -->

**Đọc kết quả.**
- Đã đo: trên 10 lớp + gộp, embedding + LR (0.955 DEV, `ocr_v2_p12`) **không vượt** TF-IDF (0.977); chênh 0.02 nằm trong độ lệch chuẩn giữa fold (0.02-0.05), và trên TEST (1.000 [1.000; 1.000] so với 0.946 [0.847; 1.000]) bị mẫu 59 làm nhiễu theo chiều ngược lại - **không xếp hạng được**. Văn bản dài hơn (2000 so với 512 ký tự) thường tốt hơn (+0.005 đến +0.05).
- Đã đo: **few-shot trên toàn taxonomy** (tâm lớp, >= 2 mẫu) cho macro-F1 Track Z DEV 0.894 [0.710; 0.937], TEST 0.913 [0.708; 0.978]; recall loại thường 0.98 nhưng **recall loại hiếm chỉ 0.67 (DEV) / 0.55 (6/11, TEST)**: loại chỉ có 1-2 mẫu không có tâm hoặc tâm nhiễu. Zero-shot bằng cách so khớp embedding của mô tả loại kém hơn (0.64) nhưng recall loại hiếm 0.76 (không cần mẫu).
- CI rộng vì chỉ ~20 loại và mỗi loại 1-7 tài liệu; "với tới được" 92% tài liệu DEV (8% là loại có < 2 mẫu ở các fold huấn luyện).
- Embedding chạy 73 ms (trung vị, bge-m3 qua Ollama, 0.63 GB VRAM). Kết luận: embedding là phương án **few-shot rẻ** cho loại mới *khi đã có >= 2 mẫu*, không thay được LLM zero-shot cho loại chưa có mẫu.

## 5. E2 - Zero-shot toàn taxonomy: Kev, Qwen, và so khớp embedding

DEV (237 tài liệu, nguồn `ocr_v2_p12`, 35 nhãn khả dĩ gồm cả `OTHER`). `*` độ trễ treo tường lúc chạy lưới, khi máy bận (xem mục 3); số đo lúc rảnh ở mục 9.

<!-- BEGIN:c_e2_dev -->
| phương pháp | accuracy | macro-F1 [CI 95%] | recall loại hiếm (63) | recall loại thường | lỗi cú pháp | độ trễ trung vị (ms)* |
|---|---|---|---|---|---|---|
| Kev-0.8B, mô tả ngắn, 1 bước | 0.781 | 0.824 [0.761; 0.861] | 0.95 | 0.72 | 0.000 | 1087 |
| Kev-0.8B, mô tả ngắn, 2 bước | 0.848 | 0.906 [0.824; 0.927] | 0.94 | 0.82 | 0.000 | 1016 |
| Kev-0.8B, mô tả DÀI, 1 bước | 0.300 | 0.138 [0.119; 0.208] | 0.14 | 0.36 | 0.000 | 4681 |
| Kev-0.8B, mô tả DÀI, 2 bước | 0.397 | 0.281 [0.228; 0.363] | 0.35 | 0.41 | 0.000 | 1903 |
| Kev-0.8B, mô tả ngắn, 800 ký tự | 0.738 | 0.777 [0.687; 0.816] | 0.86 | 0.70 | 0.000 | 1365 |
| Kev-0.8B, mô tả ngắn, 2 bước, 800 ký tự | 0.772 | 0.822 [0.716; 0.883] | 0.83 | 0.75 | 0.000 | 1943 |
| Kev-0.8B, chỉ TÊN loại, 1 bước | 0.962 | 0.963 [0.905; 0.988] | 0.90 | 0.98 | 0.000 | 839 |
| Kev-0.8B, chỉ TÊN loại, 2 bước | 0.932 | 0.953 [0.886; 0.977] | 0.92 | 0.94 | 0.000 | 1384 |
| Kev-0.8B, chỉ TÊN loại, 800 ký tự | 0.920 | 0.927 [0.861; 0.972] | 0.90 | 0.93 | 0.000 | 747 |
| Qwen3.5-4B, mô tả ngắn, 1 bước | 0.996 | 0.990 [0.968; 1.000] | 0.98 | 1.00 | 0.000 | 1374 |
| Qwen3.5-4B, mô tả DÀI, 1 bước | 0.992 | 0.987 [0.964; 1.000] | 0.98 | 0.99 | 0.000 | 1619 |
| Qwen3.5-4B, mô tả ngắn, 2 bước | 0.979 | 0.955 [0.910; 0.999] | 0.94 | 0.99 | 0.000 | 2927 |
| Qwen3.5-4B, mô tả ngắn + 1 ví dụ/loại | 0.979 | 0.967 [0.912; 1.000] | 0.94 | 0.99 | 0.000 | 1562 |
| Qwen3.5-4B, chỉ TÊN loại | 0.970 | 0.957 [0.889; 0.995] | 0.90 | 0.99 | 0.000 | 719 |
| Qwen3.5-4B, mô tả ngắn, 800 ký tự | 0.992 | 0.989 [0.967; 1.000] | 0.98 | 0.99 | 0.000 | 796 |
| Qwen2.5-3B, mô tả ngắn, 1 bước | 0.764 | 0.750 [0.652; 0.832] | 0.59 | 0.83 | 0.000 | 766 |
| bge-m3 so khớp mô tả (không mẫu) | 0.671 | 0.639 [0.551; 0.715] | 0.76 | 0.64 |  | 73 |
| bge-m3 few-shot (>= 2 mẫu/loại, out-of-fold) | 0.895 | 0.894 [0.710; 0.937] | 0.67 | 0.98 |  | 73 |
| đối chiếu: TF-IDF (01) quy về Track Z, RARE_OR_OTHER = abstain | 0.646 | 0.437 [0.379; 0.538] | 0.00 |  |  | 3 |
<!-- END:c_e2_dev -->

Cùng cấu hình tốt nhất trên ba nguồn văn bản (DEV chọn, TEST chấm một lần cho những cấu hình có trong cascade):

<!-- BEGIN:c_e2_src -->
| phương pháp | ocr_v2_p12 DEV acc / macro-F1 | ocr_v2_p12 TEST acc [CI] / macro-F1 | haiku_p12 DEV acc / macro-F1 | haiku_p12 TEST acc [CI] / macro-F1 | legacy_p1 DEV acc / macro-F1 | legacy_p1 TEST acc [CI] / macro-F1 |
|---|---|---|---|---|---|---|
| Kev-0.8B, chỉ TÊN loại, 1 bước | 0.962 / 0.963 | 0.932 [0.864; 0.983] / 0.991 | 0.970 / 0.954 | 0.966 [0.915; 1.000] / 0.992 | 0.498 / 0.463 | 0.458 [0.339; 0.576] / 0.553 |
| Kev-0.8B, mô tả ngắn, 2 bước | 0.848 / 0.906 | 0.797 [0.695; 0.898] / 0.856 | 0.840 / 0.886 | 0.797 [0.695; 0.898] / 0.835 | 0.523 / 0.463 | 0.475 [0.356; 0.593] / 0.618 |
| Qwen3.5-4B, mô tả ngắn, 1 bước | 0.996 / 0.990 | 0.983 [0.949; 1.000] / 1.000 | 1.000 / 1.000 | 1.000 [1.000; 1.000] / 1.000 | 0.945 / 0.933 | 0.915 [0.831; 0.983] / 0.952 |
| Qwen3.5-4B, mô tả ngắn, 2 bước | 0.979 / 0.955 | 1.000 [1.000; 1.000] / 1.000 | 0.987 / 0.969 | 1.000 [1.000; 1.000] / 1.000 | 0.861 / 0.839 | 0.847 [0.763; 0.932] / 0.865 |
| Qwen2.5-3B, mô tả ngắn, 1 bước | 0.764 / 0.750 | 0.797 [0.695; 0.898] / 0.867 | 0.827 / 0.846 | 0.814 [0.712; 0.898] / 0.856 | 0.565 / 0.583 | 0.458 [0.322; 0.576] / 0.624 |
<!-- END:c_e2_src -->

Recall từng **loại hiếm** (DEV, `ocr_v2_p12`; mỗi loại 1-7 tài liệu - *mang tính giai thoại*, không rút kết luận theo từng loại):

<!-- BEGIN:c_e2_rare -->
| loại hiếm | n (DEV) | Kev-0.8B tên | Qwen3.5 1 bước | Qwen3.5 2 bước | Qwen2.5-3B | TF-IDF (01) | bge few-shot | bge mô tả |
|---|---|---|---|---|---|---|---|---|
| HD_MUON_BON | 7 | 1.00 | 1.00 | 1.00 | 0.86 | 0.00 | 1.00 | 1.00 |
| HO_SO_QUAN_LY_PCCC | 7 | 0.57 | 1.00 | 0.86 | 0.14 | 0.00 | 1.00 | 1.00 |
| GCN_BAO_HIEM | 7 | 1.00 | 1.00 | 1.00 | 0.43 | 0.00 | 0.71 | 1.00 |
| CC_NGHIEP_VU_BVMT | 5 | 0.80 | 1.00 | 1.00 | 1.00 | 0.00 | 1.00 | 0.80 |
| GPLX | 4 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 |
| HD_NHUONG_QUYEN_DAI_LY | 5 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 | 1.00 | 0.20 |
| BAN_VE_KY_THUAT | 3 | 0.67 | 0.67 | 0.33 | 0.00 | 0.00 | 1.00 | 0.00 |
| CC_HUAN_LUYEN_PCCC | 3 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 | 0.33 | 1.00 |
| DANG_KY_PHUONG_TIEN | 3 | 1.00 | 1.00 | 1.00 | 0.33 | 0.00 | 1.00 | 0.67 |
| GCN_PCCC_CO_SO | 1 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 | 1.00 |
| GIAY_UY_QUYEN | 3 | 1.00 | 1.00 | 1.00 | 0.33 | 0.00 | 0.67 | 0.33 |
| BIEN_NHAN_THE_CHAP_PT | 2 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 | 1.00 |
| CONG_VAN_THONG_BAO | 2 | 1.00 | 1.00 | 1.00 | 0.50 | 0.00 | 0.00 | 0.00 |
| GCN_KIEM_DINH_DO_LUONG | 1 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 | 1.00 |
| GP_VC_HANG_NGUY_HIEM | 2 | 0.50 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | 1.00 |
| GXN_THUONG_NHAN_XD | 2 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | 1.00 |
| BIEN_PHAP_UNG_PHO_SU_CO | 1 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 | 1.00 |
| CCCD | 1 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 | 1.00 |
| GCN_ATKT_BVMT_PT | 1 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| GIAY_PHEP_XAY_DUNG | 1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | 1.00 |
| HOA_DON | 1 | 1.00 | 1.00 | 1.00 | 1.00 | 0.00 | 0.00 | 1.00 |
| OTHER | 1 | 1.00 | 1.00 | 0.00 | 1.00 | 0.00 | 0.00 | 0.00 |
| **tổng (63 tài liệu)** | 63 | 0.90 | 0.98 | 0.94 | 0.59 | 0.00 | 0.67 | 0.76 |
<!-- END:c_e2_rare -->

**Đọc kết quả.**
- Đã đo - **Qwen3.5-4B** là mô hình duy nhất vừa chính xác vừa ổn định: accuracy 0.996 (1 lỗi / 237) với mô tả ngắn, 0.992 với mô tả dài, 0.992 chỉ với 800 ký tự đầu (nhanh hơn). **Biến thể hai bước và ví dụ in-context không giúp** (0.979); chỉ-tên-loại vẫn 0.970.
  Recall loại hiếm 62/63 (DEV), 10/11 (TEST) - lỗi duy nhất ở DEV là một "bản vẽ kỹ thuật" bị gọi `OTHER`. Trên Haiku 237/237 đúng. Qwen2.5-3B yếu hơn nhiều (0.76; hay nhầm GCN_DKDN -> GCN_DDK_BAN_LE_XD).
- Đã đo - **Kev-0.8B**: mô tả ngắn 0.78 (1 bước) / 0.85 (2 bước), lỗi có hệ thống (GCN_DDK_BAN_LE_XD -> GXN_THUONG_NHAN_XD 21/21, DON_DAT_HANG -> HD_MUA_BAN 16/16); **mô tả dài làm hỏng Kev** (0.30 / 0.40 - khác hẳn Qwen, cùng mô tả);
  còn **chỉ tên loại** cho 0.962 (macro-F1 0.963 [0.905; 0.988]) - tốt nhất của Kev, hơn Qwen2.5 và gần Qwen3.5 mà chỉ cần 1.6 GB VRAM. 800 ký tự đầu kém hơn 2000 ký tự (0.920 so với 0.962 với tên loại).
  **Suy luận:** đầu "pointer" của Kev được huấn luyện với tiêu chí ngắn (nhãn/cụm từ); mô tả dài ~10k token nằm ngoài phân bố huấn luyện. Quy tắc thực hành: *với Kev, viết tiêu chí thật ngắn*.
- Đã đo - **TF-IDF (01) không bao giờ nhận loại hiếm** (recall 0): quy về Track Z nó đạt macro-F1 0.437 vì mọi loại hiếm là abstain. Kev (mô tả ngắn) nhận 0.95 loại hiếm nhưng nhầm 28% loại thường: **hai nhóm lỗi bù nhau**, lý do để dùng cascade.
- Đã đo - **phụ thuộc OCR**: trên `legacy_p1` Qwen3.5 còn 0.945 (DEV) / 0.915 (TEST) còn Kev (tên) rơi xuống 0.50 / 0.46 và Qwen2.5 0.57. Trên Haiku Kev (tên) 0.97.
- Đã đo - **chẩn đoán vòng tròn**: bỏ hẳn mô tả (chỉ tên loại) Qwen3.5 vẫn 0.970 và Kev 0.962 - phần lớn hiệu năng **không** phụ thuộc vào mô tả được viết sau khi xem tài liệu. Điều này giảm nhưng không loại trừ rủi ro nhãn do mô hình gán theo cùng taxonomy.
- Lỗi cú pháp (JSON hỏng / nhãn ngoài danh sách) = 0.000 ở mọi cấu hình trên `ocr_v2_p12` (JSON schema ràng buộc ép đúng enum); 1.3% trên `legacy_p1` là 3 tài liệu OCR cũ gần như rỗng (< 25 ký tự) bị chuyển cho người theo thiết kế.

## 6. E3 - Mô hình có biết khi nào nó không biết?

Với mỗi phương pháp: confidence của nhãn dự đoán -> **ECE** (10 bin), **AUROC** (confidence phân biệt dự đoán đúng/sai), **AURC** (diện tích dưới đường risk-coverage, thấp = tốt) và **auto-file rate** tại ngưỡng chọn *trên chính DEV* sao cho sai <= 1% / 2%
(nhãn `OTHER`, `RARE_OR_OTHER` không bao giờ được tự nhận). Đường risk-coverage: `figs/risk_coverage_zs_ocr_v2_p12.png` (và hai nguồn còn lại).

<!-- BEGIN:c_e3 -->
| phương pháp (DEV, ocr_v2_p12) | accuracy | ECE | AUROC (đúng/sai) | AURC (thấp = tốt) | auto-file@<=1% | auto-file@<=2% |
|---|---|---|---|---|---|---|
| Kev-0.8B, chỉ TÊN loại, 1 bước | 0.962 | 0.441 | 0.961 | 0.002 | 0.949 (2 sai/225) | 0.962 |
| Kev-0.8B, chỉ TÊN loại, 2 bước | 0.932 | 0.517 | 0.976 | 0.004 | 0.937 (2 sai/222) | 0.945 |
| Kev-0.8B, mô tả ngắn, 1 bước | 0.781 | 0.384 | 0.793 | 0.086 | 0.110 (0 sai/26) | 0.257 |
| Qwen3.5-4B, mô tả ngắn, 1 bước | 0.996 | 0.114 | 0.750 | 0.001 | 0.992 (0 sai/235) | 0.992 |
| Qwen3.5-4B, mô tả ngắn, 2 bước | 0.979 | 0.081 | 0.978 | 0.001 | 0.987 (2 sai/234) | 0.996 |
| Qwen3.5-4B, chỉ TÊN loại | 0.970 | 0.092 | 0.734 | 0.010 | 0.726 (1 sai/172) | 0.764 |
| Qwen2.5-3B, mô tả ngắn, 1 bước | 0.764 | 0.172 | 0.790 | 0.134 | 0.624 (1 sai/148) | 0.675 |
| TF-IDF (01), Track S -> Z | 0.734 | 0.175 | 0.856 | 0.103 | 0.650 (1 sai/154) | 0.738 |
| bge-m3 few-shot | 0.895 | 0.214 | 0.959 | 0.010 | 0.776 (1 sai/184) | 0.861 |
| bge-m3 so khớp mô tả | 0.671 | 0.394 | 0.731 | 0.168 | 0.135 (0 sai/32) | 0.135 |
| cổng luật (không có confidence) | 0.764 |  |  |  | 0.764 (0 sai/181) | 0.764 |
<!-- END:c_e3 -->

Đồng thuận (không ngưỡng): chấp nhận một tài liệu khi **mọi** nguồn trong tổ hợp cùng dự đoán một nhãn (và nhãn đó không phải `OTHER`/`RARE_OR_OTHER`). Các tổ hợp được định sẵn ở DEV, áp nguyên lên TEST. "Cận trên sai 95%" là Clopper-Pearson (bootstrap cho CI [0;0] khi 0 lỗi nên không dùng).
`kev` = Kev-0.8B tên-loại 1 bước, `q35` = Qwen3.5-4B mô tả ngắn 1 bước, `emb` = bge-m3 few-shot, `tfidf` = TF-IDF (không tính RARE_OR_OTHER), `rule` = cổng luật.

<!-- BEGIN:c_e3_agree -->
| nguồn | đồng thuận của | DEV nhận | DEV sai | DEV cận trên sai 95% | TEST nhận | TEST sai | TEST cận trên sai 95% |
|---|---|---|---|---|---|---|---|
| ocr_v2_p12 | rule+tfidf | 131/237 (0.553) | 0 | 0.023 | 40/59 (0.678) | 0 | 0.072 |
| ocr_v2_p12 | tfidf+kev | 171/237 (0.722) | 0 | 0.017 | 45/59 (0.763) | 0 | 0.064 |
| ocr_v2_p12 | tfidf+q35 | 174/237 (0.734) | 0 | 0.017 | 46/59 (0.780) | 0 | 0.063 |
| ocr_v2_p12 | kev+q35 | 227/237 (0.958) | 0 | 0.013 | 56/59 (0.949) | 1 | 0.082 |
| ocr_v2_p12 | kev+q35+tfidf | 171/237 (0.722) | 0 | 0.017 | 45/59 (0.763) | 0 | 0.064 |
| ocr_v2_p12 | tfidf+emb | 175/237 (0.738) | 5 | 0.059 | 45/59 (0.763) | 1 | 0.101 |
| ocr_v2_p12 | kev+emb | 205/237 (0.865) | 0 | 0.015 | 49/59 (0.831) | 0 | 0.059 |
| ocr_v2_p12 | q35+emb | 211/237 (0.890) | 0 | 0.014 | 50/59 (0.847) | 0 | 0.058 |
| ocr_v2_p12 | rule+kev | 176/237 (0.743) | 0 | 0.017 | 47/59 (0.797) | 0 | 0.062 |
| ocr_v2_p12 | rule+q35 | 181/237 (0.764) | 0 | 0.016 | 50/59 (0.847) | 0 | 0.058 |
| ocr_v2_p12 | tfidf+kev+emb | 168/237 (0.709) | 0 | 0.018 | 43/59 (0.729) | 0 | 0.067 |
| ocr_v2_p12 | tfidf+q35+emb | 170/237 (0.717) | 0 | 0.017 | 44/59 (0.746) | 0 | 0.066 |
| legacy_p1 | rule+tfidf | 136/237 (0.574) | 0 | 0.022 | 39/59 (0.661) | 0 | 0.074 |
| legacy_p1 | tfidf+kev | 95/237 (0.401) | 0 | 0.031 | 23/59 (0.390) | 0 | 0.122 |
| legacy_p1 | tfidf+q35 | 168/237 (0.709) | 0 | 0.018 | 43/59 (0.729) | 0 | 0.067 |
| legacy_p1 | kev+q35 | 117/237 (0.494) | 0 | 0.025 | 26/59 (0.441) | 0 | 0.109 |
| legacy_p1 | kev+q35+tfidf | 95/237 (0.401) | 0 | 0.031 | 22/59 (0.373) | 0 | 0.127 |
| legacy_p1 | tfidf+emb | 169/237 (0.713) | 4 | 0.053 | 41/59 (0.695) | 1 | 0.111 |
| legacy_p1 | kev+emb | 106/237 (0.447) | 1 | 0.044 | 25/59 (0.424) | 1 | 0.176 |
| legacy_p1 | q35+emb | 194/237 (0.819) | 0 | 0.015 | 43/59 (0.729) | 0 | 0.067 |
| legacy_p1 | rule+kev | 86/237 (0.363) | 0 | 0.034 | 23/59 (0.390) | 0 | 0.122 |
| legacy_p1 | rule+q35 | 185/237 (0.781) | 0 | 0.016 | 48/59 (0.814) | 0 | 0.061 |
| legacy_p1 | tfidf+kev+emb | 92/237 (0.388) | 0 | 0.032 | 21/59 (0.356) | 0 | 0.133 |
| legacy_p1 | tfidf+q35+emb | 162/237 (0.684) | 0 | 0.018 | 38/59 (0.644) | 0 | 0.076 |
<!-- END:c_e3_agree -->

**Đọc kết quả.**
- Đã đo - **Kev** có confidence *xếp hạng tốt* (AUROC 0.961; auto-file 94.9% với sai <= 1% trên DEV, hơn hẳn TF-IDF 65%) nhưng **rất thiếu tự tin về giá trị tuyệt đối** (ECE 0.44: xác suất rải đều trên 35 lựa chọn) - dùng ngưỡng theo thứ hạng, **đừng đọc nó như xác suất**.
  Mô tả ngắn làm confidence của Kev kém hẳn (AUROC 0.79; auto-file 11%) - cùng điều làm accuracy kém.
- Đã đo - **Qwen3.5**: ECE 0.08-0.11 (khá), nhưng AUROC của xác suất logprob *một bước* chỉ 0.75 và không có ý nghĩa thống kê (chỉ 1 lỗi để xếp hạng); **hai bước** (p(nhóm) x p(loại|nhóm)) cho AUROC 0.978 với 5 lỗi - tín hiệu có thông tin hơn.
  Ở `legacy_p1` (nhiều lỗi hơn) AUROC của một bước vẫn chỉ 0.77. Kết luận: *đừng dựa vào logprob một bước của Qwen làm ngưỡng từ chối*; dùng hai bước hoặc đồng thuận.
- Đã đo - **Đồng thuận là cách từ chối mạnh nhất**: Kev + Qwen cùng một nhãn trên 95.8% tài liệu DEV với **0 lỗi** (cận trên 1.3%), TEST 94.9% với 1 lỗi (cận trên 8.2%). Đồng thuận TF-IDF + embedding (cả hai là mô hình có giám sát) cho 5 lỗi / 175 (2.9%) - hai mô hình cùng nguồn dữ liệu mắc cùng lỗi (loại hiếm bị ép vào loại thường).
  **Hai mô hình khác họ đồng thuận thì đáng tin; hai mô hình cùng huấn luyện trên một dữ liệu thì không.** Trên `legacy_p1` đồng thuận Kev+Qwen chỉ nhận 49% (Kev kém) - tự giảm phạm vi thay vì tăng lỗi: đúng hành vi mong muốn.
- Giới hạn: số lỗi để đánh giá calibration rất ít (Qwen: 1-5 lỗi trên 237), nên AUROC/ECE của Qwen không đủ chắc chắn.

## 7. E4 - Cascade có từ chối, đánh giá đầu-cuối trên toàn taxonomy

**Thiết kế** (`src/classification/cascade.py`, có test). Tài liệu đi lần lượt qua các tầng; tầng đầu đủ tự tin nhận nó:
1. **Cổng luật** từ khóa tiêu đề (`CascadedClassifier` với Kev tắt, ~3.5 ms): nhận khi một lớp duy nhất khớp.
2. **TF-IDF** (Track S; cấu hình xếp hạng 1 theo DEV của 01 cho nguồn đó): nhận khi dự đoán *không* phải `RARE_OR_OTHER` và confidence >= `th_s`.
3. **LLM/embedding** (tầng-3): nhận khi nhãn không thuộc `OTHER`/không trả lời và (confidence >= `th_llm` **hoặc** đồng thuận với TF-IDF / embedding theo chế độ `agree` chọn trên DEV).
4. **Người**: phần còn lại. Tài liệu < 25 ký tự: thẳng cho người.

Ngưỡng `th_s`, `th_llm`, chế độ `agree` được chọn **chỉ trên dự đoán out-of-fold của DEV** (TF-IDF và embedding few-shot dự đoán out-of-fold seed 0; LLM zero-shot dự đoán trực tiếp) sao cho phần được nhận có sai <= 1% (hoặc 2%) và coverage lớn nhất (hòa -> ngưỡng cao hơn). Với TEST: huấn luyện lại TF-IDF/embedding trên toàn DEV, áp nguyên ngưỡng.
Tầng-3 "chính" (cho ablation và so sánh) chọn *một lần* theo macro-F1 DEV đứng một mình (E2) trên nguồn triển khai: **Qwen3.5-4B, mô tả ngắn, 1 bước** (không theo kết quả cascade, vì các ứng viên hòa nhau). Mọi ứng viên khác cũng được chấm TEST (mỗi cấu hình đúng một lần, không chọn lại).
`tfidf_only(classical)` = baseline cổ điển tốt nhất + ngưỡng, **được chỉnh lại trên nhãn Track Z** (nên 64.4% ở đây khác 61.0% của 01, cùng một mô hình). Các cột `%` là tỉ lệ tài liệu được từng tầng quyết định. `*` = ước tính độ trễ trung bình/tài liệu dùng trung vị đo lúc rảnh (mục 9); để trống với biến thể 2 bước (không đo).

**DEV** (ocr_v2_p12; ngưỡng chọn ngay trên DEV nên cột "tự nhận" là *lạc quan*; cột cross-fit chọn ngưỡng trên 4 fold, áp lên fold thứ 5 - trung thực hơn):

<!-- BEGIN:c_e4_dev -->
| cấu hình | tự nhận (k/n) | CP 95% | sai | cận trên sai 95% | macro-F1 | luật % | TF-IDF % | LLM/emb % | người % | ms/tài liệu (rảnh)* | cross-fit tự nhận (sai) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| đầy đủ [tầng-3 = kev_s1_name_c2000] | 233/237 = 0.983 | [0.957; 0.995] | 2 | 0.027 | 0.980 | 76 | 18 | 4 | 2 | 51 | 0.966 (0) |
| đầy đủ [tầng-3 = q35_s1_short_c2000] | 236/237 = 0.996 | [0.977; 1.000] | 1 | 0.020 | 0.989 | 76 | 18 | 5 | 0 | 70 | 0.983 (0) |
| đầy đủ [tầng-3 = q25_s1_short_c2000] | 229/237 = 0.966 | [0.935; 0.985] | 2 | 0.027 | 0.935 | 76 | 18 | 2 | 3 | 47 | 0.949 (0) |
| đầy đủ [tầng-3 = q35_s2_short_c2000] | 236/237 = 0.996 | [0.977; 1.000] | 2 | 0.026 | 0.967 | 76 | 16 | 7 | 0 |  | 0.983 (1) |
| đầy đủ [tầng-3 = kev_s2_short_c2000] | 236/237 = 0.996 | [0.977; 1.000] | 1 | 0.020 | 0.989 | 76 | 18 | 5 | 0 |  | 0.987 (1) |
| đầy đủ [tầng-3 = embfs] | 231/237 = 0.975 | [0.946; 0.991] | 2 | 0.027 | 0.988 | 76 | 4 | 17 | 3 | 19 | 0.970 (2) |
| no_rule | 235/237 = 0.992 | [0.970; 0.999] | 0 | 0.013 | 0.990 | 0 | 0 | 99 | 1 | 1196 | 0.979 (0) |
| no_tfidf | 235/237 = 0.992 | [0.970; 0.999] | 0 | 0.013 | 0.990 | 76 | 0 | 23 | 1 | 285 | 0.983 (0) |
| no_llm(rule+tfidf) | 226/237 = 0.954 | [0.918; 0.977] | 2 | 0.028 | 0.934 | 76 | 19 | 0 | 5 | 4 | 0.949 (1) |
| llm_only | 235/237 = 0.992 | [0.970; 0.999] | 0 | 0.013 | 0.990 | 0 | 0 | 99 | 1 | 1193 | 0.979 (0) |
| tfidf_only(classical) | 154/237 = 0.650 | [0.585; 0.710] | 1 | 0.030 | 0.437 | 0 | 65 | 0 | 35 | 3 | 0.675 (2) |
| rule_only | 181/237 = 0.764 | [0.704; 0.816] | 0 | 0.016 | 0.845 | 76 | 0 | 0 | 24 | 3 | 0.764 (0) |
<!-- END:c_e4_dev -->

**TEST** (ocr_v2_p12, mức sai <= 1%; n = 59; CP = Clopper-Pearson 95% của tỉ lệ tự nhận vì bootstrap suy biến [1;1] khi nhận hết):

<!-- BEGIN:c_e4_test -->
| cấu hình | tự nhận (k/n) | CP 95% | sai | cận trên sai 95% | macro-F1 | luật % | TF-IDF % | LLM/emb % | người % | ms/tài liệu (rảnh)* |
|---|---|---|---|---|---|---|---|---|---|---|
| đầy đủ [tầng-3 = kev_s1_name_c2000] | 59/59 = 1.000 | [0.939; 1.000] | 1 | 0.078 | 1.000 | 85 | 8 | 7 | 0 | 62 |
| đầy đủ [tầng-3 = q35_s1_short_c2000] | 59/59 = 1.000 | [0.939; 1.000] | 1 | 0.078 | 1.000 | 85 | 8 | 7 | 0 | 85 |
| đầy đủ [tầng-3 = q25_s1_short_c2000] | 57/59 = 0.966 | [0.883; 0.996] | 0 | 0.051 | 1.000 | 85 | 8 | 3 | 3 | 57 |
| đầy đủ [tầng-3 = q35_s2_short_c2000] | 59/59 = 1.000 | [0.939; 1.000] | 0 | 0.050 | 1.000 | 85 | 8 | 7 | 0 |  |
| đầy đủ [tầng-3 = kev_s2_short_c2000] | 58/59 = 0.983 | [0.909; 1.000] | 0 | 0.050 | 1.000 | 85 | 8 | 5 | 2 |  |
| đầy đủ [tầng-3 = embfs] | 57/59 = 0.966 | [0.883; 0.996] | 0 | 0.051 | 0.971 | 85 | 3 | 8 | 3 | 13 |
| no_rule | 58/59 = 0.983 | [0.909; 1.000] | 1 | 0.079 | 1.000 | 0 | 0 | 98 | 2 | 1196 |
| no_tfidf | 59/59 = 1.000 | [0.939; 1.000] | 1 | 0.078 | 1.000 | 85 | 0 | 15 | 0 | 185 |
| no_llm(rule+tfidf) | 57/59 = 0.966 | [0.883; 0.996] | 1 | 0.081 | 0.969 | 85 | 12 | 0 | 3 | 4 |
| llm_only | 58/59 = 0.983 | [0.909; 1.000] | 1 | 0.079 | 1.000 | 0 | 0 | 98 | 2 | 1193 |
| tfidf_only(classical) | 38/59 = 0.644 | [0.509; 0.764] | 0 | 0.076 | 0.772 | 0 | 64 | 0 | 36 | 3 |
| rule_only | 50/59 = 0.847 | [0.730; 0.928] | 0 | 0.058 | 0.863 | 85 | 0 | 0 | 15 | 3 |
<!-- END:c_e4_test -->

Mức sai <= 2% (TEST, ocr_v2_p12): cùng kết luận (xem `tables/e4_cascade_test.csv`); đáng chú ý là `no_rule` cho 3 lỗi / 58 (cận trên 12.8%) và `tfidf_only` 78.0% với 1 lỗi.

So sánh ghép cặp trên TEST với **mô hình cổ điển tốt nhất** (TF-IDF + ngưỡng, cùng nguồn, cùng mức sai 1%); Δ = cascade - cổ điển; bootstrap ghép cặp 2000 lần theo tài liệu. "Nhận ĐÚNG/SAI" = tỉ lệ tài liệu được tự nhận và đúng/sai:

<!-- BEGIN:c_e4_pair -->
| nguồn | cascade (tầng-3) | Δ tự nhận [CI] | Δ nhận ĐÚNG [CI] | Δ nhận SAI [CI] | Δ macro-F1 [CI] | p (macro-F1) |
|---|---|---|---|---|---|---|
| ocr_v2_p12 | kev_s1_name_c2000 | 0.356 [0.237; 0.475] | 0.339 [0.220; 0.458] | 0.017 [0.000; 0.051] | 0.228 [0.118; 0.448] | 0.000 |
| ocr_v2_p12 | q35_s1_short_c2000 | 0.356 [0.237; 0.475] | 0.339 [0.220; 0.458] | 0.017 [0.000; 0.051] | 0.228 [0.118; 0.448] | 0.000 |
| ocr_v2_p12 | q25_s1_short_c2000 | 0.322 [0.203; 0.441] | 0.322 [0.203; 0.441] | 0.000 [0.000; 0.000] | 0.228 [0.111; 0.444] | 0.000 |
| ocr_v2_p12 | q35_s2_short_c2000 | 0.356 [0.237; 0.475] | 0.356 [0.237; 0.475] | 0.000 [0.000; 0.000] | 0.228 [0.123; 0.463] | 0.000 |
| ocr_v2_p12 | kev_s2_short_c2000 | 0.339 [0.220; 0.458] | 0.339 [0.220; 0.458] | 0.000 [0.000; 0.000] | 0.228 [0.121; 0.451] | 0.000 |
| ocr_v2_p12 | embfs | 0.322 [0.203; 0.441] | 0.322 [0.203; 0.441] | 0.000 [0.000; 0.000] | 0.199 [0.097; 0.437] | 0.002 |
| haiku_p12 | kev_s1_name_c2000 | 0.356 [0.237; 0.475] | 0.339 [0.220; 0.458] | 0.017 [0.000; 0.051] | 0.228 [0.118; 0.448] | 0.000 |
| haiku_p12 | q35_s1_short_c2000 | 0.356 [0.237; 0.475] | 0.356 [0.237; 0.475] | 0.000 [0.000; 0.000] | 0.228 [0.123; 0.463] | 0.000 |
| haiku_p12 | q25_s1_short_c2000 | 0.339 [0.220; 0.458] | 0.339 [0.220; 0.458] | 0.000 [0.000; 0.000] | 0.228 [0.121; 0.451] | 0.000 |
| haiku_p12 | q35_s2_short_c2000 | 0.356 [0.237; 0.475] | 0.356 [0.237; 0.475] | 0.000 [0.000; 0.000] | 0.228 [0.123; 0.463] | 0.000 |
| haiku_p12 | kev_s2_short_c2000 | 0.356 [0.237; 0.475] | 0.339 [0.220; 0.458] | 0.017 [0.000; 0.051] | 0.228 [0.118; 0.448] | 0.000 |
| haiku_p12 | embfs | 0.356 [0.237; 0.475] | 0.356 [0.237; 0.475] | 0.000 [0.000; 0.000] | 0.228 [0.123; 0.463] | 0.000 |
| legacy_p1 | kev_s1_name_c2000 | 0.305 [0.203; 0.424] | 0.305 [0.203; 0.424] | 0.000 [0.000; 0.000] | 0.159 [0.056; 0.418] | 0.002 |
| legacy_p1 | q35_s1_short_c2000 | 0.305 [0.203; 0.424] | 0.305 [0.203; 0.424] | 0.000 [0.000; 0.000] | 0.159 [0.056; 0.418] | 0.002 |
| legacy_p1 | q25_s1_short_c2000 | 0.305 [0.203; 0.424] | 0.305 [0.203; 0.424] | 0.000 [0.000; 0.000] | 0.159 [0.056; 0.418] | 0.002 |
| legacy_p1 | q35_s2_short_c2000 | 0.339 [0.220; 0.458] | 0.305 [0.203; 0.424] | 0.034 [0.000; 0.085] | 0.151 [0.048; 0.411] | 0.006 |
| legacy_p1 | kev_s2_short_c2000 | 0.305 [0.203; 0.424] | 0.305 [0.203; 0.424] | 0.000 [0.000; 0.000] | 0.159 [0.056; 0.418] | 0.002 |
| legacy_p1 | embfs | 0.322 [0.203; 0.441] | 0.305 [0.186; 0.424] | 0.017 [0.000; 0.051] | 0.121 [0.027; 0.411] | 0.015 |
<!-- END:c_e4_pair -->

Hình tỉ lệ từng tầng: `figs/cascade_tier_shares_dev.png`, `figs/cascade_tier_shares_test.png`.

**Đọc kết quả.**
- Đã đo - **Cascade nâng tỉ lệ tự động xếp rất mạnh**: TEST 96.6-100% so với 64.4% [50.9; 76.4] của TF-IDF đơn; hiệu +0.356 [0.237; 0.475] (tách được; macro-F1 +0.228 [0.118; 0.448], p < 0.001). Mức tăng đến từ việc nhận được **loại hiếm** (TF-IDF luôn đưa cho người)
  và từ cổng luật (76-85% tài liệu). Phần "tự nhận đúng" tăng +0.339 [0.220; 0.458], phần "tự nhận sai" +0.017 [0.000; 0.051] (1 lỗi): **không tách được** về lỗi.
- Đã đo - **Tải cho người**: DEV 0-3.4% (cross-fit 1.3-5%), TEST 0-3.4%; so với 35% (DEV) / 36% (TEST) của baseline cổ điển. Trên `legacy_p1` (OCR cũ) vẫn chỉ 2-3% (TEST) nhờ cổng luật.
- Đã đo - **Tầng nào đóng góp gì** (DEV ocr_v2_p12): chỉ cổng luật nhận 76.4% (0 lỗi); luật + TF-IDF 95.4% (2 lỗi) nhưng recall loại hiếm chỉ 0.79 vì mọi loại hiếm nhận được đều nhờ luật; thêm LLM đưa lên 99.6% và recall loại hiếm 0.97. TF-IDF giữa luật và LLM *gần như thừa* khi đã có LLM tốt:
  `no_tfidf` (luật + LLM) cũng đạt 99.2% (0 lỗi) trên DEV và 100% (1 lỗi) trên TEST; giá trị của TF-IDF là *rẻ và nhanh* (2.7 ms) so với LLM (1.2 s).
- Đã đo - **Bỏ cổng luật** (ước lượng thận trọng hơn cho tài liệu lạ, vì từ khóa viết sau khi xem tài liệu): DEV cross-fit 97.9% (0 lỗi) với Qwen3.5; TEST 98.3% với 1 lỗi; `legacy_p1` 94.9% / 3 lỗi (DEV cross-fit), 2 lỗi / 57 (TEST).
  Tức là **trên văn bản OCR tốt, LLM (+ TF-IDF) một mình gần bằng cả cascade**; cổng luật mua thêm *tốc độ* (1.2 s -> 0.085 s/tài liệu) và độ bền với OCR kém.
- Đã đo - **Độ trễ/tài liệu** (cascade Qwen3.5 1 bước, ocr_v2_p12): ước tính 85 ms trung bình lúc rảnh (3.5 ms luật + 0.15 x 2.7 ms TF-IDF + 0.07 x 1.19 s LLM); đo trực tiếp khi chấm TEST: trung bình 54 ms, p95 649 ms. Bỏ luật: ~1.2 s/tài liệu. Chỉ-luật: 3.5 ms.
- **Không chứng minh được sai <= 1%.** Đã đo: TEST có 0-1 lỗi / 59 (cận trên 95% 5-8%). Ngưỡng chọn trên DEV *dễ dãi* đến mức tầng-3 nhận hầu như mọi thứ (người ~0%) - vì LLM sai 1/237 trên DEV nên không còn gì để tách. Hệ thống thật cần **biên an toàn** (giữ một tỉ lệ nhỏ cho người hoặc kiểm mẫu ngẫu nhiên), xem mục 10.
- Cẩn trọng - **suy luận**: con số 96-100% là ước lượng cho *cùng 10 + 24 loại, cùng công ty, cùng giai đoạn*, với cổng luật có khả năng lạc quan và nhãn chưa được người kiểm chứng. Đừng đọc nó như độ chính xác trên tài liệu của khách hàng mới.

## 8. E5 - Điều kiện triển khai: OCR local so với phiên âm đám mây so với OCR cũ

Ba nguồn, cùng cấu hình. **Cận trên (không on-premise): `haiku_p12`. Con số "on-premise thật": `ocr_v2_p12`.** `legacy_p1` chỉ để đối chứng. (Bảng chi tiết cascade cho `haiku_p12` và `legacy_p1`: `tables/e4_cascade_{dev,test}.csv`.)

<!-- BEGIN:e5 -->
| source | tfidf_macroF1_S | rule_gate_coverage | q35_s1_short_c2000 macroF1_Z | kev_s1_name_c2000 macroF1_Z | emb few-shot macroF1_Z | cascade DEV cross-fit auto-file@1% | classical DEV cross-fit | cascade bỏ luật, DEV cross-fit | cascade TEST auto-file@1% [CI] | classical TEST auto-file@1% [CI] |
|---|---|---|---|---|---|---|---|---|---|---|
| ocr_v2_p12 | 0.977 | 0.764 | 0.990 | 0.963 | 0.894 | 0.983 (0 sai) | 0.675 (2 sai) | 0.979 (0 sai) | 1.000 [1.000; 1.000] (1 sai) | 0.644 [0.525; 0.763] (0 sai) |
| haiku_p12 | 0.976 | 0.781 | 1.000 | 0.954 | 0.911 | 0.983 (0 sai) | 0.667 (2 sai) | 0.979 (0 sai) | 1.000 [1.000; 1.000] (0 sai) | 0.644 [0.525; 0.763] (0 sai) |
| legacy_p1 | 0.960 | 0.802 | 0.933 | 0.463 | 0.809 | 0.966 (1 sai) | 0.671 (2 sai) | 0.949 (3 sai) | 0.966 [0.915; 1.000] (0 sai) | 0.661 [0.542; 0.780] (0 sai) |
<!-- END:e5 -->

TEST của cascade trên `legacy_p1` (OCR cũ), để đối chiếu:

<!-- BEGIN:c_e4_test_legacy -->
| cấu hình | tự nhận (k/n) | CP 95% | sai | cận trên sai 95% | macro-F1 | luật % | TF-IDF % | LLM/emb % | người % | ms/tài liệu (rảnh)* |
|---|---|---|---|---|---|---|---|---|---|---|
| đầy đủ [tầng-3 = kev_s1_name_c2000] | 57/59 = 0.966 | [0.883; 0.996] | 0 | 0.051 | 0.980 | 85 | 10 | 2 | 3 | 48 |
| đầy đủ [tầng-3 = q35_s1_short_c2000] | 57/59 = 0.966 | [0.883; 0.996] | 0 | 0.051 | 0.980 | 85 | 10 | 2 | 3 | 65 |
| đầy đủ [tầng-3 = q25_s1_short_c2000] | 57/59 = 0.966 | [0.883; 0.996] | 0 | 0.051 | 0.980 | 85 | 10 | 2 | 3 | 44 |
| đầy đủ [tầng-3 = q35_s2_short_c2000] | 59/59 = 1.000 | [0.939; 1.000] | 2 | 0.103 | 0.972 | 85 | 10 | 5 | 0 |  |
| đầy đủ [tầng-3 = kev_s2_short_c2000] | 57/59 = 0.966 | [0.883; 0.996] | 0 | 0.051 | 0.980 | 85 | 10 | 2 | 3 |  |
| đầy đủ [tầng-3 = embfs] | 58/59 = 0.983 | [0.909; 1.000] | 1 | 0.079 | 0.942 | 85 | 12 | 2 | 2 | 6 |
| no_rule | 57/59 = 0.966 | [0.883; 0.996] | 2 | 0.106 | 0.963 | 0 | 47 | 49 | 3 | 629 |
| no_tfidf | 57/59 = 0.966 | [0.883; 0.996] | 1 | 0.081 | 0.972 | 85 | 0 | 12 | 3 | 185 |
| no_llm(rule+tfidf) | 57/59 = 0.966 | [0.883; 0.996] | 1 | 0.081 | 0.942 | 85 | 12 | 0 | 3 | 4 |
| llm_only | 56/59 = 0.949 | [0.859; 0.989] | 2 | 0.108 | 0.952 | 0 | 0 | 95 | 5 | 1193 |
| tfidf_only(classical) | 39/59 = 0.661 | [0.526; 0.779] | 0 | 0.074 | 0.821 | 0 | 66 | 0 | 34 | 3 |
| rule_only | 50/59 = 0.847 | [0.730; 0.928] | 0 | 0.058 | 0.852 | 85 | 0 | 0 | 15 | 3 |
<!-- END:c_e4_test_legacy -->

**Đọc kết quả.**
- Đã đo - **`ocr_v2` ~ Haiku**: TF-IDF 0.977 so với 0.976 (DEV, hòa); Qwen3.5 0.990 so với 1.000 (DEV), 0.983 so với 1.000 (TEST); cascade DEV cross-fit 98.3% ở cả hai; TEST 100% ở cả hai. Hiệu Qwen ocr_v2 - Haiku không tách được (1 lỗi / 59).
  Nghĩa là **không cần gửi ảnh ra ngoài để phân loại**; nhưng điều này chưa nói về *trích xuất trường* (01 đã cảnh báo OCR quan trọng hơn cho trích xuất).
- Đã đo - **OCR cũ (`legacy_p1`)**: cổng luật *không* tệ đi (coverage 0.802, luật so khớp không dấu), TF-IDF 0.960; nhưng **Kev tụt 0.96 -> 0.50** (không dấu, chữ dính) và Qwen3.5 0.996 -> 0.945. Cascade vẫn 96.6% (TEST) vì phần lớn tài liệu do luật/TF-IDF quyết.
  Hệ quả: *đừng dùng Kev-0.8B làm tầng cuối nếu OCR kém*; Qwen3.5-4B bền hơn.
- Phân biệt rõ: số trên `haiku_p12` = **cận trên với phiên âm đám mây** (không on-premise); số trên `ocr_v2_p12` = **điều kiện triển khai on-premise**; số trên `legacy_p1` = hệ thống cũ.

## 9. Bảng chi phí / quyền riêng tư (một dòng cho mỗi thiết kế)

Chất lượng lấy từ TEST (59 tài liệu, nguồn `ocr_v2_p12`) kèm CI; VRAM/độ trễ đo lúc máy rảnh (`--stage latency`, 38 tài liệu; VRAM Ollama theo `/api/ps`, Kev theo `/api/status` = bộ nhớ *cấp phát*; process Kev giữ tới ~6 GB sau các lượt prompt 10k token do bộ đệm PyTorch).
**Tài liệu/giờ = 3.6 triệu ms / độ trễ trung bình, 1 luồng, CHỈ bước phân loại.** Cột "OCR" là số đo của nhóm 1 (VietOCR: 3-6 s/trang chạy riêng; thông lượng 0.39 trang/s = 2.6 s/trang với 6 worker GPU), tức **~5-12 s cho trang 1-2 của một tài liệu: OCR lớn hơn phân loại 2-3 bậc độ lớn**.
Các cột "cần dữ liệu gán nhãn?" và "loại mới không huấn luyện lại?" là phán đoán thiết kế *có dẫn chứng* ở mục 4-5 (learning curve của 01; recall loại hiếm: TF-IDF 0, embedding few-shot 0.55-0.67, Qwen3.5 0.91-0.98, Kev tên 0.73-0.90); chưa kiểm chứng trên loại *thật sự mới* (mục 10).

<!-- BEGIN:c_cost -->
| thiết kế | on-premise? | cần dữ liệu gán nhãn? | loại MỚI không huấn luyện lại? | VRAM (GB) | độ trễ trung vị (ms) | p95 (ms) | tài liệu/giờ (1 luồng, chỉ phân loại) | OCR (s/trang) | chất lượng (ocr_v2_p12, TEST, 59 tài liệu) | dịch vụ phải chạy |
|---|---|---|---|---|---|---|---|---|---|---|
| Cổng luật từ khóa tiêu đề | có | không (từ khóa do người viết) | một phần: phải viết từ khóa | 0.00 | 3 | 4 | 1,034,721 | 3-6 s/trang (1 tiến trình VietOCR); thông lượng 0.39 trang/s (6 worker GPU) = 2.6 s/trang [team1 02_dataset_v2] | TEST Track Z: coverage 0.847, đúng trên phần quyết định 1.000 (tất định, không CI) | không |
| TF-IDF + ComplementNB (Track S) | có | có: >= 5-10 tài liệu/loại (01, mục 7c) | không: cần mẫu và huấn luyện lại (~0.4 s) | 0.00 | 3 | 5 | 1,358,337 | 3-6 s/trang (1 tiến trình VietOCR); thông lượng 0.39 trang/s (6 worker GPU) = 2.6 s/trang [team1 02_dataset_v2] | TEST macro-F1 (10 lớp + gộp) 0.946 [0.847; 1.000]; auto-file <=1% sai 0.610 [0.492; 0.729] (trần 0.81; loại hiếm luôn cho người) | không |
| Embedding bge-m3 few-shot (tâm lớp, >= 2 mẫu/loại) | có | có, rất ít: 2 mẫu/loại | một phần: thêm >= 2 mẫu, không huấn luyện | 0.62 | 73 | 160 | 49,432 | 3-6 s/trang (1 tiến trình VietOCR); thông lượng 0.39 trang/s (6 worker GPU) = 2.6 s/trang [team1 02_dataset_v2] | TEST Track Z macro-F1 0.913 [0.708; 0.978] (10 loại), recall loại hiếm 0.55 | Ollama (bge-m3) |
| Zero-shot Kev-0.8B (kev_s1_name_c2000) | có | không (chỉ mô tả loại) | có: thêm mô tả (độ tin cậy: xem recall loại hiếm, E2) | 1.55 | 860 | 934 | 4,188 | 3-6 s/trang (1 tiến trình VietOCR); thông lượng 0.39 trang/s (6 worker GPU) = 2.6 s/trang [team1 02_dataset_v2] | TEST Track Z macro-F1 0.991 [0.833; 1.000], accuracy 0.932 [0.864; 0.983], recall loại hiếm 0.73 | Kev server (GPU) |
| Zero-shot Qwen2.5-3B (q25_s1_short_c2000) | có | không (chỉ mô tả loại) | có: thêm mô tả (độ tin cậy: xem recall loại hiếm, E2) | 2.80 | 783 | 985 | 4,595 | 3-6 s/trang (1 tiến trình VietOCR); thông lượng 0.39 trang/s (6 worker GPU) = 2.6 s/trang [team1 02_dataset_v2] | TEST Track Z macro-F1 0.867 [0.667; 0.889], accuracy 0.797 [0.695; 0.898], recall loại hiếm 0.55 | Ollama (GPU) |
| Zero-shot Qwen3.5-4B (q35_s1_short_c2000) | có | không (chỉ mô tả loại) | có: thêm mô tả (độ tin cậy: xem recall loại hiếm, E2) | 3.05 | 1,193 | 1,730 | 3,018 | 3-6 s/trang (1 tiến trình VietOCR); thông lượng 0.39 trang/s (6 worker GPU) = 2.6 s/trang [team1 02_dataset_v2] | TEST Track Z macro-F1 1.000 [0.888; 1.000], accuracy 0.983 [0.949; 1.000], recall loại hiếm 0.91 | Ollama (GPU) |
| Cascade luật -> TF-IDF -> kev_s1_name_c2000 -> người | có | có (TF-IDF, embedding) + mô tả loại | có ở tầng 3 (xem E2/E4) | 1.55 | 3 | 940 | 57,917 | 3-6 s/trang (1 tiến trình VietOCR); thông lượng 0.39 trang/s (6 worker GPU) = 2.6 s/trang [team1 02_dataset_v2] | TEST tự nhận 1.000 (Clopper-Pearson 95% [0.939; 1.000]), 1 sai / 59 nhận (cận trên sai 0.078); tầng-3 xử lý 7% tài liệu; trung bình ước tính 62 ms/tài liệu (lúc rảnh) | Kev/Ollama (GPU) |
| Cascade luật -> TF-IDF -> q35_s1_short_c2000 -> người | có | có (TF-IDF, embedding) + mô tả loại | có ở tầng 3 (xem E2/E4) | 3.05 | 3 | 1,737 | 42,474 | 3-6 s/trang (1 tiến trình VietOCR); thông lượng 0.39 trang/s (6 worker GPU) = 2.6 s/trang [team1 02_dataset_v2] | TEST tự nhận 1.000 (Clopper-Pearson 95% [0.939; 1.000]), 1 sai / 59 nhận (cận trên sai 0.078); tầng-3 xử lý 7% tài liệu; trung bình ước tính 85 ms/tài liệu (lúc rảnh) | Kev/Ollama (GPU) |
| Cascade luật -> TF-IDF -> embfs -> người | có | có (TF-IDF, embedding) + mô tả loại | có ở tầng 3 (xem E2/E4) | 0.62 | 3 | 166 | 287,447 | 3-6 s/trang (1 tiến trình VietOCR); thông lượng 0.39 trang/s (6 worker GPU) = 2.6 s/trang [team1 02_dataset_v2] | TEST tự nhận 0.966 (Clopper-Pearson 95% [0.883; 0.996]), 0 sai / 57 nhận (cận trên sai 0.051); tầng-3 xử lý 12% tài liệu; trung bình ước tính 13 ms/tài liệu (lúc rảnh) | Kev/Ollama (GPU) + Ollama bge-m3 |
| Phiên âm đám mây (LLM-vision) + TF-IDF | KHÔNG: ảnh tài liệu gửi nhà cung cấp ngoài | có (TF-IDF) | không (TF-IDF); có nếu thêm LLM | 0.00 |  |  |  | không đo (phụ thuộc nhà cung cấp và mạng) | cận trên: 01 TEST macro-F1 0.974 [0.928; 1.000] - KHÔNG phải số triển khai | API đám mây + quyết định riêng tư của công ty |
<!-- END:c_cost -->

**Phương án đám mây (phiên âm LLM-vision) - ghi chú trung thực.** (i) Bắt buộc **gửi ảnh tài liệu nội bộ cho nhà cung cấp bên ngoài**: đây là quyết định riêng tư/pháp lý của công ty, không phải quyết định kỹ thuật; riêng bộ mẫu nghiên cứu này đã được chủ dự án đồng ý cho gửi tới LLM bên ngoài để tạo dữ liệu tham chiếu (bản chép Haiku, gán nhãn) - ngoại lệ cho nghiên cứu, không phải cho triển khai; hệ thống chạy thật vẫn bắt buộc on-premise.
(ii) Kết quả phân loại *không tốt hơn* OCR local trong khoảng nhiễu của dữ liệu này (mục 8), nên lợi ích cho riêng bước phân loại là không đo được. (iii) **Ước lượng bậc độ lớn về token (KHÔNG phải giá; giả định ~3 ký tự/token, token ảnh 1.5-3k/trang không đo):**
Haiku đã phiên âm 600 trang (trung bình 1395 ký tự/trang ≈ 465 token đầu ra/trang), tức mỗi 1000 trang cỡ 0.5 triệu token đầu ra và 1.5-3 triệu token đầu vào (ảnh). Dự án này không dùng giá nào; muốn biết chi phí tiền cần bảng giá hiện hành của nhà cung cấp.
(iv) Không đo độ trễ mạng/API.

## 10. Thiết kế đề xuất

**Khuyến nghị cho triển khai (on-premise, tuần tự trên một GPU 12 GB):**

1. **OCR local VietOCR chỉ cho trang 1-2** (phân loại không cần trang sau: Qwen3.5 với 800 ký tự đầu vẫn 0.992 DEV). Đây là chi phí chính (~5-12 s/tài liệu); phân loại gần như miễn phí so với nó.
2. **Tầng 1 - cổng luật tiêu đề** luôn bật (3.5 ms, ~76-85% tài liệu, đúng 100% trên phần quyết định ở DEV và TEST; bền với OCR kém: coverage 0.80 trên OCR cũ). *Bằng chứng:* ablation `rule_only` / `no_rule` (mục 7).
3. **Tầng 2 - TF-IDF (ComplementNB)** cho phần còn lại có confidence cao (2.7 ms, 0.4 s huấn luyện lại). *Bằng chứng:* E1/01: ngang embedding trên 10 lớp, rẻ nhất.
4. **Tầng 3 - Qwen3.5-4B zero-shot (Ollama, 3.1 GB VRAM, ~1.2 s)** chạy cho ~5-7% tài liệu còn lại, **kể cả loại hiếm và tài liệu TF-IDF gọi `RARE_OR_OTHER`**; chỉ nhận khi LLM đồng thuận với tầng khác hoặc confidence cao; `OTHER` luôn cho người.
   *Bằng chứng:* E2 (accuracy 0.996 DEV / 0.983 TEST, recall loại hiếm 62/63 và 10/11), E5 (bền với OCR kém hơn Kev). **Kev-0.8B (1.6 GB, chỉ tên loại) là phương án nhẹ** khi VRAM hẹp và OCR tốt (0.96 DEV / 0.93 TEST), không dùng với OCR cũ.
5. **Tầng 4 - người** nhận phần bị từ chối, *kèm gợi ý của LLM*; **giữ một tỉ lệ kiểm mẫu ngẫu nhiên (đề xuất 5-10%) trên phần tự động** để đo sai thật và hiệu chỉnh ngưỡng định kỳ - vì ngưỡng DEV hiện dễ dãi (mục 7) và mức 1% chưa được chứng minh.
6. **Từ chối bằng đồng thuận** (Kev + Qwen cùng nhãn: 95-96% phạm vi, 0-1 lỗi) là phương án dự phòng không cần ngưỡng nếu muốn an toàn hơn, đổi lại chạy hai mô hình (~2 s/tài liệu) - dùng cho tài liệu do tầng-3 xử lý, không cho cả luồng.
7. **Vận hành:** Ollama (Qwen3.5-4B, bge-m3) và Kev là hai dịch vụ GPU; chạy **tuần tự / hàng đợi** (sự cố ở mục 11), lưu cache theo (mô hình, prompt), ghi log mọi quyết định (tầng nào, confidence), đặt `num_predict` cho Ollama để một lần sinh vô hạn không làm treo hàng đợi.
8. **Loại mới:** thêm *mô tả ngắn* vào taxonomy (không huấn luyện lại) -> tầng-3 nhận được; sau khi có >= 5-10 mẫu mỗi *mẫu biểu*, huấn luyện lại TF-IDF (0.4 s) và/hoặc thêm tâm embedding (>= 2 mẫu). *Bằng chứng một phần:* recall loại hiếm của LLM zero-shot; **chưa kiểm chứng với loại thật sự mới.**

**Điều CHƯA được chứng minh (nói thẳng):**
- **Tổng quát hóa sang khách hàng/biểu mẫu/loại mới.** Mô tả loại, từ khóa luật và nhãn đều gắn với chính tập này (vòng tròn nhãn/mô tả, mục 3). Biến thể chỉ-tên-loại (0.97) làm giảm lo ngại này nhưng không loại trừ.
- **Sai <= 1%.** TEST chỉ cho cận trên 5-8%. Ngưỡng chọn trên DEV có 0-2 lỗi nên không có tín hiệu để đặt ngưỡng chặt.
- **Nhãn đúng với con người.** Chưa nhân viên công ty nào xác nhận; lỗi hệ thống chung của các mô hình gán nhãn vẫn có thể có.
- **Độ tin cậy confidence của Qwen** (ít lỗi để học), **độ bền theo thời gian/phiên bản mô hình** (Ollama, Qwen cập nhật), **thông lượng khi nhiều người dùng** (Kev đơn luồng, GPU dùng chung).
- **Kev-4B** chưa thử (mục 3).

**Thí nghiệm tiếp theo cần làm trước khi triển khai (kèm cỡ mẫu kỳ vọng):**

| # | Thí nghiệm | Cỡ mẫu | Mục đích |
|---|---|---|---|
| 1 | Chạy cascade ở chế độ **bóng (shadow)** 2-4 tuần, người vẫn xếp như cũ, ghi lại bất đồng | >= 1000 tài liệu thật | Đo sai thật; chứng minh <= 1% cần >= ~300 tài liệu tự nhận liên tiếp không lỗi (quy tắc ba), <= 0.5% cần ~600 |
| 2 | Bộ **TEST mới** từ khách hàng/biểu mẫu chưa từng thấy, nhãn do **nhân viên công ty** gán mù với mô hình | >= 150 tài liệu, >= 10 khách hàng/mẫu, gồm >= 5 loại mới x 5 tài liệu | Đo tổng quát hóa và recall loại mới; 20 tài liệu/loại cho CI recall ±15 điểm (24 loại hiếm -> ~480 tài liệu) |
| 3 | Nhân viên viết **mô tả cho loại mới trước khi xem tài liệu** rồi đo tầng-3 | 5-10 loại mới x >= 10 tài liệu | Kiểm chứng "loại mới không huấn luyện lại" mà không bị vòng tròn mô tả |
| 4 | Rà nhãn: nhân viên kiểm toàn bộ 24 loại hiếm và 30-50 tài liệu thường ngẫu nhiên | ~150 tài liệu | Ước lượng nhiễu nhãn và độ đồng thuận mô hình - người |
| 5 | Hiệu chỉnh confidence (nhiệt độ/isotonic) và ngưỡng có **biên an toàn**; thêm lựa chọn "2 LLM đồng thuận" vào cascade (hiện chỉ đo ngoài cascade) | tập ở (2) | Ngưỡng không dễ dãi; đo risk-coverage thật |
| 6 | So Kev-4B (nếu có tài nguyên), Qwen3.5 lớn hơn/nhỏ hơn, và ảnh+văn bản (late fusion) cho tài liệu OCR rỗng | cùng tập (2) | Chọn tầng-3 tối ưu theo VRAM |
| 7 | Kiểm thử tải: hàng đợi tuần tự cho Kev/Ollama trên GPU chuyên dụng | 1 ngày dữ liệu | Thông lượng thật, p95 độ trễ, độ ổn định |

## 11. Hạn chế

1. **Cỡ mẫu.** DEV 237, TEST 59 (Track Z TEST chỉ chấm được 10 loại; nhiều loại hiếm 1-2 tài liệu). Mọi CI rộng; chênh dưới ~0.05-0.1 macro-F1 không phân biệt được. Per-type recall là giai thoại.
2. **Nhãn chưa kiểm chứng + vòng tròn** (mục 3): nhãn do mô hình gán theo hướng dẫn mà mô tả/từ khóa được viết sau khi xem tài liệu; LLM zero-shot và cổng luật có thể đang đo "độ khớp với hướng dẫn" hơn là độ đúng. Kappa = 1.0 giữa hai lượt gán nhãn không chứng minh nhãn đúng.
3. **Cổng luật lạc quan**: 100% đúng trên phần quyết định, nhưng từ khóa viết sau khi xem tài liệu; ablation bỏ luật là ước lượng sát hơn cho tài liệu lạ.
4. **Chọn mô hình trên DEV nhỏ**: ~19 cấu hình LLM trên `ocr_v2_p12` + 12 cấu hình embedding; người thắng DEV có thể do may mắn; ngưỡng cascade chọn trên 237 tài liệu với 0-2 lỗi quyết định ngưỡng. Đã báo cả cross-fit và nhiều ứng viên tầng-3; trên DEV chúng **hòa nhau** (95-99.6%).
5. **Một lần chạy mỗi cấu hình** (temperature 0, seed 0): không đo được dao động giữa các lần chạy hay giữa các phiên bản mô hình/Ollama.
6. **Độ trễ dưới tải chung.** Lưới chạy khi GPU/CPU dùng chung (nhiều tiến trình của tôi và của người khác); độ trễ lúc chạy lưới có lúc bị phồng bởi chờ hàng đợi. Sự cố đã gặp: chạy Kev và Ollama đồng thời làm Ollama đứng 1-6 phút/lời gọi (đã chuyển sang chạy tuần tự;
   mọi kết quả trong cache vẫn hợp lệ vì khóa chỉ gồm mô hình + yêu cầu; `num_predict=96` được thêm làm lưới an toàn nhưng **không** nằm trong khóa cache; các lỗi truyền tải/timeout được thử lại ở lần chạy sau). Một lượt chạy DEV đầu của thí nghiệm 01 bổ sung bị sập không rõ nguyên nhân (không tái hiện; xem 01 mục 0).
7. **Kev chỉ 0.8B**; không đánh giá Kev-4B. Kev xử lý tuần tự.
8. **Ngưỡng cascade trên fold seed 0** và mô hình huấn luyện 80% DEV áp cho mô hình 100% DEV (như 01).
9. **Phạm vi**: chỉ văn bản (không dùng ảnh); chỉ trang 1-2; một công ty, một giai đoạn; không đo trôi dạt theo thời gian.
10. **Tài liệu composite hỗn hợp** (8 tệp) bị loại khỏi benchmark; cần Nhóm 2 tách trang trước.

## 12. Đã cắt / không làm (để không ai tưởng đã có)

- **Kev-4B** (mục 3). **`qwen2.5:3b` với mô tả dài**: chạy dở ~17 phút rồi dừng vì chậm và giá trị thấp (3B đã yếu với mô tả ngắn); không báo cáo. **Ví dụ in-context** chỉ thử với Qwen3.5-4B, 1 ví dụ/loại (không giúp).
- Lưới LLM đầy đủ (prompt x độ dài x 3 nguồn) bị cắt: *chọn* prompt trên `ocr_v2_p12` DEV; chỉ cấu hình tốt nhất mỗi họ + biến thể hai bước + Kev mô tả ngắn hai bước được chạy trên `haiku_p12` và `legacy_p1`. `ocr_v2_p1` không dùng cho LLM.
- Embedding: không thử mô hình embedding khác, không tinh chỉnh bge-m3.
- Calibration: không dùng nhiệt độ/isotonic/conformal; chỉ ECE, AUROC, AURC và ngưỡng chọn trên DEV. "2 LLM đồng thuận" chỉ đo như một quy tắc độc lập (mục 6), chưa là chế độ của cascade.
- Không dùng ảnh trang cho LLM (mô hình vision của Ollama); không late-fusion ảnh + văn bản.
- Không đo độ trễ API đám mây; không có giá tiền.
