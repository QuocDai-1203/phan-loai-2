# Thí nghiệm 03 — Cascade trong `src/`: kiểm hồi quy so với thí nghiệm 02 (Nhóm 3, việc T1)

> **Đọc trước.** Thí nghiệm này **không đo chất lượng mới**. Nó chứng minh một điều: mã cascade trong `src/classification/` (`DocumentClassifier`) ra **cùng quyết định, từng tài liệu**, với cascade của thí nghiệm 02 cho cùng cấu hình. Mọi con số chất lượng (độ chính xác, tỉ lệ tự xếp hồ sơ, khoảng tin cậy) vẫn là của [02](../02_llm_and_cascade/RESULTS.md) và mang đủ các hạn chế ở đó: nhãn do mô hình AI gán và chưa có nhân viên công ty kiểm; vòng tròn nhãn/mô tả; TEST chỉ 59 tài liệu; chưa chứng minh được mức sai ≤ 1%.
> Nhãn: `data/labels_v2.csv`, sha1[:10] `eb3348713a`. Chia: `data/splits/splits.csv` (DEV 237, TEST 59). Nguồn văn bản: `ocr_v2_p12` (OCR local VietOCR, trang 1–2). Ngày chạy: 2026-10-12.

## 1. Câu hỏi

Lớp `DocumentClassifier` (luật → TF-IDF → LLM → người) có cho cùng kết quả với cascade thí nghiệm 02 trên 237 tài liệu DEV, khi mọi lời gọi LLM lấy từ cache sẵn có không?

Cấu hình so sánh (cấu hình "chính" của 02 §7, mức sai ≤ 1%, đọc từ `results/02_llm_and_cascade/tables/dev_selection_02.json`, mục `cascade.ocr_v2_p12.entries["full[q35_s1_short_c2000]"]`): luật + TF-IDF `tfidf_word_cnb_raw_C0.1` (`th_s = 0,2820278…`) + Qwen3.5-4B mô tả ngắn 1 bước 2000 ký tự (`th_llm = 0,5481234…`), `agree = none`.

## 2. Lệnh chạy chính xác

```powershell
$py = ".venv\Scripts\python.exe"
# (1) huấn luyện artefact TF-IDF của src (trên toàn DEV; không đọc TEST) -> models\classification\tfidf_word_cnb_raw_C0.1\
& $py -X utf8 scripts\train_tfidf_classifier.py
# (2) hồi quy DEV (CPU, vài chục giây; LLM chỉ đọc cache _cache\ollama của thí nghiệm 02, thiếu một khóa là lỗi)
& $py -X utf8 teams\team3_classification\experiments\03_src_cascade\regress_vs_exp02.py
# (3) hồi quy TEST: ĐÚNG MỘT LẦN, chỉ để xác nhận tái lập dòng TEST đã báo cáo (sổ đăng ký chặn lần hai)
& $py -X utf8 teams\team3_classification\experiments\03_src_cascade\regress_vs_exp02.py --final-test-once
& $py -X utf8 -m pytest tests\test_classif_tfidf.py tests\test_classif_doc_classifier.py tests\test_classifier.py tests\test_contracts.py -q
```

Đầu ra: `results/03_src_cascade/regress_dev_summary.json` (tổng hợp), `regress_dev_per_doc.csv` (từng tài liệu, **chứa `doc_id`: chỉ dùng nội bộ**), `test_run_registry.json` (sổ đăng ký lần chạy TEST).

## 3. Cách so sánh (để biết "trùng" nghĩa là gì)

| | THAM CHIẾU | MỚI |
|---|---|---|
| Cổng luật | `signals.rule_signals` (thí nghiệm 02) | `CascadedClassifier.match_rules` trong `DocumentClassifier` |
| TF-IDF trên DEV | `signals.tfidf_signals`: out-of-fold, seed 0, 5 fold (mô hình của fold k không thấy tài liệu fold k) | `TfidfClassifier` của `src/`, **huấn luyện lại trên 4 fold, dự đoán fold còn lại**, cùng seed và fold |
| LLM | `signals.llm_signals` → `ZeroShotPredictor` cho **cả 237** tài liệu | `OllamaBackend` chỉ cho tài liệu mà luật và TF-IDF từ chối (**13** tài liệu) |
| Quyết định | `cascade.run_cascade` trên đủ tín hiệu | `cascade.run_cascade` trên tín hiệu từng phần, gọi theo tầng |
| Cache LLM | `_cache/ollama` (thí nghiệm 02) | cùng thư mục, bọc chế độ **chỉ đọc**: thiếu khóa → `CacheMiss` (không gọi Ollama) |

Lưu ý quan trọng: artefact TF-IDF lưu trong `models/` được huấn luyện trên **toàn DEV**, nên chạy nó lại trên DEV là chấm trên chính dữ liệu huấn luyện (rò rỉ, không có nghĩa). Vì vậy hồi quy DEV **không dùng artefact đó** mà huấn luyện lại theo fold bằng cùng lớp `TfidfClassifier`. Artefact chỉ được kiểm ở lần chạy TEST (mục 5).

Hai kiểm tra phụ để chắc rằng THAM CHIẾU là đúng cái thí nghiệm 02 đã báo cáo: (a) so tổng hợp của THAM CHIẾU với dòng đã lưu `tables/e4_cascade_dev.csv` (`n_accepted`, `errors`, tỉ lệ luật/TF-IDF/LLM); (b) so cả các tín hiệu trung gian (nhãn luật, nhãn và độ tin cậy TF-IDF, nhãn và độ tin cậy LLM) từng tài liệu.

## 4. Kết quả DEV (chạy lần cuối bằng lệnh (2) ở trên)

| Chỉ số | THAM CHIẾU (mã 02) | MỚI (`src/`) |
|---|---|---|
| Tự nhận | 236 / 237 | 236 / 237 |
| Sai trong số được nhận | 1 | 1 |
| Tài liệu theo tầng: luật / TF-IDF / LLM / người | 181 / 43 / 12 / 1 | 181 / 43 / 12 / 1 |
| Khớp dòng đã lưu `e4_cascade_dev.csv` | có (236, 1 sai; 76,4% / 18,1% / 5,1%) | — |
| Lời gọi LLM đọc từ cache | 237 trúng, 0 lỡ | 13 trúng, **0 lỡ**, 0 bản ghi lỗi |

**Kết quả hồi quy: 237 / 237 tài liệu trùng bộ ba (tầng, nhãn, được nhận); 237 / 237 trùng cả tín hiệu trung gian.** Không có tài liệu nào lệch nên không có gì để giải thích. Đây là kết quả của một lần chạy; vì cache LLM và TF-IDF đều tất định (`ComplementNB`, `temperature=0`, `seed=0`) nên lần chạy lại cho cùng kết quả.

Hai tài liệu đáng chú ý trong 237 (đã có trong 02, nêu lại để người đọc không tưởng là lỗi của mã mới): 1 tài liệu loại hiếm `BAN_VE_KY_THUAT` bị LLM trả `OTHER` → về người (`llm_other`); 1 tài liệu thật là `OTHER` bị TF-IDF nhận nhầm thành `HD_MUA_BAN` — đây chính là lỗi duy nhất của 02 trên DEV, và nó nằm ở tầng TF-IDF (bẫy 10 của README: TF-IDF ép loại hiếm vào loại đã biết).

## 5. Lần chạy TEST duy nhất (chỉ để xác nhận tái lập; không chỉnh gì)

Điều kiện: TEST đã được chấm ở 02 (`results/02_llm_and_cascade/tables/test_scored_02.json`). Lần này chạy `DocumentClassifier` với **chính artefact** `models/classification/tfidf_word_cnb_raw_C0.1` (huấn luyện trên toàn DEV; `meta.json` ghi `train_split=DEV`, 237 `doc_id`, không giao với TEST — script kiểm bằng `assert`) và cache LLM chỉ đọc, rồi so tổng hợp với dòng `e4_cascade_test.csv` của cùng cấu hình. Không đọc lỗi TEST để sửa gì; lệnh bị chặn chạy lần hai bởi `test_run_registry.json`.

| | Dòng TEST đã báo cáo (02 §7) | `DocumentClassifier` của `src/` |
|---|---|---|
| Tự nhận | 59 / 59 | 59 / 59 |
| Sai trong số được nhận | 1 | 1 |
| Luật / TF-IDF / LLM | 84,7% / 8,5% / 6,8% | 50 / 5 / 4 tài liệu = 84,7% / 8,5% / 6,8% |
| Lời gọi LLM từ cache | — | 4 trúng, 0 lỡ |

**Tái lập được** (`reproduces_stored_row = true`). Chỉ so tổng hợp, không so từng tài liệu TEST (mục đích của lần chạy duy nhất này chỉ là xác nhận dòng đã báo cáo; kiểm từng tài liệu đã làm trên DEV). Khoảng tin cậy và nhận xét về 59 tài liệu: xem 02 §7, không lặp lại ở đây.

## 6. Những gì mã mới làm khác thí nghiệm (có chủ ý, không ảnh hưởng kết quả trên 237 tài liệu DEV)

| Điểm | Thí nghiệm 02 | `src/` | Vì sao không đổi kết quả DEV |
|---|---|---|---|
| Số lời gọi LLM | một lời gọi cho **mọi** tài liệu | chỉ cho tài liệu bị luật và TF-IDF từ chối (13/237 trên DEV) | tầng sau chỉ xét tài liệu tầng trước chưa nhận |
| Tài liệu < 25 ký tự | tầng LLM trả "không đọc được"; luật và TF-IDF vẫn xét | chuyển thẳng cho người (`abstain_reason=text_too_short`), đúng điều README nhóm 3 bẫy 16 đã ghi | tài liệu DEV ngắn nhất có 38 ký tự ở trang 1 |
| Văn bản vào cascade | trang 1–2 của tài liệu (`ocr_v2_p12`) | `text_for_classification`: 2 trang đầu của **lát cắt**, bỏ trang rỗng, nối `\n` (lát cắt không có `pages` thì dùng `combined_text`) | giống cách dựng nguồn `ocr_v2_p12`; với tệp ghép, lát cắt do nhóm 2 quyết định nên chất lượng phụ thuộc bộ tách |
| LLM lỗi / hết giờ | tính là `NO_ANSWER` → về người, không ghi lý do | `tier="human"`, `abstain_reason="llm_error"`, `error=<lý do>`, gợi ý TF-IDF nếu có | cùng quyết định (về người), thêm bằng chứng |
| Chế độ `agree = emb` | có (cho Kev) | chưa có; chuyển `none` và đánh dấu `measured=False` | cấu hình chính (Qwen3.5) dùng `none` |

## 7. Tầng Kev (đã sửa; chưa đo lại)

- `CascadedClassifier.classify_with_kev` nay gửi **tên loại** (`name_vi`, bỏ `UNREADABLE`) thay vì `description` dài; câu hỏi và văn bản làm sạch giống 02; độ tin cậy là xác suất của tiêu chí được chọn trong `probabilities` (thang đã đo ở 02 §6); `model_name` lấy từ `/api/status` → `current_model` của máy chủ (`kev-unverified` nếu không hỏi được). Kev **tắt mặc định** (`kev_endpoint=None`), không còn lỗi Kev giả trong kết quả khi tắt.
- Là backend tầng 3 chọn được: `DocumentClassifier.from_defaults(llm_backend="kev")` (`kev_s1_name_c2000`). Ngưỡng `th_llm` lấy từ mục `full[kev_s1_name_c2000]` mức 1% nhưng mục đó đo với `agree = emb` (đồng thuận với embedding few-shot, chưa đưa vào `src/`). Mã dùng `agree = none` cùng ngưỡng — **chặt hơn** (tập được nhận là tập con) nhưng **không phải cấu hình đã đo**; kết quả mang `measured = False` trong `describe()`.
- **Chưa kiểm hồi quy với Kev** và không chạy Kev trong thí nghiệm này (không đổi mô hình của máy chủ dùng chung). Test đơn vị dùng HTTP giả (`tests/test_classif_doc_classifier.py`, `tests/test_classifier.py`).

## 8. Hạn chế và những gì chưa kiểm

- Hồi quy chỉ cho cấu hình Qwen3.5-4B một bước, mức 1%. Các cấu hình khác (`q35_s2`, `q25`, Kev) chỉ có test đơn vị, chưa có hồi quy từng tài liệu.
- Hồi quy dùng cache LLM của 02, nên **chưa kiểm** rằng Ollama hiện tại trả đúng câu trả lời cũ cho cùng lời nhắc (khác phiên bản Ollama/mô hình có thể đổi). Cache khóa theo toàn bộ yêu cầu, nên nếu lời nhắc đổi thì lỡ cache và lỗi chứ không lặng lẽ khác.
- Artefact TF-IDF phụ thuộc phiên bản scikit-learn (pickle): `meta.json` ghi `sklearn_version`, nạp cảnh báo khi khác.
- Thời gian chạy không đo ở đây (chạy từ cache). Độ trễ thật dưới tải: xem các lần chạy `run_pipeline.py` trong `teams/team1_ocr/experiments/07_src_engine/RESULTS.md` mục 5 (LLM gặp `ReadTimeout` 180 giây khi GPU bị chiếm, được ghi thành `llm_error` và chuyển cho người).
- Ngưỡng vẫn là ngưỡng dễ dãi của DEV (README bẫy 7, việc T3): chưa có kiểm mẫu ngẫu nhiên trên phần tự xếp hồ sơ.
