# T2 — Đánh giá bước tự xoay trang của `ocr_v2`

> `labels_v2.csv` sha1[:10] = `eb3348713a` · ngày 2026-10-15 · nguồn văn bản: `data/ocr_v2.jsonl` (chỉ đọc; trang được render lại từ PDF gốc để xem hướng).
> Tái lập một dòng: `make_sheets.py` → (xem tờ tiếp xúc, đáp án ở `gold_annotations.py`) → `evaluate_rotation.py` → `reocr_compare.py --device cuda:0`.
> **Đáp án hướng do mô hình (Claude) nhìn ảnh và ghi, không phải người** (xem §1 và §5). Mọi con số là "so với đáp án máy".

## 1. Cách làm

* `make_sheets.py` dựng ba tập trang rồi ghép thành **tờ tiếp xúc 3×3** (496 px/ô, `_sheets/`, đã `.gitignore` vì là ảnh giấy tờ thật; 40 tờ):
  1. **Bị xoay**: mọi trang có cờ `rotated_*` của `ocr_v2.jsonl` — 50 trang, trong đó 10 là bản sao trùng byte; còn **40 trang duy nhất / 18 tài liệu**.
  2. **Loại hay nằm ngang** (mục 7.6 của `02_taxonomy_design.md`): *toàn bộ* trang duy nhất của `HO_SO_QUAN_LY_PCCC`, `GCN_BAO_HIEM`, `GCN_ATKT_BVMT_PT` (đăng kiểm ghe), `BAN_VE_KY_THUAT` chưa nằm trong tập 1: **213 trang**.
  3. **Ngẫu nhiên không bị xoay**: 100 trang rút từ 718 trang duy nhất còn lại (không bị xoay, không thuộc tập 2), **seed 20261015** (`random.Random(seed).sample`).
  Tổng **353 trang đã xem** (94 tài liệu).
* Đáp án = số độ xoay **ngược chiều kim đồng hồ** cần áp lên ảnh gốc để chữ thẳng, cùng quy ước với cờ `rotated_90/180/270` (`np.rot90`). Chữ đọc từ dưới lên = 270, từ trên xuống = 90, chữ lộn ngược = 180. Với **trang gần trống** (trắng, chỉ có vệt đen mép giấy của máy scan, vài dòng lẻ: 41 trang) hướng không xác định; chúng được tách riêng.
* Quy trình xem: đọc hướng dòng chữ in trên tờ tiếp xúc (đầu dòng dồn về phía nào, số mục "1. 2. 3." ở đầu dòng, tiêu đề, logo, chữ ký), cắt vùng phóng to với trang khó (26, 30, 31, 33, 9, 19, 25, 28 — `zoom_sheets.py`). Sau khi xem xong, tôi mới đối chiếu với hướng `ocr_v2` đã áp; **một trang (idx 30, bản vẽ) tôi đã đọc nhầm là thẳng và sửa thành 180** sau khi cắt vùng nhãn bản vẽ và thấy `ocr_v2` đọc nó tốt hơn khi lật 180 (vậy trang này không còn độc lập hoàn toàn với `ocr_v2`). Đáp án chưa có người kiểm.
* `orientation_gold.csv`: `doc_id, page (đếm từ 1), gold_deg, applied_deg (ocr_v2), near_blank_gold, n_chars_ocr_v2, correct, tap`. Bản sao trùng byte (`tap = rotated_dup`) thừa nhận đáp án của bản đại diện.

## 2. Độ chính xác hướng (trang có chữ, so khớp hướng `ocr_v2` đã áp với đáp án)

Khoảng tin cậy: Wilson theo trang; dòng "theo tài liệu" là bootstrap 4000 lần lấy lại **tài liệu** (các trang cùng tài liệu không độc lập).

| tập | đúng / tổng | tỉ lệ | Wilson 95% | bootstrap theo tài liệu |
|---|---|---|---|---|
| trang bị xoay (cờ `rotated_*`), có chữ | 30 / 32 | 0,938 | [0,799; 0,983] | [0,850; 1,000] (13 tài liệu) |
| loại hay nằm ngang, **toàn bộ** (không bị xoay) | 182 / 182 | 1,000 | [0,979; 1,000] | 14 tài liệu |
| ngẫu nhiên không bị xoay | 98 / 98 | 1,000 | [0,962; 1,000] | 74 tài liệu |
| tất cả (cộng gộp, **không** đại diện cho kho vì tập 1 và 2 là toàn bộ chứ không rút mẫu) | 310 / 312 | 0,994 | [0,977; 0,998] | [0,985; 1,000] |

Phân tích theo loại sai:

* **Sót (cần xoay mà không xoay): 0/280** trang không bị xoay có chữ (182 loại-nằm-ngang + 98 ngẫu nhiên). Giới hạn trên Wilson 95%: **2,1%** (loại nằm ngang), **3,8%** (ngẫu nhiên). Nghĩa là trong 718 trang duy nhất ngoài tập 2 có thể còn tối đa vài chục trang sót (ước 3,8% × 718 ≈ 27 là cận trên, không phải ước lượng điểm; ước lượng điểm gần 0).
* **Xoay thừa trên trang có chữ (trang thẳng bị xoay): 0/32** (sau khi sửa idx 30; trước khi sửa tôi đã coi nó là xoay thừa — xem §1).
* **Xoay nhầm hướng (90 ↔ 270): 2/32** — `7ee3bbfe72eb` trang 15 và `5aad587dd02b` trang 19, cả hai thuộc sổ theo dõi PCCC, engine chọn 270 trong khi chữ đọc từ trên xuống (cần 90). Văn bản của hai trang này mất dấu gần hết (§4).
* Trong sổ PCCC (23 trang bị xoay, có chữ) có **cả hai chiều**: 16 trang cần 270 và 7 trang cần 90 (người scan lật tập giấy lẫn lộn), nên không thể sửa bằng "luôn xoay 270".

## 3. Trang gần trống bị xoay nhầm (cái bẫy thật của bước xoay)

| | số |
|---|---|
| trang gần trống đã xem | 41 (ngẫu nhiên + tập 2: không bị xoay; tập 1: bị xoay) |
| trong đó `ocr_v2` đã **xoay** | **8** (7 trang `HD_MUON_BON`, 1 trang `HD_NHUONG_QUYEN_DAI_LY`; thêm 2 bản sao trùng byte → 10 trên toàn kho, README ghi "9", số đúng là 10) |
| `n_chars` của 8 trang đó | 3, 4, 5, 5, 6, 6, 6, 7 (ký tự rác) |
| `n_chars` của trang **xoay đúng, có chữ**, ít nhất | 169 (40 trang: 169 … 3470) |

Nguyên nhân (đọc mã, `vietocr_engine.py::ocr`): bộ phát hiện dòng nhận **vệt đen dọc mép giấy** của máy scan là một hộp đứng duy nhất; điều kiện "tổng chiều dài hộp đứng / tổng chiều dài hộp > 0,6" đạt ngay với một hộp nên engine "xoay trang 90/270" rồi nhận dạng vệt đen ra vài ký tự rác. Hai nhóm tách hẳn (3–7 so với ≥ 169 ký tự) nên một ngưỡng 30 ký tự chia được; số 30 là chọn tay giữa hai nhóm, **chỉ có 8 trang rác và 40 trang tốt làm cơ sở**.

## 4. Chất lượng chữ trước/sau (chạy lại engine thật trên GPU dùng chung, 10 trang lệch, `reocr_compare.csv`)

Chỉ số: số ký tự; tỉ lệ token ≥ 2 chữ cái là âm tiết tiếng Việt hợp lệ theo luật chính tả (`is_vn_syllable` của `01_engine_bakeoff`, không dùng từ điển); tỉ lệ chữ cái có dấu (tiếng Việt thật ≈ 0,25–0,28).

| trang | `ocr_v2` tự quyết định | ép hướng đúng (90) |
|---|---|---|
| `7ee3bbfe72eb` p15 (xoay nhầm 270) | 169 ký tự, âm tiết hợp lệ 0,25, dấu 0,00 | 188 ký tự, **0,67**, dấu 0,12 |
| `5aad587dd02b` p19 (xoay nhầm 270) | 1561 ký tự, âm tiết hợp lệ 0,81, dấu 0,05 | 1127 ký tự, **0,96**, dấu **0,26** |

Chữ đọc ngược gần như mất hết dấu (0,00 và 0,05 so với 0,12 và 0,26) dù tỉ lệ âm tiết hợp lệ của trang 19 vẫn 0,81: **tỉ lệ âm tiết hợp lệ không thấy lỗi dấu, nên dùng cùng tỉ lệ chữ có dấu**. Cỡ mẫu 2 trang: chỉ minh họa, không thống kê. Trên 8 trang gần trống bị xoay nhầm, ép hướng 0 (không xoay) cho 1–4 ký tự rác thay vì 3–7, tức vẫn là rác (vệt đen vẫn bị đọc thành chữ); chỉ việc bỏ văn bản mới cho kết quả trống đúng.

## 5. Quyết định và thay đổi mã

* **Giữ** bước tự xoay: trên các trang có chữ nó đúng 30/32 (Wilson 0,80–0,98) và không sót trang nào trong 280 trang không bị xoay.
* **Cài điều kiện "không xoay trang ít chữ"** trong `src/ocr/pdf_ocr.py` (tham số mới `min_chars_for_rotation`, mặc định 30, `0`/`None` = tắt để tái tạo y hệt `ocr_v2.jsonl`; chuyển qua `ocr_page`, `ocr_pdf_pages`, `ocr_pdf`): nếu engine báo `rotated_*` mà văn bản < 30 ký tự thì **bỏ văn bản**, bỏ cờ xoay, thêm `rotation_rejected_low_text:<độ>` và `empty_text`. Trên 8 trang gần trống bị xoay nhầm → kết quả **trống** (0 ký tự) cả 8 (`reocr_compare.csv`, biến thể `luat_moi_pdf_ocr`); hai trang xoay nhầm hướng có chữ không đổi (169 và 1561 ký tự, vẫn `rotated_270`). Quy tắc chỉ đụng tới trang có cờ `rotated_*` (50 trang của `ocr_v2`): 10 trang gần trống sẽ thành trống, 40 trang có chữ (đều ≥ 169 ký tự) không đổi; 1034 trang còn lại không có cờ xoay nên không bị ảnh hưởng.
  Test: `tests/test_ocr_rotation_guard.py` (8 test: trang xoay ngắn → trống; trang xoay đủ chữ không đổi; trang ngắn không xoay không đổi; ngưỡng đúng 30 giữ / 29 bỏ; tắt bằng `0`/`None`; chuyển qua `ocr_pdf`) cùng `tests/test_ocr_pdf.py`, `tests/test_ocr_errors.py` vẫn xanh (30 test).
  **Lưu ý ảnh hưởng dữ liệu cũ:** `scripts/build_ocr_dataset.py` gọi `ocr_pdf_pages` nên chạy lại cả kho sẽ cho 10 trang này trống thay vì vài ký tự rác; phần còn lại của kho không đổi. Chưa chạy lại cả kho (46 phút GPU).
* **Chưa sửa** lỗi chọn nhầm 90/270 (2 trang). Gợi ý (chưa thử, chỉ 2 trang làm bằng chứng): chọn hướng bằng tỉ lệ chữ có dấu hoặc âm tiết hợp lệ trên toàn trang thay vì độ tin cậy trung bình trên 12 dòng dài nhất.

## 6. Hạn chế

* Đáp án do mô hình đọc từ ảnh thu nhỏ, chưa có người kiểm; 1 trang đã đổi sau khi đối chiếu với OCR (nên không độc lập hoàn toàn). Trang bản vẽ (4 trang có chữ) có chữ nhiều hướng trong cùng một trang nên "hướng đúng" mang tính ước định theo khối tiêu đề/nhãn chính.
* Tập "loại nằm ngang" là toàn bộ nên không có khoảng tin cậy ngoại suy; tập ngẫu nhiên chỉ 100 trang nên cận trên của tỉ lệ sót còn 3,8%. 94 tài liệu nhưng tập 1 chỉ 13 tài liệu (sổ PCCC chiếm 23/32 trang): khoảng tin cậy theo tài liệu rộng.
* Sổ PCCC là loại duy nhất bị lật hai chiều; kết luận về chiều 90 dựa trên 7 trang, 2 trong đó engine chọn sai.
* Chạy lại OCR trên GPU dùng chung; số giây không có ý nghĩa ở đây (chỉ so chữ).
