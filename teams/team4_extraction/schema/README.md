# Schema trích xuất theo loại tài liệu (T1) và chính sách dữ liệu cá nhân (T5)

Bốn loại đầu tiên: `GCN_DDK_BAN_LE_XD`, `CC_TAP_HUAN_VC_HNH`, `HD_MUA_BAN`, `PHIEU_XUAT_KHO`. **Trạng thái: bản nháp** — chờ nhóm 00 và một người
của công ty duyệt (câu 11, 13, 14 trong [README nhóm 4](../README.md) có thể đổi trường hoặc trường bắt buộc).

## Sinh lại

```powershell
# từ gốc repo
.venv\Scripts\python.exe -X utf8 teams\team4_extraction\schema\build_schema.py
.venv\Scripts\python.exe -X utf8 -m pytest teams\team4_extraction\tests\test_t4_schema.py -q
```

`build_schema.py` đọc `classes[].key_fields` của [`data/taxonomy_v2.json`](../../../data/taxonomy_v2.json) và ghi `<DOC_TYPE>.json` + `pii_fields.json` cạnh nó.
**Danh sách trường luôn lấy từ taxonomy.** Phần siêu dữ liệu nghiệp vụ (kiểu, bắt buộc, gợi ý) nằm trong bảng `M` ở đầu `build_schema.py`; nếu taxonomy
thêm/bớt trường mà bảng chưa cập nhật thì script dừng với thông báo rõ (không đoán kiểu), và test `test_committed_schema_is_up_to_date_with_the_builder` đỏ.

## Cấu trúc một tệp `<DOC_TYPE>.json`

Là JSON Schema (draft 2020-12) của **đầu ra phẳng** `{tên_trường: chuỗi | null}` (dùng được làm `format` ràng buộc của Ollama), cộng siêu dữ liệu từng trường
trong khóa `x-fields`:

| khóa | ý nghĩa |
|---|---|
| `type` | `date` (chuẩn hóa ISO 8601), `number` (định dạng Việt Nam `10.000,5`), `id` (mã định danh), `text` |
| `id_kind` | khi `type=id`: `tax_code` (chỉ chữ số), `plate` (biển số, bỏ dấu ngăn), `document_no` (số phiếu/giấy/hợp đồng), `generic` |
| `is_expiry` | trường hạn (lấy từ taxonomy). Mỗi loại có đúng: GCN `ngay_het_han`, CC `ngay_het_han`, HD `hieu_luc_den`; phiếu xuất kho không có |
| `required` | trường phải đúng thì tài liệu mới "đúng cấp tài liệu" (tạm thời; không bao giờ là số định danh/ngày sinh vì đầu ra mặc định bỏ chúng) |
| `is_pii`, `pii_category` | dữ liệu cá nhân: `personal_id` / `birth_date` / `personal_name` (T5 bên dưới) |
| `typical_ink` | `printed` / `handwritten` / `under_stamp` / `unknown`. **`unknown` trừ khi đã nhìn ảnh trang thật** (xem bên dưới) |
| `silver_policy` | `transcribe`, `withhold_value` (người chú thích chỉ ghi có/không, không chép giá trị), `skip` (trường dẫn xuất, không có trên trang) |
| `annotate` | `false` cho trường dẫn xuất (`vai_tro_cong_ty`: công ty chủ quản là bên bán hay mua — thuộc cấu hình/định tuyến, không đọc được từ trang); bộ chấm bỏ qua |
| `multi` | giá trị có thể gồm nhiều mục, ghi gộp cách nhau `; ` (biển số xe + rơ moóc) |
| `annotator_hint` | gợi ý ngắn cho người chú thích silver và cho prompt của LLM cục bộ |

### Quy ước giá trị vắng

Giá trị vắng luôn là `null` (không phải chuỗi rỗng, `N/A`, `0`), kèm lý do ở nơi cần ghi lý do:

| lý do | nghĩa | tính vào điểm |
|---|---|---|
| `not_present` | giấy **không ghi** trường này (đáp án đúng là null; ở silver nghĩa là "không có trên các trang đã cho xem") | dự đoán null là đúng; dự đoán có giá trị là FP ("thừa") |
| `not_found` | giấy có ghi nhưng **máy không tìm thấy** (lỗi của phương pháp) | FN ("bỏ trống") |
| `illegible` | có ghi nhưng không đọc được (mờ, dưới con dấu, chữ viết tay) | **loại khỏi điểm**, đếm riêng |

Đặc biệt quan trọng với trường hạn: hợp đồng không ghi hạn (`not_present`) khác hẳn máy bỏ sót (`not_found`) khác hẳn máy ra sai ngày.
Nếu giấy chỉ ghi thời hạn mà không có ngày cụ thể ("có giá trị 05 năm"): `value` = cụm như in, `normalized = null`, `note = chi_ghi_thoi_han`; **không tự cộng ngày**
(trong README nhóm 4, câu hỏi 11 về quy tắc ưu tiên chưa có trả lời).

### Mực viết (`typical_ink`): đã xác minh gì

Chỉ ghi khác `unknown` khi đã nhìn ảnh trang thật; hiện mới nhìn **một đơn vị DEV mỗi loại** (n = 1, quan sát sơ bộ, không phải thống kê):

* `GCN_DDK_BAN_LE_XD`: mọi trường nhìn thấy đều là chữ **in**. `ngay_het_han` ở mẫu đã xem là chữ in nhưng bị con dấu "chứng thực bản sao" đè một phần — OCR cục bộ đọc hỏng đúng chỗ này
  (mô hình thị giác cục bộ đọc được; xem báo cáo giai đoạn 1). Đây là lý do chọn `printed` mà vẫn cần cờ `under_stamp` ở mức từng giá trị khi chú thích.
* `CC_TAP_HUAN_VC_HNH`: chữ in; con dấu tròn đè lên dòng "Đơn vị công tác" ở mẫu đã xem.
* `PHIEU_XUAT_KHO`: bản số hóa, chữ in; con dấu đè phần tiêu đề, không đè các trường.
* `HD_MUA_BAN`: chưa kiểm chứng (nhiều biến thể, một số là bản quét có chữ ký/con dấu): toàn bộ `unknown`.

## T5 — dữ liệu cá nhân (`pii_fields.json`, `pii_policy.py`)

`pii_fields.json` liệt kê trường PII của **toàn taxonomy** (không chỉ 4 loại này): `personal_id` = `so_dinh_danh`, `so_gplx`; `birth_date` = `ngay_sinh`, `nam_sinh`;
`personal_name` = `ho_ten` và `nguoi_*` (người đại diện, người nhận, người ủy quyền...). Mặc định **tạm thời** (chờ câu hỏi 12):

| nơi | số định danh + ngày sinh | họ tên |
|---|---|---|
| đầu ra mặc định (`filter_output`, `src/extraction/field_result.py`) | **bỏ** (`store_personal_ids=false`) | giữ (`store_personal_names=true`, cần để gắn nhắc hạn với người) |
| log, báo cáo, bảng lỗi (`redact_for_log`, `safe_repr`, `RedactingFilter`, `safe_summary`) | không bao giờ có giá trị | không bao giờ có giá trị |
| đáp án silver | người chú thích **không chép** giá trị (`withhold_value`); file gộp không chứa giá trị PII nào | chép ở tệp thô của người chú thích (thư mục `gold/silver_raw/`, chỉ nội bộ) nhưng file gộp và báo cáo thì không |
| phương pháp trích xuất (`methods/`) | LLM cục bộ không được hỏi các trường này; `BaseMethod.extract` còn lọc thêm một lần | như trên |

Test chứng minh: `tests/test_t4_pii.py`, `tests/test_t4_silver_merge.py`, `tests/test_t4_methods.py`, và ở gốc repo `tests/test_extraction_field_result.py`.
