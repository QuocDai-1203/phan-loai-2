# Hướng dẫn cho người chú thích silver (đọc ảnh trang, điền trường)

Bạn là người chú thích dữ liệu. Nhiệm vụ: với mỗi **đơn vị** (unit) trong lô được giao, đọc các ảnh trang của đơn vị đó và điền
các trường theo schema của loại tài liệu. Kết quả là **đáp án tham chiếu** để đo phần mềm trích xuất; một giá trị bịa ra nhưng
nghe hợp lý là kết quả **tệ nhất có thể** (nó làm phần mềm sai được chấm là đúng, hoặc ngược lại). Thà ghi `illegible` còn hơn đoán.

## 1. Bạn nhận được gì

Một tệp lô `gold/batches/batch_NN.json` (hoặc `gold/batches_second_annotator.json`, mỗi phần tử `batches[]` là một lô). Mỗi đơn vị có:
`unit_id`, `doc_type`, `schema_path` (đường dẫn tuyệt đối tới schema), `shown_pages` (các trang PDF được cho xem), `n_pages`
(tổng số trang của đơn vị) và `images[]` (đường dẫn tuyệt đối từng ảnh).

Tên ảnh: `pNN.png` là trang NN của PDF gốc. Trang dọc được cắt đôi: `pNN_a.png` là nửa TRÊN, `pNN_b.png` là nửa DƯỚI của trang NN
(dòng chữ không bị cắt ngang). Ghép hai nửa trong đầu thành một trang. `page` bạn ghi luôn là **NN** (số trang PDF gốc).

## 2. Quy tắc cứng

1. Chỉ dùng công cụ **Read** để mở **đúng các ảnh được liệt kê** trong lô. Không đọc tệp nào khác ngoài tệp lô, schema của đơn vị
   và chính tệp này. Không tìm kiếm, không liệt kê thư mục, không mở PDF, không mở `ocr_*.jsonl`, `units.csv`, `labels_*.csv`,
   `manifest.csv`, **không nhìn tên tệp PDF**. Không dùng tên tệp, tên thư mục hay bất kỳ nguồn nào ngoài ảnh để suy ra giá trị.
2. **QUY TẮC DỪNG.** Nếu BẤT KỲ ảnh nào của đơn vị **không mở được** (Read báo lỗi) hoặc là ảnh **có nội dung nhưng không đọc nổi**
   (mờ hoàn toàn, cắt mất nội dung), KHÔNG điền gì cho đơn vị đó. Ghi đúng một tệp
   `{"unit_id": "<unit_id>", "error": "<mô tả ngắn: ảnh nào, lỗi gì>"}` rồi sang đơn vị kế tiếp. **Không bao giờ đoán.**
   Một giá trị bịa nhưng nghe hợp lý là kết quả tệ nhất.
   **Ảnh trắng KHÔNG phải lỗi.** Thẻ nhỏ chỉ chiếm nửa trên của tờ giấy nên nửa dưới (`pNN_b.png`), hoặc một mặt sau của tờ, có thể là giấy
   trắng hoàn toàn: đó là bình thường. Cứ bỏ qua ảnh trắng, đọc các ảnh còn lại và điền như thường lệ (đừng ghi `error`, đừng nhắc "ảnh trắng" như một vấn đề;
   có thể ghi `unit_note` = `nua_duoi_trang`). Chỉ ghi `error` khi Read thất bại hoặc khi một ảnh CÓ NỘI DUNG không đọc được. Trước khi kết luận
   "ảnh trắng", nhìn kỹ cả mép và góc ảnh: nếu có chữ, dấu hay đường kẻ thì đó là ảnh có nội dung.
3. Không bao giờ suy ngày từ tên tệp. Không tự tính ngày hết hạn (ví dụ cộng 2 năm vào ngày cấp) trừ khi trang ghi rõ ngày đó.
4. Chỉ ghi những gì **nhìn thấy trên ảnh**. Trường không thấy trên các trang được cho xem: `status = "not_present"`
   (nghĩa là "không có trên các trang đã cho xem", không phải "chắc chắn không tồn tại trong cả tài liệu").
5. Nhìn thấy nhưng không đọc chắc được (mờ, bị con dấu đè, chữ viết tay khó): `status = "illegible"`, `value = null`.
   Chỉ đọc được một phần: ghi phần chắc chắn, thay phần không chắc bằng `[?]`, và `status = "ok"` kèm `note`.
6. Mỗi ngày/số/mã phải chép **đúng từng ký tự như in** vào `value` (kể cả dấu chấm, gạch, khoảng trắng lạ). Đừng sửa lỗi chính tả của giấy.
7. **Dữ liệu cá nhân.** Với trường có `silver_policy = "withhold_value"` trong schema (số căn cước/giấy phép lái xe, ngày/năm sinh):
   **không chép giá trị**. Đặt `value = null`, `normalized = null`, `evidence = null`; chỉ ghi `status` (`ok` nếu trường CÓ trên trang,
   `not_present` nếu không có, `illegible`), `page` và `ink`. Trường `silver_policy = "skip"` (trường dẫn xuất): ghi
   `status = "not_present"`, các khóa còn lại `null`.
   Họ tên (`personal_name`) vẫn chép bình thường. Đừng đưa bất kỳ giá trị cá nhân nào vào lời nhắn, `note` hay tóm tắt cuối.
8. Chỉ ghi các tệp kết quả ở mục 4. **Không ghi gì khác** (không báo cáo, không tệp tạm, không sửa schema hay tệp lô).

## 3. Cách điền từng trường

Với **mọi** trường trong `x-fields` của schema (đủ từng trường, đúng tên khóa) trả:

| khóa | ý nghĩa |
|---|---|
| `value` | giá trị **nguyên văn như in** trên giấy (chuỗi), hoặc `null` khi `not_present`/`illegible`/withheld |
| `normalized` | dạng chuẩn: ngày `YYYY-MM-DD` (chỉ có tháng/năm: `YYYY-MM`; chỉ có năm: `YYYY`); số thập phân dùng dấu `.` không ngăn nghìn (`10.000,5` -> `10000.5`); mã số thuế/biển số/số phiếu giữ ký tự như in (viết hoa, bỏ khoảng trắng thừa); văn bản giữ nguyên. `null` nếu `value` là `null` hoặc không chuẩn hóa được |
| `page` | số trang PDF gốc (số nguyên) nơi bạn thấy giá trị; `null` nếu `not_present` |
| `evidence` | trích **tối đa 12 từ** quanh giá trị, đúng như in (để người kiểm tìm lại); `null` nếu không có |
| `ink` | `printed` (chữ in/đánh máy) · `handwritten` (viết tay) · `under_stamp` (chữ hoặc số bị/nằm dưới con dấu); `null` nếu không có giá trị |
| `status` | `ok` · `not_present` · `illegible` |
| `note` | (tùy chọn) tối đa 15 từ, vd. `chi_ghi_thoi_han`, `mot_phan_bi_che`. Không chứa dữ liệu cá nhân. Không có thì `null` |

Gợi ý theo trường (xem `annotator_hint` trong schema). Hai điểm hay sai nhất:
* **Ngày hết hạn** (`is_expiry = true`): chép ngày in sau "có giá trị đến …"/"hiệu lực đến …". Nếu giấy chỉ ghi khoảng thời gian
  (vd. "thời hạn 05 năm") không kèm ngày cụ thể: `value` = cụm như in, `normalized = null`, `status = "ok"`, `note = "chi_ghi_thoi_han"`.
* Trường gộp tên + mã số thuế (`ben_ban`, `ben_mua`, `thuong_nhan_chu_so_huu`): chép cả cụm như in trong một chuỗi.

## 4. Ghi kết quả

Với mỗi đơn vị, ghi **một tệp** `gold/silver_raw/<annotator>/<unit_id>.json`, trong đó `<annotator>` là tên được giao (vd. `haiku`, `sonnet`),
đường dẫn tuyệt đối là thư mục `silver_raw` cạnh tệp này; tạo thư mục nếu chưa có. UTF-8, JSON hợp lệ, không chú thích:

```json
{
  "unit_id": "<unit_id>",
  "annotator": "<annotator>",
  "doc_type": "<doc_type của đơn vị>",
  "pages_seen": [1, 2],
  "fields": {
    "<tên_trường_1>": {"value": "...", "normalized": "...", "page": 2, "evidence": "có giá trị đến hết ngày 12 tháng 01 năm 2028",
                       "ink": "printed", "status": "ok", "note": null},
    "<tên_trường_2>": {"value": null, "normalized": null, "page": null, "evidence": null, "ink": null,
                       "status": "not_present", "note": null}
  },
  "unit_note": null
}
```

* `pages_seen`: các số trang bạn thực sự đã mở.
* `unit_note`: tối đa 20 từ về chất lượng chung (vd. `scan_mo`, `trang_xoay`), hoặc `null`. Không dữ liệu cá nhân.
* Với đơn vị lỗi (quy tắc dừng): chỉ `{"unit_id": "...", "error": "..."}`.
* Tên tệp = `unit_id` đúng từng ký tự. Mỗi đơn vị một tệp, không gộp.

## 5. Dòng cuối

Sau khi xong cả lô, in **một dòng duy nhất** (không thêm gì khác) dạng:

`DONE units=<tổng đơn vị trong lô> ok=<số đơn vị đã ghi đáp án> errored=<số đơn vị ghi error>`
