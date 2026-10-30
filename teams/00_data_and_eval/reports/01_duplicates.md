# Báo cáo 01 — Tài liệu trùng lặp và nhóm cùng mẫu trong tập mẫu 336 PDF

> Dành cho sinh viên. Mọi số liệu trong các bảng tự sinh được tính lại từ `data/manifest.csv`, `data/duplicate_groups.csv` và `01_duplicates_stats.json`. Các mục ghi «viết tay» là nhận định của người phân tích sau khi mở từng cặp ảnh trang để xem; hãy kiểm tra lại nếu dữ liệu hoặc ngưỡng thay đổi. Toàn bộ xử lý chạy cục bộ, không gửi dữ liệu ra ngoài.

## 1. Tóm tắt

- Tập mẫu: **336** PDF (334 nằm trong 19 thư mục có nhãn, 2 tệp nằm rời ở gốc, không nhãn).
- **Trùng thật** (cùng một tài liệu được lưu hai lần): **30 nhóm**, gồm **62 tài liệu**; sau khi gộp còn **304 tài liệu duy nhất** (loại bỏ 32 bản thừa).
- Trong 30 nhóm đó, **27 nhóm nằm ở ≥ 2 thư mục khác nhau** (cùng một tệp, hai nhãn → nhãn mâu thuẫn và rò rỉ train/test); 3 nhóm nằm trong cùng một thư mục.
- Bằng chứng của các nhóm trùng (theo tài liệu): bytes+image: 35, bytes+image+text: 27. 30/30 nhóm có **cùng sha256** (byte giống hệt); không tìm thấy cặp nào «cùng ảnh nhưng khác byte» (xem mục 3).
- **Nhóm cùng mẫu** (khác tài liệu nhưng cùng biểu mẫu): **39 nhóm** gồm 161 tài liệu (đã bao gồm các nhóm trùng thật). Dùng cột `template_group` làm `groups` cho `GroupKFold`.
- Số tài liệu nhiều trang: 237; hơn 10 trang: 13. Quét (scan) 304/336, born-digital 32/336.

## 2. Tạo lại toàn bộ kết quả

Chạy từ thư mục gốc của repo (kết quả xác định, chạy lại cho đúng cùng byte đầu ra; mất khoảng 20–30 giây):

```powershell
.venv\Scripts\python.exe -X utf8 scripts\build_manifest.py
.venv\Scripts\python.exe -X utf8 teams\00_data_and_eval\make_duplicates_report.py
.venv\Scripts\python.exe -X utf8 teams\00_data_and_eval\tests\test_manifest.py
```

Tham số của `build_manifest.py`: `--samples-dir`, `--out` (mặc định `data/manifest.csv`), `--groups-out`, `--stats-out`, `--baseline` và các ngưỡng ở mục 3. Đầu ra: `data/manifest.csv`, `data/duplicate_groups.csv`, `reports/01_duplicates_stats.json`. `doc_id = sha1(đường dẫn tương đối, NFC, dấu «/»).hexdigest()[:12]`. Không bao giờ ghi vào thư mục mẫu.

## 3. Cách phát hiện và cách kiểm chứng ngưỡng

### 3.1. Hai hiện tượng, hai quy tắc

**(a) Trùng thật** — cùng một tài liệu được lưu hai lần. Hai tệp là trùng nếu thỏa MỘT trong ba bằng chứng (gộp bằng union-find, nhóm là thành phần liên thông):

1. `bytes`: sha256 giống nhau (kết luận chắc chắn).
2. `image`: cùng số trang; dHash 64-bit của trang đầu **và** trang cuối cách nhau ≤ 4 bit; tỉ lệ điểm ảnh khác nhau (chênh mức xám > 30 trên ảnh 200×283 đã làm mờ nhẹ) ≤ 0,0005 ở cả trang đầu và trang cuối; và nếu cả hai có text thì text phải giống nhau. Ý nghĩa: «cùng một bản quét, chỉ nén lại».
3. `text`: text trang 1 (chuẩn hóa: bỏ dấu, chữ thường, chỉ giữ a–z0–9) **giống hệt** (độ tương đồng ≥ 0,999), dài ≥ 150 ký tự, cùng số trang và pixel ≤ 0,02 ở trang đầu/cuối. Ý nghĩa: «cùng tài liệu quét lại».

Lý do so cả trang đầu và trang cuối: với thẻ chứng nhận 2 trang, trang 1 chỉ là bìa in sẵn giống hệt giữa mọi người, còn với hồ sơ PCCC/hợp đồng nhiều trang thì trang cuối có thể giống hệt giữa các tài liệu khác nhau (đã gặp cả hai trường hợp, mục 3.4).

Vì sao KHÔNG dùng «text tương đồng ≥ 0,95» làm bằng chứng trùng như đề xuất ban đầu: các bản điền khác nhau của cùng một biểu mẫu (đơn đặt hàng, phiếu xuất kho, biên bản giao hàng) thường có tương đồng 0,93–0,99 dù là các tài liệu khác nhau (đã xem ảnh các cặp 0,93 và 0,95 ở mục 3.4: khác ngày, số lượng, tiền). Mức 0,95 chỉ được dùng để tạo cạnh «cùng mẫu».

**(b) Cùng mẫu** — khác tài liệu, cùng biểu mẫu/đầu thư, khác khách hàng hoặc ngày. Đây không phải trùng lặp nên có cột riêng `template_group`. Cạnh «cùng mẫu» khi text trang 1 tương đồng ≥ 0,95, hoặc tương đồng ≥ 0,75 **và** bố cục trang 1 khớp (pixel ≤ 0,03). `template_group` là thành phần liên thông của (cạnh trùng thật + cạnh cùng mẫu).
Giới hạn (đo được, xem mục 7): text lấy từ OCR trang 1 của `baseline_ocr_335.jsonl` (và text layer cho 2 tệp ở gốc), nên nhóm cùng mẫu chỉ là nỗ lực tốt nhất; biểu mẫu quét lệch vị trí hoặc OCR kém sẽ không được nối. Đừng coi «không có template_group» là «chắc chắn không cùng mẫu».

### 3.2. Phân bố khoảng cách dHash (trang 1) trên mọi cặp

Có 56280 cặp; 34 cặp trùng byte. Số cặp khác byte nhưng Hamming ≤ 2: **126**; ≤ 4: **481**.

| Hamming trang 1 | Cặp trùng byte | Cặp khác byte |
|---|---|---|
| 0 | 34 | 5 |
| 1 | 0 | 46 |
| 2 | 0 | 75 |
| 3 | 0 | 155 |
| 4 | 0 | 200 |
| 5 | 0 | 233 |
| 6–7 | 0 | 647 |
| 8–9 | 0 | 993 |
| 10–11 | 0 | 1271 |
| 12–15 | 0 | 4076 |
| ≥16 | 0 | 48545 |

Đọc bảng: các cặp trùng byte luôn có Hamming 0 (đúng như dự kiến), nhưng hàng trăm cặp KHÁC tài liệu cũng có Hamming ≤ 4, vì trang giấy A4 có chữ đen trên nền trắng cùng biểu mẫu thì rất giống nhau ở độ phân giải 9×8. **Kết luận: dHash chỉ là bộ lọc thô, không đủ để kết luận trùng**; ngưỡng chọn là ≤ 4 (đủ rộng cho bản nén lại, đủ chặt để lọc cặp ứng viên) và quyết định thật sự nằm ở phép so điểm ảnh bên dưới.

### 3.3. Phân bố chênh lệch điểm ảnh (cặp ứng viên cùng số trang; lấy trang xấu nhất trong trang đầu/cuối)

| Tỉ lệ điểm ảnh khác | Cặp trùng byte | Cặp khác byte (ứng viên) |
|---|---|---|
| [0; 0,0005) | 34 | 0 |
| [0,0005; 0,001) | 0 | 2 |
| [0,001; 0,002) | 0 | 7 |
| [0,002; 0,004) | 0 | 5 |
| [0,004; 0,008) | 0 | 14 |
| [0,008; 0,016) | 0 | 37 |
| [0,016; 0,03) | 0 | 92 |
| [0,03; 0,06) | 0 | 204 |
| [0,06; 0,12) | 0 | 572 |
| [0,12; 1,0001) | 0 | 1312 |

Đọc bảng: cặp trùng byte có chênh lệch đúng 0; cặp khác byte thấp nhất là 0,0010 (gấp đôi ngưỡng 0,0005) và 10 cặp thấp nhất như dưới đây đều là biểu mẫu điền khác nhau (đã xem ảnh 2 trong số đó và nhiều cặp biên khác, mục 3.4; các cặp còn lại có số đơn/số phiếu khác nhau). Ngưỡng điểm ảnh được đặt ngay trên mức của bản sao giống hệt và dưới mọi cặp khác tài liệu quan sát được. Hệ quả đo được: **trong tập này không tồn tại cặp «cùng ảnh nhưng khác byte»**, nên các quy tắc `image`/`text` chưa từng là bằng chứng duy nhất của nhóm nào; chúng được giữ để chạy trên dữ liệu mới. Chúng chưa được kiểm chứng bằng ví dụ dương nào ngoài các cặp trùng byte.

| Tệp A | Tệp B | Pixel | Hamming p1 | Text |
|---|---|---|---|---|
| `don-hang_2604-0034.pdf` | `don-hang_2605-0004.pdf` | 0.00097 | 0 | 0.927 |
| `don-hang_2606-0019.pdf` | `don-hang_2606-0024.pdf` | 0.00099 | 0 | 0.955 |
| `don-hang_2602-0017.pdf` | `don-hang_2606-0024.pdf` | 0.0011 | 1 | 0.917 |
| `don-hang_2603-0019.pdf` | `don-hang_2604-0017.pdf` | 0.00118 | 2 | 0.919 |
| `don-hang_2602-0017.pdf` | `don-hang_2606-0019.pdf` | 0.00159 | 1 | 0.919 |
| `don-hang_2602-0017.pdf` | `don-hang_2604-0034.pdf` | 0.00186 | 1 | 0.816 |
| `BHDS 13420 (2-1-23).pdf` | `BHDS 173.10 (29-1-23).pdf` | 0.00189 | 3 | 0.911 |
| `don-hang_2604-0034.pdf` | `don-hang_2606-0024.pdf` | 0.00193 | 2 | 0.832 |
| `don-hang_2605-0004.pdf` | `don-hang_2606-0019.pdf` | 0.00196 | 2 | 0.84 |
| `don-hang_2604-0016.pdf` | `don-hang_2605-0015.pdf` | 0.00208 | 1 | 0.809 |

### 3.4. Các cặp biên đã xem bằng mắt (viết tay)

Mỗi cặp được kết xuất thành PNG (thư mục scratch, ngoài repo), ghép cạnh nhau và mở xem. Ảnh thẻ, họ tên, số giấy tờ cá nhân xuất hiện trong ảnh nhưng KHÔNG được ghi lại trong báo cáo.

| Cặp | Số đo | Nhìn thấy | Kết luận |
|---|---|---|---|
| don-hang_2604-0034 ↔ don-hang_2605-0004 | Hamming 0, pixel 0,0010, text 0,93 | Cùng mẫu «Đơn đặt hàng»; khác ngày, số lượng, thành tiền, bên nhận. | Mẫu chung, KHÔNG trùng |
| don-hang_2606-0019 ↔ don-hang_2606-0024 | Hamming 0, pixel 0,0010, text 0,95 | Cùng mẫu; khác số PO, ngày, loại dầu và thành tiền. Text 0,95 vẫn là hai tài liệu khác nhau. | Mẫu chung, KHÔNG trùng (lý do không dùng text ≥ 0,95 làm bằng chứng trùng) |
| bbgn-260206-10 ↔ bbgn-260220-1 | Hamming 5, pixel 0,0054, text 0,93 | Cùng mẫu «Biên bản giao hàng», chữ viết tay khác nhau (khách hàng, số lượng, chữ ký). | Mẫu chung, KHÔNG trùng |
| BHDS 13420 ↔ BHDS 173.10 (hồ sơ xe) | Hamming 3/1, pixel 0,0019, text 0,91 | Cùng mẫu giấy chứng nhận bảo hiểm TNDS; số giấy chứng nhận khác nhau chỉ ở chữ số cuối. | Mẫu chung, KHÔNG trùng |
| PCCC CH12-22 ↔ PCCC G1-22 (50 trang) | Hamming 16/11, trang cuối pixel 0,0000, trang 1 pixel 0,0045 | Cùng mẫu «Hồ sơ quản lý công tác PCCC», tên cơ sở khác nhau (một cửa hàng, một phương tiện thủy). | Mẫu chung, KHÔNG trùng. Trang cuối giống hệt nên bắt buộc phải so cả trang đầu lẫn trang cuối |
| NQ-18.2021-DUC TRONG ↔ THÀNH LIÊN (31-12-2026) | Hamming 2/16, trang cuối pixel 0,0000, trang 1 pixel 0,029 | Cùng mẫu bìa «Hợp đồng nhượng quyền bán lẻ xăng dầu», khác bên nhận nhượng quyền, số hợp đồng và ngày ký. | Mẫu chung, KHÔNG trùng. Cũng chứng minh phải so cả trang đầu và cuối |
| HDMBCD-02.2020-TRUONG HUNG (thư mục MUON BON) ↔ HDMBCD-04.2020-PHUC VINH (thư mục THUE KHO) | Hamming 1/1, pixel 0,011, text 0,89 | Cùng mẫu «Hợp đồng mượn bồn chứa dầu», khác bên B (tên công ty, mã số thuế, người đại diện). | Mẫu chung, KHÔNG trùng; nhưng đây là bằng chứng hai thư mục cùng một loại tài liệu |
| 65. GCN VC HNH Nhieu ↔ 72. GCN VC HNH Nhan (trang 2) | Hamming trang cuối thấp, pixel 0,0099 | Cùng mẫu thẻ chứng nhận tập huấn; ảnh chân dung, họ tên, ngày sinh, số giấy chứng nhận khác nhau. | Mẫu chung, KHÔNG trùng |
| 10. GCN VC HNH/38 (Nguyen) ↔ 9. TỔNG HỢP HỒ SƠ CỬA HÀNG/38 (Tấn) (trang 2) | pixel 0,065 | Hai người khác nhau trên cùng mẫu thẻ (dù tên tệp cùng số 38). | KHÔNG trùng |
| 15. GCN VC HNH Dong (12-5-24) ↔ 62. GCN VC HNH Huy (trang 1) | Hamming trang 1 = 4; text giống hệt (98 ký tự) | Trang 1 chỉ là bìa trống in sẵn (tên công ty + tiêu đề), giống nhau giữa mọi người. | Khác tài liệu nhưng trang 1 không phân biệt được. Bằng chứng text/ảnh của trang 1 vô giá trị với nhóm này; phải so trang cuối |
| 58. GCN VC HNH Tuan ↔ 59. GCN VC HNH Thong (trang 2) | pixel trang cuối > 0,01 | Trang 2 là thẻ có ảnh chân dung, họ tên, số giấy chứng nhận; hai người khác nhau, cùng mẫu thẻ. | KHÔNG trùng |
| GPKD-AN PHAT LAND (thư mục HOP DONG DAI LY) ↔ GPKD-AN PHÁT LAND (thư mục Giay DKKD) | Hamming 0, pixel 0,0000, cùng sha256 | Đối chứng dương: cùng một giấy phép kinh doanh, nội dung từng chữ giống nhau. | TRÙNG THẬT (bytes) |

Tổng cộng đã xem 12 cặp (11 cặp biên + 1 đối chứng dương). Cặp nào cũng cho cùng một bài học: **hai tài liệu khác nhau trên cùng một biểu mẫu trông gần như giống hệt ở mức trang**; chỉ các chi tiết nhỏ (ngày, số, tên, ảnh chân dung) mới khác. Vì vậy ngưỡng Hamming/độ tương đồng nới lỏng sẽ gộp nhầm tài liệu khác nhau, và sẽ làm mất mẫu hợp lệ.

## 4. Số tài liệu trước/sau khi loại trùng, theo thư mục

Trước: 336. Sau khi gộp các nhóm trùng thật: **304** tài liệu duy nhất. Cột «sau» đếm tài liệu duy nhất có mặt trong thư mục (bản trùng trong cùng thư mục chỉ tính một). «Dùng chung» là số tài liệu duy nhất của thư mục cũng có bản ở thư mục khác (một tài liệu dùng chung được đếm ở mỗi thư mục có bản, nên tổng cột «sau» lớn hơn số duy nhất toàn cục).

| Thư mục | Trước | Sau | Dùng chung với thư mục khác | Chỉ riêng thư mục |
|---|---|---|---|---|
| 10. GCN VC HNH | 20 | 19 | 15 | 4 |
| 5. TỔNG HỢP HỒ SƠ XE | 20 | 20 | 0 | 20 |
| 6. CUA HANG - BB MAU- VÂN | 10 | 10 | 0 | 10 |
| 6. HOP DONG MUON BON | 7 | 7 | 2 | 5 |
| 6. HOP DONG THUE KHO- Vi | 6 | 6 | 2 | 4 |
| 8. CUA HANG - TU K.TRA PCCC- VÂN | 5 | 5 | 2 | 3 |
| 8. GCN Lop dao tao van chuyen hang chay no | 20 | 20 | 16 | 4 |
| 9. TỔNG HỢP HỒ SƠ CỬA HÀNG | 25 | 25 | 2 | 23 |
| TU K.TRA PCCC- VÂN | 5 | 5 | 2 | 3 |
| _1. Giay DKKD khach hang | 23 | 23 | 4 | 19 |
| _1. HOP DONG DAI LY NHUONG QUYEN | 25 | 25 | 7 | 18 |
| _2. Giay Du Dieu Kien Khach hang | 25 | 22 | 3 | 19 |
| _2. HOP DONG KINH TE | 25 | 25 | 0 | 25 |
| _3. HOP DONG DAU VAO-Diem | 20 | 20 | 0 | 20 |
| _4. THANH LÝ HỢP ĐỒNG | 14 | 14 | 0 | 14 |
| _5. HOP DONG VAN CHUYEN | 24 | 24 | 0 | 24 |
| _Biên bản giao nhận 2026 | 20 | 20 | 0 | 20 |
| _PHIẾU XUẤT KHO MUA HÀNG 2026 | 20 | 20 | 0 | 20 |
| _Đơn đặt hàng - mua vào 2026 | 20 | 20 | 0 | 20 |
| (gốc, không nhãn) | 2 | 2 | 0 | 2 |
| **Tổng** | 336 | — | — | — |

## 5. Cặp thư mục chia sẻ tài liệu

27 nhóm trùng thật nằm ở ≥ 2 thư mục. Mỗi nhóm được đếm một lần cho mỗi cặp thư mục mà nó bắc cầu.

| Thư mục A | Thư mục B | Số nhóm dùng chung | Nhóm |
|---|---|---|---|
| `10. GCN VC HNH` | `8. GCN Lop dao tao van chuyen hang chay no` | 15 | D002, D003, D004, D005, D006, D007, D008, D009, D010, D011, D012, D013, D014, D015, D016 |
| `_1. Giay DKKD khach hang` | `_1. HOP DONG DAI LY NHUONG QUYEN` | 4 | D022, D023, D024, D025 |
| `_1. HOP DONG DAI LY NHUONG QUYEN` | `_2. Giay Du Dieu Kien Khach hang` | 3 | D026, D027, D028 |
| `6. HOP DONG MUON BON` | `6. HOP DONG THUE KHO- Vi` | 2 | D017, D018 |
| `8. CUA HANG - TU K.TRA PCCC- VÂN` | `TU K.TRA PCCC- VÂN` | 2 | D019, D020 |
| `8. GCN Lop dao tao van chuyen hang chay no` | `9. TỔNG HỢP HỒ SƠ CỬA HÀNG` | 2 | D003, D021 |
| `10. GCN VC HNH` | `9. TỔNG HỢP HỒ SƠ CỬA HÀNG` | 1 | D003 |

### Danh sách nhóm trùng khác nhãn (tên tệp)

| Nhóm | Số bản | Tệp (thư mục/tên) |
|---|---|---|
| D002 | 2 | `10. GCN VC HNH/35. GCN VCHNH Bac (BC-12-5-24).pdf`<br>`8. GCN Lop dao tao van chuyen hang chay no/35. GCN VCHNH Bắc (BC-12-5-24).pdf` |
| D003 | 3 | `10. GCN VC HNH/37. GCN VC HNH Chinh (BC-12-5-24).pdf`<br>`8. GCN Lop dao tao van chuyen hang chay no/37. GCN VC HNH Chính (BC-12-5-24).pdf`<br>`9. TỔNG HỢP HỒ SƠ CỬA HÀNG/12. VCHNH Chính (12-5-24).pdf` |
| D004 | 2 | `10. GCN VC HNH/38. GCN VC HNH Nguyen (BC-12-5-24).pdf`<br>`8. GCN Lop dao tao van chuyen hang chay no/38. GCN VC HNH Nguyên (BC-12-5-24).pdf` |
| D005 | 2 | `10. GCN VC HNH/58. GCN VC HNH Tuan (12-5-24).pdf`<br>`8. GCN Lop dao tao van chuyen hang chay no/58. GCN VC HNH-Tuấn.pdf` |
| D006 | 2 | `10. GCN VC HNH/59. GCN VC HNH Thong (12-5-24).pdf`<br>`8. GCN Lop dao tao van chuyen hang chay no/59. GCN VC HNH-Thông.pdf` |
| D007 | 2 | `10. GCN VC HNH/60. GCN VC HNH Hung (12-5-24).pdf`<br>`8. GCN Lop dao tao van chuyen hang chay no/60. GCN vc hàng nguy hiểm- Hùng.pdf` |
| D008 | 2 | `10. GCN VC HNH/61. GCN VC HNH Hong (12-5-24).pdf`<br>`8. GCN Lop dao tao van chuyen hang chay no/61. GCN vc hàng nguy hiểm-Hồng.pdf` |
| D009 | 2 | `10. GCN VC HNH/63. GCN VC HNH Trung ĐK (12-5-24).pdf`<br>`8. GCN Lop dao tao van chuyen hang chay no/63. GCN vc hàng nguy hiểm-Trung ĐK.pdf` |
| D010 | 2 | `10. GCN VC HNH/64. GCN VC HNH Binh (12-5-24).pdf`<br>`8. GCN Lop dao tao van chuyen hang chay no/64. GCN vc hàng nguy hiểm-Bình.pdf` |
| D011 | 2 | `10. GCN VC HNH/65. GCN VC HNH Nhieu (12-5-24).pdf`<br>`8. GCN Lop dao tao van chuyen hang chay no/65. GCN vc hàng nguy hiểm-Nhiễu.pdf` |
| D012 | 2 | `10. GCN VC HNH/67. GCN VC HNH Hao (12-5-24).pdf`<br>`8. GCN Lop dao tao van chuyen hang chay no/67. GCN VC HNH-Hào.pdf` |
| D013 | 2 | `10. GCN VC HNH/69. GCN VCHNH Trung (12-5-24).pdf`<br>`8. GCN Lop dao tao van chuyen hang chay no/69. GCN VCHNH- Trung.pdf` |
| D014 | 2 | `10. GCN VC HNH/72. GCN VC HNH Nhan (12-5-24).pdf`<br>`8. GCN Lop dao tao van chuyen hang chay no/72. GCN VC HNH-Nhàn.pdf` |
| D015 | 2 | `10. GCN VC HNH/75. GCN VC HNH Dat (12-5-24).pdf`<br>`8. GCN Lop dao tao van chuyen hang chay no/75. GCN vc hàng nguy hiểm-Đạt.pdf` |
| D016 | 2 | `10. GCN VC HNH/77. GCN VC HNH Nam (12-5-24).pdf`<br>`8. GCN Lop dao tao van chuyen hang chay no/77. GCN vc hàng nguy hiểm-Nam.pdf` |
| D017 | 2 | `6. HOP DONG MUON BON/HDMBCD-05.2016-TAM PHUC PHU-01-09-2016.pdf`<br>`6. HOP DONG THUE KHO- Vi/HDMBCD-05.2016-TAM PHUC PHU-01-09-2016.pdf` |
| D018 | 2 | `6. HOP DONG MUON BON/HDMBCD-05.2020-ANH DUNG-01.02.2020.pdf`<br>`6. HOP DONG THUE KHO- Vi/HDMBCD-05.2020-ANH DUNG-01.02.2020.pdf` |
| D019 | 2 | `8. CUA HANG - TU K.TRA PCCC- VÂN/GHE 3-T1+T2.pdf`<br>`TU K.TRA PCCC- VÂN/GHE 3-T1+T2.pdf` |
| D020 | 2 | `8. CUA HANG - TU K.TRA PCCC- VÂN/PCCC G1-22.pdf`<br>`TU K.TRA PCCC- VÂN/PCCC G1-22.pdf` |
| D021 | 2 | `8. GCN Lop dao tao van chuyen hang chay no/39. GCN VC HNH Tấn (BC-12-5-24).pdf`<br>`9. TỔNG HỢP HỒ SƠ CỬA HÀNG/38. VC HNH Tấn (BC-12-5-24)_2.pdf` |
| D022 | 2 | `_1. Giay DKKD khach hang/GPKD-AN PHÁT LAND.pdf`<br>`_1. HOP DONG DAI LY NHUONG QUYEN/GPKD-AN PHAT LAND.pdf` |
| D023 | 2 | `_1. Giay DKKD khach hang/GPKD-BẢO ÂN PHÁT.pdf`<br>`_1. HOP DONG DAI LY NHUONG QUYEN/GPKD-BẢO ÂN PHÁT.pdf` |
| D024 | 2 | `_1. Giay DKKD khach hang/GPKD-LÊ VĂN CƯỜNG.pdf`<br>`_1. HOP DONG DAI LY NHUONG QUYEN/GPKD-LÊ VĂN CƯỜNG.pdf` |
| D025 | 2 | `_1. Giay DKKD khach hang/GPKD-PHƯƠNG BẰNG.pdf`<br>`_1. HOP DONG DAI LY NHUONG QUYEN/GPKD-PHƯƠNG BẰNG.pdf` |
| D026 | 2 | `_1. HOP DONG DAI LY NHUONG QUYEN/DDK-DUC TRONG-12.3.24.pdf`<br>`_2. Giay Du Dieu Kien Khach hang/DDK-ĐỨC TRỌNG.pdf` |
| D027 | 2 | `_1. HOP DONG DAI LY NHUONG QUYEN/DDK-HONG CAT 2-28.3.24.pdf`<br>`_2. Giay Du Dieu Kien Khach hang/DDK-HỒNG CÁT 3.pdf` |
| D028 | 2 | `_1. HOP DONG DAI LY NHUONG QUYEN/DDK-HONG QUE-20.5.26.pdf`<br>`_2. Giay Du Dieu Kien Khach hang/DDK-HONG QUE-20.5.26.pdf` |

### Danh sách nhóm trùng trong cùng một thư mục

| Nhóm | Số bản | Tệp (thư mục/tên) |
|---|---|---|
| D001 | 2 | `10. GCN VC HNH/15. GCN VC HNH Dong (12-5-24).pdf`<br>`10. GCN VC HNH/15. GCN VC HNH Dong (BC-12-5-24).pdf` |
| D029 | 3 | `_2. Giay Du Dieu Kien Khach hang/DDK-DUY NGUYEN-27.7.26.pdf`<br>`_2. Giay Du Dieu Kien Khach hang/DDK-DUY NGUYEN-27.7.26_1.pdf`<br>`_2. Giay Du Dieu Kien Khach hang/DDK-DUY NGUYÊN.pdf` |
| D030 | 2 | `_2. Giay Du Dieu Kien Khach hang/DDK-HUONG SON-10.5.26.pdf`<br>`_2. Giay Du Dieu Kien Khach hang/DDK-HƯƠNG SƠN.pdf` |

## 6. Hệ quả cho bộ nhãn (viết tay, dựa trên số liệu và ảnh đã xem)

### 6.1. Các thư mục có vẻ là CÙNG MỘT loại tài liệu (nhãn bị tách đôi)

| Cặp thư mục | Dấu hiệu đo được | Nhận định (suy luận) |
|---|---|---|
| `10. GCN VC HNH` và `8. GCN Lop dao tao van chuyen hang chay no` | 15 nhóm trùng byte giữa hai thư mục; cả hai đều là thẻ chứng nhận tập huấn vận chuyển hàng hóa nguy hiểm (cùng ngày cấp 12-05-2022) | Là một loại tài liệu; nên gộp thành một lớp (hoặc coi là bí danh của nhau). Nếu giữ hai lớp, cùng một tệp mang hai nhãn nên chắc chắn có một nhãn bị tính sai |
| `8. CUA HANG - TU K.TRA PCCC- VÂN` và `TU K.TRA PCCC- VÂN` | 2 nhóm trùng byte (GHE 3-T1+T2, PCCC G1-22); cùng mẫu «Hồ sơ quản lý công tác PCCC» | Một loại tài liệu; nên gộp |
| `6. HOP DONG MUON BON` và `6. HOP DONG THUE KHO- Vi` | 2 nhóm trùng byte (HDMBCD-05.2016, HDMBCD-05.2020); các tệp HDMBCD-* ở cả hai thư mục cùng mẫu «Hợp đồng mượn bồn chứa dầu» | Tên thư mục «thuê kho» nhưng nội dung là hợp đồng mượn bồn. Nên gộp, hoặc hỏi khách hàng ranh giới giữa «mượn bồn» và «thuê kho» |

### 6.2. Các thư mục là «gói hồ sơ» (bundle) gồm nhiều loại tài liệu

Dựa trên tên tệp (suy luận từ tên, chưa đọc nội dung từng tệp):

- `5. TỔNG HỢP HỒ SƠ XE`: bảo hiểm xe (BHVC/BHDS), PCCC xe, barem, giấy tờ người lái... trộn trong một thư mục.
- `9. TỔNG HỢP HỒ SƠ CỬA HÀNG`: GCN đăng ký doanh nghiệp, GCN vận chuyển hàng nguy hiểm (trùng với hai thư mục GCN ở trên),
  bằng/GCN BVMT, PCCC, giấy phép xây dựng, bảo hiểm, ảnh CamScanner...
- `_1. HOP DONG DAI LY NHUONG QUYEN`: chỉ ~5/25 tệp là hợp đồng nhượng quyền (NQ-*, 10 trang); phần lớn là giấy phép kinh doanh
  (GPKD-*, GĐKKD-*) và giấy đủ điều kiện (DDK-*), tức đúng loại tài liệu của `_1. Giay DKKD khach hang` và `_2. Giay Du Dieu Kien Khach hang`.
- `_3. HOP DONG DAU VAO-Diem`: hợp đồng, giấy ủy quyền, giấy phép kinh doanh, thanh lý... trộn.
- `6. CUA HANG - BB MAU- VÂN`: tệp dài (đến 93 trang), có thể gồm nhiều biên bản; cần tách trang trước khi phân loại.

Hệ quả: (1) nhãn «thư mục» ≠ nhãn «loại tài liệu» ở các bundle; (2) bài toán tách tài liệu (Team 2) phải chạy trước phân loại;
(3) các lớp bundle nên được định nghĩa lại hoặc loại khỏi tập đánh giá cho đến khi có nhãn ở mức trang/tài liệu con.

### 6.3. Hai hiện tượng phải xử lý khác nhau

- **Trùng thật** (cùng một tài liệu nộp hai lần, ở đây luôn là cùng byte): phải gộp thành MỘT mẫu và luôn nằm cùng một fold.
  Nếu hai bản mang hai nhãn khác nhau thì nhãn đang mâu thuẫn: chọn một nhãn (hoặc gộp lớp) rồi mới đánh giá.
- **Cùng mẫu** (khác khách hàng/ngày): vẫn là các mẫu riêng, nhưng phải cùng fold khi chia cross-validation
  (`GroupKFold(groups=template_group)`), nếu không điểm số sẽ lạc quan vì mô hình chỉ cần nhớ mẫu.
  Chú ý: với bài toán phân loại, hai bản trong cùng mẫu thường cùng lớp nên điểm trong-fold cao không chứng minh được khả năng tổng quát hóa;
  hãy báo cáo thêm điểm theo `GroupKFold`.

## 7. Nhóm cùng mẫu (`template_group`)

39 nhóm, 161/336 tài liệu. Nhóm lớn nhất:

| Nhóm | Số tài liệu | Số thư mục | Thư mục |
|---|---|---|---|
| T001 | 41 | 3 | 10. GCN VC HNH; 8. GCN Lop dao tao van chuyen hang chay no; 9. TỔNG HỢP HỒ SƠ CỬA HÀNG |
| T032 | 15 | 1 | _PHIẾU XUẤT KHO MUA HÀNG 2026 |
| T037 | 7 | 1 | _Đơn đặt hàng - mua vào 2026 |
| T006 | 6 | 1 | 6. CUA HANG - BB MAU- VÂN |
| T010 | 6 | 2 | 8. CUA HANG - TU K.TRA PCCC- VÂN; TU K.TRA PCCC- VÂN |
| T029 | 6 | 1 | _Biên bản giao nhận 2026 |

Nhóm `T001` gồm các thẻ chứng nhận tập huấn: trang 1 chỉ là bìa in sẵn nên text giống hệt nhau giữa mọi người, và kéo ba thư mục vào cùng một nhóm. Tỉ lệ tài liệu có `template_group` theo thư mục (thấp = có thể do OCR/bố cục, không có nghĩa là không cùng mẫu):

| Thư mục | Số tài liệu | Có template_group | Tỉ lệ |
|---|---|---|---|
| 10. GCN VC HNH | 20 | 20 | 100% |
| 5. TỔNG HỢP HỒ SƠ XE | 20 | 8 | 40% |
| 6. CUA HANG - BB MAU- VÂN | 10 | 8 | 80% |
| 6. HOP DONG MUON BON | 7 | 5 | 71% |
| 6. HOP DONG THUE KHO- Vi | 6 | 3 | 50% |
| 8. CUA HANG - TU K.TRA PCCC- VÂN | 5 | 4 | 80% |
| 8. GCN Lop dao tao van chuyen hang chay no | 20 | 19 | 95% |
| 9. TỔNG HỢP HỒ SƠ CỬA HÀNG | 25 | 6 | 24% |
| TU K.TRA PCCC- VÂN | 5 | 2 | 40% |
| _1. Giay DKKD khach hang | 23 | 4 | 17% |
| _1. HOP DONG DAI LY NHUONG QUYEN | 25 | 10 | 40% |
| _2. Giay Du Dieu Kien Khach hang | 25 | 8 | 32% |
| _2. HOP DONG KINH TE | 25 | 7 | 28% |
| _3. HOP DONG DAU VAO-Diem | 20 | 0 | 0% |
| _4. THANH LÝ HỢP ĐỒNG | 14 | 0 | 0% |
| _5. HOP DONG VAN CHUYEN | 24 | 6 | 25% |
| _Biên bản giao nhận 2026 | 20 | 12 | 60% |
| _PHIẾU XUẤT KHO MUA HÀNG 2026 | 20 | 19 | 95% |
| _Đơn đặt hàng - mua vào 2026 | 20 | 20 | 100% |
| (gốc, không nhãn) | 2 | 0 | 0% |

## 8. Số trang theo thư mục

Tài liệu > 1 trang: **237/336**; > 10 trang: **13/336** (tính trên 336 PDF trước khi loại trùng).

| Thư mục | Số tài liệu | 1 | 2 | 3–5 | 6–10 | 11–30 | >30 | Trung vị | Tối đa |
|---|---|---|---|---|---|---|---|---|---|
| 10. GCN VC HNH | 20 | 0 | 20 | 0 | 0 | 0 | 0 | 2 | 2 |
| 5. TỔNG HỢP HỒ SƠ XE | 20 | 1 | 19 | 0 | 0 | 0 | 0 | 2 | 2 |
| 6. CUA HANG - BB MAU- VÂN | 10 | 3 | 2 | 1 | 3 | 0 | 1 | 2,5 | 93 |
| 6. HOP DONG MUON BON | 7 | 0 | 2 | 2 | 3 | 0 | 0 | 4 | 6 |
| 6. HOP DONG THUE KHO- Vi | 6 | 0 | 1 | 1 | 4 | 0 | 0 | 6 | 10 |
| 8. CUA HANG - TU K.TRA PCCC- VÂN | 5 | 0 | 0 | 0 | 0 | 3 | 2 | 26 | 50 |
| 8. GCN Lop dao tao van chuyen hang chay no | 20 | 0 | 20 | 0 | 0 | 0 | 0 | 2 | 2 |
| 9. TỔNG HỢP HỒ SƠ CỬA HÀNG | 25 | 6 | 14 | 3 | 1 | 1 | 0 | 2 | 21 |
| TU K.TRA PCCC- VÂN | 5 | 0 | 0 | 0 | 0 | 2 | 3 | 46 | 53 |
| _1. Giay DKKD khach hang | 23 | 6 | 14 | 2 | 1 | 0 | 0 | 2 | 7 |
| _1. HOP DONG DAI LY NHUONG QUYEN | 25 | 6 | 14 | 0 | 5 | 0 | 0 | 2 | 10 |
| _2. Giay Du Dieu Kien Khach hang | 25 | 10 | 10 | 5 | 0 | 0 | 0 | 2 | 3 |
| _2. HOP DONG KINH TE | 25 | 0 | 20 | 5 | 0 | 0 | 0 | 2 | 4 |
| _3. HOP DONG DAU VAO-Diem | 20 | 4 | 11 | 1 | 3 | 1 | 0 | 2 | 30 |
| _4. THANH LÝ HỢP ĐỒNG | 14 | 11 | 2 | 1 | 0 | 0 | 0 | 1 | 5 |
| _5. HOP DONG VAN CHUYEN | 24 | 0 | 20 | 3 | 1 | 0 | 0 | 2 | 6 |
| _Biên bản giao nhận 2026 | 20 | 19 | 1 | 0 | 0 | 0 | 0 | 1 | 2 |
| _PHIẾU XUẤT KHO MUA HÀNG 2026 | 20 | 13 | 2 | 5 | 0 | 0 | 0 | 1 | 4 |
| _Đơn đặt hàng - mua vào 2026 | 20 | 20 | 0 | 0 | 0 | 0 | 0 | 1 | 1 |
| (gốc, không nhãn) | 2 | 0 | 0 | 1 | 1 | 0 | 0 | 7 | 9 |
| **Tổng** | 336 | 99 | 172 | 30 | 22 | 7 | 6 | 2 | 93 |

Các tệp > 10 trang (ứng viên cần tách trang): `6. CUA HANG - BB MAU- VÂN/BB mau CH12-21.pdf` (93), `TU K.TRA PCCC- VÂN/PCCC CH5-22.pdf` (53), `8. CUA HANG - TU K.TRA PCCC- VÂN/PCCC CH12-22.pdf` (50), `8. CUA HANG - TU K.TRA PCCC- VÂN/PCCC G1-22.pdf` (50), `TU K.TRA PCCC- VÂN/PCCC G1-22.pdf` (50), `TU K.TRA PCCC- VÂN/PCCC CH17-22.pdf` (46), `_3. HOP DONG DAU VAO-Diem/L26091037793.VK3_L26091037793.VK3.VKC01_Thỏa thuận chung (đã ký số).pdf` (30), `8. CUA HANG - TU K.TRA PCCC- VÂN/CH12-T1+T2.pdf` (26), `8. CUA HANG - TU K.TRA PCCC- VÂN/CH5-T1+T2.pdf` (26), `8. CUA HANG - TU K.TRA PCCC- VÂN/GHE 3-T1+T2.pdf` (26), `TU K.TRA PCCC- VÂN/CH9-T1+T2.pdf` (26), `TU K.TRA PCCC- VÂN/GHE 3-T1+T2.pdf` (26), `9. TỔNG HỢP HỒ SƠ CỬA HÀNG/16. UPSC hóa chất (photo).pdf` (21)

## 9. Quét (scan) hay born-digital

Định nghĩa `is_scanned` (heuristic): ít hơn một nửa số trang có text layer (≥ 50 ký tự PyMuPDF) VÀ ít nhất một trang chứa ảnh raster. Còn lại là born-digital. Nơi có nhiều bản quét là nơi chất lượng OCR quyết định kết quả.

| Thư mục | Số tài liệu | Quét | Born-digital | % quét |
|---|---|---|---|---|
| 10. GCN VC HNH | 20 | 20 | 0 | 100% |
| 5. TỔNG HỢP HỒ SƠ XE | 20 | 20 | 0 | 100% |
| 6. CUA HANG - BB MAU- VÂN | 10 | 10 | 0 | 100% |
| 6. HOP DONG MUON BON | 7 | 7 | 0 | 100% |
| 6. HOP DONG THUE KHO- Vi | 6 | 6 | 0 | 100% |
| 8. CUA HANG - TU K.TRA PCCC- VÂN | 5 | 5 | 0 | 100% |
| 8. GCN Lop dao tao van chuyen hang chay no | 20 | 20 | 0 | 100% |
| 9. TỔNG HỢP HỒ SƠ CỬA HÀNG | 25 | 25 | 0 | 100% |
| TU K.TRA PCCC- VÂN | 5 | 5 | 0 | 100% |
| _1. Giay DKKD khach hang | 23 | 23 | 0 | 100% |
| _1. HOP DONG DAI LY NHUONG QUYEN | 25 | 25 | 0 | 100% |
| _2. Giay Du Dieu Kien Khach hang | 25 | 25 | 0 | 100% |
| _2. HOP DONG KINH TE | 25 | 25 | 0 | 100% |
| _3. HOP DONG DAU VAO-Diem | 20 | 17 | 3 | 85% |
| _4. THANH LÝ HỢP ĐỒNG | 14 | 14 | 0 | 100% |
| _5. HOP DONG VAN CHUYEN | 24 | 24 | 0 | 100% |
| _Biên bản giao nhận 2026 | 20 | 20 | 0 | 100% |
| _PHIẾU XUẤT KHO MUA HÀNG 2026 | 20 | 5 | 15 | 25% |
| _Đơn đặt hàng - mua vào 2026 | 20 | 6 | 14 | 30% |
| (gốc, không nhãn) | 2 | 2 | 0 | 100% |
| **Tổng** | 336 | 304 | 32 | 90% |

Phần mềm tạo PDF (`producer`) phổ biến nhất:

| Producer | Tổng | Quét | Born-digital |
|---|---|---|---|
| SECnvtToPDF V1.0 | 253 | 253 | 0 |
| (trống) | 23 | 21 | 2 |
| iTextSharp™ 5.6.140-LoganSoft; modified using eSignature™ 1.0.1.1 | 15 | 0 | 15 |
| Skia/PDF m145; pyHanko 0.35.2 | 14 | 0 | 14 |
| intsig.com pdf producer | 8 | 8 | 0 |
| Haru Free PDF Library 2.3.0RC2 | 6 | 6 | 0 |
| pypdf | 6 | 6 | 0 |
| HP Scan Extended Application | 5 | 5 | 0 |

Dấu hiệu CamScanner/ảnh chụp điện thoại có thể tìm bằng `producer` chứa `intsig` (CamScanner) và trường `created`.

