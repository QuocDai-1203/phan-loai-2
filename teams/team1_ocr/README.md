# Nhóm 1 — OCR (đọc chữ từ ảnh trang)

## Mục tiêu (doanh nghiệp nhận được gì)

Biến mỗi trang PDF quét thành văn bản **có đủ dấu tiếng Việt**, chạy hoàn toàn trên máy công ty (offline), đủ nhanh cho khối lượng hồ sơ thật. Văn bản này là đầu vào của cả ba nhóm sau: tách tài liệu, nhận loại, và đặc biệt là **trích xuất trường** (tên riêng, số, ngày) — nơi lỗi OCR gây hại thật. Đầu ra theo hợp đồng `OCRDocumentResult` (xem [`teams/README.md`](../README.md)).

## Hiện trạng

### Đã làm và đo được

| Hạng mục | Kết quả | Nguồn |
|---|---|---|
| Nguyên nhân mất dấu của baseline cũ | `rapidocr_onnxruntime` 1.2.3 có **9/67** chữ cái thường có dấu tiếng Việt trong từ điển nhận dạng nên **không thể** xuất 58 chữ còn lại; VietOCR có 67/67. Trên 302/334 bản ghi baseline (trang 1) tỉ lệ chữ có dấu chỉ 0,0018 | [`01_engine_bakeoff/RESULTS.md`](experiments/01_engine_bakeoff/RESULTS.md) §3 |
| Engine đã chọn | bộ phát hiện dòng DB của PP-OCRv5 (`rapidocr` 3.10, ONNX) + **VietOCR `vgg_seq2seq`**, 200 dpi, chuẩn hóa nền chỉ khi độ bão hòa trung vị của trang ≥ 15/255 | cùng tệp §6 |
| Chất lượng trên trang số (pseudo-gold, 10 trang chung) | CER 0,082 (baseline cũ 0,260); sau khi ảnh xuống cấp 0,185; diac_recall 0,978 | cùng tệp §4a |
| Chất lượng trên 30 trang scan thật (chấm theo bản chép của Haiku) | bag_recall 0,801 (baseline cũ 0,168) | cùng tệp §4b |
| Tập dữ liệu v2 | `data/ocr_v2.jsonl`: 336 tài liệu, **1084 trang** (tối đa 30 trang/tài liệu), 0 trang lỗi; tỉ lệ chữ có dấu ở trang 1 tăng 0,022 → 0,265 | [`02_dataset_v2/RESULTS.md`](experiments/02_dataset_v2/RESULTS.md) §2, §4 |
| Tốc độ | 1 tiến trình: ~5,9 giây/trang (CPU hoặc GPU như nhau). Chạy cả kho: **46,3 phút**, 0,39 trang/giây với GPU, 6 worker × 2 luồng; CPU 24 worker chỉ 0,08 trang/giây. Chỉ 910 trang là OCR thật (còn lại là text layer hoặc sao chép từ bản trùng) | `01_engine_bakeoff/RESULTS.md` §5, `02_dataset_v2/RESULTS.md` §3 |
| Bản chép "bạc" bằng LLM | `data/ocr_llm_haiku.jsonl`: Claude Haiku đọc ảnh, **2 trang đầu** của mọi tài liệu (336 dòng, 600 trang). Trên 39 trang born-digital so với text layer: bag_recall 0,995, diac_recall 0,9997, nhưng **CER 0,105** (VietOCR cục bộ cùng 39 trang: CER 0,088, bag_recall 0,944). Haiku và Sonnet chép 8 trang scan chênh nhau trung bình 2,8% CER | [`03_llm_silver/`](experiments/03_llm_silver/) (`llm_vs_textlayer_summary.csv`, `bag_recall_summary.csv`, `haiku_vs_sonnet_pages.csv`) |
| OCR có quan trọng cho **phân loại** không | **Gần như không.** Đổi từ OCR cũ (mất dấu) sang văn bản gần hoàn hảo của Haiku chỉ tăng macro-F1 DEV khoảng 0,016–0,02 (0,960 → 0,976); trên TEST (59 tài liệu) Δ = +0,056, khoảng tin cậy 95% [−0,004; 0,122], p = 0,25 → **không tách được** | [`01_classical_baselines/RESULTS.md`](../team3_classification/experiments/01_classical_baselines/RESULTS.md) §6, §7a |

Hai điều cần đọc cùng nhau: LLM chép *đúng chữ* tốt hơn (bag_recall, dấu) nhưng CER cao hơn VietOCR vì khác thứ tự đọc và ngắt dòng; và LLM **không dùng được trong hệ thống chạy thật** (phải on-premise), nó chỉ là công cụ xây dữ liệu tham chiếu.

### Chưa đo / chưa làm

- **CER trên scan thật: chưa đo.** Chưa có gold do người gõ (`gold/transcripts/` chưa tồn tại). Mọi số trên scan thật là so với bản chép của LLM.
- ~~Độ chính xác của bước tự xoay trang: chưa đo~~ — **đã đo ngày 2026-10-15** (T2, [`05_rotation/RESULTS.md`](experiments/05_rotation/RESULTS.md)) trên 353 trang đã xem, đáp án hướng do **mô hình** nhìn ảnh (chưa có người kiểm): trang có chữ bị xoay đúng hướng 30/32 (Wilson 0,80–0,98), sót 0/280 trang không bị xoay; 8 trang gần trống bị xoay nhầm vì vệt đen mép giấy (10 tính cả bản trùng; mục "Việc cần làm" cũ ghi 9), đã thêm điều kiện bỏ qua trong `pdf_ocr.py`. Còn lại: 2 trang sổ PCCC xoay ngược hướng (90 ↔ 270).
- Chữ viết tay và con dấu: chỉ biết là **sai gần như hoàn toàn** qua xem mắt 4 trang; chưa có số đo.
- Ảnh hưởng của OCR lên **trích xuất trường**: đã đo sơ bộ ở [`team4_extraction/experiments/02_methods/RESULTS.md`](../team4_extraction/experiments/02_methods/RESULTS.md) mục 3 (so `ocr_v2` với bản chép của LLM đám mây, dev, đáp án silver chưa người kiểm, trường ở trang 1–2): OCR cục bộ mất nhiều nhất ở chữ viết tay và chữ dưới con dấu (luật đúng 0,53 và 0,35, so với 0,82 và 0,95 trên bản chép), chữ in chỉ mất ít (0,82 so với 0,89); chưa có khoảng tin cậy ghép cặp. Ảnh hưởng lên **phân loại** đã đo: trên `ocr_v2` (trang 1–2) kết quả không tách được khỏi bản chép Haiku (TF-IDF TEST macro-F1 0,946 so với 0,974, hiệu +0,028, CI [0,000; 0,109]; Qwen3.5-4B DEV 0,996 so với 1,000), còn OCR cũ làm Kev-0.8B tụt từ 0,96 xuống 0,50 — xem mục 0 của `teams/team3_classification/experiments/01_classical_baselines/RESULTS.md` và mục 8 của `02_llm_and_cascade/RESULTS.md`.
- Tốc độ trên máy sản xuất, khi GPU không bị việc khác chiếm: chưa đo (máy dev dùng chung, 7–10 GB VRAM bị chiếm).
- ~~Code trong `src/ocr/` chưa dùng engine đã chọn~~ — **đã sửa ngày 2026-10-12** (T4 bước 1–2): engine đã chọn nằm ở `src/ocr/vietocr_engine.py` + `src/ocr/pdf_ocr.py` (hàm `ocr_pdf` trả `OCRDocumentResult`), `scripts/build_ocr_dataset.py` import từ đó; `src/ocr/rapid_ocr.py` còn lại nhưng đánh dấu **LEGACY** (mất dấu, phát `DeprecationWarning`). Bằng chứng hồi quy: [`07_src_engine/RESULTS.md`](experiments/07_src_engine/RESULTS.md). Còn lại của T4: bước 3 (kiểm offline bằng `build_ocr_dataset.py --limit 3` khi tắt mạng thật), 4 (giấy phép), 5 (thông lượng).
- `data/ocr_v2.jsonl` không lưu hộp tọa độ, kích thước trang; chỉ có văn bản, `mean_conf`, `flags`.

## Việc cần làm (theo thứ tự ưu tiên)

Công sức là **ước lượng của người viết kế hoạch**.

### T1 (P0) — Gold OCR thật từ `gold_pages_todo.csv`, đo xem bản chép LLM phải sửa bao nhiêu

- **Vì sao:** không có đáp án thật thì không biết CER thật của `ocr_v2`, và không biết bản chép của LLM đáng tin đến đâu để dùng làm "bạc" cho các nhóm khác.
- **Các bước:**
  1. Cả 25 trang trong `gold/gold_pages_todo.csv` (5 in, 5 viết tay, 5 con dấu, 5 bảng, 5 chất lượng thấp) đều đã có bản chép Haiku trong `gold/silver_llm/haiku/Pnnn.txt`. Nối `Tnn → Pnnn` bằng `(relative_path, page)` của `gold_pages_todo.csv` với `(relative_path, page0)` của `experiments/03_llm_silver/pages.csv` (**cùng đếm từ 0**).
  2. Làm trước **10 trang rủi ro nhất**: `T06–T10` (viết tay) và `T11–T15` (con dấu). Mở ảnh trang (`fitz.open(pdf)[page].get_pixmap(dpi=150)`), đọc bản nháp, sửa theo "Quy tắc gõ" trong [`gold/README.md`](gold/README.md) (NFC, giữ ngắt dòng, `[?]`, `[EMPTY]`, `[ROTATED]`).
  3. Lưu nháp gốc vào `gold/transcripts_draft/Tnn.txt` và bản đã sửa vào `gold/transcripts/Tnn.txt`; ghi thời gian sửa từng trang. Đo **CER(nháp so với bản sửa)** theo `why_chosen` — đó là câu trả lời cho "phải sửa bao nhiêu".
  4. **Kiểm tra thiên lệch neo:** `gold/README.md` yêu cầu gõ từ đầu (không sửa từ đầu ra máy) vì sửa nháp làm người sửa bỏ sót lỗi của nháp. Với 5 trang `overlap_double_transcribe = yes` (T01, T06, T11, T16, T21): người A gõ **từ đầu** (`Tnn.a.txt`), người B **sửa nháp** (`Tnn.b.txt`). CER(a so với b) cho biết thiên lệch neo; nếu lớn, các trang còn lại phải gõ từ đầu. Cập nhật `gold/README.md` theo kết quả (hiện nó chưa nhắc tới nháp LLM).
  5. Chạy `eval_on_gold.py` cho engine đã chọn và baseline.
- **Bắt đầu từ:** `gold/gold_pages_todo.csv`, `gold/README.md`, `experiments/01_engine_bakeoff/eval_on_gold.py`.

```powershell
$py = ".venv\Scripts\python.exe"; cd teams\team1_ocr\experiments\01_engine_bakeoff
& "..\..\..\..\$py" -X utf8 eval_on_gold.py --engines rapid_v1 viet_seq2seq_cpu   # đọc gold/transcripts/<Tnn>.txt, ghi gold_eval.csv
```
- **Sản phẩm:** `gold/transcripts/` (25 tệp, UTF-8 không BOM, NFC), `gold/transcripts_draft/`, `experiments/04_gold_eval/RESULTS.md` (CER/WER của từng engine theo `why_chosen`; CER của nháp LLM; thời gian sửa; CER giữa hai người).
- **Xong khi:** 25 tệp có mặt và qua kiểm NFC; 5 trang overlap có CER giữa hai người; `RESULTS.md` có bảng CER theo loại trang và khoảng sai số nêu rõ cỡ mẫu (5 trang mỗi nhóm → rất rộng).
- **Công sức (ước lượng):** 2 người × 1,5–3 ngày.
- **Điều kiện tiên quyết:** không. Thư mục `transcripts/` chứa thông tin cá nhân thật, **không đẩy lên nơi công khai**.

### T2 (P1) — Đánh giá bước tự xoay trang

- **Trạng thái (2026-10-15): ĐÃ XONG ở mức đáp án do mô hình.** Số đo, lệnh và hạn chế: [`experiments/05_rotation/RESULTS.md`](experiments/05_rotation/RESULTS.md) (`orientation_gold.csv`, 353 trang: 40 trang bị xoay duy nhất, toàn bộ 213 trang loại hay nằm ngang, 100 trang ngẫu nhiên seed 20261015). Giữ bước xoay; thêm tham số `min_chars_for_rotation=30` ở `src/ocr/pdf_ocr.py` (test `tests/test_ocr_rotation_guard.py`). Việc còn lại: người kiểm đáp án hướng; sửa chọn nhầm 90/270 (2 trang); chạy lại cả kho nếu muốn cập nhật `ocr_v2.jsonl` (10 trang đổi thành trống).
- **Vì sao:** `ocr_v2` xoay 50 trang (90°: 13, 270: 35, 180: 2), trong đó 9 trang gần trống bị xoay nhầm ra vài ký tự rác. Chưa có đáp án hướng nên không biết còn bao nhiêu trang cần xoay mà không được xoay.
- **Các bước:** (1) liệt kê trang có cờ `rotated_*` trong `flags` của `data/ocr_v2.jsonl` và xem thumbnail, gán hướng đúng {0, 90, 180, 270}; (2) lấy thêm mẫu **không bị xoay**: mọi trang của loại hay nằm ngang (sổ PCCC, bảo hiểm cháy nổ, đăng kiểm ghe, bản vẽ — mục 7.6 của [`02_taxonomy_design.md`](../00_data_and_eval/reports/02_taxonomy_design.md)) cộng một mẫu ngẫu nhiên; (3) tính độ chính xác hướng, tỉ lệ xoay nhầm trang gần trống, và chất lượng chữ (số ký tự, tỉ lệ âm tiết hợp lệ) trước/sau; (4) nếu cần, thêm điều kiện không xoay trang có ít chữ.
- **Bắt đầu từ:** `data/ocr_v2.jsonl` (trường `flags`), `scripts/build_ocr_dataset.py` (hàm xoay).
- **Sản phẩm:** `experiments/05_rotation/` (script, `orientation_gold.csv`, `RESULTS.md`).
- **Xong khi:** có độ chính xác hướng trên mẫu nêu rõ cỡ; quyết định giữ hay sửa bước xoay có số liệu.
- **Công sức (ước lượng):** 1–1,5 ngày.

### T3 (P1) — Vùng chữ viết tay và con dấu: cắt vùng + mô hình thị giác nhỏ chạy cục bộ (thí nghiệm)

- **Vì sao:** các trường vận hành quan trọng ở biên bản giao nhận, biên bản lấy mẫu (số niêm phong, biển số xe, số lượng, ngày) thường là chữ viết tay; OCR hiện tại đọc sai và `mean_conf` không báo được.
- **Các bước:** (1) xác định trường cần đọc cùng nhóm 4 (bắt đầu từ `BB_LAY_MAU`, `BB_GIAO_NHAN_HANG_HOA`); (2) chạy lại bộ phát hiện dòng để có hộp tọa độ (`ocr_v2.jsonl` không lưu) và cắt vùng; (3) kiểm tra mô hình nào trong Ollama (`127.0.0.1:11434`) nhận được ảnh (`ollama show <tên>`); nếu chưa có mô hình thị giác thì cần kéo một mô hình về (cần mạng một lần, hỏi chủ dự án); (4) so đầu ra trên các trang gold viết tay/con dấu của T1 theo từng trường, so với VietOCR và với LLM đám mây (chỉ để tham chiếu); (5) ghi `BoundingBox.is_handwritten` nếu phân biệt được.
- **Sản phẩm:** `experiments/06_handwriting_crop/` với `RESULTS.md`: độ chính xác theo trường, thời gian mỗi vùng, mô hình đã dùng.
- **Xong khi:** có số đo trên các trang gold; kết luận "có/không đáng tích hợp" nêu cỡ mẫu.
- **Công sức (ước lượng):** 3–5 ngày.
- **Điều kiện tiên quyết:** T1 (cần gold); danh sách trường từ nhóm 4.

### T4 (P0) — Tốc độ, đóng gói trọng số để chạy offline, và đưa engine đã chốt vào `src/`

- **Trạng thái (2026-10-12): bước 1 và 2 ĐÃ XONG; bước 3 làm một phần; bước 4 chưa; bước 5 làm một phần (2026-10-15, xem bên dưới).** Chi tiết, lệnh và số đo: [`experiments/07_src_engine/RESULTS.md`](experiments/07_src_engine/RESULTS.md).
  - Bước 1: engine ở `src/ocr/vietocr_engine.py`, quy tắc text layer + `ocr_pdf` ở `src/ocr/pdf_ocr.py`, test ở `tests/test_ocr_pdf.py`. Hồi quy: trên GPU, 6 tài liệu (gồm 3 loại yêu cầu: text layer, scan, lớp chữ nhúng bị loại) khớp **từng ký tự** với `data/ocr_v2.jsonl`; trên CPU 5/8 trang khớp, 3 trang lệch 1–2 ký tự (nhiễu số học CPU/GPU; xem RESULTS).
  - Bước 2: trọng số ở `models/ocr/` (đọc từ đó, thiếu thì báo lỗi kèm hướng dẫn; xem [`models/README.md`](../../models/README.md)). rapidocr lưu mô hình ở `<venv>\Lib\site-packages\rapidocr\models\` (tải lần đầu có mạng); đã chép mô hình phát hiện dòng ra `models/ocr/rapidocr/` và truyền `Det.model_path`. **Phát hiện mới:** thư viện `vietocr` tải **cấu hình** (`vgg-seq2seq.yml`, `base.yml`) từ `vocr.vn` mỗi lần khởi động, nên engine cũ không chạy được khi mất mạng dù đã có trọng số; cấu hình suy diễn nay kèm trong kho (`src/ocr/configs/vgg_seq2seq.yml`, dựng lại bằng tay và kiểm bằng hồi quy, chưa so với bản chính thức vì không gọi mạng).
- **Vì sao:** (a) hệ thống thật phải chạy không cần mạng; (b) `src/ocr` đang dùng engine cũ; (c) khối lượng thật chưa biết.
- **Các bước:**
  1. **Đưa engine vào `src/ocr/`** theo hợp đồng `OCRDocumentResult`: tách logic từ `scripts/build_ocr_dataset.py` (quy tắc dùng text layer, chuẩn hóa nền, xoay) thành module có test; kiểm hồi quy: kết quả giống `data/ocr_v2.jsonl` trên 3 tài liệu. **[xong]**
  2. **Trọng số:** VietOCR tải từ `vocr.vn` về `%TEMP%\vgg_seq2seq.pth` (có thể bị dọn); chép ra thư mục cố định, cho mã đọc từ đó; xem rapidocr lưu mô hình ở đâu sau lần tải đầu. **[xong]**
  3. **Kiểm offline thật:** ngắt mạng (hoặc chặn bằng tường lửa), chạy `build_ocr_dataset.py --limit 3`; phải chạy xong không lỗi. **[làm một phần: đã chạy engine với mọi kết nối socket/`requests` bị chặn trong tiến trình và không có lần nào cố kết nối; chưa ngắt mạng thật ở mức hệ điều hành]**
  4. **Giấy phép:** trọng số VietOCR không thấy ghi giấy phép riêng (báo cáo 01 §6); cần xác nhận trước khi triển khai thương mại. PyMuPDF là AGPL-3.0 (có giấy phép thương mại của Artifex).
  5. **Thông lượng:** thử `--batch` (mặc định 16), `--workers`, `--threads` trên cùng 24 tài liệu (53 trang) đã dùng ở báo cáo 02; ghi trang/giây, VRAM, lúc GPU rảnh và lúc dùng chung. Số tham chiếu hiện có: 6 worker × 2 luồng GPU = 0,35 trang/giây; 12 worker = 0,28 (VRAM gần cạn). **[làm một phần 2026-10-15: 3 cấu hình GPU, 0,17–0,22 trang/giây trên GPU dùng chung (chậm hơn tham chiếu), chưa tách được tác động từng tham số; xem [`08_throughput/RESULTS.md`](experiments/08_throughput/RESULTS.md); chưa đo máy rảnh, `--threads` khác 2, CPU]**
- **Sản phẩm:** `src/ocr/` có engine mới + test; `experiments/08_throughput/RESULTS.md`; thư mục trọng số (không commit) và hướng dẫn đặt.
- **Xong khi:** chạy offline thành công; `pytest` qua; bảng trang/giây theo cấu hình; kết luận đủ/không đủ cho khối lượng (sau khi có câu trả lời của công ty).
- **Công sức (ước lượng):** 3–5 ngày.

### T5 (P1) — Đánh giá OCR theo ảnh hưởng lên trích xuất

- **Vì sao:** phân loại gần như không nhạy với chất lượng OCR (xem bảng trên), nên CER không phải thước đo đúng. Thước đo đúng là: trường (ngày hết hạn, số hợp đồng, số lượng) đọc đúng bao nhiêu phần trăm.
- **Các bước:** khi nhóm 4 có đáp án trường, chạy cùng một bộ trích xuất trên ba nguồn văn bản (text layer cho trang born-digital, `ocr_v2`, bản chép LLM) và báo Δ độ chính xác trường theo loại trường (chữ in, số, chữ viết tay, dưới con dấu).
- **Sản phẩm:** `experiments/08_ocr_effect_on_extraction/RESULTS.md`.
- **Xong khi:** bảng Δ theo loại trường, có khoảng tin cậy.
- **Công sức (ước lượng):** 1 ngày sau khi có đáp án của nhóm 4.
- **Điều kiện tiên quyết:** [`team4_extraction`](../team4_extraction/README.md) T2.

### T6 (P0, quy tắc cố định) — Giữ cách làm "bạc từ LLM" trung thực

Áp dụng cho mọi lần dùng LLM chép chữ hay trích trường để làm dữ liệu tham chiếu:

1. **Luôn chấm bằng đáp án đã biết.** Với bản chép: trộn vào mỗi đợt các trang born-digital (đáp án = text layer) và báo bag_recall/CER, như `score_llm_transcripts.py` (Haiku: 39 trang, recall thấp nhất theo trang 0,987).
2. **Không bao giờ nhận văn bản cho trang mà mô hình không thực sự thấy.** Đã xảy ra: một đợt phải làm lại vì tác nhân chép chữ cho 12 trang mà ảnh của chúng nạp lỗi (theo ghi nhận khi thực hiện; không có log trong kho). Biện pháp: trộn **trang trắng** và **trang đã biết** vào mỗi đợt; trang trắng mà ra chữ → bỏ cả đợt; ghi số ảnh nạp được; kiểm chéo bản chép trang 1 với OCR độc lập bằng 4-gram không dấu như `data/ocr_llm_haiku/_check_vs_baseline.py` (trên 302 trang trung vị recall 0,88).
3. **Ghi mô hình, ngày, tham số** vào mỗi bản ghi (`engine` trong `ocr_llm_haiku.jsonl`).
4. **Chữ viết tay và con dấu là nơi LLM kém tin cậy nhất**: không dùng bản chép làm đáp án cho các vùng này khi chưa có người kiểm.
5. Chỉ bộ mẫu hiện tại được gửi ra ngoài (quyết định của chủ dự án); mẫu mới cần phê duyệt mới.

**Trạng thái (2026-10-15): ĐÃ XONG phần mã.** `experiments/03_llm_silver/validate_batch.py` (kiểm trang đã biết, trang trắng, số ảnh nạp được, kiểm chéo 4-gram), `scripts/assemble_llm_ocr.py` từ chối lô chưa qua kiểm (cờ `--skip-validation "lý do"` có ghi log), 14 test trong `tests/test_llm_batch_validation.py`, đợt thử trang trắng ra chữ → "không hợp lệ". Ngưỡng hiệu chuẩn trên số liệu Haiku có sẵn và giới hạn (kiểm chéo chỉ nhạy với lô ≤ 50–60 mục): [`03_llm_silver/RESULTS.md`](experiments/03_llm_silver/RESULTS.md). Lô Haiku cũ không thể chứng minh hợp lệ (thiếu trang kiểm), nên ghép lại nó cần `--skip-validation`.

Việc cụ thể (đã làm): viết `experiments/03_llm_silver/validate_batch.py` thực hiện 1–3 và để `scripts/assemble_llm_ocr.py` từ chối đợt chưa qua kiểm. Ngưỡng do nhóm đặt sau khi xem số liệu. **Xong khi:** có script + test, và một đợt thử với trang trắng cho ra kết quả "đợt không hợp lệ" đúng như kỳ vọng. Công sức (ước lượng): 1 ngày.

## Cách chạy lại những gì đã có

Từ gốc repo, PowerShell (môi trường: [handbook](../../docs/HANDBOOK_FOR_RESEARCHERS.md)). Lệnh bake-off đầy đủ nằm ở mục 1 của [`01_engine_bakeoff/RESULTS.md`](experiments/01_engine_bakeoff/RESULTS.md).

```powershell
$py = ".venv\Scripts\python.exe"
& $py -X utf8 scripts\build_ocr_dataset.py --limit 3                  # chạy thử 3 tài liệu, KHÔNG ghi đè data/ocr_v2.jsonl
& $py -X utf8 scripts\build_ocr_dataset.py --device cuda:0 --workers 6 --threads 2 --resume   # chạy cả kho (~46 phút), ghi data/ocr_v2.jsonl
& $py -X utf8 teams\team1_ocr\experiments\02_dataset_v2\dataset_stats.py                     # thống kê
& $py -X utf8 scripts\assemble_llm_ocr.py                             # ghép data/ocr_llm_haiku/pages/*.txt -> data/ocr_llm_haiku.jsonl
& $py -X utf8 teams\team1_ocr\experiments\03_llm_silver\score_llm_transcripts.py            # chấm bản chép LLM với text layer
```

Đã chạy khi viết tài liệu này: các lệnh `--help` của `build_ocr_dataset.py`, `assemble_llm_ocr.py`, `eval_on_gold.py` (lệnh đều tồn tại). Chưa chạy lại việc OCR cả kho (mất ~46 phút, dùng GPU chung).

Engine trong `src/` (2026-10-12), lệnh và kết quả ở [`07_src_engine/RESULTS.md`](experiments/07_src_engine/RESULTS.md):

```powershell
& $py -X utf8 scripts\setup_ocr_models.py                      # kiểm / chép mô hình vào models\ocr (không dùng mạng)
& $py -X utf8 teams\team1_ocr\experiments\07_src_engine\regress_vs_ocr_v2.py --device cuda:0 --doc-ids 741b37405405 91e3dcb5fa4e 5139035b5c3f   # hồi quy với data/ocr_v2.jsonl (chỉ đọc), ghi vào _scratch\
& $py -X utf8 scripts\run_pipeline.py <tệp.pdf> --out output\pipeline --no-llm --no-extract   # OCR + tách + luật/TF-IDF
```

Giai đoạn 3 (2026-10-15):

```powershell
$e = "teams\team1_ocr\experiments"
& $py -X utf8 $e\05_rotation\make_sheets.py                               # T2: dựng tờ tiếp xúc (ảnh giấy tờ, đã .gitignore) + sample_pages.csv
& $py -X utf8 $e\05_rotation\evaluate_rotation.py                         # T2: orientation_gold.csv + độ chính xác hướng (đáp án ở gold_annotations.py)
& $py -X utf8 $e\05_rotation\reocr_compare.py --device cuda:0             # T2: chữ trước/sau trên trang lệch (GPU dùng chung, ~2 phút)
& $py -X utf8 $e\03_llm_silver\validate_batch.py --batch-dir <thư mục .txt> --manifest <manifest.csv>   # T6: kiểm lô bản chép LLM
& $py -X utf8 $e\03_llm_silver\calibrate_validate_batch.py                # T6: hiệu chuẩn ngưỡng; demo_blank_trap.py: đợt thử trang trắng
& $py -X utf8 $e\08_throughput\bench_throughput.py --configs 6x2x16 6x2x32 4x2x16 --budget-min 10   # T4 bước 5: ~13 phút GPU dùng chung
```

## Bẫy thường gặp (đã gặp thật)

1. **Từ điển nhận dạng thiếu chữ có dấu:** engine nào cũng có thể "tự tin" mà mất dấu. `mean_conf` của baseline cũ là 0,833 dù mất dấu hoàn toàn; `mean_conf` không so được giữa các engine và **không dùng để lọc chữ viết tay**.
2. **Lớp chữ vô hình do máy scan nhúng** (render mode 3, 3 trang ở 2 tài liệu): qua được kiểm tra "≥ 50 ký tự" của baseline nhưng 0% chữ có dấu. `build_ocr_dataset.py` loại và OCR lại.
3. **`src/ocr/rapid_ocr.py` là engine cũ** (nay đánh dấu LEGACY, phát `DeprecationWarning`). Đừng dùng nó để tạo số liệu mới; dùng `src.ocr.pdf_ocr.ocr_pdf`.
4. **dpi:** 150 làm hỏng ảnh xuống cấp (CER 0,225), 300 không hơn và chậm hơn; chọn 200. Thu nhỏ ảnh cho bộ phát hiện (`--det-max-side 1280`) nhanh hơn ~20% nhưng hại trang số dày (CER 0,082 → 0,097): đừng bật.
5. **Chuẩn hóa nền cho mọi trang làm tệ trang trắng** (CER +0,03); chỉ bật khi giấy có màu. Ngưỡng 15/255 chọn sau khi xem 30 trang scan nên số 0,801 hơi lạc quan.
6. **Tệp trùng byte được sao chép kết quả** (cờ `copied_from_exact_duplicate:<doc_id>`); khi tính tốc độ chỉ đếm 910 trang OCR thật.
7. **Bị cắt ở 30 trang:** 6 tài liệu (5 sổ PCCC 46–53 trang và tệp biên bản lấy mẫu 93 trang) không có văn bản từ trang 31. Nhóm 2 cần OCR đủ trang của tệp 93 trang composite (`--max-pages`; script chưa có cờ lọc theo tài liệu). Trong pipeline, từ giai đoạn 3 tệp dài hơn `max_pages` (30) được chuyển cả tệp sang người (lý do `truncated_pages`) thay vì cắt âm thầm; vẫn chưa OCR đủ trang.
8. **57 trang gần trống** (< 5 ký tự): không phải lỗi OCR; bộ phân loại phải xử lý.
9. **Máy dùng chung:** số tốc độ chạy song song rất nhiễu; chỉ tin bảng đo riêng.
10. **LLM chép bịa khi ảnh không nạp được** (T6). **Đếm trang:** gold OCR đếm từ 0, hướng dẫn gán nhãn đếm từ 1.
11. **PaddleOCR 3.x** kéo `opencv-contrib-python` đè lên `opencv-python`; chỉ cài trong venv riêng; trên CPU phải tắt oneDNN (`enable_mkldnn=False`).
12. **`scripts/generate_baseline_ocr.py` là script cũ, ghi đè `data/baseline_ocr_335.jsonl`:** nay từ chối chạy nếu không có `--force`; đừng chạy, dùng `scripts/build_ocr_dataset.py`.
13. **`scripts/build_ocr_dataset.py` mặc định ghi `data/ocr_v2.jsonl`** (khi không có `--limit`). Muốn thử mà không đụng dữ liệu: luôn truyền `--out` và `--cache` ra thư mục nháp (xem `07_src_engine/RESULTS.md`).
14. **CPU và GPU cho văn bản lệch nhau vài ký tự** ở các dòng độ tin cậy thấp (chữ lặp, chữ nhỏ): `data/ocr_v2.jsonl` được dựng trên GPU; so hồi quy trên CPU sẽ thấy 1–2 ký tự lệch trên một số trang. Không phải lỗi mã (cùng mã trên GPU khớp từng ký tự).
15. **`vietocr` tải cấu hình từ mạng mỗi lần khởi động** (`Cfg.load_config_from_name`): đừng dùng hàm đó trong mã chạy thật; engine trong `src/ocr/` nạp cấu hình cục bộ.
16. **Lần chạy đầu của tiến trình chậm hơn** vì nạp mô hình (VietOCR khoảng 7–14 giây trên máy này, đo dưới tải): `run_pipeline.py` ghi riêng `ocr_model_load` trong `stage_timings_ms`.

## Câu hỏi cần hỏi doanh nghiệp

1. Khối lượng thật: bao nhiêu trang mỗi ngày, đỉnh bao nhiêu? Cần xử lý ngay hay theo lô ban đêm? (quyết định cấu hình tốc độ ở T4)
2. Máy chạy thật có GPU không? (máy dev: RTX 3060 12 GB)
3. Máy quét và chế độ quét đang dùng (dpi, màu hay xám, nén)? Có thể chuẩn hóa cách quét (ví dụ ≥ 200 dpi, thẳng trang) không? Tỉ lệ PDF born-digital so với bản quét là bao nhiêu?
4. Những trường **viết tay** nào thật sự cần máy đọc (số niêm phong, biển số, số lượng, ngày)? Có thể thay bằng nhập liệu có cấu trúc ngay từ nguồn không?
5. Chữ trong con dấu có cần đọc không (ví dụ tên đơn vị)?
6. Xác nhận: hệ thống chạy thật **không** được gọi LLM ngoài. Có đồng ý để mẫu mới (nếu thu thêm) được gửi LLM ngoài chỉ để dựng dữ liệu tham chiếu không?
7. Có ràng buộc giấy phép với trọng số/thư viện OCR được triển khai (VietOCR, PyMuPDF AGPL) không? Ai ký duyệt?
