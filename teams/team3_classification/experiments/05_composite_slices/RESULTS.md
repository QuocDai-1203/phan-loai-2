# Thí nghiệm 05 — Vì sao biên bản giao nhận trong tệp ghép bị gán `PHIEU_XUAT_KHO` (Nhóm 3, việc T9 và hậu quả của e2e)

> Nhãn `data/labels_v2.csv` sha1[:10] `eb3348713a`. Ngày 2026-10-15. Nguồn văn bản: `data/ocr_v2.jsonl` (OCR local, từng trang). Không mở TEST.
> **Phạm vi: 8 tệp ghép khác loại, tất cả của MỘT nhà cung cấp** (`data/splits/excluded_composites.csv`; 28 lát theo đáp án, 34 trang, 7 lát biên bản giao nhận). Mọi số trên 8 tệp là **chẩn đoán/giả thuyết**, không phải ước lượng tổng quát. Phần kiểm hồi quy DEV (237 tài liệu đơn lẻ) mới là phần kiểm "không làm hỏng".
> Tái lập (từ gốc repo, `$py = ".venv\Scripts\python.exe -X utf8"`): `$py teams\team3_classification\experiments\05_composite_slices\analyze_dev.py`, `...\diagnose.py`, `...\eval_fix.py`. Cache LLM mới ghi vào `05_composite_slices/_cache/` (không commit). Đầu ra ở `teams/team3_classification/results/05_composite_slices/` (CSV có `doc_id`: nội bộ).

## 1. Nguyên nhân (đã đo)

Chuỗi sai gồm **hai mắt xích**, cả hai đều thuộc phía phân loại chứ không phải bộ tách:

1. **Cổng luật bị "mơ hồ".** Trang biên bản giao nhận của nhà cung cấp này có tiêu đề «BIÊN BẢN GIAO NHẬN HÀNG» ở đầu (ký tự ~180–320 của văn bản chuẩn hóa) **và** một tên cột trong bảng hàng hóa là «Phiếu Xuất kho Thành phẩm» (ký tự ~830–1000, vẫn trong cửa sổ quét 1500 ký tự). Cổng luật thấy từ khóa của cả hai loại (`BB_GIAO_NHAN_HANG_HOA`: 2 từ khóa; `PHIEU_XUAT_KHO`: 3 từ khóa), không quyết định → chuyển xuống tầng sau. Đúng 6/6 lát BB một trang đều rơi vào trường hợp này.
2. **Ngưỡng TF-IDF quá dễ.** TF-IDF (huấn luyện trên DEV) dự đoán `PHIEU_XUAT_KHO` với độ tin cậy 0,56–0,66; ngưỡng `th_s` = 0,282 (chọn trên DEV, dễ dãi, README bẫy 7) nên nhận. LLM không được hỏi. Kết quả: 6/6 lát BB một trang bị tầng TF-IDF nhận là `PHIEU_XUAT_KHO` (README nhóm 3 trước đó ghi 6/7 trên toàn 7 lát BB; lát thứ 7 là biên bản nghiệm thu 2 trang, luật không khớp, LLM nhận đúng với độ tin cậy 0,99).

Vì sao TF-IDF/luật chưa từng gặp lỗi này ở DEV: **không tài liệu đơn lẻ nào trong DEV có dạng này**. DEV có 16 BB_GIAO_NHAN đơn lẻ, luật đúng 16/16, không cái nào mơ hồ với `PHIEU_XUAT_KHO`, từ khóa BB nằm ở ký tự 120–249; 10 PHIEU_XUAT_KHO đơn lẻ, luật đúng 10/10, từ khóa nằm ở ký tự 0. Mẫu BB trong tệp ghép là một biểu mẫu khác (kèm cột tham chiếu số phiếu xuất kho, dài trung vị ~1300 ký tự so với 770 của BB DEV). Đây là điểm yếu **tổng quát hóa sang biểu mẫu chưa thấy** (README, mục "Chưa đo"), được lộ ra bởi tệp ghép.

Phụ: 46/237 tài liệu DEV cũng có luật "mơ hồ" (14 `DON_DAT_HANG`|`HD_MUA_BAN`, 6 `GCN_DKDN`|`CCCD`, 5 `BB_THANH_LY_HD`|`HD_NHUONG_QUYEN_DAI_LY`, ...); mọi trường hợp này đều có lớp đúng là lớp có từ khóa xuất hiện **sớm nhất** trong văn bản (46/46), đây là cơ sở của cách sửa dưới đây.

## 2. Các cách sửa đã thử

| Cách | Kết quả | Quyết định |
|---|---|---|
| **A. Gỡ mơ hồ theo vị trí tiêu đề** (`DocumentClassifier(rule_title_tiebreak=True)`): khi ≥ 2 lớp khớp, chọn lớp có từ khóa sớm nhất nếu nó nằm trong 400 ký tự đầu và mọi lớp kia chỉ xuất hiện sau ≥ 300 ký tự (hiện thực `deciding_cue` "tiêu đề quyết định") | Xem mục 3 và 4 | **Thêm làm tùy chọn, tắt mặc định** (xem lý do ở mục 5) |
| B. Đặc trưng tiêu đề cho TF-IDF (lặp 300 ký tự đầu) | Không sửa được: 7 lát BB vẫn bị gán `PHIEU_XUAT_KHO` (6) / `DON_DAT_HANG` (1) với độ tin cậy 0,48–0,57 (thấp hơn, vẫn ≥ 0,28); DEV OOF Track S giảm 0,979 → 0,971 (n = 237, 2 tài liệu) | Bỏ |
| C. Phân loại theo trang (T9) | Chỉ có ý nghĩa khi gộp; xem mục 4: lát BB một trang nên phân loại theo trang = theo lát; lợi ích đến từ cách A, không từ việc tách theo trang | Không thêm mã |
| D. Hỏi LLM cho tài liệu có luật mơ hồ (thay vì để TF-IDF nhận) | LLM trả lời đúng `BB_GIAO_NHAN_HANG_HOA` ở 3/3 lát nó kịp trả lời (độ tin cậy 0,99–0,995); 4/7 lát **hết giờ 120 s** do GPU dùng chung (không có nhãn) → chưa đủ để kết luận; chưa đưa vào mã | Chưa làm; việc cần làm |
| E. Sửa `deciding_cue`/mô tả trong `taxonomy_v2.json` | **Không làm**: đổi mô tả làm lỡ cache LLM của mọi lời gọi (README bẫy 20) và phải đo lại toàn bộ; ngoài phạm vi | Không |

## 3. Đánh giá (a): 8 tệp ghép, lát theo đáp án (chẩn đoán, một nhà cung cấp)

| | cơ sở | + `rule_title_tiebreak` |
|---|---|---|
| lát đúng loại (28 lát) | 22/28 = 78,6% [Wilson 60,5; 89,8] | **28/28** [87,9; 100] |
| trong đó lát BB_GIAO_NHAN (7) | 1/7 (6 bị gán PXK) | 7/7 (0 gán PXK) |
| lát khác BB (21) | 21/21 | 21/21 |
| tệp mà mọi lát đúng (8 tệp) | 2/8 | 8/8 |
| tầng quyết định lát BB | TF-IDF 6, LLM 1 | luật 6, LLM 1 |
| theo từng trang (34 trang; T9) đúng | 26/34 | 32/34 [80,9; 98,4]; 2 trang còn lại về người cả hai cấu hình |
| tệp mà mọi trang đúng | 1/8 | 7/8 |

Đây là kết quả trên **chính 8 tệp đã dùng để tìm ra nguyên nhân**: đúng là sự khắc phục điều đã quan sát, không phải bằng chứng tổng quát hóa (cỡ mẫu 8 tệp, 1 nhà cung cấp, 6 trang BB gần như giống hệt nhau).

## 4. Đánh giá (b): không làm hỏng DEV (kiểm hồi quy 237 tài liệu)

Cấu hình như `03_src_cascade`: TF-IDF huấn luyện theo fold, LLM từ cache chỉ đọc của 02 (22 trúng, 0 lỡ), mức 1%.

| | cơ sở | + `rule_title_tiebreak` |
|---|---|---|
| tự nhận / sai | 236 / 1 | 236 / 1 |
| tầng luật / TF-IDF / LLM / người | 181 / 43 / 12 / 1 | 206 / 22 / 8 / 1 |

- Quyết định giữ nguyên (tầng **và** nhãn): **212/237**; **đổi tầng: 25**; **đổi nhãn: 0**; số lỗi không đổi (1, cùng tài liệu). 25 thay đổi đều là luật nhận thay cho TF-IDF (21) hoặc LLM (4) với **cùng nhãn**.
- Cơ sở trùng 237/237 với kết quả 03 (181/43/12/1). Độ chính xác của riêng 25 quyết định luật mới: 25/25 đúng (cận trên 95% của tỉ lệ sai: 11,3%, rất rộng do n nhỏ); các tham số 400/300 được chọn **theo nguyên tắc** (tiêu đề ở đầu trang, tên cột nằm sâu), nhưng được **kiểm** trên chính DEV; mọi cặp (vùng, khoảng cách) thử (400/300, 300/300, ∞/100, ∞/500, kể cả "luôn chọn sớm nhất" 46/46) đều đúng 100% trên DEV, nên kết quả không nhạy với tham số.

## 5. Quyết định về mặc định

Cải thiện ở (a) **không tách khỏi nhiễu** vì chỉ có 8 tệp một nhà cung cấp; ở (b) không có thay đổi nhãn hay lỗi nào, và đổi 25 quyết định từ tầng rẻ/đắt sang luật (rẻ hơn, nhanh hơn). Theo quy tắc đề bài ("giữ mặc định cũ nếu cải thiện không tách được") **mặc định giữ nguyên (`rule_title_tiebreak=False`)**; mã, test (`tests/test_classif_title_tiebreak.py`, 5 test) và số liệu đã có để nhóm 00/chủ phiên bật sau khi có thêm mẫu BB/PXK từ nhiều biểu mẫu. Bật cờ này trong `src/pipeline.py` nằm ngoài phạm vi của việc này.

Tác dụng phụ cần biết: tiebreak cho luật quyết định trên 25/237 tài liệu DEV mà trước đây luật bỏ qua; luật là tầng không có xác suất (điểm heuristic), nên nếu biểu mẫu mới có tên loại khác nằm trong vùng tiêu đề thì có thể nhận sai mà không có độ tin cậy cảnh báo. Đây là rủi ro chưa đo trên biểu mẫu chưa thấy.

## 6. Việc còn lại

1. Thêm mẫu BB_GIAO_NHAN/PXK từ nhiều nhà cung cấp (nhóm 00 T3/T5) rồi đo lại tiebreak; chỉ khi đó mới bật mặc định.
2. Thử cách D (LLM cho tài liệu luật mơ hồ) khi GPU rảnh; cache riêng đã sẵn trong `_cache/`.
3. Bẫy 22 của README vẫn còn: nếu bộ tách gộp nhầm BB với PXK thành một lát, văn bản đưa vào cascade là 2 trang đầu của lát, mơ hồ vẫn xảy ra.
