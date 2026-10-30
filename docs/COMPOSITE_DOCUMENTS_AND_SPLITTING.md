# Tệp ghép nhiều tài liệu (composite) và tách tài liệu

> Cập nhật theo taxonomy v2 (`data/taxonomy_v2.json`) và hướng dẫn gán nhãn v1.1 ([`LABELING_GUIDELINE.md`](LABELING_GUIDELINE.md), mục 7). Nếu tài liệu này mâu thuẫn với hướng dẫn gán nhãn thì **hướng dẫn gán nhãn thắng**. Mọi mã loại trong tài liệu là `id` của taxonomy v2. Kế hoạch công việc của nhóm tách tài liệu: [`teams/team2_splitting/README.md`](../teams/team2_splitting/README.md).
> Nhãn trong tài liệu này do mô hình gán và **chưa có người của công ty duyệt** (xem trạng thái ở mục 3). Đáp án ranh giới (`teams/team2_splitting/gold/boundary_gold_v0.csv`) cũng do máy dựng từ cột `segments`, chưa người kiểm: mọi số "tách đúng" bên dưới là "khớp đáp án máy".
> Trạng thái ngày 2026-10-16: phần nghiệp vụ (mục 1–4) giữ nguyên; kết quả đo và kết luận toàn trình nằm ở mục 6 (mục 6.5 là giai đoạn 3: tệp ghép cùng loại, biên bản trong tệp ghép, tệp > 30 trang); pipeline mặc định dùng chính sách `model+merge` (sau review giai đoạn 3 không bật `id` và `tiebreak` mặc định).

## 1. Vấn đề

Nhân viên thường quét **nhiều chứng từ thành một PDF**: bộ chứng từ của một chuyến hàng mua vào, hoặc gộp nhiều giấy cùng loại (nhiều biên bản lấy mẫu, nhiều thẻ chứng nhận). Nếu coi cả tệp là một tài liệu, hệ thống gán một loại duy nhất cho nhiều tài liệu khác nhau và trích xuất thiếu bản ghi. Cần biết **trang nào mở đầu một tài liệu mới**, rồi nhận loại và trích xuất từng tài liệu.

Hệ thống nhìn tệp như một **dòng trang**: với mỗi vị trí giữa hai trang liên tiếp quyết định "có ranh giới hay không", sau đó gom các trang liền nhau thành lát cắt (`DocumentSlice`) cho nhóm phân loại.

## 2. Định nghĩa (theo hướng dẫn gán nhãn, mục 7)

- **`is_composite = 0`**: tệp là **một** tài liệu logic, dù nhiều trang: hợp đồng nhiều trang, thẻ hai mặt, giấy chứng nhận kèm trang quy định, hợp đồng kèm phụ lục/bảng báo giá của chính nó, tập hồ sơ có bìa chung.
- **`is_composite = 1`**: tệp chứa **từ hai tài liệu logic trở lên**:
  - **khác loại**: các segment có `doc_type` khác nhau (ví dụ phiếu xuất kho + chứng thư + biên bản giao nhận + biên bản lấy mẫu). Trong dữ liệu, cột `composite_mixed = 1`.
  - **cùng loại**: mọi segment cùng `doc_type` nhưng là các **bản khác nhau** (chứng nhận của hai người, giấy của hai xe, 93 biên bản của 93 chuyến hàng).
- **Phép thử kèm theo.** Hỏi: *"Nếu cắt đoạn trang này thành một tệp riêng, nó được gán nhãn gì?"* Một loại khác với tài liệu đứng trước (và không phải `OTHER`) → segment mới. Cùng loại nhưng là bản khác (khác người, xe, số hoặc ngày) → segment mới. Cùng loại, cùng chủ thể, cùng văn bản (trang tiếp theo, mặt sau, phụ lục) → không tách. Đứng riêng chỉ là `OTHER` mà đi kèm tài liệu trước → không tách.
- **Không tách (danh sách thường gặp):** biên bản nhận bồn/trả bồn trong hợp đồng mượn bồn; "những điều quy định" sau giấy chứng nhận cửa hàng; giấy xác nhận thay đổi hay công bố đăng ký của chính doanh nghiệp; danh mục hàng nguy hiểm (trang 2 của giấy phép vận chuyển); "kết quả kiểm định" (barem); bảng báo giá sau hợp đồng; bảng xác định khối lượng sau biên bản thanh lý; bìa hợp đồng, trang trắng, mặt sau thẻ, ảnh phương tiện; **trang cuối chỉ có chữ ký/con dấu** (ví dụ trang "2/2" của phiếu xuất kho), kể cả khi trang đó lặp lại tiêu đề.
- **Tập có bìa chung** (`HO_SO_QUAN_LY_PCCC`, `BIEN_PHAP_UNG_PHO_SU_CO`) là **một** tài liệu dù có hơn 10 tiêu đề con (quyết định, kế hoạch, biên bản tự kiểm tra).
- **Nhãn chính** `doc_type` của tệp composite = loại của **segment đầu tiên**. **Đơn vị nhỏ nhất là trang**: hai giấy cùng loại in chung một trang thuộc một segment.
- Cột `segments`: `1-2:PHIEU_XUAT_KHO;3:CHUNG_THU_CHAT_LUONG;4:BB_GIAO_NHAN_HANG_HOA;5:BB_LAY_MAU` — trang đếm từ 1, các đoạn liên tiếp, phủ kín từ trang 1 tới trang cuối, không có khoảng trắng.
- Phiếu xuất kho của nhà cung cấp theo sau là biên bản giao nhận (kèm hoặc không kèm chứng thư, biên bản lấy mẫu) luôn là composite khác loại.

## 3. Số liệu thật của kho mẫu

Tính từ `data/labels_v2.csv` (304 tài liệu duy nhất) và `data/manifest.csv`; tổng số vị trí và ranh giới khớp mục 7.4 của [`02_taxonomy_design.md`](../teams/00_data_and_eval/reports/02_taxonomy_design.md).

| | Số tệp | Số trang | Vị trí giữa hai trang liền nhau | Ranh giới thật |
|---|---|---|---|---|
| Tất cả tài liệu duy nhất | 304 | 1113 | 809 | 145 |
| Composite khác loại | 8 | 34 | 26 | 20 |
| Composite cùng loại | 13 | 142 | 129 | 125 |
| Nhiều trang, không composite | 191 | 845 | 654 | 0 |

- **Tổng: 21 tệp composite** (8 khác loại, 13 cùng loại) trên 304 tài liệu duy nhất.
- Trong 13 tệp cùng loại có **7 tệp `BB_LAY_MAU`** (125 trang, mỗi trang một biên bản) chiếm 118/145 ranh giới; 6 tệp còn lại là 2 tệp `BIEN_NHAN_THE_CHAP_PT` (2 trang), 1 tệp `HOA_DON` (4 trang), 1 tệp `GCN_KIEM_DINH_DO_LUONG` (3 trang), 1 tệp `CC_NGHIEP_VU_BVMT` (4 trang), 1 tệp `BB_GIAO_NHAN_HANG_HOA` (2 trang). **Chỉ có 27 ranh giới ngoài `BB_LAY_MAU`.**
- Trạng thái nhãn: 5 tệp composite ở trạng thái `check_composite` (`36aff038b19e`, `72449aceeff3`, `9f4c4dae0c73`, `87c88bf6d0f1`, `57374da27cae`) và 1 tệp (93 trang) ở `check_low_conf`. `is_composite` và `segments` lấy từ annotator A (xem đủ trang); annotator B chỉ thấy 2 trang đầu; κ của cờ composite giữa hai bên là 0,86 (`teams/00_data_and_eval/annotation/agreement_summary.json`).

### 8 tệp composite khác loại

Thư mục xem nhanh: `data/classified_v2/_COMPOSITE_KHAC_LOAI/`.

| `doc_id` | Nơi nằm trong kho mẫu (tên tệp không nêu: một số tên chứa tên người; tra bằng `doc_id` trong `data/manifest.csv`) | Trang | `segments` | Trạng thái |
|---|---|---|---|---|
| `9f4c4dae0c73` | tệp ở gốc thư mục mẫu (tên theo mã máy của nhà cung cấp) | 5 | `1-2:PHIEU_XUAT_KHO;3:CHUNG_THU_CHAT_LUONG;4:BB_GIAO_NHAN_HANG_HOA;5:BB_LAY_MAU` | check_composite |
| `87c88bf6d0f1` | thư mục "thanh lý hợp đồng" | 5 | `1-2:BB_GIAO_NHAN_HANG_HOA;3-5:BB_THANH_LY_HD` | check_composite |
| `57374da27cae` | thư mục "hợp đồng vận chuyển" | 4 | `1-2:HD_VAN_CHUYEN;3-4:GCN_DKDN` | check_composite |
| `9c00a14eed6b` | thư mục "phiếu xuất kho mua hàng 2026" (tên tệp là ngày và số thứ tự) | 4 | `1:PHIEU_XUAT_KHO;2:BB_GIAO_NHAN_HANG_HOA;3:BB_LAY_MAU;4:CHUNG_THU_CHAT_LUONG` | agreed |
| `11133174f271` | cùng thư mục trên | 4 | như trên | agreed |
| `3a74922446fc` | cùng thư mục trên | 4 | như trên | agreed |
| `129e563d2196` | cùng thư mục trên | 4 | như trên | agreed |
| `98d9bec84dcc` | cùng thư mục trên | 4 | như trên | agreed |

Hai điều rút ra: (1) **thứ tự loại khác nhau giữa các bộ** (tệp `9f4c4dae0c73`: phiếu, chứng thư, giao nhận, lấy mẫu; 5 tệp năm 2026: phiếu, giao nhận, lấy mẫu, chứng thư) nên không thể dựa vào thứ tự cố định; (2) tệp `87c88bf6d0f1` mang nhãn chính `BB_GIAO_NHAN_HANG_HOA` (segment đầu) dù nằm trong thư mục "thanh lý hợp đồng" của công ty.

### 13 tệp composite cùng loại

| Loại | Số tệp | Số trang mỗi tệp |
|---|---|---|
| `BB_LAY_MAU` | 7 | 93, 2, 6, 10, 2, 3, 9 (mỗi trang một biên bản) |
| `BIEN_NHAN_THE_CHAP_PT` | 2 | 2, 2 (một giấy cho đầu kéo, một cho rơ moóc) |
| `HOA_DON` | 1 | 4 (hai hóa đơn, mỗi hóa đơn 2 trang) |
| `CC_NGHIEP_VU_BVMT` | 1 | 4 (hai người, mỗi người bìa + mặt trong) |
| `GCN_KIEM_DINH_DO_LUONG` | 1 | 3 (ba cột đo) |
| `BB_GIAO_NHAN_HANG_HOA` | 1 | 2 (hai biên bản) |

## 4. Ví dụ: tệp `9f4c4dae0c73` 5 trang

Tệp có `doc_id` `9f4c4dae0c73` (nằm ở gốc `docs/_chot_samples_phanloaitailieu/`; tra đường dẫn trong `data/manifest.csv`) gồm bốn tài liệu: phiếu xuất kho (trang 1–2, trang 2 chỉ có chữ ký), chứng thư chất lượng (3), biên bản giao nhận (4), biên bản lấy mẫu (5). Đầu ra mong muốn của nhóm tách, đúng hợp đồng `SplitResult` (`src/common/contracts.py`):

```text
SplitResult(source_file="<tên tệp 9f4c4dae0c73>.pdf", total_pages=5, slices=[
  DocumentSlice(slice_id="slice_001", start_page=1, end_page=2, page_count=2, boundary_method=..., ...),
  DocumentSlice(slice_id="slice_002", start_page=3, end_page=3, page_count=1, ...),
  DocumentSlice(slice_id="slice_003", start_page=4, end_page=4, page_count=1, ...),
  DocumentSlice(slice_id="slice_004", start_page=5, end_page=5, page_count=1, ...)])
```

`DocumentSlice` **không** chứa loại tài liệu: loại do nhóm phân loại trả về trong `ClassificationResult` (`predicted_category` = id taxonomy; ở đây lần lượt `PHIEU_XUAT_KHO`, `CHUNG_THU_CHAT_LUONG`, `BB_GIAO_NHAN_HANG_HOA`, `BB_LAY_MAU`). Trường `boundary_confidence` của bộ luật (`rule`, `rule_v2`) là hằng số 0,95, không phải xác suất; của phương pháp `model` là điểm thô của bộ phân loại cặp trang (chưa hiệu chỉnh, chưa đo ECE), cũng không được đọc như xác suất. `boundary_method` ghi đúng phương pháp đã chạy (`rule`, `rule_v2`, `model`, `none`, thêm hậu tố `+type_merge` khi đã gộp).

## 5. Dấu hiệu gợi ý ranh giới (có phản ví dụ; hiệu quả của các luật dùng chúng đã đo ở mục 6)

| Dấu hiệu | Gợi ý trang mở đầu | Phản ví dụ thật trong kho |
|---|---|---|
| Quốc hiệu, tiêu ngữ ở đầu trang | Có | Chưa có số liệu về tần suất quốc hiệu ở trang đầu so với trang tiếp nối; bộ luật hiện có coi quốc hiệu ở **bất kỳ đâu** trong trang là ranh giới |
| Tiêu đề in hoa lớn ở 1/3 trên | Có | Tập PCCC 26–53 trang có hơn 10 tiêu đề con nhưng là một tài liệu; "biên bản nhận bồn/trả bồn" có tiêu đề riêng nhưng thuộc hợp đồng mượn bồn; trang 2/2 của ví dụ chuẩn lặp tiêu đề phiếu (mục 6) |
| Tên đơn vị, logo | Có | Tệp biên bản lấy mẫu: mọi trang giống hệt nhau về bố cục mà mọi trang đều là ranh giới |
| Khối chữ ký, con dấu | Thường ở trang cuối | Trang chỉ có chữ ký thuộc tài liệu trước (hướng dẫn gán nhãn 7.2) |
| Đánh số "1/2", "2/2" | "1/…" là đầu | Chưa có số liệu về tỉ lệ tài liệu có đánh số |
| Loại tài liệu của trang khác loại trang trước | Có | Nhiều bản cùng loại liên tiếp không đổi loại (7 tệp `BB_LAY_MAU`, 13 tệp cùng loại nói chung) |

Tần suất của từng dấu hiệu riêng lẻ chưa được thống kê; cái đã đo là hiệu quả của các bộ tách dùng chúng (mục 6). Kết luận từ đó: bộ tách **phải biết loại tài liệu** (gộp lát cắt liền kề cùng loại là hiệu chỉnh có ích nhất ở cấp tệp) và phải có dấu hiệu "bản khác" (số, ngày, biển số, họ tên) cho trường hợp cùng loại; nhóm cùng loại ngoài biên bản lấy mẫu vẫn là chỗ chưa phương pháp nào xử lý được.

## 6. Kết quả đo và kết luận

Nguồn: [README nhóm 2, mục "Đã đo"](../teams/team2_splitting/README.md) và năm báo cáo `experiments/01_rule_baseline` … `05_llm_zero_shot`; toàn trình: [`01_end_to_end/RESULTS.md`](../teams/00_data_and_eval/experiments/01_end_to_end/RESULTS.md). "Dev" của riêng bài toán tách = 174 tệp: 155 tệp nhiều trang không ghép (mẫu âm) và 19 tệp ghép (8 khác loại, 6 cùng loại ngoài `BB_LAY_MAU`, 5 `BB_LAY_MAU`); 2 tệp ghép còn lại (`BB_LAY_MAU`) nằm trong TEST. Đáp án ranh giới là bản máy, văn bản `data/ocr_v2.jsonl` (tối đa 30 trang mỗi tệp). Số của phương pháp có học là cross-validated (5 fold theo nhóm biểu mẫu), **không** phải tập TEST khóa.

### 6.1. Từng phương pháp đứng riêng (dev)

Mỗi ô: số ranh giới thật bắt được trên tổng, kèm số tách nhầm (FP) và số tệp tách đúng hoàn toàn.

| Nhóm (tệp / ranh giới thật) | luật cũ (01) | luật v2 (02) | chỉ đổi loại (03, b0) | b0 + "bản khác" (03, b1) | logistic (04, c1) | **boosting (04, c2)** |
|---|---|---|---|---|---|---|
| composite khác loại (8 / 20) | 19, FP 2; 5/8 tệp | 19, FP 0; 7/8 | 13, FP 0; 1/8 | 14, FP 0; 2/8 | 20, FP 0; 8/8 | **20, FP 0; 8/8** |
| cùng loại ngoài `BB_LAY_MAU` (6 / 7) | 4, FP 2; 2/6 | 4, FP 1; 2/6 | 0, FP 0; 0/6 | 2, FP 1; 1/6 | 2, FP 2; 1/6 | **3, FP 2; 2/6** |
| `BB_LAY_MAU` (5 / 46) | 46, FP 0; 5/5 | 46, FP 0; 5/5 | 0; 0/5 | 38; 1/5 | 41; 2/5 | **44; 4/5** |
| mẫu âm (155 tệp nhiều trang không ghép, 501 vị trí): tách nhầm trên 100 vị trí | 46,7 [41,4; 52,8] | 30,1 [23,4; 36,4] | 1,0 [0,1; 2,2] | 27,7 [21,8; 33,5] | 12,6 [9,6; 16,5] | **9,6 [6,3; 12,7]** |
| mẫu âm: số tệp còn nguyên | 50/155 | 85/155 | 151/155 | 89/155 | 107/155 | **129/155** |

Cách đọc:

1. **Chênh lệch thật nằm ở mẫu âm**, tức tài liệu nhiều trang *không* ghép, nơi tách nhầm làm cắt vụn một tệp vốn đúng. Bộ phân loại cặp trang (c2) so với luật cũ: −37,1 điểm [−43,9; −32,0]; so với luật v2: −20,6 [−25,9; −15,5]; cả hai đều "tách được". Lỗi của luật cũ: 238 lần tách nhầm, đông nhất là trang có "CỘNG HÒA XÃ HỘI" ở bất kỳ đâu trong các tập hồ sơ PCCC dài (80 lần) và tiêu đề "GIẤY CHỨNG NHẬN" hay "HỢP ĐỒNG" trong 6 dòng đầu của trang tiếp nối.
2. **Ở ba nhóm ghép, hầu hết các cặp phương pháp "không tách được"** (8, 6, 5 tệp). Ngoại lệ: "chỉ đổi loại" (b0) và b1 kém hơn luật cũ ở `BB_LAY_MAU` vì sót ranh giới, và b0 cũng kém ở hai nhóm kia.
3. **Nhóm cùng loại ngoài `BB_LAY_MAU`** (hai biên nhận thế chấp, một hóa đơn hai bản…) là chỗ chưa phương pháp nào xử lý được: tối đa 4/7 ranh giới.
4. **Ngưỡng của c2 là đánh đổi vận hành.** Ngưỡng 0,5 (mặc định của mô hình): tách nhầm 9,58 trên 100 vị trí. Ngưỡng 0,7: 5,19 (139/155 tệp nguyên) nhưng `BB_LAY_MAU` còn 40/46; ngưỡng 0,9: 2,20 (145/155) nhưng chỉ 12/46. Chọn cắt vụn hay dính hai giấy đắt hơn là quyết định của doanh nghiệp.
5. **Qwen3.5-4B hỏi có/không** (zero-shot, một prompt, 19 tệp ghép + 20 tệp âm) gần như không bao giờ nói "tài liệu mới": 0/20, 0/7, 1/46 ranh giới. Có thể do prompt chứ không do mô hình; prompt thứ hai chưa chạy xong, nên **chưa có bằng chứng về giới hạn của hướng zero-shot nói chung**. Kev `Noul` chưa thử.
6. **Tài liệu TEST** (2 tệp `BB_LAY_MAU` và 36 tệp âm, chấm một lần với cấu hình đã đóng băng): c2 bắt 9/9 ranh giới, 5 tách nhầm trên 74 vị trí âm (6,76 trên 100 [2,27; 13,46]), 31/36 tệp nguyên vẹn. Cỡ mẫu rất nhỏ.

### 6.2. Ví dụ chuẩn 5 trang

Chạy trên `MOCK_OCR_DOCUMENT_BSR` (`tests/fixtures/sample_pipeline_fixtures.py`, đáp án đúng `1-2, 3, 4, 5`) cho kết quả quan sát: `rule` cho **5 lát** `(1,1) (2,2) (3,3) (4,4) (5,5)` vì trang chữ ký 2/2 lặp dòng tiêu đề phiếu; `rule_v2` và `model` cho đúng **4 lát** `(1,2) (3,3) (4,4) (5,5)`. Lệnh: `.venv\Scripts\python.exe -X utf8 -c "from src.splitting.boundary_detector import split_document; from tests.fixtures.sample_pipeline_fixtures import MOCK_OCR_DOCUMENT_BSR as d; [print(m, [(s.start_page, s.end_page) for s in split_document(d, m).slices]) for m in ('rule', 'rule_v2', 'model')]"`.

### 6.3. Kết luận toàn trình: tách có đáng không?

Câu hỏi khác với 6.1: trong hệ thống thật, khoảng 92% tệp là tài liệu đơn hoặc nhiều trang không ghép, và composite chỉ khoảng 7%. Phép đo toàn trình nối tách trang với cascade phân loại và chấm theo **tệp** (dev 245 tệp; TEST 59 tệp, chấm một lần; đáp án ranh giới vẫn là bản máy):

| | không tách | luật cũ | luật v2 | bộ phân loại cặp trang, ngưỡng 0,5 | **`model+merge` (mặc định)** | `triage` |
|---|---|---|---|---|---|---|
| Tệp đúng hoàn toàn, dev | 92,3% [91,0%; 93,1%] | 53,4% | 67,5% | 84,9% | **91,9% [89,2%; 94,4%]** | 92,3% |
| Tệp nhiều trang bị làm hỏng so với không tách (trên 155) | 0 | 104 | 70 | 26 | 6 | 0 |
| Tài liệu đáp án giao đúng và tự động, dev (trên 318) | 224 (70,4%) | 195 (61,3%) | 232 (73,0%) | 273 (85,8%) | **279 (87,7%)** | 185 (58,2%) |
| Trong đó thuộc tệp ghép (trên 92) | 0 | 75 | 78 | 75 | 61 | 0 |
| Sai lặng lẽ, trên tổng số tệp dev | 7,31% | 39,37% | 28,42% | 11,53% | 4,94% | 1,45% |

Bốn kết luận:

1. **Tách trang không làm tăng tỉ lệ tệp đúng hoàn toàn.** Biến thể tốt nhất chỉ ngang không tách (`model+merge` so với không tách: −0,4 điểm, khoảng ghép cặp [−2,9; +1,9] chứa 0: "không tách được"). Lý do: mọi lần cắt nhầm một tệp thường là làm hỏng một tệp đã đúng; luật cũ hỏng 104/155 tệp nhiều trang, luật v2 70/155. Trên TEST, `model+merge` và không tách cùng 56/59 tệp đúng (hiệu −1,2 điểm [−6,7; +2,4]).
2. **Tách trang có lợi ở cấp tài liệu và giảm sai lặng lẽ.** Dev: giao đúng và tự động 87,7% [83,2%; 92,6%] tài liệu đáp án so với 70,4% [56,3%; 84,7%] khi không tách; trong 92 tài liệu thuộc tệp ghép, không tách giao đúng 0 và `model+merge` giao đúng 61. Sai lặng lẽ giảm từ 7,31% xuống 4,94% tổng số tệp. TEST: 65/68 so với 56/68 tài liệu; nhưng TEST chỉ có 2 tệp ghép, cả hai là `BB_LAY_MAU`, nên **không nói được gì** về tệp ghép khác loại.
3. **Mặc định của pipeline là `model+merge`**: bộ phân loại cặp trang ngưỡng 0,7, rồi gộp lát cắt liền kề được phân loại cùng loại (trừ `BB_LAY_MAU`, và trừ ranh giới điểm ≥ 0,99). Chọn trên dev bằng một quy tắc đặt **sau khi xem số dev** (mục tiêu ban đầu "sai lặng lẽ ≤ 1%" không biến thể nào đạt), nên tham số lạc quan. Nếu doanh nghiệp coi sai lặng lẽ đắt hơn nhân sự duyệt, chế độ `triage` là phương án thay thế: không tách, chuyển người tệp nghi là ghép; dev: 22% tệp về người, sai lặng lẽ 1,45% tổng số tệp (1,86% trong phần tự xử lý), nhưng chỉ giao đúng 58,2% tài liệu và vẫn **không đạt ≤ 1%**.
4. **Với tệp ghép khác loại, điểm nghẽn là phân loại lát cắt, không phải tách.** Khi tách đúng tuyệt đối (8/8 tệp), chỉ 2/8 tệp có mọi tài liệu đúng loại: trong 7 trang biên bản giao nhận của các bộ chứng từ này, bộ phân loại gán `PHIEU_XUAT_KHO` 6 lần. Đây là kết quả trên **8 tệp thuộc vài bộ chứng từ cùng dạng của một nhà cung cấp**, nên là giả thuyết cần kiểm bằng thêm mẫu; muốn xử lý tốt bộ chứng từ cần thêm luật hoặc ví dụ cho `BB_GIAO_NHAN_HANG_HOA` so với `PHIEU_XUAT_KHO`.

Chi phí của tách rất nhỏ so với phần còn lại: tách bằng mô hình cặp trang trung vị 28 ms mỗi tệp; số lời gọi LLM phân loại mỗi tệp là 0,06 khi không tách, 0,14 với `model+merge`, 0,45 với luật cũ (vì luật cũ tạo nhiều lát cắt). Chi tiết: [`VISUAL_ARCHITECTURE.md`](VISUAL_ARCHITECTURE.md) mục 6.

### 6.4. Giới hạn của các kết luận trên

- Đáp án ranh giới là bản máy (một mô hình xem đủ trang), chưa người kiểm; 5 tệp `check_composite` rủi ro cao nhất; chưa ai lật xem 191 tệp "không composite" để bắt tệp ghép bị sót.
- Chỉ có 19 tệp ghép ở dev (8 khác loại, 6 cùng loại ngoài `BB_LAY_MAU`, 5 `BB_LAY_MAU`) và 2 ở TEST; chỉ 27 ranh giới ngoài `BB_LAY_MAU`. Khoảng bootstrap "toàn bộ" hẹp giả khi nhóm ghép quan sát 0/n (cận trên Clopper-Pearson của nhóm có thể tới 37–52%); chênh dưới 10–15 điểm giữa hai phương pháp ở nhóm ghép không tách được.
- Các bộ chứng từ khác loại thuộc cùng một nhà cung cấp: kết quả tốt có thể là nhớ bố cục.
- Văn bản chỉ tới trang 30: tệp 93 trang chỉ chấm 29–30 vị trí đầu (63/92 ranh giới của nó chưa được chấm); trong pipeline, tệp > 30 trang nay chuyển người thay vì cắt âm thầm.
- Phép đo toàn trình dùng văn bản OCR có sẵn, không đo lại OCR; độ trễ đo khi GPU và Ollama dùng chung.

### 6.5. Giai đoạn 3: nhóm cùng loại, biên bản trong tệp ghép, tệp dài

Nguồn: [`06_same_type`](../teams/team2_splitting/experiments/06_same_type/RESULTS.md) (nhóm 2), [`05_composite_slices`](../teams/team3_classification/experiments/05_composite_slices/RESULTS.md) (nhóm 3), [`03_end_to_end_v2`](../teams/00_data_and_eval/experiments/03_end_to_end_v2/RESULTS.md) và [báo cáo 04](../teams/00_data_and_eval/reports/04_phase3_review_and_deployment.md) (review). Mọi số trên dev, đáp án máy.

- **Nhiều bản cùng loại trong một tệp** (6 tệp, 7 ranh giới ngoài `BB_LAY_MAU`): `model+merge` bắt 0/7 vì bộ gộp cùng loại xóa ranh giới và mô hình cặp trang cho điểm thấp khi hai tờ cùng mẫu. Quy tắc `id` (đầu trang giống nhau, jaccard ≥ 0,7, mà số hiệu "Số ..." ở đầu hai trang khác nhau) thêm ranh giới điểm 1,0: **0/7 → 4/7** (recall +0,571, CI bootstrap theo tệp [0,167; 0,889]; 3/6 tệp đúng hoàn toàn), không đổi ba nhóm còn lại, 0/448 cặp mẫu âm bị kích hoạt. Đặc trưng id trong mô hình cặp trang: 1/7 (không tách được khỏi nền); VLM nhìn hai ảnh: 3/7 nhưng thêm 7 tách nhầm. 3/7 ranh giới còn lại (OCR hỏng, mẫu không có "Số", hai giấy khác mẫu) chưa phương pháp nào bắt được. Quy tắc được nghĩ ra sau khi đọc các tệp này (4 ranh giới bắt được nằm ở 3 tệp) và TEST không có tệp cùng loại ngoài `BB_LAY_MAU`, nên **chưa có kiểm giữ ngoài**.
- **Biên bản giao nhận bị gán `PHIEU_XUAT_KHO`** (mục 6.3, điểm 4) đã được chẩn đoán: cổng luật thấy từ khóa của cả hai loại (tiêu đề "BIÊN BẢN GIAO NHẬN HÀNG" ở ký tự ~180–320, tên cột "Phiếu Xuất kho Thành phẩm" ở ký tự ~830–1000), chuyển xuống TF-IDF, mà ngưỡng TF-IDF dễ nên nhận sai (6/6 lát biên bản một trang). `rule_title_tiebreak` sửa: 28 lát của 8 tệp từ 22/28 lên 28/28 đúng, tệp mà mọi lát đúng 2/8 → 8/8 (đơn vị đúng là tệp: Clopper–Pearson [63%; 100%]); trên 237 tài liệu đơn lẻ của dev đổi tầng ở 25, đổi nhãn 0. Vẫn là **8 tệp của một nhà cung cấp**, 6 trang biên bản gần như giống hệt nhau: sửa đúng thứ đã thấy, không phải bằng chứng tổng quát hóa; nhóm 3 khuyên chưa bật mặc định.
- **Cả chuỗi (S10 → S10+id+tb, 245 tệp dev):** tệp đúng hoàn toàn 223 → 232, lỗi lặng lẽ 14 → 5, tài liệu giao đúng 279 → 293/318; hiệu có trọng số theo cơ cấu tệp +3,0 điểm [+2,0; +3,9]. Cả 9 tệp được sửa đều là composite (3 cùng loại, 6 khác loại); 0 tệp thường bị làm hỏng. TEST (59 tệp) giống hệt S10. Review ghi đó là **mức trần lạc quan**: hai tùy chọn thiết kế trên chính 14 tệp này, CI hẹp vì 14 tệp đổi cùng chiều, không vì nhiều bằng chứng. Do đó mặc định của pipeline **vẫn là `model+merge`**; `id` chạy bóng (không tách, chuyển tệp sang người khi nó muốn thêm ranh giới; dev kích hoạt 3/245 tệp) và `tiebreak` tắt nhưng ghi nhãn bóng. Điều kiện bật tự động: ≥ 30 tệp composite mỗi loại từ ≥ 3 nhà cung cấp chưa từng xem.
- **Tệp trên 30 trang** (6/336 tệp, dài nhất 93 trang): trước đây các trang sau trang 30 bị cắt âm thầm khỏi tách, phân loại và chuyển người. Pipeline nay chuyển cả tệp sang người (lý do `truncated_pages`).

## 7. Các hướng đã thử và còn lại

(Chi tiết, thứ tự ưu tiên và tiêu chí hoàn thành: README nhóm 2.)

| Hướng | Trạng thái |
|---|---|
| Phân loại loại theo **từng trang**, gộp các trang liên tiếp cùng loại; thêm dấu hiệu "bản khác" cho cùng loại | **Đã đo** (b0, b1): kém luật ở composite vì sót ranh giới; nhưng ý tưởng "gộp lát cắt liền kề cùng loại" được dùng lại *sau khi phân loại lát cắt* trong chính sách `model+merge` và có ích (S4 so với S3 trong báo cáo toàn trình: +5,8 điểm [+2,8; +9,0], tách được) |
| Bộ phân loại **cặp trang** (trang i, trang i+1 có ranh giới không) | **Đã đo và đã đưa vào `src/splitting/`** làm phương pháp `model` (mô hình ở `teams/team2_splitting/models/`) |
| Mô hình quyết định Kev (`Noul`, nhị phân) hỏi "trang này có mở tài liệu mới không?" | **Chưa thử.** Thay bằng Qwen3.5-4B qua Ollama: một prompt, gần như không bao giờ tách |
| Composite **tổng hợp** (nối tài liệu đơn) chỉ để huấn luyện/chỉnh tham số | **Đã làm** (`gold/make_synthetic.py`); báo cáo cuối vẫn tính trên composite thật |
| Đánh giá bằng precision/recall/F1 ranh giới, tỉ lệ tệp đúng toàn bộ segment, độ chính xác loại theo segment, báo riêng từng nhóm | **Đã làm**; thêm đo theo tệp và theo tài liệu ở toàn trình |
| Dấu hiệu "bản khác" (quy tắc `id`) cho nhóm cùng loại ngoài `BB_LAY_MAU` | **Đã làm trên dev** (0/7 → 4/7 ranh giới, 6 tệp; mục 6.5), chưa kiểm giữ ngoài; chạy bóng trong pipeline |
| Gỡ mơ hồ biên bản giao nhận / phiếu xuất kho theo tiêu đề (`rule_title_tiebreak`) | **Đã làm trên dev** (28/28 lát, 8 tệp một nhà cung cấp; mục 6.5), tắt mặc định |
| Hiệu chỉnh `boundary_confidence`; bộ chứng từ nhà cung cấp khác (≥ 3 nhà cung cấp, ≥ 30 tệp composite mỗi loại); đáp án ranh giới do người kiểm; đo lại tệp trên 30 trang khi OCR hết | **Còn lại** |

## 8. Câu hỏi còn mở cho doanh nghiệp

Bộ chứng từ một chuyến hàng nên lưu nguyên bộ hay tách (câu 9)? Biên bản lấy mẫu có cần từng biên bản một bản ghi (câu 14)? Biên bản trả bồn ký sẵn nhưng để trống ngày hiểu thế nào (câu 15)? Thêm một quyết định đã nảy sinh từ phép đo toàn trình: sai lặng lẽ (tệp được xử lý tự động nhưng sai) đắt hơn hay công người duyệt đắt hơn? Câu trả lời quyết định chọn `model+merge` hay `triage` (mục 6.3). Danh sách đầy đủ 17 câu: [`teams/00_data_and_eval/README.md`](../teams/00_data_and_eval/README.md).
