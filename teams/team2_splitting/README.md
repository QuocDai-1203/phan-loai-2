# Nhóm 2 — Tách tài liệu (document splitting)

## Mục tiêu (doanh nghiệp nhận được gì)

Nhân viên thường quét **cả bộ chứng từ của một chuyến hàng thành một PDF** (phiếu xuất kho, chứng thư chất lượng, biên bản giao nhận, biên bản lấy mẫu) hoặc gộp nhiều giấy cùng loại (93 biên bản lấy mẫu trong một tệp). Nhóm này cho hệ thống biết **trang nào mở đầu một tài liệu mới**, để từng tài liệu được nhận loại, lưu đúng hồ sơ và trích xuất riêng. Nếu tách sai: hai giấy bị coi là một (mất bản ghi), hoặc một giấy bị cắt đôi (trường nằm ở hai nửa). Đầu vào `OCRDocumentResult`, đầu ra `SplitResult` / `DocumentSlice` (xem [`teams/README.md`](../README.md)). Quy tắc thế nào là "một tài liệu": mục 7 của [`docs/LABELING_GUIDELINE.md`](../../docs/LABELING_GUIDELINE.md); tổng quan: [`docs/COMPOSITE_DOCUMENTS_AND_SPLITTING.md`](../../docs/COMPOSITE_DOCUMENTS_AND_SPLITTING.md).

## Hiện trạng

### Mã có sẵn

`src/splitting/` có **ba phương pháp chọn bằng `split_document(ocr_doc, method=...)`** (hợp đồng `SplitResult` không đổi; `boundary_method` của mỗi lát cắt ghi đúng phương pháp đã chạy):

| `method` | Mã | Trạng thái |
|---|---|---|
| `"rule"` (**mặc định, hành vi cũ giữ nguyên**) | `boundary_detector.py::is_new_document_start`: trang mở tài liệu mới nếu là trang đầu, **hoặc** chứa "CỘNG HÒA XÃ HỘI" ở bất kỳ đâu, **hoặc** 6 dòng đầu chứa từ khóa tiêu đề. `boundary_confidence` = hằng số 0,95 của luật, **không phải xác suất** | đã đo (thí nghiệm 01): tách nhầm nhiều trên tài liệu nhiều trang không ghép |
| `"rule_v2"` | `rules_v2.py` + `page_features.py`: luật đã sửa (tiêu đề phải mở đầu một dòng, quốc hiệu chỉ ở đầu trang, không tách ở trang trống/chỉ chữ ký/đánh số "2/2"/tiêu đề lặp ở trang ngắn). `boundary_confidence` vẫn là cờ luật 0,95 | đã đo (thí nghiệm 02) |
| `"model"` | `learned.py` + `teams/team2_splitting/models/pair_gb_v0.joblib` (nằm trong thư mục nhóm, có trong kho; không phải thư mục `models/` ở gốc): bộ phân loại cặp trang (gradient boosting, 30 đặc trưng, xác suất loại trang dùng làm đặc trưng). `boundary_confidence` = **điểm thô** tại trang mở lát cắt, chưa hiệu chỉnh (lát cắt đầu: 1.0 theo định nghĩa). Thiếu mô hình thì **báo lỗi**, không âm thầm quay về luật | đã đo bằng cross-fitting (thí nghiệm 04); xem "Đã đo" |

Test: `tests/test_boundary_detector.py` (luật cũ, luật v2, hợp đồng) và `tests/test_splitting_model.py` (phương pháp `model`, lưu/nạp có kiểm sha256, thiếu mô hình thì lỗi).

**Ví dụ chuẩn của kho** (`MOCK_OCR_DOCUMENT_BSR`, 5 trang, đáp án đúng `1-2, 3, 4, 5`: phiếu xuất kho gồm trang 1 và trang chữ ký 2/2): luật cũ trả **5 lát cắt** `(1,1) (2,2) (3,3) (4,4) (5,5)` vì trang 2 lặp lại dòng "PHIEU XUAT KHO THANH PHAM" (tài liệu cũ nói ví dụ này tách đúng; điều đó **không đúng**); `rule_v2` và `model` đều trả đúng 4 lát cắt.

```powershell
.venv\Scripts\python.exe -X utf8 -c "from src.splitting.boundary_detector import split_document; from tests.fixtures.sample_pipeline_fixtures import MOCK_OCR_DOCUMENT_BSR as d; [print(m, [(s.start_page, s.end_page) for s in split_document(d, m).slices]) for m in ('rule', 'rule_v2', 'model')]"
```

### Đã đo (2026-10-12)

Phạm vi **dev** = tài liệu DEV + `EXCLUDED_COMPOSITE` (không có tài liệu TEST), đáp án `gold/boundary_gold_v0.csv` (**máy, chưa người kiểm**), văn bản `data/ocr_v2.jsonl` (tối đa 30 trang/tài liệu; tệp 93 trang chỉ chấm 29 vị trí đầu). Ô: số ranh giới thật bắt được / tổng, kèm số tách nhầm (FP). Mọi số có CI bootstrap theo tệp và so sánh ghép cặp trong `RESULTS.md` của từng thí nghiệm. **Số của phương pháp có học là cross-validated (5 fold theo nhóm biểu mẫu), không phải tập TEST khóa.**

| Nhóm (tệp / ranh giới thật) | rule cũ (01) | rule v2 (02) | b0 chỉ đổi loại (03) | b1 + "bản khác" (03) | c1 logistic (04) | **c2 boosting (04)** |
|---|---|---|---|---|---|---|
| composite khác loại (8 / 20) | 19, FP 2; 5/8 tệp đúng | 19, FP 0; 7/8 | 13, FP 0; 1/8 | 14, FP 0; 2/8 | 20, FP 0; 8/8 | **20, FP 0; 8/8** |
| cùng loại ngoài BB_LAY_MAU (6 / 7) | 4, FP 2; 2/6 | 4, FP 1; 2/6 | 0, FP 0; 0/6 | 2, FP 1; 1/6 | 2, FP 2; 1/6 | **3, FP 2; 2/6** |
| BB_LAY_MAU (5 / 46) | 46, FP 0; 5/5 | 46, FP 0; 5/5 | 0; 0/5 | 38; 1/5 | 41; 2/5 | **44; 4/5** |
| mẫu âm, tách nhầm / 100 vị trí (155 tệp / 501 vị trí) | 46,7 [41,4; 52,8] | 30,1 [23,4; 36,4] | 1,0 [0,1; 2,2] | 27,7 [21,8; 33,5] | 12,6 [9,6; 16,5] | **9,6 [6,3; 12,7]** |
| mẫu âm, tệp nguyên vẹn | 50/155 | 85/155 | 151/155 | 89/155 | 107/155 | **129/155** |

Đọc bảng: (1) **sự khác biệt thật nằm ở mẫu âm** (tài liệu nhiều trang không ghép, nơi tách nhầm làm cắt vụn tệp): c2 so với rule cũ -37,1 [-43,9; -32,0] điểm, so với rule v2 -20,6 [-25,9; -15,5], đều "tách được". (2) **Ở ba nhóm composite hầu hết cặp phương pháp "không tách được"** (8 / 6 / 5 tệp). Ngoại lệ: b0 và b1 "tách được: kém hơn" rule cũ ở `BB_LAY_MAU` vì sót ranh giới, và b0 cũng kém hơn ở hai nhóm còn lại. (3) Nhóm cùng loại ngoài `BB_LAY_MAU` là chỗ chưa phương pháp nào xử lý được (tối đa 4/7). (4) Qwen3.5-4B zero-shot với prompt đã viết gần như không bao giờ nói "tài liệu mới" (0/20, 0/7, 1/46), xem thí nghiệm 05; chỉ chấm 39 tệp. (5) Tài liệu TEST (2 tệp `BB_LAY_MAU`, 36 tệp âm) được chấm MỘT lần với cấu hình đã đóng băng: `experiments/RESULTS_test_docs_only.md` (c2: 9/9 ranh giới, 5 tách nhầm trên 74 vị trí âm; cỡ mẫu rất nhỏ).

**Kết luận end-to-end và mặc định của pipeline (2026-10-12).** Nối tách trang với cascade phân loại và đo theo tệp ([`../00_data_and_eval/experiments/01_end_to_end/RESULTS.md`](../00_data_and_eval/experiments/01_end_to_end/RESULTS.md); dev 245 tệp, TEST 59 tệp chấm một lần, đáp án ranh giới vẫn là `v0` máy): vì 92% tệp là tài liệu đơn hoặc nhiều trang không ghép, **tách trang không làm tăng tỉ lệ tệp đúng hoàn toàn** so với không tách (S0 92,3%; luật cũ 53,4%, luật v2 67,5%, mô hình c2 ngưỡng 0,5 84,9%; tốt nhất 91,9%, hiệu −0,4 điểm, CI [−2,9; +1,9] chứa 0), nhưng giao đúng thêm nhiều tài liệu của tệp ghép (87,7% so với 70,4% tài liệu đáp án). Hai hiệu chỉnh nhận biết loại đã thêm: gộp lát cắt liền kề được phân loại cùng loại (trừ `BB_LAY_MAU`, `src/splitting/type_merge.py`) và ngưỡng ranh giới chọn trên dev. **`src/pipeline.py` nay mặc định `model+merge`** (c2, ngưỡng 0,7, gộp cùng loại trừ ranh giới điểm >= 0,99; `--splitter rule` để về hành vi cũ). Điểm nghẽn của composite khác loại là phân loại lát cắt (biên bản giao nhận bị gán phiếu xuất kho), không còn là tách.

Bảng kết quả riêng của nhóm (bảng chung của nhóm 3 có cột accuracy/macro-F1 không hợp với bài toán tách): `results/results_table.csv`.

### Dữ liệu tham chiếu có thể dựng ngay (tính lại từ `data/labels_v2.csv` và `data/manifest.csv`; khớp mục 7.4 của [`02_taxonomy_design.md`](../00_data_and_eval/reports/02_taxonomy_design.md))

| | Tệp | Trang | Vị trí "giữa hai trang liên tiếp" | Ranh giới thật |
|---|---|---|---|---|
| Tất cả tài liệu duy nhất | 304 | 1113 | 809 | **145** |
| Composite **khác loại** (`composite_mixed=1`) | 8 | 34 | 26 | 20 |
| Composite **cùng loại** | 13 (7 tệp `BB_LAY_MAU` = 125 trang; 6 tệp khác) | 142 | 129 | 125 (trong đó 118 ở 7 tệp `BB_LAY_MAU`) |
| Nhiều trang, **không** composite (mẫu âm) | 191 | 845 | 654 | 0 |

Hệ quả: **chỉ có 27 ranh giới thật ngoài `BB_LAY_MAU`** (20 + 7) trong 14 tệp. 118/145 ranh giới (81%) thuộc 7 tệp biên bản lấy mẫu mà mọi trang đều là một tài liệu; một bộ tách chỉ cần "mỗi trang `BB_LAY_MAU` là một tài liệu" đã ăn gần hết điểm. Phải báo cáo theo từng nhóm, không chỉ F1 gộp.

Văn bản đầu vào: `data/ocr_v2.jsonl` có **mọi trang tới tối đa 30 trang/tài liệu** (tệp biên bản 93 trang bị cắt ở trang 30). `data/ocr_llm_haiku.jsonl` chỉ có **2 trang đầu**, không dùng được để tách. Không lưu hộp tọa độ, kích thước trang.

### Chưa đo / chưa có

- **Chưa có số đo nào trên tập giữ ngoài đủ lớn.** Các số ở mục "Đã đo" là trên đáp án `v0` (chưa người kiểm) và, với phương pháp có học, là cross-validated; chỉ có 27 ranh giới thật ngoài `BB_LAY_MAU` trong 14 tệp (dev: 20 + 7) nên chênh dưới ~10-15 điểm giữa hai phương pháp không tách được. Mọi mục tiêu cũ ("F1-boundary > 95%") đã bị bỏ vì chưa dựa trên phép đo.
- **Kiểu đo chưa làm:** hiệu chỉnh `boundary_confidence` của phương pháp `model` (chưa đo ECE nên là điểm thô); ngưỡng vận hành (cần doanh nghiệp quyết định cắt vụn hay dính hai giấy đắt hơn: bảng độ nhạy ở `experiments/04_pair_classifier/RESULTS.md`); nhóm cùng loại ngoài `BB_LAY_MAU` (T5: có thử nghiệm 06, chưa kiểm giữ ngoài được vì TEST không có tệp loại này); tệp 93 trang chỉ có văn bản tới trang 30 nên 63/92 ranh giới của nó chưa được chấm; mô hình chưa thấy nhà cung cấp chứng từ nào khác ngoài mẫu BSR.
- **Đáp án ranh giới chưa được người kiểm.** `segments` lấy từ annotator A (đã xem đủ trang); B chỉ thấy 2 trang đầu nên không xác nhận được. κ của cờ `is_composite` giữa A và B là 0,86 (16 tệp cả hai đánh dấu, 5 tệp chỉ A). 5 tệp `check_composite`: `36aff038b19e`, `72449aceeff3`, `9f4c4dae0c73`, `87c88bf6d0f1`, `57374da27cae`. Chưa ai xem xem trong 191 tệp "không composite" có tệp ghép bị bỏ sót không (chỉ A xem đủ trang).
- Hiệu quả của Kev `Noul` ("trang này có mở tài liệu mới không?"): **chưa thử** (thay bằng Qwen3.5-4B qua Ollama ở thí nghiệm 05: prompt đã viết gần như luôn trả "cùng tài liệu"; prompt thứ hai chưa chạy xong). Code hiện chỉ gọi Kev với `type: choice` (`CascadedClassifier.classify_with_kev`); chưa kiểm tra máy chủ Kev nhận kiểu nhị phân thế nào (kiểu nhị phân chỉ được nhắc trong bản thiết kế cũ, xem mục 11 của [`docs/RESEARCH_GUIDE.md`](../../docs/RESEARCH_GUIDE.md)).
- Các biểu mẫu bộ chứng từ của nhà cung cấp khác: kho chỉ có 6 bộ chứng từ xuất kho (5 tệp 4 trang + `BSR-…` 5 trang), mọi bộ từ cùng một dạng.

## Việc cần làm (theo thứ tự ưu tiên)

Công sức là **ước lượng của người viết kế hoạch**.

### T1 (P0) — Dựng đáp án ranh giới mức trang và nhờ người kiểm

**Trạng thái (2026-10-12): phần máy XONG, phần người CHƯA LÀM.** `gold/build_boundary_gold.py` -> `gold/boundary_gold_v0.csv` (+ `.meta.json`, `gold/README.md`) tái lập đúng 1113 trang / 809 vị trí / 145 ranh giới bằng một lệnh. **`boundary_gold_v1.csv` KHÔNG tồn tại**: cần người xem đủ trang 21 tệp composite (đặc biệt 5 tệp `check_composite`) và lật nhanh các tệp "không composite" nhiều trang; mọi số ở trên là "đo theo nhãn tạm". Điều kiện tiên quyết bên dưới (không đo trên `v0`) đã được bỏ qua có chủ đích theo yêu cầu của chủ dự án; kết quả phải đọc là tạm thời.

- **Vì sao:** chưa có đáp án thì không đo được gì. Tách tài liệu cần đáp án ở mức **trang** ("trang này có phải trang đầu của một tài liệu mới không", kèm loại).
- **Các bước:**
  1. Chuyển `segments` của `labels_v2.csv` thành bảng trang: mỗi trang có `is_start` (1 ở trang đầu của mỗi segment), loại của segment, `kind` (`mixed` / `same_type` / `single`). Đánh giá chỉ trên **trang ≥ 2** (trang 1 luôn là trang đầu). Đoạn mã dưới cho ra đúng bảng 809 vị trí / 145 ranh giới.
  2. **Mẫu âm:** thêm tài liệu nhiều trang không composite (191 tệp, 654 vị trí). Chúng quan trọng không kém mẫu dương: tập PCCC 26–53 trang có hơn 10 tiêu đề con nhưng không có ranh giới; biên bản nhận bồn/trả bồn, "những điều quy định", "giấy xác nhận thay đổi đăng ký" có tiêu đề riêng nhưng không phải ranh giới.
  3. **Nhờ người kiểm:** xem đủ trang 21 tệp composite (176 trang), đặc biệt 8 tệp composite khác loại (thư mục `data/classified_v2/_COMPOSITE_KHAC_LOAI/`) và 5 tệp `check_composite`; và lật nhanh (ảnh thu nhỏ) các tệp "không composite" nhiều trang để bắt tệp ghép bị bỏ sót. Làm cùng nhóm 00 ([T1 của nhóm 00](../00_data_and_eval/README.md)).
  4. Lưu kết quả kiểm vào `gold/boundary_gold_v1.csv` với cột `verified_by`.
- **Bắt đầu từ:**

```python
# .venv\Scripts\python.exe -X utf8 -  (từ gốc repo)
import pandas as pd
lab = pd.read_csv("data/labels_v2.csv", dtype=str, keep_default_na=False)
man = pd.read_csv("data/manifest.csv", dtype=str, keep_default_na=False)
u = lab[lab.is_duplicate_of == ""].merge(man[["doc_id", "relative_path", "page_count"]], on="doc_id")
rows = []
for r in u.itertuples():
    n = int(r.page_count)
    if r.is_composite == "1":                      # segments dạng "1-2:PHIEU_XUAT_KHO;3:CHUNG_THU_CHAT_LUONG;..."
        segs = []
        for s in r.segments.split(";"):
            rng, typ = s.split(":"); a, _, b = rng.partition("-"); segs.append((int(a), int(b or a), typ))
    else:
        segs = [(1, n, r.doc_type)]
    for k, (a, b, typ) in enumerate(segs):
        for p in range(a, b + 1):
            rows.append(dict(doc_id=r.doc_id, page=p, is_start=int(p == a), segment_idx=k, page_doc_type=typ, n_pages=n,
                             kind="mixed" if r.composite_mixed == "1" else "same_type" if r.is_composite == "1" else "single"))
g = pd.DataFrame(rows); pos = g[g.page >= 2]
print(len(g), len(pos), int(pos.is_start.sum()))   # 1113 809 145
g.to_csv("teams/team2_splitting/gold/boundary_gold_v0.csv", index=False, encoding="utf-8-sig")
```
- **Sản phẩm:** `gold/build_boundary_gold.py`, `gold/boundary_gold_v0.csv` (từ máy) và `boundary_gold_v1.csv` (đã kiểm), `gold/README.md` mô tả cột.
- **Xong khi:** 809 vị trí / 145 ranh giới tái lập bằng một lệnh; có `boundary_gold_v1.csv` với danh sách tệp đã được người xem đủ trang; cập nhật `labels_v2.csv` qua `annotation/adjudication.csv` nếu người sửa `segments`.
- **Công sức (ước lượng):** 0,5 ngày viết script; người kiểm 0,5–1 ngày.
- **Điều kiện tiên quyết:** không để bắt đầu T2 trên bản `v0`; bản `v1` cần người kiểm.

### T2 (P0) — Đo bộ luật hiện có (baseline)

**Trạng thái (2026-10-12): XONG trên đáp án `v0`.** `experiments/01_rule_baseline/{run.py,RESULTS.md}`: theo nhóm, CI bootstrap theo tệp, 5 kiểu lỗi đông nhất, tệp 93 trang chỉ chấm 29 vị trí đầu (ghi rõ). Một lệnh: `.venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/01_rule_baseline/run.py`.

- **Vì sao:** mọi cải tiến sau này chỉ có nghĩa khi so được với baseline đo trung thực.
- **Các bước:** (1) viết bộ nạp từ `data/ocr_v2.jsonl` sang `OCRDocumentResult` (`OCRPageResult` cần `width`, `height` nguyên: điền 0 nếu không biết, ghi rõ); (2) chạy `split_document`, lấy các trang bắt đầu dự đoán; (3) tính **precision/recall/F1 của ranh giới** (trên trang ≥ 2), **tỉ lệ tệp đúng toàn bộ segment** (exact-segment match), **số lần tách nhầm trên mẫu âm** (trên 654 vị trí), và **độ chính xác loại theo segment** (dùng cổng luật `CascadedClassifier.match_rules`, Kev tắt, trên `combined_text` của lát cắt đã ghép khớp theo trang trùng nhiều nhất với segment đáp án); (4) báo **riêng từng nhóm**: 8 composite khác loại, 6 composite cùng loại ngoài `BB_LAY_MAU`, 7 tệp `BB_LAY_MAU`, 191 tệp mẫu âm; (5) khoảng tin cậy Wilson (hoặc bootstrap theo tệp); (6) tệp 93 trang: chỉ có văn bản tới trang 30 — hoặc chạy OCR đủ trang cho tệp đó (`build_ocr_dataset.py --max-pages`, hiện chưa có cờ lọc theo tài liệu) hoặc báo cáo rõ phần bị cắt.
- **Cỡ mẫu để đọc kết quả:** với 27 ranh giới ngoài `BB_LAY_MAU`, kể cả bắt đủ 27/27 thì khoảng Wilson 95% của recall là [0,875; 1,0]; bắt 24/27 là [0,72; 0,96]. Chênh dưới ~10–15 điểm giữa hai phương pháp **không tách được** trên dữ liệu này.
- **Sản phẩm:** `experiments/01_rule_baseline/{run.py, RESULTS.md}` theo [giao thức đánh giá](../00_data_and_eval/reports/03_evaluation_protocol.md) (nêu nhãn + sha, nguồn văn bản, ngày).
- **Xong khi:** bảng số theo nhóm có khoảng tin cậy; phân tích 5 lỗi lớn nhất (đã biết một: trang chữ ký 2/2 lặp tiêu đề); mọi số sinh từ một lệnh.
- **Công sức (ước lượng):** 1–1,5 ngày.
- **Điều kiện tiên quyết:** T1.

### T3 (P1) — Các phương pháp tiếp theo (so với baseline bằng cùng thước đo)

**Trạng thái (2026-10-12): XONG cả bốn.** (a) luật v2 `experiments/02_rule_v2`; (b) gộp theo loại trang `03_type_merge`; (c) bộ phân loại cặp trang `04_pair_classifier` (logistic và gradient boosting); (d) Qwen3.5-4B zero-shot `05_llm_zero_shot` (không phải Kev `Noul`; chỉ 39 tệp, một prompt). Mỗi cái có `RESULTS.md` với bootstrap ghép cặp theo tệp và dòng "không tách được" khi CI chứa 0. Tốt nhất: c2 (gradient boosting), đã đưa vào `src/splitting/` làm `method="model"`.

1. **Phân loại loại theo từng trang rồi gộp các trang liên tiếp cùng loại.** Nhãn loại theo trang lấy từ bảng ở T1. Dùng TF-IDF + hồi quy logistic như nhóm 3 (chia theo nhóm biểu mẫu), gộp trang liên tiếp có cùng loại dự đoán. Hạn chế sẵn có: các tài liệu **cùng loại nối tiếp nhau** phải thêm dấu hiệu "bản khác" (số biên bản, biển số, ngày, đánh số "1/1", tiêu đề lặp lại).
2. **Bộ phân loại cặp trang** (trang i, trang i+1 → có ranh giới không): đặc trưng gồm độ giống văn bản, cùng loại dự đoán, tiêu đề xuất hiện đầu trang i+1, số trang "x/y", số ký tự, dấu hiệu trang chỉ có chữ ký. Hồi quy logistic hoặc cây tăng cường; học từ T4.
3. **Zero-shot với mô hình quyết định Kev `Noul`** ("trang này có mở một tài liệu mới không?"), chạy cục bộ ở `127.0.0.1:8009`. Cần xem tài liệu máy chủ về kiểu nhị phân trước; đo cả độ trễ mỗi cặp trang.
4. **Sửa bộ luật** làm tham chiếu mạnh hơn: không tách ở trang chỉ có chữ ký/con dấu hoặc rất ít chữ; chỉ tính "CỘNG HÒA XÃ HỘI" ở đầu trang. Đây là baseline thứ hai, không phải phương pháp mới.

- **Sản phẩm:** mỗi phương pháp một thư mục `experiments/NN_ten/` với `RESULTS.md`; phương pháp tốt được chuyển vào `src/splitting/` với `boundary_method="model"` và test.
- **Xong khi:** ít nhất hai phương pháp được so với baseline bằng bootstrap ghép cặp theo tệp, nêu "không tách được" khi khoảng tin cậy chứa 0.
- **Công sức (ước lượng):** 3–5 ngày cho ba phương pháp đầu.

### T4 (P1) — Composite tổng hợp, chỉ để huấn luyện và chỉnh tham số

**Trạng thái (2026-10-12): XONG.** `gold/make_synthetic.py` (seed 20261012, chỉ tài liệu đơn DEV, có kiểm tra rò rỉ; `gold/synthetic_v0.csv`). Cross-fitting dùng `generate()` theo từng fold (`cvlib.py`); bảng "trên tổng hợp" và "trên thật" nằm trong `RESULTS.md` của 03 và 04.

- **Vì sao:** chỉ có 21 tệp composite thật (27 ranh giới ngoài `BB_LAY_MAU`). Muốn huấn luyện phải sinh thêm bằng cách **nối các tài liệu đơn**.
- **Các bước:** viết `gold/make_synthetic.py` (hạt giống ghi vào `RESULTS.md`) nối trang của các tài liệu đơn theo mẫu giống thật: bộ 4 chứng từ xuất kho; hợp đồng + giấy đăng ký doanh nghiệp của đối tác; N giấy cùng loại liên tiếp; trộn ngẫu nhiên có trang trắng. **Chỉ lấy tài liệu thuộc DEV** của chia đã đóng băng; không lấy tài liệu TEST và không lấy trang của 21 tệp composite thật.
- **Quy tắc báo cáo:** tổng hợp chỉ dùng để **huấn luyện/chỉnh**; mọi con số trong báo cáo cuối tính trên **composite thật**. Báo cả hiệu năng trên tổng hợp lẫn trên thật để thấy khoảng cách miền (ranh giới tổng hợp thường dễ hơn vì các trang đến từ các lần quét độc lập).
- **Xong khi:** script tái lập được; có bảng "trên tổng hợp vs trên thật" cho mỗi phương pháp học.
- **Công sức (ước lượng):** 1 ngày.

### T5 (P2) — Ca khó: nhiều bản cùng loại trong một tệp

**Trạng thái (2026-10-15): ĐÃ LÀM MỘT PHẦN trên dev, chưa có kiểm giữ ngoài** ([`experiments/06_same_type/RESULTS.md`](experiments/06_same_type/RESULTS.md)). Quy tắc "cùng mẫu (đầu trang giống) mà số hiệu 'Số ...' ở đầu trang khác" thêm ranh giới điểm 1,0 vào `model+merge`: cùng loại ngoài `BB_LAY_MAU` **0/7 -> 4/7** ranh giới (recall +0,571 [0,167; 0,889], n = 6 tệp, 4 ranh giới nằm ở 3 tệp), mẫu âm vẫn 9 tách nhầm / 501 vị trí, khác loại và `BB_LAY_MAU` không đổi. Có trong `src/splitting/` làm tùy chọn `model+merge+id` (`PRESETS`, **không phải mặc định**; mặc định pipeline là `model+merge`). Khi không bật, quy tắc vẫn chạy ở chế độ bóng: trang nó sẽ thêm làm ranh giới ghi ở `file_routing.shadow["id_rule_extra_boundaries"]` và tệp chuyển người kiểm ranh giới (lý do `id_rule_boundary`), không tách. Tệp dài hơn `max_pages` (30) nay chuyển người (lý do `truncated_pages`) thay vì cắt âm thầm. Quy tắc được nghĩ ra sau khi đọc dev và TEST không có tệp cùng loại ngoài BB, nên 4/7 là số trên dữ liệu đã dùng để thiết kế; 3/7 ranh giới còn lại (OCR hỏng, mẫu không có "Số", hai giấy khác mẫu) chưa bắt được. Đặc trưng định danh đưa vào bộ phân loại cặp trang (1/7) và VLM `qwen3.5:4b` nhìn hai ảnh trang (3/7 nhưng +7 tách nhầm ở mẫu âm) **không** đạt. Câu hỏi 14 vẫn còn mở.

- **Vì sao:** biên bản lấy mẫu (tới 93 biên bản/tệp, các trang giống hệt nhau về bố cục), thẻ chứng nhận của hai người (mỗi người 2 trang), hai giấy biên nhận thế chấp, hai hóa đơn. Chỉ nhìn "loại" không đủ.
- **Các bước:** phân tích riêng các tệp cùng loại; thử dấu hiệu "bản khác" (số biên bản, biển số xe, ngày, họ tên, đánh số trang); tách rõ trường hợp mỗi trang là một tài liệu (`BB_LAY_MAU`) với trường hợp tài liệu 2 trang (`CC_NGHIEP_VU_BVMT`, `HOA_DON`).
- **Xong khi:** bảng kết quả riêng cho nhóm này, nêu rõ phương pháp nào xử lý được, phương pháp nào không.
- **Công sức (ước lượng):** 2–3 ngày.
- **Điều kiện tiên quyết:** câu trả lời cho câu hỏi 14 (có cần từng biên bản là một bản ghi không).

### T6 (P1) — Nối vào đường ống

**Trạng thái (2026-10-12): XONG, đã nối vào pipeline** (`src/pipeline.py` mặc định `model+merge` theo thí nghiệm end-to-end 01; trước đó gọi `split_document(doc)` = luật cũ). `boundary_method` ghi đúng (`rule` / `rule_v2` / `model`), `boundary_confidence` của `model` là điểm thô chưa hiệu chỉnh, `ocr_errors` truyền xuống lát cắt, có test. Chú thích `boundary_method` ở `src/common/contracts.py` đã liệt kê `rule_v2`, `none` và hậu tố `+type_merge`.

- Đầu ra `SplitResult` đúng hợp đồng; `boundary_confidence` của phương pháp học phải là xác suất đã hiệu chỉnh hoặc để rõ là điểm thô; `ocr_errors` của lát cắt phải truyền lỗi OCR xuống. Test ở `tests/test_boundary_detector.py`. Công sức (ước lượng): 0,5 ngày.

## Cách chạy lại những gì đã có

```powershell
# từ gốc repo (CPU; máy dùng chung nên thời gian chỉ tham khảo)
.venv\Scripts\python.exe -X utf8 -m pytest tests\test_boundary_detector.py tests\test_splitting_model.py -q    # 15 test
.venv\Scripts\python.exe -X utf8 teams/team2_splitting/gold/build_boundary_gold.py                           # đáp án v0: in 1113 809 145
.venv\Scripts\python.exe -X utf8 teams/team2_splitting/gold/make_synthetic.py                                # composite tổng hợp (seed cố định)
.venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/01_rule_baseline/run.py                   # ~1 phút
.venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/02_rule_v2/run.py                         # ~1 phút
.venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/03_type_merge/run.py                      # ~2 phút
.venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/04_pair_classifier/run.py                 # ~8-15 phút
.venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/04_pair_classifier/save_model.py          # huấn luyện lại teams/team2_splitting/models/pair_gb_v0.joblib
.venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/05_llm_zero_shot/run.py --neg-files 20    # cần Ollama + qwen3.5:4b; có cache nên chạy lại tức thời
.venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/06_same_type/run.py                      # T5; ~1 phút (cross-fit c2+id lần đầu ~7 phút, rồi cache)
.venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/06_same_type/vlm_pairs.py                   # tùy chọn: VLM 147 lời gọi, cần Ollama; có cache
.venv\Scripts\python.exe -X utf8 -m pytest tests\test_splitting_id.py -q                                      # 9 test
# Chấm MỘT lần có cả tài liệu TEST (cấu hình đã đóng băng); mỗi run.py thêm: --scope all --final-test; rồi:
.venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/test_docs_only.py
```

Ví dụ chuẩn của kho với ba phương pháp: xem lệnh ở mục "Mã có sẵn". Quy ước: mặc định mọi `run.py` chỉ dùng tài liệu DEV + `EXCLUDED_COMPOSITE`; `--scope all` bị chặn nếu thiếu `--final-test` (luật mở TEST của [giao thức đánh giá](../00_data_and_eval/reports/03_evaluation_protocol.md)).

Bộ lọc loại composite để xem bằng mắt: `data/classified_v2/_COMPOSITE_KHAC_LOAI/` (8 tệp) và cột `segments` trong `data/classified_v2/INDEX.csv`. Danh sách composite hỗn hợp của chia dữ liệu: `data/splits/excluded_composites.csv`.

## Bẫy thường gặp

1. **Tiêu đề không phải ranh giới.** Trang 2 chữ ký lặp tiêu đề "PHIẾU XUẤT KHO"; tập PCCC 26–53 trang có hơn 10 tiêu đề con; biên bản nhận/trả bồn nằm trong hợp đồng mượn bồn. Quy tắc "có tiêu đề mới" cho ra nhiều tách nhầm.
2. **Ranh giới ở mọi trang** của tệp biên bản lấy mẫu dù các trang giống hệt nhau.
3. **F1 gộp bị `BB_LAY_MAU` chi phối** (118/145 ranh giới). Luôn báo theo nhóm.
4. **Đánh số trang:** `segments` và `OCRPageResult.page_number` đếm từ 1; gold OCR của nhóm 1 (`gold_pages_todo.csv`) đếm từ 0.
5. **Rò rỉ khi sinh composite tổng hợp** từ tài liệu TEST hoặc từ chính trang của composite thật.
6. **Đáp án chưa kiểm:** `segments` do một mô hình xem đủ trang gán; 5 tệp `check_composite` đang chờ người.
7. **Một bộ chứng từ, một nhà cung cấp:** 6 bộ chứng từ xuất kho cùng một dạng; kết quả tốt có thể chỉ là nhớ bố cục.
8. **Văn bản chỉ tới trang 30** trong `ocr_v2.jsonl`; tệp 93 trang thiếu phần sau.
9. **Hai tài liệu khác loại dùng chung một trang** chưa có quy tắc trong hướng dẫn (ghi `GUIDE:`); hai tài liệu cùng loại chung trang là một segment (mục 7.3).
10. Tài liệu cũ `COMPOSITE_DOCUMENTS_AND_SPLITTING.md` từng có JSON ví dụ với loại viết thường và độ tin cậy bịa; bản mới đã bỏ.

## Câu hỏi cần hỏi doanh nghiệp

1. (câu 9) Bộ chứng từ một chuyến hàng: lưu nguyên bộ theo chuyến hay tách từng loại? ERP cần số nào từ mỗi chứng từ?
2. (câu 13) Tập tự kiểm tra PCCC: cần ngày của từng biên bản tự kiểm tra hằng tháng hay chỉ cần biết kỳ nào đã nộp?
3. (câu 14) Biên bản lấy mẫu: mỗi biên bản một bản ghi, hay lưu theo cửa hàng và kỳ?
4. (câu 15) Biên bản trả bồn có là sự kiện riêng? Biên bản ký sẵn nhưng để trống ngày hiểu thế nào?
5. Trang trong một tệp ghép có luôn liền nhau theo từng tài liệu không, hay có khi trang của hai tài liệu xen kẽ?
6. Có thể áp dụng **tờ ngăn** (tờ trắng hoặc mã vạch) giữa các tài liệu khi quét không? Nếu được, bài toán dễ đi nhiều.
7. Số trang lớn nhất của một tệp ghép? Một tệp có thể chứa tài liệu của nhiều khách hàng/nhà cung cấp không?
8. Xin thêm vài bộ chứng từ từ **nhà cung cấp khác** (bố cục phiếu xuất kho khác) để kiểm tra khả năng tổng quát hóa.
