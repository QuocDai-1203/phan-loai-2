# Thí nghiệm 04 — Biên an toàn của cascade: hiệu chỉnh, đồng thuận hai nguồn, kiểm mẫu ngẫu nhiên (Nhóm 3, việc T3)

> Nhãn `data/labels_v2.csv` sha1[:10] `eb3348713a`. Ngày 2026-10-15. Chỉ DEV (237 tài liệu, nguồn `ocr_v2_p12`); **không mở TEST**. Mọi lời gọi LLM lấy từ cache của 02 (chỉ đọc, 941 lần trúng, 0 lỡ); không gọi mô hình mới.
> Tái lập: `.venv\Scripts\python.exe -X utf8 teams\team3_classification\experiments\04_safety_margin\extract_signals.py` rồi `...\run_margin.py`. Đầu ra ở `teams/team3_classification/results/04_safety_margin/` (`dev_signals.csv` chứa `doc_id`: chỉ dùng nội bộ).
> Nhãn là nhãn máy; "sai" nghĩa là khác đáp án máy.

## Kết luận ngắn

1. **Trên DEV hiện có, không đo được lợi ích của bất kỳ biên an toàn nào**: cascade ở mọi mức biên có 0 lỗi cross-fit trong 221–235 tài liệu tự nhận; cận trên Clopper–Pearson 95% của tỉ lệ sai đều quanh 1,3% và do **cỡ mẫu** quyết định, không do mức biên. Không có lỗi để các mức tách nhau, nên **dữ liệu chưa đủ để chọn giữa các mức**.
2. Các mức "đồng thuận hai nguồn" **làm giảm độ phủ có ý nghĩa thống kê** (1,7 đến 5,9 điểm so với mức đang dùng, khoảng tin cậy loại 0) mà không giảm lỗi nào (0 so với 0). Đó là giá của bảo hiểm, không phải bằng chứng bảo hiểm có tác dụng.
3. Hiệu chỉnh độ tin cậy đơn điệu (nhiệt độ, isotonic) **không đổi thứ hạng** nên không đổi đường risk–coverage (trừ các điểm hòa); nó chỉ cho phép phát biểu ngưỡng bằng xác suất. Với LLM chính (`q35_s1`) không học được hiệu chỉnh vì **0 lỗi** trong 235 dự đoán có nhãn dùng được.
4. Kiểm mẫu ngẫu nhiên đã có trong mã (tắt mặc định). Trên DEV nó không bắt được gì vì không có lỗi; để thấy ít nhất 1 lỗi với xác suất 95% khi tỉ lệ sai thật là 1% cần kiểm khoảng **299 tài liệu** (≈ `ln 0,05 / ln 0,99`), tức nhiều hơn mọi mẫu 5–10% ở quy mô 237 tài liệu.

## 1. Hiệu chỉnh (out-of-fold, cross-fit 5 fold seed 0)

Bộ hiệu chỉnh của fold k chỉ học từ các fold khác. "Nhiệt độ" là xấp xỉ một tham số trên `logit(conf)` cho độ tin cậy lớp đứng đầu (không có logit đầy đủ). ECE 10 bin, khoảng 95% bootstrap theo tài liệu (2000 lần). Đường risk–coverage: `results/04_safety_margin/risk_coverage.png`.

| nguồn (DEV) | n có nhãn dùng được | số sai | hiệu chỉnh | ECE [CI] | AURC | số giá trị tin cậy khác nhau |
|---|---|---|---|---|---|---|
| TF-IDF (OOF, ≠ RARE_OR_OTHER) | 179 | 5 | thô | 0,051 [0,026; 0,080] | 0,0024 | 128 |
| | | | nhiệt độ | 0,049 [0,029; 0,078] | 0,0024 | 168 |
| | | | isotonic | 0,022 [0,007; 0,047] | 0,0036 | 11 |
| Qwen3.5-4B 1 bước (`q35_s1`) | 235 | **0** | thô | 0,117 [0,094; 0,141] | 0,0000 | 235 |
| | | | nhiệt độ | 0,082 [0,060; 0,107] | 0,0000 | 74 |
| | | | isotonic | 0,000 (suy biến: mọi giá trị về 1,0) | 0,0000 | 1 |
| Qwen3.5-4B 2 bước (`q35_s2`) | 236 | 4 | thô | 0,084 [0,067; 0,102] | 0,0002 | 236 |
| | | | nhiệt độ | 0,036 [0,021; 0,054] | 0,0002 | 69 |
| | | | isotonic | 0,000 [0,000; 0,001] | 0,0002 | 4 |
| Qwen2.5-3B 1 bước (`q25_s1`) | 216 | 36 | thô | 0,104 [0,070; 0,148] | 0,0240 | 215 |
| | | | nhiệt độ | 0,097 [0,069; 0,139] | 0,0243 | 216 |
| | | | isotonic | 0,054 [0,041; 0,100] | 0,0276 | 28 |

Đọc: (i) ECE giảm nhờ hiệu chỉnh nhưng với 0–5 lỗi, ECE của hai dòng Qwen3.5 **không đáng tin** (isotonic "ECE = 0" chỉ vì bộ hiệu chỉnh trả hằng số). (ii) Hiệu chỉnh isotonic làm AURC của TF-IDF và q25 **xấu đi** (nhiều giá trị hòa). (iii) Chỉ `q25_s1` (36 lỗi) có đủ lỗi để hiệu chỉnh có nghĩa, nhưng nó không phải tầng chính. (iv) Kết luận cũ của 02 giữ nguyên: logprob một bước của Qwen3.5 không có tín hiệu từ chối; hai bước có (AURC 0,0002 với 4 lỗi) nhưng 4 lỗi vẫn là mẫu rất nhỏ.

## 2. Thang biên an toàn: tự xếp, số sai, cận trên, số cross-fit

"Resub" = chọn ngưỡng và chấm trên cùng DEV (lạc quan). "Cross-fit" = chọn trên 4 fold, áp lên fold còn lại. Cận trên = Clopper–Pearson 95% một phía của tỉ lệ sai trên phần tự nhận. Tầng LLM = `q35_s1` (cấu hình đang dùng); nguồn thứ hai của đồng thuận: `q35_s2` (cùng mô hình, prompt hai bước), `q25_s1` (Qwen2.5-3B, mô hình khác), hoặc nhãn TF-IDF. Cả hai mô hình Ollama đều đã có sẵn; không gọi thêm.

| mức | cách chọn | resub tự nhận / sai | cross-fit tự nhận (n = 237) [CP 95% của độ phủ] | cross-fit sai | cận trên sai (cross-fit) | luật / TF-IDF / LLM / người (cross-fit) |
|---|---|---|---|---|---|---|
| L0 (đang dùng) | sai ≤ 1% trên DEV | 236 / 1 | 235 = 99,2% [97,0; 99,9] | 0 | 1,27% | 181 / 32 / 22 / 2 |
| L1 | không lỗi nào trên tập chọn | 235 / 0 | 234 = 98,7% [96,4; 99,7] | 0 | 1,27% | 181 / 0 / 53 / 3 |
| L2 | xác suất isotonic ≥ 99% | 235 / 0 | 235 = 99,2% [97,0; 99,9] | 0 | 1,27% | 181 / 33 / 21 / 2 |
| L3 | cận trên CP trên tập chọn ≤ 5% | 236 / 1 | 235 = 99,2% [97,0; 99,9] | 0 | 1,27% | 181 / 32 / 22 / 2 |
| L4 | cận trên CP trên tập chọn ≤ 2% | 236 / 1 | 234 = 98,7% [96,4; 99,7] | 0 | 1,27% | 181 / 0 / 53 / 3 |
| C1 | L1 + `q35_s2` cùng nhãn | 234 / 0 | 231 = 97,5% [94,6; 99,1] | 0 | 1,29% | 181 / 31 / 19 / 6 |
| C2 | L1 + `q25_s1` cùng nhãn | 227 / 0 | 223 = 94,1% [90,3; 96,7] | 0 | 1,33% | 181 / 22 / 20 / 14 |
| C3 | L1 + TF-IDF cùng nhãn | 224 / 0 | 223 = 94,1% [90,3; 96,7] | 0 | 1,33% | 181 / 0 / 42 / 14 |
| C4 | L1 + TF-IDF **và** `q35_s2` cùng nhãn | 224 / 0 | 221 = 93,2% [89,3; 96,1] | 0 | 1,35% | 181 / 31 / 9 / 16 |

Chênh lệch ghép cặp theo tài liệu so với L0 (bootstrap 2000 lần, cross-fit): L1, L2, L3, L4: độ phủ −0,4 đến 0,0 điểm, khoảng chứa 0 → **không tách được**. C1: −1,7 [−3,8; −0,4]; C2: −5,1 [−8,0; −2,5]; C3: −5,1 [−8,0; −2,5]; C4: −5,9 [−8,9; −3,0] → độ phủ **giảm có ý nghĩa**. Chênh lệch số lỗi: 0 ở mọi mức (khoảng [0; 0]) → **không tách được về an toàn**.

Lưu ý:
- **Không tái tạo đúng 98,3% cross-fit của 02 §7** (02: 233/237 với 0 sai; ở đây L0 cho 235/237 với 0 sai). Resub khớp 02 (236, 1 sai). Chênh 2 tài liệu chưa tìm ra nguyên nhân; nghi 02 chọn thêm chế độ `agree` trong cross-fit (thử `none`+`s` cho 234, vẫn không ra 233). Đây là con số của 04, không thay con số 02.
- Chỉ có **1 lỗi** trên toàn DEV ở cấu hình đang dùng (tài liệu loại `OTHER` bị TF-IDF nhận thành `HD_MUA_BAN`). Mọi lập luận "mức nào an toàn hơn" dựa vào một tài liệu. Trong cross-fit, ở mọi mức tài liệu này không còn bị tự nhận sai (chưa phân tích từng mức vì sao; ngưỡng mỗi fold học từ 4 fold còn lại).
- Hai mức không-đồng-thuận nghiêm (L1, L4) tắt cả tầng TF-IDF và đẩy gánh nặng sang LLM (53 tài liệu): đổi lấy độ trễ ~1,2 s/tài liệu cho 22% tài liệu thay vì 9% (số độ trễ từ 02 §9, không đo lại).
- Con số "cận trên ≈ 1,3%" là hàm của n ≈ 230 và 0 lỗi. Muốn chứng minh sai ≤ 1% cần ≈ 300 tài liệu tự nhận không lỗi **liên tiếp** (quy tắc ba) trên dữ liệu độc lập, tức T4 (chạy bóng), không phải mức biên nào ở trên.

## 3. Kiểm mẫu ngẫu nhiên trên phần tự nhận (cross-fit)

Hàm `audit_flags` (tất định theo `seed` + id tài liệu) chọn tỉ lệ `rate`; tài liệu được chọn vẫn tự nhận nhưng giữ lại cho người kiểm. Trung bình 200 seed trên phần tự nhận cross-fit:

| mức | tỉ lệ kiểm | tự nhận (cross-fit) | bị giữ để kiểm (TB) | còn tự xếp hẳn (TB; % tổng) | lỗi bắt được / lỗi còn lọt |
|---|---|---|---|---|---|
| L0 | 0% | 235 | 0 | 235 (99,2%) | 0 / 0 |
| L0 | 5% | 235 | 12,0 | 223,0 (94,1%) | 0 / 0 |
| L0 | 10% | 235 | 23,5 | 211,5 (89,2%) | 0 / 0 |
| L1 | 5% / 10% | 234 | 11,9 / 23,5 | 222,1 (93,7%) / 210,5 (88,8%) | 0 / 0 |
| C1 | 5% / 10% | 231 | 11,8 / 23,1 | 219,3 (92,5%) / 207,9 (87,7%) | 0 / 0 |

Không có lỗi trong phần tự nhận cross-fit nên bảng này chỉ đo **chi phí** (5–10% tự xếp bị chuyển sang người), không đo lợi ích. Xác suất bắt ≥ 1 lỗi: nếu có e lỗi lọt, kiểm mẫu tỉ lệ r bắt được với xác suất 1 − (1 − r)^e (5%: 9,8% với 2 lỗi; 10%: 19%). Kiểm mẫu có nghĩa là **giám sát** tỉ lệ sai theo thời gian (T4), không phải lưới an toàn cho từng tài liệu.

## 4. Mã đã thêm vào `src/classification/` (tất cả tắt mặc định)

- `cascade.py`: `CascadeParams.consensus` ∈ {`none`,`s`,`llm2`,`s_llm2`} (tầng LLM chỉ nhận khi TF-IDF và/hoặc nguồn LLM thứ hai **cùng nhãn**; AND, khác `agree` là OR; thiếu nguồn thứ hai → không nhận gì, không âm thầm bỏ yêu cầu); `Signals.llm2_label/llm2_conf/lat_llm2`; `audit_flags`, `apply_audit`, `decision_records`.
- `doc_classifier.py`: `DocumentClassifier(..., llm2=, audit_rate=, audit_seed=, decision_log=)`. Tài liệu bị kiểm mẫu giữ nhãn và tầng của mô hình nhưng `requires_human_review=True`, `abstain_reason="audit_sample"`. Khi LLM thứ hai bất đồng: về người với `abstain_reason="llm_no_consensus"` kèm gợi ý. `decision_log` là JSONL (id, tầng, nhãn, độ tin cậy, nhận/từ chối, audit; không chứa văn bản).
- Test: `tests/test_classif_safety_margin.py` (13 test). Hồi quy: `test_cascade.py`, `test_classif_doc_classifier.py` vẫn xanh; mặc định không đổi (kiểm bằng test "default off").
- **Chưa kiểm hồi quy từng tài liệu với `llm2`** (cache `q35_s2`/`q25_s1` có trên DEV; đồng thuận mới được đo ở mức tín hiệu qua `cascade.py`, chưa qua `DocumentClassifier` đầu-cuối).

## 5. Hạn chế

- Chỉ DEV, chỉ 1 lỗi ở cấu hình chính; các số "không tách được" phản ánh thiếu dữ liệu, không phản ánh hai mức tương đương.
- Hiệu chỉnh nhiệt độ ở đây là xấp xỉ một tham số trên độ tin cậy lớp đứng đầu.
- Chưa chạy TEST (không cần). Chưa có nhãn do nhân viên công ty kiểm.
- Đề xuất: chưa đổi mặc định. Nếu công ty muốn bảo hiểm trước khi có dữ liệu bóng, C1 (đồng thuận hai prompt, mất ~1,7 điểm độ phủ) là mức rẻ nhất; C2/C3 mất ~5 điểm. Lựa chọn thật sự phải dựa trên T4.
