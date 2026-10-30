# Bộ mẫu đã phân loại theo taxonomy v2

> Thư mục này được **sinh tự động** bởi `scripts/build_classified_folder.py` từ `data/labels_v2.csv`.
> Đừng sửa tay ở đây: sửa nhãn trong `data/labels_v2.csv` (hoặc `teams/00_data_and_eval/annotation/adjudication.csv`) rồi chạy lại script.

## Cách đọc

- `<NHÓM>/<LOẠI>/tệp.pdf`: loại tài liệu xác định theo **nội dung** (tiêu đề, cơ quan ban hành, bố cục), không theo nơi công ty lưu hồ sơ.
  Định nghĩa từng loại: `docs/LABELING_GUIDELINE.md`; danh mục máy đọc được: `data/taxonomy_v2.json`.
- `_COMPOSITE_KHAC_LOAI/`: một tệp PDF chứa nhiều tài liệu **khác loại**. Dải trang của từng phần nằm ở cột `segments` trong `INDEX.csv`. Dùng làm chuẩn cho bài toán tách tài liệu, không dùng cho bài phân loại đơn nhãn.
- `_CAN_KIEM_TRA/<LOẠI>/`: nhãn đề xuất nhưng chưa đủ chắc, cần người phụ trách hồ sơ của công ty xem lại.
- `INDEX.csv`: một dòng mỗi tài liệu — `doc_id`, đường dẫn mới, loại, số trang, tệp ghép hay không, trạng thái duyệt, căn cứ gán nhãn, và **mọi** đường dẫn gốc trong `docs/_chot_samples_phanloaitailieu/` (bản trùng byte đã gộp làm một).

## Trạng thái nhãn

Nhãn do hai annotator là mô hình AI gán độc lập (một bên xem ảnh trang, một bên đọc văn bản chép lại) rồi đối chiếu; **chưa có người của công ty duyệt**.
Cột `review_status`: `agreed` = hai bên trùng nhau; `check_composite` = hai bên trùng loại nhưng chỉ một bên (bên xem đủ trang) ghi nhận tệp ghép; `check_low_conf` = bên đọc văn bản không tự tin; `adjudicated` = hai bên khác nhau, nhãn do phân xử.

| review_status | số tài liệu |
|---|---|
| agreed | 296 |
| check_composite | 5 |
| check_low_conf | 3 |

Tổng: **304 tài liệu duy nhất** (từ 336 tệp gốc), trong đó 8 tệp ghép khác loại và 3 tệp cần kiểm tra.

## Số tài liệu theo loại (không tính hai thư mục đặc biệt)

| Nhóm | Mã loại | Tên loại | Số tài liệu | Dữ liệu |
|---|---|---|---|---|
| Hợp đồng và thanh lý hợp đồng | `HD_MUA_BAN` | Hợp đồng mua bán hàng hóa / xăng dầu | 32 | đủ để huấn luyện/đánh giá |
| Hợp đồng và thanh lý hợp đồng | `HD_NHUONG_QUYEN_DAI_LY` | Hợp đồng nhượng quyền bán lẻ / đại lý xăng dầu | 5 | THIẾU — cần thu thập thêm |
| Hợp đồng và thanh lý hợp đồng | `HD_VAN_CHUYEN` | Hợp đồng vận chuyển hàng hóa | 25 | đủ để huấn luyện/đánh giá |
| Hợp đồng và thanh lý hợp đồng | `HD_MUON_BON` | Hợp đồng mượn bồn chứa dầu (kèm biên bản nhận bồn, trả bồn) | 9 | THIẾU — cần thu thập thêm |
| Hợp đồng và thanh lý hợp đồng | `HD_THUE_TAI_SAN` | Hợp đồng thuê kho / cửa hàng / tài sản | 1 | THIẾU — cần thu thập thêm |
| Hợp đồng và thanh lý hợp đồng | `BB_THANH_LY_HD` | Biên bản thanh lý hợp đồng | 14 | đủ để huấn luyện/đánh giá |
| Giấy phép, chứng nhận pháp lý của doanh nghiệp/cơ sở | `GCN_DKDN` | Giấy chứng nhận đăng ký doanh nghiệp / kinh doanh / hợp tác xã / chi nhánh | 34 | đủ để huấn luyện/đánh giá |
| Giấy phép, chứng nhận pháp lý của doanh nghiệp/cơ sở | `GCN_DDK_BAN_LE_XD` | Giấy chứng nhận cửa hàng đủ điều kiện bán lẻ xăng dầu | 27 | đủ để huấn luyện/đánh giá |
| Giấy phép, chứng nhận pháp lý của doanh nghiệp/cơ sở | `GXN_THUONG_NHAN_XD` | Giấy xác nhận đủ điều kiện làm thương nhân đầu mối / phân phối / đại lý xăng dầu | 2 | THIẾU — cần thu thập thêm |
| Giấy phép, chứng nhận pháp lý của doanh nghiệp/cơ sở | `GP_KD_VAN_TAI` | Giấy phép kinh doanh vận tải bằng xe ô tô | 1 | THIẾU — cần thu thập thêm |
| Giấy phép, chứng nhận pháp lý của doanh nghiệp/cơ sở | `GIAY_PHEP_XAY_DUNG` | Giấy phép xây dựng công trình (cửa hàng xăng dầu) | 1 | THIẾU — cần thu thập thêm |
| Chứng chỉ và giấy tờ cá nhân | `CC_TAP_HUAN_VC_HNH` | Giấy chứng nhận hoàn thành chương trình tập huấn vận chuyển hàng hóa nguy hiểm | 24 | đủ để huấn luyện/đánh giá |
| Chứng chỉ và giấy tờ cá nhân | `CC_HUAN_LUYEN_PCCC` | Chứng nhận huấn luyện nghiệp vụ PCCC và cứu nạn, cứu hộ | 3 | THIẾU — cần thu thập thêm |
| Chứng chỉ và giấy tờ cá nhân | `CC_NGHIEP_VU_BVMT` | Giấy chứng nhận đào tạo/bồi dưỡng nghiệp vụ bảo vệ môi trường trong kinh doanh xăng dầu | 6 | THIẾU — cần thu thập thêm |
| Chứng chỉ và giấy tờ cá nhân | `GPLX` | Giấy phép lái xe | 5 | THIẾU — cần thu thập thêm |
| Chứng chỉ và giấy tờ cá nhân | `CCCD` | Căn cước công dân / chứng minh nhân dân | 1 | THIẾU — cần thu thập thêm |
| Hồ sơ phương tiện và thiết bị | `DANG_KY_PHUONG_TIEN` | Chứng nhận đăng ký xe ô tô / rơ moóc / phương tiện thủy nội địa | 3 | THIẾU — cần thu thập thêm |
| Hồ sơ phương tiện và thiết bị | `BIEN_NHAN_THE_CHAP_PT` | Giấy biên nhận thế chấp phương tiện giao thông (ngân hàng cấp) | 2 | THIẾU — cần thu thập thêm |
| Hồ sơ phương tiện và thiết bị | `GCN_ATKT_BVMT_PT` | Giấy chứng nhận an toàn kỹ thuật và bảo vệ môi trường của phương tiện (đăng kiểm) | 1 | THIẾU — cần thu thập thêm |
| Hồ sơ phương tiện và thiết bị | `GCN_KIEM_DINH_DO_LUONG` | Giấy chứng nhận kiểm định phương tiện đo (cột đo xăng dầu, xi téc ô tô) | 2 | THIẾU — cần thu thập thêm |
| Hồ sơ phương tiện và thiết bị | `GP_VC_HANG_NGUY_HIEM` | Giấy phép vận chuyển hàng hóa nguy hiểm (về cháy, nổ) | 2 | THIẾU — cần thu thập thêm |
| Hồ sơ PCCC, an toàn, môi trường của cơ sở | `GCN_PCCC_CO_SO` | Giấy chứng nhận đủ điều kiện / thẩm duyệt thiết kế về PCCC của cơ sở, phương tiện | 3 | THIẾU — cần thu thập thêm |
| Hồ sơ PCCC, an toàn, môi trường của cơ sở | `HO_SO_QUAN_LY_PCCC` | Hồ sơ quản lý, theo dõi công tác PCCC của cơ sở (kèm biên bản tự kiểm tra PCCC) | 7 | THIẾU — cần thu thập thêm |
| Hồ sơ PCCC, an toàn, môi trường của cơ sở | `BIEN_PHAP_UNG_PHO_SU_CO` | Biện pháp / kế hoạch phòng ngừa, ứng phó sự cố (hóa chất, tràn dầu), phương án chữa cháy | 1 | THIẾU — cần thu thập thêm |
| Hồ sơ PCCC, an toàn, môi trường của cơ sở | `BAN_VE_KY_THUAT` | Bản vẽ kỹ thuật / thiết kế | 4 | THIẾU — cần thu thập thêm |
| Bảo hiểm | `GCN_BAO_HIEM` | Giấy chứng nhận bảo hiểm (xe cơ giới, cháy nổ, tàu thuyền) | 7 | THIẾU — cần thu thập thêm |
| Chứng từ mua bán, giao nhận hàng hóa | `DON_DAT_HANG` | Đơn đặt hàng | 20 | đủ để huấn luyện/đánh giá |
| Chứng từ mua bán, giao nhận hàng hóa | `PHIEU_XUAT_KHO` | Phiếu xuất kho | 15 | đủ để huấn luyện/đánh giá |
| Chứng từ mua bán, giao nhận hàng hóa | `BB_GIAO_NHAN_HANG_HOA` | Biên bản giao nhận / giao hàng / nghiệm thu bàn giao hàng hóa | 20 | đủ để huấn luyện/đánh giá |
| Chứng từ mua bán, giao nhận hàng hóa | `BB_LAY_MAU` | Biên bản lấy mẫu, niêm phong, bàn giao mẫu xăng dầu | 9 | THIẾU — cần thu thập thêm |
| Chứng từ mua bán, giao nhận hàng hóa | `HOA_DON` | Hóa đơn bán hàng / hóa đơn giá trị gia tăng | 1 | THIẾU — cần thu thập thêm |
| Văn bản hành chính và loại khác | `GIAY_UY_QUYEN` | Giấy ủy quyền | 3 | THIẾU — cần thu thập thêm |
| Văn bản hành chính và loại khác | `CONG_VAN_THONG_BAO` | Công văn / thông báo / quyết định / quy chế (văn bản hành chính) | 2 | THIẾU — cần thu thập thêm |
| Văn bản hành chính và loại khác | `OTHER` | Tài liệu khác (đọc được nhưng không thuộc loại nào trong danh mục) | 1 | THIẾU — cần thu thập thêm |

Loại có trong taxonomy nhưng chưa có tệp đơn nào trong bộ mẫu: `CHUNG_THU_CHAT_LUONG`, `UNREADABLE`.
