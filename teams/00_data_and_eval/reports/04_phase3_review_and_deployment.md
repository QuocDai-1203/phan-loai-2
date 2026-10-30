# 04 - Review độc lập giai đoạn 3 và thiết kế triển khai khuyến nghị

> `data/labels_v2.csv` sha1[:10] = `eb3348713a` · ngày 2026-10-16 · nhánh `research-v2`, bản làm việc CHƯA commit của giai đoạn 3.
> Cách làm: đọc mã (`src/`, script thí nghiệm) và các tệp kết quả (`results/*.csv`, `*.json`); tự tính lại các số chính trên CPU (pandas, scipy; không GPU, không Ollama, không gọi mô hình). `pytest -q` ở gốc: **315 qua** (bản làm việc lúc review, khi một agent khác đang sửa `src/extraction/`).
> Mọi "đúng/sai" là **so với đáp án máy** (nhãn loại do hai lượt mô hình AI, ranh giới do một mô hình, trường do Haiku/Sonnet/Opus), chưa có nhân viên công ty kiểm. Tệp này không chứa định danh cá nhân; tài liệu được nhắc bằng `doc_id`.
> Viết cho sinh viên năm cuối. Phần 1 là review (tìm chỗ số có thể sai), phần 2 là thiết kế triển khai (dựa trên số đo, chỉ rõ chỗ chưa có số).

---

## 0. Tóm tắt (đọc trước)

**Review.** Các con số chính của giai đoạn 3 **tính lại được đúng** từ tệp kết quả (mục 1). Vấn đề không nằm ở phép tính mà ở **cách diễn giải và cách đổi mặc định**:

1. **Nghiêm trọng.** Mặc định của pipeline đã được đổi sang `model+merge+id` và `title_tiebreak = True` dựa trên bằng chứng **hoàn toàn trong mẫu**: hai tùy chọn được nghĩ ra sau khi đọc chính 14 tệp composite dev, kết quả dev biết trước khi "ghi quy tắc" (232 = 223 + 3 + 6), còn TEST có **0** tệp composite thuộc hai nhóm đó nên cổng "TEST không hại" không thể trượt. Chính nhóm 3 (thí nghiệm 05) và nhóm 2 (thí nghiệm 06) đều khuyên **chưa** bật.
2. **Nghiêm trọng.** Tự nhận ngày hết hạn của 4 loại cũ dựa vào quy ước "ngày trong tên tệp = ngày hết hạn" (quy tắc `any-model=filename`). Quy ước này là đặc điểm của kho mẫu, chưa được công ty xác nhận, và đã hỏng ở loại mới (đứng một mình sai 17/40 lần trên DEV v2) và ở tệp ghép (0/9). Nếu máy quét đặt tên kiểu `scan_0001.pdf`, tỉ lệ tự nhận 56% không còn.
3. **Nghiêm trọng.** `src/extraction/field_extractor.py:47` đặt `GENERIC_EXPIRY_RULE = "regex=llm"` làm quy tắc **tự nhận** cho 17 loại mới, trái với khuyến nghị số 5 của chính nhóm 4 ("chưa nên bật tự nhận hạn không có người duyệt cho loại mới", `03_unseen_types/RESULTS.md:244`). Hai nguồn này cùng đọc một bản OCR nên không độc lập; ngoài mẫu chỉnh chỉ có 12 lần tự nhận (cận trên 95% của tỉ lệ sai: 22%).
4. **Nghiêm trọng về quyền riêng tư.** 306 tệp PDF gốc (có CCCD, GPLX, hợp đồng; nhiều tên tệp chứa họ tên), toàn văn OCR `data/ocr_v2.jsonl` và silver trường v1 đang được git theo dõi; remote là GitHub. Silver được làm bằng mô hình đám mây, tức tài liệu đã ra khỏi công ty. Cần xác nhận văn bản rằng việc này đã được công ty duyệt.
5. **Trung bình (lỗi mã).** Kiểm mẫu ngẫu nhiên (`audit_rate`) băm theo `slice_id` dạng `slice_000`, không duy nhất giữa các tệp: ở seed 0, mức 5% **không bao giờ** chọn ai, mức 10% chọn **mọi** lát cắt đầu (gần như mọi tệp). Tệp > 30 trang bị cắt âm thầm (6/336 tệp, dài nhất 93 trang). Khi 17 loại mới vào `src/`, VLM sẽ được gọi cho 53% tài liệu dù quy tắc `regex=llm` không dùng nó, kéo thông lượng ước lượng từ ~500 xuống ~365 trang/giờ.

**Triển khai (mục 6–10).** Một máy RTX 3060 12 GB đủ cho 500 và 2.000 trang/ngày (chạy ca đêm), 10.000 trang/ngày cần khoảng 3 máy (giả định ở mục 8). Cấu hình khuyến nghị cho chạy bóng: `model+merge` (S10), tắt `tiebreak` khi tự động hóa nhưng **ghi lại** quyết định của nó, `id` chỉ dùng để **chuyển người**, không tự nhận ngày hết hạn nào trong chạy bóng. Tiêu chí chấp nhận: lỗi âm thầm trên tệp tự xử lý có cận trên 95% ≤ 1%, tức ≥ 299 tệp tự xử lý liên tiếp không lỗi (hoặc ≥ 473 tệp với ≤ 1 lỗi). Hiện mức dev+TEST của cấu hình mới là 7/295 = 2,4% (cận trên một phía 4,4%), nên **chưa đạt**; doanh nghiệp phải chọn giữa thêm người duyệt (`triage`) và chấp nhận mức lỗi cao hơn.

---

## 1. Kiểm lại số (tự tính từ tệp kết quả, CPU)

| # | Con số được báo | Nguồn | Tự tính lại | Khớp? |
|---|---|---|---|---|
| 1 | Dev: S10 223/245 tệp đúng hoàn toàn, 14 sai lặng lẽ, 279/318 tài liệu; S10+id+tb 232/245, 5 sai lặng lẽ, 293/318 | `03_end_to_end_v2/results/per_file_dev.csv` | 223 / 14 / 279 và 232 / 5 / 293; tự xử lý 237/245 cả hai; sai lặng lẽ 5/237 = 2,1%, Clopper–Pearson hai phía [0,69%; 4,85%] | khớp |
| 2 | (c) có trọng số theo cơ cấu tệp: 91,9% → 94,8%, hiệu +3,0 điểm, CI ghép cặp [+2,0; +3,9] | cùng tệp + trọng số từ `boundary_gold_v0.csv` (304 tệp: 191 / 92 / 8 / 7 / 6) | 91,87% → 94,83%; bootstrap phân tầng ghép cặp của tôi (B = 4000, seed 0): +2,96 [+1,97; +3,95] | khớp |
| 3 | TEST: S10 và S10+id+tb cùng 56/59, 2/58 sai lặng lẽ, "tb không đổi quyết định nào ở 59 tệp" | `per_file_test.csv` | 56/59 và 2/58 đúng; nhưng **3/59 tệp đổi tầng quyết định** (TF-IDF → luật, cùng nhãn đúng) | số khớp, câu chữ sai (mục 3, N3) |
| 4 | Ảnh trang cho VLM: hạn đúng và tự nhận 32/66 → 37/66, thêm 5 mất 0, sai 0; bootstrap [+1,5; +15,2]; dấu p = 0,0625 | `02_chain_with_images/results/*_per_field.csv`, `*_per_unit.csv` | 32 → 37, bảng chéo 5 thêm / 0 mất, 0 sai; bootstrap theo đơn vị (82 đơn vị, B = 5000): +7,6 [+1,6; +14,8]; kiểm định dấu chính xác p = 0,0625 | khớp |
| 5 | Tiebreak trên 237 tài liệu DEV: đổi tầng 25, đổi nhãn 0, lỗi 1 không đổi | `team3/results/05_composite_slices/dev_regress_base_vs_tiebreak.csv` | 25 đổi tầng (21 TF-IDF→luật, 4 LLM→luật), 0 đổi nhãn (1 dòng "đổi" là NaN của tầng người), 1 lỗi tự nhận (cùng tài liệu) | khớp |
| 6 | Biên an toàn L0: cross-fit 235/237 tự nhận, 0 sai, cận trên 1,27% | `team3/results/04_safety_margin/summary.json` | 0/235, cận trên một phía 1 − 0,05^(1/235) = 1,27% | khớp |
| 7 | Thông lượng ~500 trang/giờ | `03_end_to_end_v2/RESULTS.md` mục chi phí, `cost_v2.json` | 3,36 trang × 4,17 s + 0,273 × 33,9 s + 0,069 × 13,3 s = 24,2 s/tệp → 149 tệp/giờ → 500 trang/giờ | khớp (nhưng xem T3) |
| 8 | Cận trên khi 0 lỗi: 299 lần cho mức 1% | giao thức §7, team3 04 | Clopper–Pearson một phía: 0/299 → 1,00%; 1/473 → 1,00%; 2/628 → 1,00%; 3/773 → 1,00% | khớp |

Kết luận: không có lỗi số học. Các phát hiện dưới đây là về **thiết kế đo, diễn giải, và mã**.

---

## 2. Phát hiện nghiêm trọng (làm sai kết luận hoặc chặn triển khai)

### N1. Đổi mặc định của pipeline dựa trên bằng chứng trong mẫu và một cổng TEST rỗng

* **Ở đâu.** `src/pipeline.py:55` (`DEFAULT_TITLE_TIEBREAK = True`), `src/splitting/policy.py:57` (`DEFAULT_PRESET = "model+merge+id"`); lập luận ở `03_end_to_end_v2/RESULTS.md` (tóm tắt dòng 12, mục "Mặc định mới và rủi ro").
* **Vì sao sai kết luận.**
  1. *Quy tắc "ghi trước" không ghi trước kết quả.* Kết quả của 06 (nhóm 2) ghi lúc 23:33 và của 05 (nhóm 3) lúc 23:38 ngày 15/10 (giờ máy); `dev_selection_v2.json` mang trạng thái `dev_done` lúc 00:20 ngày 16/10. Khi viết quy tắc, người viết đã biết `id` sửa 3/6 tệp cùng loại, `tb` sửa 6/8 tệp khác loại, cả hai 0 hỏng. Dev cho đúng 232 = 223 + 3 + 6. Quy tắc chọn vì vậy là hình thức. Tệp quy tắc chưa commit và bị ghi đè tại chỗ (đổi `status`), nên không kiểm được nó có trước lần chạy hay không.
  2. *Thiết kế và chấm trên cùng 14 tệp.* Cả hai tùy chọn được nghĩ ra sau khi đọc chính các tệp composite dev (06: "quy tắc được thiết kế sau khi đọc các tệp cùng loại của dev", ngưỡng 0,7 chọn sau khi xem độ nhạy; 05: 8 tệp **của một nhà cung cấp**, 6 trang biên bản gần như giống hệt nhau). "+3,0 điểm [+2,0; +3,9]" là **mức sửa đúng thứ đã thấy**, không phải ước lượng tổng quát hóa; CI hẹp vì 14 tệp đổi cùng chiều, không vì có nhiều bằng chứng.
  3. *Cổng TEST không thể trượt theo hướng có ích.* TEST có 21 / 36 / 0 / 0 / 2 tệp (không có composite khác loại hay cùng loại ngoài `BB_LAY_MAU`). Quy tắc đổi mặc định chỉ đòi "TEST không tệ hơn S10", nên chỉ kiểm "không hại tệp thường". Điều đó có giá trị nhưng không biện minh cho việc bật.
  4. *Trái với khuyến nghị của nhóm sở hữu.* 05 (`RESULTS.md:56`): "mặc định giữ nguyên `rule_title_tiebreak=False` … bật sau khi có thêm mẫu BB/PXK từ nhiều biểu mẫu". README nhóm 2 (`teams/team2_splitting/README.md:147`) và nhóm 3 (`teams/team3_classification/README.md:51`) vẫn ghi "không phải mặc định" / "tắt mặc định".
  5. *Rủi ro âm thầm có thật.* Tiebreak cho tầng luật (không có độ tin cậy) quyết định thay TF-IDF/LLM ở 25/237 tài liệu DEV và 3/59 tệp TEST. Cả 28 đều đúng, nhưng 0/28 chỉ cho cận trên một phía 10,2%. Một biểu mẫu mới có tên loại khác nằm trong 400 ký tự đầu sẽ bị nhận sai mà không có tín hiệu nào chuyển người.
* **Cách sửa.** Trong triển khai (mục 7): đặt lại `DEFAULT_TITLE_TIEBREAK = False` và `DEFAULT_PRESET = "model+merge"`, hoặc giữ hai tùy chọn nhưng ở chế độ **"cờ chuyển người"** (lát cắt có ranh giới do quy tắc `id` thêm, hoặc do tiebreak quyết định, đi vào hàng duyệt nhẹ). Trên dev, `id` kích hoạt ở 3/245 tệp (~1%), cấu hình id+tb đổi tầng hoặc lát cắt ở 33/245 tệp (13%, phần lớn do tiebreak). Ghi trong RESULTS: "+3,0 điểm là trần lạc quan trên dữ liệu thiết kế". Chỉ bật tự động khi có ≥ 30 tệp composite mỗi loại từ ≥ 3 nhà cung cấp chưa từng xem.

### N2. Tự nhận ngày hết hạn phụ thuộc quy ước đặt tên tệp của kho mẫu

* **Ở đâu.** `src/extraction/expiry_rules.py:58` (`any-model=filename`), `src/extraction/field_extractor.py:45,143` (`fn_date = ds[-1]`: ngày cuối cùng trong tên tệp); kết quả ở `02_chain_with_images/RESULTS.md` (32 → 37/66, 0 sai), README gốc dòng 45.
* **Vì sao sai kết luận.** Quy tắc chỉ nhận một ngày khi mô hình đọc trùng ngày trong tên tệp. Tên tệp ở kho mẫu do người thu thập đặt (có ngày); điều này chưa được công ty xác nhận (`02_chain_with_images/RESULTS.md:44`). Bằng chứng nó không chuyển sang được: ở 17 loại mới, ngày trong tên tệp đứng một mình sai 17/40 lần có ngày ở DEV (14 là giấy không có hạn), tệp ghép 0/9 tự nhận (`03_unseen_types/RESULTS.md` §0, §3). Nếu đầu vào thật đến từ máy quét (`scan_0001.pdf`) thì tỉ lệ tự nhận về gần 0. Nếu nhân viên đặt tên theo ngày **cấp** thay vì ngày hết hạn, quy tắc có thể tự nhận sai.
* **Cách sửa.** (a) Hỏi công ty quy trình đặt tên thật và lấy 100 tên tệp thật (không cần nội dung). (b) Đo trên DEV một quy tắc không dùng tên tệp nhưng có nguồn độc lập với OCR, ví dụ `regex=vlm`: trên 84 đơn vị v2 cho 46/62 tự nhận đúng, 0 sai (cận trên 6%). (c) Trong chạy bóng, không tự nhận ngày nào, chỉ đo.

### N3. `regex=llm` đang thành quy tắc tự nhận mặc định cho 17 loại mới

* **Ở đâu.** `src/extraction/field_extractor.py:47,54` (`GENERIC_EXPIRY_RULE = "regex=llm"`, do agent đang tích hợp 17 loại thêm vào). Khuyến nghị ngược lại: `03_unseen_types/RESULTS.md:244`.
* **Vì sao sai kết luận.** Luật ngày chung và LLM cùng đọc **một bản OCR**: khi OCR đọc sai chữ số (bài học giai đoạn 2: "22" thay "12"), hai nguồn cùng sai và đồng thuận. Có 47 lần tự nhận, 0 sai, nhưng 35 lần nằm trên DEV đã dùng để chỉnh luật; ngoài mẫu chỉnh chỉ có 12 lần (cận trên 22%). Đáp án là silver máy, và trước phân xử hai người chú thích chỉ đồng thuận 0,896 [0,842; 0,933] ở trường ngày (`gold/v2/silver_report_v2.md` §3).
* **Cách sửa.** Với 17 loại mới: trích xuất chỉ làm **gợi ý** (`needs_review`), không tự nhận, cho tới khi chạy bóng có ≥ 299 lần tự nhận không lỗi. Nếu cần tự động sớm: dùng `regex=vlm` hoặc `regex=llm=vlm` (45/62, 0 sai), có một nguồn đọc ảnh.

### N4. Dữ liệu nhạy cảm nằm trong git; tài liệu đã được gửi tới mô hình đám mây

* **Ở đâu.** `git ls-files data/classified_v2 | wc -l` = 306 (PDF gốc, gồm CCCD, GPLX; tên tệp có họ tên người); `data/ocr_v2.jsonl` (toàn văn), `teams/team4_extraction/gold/fields_silver_v1.jsonl` được theo dõi; `teams/team4_extraction/gold/v2/fields_silver_v2.jsonl` (chưa theo dõi, 16/84 bản ghi có trường `ho_ten`) sẽ bị commit nếu chủ phiên `git add` cả thư mục. Remote: `github.com/.../sdh-phanloaitailieu`. Silver v1/v2 và đáp án hướng trang do Haiku/Sonnet/Opus đọc ảnh, tức ảnh tài liệu đã đi qua dịch vụ đám mây.
* **Vì sao nghiêm trọng.** Đây không phải lỗi số, nhưng là điều kiện tiên quyết của triển khai on-premise: nếu chưa có văn bản chấp thuận của công ty, việc lưu trên dịch vụ git bên ngoài và gửi ảnh cho API là rò rỉ dữ liệu cá nhân (CCCD, GPLX có số định danh, ngày sinh).
* **Cách sửa.** (1) Xác nhận repo là private và việc dùng API đã được duyệt bằng văn bản; nếu chưa, dừng push, gỡ dữ liệu khỏi lịch sử (`git filter-repo`), chuyển dữ liệu ra ổ nội bộ ngoài git. (2) Thêm `teams/team4_extraction/gold/v2/fields_silver_v2.jsonl`, `silver_raw/`, `adjudication/` vào `.gitignore` hoặc bỏ trường `ho_ten` khỏi bản commit. (3) Từ nay, mọi tài liệu mới chỉ đi qua mô hình cục bộ (mục 9).

---

## 3. Phát hiện mức trung bình

| # | Vấn đề | Đường dẫn:dòng | Ảnh hưởng | Cách sửa |
|---|---|---|---|---|
| T1 | **Kiểm mẫu không ngẫu nhiên trong pipeline.** `audit_flags([slice_id], …)` băm `"{seed}:{slice_id}"`, mà `slice_id` là `slice_000`, `slice_001`… lặp lại ở mọi tệp. Tôi chạy thử: seed 0, mức 5% → không lát cắt nào được chọn; mức 10% → `slice_000` luôn được chọn (gần như mọi tệp, vì đa số tệp có một lát cắt); seed 1, mức 5% → luôn `slice_003` và `slice_007`. Mô phỏng ở team3 04 dùng `doc_id` nên số của 04 đúng, nhưng mã sản phẩm không làm như vậy. | `src/classification/doc_classifier.py:212`; `src/splitting/boundary_detector.py:75`, `src/splitting/type_merge.py:73` | Nếu bật `audit_rate` trong sản xuất: hoặc không kiểm gì, hoặc kiểm gần 100% | Băm theo `(sha256 tệp, slice_id)` hoặc `(doc_id, slice_id)`; test: 1000 tệp giả × 1 lát cắt, mức 5% → 30–70 lát được chọn |
| T2 | **Tệp > 30 trang bị cắt âm thầm.** `ocr_pdf` trả `total_pages` nhưng pipeline không so với `len(pages)`; các trang sau 30 không được tách, phân loại hay chuyển người. Kho có 6/336 tệp > 30 trang (dài nhất 93). Đánh giá toàn trình cũng cắt đáp án ở 30 trang (`01_end_to_end/RESULTS.md`, Thiết lập), nên lỗi này **không hiện** trong số nào. | `src/pipeline.py:199,239`; `src/ocr/pdf_ocr.py:202,210` | Tài liệu nằm sau trang 30 của tệp ghép bị mất, không có cảnh báo | Nếu `total_pages > len(pages)` thì chuyển cả tệp sang người (lý do `truncated`) hoặc OCR hết; thêm test |
| T3 | **VLM bị gọi kể cả khi quy tắc không dùng.** `FieldExtractor` gọi VLM hễ có ảnh và loại có trường hạn; pipeline dựng ảnh cho mọi loại có trường hạn trong `SUPPORTED_TYPES`. Với 17 loại mới, 162/304 tài liệu duy nhất (53%) sẽ dựng ảnh và gọi VLM (~21 s + 0,9 s), so với 83/304 (27,3%) trong mô hình chi phí, dù `regex=llm` không đọc kết quả VLM (chỉ dùng làm gợi ý). Theo công thức của 03: **~365 trang/giờ** thay vì 500. | `src/extraction/field_extractor.py:120-129`; `src/pipeline.py:302-310` | Ước lượng thông lượng và số máy cũ không còn đúng | Chỉ dựng ảnh khi quy tắc hạn của loại đó có `vlm`, hoặc chọn `regex=vlm` cho loại mới; đo lại `cost_sample_v2.py` |
| T4 | **Trang có từ khóa hạn không tới được VLM.** `choose_vlm_pages` chọn tối đa 6 trang (2 đầu, trang cuối, trang có từ khóa) nhưng trang dọc bị cắt đôi và `max_vlm_images = 4` → chỉ 2 trang đầu được gửi. Hợp đồng dài có điều khoản hiệu lực ở trang 3 trở đi thì VLM không thấy, trong khi người chú thích silver thấy tới 6 trang. Kết quả là ô trống (không sai), nên làm giảm tự động hóa mà không làm tăng lỗi. | `src/pipeline.py:61-79`; `src/extraction/field_extractor.py:69,123` | Phần logic chọn trang theo từ khóa là mã chết với tài liệu dọc > 2 trang | Xếp nửa ảnh của trang có từ khóa lên trước, hoặc gửi trang đầu + trang từ khóa; đo lại trên DEV |
| T5 | **TEST đã mòn.** TEST 59 tệp đã được mở: phân loại 02/03 (nhiều ứng viên được báo trên TEST), tách trang (`team2_splitting/experiments/RESULTS_test_docs_only.md`, 6 phương pháp), toàn trình lần 1 và lần 2, trích xuất giai đoạn 2, và nhóm 4 giai đoạn 3 (6 cấu hình zero-tuning trên TEST, tổng hợp TEST+EXCLUDED được xem **trước** vòng cải tiến, tự thừa nhận ở `03_unseen_types/RESULTS.md` §0). Mỗi lần riêng lẻ hợp lệ, nhưng cộng lại thì TEST không còn là giữ ngoài sạch; thêm nữa nó không có composite. | `01_end_to_end/test_run_registry.json`; giao thức §4 | Con số TEST là "đối chiếu", không phải ước lượng triển khai | Ghi rõ "TEST đã mòn"; giữ ngoài thật sự = dữ liệu chạy bóng; lập TEST v2 từ chạy bóng, phân tầng có composite |
| T6 | **Đáp án silver đọc ảnh, so với VLM đọc ảnh.** Silver v1/v2 do mô hình đọc ảnh; phương pháp OCR+LLM bị phạt vì lỗi OCR, VLM thì không. "VLM F1 mềm 0,83 so với LLM 0,75" có một phần do điều này (nhóm 4 đã ghi "lưu ý bắt buộc 3"). Hàng phân xử ưu tiên các trường lệch tên tệp (`filename_mismatch`), nên trường đồng thuận mà **khớp** tên tệp ít được soát lại → đáp án nghiêng nhẹ về phía quy tắc dùng tên tệp. | `teams/team4_extraction/gold/build_adjudication.py:9,54-98`; `03_unseen_types/RESULTS.md` §2 | So sánh VLM với LLM thiên lệch; "0 sai" của `any-model=filename` hơi lạc quan | Nhân viên kiểm 100 trường hạn rút ngẫu nhiên (không theo hàng phân xử) |
| T7 | **Thông lượng không dùng được để lập kế hoạch.** GPU dùng chung, mỗi cấu hình chạy một lần, không CI; 08 đo 0,17–0,22 trang/giây với 4–6 worker, **chậm hơn** một tiến trình ở 03 (4,26 s/trang ≈ 0,23 trang/giây) và không tái lập được 0,35 trang/giây của báo cáo 02. Độ trễ VLM thay đổi 14,7 s (02) → 20,9 s (03) → 19,1 s (nhóm 4). | `team1_ocr/experiments/08_throughput/RESULTS.md` §2; `03_end_to_end_v2/RESULTS.md` mục chi phí | Số máy ở mục 8 có sai số ít nhất ±50% | Đo trên máy riêng, 3 lần lặp, 200 tệp theo cơ cấu thật, báo trung vị và khoảng |
| T8 | **Đơn vị CI của chẩn đoán composite.** 05 báo "28/28 lát đúng [Wilson 87,9; 100]" theo **lát cắt** của 8 tệp một nhà cung cấp; các lát không độc lập. Đơn vị đúng là tệp: 8/8, Clopper–Pearson [63%; 100%]. Tương tự, CI "toàn bộ theo cơ cấu tệp" hẹp giả khi nhóm composite có 0/n hoặc n/n (ví dụ S9: [93,1; 93,1]); 01 đã ghi điều này nhưng tóm tắt 03 vẫn dẫn CI hẹp. | `team3_classification/experiments/05_composite_slices/RESULTS.md:32`; `03_end_to_end_v2/RESULTS.md` tóm tắt | CI trông chắc hơn thực tế | Báo theo tệp; luôn đặt đếm thô + Clopper–Pearson theo nhóm cạnh số có trọng số |
| T9 | **Tài liệu lệch mã.** README gốc (dòng 20, 26, 89) vẫn ghi mặc định `model+merge`; docstring `src/pipeline.py:212` ghi "None = mặc định `model+merge`"; README nhóm 2, 3 ghi "không phải mặc định". | như cột trái | Sinh viên và chủ phiên đọc sai cấu hình đang chạy | Đồng bộ sau khi chốt N1 |
| T10 | **Chuỗi trích xuất được đo có điều kiện.** 82 đơn vị của 02 đều là loại mà cascade nhận đúng và bộ tách để nguyên tệp (tự ghi ở Hạn chế). Số "0 sai" không gồm lỗi lan truyền từ tách/phân loại. | `02_chain_with_images/RESULTS.md:43` | Lỗi hạn toàn trình bị đánh giá thấp | Báo thêm chuỗi trên mọi lát cắt `auto_file` dev, kể cả lát sai loại |

## 4. Phát hiện nhỏ

* 02: bootstrap ghép cặp loại trừ 0 ([+1,5; +15,2]) trong khi kiểm định dấu chính xác cho p = 0,0625; với 5 cặp lệch cùng chiều, bootstrap percentile lạc quan. Nên lấy kiểm định chính xác (McNemar/dấu) làm câu chính. RESULTS đã nói "ở mức biên", đúng.
* 03 `RESULTS.md:185`: "tb không đổi quyết định nào ở 59 tệp" sai. Tầng quyết định đổi ở 3/59 tệp TEST (`0b539608cb6b`, `6d975a7e4312`, `dbc8b0c354da`: TF-IDF → luật, cùng nhãn đúng). Đây thật ra là bằng chứng nhỏ có lợi (3/3 đúng), nên ghi đúng.
* `src/splitting/policy.py:97,108`: `info.scores` lưu điểm **trước** khi quy tắc `id` ghi đè thành 1,0, nên điểm trong đầu ra/nhật ký không cho thấy ranh giới do `id` thêm. Không ảnh hưởng tách hay cờ triage, chỉ ảnh hưởng chẩn đoán.
* Khóa cache LLM/VLM gồm **tên** mô hình (`qwen3.5:4b`), không gồm digest (`src/extraction/field_vlm.py:79`, `field_llm.py:145`, `classification/zero_shot.py:153`). Ollama dùng chung: nếu ai đó pull bản mới cùng tên, cache trả câu trả lời của mô hình cũ mà không báo. Thêm digest (`/api/show`) vào khóa.
* Đổi khóa VLM `t4-src-vlm-v1` → `v2` làm mất cache một lần; 02 chưa chạy lại sau khi đổi (03 tự ghi ở "Chưa chứng minh" 6). Nên chạy lại 82 đơn vị khi GPU rảnh để xác nhận 37/66.
* team3 04 không tái lập được 98,3% cross-fit của 02 (233 so với 235, `04_safety_margin/RESULTS.md:54`). Chênh 2 tài liệu chưa rõ nguyên nhân.
* Đáp án hướng trang (team1 05) do mô hình đọc; một trang được sửa sau khi đối chiếu với OCR (đã tự ghi).
* TEST lần 2 chạy 68 giây sau khi dev xong. Hợp lệ theo quy tắc, nhưng không có bước người đọc lại quyết định trước khi mở TEST.

---

## 5. Điều đã đo được và đứng vững (để dùng trong thiết kế)

| Mệnh đề | Số đo (n, CI) | Mức tin |
|---|---|---|
| Cascade phân loại tài liệu đơn rất ít lỗi | DEV cross-fit 0/235 tự nhận sai (cận trên 1,27%); TEST 1/59 sai (cận trên 7,8%) | tốt trong phạm vi tài liệu đơn đã thấy; đáp án máy |
| Tách `model+merge` không làm hỏng nhiều tệp thường | 6/155 tệp nhiều trang dev có tách nhầm (3,9%); TEST 2/36 | trung bình |
| Lỗi âm thầm cấp tệp của toàn trình | S10: 14/237 dev (5,9%), 2/58 TEST; S10+id+tb: 5/237 dev (lạc quan), 2/58 TEST; gộp dev+TEST cấu hình mới 7/295 = 2,4% [CP 0,96; 4,8] | **chưa đạt 1%** |
| Nguồn lỗi âm thầm còn lại (S10+id+tb) | dev: 4/5 là composite bị **tách thiếu** (2 `BB_LAY_MAU`, 2 cùng loại khác), 1/5 TF-IDF nhận sai; TEST: 1 tách nhầm tệp thường, 1 LLM nhận sai tệp một trang | định hướng chính sách duyệt |
| `triage` giảm lỗi âm thầm, đổi bằng nhân sự | dev: 4/189 tự xử lý sai (2,1%), nhưng 22% tệp về người và chỉ 185/318 tài liệu giao tự động | tốt |
| Ảnh trang giúp VLM đọc hạn | +5/66 hạn tự nhận, 0 mất, 0 sai (p dấu 0,0625) | biên |
| Hạn tự nhận 4 loại cũ | 0 sai trên 37 (dev 02) + 12 (TEST giai đoạn 2) = 49; cận trên một phía 5,9% gộp | phụ thuộc tên tệp (N2) |
| Chi phí theo giai đoạn | OCR 45%, trích xuất LLM+VLM 52%, tách+phân loại+dựng ảnh < 3%; VRAM đỉnh 6,6 GiB toàn GPU | 30 tệp, GPU dùng chung |
| Tự xoay trang | 30/32 trang bị xoay đúng hướng, 0/280 sót; 8 trang gần trống bị xoay nhầm đã có luật chặn | đáp án máy |

---

## 6. Kiến trúc chạy thật (khuyến nghị)

```
[Máy quét / thư mục mạng chỉ-ghi] --(PDF)--> [1. Bộ nạp]
     - băm sha256, khử trùng lặp, kiểm PDF mở được, đếm trang
     - ghi hàng đợi (SQLite/PostgreSQL nội bộ): file_id, trạng thái, thời điểm; KHÔNG ghi nội dung
                 |
                 v
[2. Worker GPU (một tiến trình/GPU, xử lý tuần tự từng tệp)]
     OCR VietOCR (cuda) -> tách model+merge -> phân loại cascade (luật -> TF-IDF -> Qwen3.5-4B qua Ollama 127.0.0.1)
     -> định tuyến từng lát cắt (auto_file / needs_human + lý do)
     -> trích xuất trường (luật + LLM; VLM chỉ cho loại có quy tắc hạn dùng ảnh; ảnh ở thư mục tạm, xóa ngay)
     -> ghi kết quả JSON vào kho nội bộ (mã hóa đĩa), nhật ký quyết định (không văn bản)
                 |
                 v
[3. Hàng đợi người duyệt (web nội bộ, đăng nhập theo vai trò)]
     - xem ảnh trang + ranh giới + loại + trường + ngày gợi ý; sửa/duyệt; ghi thời gian thao tác
     - mọi sửa của người = nhãn mới (vào kho dữ liệu cho vòng huấn luyện sau)
                 |
                 v
[4. Xuất]  ERP (CSV/API: loại, số hiệu, bên, ngày ký, ngày hết hạn, đường dẫn tệp)
           Lịch nhắc hạn: nhắc ở 90/60/30/7 ngày trước hạn; CHỈ dùng ngày đã "accepted" hoặc người duyệt
[5. Giám sát] bảng số: tệp/ngày, tỉ lệ tự xử lý, tỉ lệ sửa của người theo loại, lỗi kiểm mẫu, độ trễ, lỗi Ollama
```

Ghi chú thiết kế:

* **Một GPU, tuần tự.** OCR và Qwen3.5-4B tranh cùng GPU; 08 cho thấy thêm worker OCR không tăng tốc trên máy dùng chung. Chạy song song OCR của tệp sau với trích xuất của tệp trước là hướng tăng tốc chưa đo.
* **Idempotent theo sha256**: nạp lại cùng tệp không xử lý lại; kết quả gắn phiên bản cấu hình (preset tách, quy tắc hạn, digest mô hình, sha schema) để truy vết.
* **Không bao giờ để lỗi đi thẳng vào ERP**: mọi lát cắt `needs_human`, mọi trường hạn không `accepted`, mọi tệp bị cắt trang (T2) phải qua hàng đợi.
* **Ngày hết hạn là trường có hậu quả** (nhắc gia hạn giấy phép, bảo hiểm, kiểm định): lịch nhắc chỉ nhận ngày đã được người duyệt hoặc tự nhận bởi quy tắc đã qua chạy bóng.

## 7. Cấu hình mặc định nên dùng (chạy bóng và 3 tháng đầu)

| Tùy chọn | Khuyến nghị | Căn cứ |
|---|---|---|
| Tách | `model+merge` (S10) | chọn trên dev ở thí nghiệm 01, TEST 56/59; không phụ thuộc thiết kế trên composite |
| Quy tắc `id` ("bản khác") | **Không** dùng để tự tách; dùng làm **cờ chuyển người** (tệp có trang bị cờ → hàng duyệt "kiểm ranh giới") | dev: kích hoạt 3/245 tệp, 0/448 cặp mẫu âm; chi phí duyệt ~1% tệp; thu được dữ liệu kiểm giữ ngoài |
| `title_tiebreak` | **Tắt** khi quyết định; chạy song song "ở chế độ bóng" và ghi nhãn nó sẽ chọn | N1; 28/28 đúng nhưng chỉ 1 nhà cung cấp; tầng luật không có độ tin cậy |
| `triage` | Không mặc định; là lựa chọn kinh doanh nếu chi phí một lỗi âm thầm > chi phí duyệt ~22% tệp | dev 4/189 so với 14/237 (S10) |
| LLM phân loại | Qwen3.5-4B qua Ollama cục bộ, timeout 45 s/lời gọi, 90 s/tệp (mặc định hiện có) | TEST 0,983 [0,949; 1,000] |
| VLM cho hạn | Bật cho 4 loại cũ (đo được +5/66); với loại mới chỉ bật nếu quy tắc hạn dùng `vlm` | 02; T3 |
| Tự nhận ngày hết hạn | **Tắt trong chạy bóng** (mọi ngày là gợi ý); sau chạy bóng chỉ bật quy tắc nào đạt ≥ 299 lần tự nhận không lỗi trên dữ liệu thật | N2, N3 |
| Trường định danh cá nhân | Giữ tắt (`store_personal_ids = False`) | thiết kế hiện có |
| Kiểm mẫu | Tắt cho tới khi sửa T1; sau đó 10% trong 3 tháng đầu, 5% khi ổn định | T1; 04 §3 |
| Tệp > 30 trang | Chuyển người (hoặc OCR hết) | T2 |
| Xoay trang | Bật, với `min_chars_for_rotation = 30` | team1 05 |

## 8. Chi phí phần cứng và thời gian

**Mô hình thời gian một tệp** (từ đo của 03 trên RTX 3060 dùng chung; 3,36 trang/tệp theo cơ cấu kho mẫu): `t = trang × 4,17 s + p_vlm × 33,9 s + p_llm_only × 13,3 s`.

| Kịch bản | p_vlm | p_llm_only | s/tệp | trang/giờ (1 máy) |
|---|---|---|---|---|
| A. Như đo ở 03 (4 loại có schema) | 0,273 | 0,069 | 24,2 | ~500 |
| B. 17 loại mới tích hợp, VLM cho mọi loại có hạn (mã hiện tại, T3) | 0,533 | 0,069 | 33,0 | ~365 |
| C. Như B nhưng chỉ dựng ảnh khi quy tắc dùng VLM | 0,273 | 0,329 | 27,6 | ~440 |
| D. Không trích xuất (chỉ OCR + tách + phân loại) | 0 | 0 | 14,0 | ~860 |

Số máy cần (giả định: kịch bản B, cửa sổ chạy 20 giờ/ngày vì tài liệu không cần xử lý trong vài phút, mức sử dụng 60% để dự phòng nạp lại mô hình, thử lại, đỉnh khối lượng; **chưa đo trên máy riêng**, xem T7):

| Khối lượng | Giờ GPU cần/ngày | Năng lực 1 máy (365 × 20 × 0,6 ≈ 4.400 trang/ngày) | Số máy |
|---|---|---|---|
| 500 trang/ngày | ~1,4 h | dư nhiều | 1 (có thể chạy trong giờ hành chính) |
| 2.000 trang/ngày | ~5,5 h | đủ | 1 (chạy ca chiều và đêm); 2 nếu đòi xử lý xong trong 8 giờ làm việc |
| 10.000 trang/ngày | ~27 h | 10.000 / 4.400 ≈ 2,3 | 3 máy (hoặc 6 máy nếu chỉ chạy 8 giờ/ngày) |

Giả định giá (chưa có báo giá thật): một máy trạm RTX 3060 12 GB khoảng 25–35 triệu đồng; công suất khi tải ~250–350 W, tức ~6–8 kWh/ngày nếu chạy 24 giờ. Số máy có sai số lớn vì thông lượng đo trên GPU dùng chung, một lần chạy; số tham chiếu cũ 0,35 trang/giây (OCR) cho thấy máy riêng có thể nhanh hơn tới ~1,5 lần nhưng chưa tái lập được.

**Thời gian người duyệt: CHƯA CÓ SỐ.** Ước lượng tải hàng đợi ở 2.000 trang/ngày (~600 tệp): tệp không tự xử lý 3,2% (~19 tệp), trường hạn cần duyệt của 4 loại cũ ~44% × 27% (~71 tài liệu), trường của 17 loại mới khi chưa tự nhận ~26% (~156 tài liệu), kiểm mẫu 10% (~58 tệp), cờ `id` ~1% (~6 tệp): **~300 mục/ngày**. Nếu mỗi mục mất 1–2 phút (giả định), đó là 5–10 giờ công/ngày. Đo thời gian thao tác thật là việc ưu tiên của chạy bóng.

**So với gọi API LLM đám mây (giả định, không có giá thật trong repo).** Chi phí mỗi tài liệu = `(token vào × giá vào + token ra × giá ra) / 10^6`. Ước lượng token: văn bản OCR trung vị 1.379 ký tự/trang (đo trên `ocr_v2.jsonl`, 1.084 trang), tiếng Việt khoảng 3 ký tự/token → 2 trang + prompt + taxonomy ≈ 2.000–3.000 token vào, ~300 token ra; phương án đọc ảnh 4 ảnh × ~1.500 token + prompt ≈ 7.000 token vào, ~400 ra (số token/ảnh tùy nhà cung cấp và độ phân giải). Với dải giá minh họa 0,1–3 USD/triệu token vào và 0,4–15 USD/triệu token ra (phải tra bảng giá hiện hành trước khi dùng), chi phí khoảng **0,001–0,03 USD/tài liệu**, tức ~3–90 USD/ngày ở 10.000 trang (~3.000 tài liệu). Về tiền, API có thể rẻ hơn mua 3 máy trong năm đầu. Nhưng:

* **Rủi ro quyền riêng tư là quyết định chính**: CCCD, GPLX, hợp đồng có dữ liệu cá nhân; gửi ra nước ngoài thuộc phạm vi Nghị định 13/2023/NĐ-CP và Luật Bảo vệ dữ liệu cá nhân (hiệu lực 01/01/2026): cần hồ sơ đánh giá tác động, đồng ý của chủ thể dữ liệu hoặc căn cứ pháp lý khác, hợp đồng xử lý dữ liệu với nhà cung cấp. Pháp chế công ty phải xác nhận; báo cáo này không phải ý kiến pháp lý.
* Phụ thuộc mạng và nhà cung cấp; nhà cung cấp đổi mô hình làm số đo hết hiệu lực.
* Đề bài đặt on-premise; giữ phương án đám mây chỉ làm **đối chứng** (như silver), và chỉ với tài liệu đã được công ty duyệt.

## 9. Quyền riêng tư và lưu trữ

1. **On-premise hoàn toàn**: Ollama chỉ lắng nghe `127.0.0.1`; máy xử lý không có đường ra Internet (tường lửa chặn chiều ra, trừ cập nhật có kiểm soát); kiểm định kỳ bằng nhật ký tường lửa.
2. **Không gửi tài liệu mới ra ngoài** (kể cả cho silver, cho "LLM mạnh hơn phân xử") nếu chưa có văn bản duyệt cho từng đợt; mọi đợt đã duyệt ghi sổ (ngày, số trang, mục đích, nhà cung cấp).
3. **Dữ liệu cá nhân**: không lưu số CCCD/GPLX, ngày sinh (đã tắt mặc định); hàng đợi người duyệt hiển thị ảnh, nhưng xuất ERP chỉ các trường nghiệp vụ.
4. **Nhật ký**: chỉ `file_id`, sha256, `slice_id`, tầng, nhãn, độ tin cậy, mã lý do, thời gian (như `decision_log`); không văn bản, không giá trị trường. Thông báo lỗi LLM đã che chuỗi số ≥ 5 chữ số; giữ nguyên quy ước.
5. **Cache LLM/VLM** (`cache/llm`, `_cache/ollama`) chứa giá trị trường trích xuất (có thể có họ tên): đặt trên ổ mã hóa, xóa theo hạn (ví dụ 30 ngày), không sao lưu ra ngoài.
6. **Ảnh trang**: chỉ ở thư mục tạm, xóa sau mỗi lát cắt (đã làm trong pipeline); không lưu ảnh dựng lại. PDF gốc ở kho tài liệu của công ty, phân quyền như hiện tại.
7. **Repo mã nguồn không chứa dữ liệu thật** (N4): dữ liệu nghiên cứu ở ổ nội bộ riêng; kiểm `git ls-files` trước mỗi lần push (một hook pre-commit chặn `*.pdf`, `*.jsonl` dưới `data/`).

## 10. Kế hoạch chạy bóng với công ty

**Hình thức.** 6–8 tuần. Nhân viên xếp hồ sơ như hiện nay, không thấy kết quả máy. Máy xử lý cùng tệp, kết quả ghi riêng. Cuối mỗi tuần, một người thứ hai (nhân viên có kinh nghiệm) xem **mọi tệp bất đồng** giữa người và máy, cộng **5% tệp đồng thuận rút ngẫu nhiên** (để ước lượng lỗi chung của người và máy), và quyết định đáp án.

**Cỡ mẫu.**

| Mục tiêu | Cỡ mẫu tối thiểu (Clopper–Pearson một phía 95%) | Ghi chú |
|---|---|---|
| Lỗi âm thầm trên tệp tự xử lý ≤ 1% | 299 tệp với 0 lỗi; 473 với ≤ 1; 628 với ≤ 2; 773 với ≤ 3 | mức hiện tại ~2–3% nên dự kiến **không đạt**; cần ≥ 1.000 tệp để ước lượng mức thật với sai số ~±1 điểm |
| Lỗi âm thầm ≤ 2% (nếu doanh nghiệp chấp nhận) | 149 với 0 lỗi; 236 với ≤ 1; 314 với ≤ 2 | |
| Ngày hết hạn tự nhận ≤ 1% | ≥ 299 trường tự nhận không lỗi, **theo từng quy tắc** | hiện có 49 (4 loại cũ) và 12 ngoài mẫu (loại mới) |
| Kiểm `id` và `tiebreak` giữ ngoài | ≥ 30 tệp composite mỗi loại (khác loại, cùng loại ngoài BB) từ ≥ 3 nhà cung cấp; ≥ 100 tài liệu mà tiebreak đổi quyết định | lấy mẫu dồn: yêu cầu công ty gom riêng tệp ghép |

**Thước đo.** (1) Tệp đúng hoàn toàn và lỗi âm thầm cấp tệp, theo nhóm (một trang / nhiều trang / ghép); (2) tài liệu giao đúng và tự động; (3) tỉ lệ tự xử lý; (4) ngày hết hạn: tự nhận, đúng, sai, gợi ý đúng; (5) thời gian người duyệt mỗi mục (đo trong giao diện); (6) thông lượng và độ trễ p95 trên máy sản xuất **riêng**; (7) lỗi hệ thống: Ollama hết giờ, PDF hỏng, tệp bị cắt trang; (8) quyết định "bóng" của `tiebreak` và `id` (đúng/sai khi chúng khác S10).

**Tiêu chí chấp nhận (đề xuất, công ty chốt trước khi bắt đầu).**

1. Lỗi âm thầm cấp tệp: cận trên 95% ≤ 1% (hoặc mức công ty chọn, ghi trước), tính trên tệp tự xử lý **liên tiếp** của cấu hình đóng băng.
2. Ngày hết hạn: chỉ bật tự nhận cho quy tắc đạt ≥ 299 lần không lỗi; một lỗi tự nhận hạn trong chạy bóng → quy tắc đó giữ thủ công và phân tích nguyên nhân.
3. Không loại tài liệu nào có tỉ lệ người sửa > 10% được tự động (theo loại, cần ≥ 30 tài liệu/loại để xét).
4. Thông lượng ≥ 1,5 lần khối lượng ngày cao điểm trong cửa sổ chạy.
5. Kiểm quyền riêng tư đạt: không có kết nối ra ngoài từ máy xử lý, nhật ký không chứa văn bản/giá trị trường.
6. Đổi cấu hình giữa chừng thì đồng hồ đếm "liên tiếp" chạy lại từ đầu.

**Sau chạy bóng.** Dữ liệu người duyệt thành đáp án thật đầu tiên: tính lại mọi số trong README; lấy 20% làm TEST v2 khóa (phân tầng, có composite), phần còn lại làm DEV v2.

## 11. Việc còn lại theo thứ tự ưu tiên (cho các nhóm sinh viên)

| Ưu tiên | Việc | Nhóm | Ước lượng |
|---|---|---|---|
| 1 | Xác nhận quyền dùng dữ liệu và trạng thái repo; gỡ dữ liệu thật khỏi git nếu cần; thêm hook chặn (N4) | 00 + chủ phiên | 1–2 ngày |
| 2 | Chốt mặc định: S10, `tiebreak` tắt nhưng chạy bóng, `id` thành cờ chuyển người; sửa README/docstring (N1, T9) | 00, 2, 3 | 1 ngày |
| 3 | Tắt tự nhận hạn cho 17 loại mới (chỉ gợi ý) trong `field_extractor.py` (N3); phối hợp với agent đang tích hợp | 4 | 0,5 ngày |
| 4 | Sửa khóa kiểm mẫu theo tệp + test (T1) | 3 | 0,5 ngày |
| 5 | Tệp > 30 trang → người, có test (T2) | 00/1 | 0,5 ngày |
| 6 | Chỉ dựng ảnh khi quy tắc dùng VLM; xếp trang có từ khóa hạn vào 4 ảnh gửi đi; đo lại trên DEV (T3, T4) | 4 | 2–3 ngày |
| 7 | Hỏi công ty về quy ước tên tệp; đo `regex=vlm` / `regex=llm=vlm` cho 4 loại cũ không dùng tên tệp (N2) | 4 + công ty | 2 ngày |
| 8 | Dựng hệ chạy bóng: bộ nạp, hàng đợi, giao diện duyệt có đo thời gian, bảng giám sát | 00 + mọi nhóm | 2–3 tuần |
| 9 | Đo thông lượng trên máy riêng (3 lần lặp, 200 tệp), thử chồng OCR/LLM | 1 | 3 ngày |
| 10 | Nhân viên kiểm đáp án: 19 tệp composite, 59 tệp TEST, 100 trường hạn ngẫu nhiên; tính lại số chính | 00 + công ty | 1 tuần |
| 11 | Thu thêm tệp ghép từ ≥ 3 nhà cung cấp; đo lại `id`/`tiebreak` giữ ngoài | 2, 3 | theo dữ liệu |
| 12 | Thêm digest mô hình Ollama vào khóa cache; chạy lại 02 sau khi đổi khóa VLM | 3, 4 | 1 ngày |
| 13 | Sửa chọn nhầm 90/270 ở sổ PCCC; OCR lại 10 trang gần trống | 1 | 2 ngày |
| 14 | Cách D: hỏi LLM khi luật mơ hồ (thay tiebreak) khi GPU rảnh | 3 | 2 ngày |
| 15 | Cải tiến prompt cho trường văn bản dài (42 lỗi `llm_miss` DEV v2) | 4 | 1 tuần |

---

## Phụ lục: cập nhật sau review (2026-10-16, quyết định của công ty)

*Thân báo cáo ở trên giữ nguyên như lúc review; phụ lục này chỉ ghi điều đã thay đổi sau đó. Quyết định do chủ dự án truyền đạt, chưa có văn bản.*

**1. Câu hỏi về quy ước tên tệp (N2, việc 7) đã được trả lời.** Nguyên ý chủ dự án (nói tắt): *"ngày trong tệp phải cụ thể là ngày gì thì mới là ngày hết hạn"*. Diễn giải của nhóm (cần xác nhận lại nếu khác): một ngày chỉ là ngày hết hạn khi tài liệu ghi cụ thể đó là ngày gì ("có hiệu lực đến ngày…", "ngày hết hạn…"); ngày trong tên tệp không mặc nhiên là hạn; một số giấy tờ không có hạn. Hệ quả cho các phát hiện ở trên:

* **N2 được xác nhận theo hướng bất lợi cho quy tắc.** `any-model=filename` không được dùng như nguồn xác nhận độc lập. Các số "0 sai trong 49 lần tự nhận" (mục 5) vẫn đúng như phép đo, nhưng không còn là cơ sở để bật tự nhận. Việc 7 đổi thành: bỏ/thay quy tắc dựa tên tệp (đo `regex=vlm`, `regex=llm=vlm` trên DEV), xem T8 trong [README nhóm 4](../../team4_extraction/README.md). Tự nhận ngày hết hạn vẫn **tắt** (`auto_accept_expiry=False`), đúng khuyến nghị mục 7.
* **Trường `ngay_het_han` = `not_present` là kết quả hợp lệ** với loại giấy tờ không có hạn (14 trong 17 lần ngày tên tệp đứng một mình sai ở N2 là giấy không có hạn). Bộ chấm và báo cáo không được tính đó là bỏ sót; quy ước phân xử "kể từ ngày ký" → `not_present` là phù hợp. Tiêu chí chấp nhận mục 10 (≥ 299 lần tự nhận không lỗi theo từng quy tắc) áp dụng cho quy tắc thay thế, không cho `filename`.
* **N4 (dữ liệu và đám mây):** công ty cho phép dùng LLM bên ngoài (đám mây) để **tạo đáp án** trên tài liệu mẫu; sản xuất vẫn on-premise. Điều này giải quyết phần "việc gửi ảnh mẫu cho API để dựng đáp án" của câu hỏi cần văn bản duyệt, nhưng **không** thay đổi: dữ liệu thật vẫn đang nằm trong git (cần xác nhận nơi lưu và dọn), và mọi tài liệu mới vẫn chỉ đi qua mô hình cục bộ (mục 9). Nên có văn bản ghi lại quyết định.
* Mục 10 ("cần gì từ công ty"): bỏ yêu cầu "quy trình đặt tên tệp thật" như điều kiện chặn; còn ~100 tên tệp thật là tùy chọn nếu muốn dùng tên tệp làm tín hiệu phụ (kiểm chéo).

**2. Hướng đi ban đầu.** Bản nguyên văn các tài liệu tổng quan cũ và bảng đối chiếu "giữ/đổi/bỏ/chưa kiểm" nằm ở [`docs/original_direction/README.md`](../../../docs/original_direction/README.md).
