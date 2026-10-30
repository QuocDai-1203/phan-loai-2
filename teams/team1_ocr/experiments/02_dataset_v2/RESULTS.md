# Dataset OCR v2: `data/ocr_v2.jsonl`

Dựng bằng `scripts/build_ocr_dataset.py` (engine: bộ phát hiện DB PP-OCRv5 mobile + VietOCR `vgg_seq2seq`, 200 dpi; lý do chọn ở `../01_engine_bakeoff/RESULTS.md`).
Thống kê sinh bởi `dataset_stats.py` (`stats.json`), file này sinh bởi `make_results_md.py`. Mọi số dưới đây **đo được** từ tệp dữ liệu hoặc log (`build.log`), trừ chỗ ghi "suy luận".

## 1. Lệnh chạy (tái hiện)

```powershell
# từ thư mục gốc repo
.venv\Scripts\python.exe -X utf8 scripts\build_ocr_dataset.py --limit 3                                          # chạy thử (không ghi đè data/ocr_v2.jsonl)
.venv\Scripts\python.exe -X utf8 scripts\build_ocr_dataset.py --device cuda:0 --workers 6 --threads 2 --resume   # chạy đầy đủ (cấu hình đã dùng)
.venv\Scripts\python.exe -X utf8 teams\team1_ocr\experiments\02_dataset_v2\dataset_stats.py                    # thống kê
```
`--resume` dùng cache theo tài liệu ở `_cache/docs/<doc_id>.json` (không commit; khoá cache gồm engine, dpi, max-pages, cấu hình nền/phát hiện); tài liệu có trang lỗi sẽ được làm lại.
Mã thoát 1 nếu còn trang lỗi hoặc thiếu tài liệu (lần chạy này: **0 lỗi**). Không cần GPU: bỏ `--device cuda:0` (CPU) thì chậm hơn nhiều khi chạy nhiều worker (§3).

## 2. Tổng kết

| | |
|---|---|
| tài liệu | **336** (334 trong 19 thư mục + 2 PDF ở gốc, `folder_label = null`) |
| trang xử lý | **1084** (tối đa 30 trang/tài liệu; **6** tài liệu bị cắt: 5 sổ PCCC 46–53 trang, 1 biên bản mẫu 93 trang) |
| trang theo nguồn | `ocr` **1020**, `text_layer` **61**, `embedded_ocr_layer+ocr` **3** |
| lỗi | **0** trang |
| trang gần như trống (< 5 ký tự, không lỗi) | **57** (tính cả bản sao; 68 trang < 30 ký tự) |
| tổng ký tự | 1,523,327 |
| kích thước tệp | 2,4 MB |
| độ tin cậy VietOCR trung bình (trang OCR thật) | 0.782; 40 trang < 0,6 |

Kiểm tra tự động trên tệp: sắp theo `relative_path`; `doc_id`, `page_count`, `folder_label` khớp 100% với `data/manifest.csv` (336/336); `doc_id` = `sha1(rel NFC).hexdigest()[:12]`.

**Quy tắc dùng text layer** (chi tiết trong docstring của script): chỉ dùng khi ≥ 30 chữ cái, chữ hiển thị (không phải render mode 3) ≥ 50%, trang không phải ảnh phủ ≥ 80% diện tích kèm lớp chữ, ký tự rác < 2%.
Kết quả: **61** trang đạt (đều born-digital có dấu); **3** trang (2 tài liệu: `HDVC HOÀNG GIA HÂN-HIEP HOA.PDF` trang 1–2, `HK - Cao Thị Như Tuyết … ký BBĐC.pdf` trang 1) bị loại vì lớp chữ vô hình do máy scan nhúng
(`embedded_layer_rejected = invisible_text(render_mode_3)`) và được OCR lại: lớp chữ cũ có **0%** chữ cái có dấu, kết quả mới có **27–29%** (`stats.json`, `embedded_layer_pages`).
Trường phụ ngoài đặc tả (tuỳ chọn, không phá schema): `flags` (`bg_normalized`, `rotated_90/270/180`, `no_boxes`, `empty_text`, `copied_from_exact_duplicate:<doc_id>`) và `embedded_layer_rejected`.
Với trang `text_layer`: `dpi = null`, `mean_conf = null`, `engine = pymupdf-<phiên bản>/get_text`.

**Tệp trùng byte** (cùng sha256 với tệp khác; 32 tài liệu = 113 trang): OCR một lần, bản còn lại **sao chép kết quả** (`copied_from_exact_duplicate:<doc_id gốc>`, `seconds = 0`).
Vì vậy chỉ **910** trang OCR thật được chạy; số tốc độ chỉ tính các trang này.

## 3. Tốc độ

* **Chạy đầy đủ: 46,3 phút thực, 0,39 trang/giây** (1084 trang = 910 OCR thật + 61 text layer + 113 sao chép), GPU 6 worker × 2 luồng. Cộng dồn các worker: 18.1 giây/trang (median 15.4) — cao vì 6 worker chạy song song trên máy dùng chung; một tiến trình chạy riêng ~3–6 giây/trang.
* **Vì sao đổi cấu hình** (cùng 24 tài liệu = 53 trang; máy dùng chung nên số tuyệt đối dao động):

  | cấu hình | trang/giây |
  |---|---|
  | CPU, 6 worker × 8 luồng (chạy đầu tiên, ~50 giây/trang/worker) | ≈ 0,12 |
  | CPU, 24 worker × 1 luồng | 0,08 |
  | **GPU (VietOCR), 6 worker × 2 luồng** | **0,35** (chọn) |
  | GPU, 12 worker × 2 luồng | 0,28 (VRAM gần cạn: 11,7/12,3 GB) |

  (Suy luận: nhiều tiến trình CPU tranh nhau lõi; GPU gỡ phần CNN/giải mã khỏi CPU. Một tiến trình GPU đơn lẻ **không** nhanh hơn CPU: 5,9 giây/trang cả hai.)
* Thử `--det-max-side 1280` (thu nhỏ ảnh cho bộ phát hiện): nhanh hơn ~20% nhưng CER trang số dày tăng 0,082 → 0,097 ⇒ **không dùng** (mặc định 0).

## 4. Dấu tiếng Việt: trước và sau (theo thư mục)

"Trước" = `baseline_ocr_335.jsonl` (chỉ trang 1); "sau (tr.1)" = trang 1 của v2 (so cùng trang); "sau (mọi trang)" = toàn bộ trang v2.
Cột dấu = tỉ lệ chữ cái có dấu tiếng Việt (văn bản thật ≈ 0,25–0,28). "Token dài" = tỉ lệ token ≥ 12 chữ cái (thước đo chữ dính kiểu `CONGTYCOPHANTHUONGMAI`).

| thư mục | tài liệu | trang | dấu trước (tr.1) | dấu sau (tr.1) | dấu sau (mọi trang) | token dài trước | token dài sau |
|---|---|---|---|---|---|---|---|
| (root) | 2 | 14 | – | 0,251 | 0,257 | – | 0,000 |
| 10. GCN VC HNH | 20 | 40 | 0,000 | 0,253 | 0,261 | 0,056 | 0,000 |
| 5. TỔNG HỢP HỒ SƠ XE | 20 | 39 | 0,002 | 0,234 | 0,229 | 0,022 | 0,003 |
| 6. CUA HANG - BB MAU- VÂN | 10 | 65 | 0,005 | 0,253 | 0,248 | 0,010 | 0,000 |
| 6. HOP DONG MUON BON | 7 | 29 | 0,002 | 0,284 | 0,281 | 0,000 | 0,000 |
| 6. HOP DONG THUE KHO- Vi | 6 | 34 | 0,001 | 0,276 | 0,269 | 0,000 | 0,000 |
| 8. CUA HANG - TU K.TRA PCCC- VÂN | 5 | 138 | 0,000 | 0,290 | 0,274 | 0,000 | 0,000 |
| 8. GCN Lop dao tao van chuyen hang chay no | 20 | 40 | 0,000 | 0,256 | 0,261 | 0,044 | 0,000 |
| 9. TỔNG HỢP HỒ SƠ CỬA HÀNG | 25 | 71 | 0,002 | 0,252 | 0,273 | 0,012 | 0,002 |
| TU K.TRA PCCC- VÂN | 5 | 142 | 0,001 | 0,297 | 0,278 | 0,000 | 0,000 |
| _1. Giay DKKD khach hang | 23 | 48 | 0,002 | 0,260 | 0,255 | 0,003 | 0,000 |
| _1. HOP DONG DAI LY NHUONG QUYEN | 25 | 84 | 0,003 | 0,270 | 0,276 | 0,004 | 0,000 |
| _2. Giay Du Dieu Kien Khach hang | 25 | 45 | 0,001 | 0,282 | 0,280 | 0,001 | 0,000 |
| _2. HOP DONG KINH TE | 25 | 56 | 0,002 | 0,278 | 0,283 | 0,001 | 0,000 |
| _3. HOP DONG DAU VAO-Diem | 20 | 84 | 0,009 | 0,272 | 0,280 | 0,002 | 0,001 |
| _4. THANH LÝ HỢP ĐỒNG | 14 | 20 | 0,003 | 0,277 | 0,281 | 0,002 | 0,000 |
| _5. HOP DONG VAN CHUYEN | 24 | 57 | 0,003 | 0,268 | 0,275 | 0,002 | 0,000 |
| _Biên bản giao nhận 2026 | 20 | 21 | 0,002 | 0,213 | 0,214 | 0,005 | 0,003 |
| _PHIẾU XUẤT KHO MUA HÀNG 2026 | 20 | 37 | 0,185 | 0,247 | 0,221 | 0,005 | 0,000 |
| _Đơn đặt hàng - mua vào 2026 | 20 | 20 | 0,136 | 0,264 | 0,264 | 0,009 | 0,001 |
| **toàn kho** | 336 | 1084 | **0,022** | **0,265** | | 0,005 | 0,001 |

(2 PDF ở gốc không có trong baseline ⇒ "–". `_PHIẾU XUẤT KHO` và `_Đơn đặt hàng` trước đã có dấu vì là PDF born-digital dùng text layer; các thư mục còn lại ≈ 0.)
Toàn kho: tỉ lệ chữ có dấu (trang 1) tăng **0,022 → 0,265**; token ≥ 12 chữ cái giảm 0,005 → 0,001.

## 5. Lỗi/nhược điểm còn lại (quan sát; một phần là suy luận)

1. **Trang trống/gần trống: 57 trang** (+ bản sao). Kiểm tra mẫu 25 trang: 22 hoàn toàn trắng (tỉ lệ điểm tối 0,000), 3 có ≈ 1% điểm tối (con dấu/chữ ký) nhưng không có chữ. 49 trang gắn `no_boxes`/`empty_text`. Tập trung ở sổ PCCC (31 trang), `6. HOP DONG THUE KHO` (7), `_1. HOP DONG DAI LY` (6). Bộ phân loại cần xử lý trang rỗng; đây không phải lỗi OCR.
2. **Tự xoay trang**: 50 trang bị xoay (`rotated_90`: 13, `rotated_270`: 35, `rotated_180`: 2; gồm cả bản sao): 31 trang thật (≥ 200 ký tự, median độ tin cậy 0,80, chủ yếu bảng ngang của sổ PCCC) nhưng **9 trang gần trống bị xoay nhầm** (con dấu/chữ ký đứng tạo hộp đứng) ra vài ký tự rác (độ tin cậy ≈ 0,2). Chưa có gold hướng trang nên **chưa đánh giá chính xác** bước xoay.
3. **Chữ viết tay** (ngày, số niêm phong, tên, nhiều ô biên bản) vẫn sai và `mean_conf` không báo được; **~10 trang cần người kiểm tra** (`teams/team1_ocr/gold/`). Con dấu đè chữ, chữ ký sinh dòng rác (nhiều ký tự đơn lẻ).
4. **Bảng và tiêu đề nhiều dòng**: thứ tự đọc theo hàng hình học nên có thể trộn ô/hàng hoặc gộp hai dòng sát nhau. Ít ảnh hưởng tới phân loại theo từ khoá, ảnh hưởng tới trích xuất theo ô.
5. Dấu câu cuối ô/dòng đôi khi mất (`Số:` → `Số`); số tiền/mã số cần kiểm tra lại bằng quy tắc ở khâu trích xuất.
6. **40 trang có độ tin cậy < 0,6** (giấy phép/GCN chụp nghiêng, nền hoa văn, `6. HOP DONG THUE KHO/HDB 2017-.pdf` trang 1 = 0,40). Có thể dùng `mean_conf` + `n_chars` để chọn trang đưa người xem lại (không dùng được cho chữ viết tay).
7. **6 tài liệu bị cắt ở 30 trang** (sổ PCCC 46–53 trang, biên bản mẫu 93 trang): phần sau không được OCR; phân loại chỉ cần đầu tài liệu.
8. Trọng số VietOCR nằm ở `%TEMP%\vgg_seq2seq.pth` (nên sao chép ra thư mục cố định). `mean_conf` của VietOCR không so được với engine khác.
9. **Chưa có gold thật** để đo CER của bộ dữ liệu này: chất lượng chữ in chỉ được xác nhận gián tiếp qua bản chép Haiku (bag-recall 0,80 trên 30 trang scan) và pseudo-gold (bake-off).
