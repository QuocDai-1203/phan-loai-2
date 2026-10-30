# Báo cáo 02 — Thiết kế bộ nhãn loại tài liệu (taxonomy v2) và hướng dẫn gán nhãn

> **Ghi chú thêm ngày 2026-10-11, sau khi có bộ nhãn hai lượt gán:** các số đếm «ước tính» trong báo cáo này (số tệp theo loại, số tệp composite, cột `est_count` của taxonomy) đã được thay bằng số chính thức tính từ `data/labels_v2.csv`, liệt kê ở `data/classified_v2/README.md`. Khi hai nơi khác nhau, dùng số chính thức. Báo cáo này được giữ nguyên, không viết lại.
>
> Dành cho sinh viên các nhóm 1–4 và người phụ trách dữ liệu. Sản phẩm đi kèm: `data/taxonomy_v2.json` (danh mục, máy đọc được) và
> `docs/LABELING_GUIDELINE.md` (hướng dẫn cho người gán nhãn). Số liệu đếm trong báo cáo lấy từ `data/manifest.csv` và từ **bản gán nhãn tạm của người thiết kế**
> (một người, dựa trên OCR trang 1 và ảnh trang đã mở xem) — **chưa phải gold**; mọi con số «ước tính» sẽ được thay khi có bộ nhãn hai người gán độc lập.
> Toàn bộ xử lý chạy cục bộ; ảnh trang chỉ được kết xuất ra thư mục tạm ngoài repo. Báo cáo không chép số giấy tờ cá nhân, số điện thoại, số tài khoản.

## 1. Tóm tắt

- Nhãn cũ là **tên 19 thư mục** — đó là tủ hồ sơ của công ty, không phải loại tài liệu. Taxonomy v2 thay bằng **34 loại tài liệu theo nội dung** trong **8 nhóm**, cộng hai nhãn đặc biệt `OTHER` và `UNREADABLE`.
- Trong 304 tệp duy nhất: **10 loại đủ dữ liệu** (≥ 10 tệp; 222 tệp không phải composite khác loại) và **24 loại thiếu dữ liệu** (1–9 tệp; tổng 74 tệp, kể cả 1 tệp `OTHER`). Các loại thiếu vẫn được định nghĩa vì nghiệp vụ cần (đa số có ngày hết hạn phải theo dõi), và được đánh dấu `insufficient`.
- Cả 27 nhóm tệp trùng byte đang mang hai nhãn thư mục khác nhau đều nhận **một nhãn duy nhất** dưới v2 — mâu thuẫn nhãn biến mất mà không cần quy ước tùy tiện.
- **21 tệp composite** (chứa ≥ 2 tài liệu logic): 8 tệp khác loại (gold set cho bài toán tách tài liệu, loại khỏi benchmark một nhãn) và 13 tệp cùng loại (vẫn dùng cho phân loại; cần tách khi trích xuất).
- Nơi lưu trữ được mô tả bằng **25 quy tắc định tuyến** (`doc_type` + thực thể trích xuất → thư mục cũ), không còn là lớp.
- Pilot: người thiết kế tự gán 60 tệp thuộc cả 19 thư mục và 2 tệp ở gốc theo đúng hướng dẫn; tìm ra 7 chỗ mơ hồ, đã sửa (mục 8).
- Còn 17 câu hỏi cần chủ nghiệp vụ của công ty trả lời (mục 9).

## 2. Vì sao thư mục không phải là loại tài liệu — bằng chứng

**(a) Cùng một tệp, hai thư mục.** Báo cáo 01 tìm thấy 30 nhóm trùng byte, 27 nhóm nằm ở ≥ 2 thư mục. Với nhãn = thư mục, 27 tài liệu này có hai «đáp án đúng» mâu thuẫn nhau;
mô hình nào cũng bị tính sai ít nhất một lần cho mỗi nhóm. Với v2, cả 27 nhóm có đúng một `doc_type` (đã kiểm bằng máy trên bản gán nhãn tạm).

**(b) Hai cặp thư mục là bí danh của nhau.** «10. GCN VC HNH» và «8. GCN Lop dao tao van chuyen hang chay no» (15 nhóm trùng byte) đều chỉ chứa thẻ
«Giấy chứng nhận hoàn thành chương trình tập huấn vận chuyển hàng hóa nguy hiểm». «8. CUA HANG - TU K.TRA PCCC- VÂN» và «TU K.TRA PCCC- VÂN» (2 nhóm trùng byte)
đều chỉ chứa tập «Hồ sơ quản lý công tác phòng cháy chữa cháy». Không có đặc điểm nội dung nào phân biệt hai thư mục trong mỗi cặp.

**(c) Thư mục là «gói hồ sơ» theo đối tượng quản lý.** Đã mở xem ảnh trang của 55/65 tệp thuộc ba thư mục đầu dưới đây; các tệp còn lại xác định theo OCR trang 1:

- «5. TỔNG HỢP HỒ SƠ XE» (20 tệp) chứa **8 loại**: bảo hiểm xe, giấy phép lái xe, đăng ký xe, giấy biên nhận thế chấp của ngân hàng, giấy phép vận chuyển hàng nguy hiểm, căn cước, kiểm định xi téc, giấy phép kinh doanh vận tải.
- «9. TỔNG HỢP HỒ SƠ CỬA HÀNG» (25 tệp) chứa **12 loại**: từ chứng nhận nghiệp vụ của nhân viên tới giấy phép xây dựng, đăng kiểm ghe, bản vẽ, hợp đồng thuê cửa hàng.
- «_3. HOP DONG DAU VAO-Diem» (20 tệp) chứa **8 loại**: chỉ 6 tệp là hợp đồng mua bán; còn lại là giấy đăng ký doanh nghiệp, giấy ủy quyền, giấy xác nhận thương nhân, hợp đồng vận chuyển, thông báo, thanh lý, thỏa thuận tín dụng.
- «_1. HOP DONG DAI LY NHUONG QUYEN» (25 tệp): chỉ **5 tệp** là hợp đồng nhượng quyền; 12 tệp là giấy đăng ký doanh nghiệp, 8 tệp là giấy đủ điều kiện bán lẻ — đúng loại của hai thư mục «_1. Giay DKKD khach hang» và «_2. Giay Du Dieu Kien Khach hang».

**(d) Tên thư mục sai so với nội dung.** «6. HOP DONG THUE KHO- Vi» (6 tệp) **không có hợp đồng thuê kho nào**: 4 hợp đồng mượn bồn (2 trùng byte với thư mục mượn bồn), 1 hợp đồng mua bồn, 1 tệp hóa đơn.
Hợp đồng thuê duy nhất của kho mẫu lại nằm trong hồ sơ cửa hàng.

**(e) Thư mục tách theo vai trò giao dịch, không theo loại văn bản.** «_2. HOP DONG KINH TE» và các hợp đồng trong «_3. HOP DONG DAU VAO-Diem» cùng là «Hợp đồng mua bán hàng hóa/xăng dầu»;
khác nhau ở chỗ công ty đứng bên bán hay bên mua. Đó là một **trường trích xuất** (`vai_tro_cong_ty`), không phải loại tài liệu.

**(f) Một tệp, nhiều tài liệu.** 21 tệp chứa hơn một tài liệu; 5/20 tệp của «_PHIẾU XUẤT KHO MUA HÀNG 2026» là bộ 4 chứng từ khác loại; một tệp của «6. CUA HANG - BB MAU- VÂN» chứa 93 biên bản.

**Hệ quả đo được.** Kết quả cổng luật cũ trên nhãn thư mục (`teams/team3_classification/results/rule_gate_baseline/summary.json`): đúng 51,9% trên phần luật quyết định được.
Ít nhất một phần «lỗi» đó là lỗi của nhãn chứ không phải của luật: luật nhận ra «giấy chứng nhận đăng ký doanh nghiệp» nhưng tệp nằm trong thư mục «hợp đồng đại lý nhượng quyền»
(20/25 tệp của thư mục đó rơi vào trường hợp này). Chưa tách được bao nhiêu phần trăm là lỗi nhãn, nhưng rõ ràng không thể dùng thước đo như vậy để so sánh mô hình.

## 3. Nguyên tắc thiết kế

1. **Lớp = loại tài liệu, quyết định được từ chính tài liệu**: tiêu đề → cơ quan ban hành → bố cục. Không dùng tên tệp, tên thư mục, hay việc tài liệu thuộc về ai.
2. **Hai cấp**: `group` (8 nhóm, dùng để báo cáo và làm mức lùi khi mô hình không chắc) và `doc_type` (lá).
3. **Độ mịn theo nhu cầu nghiệp vụ**: hai tài liệu khác lớp khi chúng cần **bộ trường trích xuất khác nhau** hoặc **cách theo dõi hết hạn / nơi lưu khác nhau**.
   Ví dụ giấy phép lái xe ≠ căn cước (hạng xe, hạn khác nhau); giấy biên nhận thế chấp ≠ đăng ký xe (do ngân hàng cấp, có hạn hiệu lực ngắn).
4. **Gộp các biến thể giống nhau về chức năng và trường dữ liệu**, kể cả khi mẫu in khác nhau:
   - bảo hiểm TNDS bắt buộc + bảo hiểm vật chất xe + bảo hiểm cháy nổ → `GCN_BAO_HIEM` (phân biệt bằng trường `loai_bao_hiem`);
   - đăng ký doanh nghiệp / đăng ký kinh doanh mẫu cũ / hợp tác xã / chi nhánh → `GCN_DKDN`;
   - đăng ký xe / rơ moóc / phương tiện thủy → `DANG_KY_PHUONG_TIEN`;
   - giấy đủ điều kiện PCCC + giấy thẩm duyệt thiết kế PCCC → `GCN_PCCC_CO_SO`;
   - kiểm định cột đo + kiểm định xi téc → `GCN_KIEM_DINH_DO_LUONG`;
   - «biên bản giao hàng» (mẫu công ty) + «biên bản giao nhận hàng» (mẫu nhà cung cấp) + «biên bản nghiệm thu, bàn giao hàng hóa» → `BB_GIAO_NHAN_HANG_HOA`;
   - biên bản lấy mẫu Mẫu 1 và Mẫu 2 → `BB_LAY_MAU`;
   - hợp đồng mua bán, hợp đồng nguyên tắc, hợp đồng thương nhân phân phối, «hợp đồng kinh tế» có nội dung mua bán → `HD_MUA_BAN`.
5. **Không gộp** chứng nhận huấn luyện PCCC với chứng nhận nghiệp vụ BVMT dù cả hai đều ít mẫu: khác cơ quan cấp, khác tiêu đề, khác quy định về hạn, và nghiệp vụ cần biết từng nhân viên còn thiếu chứng chỉ nào.
6. **Ngưỡng dữ liệu**: `data_status = ok` khi có ≥ 10 tệp duy nhất (đủ để mỗi fold của GroupKFold 5 phần có khoảng 2 mẫu); ngược lại `insufficient`. Ngưỡng này là quy ước của người thiết kế, có thể chỉnh.
7. **`OTHER`** cho tài liệu đọc được nhưng ngoài danh mục (phải ghi tiêu đề để xét mở loại mới); **`UNREADABLE`** cho tệp/trang không đọc được. Hai nhãn này không phải «lớp nội dung» để huấn luyện.
8. **Tương thích mã hiện có**: `src/classification/taxonomy.py` đọc `classes[].id/description/keywords/legacy_folders`. Trường `legacy_folders` chỉ liệt kê thư mục mà ≥ 90% số tệp thuộc đúng lớp đó,
   và mỗi thư mục xuất hiện ở nhiều nhất một lớp, nên `Taxonomy.legacy_to_id` vẫn là một ánh xạ hàm (14/19 thư mục). 5 thư mục hỗn hợp cố ý **không ánh xạ**; script đánh giá cũ sẽ đếm chúng là «unmapped».
   Đây chỉ là **nhãn yếu tạm thời** cho tới khi có bộ nhãn gold theo `doc_id`.

## 4. Danh mục nhóm và loại

Cột «Tệp» = số tệp duy nhất có nhãn chính là loại này; «Bản» = số tài liệu logic nếu tách hết các tệp composite; cột cuối = trường ngày hết hạn (nếu có).

| Nhóm | `doc_type` | Tên loại | Tệp | Bản | Dữ liệu | Trường hết hạn |
|---|---|---|---|---|---|---|
| Hợp đồng và thanh lý hợp đồng | `HD_MUA_BAN` | Hợp đồng mua bán hàng hóa / xăng dầu | 32 | 32 | ok | `hieu_luc_den` |
| Hợp đồng và thanh lý hợp đồng | `HD_NHUONG_QUYEN_DAI_LY` | Hợp đồng nhượng quyền bán lẻ / đại lý xăng dầu | 5 | 5 | insufficient | `hieu_luc_den` |
| Hợp đồng và thanh lý hợp đồng | `HD_VAN_CHUYEN` | Hợp đồng vận chuyển hàng hóa | 26 | 26 | ok | `hieu_luc_den` |
| Hợp đồng và thanh lý hợp đồng | `HD_MUON_BON` | Hợp đồng mượn bồn chứa dầu (kèm biên bản nhận bồn, trả bồn) | 9 | 9 | insufficient | `hieu_luc_den` |
| Hợp đồng và thanh lý hợp đồng | `HD_THUE_TAI_SAN` | Hợp đồng thuê kho / cửa hàng / tài sản | 1 | 1 | insufficient | `thoi_han_thue_den` |
| Hợp đồng và thanh lý hợp đồng | `BB_THANH_LY_HD` | Biên bản thanh lý hợp đồng | 14 | 15 | ok | — |
| Giấy phép, chứng nhận pháp lý của doanh nghiệp/cơ sở | `GCN_DKDN` | Giấy chứng nhận đăng ký doanh nghiệp / kinh doanh / hợp tác xã / chi nhánh | 35 | 36 | ok | — |
| Giấy phép, chứng nhận pháp lý của doanh nghiệp/cơ sở | `GCN_DDK_BAN_LE_XD` | Giấy chứng nhận cửa hàng đủ điều kiện bán lẻ xăng dầu | 27 | 27 | ok | `ngay_het_han` |
| Giấy phép, chứng nhận pháp lý của doanh nghiệp/cơ sở | `GXN_THUONG_NHAN_XD` | Giấy xác nhận đủ điều kiện làm thương nhân đầu mối / phân phối / đại lý xăng dầu | 2 | 2 | insufficient | `ngay_het_han` |
| Giấy phép, chứng nhận pháp lý của doanh nghiệp/cơ sở | `GP_KD_VAN_TAI` | Giấy phép kinh doanh vận tải bằng xe ô tô | 1 | 1 | insufficient | `ngay_het_han` |
| Giấy phép, chứng nhận pháp lý của doanh nghiệp/cơ sở | `GIAY_PHEP_XAY_DUNG` | Giấy phép xây dựng công trình (cửa hàng xăng dầu) | 1 | 1 | insufficient | `thoi_han_khoi_cong` |
| Chứng chỉ và giấy tờ cá nhân | `CC_TAP_HUAN_VC_HNH` | Giấy chứng nhận hoàn thành chương trình tập huấn vận chuyển hàng hóa nguy hiểm | 24 | 24 | ok | `ngay_het_han` |
| Chứng chỉ và giấy tờ cá nhân | `CC_HUAN_LUYEN_PCCC` | Chứng nhận huấn luyện nghiệp vụ PCCC và cứu nạn, cứu hộ | 3 | 3 | insufficient | `ngay_het_han` |
| Chứng chỉ và giấy tờ cá nhân | `CC_NGHIEP_VU_BVMT` | Giấy chứng nhận đào tạo/bồi dưỡng nghiệp vụ bảo vệ môi trường trong kinh doanh xăng dầu | 6 | 7 | insufficient | `ngay_het_han` |
| Chứng chỉ và giấy tờ cá nhân | `GPLX` | Giấy phép lái xe | 5 | 5 | insufficient | `ngay_het_han` |
| Chứng chỉ và giấy tờ cá nhân | `CCCD` | Căn cước công dân / chứng minh nhân dân | 1 | 1 | insufficient | `ngay_het_han` |
| Hồ sơ phương tiện và thiết bị | `DANG_KY_PHUONG_TIEN` | Chứng nhận đăng ký xe ô tô / rơ moóc / phương tiện thủy nội địa | 3 | 3 | insufficient | `ngay_het_han` |
| Hồ sơ phương tiện và thiết bị | `BIEN_NHAN_THE_CHAP_PT` | Giấy biên nhận thế chấp phương tiện giao thông (ngân hàng cấp) | 2 | 4 | insufficient | `ngay_het_han` |
| Hồ sơ phương tiện và thiết bị | `GCN_ATKT_BVMT_PT` | Giấy chứng nhận an toàn kỹ thuật và bảo vệ môi trường của phương tiện (đăng kiểm) | 1 | 1 | insufficient | `ngay_het_han` |
| Hồ sơ phương tiện và thiết bị | `GCN_KIEM_DINH_DO_LUONG` | Giấy chứng nhận kiểm định phương tiện đo (cột đo xăng dầu, xi téc ô tô) | 2 | 4 | insufficient | `ngay_het_han` |
| Hồ sơ phương tiện và thiết bị | `GP_VC_HANG_NGUY_HIEM` | Giấy phép vận chuyển hàng hóa nguy hiểm (về cháy, nổ) | 2 | 2 | insufficient | `ngay_het_han` |
| Hồ sơ PCCC, an toàn, môi trường của cơ sở | `GCN_PCCC_CO_SO` | Giấy chứng nhận đủ điều kiện / thẩm duyệt thiết kế về PCCC của cơ sở, phương tiện | 3 | 3 | insufficient | — |
| Hồ sơ PCCC, an toàn, môi trường của cơ sở | `HO_SO_QUAN_LY_PCCC` | Hồ sơ quản lý, theo dõi công tác PCCC của cơ sở (kèm biên bản tự kiểm tra PCCC) | 8 | 8 | insufficient | — |
| Hồ sơ PCCC, an toàn, môi trường của cơ sở | `BIEN_PHAP_UNG_PHO_SU_CO` | Biện pháp / kế hoạch phòng ngừa, ứng phó sự cố (hóa chất, tràn dầu), phương án chữa cháy | 1 | 1 | insufficient | — |
| Hồ sơ PCCC, an toàn, môi trường của cơ sở | `BAN_VE_KY_THUAT` | Bản vẽ kỹ thuật / thiết kế | 4 | 4 | insufficient | — |
| Bảo hiểm | `GCN_BAO_HIEM` | Giấy chứng nhận bảo hiểm (xe cơ giới, cháy nổ, tàu thuyền) | 7 | 7 | insufficient | `ngay_het_han` |
| Chứng từ mua bán, giao nhận hàng hóa | `DON_DAT_HANG` | Đơn đặt hàng | 20 | 20 | ok | — |
| Chứng từ mua bán, giao nhận hàng hóa | `PHIEU_XUAT_KHO` | Phiếu xuất kho | 21 | 21 | ok | — |
| Chứng từ mua bán, giao nhận hàng hóa | `BB_GIAO_NHAN_HANG_HOA` | Biên bản giao nhận / giao hàng / nghiệm thu bàn giao hàng hóa | 21 | 28 | ok | — |
| Chứng từ mua bán, giao nhận hàng hóa | `BB_LAY_MAU` | Biên bản lấy mẫu, niêm phong, bàn giao mẫu xăng dầu | 10 | 134 | ok | — |
| Chứng từ mua bán, giao nhận hàng hóa | `CHUNG_THU_CHAT_LUONG` | Chứng thư chất lượng (Certificate of Quality) | 0 | 6 | insufficient | — |
| Chứng từ mua bán, giao nhận hàng hóa | `HOA_DON` | Hóa đơn bán hàng / hóa đơn giá trị gia tăng | 1 | 2 | insufficient | — |
| Văn bản hành chính và loại khác | `GIAY_UY_QUYEN` | Giấy ủy quyền | 3 | 3 | insufficient | `ngay_het_han` |
| Văn bản hành chính và loại khác | `CONG_VAN_THONG_BAO` | Công văn / thông báo / quyết định / quy chế (văn bản hành chính) | 2 | 2 | insufficient | — |
| Văn bản hành chính và loại khác | `OTHER` | Tài liệu khác (đọc được nhưng không thuộc loại nào trong danh mục) | 1 | 1 | insufficient | — |
| Văn bản hành chính và loại khác | `UNREADABLE` | Không đọc được | 0 | 0 | insufficient | — |

Tổng: 304 tệp duy nhất; 449 tài liệu logic. `CHUNG_THU_CHAT_LUONG` chưa có tệp đứng riêng nào — chỉ xuất hiện như một trang trong 6 bộ chứng từ xuất kho.

## 5. Ánh xạ thư mục cũ → loại tài liệu

«Composite» = số tệp duy nhất là composite / trong đó khác loại. «Ánh xạ yếu» = lớp mà `legacy_to_id` trả về cho thư mục (chỉ khi thư mục gần như thuần một loại).

| Thư mục cũ | Tệp | Duy nhất | Loại tài liệu bên trong (số tệp, tính cả bản trùng) | Composite | Ánh xạ yếu |
|---|---|---|---|---|---|
| `(gốc, không nhãn)` | 2 | 2 | `PHIEU_XUAT_KHO` 1, `CONG_VAN_THONG_BAO` 1 | 1 / 1 | — |
| `10. GCN VC HNH` | 20 | 19 | `CC_TAP_HUAN_VC_HNH` 20 | 0 / 0 | `CC_TAP_HUAN_VC_HNH` |
| `5. TỔNG HỢP HỒ SƠ XE` | 20 | 20 | `GCN_BAO_HIEM` 6, `GPLX` 5, `DANG_KY_PHUONG_TIEN` 2, `BIEN_NHAN_THE_CHAP_PT` 2, `GP_VC_HANG_NGUY_HIEM` 2, `CCCD` 1, `GCN_KIEM_DINH_DO_LUONG` 1, `GP_KD_VAN_TAI` 1 | 2 / 0 | — (hỗn hợp) |
| `6. CUA HANG - BB MAU- VÂN` | 10 | 10 | `BB_LAY_MAU` 10 | 7 / 0 | `BB_LAY_MAU` |
| `6. HOP DONG MUON BON` | 7 | 7 | `HD_MUON_BON` 7 | 0 / 0 | `HD_MUON_BON` |
| `6. HOP DONG THUE KHO- Vi` | 6 | 6 | `HD_MUON_BON` 4, `HOA_DON` 1, `HD_MUA_BAN` 1 | 1 / 0 | — (hỗn hợp) |
| `8. CUA HANG - TU K.TRA PCCC- VÂN` | 5 | 5 | `HO_SO_QUAN_LY_PCCC` 5 | 0 / 0 | `HO_SO_QUAN_LY_PCCC` |
| `8. GCN Lop dao tao van chuyen hang chay no` | 20 | 20 | `CC_TAP_HUAN_VC_HNH` 20 | 0 / 0 | `CC_TAP_HUAN_VC_HNH` |
| `9. TỔNG HỢP HỒ SƠ CỬA HÀNG` | 25 | 25 | `CC_NGHIEP_VU_BVMT` 6, `BAN_VE_KY_THUAT` 4, `CC_HUAN_LUYEN_PCCC` 3, `GCN_PCCC_CO_SO` 3, `CC_TAP_HUAN_VC_HNH` 2, `GCN_DKDN` 1, `BIEN_PHAP_UNG_PHO_SU_CO` 1, `GCN_ATKT_BVMT_PT` 1, `GIAY_PHEP_XAY_DUNG` 1, `GCN_BAO_HIEM` 1, `GCN_KIEM_DINH_DO_LUONG` 1, `HD_THUE_TAI_SAN` 1 | 2 / 0 | — (hỗn hợp) |
| `TU K.TRA PCCC- VÂN` | 5 | 5 | `HO_SO_QUAN_LY_PCCC` 5 | 0 / 0 | `HO_SO_QUAN_LY_PCCC` |
| `_1. Giay DKKD khach hang` | 23 | 23 | `GCN_DKDN` 22, `DANG_KY_PHUONG_TIEN` 1 | 0 / 0 | `GCN_DKDN` |
| `_1. HOP DONG DAI LY NHUONG QUYEN` | 25 | 25 | `GCN_DKDN` 12, `GCN_DDK_BAN_LE_XD` 8, `HD_NHUONG_QUYEN_DAI_LY` 5 | 0 / 0 | — (hỗn hợp) |
| `_2. Giay Du Dieu Kien Khach hang` | 25 | 22 | `GCN_DDK_BAN_LE_XD` 25 | 0 / 0 | `GCN_DDK_BAN_LE_XD` |
| `_2. HOP DONG KINH TE` | 25 | 25 | `HD_MUA_BAN` 25 | 0 / 0 | `HD_MUA_BAN` |
| `_3. HOP DONG DAU VAO-Diem` | 20 | 20 | `HD_MUA_BAN` 6, `GCN_DKDN` 4, `GIAY_UY_QUYEN` 3, `GXN_THUONG_NHAN_XD` 2, `HD_VAN_CHUYEN` 2, `OTHER` 1, `CONG_VAN_THONG_BAO` 1, `BB_THANH_LY_HD` 1 | 0 / 0 | — (hỗn hợp) |
| `_4. THANH LÝ HỢP ĐỒNG` | 14 | 14 | `BB_THANH_LY_HD` 13, `BB_GIAO_NHAN_HANG_HOA` 1 | 1 / 1 | `BB_THANH_LY_HD` |
| `_5. HOP DONG VAN CHUYEN` | 24 | 24 | `HD_VAN_CHUYEN` 24 | 1 / 1 | `HD_VAN_CHUYEN` |
| `_Biên bản giao nhận 2026` | 20 | 20 | `BB_GIAO_NHAN_HANG_HOA` 20 | 1 / 0 | `BB_GIAO_NHAN_HANG_HOA` |
| `_PHIẾU XUẤT KHO MUA HÀNG 2026` | 20 | 20 | `PHIEU_XUAT_KHO` 20 | 5 / 5 | `PHIEU_XUAT_KHO` |
| `_Đơn đặt hàng - mua vào 2026` | 20 | 20 | `DON_DAT_HANG` 20 | 0 / 0 | `DON_DAT_HANG` |

### Thư mục nào gộp lại, thư mục nào tách ra

**Gộp (nhiều thư mục → một loại):**

| Loại | Gộp từ |
|---|---|
| `CC_TAP_HUAN_VC_HNH` | «10. GCN VC HNH» + «8. GCN Lop dao tao van chuyen hang chay no» + 2 tệp trong hồ sơ cửa hàng |
| `HO_SO_QUAN_LY_PCCC` | «8. CUA HANG - TU K.TRA PCCC- VÂN» + «TU K.TRA PCCC- VÂN» |
| `HD_MUON_BON` | «6. HOP DONG MUON BON» + 4/6 tệp của «6. HOP DONG THUE KHO- Vi» |
| `HD_MUA_BAN` | «_2. HOP DONG KINH TE» + 6 hợp đồng trong «_3. HOP DONG DAU VAO-Diem» + 1 tệp trong «6. HOP DONG THUE KHO- Vi» |
| `GCN_DKDN` | «_1. Giay DKKD khach hang» + 12 tệp trong «_1. HOP DONG DAI LY NHUONG QUYEN» + 4 tệp trong «_3. HOP DONG DAU VAO-Diem» + 1 tệp trong hồ sơ cửa hàng |
| `GCN_DDK_BAN_LE_XD` | «_2. Giay Du Dieu Kien Khach hang» + 8 tệp trong «_1. HOP DONG DAI LY NHUONG QUYEN» |
| `HD_VAN_CHUYEN` | «_5. HOP DONG VAN CHUYEN» + 2 tệp trong «_3. HOP DONG DAU VAO-Diem» |
| `BB_THANH_LY_HD` | «_4. THANH LÝ HỢP ĐỒNG» + 1 tệp trong «_3. HOP DONG DAU VAO-Diem» |
| `BB_GIAO_NHAN_HANG_HOA` | «_Biên bản giao nhận 2026» + trang biên bản giao nhận trong 6 bộ chứng từ xuất kho + 1 tệp trong «_4. THANH LÝ HỢP ĐỒNG» |
| `BB_LAY_MAU` | «6. CUA HANG - BB MAU- VÂN» + trang biên bản lấy mẫu trong 6 bộ chứng từ xuất kho |

**Tách (một thư mục → nhiều loại):** «5. TỔNG HỢP HỒ SƠ XE» → 8 loại; «9. TỔNG HỢP HỒ SƠ CỬA HÀNG» → 12 loại; «_3. HOP DONG DAU VAO-Diem» → 8 loại;
«_1. HOP DONG DAI LY NHUONG QUYEN» → 3 loại; «6. HOP DONG THUE KHO- Vi» → 3 loại; «_1. Giay DKKD khach hang» → 2 loại (22 + 1 đăng ký tàu);
«_4. THANH LÝ HỢP ĐỒNG» → 2 loại (13 + 1 bộ nghiệm thu–thanh lý); «_PHIẾU XUẤT KHO MUA HÀNG 2026» → 4 loại ở mức segment (5/20 tệp là bộ chứng từ).

**Giữ nguyên 1–1:** «_Đơn đặt hàng - mua vào 2026» → `DON_DAT_HANG`.

## 6. Quy tắc định tuyến (nơi lưu = hàm của loại + thực thể)

Nguyên tắc: bộ phân loại trả lời «đây là giấy gì»; bộ trích xuất trả lời «của ai / xe nào / cửa hàng nào / hạn đến bao giờ»; **bộ định tuyến** kết hợp hai câu trả lời với danh mục chủ dữ liệu
(khách hàng, nhà cung cấp, cửa hàng, xe, lái xe) để chọn hồ sơ đích. Một tài liệu có thể đi tới hơn một hồ sơ. «Công ty chủ quản» được nhận biết bằng mã số thuế cấu hình khi triển khai, không viết cứng trong taxonomy.

| Mã | `doc_type` | Điều kiện | Thực thể khóa | Thư mục đích | Căn cứ |
|---|---|---|---|---|---|
| R01 | `HD_MUA_BAN` | vai_tro_cong_ty = ben_ban (công ty chủ quản bán hàng cho khách) | khách hàng (ben_mua: tên + mã số thuế), năm hiệu lực | `_2. HOP DONG KINH TE` | quan sát |
| R02 | `HD_MUA_BAN` | vai_tro_cong_ty = ben_mua và mặt hàng là xăng dầu (hợp đồng với nhà cung cấp) | nhà cung cấp (ben_ban: tên + mã số thuế) | `_3. HOP DONG DAU VAO-Diem` | quan sát |
| R03 | `HD_MUA_BAN` | vai_tro_cong_ty = ben_mua và mặt hàng là tài sản/thiết bị (bồn, xe) | nhà cung cấp | *(chưa xác định)* | cần hỏi |
| R04 | `HD_NHUONG_QUYEN_DAI_LY` | luôn luôn | khách hàng nhận nhượng quyền/đại lý (tên + mã số thuế), ngày hết hiệu lực | `_1. HOP DONG DAI LY NHUONG QUYEN` | quan sát |
| R05 | `GCN_DKDN` | chủ thể trên giấy là khách hàng (tra mã số doanh nghiệp trong danh mục khách hàng) | mã số doanh nghiệp | `_1. Giay DKKD khach hang` | quan sát |
| R06 | `GCN_DKDN`, `GXN_THUONG_NHAN_XD`, `GIAY_UY_QUYEN`, `CONG_VAN_THONG_BAO` | chủ thể/đơn vị ban hành là nhà cung cấp (tra mã số thuế trong danh mục nhà cung cấp) | nhà cung cấp (mã số thuế) | `_3. HOP DONG DAU VAO-Diem` | quan sát |
| R07 | `GCN_DDK_BAN_LE_XD` | cửa hàng trên giấy thuộc khách hàng | khách hàng (thương nhân chủ sở hữu) + tên cửa hàng + ngày hết hạn | `_2. Giay Du Dieu Kien Khach hang` | quan sát |
| R08 | `GCN_DKDN`, `GCN_DDK_BAN_LE_XD`, `GCN_PCCC_CO_SO`, `GIAY_PHEP_XAY_DUNG`, `BIEN_PHAP_UNG_PHO_SU_CO`, `BAN_VE_KY_THUAT`, `CC_HUAN_LUYEN_PCCC`, `CC_NGHIEP_VU_BVMT` | chủ thể là cửa hàng/ghe bán lẻ thuộc hệ thống của công ty chủ quản, hoặc cá nhân là nhân viên của cửa hàng đó | cửa hàng (số cửa hàng / tên ghe, tàu); với chứng chỉ: họ tên nhân viên + ngày hết hạn | `9. TỔNG HỢP HỒ SƠ CỬA HÀNG` | quan sát |
| R09 | `HD_VAN_CHUYEN` | mặc định (cả hai vai trò chủ hàng và vận chuyển) | đối tác (tên + mã số thuế), năm hiệu lực | `_5. HOP DONG VAN CHUYEN` | quan sát |
| R10 | `HD_MUON_BON` | luôn luôn | khách hàng mượn bồn (tên + mã số thuế), năm | `6. HOP DONG MUON BON` | quan sát |
| R11 | `HD_THUE_TAI_SAN` | tài sản thuê là kho chứa | bên cho thuê/bên thuê, ngày hết hạn thuê | `6. HOP DONG THUE KHO- Vi` | giả định |
| R12 | `HD_THUE_TAI_SAN` | tài sản thuê là cửa hàng/điểm bán lẻ | cửa hàng | `9. TỔNG HỢP HỒ SƠ CỬA HÀNG` | quan sát |
| R13 | `BB_THANH_LY_HD` | mặc định | đối tác + số hợp đồng gốc | `_4. THANH LÝ HỢP ĐỒNG` | quan sát |
| R14 | `CC_TAP_HUAN_VC_HNH` | luôn luôn (người được cấp là lái xe/áp tải) | họ tên người được cấp + ngày hết hạn | `8. GCN Lop dao tao van chuyen hang chay no` | quan sát |
| R15 | `GPLX`, `CCCD` | người đứng tên là lái xe của công ty | họ tên lái xe + ngày hết hạn (gắn với xe được phân công nếu có) | `5. TỔNG HỢP HỒ SƠ XE` | quan sát |
| R16 | `DANG_KY_PHUONG_TIEN`, `BIEN_NHAN_THE_CHAP_PT`, `GCN_ATKT_BVMT_PT`, `GP_VC_HANG_NGUY_HIEM`, `GCN_KIEM_DINH_DO_LUONG`, `GCN_BAO_HIEM` | đối tượng là xe ô tô/rơ moóc/xi téc (có biển số xe) | biển số xe + ngày hết hạn | `5. TỔNG HỢP HỒ SƠ XE` | quan sát |
| R17 | `GP_KD_VAN_TAI` | luôn luôn | đơn vị được cấp | `5. TỔNG HỢP HỒ SƠ XE` | quan sát |
| R18 | `DANG_KY_PHUONG_TIEN`, `GCN_ATKT_BVMT_PT`, `GCN_KIEM_DINH_DO_LUONG`, `GCN_BAO_HIEM` | đối tượng là ghe/tàu bán lẻ hoặc thiết bị, tài sản của một cửa hàng thuộc công ty (cột đo, bảo hiểm cháy nổ cửa hàng) | cửa hàng/ghe (số, tên) + ngày hết hạn | `9. TỔNG HỢP HỒ SƠ CỬA HÀNG` | quan sát |
| R19 | `DANG_KY_PHUONG_TIEN` | phương tiện thuộc sở hữu của khách hàng | khách hàng | `_1. Giay DKKD khach hang` | quan sát |
| R20 | `HO_SO_QUAN_LY_PCCC` | luôn luôn | cửa hàng/ghe + kỳ hồ sơ (năm, tháng) | `8. CUA HANG - TU K.TRA PCCC- VÂN` | quan sát |
| R21 | `BB_LAY_MAU` | Mẫu 2 (BBLM-BGM-KTNP) lập tại cửa hàng khi nhập hàng | cửa hàng + năm/tháng | `6. CUA HANG - BB MAU- VÂN` | quan sát |
| R22 | `PHIEU_XUAT_KHO`, `CHUNG_THU_CHAT_LUONG`, `BB_LAY_MAU`, `BB_GIAO_NHAN_HANG_HOA` | chứng từ của chuyến hàng MUA VÀO từ nhà cung cấp (phiếu xuất kho của nhà máy/kho và các chứng từ kèm theo cùng chuyến: chứng thư, biên bản giao nhận, biên bản lấy mẫu Mẫu 1) | số phiếu xuất kho + ngày + biển số xe | `_PHIẾU XUẤT KHO MUA HÀNG 2026` | quan sát |
| R23 | `BB_GIAO_NHAN_HANG_HOA` | chieu_giao_dich = ban_ra (công ty giao hàng cho khách) | khách hàng + ngày giao + biển số xe | `_Biên bản giao nhận 2026` | quan sát |
| R24 | `DON_DAT_HANG` | luôn luôn (đơn do công ty gửi nhà cung cấp) | nhà cung cấp + số đơn + ngày | `_Đơn đặt hàng - mua vào 2026` | quan sát |
| R25 | `HOA_DON`, `OTHER`, `UNREADABLE` | luôn luôn | — | *(chưa xác định)* | cần hỏi |

Căn cứ «quan sát» = suy ra từ vị trí thực tế của các tệp mẫu (chi tiết ở trường `evidence` của từng quy tắc trong JSON); «giả định» = suy từ tên thư mục; «cần hỏi» = xem mục 9.
Bộ định tuyến cần **danh mục chủ dữ liệu** từ ERP; nếu chưa có, các quy tắc phụ thuộc vai trò (R01–R03, R05–R08, R15–R19) phải chuyển sang hàng chờ người duyệt.

## 7. Tệp composite và hệ quả cho từng nhóm

### 7.1. Quy tắc (bản đầy đủ ở mục 7 của hướng dẫn gán nhãn)

1. `is_composite=1` khi tệp chứa ≥ 2 tài liệu logic: **khác loại**, hoặc **cùng loại nhưng khác bản** (khác người, khác xe, khác số/ngày).
2. **Phép thử kèm theo**: một đoạn trang chỉ mở segment mới nếu, khi đứng riêng, nó là một `doc_type` khác tài liệu đứng trước (và khác `OTHER`) hoặc là một bản khác của cùng loại. Phụ lục, danh mục, «những điều quy định», mặt sau, bìa, trang trắng, biên bản nhận/trả bồn, bảng báo giá, giấy xác nhận thay đổi đăng ký của chính doanh nghiệp đó → không tách.
3. **Tập có bìa chung** (hồ sơ quản lý PCCC, biện pháp ứng phó sự cố) là một tài liệu dù có nhiều tiêu đề con.
4. **Nhãn chính** của tệp composite = loại của segment đầu tiên (máy kiểm tra được từ cột `segments`).
5. Composite **khác loại** bị loại khỏi benchmark phân loại một nhãn và trở thành gold set cho tách tài liệu; composite **cùng loại** vẫn nằm trong benchmark phân loại.

Đề xuất ban đầu («loại toàn bộ tệp composite khỏi benchmark phân loại») được **điều chỉnh**: nếu loại cả composite cùng loại thì `BB_LAY_MAU` mất 7/10 tệp dù nhãn cấp tệp của chúng hoàn toàn rõ ràng. Chỉ nên loại 8 tệp khác loại.

### 7.2. 21 tệp composite trong kho mẫu (bản gán nhãn tạm)

| `doc_id` | Tệp | Trang | Kiểu | Segments |
|---|---|---|---|---|
| `898572a6f361` | `5. TỔNG HỢP HỒ SƠ XE/1. Xe 08001-02645-15.2.24.pdf` | 2 | cùng loại | `1:BIEN_NHAN_THE_CHAP_PT;2:BIEN_NHAN_THE_CHAP_PT` |
| `4ad1c01d6262` | `5. TỔNG HỢP HỒ SƠ XE/3. Xe 09567-00934.pdf` | 2 | cùng loại | `1:BIEN_NHAN_THE_CHAP_PT;2:BIEN_NHAN_THE_CHAP_PT` |
| `aba856a262ef` | `6. CUA HANG - BB MAU- VÂN/BB mau CH12-21.pdf` | 93 | cùng loại | `1:BB_LAY_MAU;…;93:BB_LAY_MAU` (93 segment một trang) |
| `d51eeba77210` | `6. CUA HANG - BB MAU- VÂN/BB mau G1-21..pdf` | 2 | cùng loại | `1:BB_LAY_MAU;2:BB_LAY_MAU` |
| `4f81a78f1e50` | `6. CUA HANG - BB MAU- VÂN/BB mau G1-22..pdf` | 6 | cùng loại | `1:BB_LAY_MAU;2:BB_LAY_MAU;3:BB_LAY_MAU;4:BB_LAY_MAU;5:BB_LAY_MAU;6:BB_LAY_MAU` |
| `596b4f4c5bda` | `6. CUA HANG - BB MAU- VÂN/T1+2+3.pdf` | 10 | cùng loại | `1:BB_LAY_MAU;…;10:BB_LAY_MAU` (10 segment một trang) |
| `ece9a4318b32` | `6. CUA HANG - BB MAU- VÂN/T2_2.pdf` | 2 | cùng loại | `1:BB_LAY_MAU;2:BB_LAY_MAU` |
| `0cf9aa186387` | `6. CUA HANG - BB MAU- VÂN/T2_3.pdf` | 3 | cùng loại | `1:BB_LAY_MAU;2:BB_LAY_MAU;3:BB_LAY_MAU` |
| `7888ea753973` | `6. CUA HANG - BB MAU- VÂN/T3_1.pdf` | 9 | cùng loại | `1:BB_LAY_MAU;…;9:BB_LAY_MAU` (9 segment một trang) |
| `36aff038b19e` | `6. HOP DONG THUE KHO- Vi/HDB 2017-.pdf` | 4 | cùng loại | `1-2:HOA_DON;3-4:HOA_DON` |
| `6c50528f7f4f` | `9. TỔNG HỢP HỒ SƠ CỬA HÀNG/Cột đo ghe 1.pdf` | 3 | cùng loại | `1:GCN_KIEM_DINH_DO_LUONG;2:GCN_KIEM_DINH_DO_LUONG;3:GCN_KIEM_DINH_DO_LUONG` |
| `72449aceeff3` | `9. TỔNG HỢP HỒ SƠ CỬA HÀNG/MT 2 nhân vien GH3_2.pdf` | 4 | cùng loại | `1-2:CC_NGHIEP_VU_BVMT;3-4:CC_NGHIEP_VU_BVMT` |
| `9f4c4dae0c73` | `(gốc, không nhãn)/BSR-2629763-HH 10-06-2026 20-10-37.pdf` | 5 | khác loại | `1-2:PHIEU_XUAT_KHO;3:CHUNG_THU_CHAT_LUONG;4:BB_GIAO_NHAN_HANG_HOA;5:BB_LAY_MAU` |
| `87c88bf6d0f1` | `_4. THANH LÝ HỢP ĐỒNG/TLHD 11.20-SU DOAN 31.pdf` | 5 | khác loại | `1-2:BB_GIAO_NHAN_HANG_HOA;3-5:BB_THANH_LY_HD` |
| `57374da27cae` | `_5. HOP DONG VAN CHUYEN/HDVC 2020-TOAN THINH-01.01-31.12.pdf` | 4 | khác loại | `1-2:HD_VAN_CHUYEN;3-4:GCN_DKDN` |
| `83f88be6530c` | `_Biên bản giao nhận 2026/bbgn-260528-6.pdf` | 2 | cùng loại | `1:BB_GIAO_NHAN_HANG_HOA;2:BB_GIAO_NHAN_HANG_HOA` |
| `9c00a14eed6b` | `_PHIẾU XUẤT KHO MUA HÀNG 2026/20260109-04.pdf` | 4 | khác loại | `1:PHIEU_XUAT_KHO;2:BB_GIAO_NHAN_HANG_HOA;3:BB_LAY_MAU;4:CHUNG_THU_CHAT_LUONG` |
| `11133174f271` | `_PHIẾU XUẤT KHO MUA HÀNG 2026/20260111-06.pdf` | 4 | khác loại | `1:PHIEU_XUAT_KHO;2:BB_GIAO_NHAN_HANG_HOA;3:BB_LAY_MAU;4:CHUNG_THU_CHAT_LUONG` |
| `3a74922446fc` | `_PHIẾU XUẤT KHO MUA HÀNG 2026/20260119-03.pdf` | 4 | khác loại | `1:PHIEU_XUAT_KHO;2:BB_GIAO_NHAN_HANG_HOA;3:BB_LAY_MAU;4:CHUNG_THU_CHAT_LUONG` |
| `129e563d2196` | `_PHIẾU XUẤT KHO MUA HÀNG 2026/20260120-02.pdf` | 4 | khác loại | `1:PHIEU_XUAT_KHO;2:BB_GIAO_NHAN_HANG_HOA;3:BB_LAY_MAU;4:CHUNG_THU_CHAT_LUONG` |
| `98d9bec84dcc` | `_PHIẾU XUẤT KHO MUA HÀNG 2026/20260120-04.pdf` | 4 | khác loại | `1:PHIEU_XUAT_KHO;2:BB_GIAO_NHAN_HANG_HOA;3:BB_LAY_MAU;4:CHUNG_THU_CHAT_LUONG` |

Tệp 93 trang mới được đọc 10 trang rải đều (trang nào cũng là một biên bản một trang cùng mẫu); người gán nhãn cần lướt hết.

### 7.3. Nhóm 3 — Phân loại

- **Mục tiêu dự đoán**: `doc_type` (34 loại + `OTHER`; mô hình được phép từ chối = `UNKNOWN`). Đơn vị đánh giá là **tệp duy nhất** (gộp theo `sha256`), chia fold bằng `GroupKFold(groups=template_group)` như báo cáo 01.
- **Benchmark A (chính)**: 222 tệp thuộc 10 loại `ok`, bỏ 8 tệp composite khác loại. Báo cáo macro-F1, F1 từng loại, tỉ lệ từ chối.
- **Benchmark B (đuôi dài)**: 74 tệp thuộc 24 loại `insufficient` + `OTHER`. Không huấn luyện có giám sát được; chỉ đánh giá zero-shot (mô tả lớp trong `description`) và cổng luật: báo cáo số tệp đúng / tổng theo từng loại và **độ chính xác ở mức nhóm**. Không báo cáo F1 riêng cho loại có < 10 tệp.
- **Đầu vào**: văn bản **mọi trang** hoặc ít nhất tới trang nhận dạng được. Chỉ dùng trang 1 là không đủ: ít nhất 2/6 tệp `CC_NGHIEP_VU_BVMT` có trang 1 là bìa chỉ ghi «GIẤY CHỨNG NHẬN», thẻ tập huấn có trang 1 là bìa không ghi tên người; thẻ đăng ký xe có tiêu đề ở trang 2.
- **Nhãn thật**: khi có bộ gold, script đánh giá phải nối theo `doc_id` với tệp nhãn thay vì dùng `legacy_to_id`. Trước đó, `legacy_to_id` chỉ phủ 14/19 thư mục (238/334 tệp có thư mục) và là nhãn yếu.
- **Thay đổi hành vi mặc định**: từ khi `data/taxonomy_v2.json` tồn tại, `load_taxonomy()` và `scripts/evaluate_classifier_baseline.py` tự nạp v2 thay cho 19 nhãn thư mục. Kết quả cũ trong `results/rule_gate_baseline/` là của taxonomy legacy và không còn tái lập được bằng lệnh mặc định (bộ nạp chỉ quay về legacy khi tệp v2 không tồn tại). Người thiết kế chưa chạy trọn script đánh giá với v2 (lần chạy thử bị dừng vì Kev cục bộ đang bật và mỗi lần gọi rất chậm); con số duy nhất với v2 là phép kiểm cổng luật ở mục 8.3.
- **Kích thước prompt**: 36 đoạn `description` dài tổng cộng khoảng 23.000 ký tự — quá nặng nếu gửi tất cả cho một mô hình cục bộ nhỏ trong một lần gọi (mã hiện tại gửi `criteria` = `description` của mọi lớp). Hai lối ra: dùng `short_description` (một câu mỗi lớp, tổng khoảng 4.000 ký tự) cho lần gọi liệt kê mọi lớp; hoặc phân loại hai bước (chọn `group` trước bằng `groups[].description`, rồi chọn lớp trong nhóm bằng `description` đầy đủ; nhóm lớn nhất có 6 lớp). Cần đo cả hai.
- **Cổng luật**: `keywords` là cụm tiêu đề. Kiểm tra nhanh ở mục 8.3 cho thấy quy tắc «chỉ quyết định khi đúng một lớp khớp» bỏ lỡ 30 tệp vì thân văn bản nhắc tên loại khác
  (đơn đặt hàng nhắc «hợp đồng mua bán», biên bản thanh lý nhắc «hợp đồng nhượng quyền»). Đề xuất thử quy tắc «từ khóa xuất hiện sớm nhất thắng» và trường mở rộng `rule_priority`.
- `OTHER` và `UNREADABLE` có `"special": true`: đừng coi chúng là lớp nội dung khi huấn luyện; `UNREADABLE` nên do bước kiểm tra chất lượng OCR quyết định, không do bộ phân loại văn bản.

### 7.4. Nhóm 2 — Tách tài liệu

- **Gold set**: cột `segments` của 21 tệp composite là mẫu dương; 191 tệp nhiều trang không composite là **mẫu âm** (không có ranh giới bên trong) và quan trọng không kém.
  Tổng cộng 809 vị trí «giữa hai trang liên tiếp», trong đó 145 là ranh giới thật (27 nếu không tính 7 tệp biên bản lấy mẫu nhiều trang).
- **Chỉ số**: precision/recall/F1 của ranh giới ở mức trang; tỉ lệ tệp có toàn bộ segment đúng; báo cáo riêng cho composite khác loại và cùng loại.
- **Ca khó có chủ ý**: (i) tập PCCC 26–53 trang có hơn 10 tiêu đề con nhưng **không** có ranh giới; (ii) tệp biên bản lấy mẫu có ranh giới ở **mọi** trang dù các trang giống hệt nhau về bố cục;
  (iii) «biên bản nhận bồn/trả bồn», «những điều quy định», «giấy xác nhận thay đổi…» có tiêu đề riêng nhưng không phải ranh giới; (iv) trang trắng do quét hai mặt; (v) trang chữ ký «2/2».
  Vì vậy bộ tách phải **biết loại tài liệu** (tách và phân loại theo trang nên chạy cùng nhau), không thể chỉ dựa vào «có quốc hiệu + tiêu đề in hoa».
- Tài liệu `docs/COMPOSITE_DOCUMENTS_AND_SPLITTING.md` dùng tên loại viết thường (`phieu_xuat_kho`…) và `category_label` là tên thư mục; nên chuyển sang `id` của taxonomy v2.

### 7.5. Nhóm 4 — Trích xuất

- **Schema**: `classes[].key_fields` là danh sách trường cho từng loại (tên ASCII, mô tả, cờ `is_expiry`). Chọn schema theo `doc_type` của **segment**, không theo tệp: tệp composite sinh ra một bản ghi cho mỗi segment (tệp 93 biên bản lấy mẫu → 93 bản ghi).
- **Trường hết hạn** (21 trường ở 21 loại) là ưu tiên số một vì chúng điều khiển lịch nhắc hạn:

| `doc_type` | Trường | Ý nghĩa |
|---|---|---|
| `HD_MUA_BAN` | `hieu_luc_den` | Ngày hết hiệu lực hợp đồng |
| `HD_NHUONG_QUYEN_DAI_LY` | `hieu_luc_den` | Ngày hết hiệu lực hợp đồng |
| `HD_VAN_CHUYEN` | `hieu_luc_den` | Ngày hết hiệu lực hợp đồng |
| `HD_MUON_BON` | `hieu_luc_den` | Ngày hết hiệu lực hợp đồng, nếu có ghi |
| `HD_THUE_TAI_SAN` | `thoi_han_thue_den` | Ngày hết hạn thuê |
| `GCN_DDK_BAN_LE_XD` | `ngay_het_han` | «Có giá trị đến hết ngày…» (thường 5 năm) |
| `GXN_THUONG_NHAN_XD` | `ngay_het_han` | «Có giá trị đến hết ngày…» |
| `GP_KD_VAN_TAI` | `ngay_het_han` | Ngày hết hạn, nếu giấy có ghi thời hạn |
| `GIAY_PHEP_XAY_DUNG` | `thoi_han_khoi_cong` | Thời hạn hiệu lực để khởi công (ví dụ «có giá trị trong 12 tháng») |
| `CC_TAP_HUAN_VC_HNH` | `ngay_het_han` | Có giá trị đến ngày (thường 2 năm) |
| `CC_HUAN_LUYEN_PCCC` | `ngay_het_han` | Ngày hết giá trị (ghi trên thẻ hoặc tính theo quy định hiện hành) |
| `CC_NGHIEP_VU_BVMT` | `ngay_het_han` | «Có giá trị đến ngày…», nếu có ghi |
| `GPLX` | `ngay_het_han` | «Có giá trị đến» |
| `CCCD` | `ngay_het_han` | «Có giá trị đến» |
| `DANG_KY_PHUONG_TIEN` | `ngay_het_han` | «Đăng ký xe có giá trị đến ngày» (niên hạn sử dụng), nếu có |
| `BIEN_NHAN_THE_CHAP_PT` | `ngay_het_han` | «Có hiệu lực đến hết ngày…» |
| `GCN_ATKT_BVMT_PT` | `ngay_het_han` | «Có hiệu lực đến ngày» (hạn đăng kiểm) |
| `GCN_KIEM_DINH_DO_LUONG` | `ngay_het_han` | «Thời hạn đến / Valid until» |
| `GP_VC_HANG_NGUY_HIEM` | `ngay_het_han` | «Thời hạn của giấy phép» |
| `GCN_BAO_HIEM` | `ngay_het_han` | Thời hạn bảo hiểm đến |
| `GIAY_UY_QUYEN` | `ngay_het_han` | Hiệu lực đến hết ngày |

- **Nhãn yếu miễn phí**: tên tệp thường ghi ngày hết hạn do nhân viên nhập (ví dụ «DDK-CHIN LOAN-12.1.28» khớp dòng «có giá trị đến hết ngày 12 tháng 01 năm 2028» trên giấy; «DDK-HAI THAO-15.12.24» khớp «15 tháng 12 năm 2024»). Có thể dùng để kiểm tra chéo trường hết hạn, sau khi chủ nghiệp vụ xác nhận quy ước đặt tên (câu hỏi 16).
- **Trường định tuyến**: `vai_tro_cong_ty`, `chieu_giao_dich`, `doi_tuong_bao_hiem`, biển số, mã số doanh nghiệp, tên/số cửa hàng — cần chuẩn hóa để tra danh mục chủ dữ liệu.
- **Dữ liệu cá nhân**: `CCCD`, `GPLX` và phần người đại diện trên `GCN_DKDN`, `GIAY_UY_QUYEN` chứa số định danh. Chỉ trích khi nghiệp vụ yêu cầu (câu hỏi 12); không đưa vào log, không đưa vào bộ dữ liệu chia sẻ.

### 7.6. Nhóm 1 — OCR

- Bộ nhãn cần **văn bản mọi trang**; vùng quan trọng nhất là 1/3 trên của trang đầu mỗi tài liệu (tiêu đề, cơ quan ban hành, số, ngày).
- Thẻ nhỏ (giấy phép lái xe, căn cước, đăng ký xe, chứng nhận) chỉ chiếm một góc trang A4 → cần phát hiện vùng và phóng to trước khi OCR.
- Có trang xoay 90° (đăng kiểm ghe, bảo hiểm cháy nổ, bản vẽ, sổ kẻ bảng trong tập PCCC) → cần chuẩn hóa hướng trang.
- Chữ viết tay trên mẫu in (biên bản giao hàng, biên bản lấy mẫu, bảo hiểm) quyết định chất lượng trích xuất nhưng **không** ảnh hưởng phân loại (tiêu đề là chữ in).
- Mất dấu tiếng Việt không cản trở phân loại (so khớp không dấu) nhưng làm hỏng trích xuất tên riêng.

### 7.7. Dữ liệu và đánh giá

- Tổ chức gán nhãn hai người độc lập trên cả 336 dòng manifest theo `docs/LABELING_GUIDELINE.md`; κ mục tiêu ≥ 0,85; phân xử; lưu nhật ký thay đổi.
- Viết script kiểm tra tệp nhãn theo 7 quy tắc ở mục 9 của hướng dẫn, và script tính κ / đồng thuận theo loại / khớp ranh giới.
- **Thu thập thêm dữ liệu** cho 24 loại `insufficient`, ưu tiên các loại có hạn và chắc chắn có nhiều trong thực tế: `GCN_BAO_HIEM`, `GPLX`, `DANG_KY_PHUONG_TIEN`, `GCN_ATKT_BVMT_PT`, `GP_VC_HANG_NGUY_HIEM`, `GCN_KIEM_DINH_DO_LUONG`, `CC_HUAN_LUYEN_PCCC`, `CC_NGHIEP_VU_BVMT`, `HD_NHUONG_QUYEN_DAI_LY`, `HD_MUON_BON`, `HO_SO_QUAN_LY_PCCC` (mục tiêu ≥ 20 tệp duy nhất mỗi loại, từ nhiều xe/cửa hàng/năm khác nhau để tránh trùng mẫu).

## 8. Pilot: tự gán nhãn theo hướng dẫn

### 8.1. Cách làm

Người thiết kế kết xuất ảnh trang (PyMuPDF → PNG trong thư mục tạm ngoài repo), mở xem và gán nhãn theo đúng quy trình 9 bước của hướng dẫn. Bảng dưới gồm **60 tệp**
thuộc đủ 19 thư mục và 2 tệp ở gốc; 34 loại khác nhau; 11 tệp composite; confidence: 49 high, 8 medium, 3 low.
Ngoài bảng này, khoảng 70 tệp khác được mở xem đầy đủ hoặc gần đầy đủ, và khoảng 70 tệp nữa được xem thu nhỏ các trang từ trang 2 trở đi để dò tài liệu ghép; kết hợp với OCR trang 1, đó là cơ sở của bản gán nhãn tạm cho cả 336 tệp (dùng tính các cột «ước tính»).
Giới hạn: chỉ **một** người gán, nên chưa có số đo đồng thuận; pilot này kiểm tra tính khả thi của hướng dẫn, không thay cho vòng hiệu chỉnh hai người.

| # | `doc_id` | Thư mục cũ | Tệp | Trang | `doc_type` | Comp. | Segments | Conf. | Evidence (tiêu đề) | Ghi chú |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `b25d539d66af` | `10. GCN VC HNH` | `62. GCN VC HNH Huy (12-5-24).pdf` | 2 | `CC_TAP_HUAN_VC_HNH` | 0 |  | high | GIẤY CHỨNG NHẬN HOÀN THÀNH CHƯƠNG TRÌNH TẬP HUẤN VẬN CHUYỂN HÀNG HÓA NGUY HIỂM | tr.1 là bìa, tr.2 là mặt có ảnh |
| 2 | `026a4a2e8c9e` | `8. GCN Lop dao tao van chuyen hang chay no` | `73. GCN vc hàng nguy hiểm-Tình.pdf` | 2 | `CC_TAP_HUAN_VC_HNH` | 0 |  | high | GIẤY CHỨNG NHẬN HOÀN THÀNH CHƯƠNG TRÌNH TẬP HUẤN VẬN CHUYỂN HÀNG HÓA NGUY HIỂM | cùng mẫu với thư mục «10.» |
| 3 | `898572a6f361` | `5. TỔNG HỢP HỒ SƠ XE` | `1. Xe 08001-02645-15.2.24.pdf` | 2 | `BIEN_NHAN_THE_CHAP_PT` | 1 | `1:BIEN_NHAN_THE_CHAP_PT;2:BIEN_NHAN_THE_CHAP_PT` | high | GIẤY BIÊN NHẬN THẾ CHẤP PHƯƠNG TIỆN GIAO THÔNG | 2 giấy cho đầu kéo và rơ moóc |
| 4 | `7bbc9f2bf3ef` | `5. TỔNG HỢP HỒ SƠ XE` | `1b. BHVC 02645 (5-2-24).pdf` | 2 | `GCN_BAO_HIEM` | 0 |  | high | GIẤY CHỨNG NHẬN BẢO HIỂM TỰ NGUYỆN XE Ô TÔ | bảo hiểm vật chất xe |
| 5 | `baebf72f798f` | `5. TỔNG HỢP HỒ SƠ XE` | `BHDS 13420 (2-1-23).pdf` | 2 | `GCN_BAO_HIEM` | 0 |  | high | GIẤY CHỨNG NHẬN BẢO HIỂM BẮT BUỘC TNDS CỦA CHỦ XE Ô TÔ | 2 giấy (bắt buộc + tự nguyện) trên cùng một tờ |
| 6 | `cc3992cb23d7` | `5. TỔNG HỢP HỒ SƠ XE` | `3.2 77R-009.34.pdf` | 2 | `DANG_KY_PHUONG_TIEN` | 0 |  | high | CHỨNG NHẬN ĐĂNG KÝ RƠ MOÓC, SƠ MI RƠ MOÓC | tiêu đề ở tr.2; tr.1 là mặt thông tin |
| 7 | `f59a351ba852` | `5. TỔNG HỢP HỒ SƠ XE` | `72. HA THANH NHAN.pdf` | 2 | `CCCD` | 0 |  | high | CĂN CƯỚC CÔNG DÂN |  |
| 8 | `a76ae560baf3` | `5. TỔNG HỢP HỒ SƠ XE` | `HUYNH VIET NAM-4.11.25.pdf` | 2 | `GPLX` | 0 |  | high | GIẤY PHÉP LÁI XE / DRIVER'S LICENSE |  |
| 9 | `b0a73e00d299` | `5. TỔNG HỢP HỒ SƠ XE` | `Barem 77R- 01926-31.12.22.pdf` | 2 | `GCN_KIEM_DINH_DO_LUONG` | 0 |  | high | GIẤY CHỨNG NHẬN KIỂM ĐỊNH — đối tượng: xi téc ô tô | tr.2 «kết quả kiểm định» không tách |
| 10 | `91d8c499df3b` | `5. TỔNG HỢP HỒ SƠ XE` | `PCCC 09567+00934 (31-5-23).pdf` | 2 | `GP_VC_HANG_NGUY_HIEM` | 0 |  | high | GIẤY PHÉP VẬN CHUYỂN HÀNG HÓA NGUY HIỂM VỀ CHÁY, NỔ | tên tệp gợi ý sai «PCCC» |
| 11 | `33407b90528b` | `5. TỔNG HỢP HỒ SƠ XE` | `Vận tải CP.pdf` | 1 | `GP_KD_VAN_TAI` | 0 |  | high | GIẤY PHÉP KINH DOANH VẬN TẢI BẰNG XE Ô TÔ |  |
| 12 | `aba856a262ef` | `6. CUA HANG - BB MAU- VÂN` | `BB mau CH12-21.pdf` | 93 | `BB_LAY_MAU` | 1 | `1:BB_LAY_MAU;…;93:BB_LAY_MAU` | medium | BIÊN BẢN LẤY MẪU, BÀN GIAO MẪU VÀ KIỂM TRA NIÊM PHONG (Mẫu 2) | 93 trang; đã đọc 10 trang rải đều, chưa đọc hết; 93 segment một trang |
| 13 | `0cf9aa186387` | `6. CUA HANG - BB MAU- VÂN` | `T2_3.pdf` | 3 | `BB_LAY_MAU` | 1 | `1:BB_LAY_MAU;2:BB_LAY_MAU;3:BB_LAY_MAU` | high | BIÊN BẢN LẤY MẪU, BÀN GIAO MẪU VÀ KIỂM TRA NIÊM PHONG (Mẫu 2) | 3 biên bản |
| 14 | `3376b0c936f1` | `6. HOP DONG MUON BON` | `HDMBCD-02.2020-TRUONG HUNG-02.01.2020.pdf` | 6 | `HD_MUON_BON` | 0 |  | high | HỢP ĐỒNG MƯỢN BỒN CHỨA DẦU | kèm biên bản nhận bồn, trả bồn → không tách |
| 15 | `5b84a6c30d75` | `6. HOP DONG THUE KHO- Vi` | `HDMBCD-01.2018-ABS-02.01.2018.pdf` | 6 | `HD_MUON_BON` | 0 |  | high | HỢP ĐỒNG MƯỢN BỒN CHỨA DẦU | thư mục «thuê kho» nhưng là mượn bồn |
| 16 | `6ac314e2f770` | `6. HOP DONG THUE KHO- Vi` | `HDKT-017.2018-CHUONG PHAT-24.09.2018.pdf` | 10 | `HD_MUA_BAN` | 0 |  | medium | HỢP ĐỒNG KINH TẾ (mua bồn inox) + BẢNG BÁO GIÁ | tiêu đề chung chung; quyết định theo Điều 1; bảng báo giá không tách |
| 17 | `36aff038b19e` | `6. HOP DONG THUE KHO- Vi` | `HDB 2017-.pdf` | 4 | `HOA_DON` | 1 | `1-2:HOA_DON;3-4:HOA_DON` | low | HÓA ĐƠN BÁN HÀNG (2 hóa đơn) | scan rất mờ |
| 18 | `7ee3bbfe72eb` | `8. CUA HANG - TU K.TRA PCCC- VÂN` | `CH12-T1+T2.pdf` | 26 | `HO_SO_QUAN_LY_PCCC` | 0 |  | high | HỒ SƠ QUẢN LÝ CÔNG TÁC PHÒNG CHÁY CHỮA CHÁY | 26 trang, 12 tiêu đề con → một tài liệu |
| 19 | `297c0d94ec78` | `TU K.TRA PCCC- VÂN` | `PCCC CH5-22.pdf` | 53 | `HO_SO_QUAN_LY_PCCC` | 0 |  | medium | SỔ THEO DÕI PHƯƠNG TIỆN PHÒNG CHÁY VÀ CHỮA CHÁY | không có bìa hồ sơ; mới xem tr.1 |
| 20 | `7bc2d3c97831` | `9. TỔNG HỢP HỒ SƠ CỬA HÀNG` | `1. GCN ĐK DN (BC).pdf` | 2 | `GCN_DKDN` | 0 |  | high | GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP — CÔNG TY TNHH HAI THÀNH VIÊN TRỞ LÊN |  |
| 21 | `1700fb51ee4b` | `9. TỔNG HỢP HỒ SƠ CỬA HÀNG` | `16. UPSC hóa chất (photo).pdf` | 21 | `BIEN_PHAP_UNG_PHO_SU_CO` | 0 |  | high | BIỆN PHÁP PHÒNG NGỪA, ỨNG PHÓ SỰ CỐ HÓA CHẤT CỦA CỬA HÀNG XĂNG DẦU | 21 trang, có mục lục |
| 22 | `6b14a798c908` | `9. TỔNG HỢP HỒ SƠ CỬA HÀNG` | `36. Bằng BVMT a.Chí (BC-30-1-23).pdf` | 2 | `CC_NGHIEP_VU_BVMT` | 0 |  | high | GIẤY CHỨNG NHẬN ĐÀO TẠO NGHIỆP VỤ BẢO VỆ MÔI TRƯỜNG |  |
| 23 | `bcf218315fa4` | `9. TỔNG HỢP HỒ SƠ CỬA HÀNG` | `36a. BVMT a.Đông (BC-4-4-24)_1.pdf` | 2 | `CC_NGHIEP_VU_BVMT` | 0 |  | high | GIẤY CHỨNG NHẬN — lớp bồi dưỡng nghiệp vụ bảo vệ môi trường trong kinh doanh xăng dầu | tr.1 chỉ là bìa đỏ |
| 24 | `72449aceeff3` | `9. TỔNG HỢP HỒ SƠ CỬA HÀNG` | `MT 2 nhân vien GH3_2.pdf` | 4 | `CC_NGHIEP_VU_BVMT` | 1 | `1-2:CC_NGHIEP_VU_BVMT;3-4:CC_NGHIEP_VU_BVMT` | high | CHỨNG NHẬN — khóa đào tạo nghiệp vụ bảo vệ môi trường (2 người) | 2 chứng nhận của 2 người |
| 25 | `d88b2ec4ccd1` | `9. TỔNG HỢP HỒ SƠ CỬA HÀNG` | `37b. Bằng PCCC Loan (BC-6-6-27).pdf` | 2 | `CC_HUAN_LUYEN_PCCC` | 0 |  | high | CHỨNG NHẬN HUẤN LUYỆN NGHIỆP VỤ PHÒNG CHÁY, CHỮA CHÁY, CỨU NẠN, CỨU HỘ |  |
| 26 | `ed9b06c8b985` | `9. TỔNG HỢP HỒ SƠ CỬA HÀNG` | `4. ATKT  Và BVMT GH1_3.pdf` | 2 | `GCN_ATKT_BVMT_PT` | 0 |  | high | GIẤY CHỨNG NHẬN AN TOÀN KỸ THUẬT VÀ BẢO VỆ MÔI TRƯỜNG PHƯƠNG TIỆN THỦY NỘI ĐỊA | trang xoay 90° |
| 27 | `e386fb0f776e` | `9. TỔNG HỢP HỒ SƠ CỬA HÀNG` | `5. GCN đủ ĐK PCCC (BC)_1.pdf` | 1 | `GCN_PCCC_CO_SO` | 0 |  | high | GIẤY CHỨNG NHẬN ĐỦ ĐIỀU KIỆN VỀ PHÒNG CHÁY VÀ CHỮA CHÁY |  |
| 28 | `2a14bd33fd68` | `9. TỔNG HỢP HỒ SƠ CỬA HÀNG` | `Thẩm duyệt PCCC GH3_4.pdf` | 2 | `GCN_PCCC_CO_SO` | 0 |  | high | GIẤY CHỨNG NHẬN THẨM DUYỆT THIẾT KẾ VỀ PHÒNG CHÁY VÀ CHỮA CHÁY | tr.2 là danh mục bản vẽ → không tách |
| 29 | `0567ee057de3` | `9. TỔNG HỢP HỒ SƠ CỬA HÀNG` | `9. GPXD Ba Phú (BC).pdf` | 2 | `GIAY_PHEP_XAY_DUNG` | 0 |  | high | GIẤY PHÉP XÂY DỰNG — công trình: cửa hàng xăng dầu |  |
| 30 | `3600c9ec3036` | `9. TỔNG HỢP HỒ SƠ CỬA HÀNG` | `Bảo Hiểm GH3 (26-11-2024).pdf` | 3 | `GCN_BAO_HIEM` | 0 |  | medium | GIẤY CHỨNG NHẬN BẢO HIỂM (cháy, nổ bắt buộc) | trang xoay 90°, chữ nhỏ |
| 31 | `cb8636a17725` | `9. TỔNG HỢP HỒ SƠ CỬA HÀNG` | `CamScanner 20-04-24 14.01.pdf` | 1 | `BAN_VE_KY_THUAT` | 0 |  | medium | bản vẽ chi tiết trục lái tàu dầu, không có tiêu đề văn bản | bản nháp đầu gán OTHER → mở loại BAN_VE_KY_THUAT |
| 32 | `6c50528f7f4f` | `9. TỔNG HỢP HỒ SƠ CỬA HÀNG` | `Cột đo ghe 1.pdf` | 3 | `GCN_KIEM_DINH_DO_LUONG` | 1 | `1:GCN_KIEM_DINH_DO_LUONG;…;3:GCN_KIEM_DINH_DO_LUONG` | high | GIẤY CHỨNG NHẬN KIỂM ĐỊNH — đối tượng: cột đo | 3 giấy cho 3 cột đo; 3 segment một trang |
| 33 | `4d9f145f7932` | `9. TỔNG HỢP HỒ SƠ CỬA HÀNG` | `hợp đồng thuê mang zang - hòa khánh.pdf` | 6 | `HD_THUE_TAI_SAN` | 0 |  | high | HỢP ĐỒNG THUÊ TÀI SẢN ĐIỂM, CỬA HÀNG KINH DOANH XĂNG DẦU |  |
| 34 | `ef39bb3714e1` | `_1. Giay DKKD khach hang` | `GPKD-THÀNH LIÊN.pdf` | 7 | `GCN_DKDN` | 0 |  | medium | GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP + CÔNG BỐ NỘI DUNG ĐĂNG KÝ DOANH NGHIỆP | phần công bố 5 trang không tách |
| 35 | `9f0ee68c16ca` | `_1. Giay DKKD khach hang` | `GPKD-AN TIN 2018.pdf` | 2 | `GCN_DKDN` | 0 |  | high | GIẤY CHỨNG NHẬN ĐĂNG KÝ HỢP TÁC XÃ |  |
| 36 | `a76c35cddb4e` | `_1. Giay DKKD khach hang` | `Đăng ký tàu HƯƠNG SƠN 2.pdf` | 2 | `DANG_KY_PHUONG_TIEN` | 0 |  | high | GIẤY CHỨNG NHẬN ĐĂNG KÝ PHƯƠNG TIỆN THỦY NỘI ĐỊA | tr.2 là ảnh tàu; thư mục gợi ý sai |
| 37 | `bfbfb743b8d5` | `_1. HOP DONG DAI LY NHUONG QUYEN` | `NQ-02.2023-LOI HUYNH-01.01.2023-31.12.2025.pdf` | 10 | `HD_NHUONG_QUYEN_DAI_LY` | 0 |  | high | HỢP ĐỒNG NHƯỢNG QUYỀN BÁN LẺ XĂNG DẦU | tr.1 bìa, tr.2 trắng |
| 38 | `55aed65b0c2b` | `_1. HOP DONG DAI LY NHUONG QUYEN` | `GPKD-ANH KHA.pdf` | 1 | `GCN_DKDN` | 0 |  | high | GIẤY CHỨNG NHẬN ĐĂNG KÝ KINH DOANH — DOANH NGHIỆP TƯ NHÂN | thư mục gợi ý sai |
| 39 | `8cf960f4632e` | `_1. HOP DONG DAI LY NHUONG QUYEN` | `DDK-HOANG MINH-15.12.24.pdf` | 2 | `GCN_DDK_BAN_LE_XD` | 0 |  | medium | GIẤY CHỨNG NHẬN CỬA HÀNG ĐỦ ĐIỀU KIỆN BÁN LẺ XĂNG DẦU | ảnh chụp nghiêng, mờ |
| 40 | `547141773252` | `_2. Giay Du Dieu Kien Khach hang` | `DDK-CHIN LOAN-12.1.28.pdf` | 3 | `GCN_DDK_BAN_LE_XD` | 0 |  | high | GIẤY CHỨNG NHẬN CỬA HÀNG ĐỦ ĐIỀU KIỆN BÁN LẺ XĂNG DẦU | tr.3 «những điều quy định» không tách |
| 41 | `4a2298c0dea7` | `_2. Giay Du Dieu Kien Khach hang` | `DDK-SAU LIEM-21.6.23.pdf` | 1 | `GCN_DDK_BAN_LE_XD` | 0 |  | low | GIẤY CHỨNG NHẬN CỬA HÀNG ĐỦ ĐIỀU KIỆN BÁN LẺ XĂNG DẦU (đọc được một phần) | scan rất tối |
| 42 | `4da3d98d6227` | `_2. HOP DONG KINH TE` | `HDKT 2021-DEO CA-10.7.pdf` | 3 | `HD_MUA_BAN` | 0 |  | high | HỢP ĐỒNG MUA BÁN HÀNG HÓA | tên tệp «HDKT» |
| 43 | `8af369ea50f5` | `_2. HOP DONG KINH TE` | `lắp máy vn ( 31-12-2024).pdf` | 4 | `HD_MUA_BAN` | 0 |  | high | HỢP ĐỒNG NGUYÊN TẮC MUA BÁN XĂNG DẦU |  |
| 44 | `8c0b35ee9ef4` | `_3. HOP DONG DAU VAO-Diem` | `QĐKV3 2024.pdf` | 8 | `HD_MUA_BAN` | 0 |  | high | HỢP ĐỒNG THƯƠNG NHÂN PHÂN PHỐI XĂNG DẦU | công ty là bên mua → cùng loại với «hợp đồng kinh tế» |
| 45 | `deab4d6d4713` | `_3. HOP DONG DAU VAO-Diem` | `83-TNĐM-QĐ-BCT Giấy XN Đủ điều kiện làm thươn…` | 2 | `GXN_THUONG_NHAN_XD` | 0 |  | high | GIẤY XÁC NHẬN ĐỦ ĐIỀU KIỆN LÀM THƯƠNG NHÂN ĐẦU MỐI KINH DOANH XĂNG DẦU |  |
| 46 | `b8b72c553653` | `_3. HOP DONG DAU VAO-Diem` | `GIAY UY QUYEN PETROLIMEX.pdf` | 2 | `GIAY_UY_QUYEN` | 0 |  | high | GIẤY ỦY QUYỀN |  |
| 47 | `9b62bdcd0bcc` | `_3. HOP DONG DAU VAO-Diem` | `TB thay đổi người đại diện.pdf` | 1 | `CONG_VAN_THONG_BAO` | 0 |  | high | THÔNG BÁO V/v thay đổi người đại diện theo pháp luật | bản nháp đầu gán OTHER → mở loại CONG_VAN_THONG_BAO |
| 48 | `e8cfd1798742` | `_3. HOP DONG DAU VAO-Diem` | `L2609…_Thỏa thuận chung (đã ký số).pdf` | 30 | `OTHER` | 0 |  | high | THỎA THUẬN CHUNG về việc cấp và sử dụng tín dụng | ngoài danh mục; xem câu hỏi mở |
| 49 | `aa096e12e4cf` | `_3. HOP DONG DAU VAO-Diem` | `THANH LÝ HĐ THUÊ KHO - HK.pdf` | 1 | `BB_THANH_LY_HD` | 0 |  | high | BIÊN BẢN THANH LÝ HỢP ĐỒNG THUÊ KHO CHỨA XĂNG DẦU |  |
| 50 | `87c88bf6d0f1` | `_4. THANH LÝ HỢP ĐỒNG` | `TLHD 11.20-SU DOAN 31.pdf` | 5 | `BB_GIAO_NHAN_HANG_HOA` | 1 | `1-2:BB_GIAO_NHAN_HANG_HOA;3-5:BB_THANH_LY_HD` | medium | BIÊN BẢN NGHIỆM THU, BÀN GIAO HÀNG HÓA (tr.1); THANH LÝ HỢP ĐỒNG KINH TẾ (tr.3) | nhãn chính theo segment đầu, trái với tên thư mục |
| 51 | `dc3847632556` | `_4. THANH LÝ HỢP ĐỒNG` | `TLHD 2021-TU HUE.pdf` | 1 | `BB_THANH_LY_HD` | 0 |  | low | BIÊN BẢN THANH LÝ HỢP ĐỒNG (đọc được một phần) | scan rất mờ |
| 52 | `57374da27cae` | `_5. HOP DONG VAN CHUYEN` | `HDVC 2020-TOAN THINH-01.01-31.12.pdf` | 4 | `HD_VAN_CHUYEN` | 1 | `1-2:HD_VAN_CHUYEN;3-4:GCN_DKDN` | high | HỢP ĐỒNG VẬN CHUYỂN HÀNG HÓA | kèm giấy đăng ký doanh nghiệp của đối tác |
| 53 | `2829275a2ce5` | `_5. HOP DONG VAN CHUYEN` | `HDVC 2020-CHU LAI-01.12.19-31.12.20.pdf` | 4 | `HD_VAN_CHUYEN` | 0 |  | high | HỢP ĐỒNG VẬN CHUYỂN | mẫu của đối tác, công ty là bên vận chuyển |
| 54 | `83f88be6530c` | `_Biên bản giao nhận 2026` | `bbgn-260528-6.pdf` | 2 | `BB_GIAO_NHAN_HANG_HOA` | 1 | `1:BB_GIAO_NHAN_HANG_HOA;2:BB_GIAO_NHAN_HANG_HOA` | high | BIÊN BẢN GIAO HÀNG | 2 biên bản (2 mặt hàng, 2 xe) |
| 55 | `3b84aa09975d` | `_Biên bản giao nhận 2026` | `bbgn-260102-3.pdf` | 1 | `BB_GIAO_NHAN_HANG_HOA` | 0 |  | high | BIÊN BẢN GIAO HÀNG |  |
| 56 | `9c00a14eed6b` | `_PHIẾU XUẤT KHO MUA HÀNG 2026` | `20260109-04.pdf` | 4 | `PHIEU_XUAT_KHO` | 1 | `1:PHIEU_XUAT_KHO;2:BB_GIAO_NHAN_HANG_HOA;3:BB_LAY_MAU;4:CHUNG_THU_CHAT_LUONG` | high | PHIẾU XUẤT KHO THÀNH PHẨM | bộ 4 chứng từ |
| 57 | `01af575b5ff4` | `_PHIẾU XUẤT KHO MUA HÀNG 2026` | `20260127-03.pdf` | 2 | `PHIEU_XUAT_KHO` | 0 |  | high | PHIẾU XUẤT KHO THÀNH PHẨM | 2 trang 1/2, 2/2 → một tài liệu |
| 58 | `053ebee54c42` | `_Đơn đặt hàng - mua vào 2026` | `don-hang_2605-0041.pdf` | 1 | `DON_DAT_HANG` | 0 |  | high | ĐƠN ĐẶT HÀNG | có phần xác nhận của nhà cung cấp |
| 59 | `9f4c4dae0c73` | `(gốc, không nhãn)` | `BSR-2629763-HH 10-06-2026 20-10-37.pdf` | 5 | `PHIEU_XUAT_KHO` | 1 | `1-2:PHIEU_XUAT_KHO;3:CHUNG_THU_CHAT_LUONG;4:BB_GIAO_NHAN_HANG_HOA;5:BB_LAY_MAU` | high | PHIẾU XUẤT KHO THÀNH PHẨM | bộ 4 chứng từ |
| 60 | `03baaeec961e` | `(gốc, không nhãn)` | `Quy che dan tem Thue - 2016-11-01.pdf` | 9 | `CONG_VAN_THONG_BAO` | 0 |  | high | QUYẾT ĐỊNH ban hành Quy chế hoạt động của Ban chỉ đạo dán tem niêm phong cột đo xăng dầu | quyết định + quy chế = một tài liệu |

### 8.2. Chỗ hướng dẫn mơ hồ và cách đã sửa

| # | Tình huống gặp trong pilot | Vì sao bản nháp mơ hồ | Cách sửa (đã đưa vào hướng dẫn và JSON) |
|---|---|---|---|
| 1 | Hợp đồng mượn bồn có thêm trang «BIÊN BẢN NHẬN BỒN», «BIÊN BẢN TRẢ BỒN» (ít nhất 5/9 tệp) | Bản nháp: «trang có tiêu đề + khối chữ ký riêng là tài liệu mới» → gần hết lớp `HD_MUON_BON` thành composite và bị loại khỏi benchmark; trong khi biên bản trả bồn có bản còn để trống ngày, tức là biểu mẫu ký sẵn đi kèm hợp đồng | **Phép thử kèm theo**: chỉ tách khi đoạn đó, đứng riêng, là một loại khác hoặc một bản khác. Biên bản nhận/trả bồn thuộc `HD_MUON_BON`; ngày nhận/trả là trường trích xuất |
| 2 | Giấy đăng ký doanh nghiệp kèm «Giấy xác nhận về việc thay đổi nội dung đăng ký doanh nghiệp» / «Công bố nội dung đăng ký» (3 tệp, tới 7 trang); giấy đủ điều kiện bán lẻ kèm «Những điều quy định» | Các trang này có tiêu đề, số, dấu riêng | Cùng phép thử: cùng loại, cùng chủ thể → không tách. Liệt kê tường minh trong danh sách «không tách» |
| 3 | Tập hồ sơ PCCC 26–53 trang chứa quyết định, kế hoạch, báo cáo, 2–12 biên bản tự kiểm tra | Mỗi thành phần trông như một văn bản độc lập; «quyết định», «kế hoạch» còn trùng với `CONG_VAN_THONG_BAO` | Quy tắc **«tập có bìa chung»**: cả tập là một `HO_SO_QUAN_LY_PCCC`; mô tả lớp `CONG_VAN_THONG_BAO` loại trừ văn bản nằm trong tập này |
| 4 | Tệp 2 trang = 2 giấy biên nhận thế chấp cho 2 xe; tệp 4 trang = chứng nhận của 2 người; tệp 93 trang = 93 biên bản lấy mẫu | «Composite» ban đầu chỉ nghĩ tới khác loại; nếu coi là một tài liệu thì trích xuất mất bản ghi, nếu coi là composite thì mất mẫu phân loại | Tách khái niệm composite **cùng loại** (vẫn ở benchmark phân loại) và **khác loại** (ra khỏi benchmark); thêm công thức sinh chuỗi `segments` cho tệp dài |
| 5 | «TLHD 11.20-SU DOAN 31»: biên bản nghiệm thu bàn giao (tr.1–2) + thanh lý (tr.3–4) + bảng xác định khối lượng (tr.5), nằm trong thư mục thanh lý | Không rõ nhãn chính là tài liệu «quan trọng nhất» hay tài liệu đầu tiên; bảng tr.5 là tài liệu gì | Nhãn chính = **segment đầu tiên** (máy kiểm tra được, khớp với thứ bộ phân loại trang 1 nhìn thấy); bảng xác định khối lượng đứng riêng chỉ là `OTHER` và đi kèm bản thanh lý → gộp vào segment thanh lý |
| 6 | 4 tệp «CamScanner» là bản vẽ tàu; 1 thông báo đổi người đại diện; 1 quyết định ban hành quy chế | Bản nháp dồn cả vào `OTHER`, làm `OTHER` thành một lớp 7 tệp không liên quan gì tới nhau | Mở loại `BAN_VE_KY_THUAT` (nhận biết bằng hình, không cần tiêu đề) và `CONG_VAN_THONG_BAO`; `OTHER` chỉ còn 1 tệp (thỏa thuận tín dụng) |
| 7 | Tờ bảo hiểm in cả giấy bắt buộc TNDS và giấy tự nguyện trên một trang; trang 1 của phiếu xuất kho chụp gộp hai trang giấy | `segments` tính theo trang nên không tách được hai giấy trên một trang | Quy định **đơn vị segment là trang**; hai giấy trên một trang thuộc một segment, ghi `note` |

Các quan sát khác đã thành quy tắc: không gán nhãn theo tên tệp/thư mục (11 kiểu tên gây hiểu nhầm, phụ lục 12 của hướng dẫn); phải xem mọi trang vì trang 1 có thể là bìa; bản quét xấu nhưng đọc được thì gán loại với `confidence=low` chứ không dùng `UNREADABLE`.

### 8.3. Kiểm tra nhanh tính tách được bằng từ khóa tiêu đề

Chạy cổng luật hiện có (`CascadedClassifier.match_rules`, 1500 ký tự đầu) với `keywords` của taxonomy v2 trên văn bản OCR **trang 1** của `data/baseline_ocr_335.jsonl`, so với bản gán nhãn tạm, trên 302 tệp duy nhất có trong tệp OCR:

| Quy tắc quyết định | Đúng | Mơ hồ (≥ 2 lớp khớp) | Không khớp | Sai |
|---|---|---|---|---|
| Hiện tại: chỉ quyết định khi đúng một lớp khớp | 247 (81,8%) | 30 | 25 | 0 |
| Thử nghiệm ngoài repo: từ khóa xuất hiện sớm nhất thắng, `rule_priority` phá hòa | 277 (91,7%) | — | 25 | 0 |

**Đọc kết quả thận trọng**: từ khóa đã được chỉnh sau khi nhìn chính dữ liệu này và «đáp án» là nhãn tạm của một người, nên các con số **lạc quan** và không phải kết quả benchmark.
Điều đáng tin là hướng: với nhãn theo nội dung, tiêu đề đủ để quyết định phần lớn tài liệu và không có lớp nào bị nhầm hệ thống; 25 tệp không khớp là do OCR hỏng tiêu đề, bìa thẻ không có chữ, hoặc bản vẽ.
30 tệp mơ hồ gồm 14 đơn đặt hàng (nhắc «hợp đồng mua bán xăng dầu số…»), 8 biên bản thanh lý (nhắc tên hợp đồng gốc), 6 hợp đồng vận chuyển (nhắc «giấy xác nhận… thương nhân phân phối», «giấy ủy quyền»), 2 tệp khác.

## 9. Câu hỏi mở cho chủ nghiệp vụ của công ty

**Về danh mục loại tài liệu**

1. Công ty có **danh mục chuẩn của hồ sơ cửa hàng và hồ sơ xe** không? Tên tệp trong hồ sơ cửa hàng được đánh số tới 38 («1. GCN ĐK DN», «4. ATKT và BVMT», «5. GCN đủ ĐK PCCC», «9. GPXD», «16. UPSC hóa chất», «36. Bằng BVMT», «37b. Bằng PCCC»…), cho thấy có một danh mục dài hơn nhiều so với 12 loại thấy trong mẫu (ví dụ giấy chứng nhận quyền sử dụng đất, giấy xác nhận đăng ký môi trường, đăng kiểm xe cơ giới, phù hiệu xe). Xin danh mục đó để bổ sung loại còn thiếu.
2. **Hóa đơn**, **thỏa thuận/hợp đồng tín dụng ngân hàng**, **bảng báo giá**, **công văn/thông báo/quy chế** có thuộc phạm vi hệ thống không? Nếu có thì lưu ở đâu?
3. Chứng nhận huấn luyện PCCC và chứng nhận nghiệp vụ bảo vệ môi trường của nhân viên: cần theo dõi **riêng từng loại** (đang thiết kế như vậy) hay gộp thành «chứng chỉ nghiệp vụ nhân viên cửa hàng»?
4. Bản vẽ kỹ thuật (4 tệp quét rời từng tờ): có cần lưu như tài liệu riêng không, hay chỉ là phụ lục của giấy thẩm duyệt PCCC?

**Về nơi lưu (định tuyến)**

5. Hai cặp thư mục cùng nội dung — «8. GCN Lop dao tao…» / «10. GCN VC HNH» và «8. CUA HANG - TU K.TRA PCCC» / «TU K.TRA PCCC»: thư mục nào là chính, hay đó là của hai bộ phận khác nhau?
6. «6. HOP DONG THUE KHO- Vi» không có hợp đồng thuê kho nào. Hợp đồng thuê kho thật nằm ở đâu? Các hợp đồng mượn bồn ở đây là lưu nhầm hay cố ý? Hợp đồng **mua** bồn/xe lưu ở đâu?
7. Giấy đăng ký doanh nghiệp và giấy đủ điều kiện bán lẻ của khách hàng nhượng quyền đang có ở **cả hai** nơi (hồ sơ giấy phép khách hàng và hồ sơ hợp đồng nhượng quyền). Hệ thống nên lưu một bản và liên kết, hay sao ra hai nơi?
8. Hợp đồng vận chuyển: có cần tách «công ty đi thuê vận chuyển» (2 hợp đồng năm 2026 đang nằm ở thư mục đầu vào) với «công ty vận chuyển cho khách» không?
9. Bộ chứng từ một chuyến hàng mua vào (phiếu xuất kho + chứng thư chất lượng + biên bản giao nhận + biên bản lấy mẫu): lưu **nguyên bộ** theo chuyến hay tách từng loại? ERP cần số nào từ mỗi chứng từ?
10. Giấy phép kinh doanh vận tải (cấp cho công ty, không theo xe) có đúng là lưu trong hồ sơ xe không?

**Về trích xuất và hạn**

11. Những **ngày hết hạn** nào cần nhắc, nhắc trước bao lâu, nhắc cho ai? (Bảng ở mục 7.5 liệt kê 21 trường.) Với chứng nhận huấn luyện PCCC không ghi hạn trên thẻ, dùng quy định nào để tính?
12. **Dữ liệu cá nhân**: có được trích và lưu vào ERP số căn cước, số giấy phép lái xe, ngày sinh không? Ai được xem? Thời hạn lưu?
13. Tập «tự kiểm tra PCCC»: ERP cần **ngày của từng biên bản tự kiểm tra hằng tháng**, hay chỉ cần biết tập của cửa hàng nào, kỳ nào đã nộp?
14. Biên bản lấy mẫu (một tệp tới 93 biên bản): ERP cần **từng biên bản** thành một bản ghi (số niêm phong, biển số, ngày), hay chỉ lưu trữ theo cửa hàng/kỳ?
15. Hợp đồng mượn bồn: «biên bản trả bồn» có cần thành sự kiện riêng (bồn đã thu hồi) không? Một số biên bản trả bồn được ký sẵn nhưng để trống ngày — hiểu thế nào?
16. Quy ước **tên tệp**: ngày trong tên («-12.1.28», «(31-12-2024)», «BC-12-5-24») có phải luôn là ngày hết hạn không? «BC», «GOC», «photo» nghĩa là gì (bản chính / bản công chứng / bản chụp)? Hệ thống có cần ghi nhận thuộc tính bản chính/bản sao không?
17. Danh mục chủ dữ liệu: ERP có sẵn danh sách **khách hàng, nhà cung cấp, cửa hàng/ghe, xe, lái xe** kèm mã số thuế/biển số để bộ định tuyến tra cứu không? Những pháp nhân nào được coi là «công ty mình» (công ty mẹ, chi nhánh, cửa hàng hạch toán phụ thuộc)?

## 10. Giới hạn và những điều chưa chắc

- **Số đếm là ước tính của một người.** Bản gán nhãn tạm cho 336 tệp dựa trên OCR trang 1 (mất dấu, dính chữ) cộng với việc mở xem ảnh khoảng 130 tệp (60 tệp trong bảng pilot được đọc kỹ) và dò trang sau của khoảng 70 tệp nữa. Khoảng 100 tệp còn lại — thuộc các thư mục thuần một mẫu (thẻ tập huấn, đơn đặt hàng, biên bản giao hàng, phiếu xuất kho một trang) — được gán theo tiêu đề OCR và mẫu chung, **chưa mở ảnh từng tệp**. Có thể còn sai sót hoặc composite chưa phát hiện trong số đó.
- **Ngưỡng 10 tệp** cho `ok` là quy ước. `HD_MUON_BON` (9) và `HO_SO_QUAN_LY_PCCC` (8) nằm sát ngưỡng; cả hai đều rất đồng mẫu nên số mẫu «độc lập» thực tế còn ít hơn.
- **Ranh giới «kèm theo / tài liệu riêng»** là lựa chọn thiết kế, không phải sự thật khách quan. Lựa chọn hiện tại ưu tiên cách doanh nghiệp dùng hồ sơ (một bộ hợp đồng mượn bồn, một bộ đăng ký doanh nghiệp). Nếu câu trả lời cho câu hỏi 13–15 khác đi thì phải đổi quy tắc và gán lại các loại liên quan.
- **Nhãn chính = segment đầu tiên** làm «TLHD 11.20» mang nhãn `BB_GIAO_NHAN_HANG_HOA` dù doanh nghiệp coi đó là hồ sơ thanh lý. Chấp nhận được vì tệp composite khác loại không nằm trong benchmark một nhãn và khi vận hành mỗi segment được định tuyến riêng.
- **`CONG_VAN_THONG_BAO` và `OTHER` là lớp rộng**, mới có 2 và 1 tệp; định nghĩa của chúng sẽ phải siết lại khi có thêm dữ liệu.
- **Từ khóa** được chỉnh trên chính 302 tệp dùng để kiểm tra (mục 8.3); chưa có tập kiểm tra độc lập. Một số từ khóa là «tiêu đề + dòng phụ» (ví dụ «giấy chứng nhận đăng ký doanh nghiệp công ty») để tránh khớp nhầm câu nhắc trong thân hợp đồng — phụ thuộc thứ tự dòng của OCR.
- **Định tuyến** suy từ 336 tệp mẫu do một vài nhân viên lưu (một số tên thư mục gắn tên người phụ trách); thói quen lưu của bộ phận khác có thể khác. 3 quy tắc ở trạng thái «giả định/cần hỏi».
- **Tài liệu pháp lý chỉ được nhận dạng về hình thức.** Tên gọi văn bản và thời hạn hiệu lực theo quy định hiện hành (ví dụ thời hạn của chứng nhận huấn luyện PCCC, tên cơ quan sau sắp xếp bộ máy) cần người am hiểu nghiệp vụ xác nhận.

## 11. Kiểm tra hợp lệ của sản phẩm

Chạy từ gốc repo. Đoạn mã kiểm tra: JSON nạp được; `id` không trùng; mọi `group`, `confusable_with`, `routing[].doc_types`, `legacy_folder_map[].maps_to` trỏ tới mục có thật;
mỗi thư mục cũ thuộc nhiều nhất một lớp; mọi mã viết trong dấu `…` hoặc trong chuỗi segments của hướng dẫn và của báo cáo này đều là `id` lớp/nhóm có thật (`UNKNOWN` là nhãn từ chối của bộ phân loại, `DOC_TYPE` là chữ giữ chỗ), và mọi lớp đều có mục mô tả trong hướng dẫn.

```powershell
.venv\Scripts\python.exe -X utf8 -c "
import json, re, collections
t = json.load(open('data/taxonomy_v2.json', encoding='utf-8'))
ids = [c['id'] for c in t['classes']]; S = set(ids)
assert t['version'] == '2.0' and len(ids) == len(S)
G = {g['id'] for g in t['groups']}
need = {'id','name_vi','group','description','keywords','confusable_with','key_fields','legacy_folders','est_count','data_status'}
lf = collections.Counter()
for c in t['classes']:
    assert need <= set(c), c['id']; assert c['group'] in G
    assert set(c['confusable_with']) <= S and c['id'] not in c['confusable_with'], c['id']
    assert c['data_status'] in ('ok', 'insufficient')
    assert all(set(f) == {'name','desc','is_expiry'} for f in c['key_fields'])
    lf.update(c['legacy_folders'])
assert max(lf.values()) == 1
for r in t['routing']: assert set(r['doc_types']) <= S, r['id']
for m in t['legacy_folder_map']: assert m['maps_to'] in S | {None} and set(m['contains']) <= S
for name in ('docs/LABELING_GUIDELINE.md', 'teams/00_data_and_eval/reports/02_taxonomy_design.md'):
    g = open(name, encoding='utf-8').read()
    used = set(re.findall(r'\x60([A-Z][A-Z0-9_]{2,})\x60', g)) | set(re.findall(r'\d:([A-Z][A-Z0-9_]+)', g))
    assert used <= S | G | {'DOC_TYPE', 'UNKNOWN'}, (name, used - S - G)
    if 'GUIDELINE' in name: assert S <= used, S - used
print('OK', len(ids), 'classes;', len(t['routing']), 'routing rules')
"
.venv\Scripts\python.exe -X utf8 -m pytest tests/test_taxonomy.py tests/test_classifier.py -q
```

Kết quả tại thời điểm viết báo cáo: `OK 36 classes; 25 routing rules`, và các test hiện có của bộ nạp taxonomy/bộ phân loại vẫn qua.
