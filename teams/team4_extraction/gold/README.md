# gold/ — đáp án trường (silver) cho nhóm 4

Đây là **silver**, không phải vàng: do mô hình đọc ảnh trang, chưa người nào của công ty kiểm. `agreed_unverified` (hai mô hình giống nhau) và `model_adjudicated`
(người đọc thứ ba là mô hình mạnh hơn) **không phải sự thật**; chỉ `human_verified` mới là đáp án cuối, và trạng thái đó chưa có ở đâu.

## Tệp và quy trình

| bước | script / tệp | sinh ra |
|---|---|---|
| 1 | `build_units.py` | `units.csv`, `pages/<unit_id>/pNN*.png`, `batches/batch_NN.json`, `batches_second_annotator.json` |
| 2 | người chú thích đọc ảnh theo `SILVER_PROMPT.md` | `silver_raw/<annotator>/<unit_id>.json` |
| 3 | `merge_silver.py` | `fields_silver_v1.jsonl`, `silver_report.md` |
| 4 | `build_adjudication.py` | `adjudication/queue.json`, `key.json`, `queue_batch_NN.json` |
| 5 | người phân xử theo `adjudication/ADJUDICATION_PROMPT.md` | `adjudication/out/<item_id>.json` |
| 6 | `merge_silver.py` (chạy lại) | trường đã phân xử có `review_status = model_adjudicated`; báo cáo có mục 6 |

Đơn vị = `(doc_id, segment_idx)`; `units.csv` ghi **các trang được cho xem** (`shown_pages`), nên `not_present` nghĩa là "không có trên các trang đã cho xem".
`pages/`, `silver_raw/`, `units.csv` (có tên tệp) và `adjudication/` (có bản đọc nguyên văn) chứa dữ liệu thật: **không commit**.

## Ghi chép sự cố: ảnh trắng bị coi là lỗi (vòng 1, Haiku)

Ở vòng 1, **8 đơn vị Haiku** trả bản ghi lỗi theo QUY TẮC DỪNG vì nửa dưới trang (`pNN_b.png`) hoặc một mặt sau là **giấy trắng**: thẻ nhỏ chỉ chiếm nửa trên tờ giấy.
Hai trường hợp đã được kiểm bằng mắt: ảnh thật sự là giấy trắng; một thông báo lỗi còn gọi nhầm một nửa trang **có nội dung** là "trắng". Sonnet không gặp vấn đề này.
Xử lý:
* 8 tệp lỗi chuyển sang `silver_raw_errors_round1/haiku/` (giữ để truy vết, `merge_silver.py` không đọc thư mục này).
* Chạy lại 8 đơn vị với một câu làm rõ ("ảnh trắng là bình thường, không phải lỗi; chỉ ghi lỗi khi Read thất bại hoặc ảnh CÓ NỘI DUNG không đọc được"):
  `batches/retry_haiku_01.json`, `batches/retry_haiku_02.json`. Kết quả: 104/104 đơn vị Haiku hợp lệ, 0 bản ghi lỗi.
* Câu làm rõ đã được đưa vào `SILVER_PROMPT.md` (quy tắc 2) và `ADJUDICATION_PROMPT.md` để dùng về sau.
* **Tùy chọn cho lần render sau** (chưa render lại): `python gold/build_units.py --drop-blank` bỏ nửa trang trắng (tỉ lệ điểm ảnh có mực < 0,05%) khi nửa kia có mực.
  Trang trắng hoàn toàn vẫn giữ một ảnh để `shown_pages` khớp số ảnh. Vòng 1 và hàng đợi phân xử dùng ảnh đã render KHÔNG bỏ nửa trắng, nên ảnh trắng vẫn xuất hiện
  và prompt phân xử có dặn.

## Quy tắc kiểm hợp lệ của `merge_silver.py` (đã nới sau vòng 1)

Chỉ những lỗi làm giá trị **không đáng tin** mới loại dữ liệu, và loại ở **mức trường** khi được:

| mức | lỗi | hệ quả |
|---|---|---|
| cả đơn vị | JSON hỏng, `unit_id`/`doc_type` sai, thiếu `fields`, bản ghi `error` | đơn vị bị bỏ khỏi người đó |
| một trường | thiếu trường, `status` lạ, `page` không thuộc các trang được xem, `page` không phải số nguyên, ghi giá trị PII (`withhold_value`), `ok` mà không có giá trị, có giá trị mà status khác `ok` | trường đó bị bỏ khỏi người đó; các trường khác của đơn vị giữ nguyên |
| chỉ cảnh báo (đếm) | `evidence` quá 12 từ (cắt còn 12 từ, đơn vị vẫn giữ), `ink` lạ (bỏ `ink`), `ok` không có `page` | không mất dữ liệu |

(Trước đó `evidence` quá dài làm mất cả đơn vị: 3 đơn vị Haiku + 16 đơn vị Sonnet.)

## So sánh chặt và mềm

* **Chặt** (định nghĩa không đổi): bằng nhau sau chuẩn hóa ngày/số/mã/văn bản (NFC, chữ hoa/thường, khoảng trắng).
* **Mềm** (chỉ cho kiểu `text`, `eval/normalize.py::lenient_text_equal`): thêm bỏ dấu tiếng Việt, bỏ dấu câu, chuỗi ngắn nằm **trọn từ** trong chuỗi dài, và với trường
  "tên + mã số thuế" khớp theo tên (nếu cả hai có mã số thuế mà khác hẳn nhau thì KHÔNG khớp).
Trường đồng thuận mềm cũng được đặt `agreed_unverified` (với `agreement = lenient`); báo cáo in hai cột cạnh nhau.

## Phân xử bởi người đọc thứ ba

Hàng đợi gồm mọi trường (trong tập đơn vị có hai người chú thích) còn `needs_human` sau so sánh mềm, mọi trường có `ink_risk`, và mọi trường hạn mà ngày silver lệch ngày trong
tên tệp. Thứ tự hai bản đọc `candidate_x`/`candidate_y` được xáo ngẫu nhiên (hạt giống cố định); ai là x/y nằm ở `adjudication/key.json` mà người phân xử được dặn không mở.
Mục "lệch tên tệp" chỉ có một bản đọc và không có thông tin tên tệp. Người phân xử không bao giờ tạo ra `human_verified`.
Ước lượng độ sai của từng người chú thích (báo cáo mục 6) là tỉ lệ **có điều kiện** trên các mục đã vào hàng đợi, kèm một cận dưới trên toàn bộ bản đọc; hai mô hình cùng họ vẫn có thể
cùng sai ở các trường đồng thuận không bị phân xử.
