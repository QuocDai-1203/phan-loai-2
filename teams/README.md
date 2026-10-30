# Bản đồ các nhóm làm việc

Dự án: hệ thống **chạy tại chỗ (on-premise)** cho một công ty kinh doanh xăng dầu. Đầu vào là PDF quét; hệ thống phải (1) tách tệp ghép thành từng tài liệu, (2) nhận ra mỗi tài liệu là loại gì, (3) lưu đúng hồ sơ, (4) lấy các trường quan trọng (nhất là **ngày hết hạn**) đưa vào ERP. Đây là ứng dụng thật, không phải bài báo: mọi nhóm phải làm ra thứ chạy được, đo được và nói thật về chỗ chưa đo.

Người mới: đọc [`docs/HANDBOOK_FOR_RESEARCHERS.md`](../docs/HANDBOOK_FOR_RESEARCHERS.md) trước, rồi README của nhóm mình. Kế hoạch tuần, giả thuyết và điểm tích hợp: [`docs/PARALLEL_RESEARCH_PLAN.md`](../docs/PARALLEL_RESEARCH_PLAN.md).

**Trạng thái ngày 2026-10-16 (sau giai đoạn 3).** Giai đoạn 3 mở rộng trích xuất sang 21 loại, đưa ảnh trang vào pipeline, thêm quy tắc `id` và `tiebreak` cho tệp ghép, và có review độc lập kèm thiết kế triển khai ([`00_data_and_eval/reports/04_phase3_review_and_deployment.md`](00_data_and_eval/reports/04_phase3_review_and_deployment.md)). **Mặc định sau review (mã là chuẩn):** tách `model+merge`; `tiebreak` tắt nhưng ghi bóng; `id` chạy bóng và chuyển tệp sang người duyệt; VLM bật; tự nhận ngày hết hạn **tắt** (`--auto-accept-expiry` để bật); tệp > 30 trang chuyển người. Lý do: các tùy chọn được thiết kế từ chính các tệp dùng để đo và TEST không có tệp ghép loại đó, nên không kiểm được ngoài mẫu. Tóm tắt giai đoạn 3 và 15 việc ưu tiên: [`README.md`](../README.md) mục "Giai đoạn 3".

**Trạng thái ngày 2026-10-12.** Cả bốn nhóm đã có kết quả đo và mã trong `src/`; đường ống đầy đủ chạy bằng `scripts/run_pipeline.py` (chính sách tách mặc định `model+merge`). Kết quả toàn trình theo tệp (tách + phân loại, dev 245 tệp và TEST 59 tệp chấm một lần, kèm chuỗi tới ngày hết hạn và chi phí) nằm ở [`00_data_and_eval/experiments/01_end_to_end/RESULTS.md`](00_data_and_eval/experiments/01_end_to_end/RESULTS.md). Điều chưa có: nhân viên công ty kiểm đáp án (nhãn loại, ranh giới, trường: cả ba đều do máy tạo) và mẫu ghép lớn hơn. Số liệu và việc còn lại: README từng nhóm.

## 1. Các nhóm

| Thư mục | Sở hữu | Nhận từ | Giao cho | README |
|---|---|---|---|---|
| [`00_data_and_eval/`](00_data_and_eval/) | Dữ liệu mẫu, nhãn (`data/labels_v2.csv`), taxonomy, chia DEV/TEST, bộ chấm (`eval/`), quy trình đánh giá, bảng kết quả chung, câu hỏi cho doanh nghiệp, quản trị dữ liệu | Nhân viên công ty (kiểm nhãn, trả lời câu hỏi) | Mọi nhóm: nhãn, splits, harness | [README](00_data_and_eval/README.md) |
| [`team1_ocr/`](team1_ocr/) | Đọc chữ từ ảnh trang: engine OCR, tập `data/ocr_v2.jsonl`, bản chép "bạc" của LLM, gold OCR, tốc độ, chạy offline | PDF | `OCRDocumentResult` | [README](team1_ocr/README.md) |
| [`team2_splitting/`](team2_splitting/) | Tách tệp ghép thành tài liệu, tìm ranh giới trang | `OCRDocumentResult` | `SplitResult` | [README](team2_splitting/README.md) |
| [`team3_classification/`](team3_classification/) | Nhận loại tài liệu (34 loại + `OTHER`), từ chối khi không chắc, tỉ lệ tự xếp hồ sơ. Kết quả hiện có: [`01_classical_baselines/RESULTS.md`](team3_classification/experiments/01_classical_baselines/RESULTS.md) (baseline cổ điển), [`02_llm_and_cascade/RESULTS.md`](team3_classification/experiments/02_llm_and_cascade/RESULTS.md) (LLM cục bộ, embedding, cascade có từ chối), [`03_src_cascade/RESULTS.md`](team3_classification/experiments/03_src_cascade/RESULTS.md) (mã cascade trong `src/` so với thí nghiệm); giai đoạn 3: [`04_safety_margin`](team3_classification/experiments/04_safety_margin/RESULTS.md) (biên an toàn, kiểm mẫu), [`05_composite_slices`](team3_classification/experiments/05_composite_slices/RESULTS.md) (biên bản trong tệp ghép, `rule_title_tiebreak`) | `DocumentSlice` | `ClassificationResult` | [README](team3_classification/README.md) |
| [`team4_extraction/`](team4_extraction/) | Lấy trường theo từng loại (ngày hết hạn, số hợp đồng, bên A/B, số lượng…) | `DocumentSlice` + `ClassificationResult` | `ExtractionResult` | [README](team4_extraction/README.md) |

Quy tắc sở hữu: mỗi nhóm chỉ sửa trong thư mục của mình và trong module `src/` tương ứng (`src/ocr`, `src/splitting`, `src/classification`, `src/extraction`). Muốn đổi `src/common/contracts.py`, dữ liệu trong `data/` hoặc `docs/LABELING_GUIDELINE.md` thì báo nhóm `00_data_and_eval` và ghi vào nhật ký thay đổi.

## 2. Quy ước thư mục (mọi nhóm giống nhau)

```text
teams/<nhóm>/
  README.md              Mục tiêu · Hiện trạng · Việc cần làm · Cách chạy lại · Bẫy · Câu hỏi cho doanh nghiệp
  experiments/
    NN_ten_ngan/         NN = số thứ tự hai chữ số (01, 02, ...), tên không dấu
      *.py / *.sh        script sinh ra MỌI con số trong RESULTS.md
      RESULTS.md         câu hỏi · lệnh chạy chính xác · bảng số · "đo được" tách khỏi "suy luận" · hạn chế
      _cache/            đầu ra trung gian, KHÔNG commit (đã nằm trong .gitignore)
  results/               CSV/hình cuối cùng (bảng chung ở teams/team3_classification/results/results_table.csv)
  gold/                  đáp án do người làm (nếu nhóm cần), có README nói cách làm
  tests/                 pytest cho code của nhóm (code dùng lại được thì chuyển vào src/ kèm test ở tests/)
```

Các thư mục nhóm đã có đủ phần cần dùng: `team2_splitting/` có `experiments/01`–`05`, `gold/`, `models/` (mô hình cặp trang), `results/`; `team4_extraction/` có `schema/`, `gold/`, `methods/`, `eval/`, `experiments/02_methods`, `results/`, `tests/`; `00_data_and_eval/` có thêm `experiments/01_end_to_end`. Nhóm nào cần thư mục mới thì tạo theo quy ước trên.

Mỗi `RESULTS.md` phải nêu: nhãn nào (tệp và `labels_sha1_10`), nguồn văn bản nào (`text_source`), biến thể split nào, mô hình/engine **thật sự** đã chạy, ngày chạy. Mẫu tốt: [`team1_ocr/experiments/01_engine_bakeoff/RESULTS.md`](team1_ocr/experiments/01_engine_bakeoff/RESULTS.md).

## 3. Giao diện giữa các nhóm: các lớp Pydantic thật trong `src/common/contracts.py`

Chỉ các trường dưới đây tồn tại. Trường nào không có ở đây thì chưa có trong hợp đồng; muốn thêm phải qua nhóm 00.

| Lớp | Nhóm tạo ra | Trường (kiểu, mặc định) |
|---|---|---|
| `BoundingBox` | 1 | `text`, `x`, `y`, `w`, `h`, `confidence=1.0`, `polygon=None`, `is_handwritten=False` |
| `OCRPageResult` | 1 | `page_number` (từ 1), `width`, `height`, `full_text=""`, `boxes=[]`, `has_header_seal=False`, `has_signature_box=False` (hai cờ này chỉ khớp từ khóa trong văn bản, không phát hiện con dấu thật), `ocr_engine="apple_vision"` (tên engine thực sự đã chạy), `source="ocr"` (`text_layer`, `ocr` hoặc `embedded_ocr_layer+ocr`), `error=None`, **`mean_conf=None`**, **`flags=[]`** (hai trường in đậm: thêm ở thay đổi #1) |
| `OCRDocumentResult` | 1 → 2 | `file_name`, `total_pages`, `pages=[OCRPageResult]`, `processing_time_ms=0.0`, `error=None` |
| `DocumentSlice` | 2 | `slice_id`, `start_page`, `end_page` (từ 1, gồm cả đầu cuối), `page_count`, `combined_text`, `pages=[]`, `boundary_confidence=1.0` (cờ của luật, không phải xác suất; của phương pháp `model` là điểm thô chưa hiệu chỉnh), `boundary_method="rule"` (`rule`, `rule_v2`, `model`, `none`; hậu tố `+type_merge` khi lát cắt là kết quả gộp), `ocr_errors=[]` |
| `SplitResult` | 2 → 3 | `source_file`, `total_pages`, `slices=[DocumentSlice]`, `processing_time_ms=0.0` |
| `ClassificationResult` | 3 → 4 | `slice_id`, `predicted_category` (id taxonomy hoặc `UNKNOWN`), `confidence=0.0`, `probabilities={}`, `model_name="none"`, `requires_human_review=False`, `processing_time_ms=0.0`, `tier="none"` (`rule`/`tfidf`/`kev`/`llm`/`human`/`none`; hằng số `CLASSIFICATION_TIERS`), `confidence_kind="none"` (`model`/`heuristic`/`none`), `abstain_reason=None`, `evidence=None`, `error=None`, `fallback_used=False`, **`suggested_category=None`**, **`suggested_confidence=None`**, **`suggestion_source=None`** (ba trường in đậm: thêm ở thay đổi #1; chỉ có ý nghĩa khi `tier="human"`) |
| `ExtractedEntity` | 4 | `label`, `text`, `start_char=None`, `end_char=None`, `confidence=1.0` |
| `ExtractedTable` | 4 | `table_name`, `headers=[]`, `rows=[]` |
| `ExtractionResult` | 4 → ERP | `slice_id`, `document_type`, `entities=[]`, `entity_dict={}`, `tables=[]`, `processing_time_ms=0.0`, `status="ok"` (`ok`/`error`/`skipped`), `error=None` |
| `SliceRouting` (thay đổi #1, #3) | ghép | `slice_id`, `decision` (`auto_file`/`needs_human`), `category=UNKNOWN`, `reasons=[]`, `suggested_category=None`, `extraction_status=None`, **`extraction_note=None`**, **`expiry={}`** (`accepted`/`needs_review`/`not_found` theo trường hạn), **`expiry_suggestion={}`**, **`field_review=False`** (bốn trường in đậm: thêm ở thay đổi #3) |
| `FileRoutingSummary` (thay đổi #2) | ghép | `decision="needs_human"`, `n_slices=0`, `n_auto=0`, `n_needs_human=0`, `reasons=[]`, `splitter=""`, `n_slices_before_merge=0`, `n_field_review=0`, `n_llm_calls=0`, `llm_ms=0.0` |
| `DocumentProcessingPipelineResult` | ghép (`src/pipeline.py`) | `file_name`, `total_pages`, `is_composite_bundle` (nay: bộ tách trả > 1 lát cắt), `ocr_result`, `split_result`, `classifications=[]`, `extractions=[]`, `total_processing_time_ms=0.0`, **`routing=[]`**, **`stage_timings_ms={}`**, **`warnings=[]`** (ba trường in đậm: thêm ở thay đổi #1), **`file_routing=None`** (thêm ở thay đổi #2) |

Quy ước đã thành luật (và có test ở `tests/test_contracts.py`):

- **Lỗi phải nói ra.** OCR hỏng → `full_text` rỗng và lý do trong `error`; không bao giờ nhét thông báo lỗi vào văn bản. Bộ phân loại không quyết định được → `UNKNOWN`, `confidence=0.0`, `requires_human_review=True`. Bộ trích xuất lỗi → `status="error"`; kết quả rỗng không được coi là thành công.
- **Nói đúng ai tạo ra kết quả.** `tier`, `model_name`, `boundary_method`, `ocr_engine` ghi đúng thành phần đã chạy.
- **Điểm của luật không phải xác suất.** `confidence_kind="heuristic"` và `boundary_confidence` là hằng số của luật.
- Nhãn loại tài liệu là `id` trong [`data/taxonomy_v2.json`](../data/taxonomy_v2.json), không phải tên thư mục cũ.

Khoảng trống hiện có (ghi nhận, chưa sửa): hợp đồng không có `doc_id` nối về `data/manifest.csv`; `ExtractedEntity` không có trang và tọa độ nên chưa truy vết được trường về ảnh; `ExtractionResult.entity_dict` chưa có schema theo loại; `data/ocr_v2.jsonl` không lưu hộp tọa độ nên chưa điền được `boxes`.

## 4. Quy tắc đánh giá: mọi thí nghiệm đều theo một giao thức

Văn bản quy chuẩn: [`00_data_and_eval/reports/03_evaluation_protocol.md`](00_data_and_eval/reports/03_evaluation_protocol.md). Tóm tắt những điều không được vi phạm:

1. Đơn vị đánh giá là **tài liệu duy nhất** (304 tài liệu từ 336 tệp), không phải tệp; bản sao byte-giống-hệt cùng nhãn và cùng phía chia.
2. Nhãn là `data/labels_v2.csv` (cột `doc_type`), **không** dùng tên thư mục cũ. Script nhận tham số `--labels`.
3. Chia theo nhóm biểu mẫu (`StratifiedGroupKFold`); chọn mô hình, đặc trưng, ngưỡng, prompt **chỉ** trên DEV bằng CV.
4. **TEST khóa**: mỗi cấu hình đã chốt chấm TEST đúng một lần, bằng lệnh riêng. Không sửa gì sau khi nhìn điểm TEST.
5. Báo cáo kèm khoảng tin cậy (bootstrap theo tài liệu) và so sánh ghép cặp; khi khoảng tin cậy của hiệu chứa 0, viết "không tách được hai phương pháp".
6. Ghi kết quả vào bảng chung bằng `append_result_row` (chỉ thêm dòng, không sửa dòng cũ) và viết `RESULTS.md` có script tái lập.
7. Nói rõ cái gì **đã đo** và cái gì **suy luận**; chưa đo thì viết "chưa đo".

## 5. Dữ liệu chung (tóm tắt, chi tiết ở handbook)

`data/manifest.csv` (336 PDF) · `data/duplicate_groups.csv` · `data/taxonomy_v2.json` · `data/labels_v2.csv` (nhãn do mô hình gán, **chưa có người của công ty duyệt**) · `data/splits/` · `data/ocr_v2.jsonl` (OCR cục bộ, mọi trang tới tối đa 30 trang/tài liệu) · `data/ocr_llm_haiku.jsonl` (bản chép của LLM, 2 trang đầu) · `data/classified_v2/` (bộ mẫu đã xếp đúng loại để xem bằng mắt).

Dữ liệu là hồ sơ nội bộ có thông tin cá nhân: chỉ giữ trong kho riêng tư, không công bố, và chỉ bộ mẫu này mới được gửi cho LLM bên ngoài (chủ dự án đã đồng ý cho mục đích nghiên cứu). Bản chạy thật phải on-premise. Chi tiết: [`00_data_and_eval/README.md`](00_data_and_eval/README.md), mục Quản trị dữ liệu.

## 6. Nhật ký thay đổi hợp đồng (`src/common/contracts.py`)

Quy tắc (mục 1): đổi hợp đồng phải ghi vào đây. Điều kiện chấp nhận một thay đổi: **chỉ thêm**; mọi trường cũ giữ nguyên tên, kiểu, mặc định; payload JSON cũ vẫn nạp được; `tests/test_contracts.py` có test tương thích ngược; các nhóm khác không phải sửa mã.

| # | Ngày | Ai | Thay đổi | Lý do | Tương thích |
|---|---|---|---|---|---|
| 1 | 2026-10-12 | kỹ sư tích hợp (đưa cascade và engine OCR đã chốt vào `src/`) | **`OCRPageResult`**: thêm `mean_conf: Optional[float]=None`, `flags: List[str]=[]`; `source` có thêm giá trị `embedded_ocr_layer+ocr`; `ocr_engine` ghi tên engine thực sự đã chạy (chuỗi đầy đủ, `pymupdf-<ver>/get_text`...). **`ClassificationResult`**: `tier` có thêm `tfidf`, `llm`, `human` (hằng số mới `CLASSIFICATION_TIERS = rule, tfidf, kev, llm, human, none`); thêm `suggested_category`, `suggested_confidence`, `suggestion_source` (đều `None` mặc định). **Lớp mới `SliceRouting`**. **`DocumentProcessingPipelineResult`**: thêm `routing=[]`, `stage_timings_ms={}`, `warnings=[]`; `is_composite_bundle` nay nghĩa là "bộ tách trả > 1 lát cắt" | engine OCR đã chốt có độ tin cậy và cờ xoay/nền theo trang, ba nguồn trang (text layer, OCR, lớp chữ nhúng bị loại) phải phân biệt được; cascade có tầng TF-IDF và LLM và kết quả "chuyển cho người kèm gợi ý" (nhưng `predicted_category` vẫn là `UNKNOWN`, `confidence` vẫn 0); bộ điều phối cần chỗ ghi quyết định xếp hồ sơ và thời gian | Chỉ thêm. Test: `tests/test_contracts.py::test_contract_change_1_*`. Giá trị `tier`/`source` mới là chuỗi tự do nên không vỡ mã cũ; mã nào so sánh `source == "ocr"` phải chấp nhận `embedded_ocr_layer+ocr` (đã rà `src/` và `teams/`: không có). **Nhóm 00 chưa xác nhận** thay đổi này — cần xác nhận khi rà |
| 2 | 2026-10-12 | thí nghiệm toàn trình (`00_data_and_eval/experiments/01_end_to_end`) | Lớp mới **`FileRoutingSummary`** (quyết định cấp tệp, chính sách tách đã chạy, số lát cắt trước và sau khi gộp, số lời gọi LLM, thời gian chờ LLM); **`DocumentProcessingPipelineResult`**: thêm `file_routing: Optional[FileRoutingSummary]=None`; chú thích `boundary_method` liệt kê thêm `rule_v2`, `none` và hậu tố `+type_merge` | pipeline có chính sách tách chọn được và gộp lát cắt cùng loại; cần chỗ ghi quyết định cấp tệp | Chỉ thêm; `file_routing=None` khi kết quả do phiên bản cũ sinh ra. Theo `src/common/contracts.py` và báo cáo toàn trình mục "Thay đổi mã". **Nhóm 00 chưa xác nhận** (dòng này được ghi bổ sung khi đồng bộ tài liệu, vì mã đã đổi mà nhật ký chưa có) |
| 3 | 2026-10-12 | thí nghiệm toàn trình (nối `FieldExtractor` của nhóm 4 vào pipeline) | **`SliceRouting`**: thêm `extraction_note: Optional[str]=None`, `expiry: Dict[str,str]={}`, `expiry_suggestion: Dict[str,str]={}`, `field_review: bool=False` | phản ánh quyết định tự nhận / chuyển người của ngày hết hạn (quy tắc đóng băng `any-model=filename`) trong định tuyến từng lát cắt; phân biệt loại chưa có schema (`skipped` + `no_schema`) với lỗi | Chỉ thêm, có mặc định. Theo `src/common/contracts.py`. **Nhóm 00 chưa xác nhận** (ghi bổ sung như dòng #2) |
| 4 | 2026-10-16 | giai đoạn 3 (chạy bóng sau review độc lập) | **`SliceRouting`**: thêm `shadow: Dict[str, Any]={}` (quyết định mà tùy chọn đang tắt sẽ đưa ra, chỉ để đo: `title_tiebreak_label`, `title_tiebreak_differs`, `expiry_would_accept`). **`FileRoutingSummary`**: thêm `shadow: Dict[str, Any]={}` (`id_rule_extra_boundaries`: trang mà quy tắc `id` sẽ thêm làm ranh giới; `truncated_pages`: trang không được xử lý vì tệp dài hơn `max_pages`) | số liệu chạy bóng cho `id`, `tiebreak`, tự nhận ngày hết hạn và tệp bị cắt trang mà không đổi quyết định; lý do chuyển người mới: `id_rule_boundary`, `truncated_pages` | chỉ thêm; payload cũ vẫn nạp được |

Khoảng trống hợp đồng vẫn còn (xem cuối mục 3): chưa có `doc_id`, `ExtractedEntity` chưa có trang/tọa độ, `OCRPageResult.boxes` chưa được điền bởi engine đã chốt (`ocr_v2.jsonl` cũng không lưu).
