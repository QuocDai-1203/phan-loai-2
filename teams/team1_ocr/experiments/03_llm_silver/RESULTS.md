# T6 — Kiểm lô bản chép chữ của LLM (`validate_batch.py`)

> `labels_v2.csv` sha1[:10] = `eb3348713a` · ngày 2026-10-15 · nguồn: bản chép Haiku có sẵn (`data/ocr_llm_haiku/pages`, `gold/silver_llm/haiku`), OCR độc lập `data/ocr_v2.jsonl`, text layer của PDF; **không gọi LLM, không gửi ảnh đi đâu**.
> Tái lập một dòng: `.venv\Scripts\python.exe -X utf8 teams\team1_ocr\experiments\03_llm_silver\calibrate_validate_batch.py` (hiệu chuẩn), `…\demo_blank_trap.py` (đợt thử trang trắng), `.venv\Scripts\python.exe -X utf8 -m pytest -q tests\test_llm_batch_validation.py` (14 test).
> Các bản chép LLM và ngưỡng ở đây đều là "so với đáp án máy" (text layer là đáp án thật chỉ cho trang born-digital).

## 1. Vì sao cần

Từng có một đợt phải làm lại vì tác nhân chép chữ cho 12 trang mà ảnh nạp lỗi (theo ghi nhận khi thực hiện; không có log trong kho). LLM không báo "không thấy ảnh", nó bịa. Vì vậy mỗi lô phải **tự chứng minh** mô hình thật sự nhìn thấy ảnh.

## 2. Kiểm gì (`validate_batch.py`, ngưỡng ở lớp `Thresholds`)

| # | kiểm | điều kiện hợp lệ |
|---|---|---|
| 1 | **Trang đã biết** (`control_textlayer`, trang born-digital trộn vào lô; đáp án = text layer PyMuPDF sắp theo dòng) | mọi trang `bag_recall ≥ 0,90`; trung bình `bag_recall ≥ 0,95`; CER trung bình `≤ 0,25`; ít nhất 3 trang |
| 2 | **Trang trắng** (`control_blank`) | bản chép (bỏ chú thích `[…]`) có `≤ 4` ký tự chữ/số; trang trắng mà ra chữ → **lô không hợp lệ**; ít nhất 1 trang |
| 3 | **Số ảnh nạp được** (tác nhân ghi vào `_images_loaded.txt` hoặc `--images-loaded N`) | bằng đúng số mục của lô; không khai báo hoặc khác → không hợp lệ; thiếu bản chép hoặc có tệp thừa ngoài manifest → không hợp lệ |
| 4 | **Kiểm chéo** 4-gram ký tự đã bỏ dấu/khoảng trắng với OCR độc lập (`ocr_v2`, chỉ trang OCR thật, ≥ 44 ký tự chữ số) như `data/ocr_llm_haiku/_check_vs_baseline.py` | trung vị recall `≥ 0,75`; tỉ lệ trang nghi vấn (recall `< 0,30`) `≤ 0,10` |

Kết quả ghi `<lô>/_validation.json` (trạng thái, lý do, số đo từng trang, **sha1 nội dung** các tệp `.txt`), mã thoát 0/1. Lô > 60 mục chỉ bị **cảnh báo** (xem §4).
`scripts/assemble_llm_ocr.py` **từ chối** (mã thoát 2, không ghi gì) lô không có `_validation.json` trạng thái `valid` hoặc có hash nội dung không khớp (sửa tệp sau khi kiểm). Cờ `--skip-validation "lý do"` bỏ qua cổng, bắt buộc có lý do và được **ghi log** (`<pages-dir>/../_validation_skipped.log`: thời gian, hash, lý do, lý do bị từ chối).
**Hệ quả:** lô Haiku cũ (`data/ocr_llm_haiku/pages`, 541 mục) không có trang trắng, trang đã biết lẫn khai báo số ảnh, nên **không thể chứng minh hợp lệ**; chạy lại `assemble_llm_ocr.py` trên đó bây giờ cần `--skip-validation`. Tôi **chưa** chạy lại hay ghi đè `data/ocr_llm_haiku.jsonl`.
Định dạng manifest và cách dựng lô nằm ở docstring của `validate_batch.py`; `--pages-csv` đọc thẳng `pages.csv` hiện có.

## 3. Hiệu chuẩn ngưỡng trên số liệu có sẵn

**Trang đã biết** — chạy `validate_batch.py` trên `gold/silver_llm/haiku` với 39 trang born-digital (khớp số cũ): `bag_recall` trung bình **0,995**, thấp nhất **0,987**, CER trung bình **0,105**. Ngưỡng 0,90/0,95/0,25 nằm xa dưới số này một khoảng đủ để Haiku qua, đủ cao để loại bản chép không liên quan (đã thử trong test: văn bản lạc đề cho `bag_recall` < 0,5).

**Kiểm chéo 4-gram** — 477 trang thật của lô Haiku cũ có OCR độc lập (`calibrate_validate_batch.py`, seed 20261015):

| | phân vị 1% | 5% | 25% | 50% | 90% | 95% | 99% |
|---|---|---|---|---|---|---|---|
| recall khi bản chép **đúng trang** | 0,265 | 0,600 | 0,836 | **0,928** | | | |
| recall khi bản chép bị **gán nhầm** sang trang khác | | | | 0,190 | 0,458 | 0,571 | 0,902 |

Vì các trang cùng loại tài liệu (mẫu biểu lặp, hợp đồng cùng khuôn) chia sẻ nhiều 4-gram nên **một trang bịa riêng lẻ không bị bắt chắc chắn**: với nghi vấn `< 0,3`, trang đúng bị gán nhầm 7/477 = 1,5% (Wilson 0,7–3,0%) còn trang bịa bị bắt 357/477 = 74,8% (Wilson 70,8–78,5%). Ngưỡng cấp **lô** (trung vị + tỉ lệ nghi vấn) mạnh hơn nhiều:

| N trang / lô | f = 12 trang bịa | lô sạch bị báo sai | lô có 12 trang bịa bị bắt (chỉ kiểm chéo) | + xác suất ≥ 1 trong 10 trang kiểm rơi trúng nhóm bịa |
|---|---|---|---|---|
| 20 | | 0,2% | 100% | 100% |
| 50 | | 0% | 99,3% | 95% |
| 100 | | 0% | **46,4%** | 74% |
| 200 | | 0% | **0%** | 47% |
| 400 | | 0% | 0% | 27% |

(4000 lô mô phỏng mỗi dòng; mô phỏng lấy mẫu có hoàn lại từ 477 trang, các trang bịa mô phỏng bằng gán nhầm; xác suất "rơi trúng" giả định trang kiểm bị bịa cùng nhóm với các trang khác khi tác nhân hỏng toàn bộ một đoạn lô, tính theo hoán vị ngẫu nhiên, không phải thực nghiệm.) **Kết luận thực hành: chia lô ≤ 50–60 mục, mỗi lô có trang kiểm riêng (≥ 10% là trang trắng/đã biết trộn ngẫu nhiên)**; lô lớn hơn kiểm chéo không còn nhạy với một nhóm nhỏ trang hỏng, chỉ còn trang kiểm làm chỗ dựa.

## 4. Đợt thử trang trắng (`demo_blank_trap.py`, dữ liệu thật, không dựng ảnh)

Lô 53 mục: 39 trang born-digital + 12 trang scan có bản chép Haiku sẵn + 2 trang trắng (mục giả).

| lô | tình huống | kết quả | mã thoát |
|---|---|---|---|
| A | trang trắng được chép `[trang trắng]`, khai báo 53/53 ảnh | **HỢP LỆ** (known 0,995 / 0,987 / CER 0,105; kiểm chéo 10 trang, trung vị 0,78) | 0 |
| B | một trang trắng bị "chép" ra 3 dòng chữ (mô phỏng bịa khi ảnh không nạp được) | **KHÔNG HỢP LỆ**: "1/2 trang TRẮNG mà ra chữ" | 1 |
| C | như A nhưng khai báo nạp 51/53 ảnh | **KHÔNG HỢP LỆ**: "số ảnh nạp được 51 != 53" | 1 |

Cả ba đúng kỳ vọng. Trên lô Haiku cũ chạy thử (541 mục, ghi ra thư mục tạm, không đụng `data/`): kiểm chéo cho trung vị 0,928 và 7 trang nghi vấn / 477 (1,5%); lô bị loại vì thiếu trang kiểm và số ảnh (đúng như thiết kế). Trong 7 trang nghi vấn có `7ee3bbfe72eb` p15, chính là trang `ocr_v2` xoay nhầm hướng (xem `05_rotation/RESULTS.md`), và `cb8636a17725` p1 là bản vẽ kỹ thuật (chữ nhiều hướng): kiểm chéo cũng bắt lỗi của OCR chứ không chỉ lỗi của LLM, vì vậy "nghi vấn" là tín hiệu cần xem, không phải kết luận.

## 5. Test (`tests/test_llm_batch_validation.py`, 14 test, xanh)

Lô giả có trang trắng ra chữ → "không hợp lệ" (`test_blank_page_that_comes_back_with_text_makes_the_batch_invalid`); ký tự chú thích không tính là chữ, ngưỡng 4/5 ký tự; thiếu/sai số ảnh; trang đã biết sai nội dung; bản chép không khớp OCR; thiếu bản chép / tệp thừa; lô không có trang kiểm; lô lớn chỉ cảnh báo; hash `content_hash` của validator và assembler trùng và bỏ qua tệp `_*`; cổng của `assemble_llm_ocr.py` từ chối lô chưa kiểm / không hợp lệ / sửa sau khi kiểm và nhận lô hợp lệ; `--skip-validation` cần lý do không rỗng và được ghi log.

## 6. Hạn chế

* Ngưỡng đặt trên 39 trang đã biết và 477 trang thật của **một** mô hình (Haiku) và **một** OCR (`ocr_v2`); mô hình khác có thể cần ngưỡng khác. Chữ viết tay và con dấu (nơi LLM kém tin cậy nhất, quy tắc 4 của T6) không được kiểm bởi lô nào ở đây: kiểm chéo với OCR vô nghĩa trên chữ viết tay vì OCR đọc sai gần hết.
* Trang đã biết là born-digital (chữ in sạch) nên không đại diện cho scan; trang trắng chỉ chứng minh mô hình không bịa khi ảnh **trắng**, không chứng minh nó thấy ảnh khác. Hai thứ kết hợp (số ảnh khai báo do chính tác nhân ghi, tác nhân có thể khai sai) vẫn không thay được kiểm soát của con người: `_images_loaded.txt` là lời khai.
* Kiểm chéo mạnh với lô ≤ 50 mục, yếu với lô ≥ 100 (bảng §3); mô phỏng dùng trang gán nhầm làm "trang bịa", bản chép bịa thật có thể giống OCR hơn (chép từ tên tệp, tiêu đề) hoặc kém hơn.
* Chưa kiểm trên một lô thật vừa chạy xong (không có lô mới trong phạm vi này).
