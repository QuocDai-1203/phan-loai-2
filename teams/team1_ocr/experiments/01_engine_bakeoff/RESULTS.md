# Bake-off engine OCR cho PDF scan tiếng Việt (Team 1)

Mục tiêu: chọn engine OCR **chạy hoàn toàn trên máy (offline)**, giữ được **dấu tiếng Việt**, đủ nhanh cho ~1000 trang.
Tất cả số liệu dưới đây do script trong thư mục này sinh ra (`results.csv`, `results_pages.csv`, `results_vs_haiku*.csv`);
chưa có số nào ghi tay. Phần **"Suy luận"** được tách riêng khỏi **"Đo được"**.

## 0. Kết luận một dòng

> **Engine chọn:** bộ phát hiện dòng chữ DB của PP-OCRv5 (`rapidocr` 3.10, ONNX, CPU) **+ VietOCR `vgg_seq2seq`** (nhận dạng),
> **200 dpi**, chuẩn hoá nền chỉ khi giấy có màu/hoa văn. Giữ lại 100% bộ dấu tiếng Việt (diacritic recall 0,97–0,98 trên trang sạch),
> CER 0,082 (so với 0,260 của baseline cũ), ≈ 3–6 giây/trang trên máy rảnh.
> Baseline cũ (`rapidocr_onnxruntime` 1.2.3) **không thể** xuất ra 58/67 chữ cái thường có dấu của tiếng Việt vì từ điển nhận dạng của nó không chứa chúng.

## 1. Cách tái hiện (từ thư mục gốc repo, Windows)

```powershell
$py = ".venv\Scripts\python.exe"; $d = "teams\team1_ocr\experiments\01_engine_bakeoff"; cd $d
& "..\..\..\..\$py" -X utf8 survey_pdfs.py          # khảo sát 1246 trang: có text layer không, ảnh phủ trang, chữ vô hình
& "..\..\..\..\$py" -X utf8 make_samples.py          # sample_gold_pages.csv (39 trang) + sample_scan_pages.csv (30 trang), seed cố định
bash run_all_main.sh                                  # luợt chính 200 dpi (resume được; engine chậm chạy tập con, xem §6)
bash run_variants.sh ; bash run_dpi.sh                # biến thể cấu hình VietOCR; 150/200/300 dpi
bash run_timing.sh                                    # đo tốc độ riêng (máy không chạy việc khác)
& "..\..\..\..\$py" -X utf8 aggregate.py              # -> results.csv, results_pages.csv
& "..\..\..\..\$py" -X utf8 score_vs_haiku.py         # -> results_vs_haiku.csv (chấm theo bản chép "bạc" của Haiku)
& "..\..\..\..\$py" -X utf8 baseline_diag.py          # chẩn đoán baseline cũ (§3)
& "..\..\..\..\$py" -X utf8 vocab_coverage.py         # từ điển nhận dạng của từng mô hình có chữ có dấu nào (§3)
```

Cài đặt (xem `requirements.txt`, mục `# OCR engines`): `rapidocr==3.10.0`, `vietocr==0.3.13` (`pip install --no-deps`),
`easyocr==1.7.2` (`--no-deps`), `einops`, `gdown`, `scikit-image`, `python-bidi`, `torchvision`.
Trọng số tải lần đầu từ mạng công khai (VietOCR: `vocr.vn` về `%TEMP%\vgg_seq2seq.pth`; rapidocr: modelscope; EasyOCR: GitHub release);
sau đó chạy offline. **Nên sao chép trọng số ra thư mục cố định** (`%TEMP%` có thể bị dọn).
PaddleOCR 3.7 cài trong **venv riêng** `_cache/venv_paddle` (lý do ở §6).

Máy: 64 lõi/128 GB, RTX 3060 12 GB **dùng chung** với tiến trình khác (7–10 GB VRAM bị chiếm, GPU thường 20–80% util do việc khác).
Điều này làm mọi số đo tốc độ chạy song song (lượt chính) rất nhiễu; số tốc độ đáng tin duy nhất là bảng ở §5 (chạy riêng).

## 2. Dữ liệu đánh giá

* **Pseudo-gold (39 trang born-digital)**: text layer thật (font thật, có dấu), chuẩn hoá NFC, gộp khoảng trắng. Toàn bộ kho chỉ có **61 trang
  born-digital, nằm trong đúng 3 thư mục**, nên không thể "rải đều nhiều thư mục": 10 trang của 1 hợp đồng Word 30 trang, 15 phiếu xuất kho, 14 đơn đặt hàng
  (các phiếu/đơn cùng khuôn mẫu ⇒ độ đa dạng thấp). Mỗi trang render 200 dpi (**clean**) và thêm bản **degraded** (xoay ngẫu nhiên |góc| ≤ 2°, blur Gauss σ 0,8–1,4,
  giảm tương phản α 0,6–0,8 + lệch sáng, nhiễu Gauss σ 6–10, JPEG q = 40; seed = sha1(đường dẫn|trang)).
* **Scan thật (30 trang, 20 thư mục)**: trang không có text layer; 3 trang/thư mục cho nhóm khó (`6. CUA HANG - BB MAU- VÂN`, `TU K.TRA PCCC- VÂN`, `8. CUA HANG - TU K.TRA PCCC- VÂN`,
  `_Biên bản giao nhận 2026`, `9. TỔNG HỢP HỒ SƠ CỬA HÀNG`: viết tay, con dấu, bảng), 1 trang/thư mục còn lại.
* **Bản chép "bạc" của Haiku** (do coordinator cung cấp, `teams/team1_ocr/gold/silver_llm/haiku`): dùng làm tham chiếu cho 30 trang scan thật (§4b).
  Trên 39 trang born-digital, Haiku đạt bag-recall 99,5% so với text layer (phần lớn lỗi còn lại là chỉ số trên `15⁰C`), nên đáng tin cho **chữ in**; **chữ viết tay vẫn cần ~10 trang người kiểm tra**.

**Metric** (script: `ocrlib.py`). Mọi chỉ số tính **không phân biệt hoa/thường** (casefold): một số PDF (Chromium/CSS `text-transform`) lưu chữ thường trong text layer nhưng
*hiển thị* chữ hoa, OCR đọc đúng bị tính sai; cột `cer_cs` trong `results.csv` giữ bản phân biệt hoa/thường.
* `CER`, `WER`: khoảng cách Levenshtein toàn chuỗi (NFC, khoảng trắng gộp), GT và kết quả OCR **cùng được sắp theo hàng hình học** (gom hộp theo toạ độ y, dung sai 0,6 × chiều cao dòng; trong hàng sắp theo x).
  CER vẫn nhạy với thứ tự đọc ở bảng/2 cột ⇒ có thêm `bag_f1`.
* `CER_nodiac`: như CER sau khi bỏ mọi dấu (đ→d) ⇒ phần còn lại là "sai chữ cái", chênh với CER là "mất/sai dấu".
* `diac_recall`: theo túi ký tự, Σ min(đếm GT, đếm OCR) / Σ đếm GT, chỉ trên ký tự có dấu tiếng Việt (không phụ thuộc thứ tự).
* `bag_f1`: F1 theo túi từ, so khớp chính xác (không phụ thuộc thứ tự đọc).
* Scan thật không có GT thật: `diac_ratio` (tỉ lệ chữ cái có dấu; tiếng Việt thật ≈ 0,25), `valid_syl` (tỉ lệ token là âm tiết có trong từ điển 860 âm tiết lấy từ text layer của kho — **thiên lệch**
  vì chỉ từ 3 thư mục khuôn mẫu), `valid_rule` (tỉ lệ token ≤ 7 ký tự hợp quy tắc chính tả âm tiết tiếng Việt, không cần từ điển, nhưng cũng cho qua nhiều từ tiếng Anh/không dấu ⇒ ít phân biệt), `mean_conf` (độ tin cậy engine, **không so được giữa các engine**).

## 3. Câu hỏi "dấu tiếng Việt đi đâu?" (đo được)

Giả thuyết cần phân xử: (A) mô hình mặc định của RapidOCR làm mất dấu, hay (B) text layer chất lượng thấp do app scan nhúng (CamScanner…) qua được kiểm tra "≥ 50 ký tự".

1. **Phần lớn kho không có text layer.** Trong 1246 trang của 336 PDF: **1182 trang (94,9%) không có text layer**; 61 trang born-digital; 3 trang (2 tài liệu) có lớp chữ **vô hình** (render mode 3) do máy scan nhúng: tỉ lệ chữ có dấu của lớp đó **= 0,000**.
   (`survey_pdfs.py`; chỉ 2/336 tài liệu ảnh hưởng.)
2. **Baseline cũ lấy trang 1 của 334 tài liệu** (`baseline_diag.py`, tiêu chí ≥ 50 ký tự như `generate_baseline_ocr.py`):
   | nguồn của bản ghi | số bản ghi | tỉ lệ chữ có dấu trung bình |
   |---|---|---|
   | RapidOCR (không có text layer) | **302** | **0,0018** (max 0,0127) |
   | text layer born-digital | 30 | 0,254 |
   | lớp chữ vô hình của máy scan (thuộc giả thuyết B) | 2 | 0,000 |
   → giả thuyết B chỉ giải thích **2/334** bản ghi; **302/334 (90%)** mất dấu do RapidOCR. Với 32 bản ghi còn lại baseline vẫn đúng.
3. **Thí nghiệm đối chứng** (`results.csv`): cùng 39 trang born-digital (GT có dấu, tỉ lệ chữ có dấu ≈ 0,25) render sạch 200 dpi: `rapidocr_onnxruntime` 1.2.3 mặc định có **diac_recall = 0,000**, `CER_nodiac` = 0,119 vs `CER` = 0,263
   (nghĩa là nó đọc được chữ cái nền nhưng **không bao giờ** sinh ra ký tự có dấu); VietOCR cùng ảnh: diac_recall 0,979.
4. **Nguyên nhân gốc: từ điển nhận dạng** (`vocab_coverage.py`, đọc `character` trong metadata ONNX / vocab của VietOCR). Số chữ cái **thường** có dấu tiếng Việt (tổng 67, gồm `đ`) nằm trong từ điển:
   | mô hình | từ điển | có mặt / 67 | thiếu (ví dụ) |
   |---|---|---|---|
   | `rapidocr_onnxruntime` 1.2.3 (`ch_PP-OCRv3_rec`) | 6623 | **9** | `đ ư ơ ô ê ả ạ ắ ế ề ộ …` |
   | rapidocr 3.10 PP-OCRv5 latin (mobile) | 503 | 17 | `ạ ặ ế ệ ộ ợ ự …` |
   | rapidocr 3.10 PP-OCRv6 multi (small) | 18708 | 23 | `ạ ặ ế ệ ộ ợ ự …` |
   | VietOCR (`vgg_seq2seq`/`vgg_transformer`) | 229 | **67** | — |
   ⇒ **(A) đúng**: mô hình mặc định của baseline không có 58/67 chữ cái này trong từ điển nên không thể xuất ra. Ngay cả PP-OCRv5-latin/v6 (dùng cho "tiếng Việt" ở PaddleOCR) mới chỉ có 17–23/67.
   Hệ quả đo được trên scan thật (§4b): `diac_ratio` của baseline **0,005** so với 0,24 của VietOCR (kỳ vọng ≈ 0,25).
5. **Chữ dính** ("CONGTYCOPHANTHUONGMAI"): trên trang sạch render, baseline giữ nguyên số token (tỉ lệ token OCR/GT `tok_ratio` = 0,99) — tức dính chữ **không** phải lỗi chung mà xuất hiện trên ảnh scan/đã xuống cấp:
   ở bản degraded `tok_ratio` của baseline chỉ 0,64 (mất/dính ~36% token) so với 1,04 của VietOCR. (Suy luận: DB + CTC với từ điển CJK phát ra ít ký tự cách khi khoảng cách giữa từ hẹp; chưa tách riêng nguyên nhân.)

## 4. Kết quả

### 4a. Trang born-digital (pseudo-gold), 200 dpi, tập chung 10 trang (stride 4) × {clean, degraded}

Các engine chậm (transformer, EasyOCR, Paddle) chỉ chạy tập con nên bảng so sánh trên **10 trang chung** (chọn trang thứ 0,4,8,… của `sample_gold_pages.csv`); số nhỏ ⇒ sai số lớn, chỉ dùng để xếp hạng thô.

| engine | clean CER | clean WER | clean CER_nodiac | clean diac_recall | clean bag_F1 | degraded CER | degraded diac_recall | degraded bag_F1 |
|---|---|---|---|---|---|---|---|---|
| `rapidocr_onnxruntime` 1.2.3 (baseline) | 0,260 | 0,770 | 0,115 | **0,000** | 0,277 | 0,393 | 0,000 | 0,163 |
| rapidocr 3.10 PP-OCRv5 latin | 0,218 | 0,563 | 0,142 | 0,288 | 0,496 | 0,288 | 0,277 | 0,478 |
| rapidocr 3.10 PP-OCRv6 multi small | 0,171 | 0,489 | 0,154 | 0,481 | 0,562 | 0,264 | 0,397 | 0,516 |
| EasyOCR 1.7.2 `['vi','en']` | 0,092 | 0,143 | 0,090 | 0,988 | 0,918 | 0,239 | 0,719 | 0,665 |
| **DB-det + VietOCR seq2seq** | **0,082** | **0,127** | 0,079 | 0,978 | 0,931 | **0,185** | **0,972** | **0,933** |
| DB-det + VietOCR transformer | 0,080 | 0,116 | 0,077 | 0,981 | 0,942 | 0,187 | 0,971 | 0,928 |

Trên **toàn bộ** số trang đã chạy (`results.csv`, subset `all`): baseline (39 trang) clean CER 0,263 / degraded 0,364; VietOCR seq2seq (39 trang) clean 0,088 / degraded 0,150; transformer (23/20 trang) 0,077 / 0,179;
EasyOCR (15/10 trang) 0,065 / 0,239; PaddleOCR 3.7 `lang=vi` (6/4 trang, CPU rất chậm) clean CER 0,136, diac_recall 0,485.

Đọc kết quả:
* VietOCR giữ gần như toàn bộ dấu (0,97–0,98), kể cả khi ảnh xuống cấp; EasyOCR tốt trên ảnh sạch nhưng **rơi mạnh khi xuống cấp** (CER 0,239, diac_recall 0,72, WER 0,46) và chậm hơn nhiều.
* Còn lại ~8% CER của VietOCR trên ảnh sạch chủ yếu là **dấu câu cuối ô bị cắt** (`Số:` → `Số`, `-` ở cuối dòng) và thứ tự đọc ở bảng, không phải sai chữ (CER_nodiac 0,079 chỉ thấp hơn CER 0,003).
* transformer vs seq2seq: chênh không có ý nghĩa (±0,002 CER; bag_F1 0,942 vs 0,931) nhưng transformer **chậm gấp ~3** (§5) ⇒ chọn seq2seq.

### 4b. Scan thật (30 trang), 200 dpi

Chấm theo bản chép Haiku (bag-of-words, độ phủ từ; `score_vs_haiku.py`) **và** theo các chỉ số proxy không cần GT:

| engine | số trang | **bag_recall vs Haiku** | bag_precision | diac_recall vs Haiku | diac_ratio | valid_syl | valid_rule | mean_conf |
|---|---|---|---|---|---|---|---|---|
| `rapidocr_onnxruntime` 1.2.3 (baseline) | 30 | **0,168** | 0,196 | 0,001 | 0,005 | 0,237 | 0,845 | 0,833 |
| rapidocr 3.10 PP-OCRv5 latin | 15 | 0,392 | 0,426 | 0,244 | 0,134 | 0,398 | 0,807 | 0,920 |
| rapidocr 3.10 PP-OCRv6 multi small | 15 | 0,422 | 0,455 | 0,355 | 0,134 | 0,444 | 0,770 | 0,932 |
| EasyOCR 1.7.2 | 8 | 0,624 | 0,638 | 0,725 | 0,235 | 0,661 | 0,769 | 0,646 |
| DB-det + VietOCR seq2seq | 30 | 0,781 | 0,765 | 0,900 | 0,239 | 0,804 | 0,923 | 0,789 |
| DB-det + VietOCR transformer | 15 | 0,764 | 0,762 | 0,861 | 0,248 | 0,758 | 0,887 | 0,859 |
| **seq2seq + chuẩn hoá nền khi giấy có màu (cấu hình chọn)** | 30 | **0,801** | 0,782 | 0,918 | 0,240 | 0,814 | 0,928 | 0,786 |

(Trên 15 trang chung: seq2seq 0,748, seq2seq+nền 0,785, transformer 0,764, baseline 0,181, v5-latin 0,392, v6 0,422.) PaddleOCR chưa chạy trên scan thật (một trang mất ~93–500 giây trên CPU).
**Lưu ý đọc số**: (i) `mean_conf` không so được giữa các engine (baseline "tự tin" 0,83 dù mất dấu hoàn toàn: nó tự tin về chuỗi sai); (ii) `valid_rule` gần như không phân biệt (baseline 0,845 vs 0,928) vì nó cho qua văn bản bỏ dấu;
(iii) bag_recall chưa phạt thứ tự đọc nhưng bao gồm cả chữ viết tay mà Haiku cũng có thể đọc sai ~3% (Haiku vs Sonnet bất đồng CER 2,8% trên 8 trang scan).

**Đối chiếu bằng mắt (4 trang scan mở ra xem rồi so với đầu ra từng engine):**
* *Biên bản lấy mẫu* (in + viết tay): baseline ra `Tén, loai xang dau`, `CTYCPTM-DVHIEPHOA`; VietOCR ra `Tên, loại xăng dầu`, `CTY CP TM-DV HIỆP HÒA` đúng. Ô viết tay (loại xăng, số niêm phong) **sai ở cả hai** (VietOCR `DO 0,000` thay cho số viết tay).
* *Biên bản tự kiểm tra PCCC* (có bảng, ngày viết tay): VietOCR đúng phần in nhưng **gộp dòng tiêu đề** (`CÔNG TÁC PHÒNG CHỮA CHỮA CHÁY BIÊN BẢN TỰ KIỂM TRA`) và đọc bảng theo hàng lẫn cột; ngày viết tay hỏng.
* *GCN ĐKKD nền hoa văn vàng*: **VietOCR thường gặp thất bại** (`0 g tiêng g ngới người a S`; 876 ký tự, valid_syl 0,58); baseline cũng chỉ đọc được vài dòng. Sau chuẩn hoá nền (§4c, cấu hình chọn) valid_syl 0,84 và 1370 ký tự (so với 0,58 và 876 ký tự). Đây là chỗ proxy phản ánh đúng quan sát bằng mắt.
* *Hợp đồng in rõ (QĐKV3)*: VietOCR gần như hoàn hảo (diacritic đầy đủ); baseline ra `Phuong tien van chuyén cua Ben A`. Proxy `valid_syl` 0,98 vs 0,24.
Cả proxy lẫn mắt đều cùng xếp hạng: VietOCR ≫ EasyOCR > PP-OCR v6/v5 > baseline.

### 4c. Tinh chỉnh VietOCR đã thử (`run_variants.sh`; tập con, so với seq2seq trần)

| biến thể | clean CER (10 trang) | degraded CER | scan bag_recall vs Haiku | kết luận |
|---|---|---|---|---|
| seq2seq trần | 0,082 | 0,185 | 0,781 (30) / 0,748 (15 chung) | mốc |
| + nong hộp 0,3 × chiều cao | 0,091 | 0,185 | 0,727 (15) | **tệ hơn** (kéo thêm chữ của hộp bên cạnh) — bỏ |
| + chuẩn hoá nền cho mọi trang | 0,122 | 0,202 | 0,763 (15) | làm tăng CER ~0,03 trên trang trắng sạch — không bật cho mọi trang |
| + chuẩn hoá nền **chỉ khi độ bão hoà trung vị của trang ≥ 15/255** | 0,082 | 0,185 | **0,801 (30)** | **chọn**: trang hoa văn vàng valid_syl 0,58 → 0,84, thẻ GCN nền xanh nhỉnh hơn, trang trắng không đổi |
| + thu nhỏ ảnh đưa vào bộ phát hiện (cạnh dài ≤ 1280) | 0,097 | 0,213 | 0,800 (30) | nhanh hơn ~20% nhưng **hại trang số dày** — bỏ |

Cảnh báo: ngưỡng bão hoà 15 được chọn **sau khi xem** 30 trang scan này (và chấm trên chính 30 trang đó) nên số 0,801 hơi lạc quan.
`image_max_width` = 1024 của VietOCR (dòng dài > 16:1 bị nén ngang về 512 px) **chưa thử** do thiếu thời gian máy; hợp đồng dòng ~100 ký tự vẫn đạt CER 0,017 nên có vẻ không nghiêm trọng.

### 4d. DPI (VietOCR seq2seq trần, tập con 10 trang gold × 2 và 15 trang scan)

| dpi | clean CER | clean WER | degraded CER | degraded bag_F1 | scan valid_syl (15 trang) |
|---|---|---|---|---|---|
| 150 | 0,082 | 0,134 | 0,225 | 0,874 | 0,771 |
| **200** | 0,082 | 0,127 | 0,185 | 0,933 | 0,762 |
| 300 | 0,093 | 0,168 | 0,183 | 0,944 | 0,761 |

⇒ **200 dpi**: 150 dpi hỏng khi ảnh xuống cấp (CER 0,225), 300 dpi không hơn mà làm trang sạch tệ hơn (0,093) và chậm hơn. Chỉ test với seq2seq (engine tốt nhất); không test dpi cho engine khác.

## 5. Tốc độ (chạy riêng, máy không có việc khác của tôi; 5 trang scan, 200 dpi, 16 luồng, **không tính khởi tạo**)

| engine | thiết bị | giây/trang (median) |
|---|---|---|
| rapidocr 3.10 PP-OCRv6 multi small | CPU | 3,8 |
| **DB-det + VietOCR seq2seq** | CPU | **5,9** |
| DB-det + VietOCR seq2seq | GPU | 5,9 (không nhanh hơn CPU với 1 tiến trình: vòng giải mã tuần tự bị giới hạn bởi CPU/GPU dùng chung) |
| DB-det + VietOCR seq2seq + chuẩn hoá nền (mọi trang) | CPU | 5,5 |
| rapidocr 3.10 PP-OCRv5 latin | CPU | 12,2 |
| DB-det + VietOCR transformer | GPU / CPU | 15,8 / 17,1 |
| EasyOCR | GPU / CPU | 15,8 / 30,7 |
| `rapidocr_onnxruntime` 1.2.3 (baseline) | CPU | 21,6 (chạy 200 dpi; baseline cũ chạy 150 dpi nên nhanh hơn) |
| PaddleOCR 3.7 `vi` (PP-OCRv6 medium, oneDNN tắt) | CPU | 93 (1 trang) |

**Quy mô cho cả kho (đo được trong Task 2):** một tiến trình chậm, nhưng nhiều tiến trình dùng GPU hiệu quả hơn nhiều: 6 worker × 2 luồng, VietOCR trên GPU chạy 53 trang trong 2,5 phút (0,35 trang/giây) so với 0,08 trang/giây của 24 worker × 1 luồng chỉ dùng CPU
(CPU là nút cổ chai, 12 worker GPU lại chậm hơn: 0,28 trang/giây và gần cạn VRAM). Chi tiết ở `../02_dataset_v2/RESULTS.md`.

## 6. Engine nào, vì sao, và những gì bị bỏ

**Chọn: bộ phát hiện DB (PP-OCRv5 mobile qua `rapidocr` 3.10) + VietOCR `vgg_seq2seq`, 200 dpi, chuẩn hoá nền khi giấy có màu.**
* Độ chính xác: tốt nhất hoặc ngang tốt nhất ở mọi bài đo; thắng EasyOCR rõ rệt khi ảnh xuống cấp và trên scan thật; thắng baseline ở mọi chỉ số (bag_recall vs Haiku 0,80 vs 0,17).
* Tốc độ: ~3× nhanh hơn transformer, 5× nhanh hơn EasyOCR/baseline; chạy được hoàn toàn trên CPU (GPU chỉ để chạy nhiều worker).
* Giấy phép (**suy luận từ trang dự án, chưa nhờ pháp chế xác nhận**): rapidocr, mô hình PP-OCR, VietOCR (mã), EasyOCR, PaddleOCR: Apache-2.0. Trọng số VietOCR tải từ `vocr.vn` **không thấy ghi giấy phép riêng** — cần kiểm tra trước khi triển khai thương mại.
  PyMuPDF (đã dùng cho text layer/render) là AGPL-3.0 (có giấy phép thương mại của Artifex) — lưu ý chung của dự án.
* Chạy offline: có, sau lần tải trọng số đầu.

**Bỏ/không dùng:** baseline cũ (thiếu dấu); PP-OCRv5-latin/v6 qua rapidocr (từ điển thiếu dấu, diac_recall 0,29–0,48); EasyOCR (tốt trên ảnh sạch nhưng yếu khi xuống cấp, chậm); VietOCR transformer (không chính xác hơn rõ ràng, chậm gấp 3; vẫn là lựa chọn nếu sau này có GPU rảnh và cần thêm vài phần trăm trên chữ in);
PaddleOCR 3.x `lang=vi` (PP-OCRv6 medium, từ điển vẫn thiếu dấu; CPU 90–500 giây/trang; **không** cài được an toàn vào venv chung: kéo `opencv-contrib-python` đè lên `opencv-python`, hạ PyYAML ⇒ cài ở venv riêng; trên CPU phải tắt oneDNN (`enable_mkldnn=False`) vì lỗi `ConvertPirAttribute2RuntimeAttribute`;
Tesseract không cài, không thử).

**Lệch so với yêu cầu ban đầu (nêu thẳng):** (1) PaddleOCR không cài vào venv chung mà vào venv riêng; (2) vì máy dùng chung và quá chậm khi nhiều tiến trình chạy cùng lúc, các engine chậm chỉ chạy **tập con** (transformer: 23 trang gold clean / 20 degraded, 15 scan; EasyOCR: 15 / 10 gold, 8 scan; Paddle: 6 / 4 gold, 0 scan) nên so sánh dựa trên tập chung nhỏ;
(3) dpi chỉ test cho seq2seq.

## 7. Lỗi còn tồn tại (failure modes, quan sát được)

1. **Chữ viết tay**: sai gần như hoàn toàn (số niêm phong, tên, ngày trong biên bản); `mean_conf` vẫn khá cao ⇒ **không dùng độ tin cậy để lọc chữ viết tay**. Cần ~10 trang viết tay do người kiểm tra (xem `teams/team1_ocr/gold/`).
2. **Con dấu đè lên chữ** và chữ ký: đoạn bị đè thành chuỗi rác; con dấu tròn đôi khi cho vài dòng "ảo".
3. **Bảng**: thứ tự đọc (gộp tiêu đề nhiều dòng thành một hàng; trộn theo hàng thay vì theo ô), dấu `|`/viền bảng có thể bị đọc thành `I`, `l`.
4. **Nền hoa văn/màu**: xem §4b; đã giảm nhưng chưa hết (chữ ghi chú nhỏ trên nền vàng vẫn kém). Trang xoay 90° (một bảng xoay ngang trong mẫu) cần bước tự xoay; bước này có trong `scripts/build_ocr_dataset.py`
   nhưng **chưa được đánh giá riêng trong bake-off** (số trang bị xoay có trong `../02_dataset_v2/RESULTS.md`).
5. **Dấu câu cuối ô/dòng bị cắt** (`Số:` → `Số`), ký tự `-`, `.` ở rìa hộp: do hộp DB hơi chặt; nong hộp làm tệ hơn (§4c) nên chưa sửa.
6. Dòng rất dài bị VietOCR nén về 512 px chiều ngang (chưa đo ảnh hưởng, xem §4c).
7. Trang trống/gần trống (chỉ con dấu): ra chuỗi ngắn rác hoặc rỗng (đánh dấu `empty_text` trong dữ liệu v2).

## 8. Giới hạn của đánh giá này

* Pseudo-gold **sạch hơn scan thật rất nhiều** và chỉ gồm 3 loại biểu mẫu (hợp đồng Word, phiếu xuất kho, đơn đặt hàng; 39 trang, 10 trang chung cho engine chậm): CER ở đó **không** phải CER trên scan thật. Bản degraded chỉ mô phỏng, không có viết tay/con dấu/gấp nếp.
* Scan thật chỉ có tham chiếu "bạc" (Haiku, bất đồng với Sonnet 2,8% CER trên 8 trang scan); cần gold do người gõ (`teams/team1_ocr/gold/gold_pages_todo.csv`, 25 trang; chạy `eval_on_gold.py` khi có `transcripts/`).
* Từ điển âm tiết của `valid_syl` chỉ 860 âm tiết (3 thư mục khuôn mẫu) ⇒ thiên lệch; `valid_rule` quá dễ.
* Số tốc độ lượt chính nhiễu do máy dùng chung; chỉ dùng bảng §5. GPU bị tiến trình khác chiếm (7–10 GB, 20–80% util), nên số GPU là "dưới tải ngoài".
* Mẫu nhỏ (10 trang chung, 15 trang scan chung): chênh dưới ~0,01 CER không có ý nghĩa thống kê. Ngưỡng bão hoà 15 chọn sau khi thấy dữ liệu (§4c).
* Không đo OCR trên PDF scan >30 trang/tài liệu ngoài 30 trang đầu (xem Task 2).
