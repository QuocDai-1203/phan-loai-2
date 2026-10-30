# Hướng dẫn cho người chú thích silver v2 (giai đoạn 3: 17 loại còn lại có trường hạn)

> Giống hệt `SILVER_PROMPT.md` (v1) về quy tắc cứng; khác ở đường dẫn (thư mục `gold/v2/`), danh sách loại và mục 6 (lưu ý theo loại). Đọc kỹ cả mục 6.

Bạn là người chú thích dữ liệu. Nhiệm vụ: với mỗi **đơn vị** (unit) trong lô được giao, đọc các ảnh trang của đơn vị đó và điền
các trường theo schema của loại tài liệu. Kết quả là **đáp án tham chiếu** để đo phần mềm trích xuất; một giá trị bịa ra nhưng
nghe hợp lý là kết quả **tệ nhất có thể** (nó làm phần mềm sai được chấm là đúng, hoặc ngược lại). Thà ghi `illegible` còn hơn đoán.

## 1. Bạn nhận được gì

Một tệp lô `gold/v2/batches_v2/batch_NN.json` (hoặc `gold/v2/batches_v2_second.json`, mỗi phần tử `batches[]` là một lô). Mỗi đơn vị có:
`unit_id`, `doc_type`, `schema_path` (đường dẫn tuyệt đối tới schema), `shown_pages` (các trang PDF được cho xem), `n_pages`
(tổng số trang của đơn vị) và `images[]` (đường dẫn tuyệt đối từng ảnh).

Tên ảnh: `pNN.png` là trang NN của PDF gốc. Trang dọc được cắt đôi: `pNN_a.png` là nửa TRÊN, `pNN_b.png` là nửa DƯỚI của trang NN
(dòng chữ không bị cắt ngang). Ghép hai nửa trong đầu thành một trang. `page` bạn ghi luôn là **NN** (số trang PDF gốc).

## 2. Quy tắc cứng

1. Chỉ dùng công cụ **Read** để mở **đúng các ảnh được liệt kê** trong lô. Không đọc tệp nào khác ngoài tệp lô, schema của đơn vị
   và chính tệp này. Không tìm kiếm, không liệt kê thư mục, không mở PDF, không mở `ocr_*.jsonl`, `units.csv`, `units_v2.csv`, `labels_*.csv`,
   `manifest.csv`, **không nhìn tên tệp PDF**. Không dùng tên tệp, tên thư mục hay bất kỳ nguồn nào ngoài ảnh để suy ra giá trị.
2. **QUY TẮC DỪNG.** Nếu BẤT KỲ ảnh nào của đơn vị **không mở được** (Read báo lỗi) hoặc là ảnh **có nội dung nhưng không đọc nổi**
   (mờ hoàn toàn, cắt mất nội dung), KHÔNG điền gì cho đơn vị đó. Ghi đúng một tệp
   `{"unit_id": "<unit_id>", "error": "<mô tả ngắn: ảnh nào, lỗi gì>"}` rồi sang đơn vị kế tiếp. **Không bao giờ đoán.**
   Một giá trị bịa nhưng nghe hợp lý là kết quả tệ nhất.
   **Ảnh trắng KHÔNG phải lỗi.** Thẻ nhỏ chỉ chiếm nửa trên của tờ giấy nên nửa dưới (`pNN_b.png`), hoặc một mặt sau của tờ, có thể là giấy
   trắng hoàn toàn: đó là bình thường. Cứ bỏ qua ảnh trắng, đọc các ảnh còn lại và điền như thường lệ (đừng ghi `error`, đừng nhắc "ảnh trắng" như một vấn đề;
   có thể ghi `unit_note` = `nua_duoi_trang`). Chỉ ghi `error` khi Read thất bại hoặc khi một ảnh CÓ NỘI DUNG không đọc được. Trước khi kết luận
   "ảnh trắng", nhìn kỹ cả mép và góc ảnh: nếu có chữ, dấu hay đường kẻ thì đó là ảnh có nội dung.
   **Bổ sung (sau đợt 1 của v2): ảnh quét MỜ hoặc chỉ có bóng chữ in xuyên từ mặt sau KHÔNG phải lỗi dừng.** Chỉ ghi `error` khi Read
   thất bại (ảnh không nạp được). Nếu ảnh nạp được nhưng một phần hay cả ảnh mờ/không đọc nổi: vẫn điền đơn vị từ các ảnh đọc được; trường nào
   có thể nằm ở phần mờ mà không thấy rõ thì ghi `status = "illegible"` (nếu thấy có chữ ở vị trí trường nhưng không đọc chắc) hoặc `not_present`
   (nếu không thấy trường); ghi `unit_note` = `anh_mo: pNN_x,...` liệt kê các ảnh mờ. Quy tắc "không bao giờ đoán" vẫn giữ nguyên.
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

Với mỗi đơn vị, ghi **một tệp** `gold/v2/silver_raw/<annotator>/<unit_id>.json`, trong đó `<annotator>` là tên được giao (vd. `haiku`, `sonnet`),
đường dẫn tuyệt đối là thư mục `silver_raw` cạnh tệp này (`gold/v2/silver_raw`); tạo thư mục nếu chưa có. UTF-8, JSON hợp lệ, không chú thích:

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

## 6. Lưu ý riêng cho giai đoạn 3

* **Trường hạn** là trường có `is_expiry = true` (cũng được liệt kê trong khóa `x-expiry_fields` của schema): đọc thật kỹ, chép đúng ngày in.
  Tên trường có thể là `ngay_het_han`, `hieu_luc_den` hoặc `thoi_han_thue_den`. Ngày kèm giờ (giấy bảo hiểm: "từ 08h00 ngày … đến 08h00 ngày …"):
  chỉ chép phần ngày vào `value` như in (có thể kèm giờ trong `evidence`).
* Giấy "Không thời hạn"/"Vô thời hạn" (GPLX, CCCD): `value` = cụm như in, `normalized = null`, `status = "ok"`, `note = "khong_thoi_han"`.
  Hợp đồng chỉ nêu khoảng thời gian: `note = "chi_ghi_thoi_han"` (như mục 3). Hợp đồng không nêu hạn: `not_present`.
* **PII**: `so_gplx`, `so_dinh_danh`, `ngay_sinh`, `nam_sinh` có `silver_policy = "withhold_value"` (xem mục 2.7). `ho_ten`, `nguoi_*` vẫn chép.
  GPLX và CCCD là thẻ nhỏ: ảnh trắng nửa dưới hoặc mặt sau là bình thường.
* Trường có `multi = true` (biển số): nhiều giá trị cách nhau `"; "` trong một chuỗi. Trường `silver_policy = "skip"` (vd. `vai_tro_cong_ty`,
  `loai_thuong_nhan`, `loai_bao_hiem`): ghi `status = "not_present"`, các khóa còn lại `null`.
* Hợp đồng nhiều trang: chỉ có những trang trong `shown_pages`; điều khoản hiệu lực thường nằm ở trang cuối hoặc trang gần cuối. Trường không thấy trên các trang
  được cho xem thì `not_present`. Tệp ghép: bạn chỉ thấy các trang của đơn vị, đừng suy diễn về trang khác.
* Vẫn không đoán, không dùng tên tệp, evidence <= 12 từ, in dòng `DONE units=...` khi xong.

---

## Ghi chú cho lượt silver SAU (cập nhật 2026-10-16, theo quyết định của công ty)

> **Không áp dụng ngược** cho silver v2 hiện có: phần bên trên là bản đã dùng để tạo `fields_silver_v2.jsonl` và được giữ nguyên. Ghi chú này chỉ dành cho lượt chú thích tiếp theo.

Prompt hiện hành đã đúng hướng ở một điểm quan trọng: nó cấm dùng tên tệp để suy giá trị (mục 1 và 3, và dòng cuối), nên **silver v2 không lấy ngày hết hạn từ tên tệp**. Quyết định của công ty ngày 2026-10-16 (nguyên ý chủ dự án, nói tắt: *"ngày trong tệp phải cụ thể là ngày gì thì mới là ngày hết hạn"*; diễn giải này là của nhóm, cần xác nhận lại nếu khác) cho các điều chỉnh sau ở lượt sau:

1. Trường `is_expiry` chỉ điền khi **tài liệu ghi rõ đó là ngày hết hạn/hiệu lực đến**. Ngày ký, ngày cấp, ngày lập, ngày in ở chỗ khác không tự thành hạn. Giấy không có hạn: `status = "not_present"` (đây là kết quả hợp lệ, không phải lỗi).
2. "Có hiệu lực kể từ ngày ký" không kèm ngày kết thúc → `not_present`. Chỉ ghi khoảng thời gian ("thời hạn 05 năm") → giữ quy ước `chi_ghi_thoi_han` hiện có (`normalized = null`), không cộng ngày.
3. **Phân xử (Opus/người):** không dùng ngày trong tên tệp để chọn giữa hai giá trị bất đồng và không ưu tiên các trường lệch tên tệp trong hàng phân xử (báo cáo 04, T6 ghi hàng phân xử hiện nghiêng nhẹ về quy tắc dùng tên tệp). Nếu cần, dùng tên tệp chỉ như cờ cảnh báo để người xem lại, không như bằng chứng.
4. Được phép dùng LLM bên ngoài (đám mây) để tạo đáp án trên tài liệu mẫu. Sản xuất vẫn on-premise; tài liệu mới không đi qua đám mây.
