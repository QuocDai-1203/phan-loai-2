## Thiết lập và quy tắc chọn (ghi trước khi chạy dev)

* **Đơn vị, dữ liệu, thước đo, bootstrap, điểm cặp trang cross-fit, TF-IDF cross-fit**: đúng như thí nghiệm 01 (dùng lại `e2e_lib.py` và `Summary` của 01; điểm cặp trang đọc từ `01_end_to_end/results/pair_scores_dev.json`). Kiểm tái lập: biến thể S10 ở đây trùng thí nghiệm 01 (chuỗi lát cắt và nhãn) ở **245/245 tệp**.
* **Biến thể.** S10 = `model` ngưỡng 0,7 + gộp cùng loại trừ ranh giới điểm >= 0,99. `+id`: trước khi tách, các trang được quy tắc "bản khác" (đầu trang giống nhau jaccard >= 0,7 và số hiệu "Số ..." ở đầu hai trang khác nhau) nhận điểm 1,0 (đúng như `split_with_policy`); điểm 1,0 >= 0,99 nên không bị gộp lại. `+tb`: `DocumentClassifier.rule_title_tiebreak = True`. S9 (triage, cờ 0,3) và S0 (không tách) chỉ để đối chiếu.
* **Quy tắc ghi trong `dev_selection_v2.json` TRƯỚC khi chạy dev** (trạng thái `rule_frozen_before_dev_run`, sau đó script ghi kết quả vào cùng tệp và đổi trạng thái thành `dev_done`): biến thể X khác S10 hợp lệ khi, trên 245 tệp dev, (a) số tệp đúng hoàn toàn >= S10, (b) số tệp sai lặng lẽ <= S10, (c) số tài liệu giao đúng và tự động >= S10; trong các biến thể hợp lệ lấy cái giao đúng nhiều tài liệu nhất, hòa thì nhiều tệp đúng hơn, hòa nữa thì ít tùy chọn hơn. Quy tắc đổi mặc định: dev chọn khác S10 **và** trên TEST số tệp đúng >= S10 cũ, số sai lặng lẽ <= S10 cũ. Quy tắc này đơn giản hơn quy tắc của thí nghiệm 01 (không dùng CI) vì ở đây mọi biến thể chỉ khác S10 ở vài tệp composite.
* **Lời gọi LLM phân loại**: cache có sẵn của 01/02 (chỉ đọc); lời gọi mới (4 văn bản ở dev, 0 ở TEST) ghi cache đĩa riêng `_cache/ollama` (không commit), 0 lỗi.

## Đọc kết quả dev

1. **Mỗi tùy chọn sửa đúng nhóm nó nhắm tới và không động vào nhóm khác.** Bảng "Tệp đổi kết quả": id sửa 3 tệp composite cùng loại (đúng như thí nghiệm 06: 3/6 tệp nguyên vẹn), tb sửa 6 tệp composite khác loại (2/8 -> 8/8, đúng như thí nghiệm 05), gộp hai thì cộng lại (không giẫm lên nhau): 232 = 223 + 3 + 6. **0 tệp hỏng** ở mọi nhóm, kể cả 155 tệp nhiều trang không ghép (nơi tách nhầm là rủi ro chính; số tách nhầm của nhóm này không đổi so với S10).
2. **Sai lặng lẽ giảm 14 -> 5** (5,9% -> 2,1% số tệp tự xử lý, Clopper-Pearson [0,7%; 4,9%]), vì phần lớn lỗi âm thầm cũ là tệp composite bị gán nhầm loại. Vẫn **chưa đạt** mục tiêu 1% của giao thức (§7).
3. **Số lời gọi LLM phân loại giảm** 35 -> 26 trên 245 tệp, vì tb cho cổng luật quyết định thay cho TF-IDF/LLM ở một số tài liệu (kiểm hồi quy của thí nghiệm 05: 25/237 tài liệu đơn, cùng nhãn).
4. **Mức độ chắc của "+3,0 điểm [+2,0; +3,9]".** CI hẹp vì chỉ 14 tệp composite thay đổi, tất cả cùng một cách (hỏng 0, sửa 14), nên bootstrap không có biến thiên; đừng đọc nó như độ chắc tổng quát hóa. Hai tùy chọn được nghĩ ra sau khi đọc chính các tệp này (06 và 05 nói rõ), nên đây là mức **trần lạc quan**. Hiệu id ở cấp tài liệu (+2,2 điểm, CI [+0,0; +5,1]) sát 0.
5. **S9 (triage) khác bản chất**: giữ tệp thường nguyên vẹn (155/155) và sai lặng lẽ thấp (4), nhưng trả bằng việc chuyển 22% tệp về người và bỏ rơi tệp ghép (185/318 tài liệu giao đúng). Nếu doanh nghiệp coi sai lặng lẽ đắt hơn nhân sự duyệt, triage vẫn là lựa chọn thay thế (`--splitter triage`).

## Kết quả TEST: đọc đúng nghĩa

Cấu hình đóng băng S10+id+tb cho đúng kết quả của S10 trên 59 tệp (0 tệp đổi). Điều đó nhất quán với việc TEST không có composite khác loại hay cùng loại ngoài `BB_LAY_MAU` để hai tùy chọn tác động; số lời gọi LLM (5) và số lát cắt (70) cũng không đổi, tức tb không đổi quyết định nào ở 59 tệp. TEST vì vậy chỉ trả lời "không hại tệp thường" (đạt, 0 hỏng), **không** xác nhận mức +3 điểm của dev. Lần chạy này ghi là `run2` trong `01_end_to_end/test_run_registry.json` (lần TEST thứ hai của thí nghiệm toàn trình, lý do: cấu hình mới; lần thứ nhất của S10 giữ nguyên).

## Dựng ảnh cho VLM: nén nhanh và khóa cache

* **Vì sao chậm.** Ảnh PNG lưu với `optimize=True` (thí nghiệm 02: trung vị 4,2 s/lát cắt). Đo thẳng (`bench_render.py`, 40 đơn vị dev có trường hạn, 154 ảnh, cùng PyMuPDF 200 dpi, cắt đôi trang, cạnh dài <= 1600 px): `optimize=True` trung vị **3,62 s** (p90 4,32) so với `compress_level=1` **0,89 s** (p90 1,17), nhanh hơn **4,0 lần**. Tệp ảnh to hơn khoảng 40% (23,2 MB so với 16,5 MB trên 16 ảnh thử), không đáng kể vì ảnh chỉ ở thư mục tạm.
* **Điểm ảnh không đổi**: PNG nén không mất; so sánh mảng điểm ảnh RGB của hai cách lưu: **154/154 ảnh giống hệt** (và có test `tests/test_pipeline_options_v2.py`). VLM nhận cùng điểm ảnh.
* **Khóa cache.** Kiểm lại `ollama_vlm_client`: khóa cache trước đây băm **byte của tệp PNG**, nên đổi mức nén sẽ làm lỡ cache dù ảnh giống hệt. Đã đổi sang `image_content_hash` (băm kích thước + điểm ảnh RGB; không giải mã được thì băm byte), tag khóa `t4-src-vlm-v1` -> `v2`. **Hệ quả một lần**: các câu trả lời VLM đã cache dưới khóa cũ (cache của nhóm 4 và `vlm_store.json` của thí nghiệm 02) không còn khớp; lần chạy sau tính lại và cache lại. Số liệu thí nghiệm 02 không đổi vì ảnh/pixel không đổi.
* Trong lúc chạy cả pipeline (mục dưới), `render_ms` của lát cắt có VLM: trung vị **0,92 s**, p95 1,18 s (12 lát).

## Chi phí của cấu hình đã chọn, có OCR thật (`cost_sample_v2.py`)

Mẫu **30 tệp dev, 90 trang** (OCR 30 trang đầu mỗi tệp; mẫu dài nhất 10 trang): 10 tệp loại có trường hạn (3/4/3 theo loại, <= 12 trang) cộng 20 tệp ngẫu nhiên theo nhóm (hạn ngạch 6 một trang, 10 nhiều trang, 2 composite khác loại, 1 cùng loại, 1 `BB_LAY_MAU`), seed cố định; tính chung cả mẫu: 7 một trang, 19 nhiều trang không ghép, 2 composite khác loại, 1 cùng loại, 1 `BB_LAY_MAU`. Chạy qua `DocumentPipeline` thật: `model+merge+id`, `title_tiebreak`, trích xuất bật, VLM bật, OCR VietOCR trên `cuda:0`, cache LLM/VLM là thư mục tạm trống (mọi lời gọi là thật). **GPU RTX 3060 12 GB dùng chung** (Ollama có client khác; Kev không chạy), độ trễ phụ thuộc tải. Cả 30 tệp ra `auto_file`, 0 cảnh báo.

| giai đoạn | trung vị / tệp | p95 / tệp | trung vị / trang | p95 / trang | tỉ trọng tổng thời gian |
|---|---|---|---|---|---|
| OCR (không tính nạp mô hình 6,8 s, một lần) | 8,6 s | 32,2 s | 4,26 s | 6,27 s | 45% |
| tách | 0,25 s | 0,40 s | 0,12 s | 0,22 s | 1,0% |
| phân loại | 8 ms | 25 ms | 4 ms | 7 ms | 0,04% |
| dựng ảnh (chỉ lát cắt có VLM) | 0 (12/30 tệp có), 0,92 s ở các tệp đó | 1,18 s | 0 | 0,47 s | 1,3% |
| trích xuất (LLM + VLM) | 6 ms (12/30 tệp có VLM) | 36,2 s | 6 ms | 25,3 s | 52% |
| **tổng** | **32,6 s** | **49,3 s** | **6,8 s** | **30,5 s** | |

Tệp có VLM (12 tệp): tổng trung vị 42,6 s; tệp không có VLM (18 tệp): 11,2 s. Cả mẫu 809 s cho 90 trang = 400 trang/giờ, nhưng mẫu cố ý nhiều tệp có trường hạn (12/30 = 40%, quần thể 27%).

**Số lời gọi mỗi tệp** (30 tệp): LLM phân loại **0** (0/30; trên 245 tệp dev đếm được 26 lời gọi = 0,11/tệp); LLM trích xuất 14 (0,47/tệp); VLM 12 (0,40/tệp). Độ trễ mỗi lời gọi: LLM trích xuất trung vị 13,3 s (p95 14,7 s), VLM trung vị 20,9 s (p95 22,5 s).

**VRAM** (nvidia-smi 0,5 s/lần, 1296 mẫu, tổng của cả GPU gồm Ollama `qwen3.5:4b` đang nạp): nền trước khi chạy 4,93 GiB, trung vị 5,70 GiB, **đỉnh 6,58 GiB** (+1,65 GiB so với nền: mô hình OCR và ngữ cảnh VLM 12288). Còn dư ~5,7 GiB trên thẻ 12 GiB.

**Ước lượng số trang/giờ cho một máy RTX 3060 12 GB** (xử lý tuần tự từng tệp, như pipeline hiện tại): thời gian một tệp = trang × (OCR 4,04 + tách 0,13 + phân loại ~0) s + 0,273 × 33,9 s (tệp loại có trường hạn: trích xuất LLM+VLM + dựng ảnh, 83/304 = 27,3% tài liệu duy nhất) + 0,069 × 13,3 s (phiếu xuất kho: một lời gọi LLM, 21/304, suy từ độ trễ LLM đo được, không có VLM). Trung bình 3,36 trang/tệp theo cơ cấu tệp thật -> **24,2 s/tệp -> khoảng 500 trang/giờ** (~150 tệp/giờ). Chặn hai đầu: không trích xuất 860 trang/giờ; mọi tệp đều loại có VLM 250 trang/giờ. **Đây là ước lượng từ mẫu 30 tệp một mô hình tuyến tính, không phải đo trên ngày làm việc thật**; nút cổ chai là OCR (4 s/trang) và lời gọi Qwen3.5-4B (13 s + 21 s). Chưa thử chạy OCR của tệp kế tiếp song song với trích xuất của tệp trước (GPU tranh nhau), hướng tăng thông lượng rõ nhất.

## Mặc định mới và rủi ro

Quy tắc ghi trước cho phép đổi mặc định, và đã đổi: `DEFAULT_PRESET = "model+merge+id"` (`src/splitting/policy.py`), `DEFAULT_TITLE_TIEBREAK = True` (`src/pipeline.py`); CLI `--splitter model+merge`, `--no-title-tiebreak` trả về hành vi cũ. Các test khẳng định mặc định cũ trong `tests/test_pipeline.py`, `tests/test_splitting_type_merge.py`, `tests/test_splitting_id.py` được sửa theo (3 dòng khẳng định tên preset). Rủi ro cần chủ phiên cân nhắc, vì bằng chứng TEST là rỗng:

* **tiebreak cho luật quyết định ở 25/237 tài liệu đơn dev** mà trước đây luật bỏ qua (cùng nhãn, 25/25 đúng, nhưng cận trên 95% của tỉ lệ sai là 11,3%). Luật không có độ tin cậy cảnh báo: biểu mẫu chưa thấy có tên loại khác nằm ở vùng tiêu đề có thể nhận sai âm thầm. Chưa đo trên biểu mẫu lạ; thí nghiệm 05 từng đề nghị chờ thêm mẫu BB/PXK từ nhiều nhà cung cấp trước khi bật. Nếu chủ phiên thấy quá sớm: đặt `DEFAULT_TITLE_TIEBREAK = False` (một dòng), id vẫn giữ.
* **id** chỉ có bằng chứng ở 6 tệp composite cùng loại, quy tắc được nghĩ ra sau khi đọc chính chúng (0/448 cặp mẫu âm kích hoạt, 0 tách nhầm thêm trên 155 tệp nhiều trang).

## Chưa chứng minh

1. Đáp án máy, chưa người kiểm; 5 tệp `check_composite` rủi ro cao nhất.
2. Lợi ích của id và tb nằm ở **14 tệp composite dev của vài nhà cung cấp**, đã dùng để nghĩ ra hai tùy chọn; không có giữ ngoài. TEST không chứa composite nào ngoài `BB_LAY_MAU` nên không kiểm được; muốn kiểm cần thêm mẫu ghép từ nguồn khác.
3. Quy tắc chọn ghi trước nhưng ngưỡng của từng tùy chọn (0,7 cho id; 400/300 ký tự cho tb) chọn ở các thí nghiệm 05/06 sau khi xem dev.
4. Sai lặng lẽ vẫn 5/237 (2,1%) trên dev; mục tiêu 1% chưa đạt; chưa đo trên mẫu ngẫu nhiên phần tự xử lý.
5. Chi phí: mẫu 30 tệp, GPU dùng chung (độ trễ thay đổi theo tải; lần chạy này không bị nạp lại mô hình rõ rệt), ước lượng 500 trang/giờ là mô hình tuyến tính trên mẫu cố ý nhiều tệp có trường hạn; OCR giới hạn 30 trang/tệp; không đo nhiều tiến trình song song.
6. Đổi khóa cache VLM làm mất cache cũ một lần (xem trên); chưa chạy lại thí nghiệm 02 để kiểm kết quả VLM giống hệt sau khi đổi khóa (ảnh giống hệt điểm ảnh nên kết quả đáng lẽ giống, nhưng đó là suy luận, VLM chưa được gọi lại trên 82 đơn vị).

## Thay đổi mã

* `src/pipeline.py`: tham số `title_tiebreak` (`DEFAULT_TITLE_TIEBREAK = True`), gán `rule_title_tiebreak` cho bộ phân loại có thuộc tính này (không sửa `doc_classifier.py`).
* `src/splitting/policy.py`: `DEFAULT_PRESET = "model+merge+id"` (chỉ đổi mặc định; preset đã có từ thí nghiệm 06).
* `scripts/run_pipeline.py`: `--splitter` nhận `model+merge+id` (lấy từ `PRESETS`), `--title-tiebreak/--no-title-tiebreak`.
* `src/extraction/field_vlm.py`: `PNG_COMPRESS_LEVEL = 1`, `image_content_hash`, khóa cache `t4-src-vlm-v2`.
* Test mới `tests/test_pipeline_options_v2.py` (CLI, tiebreak truyền xuống bộ phân loại, ảnh giống hệt điểm ảnh, khóa theo điểm ảnh, mặc định mới); 3 khẳng định mặc định cũ được cập nhật ở các tệp test hiện có. Toàn bộ `pytest -q` 285 qua; `teams/00_data_and_eval/tests` + `teams/team4_extraction/tests` 256 qua.
* Thí nghiệm: `run_v2.py`, `cost_sample_v2.py`, `bench_render.py`, `dev_selection_v2.json`, `results/*` (CSV từng tệp chứa `doc_id`, chỉ dùng nội bộ); `01_end_to_end/test_run_registry.json` thêm mục `run2`.
