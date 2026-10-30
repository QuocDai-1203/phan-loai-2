# Nhóm 00 — Dữ liệu và đánh giá

## Mục tiêu (doanh nghiệp nhận được gì)

1. Một **bộ mẫu có nhãn đáng tin**: mỗi tài liệu được ghi đúng *loại theo nội dung*, được nhân viên công ty xác nhận. Không có nó thì không ai biết hệ thống đúng hay sai.
2. Một **bộ chấm điểm trung thực**: cùng một cách chia dữ liệu, cùng một cách tính, để so sánh các phương pháp mà không tự lừa mình (không rò rỉ, TEST khóa, có khoảng tin cậy).
3. **Danh sách quyết định nghiệp vụ** mà chỉ công ty trả lời được (giữ giấy nào, lưu ở đâu, nhắc hạn nào, được lưu dữ liệu cá nhân nào) — và câu trả lời được ghi lại thành thay đổi taxonomy.
4. Quy tắc **quản trị dữ liệu**: ai được thấy gì, cái gì được gửi ra ngoài.

## Hiện trạng

### Đã làm và đo được (ngày 2026-10-11)

| Hạng mục | Kết quả | Nguồn |
|---|---|---|
| Kho mẫu | 336 PDF → **304 tài liệu duy nhất**; 30 nhóm trùng byte (62 tệp), 27 nhóm nằm ở ≥ 2 thư mục khác nhau; 39 nhóm cùng biểu mẫu (161 tài liệu); 304/336 tệp là bản quét | [`reports/01_duplicates.md`](reports/01_duplicates.md) |
| Taxonomy v2 | 36 mục: 34 loại nội dung trong 8 nhóm + `OTHER` + `UNREADABLE`; 25 quy tắc định tuyến "loại + thực thể → thư mục"; 17 câu hỏi mở cho doanh nghiệp | [`data/taxonomy_v2.json`](../../data/taxonomy_v2.json), [`reports/02_taxonomy_design.md`](reports/02_taxonomy_design.md) |
| Hướng dẫn gán nhãn | v1.1: 5 nguyên tắc, quy trình 9 bước, phép thử "kèm theo", 14 ví dụ có lời giải, nhật ký thay đổi | [`docs/LABELING_GUIDELINE.md`](../../docs/LABELING_GUIDELINE.md) |
| Nhãn | `data/labels_v2.csv`: hai annotator **đều là mô hình AI** gán độc lập; `doc_type` trùng 304/304, Cohen κ = 1,0; composite κ = 0,86 (16 tệp cả hai đánh dấu, 5 tệp chỉ A). Trạng thái: 296 `agreed`, 5 `check_composite`, 3 `check_low_conf` | [`annotation/agreement_summary.json`](annotation/agreement_summary.json) |
| Phân bố nhãn | 10 loại có ≥ 10 tài liệu (230 tài liệu); 24 loại (kể cả `OTHER`) có 1–9 tài liệu, tổng 74. 21 tệp composite: 8 khác loại, 13 cùng loại | tính từ `data/labels_v2.csv` (tài liệu duy nhất) |
| Chia dữ liệu | DEV 237, TEST khóa 59, 8 composite hỗn hợp bị loại; tất định; ghi `labels_sha1_10` = `eb3348713a` | [`data/splits/README.md`](../../data/splits/README.md), `data/splits/splits_meta.json` |
| Bộ chấm | `eval/harness.py`, `eval/eval_metrics.py`, `eval/eval_splits.py`; 33 test qua (lần chạy 2026-10-16: `pytest teams/00_data_and_eval/tests -q`) | [`reports/03_evaluation_protocol.md`](reports/03_evaluation_protocol.md) |
| Thí nghiệm end-to-end (CP3) | [`experiments/01_end_to_end/`](experiments/01_end_to_end/RESULTS.md): tách trang + phân loại đo theo **tệp** trên 245 tệp dev, 11 biến thể, chấm TEST một lần (59 tệp). Kết luận: tách **không** tăng tỉ lệ tệp đúng hoàn toàn so với không tách (92,3% vs 91,9%, không tách được) nhưng giao thêm tài liệu của tệp ghép (+17 điểm ở cấp tài liệu) và giảm sai lặng lẽ; luật cũ/v2 làm hại tệp thường. Mặc định pipeline = `model+merge`; kèm chuỗi tới ngày hết hạn (82 đơn vị dev) và nguyên nhân lần chạy 195 s. Đáp án ranh giới là bản máy, composite chỉ 19 tệp dev | `experiments/01_end_to_end/{run.py,RESULTS.md,dev_selection.json}` |
| Chuỗi tới ngày hết hạn có ảnh trang (02) | [`experiments/02_chain_with_images/`](experiments/02_chain_with_images/RESULTS.md): pipeline dựng ảnh trang cho VLM (mặc định bật, `--no-vlm` để tắt); 82 đơn vị dev, 66 trường hạn: tự nhận đúng 37/66 (56,1%) so với 32/66 (48,5%) không ảnh, sai 0, hiệu +7,5 điểm CI95 [+1,5; +15,2] nhưng kiểm định dấu p = 0,0625 (biên); thêm ~4 s dựng ảnh + ~15 s VLM/lát cắt (GPU dùng chung). Đáp án máy, chỉ DEV. | [`RESULTS.md`](experiments/02_chain_with_images/RESULTS.md) |
| Toàn trình v2 (03) | [`experiments/03_end_to_end_v2/`](experiments/03_end_to_end_v2/RESULTS.md): S10 so với S10 + quy tắc "bản khác" (id) + gỡ mơ hồ theo tiêu đề (tiebreak) trên 245 tệp dev: tệp đúng hoàn toàn 223 -> 232, sai lặng lẽ 14 -> 5, tài liệu giao đúng 279 -> 293/318, 0 tệp hỏng (hiệu +3,0 điểm, CI [+2,0; +3,9], nhưng hai tùy chọn được nghĩ ra từ chính các tệp composite này nên là mức trần). TEST (lần hai, 59 tệp): giống hệt S10, chỉ kiểm được "không hại". **Mặc định pipeline (cập nhật theo báo cáo review 04, N1): `model+merge` (S10), tiebreak TẮT, không tự nhận ngày hết hạn**; `id` và `tiebreak` chạy ở chế độ bóng (ghi quyết định, `id` chỉ chuyển người), bật lại bằng `--splitter model+merge+id` / `--title-tiebreak`. Dựng ảnh VLM nhanh hơn 4 lần (3,6 s -> 0,9 s, cùng điểm ảnh; khóa cache VLM theo điểm ảnh). Chi phí có OCR thật (30 tệp, 90 trang): trung vị 32,6 s/tệp, ước lượng ~500 trang/giờ/RTX 3060, VRAM đỉnh 6,6 GiB (GPU dùng chung). | [`RESULTS.md`](experiments/03_end_to_end_v2/RESULTS.md) |
| Review độc lập giai đoạn 3 và thiết kế triển khai (2026-10-16) | [`reports/04_phase3_review_and_deployment.md`](reports/04_phase3_review_and_deployment.md): tính lại được mọi số chính (CPU, không gọi mô hình); 4 phát hiện nghiêm trọng (đổi mặc định bằng bằng chứng trong mẫu thiết kế, tự nhận hạn dựa vào tên tệp, `regex=llm` làm quy tắc tự nhận cho 17 loại mới, dữ liệu thật trong git và đã qua mô hình đám mây), 10 phát hiện trung bình (kiểm mẫu băm theo `slice_id`, tệp > 30 trang bị cắt, VLM gọi thừa, TEST đã mòn...); kiến trúc chạy thật, cấu hình khuyến nghị, chi phí 1–3 máy cho 500/2.000/10.000 trang/ngày (chưa đo trên máy riêng), kế hoạch chạy bóng 6–8 tuần (≥ 299 tệp tự xử lý liên tiếp không lỗi), 15 việc ưu tiên. Các mặc định trong mã đã đổi theo báo cáo này. | [`reports/04_phase3_review_and_deployment.md`](reports/04_phase3_review_and_deployment.md) |
| Bộ mẫu đã xếp đúng loại | `data/classified_v2/` kèm `INDEX.csv`; `_CAN_KIEM_TRA/` (3 tài liệu), `_COMPOSITE_KHAC_LOAI/` (8 tệp) | [`data/classified_v2/README.md`](../../data/classified_v2/README.md) |

### Chưa đo / chưa làm

- **Chưa có người của công ty nào xác nhận nhãn.** κ = 1,0 giữa hai mô hình cùng họ, cùng hướng dẫn **không** chứng minh nhãn đúng. Annotator A đồng thời là người thiết kế taxonomy, xem ảnh trang; annotator B chỉ đọc văn bản 2 trang đầu. Tỉ lệ nhãn sai so với nhân viên công ty: **chưa đo**.
- Mức đồng thuận giữa hai **người** thật: chưa đo.
- 17 câu hỏi nghiệp vụ: chưa có câu trả lời nào.
- 24 loại có dưới 10 tài liệu chưa đủ để huấn luyện hay chấm riêng từng loại; hai loại lớn (`CC_TAP_HUAN_VC_HNH`, `PHIEU_XUAT_KHO`) gần như chỉ có **một biểu mẫu** — chia nghiêm ngặt theo biểu mẫu làm recall của chúng rơi về 0,05 và 0,00 (xem mục 8 của [`01_classical_baselines/RESULTS.md`](../team3_classification/experiments/01_classical_baselines/RESULTS.md)), tức là khả năng tổng quát hóa sang biểu mẫu mới **chưa được chứng minh**.
- Chia dữ liệu đã được đóng băng trong harness (sửa nhãn không làm tài liệu đổi tập); phần còn thiếu là chỗ đặt tài liệu **mới** (xem việc T5).

## Việc cần làm (theo thứ tự ưu tiên)

Công sức ghi là **ước lượng của người viết kế hoạch**, không phải số đo.

### T1 (P0) — Nhân viên công ty kiểm nhãn

- **Vì sao:** mọi con số của cả dự án đều tính trên nhãn này. Nhãn sai có hệ thống làm mọi kết quả vô nghĩa mà không ai thấy.
- **Các bước:**
  1. Lập phiếu kiểm bằng đoạn mã dưới (13 tài liệu bắt buộc + 30 tài liệu ngẫu nhiên = 43 dòng). Thứ tự bắt buộc: (a) 3 tài liệu ở `data/classified_v2/_CAN_KIEM_TRA/`; (b) 5 tệp `check_composite`; (c) 8 tệp composite khác loại ở `_COMPOSITE_KHAC_LOAI/` (trùng một phần với (b)); (d) mẫu ngẫu nhiên 10% của phần còn lại.
  2. Nhân viên mở PDF theo cột `classified_path`, điền `staff_doc_type`, `staff_is_composite`, `staff_segments`, `staff_comment`. Chỉ máy nội bộ.
  3. Mỗi dòng nhân viên khác nhãn máy: thêm một dòng vào `annotation/adjudication.csv` (cột `doc_id, doc_type, is_composite, segments, note`; dùng `doc_id` của bản **đại diện**, tức dòng có `is_duplicate_of` rỗng). Tệp này chưa tồn tại, tạo mới.
  4. Chạy lại `scripts\build_labels_v2.py`, rồi `scripts\build_classified_folder.py` (xem mục Cách chạy). Dòng được phân xử có `review_status = adjudicated`.
  5. Viết `reports/04_label_audit.md`: số tài liệu đã kiểm, số tài liệu bị sửa (theo loại và nhóm), tỉ lệ sai kèm khoảng tin cậy 95% (Clopper–Pearson). **Đọc số cẩn thận:** 0 lỗi trên 30 tài liệu ngẫu nhiên chỉ cho cận trên ~10% (quy tắc ba, 3/n). Nếu có ≥ 1 lỗi, mở rộng kiểm sang toàn bộ 24 loại hiếm (74 tài liệu).
- **Bắt đầu từ:**

```python
# chạy từ gốc repo:  .venv\Scripts\python.exe -X utf8 -
import pandas as pd
lab = pd.read_csv("data/labels_v2.csv", dtype=str, keep_default_na=False)
idx = pd.read_csv("data/classified_v2/INDEX.csv", dtype=str, keep_default_na=False)
u = lab[lab.is_duplicate_of == ""]                                  # 304 tài liệu duy nhất
must = u[(u.review_status != "agreed") | (u.composite_mixed == "1")]  # 13 dòng
audit = u.drop(must.index).sample(n=round(0.10 * len(u)), random_state=42)  # 30 dòng
sheet = pd.concat([must.assign(why="bat_buoc"), audit.assign(why="ngau_nhien_10pct")])
sheet = sheet.merge(idx[["doc_id", "classified_path", "page_count"]], on="doc_id", how="left")
for c in ("staff_doc_type", "staff_is_composite", "staff_segments", "staff_comment"):
    sheet[c] = ""
sheet[["doc_id", "classified_path", "page_count", "why", "doc_type", "is_composite", "segments", "evidence",
       "staff_doc_type", "staff_is_composite", "staff_segments", "staff_comment"]].to_csv(
    "teams/00_data_and_eval/annotation/review_sheet.csv", index=False, encoding="utf-8-sig")
```
- **Sản phẩm:** `annotation/review_sheet.csv` (đã điền), `annotation/adjudication.csv`, `data/labels_v2.csv` mới, `reports/04_label_audit.md`.
- **Xong khi:** mọi dòng của phiếu có `staff_doc_type`; `build_labels_v2.py` thoát mã 0; báo cáo kiểm nêu số sửa và khoảng tin cậy.
- **Công sức (ước lượng):** nhân viên công ty 0,5–1 ngày cho 43 tài liệu (tệp 93 trang chỉ cần lướt); sinh viên 0,5 ngày để chuẩn bị và nhập.
- **Điều kiện tiên quyết:** người của công ty có thời gian; trước khi sửa nhãn, báo cho các nhóm (đặc biệt nhóm 3 đang chạy thí nghiệm) rằng `labels_sha1_10` sẽ đổi.

### T2 (P0) — Lấy câu trả lời cho 17 câu hỏi nghiệp vụ

- **Vì sao:** một số quyết định đổi hẳn taxonomy hoặc phạm vi (ví dụ có lưu số căn cước vào ERP không; mỗi biên bản lấy mẫu là một bản ghi hay cả tập là một bản ghi).
- **Các bước:** (1) gửi danh sách ở mục "Câu hỏi cần hỏi doanh nghiệp" cho người phụ trách; (2) họp 60 phút, ghi câu trả lời vào `reports/05_business_answers.md` (mỗi câu: câu trả lời, ai trả lời, ngày, nhóm nào bị ảnh hưởng); (3) với từng câu, sửa taxonomy/hướng dẫn nếu cần, tăng `version` và ghi nhật ký ở mục 11 của hướng dẫn gán nhãn; (4) báo nhóm bị ảnh hưởng.
- **Bắt đầu từ:** [`reports/02_taxonomy_design.md`](reports/02_taxonomy_design.md), mục 9 (nguyên văn 17 câu).
- **Sản phẩm:** `reports/05_business_answers.md`; taxonomy/hướng dẫn cập nhật nếu có.
- **Xong khi:** mỗi câu có câu trả lời hoặc ghi "công ty chưa quyết, người chịu trách nhiệm: …". Câu 11, 12, 13, 14 (hạn, dữ liệu cá nhân, mức chi tiết) chặn nhóm 4; câu 9, 14, 15 chặn nhóm 2.
- **Công sức (ước lượng):** 0,5 ngày chuẩn bị, 1 buổi họp, 0,5 ngày ghi kết quả; thời gian chờ phụ thuộc công ty.

### T3 (P1) — Thu thêm mẫu

- **Vì sao:** 24 loại có dưới 10 tài liệu không thể huấn luyện hay chấm riêng; hai loại lớn chỉ có một biểu mẫu nên chưa biết hệ thống có đọc được biểu mẫu mới không.
- **Các bước:**
  1. Xin công ty thêm mẫu, ưu tiên 11 loại ghi ở mục 7.7 của báo cáo 02 (`GCN_BAO_HIEM`, `GPLX`, `DANG_KY_PHUONG_TIEN`, `GCN_ATKT_BVMT_PT`, `GP_VC_HANG_NGUY_HIEM`, `GCN_KIEM_DINH_DO_LUONG`, `CC_HUAN_LUYEN_PCCC`, `CC_NGHIEP_VU_BVMT`, `HD_NHUONG_QUYEN_DAI_LY`, `HD_MUON_BON`, `HO_SO_QUAN_LY_PCCC`). Mục tiêu của báo cáo đó là ≥ 20 tài liệu duy nhất mỗi loại, từ nhiều xe, cửa hàng, năm khác nhau; so với số hiện có trong `labels_v2.csv` là thiếu **169 tài liệu** cho 11 loại này (tính bằng 20 trừ số hiện có, cộng lại).
  2. Xin riêng **biểu mẫu mới** cho `CC_TAP_HUAN_VC_HNH` (đơn vị tập huấn khác) và `PHIEU_XUAT_KHO` (nhà cung cấp/kho khác). Đây là bộ kiểm tra "biểu mẫu chưa từng thấy".
  3. Đặt vào thư mục mẫu mới, chạy `scripts\build_manifest.py` để lấy `doc_id` và phát hiện trùng; gán nhãn bằng hướng dẫn v1.1 (ít nhất một người thật gán).
  4. **Không** xáo lại chia cũ: tài liệu mới vào một tập riêng `NEW_*` (xem T5); riêng biểu mẫu mới của hai loại lớn giữ làm tập kiểm tra, không dùng để huấn luyện.
- **Bắt đầu từ:** `data/labels_v2.csv` (cột `doc_type`), `data/manifest.csv`.
- **Sản phẩm:** thư mục mẫu mới (kho riêng), nhãn mới, `reports/06_new_samples.md` (bao nhiêu tài liệu, loại nào, trùng bao nhiêu).
- **Xong khi:** mỗi loại ưu tiên có số tài liệu duy nhất mới ghi trong báo cáo; hai biểu mẫu mới đã vào tập kiểm tra.
- **Công sức (ước lượng):** phần lớn là chờ công ty; xử lý phía sinh viên 1–2 ngày mỗi đợt.
- **Điều kiện tiên quyết:** chủ dự án đồng ý cho mẫu mới được gửi ra LLM ngoài hay không (hiện chỉ **bộ mẫu này** được phép).

### T4 (P1) — Áp dụng hướng dẫn v1.1 và đóng các lỗ hổng còn lại

- **Vì sao:** annotator đã báo những chỗ mơ hồ; v1.1 đã làm rõ trên giấy, nhưng nhãn chưa được rà lại theo bản mới.
- **Các bước:** (1) rà các loại ghi ở cột "Tệp cần rà lại" của nhật ký v1.1 (`HD_MUA_BAN`, `BB_THANH_LY_HD`, `CC_TAP_HUAN_VC_HNH`, `GCN_BAO_HIEM`, `DANG_KY_PHUONG_TIEN`, `GCN_DDK_BAN_LE_XD`, `GCN_PCCC_CO_SO`, `HO_SO_QUAN_LY_PCCC`, `DON_DAT_HANG`, `CONG_VAN_THONG_BAO`, `PHIEU_XUAT_KHO`, `GCN_DKDN`) bằng cách gán lại độc lập (người thứ ba, đủ trang) rồi đối chiếu; (2) chạy lại `annotation\agreement.py` và báo cáo cả κ **loại trừ tệp nêu tên trong hướng dẫn** (hiện: 228 tài liệu, agree 1,0); (3) gom ghi chú `GUIDE:` và "ranh giới?" trong các tệp nhãn để sửa tiếp hướng dẫn; (4) viết quy tắc cho trường hợp còn trống: hai tài liệu **khác loại** dùng chung một trang.
- **Sản phẩm:** hướng dẫn v1.2 nếu cần, nhật ký cập nhật, `reports/04_label_audit.md` bổ sung.
- **Xong khi:** các loại bị ảnh hưởng đã được gán lại độc lập và κ (cả hai cách tính) được báo cáo; không còn `GUIDE:` chưa xử lý.
- **Công sức (ước lượng):** 1–2 ngày.

### T5 (P1) — Hoàn tất việc đóng băng chia DEV/TEST

- **Đã làm (có test):** `load_or_make_splits` chỉ đọc `data/splits/` khi thư mục đã có. Các tệp chia không chứa nhãn, nên sửa nhãn **không** làm tài liệu đổi tập hay đổi fold; harness chỉ cảnh báo rằng sha nhãn đã khác lúc chia. Tài liệu được sửa thành "ghép khác loại" bị loại khỏi benchmark dù tệp chia vẫn ghi DEV/TEST. Nếu benchmark có tài liệu chưa được gán tập (tài liệu mới, hoặc tệp ghép khác loại được sửa thành tài liệu đơn), harness dừng với `SplitsOutOfDateError`. Chia lại phải gọi có chủ ý: `load_or_make_splits(bench, rebuild=True)` hoặc cờ `--rebuild-splits` của `01_classical_baselines/run_all.py`. Test: `test_frozen_splits_survive_label_edits_and_refuse_unassigned_docs`, `test_relabelled_mixed_composite_is_dropped_even_if_frozen_split_says_dev`.
- **Còn lại:** (1) quyết định chỗ cho tài liệu mới của T3: gán `split = "NEW"` trong một tệp riêng (`data/splits/splits_new.csv`) và cho `load_documents` đọc được, thay vì chia lại; (2) sửa nhãn làm lệch tỉ lệ loại giữa các fold (chia ban đầu phân tầng theo nhãn cũ): sau T1, đếm số tài liệu mỗi loại theo fold và báo cáo nếu có fold thiếu hẳn một loại Track S; (3) quy định: sau khi sửa nhãn của tài liệu TEST, chấm lại TEST phải ghi lý do trong báo cáo (`--allow-rescore`); (4) cập nhật mục 3 của giao thức đánh giá cho khớp.
- **Sản phẩm:** `splits_new.csv` + sửa `eval/harness.py` + test; đoạn bổ sung trong `reports/03_evaluation_protocol.md`.
- **Xong khi:** thêm một tài liệu giả vào nhãn thì nó nhận `NEW`, không tài liệu cũ nào đổi tập, và `pytest teams/00_data_and_eval/tests -q` qua.
- **Công sức (ước lượng):** 0,5 ngày.
- **Điều kiện tiên quyết:** không; nên xong trước khi T3 thêm tài liệu.

### T6 (P1) — Giữ bảng kết quả chung sạch

- **Vì sao:** `teams/team3_classification/results/results_table.csv` là nơi so sánh mọi phương pháp; nó chỉ có ý nghĩa khi chỉ-thêm-dòng và mỗi dòng gắn đúng nhãn.
- **Các bước:** viết `eval/check_results_table.py` kiểm: `run_id` không trùng; `labels_sha` của dòng mới khớp nhãn hiện hành (dòng cũ hơn đánh dấu "cũ"); mỗi cặp (`method`, cấu hình) chấm `split=TEST` không quá một lần; không có dòng cũ bị sửa (`git diff` chỉ có dòng thêm); `text_source` thuộc `available_sources()`. Mỗi tuần sinh `reports/07_results_overview.md` (bảng theo phương pháp × nguồn văn bản, có CI), ghi rõ dòng nào còn hiệu lực.
- **Sản phẩm:** script + test + báo cáo tuần.
- **Xong khi:** script chạy trên bảng hiện tại, báo cáo liệt kê dòng cũ/mới; được gọi trong checklist trước mỗi điểm tích hợp.
- **Công sức (ước lượng):** 0,5 ngày, rồi 1 giờ mỗi tuần.

### T7 (P0) — Quản trị dữ liệu

- **Vì sao:** các PDF là hồ sơ thật của doanh nghiệp, chứa tên, số căn cước, số giấy phép lái xe, địa chỉ, mã số thuế, số tài khoản. Kho git hiện **theo dõi cả 336 PDF** (`git ls-files docs/_chot_samples_phanloaitailieu`) và remote là `https://github.com/aidodq/sdh-phanloaitailieu.git`.
- **Các bước:** (1) kiểm tra kho đó là **private** (`gh repo view --json visibility` hoặc trang cài đặt GitHub; chưa kiểm tra khi viết) và ai có quyền; nếu không private thì dừng đẩy code và báo chủ dự án; (2) bảng phân loại dữ liệu và cái được phép (dưới đây); (3) thêm vào `.gitignore` những đường dẫn chứa dữ liệu cá nhân phát sinh về sau (`teams/team1_ocr/gold/transcripts/`, CSV lỗi có tên tệp, phiếu kiểm nhãn); (4) ghi vào `reports/08_data_governance.md` mỗi lần dữ liệu rời máy nội bộ: gửi gì, cho dịch vụ nào, ngày, ai duyệt.
- **Sản phẩm:** `reports/08_data_governance.md`; `.gitignore` cập nhật (nhờ chủ kho, vì tệp đó ngoài thư mục nhóm).
- **Xong khi:** có xác nhận bằng văn bản về chế độ riêng tư của kho; mọi nhóm đã đọc bảng dưới đây.
- **Công sức (ước lượng):** 0,5 ngày.

| Dữ liệu | Có thông tin cá nhân/nhạy cảm | Được phép |
|---|---|---|
| PDF gốc, `data/classified_v2/` | Có (CCCD, GPLX, tên, địa chỉ, MST, số tài khoản) | Chỉ trong kho riêng tư và máy nội bộ. Không công bố, không đưa vào chat/issue. Chỉ **bộ mẫu này** được gửi LLM bên ngoài để nghiên cứu (chủ dự án đã đồng ý) |
| Văn bản OCR/bản chép (`data/ocr_v2.jsonl`, `data/ocr_llm_haiku*`, `gold/transcripts/`, `gold/silver_llm/`) | Có (chép nguyên văn) | Như PDF gốc |
| CSV lỗi, phiếu kiểm nhãn | Có (tên tệp, 150 ký tự đầu) | Chỉ nội bộ; không đưa vào `.md` công khai |
| Báo cáo `.md`, bảng kết quả | Không được chứa số định danh, số điện thoại, số tài khoản, họ tên | Được chia sẻ trong nhóm |
| Hệ thống chạy thật | Có | **Phải on-premise**; không gọi LLM/đám mây ngoài |

### T8 (P2) — Sửa công cụ nhãn

- `scripts/build_labels_v2.py`: **đã sửa** để suy `composite_mixed` từ số loại khác nhau trong `segments` (sau phân xử), chỉ dùng ghi chú của annotator A khi thiếu `segments`; tệp nhãn sinh ra giống hệt trước khi sửa. Còn thiếu: test cho script này.
- `annotation/agreement.py` mỗi lần chạy **ghi đè** `annotator_B_sonnet.csv` từ các `part*.csv`; ghi chú vào đầu script hoặc tách phần ghi.
- Công sức (ước lượng): 0,5 ngày.

## Cách chạy lại những gì đã có

Chạy từ gốc repo, PowerShell, luôn có `-X utf8` (xem [handbook](../../docs/HANDBOOK_FOR_RESEARCHERS.md) để dựng môi trường):

```powershell
$py = ".venv\Scripts\python.exe"
& $py -X utf8 scripts\build_manifest.py                      # manifest + nhóm trùng (~20-30 giây theo báo cáo 01); chỉ đọc PDF
& $py -X utf8 teams\00_data_and_eval\make_duplicates_report.py   # sinh lại reports/01_duplicates.md
& $py -X utf8 teams\00_data_and_eval\annotation\build_packets.py --parts 3 --seed 7   # gói gán nhãn cho annotator
& $py -X utf8 teams\00_data_and_eval\annotation\agreement.py     # κ, disagreements.csv, agreement_summary.json (GHI ĐÈ annotator_B_sonnet.csv)
& $py -X utf8 scripts\build_labels_v2.py                     # hợp nhất A+B+adjudication.csv -> data/labels_v2.csv (GHI ĐÈ)
& $py -X utf8 scripts\build_classified_folder.py             # dựng lại data/classified_v2/ (GHI ĐÈ, chỉ chấp nhận --out tên classified_v2)
& $py -X utf8 -m pytest teams\00_data_and_eval\tests -q      # 33 test (qua ngày 2026-10-16)
```

Dùng bộ chấm trong Python (ví dụ đầy đủ ở mục 9 của [giao thức](reports/03_evaluation_protocol.md)):

```python
import sys; sys.path.insert(0, "teams/00_data_and_eval/eval")
from harness import *
bench  = load_benchmark("data/labels_v2.csv")          # 11 lớp Track S (10 loại + RARE_OR_OTHER)
splits = load_or_make_splits(bench)                    # đọc tập chia đã khóa; không tự chia lại khi nhãn đổi (xem T5)
print(available_sources())                             # legacy_p1, haiku_p1, haiku_p12, ocr_v2_p1, ocr_v2_p12
```

## Bẫy thường gặp (đã gặp thật)

1. **Nhãn = tên thư mục.** Thư mục là tủ hồ sơ: 27 nhóm trùng byte nằm ở ≥ 2 thư mục (cùng tệp, hai "đáp án"); thư mục "THUE KHO" không có hợp đồng thuê kho nào. Luôn dùng `labels_v2.csv`.
2. **Quên loại bản sao.** Chấm trên 336 tệp thay vì 304 tài liệu làm cùng một tờ nằm ở cả train và test.
3. **κ = 1,0 không có nghĩa đúng.** Hai annotator cùng họ mô hình, cùng hướng dẫn; A là người viết hướng dẫn.
4. **Ví dụ trong hướng dẫn là tên tệp thật** → người gán có thể chép đáp án. Luôn báo κ loại trừ các tệp đó (`in_guideline`).
5. **Annotator chỉ thấy 2 trang đầu** không biết tệp có composite hay không: 5 tệp `check_composite` sinh ra từ đó. `is_composite`/`segments` chỉ tin người xem đủ trang.
6. **Số trang:** hướng dẫn gán nhãn đếm từ **1**, gold OCR (`gold_pages_todo.csv`) và `page0` trong thí nghiệm 03 đếm từ **0**.
7. **`scripts/generate_baseline_ocr.py` là script cũ, ghi đè `data/baseline_ocr_335.jsonl`** (đã bị chạy nhầm một lần khi thử `--help`, đã khôi phục bằng `git checkout`). Nay script từ chối chạy nếu không có `--force`. Đừng chạy nó; dùng `build_ocr_dataset.py`.
8. **Con số khác nhau theo mẫu số.** `PHIEU_XUAT_KHO` là 21 tài liệu theo nhãn chính nhưng 15 trong benchmark (6 tệp composite hỗn hợp mang nhãn chính này bị loại). Luôn ghi mẫu số.
9. **Tên tệp tiếng Việt** có thể ở dạng NFC hoặc NFD; mã dùng `unicodedata.normalize("NFC", ...)` khi so đường dẫn — làm tương tự.
10. **Ngày trong tên tệp** ("DDK-CHIN LOAN-12.1.28") do nhân viên gõ, có thể là ngày hết hạn nhưng **không mặc nhiên** (công ty trả lời câu hỏi 16 ngày 2026-10-16: ngày chỉ là hạn khi tài liệu ghi cụ thể đó là ngày gì; xem [`README.md`](../../README.md) "Quyết định của công ty"): chỉ dùng để kiểm chéo, không làm đáp án và không làm nguồn xác nhận độc lập.

## Câu hỏi cần hỏi doanh nghiệp

Nguyên văn và bối cảnh ở mục 9 của [`reports/02_taxonomy_design.md`](reports/02_taxonomy_design.md). Rút gọn:

| # | Câu hỏi | Ảnh hưởng |
|---|---|---|
| 1 | Có danh mục chuẩn của hồ sơ cửa hàng và hồ sơ xe (tên tệp đánh số tới 38) không? | thêm loại |
| 2 | Hóa đơn, thỏa thuận tín dụng, bảng báo giá, công văn/thông báo/quy chế có thuộc phạm vi không, lưu ở đâu? | phạm vi |
| 3 | Chứng nhận huấn luyện PCCC và nghiệp vụ BVMT theo dõi riêng hay gộp? | taxonomy |
| 4 | Bản vẽ kỹ thuật có cần lưu riêng hay chỉ là phụ lục giấy thẩm duyệt? | taxonomy |
| 5 | Hai cặp thư mục cùng nội dung: cái nào là chính? | định tuyến |
| 6 | Hợp đồng thuê kho thật nằm đâu? Hợp đồng mua bồn/xe lưu đâu? | định tuyến |
| 7 | Giấy đăng ký DN/giấy đủ điều kiện của khách nhượng quyền: một bản + liên kết hay sao hai nơi? | định tuyến |
| 8 | Hợp đồng vận chuyển: tách "đi thuê" và "vận chuyển cho khách"? | định tuyến |
| 9 | Bộ chứng từ một chuyến hàng: lưu cả bộ hay tách? ERP cần số nào? | nhóm 2, 4 |
| 10 | Giấy phép kinh doanh vận tải có đúng là lưu ở hồ sơ xe? | định tuyến |
| 11 | Ngày hết hạn nào cần nhắc, trước bao lâu, cho ai? Thẻ PCCC không ghi hạn tính theo quy định nào? | nhóm 4 |
| 12 | Có được trích/lưu số căn cước, số GPLX, ngày sinh vào ERP? Ai xem? Lưu bao lâu? | nhóm 4, T7 |
| 13 | Tập tự kiểm tra PCCC: cần ngày từng biên bản hay chỉ cần biết đã nộp kỳ nào? | nhóm 2, 4 |
| 14 | Biên bản lấy mẫu (tới 93 biên bản/tệp): mỗi biên bản một bản ghi hay lưu theo cửa hàng/kỳ? | nhóm 2, 4 |
| 15 | Biên bản trả bồn có là sự kiện riêng? Biên bản ký sẵn để trống ngày hiểu thế nào? | nhóm 2, 4 |
| 16 | ~~Quy ước ngày trong tên tệp~~ **đã trả lời 2026-10-16** (ngày trong tên tệp không mặc nhiên là ngày hết hạn; chỉ ngày tài liệu ghi cụ thể là hạn mới là hạn; có giấy tờ không có hạn). Còn mở: "BC", "GOC", "photo" nghĩa là gì; cần ghi bản chính/bản sao? | nhóm 4 |
| 17 | ERP có danh mục khách hàng, nhà cung cấp, cửa hàng/ghe, xe, lái xe kèm MST/biển số? Pháp nhân nào là "công ty mình"? | định tuyến |

Thêm từ nhóm này: ai ở công ty chịu trách nhiệm kiểm nhãn (T1) và có thể dành bao nhiêu giờ; công ty có đồng ý cho mẫu mới (T3) gửi LLM ngoài cho mục đích nghiên cứu không; kho git hiện được lưu ở đâu và ai có quyền (T7).
