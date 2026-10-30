# Phương pháp luận nghiên cứu (tài liệu chuẩn)

> Trạng thái ngày 2026-10-16 (sau giai đoạn 2: tách trang, trích xuất trường, đo toàn trình; và giai đoạn 3: 21 loại có trường, ảnh trang cho VLM, review độc lập; mục 6 có các dòng O5–O7, S6, C4–C5, X3, E2–E3, R4). Đây là văn bản chuẩn về **cách làm và cách báo cáo** của đề tài. Khi một tài liệu khác trong kho nói khác về phương pháp, tài liệu này và [giao thức đánh giá](../teams/00_data_and_eval/reports/03_evaluation_protocol.md) thắng; khi nói khác về một con số, tệp `RESULTS.md` sinh ra con số đó thắng.
> Người đọc: sinh viên năm cuối ngành AI tiếp tục đề tài. Đọc [`HANDBOOK_FOR_RESEARCHERS.md`](HANDBOOK_FOR_RESEARCHERS.md) trước để dựng môi trường; kiến trúc đề xuất ở [`VISUAL_ARCHITECTURE.md`](VISUAL_ARCHITECTURE.md).
> Bản trước của tệp này mô tả một hệ thống 19 danh mục với các con số tốc độ và độ chính xác chưa từng được đo; nội dung đó đã bị thay toàn bộ (mục 11).

## 1. Đề tài và câu hỏi nghiên cứu

Một công ty kinh doanh xăng dầu quét hồ sơ giấy thành PDF. Hệ thống cần: đọc chữ (OCR), tách tệp ghép thành từng tài liệu, nhận loại tài liệu, và lấy các trường quan trọng (trước hết là ngày hết hạn) đưa vào ERP. Đây là ứng dụng thật, không phải bài báo: kết quả được dùng để quyết định có triển khai hay không, nên một con số sai lạc quan gây hại nhiều hơn một con số thấp nhưng thật.

**Câu hỏi trung tâm.** Với hồ sơ quét của công ty, một hệ thống chạy hoàn toàn tại chỗ tự xử lý đúng được bao nhiêu phần trăm tài liệu ở mức sai công ty chấp nhận, với chi phí phần cứng và thời gian bao nhiêu, và phần còn lại được chuyển cho người như thế nào?

Ba trục phải được trả lời cùng lúc: **chính xác** (ở dạng "tự xử lý được bao nhiêu với sai tối đa bao nhiêu", không phải độ chính xác trung bình), **chi phí** (VRAM, giây mỗi trang, công gán nhãn), **riêng tư** (chạy được on-premise hay không).

| # | Câu hỏi con | Trạng thái | Nơi trả lời |
|---|---|---|---|
| Q1 | Nhãn của bộ mẫu có đúng và đủ để đo không? | Một phần: nhãn theo nội dung đã có, hai lượt gán của mô hình trùng nhau; **chưa có người của công ty kiểm** (và cũng chưa kiểm đáp án ranh giới và đáp án trường, đều do máy tạo) | mục 2–3, 9.1 |
| Q2 | Engine OCR cục bộ nào giữ được dấu tiếng Việt, nhanh đến đâu? | Đã đo trên trang số hóa và so với bản chép LLM; mã trong `src/` cho lại đúng bộ dữ liệu trên GPU; **chưa đo trên đáp án do người gõ** | mục 6, O1–O4 |
| Q3 | Chất lượng OCR có ảnh hưởng tới phân loại không? Tới trích xuất? | Phân loại: không tách được trong khoảng nhiễu. Trích xuất: **có**, tập trung ở chữ viết tay và chữ dưới con dấu (luật đúng 0,53 và 0,35 trên OCR cục bộ, 0,82 và 0,95 trên bản chép của LLM đám mây; dev, chưa có khoảng tin cậy ghép cặp) | mục 6, C1–C2, X1 |
| Q4 | Một baseline rẻ phân loại được bao nhiêu, và tự xếp hồ sơ được bao nhiêu? | Đã đo | mục 6, C1 |
| Q5 | Loại hiếm (không đủ dữ liệu huấn luyện) xử lý thế nào? Mô hình có biết khi nào nó không biết? | Đã đo trên bộ mẫu; tổng quát hóa **chưa đo** | mục 6, C2 |
| Q6 | Tách tệp ghép đạt mức nào? | Đã đo trên đáp án ranh giới do máy dựng. Ở cấp tệp: tách **không tăng** tỉ lệ tệp đúng hoàn toàn (dev 91,9% so với 92,3%, không tách được). Ở cấp tài liệu: có lợi (87,7% so với 70,4%). Tệp ghép khác loại: tách tốt nhưng phân loại lát cắt kém. Giai đoạn 3: quy tắc `id` đưa nhóm cùng loại từ 0/7 lên 4/7 ranh giới (6 tệp), chưa có kiểm giữ ngoài | mục 6, S1–S6, E1, E3; [nhóm 2](../teams/team2_splitting/README.md) |
| Q7 | Trích xuất trường (ngày hết hạn) đạt mức nào? | Đã đo trên 4 loại, đáp án silver (chưa người kiểm): F1 nới lỏng 0,90 (TEST n = 22); hạn tự nhận 12/16 sai 0 (TEST). Giai đoạn 3: thêm 17 loại (84 đơn vị silver v2; F1 mềm 0,75 LLM, 0,83 VLM), ảnh trang cho VLM (hạn đúng và tự nhận 32 → 37/66, sai 0, p dấu 0,0625); tự nhận hạn nay **tắt mặc định** vì phụ thuộc quy ước tên tệp và cùng nguồn OCR; **sai ≤ 1% chưa chứng minh** | mục 6, X1, X3, E2; [nhóm 4](../teams/team4_extraction/README.md) |
| Q8 | Khâu nào là điểm nghẽn của toàn trình? | Một phần. Thời gian: OCR, rồi trích xuất (>98% thời gian sau OCR). Độ chính xác: phân loại lát cắt với tệp ghép khác loại (8 tệp, giả thuyết), và đọc sai chữ số ngày hết hạn trên OCR (khoảng 6% trường hạn). Bảng E0–E3 (ΔF₁ theo khâu) **chưa chạy** | mục 6, E1; [`PARALLEL_RESEARCH_PLAN.md`](PARALLEL_RESEARCH_PLAN.md) mục 4 |

## 2. Dữ liệu và đơn vị đánh giá

**Bộ mẫu.** 336 tệp PDF trong `docs/_chot_samples_phanloaitailieu/` (334 tệp trong 19 thư mục cũ, 2 tệp ở gốc); 304/336 là bản quét. Danh mục tệp: `data/manifest.csv`.

**Khử trùng lặp.** 30 nhóm tệp giống hệt từng byte (62 tệp) được gộp, còn **304 tài liệu duy nhất**. 27 trong 30 nhóm nằm ở từ hai thư mục cũ trở lên: cùng một tờ giấy, hai "nhãn thư mục". Đó là bằng chứng thư mục cũ là tủ hồ sơ (hồ sơ khách hàng, hồ sơ xe, hồ sơ cửa hàng), không phải loại tài liệu, và là lý do cách làm cũ — nhãn = tên thư mục — bị bỏ. Nguồn và cách kiểm ngưỡng: [`01_duplicates.md`](../teams/00_data_and_eval/reports/01_duplicates.md).

**Đơn vị đánh giá là tài liệu duy nhất**, không phải tệp. Nếu chấm trên 336 tệp, cùng một tờ giấy nằm ở cả tập huấn luyện lẫn tập kiểm tra.

**Nhóm biểu mẫu** (`template_group` trong manifest): 39 nhóm gồm 161 tài liệu là các bản điền khác nhau của cùng một biểu mẫu (khác khách hàng, khác ngày). Chúng không phải bản trùng, nhưng nếu nằm ở hai phía train/test thì mô hình chỉ cần nhớ biểu mẫu. Vì vậy chia dữ liệu phải theo nhóm (mục 4.2).

**Tệp ghép** (composite): 21 tệp chứa từ hai tài liệu trở lên. 8 tệp ghép **khác loại** không có một nhãn duy nhất nên bị loại khỏi benchmark phân loại và dành cho bài toán tách tài liệu (`data/splits/excluded_composites.csv`); 13 tệp ghép **cùng loại** vẫn ở lại. Benchmark phân loại vì vậy có **296 tài liệu**. Quy tắc thế nào là một tài liệu: [`COMPOSITE_DOCUMENTS_AND_SPLITTING.md`](COMPOSITE_DOCUMENTS_AND_SPLITTING.md).

Luôn ghi mẫu số khi nêu một con số đếm: `PHIEU_XUAT_KHO` là 21 tài liệu theo nhãn chính nhưng 15 trong benchmark, vì 6 tệp ghép khác loại mang nhãn chính này bị loại.

## 3. Nhãn: định nghĩa, quy trình gán và phân xử

**Taxonomy v2** (`data/taxonomy_v2.json`): 36 mục trong 8 nhóm, gồm 34 loại theo nội dung cùng hai nhãn đặc biệt `OTHER` (đọc được nhưng ngoài danh mục) và `UNREADABLE`. Định nghĩa từng loại, phép thử cho tệp ghép và 14 ví dụ có lời giải: [`LABELING_GUIDELINE.md`](LABELING_GUIDELINE.md). Lý do thiết kế: [`02_taxonomy_design.md`](../teams/00_data_and_eval/reports/02_taxonomy_design.md).

**Phân bố** (tính trên tài liệu duy nhất, từ `data/labels_v2.csv`; bảng theo loại ở [`data/classified_v2/README.md`](../data/classified_v2/README.md)): chỉ **10 loại có từ 10 tài liệu trở lên** (222 tài liệu trong benchmark); **24 nhãn hiếm** có 1–9 tài liệu, tổng 74 tài liệu. Chú ý chữ "34 loại" có hai nghĩa trong kho: taxonomy có 34 loại nội dung; còn benchmark có 34 nhãn *có mặt trong dữ liệu*, gồm 33 loại nội dung và `OTHER` (loại `CHUNG_THU_CHAT_LUONG` chỉ xuất hiện như một phần của tệp ghép, `UNREADABLE` chưa có tệp nào).

**Quy trình gán** (chi tiết: hướng dẫn gán nhãn mục 10):

1. Hai annotator gán độc lập, thứ tự tệp xáo trộn khác nhau, không thấy nhãn của nhau và không thấy thư mục cũ.
2. Đo đồng thuận bằng Cohen κ (mức đồng thuận đã trừ phần trùng do ngẫu nhiên) trên tài liệu duy nhất, và **báo riêng trên các tệp không được nêu tên trong hướng dẫn**, vì ví dụ trong hướng dẫn dùng tên tệp thật.
3. Mọi bất đồng, mọi nhãn độ tin cậy thấp, mọi `OTHER`/`UNREADABLE` đi vào phân xử; quyết định ghi vào `teams/00_data_and_eval/annotation/adjudication.csv` (tệp này chưa tồn tại: lần gán đầu không có bất đồng nào về loại); `scripts/build_labels_v2.py` hợp nhất thành `data/labels_v2.csv` và dừng với lỗi nếu còn bất đồng chưa phân xử.

**Trạng thái thật của lần gán đầu** (`teams/00_data_and_eval/annotation/agreement_summary.json`):

- Hai annotator **đều là mô hình AI**: A xem ảnh trang và đồng thời là bên thiết kế taxonomy, B chỉ đọc văn bản chép lại của hai trang đầu.
- `doc_type` trùng 304/304, κ = 1,0; trên 228 tài liệu không nêu tên trong hướng dẫn cũng 1,0. Cờ tệp ghép: κ = 0,86 (16 tệp cả hai đánh dấu, 5 tệp chỉ A).
- Trạng thái duyệt: 296 `agreed`, 5 `check_composite`, 3 `check_low_conf`.
- **Chưa có nhân viên công ty nào kiểm.** Hai mô hình cùng họ, cùng một hướng dẫn: κ cao chứng minh hai bên nhất quán, không chứng minh nhãn đúng. Tỉ lệ nhãn sai so với người của công ty: **chưa đo**.

Mọi báo cáo phải ghi tệp nhãn và mã băm của nó (hiện `labels_v2.csv`, sha1[:10] = `eb3348713a`) và nhắc lại rằng nhãn chưa được người kiểm.

## 4. Giao thức đánh giá (tóm tắt)

Văn bản đầy đủ, với từ khóa PHẢI / KHÔNG ĐƯỢC: [`03_evaluation_protocol.md`](../teams/00_data_and_eval/reports/03_evaluation_protocol.md). Mã: `teams/00_data_and_eval/eval/` (`harness.py`, `eval_metrics.py`, `eval_splits.py`). Dưới đây chỉ là phần phải thuộc.

### 4.1. Hai cách chấm (track)

- **Track S** (có huấn luyện, tập đóng): mỗi loại có từ 10 tài liệu trở lên là một lớp; mọi loại còn lại gộp thành `RARE_OR_OTHER` — lớp "hãy đưa cho người". Hiện là 10 lớp + lớp gộp (24 nhãn, 74 tài liệu).
- **Track Z** (zero-shot, tức phương pháp không dùng dữ liệu huấn luyện của mình: cổng luật, LLM): chấm trên toàn bộ taxonomy. Macro-F1 chỉ tính trên các loại có từ 3 tài liệu thật trở lên trong tập đang chấm (DEV: 20 loại; TEST: 10 loại); từ chối tính là sai.

### 4.2. Chia dữ liệu

- Chia theo nhóm biểu mẫu bằng `StratifiedGroupKFold`: khoảng 20% làm **TEST khóa (59 tài liệu)**, còn lại là **DEV (237 tài liệu)**; DEV chia tiếp 5 fold, lặp với 3 seed.
- Nhóm biểu mẫu lớn hơn 5 tài liệu được cắt tất định thành nhóm con, vì một biểu mẫu có thể chiếm gần hết một loại (23/24 chứng chỉ tập huấn). Đổi lại có rò rỉ biểu mẫu nhẹ. Biến thể nghiêm ngặt `splits_strict.csv` giữ nguyên khối và dùng để đo khả năng đọc biểu mẫu chưa từng thấy. Báo cáo phải nói dùng biến thể nào.
- **`data/splits/` là tập chia đã khóa.** Các tệp chia không chứa nhãn, nên sửa nhãn không làm tài liệu đổi DEV/TEST hay đổi fold; bộ chấm chỉ cảnh báo rằng mã băm nhãn đã khác lúc chia. Nếu benchmark có tài liệu chưa được gán tập (ví dụ thêm tài liệu mới), bộ chấm dừng với `SplitsOutOfDateError` thay vì âm thầm chia lại. Chia lại là quyết định có chủ ý (`load_or_make_splits(bench, rebuild=True)`, hoặc cờ `--rebuild-splits` của `run_all.py` thí nghiệm 01) và có giá: TEST mới khác TEST cũ, mọi số TEST đã báo cáo phải chấm lại, và TEST cũ coi như đã bị nhìn thấy. Mục 3.7 của giao thức còn ghi quy tắc cũ ("nhãn đổi thì phải sinh lại"); về điểm này, hành vi của bộ chấm và [`data/splits/README.md`](../data/splits/README.md) là chuẩn.

### 4.3. DEV để chọn, TEST khóa chấm một lần

- Mọi lựa chọn — đặc trưng, siêu tham số, prompt, độ dài đầu vào, ngưỡng, từ khóa luật — chỉ dùng DEV, qua dự đoán **out-of-fold** (mỗi tài liệu được dự đoán bởi mô hình không thấy nó khi huấn luyện).
- Cấu hình cuối được chốt và ghi ra tệp trước khi mở TEST. TEST chỉ mở bằng lệnh riêng (`--final-test`), mỗi cấu hình **một lần**; lệnh từ chối chạy lại cho cùng bộ nhãn.
- Không chỉnh gì sau khi nhìn điểm TEST, không đọc lỗi TEST để sửa luật hay prompt. Nếu đã làm, TEST đã "cháy" và cần một vòng dữ liệu mới.

### 4.4. Độ bất định và so sánh

- **DEV:** trung bình ± độ lệch chuẩn qua 15 điểm (3 seed × 5 fold). Số này hơi lạc quan khi cấu hình được chọn trên chính DEV. Các điểm không độc lập, đừng chia căn n để tạo khoảng tin cậy.
- **TEST:** khoảng tin cậy 95% bằng **bootstrap** — lấy mẫu lại theo tài liệu 2000 lần, lấy phân vị 2,5% và 97,5%.
- **So sánh hai phương pháp:** bootstrap **ghép cặp** (cùng mẫu lại cho cả hai), báo hiệu số, khoảng tin cậy và p. Khi khoảng tin cậy của hiệu chứa 0, viết **"không tách được hai phương pháp"**; không tuyên bố hơn kém vì điểm lệch nhau.
- Với TEST 59 tài liệu, một lỗi là 1,7 điểm phần trăm; chênh dưới khoảng 0,05–0,1 macro-F1 không phân biệt được.

### 4.5. Chỉ số nghiệp vụ: tự xếp hồ sơ ở mức sai cho trước

- **Tự xếp hồ sơ** (auto-file) = tỉ lệ tài liệu, tính trên mọi tài liệu, mà hệ thống tự nhận trong khi tỉ lệ sai trên phần đã nhận ≤ mức đặt (1% và 2%). Dự đoán `RARE_OR_OTHER` và `OTHER` không bao giờ được tự nhận.
- Ngưỡng chọn trên dự đoán out-of-fold của DEV sao cho phần được nhận lớn nhất mà vẫn thỏa mức sai; sau đó **áp nguyên** lên TEST và báo tỉ lệ nhận, số sai, kèm khoảng tin cậy.
- **Cross-fit** là ước lượng trung thực hơn ngay trên DEV: chọn ngưỡng trên 4 fold, áp lên fold thứ 5, lặp cho cả 5 fold.
- **"0 lỗi" chứng minh được gì.** Với k lỗi trong n tài liệu được nhận, báo cận trên 95% Clopper–Pearson của tỉ lệ sai (hàm `clopper_pearson_upper`); bootstrap cho khoảng [0; 0] khi k = 0 nên không dùng được. Quy tắc ba: 0 lỗi trong n tài liệu cho cận trên xấp xỉ 3/n. Muốn nói "sai ≤ 1%" cần khoảng 300 tài liệu tự nhận liên tiếp không lỗi; "≤ 0,5%" cần khoảng 600.

### 4.6. Nguồn văn bản phải được nêu tên

| Tên trong bộ chấm | Là gì | Vai trò |
|---|---|---|
| `ocr_v2_p1`, `ocr_v2_p12` | OCR cục bộ (VietOCR), trang 1 hoặc trang 1–2 | **điều kiện triển khai on-premise** |
| `haiku_p1`, `haiku_p12` | bản chép của Claude Haiku đọc ảnh trang | **cận trên**, không dùng được on-premise |
| `legacy_p1` | OCR cũ làm mất dấu, trang 1 | đối chứng chất lượng thấp |

Bản chép Haiku là **chuẩn bạc** (silver): bản tham chiếu do máy tạo, đã đo độ tin cậy trên trang có đáp án nhưng chưa được người kiểm. **Chuẩn vàng** (gold) là đáp án do người làm hoặc kiểm. Chuẩn bạc không thay được chuẩn vàng ở số liệu cuối.

## 5. Quy tắc báo cáo

1. **Không con số nào không có tệp kết quả.** Mọi số trong tài liệu phải sinh từ một script nằm trong kho và trỏ được tới tệp (`RESULTS.md` hoặc CSV). Số ghi tay, số "ước chừng" và mục tiêu đặt trước khi đo không được viết như kết quả.
2. **Tách ba loại phát biểu:** *Đã đo* (có script, có tệp), *Suy luận* (giải thích chưa kiểm chứng), *Chưa đo*. Điều chưa đo thì viết "chưa đo".
3. **Luôn kèm n và khoảng tin cậy.** Ví dụ đúng: "macro-F1 0,946 [0,847; 1,000], TEST, n = 59". Không làm tròn theo hướng đẹp hơn.
4. **Nêu điều kiện của con số:** tệp nhãn và mã băm, nguồn văn bản, biến thể chia, mô hình và phiên bản **thật sự đã chạy**, ngày chạy. Không gọi tên một mô hình khi nó không chạy.
5. **Nêu rõ on-premise hay không** cho mọi phương pháp, và mọi số trên nguồn Haiku phải ghi là cận trên.
6. **Kết quả vào bảng chung** `teams/team3_classification/results/results_table.csv` bằng `append_result_row` — chỉ thêm dòng, không sửa dòng cũ.
7. **Không đưa định danh cá nhân vào báo cáo:** không số giấy tờ, số điện thoại, số tài khoản, họ tên khách hàng. Các CSV lỗi và tệp dự đoán có tên tệp hoặc `doc_id` chỉ dùng nội bộ.
8. **Hạn chế là một mục bắt buộc** của mỗi `RESULTS.md`, viết trước khi viết kết luận.

## 6. Các thí nghiệm đã làm và kết luận

Mỗi dòng chỉ là tóm tắt; đọc mục hạn chế của tệp nguồn trước khi trích dẫn. Số phân loại: nhãn `labels_v2.csv`, TEST n = 59, khoảng tin cậy 95%. Số tách và trích xuất: đáp án do máy tạo (ranh giới `boundary_gold_v0.csv`; trường silver), **chưa người kiểm**; "dev" là phần dùng để chọn tham số, "TEST" là phần chấm một lần; mỗi dòng ghi rõ n.

| Mã | Thí nghiệm và nguồn | Câu hỏi | Kết luận đã đo |
|---|---|---|---|
| D1 | Trùng lặp và nhóm biểu mẫu — [`01_duplicates.md`](../teams/00_data_and_eval/reports/01_duplicates.md) | Bộ mẫu có trùng không? | 336 tệp → 304 tài liệu duy nhất; 27/30 nhóm trùng nằm ở nhiều thư mục; 39 nhóm biểu mẫu (161 tài liệu) |
| D2 | Taxonomy v2 và gán nhãn — [`02_taxonomy_design.md`](../teams/00_data_and_eval/reports/02_taxonomy_design.md), `agreement_summary.json` | Nhãn theo nội dung có nhất quán không? | 34 loại + 2 nhãn đặc biệt; hai mô hình trùng 304/304 (κ = 1,0); chưa có người kiểm |
| O1 | So sánh engine OCR — [`01_engine_bakeoff/RESULTS.md`](../teams/team1_ocr/experiments/01_engine_bakeoff/RESULTS.md) | Vì sao mất dấu, chọn engine nào? | Engine cũ chỉ có 9/67 chữ cái thường có dấu trong từ điển nhận dạng nên không thể xuất 58 chữ còn lại. Engine chọn (phát hiện dòng PP-OCRv5 + VietOCR): CER 0,082 trên 10 trang số hóa sạch (0,088 trên 39 trang), giữ 97,8% ký tự có dấu; trên 30 trang quét thật nhớ lại 80,1% số từ so với bản chép Haiku (engine cũ 16,8%) |
| O2 | Tập OCR v2 — [`02_dataset_v2/RESULTS.md`](../teams/team1_ocr/experiments/02_dataset_v2/RESULTS.md) | Chạy cả kho mất bao lâu, còn lỗi gì? | 1084 trang, 0 trang lỗi, 46,3 phút, 0,39 trang/giây (GPU, 6 worker); một tiến trình 5,9 giây/trang. Chữ viết tay vẫn sai và độ tin cậy của engine không báo được |
| O3 | Bản chép LLM làm chuẩn bạc — CSV trong `teams/team1_ocr/experiments/03_llm_silver/` | Bản chép Haiku đáng tin đến đâu? | Trên 39 trang số hóa so với text layer: nhớ lại 99,5% số từ, 99,97% ký tự có dấu, nhưng CER 0,105 (khác thứ tự đọc và ngắt dòng; VietOCR cùng trang: CER 0,088, nhớ lại 94,4% số từ). Haiku và Sonnet lệch nhau trung bình 2,8% CER trên 8 trang quét |
| C1 | Baseline cổ điển — [`01_classical_baselines/RESULTS.md`](../teams/team3_classification/experiments/01_classical_baselines/RESULTS.md) | Baseline rẻ làm được gì? OCR có quan trọng cho phân loại? | TF-IDF trên OCR cục bộ: macro-F1 TEST 0,946 [0,847; 1,000]; tự xếp 61,0% [49,2; 72,9] ở mức sai ≤ 1% (0 lỗi trong 36). Không tách được khỏi nguồn Haiku (+0,028 [0,000; 0,109]) hay khỏi OCR cũ (Haiku trừ OCR cũ: +0,056 [−0,004; 0,122]). Văn bản hơn hẳn ảnh trang (+0,269 [0,184; 0,360]). Chia nghiêm ngặt theo biểu mẫu: hai loại một-biểu-mẫu rơi về recall 0,05 và 0,00 |
| C2 | LLM, embedding, cascade — [`02_llm_and_cascade/RESULTS.md`](../teams/team3_classification/experiments/02_llm_and_cascade/RESULTS.md) | Loại hiếm, từ chối, chi phí? | Qwen3.5-4B zero-shot cục bộ: accuracy TEST 0,983 [0,949; 1,000], nhớ lại loại hiếm 10/11. Kev-0.8B: 0,96 DEV / 0,93 TEST khi chỉ đưa tên loại, sụp với mô tả dài và với OCR cũ. Cascade luật → TF-IDF → LLM → người: tự xếp 96,6–100% trên TEST với 0–1 lỗi trong 59 (cận trên 95% của tỉ lệ sai: 5–8%). Phân loại tốn 3 ms đến 1,2 giây mỗi tài liệu; OCR 5–12 giây mỗi tài liệu là nút cổ chai |
| C3 | Cascade trong `src/` — [`03_src_cascade/RESULTS.md`](../teams/team3_classification/experiments/03_src_cascade/RESULTS.md) | Mã `DocumentClassifier` trong `src/` ra cùng quyết định với thí nghiệm C2? | Không đo chất lượng mới. DEV: 237/237 tài liệu trùng bộ ba (tầng, nhãn, được nhận) và trùng cả tín hiệu trung gian. TEST, chạy đúng một lần chỉ để tái lập: 59/59 tự nhận, 1 sai, đúng dòng đã báo cáo ở C2 |
| O4 | Engine OCR trong `src/` — [`07_src_engine/RESULTS.md`](../teams/team1_ocr/experiments/07_src_engine/RESULTS.md) | Mã trong `src/ocr/` cho cùng văn bản với `data/ocr_v2.jsonl`? Chạy được khi không có mạng? | GPU: 8/8 trang (6 tài liệu) giống từng ký tự. CPU: 5/8 trang giống, 3 trang lệch (7 ký tự đổi trên 7 280). Cấu hình VietOCR trước đây tải từ mạng mỗi lần khởi động, nay nạp từ tệp kèm trong kho. Chặn kết nối trong tiến trình: 0 lần cố kết nối trên 1 trang; chưa ngắt mạng thật |
| S1 | Tách: luật cũ — [`01_rule_baseline`](../teams/team2_splitting/experiments/01_rule_baseline/RESULTS.md) | Bộ luật có sẵn tách đúng đến đâu? | Dev, đáp án máy: trên 155 tệp nhiều trang không ghép, tách nhầm 46,7 [41,4; 52,8] trên 100 vị trí, chỉ 50/155 tệp còn nguyên. Tệp ghép khác loại: bắt 19/20 ranh giới kèm 2 tách nhầm; cùng loại ngoài `BB_LAY_MAU`: 4/7; `BB_LAY_MAU`: 46/46 |
| S2 | Tách: luật v2 — [`02_rule_v2`](../teams/team2_splitting/experiments/02_rule_v2/RESULTS.md) | Sửa luật (tiêu đề phải mở đầu dòng, bỏ trang chữ ký, trang trống, trang "2/2") có đủ không? | Tách nhầm 30,1 [23,4; 36,4] trên 100 vị trí, 85/155 tệp còn nguyên; tệp ghép khác loại 19/20 và 0 tách nhầm. Tham số chọn tay sau khi xem lỗi của luật cũ nên số hơi lạc quan |
| S3 | Tách: phân loại từng trang rồi gộp — [`03_type_merge`](../teams/team2_splitting/experiments/03_type_merge/RESULTS.md) | Chỉ cần đổi loại giữa hai trang là đủ? | Không. Chỉ đổi loại (b0): tách nhầm 1,0 [0,1; 2,2], 151/155 tệp nguyên, nhưng chỉ bắt 13/20, 0/7, 0/46 ranh giới của ba nhóm ghép. Thêm dấu hiệu "bản khác" (b1): 14/20, 2/7, 38/46, nhưng tách nhầm lên 27,7 |
| S4 | Tách: bộ phân loại cặp trang — [`04_pair_classifier`](../teams/team2_splitting/experiments/04_pair_classifier/RESULTS.md), [tài liệu TEST](../teams/team2_splitting/experiments/RESULTS_test_docs_only.md) | Bộ phân loại học từ cặp trang có tốt hơn luật? | Dev (cross-validated theo nhóm biểu mẫu): c2 gradient boosting, ngưỡng 0,5, tách nhầm 9,6 [6,3; 12,7], 129/155 tệp nguyên (so luật cũ −37,1 điểm [−43,9; −32,0], tách được); ngưỡng 0,7: 139/155 nhưng `BB_LAY_MAU` còn 40/46; ngưỡng 0,9: 145/155 nhưng 12/46. Ba nhóm ghép: 20/20, 3/7, 44/46 ranh giới, **không tách được** khỏi luật. TEST (chấm một lần): 9/9 ranh giới trong 2 tệp `BB_LAY_MAU`, 5 tách nhầm trên 74 vị trí âm của 36 tệp |
| S5 | Tách: LLM cục bộ hỏi có/không — [`05_llm_zero_shot`](../teams/team2_splitting/experiments/05_llm_zero_shot/RESULTS.md) | Qwen3.5-4B zero-shot có tách được không? | Với một prompt: 0/20, 0/7, 1/46 ranh giới (19 tệp ghép + 20 tệp âm); tách nhầm ít (7/63 vị trí âm) vì gần như luôn trả "cùng tài liệu". Prompt thứ hai chưa chạy xong, nên chưa có bằng chứng về giới hạn của hướng zero-shot nói chung. Trung vị 1,2 giây mỗi cặp trang (GPU dùng chung) |
| X1 | Trích xuất trường — [`02_methods/RESULTS.md`](../teams/team4_extraction/experiments/02_methods/RESULTS.md) | Phương pháp nào trích đúng trường, và ngày hết hạn có tự nhận được không? | 4 loại, 104 đơn vị (dev 76, TEST 22), đáp án silver. Tốt nhất với OCR cục bộ: luật cho ngày/số/mã + LLM cho văn bản, F1 nới lỏng TEST 0,90 [0,83; 0,96] (dev 0,88); GLiNER 0,46. Đọc ảnh trang bằng mô hình cục bộ mạnh nhất (0,91) nhưng bị thổi phồng vì đáp án cũng đọc từ ảnh. Hạn: mọi phương pháp dựa OCR sai giá trị ở 0,05–0,06 số trường có đáp án; quy tắc "một mô hình đọc trùng ngày trong tên tệp" tự nhận 37/64 (dev) và 12/16 (TEST), sai 0 (cận trên 95%: 8% và 22%) |
| X2 | Dựng đáp án trường bằng LLM — [`gold/README.md`](../teams/team4_extraction/gold/README.md), [`silver_report.md`](../teams/team4_extraction/gold/silver_report.md) | Đáp án trường dựng bằng LLM đáng tin đến đâu? | Haiku đọc 104 đơn vị, Sonnet 40, Opus phân xử 58 trường. Haiku–Sonnet đồng thuận ngày 0,944, mã 0,950, số 1,000, văn bản 0,668 chặt / 0,932 nới. Haiku bị người phân xử coi sai ở 10/58 mục được đưa vào hàng đợi (17,2%), Sonnet 8/54 (14,8%). Chi tiết phương pháp: mục 9.1 |
| E1 | Toàn trình tách + phân loại theo tệp — [`01_end_to_end/RESULTS.md`](../teams/00_data_and_eval/experiments/01_end_to_end/RESULTS.md) | Tách có làm hệ thống tốt lên trên cơ cấu tệp thật? Mặc định nào? | Dev 245 tệp: tệp đúng hoàn toàn S0 (không tách) 92,3%, `model+merge` 91,9% (hiệu −0,4 [−2,9; +1,9], không tách được), luật cũ 53,4%, luật v2 67,5%. Tài liệu đúng và tự động: 87,7% so với 70,4%. Sai lặng lẽ: 4,94% so với 7,31% tổng số tệp; không biến thể nào đạt ≤ 1%. TEST 59 tệp (chấm một lần): cùng 56/59; tài liệu 65/68 so với 56/68. Mặc định chọn trên dev: `model+merge`. Chuỗi tới ngày hết hạn (82 đơn vị dev): loại đúng 82/82, hạn tự nhận đúng 32/66, sai 0. Chi phí và nguyên nhân lần chạy 195 giây: cùng báo cáo |
| O5 | Tự xoay trang — [`05_rotation/RESULTS.md`](../teams/team1_ocr/experiments/05_rotation/RESULTS.md) | Bước tự xoay trang của `ocr_v2` đúng đến đâu? | 353 trang đã xem (94 tài liệu), đáp án hướng do mô hình xem ảnh: trang bị xoay đúng 30/32 (Wilson [79,9%; 98,3%]); 0/280 trang thẳng có chữ bị sót (cận trên Wilson 2,1% và 3,8%); 2 trang sổ PCCC chọn nhầm 90/270; 8 trang gần trống bị xoay nhầm đã có luật chặn |
| O6 | Kiểm lô bản chép của LLM — [`03_llm_silver/RESULTS.md`](../teams/team1_ocr/experiments/03_llm_silver/RESULTS.md) | Làm sao biết mô hình thật sự nhìn thấy ảnh khi dựng đáp án? | `validate_batch.py` (14 test): trang đã biết, trang trắng, số ảnh nạp được, kiểm chéo 4-gram; lô > 50–60 mục thì kiểm chéo không còn nhạy (mô phỏng); lô Haiku cũ không thể chứng minh hợp lệ |
| O7 | Thông lượng OCR — [`08_throughput/RESULTS.md`](../teams/team1_ocr/experiments/08_throughput/RESULTS.md) | Thêm worker có tăng tốc? | 0,17–0,22 trang/giây với 4–6 worker (53 trang), GPU dùng chung, một lần chạy mỗi cấu hình, **không có khoảng tin cậy**, không tách được tác động của từng tham số |
| S6 | Tách: nhiều bản cùng loại — [`06_same_type`](../teams/team2_splitting/experiments/06_same_type/RESULTS.md) | Đặc trưng "bản khác" bắt được tệp ghép cùng loại không? | Quy tắc không tham số (đầu trang giống, số hiệu khác): 0/7 → 4/7 ranh giới (recall +0,571 [0,167; 0,889], 6 tệp, 4 ranh giới ở 3 tệp), mẫu âm không đổi (0/448 cặp bị kích hoạt); đặc trưng id trong mô hình cặp trang 1/7; VLM 3/7 nhưng thêm 7 tách nhầm. Thiết kế sau khi đọc tệp dev, TEST không có tệp loại này |
| C4 | Biên an toàn — [`04_safety_margin/RESULTS.md`](../teams/team3_classification/experiments/04_safety_margin/RESULTS.md) | Hiệu chỉnh, đồng thuận hai nguồn, kiểm mẫu có giúp? | DEV 237 tài liệu: 0 lỗi cross-fit ở mọi mức biên (221–235 tài liệu tự nhận tùy mức; mức đang dùng 235, cận trên 1,27%; cận trên mọi mức quanh 1,3%) nên chưa chọn được mức; đồng thuận hai nguồn chỉ giảm độ phủ 1,7–5,9 điểm; hiệu chỉnh đơn điệu không đổi thứ hạng; kiểm mẫu cần ~299 tài liệu để thấy 1 lỗi ở mức sai thật 1% |
| C5 | Biên bản trong tệp ghép — [`05_composite_slices/RESULTS.md`](../teams/team3_classification/experiments/05_composite_slices/RESULTS.md) | Vì sao biên bản giao nhận bị gán `PHIEU_XUAT_KHO`? | Luật mơ hồ + ngưỡng TF-IDF dễ (6/6 lát một trang). `rule_title_tiebreak`: 22/28 → 28/28 lát đúng trên 8 tệp một nhà cung cấp (đơn vị đúng là tệp: 2/8 → 8/8, Clopper–Pearson [63%; 100%]); DEV 237 tài liệu: đổi tầng 25, đổi nhãn 0. Mặc định tắt |
| X3 | Loại tài liệu mới — [`03_unseen_types/RESULTS.md`](../teams/team4_extraction/experiments/03_unseen_types/RESULTS.md), [`silver_report_v2.md`](../teams/team4_extraction/gold/v2/silver_report_v2.md) | Cấu hình giai đoạn 2 dùng được cho 17 loại chưa chỉnh luật? | 84 đơn vị: F1 mềm 0,75 [0,70; 0,79] (LLM), 0,83 [0,80; 0,86] (VLM); hạn: LLM đúng 52/62, sai 2; `any-model=filename` chỉ nhận 24/62 (0 sai). Sau vòng chỉnh trên DEV (luật ngày chung + `regex=llm`): phần không chỉnh 12/17, 0 sai, cận trên 22%. Hai người chú thích silver v2 đồng thuận 0,896 [0,842; 0,933] ở trường ngày |
| E2 | Chuỗi tới ngày hết hạn có ảnh trang — [`02_chain_with_images/RESULTS.md`](../teams/00_data_and_eval/experiments/02_chain_with_images/RESULTS.md) | Dựng ảnh trang trong pipeline lấy lại phần tự nhận hạn? | 82 đơn vị dev, 66 trường hạn: 32/66 → 37/66, thêm 5 mất 0, sai 0; bootstrap theo đơn vị hiệu +7,5 điểm [+1,5; +15,2] nhưng kiểm định dấu chính xác p = 0,0625 (lấy câu này làm kết luận chính); mặc định bật |
| E3 | Toàn trình v2 — [`03_end_to_end_v2/RESULTS.md`](../teams/00_data_and_eval/experiments/03_end_to_end_v2/RESULTS.md) | `id` và `tiebreak` có làm tệp đúng hoàn toàn tăng mà không tăng lỗi lặng lẽ? Chi phí có OCR thật? | Dev 245 tệp: S10 223 → S10+id+tb 232 đúng hoàn toàn; lỗi lặng lẽ 14 → 5; 279 → 293/318 tài liệu; hiệu có trọng số +3,0 [+2,0; +3,9], **mức trần lạc quan** (thiết kế trên chính các tệp này). TEST 59 tệp: cùng 56/59, chỉ kiểm được "không hại". Chi phí 30 tệp / 90 trang: ~500 trang/giờ/máy, OCR 45%, trích xuất 52% |
| R4 | Review độc lập giai đoạn 3 — [`04_phase3_review_and_deployment.md`](../teams/00_data_and_eval/reports/04_phase3_review_and_deployment.md) | Số giai đoạn 3 có đứng vững, và triển khai thế nào? | Tính lại được mọi số chính; 4 phát hiện nghiêm trọng (đổi mặc định bằng bằng chứng trong mẫu, tự nhận hạn dựa tên tệp, `regex=llm` làm quy tắc tự nhận cho loại mới, dữ liệu thật trong git), 10 phát hiện trung bình; thiết kế chạy bóng 6–8 tuần, cỡ mẫu 299/473 tệp, 1–3 máy tùy 500/2.000/10.000 trang/ngày |

Các kết luận rút ra để định hướng thiết kế:

1. **Không cần gửi ảnh ra ngoài để phân loại.** OCR cục bộ cho chất lượng phân loại ngang cận trên Haiku trong khoảng nhiễu (C1, C2).
2. **Loại hiếm cần phương pháp không huấn luyện.** TF-IDF không bao giờ nhận loại hiếm (đúng thiết kế: chuyển cho người); LLM zero-shot nhận được chúng. Hai nhóm lỗi bù nhau, đó là lý do dùng cascade.
3. **Mức sai ≤ 1% chưa chứng minh được** với 59 tài liệu TEST, dù số lỗi quan sát là 0–1.
4. **Công sức OCR nên dồn vào trích xuất**, không phải phân loại. Phần phân loại là kết quả đo (C1, C2); phần trích xuất nay có số đo sơ bộ (X1, mục 3 của báo cáo): OCR cục bộ mất nhiều nhất ở chữ viết tay và chữ dưới con dấu, còn chữ in chỉ mất ít (luật đúng 0,82 so với 0,89 trên bản chép của LLM đám mây). Số này ở dev, trên trường nằm ở trang 1–2, so với đáp án silver, chưa có khoảng tin cậy ghép cặp.
5. **Tách trang không thắng ở cấp tệp, chỉ thắng ở cấp tài liệu** (E1). Khoảng 92% tệp là tài liệu đơn hoặc nhiều trang không ghép, nên mỗi lần tách nhầm là làm hỏng một tệp đã đúng; phần được cứu chỉ nằm ở 7% tệp ghép. Hệ quả cho cách đo: luôn báo cả cấp tệp lẫn cấp tài liệu, theo từng nhóm, vì một con số gộp che mất điều này.
6. **Bộ tách phải biết loại tài liệu.** Gộp các lát cắt liền kề được phân loại cùng loại (trừ loại "một tờ = một tài liệu") cứu thêm 5,8 điểm tệp đúng (S4 so với S3 trong E1: +5,8 [+2,8; +9,0], tách được); giữ lại ranh giới rất chắc (điểm ≥ 0,99) cứu tệp ghép khác loại khỏi bị gộp nhầm. Ngưỡng ranh giới là quyết định vận hành (cắt vụn hay dính hai giấy đắt hơn), không phải thứ đo ra được từ dữ liệu dev.
7. **Với tệp ghép khác loại, điểm nghẽn là phân loại lát cắt, không phải tách** (E1): tách đúng 8/8 nhưng chỉ 2/8 tệp có mọi tài liệu đúng loại. Đây là *giả thuyết* từ 8 tệp của một nhà cung cấp.
8. **Ngày hết hạn không được tin vào một nguồn đọc OCR.** Hai phương pháp cùng đọc một bản OCR chung lỗi (đọc nhầm chữ số: 22 thay 12, 24 thay 21). Giải pháp đã đo ở giai đoạn 2: chỉ tự nhận khi một mô hình đọc trùng ngày trong tên tệp, phần còn lại về người kèm ngày gợi ý. Quy tắc này phụ thuộc quy ước đặt tên tệp; **công ty đã trả lời ngày 2026-10-16 rằng ngày trong tên tệp không mặc nhiên là ngày hết hạn** (chỉ ngày mà tài liệu ghi cụ thể là hạn mới là hạn; xem [`README.md`](../README.md) mục "Quyết định của công ty"), nên quy tắc không còn được dùng làm nguồn xác nhận độc lập; trong 83 đơn vị có hạn, 28 tên tệp không chứa ngày nào (`silver_report.md` §4), và ở 17 loại mới ngày trong tên tệp đứng một mình sai 17/40 lần có ngày (X3). Giai đoạn 3 thêm quy tắc `regex=llm` cho loại mới nhưng luật và LLM đọc **cùng một bản OCR** nên không độc lập (ngoài mẫu chỉnh 12 lần tự nhận, cận trên 22%). Vì vậy review (R4) đặt **tự nhận hạn tắt mặc định**: mọi hạn là gợi ý cho tới khi chạy bóng có ≥ 299 lần tự nhận không lỗi theo từng quy tắc.
9. **LLM bên ngoài chỉ để dựng dữ liệu tham chiếu, và dữ liệu đó là bản nháp.** Mọi đáp án do máy tạo (nhãn, ranh giới, trường) cần người kiểm trước khi coi là đáp án cuối; quy trình và giới hạn ở mục 9.1.
10. **Số đo trên chính dữ liệu đã dùng để thiết kế là mức trần, không phải ước lượng** (E3, C5, S6). `id` và `tiebreak` sửa 9 trong 14 tệp composite dev nhưng được nghĩ ra sau khi đọc chính các tệp đó và TEST không có tệp loại này; CI hẹp vì 14 tệp đổi cùng chiều, không vì có nhiều bằng chứng. Quy tắc thực hành: chỉ bật tự động khi có ≥ 30 tệp composite mỗi loại từ ≥ 3 nhà cung cấp chưa từng xem; đơn vị CI là tệp, không phải lát cắt (R4, T8); và kiểm "ghi trước" phải ghi trước **kết quả**, không chỉ trước lệnh chạy.

## 7. Các mối đe dọa tính hợp lệ

| Mối đe dọa | Vì sao là vấn đề | Đã làm gì | Còn phải làm |
|---|---|---|---|
| **Cỡ mẫu nhỏ** | TEST 59 tài liệu, mỗi lớp 3–7 tài liệu; Track Z trên TEST chỉ chấm được 10 loại; nhiều loại hiếm chỉ có 1–2 tài liệu | Báo khoảng tin cậy, so sánh ghép cặp, cận trên Clopper–Pearson; viết "không tách được" khi cần | Tập TEST mới và chạy bóng (mục 8) |
| **Nhãn chưa có người duyệt** | Lỗi hệ thống chung của hai mô hình gán nhãn sẽ không lộ ra qua κ | Báo κ cả trên tập không nêu tên trong hướng dẫn; đánh dấu 8 tệp cần xem | Nhân viên công ty kiểm nhãn (nhóm 00, T1) |
| **Vòng tròn nhãn/mô tả** | Mô tả loại và từ khóa luật được viết sau khi xem chính bộ mẫu; nhãn do mô hình gán theo chính mô tả đó. LLM zero-shot đọc cùng mô tả có thể chỉ đang tái tạo cách gán nhãn; cổng luật "đúng 100%" cũng vậy | Biến thể chỉ đưa tên loại (Qwen3.5 0,970, Kev 0,962 trên DEV); ablation bỏ cổng luật; nguồn OCR chất lượng thấp | Nhân viên viết mô tả loại mới **trước khi** xem tài liệu; nhãn do người gán mù với mô hình |
| **Một công ty, một giai đoạn** | Cùng khách hàng, cùng biểu mẫu, cùng máy quét; không đo trôi dạt theo thời gian | Chia theo nhóm biểu mẫu; đo biến thể nghiêm ngặt | Mẫu từ khách hàng và biểu mẫu chưa thấy |
| **Một loại gần như một biểu mẫu** | `CC_TAP_HUAN_VC_HNH` (23/24) và `PHIEU_XUAT_KHO` (15/15): điểm cao có thể chỉ là nhớ biểu mẫu | Báo cả hai biến thể chia | Thu biểu mẫu mới của hai loại này làm tập kiểm tra |
| **Chọn mô hình trên DEV nhỏ** | Hàng chục cấu hình trên 237 tài liệu; ngưỡng do 0–2 lỗi quyết định | Báo cả á quân, cross-fit, nhiều ứng viên tầng 3; coi các họ mô hình hòa nhau | Ngưỡng có biên an toàn; kiểm mẫu ngẫu nhiên khi vận hành |
| **Chuẩn bạc thay cho chuẩn vàng** | Số OCR trên bản quét thật là so với bản chép Haiku, không phải với người | Chấm Haiku trên trang có đáp án; so Haiku với Sonnet | 25 trang do người sửa và gõ (nhóm 1, T1) |
| **Một lần chạy mỗi cấu hình** | Không biết dao động giữa các lần chạy và giữa các phiên bản mô hình | Cố định `temperature = 0`, `seed = 0`, lưu bộ nhớ đệm | Chạy lặp khi đổi phiên bản |
| **Phạm vi hẹp của phép đo phân loại** | Chỉ văn bản, chỉ trang 1–2, không có tệp ghép khác loại; không đo lỗi tách | Đã đo thêm toàn trình theo tệp (E1: dev 245 tệp, TEST 59 tệp) | Toàn trình có OCR; mẫu ngẫu nhiên phần tự xử lý |
| **Đáp án ranh giới và đáp án trường do máy tạo** | Mọi số "đúng" của tách và trích xuất là "khớp đáp án máy"; hai mô hình cùng họ có thể chung lỗi | Ghi rõ ở mọi báo cáo; phân xử bằng mô hình mạnh hơn cho 58 trường; ước lượng sai của người chú thích (mục 9.1) | Người của công ty kiểm: 5 tệp `check_composite`, các trường viết tay/dưới dấu, mẫu ngẫu nhiên phần đồng thuận |
| **Tham số chọn sau khi xem số dev** | Ngưỡng tách (0,7; 0,99), quy tắc chọn mặc định và lưới tham số đều đặt sau khi xem dev, vì mục tiêu sai lặng lẽ ≤ 1% không biến thể nào đạt; luật và prompt trích xuất chỉnh trên chính đơn vị chấm | Tách dev (chọn) và TEST (chấm một lần); nêu rõ số dev lạc quan; các cặp tham số lân cận cho kết quả gần như nhau | TEST lớn hơn, nhiều tệp ghép hơn (TEST hiện chỉ có 2 tệp ghép) |
| **Quá ít tệp ghép** | Dev 19 tệp ghép (8 khác loại), TEST 2 (cùng loại `BB_LAY_MAU`); 8 tệp khác loại thuộc vài bộ chứng từ cùng dạng của một nhà cung cấp, có thể chỉ là nhớ bố cục | Cross-fitting theo nhóm biểu mẫu, gộp các bộ cùng nhà cung cấp một nhóm; khoảng Clopper-Pearson cho ô theo nhóm | Thêm bộ chứng từ của nhà cung cấp khác (câu hỏi 8 của nhóm 2) |
| **Máy dùng chung** | Số độ trễ nhiễu; Ollama bị tiến trình khác đẩy mô hình ra và nạp lại (18–32 giây mỗi lời gọi) | Hết giờ mỗi lời gọi 45 giây và ngân sách 90 giây mỗi tệp trong pipeline | Đo trên máy đích; thống nhất cấu hình Ollama giữa các client |

## 8. Thí nghiệm tiếp theo, kèm cỡ mẫu

Danh sách này được sắp lại sau ngày 2026-10-12 theo các mục "chưa chứng minh" của báo cáo tách, trích xuất và toàn trình. Cỡ mẫu lấy từ mục 10 của [báo cáo C2](../teams/team3_classification/experiments/02_llm_and_cascade/RESULTS.md), từ README các nhóm, từ [`01_end_to_end/RESULTS.md`](../teams/00_data_and_eval/experiments/01_end_to_end/RESULTS.md) và từ mục 6 của [`PARALLEL_RESEARCH_PLAN.md`](PARALLEL_RESEARCH_PLAN.md). Hai công thức dùng lại nhiều lần: cận trên 95% khi 0 lỗi trong n là khoảng 3/n; và để một tỉ lệ p có khoảng tin cậy ± d cần n ≈ 1,96² · p(1 − p) / d². Cột "Ai" trỏ tới nơi mô tả việc; công sức không được ước lượng ở đây (mỗi README nhóm có ước lượng của người viết kế hoạch).

| # | Thí nghiệm | Cỡ mẫu | Trả lời câu hỏi | Ai |
|---|---|---|---|---|
| 1 | Nhân viên công ty kiểm **ba loại đáp án máy**: (a) nhãn loại; (b) ranh giới: xem đủ trang 21 tệp ghép, đặc biệt 5 tệp `check_composite`, và lật nhanh các tệp nhiều trang "không ghép" để bắt tệp ghép bị bỏ sót; (c) trường: mọi trường viết tay/dưới con dấu (67 trường có cờ rủi ro mực), mọi trường hạn lệch tên tệp, và một mẫu ngẫu nhiên phần hai mô hình đồng thuận | (a) kế hoạch của nhóm 00: 13 tài liệu bắt buộc + 30 tài liệu ngẫu nhiên = 43, mở rộng sang 74 tài liệu loại hiếm nếu có lỗi; báo cáo C2 đề nghị rà 24 loại hiếm và 30–50 tài liệu thường (khoảng 150). 0 lỗi trong 30 tài liệu ngẫu nhiên chỉ cho cận trên khoảng 10%. (b) 21 tệp ghép (176 trang) + 191 tệp nhiều trang. (c) theo `gold/README.md` của nhóm 4 | Q1, Q6, Q7. Mọi số tách và trích xuất đang là "khớp đáp án máy" | [nhóm 00](../teams/00_data_and_eval/README.md) T1, [nhóm 2](../teams/team2_splitting/README.md) T1, [nhóm 4](../teams/team4_extraction/README.md) T2 |
| 2 | ~~Công ty xác nhận quy ước "ngày trong tên tệp = ngày hết hạn" (câu hỏi 16)~~ **ĐÃ TRẢ LỜI ngày 2026-10-16** (chủ dự án truyền đạt, nói tắt: "ngày trong tệp phải cụ thể là ngày gì thì mới là ngày hết hạn"; diễn giải của nhóm: ngày chỉ là hạn khi tài liệu ghi rõ, ngày trong tên tệp không mặc nhiên là hạn, có giấy tờ không có hạn; cần xác nhận lại nếu khác). Còn lại: việc thay quy tắc tự nhận dùng tên tệp (nhóm 4) và, tùy chọn, ~100 tên tệp thật nếu muốn dùng tên tệp làm tín hiệu phụ | trong 83 đơn vị có hạn, 28 tên tệp không chứa ngày (`silver_report.md` §4) | quy tắc `any-model=filename` không còn là nguồn xác nhận độc lập; tự nhận hạn giữ tắt; `ngay_het_han` = `not_present` là kết quả hợp lệ với loại không có hạn ([README gốc](../README.md) "Quyết định của công ty") | nhóm 00 (câu hỏi), [nhóm 4](../teams/team4_extraction/README.md) |
| 3 | **Đã làm (E2)**: ảnh trang đã vào pipeline, 32 → 37/66, sai 0, p dấu 0,0625. Còn lại: chạy lại sau khi đổi khóa cache VLM, và chỉ dựng ảnh khi quy tắc hạn dùng VLM (T3, T4 của báo cáo 04). Ban đầu: đưa ảnh trang (hai trang đầu) vào `extract_fields` rồi đo lại tỉ lệ tự nhận hạn | cùng 66 trường hạn dev của E1 để so với 48,5% và 58% (37/64) của thí nghiệm trích xuất; đáp án người kiểm là điều kiện để con số có nghĩa, vì silver cũng đọc từ ảnh | tự nhận hạn lấy lại được bao nhiêu mà không tăng sai | [`01_end_to_end/RESULTS.md`](../teams/00_data_and_eval/experiments/01_end_to_end/RESULTS.md) mục "Chuỗi tới ngày hết hạn" |
| 4 | Chạy bóng toàn trình 2–4 tuần, người vẫn xếp như cũ, ghi mọi bất đồng; lấy mẫu ngẫu nhiên phần hệ thống tự xử lý | ≥ 1000 tài liệu thật; cần khoảng 300 tài liệu tự nhận liên tiếp không lỗi cho mức ≤ 1%, khoảng 600 cho ≤ 0,5%; riêng ngày hết hạn tự nhận cần ≥ 299 (hiện có 49) | mức sai lặng lẽ thật của `model+merge` (4,94% trên dev) và của `triage` (1,45%) | [nhóm 3](../teams/team3_classification/README.md) T4 |
| 5 | Doanh nghiệp quyết định giữa `model+merge` và `triage`: đo thời gian người duyệt một tệp và chi phí của một tệp sai lặng lẽ | `triage` đưa 22% tệp dev về người; `model+merge` 3,2% | chọn chính sách tách mặc định theo chi phí thật, không theo độ chính xác | doanh nghiệp + nhóm 00 |
| 6 | Thêm bộ chứng từ của nhà cung cấp khác; thêm luật hoặc ví dụ cho `BB_GIAO_NHAN_HANG_HOA` so với `PHIEU_XUAT_KHO` | dev chỉ có 8 tệp ghép khác loại; để recall ranh giới ≈ 0,9 có khoảng ± 7 điểm cần ≈ 71 ranh giới (1,96²·0,9·0,1/0,07²); với mỗi loại ≥ 20 lát cắt cho recall ± 15 điểm | giả thuyết "điểm nghẽn là phân loại lát cắt" có đứng vững ngoài một nhà cung cấp không | [nhóm 2](../teams/team2_splitting/README.md) (câu hỏi 8), [nhóm 3](../teams/team3_classification/README.md) |
| 7 | Tập TEST mới từ khách hàng và biểu mẫu chưa thấy, nhãn do nhân viên gán mù với mô hình, **có đủ tệp ghép** | ≥ 150 tài liệu, ≥ 10 khách hàng hoặc biểu mẫu, gồm ≥ 5 loại mới × 5 tài liệu; 20 tài liệu mỗi loại cho khoảng tin cậy recall ± 15 điểm (24 loại hiếm: khoảng 480 tài liệu); thêm tệp ghép vì TEST hiện chỉ có 2 | tổng quát hóa; tách trên tệp ghép khác loại | nhóm 00 T3, nhóm 3 T5 |
| 8 | Nhân viên viết mô tả cho loại mới trước khi xem tài liệu, rồi đo tầng LLM | 5–10 loại mới × ≥ 10 tài liệu | vòng tròn mô tả | nhóm 3 T6 |
| 9 | Hiệu chỉnh độ tin cậy (cả `boundary_confidence` của bộ tách, hiện là điểm thô), ngưỡng có biên an toàn, chế độ hai LLM đồng thuận trong cascade | tập ở dòng 7 | ngưỡng không dễ dãi | nhóm 3 T3, nhóm 2 |
| 10 | Vận hành LLM: mọi client của `qwen3.5:4b` dùng chung `num_ctx` 6144 hoặc tách một máy chủ Ollama riêng cho pipeline; so mô hình tầng 3 (Kev-4B, các cỡ Qwen); kiểm thử tải hàng đợi GPU | một ngày dữ liệu; đo lúc GPU không dùng chung | chi phí; hàng đợi kẹt (lời gọi mất 18–32 giây vì nạp lại mô hình) còn xảy ra không | nhóm 3 T7, T8; khuyến nghị vận hành trong E1 (chưa làm) |
| 11 | Đáp án OCR do người làm trên bản quét thật | 25 trang, 5 trang mỗi nhóm (in, viết tay, con dấu, bảng, chất lượng thấp); 5 trang mỗi nhóm cho khoảng rất rộng, dùng để ước lượng độ lệch chuẩn rồi tính cỡ mẫu | Q2 | [nhóm 1](../teams/team1_ocr/README.md) T1 |
| 12 | Trích xuất trên biểu mẫu mới và loại thứ 5 trở đi: mở rộng schema, bảng hàng hóa | `CC_TAP_HUAN_VC_HNH` (23/24) và `PHIEU_XUAT_KHO` gần như một biểu mẫu; TEST chỉ 6 đơn vị mỗi loại có nhiều biến thể; 13 loại còn lại chưa có schema (giai đoạn 3 đã thêm 17 loại, X3) | tổng quát hóa của trích xuất | [nhóm 4](../teams/team4_extraction/README.md) |
| 13 | Tách: nhóm cùng loại ngoài `BB_LAY_MAU` (tối đa 4/7 ranh giới), tệp trên 30 trang (63/92 ranh giới của tệp 93 trang chưa được chấm), prompt thứ hai cho LLM hỏi có/không | 6 tệp cùng loại, 27 ranh giới ngoài `BB_LAY_MAU` (S6: quy tắc `id` đạt 4/7, chưa kiểm giữ ngoài; tệp > 30 trang nay chuyển người) | giới hạn của bộ tách hiện có | [nhóm 2](../teams/team2_splitting/README.md) T5 |
| 14 | Bảng E0–E3 (ΔF₁ theo khâu): thay dần từng khâu từ đáp án sang thành phần thật, **kể cả OCR** (E1 dùng văn bản OCR đã có, không đo lại OCR) | DEV; mỗi hiệu số kèm khoảng tin cậy | Q8 | mọi nhóm |

Việc đã làm so với phiên bản cũ của danh sách: đo bộ tách (T1–T3 của nhóm 2, báo cáo S1–S5), đáp án trường và so sánh phương pháp trích xuất (báo cáo X1, X2), cùng một bộ trích xuất trên hai nguồn văn bản (OCR cục bộ và bản chép của LLM, mục 3 của X1) và toàn trình theo tệp (E1). Còn lại từ danh sách cũ: cùng bộ trích xuất trên text layer (không đo được: các trang có chữ số hóa nằm sẵn trong `ocr_v2`, nên hai nguồn cho kết quả giống hệt, xem X1).

**Sau giai đoạn 3**, danh sách ưu tiên mới (15 việc, có nhóm phụ trách và ước lượng) nằm ở mục 11 của [báo cáo 04](../teams/00_data_and_eval/reports/04_phase3_review_and_deployment.md); bản rút gọn trong [`README.md`](../README.md) mục "Giai đoạn 3". Cỡ mẫu chạy bóng: ≥ 299 tệp tự xử lý liên tiếp không lỗi (hoặc ≥ 473 với ≤ 1 lỗi) cho mức lỗi lặng lẽ ≤ 1%; ≥ 299 lần tự nhận không lỗi theo từng quy tắc cho ngày hết hạn; ≥ 30 tệp composite mỗi loại từ ≥ 3 nhà cung cấp để kiểm `id` và `tiebreak`.

Thứ tự quan trọng: dòng 1 và 2 đi trước, vì mọi con số đều tính trên đáp án máy và quy tắc tự nhận hạn dựa vào một quy ước mà công ty đã bác (dòng 2 ở trên: đã trả lời, còn phải thay quy tắc).

## 9. Tự làm một thí nghiệm mới đúng chuẩn

1. **Viết một câu hỏi trả lời được bằng số**, và viết trước bạn sẽ kết luận gì với từng kết quả có thể xảy ra. Ví dụ: "embedding ở tầng 3 có tự xếp ít hơn LLM ở mức sai ≤ 1% không?".
2. **Tạo thư mục** `teams/<nhóm>/experiments/NN_ten_ngan/` (NN là số thứ tự hai chữ số, tên không dấu). Mọi script sinh ra số nằm trong đó; đầu ra trung gian vào `_cache/` (không commit); bảng và hình cuối vào `teams/<nhóm>/results/NN_ten_ngan/`. Quy ước: [`teams/README.md`](../teams/README.md) mục 2.
3. **Nạp dữ liệu qua bộ chấm chung, không tự chia.** Script nhận tham số `--labels` và không gắn cứng điều gì phụ thuộc nhãn.

   ```python
   import sys; sys.path.insert(0, "teams/00_data_and_eval/eval")
   from harness import *

   bench  = load_benchmark("data/labels_v2.csv")     # tài liệu duy nhất, đã loại tệp ghép khác loại
   splits = load_or_make_splits(bench)               # chỉ đọc tập chia đã khóa
   dev    = load_documents(bench, splits, "ocr_v2_p12", "DEV")

   class MyPredictor(Predictor):
       name = "my_method"; track = "S"               # "Z" nếu chấm trên toàn taxonomy
       def fit(self, train_docs):                    # zero-shot thì để trống
           return self
       def predict(self, docs) -> Prediction:
           return Prediction(labels=[...])           # thêm proba và classes nếu có xác suất

   cv = cross_validate(lambda: MyPredictor(), dev, bench.s_classes, track="S", seed=0)
   print(summarize_folds(cv.fold_scores))            # lặp seed 0, 1, 2 để có 15 điểm
   ```

   Đoạn trên là khung theo chữ ký hàm hiện có trong `harness.py`, chưa được chạy khi viết tài liệu này. Ví dụ đã chạy thật: `teams/team3_classification/experiments/01_classical_baselines/methods.py` (mô hình có huấn luyện) và `experiments/02_llm_and_cascade/predictors.py` (LLM và embedding).
4. **Chọn mọi thứ trên DEV.** Dùng dự đoán out-of-fold (`cv.oof`) để chọn cấu hình và ngưỡng (`choose_threshold`). Không gọi `load_documents(..., "TEST")`: hàm ném `PermissionError` trừ khi truyền `final_test=True`, và tham số đó chỉ được xuất hiện trong lệnh chấm cuối.
5. **Nếu gọi mô hình cục bộ** (Kev, Ollama): đi qua `DiskCache` trong `src/classification/llm_cache.py` để chạy lại tất định; kiểm tra tên mô hình máy chủ đang nạp trước mỗi lượt; chạy tuần tự, không cho Kev và Ollama dùng GPU cùng lúc; đo độ trễ riêng lúc máy rảnh.
6. **Chốt cấu hình cuối ra tệp** (kèm mã băm nhãn) trước khi mở TEST. Viết lệnh chấm TEST riêng, từ chối chạy lần hai cho cùng bộ nhãn, như `--final-test` của hai thí nghiệm hiện có.
7. **Chấm TEST một lần.** Huấn luyện lại trên toàn bộ DEV; báo khoảng tin cậy bootstrap (`bootstrap_metrics`), so sánh ghép cặp với baseline đã chốt (`paired_bootstrap`), và với chỉ số tự xếp hồ sơ thì thêm cận trên Clopper–Pearson (`apply_threshold`, `clopper_pearson_upper`).
8. **Ghi kết quả** bằng `append_result_row` (một dòng cho DEV, một dòng cho TEST) và viết `RESULTS.md` theo khuôn dưới đây.
9. **Tự phản biện trước khi báo xong:** chạy lại từ đầu bằng một lệnh; kiểm rằng mọi số trong phần viết tay khớp bảng do script sinh; `pytest -q` qua.

Ba chỗ để biết khi làm thí nghiệm về tách, trích xuất hoặc toàn trình (khác với khung phân loại ở trên):

- **Đường ống thật** ở `src/pipeline.py` (`DocumentPipeline`, chính sách tách chọn bằng `split_policy=`; `scripts/run_pipeline.py` là lệnh bọc). Thí nghiệm toàn trình nên gọi lớp này thay vì ghép lại từng khâu, như `teams/00_data_and_eval/experiments/01_end_to_end/cost_sample.py`.
- **Đáp án tham chiếu**: ranh giới ở `teams/team2_splitting/gold/boundary_gold_v0.csv` (máy), trường ở `teams/team4_extraction/gold/fields_silver_v1.jsonl` (máy). Cả hai ghi rõ "chưa người kiểm"; ảnh trang, bản đọc nguyên văn và `units.csv` chứa dữ liệu thật nên không commit.
- **Chống rò rỉ khi mô hình có học nằm trong chuỗi**: điểm cặp trang phải là cross-fitted (5 fold theo nhóm biểu mẫu, `teams/team2_splitting/cvlib.py`), TF-IDF huấn luyện lại theo fold DEV; không dùng artefact trong `models/` để chấm DEV (nó đã học toàn DEV). TEST của một chuỗi cũng chỉ mở một lần, bằng `--stage test --final-test` có sổ đăng ký chặn lần hai.

### 9.1. Dựng đáp án tham chiếu cho trường bằng LLM đọc ảnh (phương pháp dùng cho đáp án trường của nhóm 4)

Dùng khi chưa có đáp án cấp **trường** và gõ tay quá tốn công. Kết quả là **silver** (bản nháp do máy tạo), không phải gold; dưới đây là quy trình đã làm và đo, nguồn [`gold/README.md`](../teams/team4_extraction/gold/README.md) và [`silver_report.md`](../teams/team4_extraction/gold/silver_report.md).

**Điều kiện về quyền riêng tư.** Chỉ được làm trên **bộ mẫu này**, vì chủ dự án đã đồng ý rõ ràng cho gửi ảnh tới LLM bên ngoài; ngoại lệ không áp dụng cho tài liệu mới. Ảnh trang, bản đọc nguyên văn và hàng đợi phân xử chứa dữ liệu thật nên không commit.

**Các bước.**

1. **Đơn vị và ảnh.** Đơn vị = `(doc_id, đoạn)` của 4 loại có schema (104 đơn vị). Mỗi trang render 200 dpi; trang dọc cắt đôi thành nửa trên và nửa dưới để chữ nhỏ không bị thu nhỏ quá, cạnh dài ≤ 1600 px. Danh sách trang được cho xem ghi trong `units.csv` (đơn vị dài hơn 4 trang chỉ cho xem tối đa 6 trang), nên "không có trường này" nghĩa là "không có trên các trang đã cho xem".
2. **Hai người chú thích độc lập.** Haiku đọc cả 104 đơn vị; Sonnet đọc lại độc lập 40 đơn vị. Cả hai theo cùng một prompt với **quy tắc dừng**: không đọc được thì ghi `error`, không bao giờ đoán. Mỗi trường ghi giá trị, trang, đoạn trích dẫn nguồn (≤ 12 từ), kiểu mực (in, viết tay, dưới con dấu).
3. **Gộp và kiểm hợp lệ.** Script gộp kiểm từng bản ghi và loại ở mức **trường** khi được (không bỏ cả đơn vị). So sánh hai người ở hai chế độ cạnh nhau: *chặt* (sau chuẩn hóa ngày/số/mã/văn bản) và *nới lỏng* (văn bản bỏ dấu tiếng Việt và dấu câu, chuỗi ngắn nằm trọn trong chuỗi dài). Giống nhau → `agreed_unverified`; khác → `needs_human`.
4. **Phân xử mù.** Hàng đợi 58 mục gồm: trường còn `needs_human` sau so sánh nới lỏng, trường có cờ rủi ro mực, trường hạn lệch ngày trong tên tệp. Người phân xử thứ ba là **mô hình mạnh hơn (Opus)**, thấy hai bản đọc theo thứ tự xáo ngẫu nhiên (hạt giống cố định) và không biết ai đọc bản nào. Phán quyết: x đúng 13, y đúng 8, hai bên tương đương 36, cả hai sai 1. Trường đã phân xử mang `model_adjudicated`; **không bước nào tạo ra `human_verified`**.
5. **Kiểm chéo hạn với tên tệp** (chỉ kiểm chéo, không phải đáp án): khớp 50, lệch 4, tên tệp không có ngày 28, silver không có hạn đọc được 1.
6. **Kiểm lô trước khi tin** (giai đoạn 3): mỗi lô bản chép phải qua `validate_batch.py` (trang đã biết, trang trắng, số ảnh nạp được, kiểm chéo với OCR); lô ≤ 50–60 mục, vì lô lớn hơn kiểm chéo không còn nhạy (O6). Silver v2 (17 loại mới, 84 đơn vị) làm cùng quy trình: hai người chú thích đồng thuận 0,896 [0,842; 0,933] ở trường ngày (173 cặp có giá trị), 0,536 chặt và 0,924 mềm ở trường văn bản; 95 trường có cờ rủi ro mực vẫn phải xem lại dù đồng thuận (`silver_report_v2.md`).

**Đã đo.**

| Đại lượng | Giá trị (Wilson 95%) |
|---|---|
| Đồng thuận Haiku–Sonnet, 40 đơn vị: ngày (90 cặp) | 0,944 [0,876; 0,976] |
| mã định danh (80 cặp) | 0,950 [0,878; 0,980] |
| số (30 cặp) | 1,000 [0,886; 1,000] |
| văn bản (190 cặp): chặt / nới lỏng | 0,668 [0,599; 0,731] / 0,932 [0,886; 0,960] |
| Haiku bị người phân xử coi là **sai**, trong số mục vào hàng đợi (có điều kiện) | 10/58 = 17,2% [9,6%; 28,9%]; ngày 6/21, mã 3/9, văn bản 1/28 |
| Sonnet, như trên | 8/54 = 14,8% [7,7%; 26,6%]; ngày 0/17, mã 0/9, văn bản 8/28 |
| Cận **dưới** của tỉ lệ sai trên mọi bản đọc (coi trường đồng thuận là đúng) | Haiku 10/400 = 2,5% [1,4%; 4,5%]; Sonnet 8/400 = 2,0% [1,0%; 3,9%] |

Đọc: hai mô hình sai ở chỗ khác nhau (Haiku ở ngày và mã, Sonnet ở văn bản), nên đối chiếu có ích; nhưng tỉ lệ có điều kiện chỉ nói về các mục đã bị nghi, còn tỉ lệ thật cần kiểm mẫu ngẫu nhiên phần đồng thuận.

**Sự cố ảnh nửa trang trắng và cách sửa.** Ở vòng 1, 8 đơn vị của Haiku trả bản ghi lỗi theo quy tắc dừng vì nửa dưới trang (hoặc một mặt sau) là giấy trắng: thẻ nhỏ chỉ chiếm nửa trên tờ giấy. Hai trường hợp được xem bằng mắt: ảnh thật sự là giấy trắng, nhưng một thông báo lỗi còn gọi nhầm một nửa trang *có nội dung* là "trắng". Cách xử lý: chuyển 8 tệp lỗi sang thư mục riêng để truy vết, chạy lại đúng 8 đơn vị với một câu làm rõ ("ảnh trắng là bình thường, không phải lỗi; chỉ ghi lỗi khi không đọc được tệp hoặc ảnh có nội dung mà không đọc được"), rồi đưa câu đó vào prompt chú thích và prompt phân xử. Kết quả: 104/104 đơn vị Haiku hợp lệ. Bài học: quy tắc dừng là cần (không để mô hình đoán), nhưng phải đếm bản ghi lỗi, xem mắt vài ca, và chạy lại **chỉ** phần lỗi; tùy chọn bỏ nửa trang trắng khi render (`--drop-blank`) có sẵn nhưng chưa dùng. Một bài học thứ hai: ban đầu bản ghi có đoạn trích quá dài làm mất cả đơn vị (3 đơn vị Haiku, 16 đơn vị Sonnet); sau đó đổi thành cắt còn 12 từ và chỉ cảnh báo.

**Giới hạn của phương pháp.**

- **Không có người kiểm.** `agreed_unverified` không phải sự thật; mọi số trích xuất "đúng" là khớp silver. Phải có người của công ty kiểm ít nhất mọi ô `needs_human`, mọi trường viết tay hoặc dưới con dấu (67 trường có cờ rủi ro mực), và một mẫu ngẫu nhiên phần đồng thuận để đo sai của chính phần đó.
- **Chung họ, chung lỗi.** Haiku, Sonnet và Opus cùng họ Claude; đồng thuận không chứng minh đúng, người phân xử cũng là mô hình.
- **Đọc cùng một thứ.** Người chú thích đọc **ảnh**, nên mô hình cục bộ đọc ảnh khi so với silver có điểm cao hơn so với phương pháp dựa OCR; đừng đọc đó là lợi thế thật.
- **Trường ngoài tầm nhìn**: trường nằm ở trang không được cho xem có thể bị ghi `not_present`.
- **Một biểu mẫu, nhiều tài liệu** (thẻ tập huấn, phiếu xuất kho) làm điểm cao giả tạo; trường dữ liệu cá nhân chỉ ghi có hay không và không được chấm.
- **Đáp án có chỗ không phải ngày** ("từ ngày ký", cụm thời hạn) phải có quy ước chuyển đổi, áp dụng như nhau cho DEV và TEST.


Khuôn `RESULTS.md` (mẫu tốt để đọc: [`01_engine_bakeoff/RESULTS.md`](../teams/team1_ocr/experiments/01_engine_bakeoff/RESULTS.md) và [`02_llm_and_cascade/RESULTS.md`](../teams/team3_classification/experiments/02_llm_and_cascade/RESULTS.md)):

```text
# Thí nghiệm NN - <tên>
> Đọc trước: nhãn nào (tệp + sha), nhãn đã được người kiểm chưa, nguồn văn bản, biến thể chia, cỡ mẫu.
0. Tóm tắt       bảng: kết luận | mức chắc chắn (Đã đo / Suy luận)
1. Mục tiêu      câu hỏi, và quyết định gắn với từng câu trả lời
2. Lệnh chạy     chính xác, chép-dán được; đầu ra nằm ở đâu
3. Thiết lập     dữ liệu, mô hình và phiên bản THẬT SỰ đã chạy, ngày chạy, prompt
4. Kết quả DEV   bảng do script sinh + đoạn "Đọc kết quả" tách Đã đo / Suy luận
5. Kết quả TEST  chấm một lần; khoảng tin cậy; so sánh ghép cặp
6. Chi phí       độ trễ trung vị và p95, VRAM, on-premise hay không
7. Hạn chế       cỡ mẫu, nhãn, những gì đã chọn sau khi xem dữ liệu
8. Đã cắt / không làm   để không ai tưởng đã có
```

## 10. Riêng tư

- **Hệ thống chạy thật: bắt buộc on-premise**, không gọi LLM hay dịch vụ đám mây bên ngoài.
- **Riêng bộ mẫu nghiên cứu này**, chủ dự án đã đồng ý cho gửi tới LLM bên ngoài (Claude Haiku, Sonnet, Opus) để tạo dữ liệu tham chiếu: bản chép, gán nhãn loại, ranh giới, đáp án trường và phân xử. Đây là ngoại lệ cho nghiên cứu, không phải cho triển khai; mẫu mới cần phê duyệt mới. **Quyết định của công ty 2026-10-16:** được dùng LLM bên ngoài (đám mây) để **tạo đáp án** (silver/gold) trên tài liệu mẫu; sản xuất vẫn on-premise và các khuyến nghị riêng tư khác giữ nguyên ([`README.md`](../README.md) mục "Quyết định của công ty").
- Hệ quả phương pháp luận: phương pháp nào dùng dịch vụ ngoài chỉ được báo cáo như **cận trên** hoặc như công cụ dựng dữ liệu tham chiếu, không như một phương án triển khai.
- PDF, văn bản OCR, bản chép, CSV lỗi đều chứa thông tin cá nhân: chỉ giữ trong kho riêng tư và máy nội bộ. Bảng phân loại dữ liệu và những gì được phép: [nhóm 00](../teams/00_data_and_eval/README.md), việc T7.
- **Review giai đoạn 3 (báo cáo 04, N4 và mục 9) ghi nhận một việc chưa xong:** PDF gốc, toàn văn OCR và silver trường đang được git theo dõi (remote GitHub) và ảnh đã qua mô hình đám mây; cần văn bản duyệt của công ty, dọn khỏi lịch sử git nếu chưa có, và từ nay tài liệu mới chỉ đi qua mô hình cục bộ. Quy ước: tài liệu được nhắc bằng `doc_id`, không bằng tên tệp có họ tên.

## 11. Vì sao phương pháp cũ bị bỏ

Bản đầu của đề tài (và của tệp này) không đứng vững ở bốn điểm; ghi lại để không lặp lại:

1. **Nhãn = tên thư mục lưu trữ.** Thư mục là tủ hồ sơ; 27 nhóm tệp trùng nằm ở hai thư mục nên có hai "đáp án".
2. **Không khử trùng, không có tập TEST.** Kế hoạch dùng kiểm định chéo phân tầng trên mọi tệp, nên bản trùng và biểu mẫu chung nằm ở cả hai phía.
3. **Con số không có phép đo.** Độ chính xác, độ trễ, ngưỡng tin cậy và tỉ lệ tài liệu "thoát sớm" được viết như kết quả trước khi có thí nghiệm nào.
4. **OCR mất dấu mà không ai đo.** Engine mặc định không thể xuất phần lớn chữ có dấu tiếng Việt; điều này chỉ lộ ra khi đếm tỉ lệ chữ có dấu.

Phần giới thiệu các mô hình quyết định nhanh của bản cũ được thay bằng phép đo trong báo cáo C2. Điều còn dùng được từ phần đó: Kev là mô hình không sinh văn bản mà trả lời các câu hỏi định kiểu trên một đoạn văn bản — `Choice` (chọn một trong N tiêu chí, kèm xác suất từng tiêu chí), `Noul` (đúng/sai), `Score` (chấm theo thang). Trong kho này **chỉ `Choice` đã được gọi và đo** (mã: `src/classification/zero_shot.py`); `Noul` cho bài toán ranh giới trang chưa được thử (thay vào đó nhóm 2 thử Qwen3.5-4B hỏi có/không với một prompt: gần như không bao giờ trả "tài liệu mới", báo cáo S5), và các tuyên bố của bản cũ về tốc độ hay độ hiệu chỉnh của Kev không được giữ lại vì trái với số đo (độ trễ trung vị 860 ms, ECE 0,441 trong báo cáo C2).
