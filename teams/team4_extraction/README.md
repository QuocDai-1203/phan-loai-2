# Nhóm 4 — Trích xuất trường dữ liệu

## Mục tiêu (doanh nghiệp nhận được gì)

Từ mỗi tài liệu đã được tách và nhận loại, lấy ra **các trường có cấu trúc** đưa vào ERP và hệ thống nhắc hạn. Giá trị lớn nhất, đã có trong báo cáo thiết kế: **ngày hết hạn** — 21 loại tài liệu có một trường hạn (giấy chứng nhận đủ điều kiện bán lẻ, thẻ tập huấn vận chuyển hàng nguy hiểm, hợp đồng, bảo hiểm, đăng kiểm, giấy phép lái xe…) và công ty cần được nhắc trước khi hết hạn. Sau đó là các trường kế toán của chứng từ giao nhận (số phiếu, biển số xe, số lượng, hợp đồng căn cứ). Đầu vào: `DocumentSlice` + `ClassificationResult`; đầu ra: `ExtractionResult` (xem [`teams/README.md`](../README.md)).

## Hiện trạng

### Mã có sẵn

- `src/extraction/barb_extractor.py`: bọc mô hình GLiNER `belumind/barb-1-ie-vi`. Nạp lười lần dùng đầu (đã kiểm ở giai đoạn 1: mô hình có sẵn trong cache Hugging Face, nạp trên CPU ~40 s, dự đoán đúng "ngày/tổ chức/mã số thuế" trên câu mẫu). Dùng 10 nhãn cố định (`tổ chức, người, chức vụ, địa điểm, ngày, mã số thuế, số tài khoản, xăng dầu, số lượng, tiền tệ`), ngưỡng 0,4, và **chỉ đọc 4000 ký tự đầu** của lát cắt. Kết quả là `entity_dict = {nhãn: [văn bản…]}`; không gán thực thể vào trường nghiệp vụ nào, `tables` luôn rỗng. Lỗi nạp mô hình hay dự đoán trả `status="error"` kèm lý do; không có văn bản trả `status="skipped"`. Có test ở `tests/test_extractor.py` (dùng mô hình giả).
- `src/extraction/barb_labels.py`: chặn nhãn bị mất dấu tiếng Việt (nhãn không dấu như `to_chuc` làm GLiNER lệch; mã ghi mất ~35 điểm F1 — con số kế thừa từ dự án gốc, **chưa kiểm lại ở đây**).

### Đã có sẵn để bắt đầu

- **Danh sách trường theo loại**: `classes[].key_fields` trong [`data/taxonomy_v2.json`](../../data/taxonomy_v2.json) — mỗi trường có `name` (ASCII), mô tả và cờ `is_expiry`. Ví dụ `PHIEU_XUAT_KHO` có 14 trường (`so_phieu, ky_hieu, ngay_xuat, ben_giao, ben_nhan, hop_dong_can_cu, lenh_xuat_hang, bon_xuat, bien_so_phuong_tien, mat_hang, so_luong_m3_15c, so_luong_tan, so_luong_m3_thuc_te, so_chung_thu_chat_luong`); `GCN_DDK_BAN_LE_XD` có 9 trường kết thúc bằng `ngay_het_han`.
- **21 trường hạn ở 21 loại** (bảng ở mục 7.5 của [`02_taxonomy_design.md`](../00_data_and_eval/reports/02_taxonomy_design.md)).
- **Số tài liệu duy nhất** của các loại ứng viên (từ `data/labels_v2.csv`): `HD_MUA_BAN` 32, `HD_VAN_CHUYEN` 26, `GCN_DDK_BAN_LE_XD` 27, `CC_TAP_HUAN_VC_HNH` 24, `PHIEU_XUAT_KHO` 21 (6 trong đó là tệp ghép khác loại, trích theo segment), `BB_GIAO_NHAN_HANG_HOA` 21, `DON_DAT_HANG` 20. Gần như cả `CC_TAP_HUAN_VC_HNH` (23/24) và `PHIEU_XUAT_KHO` (15/15 ngoài tệp ghép) là **một biểu mẫu duy nhất** nên kết quả trích xuất trên chúng sẽ lạc quan.
- **Văn bản**: `data/ocr_v2.jsonl` (OCR cục bộ, mọi trang tới 30 trang, chữ có dấu nhưng sai ở chữ viết tay/con dấu), `data/ocr_llm_haiku.jsonl` (LLM chép, chỉ 2 trang đầu), và text layer thật cho các trang born-digital (61 trang, nằm trong đúng 3 thư mục: phiếu xuất kho, đơn đặt hàng và một tệp Word 30 trang — [báo cáo bake-off](../team1_ocr/experiments/01_engine_bakeoff/RESULTS.md) §2).
- **Ngày trong tên tệp** (ví dụ "DDK-CHIN LOAN-12.1.28" khớp dòng "có giá trị đến hết ngày 12 tháng 01 năm 2028" trên giấy; theo mục 7.5 báo cáo 02) từng được coi là nhãn yếu miễn phí. **Công ty đã trả lời câu 16 ngày 2026-10-16: ngày trong tên tệp không mặc nhiên là ngày hết hạn** (xem "Quy ước trường hạn" bên dưới), nên chỉ dùng để kiểm chéo, không làm đáp án và không làm nguồn xác nhận độc lập.

### Trạng thái các việc (cập nhật sau giai đoạn 2: đã có số đo trên đáp án silver)

| việc | trạng thái | ở đâu |
|---|---|---|
| T1 schema 4 loại | **xong bản nháp**, chờ duyệt (câu 11, 13, 14) | [`schema/`](schema/README.md): `<DOC_TYPE>.json`, `build_schema.py`, test khớp taxonomy |
| T5 dữ liệu cá nhân | **xong**: `store_personal_ids=false` bỏ số định danh + ngày sinh khỏi đầu ra mặc định; log/báo cáo không có giá trị PII; có test. Họ tên tạm giữ (cần gắn nhắc hạn với người) — chờ câu 12 | `schema/pii_fields.json`, `schema/pii_policy.py`, `src/extraction/field_result.py` |
| T3 bộ chấm | **xong**: 4 chế độ so sánh (chặt/thô/không dấu/mềm), CI bootstrap theo đơn vị, tỉ lệ đúng/bỏ trống/**sai giá trị** cho trường hạn; đã dùng chấm DEV và TEST | `eval/normalize.py` (cài đặt chuẩn ở `src/extraction/normalize.py`), `eval/field_metrics.py` |
| T2 đáp án trường | **silver xong, CHƯA có người kiểm**: Haiku 104 đơn vị, Sonnet 40, Opus phân xử 58 trường (`model_adjudicated`); ước lượng sai của Haiku ~17% trên mục bất đồng/rủi ro. Cần người của công ty kiểm trước khi coi là đáp án thật | `gold/` ([README](gold/README.md), `silver_report.md`) |
| T4 so sánh phương pháp | **xong** (DEV 76 + TEST 22 đơn vị, TEST chấm một lần với cấu hình đóng băng): [`RESULTS.md`](experiments/02_methods/RESULTS.md). Khuyến nghị: luật + LLM cục bộ ghép theo kiểu, hạn chỉ tự nhận khi một mô hình đọc trùng ngày trong tên tệp. Đã thăng cấp vào `src/extraction/field_extractor.py` | `methods/`, `experiments/02_methods/`, `src/extraction/` |
| T7 ảnh trang trong pipeline | **xong**: `src/pipeline.py` dựng ảnh trang (PyMuPDF 200 dpi, thư mục tạm) cho nguồn VLM của hạn, mặc định bật; DEV 66 trường hạn: tự nhận đúng 37/66 so với 32/66 không ảnh, sai 0 (đáp án máy, hiệu ở mức biên) | [`../00_data_and_eval/experiments/02_chain_with_images/RESULTS.md`](../00_data_and_eval/experiments/02_chain_with_images/RESULTS.md) |
| T4b loại mới, zero-tuning (giai đoạn 3) | **xong** (84 đơn vị silver v2, 17 loại; DEV 62, TEST 12, EXCLUDED 10 báo riêng): cấu hình đóng băng giai đoạn 2 cho F1 mềm 0.75 [0.70; 0.79] (LLM; luật giai đoạn 2 trống cho loại mới), hạn đúng 52/62, sai 2; quy tắc tự nhận `any-model=filename` chỉ nhận 24/62 (0 sai) vì tên tệp loại mới không luôn là hạn. Một vòng cải tiến chung chỉnh trên DEV (luật ngày chung `methods/generic_date_rules.py`, quy tắc `regex=llm`): phần không chỉnh (TEST+EXCLUDED) tự nhận 12/17, 0 sai (cận trên 22%) so với 3/17 của quy tắc cũ. Đề xuất đưa vào `src/` (chưa làm, cần thêm 17 loại vào `schemas.py`) ở mục 6 báo cáo | [`experiments/03_unseen_types/RESULTS.md`](experiments/03_unseen_types/RESULTS.md) |
| T6 truy vết/bảng | chưa làm (`page` chưa có trong `ExtractedEntity`; bảng hàng hóa chưa trích) | — |

**Bộ công cụ chú thích silver (`gold/`).** `units.csv` (đơn vị = `(doc_id, segment_idx)`, split DEV/TEST/EXCLUDED, trang, **trang được cho xem**), `pages/<unit_id>/pNN.png`
(200 dpi như `team1_ocr/experiments/03_llm_silver/render_pages.py`, trang dọc cắt đôi thành `pNN_a`/`pNN_b`, cạnh dài <= 1600 px), `SILVER_PROMPT.md` (lệnh cho người chú thích:
chỉ đọc ảnh được liệt kê, **quy tắc dừng: không đọc được thì ghi `error`, không bao giờ đoán**), `batches/batch_NN.json` và `batches_second_annotator.json`, `merge_silver.py`
(kiểm hợp lệ, gộp, `fields_silver_v1.jsonl`, `silver_report.md`). Quy trình: `build_units.py` -> người chú thích ghi `gold/silver_raw/<tên>/<unit_id>.json` -> `merge_silver.py`.
Thư mục `gold/pages/` (~440 MB, chứa ảnh giấy tờ thật), `gold/silver_raw/` (có họ tên), `gold/units.csv` (có tên tệp) và `_cache/` **không được commit** (xem ghi chú `.gitignore` trong báo cáo giai đoạn 1).

**Phương pháp (`methods/`).** Giao diện chung: `method.extract(unit) -> {trường: {value, normalized, page}}` (đủ mọi trường schema, giá trị vắng = null) và `method.run(unit) -> MethodResult`
(có `status` ok/skipped/error và độ trễ; "rỗng" không phải "thành công"). Chạy được trên mọi nguồn văn bản: `ocr_v2`, `ocr_llm_haiku`, `text_layer`.

| phương pháp | tệp | cần | ghi chú |
|---|---|---|---|
| luật/regex | `regex_rules.py` | chỉ CPU | chạy trên văn bản bỏ dấu giữ nguyên chỉ số (chịu lỗi dấu của OCR); luật viết/chỉnh trên DEV |
| ngày trong tên tệp | `filename_date.py` | không cần văn bản | baseline yếu cho trường hạn; chưa xác nhận quy ước (câu 16) |
| GLiNER + gán trường | `gliner_fields.py` | `gliner`, mô hình `belumind/barb-1-ie-vi` (đã có trong cache HF; nạp CPU ~40 s) | đoạn liên quan thay vì 4000 ký tự đầu; trường mã định danh luôn null (10 nhãn cố định của `BarbEntityExtractor` không có nhãn số hiệu) |
| LLM cục bộ + JSON Schema | `local_llm_json.py` | Ollama >= 0.5, `qwen3.5:4b` | `format` = JSON Schema; cache đĩa; on-premise |
| VLM cục bộ (ảnh) | `local_vlm_json.py` | như trên + ảnh `gold/pages/` (v2: tham số `pages_dir`, `gold/v2/pages_v2/`) | không qua OCR: thử với chữ viết tay/dưới con dấu |
| luật ngày chung (loại chưa có luật riêng) | `generic_date_rules.py`, bật bằng `RegexRules(generic=True)` | chỉ CPU | giai đoạn 3: nhãn hạn/hiệu lực/ngày ký/ngày cấp dùng chung cho mọi loại; mặc định tắt (giữ hành vi v1) |

Chạy thử: `.venv\Scripts\python.exe -X utf8 teams\team4_extraction\methods\smoke_test.py --methods regex,filename,gliner,llm,vlm` (chỉ DEV). Test:
`.venv\Scripts\python.exe -X utf8 -m pytest teams\team4_extraction\tests -q`.

### Chưa đo / chưa có (sau giai đoạn 2)

- **Chưa có đáp án do người kiểm**: mọi con số là so với silver do mô hình LLM đọc (Haiku, Sonnet, Opus phân xử). Phải có người của công ty kiểm ít nhất mọi ô `needs_human`/viết tay/dưới dấu và một mẫu ngẫu nhiên phần đồng thuận.
- **Chưa chứng minh tỉ lệ sai <= 1% của hạn tự nhận**: cần >= 299 lần tự nhận đúng liên tiếp; ta có 37 (DEV) + 12 (TEST), 0 sai (cận trên 95%: 8% và 22%).
- **Chưa thử biểu mẫu mới**: thẻ tập huấn và phiếu xuất kho gần như một mẫu; GCN và hợp đồng có biến thể nhưng ít (TEST 6 đơn vị mỗi loại). **Cập nhật giai đoạn 3**: đã thử cấu hình đóng băng trên 17 loại mới (84 đơn vị, silver v2) — xem hàng T4b; luật giai đoạn 2 không có gì cho loại mới, LLM/VLM vẫn đọc được phần lớn, hạn tự nhận cần quy tắc khác (còn 17 trường ngoài mẫu chỉnh, chưa đủ cho mức sai ≤ 1%).
- Quy ước "ngày trong tên tệp = ngày hết hạn" đã bị công ty bác (câu 16, 2026-10-16) trong khi quy tắc `any-model=filename` của 4 loại cũ vẫn dựa vào nó: phải bỏ hoặc thay (T8).
- Chưa biết khuôn dạng ERP, danh sách trường bắt buộc, quy tắc nhắc hạn; chưa trích bảng hàng hóa (T6); dữ liệu cá nhân: mặc định tạm thời (xem T5), chờ câu 12.
- Độ trễ/VRAM đo khi GPU dùng chung với việc khác.

### Bẫy đã thực sự gặp ở giai đoạn 2 (chi tiết ở [`RESULTS.md`](experiments/02_methods/RESULTS.md) mục 8)

Ollama bị tiến trình khác đẩy mô hình ra (mỗi lời gọi mất 30-45 s nạp lại); LLM 4B đọc bảng phiếu xuất kho lệch một cột; hạn sai vì OCR đọc nhầm chữ số (22/12) và chữ viết tay (24/21) mà luật, LLM và cả VLM cùng đọc nhầm; đáp án có chỗ không phải ngày ("từ ngày ký"); regex không dấu bắt nhầm số văn bản căn cứ pháp lý; ký tự điều khiển backspace lọt vào chuỗi regex khi vá tệp bằng heredoc không-raw.

### Dùng trong sản xuất

```python
from src.extraction.field_extractor import FieldExtractor, extract_fields     # cùng chữ ký extract(slice, label) với BarbEntityExtractor
res = FieldExtractor().extract(doc_slice, "GCN_DDK_BAN_LE_XD", filename="DDK-XYZ-12.1.28.pdf")   # -> ExtractionResult; không ném ngoại lệ
```

`status`: `ok` | `skipped` | `error` (kết quả một phần nếu LLM hỏng: luật vẫn chạy; xem `error`). `entity_dict` có `_sources`, `_expiry` (`accepted`/`needs_review`/`not_found`/`no_expiry`), `_expiry_suggestion`, `_expiry_rule` (quy tắc tự nhận đã dùng) và `_expiry_would_accept` (quy tắc SẼ nhận không; số liệu chạy bóng). **Mặc định `ExtractConfig.auto_accept_expiry=False`**: mọi hạn là `needs_review`, không ngày nào tự nhận; `--auto-accept-expiry` (CLI) / `auto_accept_expiry=True` bật lại hành vi cũ (báo cáo 04 N2/N3). Mặc định bỏ số định danh + ngày sinh (T5).

**21 loại được hỗ trợ** (`schemas.SUPPORTED_TYPES`; giai đoạn 3 thêm 17 loại, đưa kết quả [thí nghiệm 03](experiments/03_unseen_types/RESULTS.md) vào sản phẩm):
- 4 loại giai đoạn 2: luật riêng (`field_rules.RULES`, tệp đã đóng băng) + LLM, quy tắc tự nhận hạn `any-model=filename` (không đổi; kiểm trên 104 đơn vị v1 bằng `ocr_v2`: 0 đơn vị / 0 trường khác trước khi sửa).
- 17 loại giai đoạn 3: luật ngày chung `src/extraction/generic_date_rules.py` (chỉ trường ngày: hạn, hiệu lực từ, ký, cấp; là dự phòng cho loại không có luật riêng, qua `apply_rules_with_fallback`) + LLM; quy tắc tự nhận hạn `regex=llm` (chọn trên DEV; ngoài mẫu chỉnh tự nhận 12/17 trường hạn, 0 sai, cận trên 95% 0,22). **Chưa đủ bằng chứng cho mức sai <= 1%** (47 lần tự nhận đúng trên 84 đơn vị, chỉ 12 ngoài mẫu chỉnh): luật chung và LLM đọc cùng một bản OCR nên không độc lập. **Vì vậy `auto_accept_expiry` TẮT mặc định cho cả 21 loại** (báo cáo 04, N2/N3): quy tắc `regex=llm` vẫn chạy và ghi `_expiry_would_accept` để đo, nhưng mọi hạn là `needs_review` kèm ngày gợi ý; chỉ bật (`--auto-accept-expiry`) cho quy tắc nào đạt ≥ 299 lần tự nhận không lỗi trong chạy bóng.
- Giấy ghi "không/vô thời hạn" và không nguồn nào nêu ngày: `_expiry[trường] = "no_expiry"`, giá trị `None` (không bịa ngày); chưa có số đo thật (0/62 đơn vị DEV v2 có cụm này), chỉ có test tổng hợp.
- Đặt `ExtractConfig(expiry_rule=...)` để ép một quy tắc cho mọi loại; mặc định `None` = theo loại (quy tắc chỉ quyết định tự nhận khi `auto_accept_expiry=True`; xem trên).

Cần Ollama chạy ở 127.0.0.1 với `qwen3.5:4b` (không thì status `error`, kết quả một phần).

### Chạy lại giai đoạn 2

Xem mục 9 của [`RESULTS.md`](experiments/02_methods/RESULTS.md): `run_methods.py` → `make_results.py` → `freeze.py` (một lần, ghi `dev_selection.json`) → TEST một lần với `--final-test` → `render_tables.py` → `build_results_md.py`. Bảng kết quả: [`results/results_table.csv`](results/results_table.csv) (giao thức đánh giá chỉ định nghĩa bảng chung cho phân loại, nên trích xuất dùng bảng riêng này, cùng quy tắc chỉ thêm dòng). Test: `.venv\Scripts\python.exe -X utf8 -m pytest teams\team4_extraction\tests tests\test_extraction_fields.py tests\test_extraction_field_result.py -q`.


### Quy ước trường hạn (quyết định của công ty, 2026-10-16)

Nguyên ý chủ dự án (nói tắt): *"ngày trong tệp phải cụ thể là ngày gì thì mới là ngày hết hạn"*. **Diễn giải của nhóm** (cần xác nhận lại nếu khác ý chủ dự án):

* Một ngày chỉ là ngày hết hạn khi **tài liệu ghi cụ thể đó là ngày gì** ("có hiệu lực đến ngày…", "ngày hết hạn…", "có giá trị đến hết ngày…"). Ngày in ở chỗ khác (ngày ký, ngày cấp, ngày lập) không tự thành hạn; ngày trong **tên tệp** cũng không.
* Một số giấy tờ **không có** ngày hết hạn. Với loại đó, `ngay_het_han` = `not_present` là **kết quả hợp lệ**, không phải lỗi hay "bỏ sót"; bộ chấm không được tính là miss.
* Quy ước phân xử "kể từ ngày ký" → `not_present` là **phù hợp** với quyết định này. Giấy chỉ ghi khoảng thời gian không kèm ngày cụ thể ("thời hạn 05 năm"): prompt silver đã quy định `value` = cụm như in, `normalized = null`, `note = chi_ghi_thoi_han` (không tự cộng ngày). Nếu hai quy ước này chưa được áp đồng nhất ở mọi nơi, đối chiếu lại ở lượt silver sau.
* Hệ quả cho mã: quy tắc `any-model=filename` (`src/extraction/expiry_rules.py`) **không được dùng như nguồn xác nhận độc lập**; `auto_accept_expiry` giữ `False`.

## Việc cần làm (theo thứ tự ưu tiên)

Công sức là **ước lượng của người viết kế hoạch**.

### T1 (P0) — Schema trích xuất theo loại, bắt đầu từ 4 loại

- **Vì sao:** không có schema thì không có "đúng/sai" để đo. Bắt đầu ít loại nhưng làm sạch.
- **Chọn 4 loại đầu:** `GCN_DDK_BAN_LE_XD` (hạn `ngay_het_han`, 27 tài liệu), `CC_TAP_HUAN_VC_HNH` (hạn `ngay_het_han`, 24), `HD_MUA_BAN` (hạn `hieu_luc_den` + `so_hop_dong`, `ben_ban`, `ben_mua`, 32), `PHIEU_XUAT_KHO` (chứng từ kế toán, văn bản số hóa sạch, 21). Lý do: số lượng lớn nhất trong các loại có trường hạn, cộng một loại chứng từ cho ERP.
- **Các bước:** (1) script `schema/build_schema.py` đọc `key_fields` của taxonomy và sinh mô hình Pydantic/JSON Schema cho mỗi loại; (2) với mỗi trường ghi **kiểu chuẩn hóa**: `date` (ISO 8601; từ "ngày 12 tháng 01 năm 2028", "12/1/28"), `number` (định dạng Việt Nam "10.000,5"), `id` (mã số thuế chỉ chữ số), `text`; (3) quy ước giá trị vắng: `null` kèm lý do `not_present` (giấy không ghi) khác `not_found` (giấy có ghi nhưng máy không tìm thấy) — rất quan trọng cho trường hạn (hợp đồng không ghi hạn khác với máy bỏ sót); (4) ghi cho mỗi trường nó thường là chữ in, viết tay hay dưới con dấu (để phân tích lỗi); (5) đánh dấu trường chứa dữ liệu cá nhân (xem T5); (6) test: schema khớp taxonomy.
- **Bắt đầu từ:** `data/taxonomy_v2.json` (`classes[].key_fields`).
- **Sản phẩm:** `schema/<DOC_TYPE>.json` (4 tệp), `schema/README.md`, test.
- **Xong khi:** 4 schema được nhóm 00 và một người của công ty duyệt (câu 11, 13, 14 có thể đổi trường); test qua.
- **Công sức (ước lượng):** 1–1,5 ngày.

### T2 (P0) — Đáp án trường (reference data) có LLM hỗ trợ, người kiểm

- **Vì sao:** cần đáp án cấp **trường**. Gõ tay toàn bộ quá tốn công; dùng LLM làm bản nháp rồi người kiểm là cách rẻ nhất — nhưng chỉ khi kiểm có kỷ luật.
- **Các bước:**
  1. Tập tài liệu: mọi tài liệu duy nhất của 4 loại ở T1 (27 + 24 + 32 + 21 = 104). Với tệp ghép, chạy theo **segment** (cột `segments` của `labels_v2.csv`).
  2. Hai mô hình **khác nhau** (khác họ nếu chủ dự án cho phép; hoặc một mô hình thị giác cục bộ qua Ollama nếu đọc được ảnh) trích **độc lập** từ **ảnh trang** vào đúng schema T1, ghi thêm `page` và trích dẫn nguồn trên trang. Hai mô hình cùng họ chung lỗi: bài học từ nhãn loại tài liệu (κ = 1,0 giữa hai mô hình cùng họ vẫn chưa chứng minh nhãn đúng).
  3. Chuẩn hóa rồi so từng trường: giống nhau → `agreed_unverified`; khác hoặc một bên `null` → `needs_human`.
  4. **Người kiểm:** toàn bộ `needs_human`; **toàn bộ trường nằm ở vùng viết tay hoặc dưới con dấu** (đây là chỗ bản chép của LLM kém tin cậy nhất: OCR cục bộ sai gần như hoàn toàn ở đó và `mean_conf` không báo được; Haiku và Sonnet chép lệch nhau tới ~6% CER trên một số trang scan, xem `team1_ocr/experiments/03_llm_silver/haiku_vs_sonnet_pages.csv`); và một **mẫu ngẫu nhiên các trường `agreed_unverified`** để đo tỉ lệ sai của chính phần "đồng thuận" (kèm khoảng tin cậy).
  5. Kiểm chéo trường hạn với ngày trong tên tệp: chênh lệch → xem lại cả hai (có thể tên tệp sai hoặc đáp án sai).
  6. Mỗi giá trị lưu: `value`, `normalized`, `status` (`human_verified` / `agreed_unverified`), `verifier`, `page`, tên và phiên bản hai mô hình, ngày.
- **Cảnh báo cứng:** số dưới con dấu và chữ viết tay là nơi LLM dễ **bịa một giá trị hợp lý**. Không nhận trường nào làm đáp án cuối cùng chỉ vì hai mô hình giống nhau. Con số báo cáo cuối chỉ tính trên `human_verified` hoặc báo cả hai riêng.
- **Văn bản LLM chỉ có 2 trang đầu** (`ocr_llm_haiku.jsonl`): trường nằm sau trang 2 (ví dụ điều khoản hiệu lực của hợp đồng) cần chép thêm trang; ghi trang của từng trường để lọc khi so sánh nguồn văn bản.
- **Sản phẩm:** `gold/fields_v1.jsonl`, `gold/README.md`, `experiments/01_reference_data/RESULTS.md` (số trường, tỉ lệ đồng thuận hai mô hình, tỉ lệ sai trong mẫu kiểm, thời gian người kiểm).
- **Xong khi:** mọi trường của 104 tài liệu có trạng thái; tất cả `needs_human` và trường viết tay/con dấu đã `human_verified`; có ước lượng tỉ lệ sai của phần đồng thuận.
- **Công sức (ước lượng):** 3–5 ngày kể cả giờ người kiểm.
- **Điều kiện tiên quyết:** T1; chủ dự án đã cho phép gửi **bộ mẫu này** cho LLM ngoài (không áp dụng cho mẫu mới); dữ liệu cá nhân xử lý theo T5.

### T3 (P0) — Chỉ số và bộ chấm trường

- **Chỉ số:** (a) khớp **chính xác** (chuỗi trước chuẩn hóa) và khớp **sau chuẩn hóa** (ngày, số, mã số thuế, chữ hoa/thường và dấu cách); (b) precision/recall/F1 **theo từng trường**, với quy ước: dự đoán không `null` và đúng = TP; không `null` nhưng sai = FP + FN; `null` mà đáp án có = FN; không `null` mà đáp án `null` = FP; (c) **cấp tài liệu**: tỉ lệ tài liệu có *mọi trường bắt buộc* đúng; (d) với trường hạn: tỉ lệ đúng ngày tuyệt đối, tỉ lệ bỏ trống, tỉ lệ **ra sai giá trị** (nguy hiểm hơn bỏ trống vì làm lịch nhắc sai). Khoảng tin cậy bootstrap theo tài liệu.
- **Cỡ mẫu:** ước lượng một tỉ lệ ≈ 0,9 với sai số ±5 điểm ở độ tin cậy 95% cần khoảng 138 giá trị trường (công thức 1,96²·p(1−p)/e²); mỗi loại chỉ có 21–32 tài liệu nên đọc theo loại sẽ có khoảng rộng (~±11 điểm cho 27 tài liệu); gộp theo loại trường để có kết luận mạnh hơn.
- **Chia dữ liệu:** dùng chia DEV/TEST đóng băng của nhóm 00; luật và prompt chỉnh trên DEV, TEST chấm một lần ([giao thức](../00_data_and_eval/reports/03_evaluation_protocol.md)).
- **Sản phẩm:** `eval/field_metrics.py` + test trong `teams/team4_extraction/tests/`; kết quả ghi vào bảng chung theo quy tắc của nhóm 00.
- **Xong khi:** test qua trên dữ liệu giả có đáp án biết trước; báo cáo mẫu cho một phương pháp đơn giản.
- **Công sức (ước lượng):** 1 ngày.

### T4 (P1) — So sánh phương pháp, và đo cái giá của lỗi OCR

- **Ba phương pháp, cùng thước đo T3:**
  1. **Luật/regex** theo từng trường (ví dụ "có giá trị đến hết ngày … tháng … năm …", mã số thuế, số có dấu chấm ngăn nghìn).
  2. **GLiNER** (`src/extraction/barb_extractor.py`): thực thể "ngày" chưa nói ngày nào là ngày hết hạn, nên cần thêm luật gán thực thể → trường (từ khóa lân cận); sửa giới hạn 4000 ký tự bằng cách đưa vào đoạn liên quan thay vì 4000 ký tự đầu.
  3. **LLM cục bộ có đầu ra ràng buộc JSON** qua Ollama (`127.0.0.1:11434`: `qwen3.5:4b`, `qwen2.5:3b`): đưa schema T1, yêu cầu JSON; kiểm tra phiên bản Ollama hỗ trợ ràng buộc định dạng theo schema (chưa kiểm tra). Phải chạy được on-premise.
- **Cái giá của OCR:** chạy **cùng** bộ trích xuất, cùng tài liệu, trên (a) `ocr_v2.jsonl`, (b) bản chép LLM, (c) text layer cho trang born-digital; báo Δ độ chính xác trường theo loại trường (chữ in / số / viết tay / dưới con dấu). Đây là câu trả lời cho nhóm 1 "OCR cần tốt tới đâu".
- **Baseline rẻ:** ngày trong tên tệp (chỉ cho trường hạn).
- **Sản phẩm:** `experiments/02_methods/RESULTS.md` (và các thư mục con theo phương pháp); phương pháp thắng chuyển vào `src/extraction/` với test.
- **Xong khi:** bảng so sánh ba phương pháp × ba nguồn văn bản có khoảng tin cậy, nêu "không tách được" khi cần; đã nêu độ trễ và có chạy on-premise được hay không.
- **Công sức (ước lượng):** 4–6 ngày.
- **Điều kiện tiên quyết:** T1–T3.

### T5 (P0) — Dữ liệu cá nhân: cái gì được trích và lưu

- **Vì sao:** `CCCD`, `GPLX` và phần người đại diện trên `GCN_DKDN`, `GIAY_UY_QUYEN` chứa số định danh; thẻ tập huấn có họ tên và năm sinh. Chưa có quyết định của công ty.
- **Các bước:** (1) từ `key_fields` lập `schema/pii_fields.json` liệt kê trường chứa dữ liệu cá nhân (ví dụ `so_dinh_danh`, `so_gplx`, `ngay_sinh`, `ho_ten`, `nam_sinh`); (2) **tạm thời** không trích số định danh và ngày sinh vào đầu ra mặc định, cờ cấu hình `store_personal_ids=false`; (3) log và báo cáo không bao giờ chứa giá trị các trường đó (che hoặc bỏ); (4) test bảo đảm điều này; (5) khi có câu trả lời (câu 12) cập nhật.
- **Sản phẩm:** `schema/pii_fields.json`, cấu hình, test.
- **Xong khi:** test chứng minh log và `ExtractionResult` mặc định không chứa các trường PII.
- **Công sức (ước lượng):** 0,5–1 ngày.

### T6 (P2) — Truy vết về ảnh, bảng, đầu ra ERP

- Hợp đồng hiện **không** lưu trang và tọa độ của giá trị; `data/ocr_v2.jsonl` không lưu hộp. Để người duyệt thấy "giá trị này nằm ở đâu" cần: thêm `page` (và hộp) vào `ExtractedEntity` qua nhóm 00, và nhóm 1 chạy lại bộ phát hiện dòng để lưu hộp.
- Bảng hàng hóa của `PHIEU_XUAT_KHO`, `BB_GIAO_NHAN_HANG_HOA`, `DON_DAT_HANG` (`dong_hang`) → `ExtractedTable`: làm sau khi trường đơn giản ổn.
- Định dạng ERP: chờ câu trả lời của công ty.
- **Công sức (ước lượng):** 3+ ngày.

### T8 (P0) — Bỏ/thay quy tắc tự nhận dựa trên tên tệp (từ quyết định của công ty 2026-10-16)

- **Vì sao:** `any-model=filename` (4 loại cũ) chỉ nhận một ngày khi một mô hình đọc trùng ngày trong tên tệp; công ty nói ngày trong tên tệp không mặc nhiên là hạn. Số cũ (0 sai trong 49 lần tự nhận; dev 37, TEST 12) đúng như phép đo nhưng không còn là cơ sở để bật tự nhận. Ở 17 loại mới ngày trong tên tệp đứng một mình sai 17/40 lần có ngày (14 là giấy không có hạn).
- **Các bước:** (1) bỏ `filename` khỏi mọi quy tắc tự nhận trong `src/extraction/expiry_rules.py` hoặc đánh dấu "chỉ kiểm chéo, không đếm vào tự nhận"; (2) đo trên DEV các quy tắc không dùng tên tệp, có nguồn độc lập với OCR: `regex=vlm` (84 đơn vị v2: 46/62 tự nhận đúng, 0 sai, cận trên 6%), `regex=llm=vlm` (45/62, 0 sai); (3) thêm ca kiểm cho loại không có hạn: `not_present` đúng được tính là đúng, không phải bỏ sót; (4) cập nhật `_expiry_would_accept` và các báo cáo để nói rõ quy tắc nào đã bỏ; (5) bộ chấm: phân biệt "không có hạn" với "có hạn nhưng không đọc được".
- **Chỉ đo trên DEV;** không mở TEST. Mọi quy tắc tự nhận mới cần ≥ 299 lần tự nhận không lỗi trước khi bật (chạy bóng).
- **Xong khi:** không còn quy tắc tự nhận nào dựa vào tên tệp; báo cáo ghi số trước/sau trên cùng DEV; test cho `not_present`.

## Cách chạy lại những gì đã có

```powershell
# từ gốc repo
.venv\Scripts\python.exe -X utf8 -m pytest tests\test_extractor.py -q     # test bộ trích xuất (mô hình giả, không tải GLiNER)
.venv\Scripts\python.exe -X utf8 -c "import json; t=json.load(open('data/taxonomy_v2.json',encoding='utf-8')); c={x['id']:x for x in t['classes']}['PHIEU_XUAT_KHO']; print([k['name'] for k in c['key_fields']])"
```

Chạy GLiNER thật (đã chạy được ở giai đoạn 1 trên CPU; lần đầu trên máy khác cần mạng để tải mô hình):

```powershell
.venv\Scripts\python.exe -X utf8 -c "from src.extraction.barb_extractor import BarbEntityExtractor; from src.common.contracts import DocumentSlice; s=DocumentSlice(slice_id='s1',start_page=1,end_page=1,page_count=1,combined_text='BÊN BÁN: CÔNG TY TNHH ... Mã số thuế: 0000000000. Giấy có giá trị đến hết ngày 12 tháng 01 năm 2028.'); r=BarbEntityExtractor().extract(s,'GCN_DDK_BAN_LE_XD'); print(r.status, r.error, r.entity_dict)"
```
Nếu in `status = error`, đọc `error`: thiếu thư viện `gliner`/`torch` hoặc không tải được mô hình. Đó là hành vi đúng, không phải lỗi giấu.

## Bẫy thường gặp

1. **NER không phải điền trường.** GLiNER trả mọi "ngày", không biết ngày nào là ngày hết hạn. Phải có bước gán trường.
2. **4000 ký tự đầu.** Trường nằm sau đó (điều khoản hiệu lực trong hợp đồng dài) bị bỏ qua mà không báo.
3. **Nhãn GLiNER phải có dấu** ("tổ chức"); nhãn ASCII làm mô hình lệch.
4. **Định dạng ngày/số tiếng Việt:** "ngày 12 tháng 01 năm 2028", "12/1/28", "10.000.000", "15⁰C" (chỉ số trên bị đọc sai — là phần lớn lỗi còn lại của LLM trên trang số hóa, báo cáo bake-off §2).
5. **Hạn in trên giấy khác hạn tính ra** ("có giá trị 02 năm, từ ngày … đến ngày …"): ghi quy tắc nào được ưu tiên (câu 11).
6. **Số dưới con dấu và chữ viết tay:** OCR sai và LLM có thể bịa giá trị hợp lý. Không dùng `mean_conf` để lọc.
7. **Hai LLM giống nhau không có nghĩa đúng** (cùng họ, cùng lỗi).
8. **Một biểu mẫu, nhiều tài liệu:** `CC_TAP_HUAN_VC_HNH` và `PHIEU_XUAT_KHO` gần như một biểu mẫu → điểm cao giả; kiểm tra bằng biểu mẫu mới khi có (nhóm 00, T3).
9. **Tệp ghép:** trích theo segment, không theo tệp; tệp 93 biên bản lấy mẫu sinh 93 bản ghi (nếu công ty cần — câu 14).
10. **Kết quả rỗng không phải thành công:** `status` phải là `ok` mới tính; `skipped`/`error` phải đếm riêng trong báo cáo.
11. **Ngày trong tên tệp** do nhân viên gõ và không mặc nhiên là ngày hết hạn (quyết định của công ty 2026-10-16); dùng kiểm chéo, không làm đáp án, không làm nguồn xác nhận độc lập.
12. **Dữ liệu cá nhân trong báo cáo/log** (xem T5).
13. **Lỗi đã biết ở luật ngày chung (giai đoạn 3): ký tự backspace thay cho `\b`.** Trong `src/extraction/generic_date_rules.py` dòng ~44 (bản gốc ở `teams/team4_extraction/methods/generic_date_rules.py` dòng ~41) mẫu `SIGN_PATTERNS` "Ký ngày …" chứa ký tự điều khiển 0x08 (backspace) ở chỗ lẽ ra là `\b` (ranh giới từ), nên mẫu này **không bao giờ khớp**. Giữ nguyên có chủ ý để khớp các số đã đo (mọi số của thí nghiệm 03 chạy với mã này); sửa thì phải đo lại cả thí nghiệm. Ảnh hưởng chủ yếu tới trường ngày ký, không phải ngày hết hạn. Nếu sửa: đổi thành `\b` trong chuỗi `rf"..."` rồi chạy lại `03_unseen_types` và các test `test_t4_generic_date_rules.py`, `tests/test_extraction_generic_types.py`.
14. **Số dev của quy tắc chọn trên chính dev là lạc quan.** `regex=llm` được chọn trên DEV v2 (35 lần tự nhận), phần ngoài mẫu chỉnh chỉ 12 lần; trên 84 đơn vị hai người chú thích silver chỉ đồng thuận 0,896 [0,842; 0,933] ở trường ngày, và hàng phân xử ưu tiên trường lệch tên tệp nên đáp án nghiêng nhẹ về quy tắc dùng tên tệp (báo cáo 04, T6).

## Câu hỏi cần hỏi doanh nghiệp

1. (câu 11) Những ngày hết hạn nào cần nhắc, nhắc trước bao lâu, cho ai? Giấy không ghi hạn (thẻ huấn luyện PCCC) tính theo quy định nào? Khi giấy ghi cả "thời hạn 02 năm" và ngày cụ thể, lấy cái nào?
2. (câu 12) Có được trích và lưu số căn cước, số giấy phép lái xe, ngày sinh, họ tên vào ERP không? Ai được xem, lưu bao lâu?
3. (câu 13, 14) Mức chi tiết: từng biên bản tự kiểm tra, từng biên bản lấy mẫu là một bản ghi hay chỉ lưu theo cửa hàng/kỳ?
4. (câu 16) ~~Ngày trong tên tệp có luôn là ngày hết hạn không?~~ **Đã trả lời 2026-10-16: không mặc nhiên** (xem "Quy ước trường hạn"). Còn mở: "BC", "GOC", "photo" nghĩa là gì? Có cần ghi bản chính/bản sao?
5. (câu 9, 17) ERP cần số nào từ mỗi chứng từ giao nhận? Có sẵn danh mục khách hàng/nhà cung cấp/cửa hàng/xe/lái xe (kèm mã số thuế, biển số) để đối chiếu và chuẩn hóa tên không?
6. Khuôn dạng nhập vào ERP (API, tệp, trường bắt buộc, định dạng ngày/số)?
7. Mức sai chấp nhận được với trường hạn, và quy trình người duyệt khi máy không chắc?
8. Ai chịu trách nhiệm kiểm đáp án trường (T2) và dành bao nhiêu giờ?
