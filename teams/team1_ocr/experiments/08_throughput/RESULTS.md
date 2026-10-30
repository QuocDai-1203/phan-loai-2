# T4 bước 5 — Thông lượng OCR của `src/ocr` (24 tài liệu / 53 trang)

> `labels_v2.csv` sha1[:10] = `eb3348713a` · ngày 2026-10-15 (23:00–23:13) · nguồn: PDF gốc trong kho, OCR bằng engine trong `src/ocr` (không dùng `ocr_v2.jsonl`).
> Tái lập một dòng: `.venv\Scripts\python.exe -X utf8 teams\team1_ocr\experiments\08_throughput\bench_throughput.py --configs 6x2x16 6x2x32 4x2x16 3x4x16 --budget-min 10`
> (mỗi cấu hình = `workers x threads x batch`; kết quả ghi `throughput.csv`; bản thô ở `_scratch/` đã `.gitignore`).

## 1. Tập đo

24 tài liệu = tập mà `build_ocr_dataset.py --limit 24` chọn (lấy đều mỗi 14 tài liệu trong 336 tài liệu xếp theo `relative_path`; danh sách `doc_id` ở `doc_ids_24.txt`). Tập này có **đúng 53 trang** (khớp báo cáo 02): 51 trang cần OCR thật, 2 trang dùng text layer.
Mỗi cấu hình chạy `scripts/build_ocr_dataset.py` trong tiến trình con, dùng cache và đầu ra riêng ở `_scratch/` (không đụng `data/ocr_v2.jsonl`), GPU `cuda:0`, `--dpi 200`. Thời gian là **thời gian thực của tiến trình con**, gồm cả nạp mô hình ở mỗi worker và băm sha256 24 tệp; VRAM/độ sử dụng lấy mẫu `nvidia-smi` mỗi giây (VRAM của **cả GPU**, không tách riêng được phần của mình).

## 2. Kết quả (RTX 3060 12 GB, **GPU dùng chung**, mỗi cấu hình chạy 1 lần)

| cấu hình (worker × luồng × batch) | thời gian | trang/giây (53 trang) | trang OCR/giây (51) | VRAM GPU trước → đỉnh (MiB) | GPU dùng trung bình | GPU đang bận trước khi chạy |
|---|---|---|---|---|---|---|
| 6 × 2 × 16 | 310,4 s | **0,171** | 0,164 | 5818 → 9901 | 50% | 66% (người khác đang dùng) |
| 6 × 2 × 32 | 246,5 s | **0,215** | 0,207 | 851 → 10697 | 39% | 0% (rảnh lúc bắt đầu) |
| 4 × 2 × 16 | 253,3 s | **0,209** | 0,201 | 4741 → 8754 | 44% | 0% |
| 3 × 4 × 16 | không chạy: hết ngân sách GPU 15 phút (3 cấu hình đã dùng 13,5 phút) | | | | | |

* Cả ba cấu hình cho **cùng một văn bản** (băm sha1 của toàn bộ văn bản 53 trang đều `b33c27ec48`, 0 lỗi): batch và số worker không đổi kết quả, chỉ đổi tốc độ.
* **Không tách được** tác động của từng tham số: mỗi cấu hình chỉ một lần chạy, máy dùng chung, và lúc chạy cấu hình đầu một tiến trình khác đang chiếm GPU 66% (VRAM nền 5,8 GB) còn hai lần sau GPU rảnh lúc bắt đầu. Chênh 6×2×16 so với 6×2×32 (0,171 so với 0,215) lẫn lộn giữa batch và tải của người khác; 6 worker so với 4 worker (0,215 so với 0,209) không khác nhau trong sai số của một lần chạy. Không có khoảng tin cậy vì không có lần chạy lặp.
* Số tham chiếu từ báo cáo 02, cùng 53 trang, chạy trong lần dựng dữ liệu: 6×2 GPU **0,35** trang/giây (2,5 phút); 12 worker 0,28 (VRAM 11,7/12,3 GB, gần cạn); CPU 24 worker × 1 luồng 0,08; một tiến trình GPU ≈ 5,9 s/trang (≈ 0,17 trang/giây). Lần đo này (0,17–0,22) **chậm hơn** lần đó gần gấp đôi cho cùng cấu hình 6×2: nguyên nhân chưa xác định (tải người khác trên GPU, hai lần chạy cách nhau 4 ngày, phiên bản thư viện), không thể tách bằng dữ liệu hiện có.
* VRAM: đỉnh toàn GPU 8,8–10,7 GB (gồm cả tiến trình của người khác, nền 0,9–5,8 GB). Nếu trừ nền đầu mỗi lần thì phần của mình khoảng 4–10 GB cho 4–6 worker, nhưng nền của người khác đổi trong lúc chạy nên không đáng tin; đo đúng cần `nvidia-smi --query-compute-apps` theo PID (chưa làm). 12 worker đã báo cáo 02 gần cạn VRAM nên không thử lại.

## 3. Kết luận cho khối lượng (chưa có câu trả lời của công ty)

* Trên máy dev dùng chung, `src/ocr` đạt **khoảng 0,17–0,22 trang/giây ≈ 600–770 trang/giờ** (cả nạp mô hình), tức cỡ 15–19 nghìn trang/ngày nếu chạy liên tục 24 giờ và GPU không bị việc khác chiếm. Khi 6 worker chạy song song mỗi worker mất khoảng 25–30 giây cho một trang (250 giây × 6 worker / 53 trang).
* **Chưa đo được tốc độ trên máy sản xuất không bị chia sẻ**: con số tốt nhất đáng tin vẫn là tham chiếu 0,35 trang/giây của báo cáo 02 (2,5 phút/53 trang); lần đo này không tái hiện được số đó.
* Đủ hay không phụ thuộc vào câu hỏi 1 và 2 của README (trang/ngày, đỉnh, có GPU không); với vài trăm trang/ngày thì đủ rộng rãi; với hàng chục nghìn trang/ngày cần GPU riêng hoặc nhiều máy.
* Thiếu so với mục tiêu của T4 bước 5: chưa đo `--threads` khác 2 (cấu hình 3×4×16 bị bỏ), chưa đo CPU-only trong lần này, chưa đo lúc GPU rảnh hoàn toàn, chưa đo 1 tiến trình riêng.

## 4. Hạn chế

Mỗi cấu hình một lần chạy; GPU dùng chung (tải của người khác thay đổi giữa các lần); thời gian gồm nạp mô hình (6 worker nạp song song, vài chục giây trong 250 giây, nên trang/giây trạng thái ổn định cao hơn một chút); 24 tài liệu là mẫu rải đều nhưng 53 trang ngắn (trung bình 2,2 trang/tài liệu) nên tải worker không cân; tài liệu dài (sổ PCCC 30 trang) có thể làm số khác. Không có đo trên máy khác.
