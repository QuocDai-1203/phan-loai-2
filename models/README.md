# `models/` — mô hình cần có để chạy OFFLINE

Thư mục này **không được commit** (xem `.gitignore`: chỉ tệp README này được theo dõi). Máy triển khai không có mạng, nên mọi thứ dưới đây phải có sẵn trước khi chạy `scripts/run_pipeline.py`. Thiếu tệp nào, mã dừng với thông báo nêu rõ cần đặt tệp gì ở đâu; mã **không** tự tải gì từ mạng và **không** âm thầm đổi sang engine khác.

## 1. Bảng tóm tắt

| Đường dẫn | Là gì | Ai đọc | Cách có được / dựng lại |
|---|---|---|---|
| `models/ocr/vietocr/vgg_seq2seq.pth` | Trọng số bộ nhận dạng VietOCR `vgg_seq2seq` (89,6 MB) | `src/ocr/vietocr_engine.py` | Chép từ máy đã chạy OCR (`%TEMP%\vgg_seq2seq.pth`) bằng `scripts\setup_ocr_models.py`; máy có mạng: thêm `--download` (tải một lần từ `vocr.vn`). Giấy phép trọng số chưa được xác nhận (xem `teams/team1_ocr/README.md` T4 bước 4) |
| `models/ocr/rapidocr/ch_PP-OCRv5_det_mobile.onnx` | Mô hình phát hiện dòng chữ PP-OCRv5 của rapidocr (4,8 MB) | `src/ocr/vietocr_engine.py` | `scripts\setup_ocr_models.py` chép từ `<venv>\Lib\site-packages\rapidocr\models\` (nơi rapidocr tự tải vào lần chạy đầu có mạng) |
| `models/classification/tfidf_word_cnb_raw_C0.1/{model.joblib,meta.json}` | Bộ TF-IDF + ComplementNB đã chốt, huấn luyện trên **DEV** | `src/classification/tfidf_classifier.py` | `.venv\Scripts\python.exe -X utf8 scripts\train_tfidf_classifier.py` (cần `data/labels_v2.csv`, `data/ocr_v2.jsonl`, `data/splits/`; chạy vài giây, CPU) |

Cấu hình suy diễn của VietOCR (`vgg_seq2seq.yml`) **được kèm trong kho** tại `src/ocr/configs/vgg_seq2seq.yml` (nhỏ, có version control). Thư viện `vietocr` mặc định tải tệp này từ `vocr.vn` **mỗi lần khởi động**, nên không chạy được khi mất mạng; mã của chúng ta nạp từ tệp cục bộ. Tệp kèm trong kho được dựng lại bằng tay và kiểm bằng phép so khớp văn bản đầu ra với `data/ocr_v2.jsonl` — xem `teams/team1_ocr/experiments/07_src_engine/RESULTS.md`. Nếu thả một tệp `models/ocr/vietocr/vgg_seq2seq.yml`, tệp đó được ưu tiên.

Biến môi trường `SDH_OCR_MODELS_DIR` đổi thư mục gốc của mô hình OCR (mặc định `models/ocr`).

## 2. Những thứ nằm ngoài `models/` nhưng cũng cần có offline

| Thứ | Dùng cho | Ghi chú |
|---|---|---|
| Ollama ở `127.0.0.1:11434` có mô hình `qwen3.5:4b` | Tầng 3 của cascade (mặc định) | `ollama pull qwen3.5:4b` một lần khi có mạng. Không có Ollama: `run_pipeline.py --no-llm` (tài liệu chưa nhận → người) |
| Kev ở `127.0.0.1:8009` | Tầng 3 tùy chọn (`--llm kev`) | Tên mô hình ghi vào kết quả lấy từ `/api/status` của máy chủ. Kev-0.8B chỉ dùng tên loại làm tiêu chí |
| `teams/team2_splitting/models/pair_gb_v0.joblib` (+ `.json` kiểm sha256) | Tách tệp ghép, chính sách mặc định `model+merge` | Có trong kho (không nằm trong `models/`). Thiếu tệp thì bộ tách báo lỗi, không âm thầm quay về luật |
| Mô hình GLiNER `belumind/barb-1-ie-vi` trong cache Hugging Face | **Không còn cần cho đường ống**: từ 2026-10-12 pipeline trích xuất bằng `FieldExtractor` (luật + LLM cục bộ qua Ollama). Chỉ cần nếu tự gọi `BarbEntityExtractor` | GLiNER đo được là quá yếu để điền trường (xem `teams/team4_extraction/experiments/02_methods/RESULTS.md`) |
| `data/taxonomy_v2.json` | Nhãn, từ khóa luật, mô tả cho LLM | Có trong kho |
| `teams/team3_classification/results/02_llm_and_cascade/tables/dev_selection_02.json` | Ngưỡng cascade (`th_s`, `th_llm`) | Có trong kho. `DocumentClassifier` ghi sha1 của tệp này vào cấu hình |
| `cache/llm/` (tự tạo) | Cache lời gọi LLM theo (mô hình + toàn bộ yêu cầu) | Không bắt buộc; xóa được. Có cache thì chạy lại cùng tài liệu không gọi lại mô hình |
| `src/extraction/schema_data/*.json` (21 schema + `pii_fields.json`, có trong kho) | Schema trích xuất của 21 loại (4 loại giai đoạn 2 + 17 loại giai đoạn 3) | `src/extraction/schemas.py`; bản gốc của nhóm 4 ở `teams/team4_extraction/schema/`, test kiểm hai bản giống nhau |
| `qwen3.5:4b` có thị giác (cùng mô hình Ollama với tầng 3) | Nguồn VLM đọc ảnh trang cho trường hạn (bật mặc định, `--no-vlm` để tắt) | Không cần mô hình thêm. Lời gọi VLM cache ở `_cache/ollama` / `cache/llm`: **cache chứa giá trị trường trích xuất (có thể có họ tên)**, đặt trên ổ mã hóa, xóa theo hạn (ví dụ 30 ngày), không sao lưu ra ngoài (báo cáo 04, mục 9). Khóa cache gồm **tên** mô hình, chưa gồm digest: nếu ai đó `ollama pull` bản mới cùng tên thì cache trả câu trả lời của mô hình cũ mà không báo (việc ưu tiên 12) |

## 3. Kiểm tra nhanh trước khi triển khai

```powershell
$py = ".venv\Scripts\python.exe"
& $py -X utf8 scripts\setup_ocr_models.py          # in OK/THIẾU cho 3 tệp OCR, không dùng mạng
& $py -X utf8 -c "from src.classification.tfidf_classifier import TfidfClassifier as T; m=T.load(); print(m.meta.labels_sha1_10, m.meta.n_train, m.meta.sklearn_version)"
& $py -X utf8 scripts\run_pipeline.py <tệp.pdf> --no-llm --no-extract --out output\pipeline    # chạy được khi tắt mạng và tắt Ollama
```

## 4. Siêu dữ liệu của mô hình TF-IDF (`meta.json`)

`config`, `classes` (Track S), `labels_file` + `labels_sha1_10` (nhãn dùng để huấn luyện), `text_source` (`ocr_v2_p12`), `train_split` (`DEV`), `train_doc_ids` (danh sách `doc_id`, chỉ DEV), `n_train`, `class_counts`, `sklearn_version`, `numpy_version`, `python_version`, `created_at`, `model_sha256`. Nạp mô hình kiểm checksum (sai → `TfidfModelError`) và cảnh báo khi phiên bản scikit-learn khác lúc huấn luyện. `model.joblib` là pickle: **chỉ nạp tệp do chính mình huấn luyện**, đừng nhận từ nguồn không tin cậy.

Huấn luyện lại bắt buộc khi: nhãn đổi (T2 của nhóm 3), nâng scikit-learn, hoặc đổi engine OCR (văn bản huấn luyện phải cùng nguồn với văn bản lúc chạy).
