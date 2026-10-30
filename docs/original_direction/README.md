# Hướng đi ban đầu của đề tài, và nó đã đổi thế nào

Thư mục này **giữ nguyên văn** các tài liệu tổng quan của hướng đi ban đầu (lấy từ nhánh `main` trước khi nhánh `research-v2` được gộp vào), kèm một bảng đối chiếu: với mỗi quyết định hoặc giả định lớn của hướng đi ban đầu, hiện nay nó **giữ, đổi, bỏ** hay **chưa kiểm**, vì sao, và bằng chứng ở đâu. Viết cho sinh viên năm cuối tiếp tục đề tài: đọc bảng này trước khi quyết định "làm lại theo ý ban đầu", vì phần lớn các ý ban đầu đã được thử và có số đo.

Cách đọc các số: mọi "đúng/sai" dưới đây là **so với đáp án máy** (nhãn do hai lượt mô hình AI, ranh giới do một mô hình xem đủ trang, trường do Haiku/Sonnet/Opus), chưa có nhân viên công ty kiểm. Khoảng trong ngoặc vuông là khoảng tin cậy 95%. Tài liệu sống hiện hành nằm ở [`README.md`](../../README.md) gốc, [`docs/PARALLEL_RESEARCH_PLAN.md`](../PARALLEL_RESEARCH_PLAN.md) và [báo cáo 04](../../teams/00_data_and_eval/reports/04_phase3_review_and_deployment.md); tài liệu trong thư mục này là **bản lưu trữ**.

## 1. Các tệp lưu trữ (nguyên văn từ `main`)

| Tệp lưu trữ | Nội dung ban đầu | Bản sống hiện nay |
|---|---|---|
| [`README_original.md`](README_original.md) | Tổng quan: 19 danh mục, Jev/Kev, OCR 3 tầng, cascade, IE | [`README.md`](../../README.md) gốc |
| [`HANDBOOK_FOR_RESEARCHERS.md`](HANDBOOK_FOR_RESEARCHERS.md) | Cẩm nang 4 nhóm | [`docs/HANDBOOK_FOR_RESEARCHERS.md`](../HANDBOOK_FOR_RESEARCHERS.md) |
| [`RESEARCH_GUIDE.md`](RESEARCH_GUIDE.md) | Hướng dẫn thực nghiệm (Jev/Kev, OCR lai, GLiNER, 5-fold) | [`docs/RESEARCH_GUIDE.md`](../RESEARCH_GUIDE.md) |
| [`VISUAL_ARCHITECTURE.md`](VISUAL_ARCHITECTURE.md) | Sơ đồ kiến trúc ban đầu | [`docs/VISUAL_ARCHITECTURE.md`](../VISUAL_ARCHITECTURE.md) |
| [`COMPOSITE_DOCUMENTS_AND_SPLITTING.md`](COMPOSITE_DOCUMENTS_AND_SPLITTING.md) | Tệp ghép, ca BSR 5 trang, dấu hiệu ranh giới | [`docs/COMPOSITE_DOCUMENTS_AND_SPLITTING.md`](../COMPOSITE_DOCUMENTS_AND_SPLITTING.md) |
| [`PARALLEL_RESEARCH_PLAN.md`](PARALLEL_RESEARCH_PLAN.md) | 4 nhánh song song, hợp đồng dữ liệu, lộ trình 4 tuần | [`docs/PARALLEL_RESEARCH_PLAN.md`](../PARALLEL_RESEARCH_PLAN.md) (kế hoạch 6–8 tuần, giả thuyết H1–H14) |
| [`DECOUPLED_PARALLEL_METHODOLOGY.md`](DECOUPLED_PARALLEL_METHODOLOGY.md) | Tách phụ thuộc giữa nhóm bằng dữ liệu chuẩn và hợp đồng | [`docs/DECOUPLED_PARALLEL_METHODOLOGY.md`](../DECOUPLED_PARALLEL_METHODOLOGY.md) (tài liệu sống, có khung "đã thay đổi gì") |

**Lưu ý về liên kết.** Các liên kết tương đối *bên trong* bảy tệp lưu trữ là của bản cũ (trỏ `./docs/...`, `../src/...`, `tests/fixtures/...`); nhiều liên kết sẽ hỏng hoặc trỏ sang tệp đã được viết lại khi mở từ thư mục này. Không sửa, vì đó là bản lưu trữ. Muốn tìm đúng nơi, dùng cột "Bản sống hiện nay" ở trên.

## 2. Bảng đối chiếu: hướng ban đầu và hiện trạng

Nhãn trạng thái: **Giữ** (vẫn đúng như ban đầu), **Đổi** (cùng mục tiêu, cách làm khác), **Bỏ** (không còn là hướng đi), **Chưa kiểm** (chưa có phép đo nào quyết định được).

### A. Bài toán, dữ liệu, nhãn

| # | Hướng ban đầu | Hiện trạng | Lý do, số đo, bằng chứng |
|---|---|---|---|
| A1 | Bộ mẫu 335 PDF, **19 danh mục = 19 tên thư mục**, dùng thư mục làm nhãn | **Đổi** | Thư mục là "tủ hồ sơ", không phải loại tài liệu: 27 trong 30 nhóm tệp trùng byte nằm ở hai thư mục khác nhau. Nay 336 PDF = 304 tài liệu duy nhất, taxonomy 34 loại theo nội dung + `OTHER` + `UNREADABLE`, trong 8 nhóm; chỉ 10 loại có từ 10 tài liệu trở lên. Xem [`01_duplicates.md`](../../teams/00_data_and_eval/reports/01_duplicates.md), [`02_taxonomy_design.md`](../../teams/00_data_and_eval/reports/02_taxonomy_design.md) |
| A2 | Đơn vị đánh giá là tệp; Stratified 5-fold | **Đổi** | Chia theo tài liệu duy nhất và nhóm biểu mẫu (`StratifiedGroupKFold`), một phần TEST khóa chấm một lần, DEV lặp 3 hạt giống; để tránh rò rỉ giữa train và test và tránh chọn tham số trên TEST. Xem [`03_evaluation_protocol.md`](../../teams/00_data_and_eval/reports/03_evaluation_protocol.md) |
| A3 | Mục tiêu hiệu năng nêu trước khi có thí nghiệm (OCR chữ in > 99%, viết tay > 92%, F1 ranh giới > 95%, Macro-F1 > 97%, trích xuất 100%, < 200 ms/tài liệu) | **Đổi** | Các mục tiêu này không dựa trên phép đo. Nay mọi số là kết quả đo kèm cỡ mẫu và khoảng tin cậy; mục tiêu vận hành là *tỉ lệ sai lặng lẽ ≤ 1% trên phần tự xử lý* (chưa đạt: 4,94% tổng số tệp ở mặc định `model+merge`, 1,45% với `triage`). Xem [`01_end_to_end/RESULTS.md`](../../teams/00_data_and_eval/experiments/01_end_to_end/RESULTS.md); từng mục tiêu cũ ở các hàng dưới |
| A4 | Đáp án (gold) coi như có sẵn ("Mock Gold", `GT_*`) | **Đổi** | Không có đáp án do người kiểm. Đáp án nay là *máy tạo* và luôn được gọi là "khớp đáp án máy". Ba loại: nhãn (hai lượt gán trùng 304/304, cùng họ mô hình nên không độc lập), ranh giới (một mô hình), trường silver (Haiku đọc cả 104 đơn vị, Sonnet đọc lại 40, Opus phân xử 58 trường). Người của công ty kiểm đáp án vẫn là việc lớn nhất còn thiếu |

### B. OCR

| # | Hướng ban đầu | Hiện trạng | Lý do, số đo, bằng chứng |
|---|---|---|---|
| B1 | PDF có text layer thì đọc thẳng bằng PyMuPDF (0 ms, 100% chính xác) | **Giữ** (có điều chỉnh) | `src/ocr/pdf_ocr.py` vẫn dùng text layer khi có đủ chữ, còn lại OCR; chỉ 61 trang born-digital trong cả kho (3 thư mục), nên phần lớn tài liệu vẫn phải OCR. Xem [`01_engine_bakeoff`](../../teams/team1_ocr/experiments/01_engine_bakeoff/RESULTS.md) |
| B2 | OCR chữ in bằng RapidOCR / PaddleOCR ONNX | **Đổi** | `rapidocr_onnxruntime` 1.2.3 chỉ có 9/67 chữ cái thường có dấu tiếng Việt trong từ điển nhận dạng, nên không thể xuất 58 chữ còn lại (trang 1: tỉ lệ chữ có dấu 0,0018). Engine chọn: bộ phát hiện dòng PP-OCRv5 + VietOCR: CER 0,082 trên trang số sạch (10 trang), 0,185 khi xuống cấp; giữ 97,8% ký tự có dấu; 0,39 trang/giây khi chạy cả kho. Xem [`01_engine_bakeoff`](../../teams/team1_ocr/experiments/01_engine_bakeoff/RESULTS.md), [`07_src_engine`](../../teams/team1_ocr/experiments/07_src_engine/RESULTS.md) |
| B3 | Apple Vision (iOS-OCR-Server / Mac) làm OCR chính, "bắt trọn chữ viết tay" | **Chưa kiểm** | Không có thiết bị Apple trong phạm vi các thí nghiệm; kho không có phép đo nào dùng nó (client còn trong `src/ocr/ios_ocr_client.py`, đánh dấu cũ). Trên máy Windows + GPU, phương án đã chọn là cục bộ. Nếu công ty có Mac, đây là hướng đáng thử, nhưng phải so bằng CER trên đáp án người gõ |
| B4 | Hiệu đính chữ viết tay bằng cắt vùng + Vision LLM nhỏ (Qwen2.5-VL / **Gemini Flash**), "tiết kiệm 95% token" | **Đổi / Chưa kiểm** | Gemini Flash (đám mây) **bỏ** vì sản xuất phải on-premise. Cắt vùng bằng VLM cục bộ chưa làm (T3 của nhóm 1, [README nhóm 1](../../teams/team1_ocr/README.md)); con số 95% chưa kiểm. Điều đã đo: OCR cục bộ mất nhiều nhất ở chữ viết tay và chữ dưới con dấu (luật đúng 0,53 và 0,35, so với 0,82 và 0,95 trên bản chép của LLM đám mây); VLM cục bộ đọc cả ảnh trang đúng 0,76 ở chữ viết tay (n = 34) và 0,95 dưới con dấu (n = 20), mẫu nhỏ. Xem [`02_methods/RESULTS.md`](../../teams/team4_extraction/experiments/02_methods/RESULTS.md) |
| B5 | Không nhắc tới xoay trang, chất lượng ảnh | **Thêm** | Tự xoay trang đúng hướng 30/32 trang bị xoay (Wilson [79,9%; 98,3%]), 0/280 trang thẳng bị sót. Xem [`05_rotation`](../../teams/team1_ocr/experiments/05_rotation/RESULTS.md) |
| B6 | Mục tiêu OCR chữ in > 99%, viết tay > 92% | **Chưa kiểm** | Chưa có đáp án do người gõ nên chưa có CER trên bản quét thật; số CER 0,082 là trên trang số hóa sạch. Chữ viết tay: mới biết là sai nhiều qua xem mắt, chưa có số |

### C. Tách tệp ghép

| # | Hướng ban đầu | Hiện trạng | Lý do, số đo, bằng chứng |
|---|---|---|---|
| C1 | Luật dấu hiệu (Quốc hiệu, tiêu đề, chữ ký cuối, đánh số trang) nhận trang FIRST / CONTINUATION | **Bỏ** làm phương pháp chính | Luật có sẵn chỉ giữ nguyên 50/155 tệp nhiều trang không ghép (còn lại bị tách nhầm); luật sửa 85/155; bộ phân loại cặp trang (ngưỡng 0,5) 129/155. Xem [`01_rule_baseline`](../../teams/team2_splitting/experiments/01_rule_baseline/RESULTS.md), [`02_rule_v2`](../../teams/team2_splitting/experiments/02_rule_v2/RESULTS.md), [`04_pair_classifier`](../../teams/team2_splitting/experiments/04_pair_classifier/RESULTS.md). Các dấu hiệu vẫn là đặc trưng đầu vào của bộ phân loại cặp trang |
| C2 | Kev/Jev `Noul` trả lời "trang này có mở tài liệu mới không?" | **Đổi** | Kev `Noul` chưa thử; thay bằng Qwen3.5-4B hỏi có/không với một prompt: gần như không bao giờ nói "tài liệu mới" (0/20, 0/7, 1/46 ranh giới). Xem [`05_llm_zero_shot`](../../teams/team2_splitting/experiments/05_llm_zero_shot/RESULTS.md) |
| C3 | Tách là bước bắt buộc, mục tiêu F1 ranh giới > 95% | **Đổi** | Khoảng 92% tệp là tài liệu đơn hoặc nhiều trang không ghép, nên bộ tách cắt nhầm là làm hỏng tệp đang đúng. Dev n = 245 tệp: `model+merge` 91,9% tệp đúng hoàn toàn so với 92,3% khi không tách (hiệu −0,4 điểm [−2,9; +1,9], không tách được); TEST cùng 56/59. Tách có lợi ở cấp tài liệu (dev 87,7% so với 70,4% tài liệu giao đúng). Mặc định: `model+merge`; phương án thay thế `triage` (không tách, nghi ghép thì chuyển người). Xem [`01_end_to_end/RESULTS.md`](../../teams/00_data_and_eval/experiments/01_end_to_end/RESULTS.md) |
| C4 | Ca BSR 5 trang như kiểu mẫu của tệp ghép | **Giữ** làm minh họa; **Đổi** về quy mô | Tệp ghép khác loại trong dev chỉ có 8 tệp (20 ranh giới), cùng loại 6 tệp (7 ranh giới ngoài `BB_LAY_MAU`), TEST có 2 tệp ghép. Bộ phân loại cặp trang 20/20 ranh giới khác loại, không tách nhầm; cùng loại: quy tắc `id` đưa từ 0/7 lên 4/7 nhưng chưa có kiểm giữ ngoài. Xem [`06_same_type`](../../teams/team2_splitting/experiments/06_same_type/RESULTS.md) |

### D. Phân loại (Kev / Jev, cascade)

| # | Hướng ban đầu | Hiện trạng | Lý do, số đo, bằng chứng |
|---|---|---|---|
| D1 | Phân loại theo Jev/Kev System One: nhãn kèm **xác suất hiệu chỉnh**, ngưỡng 0,85 tự nhận / 0,60 gửi người; "100–300 ms"; "không bịa" | **Đổi** | Kev-4B chưa chạy (cần ~8,4 GB VRAM trên GPU dùng chung), mọi số "Kev" là Kev-0.8B. Kev-0.8B khi chỉ đưa tên loại: accuracy 0,962 (DEV), 0,932 [0,864; 0,983] (TEST); mô tả dài làm sụp xuống 0,300; trên OCR mất dấu 0,498. Xếp hạng tốt (AUROC 0,961) nhưng **xác suất không hiệu chỉnh** (ECE 0,441), nên ngưỡng đặt theo thứ hạng, không theo giá trị 0,85. Độ trễ 860 ms. Xem [`02_llm_and_cascade/RESULTS.md`](../../teams/team3_classification/experiments/02_llm_and_cascade/RESULTS.md) |
| D2 | Phân loại bằng Kev ở tầng 2 | **Đổi** | Tầng LLM nay là Qwen3.5-4B cục bộ qua Ollama, chỉ đọc mô tả loại: accuracy 0,983 [0,949; 1,000], độ trễ ~1,2 giây, chỉ chạy cho 5–7% tài liệu. Kev vẫn có trong mã như phương án tùy chọn, tắt mặc định |
| D3 | Cascade 3 tầng: tiêu đề nhanh → Kev → LLM suy luận | **Giữ** cấu trúc, **Đổi** nội dung | Nay: luật từ khóa (3 ms) → TF-IDF + ComplementNB (3 ms) → LLM cục bộ → người duyệt. TF-IDF thêm vào vì rẻ và mạnh: macro-F1 0,946 [0,847; 1,000] (TEST). Cascade: tự xếp 96,6–100% với 0–1 lỗi trong 59 tài liệu TEST (TEST không có tệp ghép khác loại); cross-fit trên 237 tài liệu DEV nhận 235, 0 sai (cận trên 1,27%). Xem [`04_safety_margin`](../../teams/team3_classification/experiments/04_safety_margin/RESULTS.md), [`03_src_cascade`](../../teams/team3_classification/experiments/03_src_cascade/RESULTS.md) |
| D4 | "70% tài liệu form chuẩn thoát ở tầng nhanh" | **Chưa kiểm** nguyên số này | Số gần nhất đo được: TF-IDF đơn tự xếp 61–64% tài liệu ở mức sai ≤ 1% (TEST, n = 59). Chưa có phép đo phần "thoát ở tầng tiêu đề" riêng theo nghĩa ban đầu |
| D5 | Phân loại trên ảnh trang 1 (ViT/LayoutLM) như tầng đầu | **Đổi** | Không dùng bộ phân loại ảnh riêng. Ảnh trang chỉ được dùng cho VLM đọc trường hạn (giai đoạn 3). Với 7 loại hợp đồng/thanh lý giống hệt nhau về bố cục, ý ban đầu "phải đọc chữ" vẫn đúng |
| D6 | Mục tiêu Macro-F1 > 97%, trễ < 200 ms | **Đổi** (xem A3) | Macro-F1 TF-IDF 0,946 (TEST, chỉ 10 loại đủ mẫu); cascade đo trực tiếp trung bình 54 ms, p95 649 ms khi có lời gọi LLM |
| D7 | 19 lớp là đích phân loại | **Đổi** (xem A1) | 34 loại + `OTHER` + `UNREADABLE`; 24 loại hiếm (74 tài liệu). Macro-F1 trên loại hiếm không đáng tin ở cỡ mẫu này; đọc cùng accuracy và recall loại hiếm |

### E. Trích xuất thông tin

| # | Hướng ban đầu | Hiện trạng | Lý do, số đo, bằng chứng |
|---|---|---|---|
| E1 | Trích xuất thực thể bằng GLiNER `barb-1-ie-vi` | **Đổi** | GLiNER yếu: F1 0,46 (TEST, so khớp nới lỏng). Tốt nhất khi chỉ dùng OCR cục bộ: luật/regex cho ngày, số, mã và LLM cục bộ (đầu ra ràng buộc JSON Schema) cho văn bản: F1 nới lỏng 0,90 [0,83; 0,96], so từng ký tự 0,72 [0,59; 0,82] (TEST, n = 22). Xem [`02_methods/RESULTS.md`](../../teams/team4_extraction/experiments/02_methods/RESULTS.md) |
| E2 | Mục tiêu "100% thực thể then chốt", schema thực thể (bên A/B, MST, sản phẩm...) cho hợp đồng | **Đổi** | Trọng tâm nay là **ngày hết hạn** và trường theo schema từng loại (nay 21 loại có schema). Mọi phương pháp dựa OCR đọc sai giá trị hạn ở khoảng 6% số trường (TEST n = 16), nên không tự nhận từ một nguồn. 17 loại mới: F1 mềm 0,75 [0,70; 0,79] (LLM), 0,83 [0,80; 0,86] (VLM). Xem [`03_unseen_types`](../../teams/team4_extraction/experiments/03_unseen_types/RESULTS.md) |
| E3 | Ngày trong tên tệp / ngày hết hạn: không có trong hướng ban đầu | **Thêm rồi thu hẹp** | Quy tắc tự nhận `any-model=filename` (một mô hình đọc trùng ngày trong tên tệp): 0 sai trong 49 lần (4 loại cũ), nhưng ở 17 loại mới ngày trong tên tệp đứng một mình sai 17/40 lần có ngày. Quyết định của công ty ngày 2026-10-16 (mục 3) khiến quy tắc này **không còn được dùng làm nguồn xác nhận độc lập**. Tự nhận ngày hết hạn tắt mặc định. Xem [báo cáo 04](../../teams/00_data_and_eval/reports/04_phase3_review_and_deployment.md) N2, N3 |
| E4 | Bảng hàng hóa, `audit_trail` tọa độ ô | **Chưa kiểm** | Chưa trích bảng hàng hóa; truy vết về ảnh/bảng là việc P2 của nhóm 4 ([README nhóm 4](../../teams/team4_extraction/README.md)) |

### F. Tổ chức nghiên cứu song song, đo lường

| # | Hướng ban đầu | Hiện trạng | Lý do, số đo, bằng chứng |
|---|---|---|---|
| F1 | 4 nhánh độc lập (OCR, Tách, Phân loại, Trích xuất) | **Đổi** | Thêm nhóm **00 Dữ liệu và đánh giá** (nhãn, chia dữ liệu, bộ chấm, toàn trình) vì các nhóm cần chung đáp án và bộ chấm; nay 5 thư mục trong `teams/`. Xem [`teams/README.md`](../../teams/README.md) |
| F2 | Tách phụ thuộc bằng dữ liệu chuẩn giả (mock fixtures) + hợp đồng Pydantic (`contracts.py`) | **Giữ** ý tưởng, **Đổi** nguồn dữ liệu | Hợp đồng `src/common/contracts.py` vẫn là xương sống (có test). Thay mock bằng dữ liệu thật đã đóng băng: `data/ocr_v2.jsonl`, `data/labels_v2.csv`, `data/splits/`, đáp án ranh giới và silver trường. Xem [`DECOUPLED_PARALLEL_METHODOLOGY.md`](../DECOUPLED_PARALLEL_METHODOLOGY.md) |
| F3 | Đánh giá hai pha: từng thành phần trên đáp án sạch, rồi toàn trình | **Giữ** | Làm đúng: bảng E0–E3 (thay dần từng khâu từ đáp án sang thành phần thật) và phép đo toàn trình theo tệp, 11 biến thể tách. Phát hiện chính: ở cấp tệp tách không phân biệt được với không tách. Xem [`PARALLEL_RESEARCH_PLAN.md`](../PARALLEL_RESEARCH_PLAN.md) mục 4 |
| F4 | Lộ trình 4 tuần, ghép nối ở tuần 4 | **Đổi** | Kế hoạch nay là 6–8 tuần (bản tối thiểu 6) với các điểm tích hợp; điểm tích hợp toàn trình đã làm sớm dưới dạng thí nghiệm. Mọi mốc tuần là ước lượng, không phải số đo |
| F5 | Chi phí: so Kev local (0 đồng) với Gemini API / GPT-4o trên 1.000 tài liệu | **Chưa kiểm** phần so API | Không đo đường đám mây cho sản xuất (sản xuất on-premise). Chi phí đo được là thời gian máy: ~500 trang/giờ trên một RTX 3060 dùng chung (khoảng 250–860), OCR 45%, trích xuất 52%; sai số ít nhất ±50% |

### G. Riêng tư và triển khai

| # | Hướng ban đầu | Hiện trạng | Lý do, số đo, bằng chứng |
|---|---|---|---|
| G1 | On-premise hoàn toàn, không gửi gì ra ngoài | **Giữ** cho sản xuất | Đường chạy thật không gửi gì ra ngoài. Ngoại lệ (quyết định của công ty, mục 3a): được dùng LLM đám mây để **tạo đáp án** trên tài liệu mẫu. Tài liệu mới chỉ đi qua mô hình cục bộ. Dữ liệu thật nằm trong git là rủi ro chưa xử lý (báo cáo 04, N4) |
| G2 | Dùng Gemini / Claude API để hiệu đính khi cần | **Bỏ** cho sản xuất | Xem G1. LLM đám mây chỉ còn vai trò dựng dữ liệu tham chiếu |
| G3 | Bộ mẫu đại diện cho mọi khách hàng | **Chưa kiểm** | Dữ liệu là của một công ty, một giai đoạn; chưa thử trên khách hàng, biểu mẫu, nhà cung cấp mới; TEST đã mòn sau nhiều lần mở hợp lệ |

## 3. Quyết định của công ty ngày 2026-10-16

Do chủ dự án truyền đạt (hai điểm; ghi vào [`README.md`](../../README.md) mục "Quyết định của công ty" và các nơi liên quan):

* **(a) LLM bên ngoài để tạo đáp án.** Được phép dùng LLM ngoài (đám mây) để **tạo đáp án** (silver/gold) trên tài liệu mẫu. Sản xuất vẫn on-premise; các khuyến nghị riêng tư khác giữ nguyên.
* **(b) Ngày hết hạn.** Nguyên ý chủ dự án (nói tắt): *"ngày trong tệp phải cụ thể là ngày gì thì mới là ngày hết hạn"*. **Diễn giải của nhóm** (cần xác nhận lại nếu khác ý): một ngày chỉ là ngày hết hạn khi tài liệu ghi cụ thể đó là ngày gì ("có hiệu lực đến ngày…", "ngày hết hạn…"); ngày trong tên tệp không mặc nhiên là ngày hết hạn; một số giấy tờ không có ngày hết hạn. Hệ quả: quy tắc tự nhận dựa trên khớp ngày tên tệp (`any-model=filename`) không dùng làm nguồn xác nhận độc lập; giữ `auto_accept_expiry=False`; `ngay_het_han = not_present` là kết quả hợp lệ (không phải lỗi) với loại không có hạn; quy ước phân xử "kể từ ngày ký" → `not_present` là phù hợp.

Tác động lên bảng trên: dòng E3 (quy ước tên tệp), G1 (đám mây chỉ để dựng đáp án).

## 4. Nên đọc gì tiếp

1. [`README.md`](../../README.md) gốc: hiện trạng và "những điều chưa được chứng minh".
2. [Báo cáo 04](../../teams/00_data_and_eval/reports/04_phase3_review_and_deployment.md): review độc lập, thiết kế triển khai, 15 việc ưu tiên.
3. [`docs/PARALLEL_RESEARCH_PLAN.md`](../PARALLEL_RESEARCH_PLAN.md) mục 6: giả thuyết H1–H14 với trạng thái và số đo.
