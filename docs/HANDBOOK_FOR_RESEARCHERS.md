# Cẩm nang cho người mới

Dành cho sinh viên năm cuối ngành AI: giỏi Python/ML, **mới** với kho mã này và với bài toán xử lý tài liệu. Đọc hết trong khoảng một giờ, rồi mở README của nhóm mình. Tài liệu này mô tả trạng thái **thật** ngày 2026-10-16 (sau giai đoạn 2: tách, trích xuất, toàn trình đo một lần; và giai đoạn 3: 21 loại có trường, ảnh trang cho VLM, review độc lập); cái gì mới là kế hoạch thì được ghi là kế hoạch.

## 1. Bài toán và trạng thái hôm nay

Một công ty kinh doanh xăng dầu có hàng nghìn hồ sơ giấy được quét thành PDF. Hệ thống cần: tách tệp ghép thành từng tài liệu, nhận loại, lưu đúng hồ sơ, lấy các trường quan trọng (nhất là **ngày hết hạn**) đưa vào ERP. Bản chạy thật phải **on-premise** (không gọi dịch vụ đám mây). Đây là ứng dụng thật: mọi con số bạn báo cáo sẽ được dùng để quyết định có triển khai hay không.

Kho này có 336 PDF mẫu (304 tài liệu duy nhất), ~36 loại tài liệu, và một đường ống chạy được từ PDF tới trường dữ liệu (`scripts/run_pipeline.py`) cùng số đo cho từng khâu và cho cả chuỗi. Cách làm ban đầu bị kiểm tra và bỏ vì không đứng vững (nhãn là tên thư mục, có tệp trùng giữa train và test, OCR mất dấu tiếng Việt, mục tiêu hiệu năng nêu trước khi có thí nghiệm). Cái bạn thừa hưởng là bản đã sửa: nhãn theo nội dung, chia dữ liệu có nhóm, bộ chấm có TEST khóa, OCR cục bộ giữ dấu, mã báo lỗi rõ ràng.

**Điều quan trọng nhất cần nhớ: mọi đáp án trong kho đều do máy tạo và chưa có nhân viên công ty kiểm** — nhãn loại tài liệu (hai mô hình AI), đáp án ranh giới tách trang (một mô hình xem đủ trang), đáp án trường (Haiku, Sonnet, Opus phân xử). "Đúng" luôn có nghĩa "khớp đáp án máy".

**Kết quả lớn nhất cho tới nay** ([báo cáo toàn trình](../teams/00_data_and_eval/experiments/01_end_to_end/RESULTS.md); dev n = 245 tệp là phần dùng để chọn, TEST n = 59 tệp chấm một lần): tách trang **không** làm tăng tỉ lệ tệp đúng hoàn toàn (dev: 91,9% so với 92,3% khi không tách, hiệu −0,4 điểm [−2,9; +1,9], không tách được; TEST cùng 56/59), vì khoảng 92% tệp là tài liệu đơn hoặc nhiều trang không ghép; nhưng tách giao đúng thêm tài liệu của tệp ghép (87,7% so với 70,4% tài liệu đáp án) và giảm sai lặng lẽ (4,94% so với 7,31% tổng số tệp). Không biến thể nào đạt sai lặng lẽ ≤ 1%. Mặc định của pipeline là `model+merge`; phương án thận trọng hơn là `triage`.

**Giai đoạn 3 (2026-10-15 đến 16), nên biết trước khi làm gì tiếp.**

* *Đã làm:* quy tắc `id` cho tệp ghép cùng loại (0/7 → 4/7 ranh giới, n = 6 tệp); biên an toàn cascade (0/235 sai cross-fit, cận trên 1,27%, chưa đủ dữ liệu để chọn mức biên); gỡ mơ hồ theo tiêu đề `rule_title_tiebreak` (28/28 lát đúng trên 8 tệp một nhà cung cấp, đổi tầng 25/237 tài liệu DEV, 0 đổi nhãn); 17 loại mới có trường (84 đơn vị silver v2); ảnh trang cho VLM trong pipeline (hạn tự nhận đúng 32 → 37/66, sai 0, p dấu = 0,0625); tự xoay trang (30/32 đúng); toàn trình v2 và chi phí có OCR thật (~500 trang/giờ/máy, GPU dùng chung).
* *Mặc định hiện tại (mã là chuẩn):* tách `model+merge`; `tiebreak` tắt nhưng ghi nhãn "bóng"; `id` chạy bóng và chuyển tệp sang người duyệt khi muốn thêm ranh giới; VLM bật; **tự nhận ngày hết hạn tắt** (`--auto-accept-expiry` để bật); tệp > 30 trang chuyển người; kiểm mẫu theo tệp. *Lý do:* review độc lập ([báo cáo 04](../teams/00_data_and_eval/reports/04_phase3_review_and_deployment.md)) thấy `id`, `tiebreak` và quy tắc tự nhận được thiết kế từ chính các tệp dùng để đo, còn TEST không có tệp ghép loại đó nên không kiểm được ngoài mẫu. Số dev của S10+id+tiebreak (232/245 tệp đúng hoàn toàn, lỗi lặng lẽ 5) vẫn đúng nhưng là **mức trần lạc quan**; dev + TEST gộp 7/295 = 2,4% lỗi lặng lẽ, chưa đạt 1% (cần ≥ 299 tệp tự xử lý liên tiếp không lỗi).
* *Điều dễ bỏ qua:* tự nhận hạn dựa vào quy ước "ngày trong tên tệp = ngày hết hạn", mà công ty đã bác ngày 2026-10-16 (ngày chỉ là hạn khi tài liệu ghi rõ; xem [`README.md`](../README.md) mục "Quyết định của công ty"); dữ liệu thật đang nằm trong git; thông lượng có sai số ≥ ±50%; TEST đã mòn sau nhiều lần mở.
* *Việc còn lại và cần gì từ công ty:* 15 việc ưu tiên ở mục 11 của báo cáo 04 (bản rút gọn trong [`README.md`](../README.md), mục "Giai đoạn 3"): xác nhận quyền dùng dữ liệu, quy ước đặt tên tệp thật, nhân viên kiểm đáp án máy, tệp ghép từ ≥ 3 nhà cung cấp, 6–8 tuần chạy bóng.

**Đọc trước (10 phút):** [`original_direction/README.md`](original_direction/README.md) — hướng đi ban đầu của đề tài (19 danh mục, Jev/Kev, OCR Apple Vision, tách bằng luật, GLiNER, lộ trình 4 tuần) và bảng đối chiếu từng quyết định: cái nào được giữ, đổi, bỏ hay chưa kiểm, kèm số đo. Bản nguyên văn các tài liệu cũ nằm cùng thư mục; liên kết bên trong chúng là của bản cũ.

Đọc theo thứ tự: mục 2 (cài đặt và ngày đầu tiên) → mục 4 (đường ống thật) → mục 7 (mười quy tắc) → [`teams/README.md`](../teams/README.md) → README nhóm của bạn → [`PARALLEL_RESEARCH_PLAN.md`](PARALLEL_RESEARCH_PLAN.md).

## 2. Dựng môi trường từ đầu

Máy mẫu: Windows, Python 3.13, RTX 3060 12 GB (dùng chung với việc khác). GPU **không bắt buộc** (trừ khi chạy OCR cả kho cho nhanh). Dịch vụ tùy chọn: máy chủ quyết định Kev ở `127.0.0.1:8009`; Ollama ở `127.0.0.1:11434` (`qwen3.5:4b`, `qwen2.5:3b`, `bge-m3`).

```powershell
cd Z:\projects\sdh-phanloaitailieu
python -m venv --system-site-packages .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
# torch bản CUDA cài riêng theo máy: https://pytorch.org/get-started/locally/
```

- Luôn chạy Python với **`-X utf8`** (đường dẫn và nội dung tiếng Việt): `.venv\Scripts\python.exe -X utf8 ...`.
- `requirements.txt` ghi chú: `vietocr`, `easyocr` cài bằng `pip install --no-deps` nếu pip kéo phiên bản torch khác; PaddleOCR **không** cài vào venv chung. Lệnh cài trên máy sạch **chưa được chạy lại** khi viết cẩm nang này (môi trường `.venv` hiện có đã được dùng để chạy mọi lệnh bên dưới).
- Bộ mẫu PDF nằm sẵn trong kho: `docs/_chot_samples_phanloaitailieu/` (336 tệp, 19 thư mục + 2 tệp ở gốc). Đây là hồ sơ thật có thông tin cá nhân — xem quy tắc 9.

Kiểm tra môi trường:

```powershell
.venv\Scripts\python.exe -X utf8 -m pytest -q                              # test của src/
.venv\Scripts\python.exe -X utf8 -m pytest teams\00_data_and_eval\tests -q   # test của bộ chấm và manifest
.venv\Scripts\python.exe -X utf8 -m pytest teams\team4_extraction\tests -q   # test riêng của nhóm trích xuất
```

Lần chạy gần nhất (2026-10-16, cuối giai đoạn 3): 327 test qua trong `tests/` (đã gồm các test của `src/extraction/`), 33 test qua trong `teams\00_data_and_eval\tests` và 223 test qua trong `teams\team4_extraction\tests`. `pytest.ini` đặt `testpaths = tests`, nên `pytest -q` ở gốc chỉ chạy `tests/`; hai bộ test còn lại chạy riêng như trên. Các test này không cần GPU, mạng hay thư mục `models/`.

### Ngày đầu tiên: chạy cả đường ống trên một tệp và biết đọc kết quả ở đâu

1. **Kiểm tra mô hình.** `.venv\Scripts\python.exe -X utf8 scripts\setup_ocr_models.py` in OK hoặc THIẾU cho ba tệp OCR trong `models/` (không dùng mạng). Thiếu bộ TF-IDF: `.venv\Scripts\python.exe -X utf8 scripts\train_tfidf_classifier.py` (vài giây, CPU). Mô hình tách trang `pair_gb_v0.joblib` đã nằm trong kho ở `teams/team2_splitting/models/`. Cách có từng tệp: [`models/README.md`](../models/README.md).
2. **Chạy thử không cần Ollama** (chỉ luật + TF-IDF, chưa nhận → người): `.venv\Scripts\python.exe -X utf8 scripts\run_pipeline.py "data\classified_v2\_COMPOSITE_KHAC_LOAI\20260109-04.pdf" --no-llm --no-extract --out output\pipeline`.
3. **Chạy đầy đủ** khi đã có Ollama với `qwen3.5:4b` ở `127.0.0.1:11434`: bỏ `--no-llm --no-extract`. So hai chính sách tách trên cùng tệp bằng `--splitter model+merge` (mặc định) và `--splitter triage`.
4. **Đọc kết quả.** Bản tóm tắt in ra màn hình: thời gian từng khâu, mỗi lát cắt một dòng (tầng, nhãn, độ tin cậy, quyết định `auto_file` hoặc `needs_human`, lý do, gợi ý), dòng "Định tuyến cấp tệp" (chính sách tách, số lát trước và sau khi gộp, số lời gọi LLM) và các dòng CẢNH BÁO. Bản đầy đủ nằm ở `output\pipeline\<tên tệp>.pipeline.json`: văn bản OCR, `split_result`, `classifications`, `extractions`, `routing` (mỗi lát cắt, gồm `expiry`, `expiry_suggestion`, `field_review`), `file_routing`, `stage_timings_ms`, `warnings`. **Tệp này chứa nội dung tài liệu thật: không dán vào chat hay issue.**
5. **Rồi đọc** phần "Tóm tắt" của [báo cáo toàn trình](../teams/00_data_and_eval/experiments/01_end_to_end/RESULTS.md), README của nhóm bạn, và [`PARALLEL_RESEARCH_PLAN.md`](PARALLEL_RESEARCH_PLAN.md) mục 6 (giả thuyết và trạng thái).

Mọi cờ của `run_pipeline.py` (đối chiếu với `--help`): `--out`, `--max-pages` (30), `--no-llm`, `--no-extract`, `--device` (`auto`/`cpu`/`cuda:0`), `--dpi` (200), `--llm` (`ollama`/`kev`), `--splitter` (`model+merge`/`triage`/`none`/`rule`/`rule_v2`/`model`), `--llm-timeout` (45 giây mỗi lời gọi), `--llm-file-budget` (90 giây mỗi tệp), `--cache-dir`.

## 3. Bản đồ kho

### Thư mục và tệp gốc

| Đường dẫn | Là gì |
|---|---|
| `README.md` | trang vào cửa: hiện trạng từng khâu, thiết kế đề xuất, cài đặt nhanh, bản đồ tài liệu, những điều chưa được chứng minh |
| `requirements.txt`, `pytest.ini`, `conftest.py` | môi trường, cấu hình pytest, đưa gốc repo vào `sys.path` |
| `.gitignore` | bỏ `__pycache__`, `.venv`, `_cache/`, `*.log`, `models/*` (trừ `models/README.md`), `cache/`, `output/` |
| `data/` | dữ liệu đã xử lý (bảng dưới) |
| `docs/` | tài liệu (bảng dưới) và `_chot_samples_phanloaitailieu/` (336 PDF gốc) |
| `models/` | trọng số chạy offline (không commit; `models/README.md`). Mô hình tách trang là ngoại lệ: nằm trong kho ở `teams/team2_splitting/models/` |
| `output/`, `cache/` | kết quả `run_pipeline.py` (chứa nội dung tài liệu) và cache lời gọi LLM; đã nằm trong `.gitignore` |
| `scripts/` | các script dựng dữ liệu (bảng ở mục 5) và hai lệnh vận hành: `run_pipeline.py`, `setup_ocr_models.py` |
| `src/` | mã dùng lại được của đường ống (mục 4) |
| `teams/` | thư mục của từng nhóm: `00_data_and_eval`, `team1_ocr`, `team2_splitting`, `team3_classification`, `team4_extraction` — xem [`teams/README.md`](../teams/README.md) |
| `tests/` | pytest cho `src/`: hợp đồng, taxonomy, cổng luật, cascade và `DocumentClassifier`, TF-IDF, zero-shot, OCR (`test_ocr_pdf`, `test_ocr_errors`), tách (`test_boundary_detector`, `test_splitting_model`, `test_splitting_type_merge`), trích xuất (`test_extractor`, `test_extraction_fields`, `test_extraction_field_result`), pipeline (`test_pipeline`: không GPU, không mạng) và `fixtures/sample_pipeline_fixtures.py` (dữ liệu giả 5 trang của tệp BSR) |

### `data/`

| Tệp | Nội dung |
|---|---|
| `manifest.csv` | một dòng mỗi PDF (336): `doc_id` = `sha1(đường dẫn tương đối)[:12]`, `sha256`, `page_count`, `exact_dup_group`, `template_group`, `folder_label` (nhãn thư mục cũ, **không dùng làm đáp án**)… |
| `duplicate_groups.csv` | các nhóm tệp trùng byte và cùng biểu mẫu |
| `taxonomy_v2.json` | 8 nhóm, 36 mục (34 loại + `OTHER` + `UNREADABLE`), từ khóa, `key_fields`, 25 quy tắc định tuyến |
| `labels_v2.csv` | nhãn theo `doc_id`: `doc_type`, `is_composite`, `segments`, `confidence`, `evidence`, `review_status`, `composite_mixed`, `is_duplicate_of`. **Do mô hình gán, chưa có người duyệt** |
| `splits/` | chia DEV/TEST/composite loại trừ + `README.md` + `splits_meta.json` (sha nhãn) |
| `ocr_v2.jsonl` | OCR cục bộ, mọi trang tới 30 trang/tài liệu, có `source`, `mean_conf`, `flags` (không có hộp tọa độ) |
| `ocr_llm_haiku.jsonl` + `ocr_llm_haiku/` | bản chép của LLM (2 trang đầu mỗi tài liệu) và tệp từng trang + script kiểm chéo |
| `classified_v2/` | bản sao PDF **đã xếp đúng loại** theo nhãn (`<NHÓM>/<LOẠI>/`), `INDEX.csv`, `README.md`; `_CAN_KIEM_TRA/`, `_COMPOSITE_KHAC_LOAI/` |
| `baseline_ocr_335.jsonl` | OCR **cũ** trang 1 bằng engine mất dấu, gắn nhãn thư mục cũ. Giữ để so sánh lịch sử (nguồn `legacy_p1`) |

### `docs/`

| Tệp | Nội dung |
|---|---|
| `LABELING_GUIDELINE.md` | hướng dẫn gán nhãn v1.1 — **nguồn chuẩn** về loại tài liệu và tệp ghép |
| `COMPOSITE_DOCUMENTS_AND_SPLITTING.md` | tệp ghép và tách tài liệu: giải thích nghiệp vụ, số liệu của kho, kết quả đã đo và kết luận toàn trình |
| `PARALLEL_RESEARCH_PLAN.md` | kế hoạch phối hợp 6–8 tuần, giả thuyết H1–H10 và trạng thái, định nghĩa hoàn thành |
| `HANDBOOK_FOR_RESEARCHERS.md` | cẩm nang này |
| `RESEARCH_GUIDE.md` | phương pháp luận chuẩn: câu hỏi nghiên cứu, giao thức đánh giá tóm tắt, quy tắc báo cáo, các mối đe dọa tính hợp lệ, thí nghiệm tiếp theo kèm cỡ mẫu, cách tự làm một thí nghiệm, cách dựng đáp án trường bằng LLM (mục 9.1) |
| `VISUAL_ARCHITECTURE.md` | kiến trúc đo được: sơ đồ luồng, chính sách tách, cascade phân loại, trích xuất và quy tắc tự nhận ngày hết hạn, ngân sách thời gian LLM, triển khai trên một GPU, chi phí, riêng tư, cái nào đã vào `src/` |

### `src/`, `scripts/`, `teams/`

| Đường dẫn | Là gì |
|---|---|
| `src/common/contracts.py` | các lớp Pydantic giữa các nhóm (xem [`teams/README.md`](../teams/README.md) mục 3) |
| `src/common/text_norm.py` | chuẩn hóa văn bản để so khớp từ khóa không phân biệt dấu/khoảng trắng/chữ dính |
| `src/pipeline.py` | bộ điều phối `DocumentPipeline`: OCR → tách → phân loại → gộp theo loại → trích xuất; ngân sách thời gian LLM; quyết định `auto_file` / `needs_human` |
| `src/ocr/` | **đường đã chốt**: `pdf_ocr.py` (text layer hay OCR, `ocr_pdf`), `vietocr_engine.py` (PP-OCRv5 + VietOCR), `configs/`. Cũ: `rapid_ocr.py` (LEGACY, mất dấu), `ios_ocr_client.py` (Apple Vision), `page_heuristics.py` (hai cờ theo từ khóa) |
| `src/splitting/` | `boundary_detector.py` (`split_document`, ba phương pháp), `rules_v2.py`, `page_features.py`, `learned.py` (bộ phân loại cặp trang), `type_merge.py` (gộp lát cắt cùng loại), `policy.py` (chính sách tách: `model+merge`, `triage`, ...) |
| `src/classification/` | `system_one_classifier.py` (cổng luật + Kev), `tfidf_classifier.py`, `doc_classifier.py` (cascade đầu-cuối), `cascade.py` (logic nhận/từ chối và chọn ngưỡng), `llm_backends.py` (Ollama, Kev; hết giờ), `zero_shot.py`, `llm_cache.py`, `taxonomy.py` (nạp `taxonomy_v2.json`) |
| `src/extraction/` | `field_extractor.py` (`FieldExtractor`), `field_rules.py`, `field_llm.py`, `field_vlm.py`, `expiry_rules.py`, `schemas.py`, `field_result.py`, `normalize.py`; cũ: `barb_extractor.py` (GLiNER, yếu), `barb_labels.py` |
| `teams/00_data_and_eval/` | `annotation/`, `eval/` (`harness.py`, `eval_metrics.py`, `eval_splits.py`), `reports/` (01 trùng lặp, 02 taxonomy, 03 giao thức đánh giá), `experiments/01_end_to_end` (toàn trình), `tests/` |
| `teams/team1_ocr/` | `experiments/01_engine_bakeoff`, `02_dataset_v2`, `03_llm_silver`, `07_src_engine`; `gold/` |
| `teams/team2_splitting/` | `gold/` (đáp án ranh giới `boundary_gold_v0.csv`, composite tổng hợp), `experiments/01_rule_baseline` … `05_llm_zero_shot`, `models/` (mô hình cặp trang), `cvlib.py` (cross-fitting) |
| `teams/team3_classification/` | `README.md`; `experiments/01_classical_baselines`, `02_llm_and_cascade` (LLM cục bộ, embedding, cascade có từ chối), `03_src_cascade` (kiểm mã trong `src/`); `results/` (bảng chung `results_table.csv`) |
| `teams/team4_extraction/` | `schema/`, `gold/` (đáp án trường silver, quy trình, báo cáo), `methods/`, `eval/`, `experiments/02_methods` |

## 4. Đường ống hôm nay: cái nào là mã thật, cái nào là kế hoạch

Đã đo = có số trong `RESULTS.md` được liên kết; mọi số về loại, ranh giới và trường là so với **đáp án máy** (chưa người kiểm).

| Khâu | Mã có thật | Trạng thái và số đo |
|---|---|---|
| **OCR** | engine đã chọn (bộ phát hiện DB PP-OCRv5 + VietOCR `vgg_seq2seq`) nằm trong `src/ocr/pdf_ocr.py` và `src/ocr/vietocr_engine.py`; `scripts/build_ocr_dataset.py` gọi lại module này. Trọng số đặt ở `models/ocr/` (không commit, xem `models/README.md`). `src/ocr/rapid_ocr.py` là **engine cũ làm mất dấu**, giữ lại với nhãn LEGACY — đừng dùng để tạo số liệu mới. `ios_ocr_client.py` gọi máy chủ Apple Vision, không thuộc đường on-prem đã chọn | **đã vào `src/`**; kiểm hồi quy trên GPU: 8/8 trang giống `data/ocr_v2.jsonl` từng ký tự, trên CPU 3/8 trang lệch 1–2 ký tự ([`07_src_engine/RESULTS.md`](../teams/team1_ocr/experiments/07_src_engine/RESULTS.md)). Chạy offline mới kiểm bằng cách chặn kết nối trong tiến trình. CER trên bản quét thật: chưa đo |
| **Tách tài liệu** | `src/splitting/`: `split_document(doc, method="rule" \| "rule_v2" \| "model" \| "none")`; `type_merge.py` gộp lát cắt cùng loại; `policy.py` đặt chính sách. **Mặc định của pipeline: `model+merge`** (bộ phân loại cặp trang ngưỡng 0,7, gộp cùng loại trừ `BB_LAY_MAU` và ranh giới điểm ≥ 0,99); thay thế: `triage`. `split_document` đứng riêng vẫn mặc định `rule` (hành vi cũ) | **đã đo** riêng từng phương pháp ([README nhóm 2](../teams/team2_splitting/README.md)): luật cũ cắt vụn 105/155 tệp nhiều trang không ghép, luật v2 70/155, bộ phân loại cặp trang 26/155. **Đã đo toàn trình** ([báo cáo](../teams/00_data_and_eval/experiments/01_end_to_end/RESULTS.md)): tách không tăng tỉ lệ tệp đúng, tăng tài liệu giao đúng. Đáp án ranh giới là bản máy; composite chỉ 19 tệp dev và 2 tệp TEST. Giai đoạn 3: tùy chọn `model+merge+id` (bản khác): cùng loại 0/7 → 4/7 ranh giới, **không phải mặc định**; khi dùng `model+merge` quy tắc này chạy bóng và chuyển tệp sang người ([`06_same_type`](../teams/team2_splitting/experiments/06_same_type/RESULTS.md)) |
| **Phân loại** | `src/classification/doc_classifier.py` chạy đầu-cuối `DocumentSlice → ClassificationResult`: cổng luật từ khóa → TF-IDF (`tfidf_classifier.py`, mô hình lưu ở `models/classification/`) → LLM cục bộ (`llm_backends.py`, `zero_shot.py`) → chuyển người kèm gợi ý; quyết định nhận/từ chối ở `cascade.py`. Tầng Kev của `CascadedClassifier` đã sửa nhưng tắt mặc định và chưa đo lại | cổng luật, baseline học, Kev-0.8B, Qwen cục bộ và cascade **đã đo** ([README nhóm 3](../teams/team3_classification/README.md)); mã trong `src/` cho quyết định trùng 237/237 tài liệu DEV với thí nghiệm 02 ([`03_src_cascade/RESULTS.md`](../teams/team3_classification/experiments/03_src_cascade/RESULTS.md)). Trên tệp ghép khác loại, điểm nghẽn là phân loại lát cắt (2/8 tệp có mọi tài liệu đúng loại dù tách đúng 8/8) — giả thuyết từ 8 tệp |
| **Trích xuất** | `src/extraction/field_extractor.py` (`FieldExtractor`): luật/regex + LLM cục bộ theo schema của **21 loại** tài liệu (4 loại có luật riêng, 17 loại giai đoạn 3 dùng luật ngày chung `generic_date_rules.py`), lọc dữ liệu cá nhân. `field_vlm.py` (đọc ảnh trang): **pipeline đã dựng ảnh trang** (PyMuPDF, thư mục tạm, bật mặc định, `--no-vlm` để tắt). Quy tắc tự nhận ngày hết hạn (4 loại cũ: một mô hình đọc trùng ngày trong tên tệp; 17 loại mới: `regex=llm`) có trong mã nhưng **TẮT mặc định** (`--auto-accept-expiry` để bật): mọi hạn là `needs_review` kèm gợi ý, quy tắc chỉ ghi `_expiry_would_accept`. `BarbEntityExtractor` (GLiNER) giữ lại, không dùng để điền trường | **đã đo** trên 4 loại với đáp án silver do LLM đọc ảnh ([kết quả](../teams/team4_extraction/experiments/02_methods/RESULTS.md)): F1 0,90 khi so khớp nới lỏng trên TEST (n = 22); ngày hết hạn tự nhận 12/16, sai 0. Qua cả chuỗi dev: tự nhận 32/66 không ảnh, **37/66 có ảnh**, sai 0 ([`02_chain_with_images`](../teams/00_data_and_eval/experiments/02_chain_with_images/RESULTS.md)). 17 loại mới (84 đơn vị silver v2): F1 mềm 0,75 (LLM), 0,83 (VLM); tự nhận hạn ngoài mẫu chỉnh 12/17, 0 sai, cận trên 22% ([`03_unseen_types`](../teams/team4_extraction/experiments/03_unseen_types/RESULTS.md)). 13 loại còn lại chưa có schema |
| **Định tuyến** (loại + thực thể → hồ sơ đích) | 25 quy tắc dạng dữ liệu trong `taxonomy_v2.json`; không có mã. Quyết định tự xếp / chuyển người đã có trong pipeline (`SliceRouting`, `FileRoutingSummary`) | kế hoạch |
| **Điều phối toàn trình** | `src/pipeline.py` + `scripts/run_pipeline.py <pdf>`: OCR → tách → phân loại → gộp → trích xuất, ghi thời gian từng khâu và quyết định "tự xếp / chuyển người" cho từng lát cắt và cả tệp; hết giờ mỗi lời gọi LLM, ngân sách 90 giây mỗi tệp, mạch ngắt; tệp > 30 trang chuyển người (lý do `truncated_pages`); `--auto-accept-expiry`, `--title-tiebreak`, `--no-vlm` | **đã đo** theo tệp (dev 245, TEST 59) và chi phí ([báo cáo](../teams/00_data_and_eval/experiments/01_end_to_end/RESULTS.md)); chi phí có OCR thật đo trên 30 tệp / 90 trang: ~500 trang/giờ/máy (khoảng 250–860), GPU dùng chung, một lần chạy ([`03_end_to_end_v2`](../teams/00_data_and_eval/experiments/03_end_to_end_v2/RESULTS.md)); sai lặng lẽ ≤ 1% chưa đạt |
| **Hàng đợi người duyệt, ERP, nhắc hạn, giao diện** | không có | kế hoạch (cần quyết định của doanh nghiệp) |

Các tầng đều phải nói thật: `ClassificationResult.tier` là `rule`/`tfidf`/`kev`/`llm`/`human`/`none`, `model_name` ghi engine thực sự đã chạy, `confidence_kind` phân biệt xác suất của mô hình với điểm của luật; `DocumentSlice.boundary_method` ghi phương pháp tách đã chạy (có hậu tố `+type_merge` khi đã gộp). Không dùng Kev khi nó không chạy.

## 5. Cách chạy từng script và bộ test

Chạy từ gốc repo. Cột "Đã kiểm" cho biết điều đã làm khi viết cẩm nang.

| Lệnh | Việc | Ghi đè | Đã kiểm |
|---|---|---|---|
| `.venv\Scripts\python.exe -X utf8 -m pytest -q` | test của `src/` (327 test qua ngày 2026-10-16) | không | đếm bằng `--collect-only`; số có thể tăng khi nhóm khác thêm test |
| `... -m pytest teams\00_data_and_eval\tests -q` | 33 test của bộ chấm và manifest | không | đếm bằng `--collect-only`; lần chạy 2026-10-16: 33 qua |
| `... scripts\setup_ocr_models.py` | in OK/THIẾU cho 3 tệp mô hình OCR; chép từ máy đã chạy OCR (`--download` cần mạng) | `models/ocr/` khi chép | đọc báo cáo 07 |
| `... scripts\train_tfidf_classifier.py` | huấn luyện TF-IDF trên DEV → `models/classification/` (vài giây) | thư mục đó | đọc báo cáo 03 |
| `... scripts\run_pipeline.py <tệp.pdf> --out output\pipeline` | chạy cả chuỗi trên một PDF (xem "Ngày đầu tiên") | `output\pipeline` | `--help`; chạy thật có ở báo cáo 07 mục 5 và báo cáo toàn trình |
| `... scripts\build_manifest.py` | quét 336 PDF → `data/manifest.csv`, `data/duplicate_groups.csv`, `01_duplicates_stats.json` (~20–30 giây theo báo cáo 01) | các tệp đó | `--help` |
| `... teams\00_data_and_eval\make_duplicates_report.py` | sinh lại `reports/01_duplicates.md` | báo cáo | có tệp |
| `... teams\00_data_and_eval\annotation\build_packets.py --parts 3 --seed 7` | gói gán nhãn cho annotator B từ `ocr_llm_haiku.jsonl` | `annotation/packets/` | `--help` |
| `... teams\00_data_and_eval\annotation\agreement.py` | κ, `disagreements.csv`, `agreement_summary.json` | `annotator_B_sonnet.csv` (gộp lại từ các `part*.csv`) | có tệp |
| `... scripts\build_labels_v2.py` | hợp nhất A + B + `adjudication.csv` → `data/labels_v2.csv`; thoát mã 1 nếu còn bất đồng chưa phân xử | `data/labels_v2.csv` | đọc mã |
| `... scripts\build_classified_folder.py` | dựng `data/classified_v2/` | thư mục đó | `--help` |
| `... scripts\build_ocr_dataset.py --limit 3` | thử OCR 3 tài liệu (không ghi đè `--out`); đầy đủ: `--device cuda:0 --workers 6 --threads 2 --resume`, ~46 phút | `data/ocr_v2.jsonl` (chỉ khi chạy đầy đủ) | `--help` |
| `... scripts\assemble_llm_ocr.py` | ghép `data/ocr_llm_haiku/pages/*.txt` → `data/ocr_llm_haiku.jsonl` | tệp đó | `--help` |
| `... teams\team1_ocr\experiments\03_llm_silver\score_llm_transcripts.py` | chấm bản chép LLM với text layer | CSV trong thư mục | có tệp |
| `... teams\team1_ocr\experiments\01_engine_bakeoff\eval_on_gold.py --engines viet_seq2seq_cpu` | CER/WER trên gold OCR (cần `gold/transcripts/`, chưa có) | `gold_eval.csv` | `--help` |
| `... teams\team3_classification\experiments\01_classical_baselines\run_all.py --labels data\labels_v2.csv --jobs 16` | baseline cổ điển, giai đoạn DEV (~8 phút với `--jobs 28`); `--final-test` chấm TEST đúng một lần | `results/`, thêm dòng vào `results_table.csv`. `data/splits/` là tập chia đã khóa: chỉ bị ghi đè khi truyền `--rebuild-splits` (TEST đổi, mọi số TEST cũ phải chấm lại) | đọc báo cáo |
| `... scripts\evaluate_classifier_baseline.py --input data\ocr_v2.jsonl --labels data\labels_v2.csv --kev-endpoint ""` | chấm bộ phân loại có sẵn trong `src/` (cổng luật + Kev). Với `--labels` script chấm theo loại v2 (ghép theo `doc_id`, bỏ bản trùng byte và tệp ghép khác loại); không có `--labels` thì nhãn thật là **nhãn thư mục cũ**, chỉ để tái lập baseline cũ. Bản ghi có nhãn thư mục rỗng (2 PDF ở gốc) được bỏ qua và đếm, không còn gây lỗi. `--kev-endpoint ""` để chỉ chấm cổng luật. Để so sánh mô hình vẫn dùng harness | `--out`; mặc định là `teams/team3_classification/results/rule_gate_runs/<tên đầu vào>__<bộ nhãn>/`, không còn ghi đè thư mục lịch sử `rule_gate_baseline/` | chưa chạy lại sau khi script được sửa |
| **`scripts\generate_baseline_ocr.py`** | **ĐỪNG CHẠY.** Sinh lại OCR cũ (engine mất dấu) và **ghi đè** `data/baseline_ocr_335.jsonl`. Nay script từ chối chạy nếu không có `--force` (in thông báo, thoát mã 2). Trước đây nó không có `--help` và chạy thật với mọi tham số; tệp đã từng bị ghi đè theo cách đó (khôi phục bằng `git checkout -- data/baseline_ocr_335.jsonl`) | `data/baseline_ocr_335.jsonl` (chỉ khi có `--force`) | — |

Các thí nghiệm dài (không chạy khi viết cẩm nang; lệnh và thời gian ghi ở mục "Cách chạy lại" của README nhóm và mục "Lệnh" của từng `RESULTS.md`): tách `teams\team2_splitting\experiments\0N_*\run.py` (từ khoảng 1 phút tới 8–15 phút cho 04); trích xuất `teams\team4_extraction\experiments\02_methods\run_methods.py` (có cache, tuần tự); toàn trình `teams\00_data_and_eval\experiments\01_end_to_end\run.py --stage dev` (thêm `--call-llm` để gọi Ollama, khoảng 10 phút theo báo cáo). Ba lệnh chấm TEST (`--final-test`) chỉ chạy được **một lần**, có sổ đăng ký chặn lần hai.

Ví dụ nhanh từng khâu (đã chạy):

```powershell
# Tách: ví dụ chuẩn 5 trang, đáp án đúng là 4 lát. Kết quả quan sát: rule -> 5 lát, rule_v2 và model -> 4 lát
.venv\Scripts\python.exe -X utf8 -c "from src.splitting.boundary_detector import split_document; from tests.fixtures.sample_pipeline_fixtures import MOCK_OCR_DOCUMENT_BSR as d; [print(m, [(s.start_page, s.end_page) for s in split_document(d, m).slices]) for m in ('rule', 'rule_v2', 'model')]"
# Phân loại bằng cổng luật (Kev tắt): in loại, tầng, độ tin cậy kiểu heuristic
.venv\Scripts\python.exe -X utf8 -c "from src.classification.system_one_classifier import CascadedClassifier; from src.common.contracts import DocumentSlice; s=DocumentSlice(slice_id='s1',start_page=1,end_page=1,page_count=1,combined_text='CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nHỢP ĐỒNG ĐẠI LÝ BÁN LẺ XĂNG DẦU'); r=CascadedClassifier().classify_slice(s); print(r.predicted_category, r.tier, r.model_name, r.confidence, r.confidence_kind)"
```
Kết quả quan sát khi Kev tắt: `HD_NHUONG_QUYEN_DAI_LY rule keyword_rule_gate 0.9 heuristic`.

Dùng bộ chấm trong Python để so sánh mô hình (quy ước ở giao thức, mục 9):

```python
import sys; sys.path.insert(0, "teams/00_data_and_eval/eval")
from harness import *
bench = load_benchmark("data/labels_v2.csv")            # đơn vị = tài liệu duy nhất, loại composite hỗn hợp
print(bench.s_classes, available_sources())             # lớp Track S; nguồn văn bản: legacy_p1, haiku_p1, haiku_p12, ocr_v2_p1, ocr_v2_p12
```

## 6. Bắt đầu một thí nghiệm mới (công thức 8 bước)

1. Viết **một câu hỏi** có thể trả lời bằng số (ví dụ "văn bản `ocr_v2` có làm giảm tỉ lệ tự xếp hồ sơ so với Haiku không?").
2. Tạo `teams/<nhóm>/experiments/NN_ten/`; đặt script trong đó. Đọc nhãn qua tham số `--labels data\labels_v2.csv`.
3. Nạp dữ liệu bằng `harness` (`load_benchmark`, `load_or_make_splits`, `load_documents`). Không tự chia dữ liệu.
4. Mọi lựa chọn (đặc trưng, tham số, ngưỡng, prompt) làm bằng CV trên **DEV**. Không mở TEST.
5. Ghi kết quả: `append_result_row(...)` vào bảng chung và `RESULTS.md` có lệnh chạy chính xác.
6. Chốt cấu hình trước khi mở TEST; chấm TEST **một lần** bằng lệnh riêng; báo khoảng tin cậy và so sánh ghép cặp.
7. Trong `RESULTS.md` tách ba phần: **đo được** / **suy luận** / **chưa đo**, và nêu nhãn (tệp + sha), nguồn văn bản, mô hình thật sự đã chạy.
8. Chạy lại từ đầu bằng một lệnh trên máy sạch trước khi báo xong.

## 7. Mười quy tắc làm việc (rút ra từ chính những sai lầm đã gặp)

1. **Nhãn là loại tài liệu theo nội dung, không phải thư mục.** Thư mục là tủ hồ sơ: 27 trong 30 nhóm trùng byte nằm ở hai thư mục khác nhau (một tờ giấy, hai đáp án), và thư mục "THUE KHO" không có hợp đồng thuê kho nào.
2. **Khử trùng trước khi chia.** Đơn vị đánh giá là 304 tài liệu duy nhất, không phải 336 tệp; bản sao cùng nhãn và cùng phía chia.
3. **Chia có nhóm theo biểu mẫu.** Cùng biểu mẫu không được nằm hai phía train/test. Chia nghiêm ngặt cho thấy hai loại lớn (`CC_TAP_HUAN_VC_HNH`, `PHIEU_XUAT_KHO`), vốn chỉ có một biểu mẫu, rơi về recall 0,05 và 0,00 — khả năng tổng quát hóa sang biểu mẫu mới **chưa được chứng minh**.
4. **TEST khóa.** Mỗi cấu hình đã chốt chấm TEST đúng một lần. Nhìn điểm TEST rồi chỉnh là tự lừa mình; nếu đã làm, TEST đã "cháy".
5. **Không con số nào không có script.** Mọi số trong báo cáo sinh từ một lệnh nằm trong `RESULTS.md`. Số ghi tay không được chấp nhận.
6. **Lỗi phải hiện ra, không bao giờ mặc định im lặng.** Baseline cũ từng chạy luật từ khóa mà vẫn tự báo là mô hình Kev; thông báo lỗi OCR từng bị đem đi phân loại như văn bản thật. Kết quả rỗng không phải thành công; `status`, `tier`, `error` phải đúng.
7. **Nói mô hình nào tạo ra con số.** Ghi engine/mô hình/phiên bản/ngày; không gọi "Kev" khi Kev tắt; phân biệt điểm của luật với xác suất của mô hình.
8. **Đầu ra của LLM chỉ là bản nháp cho tới khi được kiểm.** Một đợt chép chữ từng phải làm lại vì tác nhân chép chữ cho 12 trang mà ảnh của chúng nạp lỗi (theo ghi nhận khi thực hiện; chưa có log trong kho). Hai mô hình cùng họ đồng thuận 304/304 không chứng minh nhãn đúng; đáp án trường dựng bằng LLM cũng vậy (Haiku bị người phân xử coi là sai ở 10/58 = 17,2% số mục được nghi; `RESEARCH_GUIDE.md` mục 9.1). Luôn chấm bằng đáp án đã biết, và để người kiểm vùng viết tay/con dấu.
9. **Riêng tư.** PDF, văn bản OCR/bản chép, CSV lỗi đều có tên, số căn cước, số giấy phép lái xe, mã số thuế, số tài khoản. Chỉ trong kho riêng tư và máy nội bộ; không dán vào chat/issue/báo cáo; chỉ **bộ mẫu này** được gửi LLM ngoài (chủ dự án đã đồng ý); bản chạy thật là on-premise.
10. **Viết `RESULTS.md` như thể người khác sẽ chạy lại và phản biện.** Nêu cỡ mẫu, khoảng tin cậy, hạn chế; khi khoảng tin cậy của hiệu chứa 0 thì viết "không tách được hai phương pháp"; chưa đo thì viết "chưa đo".

## 8. Từ điển thuật ngữ

| Thuật ngữ | Nghĩa trong dự án |
|---|---|
| **OCR** | nhận dạng chữ từ ảnh trang |
| **text layer / born-digital** | lớp chữ có sẵn trong PDF do máy tạo (không cần OCR); bản quét thường không có (94,9% trang của kho không có) |
| **CER / WER** | tỉ lệ lỗi ký tự / từ = khoảng cách Levenshtein chia độ dài đáp án; thấp là tốt. Nhạy với thứ tự đọc ở bảng, nên dùng thêm `bag_recall`/`bag_f1` (so theo túi từ, không phụ thuộc thứ tự) |
| **diac_recall** | tỉ lệ ký tự có dấu tiếng Việt được giữ lại so với đáp án |
| **macro-F1** | trung bình F1 của các lớp, mỗi lớp một phiếu; không bị lớp lớn lấn át. Chỉ có nghĩa khi mỗi lớp đủ mẫu |
| **κ (Cohen kappa)** | mức đồng thuận giữa hai người gán nhãn đã trừ phần trùng do ngẫu nhiên; 1,0 là trùng hoàn toàn. Không chứng minh nhãn đúng, chỉ chứng minh hai bên nhất quán |
| **bootstrap CI** | khoảng tin cậy bằng cách lấy mẫu lại theo tài liệu nhiều lần; nêu mức sai số của con số do cỡ mẫu nhỏ |
| **so sánh ghép cặp** | bootstrap trên hiệu của hai phương pháp cùng mẫu lại; hiệu có khoảng tin cậy chứa 0 → "không tách được" |
| **composite** | tệp PDF chứa từ hai tài liệu logic trở lên; *khác loại* hoặc *cùng loại* |
| **segment** | một đoạn trang liên tiếp của một tài liệu logic, ghi `1-2:LOẠI` |
| **ranh giới** | vị trí giữa hai trang liên tiếp mà trang sau mở đầu một tài liệu mới |
| **zero-shot** | dùng mô hình/prompt có sẵn, không huấn luyện trên dữ liệu của mình |
| **cascade (tầng)** | chuỗi phương pháp từ rẻ đến đắt: cổng luật → mô hình → người; mỗi tầng chỉ nhận ca mà tầng trước không quyết định được |
| **abstain** | từ chối quyết định (trả `UNKNOWN`, chuyển người duyệt) thay vì đoán |
| **auto-file rate** | tỉ lệ tài liệu hệ thống tự xếp hồ sơ mà tỉ lệ sai trong phần đã nhận ≤ mức đặt (ví dụ 1%). Phải báo kèm *chứng minh được gì*: 0 lỗi trong n tài liệu chỉ cho cận trên ≈ 3/n |
| **DEV / TEST** | DEV để chọn mô hình bằng CV; TEST khóa, chấm một lần |
| **Track S / Track Z** | S: có huấn luyện, chỉ các loại đủ ≥ 10 tài liệu + lớp gộp `RARE_OR_OTHER`; Z: zero-shot trên toàn taxonomy |
| **silver vs gold** | *gold* = đáp án do người làm hoặc kiểm; *silver* = bản nháp do máy/LLM tạo, đã đo độ tin cậy nhưng chưa người kiểm. Silver không thay được gold ở số liệu cuối |
| **template group** | các tài liệu cùng một biểu mẫu (khác khách hàng/ngày); không được nằm hai phía train/test |
| **Kev / Jev, `Choice` / `Noul`** | mô hình quyết định nhanh; `Choice` chọn 1 trong N lớp kèm xác suất, `Noul` đúng/sai kèm xác suất. Chạy cục bộ ở `127.0.0.1:8009` |
| **GLiNER** | mô hình trích thực thể theo nhãn đưa vào lúc chạy; `belumind/barb-1-ie-vi` cho tiếng Việt |
| **lát cắt (slice)** | một đoạn trang liên tiếp mà bộ tách coi là một tài liệu; `DocumentSlice` |
| **chính sách tách** | cách tách của pipeline: `model+merge` (mặc định), `triage`, `none`, `rule`, `rule_v2`, `model` (`src/splitting/policy.py`) |
| **tệp đúng hoàn toàn / tài liệu giao đúng và tự động** | đo cấp tệp: các lát cắt đúng bằng các đoạn đáp án và mọi tài liệu được tự nhận đúng loại; đo cấp tài liệu: tài liệu đáp án có lát cắt đúng khoảng trang, được tự nhận đúng loại trong tệp tự xử lý hoàn toàn |
| **sai lặng lẽ** | tệp hệ thống tự xử lý hoàn toàn mà kết quả sai (không báo người) |
| **cross-fitting** | điểm của mô hình có học trên DEV được tính bằng mô hình không thấy tài liệu đó (5 fold theo nhóm biểu mẫu), để chuỗi nhiều khâu không bị rò rỉ |
| **phân xử (adjudication)** | người đọc thứ ba (ở đây là mô hình mạnh hơn, không phải người thật) chọn giữa hai bản đọc khác nhau, không biết ai đọc bản nào |
| **VLM** | mô hình đọc ảnh trang trực tiếp, không qua OCR (ở đây Qwen3.5-4B qua Ollama) |
| **`needs_review`** | trạng thái của trường hạn không đủ điều kiện tự nhận: để trống, chuyển người, kèm ngày gợi ý |
| **ECE, Brier** | đo độ hiệu chỉnh của xác suất; ECE thấp nghĩa là "chắc 80%" thì đúng khoảng 80% |
| **risk-coverage** | đường cong: nhận càng nhiều tài liệu (coverage) thì tỉ lệ sai (risk) trên phần được nhận thay đổi thế nào |

## 9. Hỏi ai, đọc gì

- Hiểu một loại tài liệu: [`LABELING_GUIDELINE.md`](LABELING_GUIDELINE.md) mục 6, và xem các tệp ví dụ trong `data/classified_v2/<NHÓM>/<LOẠI>/`.
- Hiểu vì sao chia dữ liệu như vậy: [`teams/00_data_and_eval/reports/03_evaluation_protocol.md`](../teams/00_data_and_eval/reports/03_evaluation_protocol.md).
- Mẫu một báo cáo thí nghiệm tốt: [`teams/team1_ocr/experiments/01_engine_bakeoff/RESULTS.md`](../teams/team1_ocr/experiments/01_engine_bakeoff/RESULTS.md).
- Việc của nhóm bạn: README trong `teams/<nhóm>/`.
- Câu hỏi về nhãn, chia dữ liệu, câu trả lời của doanh nghiệp: nhóm `00_data_and_eval`.
