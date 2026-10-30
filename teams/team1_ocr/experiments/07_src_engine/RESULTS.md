# Thí nghiệm 07 — Engine OCR đã chốt chuyển vào `src/ocr/` và pipeline đầu-cuối (Nhóm 1, việc T4 bước 1–2)

> **Đọc trước.** Thí nghiệm này không đo chất lượng OCR mới. Nó kiểm hai điều: (1) mã trong `src/ocr/` cho **cùng văn bản** với `data/ocr_v2.jsonl` (bộ dữ liệu dựng bằng engine đã chốt ở [`01_engine_bakeoff`](../01_engine_bakeoff/RESULTS.md)); (2) engine chạy được từ thư mục mô hình cố định mà không cần mạng. Mọi con số chất lượng OCR (CER, `bag_recall`...) vẫn là của 01 và 02; **CER trên scan thật vẫn chưa đo** (chưa có gold, xem README nhóm 1 T1).
> Mọi số đo thời gian bên dưới đo **trên máy dùng chung** (RTX 3060 12 GB đang chạy việc khác, Ollama và Kev đã nạp mô hình, CPU bận): chỉ là mức độ lớn, không phải thông lượng của máy sản xuất. Tài liệu được gọi bằng `doc_id`.
> Ngày chạy: 2026-10-12. Phiên bản: `rapidocr` 3.10.0, `vietocr` 0.3.13 (`vgg_seq2seq`), PyMuPDF 1.28.0, torch 2.14.0+cu126, scikit-learn 1.9.1, Python 3.13.

## 1. Cái gì đã đổi

| Trước | Sau |
|---|---|
| Engine đã chốt chỉ ở `scripts/build_ocr_dataset.py`; `src/ocr/rapid_ocr.py` dùng engine cũ (mất dấu) | `src/ocr/vietocr_engine.py` (engine: phát hiện dòng PP-OCRv5 + VietOCR, tự xoay, chuẩn hóa nền), `src/ocr/pdf_ocr.py` (quy tắc text layer, `ocr_page`, `ocr_pdf` → `OCRDocumentResult`). `scripts/build_ocr_dataset.py` **import** từ đó (không còn bản sao logic). `rapid_ocr.py` còn, đánh dấu **LEGACY** + `DeprecationWarning` |
| Trọng số VietOCR ở `%TEMP%\vgg_seq2seq.pth` (có thể bị dọn) | `models/ocr/vietocr/vgg_seq2seq.pth` (89,6 MB, sha256 bắt đầu `0921503a`) — bản sao byte-giống-hệt của tệp trong `%TEMP%` |
| Mô hình phát hiện dòng nằm trong `<venv>\Lib\site-packages\rapidocr\models\` (rapidocr tự tải vào đó ở lần chạy đầu có mạng) | chép ra `models/ocr/rapidocr/ch_PP-OCRv5_det_mobile.onnx` (4,8 MB) và truyền `Det.model_path` |
| Cấu hình VietOCR **tải từ `vocr.vn` mỗi lần khởi động** (`Cfg.load_config_from_name`) | nạp từ `src/ocr/configs/vgg_seq2seq.yml` (xem mục 4) |
| Thiếu tệp → lỗi khó hiểu hoặc âm thầm tải | `OcrModelsMissingError` liệt kê **mọi** tệp thiếu, chỗ đặt, cách có được (`scripts/setup_ocr_models.py`, [`models/README.md`](../../../../models/README.md)); `SDH_OCR_MODELS_DIR` đổi thư mục gốc |
| Hợp đồng `OCRPageResult` không có độ tin cậy, cờ xoay/nền, nguồn "lớp chữ nhúng bị loại" | thêm `mean_conf`, `flags`, `source = embedded_ocr_layer+ocr` (nhật ký thay đổi #1 ở `teams/README.md` mục 6) |

Lỗi không bị nuốt: lỗi một trang → `OCRPageResult.error` khác `None`, `full_text` rỗng, `OCRDocumentResult.error = "Trang N: ..."`, các trang khác vẫn chạy; tệp không mở được → `error = "open_failed: ..."`, `total_pages = 0` (test: `tests/test_ocr_pdf.py`).

## 2. Lệnh chạy chính xác

```powershell
$py = ".venv\Scripts\python.exe"
$S  = "teams\team1_ocr\experiments\07_src_engine"
& $py -X utf8 scripts\setup_ocr_models.py                                   # in OK/THIẾU cho 3 tệp mô hình, không dùng mạng
$docs = "741b37405405","91e3dcb5fa4e","5139035b5c3f","7a8cbcc46988","cb8636a17725","a9862aadcd60"
& $py -X utf8 $S\regress_vs_ocr_v2.py --device cuda:0 --threads 2 --out $S\_scratch\regress_gpu.json --doc-ids $docs
& $py -X utf8 $S\regress_vs_ocr_v2.py --device cpu    --threads 8 --out $S\_scratch\regress_cpu.json --doc-ids $docs
# bộ dựng dữ liệu sau khi tái cấu trúc, KHÔNG dùng --out mặc định (sẽ ghi đè data\ocr_v2.jsonl):
& $py -X utf8 scripts\build_ocr_dataset.py --limit 3 --device cuda:0 --threads 2 --out $S\_scratch\ocr_v2_limit3.jsonl --cache $S\_scratch\cache_docs
& $py -X utf8 -m pytest tests\test_ocr_pdf.py tests\test_ocr_errors.py -q
```

`regress_vs_ocr_v2.py` chỉ **đọc** `data/ocr_v2.jsonl`, từ chối ghi vào `data/`, ghi vào `_scratch/` (đã `.gitignore`). Sau khi chạy, `data/ocr_v2.jsonl` không đổi (2 361 864 byte, thời điểm sửa 2026-10-11 18:57).

## 3. Kiểm hồi quy: văn bản trùng `data/ocr_v2.jsonl`

Ba tài liệu theo yêu cầu cộng ba tài liệu bổ sung (nền được chuẩn hóa, trang bị xoay 180°, trang bị xoay 90°). `data/ocr_v2.jsonl` được dựng bằng `--device cuda:0`, DPI 200, `det-max-side 0`, `viet_seq2seq` (khóa cache `2|viet_seq2seq|200|30|None|bgsat15|det0`), đúng cấu hình của các lần chạy dưới đây.

| `doc_id` | Vai trò | Trang | Nguồn trang | GPU (`cuda:0`) | CPU |
|---|---|---|---|---|---|
| `741b37405405` | có text layer tin cậy | 1 | `text_layer` | trùng | trùng |
| `91e3dcb5fa4e` | scan | 1, 2 | `ocr` | trùng, trùng | trùng; **trang 2 lệch 1 ký tự** |
| `5139035b5c3f` | lớp chữ nhúng bị loại (`invisible_text(render_mode_3)`) | 1 | `embedded_ocr_layer+ocr` | trùng | trùng |
| `7a8cbcc46988` | bổ sung: nền được chuẩn hóa (`bg_normalized`) | 1, 2 | `ocr` | trùng, trùng | trùng, trùng |
| `cb8636a17725` | bổ sung: trang xoay 180° | 1 | `ocr` | trùng | **lệch 2 chỗ** |
| `a9862aadcd60` | bổ sung: trang xoay 90° | 1 | `ocr` | trùng | **lệch 1 chỗ** |

- **GPU: 8/8 trang trùng từng ký tự** (7 280 ký tự), `source` trùng, không trang nào có `error`. Cả 3 tài liệu theo yêu cầu trùng.
- **CPU: 5/8 trang trùng; 3 trang lệch**, tổng 4 chỗ sửa (7 ký tự đổi trên 7 280). Bốn chỗ lệch đều ở vùng độ tin cậy thấp: một chữ số trong một dãy số (`91e3dcb5fa4e` trang 2), hai chỗ trong cụm chữ lặp ở vùng nhiễu của trang `cb8636a17725` (`mean_conf` 0,413), một từ nhận sai ở `a9862aadcd60`. `mean_conf` của trang lệch khác nhau ở chữ số thứ 3–4 sau dấu phẩy (ví dụ 0,6020 so với 0,6035). **Giải thích (suy luận, chưa kiểm riêng):** chênh lệch số học CPU so với GPU làm đổi quyết định giải mã ở các ký tự gần hòa. Điều đã đo: cùng mã trên GPU khớp 100%, nên lệch không do mã mới.
- Hệ quả: `ocr_v2.jsonl` tái lập được **chỉ khi chạy GPU**. Chạy CPU cho chữ gần như giống nhưng không giống từng ký tự (README nhóm 1, bẫy 14).
- Đường hợp đồng: với mọi trang trên, `PageOutcome.to_contract()` → JSON → `OCRPageResult` giữ nguyên văn bản, nguồn, `mean_conf`.

Thêm một kiểm tra cho **bộ dựng dữ liệu đã tái cấu trúc**: `build_ocr_dataset.py --limit 3 --device cuda:0` (3 tài liệu `7a8cbcc46988`, `4d9f145f7932`, `b8b72c553653`, 10 trang) ghi `_scratch/ocr_v2_limit3.jsonl`, thoát mã 0; **10/10 trang trùng** `data/ocr_v2.jsonl` về `text`, `source`, `flags`, không lỗi, tập khóa của bản ghi và của trang giống hệt (4,6 giây/trang OCR, đo dưới tải).

## 4. Phát hiện: cấu hình VietOCR tải từ mạng, và cách xử lý

`vietocr.tool.config.Cfg.load_config_from_name` gọi `requests.get('https://vocr.vn/data/vietocr/config/<tên>')` **mỗi lần khởi động**, nên engine cũ không chạy được khi mất mạng dù trọng số đã nằm trong `%TEMP%`. Nhiệm vụ cấm gọi ra ngoài, nên **tôi không tải** cấu hình chính thức mà dựng lại bằng tay `src/ocr/configs/vgg_seq2seq.yml` từ cấu hình công khai của `vietocr` (theo trí nhớ về tệp công khai, không có bản để đối chiếu trên máy) và kiểm:

1. `vocab` 229 ký tự = 233 (số dòng embedding trong checkpoint) − 4 token đặc biệt;
2. `load_state_dict` (nghiêm ngặt, mặc định của PyTorch) không lỗi với trọng số `vgg_seq2seq.pth`;
3. văn bản trùng từng ký tự với `ocr_v2.jsonl` trên 8 trang GPU ở mục 3. Phép so này mới là kiểm chứng cho các tham số không ảnh hưởng hình dạng trọng số (bước và kích thước nhân của lớp pooling, thứ tự ký tự trong `vocab`).

Chưa so với tệp cấu hình chính thức. `python scripts\setup_ocr_models.py --download-config` (cần mạng, chủ động gõ) tải bản chính thức và in `GIỐNG`/`KHÁC` cho từng khóa; **chưa chạy**. Phạm vi kiểm chứng: 8 trang, 6 tài liệu; chưa kiểm `vgg_transformer` (kho không kèm cấu hình và trọng số của mô hình này).

## 5. Kiểm offline (một phần) và các lần chạy `run_pipeline.py`

**Offline.** Đã chạy khởi tạo engine + OCR một trang (`5139035b5c3f`, lớp chữ nhúng bị loại) khi mọi `socket.connect` và `requests.Session.request` trong tiến trình bị chặn: chạy xong, **0 lần cố kết nối**, 1 trang, 1 692 ký tự, không lỗi. **Chưa** ngắt mạng thật ở mức hệ điều hành hay tường lửa. GLiNER (nhóm 4) chưa kiểm trong điều kiện chặn mạng; pipeline đặt `HF_HUB_OFFLINE=1` và lần chạy dưới đây nạp được mô hình từ cache cục bộ.

**Chạy thử pipeline** (`scripts\run_pipeline.py <pdf> --out output\pipeline_smoke2 --cache-dir output\pipeline_smoke2\llm_cache`; OCR trên `cuda:0` vì `--device auto` thấy ≥ 2 GB VRAM trống lúc bắt đầu; LLM = Ollama `qwen3.5:4b` thật, cache LLM mới nên mọi lời gọi là thật; trích xuất = `BarbEntityExtractor` của nhóm 4, lần gọi đầu gồm cả nạp lười mô hình). Đọc PDF trong `data/classified_v2/`, ghi ra `output/` (không ghi cạnh PDF). Thời gian tính bằng mili giây, **đo trên máy dùng chung** (quan sát GPU 99% sử dụng bởi tiến trình khác lúc chạy tệp ghép):

| `doc_id` | Loại tệp | Trang | Lát cắt | nạp OCR | OCR | tách | phân loại | trích xuất (gồm nạp mô hình) | tổng |
|---|---|---|---|---|---|---|---|---|---|
| `240854950618` | 1 tài liệu, text layer | 1 | 1 | 7 589 | 194 | 1 | 8 | 25 766 | 35 767 |
| `87c88bf6d0f1` | tệp ghép khác loại (`_COMPOSITE_KHAC_LOAI`), 5 trang scan | 5 | 3 | 8 062 | 27 521 | 5 | 194 932 | 30 629 | 263 501 |
| `5139035b5c3f` | 1 tài liệu scan, lớp chữ nhúng bị loại | 1 | 1 | 7 136 | 6 128 | 1 | 6 | 23 245 | 38 790 |

Kết quả định tuyến (nhãn trong `data/classified_v2/INDEX.csv` là nhãn do mô hình gán, chưa người kiểm):

| `doc_id` | Lát cắt (trang) | Tầng | Nhãn | Độ tin cậy | Quyết định | Khớp INDEX |
|---|---|---|---|---|---|---|
| `240854950618` | 1 (1) | rule | `PHIEU_XUAT_KHO` | 0,900 (heuristic) | `auto_file`, trích xuất ok, 11 thực thể | có |
| `87c88bf6d0f1` | 1 (1) | llm | `BB_GIAO_NHAN_HANG_HOA` | 0,983 | `auto_file`, 9 thực thể | có (đoạn trang 1–2) |
| | 2 (2) | llm | `BB_GIAO_NHAN_HANG_HOA` | 0,943 | `auto_file`, 5 thực thể | có (đoạn trang 1–2) |
| | 3 (3–5) | llm | `BB_THANH_LY_HD` | 0,993 | `auto_file`, 16 thực thể | có (đoạn trang 3–5) |
| `5139035b5c3f` | 1 (1) | rule | `GIAY_UY_QUYEN` | 0,900 (heuristic) | `auto_file`, 14 thực thể | có |

Nhận xét (đã đo / chưa đo):
- Đã đo: pipeline chạy hết 3 tệp, `DocumentProcessingPipelineResult` ghi được ra JSON; trang của `5139035b5c3f` mang `source = embedded_ocr_layer+ocr`, `flags = ["embedded_layer_rejected:invisible_text(render_mode_3)"]`, `mean_conf` 0,797. Chỉ tệp ghép đi tới tầng LLM; hai tệp đơn dừng ở cổng luật (đúng thiết kế: luật nhận 76–85% tài liệu ở 02).
- Bộ tách (nhóm 2) cắt tệp ghép thành **3 lát** trong khi INDEX có **2 đoạn** (trang 1–2 và 3–5): trang 1 và trang 2 thành hai lát riêng cùng loại. Đó là hành vi của `split_document`, không sửa ở đây; hệ quả: một tài liệu hai trang bị trích xuất hai lần.
- Đã quan sát một sự cố thật ở lần chạy thử đầu (cache LLM chung, GPU bị tranh chấp): lát cắt 3 của `87c88bf6d0f1` bị `ReadTimeout` 180 giây từ Ollama. Pipeline ghi `tier = human`, `abstain_reason = llm_error`, `error = "ReadTimeout: ..."`, gợi ý `BB_THANH_LY_HD` từ TF-IDF, quyết định `needs_human (classification:llm_error, classifier_error)`; hai lát còn lại không bị ảnh hưởng. Lần chạy thứ hai (bảng trên) cùng lát cắt đó có kết quả `BB_THANH_LY_HD` 0,993. Thời gian phân loại 194,9 giây của tệp ghép (lát 1 mất khoảng 167 giây) phản ánh Ollama bị tranh GPU lúc đó; **không điều tra nguyên nhân**, không được dùng làm số đo độ trễ.
- Chưa đo: thông lượng khi GPU rảnh, p95, bộ nhớ, tải nhiều tài liệu (README nhóm 1 T4 bước 5).

## 6. Hạn chế

- Hồi quy GPU chỉ trên 8 trang / 6 tài liệu; các dạng trang khác (bảng, viết tay, con dấu, nền rất tối) chưa kiểm so với `ocr_v2.jsonl` (cùng mã nên kỳ vọng trùng, chưa chứng minh).
- `ocr_v2.jsonl` tái lập chỉ khi chạy GPU; trên máy sản xuất không có GPU văn bản sẽ lệch nhẹ so với bộ dữ liệu đã dùng để huấn luyện TF-IDF và chọn ngưỡng (ảnh hưởng đến phân loại chưa đo; 02 §8 cho thấy cascade ít nhạy với OCR).
- `OCRPageResult.boxes` vẫn rỗng (engine chưa trả tọa độ ra hợp đồng); `width`/`height` là kích thước trang tính theo pixel ở 200 dpi (suy từ khổ giấy, không phải kích thước ảnh render).
- Giấy phép trọng số VietOCR và PyMuPDF (AGPL): chưa xác nhận (README nhóm 1 T4 bước 4).
- `total_pages` của `OCRDocumentResult` là số trang thật của tệp (khác `rapid_ocr.extract_document` cũ trả `min(trang, max_pages)`); tệp dài hơn `--max-pages` có `len(pages) < total_pages` và pipeline ghi cảnh báo.
