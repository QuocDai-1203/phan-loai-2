# Hướng dẫn cho người phân xử (người đọc thứ ba)

Hai người chú thích đã đọc cùng các giấy tờ và có chỗ **khác nhau**, hoặc chỗ **rủi ro** (chữ viết tay, chữ dưới con dấu), hoặc ngày hết hạn lệch với một nguồn kiểm chéo.
Bạn mở ảnh, **tự tìm trường trên ảnh, tự đọc**, rồi phán quyết. Kết quả của bạn dùng làm đáp án tham chiếu để đo phần mềm trích xuất và đo độ sai của hai người
chú thích: **một giá trị bịa nhưng nghe hợp lý là kết quả tệ nhất.** `illegible` (không đọc chắc được) là một câu trả lời hoàn toàn chấp nhận được.

## 1. Bạn nhận được gì

Một tệp lô `gold/adjudication/queue_batch_NN.json`. Mỗi đơn vị (`units[]`) có `unit_id`, `doc_type`, `schema_path`, `images[]` (đường dẫn tuyệt đối) và `items[]`.
Mỗi mục có: `item_id`, `field` (tên trường), `field_desc` + `field_hint` (cách hiểu trường, lấy từ schema), `field_type`, `silver_policy`, `shown_pages`,
`candidate_x`, `candidate_y` (hai cách đọc của hai người chú thích, **đã xáo thứ tự ngẫu nhiên**, không biết ai là ai) và `single_candidate`.

Mỗi cách đọc gồm `status` (`ok`/`not_present`/`illegible`), `value` (nguyên văn), `page`, `ink`, `evidence` (trích dẫn ngắn), `note`.
Nếu `single_candidate` là `true`: chỉ có `candidate_x` (`candidate_y` là `null`). Hãy đọc độc lập; bạn không được biết lý do mục này vào hàng đợi.

Tên ảnh: `pNN.png` là trang NN của PDF gốc; `pNN_a.png` / `pNN_b.png` là nửa TRÊN / nửa DƯỚI của trang NN (ghép lại trong đầu). `page` bạn ghi luôn là **NN**.

## 2. Quy tắc cứng

1. Chỉ dùng công cụ **Read**, chỉ mở: tệp lô được giao, tệp schema của đơn vị, tệp này, và **các ảnh được liệt kê** của đơn vị. Không mở `key.json`, `queue.json`,
   `gold/silver_raw/**`, `units.csv`, `labels_*.csv`, `manifest.csv`, `ocr_*.jsonl`, PDF, tên tệp PDF; không tìm kiếm hay liệt kê thư mục. Không dùng nguồn nào ngoài ảnh
   để suy ra giá trị (đặc biệt: không suy ngày hết hạn từ tên tệp, không tự cộng ngày; bạn không có tên tệp và không được đi tìm).
2. **QUY TẮC DỪNG.** Nếu một ảnh của đơn vị **không mở được** (Read báo lỗi) hoặc là ảnh **có nội dung nhưng không đọc nổi**, đừng phán quyết các mục của đơn vị đó:
   với mỗi mục ghi `{"item_id": "...", "error": "<mô tả ngắn: ảnh nào, lỗi gì>"}` rồi sang đơn vị khác. **Không bao giờ đoán.**
   **Ảnh trắng KHÔNG phải lỗi:** thẻ nhỏ chỉ chiếm nửa trên của tờ giấy nên `pNN_b.png` hoặc một mặt sau có thể là giấy trắng hoàn toàn — bình thường, cứ bỏ qua. Trước khi
   kết luận "trắng", nhìn kỹ cả mép và góc ảnh: có chữ, dấu hay đường kẻ thì là ảnh có nội dung.
3. **Đọc ảnh trước, rồi mới so với hai cách đọc.** Đừng chọn cách đọc nghe hợp lý hơn; hãy tìm trường trên ảnh và đọc từng ký tự. Nếu cả hai cách đọc đều không đúng với những gì ảnh cho thấy,
   phán quyết là `neither` và ghi cách đọc của chính bạn. Nếu ảnh không cho phép bạn đọc chắc (mờ, chữ viết tay khó, con dấu che), ghi `status = "illegible"`, `value = null`
   — đừng chọn x hay y chỉ để có đáp án (khi đó dùng `neither` nếu bạn chắc ít nhất một cách đọc sai, hoặc `both_equivalent` nếu bạn thấy hai cách đọc đều có thể đúng và như nhau).
4. **Dữ liệu cá nhân.** Mục có `silver_policy = "withhold_value"` (số căn cước/giấy phép lái xe, ngày/năm sinh): `candidate_*` chỉ có `status`/`page`/`ink`, không có giá trị.
   Bạn cũng **không chép giá trị**: `value = null`, `normalized = null`; chỉ phán quyết xem trường CÓ trên trang hay không (`status = ok` nếu có, `not_present` nếu không, `illegible`)
   và ghi `page`, `ink`. Với họ tên vẫn chép bình thường. Đừng đưa dữ liệu cá nhân vào `reason`.
5. Chỉ ghi các tệp kết quả ở mục 4. Không ghi gì khác (không báo cáo, không tệp tạm, không sửa lô/schema/queue/key).

## 3. Phán quyết (`verdict`)

| giá trị | khi nào |
|---|---|
| `x_correct` | cách đọc x đúng với ảnh, y sai |
| `y_correct` | cách đọc y đúng, x sai (không dùng khi `single_candidate = true`) |
| `both_equivalent` | x và y cùng đúng (chỉ khác cách viết: dấu, dấu câu, định dạng ngày, thêm/bớt mã số thuế...) — không dùng khi `single_candidate = true` |
| `neither` | cả hai (hoặc cách đọc duy nhất) đều sai với ảnh; hoặc trường không đọc chắc được và ít nhất một cách đọc chắc chắn sai |

"Đúng" nghĩa là đúng giá trị **trên ảnh** theo mô tả trường (`field_desc`, `field_hint`). Khác biệt chỉ ở dấu tiếng Việt, hoa/thường, dấu câu, cách viết ngày
(`12/05/2024` = `ngày 12 tháng 05 năm 2024`) là `both_equivalent`, không phải lỗi. Khác ở một chữ số, một chữ cái của mã/số/tên riêng là lỗi.

## 4. Ghi kết quả

Mỗi mục một tệp `gold/adjudication/out/<item_id>.json` (đường dẫn tuyệt đối: thư mục `out` trong `output_dir` của tệp lô; tạo thư mục nếu chưa có). UTF-8, JSON hợp lệ:

```json
{
  "item_id": "<item_id>",
  "verdict": "x_correct",
  "value": "nguyên văn bạn đọc được trên ảnh, hoặc null",
  "normalized": "dạng chuẩn: ngày YYYY-MM-DD (hoặc YYYY-MM, YYYY); số thập phân dùng dấu chấm; mã giữ ký tự như in, hoặc null",
  "page": 2,
  "ink": "printed",
  "status": "ok",
  "reason": "tối đa 15 từ"
}
```

* `value`: cách đọc CỦA BẠN, nguyên văn từng ký tự như in (kể cả khi bạn chọn x hoặc y). `null` khi `status` khác `ok` hoặc trường PII `withhold_value`.
* `ink`: `printed` · `handwritten` · `under_stamp`; `null` nếu không có giá trị. `page`: số trang PDF gốc, `null` nếu `not_present`.
* `status`: `ok` (bạn thấy và đọc chắc) · `not_present` (không có trên các trang được cho xem) · `illegible`.
* `reason`: tối đa 15 từ, không chứa dữ liệu cá nhân (vd. `x thieu so 0 cuoi`, `chu viet tay ro, y doc sai chu so`). Không có lý do thì `null`.
* Tên tệp = `item_id` đúng từng ký tự. Một mục một tệp.

## 5. Dòng cuối

Sau khi xong cả lô, in **một dòng duy nhất**: `DONE items=<tổng mục trong lô> judged=<số mục đã ghi phán quyết> errored=<số mục ghi error>`
