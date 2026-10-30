# Hướng dẫn gán nhãn loại tài liệu (taxonomy v2)

> Phiên bản 1.1 (2026-10-11, xem nhật ký mục 11) — đi kèm `data/taxonomy_v2.json` (version 2.0). Người đọc: sinh viên gán nhãn và nhân viên văn phòng.
> Mọi mã loại (`doc_type`) trong tài liệu này phải trùng với `classes[].id` trong tệp JSON; nếu hai nơi khác nhau thì tệp JSON là chuẩn.
> Tài liệu mẫu là hồ sơ nội bộ của doanh nghiệp: chỉ mở trên máy nội bộ, không tự ý tải lên dịch vụ bên ngoài (ngoại lệ duy nhất: chủ dự án đã đồng ý cho gửi riêng bộ mẫu nghiên cứu này tới LLM bên ngoài để tạo dữ liệu tham chiếu như bản chép và nhãn; hệ thống chạy thật vẫn phải on-premise), không chép số giấy tờ cá nhân, số điện thoại, số tài khoản vào tệp nhãn.

## 1. Mục đích

Hệ thống cần biết mỗi tệp PDF là **loại tài liệu gì** để (1) chọn đúng mẫu trích xuất trường dữ liệu, (2) theo dõi ngày hết hạn, (3) lưu vào đúng hồ sơ.
Trước đây nhãn là **tên thư mục** nơi công ty cất tệp. Cách đó sai vì thư mục là «tủ hồ sơ» (hồ sơ khách hàng, hồ sơ xe, hồ sơ cửa hàng…), không phải loại tài liệu:
cùng một tệp nằm ở hai thư mục, và một thư mục chứa hơn mười loại giấy tờ khác nhau (xem `teams/00_data_and_eval/reports/02_taxonomy_design.md`).

Việc của bạn: với mỗi dòng trong `data/manifest.csv` (336 tệp), mở tệp và ghi **loại tài liệu theo nội dung** của nó.

## 2. Năm nguyên tắc

1. **Nhìn nội dung, không nhìn tên.** Không suy ra nhãn từ tên thư mục hay tên tệp. Tên tệp «GPKD-…» là giấy đăng ký doanh nghiệp; «HDKT…» là hợp đồng mua bán;
   «PCCC 09567+00934» là giấy phép vận chuyển hàng nguy hiểm; «CamScanner…» có thể là bất cứ thứ gì.
2. **Xem hết các trang.** Trang 1 có thể chỉ là bìa thẻ, bìa hợp đồng, hoặc là tài liệu đầu của một bộ nhiều tài liệu.
3. **Một tài liệu logic = một nhãn.** Tệp chứa nhiều tài liệu độc lập thì đánh dấu `is_composite=1` và ghi từng đoạn trang (mục 7).
4. **Nơi lưu không phải là nhãn.** Hợp đồng mua bán là `HD_MUA_BAN` dù công ty là bên mua («đầu vào») hay bên bán. Giấy đăng ký doanh nghiệp là `GCN_DKDN`
   dù của khách hàng, của nhà cung cấp hay của cửa hàng.
5. **Không chắc thì nói là không chắc.** Dùng `confidence` và `note`; không đoán bừa để cho xong (mục 8).

## 3. Chuẩn bị

- Mở tệp theo cột `relative_path` của `data/manifest.csv`, tính từ `docs/_chot_samples_phanloaitailieu/`. Chỉ đọc; không đổi tên, không di chuyển, không sửa tệp.
- Dùng trình đọc PDF có chế độ xem thu nhỏ nhiều trang (thumbnail) để nhìn nhanh toàn bộ tệp, rồi phóng to trang cần đọc.
- **Số trang trong cột `segments` đếm từ 1** (trang đầu tiên là trang 1), đúng như trình đọc PDF hiển thị. (Lưu ý: bộ gold OCR của Nhóm 1 đếm từ 0 — đừng nhầm.)
- Hai người gán nhãn làm **độc lập**: không xem tệp nhãn của nhau, không trao đổi về từng tệp cho tới bước đối chiếu (mục 10).
- Nếu bạn **không xem được hết các trang** của một tệp (ví dụ chỉ có văn bản của 2 trang đầu), làm theo mục 8.1 — đừng đoán phần chưa xem.

## 4. Quy trình quyết định

Làm lần lượt các bước sau cho mỗi tệp.

1. **Lướt toàn bộ tệp.** Mở chế độ thu nhỏ, đếm số trang, xem có trang trắng, trang xoay ngang, bìa hay không.
2. **Có đọc được không?** Nếu sau khi phóng to vẫn không trang nào đủ rõ để biết đây là gì → `doc_type=UNREADABLE`, kết thúc.
   Bản quét xấu nhưng vẫn nhận ra được loại → tiếp tục, ghi `confidence=low` hoặc `medium`.
3. **Tệp có phải một «tập có bìa chung» không?** Tập hồ sơ quản lý PCCC, tài liệu biện pháp ứng phó sự cố (có bìa, mục lục, sổ kẻ bảng liên tục) là **một** tài liệu
   dù bên trong có nhiều tiêu đề con. Nếu đúng → coi cả tệp là một tài liệu, sang bước 5.
4. **Tìm ranh giới tài liệu.** Đánh dấu những trang «mở đầu một tài liệu mới»: có quốc hiệu/tên đơn vị + **tiêu đề mới** ở phần trên trang, hoặc là một thẻ/giấy của người khác,
   xe khác, số/ngày khác. Với mỗi trang như vậy, làm **phép thử kèm theo** (mục 7.2) để quyết định nó mở segment mới hay chỉ là phần kèm theo của tài liệu trước.
   Kết quả: tệp có 1 tài liệu (`is_composite=0`) hoặc từ 2 tài liệu trở lên (`is_composite=1`).
5. **Xác định loại của từng tài liệu** theo đúng thứ tự ưu tiên sau, dừng ngay khi đủ căn cứ:
   1. **Tiêu đề**: dòng chữ in hoa, đậm, nằm giữa ở 1/3 trên của trang đầu tài liệu (với thẻ: dòng chữ lớn trên bìa hoặc mặt có ảnh). Tra bảng ở mục 5.
   2. **Cơ quan/đơn vị ban hành**: góc trên bên trái và con dấu. Sở Công Thương ≠ Phòng Đăng ký kinh doanh ≠ Công an PCCC ≠ cơ quan đăng kiểm ≠ trung tâm đo lường ≠ ngân hàng ≠ công ty bảo hiểm.
   3. **Bố cục**: thẻ nhỏ có ảnh chân dung; mẫu in sẵn điền tay; văn bản có Bên A/Bên B và điều khoản; bảng chỉ tiêu thử nghiệm; bản vẽ; sổ kẻ bảng.
   4. **Nội dung chính** (Điều 1, dòng «Căn cứ…», dòng «V/v…») khi tiêu đề chung chung như «HỢP ĐỒNG KINH TẾ», «GIẤY CHỨNG NHẬN», «BIÊN BẢN».
6. **Đối chiếu mục «Dễ nhầm với»** của loại vừa chọn (mục 6). Nếu dấu hiệu quyết định chỉ sang loại khác thì đổi.
7. **Không khớp loại nào** dù đã đọc được tiêu đề → `OTHER`, chép tiêu đề vào `evidence`.
8. **Ghi kết quả**: `doc_type` (với tệp composite: loại của segment đầu tiên), `is_composite`, `segments`, `confidence`, `evidence`, `note` (mục 9).
9. **Tự kiểm 10 giây**: nhãn có dựa vào tên tệp không? Đã xem trang cuối chưa? `segments` có phủ hết số trang không?

### 4.1. Quy tắc ưu tiên bổ sung (v1.1)

Các quy tắc dưới đây **không đổi định nghĩa loại nào**; chúng ghi lại cách hiểu mà người gán nhãn đã phản hồi là còn thiếu. Khi có mâu thuẫn với cảm giác «tài liệu này thuộc về ai / nói về việc gì», các quy tắc này thắng.

1. **Tiêu đề thắng tên và ngành nghề của bên ký kết.** Tên công ty, ngành nghề hay địa chỉ của các bên (ví dụ bên ký là một công ty vận tải, một công ty cho thuê, một đại lý) không quyết định loại. Loại do tiêu đề và Điều 1 quyết định (bước 5.1 và 5.4). Hợp đồng mua bán ký với công ty vận tải vẫn là `HD_MUA_BAN`.
2. **«HỢP ĐỒNG KINH TẾ» mua bán tài sản, thiết bị là `HD_MUA_BAN`** (mục 6.1): mua bồn, mua xe, mua thiết bị — vì nội dung chính là mua bán có giá và đợt thanh toán. Không chuyển sang `HD_MUON_BON` hay `HD_THUE_TAI_SAN` chỉ vì đối tượng mua là bồn hoặc kho.
3. **«Biên bản thanh lý» thắng loại hợp đồng gốc** (mục 6.6): `BB_THANH_LY_HD` áp dụng cho mọi hợp đồng gốc — mua bán, đại lý, nhượng quyền, thuê kho, vận chuyển. Không gán theo loại hợp đồng gốc.
4. **Loại giấy tờ theo tiêu đề, không theo người được cấp.** Chứng chỉ của người **ngoài công ty** (lái xe thuê ngoài, nhân sự đơn vị khác) vẫn là loại ghi trên tiêu đề, ví dụ `CC_TAP_HUAN_VC_HNH` (mục 6.12).
5. **Giấy không có tiêu đề rõ — dấu hiệu được chấp nhận thay tiêu đề:** thẻ/tờ bảo hiểm có «Số GCNBH» (cùng logo và thời hạn bảo hiểm) → `GCN_BAO_HIEM`; thẻ có «Tên chủ xe (Owner's full name)», biển số, số khung, số máy → `DANG_KY_PHUONG_TIEN`. Ghi dấu hiệu đó vào `evidence` và đặt `confidence=medium`.
6. **Thứ tự trang của thẻ và giấy gập không quan trọng.** Bìa trước hay mặt trong đứng trước đều là cùng một tài liệu; không dùng thứ tự trang để suy ra có tài liệu thứ hai.
7. **Cửa hàng nổi cũng là cơ sở.** Ghe, tàu bán xăng dầu (cửa hàng trên phương tiện thủy) vẫn dùng `GCN_DDK_BAN_LE_XD` cho giấy đủ điều kiện bán lẻ và `GCN_PCCC_CO_SO` cho giấy PCCC của cơ sở/phương tiện đó.

## 5. Bảng tra nhanh: tiêu đề → loại

Nhóm cấp 1 (`group`) chỉ để báo cáo; bạn chỉ cần ghi `doc_type`. Cột «Dữ liệu» cho biết loại đã đủ mẫu (`ok`) hay còn thiếu (`insufficient`) — không ảnh hưởng tới cách gán nhãn.

| Nhóm | `doc_type` | Tên loại | Cụm tiêu đề thường gặp | Dữ liệu |
|---|---|---|---|---|
| Hợp đồng và thanh lý hợp đồng | `HD_MUA_BAN` | Hợp đồng mua bán hàng hóa / xăng dầu | «hợp đồng mua bán hàng hóa»; «hợp đồng mua bán xăng dầu»; «hợp đồng nguyên tắc mua bán xăng dầu» | ok (32) |
| Hợp đồng và thanh lý hợp đồng | `HD_NHUONG_QUYEN_DAI_LY` | Hợp đồng nhượng quyền bán lẻ / đại lý xăng dầu | «hợp đồng nhượng quyền bán lẻ xăng dầu»; «hợp đồng nhượng quyền thương mại»; «hợp đồng đại lý bán lẻ xăng dầu» | insufficient (5) |
| Hợp đồng và thanh lý hợp đồng | `HD_VAN_CHUYEN` | Hợp đồng vận chuyển hàng hóa | «hợp đồng vận chuyển hàng hóa»; «hợp đồng vận chuyển»; «hợp đồng thuê vận chuyển» | ok (26) |
| Hợp đồng và thanh lý hợp đồng | `HD_MUON_BON` | Hợp đồng mượn bồn chứa dầu (kèm biên bản nhận bồn, trả bồn) | «hợp đồng mượn bồn chứa dầu»; «hợp đồng mượn bồn»; «biên bản nhận bồn» | insufficient (9) |
| Hợp đồng và thanh lý hợp đồng | `HD_THUE_TAI_SAN` | Hợp đồng thuê kho / cửa hàng / tài sản | «hợp đồng thuê tài sản»; «hợp đồng thuê kho»; «hợp đồng thuê cửa hàng» | insufficient (1) |
| Hợp đồng và thanh lý hợp đồng | `BB_THANH_LY_HD` | Biên bản thanh lý hợp đồng | «biên bản thanh lý hợp đồng»; «thanh lý hợp đồng» | ok (14) |
| Giấy phép, chứng nhận pháp lý của doanh nghiệp/cơ sở | `GCN_DKDN` | Giấy chứng nhận đăng ký doanh nghiệp / kinh doanh / hợp tác xã / chi nhánh | «giấy chứng nhận đăng ký doanh nghiệp công ty»; «giấy chứng nhận đăng ký doanh nghiệp doanh nghiệp tư nhân»; «giấy chứng nhận đăng ký kinh doanh doanh nghiệp tư nhân» | ok (35) |
| Giấy phép, chứng nhận pháp lý của doanh nghiệp/cơ sở | `GCN_DDK_BAN_LE_XD` | Giấy chứng nhận cửa hàng đủ điều kiện bán lẻ xăng dầu | «giấy chứng nhận cửa hàng đủ điều kiện bán lẻ xăng dầu»; «cửa hàng đủ điều kiện bán lẻ xăng dầu»; «giấy chứng nhận đủ điều kiện kinh doanh xăng dầu» | ok (27) |
| Giấy phép, chứng nhận pháp lý của doanh nghiệp/cơ sở | `GXN_THUONG_NHAN_XD` | Giấy xác nhận đủ điều kiện làm thương nhân đầu mối / phân phối / đại lý xăng dầu | «giấy xác nhận đủ điều kiện làm thương nhân đầu mối»; «giấy xác nhận đủ điều kiện làm thương nhân phân phối xăng dầu»; «giấy xác nhận đủ điều kiện làm thương nhân phân phối» | insufficient (2) |
| Giấy phép, chứng nhận pháp lý của doanh nghiệp/cơ sở | `GP_KD_VAN_TAI` | Giấy phép kinh doanh vận tải bằng xe ô tô | «giấy phép kinh doanh vận tải bằng xe ô tô»; «giấy phép kinh doanh vận tải» | insufficient (1) |
| Giấy phép, chứng nhận pháp lý của doanh nghiệp/cơ sở | `GIAY_PHEP_XAY_DUNG` | Giấy phép xây dựng công trình (cửa hàng xăng dầu) | «giấy phép xây dựng»; «cấp phép xây dựng công trình» | insufficient (1) |
| Chứng chỉ và giấy tờ cá nhân | `CC_TAP_HUAN_VC_HNH` | Giấy chứng nhận hoàn thành chương trình tập huấn vận chuyển hàng hóa nguy hiểm | «giấy chứng nhận hoàn thành chương trình tập huấn vận chuyển hàng hóa nguy hiểm»; «tập huấn vận chuyển hàng hóa nguy hiểm»; «hoàn thành chương trình tập huấn» | ok (24) |
| Chứng chỉ và giấy tờ cá nhân | `CC_HUAN_LUYEN_PCCC` | Chứng nhận huấn luyện nghiệp vụ PCCC và cứu nạn, cứu hộ | «chứng nhận huấn luyện nghiệp vụ phòng cháy, chữa cháy, cứu nạn, cứu hộ»; «chứng nhận huấn luyện nghiệp vụ phòng cháy»; «huấn luyện nghiệp vụ phòng cháy, chữa cháy» | insufficient (3) |
| Chứng chỉ và giấy tờ cá nhân | `CC_NGHIEP_VU_BVMT` | Giấy chứng nhận đào tạo/bồi dưỡng nghiệp vụ bảo vệ môi trường trong kinh doanh xăng dầu | «giấy chứng nhận đào tạo nghiệp vụ bảo vệ môi trường»; «nghiệp vụ bảo vệ môi trường»; «bảo vệ môi trường trong kinh doanh xăng dầu» | insufficient (6) |
| Chứng chỉ và giấy tờ cá nhân | `GPLX` | Giấy phép lái xe | «giấy phép lái xe»; «driver's license»; «driving license» | insufficient (5) |
| Chứng chỉ và giấy tờ cá nhân | `CCCD` | Căn cước công dân / chứng minh nhân dân | «căn cước công dân / citizen identity card»; «citizen identity card»; «giấy chứng minh nhân dân» | insufficient (1) |
| Hồ sơ phương tiện và thiết bị | `DANG_KY_PHUONG_TIEN` | Chứng nhận đăng ký xe ô tô / rơ moóc / phương tiện thủy nội địa | «chứng nhận đăng ký xe ô tô»; «chứng nhận đăng ký rơ moóc, sơ mi rơ moóc»; «giấy chứng nhận đăng ký phương tiện thủy nội địa» | insufficient (3) |
| Hồ sơ phương tiện và thiết bị | `BIEN_NHAN_THE_CHAP_PT` | Giấy biên nhận thế chấp phương tiện giao thông (ngân hàng cấp) | «giấy biên nhận thế chấp phương tiện giao thông»; «giấy biên nhận thế chấp»; «biên nhận thế chấp» | insufficient (2) |
| Hồ sơ phương tiện và thiết bị | `GCN_ATKT_BVMT_PT` | Giấy chứng nhận an toàn kỹ thuật và bảo vệ môi trường của phương tiện (đăng kiểm) | «giấy chứng nhận an toàn kỹ thuật và bảo vệ môi trường»; «an toàn kỹ thuật và bảo vệ môi trường phương tiện thủy nội địa»; «kiểm định an toàn kỹ thuật và bảo vệ môi trường phương tiện giao thông cơ giới đường bộ» | insufficient (1) |
| Hồ sơ phương tiện và thiết bị | `GCN_KIEM_DINH_DO_LUONG` | Giấy chứng nhận kiểm định phương tiện đo (cột đo xăng dầu, xi téc ô tô) | «giấy chứng nhận kiểm định»; «certificate of verification»; «kết quả kiểm định» | insufficient (2) |
| Hồ sơ phương tiện và thiết bị | `GP_VC_HANG_NGUY_HIEM` | Giấy phép vận chuyển hàng hóa nguy hiểm (về cháy, nổ) | «giấy phép vận chuyển hàng hóa nguy hiểm về cháy, nổ»; «giấy phép vận chuyển hàng hóa nguy hiểm»; «giấy phép vận chuyển hàng nguy hiểm» | insufficient (2) |
| Hồ sơ PCCC, an toàn, môi trường của cơ sở | `GCN_PCCC_CO_SO` | Giấy chứng nhận đủ điều kiện / thẩm duyệt thiết kế về PCCC của cơ sở, phương tiện | «giấy chứng nhận đủ điều kiện về phòng cháy và chữa cháy»; «đủ điều kiện về phòng cháy và chữa cháy»; «giấy chứng nhận thẩm duyệt thiết kế về phòng cháy và chữa cháy» | insufficient (3) |
| Hồ sơ PCCC, an toàn, môi trường của cơ sở | `HO_SO_QUAN_LY_PCCC` | Hồ sơ quản lý, theo dõi công tác PCCC của cơ sở (kèm biên bản tự kiểm tra PCCC) | «hồ sơ quản lý công tác phòng cháy chữa cháy»; «sổ theo dõi phương tiện phòng cháy và chữa cháy»; «biên bản tự kiểm tra công tác phòng cháy chữa cháy» | insufficient (8) |
| Hồ sơ PCCC, an toàn, môi trường của cơ sở | `BIEN_PHAP_UNG_PHO_SU_CO` | Biện pháp / kế hoạch phòng ngừa, ứng phó sự cố (hóa chất, tràn dầu), phương án chữa cháy | «biện pháp phòng ngừa, ứng phó sự cố hóa chất»; «phòng ngừa, ứng phó sự cố hóa chất»; «kế hoạch ứng phó sự cố tràn dầu» | insufficient (1) |
| Hồ sơ PCCC, an toàn, môi trường của cơ sở | `BAN_VE_KY_THUAT` | Bản vẽ kỹ thuật / thiết kế | «bản vẽ thiết kế»; «bản vẽ kỹ thuật»; «mặt cắt» | insufficient (4) |
| Bảo hiểm | `GCN_BAO_HIEM` | Giấy chứng nhận bảo hiểm (xe cơ giới, cháy nổ, tàu thuyền) | «giấy chứng nhận bảo hiểm»; «bảo hiểm bắt buộc tnds»; «bảo hiểm bắt buộc trách nhiệm dân sự» | insufficient (7) |
| Chứng từ mua bán, giao nhận hàng hóa | `DON_DAT_HANG` | Đơn đặt hàng | «đơn đặt hàng» | ok (20) |
| Chứng từ mua bán, giao nhận hàng hóa | `PHIEU_XUAT_KHO` | Phiếu xuất kho | «phiếu xuất kho thành phẩm»; «phiếu xuất kho»; «xuất kho thành phẩm» | ok (21) |
| Chứng từ mua bán, giao nhận hàng hóa | `BB_GIAO_NHAN_HANG_HOA` | Biên bản giao nhận / giao hàng / nghiệm thu bàn giao hàng hóa | «biên bản giao hàng»; «biên bản giao nhận hàng»; «biên bản giao nhận» | ok (21) |
| Chứng từ mua bán, giao nhận hàng hóa | `BB_LAY_MAU` | Biên bản lấy mẫu, niêm phong, bàn giao mẫu xăng dầu | «biên bản lấy mẫu»; «bàn giao mẫu và kiểm tra niêm phong»; «niêm phong, bàn giao mẫu» | ok (10) |
| Chứng từ mua bán, giao nhận hàng hóa | `CHUNG_THU_CHAT_LUONG` | Chứng thư chất lượng (Certificate of Quality) | «chứng thư chất lượng (certificate of quality)»; «certificate of quality»; «phiếu kết quả thử nghiệm» | insufficient (0) |
| Chứng từ mua bán, giao nhận hàng hóa | `HOA_DON` | Hóa đơn bán hàng / hóa đơn giá trị gia tăng | «hóa đơn giá trị gia tăng»; «hóa đơn bán hàng»; «hóa đơn gtgt» | insufficient (1) |
| Văn bản hành chính và loại khác | `GIAY_UY_QUYEN` | Giấy ủy quyền | «giấy ủy quyền»; «bên được ủy quyền»; «người được ủy quyền» | insufficient (3) |
| Văn bản hành chính và loại khác | `CONG_VAN_THONG_BAO` | Công văn / thông báo / quyết định / quy chế (văn bản hành chính) | «thông báo v/v»; «quyết định ban hành»; «quy chế hoạt động» | insufficient (2) |
| Văn bản hành chính và loại khác | `OTHER` | Tài liệu khác (đọc được nhưng không thuộc loại nào trong danh mục) | — | insufficient (1) |
| Văn bản hành chính và loại khác | `UNREADABLE` | Không đọc được | — | insufficient (0) |

Số trong ngoặc là số tệp duy nhất trong kho mẫu theo `data/labels_v2.csv`, tính cả tệp composite theo nhãn chính (nhãn do mô hình gán, chưa có người của công ty duyệt — chưa phải gold).

## 6. Mô tả từng loại

Mỗi mục gồm: định nghĩa (cũng là tiêu chí đưa cho mô hình), cụm tiêu đề, cách phân biệt với loại dễ nhầm, ví dụ tệp trong kho mẫu (đường dẫn tính từ `docs/_chot_samples_phanloaitailieu/`).

### Nhóm Hợp đồng và thanh lý hợp đồng (`HOP_DONG`)

#### 6.1. `HD_MUA_BAN` — Hợp đồng mua bán hàng hóa / xăng dầu

- **Định nghĩa.** Hợp đồng trong đó một bên bán và một bên mua hàng hóa (chủ yếu là xăng dầu, dầu nhờn; cũng có thể là tài sản, thiết bị như bồn chứa, xe bồn), kể cả hợp đồng nguyên tắc, hợp đồng kinh tế và hợp đồng thương nhân phân phối xăng dầu. Tiêu đề in hoa ở đầu trang 1 thường là «HỢP ĐỒNG MUA BÁN HÀNG HÓA», «HỢP ĐỒNG MUA BÁN XĂNG DẦU», «HỢP ĐỒNG NGUYÊN TẮC MUA BÁN XĂNG DẦU», «HỢP ĐỒNG THƯƠNG NHÂN PHÂN PHỐI XĂNG DẦU» hoặc «HỢP ĐỒNG KINH TẾ»; thân văn bản có số hợp đồng, căn cứ pháp luật, thông tin Bên A/Bên B (bên bán, bên mua), các điều khoản về mặt hàng, số lượng, giá, giao nhận, thanh toán, công nợ, và chữ ký cùng con dấu của hai bên ở trang cuối. Không chọn loại này nếu nội dung chính là nhượng quyền hay đại lý bán lẻ, vận chuyển thuê, mượn bồn, thuê kho/cửa hàng, cấp tín dụng, hoặc nếu văn bản là biên bản thanh lý một hợp đồng.
- **Cụm tiêu đề nhận biết.** «hợp đồng mua bán hàng hóa»; «hợp đồng mua bán xăng dầu»; «hợp đồng nguyên tắc mua bán xăng dầu»; «hợp đồng thương nhân phân phối xăng dầu»; «hợp đồng kinh tế».
- **Dễ nhầm với** `HD_NHUONG_QUYEN_DAI_LY`, `HD_VAN_CHUYEN`, `BB_THANH_LY_HD`, `HD_MUON_BON`. Đọc đúng dòng tiêu đề và Điều 1: có mặt hàng + giá/số lượng mua bán → HD_MUA_BAN. Có «nhượng quyền», «đại lý» trong tiêu đề → HD_NHUONG_QUYEN_DAI_LY. Có «vận chuyển» và cước → HD_VAN_CHUYEN. Tiêu đề bắt đầu bằng «biên bản thanh lý»/«thanh lý» → BB_THANH_LY_HD (dù trong thân có nhắc số hợp đồng mua bán). Hợp đồng «kinh tế» mà nội dung là mua bồn/xe → vẫn HD_MUA_BAN.
- **Lưu ý khi gán.** Không phân biệt «đầu vào» hay «đầu ra»: công ty đứng bên mua hay bên bán đều là HD_MUA_BAN (vai trò là trường trích xuất, dùng để định tuyến). Hợp đồng + phụ lục/bảng báo giá của chính nó = một tài liệu.
- **Quy tắc ưu tiên (v1.1).** Tiêu đề «HỢP ĐỒNG KINH TẾ» mà Điều 1 là mua bán bồn, xe, thiết bị → `HD_MUA_BAN` (mục 4.1, quy tắc 2). Tên hay ngành nghề của bên ký kết không đổi loại (mục 4.1, quy tắc 1).
- **Có ngày hết hạn cần theo dõi** (trường `hieu_luc_den`) — thông tin cho nhóm trích xuất; không ảnh hưởng cách gán nhãn.
- **Ví dụ.** `_2. HOP DONG KINH TE/HDKT 2021-DEO CA-10.7.pdf`; `_2. HOP DONG KINH TE/lắp máy vn ( 31-12-2024).pdf`; `_3. HOP DONG DAU VAO-Diem/QĐKV3 2024.pdf`.

#### 6.2. `HD_NHUONG_QUYEN_DAI_LY` — Hợp đồng nhượng quyền bán lẻ / đại lý xăng dầu

- **Định nghĩa.** Hợp đồng giữa thương nhân phân phối (bên nhượng quyền hoặc bên giao đại lý) và chủ cửa hàng xăng dầu (bên nhận nhượng quyền hoặc bên đại lý), cho phép cửa hàng bán lẻ xăng dầu dưới thương hiệu, biển hiệu của bên nhượng quyền. Tiêu đề thường là «HỢP ĐỒNG NHƯỢNG QUYỀN BÁN LẺ XĂNG DẦU», «HỢP ĐỒNG NHƯỢNG QUYỀN THƯƠNG MẠI» hoặc «HỢP ĐỒNG ĐẠI LÝ (BÁN LẺ/TIÊU THỤ) XĂNG DẦU»; thường dài khoảng 8–10 trang, có trang bìa in logo, dòng «GIỮA BÊN NHƯỢNG QUYỀN … VÀ BÊN NHẬN NHƯỢNG QUYỀN …», các điều khoản về hình thức nhượng quyền, biển hiệu, nguồn hàng, thời hạn hợp đồng. Không chọn loại này cho hợp đồng mua bán thông thường không có nội dung nhượng quyền/đại lý, và không chọn cho biên bản thanh lý hợp đồng nhượng quyền.
- **Cụm tiêu đề nhận biết.** «hợp đồng nhượng quyền bán lẻ xăng dầu»; «hợp đồng nhượng quyền thương mại»; «hợp đồng đại lý bán lẻ xăng dầu»; «hợp đồng đại lý tiêu thụ xăng dầu»; «bên nhận nhượng quyền».
- **Dễ nhầm với** `HD_MUA_BAN`, `BB_THANH_LY_HD`, `GCN_DDK_BAN_LE_XD`. Tiêu đề có chữ «nhượng quyền» hoặc «đại lý» và có hai bên ký → loại này. Chỉ nhắc «nhượng quyền» ở dòng «Căn cứ hợp đồng…» dưới tiêu đề «biên bản thanh lý» → BB_THANH_LY_HD. Giấy do Sở Công Thương cấp cho cửa hàng → GCN_DDK_BAN_LE_XD.
- **Lưu ý khi gán.** Trang 1 thường là bìa (logo + tên hợp đồng), trang 2 trắng, tiêu đề lặp lại ở trang 3 — vẫn là một tài liệu.
- **Có ngày hết hạn cần theo dõi** (trường `hieu_luc_den`) — thông tin cho nhóm trích xuất; không ảnh hưởng cách gán nhãn.
- **Ví dụ.** `_1. HOP DONG DAI LY NHUONG QUYEN/NQ-02.2023-LOI HUYNH-01.01.2023-31.12.2025.pdf`; `_1. HOP DONG DAI LY NHUONG QUYEN/NĂM THIẾT (31-12-2026).pdf`.

#### 6.3. `HD_VAN_CHUYEN` — Hợp đồng vận chuyển hàng hóa

- **Định nghĩa.** Hợp đồng dịch vụ vận chuyển hàng hóa (xăng dầu) giữa bên chủ hàng (bên thuê vận chuyển) và bên vận chuyển (bên vận tải). Tiêu đề thường là «HỢP ĐỒNG VẬN CHUYỂN HÀNG HÓA» hoặc «HỢP ĐỒNG VẬN CHUYỂN»; trong thân có ghi chú «(BÊN CHỦ HÀNG)» và «(BÊN VẬN CHUYỂN)» sau tên hai bên, các điều khoản về tuyến đường, giao nhận, hao hụt, giá cước và phương thức thanh toán, trách nhiệm hai bên; thường 2–6 trang, có chữ ký và con dấu hai bên. Không chọn loại này cho giấy phép vận chuyển hàng nguy hiểm do cơ quan công an cấp, cho giấy chứng nhận tập huấn của lái xe, hay cho hợp đồng mua bán có kèm điều khoản giao hàng.
- **Cụm tiêu đề nhận biết.** «hợp đồng vận chuyển hàng hóa»; «hợp đồng vận chuyển»; «hợp đồng thuê vận chuyển».
- **Dễ nhầm với** `HD_MUA_BAN`, `GP_VC_HANG_NGUY_HIEM`, `BB_THANH_LY_HD`. Có hai bên ký và có giá cước → hợp đồng vận chuyển. Do Phòng Cảnh sát PCCC cấp, có «Thời hạn của giấy phép» → GP_VC_HANG_NGUY_HIEM. Giá bán theo lít/m3 và mặt hàng → HD_MUA_BAN.
- **Lưu ý khi gán.** Công ty là bên chủ hàng (thuê vận chuyển) hay bên vận chuyển đều cùng loại này.
- **Có ngày hết hạn cần theo dõi** (trường `hieu_luc_den`) — thông tin cho nhóm trích xuất; không ảnh hưởng cách gán nhãn.
- **Ví dụ.** `_5. HOP DONG VAN CHUYEN/HDVC 2020-CHU LAI-01.12.19-31.12.20.pdf`; `_5. HOP DONG VAN CHUYEN/DƯƠNG ĐÔNG KH (VC) (31-12-2024) .pdf`; `_3. HOP DONG DAU VAO-Diem/HĐ VẬN CHUYỂN SƠN LỘC.pdf`.

#### 6.4. `HD_MUON_BON` — Hợp đồng mượn bồn chứa dầu (kèm biên bản nhận bồn, trả bồn)

- **Định nghĩa.** Hợp đồng trong đó công ty cho khách hàng mượn bồn (bể) chứa dầu để chứa hàng do công ty cung cấp. Tiêu đề là «HỢP ĐỒNG MƯỢN BỒN CHỨA DẦU»; số hợp đồng thường có ký hiệu «HĐMB»; nội dung nêu số lượng bồn, dung tích, tình trạng, trách nhiệm bảo quản và hoàn trả. Trong cùng tệp thường có thêm các trang rất ngắn «BIÊN BẢN NHẬN BỒN» và «BIÊN BẢN TRẢ BỒN» của chính hợp đồng đó: các trang này là phần kèm theo của hợp đồng mượn bồn, không phải tài liệu riêng. Một biên bản nhận bồn hoặc trả bồn đứng riêng cũng xếp vào loại này. Không chọn loại này cho hợp đồng thuê kho/cửa hàng có trả tiền thuê hay cho hợp đồng mua bồn.
- **Cụm tiêu đề nhận biết.** «hợp đồng mượn bồn chứa dầu»; «hợp đồng mượn bồn»; «biên bản nhận bồn»; «biên bản trả bồn».
- **Dễ nhầm với** `HD_THUE_TAI_SAN`, `HD_MUA_BAN`. «Mượn» và không có tiền thuê → HD_MUON_BON. Có giá thuê theo tháng/năm → HD_THUE_TAI_SAN. Mua đứt bồn (có tổng giá trị, đợt thanh toán) → HD_MUA_BAN. Tên thư mục cũ «THUE KHO» không phải căn cứ: 4/6 tệp trong đó là hợp đồng mượn bồn.
- **Lưu ý khi gán.** «Biên bản nhận bồn», «Biên bản trả bồn» của chính hợp đồng đó là phần kèm theo: KHÔNG tách segment, is_composite=0.
- **Có ngày hết hạn cần theo dõi** (trường `hieu_luc_den`) — thông tin cho nhóm trích xuất; không ảnh hưởng cách gán nhãn.
- **Ví dụ.** `6. HOP DONG MUON BON/HDMBCD-02.2020-TRUONG HUNG-02.01.2020.pdf`; `6. HOP DONG MUON BON/HDMB 2022-BAO TRAN-8.1.pdf`; `6. HOP DONG THUE KHO- Vi/HDMBCD-01.2018-ABS-02.01.2018.pdf` (tệp thứ ba nằm trong thư mục «THUE KHO» nhưng là hợp đồng mượn bồn).

#### 6.5. `HD_THUE_TAI_SAN` — Hợp đồng thuê kho / cửa hàng / tài sản

- **Định nghĩa.** Hợp đồng thuê hoặc cho thuê tài sản có trả tiền thuê: kho chứa xăng dầu, điểm/cửa hàng kinh doanh xăng dầu, mặt bằng, phương tiện. Tiêu đề thường là «HỢP ĐỒNG THUÊ TÀI SẢN», «HỢP ĐỒNG THUÊ KHO (CHỨA XĂNG DẦU)», «HỢP ĐỒNG THUÊ CỬA HÀNG», «HỢP ĐỒNG THUÊ MẶT BẰNG»; có «BÊN CHO THUÊ» và «BÊN THUÊ», mô tả tài sản thuê, thời hạn thuê, giá thuê và phương thức thanh toán. Không chọn loại này cho hợp đồng mượn bồn (không có tiền thuê), hợp đồng thuê vận chuyển, hay biên bản thanh lý hợp đồng thuê.
- **Cụm tiêu đề nhận biết.** «hợp đồng thuê tài sản»; «hợp đồng thuê kho»; «hợp đồng thuê cửa hàng»; «hợp đồng thuê mặt bằng»; «hợp đồng cho thuê».
- **Dễ nhầm với** `HD_MUON_BON`, `BB_THANH_LY_HD`, `HD_VAN_CHUYEN`. Có «bên cho thuê/bên thuê» và giá thuê → loại này. «Thuê vận chuyển» → HD_VAN_CHUYEN. «Biên bản thanh lý hợp đồng thuê kho» → BB_THANH_LY_HD.
- **Có ngày hết hạn cần theo dõi** (trường `thoi_han_thue_den`) — thông tin cho nhóm trích xuất; không ảnh hưởng cách gán nhãn.
- **Ví dụ.** `9. TỔNG HỢP HỒ SƠ CỬA HÀNG/hợp đồng thuê mang zang - hòa khánh.pdf`.

#### 6.6. `BB_THANH_LY_HD` — Biên bản thanh lý hợp đồng

- **Định nghĩa.** Biên bản hai bên xác nhận chấm dứt, quyết toán một hợp đồng đã ký. Tiêu đề là «BIÊN BẢN THANH LÝ HỢP ĐỒNG», «THANH LÝ HỢP ĐỒNG KINH TẾ», «BIÊN BẢN THANH LÝ HỢP ĐỒNG NHƯỢNG QUYỀN THƯƠNG MẠI», «BIÊN BẢN THANH LÝ HỢP ĐỒNG THUÊ KHO…»; ngay dưới tiêu đề có dòng «Căn cứ hợp đồng … số … ký ngày …», sau đó là kết quả thực hiện (số lượng, giá trị, công nợ còn lại) và câu hai bên thống nhất thanh lý; thường chỉ 1–2 trang, có chữ ký và con dấu hai bên. Chọn loại này bất kể hợp đồng gốc là mua bán, nhượng quyền, đại lý, vận chuyển hay thuê kho. Không chọn loại này cho chính bản hợp đồng, cho biên bản giao nhận hàng hay biên bản đối chiếu công nợ.
- **Cụm tiêu đề nhận biết.** «biên bản thanh lý hợp đồng»; «thanh lý hợp đồng».
- **Dễ nhầm với** `HD_MUA_BAN`, `HD_NHUONG_QUYEN_DAI_LY`, `HD_THUE_TAI_SAN`, `BB_GIAO_NHAN_HANG_HOA`. Chữ «thanh lý» nằm trong TIÊU ĐỀ → loại này, kể cả khi thân văn bản nhắc tên hợp đồng gốc. Tiêu đề «biên bản nghiệm thu, bàn giao hàng hóa» → BB_GIAO_NHAN_HANG_HOA dù nằm chung tệp với bản thanh lý.
- **Lưu ý khi gán.** Nếu bản thanh lý nằm chung tệp với hợp đồng hoặc biên bản nghiệm thu thì mỗi văn bản là một segment.
- **Làm rõ (v1.1).** Loại này áp dụng **bất kể hợp đồng gốc là loại nào**. Ví dụ tiêu đề đều là `BB_THANH_LY_HD`: «Biên bản thanh lý hợp đồng đại lý …», «Biên bản thanh lý hợp đồng nhượng quyền thương mại», «Biên bản thanh lý hợp đồng thuê kho …», «Thanh lý hợp đồng kinh tế». Không gán `HD_NHUONG_QUYEN_DAI_LY` hay `HD_THUE_TAI_SAN` cho các văn bản này.
- **Ví dụ.** `_4. THANH LÝ HỢP ĐỒNG/TLHD 12.20-SU DOAN 31.pdf`; `_4. THANH LÝ HỢP ĐỒNG/TLHD 2020-SAU LIEM.pdf`; `_3. HOP DONG DAU VAO-Diem/THANH LÝ HĐ THUÊ KHO - HK.pdf`.

### Nhóm Giấy phép, chứng nhận pháp lý của doanh nghiệp/cơ sở (`PHAP_LY_DN`)

#### 6.7. `GCN_DKDN` — Giấy chứng nhận đăng ký doanh nghiệp / kinh doanh / hợp tác xã / chi nhánh

- **Định nghĩa.** Giấy do Phòng Đăng ký kinh doanh (Sở Kế hoạch và Đầu tư, Sở Tài chính) hoặc Phòng Tài chính – Kế hoạch cấp huyện cấp, xác nhận việc đăng ký thành lập của một doanh nghiệp, doanh nghiệp tư nhân, hợp tác xã, hộ kinh doanh hoặc chi nhánh. Tiêu đề là «GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP» kèm loại hình («CÔNG TY TRÁCH NHIỆM HỮU HẠN…», «CÔNG TY CỔ PHẦN», «DOANH NGHIỆP TƯ NHÂN»), hoặc «GIẤY CHỨNG NHẬN ĐĂNG KÝ KINH DOANH (VÀ ĐĂNG KÝ THUẾ)», «GIẤY CHỨNG NHẬN ĐĂNG KÝ HỢP TÁC XÃ», «GIẤY CHỨNG NHẬN ĐĂNG KÝ HOẠT ĐỘNG CHI NHÁNH»; có dòng «Mã số doanh nghiệp», «Đăng ký lần đầu… Đăng ký thay đổi lần thứ…», các mục đánh số: tên, địa chỉ trụ sở, vốn điều lệ, người đại diện theo pháp luật; giấy in trên nền hoa văn vàng có quốc huy. Các trang «Giấy xác nhận về việc thay đổi nội dung đăng ký doanh nghiệp» hoặc «Công bố nội dung đăng ký doanh nghiệp» đi kèm cũng thuộc loại này. Không chọn loại này cho giấy chứng nhận cửa hàng đủ điều kiện bán lẻ xăng dầu (do Sở Công Thương cấp) hay giấy đăng ký xe, tàu.
- **Cụm tiêu đề nhận biết.** «giấy chứng nhận đăng ký doanh nghiệp công ty»; «giấy chứng nhận đăng ký doanh nghiệp doanh nghiệp tư nhân»; «giấy chứng nhận đăng ký kinh doanh doanh nghiệp tư nhân»; «giấy chứng nhận đăng ký kinh doanh và đăng ký thuế»; «giấy chứng nhận đăng ký hợp tác xã»; «giấy chứng nhận đăng ký hoạt động chi nhánh»; «giấy chứng nhận đăng ký hộ kinh doanh»; «giấy xác nhận về việc thay đổi nội dung đăng ký doanh nghiệp»; «mã số doanh nghiệp:»; «mã số chi nhánh:».
- **Dễ nhầm với** `GCN_DDK_BAN_LE_XD`, `GXN_THUONG_NHAN_XD`, `DANG_KY_PHUONG_TIEN`. Cơ quan cấp là Phòng Đăng ký kinh doanh và có «Mã số doanh nghiệp» → GCN_DKDN. Cơ quan cấp là Sở Công Thương/Bộ Công Thương và nói về «đủ điều kiện» → GCN_DDK_BAN_LE_XD hoặc GXN_THUONG_NHAN_XD. Tên tệp «GPKD» không có nghĩa là giấy phép khác: nội dung vẫn là đăng ký doanh nghiệp.
- **Lưu ý khi gán.** Tên tệp thường ghi «GPKD», «GĐKKD» — vẫn là loại này. «Giấy xác nhận về việc thay đổi nội dung đăng ký doanh nghiệp», «Công bố nội dung đăng ký» đi kèm không tách.
- **Ví dụ.** `_1. Giay DKKD khach hang/GPKD-THÀNH LIÊN.pdf`; `_1. Giay DKKD khach hang/GPKD-AN TIN 2018.pdf`; `_1. HOP DONG DAI LY NHUONG QUYEN/GPKD-ANH KHA.pdf` (tệp thứ nhất 7 trang có kèm «công bố nội dung đăng ký doanh nghiệp» — vẫn là một tài liệu; tệp thứ hai là đăng ký hợp tác xã).

#### 6.8. `GCN_DDK_BAN_LE_XD` — Giấy chứng nhận cửa hàng đủ điều kiện bán lẻ xăng dầu

- **Định nghĩa.** Giấy do Sở Công Thương tỉnh/thành phố cấp cho MỘT cửa hàng xăng dầu, xác nhận cửa hàng đủ điều kiện bán lẻ xăng dầu. Tiêu đề là «GIẤY CHỨNG NHẬN CỬA HÀNG ĐỦ ĐIỀU KIỆN BÁN LẺ XĂNG DẦU» (giấy cũ có thể ghi «…ĐỦ ĐIỀU KIỆN KINH DOANH XĂNG DẦU»); số giấy có ký hiệu «GCNĐĐK-SCT», «GCNBLXD-SCT» hoặc «GCN-SCT»; nội dung trình bày như một quyết định: «GIÁM ĐỐC SỞ CÔNG THƯƠNG… QUYẾT ĐỊNH: Điều 1. Cấp Giấy chứng nhận…» nêu tên, địa chỉ cửa hàng, thương nhân chủ sở hữu, thương nhân cung cấp xăng dầu, và Điều 3 ghi «có giá trị đến hết ngày…». Trang «NHỮNG ĐIỀU QUY ĐỊNH» kèm theo là một phần của giấy này. Không chọn loại này cho giấy đăng ký doanh nghiệp, cho giấy xác nhận thương nhân đầu mối/phân phối của Bộ Công Thương, hay cho giấy chứng nhận đủ điều kiện về PCCC do công an cấp.
- **Cụm tiêu đề nhận biết.** «giấy chứng nhận cửa hàng đủ điều kiện bán lẻ xăng dầu»; «cửa hàng đủ điều kiện bán lẻ xăng dầu»; «giấy chứng nhận đủ điều kiện kinh doanh xăng dầu».
- **Dễ nhầm với** `GCN_DKDN`, `GXN_THUONG_NHAN_XD`, `GCN_PCCC_CO_SO`. Chủ thể được cấp là một CỬA HÀNG và cơ quan cấp là Sở Công Thương → loại này. Chủ thể là thương nhân (đầu mối, phân phối) và cơ quan cấp là Bộ Công Thương → GXN_THUONG_NHAN_XD. «Đủ điều kiện về phòng cháy và chữa cháy», do công an cấp → GCN_PCCC_CO_SO.
- **Lưu ý khi gán.** Trang «NHỮNG ĐIỀU QUY ĐỊNH» là phần kèm theo. Ngày hết hạn nằm ở Điều 3 (thường ở trang 2).
- **Làm rõ (v1.1).** Cửa hàng có thể là **ghe, tàu bán xăng dầu** (cửa hàng nổi); giấy đủ điều kiện bán lẻ của chúng vẫn là loại này.
- **Có ngày hết hạn cần theo dõi** (trường `ngay_het_han`) — thông tin cho nhóm trích xuất; không ảnh hưởng cách gán nhãn.
- **Ví dụ.** `_2. Giay Du Dieu Kien Khach hang/DDK-CHIN LOAN-12.1.28.pdf`; `_2. Giay Du Dieu Kien Khach hang/DDK-HAI THAO-15.12.24.pdf`; `_1. HOP DONG DAI LY NHUONG QUYEN/DDK-HOANG MINH-15.12.24.pdf`.

#### 6.9. `GXN_THUONG_NHAN_XD` — Giấy xác nhận đủ điều kiện làm thương nhân đầu mối / phân phối / đại lý xăng dầu

- **Định nghĩa.** Giấy do Bộ Công Thương (hoặc Sở Công Thương) cấp cho MỘT THƯƠNG NHÂN (doanh nghiệp), xác nhận đủ điều kiện làm thương nhân đầu mối, thương nhân phân phối, tổng đại lý hoặc đại lý bán lẻ xăng dầu. Tiêu đề là «GIẤY XÁC NHẬN ĐỦ ĐIỀU KIỆN LÀM THƯƠNG NHÂN ĐẦU MỐI KINH DOANH XĂNG DẦU» hoặc «GIẤY XÁC NHẬN ĐỦ ĐIỀU KIỆN LÀM THƯƠNG NHÂN PHÂN PHỐI XĂNG DẦU»; số có ký hiệu «TNĐM/QĐ-BCT», «TNPP/QĐ-BCT»; mở đầu «BỘ TRƯỞNG BỘ CÔNG THƯƠNG… QUYẾT ĐỊNH», có điều khoản «có giá trị đến hết ngày…». Không chọn loại này cho giấy chứng nhận của một cửa hàng bán lẻ, hay cho hợp đồng thương nhân phân phối xăng dầu (là hợp đồng mua bán).
- **Cụm tiêu đề nhận biết.** «giấy xác nhận đủ điều kiện làm thương nhân đầu mối»; «giấy xác nhận đủ điều kiện làm thương nhân phân phối xăng dầu»; «giấy xác nhận đủ điều kiện làm thương nhân phân phối»; «giấy xác nhận đủ điều kiện làm tổng đại lý»; «giấy xác nhận đủ điều kiện làm đại lý bán lẻ xăng dầu».
- **Dễ nhầm với** `GCN_DDK_BAN_LE_XD`, `HD_MUA_BAN`. «Giấy xác nhận… làm thương nhân…» do Bộ Công Thương ký → loại này. «Giấy chứng nhận cửa hàng…» do Sở Công Thương ký → GCN_DDK_BAN_LE_XD. Có Bên A/Bên B và giá bán → HD_MUA_BAN.
- **Có ngày hết hạn cần theo dõi** (trường `ngay_het_han`) — thông tin cho nhóm trích xuất; không ảnh hưởng cách gán nhãn.
- **Ví dụ.** `_3. HOP DONG DAU VAO-Diem/83-TNĐM-QĐ-BCT Giấy XN Đủ điều kiện làm thương nhân đầu mối kinh doanh xăng dầu 29-05-24.pdf`; `_3. HOP DONG DAU VAO-Diem/CamScanner 31-05-24 21.21 (1).pdf` (tệp thứ hai có tên «CamScanner…» nhưng nội dung là giấy xác nhận thương nhân phân phối).

#### 6.10. `GP_KD_VAN_TAI` — Giấy phép kinh doanh vận tải bằng xe ô tô

- **Định nghĩa.** Giấy phép do Sở Giao thông vận tải (nay là Sở Xây dựng) cấp cho một đơn vị, cho phép kinh doanh vận tải bằng xe ô tô. Tiêu đề là «GIẤY PHÉP KINH DOANH VẬN TẢI BẰNG XE Ô TÔ»; một trang nền hoa văn, có số giấy phép, «Cấp lần thứ…», tên và địa chỉ đơn vị, mục «Được phép kinh doanh các loại hình vận tải bằng xe ô tô» (ví dụ vận tải hàng hóa bằng công-ten-nơ, bằng xe ô tô). Giấy cấp cho đơn vị, không gắn với một biển số xe. Không chọn loại này cho giấy đăng ký doanh nghiệp, hợp đồng vận chuyển, hay giấy phép vận chuyển hàng hóa nguy hiểm.
- **Cụm tiêu đề nhận biết.** «giấy phép kinh doanh vận tải bằng xe ô tô»; «giấy phép kinh doanh vận tải».
- **Dễ nhầm với** `GP_VC_HANG_NGUY_HIEM`, `GCN_DKDN`, `HD_VAN_CHUYEN`. Sở GTVT cấp, nói về loại hình vận tải của đơn vị → loại này. Phòng Cảnh sát PCCC cấp, có danh mục hàng nguy hiểm và biển số xe → GP_VC_HANG_NGUY_HIEM.
- **Có ngày hết hạn cần theo dõi** (trường `ngay_het_han`) — thông tin cho nhóm trích xuất; không ảnh hưởng cách gán nhãn.
- **Ví dụ.** `5. TỔNG HỢP HỒ SƠ XE/Vận tải CP.pdf`.

#### 6.11. `GIAY_PHEP_XAY_DUNG` — Giấy phép xây dựng công trình (cửa hàng xăng dầu)

- **Định nghĩa.** Giấy phép do Sở Xây dựng hoặc UBND cấp huyện cấp cho chủ đầu tư, cho phép xây dựng một công trình (ở đây là cửa hàng xăng dầu). Tiêu đề là «GIẤY PHÉP XÂY DỰNG» kèm dòng «CÔNG TRÌNH: …»; số có ký hiệu «SXD-GP» hoặc «GPXD»; nội dung «CẤP PHÉP XÂY DỰNG CÔNG TRÌNH» nêu tên công trình, địa điểm, chủ đầu tư, các hạng mục, diện tích, và phần chủ đầu tư phải thực hiện. Không chọn loại này cho giấy chứng nhận thẩm duyệt thiết kế về PCCC hay bản vẽ thiết kế.
- **Cụm tiêu đề nhận biết.** «giấy phép xây dựng»; «cấp phép xây dựng công trình».
- **Dễ nhầm với** `GCN_PCCC_CO_SO`, `BAN_VE_KY_THUAT`. Tiêu đề «giấy phép xây dựng», cơ quan cấp là Sở Xây dựng/UBND → loại này. Cơ quan cấp là công an PCCC → GCN_PCCC_CO_SO.
- **Có ngày hết hạn cần theo dõi** (trường `thoi_han_khoi_cong`) — thông tin cho nhóm trích xuất; không ảnh hưởng cách gán nhãn.
- **Ví dụ.** `9. TỔNG HỢP HỒ SƠ CỬA HÀNG/9. GPXD Ba Phú (BC).pdf`.

### Nhóm Chứng chỉ và giấy tờ cá nhân (`CHUNG_CHI_CA_NHAN`)

#### 6.12. `CC_TAP_HUAN_VC_HNH` — Giấy chứng nhận hoàn thành chương trình tập huấn vận chuyển hàng hóa nguy hiểm

- **Định nghĩa.** Thẻ/giấy chứng nhận cấp cho MỘT CÁ NHÂN (lái xe, người áp tải, nhân viên) đã hoàn thành lớp tập huấn vận chuyển hàng hóa nguy hiểm (xăng dầu). Tiêu đề là «GIẤY CHỨNG NHẬN HOÀN THÀNH CHƯƠNG TRÌNH TẬP HUẤN VẬN CHUYỂN HÀNG HÓA NGUY HIỂM»; thẻ gập đôi cỡ nhỏ, thường nền xanh: một mặt là bìa chỉ in tên đơn vị và tiêu đề, mặt kia có ảnh chân dung, họ tên, năm sinh, nghề nghiệp, đơn vị công tác, số «…-GCN», thời gian tập huấn và dòng «Giấy chứng nhận này có giá trị 02 năm, từ ngày… đến ngày…». Không chọn loại này cho giấy phép vận chuyển hàng nguy hiểm cấp cho xe của đơn vị, cho chứng nhận huấn luyện PCCC hay giấy chứng nhận nghiệp vụ bảo vệ môi trường.
- **Cụm tiêu đề nhận biết.** «giấy chứng nhận hoàn thành chương trình tập huấn vận chuyển hàng hóa nguy hiểm»; «tập huấn vận chuyển hàng hóa nguy hiểm»; «hoàn thành chương trình tập huấn».
- **Dễ nhầm với** `GP_VC_HANG_NGUY_HIEM`, `CC_HUAN_LUYEN_PCCC`, `CC_NGHIEP_VU_BVMT`. Cấp cho một người, có ảnh, chữ «tập huấn» → loại này. Cấp cho đơn vị, có biển số xe và danh mục hàng → GP_VC_HANG_NGUY_HIEM. Chữ «huấn luyện nghiệp vụ phòng cháy, chữa cháy» do công an cấp → CC_HUAN_LUYEN_PCCC.
- **Lưu ý khi gán.** Trang 1 có thể chỉ là bìa thẻ: xem cả hai trang rồi mới quyết định.
- **Làm rõ (v1.1).** Người được cấp là **người ngoài công ty** (lái xe thuê ngoài, nhân sự đơn vị khác) vẫn là `CC_TAP_HUAN_VC_HNH`: loại do tiêu đề quyết định, không do người đứng tên thuộc đơn vị nào. Thứ tự bìa/mặt trong trong tệp không quan trọng (mục 4.1, quy tắc 6).
- **Có ngày hết hạn cần theo dõi** (trường `ngay_het_han`) — thông tin cho nhóm trích xuất; không ảnh hưởng cách gán nhãn.
- **Ví dụ.** `10. GCN VC HNH/62. GCN VC HNH Huy (12-5-24).pdf`; `8. GCN Lop dao tao van chuyen hang chay no/73. GCN vc hàng nguy hiểm-Tình.pdf`; `9. TỔNG HỢP HỒ SƠ CỬA HÀNG/12. VCHNH Chính (12-5-24).pdf`.

#### 6.13. `CC_HUAN_LUYEN_PCCC` — Chứng nhận huấn luyện nghiệp vụ PCCC và cứu nạn, cứu hộ

- **Định nghĩa.** Thẻ chứng nhận do Phòng Cảnh sát PCCC và CNCH (công an tỉnh) cấp cho MỘT CÁ NHÂN đã qua huấn luyện nghiệp vụ phòng cháy, chữa cháy, cứu nạn, cứu hộ. Mặt bìa đỏ in «CHỨNG NHẬN HUẤN LUYỆN NGHIỆP VỤ PHÒNG CHÁY, CHỮA CHÁY, CỨU NẠN, CỨU HỘ» và số; mặt trong có «CHỨNG NHẬN: Ông/bà…», năm sinh, nơi làm việc, «đã được huấn luyện nghiệp vụ…», thời gian huấn luyện, dấu của Phòng Cảnh sát PCCC. Không chọn loại này cho giấy chứng nhận đủ điều kiện hay thẩm duyệt PCCC của cơ sở, cho tập hồ sơ quản lý PCCC, hay cho chứng nhận tập huấn vận chuyển hàng nguy hiểm.
- **Cụm tiêu đề nhận biết.** «chứng nhận huấn luyện nghiệp vụ phòng cháy, chữa cháy, cứu nạn, cứu hộ»; «chứng nhận huấn luyện nghiệp vụ phòng cháy»; «huấn luyện nghiệp vụ phòng cháy, chữa cháy».
- **Dễ nhầm với** `GCN_PCCC_CO_SO`, `CC_TAP_HUAN_VC_HNH`, `CC_NGHIEP_VU_BVMT`, `HO_SO_QUAN_LY_PCCC`. Thẻ nhỏ đứng tên một người → loại này. Giấy khổ A4 đứng tên cơ sở/phương tiện («đủ điều kiện», «thẩm duyệt») → GCN_PCCC_CO_SO. Sổ/tập nhiều trang có bìa «hồ sơ quản lý công tác PCCC» → HO_SO_QUAN_LY_PCCC.
- **Lưu ý khi gán.** Bìa đỏ ở trang 1, nội dung ở trang 2.
- **Có ngày hết hạn cần theo dõi** (trường `ngay_het_han`) — thông tin cho nhóm trích xuất; không ảnh hưởng cách gán nhãn.
- **Ví dụ.** `9. TỔNG HỢP HỒ SƠ CỬA HÀNG/37b. Bằng PCCC Loan (BC-6-6-27).pdf`; `9. TỔNG HỢP HỒ SƠ CỬA HÀNG/PCCC-BUI DAC TRONG (10-08-28).pdf`.

#### 6.14. `CC_NGHIEP_VU_BVMT` — Giấy chứng nhận đào tạo/bồi dưỡng nghiệp vụ bảo vệ môi trường trong kinh doanh xăng dầu

- **Định nghĩa.** Giấy chứng nhận cấp cho MỘT CÁ NHÂN đã qua lớp đào tạo, bồi dưỡng nghiệp vụ bảo vệ môi trường trong kinh doanh xăng dầu (theo Nghị định 83/2014/NĐ-CP). Do trường (ví dụ Trường Cao đẳng Thương mại – Bộ Công Thương) hoặc Sở Tài nguyên và Môi trường cấp; bìa in «GIẤY CHỨNG NHẬN» hoặc «GIẤY CHỨNG NHẬN ĐÀO TẠO NGHIỆP VỤ BẢO VỆ MÔI TRƯỜNG»; mặt trong có ảnh, «Cấp cho/Chứng nhận: Ông (bà)…», «Đã dự lớp bồi dưỡng: Bảo vệ môi trường trong kinh doanh xăng dầu», thời gian học, kết quả, số vào sổ; có thể có dòng «Có giá trị đến ngày…». Không chọn loại này cho giấy chứng nhận an toàn kỹ thuật và bảo vệ môi trường của phương tiện (đăng kiểm), cho chứng nhận huấn luyện PCCC, hay cho tập huấn vận chuyển hàng nguy hiểm.
- **Cụm tiêu đề nhận biết.** «giấy chứng nhận đào tạo nghiệp vụ bảo vệ môi trường»; «nghiệp vụ bảo vệ môi trường»; «bảo vệ môi trường trong kinh doanh xăng dầu»; «trường cao đẳng thương mại».
- **Dễ nhầm với** `GCN_ATKT_BVMT_PT`, `CC_HUAN_LUYEN_PCCC`, `CC_TAP_HUAN_VC_HNH`. Có ảnh và tên một người, nội dung là lớp học → loại này. Có tên/số đăng ký phương tiện, do cơ quan đăng kiểm cấp → GCN_ATKT_BVMT_PT.
- **Lưu ý khi gán.** Bìa chỉ ghi «GIẤY CHỨNG NHẬN» (bìa đỏ hoặc xanh): bắt buộc xem mặt trong. Evidence ghi theo mặt trong.
- **Có ngày hết hạn cần theo dõi** (trường `ngay_het_han`) — thông tin cho nhóm trích xuất; không ảnh hưởng cách gán nhãn.
- **Ví dụ.** `9. TỔNG HỢP HỒ SƠ CỬA HÀNG/36. Bằng BVMT a.Chí (BC-30-1-23).pdf`; `9. TỔNG HỢP HỒ SƠ CỬA HÀNG/18. BVMT-PHAM NGOC HOANG (3-6-27).pdf`; `9. TỔNG HỢP HỒ SƠ CỬA HÀNG/MT 2 nhân vien GH3_2.pdf` (tệp thứ ba gồm chứng nhận của 2 người (composite cùng loại)).

#### 6.15. `GPLX` — Giấy phép lái xe

- **Định nghĩa.** Giấy phép lái xe của một cá nhân: thẻ nhựa nhỏ có ảnh, dòng «GIẤY PHÉP LÁI XE / DRIVER'S LICENSE», số giấy phép, họ tên, ngày sinh, quốc tịch, nơi cư trú, hạng xe (B2, C, FC, CE…) và dòng «Có giá trị đến/Expires»; mặt sau là bảng phân hạng xe được phép lái. Thường được quét hai mặt, mỗi mặt một trang, thẻ chỉ chiếm một góc trang A4. Không chọn loại này cho căn cước công dân, cho giấy đăng ký xe hay giấy phép kinh doanh vận tải.
- **Cụm tiêu đề nhận biết.** «giấy phép lái xe»; «driver's license»; «driving license».
- **Dễ nhầm với** `CCCD`, `DANG_KY_PHUONG_TIEN`. Thẻ có chữ «giấy phép lái xe» và hạng xe → GPLX. Thẻ có «căn cước» → CCCD. Thẻ có «tên chủ xe», biển số, số khung → DANG_KY_PHUONG_TIEN.
- **Lưu ý khi gán.** Thẻ nhỏ nằm ở góc trang A4; hai mặt là hai trang của cùng một tài liệu.
- **Có ngày hết hạn cần theo dõi** (trường `ngay_het_han`) — thông tin cho nhóm trích xuất; không ảnh hưởng cách gán nhãn.
- **Ví dụ.** `5. TỔNG HỢP HỒ SƠ XE/HUYNH VIET NAM-4.11.25.pdf`; `5. TỔNG HỢP HỒ SƠ XE/PHAM VAN TUAN-12.6.28.pdf`.

#### 6.16. `CCCD` — Căn cước công dân / chứng minh nhân dân

- **Định nghĩa.** Thẻ căn cước công dân, thẻ căn cước hoặc giấy chứng minh nhân dân của một cá nhân: thẻ nhỏ có ảnh, quốc huy, dòng «CĂN CƯỚC CÔNG DÂN / Citizen Identity Card» (hoặc «CĂN CƯỚC», «GIẤY CHỨNG MINH NHÂN DÂN»), số định danh, họ tên, ngày sinh, giới tính, quê quán, nơi thường trú, «Có giá trị đến»; mặt sau có dấu vân tay, mã QR/chip và dòng mã MRZ. Thường quét hai mặt trên hai trang. Không chọn loại này cho giấy phép lái xe hay các thẻ chứng nhận tập huấn.
- **Cụm tiêu đề nhận biết.** «căn cước công dân / citizen identity card»; «citizen identity card»; «giấy chứng minh nhân dân».
- **Dễ nhầm với** `GPLX`, `GCN_DKDN`. Thẻ nhỏ có ảnh và chữ «căn cước» là tiêu đề → CCCD. Văn bản A4 chỉ NHẮC «căn cước công dân» của người đại diện (giấy đăng ký doanh nghiệp, hợp đồng, giấy ủy quyền) → không phải CCCD.
- **Có ngày hết hạn cần theo dõi** (trường `ngay_het_han`) — thông tin cho nhóm trích xuất; không ảnh hưởng cách gán nhãn.
- **Ví dụ.** `5. TỔNG HỢP HỒ SƠ XE/72. HA THANH NHAN.pdf` (kho mẫu chỉ có 1 tệp).

### Nhóm Hồ sơ phương tiện và thiết bị (`PHUONG_TIEN_THIET_BI`)

#### 6.17. `DANG_KY_PHUONG_TIEN` — Chứng nhận đăng ký xe ô tô / rơ moóc / phương tiện thủy nội địa

- **Định nghĩa.** Giấy đăng ký quyền sở hữu, lưu hành của MỘT PHƯƠNG TIỆN. Với xe: thẻ nhỏ do Phòng Cảnh sát giao thông cấp, một mặt in «CHỨNG NHẬN ĐĂNG KÝ XE Ô TÔ» hoặc «CHỨNG NHẬN ĐĂNG KÝ RƠ MOÓC, SƠ MI RƠ MOÓC» và số, mặt kia có «Tên chủ xe (Owner's full name)», địa chỉ, nhãn hiệu, số loại, số máy, số khung, «Biển số đăng ký», «Đăng ký xe có giá trị đến ngày». Với tàu/ghe: giấy khổ A4 «GIẤY CHỨNG NHẬN ĐĂNG KÝ PHƯƠNG TIỆN THỦY NỘI ĐỊA» do Sở Giao thông vận tải cấp, có tên phương tiện, số đăng ký, chủ phương tiện, kích thước, có thể kèm trang ảnh chụp phương tiện. Không chọn loại này cho giấy biên nhận thế chấp của ngân hàng, giấy đăng kiểm (an toàn kỹ thuật), giấy chứng nhận bảo hiểm, hay giấy đăng ký doanh nghiệp.
- **Cụm tiêu đề nhận biết.** «chứng nhận đăng ký xe ô tô»; «chứng nhận đăng ký rơ moóc, sơ mi rơ moóc»; «giấy chứng nhận đăng ký phương tiện thủy nội địa»; «đăng ký phương tiện thủy»; «tên chủ xe»; «owner's full name».
- **Dễ nhầm với** `BIEN_NHAN_THE_CHAP_PT`, `GCN_ATKT_BVMT_PT`, `GCN_BAO_HIEM`, `GPLX`. Do cơ quan cảnh sát giao thông/Sở GTVT cấp, có «tên chủ xe/chủ phương tiện» và biển số → loại này. Có logo ngân hàng và chữ «biên nhận thế chấp» → BIEN_NHAN_THE_CHAP_PT (dù trong thân nhắc số giấy đăng ký xe). Có «an toàn kỹ thuật và bảo vệ môi trường» → GCN_ATKT_BVMT_PT.
- **Lưu ý khi gán.** Trang 1 có thể là mặt thông tin (không có tiêu đề), tiêu đề nằm ở mặt kia. Trang ảnh chụp tàu là phần kèm theo.
- **Làm rõ (v1.1).** Khi chỉ thấy mặt thông tin, dấu hiệu «Tên chủ xe (Owner's full name)» cùng biển số, số khung, số máy là đủ để gán loại này (ghi vào `evidence`, `confidence=medium`); thứ tự hai mặt không quan trọng (mục 4.1, quy tắc 5 và 6).
- **Có ngày hết hạn cần theo dõi** (trường `ngay_het_han`) — thông tin cho nhóm trích xuất; không ảnh hưởng cách gán nhãn.
- **Ví dụ.** `5. TỔNG HỢP HỒ SƠ XE/3.2 77R-009.34.pdf`; `5. TỔNG HỢP HỒ SƠ XE/7.1 77C-173.10 (31.12.2038).pdf`; `_1. Giay DKKD khach hang/Đăng ký tàu HƯƠNG SƠN 2.pdf`.

#### 6.18. `BIEN_NHAN_THE_CHAP_PT` — Giấy biên nhận thế chấp phương tiện giao thông (ngân hàng cấp)

- **Định nghĩa.** Giấy do ngân hàng cấp, xác nhận ngân hàng đang giữ bản chính giấy chứng nhận đăng ký của một phương tiện đang thế chấp; dùng thay giấy đăng ký xe khi lưu hành. Có logo và địa chỉ ngân hàng ở đầu trang, tiêu đề «GIẤY BIÊN NHẬN THẾ CHẤP PHƯƠNG TIỆN GIAO THÔNG», số, ngày, «Thông tin Bên thế chấp», thông tin chi tiết phương tiện (số giấy đăng ký, loại phương tiện, số khung, số máy, biển kiểm soát) và mục «Giấy biên nhận thế chấp… được cấp lần…, có hiệu lực đến hết ngày…»; một trang A4 có dấu ngân hàng. Một tệp có thể chứa nhiều giấy cho nhiều phương tiện (đầu kéo và rơ moóc). Không chọn loại này cho chính thẻ đăng ký xe hay cho hợp đồng/thỏa thuận tín dụng.
- **Cụm tiêu đề nhận biết.** «giấy biên nhận thế chấp phương tiện giao thông»; «giấy biên nhận thế chấp»; «biên nhận thế chấp».
- **Dễ nhầm với** `DANG_KY_PHUONG_TIEN`, `OTHER`. Tiêu đề «giấy biên nhận thế chấp» + logo ngân hàng → loại này. Thẻ nhỏ của cảnh sát giao thông → DANG_KY_PHUONG_TIEN. Thỏa thuận/hợp đồng cấp tín dụng nhiều trang → OTHER (xem câu hỏi mở).
- **Lưu ý khi gán.** Mỗi phương tiện một giấy (một trang) → tệp 2 trang cho đầu kéo + rơ moóc là composite cùng loại `1:…;2:…`.
- **Có ngày hết hạn cần theo dõi** (trường `ngay_het_han`) — thông tin cho nhóm trích xuất; không ảnh hưởng cách gán nhãn.
- **Ví dụ.** `5. TỔNG HỢP HỒ SƠ XE/1. Xe 08001-02645-15.2.24.pdf`; `5. TỔNG HỢP HỒ SƠ XE/3. Xe 09567-00934.pdf` (mỗi tệp gồm 2 giấy cho đầu kéo và rơ moóc (composite cùng loại)).

#### 6.19. `GCN_ATKT_BVMT_PT` — Giấy chứng nhận an toàn kỹ thuật và bảo vệ môi trường của phương tiện (đăng kiểm)

- **Định nghĩa.** Giấy do cơ quan đăng kiểm cấp cho MỘT PHƯƠNG TIỆN sau khi kiểm định an toàn kỹ thuật và bảo vệ môi trường. Với tàu/ghe: «GIẤY CHỨNG NHẬN AN TOÀN KỸ THUẬT VÀ BẢO VỆ MÔI TRƯỜNG PHƯƠNG TIỆN THỦY NỘI ĐỊA» do Chi cục Đăng kiểm cấp, có tên phương tiện, số đăng ký, số kiểm soát, chủ phương tiện, thông số kỹ thuật, vùng hoạt động, «có hiệu lực đến ngày…», trang sau là bảng trang thiết bị. Với xe: «GIẤY CHỨNG NHẬN KIỂM ĐỊNH AN TOÀN KỸ THUẬT VÀ BẢO VỆ MÔI TRƯỜNG PHƯƠNG TIỆN GIAO THÔNG CƠ GIỚI ĐƯỜNG BỘ» do trung tâm đăng kiểm cấp, có biển số và hạn kiểm định. Không chọn loại này cho giấy chứng nhận đào tạo nghiệp vụ bảo vệ môi trường của cá nhân, cho giấy kiểm định cột đo/xi téc (đo lường), hay cho giấy đăng ký phương tiện.
- **Cụm tiêu đề nhận biết.** «giấy chứng nhận an toàn kỹ thuật và bảo vệ môi trường»; «an toàn kỹ thuật và bảo vệ môi trường phương tiện thủy nội địa»; «kiểm định an toàn kỹ thuật và bảo vệ môi trường phương tiện giao thông cơ giới đường bộ»; «chi cục đăng kiểm».
- **Dễ nhầm với** `GCN_KIEM_DINH_DO_LUONG`, `CC_NGHIEP_VU_BVMT`, `DANG_KY_PHUONG_TIEN`. Cơ quan đăng kiểm cấp, nói về an toàn kỹ thuật của cả phương tiện → loại này. Trung tâm đo lường chất lượng cấp, đối tượng là «cột đo»/«xi téc», có dung tích và tem kiểm định → GCN_KIEM_DINH_DO_LUONG.
- **Có ngày hết hạn cần theo dõi** (trường `ngay_het_han`) — thông tin cho nhóm trích xuất; không ảnh hưởng cách gán nhãn.
- **Ví dụ.** `9. TỔNG HỢP HỒ SƠ CỬA HÀNG/4. ATKT  Và BVMT GH1_3.pdf`.

#### 6.20. `GCN_KIEM_DINH_DO_LUONG` — Giấy chứng nhận kiểm định phương tiện đo (cột đo xăng dầu, xi téc ô tô)

- **Định nghĩa.** Giấy do tổ chức kiểm định đo lường (Trung tâm Kỹ thuật Tiêu chuẩn Đo lường Chất lượng, Trung tâm Phân tích và Đo lường chất lượng) cấp cho MỘT THIẾT BỊ ĐO. Tiêu đề song ngữ «GIẤY CHỨNG NHẬN KIỂM ĐỊNH / CERTIFICATE OF VERIFICATION», số có đuôi «/ĐLXT» hoặc dạng «K.xxx/năm»; có «Tên đối tượng: Cột đo…» hoặc «Xi téc ô tô», kiểu, số, đặc trưng kỹ thuật đo lường (dung tích danh định, cấp chính xác), nơi sử dụng, đơn vị sử dụng, phương pháp kiểm định, kết luận, số tem kiểm định và «Thời hạn đến». Với xi téc, trang sau là bảng «KẾT QUẢ KIỂM ĐỊNH» (barem: chiều cao – dung tích từng hầm). Một tệp có thể gồm nhiều giấy cho nhiều cột đo. Không chọn loại này cho giấy đăng kiểm an toàn kỹ thuật của xe/tàu hay chứng thư chất lượng xăng dầu.
- **Cụm tiêu đề nhận biết.** «giấy chứng nhận kiểm định»; «certificate of verification»; «kết quả kiểm định».
- **Dễ nhầm với** `GCN_ATKT_BVMT_PT`, `CHUNG_THU_CHAT_LUONG`. «Certificate of Verification», đối tượng là cột đo/xi téc, có tem kiểm định → loại này. «Certificate of Quality», bảng chỉ tiêu chất lượng nhiên liệu → CHUNG_THU_CHAT_LUONG. Có cụm «an toàn kỹ thuật và bảo vệ môi trường» → GCN_ATKT_BVMT_PT.
- **Lưu ý khi gán.** Giấy + trang «kết quả kiểm định» (barem) của cùng một xi téc = một tài liệu. Mỗi cột đo một giấy riêng → nhiều segment.
- **Có ngày hết hạn cần theo dõi** (trường `ngay_het_han`) — thông tin cho nhóm trích xuất; không ảnh hưởng cách gán nhãn.
- **Ví dụ.** `5. TỔNG HỢP HỒ SƠ XE/Barem 77R- 01926-31.12.22.pdf`; `9. TỔNG HỢP HỒ SƠ CỬA HÀNG/Cột đo ghe 1.pdf` (tệp «Barem» là giấy kiểm định xi téc 2 trang (một tài liệu); tệp «Cột đo» gồm 3 giấy cho 3 cột đo (composite cùng loại)).

#### 6.21. `GP_VC_HANG_NGUY_HIEM` — Giấy phép vận chuyển hàng hóa nguy hiểm (về cháy, nổ)

- **Định nghĩa.** Giấy phép do Phòng Cảnh sát PCCC và CNCH (công an tỉnh) cấp cho một đơn vị, cho phép các phương tiện cụ thể vận chuyển hàng hóa nguy hiểm về cháy, nổ (xăng, dầu). Tiêu đề «GIẤY PHÉP VẬN CHUYỂN HÀNG HÓA NGUY HIỂM VỀ CHÁY, NỔ»; số có đuôi «/PCCC»; có tên đơn vị, người đại diện, dòng «Được phép vận chuyển hàng hóa nguy hiểm về cháy, nổ ghi tại trang 02», «Thời hạn của giấy phép: …»; trang 2 là «DANH MỤC HÀNG HÓA NGUY HIỂM VỀ CHÁY, NỔ ĐƯỢC PHÉP VẬN CHUYỂN» có tên hàng, số hiệu UN, khối lượng và biển kiểm soát (BKS) của xe. Không chọn loại này cho thẻ chứng nhận tập huấn của lái xe, cho giấy phép kinh doanh vận tải, hay cho hợp đồng vận chuyển.
- **Cụm tiêu đề nhận biết.** «giấy phép vận chuyển hàng hóa nguy hiểm về cháy, nổ»; «giấy phép vận chuyển hàng hóa nguy hiểm»; «giấy phép vận chuyển hàng nguy hiểm»; «danh mục hàng hóa nguy hiểm».
- **Dễ nhầm với** `CC_TAP_HUAN_VC_HNH`, `GP_KD_VAN_TAI`, `GCN_PCCC_CO_SO`. «Giấy phép», cấp cho đơn vị, có biển số xe và thời hạn → loại này. «Giấy chứng nhận hoàn thành chương trình tập huấn», cấp cho một người → CC_TAP_HUAN_VC_HNH.
- **Có ngày hết hạn cần theo dõi** (trường `ngay_het_han`) — thông tin cho nhóm trích xuất; không ảnh hưởng cách gán nhãn.
- **Ví dụ.** `5. TỔNG HỢP HỒ SƠ XE/PCCC 09567+00934 (31-5-23).pdf`; `5. TỔNG HỢP HỒ SƠ XE/PCCC 10179 + 01942 (26-7-23).pdf` (tên tệp ghi «PCCC» vì cơ quan cấp là cảnh sát PCCC; nội dung là giấy phép vận chuyển).

### Nhóm Hồ sơ PCCC, an toàn, môi trường của cơ sở (`PCCC_AN_TOAN`)

#### 6.22. `GCN_PCCC_CO_SO` — Giấy chứng nhận đủ điều kiện / thẩm duyệt thiết kế về PCCC của cơ sở, phương tiện

- **Định nghĩa.** Giấy do cơ quan Cảnh sát PCCC (công an tỉnh, Bộ Công an) cấp cho MỘT CƠ SỞ hoặc phương tiện: «GIẤY CHỨNG NHẬN ĐỦ ĐIỀU KIỆN VỀ PHÒNG CHÁY VÀ CHỮA CHÁY» (Mẫu PC4, một trang nền hoa văn, phần «CHỨNG NHẬN:» ghi tên cơ sở, địa chỉ, ngành nghề kinh doanh xăng dầu), «GIẤY CHỨNG NHẬN THẨM DUYỆT THIẾT KẾ VỀ PHÒNG CHÁY VÀ CHỮA CHÁY» (số có ký hiệu «TD-PCCC», trang 2 là danh mục tài liệu, bản vẽ được thẩm duyệt), hoặc văn bản nghiệm thu về PCCC. Không chọn loại này cho thẻ chứng nhận huấn luyện PCCC của cá nhân, cho tập hồ sơ quản lý/biên bản tự kiểm tra PCCC do cơ sở tự lập, cho giấy phép vận chuyển hàng nguy hiểm, hay cho giấy chứng nhận cửa hàng đủ điều kiện bán lẻ xăng dầu của Sở Công Thương.
- **Cụm tiêu đề nhận biết.** «giấy chứng nhận đủ điều kiện về phòng cháy và chữa cháy»; «đủ điều kiện về phòng cháy và chữa cháy»; «giấy chứng nhận thẩm duyệt thiết kế về phòng cháy và chữa cháy»; «giấy chứng nhận thẩm duyệt thiết kế về phòng cháy»; «nghiệm thu về phòng cháy và chữa cháy».
- **Dễ nhầm với** `CC_HUAN_LUYEN_PCCC`, `HO_SO_QUAN_LY_PCCC`, `GCN_DDK_BAN_LE_XD`, `GP_VC_HANG_NGUY_HIEM`. Do công an cấp cho cơ sở/phương tiện, 1–2 trang → loại này. Do cơ sở tự lập, nhiều trang, có sổ theo dõi và biên bản tự kiểm tra → HO_SO_QUAN_LY_PCCC. Thẻ nhỏ đứng tên một người → CC_HUAN_LUYEN_PCCC.
- **Làm rõ (v1.1).** Cơ sở có thể là **ghe, tàu bán xăng dầu**; giấy PCCC của chúng vẫn là loại này.
- **Ví dụ.** `9. TỔNG HỢP HỒ SƠ CỬA HÀNG/5. GCN đủ ĐK PCCC (BC)_1.pdf`; `9. TỔNG HỢP HỒ SƠ CỬA HÀNG/Thẩm duyệt PCCC GH3_4.pdf`.

#### 6.23. `HO_SO_QUAN_LY_PCCC` — Hồ sơ quản lý, theo dõi công tác PCCC của cơ sở (kèm biên bản tự kiểm tra PCCC)

- **Định nghĩa.** Tập hồ sơ nhiều trang (thường 26–55 trang) do chính cơ sở lập để quản lý công tác phòng cháy chữa cháy của MỘT cửa hàng xăng dầu hoặc tàu/ghe bán dầu trong một kỳ. Trang bìa ghi «HỒ SƠ QUẢN LÝ CÔNG TÁC PHÒNG CHÁY CHỮA CHÁY» cùng «TÊN CƠ SỞ», «ĐỊA CHỈ»; bên trong gồm nội quy PCCC, quyết định thành lập đội PCCC, bản cam kết, «SỔ THEO DÕI PHƯƠNG TIỆN PHÒNG CHÁY VÀ CHỮA CHÁY», sổ kiểm tra điều kiện an toàn PCCC, sổ theo dõi tuyên truyền huấn luyện, báo cáo tổng kết, kế hoạch huấn luyện và các «BIÊN BẢN TỰ KIỂM TRA CÔNG TÁC PHÒNG CHÁY CHỮA CHÁY» hằng tháng. Cả tập là MỘT tài liệu, không tách từng thành phần; tập thiếu bìa hoặc một biên bản tự kiểm tra đứng riêng cũng xếp vào loại này. Không chọn loại này cho giấy chứng nhận do công an cấp hay thẻ huấn luyện PCCC của cá nhân.
- **Cụm tiêu đề nhận biết.** «hồ sơ quản lý công tác phòng cháy chữa cháy»; «sổ theo dõi phương tiện phòng cháy và chữa cháy»; «biên bản tự kiểm tra công tác phòng cháy chữa cháy»; «hồ sơ quản lý công tác pccc»; «biên bản tự kiểm tra».
- **Dễ nhầm với** `GCN_PCCC_CO_SO`, `CC_HUAN_LUYEN_PCCC`, `BIEN_PHAP_UNG_PHO_SU_CO`. Nhiều trang, do cơ sở tự lập, có sổ theo dõi/biên bản tự kiểm tra → loại này. Văn bản 1–2 trang có dấu công an → GCN_PCCC_CO_SO. Tài liệu thuyết minh «biện pháp phòng ngừa, ứng phó sự cố hóa chất» có mục lục → BIEN_PHAP_UNG_PHO_SU_CO.
- **Lưu ý khi gán.** Cả tập là MỘT tài liệu dù bên trong có quyết định, kế hoạch, báo cáo, biên bản với tiêu đề riêng. is_composite=0.
- **Làm rõ (v1.1).** Tệp **bắt đầu bằng «Sổ theo dõi…»** (ví dụ «SỔ THEO DÕI PHƯƠNG TIỆN PHÒNG CHÁY VÀ CHỮA CHÁY») và **không có bìa chung** «Hồ sơ quản lý công tác PCCC» vẫn là `HO_SO_QUAN_LY_PCCC`, `is_composite=0`. Ghi `confidence=medium` và `note` «thiếu bìa chung».
- **Ví dụ.** `8. CUA HANG - TU K.TRA PCCC- VÂN/CH12-T1+T2.pdf`; `8. CUA HANG - TU K.TRA PCCC- VÂN/PCCC CH12-22.pdf`; `TU K.TRA PCCC- VÂN/PCCC CH5-22.pdf`.

#### 6.24. `BIEN_PHAP_UNG_PHO_SU_CO` — Biện pháp / kế hoạch phòng ngừa, ứng phó sự cố (hóa chất, tràn dầu), phương án chữa cháy

- **Định nghĩa.** Tài liệu thuyết minh nhiều trang do doanh nghiệp lập cho một cơ sở, mô tả biện pháp hoặc kế hoạch phòng ngừa và ứng phó sự cố: «BIỆN PHÁP PHÒNG NGỪA, ỨNG PHÓ SỰ CỐ HÓA CHẤT CỦA CỬA HÀNG XĂNG DẦU…», «KẾ HOẠCH ỨNG PHÓ SỰ CỐ TRÀN DẦU», «PHƯƠNG ÁN CHỮA CHÁY CỦA CƠ SỞ». Có trang bìa đóng khung với tên công ty và tên tài liệu, phần mở đầu, các phần đánh số (thông tin về cơ sở, dự báo nguy cơ, tình huống và biện pháp ứng phó, năng lực ứng phó, tổ chức thực hiện), mục lục và số trang ở chân trang. Không chọn loại này cho tập hồ sơ quản lý PCCC gồm sổ theo dõi và biên bản tự kiểm tra, hay cho giấy chứng nhận do cơ quan nhà nước cấp.
- **Cụm tiêu đề nhận biết.** «biện pháp phòng ngừa, ứng phó sự cố hóa chất»; «phòng ngừa, ứng phó sự cố hóa chất»; «kế hoạch ứng phó sự cố tràn dầu»; «phương án chữa cháy của cơ sở».
- **Dễ nhầm với** `HO_SO_QUAN_LY_PCCC`, `CONG_VAN_THONG_BAO`. Văn bản thuyết minh có chương mục và mục lục → loại này. Tập gồm các sổ theo dõi kẻ bảng và biên bản tự kiểm tra hằng tháng → HO_SO_QUAN_LY_PCCC.
- **Lưu ý khi gán.** Cả tập là một tài liệu (có mục lục, đánh số trang liên tục).
- **Ví dụ.** `9. TỔNG HỢP HỒ SƠ CỬA HÀNG/16. UPSC hóa chất (photo).pdf`.

#### 6.25. `BAN_VE_KY_THUAT` — Bản vẽ kỹ thuật / thiết kế

- **Định nghĩa.** Trang bản vẽ kỹ thuật hoặc thiết kế của phương tiện hay công trình (tàu dầu, cửa hàng xăng dầu, hệ thống ống, bể chứa): phần lớn trang là hình vẽ nét mảnh, kích thước, mặt cắt, sơ đồ; có khung tên bản vẽ ở góc (tên công ty thiết kế, tên bản vẽ, ký hiệu, tỷ lệ, người vẽ/kiểm tra), thường xoay ngang và có dấu «ĐÃ THẨM DUYỆT» của cơ quan PCCC hoặc dấu đăng kiểm. Hầu như không có đoạn văn và không có tiêu đề văn bản hành chính. Không chọn loại này cho văn bản có chữ là chính (giấy chứng nhận thẩm duyệt, giấy phép xây dựng) dù có nhắc tới bản vẽ.
- **Cụm tiêu đề nhận biết.** «bản vẽ thiết kế»; «bản vẽ kỹ thuật»; «mặt cắt».
- **Dễ nhầm với** `GCN_PCCC_CO_SO`, `GIAY_PHEP_XAY_DUNG`, `UNREADABLE`. Trang chủ yếu là hình vẽ → loại này. Trang chủ yếu là chữ, có quốc hiệu và tiêu đề «giấy chứng nhận thẩm duyệt» → GCN_PCCC_CO_SO. Trang mờ/đen không nhận ra cả hình lẫn chữ → UNREADABLE.
- **Lưu ý khi gán.** Thường không có tiêu đề văn bản; evidence ghi tên bản vẽ trong khung tên nếu đọc được, hoặc «bản vẽ, không có tiêu đề».
- **Ví dụ.** `9. TỔNG HỢP HỒ SƠ CỬA HÀNG/CamScanner 20-04-24 14.01.pdf`; `9. TỔNG HỢP HỒ SƠ CỬA HÀNG/CamScanner 20-04-24 14.08.pdf`.

### Nhóm Bảo hiểm (`BAO_HIEM`)

#### 6.26. `GCN_BAO_HIEM` — Giấy chứng nhận bảo hiểm (xe cơ giới, cháy nổ, tàu thuyền)

- **Định nghĩa.** Giấy chứng nhận hoặc đơn bảo hiểm do một doanh nghiệp bảo hiểm cấp. Với xe: «GIẤY CHỨNG NHẬN BẢO HIỂM BẮT BUỘC TNDS CỦA CHỦ XE Ô TÔ», «GIẤY CHỨNG NHẬN BẢO HIỂM TỰ NGUYỆN XE Ô TÔ» (bảo hiểm vật chất xe): tờ gập nhỏ nhiều ô, có logo hãng bảo hiểm, «Số GCNBH», chủ xe, biển kiểm soát, số khung, số máy, phạm vi và mức trách nhiệm, phí bảo hiểm, «Thời hạn bảo hiểm: từ… đến…», phần lưu ý cho chủ xe. Với cơ sở hoặc tàu: «GIẤY CHỨNG NHẬN BẢO HIỂM» cháy, nổ bắt buộc hoặc bảo hiểm tài sản/thân tàu, khổ A4, có người được bảo hiểm, địa điểm, số tiền bảo hiểm, thời hạn. Không chọn loại này cho giấy đăng ký xe, giấy đăng kiểm hay hợp đồng mua bán.
- **Cụm tiêu đề nhận biết.** «giấy chứng nhận bảo hiểm»; «bảo hiểm bắt buộc tnds»; «bảo hiểm bắt buộc trách nhiệm dân sự»; «bảo hiểm tự nguyện xe ô tô»; «bảo hiểm vật chất xe»; «bảo hiểm cháy nổ bắt buộc»; «số gcnbh»; «thời hạn bảo hiểm».
- **Dễ nhầm với** `DANG_KY_PHUONG_TIEN`, `GCN_ATKT_BVMT_PT`. Có tên/logo công ty bảo hiểm, phí và thời hạn bảo hiểm → loại này. Thẻ của cảnh sát giao thông có «tên chủ xe» nhưng không có phí bảo hiểm → DANG_KY_PHUONG_TIEN.
- **Lưu ý khi gán.** Một tờ có thể in hai giấy (bắt buộc TNDS + tự nguyện) trên cùng một trang: vẫn là một tài liệu, ghi chú ở note. Bảo hiểm vật chất, TNDS, cháy nổ đều cùng loại này.
- **Làm rõ (v1.1).** Tờ/thẻ **không có dòng tiêu đề** nhưng có «Số GCNBH», logo hãng bảo hiểm và «Thời hạn bảo hiểm» vẫn là loại này (ghi dấu hiệu vào `evidence`, `confidence=medium`; mục 4.1, quy tắc 5).
- **Có ngày hết hạn cần theo dõi** (trường `ngay_het_han`) — thông tin cho nhóm trích xuất; không ảnh hưởng cách gán nhãn.
- **Ví dụ.** `5. TỔNG HỢP HỒ SƠ XE/1b. BHVC 02645 (5-2-24).pdf`; `5. TỔNG HỢP HỒ SƠ XE/BHDS 13420 (2-1-23).pdf`; `9. TỔNG HỢP HỒ SƠ CỬA HÀNG/Bảo Hiểm GH3 (26-11-2024).pdf`.

### Nhóm Chứng từ mua bán, giao nhận hàng hóa (`GIAO_NHAN_HANG_HOA`)

#### 6.27. `DON_DAT_HANG` — Đơn đặt hàng

- **Định nghĩa.** Văn bản một trang do bên mua gửi nhà cung cấp để đặt mua một lô hàng xăng dầu theo hợp đồng đã ký. Tiêu đề «ĐƠN ĐẶT HÀNG»; có số đơn (dạng «…/ĐĐH/…» hoặc «PO-…»), ngày, «Kính gửi: …» (nhà cung cấp), dòng căn cứ hợp đồng mua bán, bảng mặt hàng – số lượng – đơn giá – thành tiền, kho nhận hàng, thời gian nhận hàng, có thể có danh sách xe và lái xe nhận hàng, phần xác nhận của nhà cung cấp; ký bởi đại diện bên mua (chữ ký tay và dấu, hoặc chữ ký số). Không chọn loại này cho hợp đồng, phiếu xuất kho, biên bản giao nhận hay hóa đơn.
- **Cụm tiêu đề nhận biết.** «đơn đặt hàng».
- **Dễ nhầm với** `HD_MUA_BAN`, `PHIEU_XUAT_KHO`, `HOA_DON`. «Kính gửi» + bảng hàng muốn mua, một trang, chỉ bên đặt ký (hoặc thêm xác nhận) → loại này. Có điều khoản và hai bên ký → HD_MUA_BAN. Do kho/nhà máy phát hành khi xuất hàng → PHIEU_XUAT_KHO.
- **Làm rõ (v1.1).** Mẫu đơn có **khối «Nhà cung cấp xác nhận»** (ký, đóng dấu của nhà cung cấp) ở cuối trang vẫn là `DON_DAT_HANG`: khối xác nhận là một phần của đơn, không làm đơn thành hợp đồng hay biên bản và không mở segment mới.
- **Ví dụ.** `_Đơn đặt hàng - mua vào 2026/don-hang_2026-0004.pdf`; `_Đơn đặt hàng - mua vào 2026/don-hang_2601-0002.pdf`; `_Đơn đặt hàng - mua vào 2026/don-hang_2605-0041.pdf`.

#### 6.28. `PHIEU_XUAT_KHO` — Phiếu xuất kho

- **Định nghĩa.** Phiếu do kho hoặc nhà máy (ví dụ nhà máy lọc dầu) phát hành khi xuất một lô xăng dầu cho bên mua. Tiêu đề «PHIẾU XUẤT KHO THÀNH PHẨM» hoặc «PHIẾU XUẤT KHO»; góc trên phải có ô «Ngày», «Ký hiệu», «Số»; nội dung có «Lý do xuất kho: xuất bán sản phẩm theo hợp đồng số…», lệnh xuất hàng, bồn xuất, bên giao, bên nhận, phương tiện và thời gian giao nhận, bảng số lượng xuất (thùng, m3 tại 15°C, tấn, m3 thực tế), hệ số đồng hồ, bảng số chứng thư chất lượng theo hầm, và ba chữ ký «Người lập phiếu», «Đại diện bên giao», «Đại diện bên nhận»; thường có mã QR và đánh số trang «1/1», «1/2». Không chọn loại này cho biên bản giao nhận hàng, chứng thư chất lượng, đơn đặt hàng hay hóa đơn — kể cả khi chúng được quét chung tệp với phiếu xuất kho.
- **Cụm tiêu đề nhận biết.** «phiếu xuất kho thành phẩm»; «phiếu xuất kho»; «xuất kho thành phẩm»; «lý do xuất kho».
- **Dễ nhầm với** `BB_GIAO_NHAN_HANG_HOA`, `CHUNG_THU_CHAT_LUONG`, `DON_DAT_HANG`, `HOA_DON`. Tiêu đề «phiếu xuất kho», có «lý do xuất kho» và ô Ngày/Ký hiệu/Số → loại này. Tiêu đề «biên bản giao nhận hàng» có bên giao hàng – bên nhận hàng → BB_GIAO_NHAN_HANG_HOA. Bảng chỉ tiêu thử nghiệm → CHUNG_THU_CHAT_LUONG.
- **Lưu ý khi gán.** Trang «2/2» chỉ có chữ ký vẫn thuộc phiếu. Nếu sau phiếu là biên bản giao nhận, biên bản lấy mẫu, chứng thư → tệp là composite khác loại.
- **Ví dụ.** `_PHIẾU XUẤT KHO MUA HÀNG 2026/20260103-02.pdf`; `_PHIẾU XUẤT KHO MUA HÀNG 2026/20260127-03.pdf`; `_PHIẾU XUẤT KHO MUA HÀNG 2026/20260109-04.pdf` (tệp thứ ba là bộ 4 chứng từ: phiếu xuất kho là segment trang 1).

#### 6.29. `BB_GIAO_NHAN_HANG_HOA` — Biên bản giao nhận / giao hàng / nghiệm thu bàn giao hàng hóa

- **Định nghĩa.** Biên bản ghi nhận việc giao và nhận một chuyến hàng xăng dầu giữa bên giao và bên nhận. Tiêu đề «BIÊN BẢN GIAO HÀNG», «BIÊN BẢN GIAO NHẬN HÀNG», «BIÊN BẢN GIAO NHẬN HÀNG HÓA» hoặc «BIÊN BẢN NGHIỆM THU, BÀN GIAO HÀNG HÓA»; thường một trang, là mẫu in sẵn điền tay: tên khách hàng/bên nhận, nơi giao hàng, phương tiện giao hàng (biển số), người nhận, bảng tên hàng – đơn vị – số lượng (lít thực tế, lít 15°C, kg, nhiệt độ, tỷ trọng), và chữ ký «Người vận chuyển (giao hàng)» – «Người nhận hàng» hoặc «Bên giao hàng» – «Bên nhận hàng». Không chọn loại này cho phiếu xuất kho, biên bản lấy mẫu niêm phong, biên bản thanh lý hợp đồng, hay biên bản nhận bồn/trả bồn của hợp đồng mượn bồn.
- **Cụm tiêu đề nhận biết.** «biên bản giao hàng»; «biên bản giao nhận hàng»; «biên bản giao nhận»; «biên bản nghiệm thu, bàn giao hàng hóa»; «biên bản bàn giao hàng hóa».
- **Dễ nhầm với** `PHIEU_XUAT_KHO`, `BB_LAY_MAU`, `BB_THANH_LY_HD`, `HD_MUON_BON`. Nội dung là số lượng hàng đã giao cho bên nhận → loại này. Nội dung là mẫu xăng dầu và số niêm phong → BB_LAY_MAU. Giao/nhận BỒN chứa → HD_MUON_BON. Tiêu đề có «thanh lý» → BB_THANH_LY_HD.
- **Lưu ý khi gán.** Mẫu của công ty («Biên bản giao hàng») và mẫu của nhà cung cấp («Biên bản giao nhận hàng») cùng loại này.
- **Ví dụ.** `_Biên bản giao nhận 2026/bbgn-260102-3.pdf`; `_Biên bản giao nhận 2026/bbgn-260528-6.pdf`; `_PHIẾU XUẤT KHO MUA HÀNG 2026/20260109-04.pdf` (tệp thứ hai chứa 2 biên bản; tệp thứ ba: biên bản giao nhận là segment trang 2).

#### 6.30. `BB_LAY_MAU` — Biên bản lấy mẫu, niêm phong, bàn giao mẫu xăng dầu

- **Định nghĩa.** Biên bản lấy mẫu xăng dầu khi xuất hoặc nhập hàng, theo mẫu của Thông tư 15/2015/TT-BKHCN. Góc trên phải in «Mẫu 1. BBLM-NP-CKCL» (biên bản lấy mẫu, niêm phong, bàn giao mẫu và cam kết chất lượng — lập tại kho bên bán) hoặc «Mẫu 2. BBLM-BGM-KTNP» (biên bản lấy mẫu, bàn giao mẫu và kiểm tra niêm phong — lập tại cửa hàng khi nhập hàng), kèm «15/2015/TT-BKHCN»; tiêu đề «BIÊN BẢN LẤY MẪU, …»; các mục đánh số điền tay: tên, loại xăng dầu; thương nhân xuất hàng; số lượng nhập; doanh nghiệp vận chuyển; phương tiện và biển kiểm soát; số niêm phong trên phương tiện; số niêm phong trên bình mẫu. Mỗi biên bản dài MỘT trang; tệp nhiều trang thường là nhiều biên bản của nhiều chuyến hàng. Không chọn loại này cho biên bản giao nhận hàng, phiếu xuất kho hay chứng thư chất lượng.
- **Cụm tiêu đề nhận biết.** «biên bản lấy mẫu»; «bàn giao mẫu và kiểm tra niêm phong»; «niêm phong, bàn giao mẫu»; «BBLM-BGM-KTNP»; «BBLM-NP-CKCL».
- **Dễ nhầm với** `BB_GIAO_NHAN_HANG_HOA`, `CHUNG_THU_CHAT_LUONG`, `PHIEU_XUAT_KHO`. Có ký hiệu «BBLM» và các số niêm phong → loại này. Có bảng số lượng giao nhận nhưng không có niêm phong mẫu → BB_GIAO_NHAN_HANG_HOA. Có bảng chỉ tiêu thử nghiệm và «Certificate of Quality» → CHUNG_THU_CHAT_LUONG.
- **Lưu ý khi gán.** Mỗi trang là một biên bản → tệp N trang là composite cùng loại với N segment. Mẫu 1 và Mẫu 2 cùng loại này.
- **Ví dụ.** `6. CUA HANG - BB MAU- VÂN/BB mau CH9-21.pdf`; `6. CUA HANG - BB MAU- VÂN/T2_3.pdf`; `6. CUA HANG - BB MAU- VÂN/BB mau CH12-21.pdf` (tệp thứ hai chứa 3 biên bản, tệp thứ ba chứa 93 biên bản).

#### 6.31. `CHUNG_THU_CHAT_LUONG` — Chứng thư chất lượng (Certificate of Quality)

- **Định nghĩa.** Chứng thư do nhà sản xuất hoặc phòng thử nghiệm cấp cho MỘT LÔ xăng dầu, công bố kết quả thử nghiệm chất lượng. Tiêu đề song ngữ «CHỨNG THƯ CHẤT LƯỢNG (Certificate of Quality)»; đầu trang là tên nhà máy lọc dầu/công ty và các chứng chỉ ISO; có tên sản phẩm (ví dụ nhiên liệu điêzen DO 0,05S mức 2), nơi sản xuất, ký hiệu lô (Batch No.), bể chứa, ngày sản xuất, ngày lấy mẫu, số chứng nhận; phần chính là bảng chỉ tiêu – phương pháp thử (TCVN/ASTM) – đơn vị – mức quy định – kết quả; câu kết luận phù hợp QCVN và chữ ký, dấu của bộ phận quản lý chất lượng. Trong kho mẫu, loại này chỉ xuất hiện như một trang trong bộ chứng từ xuất kho. Không chọn loại này cho giấy chứng nhận kiểm định cột đo/xi téc, cho biên bản lấy mẫu hay phiếu xuất kho.
- **Cụm tiêu đề nhận biết.** «chứng thư chất lượng (certificate of quality)»; «certificate of quality»; «phiếu kết quả thử nghiệm».
- **Dễ nhầm với** `GCN_KIEM_DINH_DO_LUONG`, `BB_LAY_MAU`, `PHIEU_XUAT_KHO`. «Certificate of Quality» + bảng chỉ tiêu chất lượng của nhiên liệu → loại này. «Certificate of Verification» của cột đo/xi téc → GCN_KIEM_DINH_DO_LUONG.
- **Ví dụ.** `BSR-2629763-HH 10-06-2026 20-10-37.pdf`; `_PHIẾU XUẤT KHO MUA HÀNG 2026/20260111-06.pdf` (chỉ xuất hiện dưới dạng segment: trang 3 của tệp thứ nhất, trang 4 của tệp thứ hai).

#### 6.32. `HOA_DON` — Hóa đơn bán hàng / hóa đơn giá trị gia tăng

- **Định nghĩa.** Hóa đơn do bên bán lập cho một lần bán hàng hóa, dịch vụ. Tiêu đề «HÓA ĐƠN GIÁ TRỊ GIA TĂNG» hoặc «HÓA ĐƠN BÁN HÀNG»; có «Mẫu số», «Ký hiệu», «Số» hóa đơn, ngày; đơn vị bán hàng và mã số thuế; họ tên người mua, tên đơn vị, mã số thuế, địa chỉ; hình thức thanh toán; bảng tên hàng hóa, dịch vụ – đơn vị tính – số lượng – đơn giá – thành tiền; cộng tiền hàng, thuế suất GTGT, tổng cộng tiền thanh toán, số tiền viết bằng chữ; chữ ký người mua, người bán. Có thể là hóa đơn giấy viết tay hoặc bản in hóa đơn điện tử. Không chọn loại này cho phiếu xuất kho, đơn đặt hàng, bảng báo giá hay biên bản giao nhận.
- **Cụm tiêu đề nhận biết.** «hóa đơn giá trị gia tăng»; «hóa đơn bán hàng»; «hóa đơn gtgt».
- **Dễ nhầm với** `PHIEU_XUAT_KHO`, `DON_DAT_HANG`, `UNREADABLE`. Có mẫu số/ký hiệu/số hóa đơn và mã số thuế hai bên → loại này. Bản quét quá mờ không đọc nổi cả tiêu đề → UNREADABLE.
- **Lưu ý khi gán.** Hai liên/hai hóa đơn khác số trong một tệp là hai segment.
- **Ví dụ.** `6. HOP DONG THUE KHO- Vi/HDB 2017-.pdf` (2 hóa đơn trong một tệp, bản quét rất mờ → confidence=low).

### Nhóm Văn bản hành chính và loại khác (`VAN_BAN_KHAC`)

#### 6.33. `GIAY_UY_QUYEN` — Giấy ủy quyền

- **Định nghĩa.** Văn bản trong đó người đại diện của một tổ chức (bên ủy quyền) giao cho một cá nhân khác (bên được ủy quyền) thay mặt ký kết, giao dịch trong phạm vi và thời hạn nhất định. Tiêu đề «GIẤY ỦY QUYỀN»; số có ký hiệu «UQ» hoặc «GUQ»; có mục «Bên ủy quyền/Người ủy quyền», «Bên được ủy quyền/Người được ủy quyền» (họ tên, chức vụ, giấy tờ cá nhân), «Nội dung ủy quyền/Phạm vi ủy quyền», «Thời hạn ủy quyền: từ… đến…», chữ ký của cả hai người và con dấu tổ chức; thường 1–2 trang. Không chọn loại này cho hợp đồng chỉ nhắc «theo giấy ủy quyền số…» ở phần thông tin các bên, hay cho thông báo thay đổi người đại diện.
- **Cụm tiêu đề nhận biết.** «giấy ủy quyền»; «bên được ủy quyền»; «người được ủy quyền».
- **Dễ nhầm với** `CONG_VAN_THONG_BAO`, `HD_MUA_BAN`. «Giấy ủy quyền» là TIÊU ĐỀ → loại này. Chỉ được nhắc trong ngoặc ở phần Bên A/Bên B của hợp đồng → theo loại hợp đồng. Tiêu đề «thông báo» → CONG_VAN_THONG_BAO.
- **Lưu ý khi gán.** Chỉ khi «GIẤY ỦY QUYỀN» là tiêu đề của văn bản.
- **Có ngày hết hạn cần theo dõi** (trường `ngay_het_han`) — thông tin cho nhóm trích xuất; không ảnh hưởng cách gán nhãn.
- **Ví dụ.** `_3. HOP DONG DAU VAO-Diem/GIAY UY QUYEN PETROLIMEX.pdf`; `_3. HOP DONG DAU VAO-Diem/GUQ - CHỊ NGA - CN GIA LAI 06-11-2024.pdf`.

#### 6.34. `CONG_VAN_THONG_BAO` — Công văn / thông báo / quyết định / quy chế (văn bản hành chính)

- **Định nghĩa.** Văn bản hành chính một chiều do cơ quan nhà nước hoặc một đối tác ban hành để thông báo, chỉ đạo, quy định: «THÔNG BÁO V/v…», công văn có trích yếu «V/v…», «QUYẾT ĐỊNH Ban hành…» kèm quy chế/quy định, kế hoạch. Trình bày theo thể thức văn bản hành chính: tên cơ quan và số, ký hiệu («…/TB-…», «…/QĐ-UBND», «…/CV-…») ở góc trái, quốc hiệu ở góc phải, «Kính gửi» hoặc căn cứ ban hành, nội dung theo điều/khoản, «Nơi nhận» ở cuối, một bên ký và đóng dấu. Không chọn loại này nếu văn bản là giấy phép/giấy chứng nhận/giấy xác nhận cấp cho một chủ thể (dù có chữ «quyết định» trong thân), là hợp đồng, biên bản hai bên ký, hay là quyết định, kế hoạch nằm bên trong tập hồ sơ quản lý PCCC.
- **Cụm tiêu đề nhận biết.** «thông báo v/v»; «quyết định ban hành»; «quy chế hoạt động»; «v/v thay đổi».
- **Dễ nhầm với** `GIAY_UY_QUYEN`, `GCN_DDK_BAN_LE_XD`, `HO_SO_QUAN_LY_PCCC`, `OTHER`. Tiêu đề là «thông báo», «quyết định ban hành…», hoặc công văn «V/v» và chỉ một bên ký → loại này. Giấy có tiêu đề «giấy chứng nhận…/giấy xác nhận…» trình bày dưới dạng quyết định → theo loại giấy đó. Không có thể thức hành chính và không thuộc loại nào → OTHER.
- **Lưu ý khi gán.** Quyết định ban hành + quy chế kèm theo là một tài liệu.
- **Làm rõ (v1.1) — ví dụ quyết định của UBND.** Văn bản của Ủy ban nhân dân tỉnh/huyện có số «…/QĐ-UBND», tiêu đề «QUYẾT ĐỊNH — Ban hành Quy chế …» (kèm quy chế) là `CONG_VAN_THONG_BAO`. Phân biệt: «giấy chứng nhận/giấy xác nhận» của Sở hoặc Bộ trình bày dưới dạng «QUYẾT ĐỊNH: Điều 1. Cấp …» theo loại giấy đó (`GCN_DDK_BAN_LE_XD`, `GXN_THUONG_NHAN_XD`), không phải loại này.
- **Ví dụ.** `_3. HOP DONG DAU VAO-Diem/TB thay đổi người đại diện.pdf`; `Quy che dan tem Thue - 2016-11-01.pdf`.

#### 6.35. `OTHER` — Tài liệu khác (đọc được nhưng không thuộc loại nào trong danh mục)

- **Định nghĩa.** Tài liệu ĐỌC ĐƯỢC, xác định được nội dung, nhưng không khớp định nghĩa của bất kỳ loại nào khác trong danh mục — ví dụ thỏa thuận/hợp đồng cấp tín dụng với ngân hàng, bảng báo giá đứng riêng, biên bản đối chiếu công nợ, bảng lương, thư từ. Chỉ chọn OTHER sau khi đã đối chiếu tiêu đề và cơ quan ban hành với tất cả các loại khác. Không chọn OTHER cho tài liệu không đọc được (dùng UNREADABLE) hoặc cho tài liệu thuộc một loại đã có nhưng bản quét xấu.
- **Cụm tiêu đề nhận biết.** Không có (nhãn đặc biệt).
- **Dễ nhầm với** `UNREADABLE`, `CONG_VAN_THONG_BAO`. Đọc được tiêu đề nhưng danh mục không có loại tương ứng → OTHER, và ghi tiêu đề vào cột evidence. Không đọc được → UNREADABLE.
- **Lưu ý khi gán.** Bắt buộc ghi tiêu đề nguyên văn vào evidence để nhóm dữ liệu cân nhắc mở loại mới.
- **Ví dụ.** `_3. HOP DONG DAU VAO-Diem/L2609…_Thỏa thuận chung (đã ký số).pdf` (`doc_id` = `e8cfd1798742`) (tiêu đề «THỎA THUẬN CHUNG về việc cấp và sử dụng tín dụng»).

#### 6.36. `UNREADABLE` — Không đọc được

- **Định nghĩa.** Tệp hoặc đoạn trang mà người gán nhãn không thể xác định loại tài liệu dù đã phóng to và xem hết các trang: ảnh quá mờ, quá tối hoặc cháy sáng, bị che, bị cắt mất phần tiêu đề và nội dung, quét nhầm mặt giấy than, hoặc tệp hỏng. Trang trắng hoặc mặt sau trống nằm giữa một tài liệu KHÔNG phải UNREADABLE (nó thuộc tài liệu chứa nó). Bản quét xấu nhưng vẫn đọc được tiêu đề hoặc đủ dấu hiệu nhận ra loại thì gán loại đó với confidence=low, không dùng UNREADABLE.
- **Cụm tiêu đề nhận biết.** Không có (nhãn đặc biệt).
- **Dễ nhầm với** `OTHER`, `BAN_VE_KY_THUAT`. Không đọc được → UNREADABLE. Đọc được nhưng ngoài danh mục → OTHER.
- **Lưu ý khi gán.** Trong segments, dùng UNREADABLE cho các trang không đọc được nằm giữa các tài liệu khác.
- **Ví dụ.** kho mẫu chưa có tệp nào phải gán UNREADABLE cho cả tệp.

## 7. Tệp chứa nhiều tài liệu (composite)

### 7.1. Định nghĩa

- `is_composite=0`: tệp là **một** tài liệu logic, dù nhiều trang (hợp đồng nhiều trang, thẻ hai mặt, giấy chứng nhận kèm trang quy định, hợp đồng kèm phụ lục của chính nó, một tập hồ sơ có bìa chung).
- `is_composite=1`: tệp chứa **từ hai tài liệu logic trở lên**. Có hai kiểu:
  - **khác loại**: các segment có `doc_type` khác nhau (ví dụ phiếu xuất kho + chứng thư + biên bản giao nhận + biên bản lấy mẫu);
  - **cùng loại**: mọi segment cùng `doc_type` nhưng là các bản khác nhau (chứng nhận của hai người, giấy của hai xe, 93 biên bản lấy mẫu của 93 chuyến hàng).

Kho mẫu hiện có 21 tệp composite trên 304 tệp duy nhất: 8 khác loại, 13 cùng loại (theo `data/labels_v2.csv`, nhãn do mô hình gán, chưa có người của công ty duyệt).

Trường hợp thường gặp của kiểu **khác loại**: bộ chứng từ của một chuyến hàng mua vào — **phiếu xuất kho của nhà cung cấp, theo sau là biên bản giao nhận** (có thể kèm chứng thư chất lượng, biên bản lấy mẫu) — luôn là composite khác loại, segment đầu là `PHIEU_XUAT_KHO` (ví dụ 1 và 2 ở mục 7.4).

### 7.2. Phép thử kèm theo — khi nào mở segment mới

Hỏi: **«Nếu cắt đoạn trang này ra thành một tệp riêng, nó sẽ được gán nhãn gì?»**

| Câu trả lời | Quyết định |
|---|---|
| Một `doc_type` trong danh mục, **khác** loại của tài liệu đứng ngay trước và khác `OTHER` | **Segment mới** |
| **Cùng** `doc_type` với tài liệu đứng trước nhưng là **bản khác**: khác người, khác xe/thiết bị, khác số hoặc ngày văn bản, khác hợp đồng | **Segment mới** (composite cùng loại) |
| Cùng `doc_type`, cùng chủ thể, cùng văn bản — chỉ là trang tiếp theo, mặt sau, phụ lục, phần thực hiện của chính nó | **Không tách**: thuộc tài liệu đứng trước |
| Đứng riêng sẽ chỉ là `OTHER` và nó tham chiếu/đi kèm tài liệu đứng trước (bảng báo giá, bảng kê, bảng xác định khối lượng, danh mục, ảnh chụp) | **Không tách**: thuộc tài liệu đứng trước |
| Đứng riêng là `OTHER` và **không liên quan** tới tài liệu đứng trước | **Segment mới** với loại `OTHER` |
| Trang trắng, mặt sau trống | Thuộc tài liệu đứng trước (nếu ở đầu tệp: thuộc tài liệu đứng sau) |
| **Trang cuối chỉ có chữ ký / con dấu** (ví dụ «Người lập phiếu – Đại diện bên giao – Đại diện bên nhận», trang «2/2») | Thuộc tài liệu đứng ngay trước, kể cả khi trang đó lặp lại tiêu đề hoặc tên đơn vị ở đầu trang (v1.1) |
| Bìa và mặt trong của cùng một thẻ/giấy gập, thứ tự bất kỳ | Một tài liệu (v1.1) |
| Trang không đọc được nằm giữa các tài liệu | Segment `UNREADABLE` |

Danh sách **không tách** thường gặp trong kho mẫu:

- «BIÊN BẢN NHẬN BỒN», «BIÊN BẢN TRẢ BỒN» trong tệp hợp đồng mượn bồn → thuộc `HD_MUON_BON`.
- «NHỮNG ĐIỀU QUY ĐỊNH» sau giấy chứng nhận cửa hàng đủ điều kiện bán lẻ xăng dầu → thuộc `GCN_DDK_BAN_LE_XD`.
- «Giấy xác nhận về việc thay đổi nội dung đăng ký doanh nghiệp», «Công bố nội dung đăng ký doanh nghiệp» của chính doanh nghiệp đó → thuộc `GCN_DKDN`.
- «DANH MỤC HÀNG HÓA NGUY HIỂM… ĐƯỢC PHÉP VẬN CHUYỂN» (trang 2 của giấy phép) → thuộc `GP_VC_HANG_NGUY_HIEM`; danh mục tài liệu, bản vẽ được thẩm duyệt (trang 2) → thuộc `GCN_PCCC_CO_SO`.
- «KẾT QUẢ KIỂM ĐỊNH» (barem) sau giấy chứng nhận kiểm định xi téc → thuộc `GCN_KIEM_DINH_DO_LUONG`.
- «BẢNG BÁO GIÁ» đính sau hợp đồng mua bán; «BẢNG XÁC ĐỊNH KHỐI LƯỢNG CÔNG VIỆC HOÀN THÀNH» đính sau biên bản thanh lý.
- Trang bìa hợp đồng, trang chữ ký «2/2» của phiếu xuất kho (và mọi trang cuối chỉ có chữ ký, con dấu), mặt sau thẻ, ảnh chụp phương tiện, trang trắng do quét hai mặt.
- Mọi thành phần bên trong tập `HO_SO_QUAN_LY_PCCC` và `BIEN_PHAP_UNG_PHO_SU_CO` (quy tắc «tập có bìa chung»).

### 7.3. Cách ghi

- `segments` = các đoạn nối bằng dấu `;`, mỗi đoạn `<trang đầu>-<trang cuối>:<DOC_TYPE>`; đoạn một trang viết `3:DOC_TYPE`. Không có khoảng trắng.
- Các đoạn **liên tiếp, không chồng nhau, bắt đầu từ trang 1 và kết thúc ở trang cuối** (bằng `page_count` trong manifest). Trang nào cũng thuộc đúng một đoạn.
- `is_composite=0` ⇒ `segments` để **trống**. `is_composite=1` ⇒ `segments` có ít nhất 2 đoạn.
- **Nhãn chính** `doc_type` của tệp composite = `doc_type` của **segment đầu tiên** (bỏ qua segment `UNREADABLE` ở đầu nếu có). Quy tắc này máy kiểm tra được, đừng chọn theo cảm tính «tài liệu nào quan trọng hơn».
- Đơn vị nhỏ nhất là **trang**. Hai giấy in trên cùng một trang ảnh (ví dụ tờ bảo hiểm có cả giấy bắt buộc và tự nguyện) thuộc cùng một segment; ghi `note`.
- **Hai tài liệu cùng loại dùng chung một trang** (v1.1) — ví dụ phần cuối của giấy thứ nhất và phần đầu của giấy thứ hai nằm trên cùng một trang quét: trang đó thuộc **một** segment, **không** cố cắt đôi trang. Quyết định bằng phép thử ở 7.2 trên các trang còn lại; ghi `note` «2 tài liệu trên 1 trang» (và «ranh giới?» nếu không chắc có phải hai bản khác nhau). Trường hợp **khác loại** dùng chung một trang chưa có quy tắc: gán theo cách hiểu tốt nhất và ghi `GUIDE:`.
- Tệp rất dài gồm nhiều bản cùng mẫu, mỗi trang một bản (biên bản lấy mẫu): vẫn ghi đủ từng trang. Tạo chuỗi bằng công thức, đừng gõ tay:
  Excel `=TEXTJOIN(";";TRUE;SEQUENCE(93)&":BB_LAY_MAU")` (hoặc dấu phẩy thay dấu chấm phẩy tùy máy);
  Python `";".join(f"{i}:BB_LAY_MAU" for i in range(1, 94))`. Sau đó lướt hết các trang để chắc rằng không có trang nào khác mẫu.

### 7.4. Ví dụ có lời giải

| # | Tệp (số trang) | Nhìn thấy gì | `doc_type` | `is_composite` | `segments` |
|---|---|---|---|---|---|
| 1 | `BSR-2629763-HH 10-06-2026 20-10-37.pdf` (5) | tr.1–2 phiếu xuất kho (tr.2 chỉ có chữ ký), tr.3 chứng thư chất lượng, tr.4 biên bản giao nhận hàng, tr.5 biên bản lấy mẫu | `PHIEU_XUAT_KHO` | 1 | `1-2:PHIEU_XUAT_KHO;3:CHUNG_THU_CHAT_LUONG;4:BB_GIAO_NHAN_HANG_HOA;5:BB_LAY_MAU` |
| 2 | `_PHIẾU XUẤT KHO MUA HÀNG 2026/20260109-04.pdf` (4) | tr.1 phiếu xuất kho, tr.2 biên bản giao nhận hàng, tr.3 biên bản lấy mẫu (Mẫu 1), tr.4 chứng thư chất lượng | `PHIEU_XUAT_KHO` | 1 | `1:PHIEU_XUAT_KHO;2:BB_GIAO_NHAN_HANG_HOA;3:BB_LAY_MAU;4:CHUNG_THU_CHAT_LUONG` |
| 3 | `_PHIẾU XUẤT KHO MUA HÀNG 2026/20260127-03.pdf` (2) | phiếu xuất kho đánh số 1/2 và 2/2 | `PHIEU_XUAT_KHO` | 0 | *(trống)* |
| 4 | `_4. THANH LÝ HỢP ĐỒNG/TLHD 11.20-SU DOAN 31.pdf` (5) | tr.1–2 «biên bản nghiệm thu, bàn giao hàng hóa»; tr.3–4 «thanh lý hợp đồng kinh tế»; tr.5 «bảng xác định khối lượng công việc hoàn thành» (đứng riêng sẽ là OTHER, đi kèm bản thanh lý) | `BB_GIAO_NHAN_HANG_HOA` | 1 | `1-2:BB_GIAO_NHAN_HANG_HOA;3-5:BB_THANH_LY_HD` |
| 5 | `_5. HOP DONG VAN CHUYEN/HDVC 2020-TOAN THINH-01.01-31.12.pdf` (4) | tr.1–2 hợp đồng vận chuyển; tr.3–4 giấy đăng ký doanh nghiệp của đối tác | `HD_VAN_CHUYEN` | 1 | `1-2:HD_VAN_CHUYEN;3-4:GCN_DKDN` |
| 6 | `6. HOP DONG MUON BON/HDMBCD-02.2020-TRUONG HUNG-02.01.2020.pdf` (6) | tr.1–2 hợp đồng mượn bồn; tr.3 biên bản nhận bồn; tr.5 biên bản trả bồn; tr.4, 6 trắng | `HD_MUON_BON` | 0 | *(trống)* |
| 7 | `_1. Giay DKKD khach hang/GPKD-THÀNH LIÊN.pdf` (7) | tr.1–2 giấy đăng ký doanh nghiệp; tr.3–7 công bố nội dung đăng ký của chính doanh nghiệp đó | `GCN_DKDN` | 0 | *(trống)* |
| 8 | `_2. Giay Du Dieu Kien Khach hang/DDK-CHIN LOAN-12.1.28.pdf` (3) | tr.1–2 giấy chứng nhận; tr.3 «những điều quy định» | `GCN_DDK_BAN_LE_XD` | 0 | *(trống)* |
| 9 | `9. TỔNG HỢP HỒ SƠ CỬA HÀNG/MT 2 nhân vien GH3_2.pdf` (4) | chứng nhận BVMT của người thứ nhất (tr.1 mặt trong, tr.2 bìa), của người thứ hai (tr.3 mặt trong, tr.4 bìa) | `CC_NGHIEP_VU_BVMT` | 1 | `1-2:CC_NGHIEP_VU_BVMT;3-4:CC_NGHIEP_VU_BVMT` |
| 10 | `5. TỔNG HỢP HỒ SƠ XE/1. Xe 08001-02645-15.2.24.pdf` (2) | hai giấy biên nhận thế chấp: tr.1 cho đầu kéo, tr.2 cho rơ moóc | `BIEN_NHAN_THE_CHAP_PT` | 1 | `1:BIEN_NHAN_THE_CHAP_PT;2:BIEN_NHAN_THE_CHAP_PT` |
| 11 | `6. CUA HANG - BB MAU- VÂN/T2_3.pdf` (3) | ba biên bản lấy mẫu của ba chuyến hàng | `BB_LAY_MAU` | 1 | `1:BB_LAY_MAU;2:BB_LAY_MAU;3:BB_LAY_MAU` |
| 12 | `8. CUA HANG - TU K.TRA PCCC- VÂN/CH12-T1+T2.pdf` (26) | bìa «hồ sơ quản lý công tác PCCC», nội quy, quyết định, các sổ theo dõi, báo cáo, 2 biên bản tự kiểm tra | `HO_SO_QUAN_LY_PCCC` | 0 | *(trống)* |
| 13 | `5. TỔNG HỢP HỒ SƠ XE/BHDS 13420 (2-1-23).pdf` (2) | một tờ gập in cả giấy bảo hiểm bắt buộc TNDS và tự nguyện; tr.1 và tr.2 là hai mặt của tờ đó | `GCN_BAO_HIEM` | 0 | *(trống)*; `note`: «2 giấy trên cùng một tờ» |
| 14 | `5. TỔNG HỢP HỒ SƠ XE/Barem 77R- 01926-31.12.22.pdf` (2) | giấy chứng nhận kiểm định xi téc + trang kết quả kiểm định | `GCN_KIEM_DINH_DO_LUONG` | 0 | *(trống)* |

**Giới hạn của bảng ví dụ này (v1.1).** Cột «Tệp» là tên tệp **thật** của kho mẫu. Người gán nhãn đọc hướng dẫn có thể chép lại đáp án thay vì tự phán đoán, nên với các tệp này sự đồng thuận giữa hai người **không** chứng minh hướng dẫn đủ rõ. Vì vậy mọi báo cáo đồng thuận phải nêu thêm số liệu **loại trừ các tệp được nêu tên trong hướng dẫn** (mục 10.3 và 10.6). Không thêm tên tệp thật vào hướng dẫn nếu không ghi vào nhật ký mục 11 (cột `in_guideline` do `agreement.py` tự tính từ chính văn bản này).

Các tình huống **chưa gặp trong kho mẫu nhưng sẽ gặp khi vận hành** (áp dụng cùng phép thử):

- Hợp đồng và biên bản thanh lý của chính nó quét chung: `1-2:HD_MUA_BAN;3:BB_THANH_LY_HD` (thanh lý là một `doc_type` khác → tách).
- Thẻ chứng nhận kèm bản chụp căn cước của người đó: `1-2:CC_TAP_HUAN_VC_HNH;3:CCCD` (căn cước là `doc_type` khác → tách).
- Một tệp gom thẻ của nhiều người: mỗi người một segment.
- Bộ hồ sơ xe quét chung (đăng ký + bảo hiểm + đăng kiểm): mỗi giấy một segment theo thứ tự trang.

## 8. Khi không chắc

- **Phân vân giữa hai loại**: chọn loại khớp **tiêu đề** hơn; ghi `confidence=low` và `note` có `alt=<MÃ LOẠI THỨ HAI>`.
- **Tiêu đề mờ, nhưng cơ quan cấp và bố cục đủ rõ**: gán loại đó, `confidence=medium`.
- **Tệp quá dài, chỉ xem kỹ một phần** (ví dụ lướt nhanh 93 trang): `confidence=medium`, ghi `note` «đã lướt toàn bộ, đọc kỹ n trang».
- **Đọc được nhưng danh mục không có loại phù hợp**: `OTHER`, chép tiêu đề vào `evidence`. Đừng ép vào loại «gần giống».
- **Không đọc được**: `UNREADABLE`. Không dùng `UNREADABLE` cho trang trắng hay cho bản quét xấu mà vẫn đọc được tiêu đề.
- **Không chắc đoạn trang có phải tài liệu riêng không**: làm phép thử ở mục 7.2; nếu vẫn phân vân, chọn **không tách** và ghi `note` «ranh giới?» để người phân xử xem lại.
- **Thấy quy tắc trong hướng dẫn mâu thuẫn hoặc thiếu**: vẫn gán theo cách hiểu tốt nhất, ghi `note` bắt đầu bằng `GUIDE:` và mô tả vấn đề. Các ghi chú `GUIDE:` được gom lại ở bước đối chiếu để sửa hướng dẫn (mục 10.5).
- Không hỏi người gán nhãn kia về một tệp cụ thể trước khi nộp. Câu hỏi về **cách hiểu quy tắc** gửi cho người phụ trách dữ liệu; câu trả lời được ghi vào nhật ký (mục 11) để cả hai người cùng áp dụng.

### 8.1. Người gán nhãn chỉ thấy một phần số trang (v1.1)

Áp dụng khi bạn chỉ có văn bản hoặc ảnh của **một số trang đầu** (ví dụ gói gán nhãn chỉ chứa 2 trang đầu) trong khi tệp dài hơn. Nguyên tắc: **không khẳng định điều bạn chưa thấy.**

1. **`doc_type`**: gán theo tài liệu bạn thấy ở đầu tệp (nhãn chính là loại của segment đầu tiên nên thường vẫn xác định được). Nếu các trang đã xem chỉ là bìa, trang trắng hay mặt thẻ không có tiêu đề (xem mục 6.12, 6.14, 6.17) thì `confidence=low` và nêu cả `alt=`.
2. **`confidence`**: tối đa `medium` cho mọi tệp chưa xem hết trang.
3. **`note`** bắt đầu bằng `PARTIAL:` kèm số trang đã xem trên tổng số trang, ví dụ `PARTIAL: đã xem tr.1-2/5`.
4. **`is_composite` và `segments`**: chỉ ghi `is_composite=1` và các segment khi bạn **thật sự thấy** ranh giới. Với phần chưa xem, để `is_composite=0`, `segments` trống và thêm vào `note` «chưa xem tr.3-5, có thể còn tài liệu khác». **Không** suy ranh giới từ tên tệp, số trang hay từ việc tệp nằm trong một bộ có nhiều tệp composite.
5. Người phân xử (mục 10.4) coi mọi dòng có `PARTIAL:` là cần mở lại tệp với **đủ trang** và quyết định `is_composite`/`segments` từ đó. Nhãn `is_composite`/`segments` chính thức của dự án lấy từ người đã xem **toàn bộ** trang.

## 9. Định dạng tệp nhãn

Một tệp CSV cho mỗi người gán nhãn, mã hóa **UTF-8**, dấu phân cách là dấu phẩy, ô có dấu phẩy hoặc dấu chấm phẩy đặt trong ngoặc kép. Đúng 7 cột, đúng thứ tự:

| Cột | Giá trị | Quy tắc |
|---|---|---|
| `doc_id` | mã 12 ký tự trong `data/manifest.csv` | Mỗi `doc_id` của manifest xuất hiện **đúng một lần** (336 dòng). Không thêm, không bớt. |
| `doc_type` | một `id` trong `data/taxonomy_v2.json` | Viết hoa, đúng chính tả. Với tệp composite: loại của segment đầu tiên. |
| `is_composite` | `0` hoặc `1` | Theo mục 7.1. |
| `segments` | trống, hoặc `1-2:PHIEU_XUAT_KHO;3:CHUNG_THU_CHAT_LUONG` | Trống khi `is_composite=0`. Trang đếm từ 1, phủ kín 1…`page_count`. |
| `confidence` | `high` / `medium` / `low` | `high`: đọc rõ tiêu đề, khớp định nghĩa. `medium`: thiếu tiêu đề rõ nhưng đủ căn cứ khác, hoặc có cân nhắc về ranh giới. `low`: phải chọn giữa hai loại. |
| `evidence` | tiêu đề hoặc dấu hiệu đã quyết định nhãn, ≤ 120 ký tự | Chép **tiêu đề văn bản** (có dấu). **Không** chép họ tên cá nhân, số căn cước, số giấy phép lái xe, số điện thoại, số tài khoản, địa chỉ nhà. |
| `note` | chữ tự do | `alt=<MÃ>`, «2 giấy trên cùng một tờ», «scan mờ», «xoay 90°», `GUIDE: …`. Có thể để trống. |

Ví dụ (5 dòng):

```csv
doc_id,doc_type,is_composite,segments,confidence,evidence,note
9f4c4dae0c73,PHIEU_XUAT_KHO,1,1-2:PHIEU_XUAT_KHO;3:CHUNG_THU_CHAT_LUONG;4:BB_GIAO_NHAN_HANG_HOA;5:BB_LAY_MAU,high,PHIẾU XUẤT KHO THÀNH PHẨM,bộ 4 chứng từ một chuyến hàng
3376b0c936f1,HD_MUON_BON,0,,high,HỢP ĐỒNG MƯỢN BỒN CHỨA DẦU,kèm biên bản nhận bồn và trả bồn (không tách)
57374da27cae,HD_VAN_CHUYEN,1,1-2:HD_VAN_CHUYEN;3-4:GCN_DKDN,high,HỢP ĐỒNG VẬN CHUYỂN HÀNG HÓA,kèm giấy đăng ký doanh nghiệp của đối tác
e8cfd1798742,OTHER,0,,high,THỎA THUẬN CHUNG về việc cấp và sử dụng tín dụng,đề xuất loại mới: hợp đồng/thỏa thuận tín dụng
dc3847632556,BB_THANH_LY_HD,0,,low,BIÊN BẢN THANH LÝ HỢP ĐỒNG (đọc được một phần),scan rất mờ
```

**Tệp trùng lặp.** 62 tệp trong manifest là bản sao giống hệt nhau từng byte (30 nhóm, cột `exact_dup_group`). Các tệp cùng nhóm **bắt buộc có nhãn giống hệt nhau**
ở mọi cột trừ `doc_id`. Cách làm: gán nhãn một tệp trong nhóm rồi sao chép sang các tệp còn lại.

**Kiểm tra tự động trước khi nộp** (người phụ trách dữ liệu chạy script kiểm; tệp không qua thì trả lại):

1. Tập `doc_id` trùng khít với manifest; không dòng lặp.
2. `doc_type` và mọi loại trong `segments` thuộc danh mục.
3. `is_composite` ∈ {0, 1}; `segments` trống ⇔ `is_composite=0`; nếu có thì ≥ 2 đoạn, liên tiếp, phủ kín 1…`page_count`.
4. `doc_type` = loại của segment đầu tiên khác `UNREADABLE`.
5. Các tệp cùng `exact_dup_group` có nhãn giống nhau.
6. `confidence` hợp lệ; `evidence` không trống, ≤ 120 ký tự, không chứa dãy từ 9 chữ số trở lên (dấu hiệu chép nhầm số định danh).
7. `doc_type=OTHER` thì `evidence` phải là tiêu đề văn bản.

## 10. Quy trình bảo đảm chất lượng

### 10.1. Vòng hiệu chỉnh (trước khi gán toàn bộ)

1. Hai người gán nhãn (A, B) cùng đọc hướng dẫn này và 14 ví dụ ở mục 7.4.
2. Mỗi người gán **độc lập** 40 tệp do người phụ trách dữ liệu chọn: mỗi thư mục cũ ít nhất 1 tệp, hai thư mục «TỔNG HỢP HỒ SƠ» mỗi thư mục 6 tệp, và ít nhất 6 tệp nhiều trang.
3. Tính Cohen κ trên 40 tệp, họp đối chiếu mọi bất đồng, sửa hướng dẫn, ghi nhật ký (mục 11). 40 tệp này được gán lại trong vòng chính.

### 10.2. Vòng chính: hai người gán độc lập toàn bộ

- A và B mỗi người nộp một tệp CSV đủ 336 dòng (trong lần chạy đầu: `teams/00_data_and_eval/annotation/annotator_A_opus_designer.csv` và `annotator_B_sonnet.csv`; B làm trên bản chép văn bản 2 trang đầu, nên chỉ nộp 304 dòng của tài liệu duy nhất).
- Thứ tự tệp được **xáo trộn khác nhau** cho mỗi người (không đi theo thư mục) để giảm việc «đoán theo thư mục».
- Không sửa nhãn sau khi đã xem nhãn của người kia.

### 10.3. Đo đồng thuận

Tính trên **tệp duy nhất** (mỗi `exact_dup_group` lấy một đại diện → 304 tệp), để các bản sao không thổi phồng điểm số.

| Chỉ số | Cách tính | Ngưỡng |
|---|---|---|
| **Cohen κ trên `doc_type`** (chỉ số chính) | hai người, 304 tệp, nhãn là `doc_type` | **κ ≥ 0,85** |
| κ trên `group` | quy `doc_type` về nhóm cấp 1 | ≥ 0,90 |
| κ trên `is_composite` | nhị phân | ≥ 0,85 |
| Khớp ranh giới | trên các tệp mà ít nhất một người đánh composite: tỉ lệ tệp có `segments` giống hệt; và F1 của tập vị trí ranh giới (trang bắt đầu segment) | báo cáo, chưa đặt ngưỡng |
| Đồng thuận theo từng loại | với mỗi `doc_type`: 2·(số tệp cả hai cùng gán) / (số A gán + số B gán) | xem xét mọi loại < 0,80 |
| **Mọi chỉ số trên, tính lại sau khi loại các tệp được nêu tên trong hướng dẫn** (v1.1) | cùng công thức, trên tập con các tệp mà tên không xuất hiện trong văn bản hướng dẫn này (`agreement.py` cột `in_guideline`) | bắt buộc báo cáo cạnh số liệu toàn bộ |

Cohen κ = (p_o − p_e) / (1 − p_e), với p_o là tỉ lệ tệp hai người gán giống nhau, p_e là tỉ lệ giống nhau kỳ vọng do ngẫu nhiên tính từ phân bố nhãn của từng người
(`sklearn.metrics.cohen_kappa_score(a, b)`). Báo cáo kèm khoảng tin cậy 95% bằng bootstrap theo tệp (1000 lần lấy mẫu lại).
Vì 10 loại lớn chiếm khoảng 3/4 số tệp, κ tổng thể có thể cao trong khi các loại hiếm vẫn bất đồng — do đó phải xem thêm bảng đồng thuận theo từng loại và ma trận nhầm lẫn A×B.

### 10.4. Phân xử (adjudication)

1. Lập danh sách phân xử gồm: mọi tệp A ≠ B ở bất kỳ cột nào trong `doc_type`, `is_composite`, `segments`; mọi tệp có `confidence=low` của bất kỳ ai; mọi tệp `OTHER`/`UNREADABLE`; mọi tệp có `note` chứa `GUIDE:` hoặc «ranh giới?».
2. Người phân xử là người thứ ba (trưởng nhóm dữ liệu), mở lại tệp PDF, quyết định theo hướng dẫn và ghi lý do một dòng. Nếu vướng nghiệp vụ → đưa vào danh sách câu hỏi cho chủ nghiệp vụ của công ty, tạm gán `confidence=low`.
3. Quyết định phân xử ghi vào `teams/00_data_and_eval/annotation/adjudication.csv` (cột `doc_id, doc_type, is_composite, segments, note`); `scripts/build_labels_v2.py` đọc tệp này và sinh lại `data/labels_v2.csv` (cột `review_status` = `adjudicated` cho các dòng đó). Lý do một dòng ghi trong `note`. (Bản nháp đầu của mục này nói tới `data/labels_v2_gold.csv`; tệp đó không tồn tại — quy trình thật là như trên.)
4. Lưu cả ba nguồn (A, B, `adjudication.csv`) để tái lập được κ và `labels_v2.csv`.

### 10.5. Nếu κ < 0,85

1. Xem ma trận nhầm lẫn A×B, tìm các cặp loại gây bất đồng nhiều nhất.
2. Phân loại nguyên nhân: (a) hướng dẫn mơ hồ → sửa định nghĩa hoặc dấu hiệu quyết định; (b) hai loại thực sự không tách được bằng nội dung → đề xuất gộp loại (đổi taxonomy, tăng `version`); (c) lỗi bất cẩn → nhắc lại quy trình.
3. Ghi thay đổi vào nhật ký (mục 11); **gán lại độc lập** các tệp thuộc những loại bị ảnh hưởng (không chỉ sửa các tệp bất đồng); tính lại κ.
4. Chỉ công bố bộ nhãn gold khi κ ≥ 0,85 hoặc khi trưởng nhóm ghi rõ lý do chấp nhận mức thấp hơn.

### 10.6. Giới hạn đã biết của lần gán nhãn đầu, 2026-10-11 (v1.1)

1. **Ví dụ trong hướng dẫn dùng tên tệp thật** (mục 7.4 và các mục «Ví dụ» ở mục 6). Theo `teams/00_data_and_eval/annotation/agreement_summary.json`, 76/304 tài liệu duy nhất có tên được nêu trong hướng dẫn và 228/304 thì không; đồng thuận `doc_type` là 1,0 ở cả hai nhóm. Số 228 mới là số có giá trị chứng minh; số 76 có thể là chép đáp án.
2. **Hai người gán không độc lập với hướng dẫn và với nhau.** Annotator A là mô hình đồng thời là người thiết kế taxonomy và viết hướng dẫn, xem ảnh trang; annotator B là mô hình khác, chỉ đọc bản chép văn bản của 2 trang đầu (xem mục 8.1). Cả hai đều là mô hình AI. κ(`doc_type`) = 1,0 trên 304 tài liệu **không chứng minh nhãn đúng** — lỗi chung do cùng hướng dẫn vẫn có thể có.
3. **`is_composite` / `segments`** của dự án lấy từ A (đã xem đủ trang); B chỉ thấy 2 trang đầu nên đồng thuận composite thấp hơn (κ = 0,86 trong `agreement_summary.json`: 16 tệp cả hai đánh dấu, 5 tệp chỉ A đánh dấu, 0 tệp chỉ B đánh dấu).
4. **Chưa có người của công ty nào duyệt nhãn.** Việc này nằm trong kế hoạch của nhóm dữ liệu (`teams/00_data_and_eval/README.md`).
5. Khi báo cáo κ hay độ chính xác nhãn, luôn nêu: (a) con số toàn bộ, (b) con số loại trừ tệp nêu tên trong hướng dẫn, (c) ai/mô hình nào đã gán và đã xem bao nhiêu trang.

## 11. Nhật ký thay đổi hướng dẫn

Mỗi lần sửa hướng dẫn hoặc taxonomy phải thêm một dòng. Không sửa lặng lẽ. Nhãn đã gán trước thay đổi phải được rà lại cho các loại bị ảnh hưởng.

| Ngày | Phiên bản | Thay đổi | Lý do / bằng chứng | Tệp cần rà lại |
|---|---|---|---|---|
| 2026-10-11 | 0.1 (nháp) | Bản nháp đầu: mỗi trang có tiêu đề + khối chữ ký riêng là một segment | — | — |
| 2026-10-11 | 0.2 | Thêm «phép thử kèm theo» (mục 7.2): biên bản nhận bồn/trả bồn, giấy xác nhận thay đổi đăng ký doanh nghiệp, «những điều quy định», bảng báo giá, bảng xác định khối lượng **không** tách | Pilot: quy tắc 0.1 biến ít nhất 5/9 hợp đồng mượn bồn và 3 giấy đăng ký doanh nghiệp thành composite, trái với cách doanh nghiệp dùng chúng | `HD_MUON_BON`, `GCN_DKDN`, `GCN_DDK_BAN_LE_XD` |
| 2026-10-11 | 0.3 | Thêm quy tắc «tập có bìa chung» cho `HO_SO_QUAN_LY_PCCC`, `BIEN_PHAP_UNG_PHO_SU_CO` | Pilot: tập PCCC 26–53 trang có hơn 10 tiêu đề con (quyết định, kế hoạch, biên bản) | hai thư mục «TU K.TRA PCCC» |
| 2026-10-11 | 0.4 | Tách khái niệm composite **cùng loại** / **khác loại**; nhãn chính = segment đầu tiên | Pilot: tệp 2 giấy biên nhận thế chấp, tệp 93 biên bản lấy mẫu vẫn có một `doc_type` rõ ràng; tệp «TLHD 11.20» cần quy tắc máy kiểm tra được | mọi tệp nhiều trang |
| 2026-10-11 | 0.5 | Thêm loại `BAN_VE_KY_THUAT`, `CONG_VAN_THONG_BAO`; `OTHER` chỉ còn cho tài liệu thật sự ngoài danh mục | Pilot: 4 bản vẽ và 2 văn bản hành chính rơi vào OTHER | thư mục hồ sơ cửa hàng, thư mục đầu vào |
| 2026-10-11 | 0.6 | Đơn vị segment là trang; hai giấy trên cùng một trang không tách | Pilot: tờ bảo hiểm in cả giấy bắt buộc và tự nguyện | `GCN_BAO_HIEM` |
| 2026-10-11 | **1.0** | Bản phát hành cho vòng hiệu chỉnh | — | — |
| 2026-10-11 | 1.1 | Thêm mục 4.1 «Quy tắc ưu tiên bổ sung»: (1) tiêu đề thắng tên/ngành nghề bên ký kết; (2) «HỢP ĐỒNG KINH TẾ» mua bồn/xe/thiết bị là `HD_MUA_BAN` (quy tắc ưu tiên, đã có ở 6.1); (3) `BB_THANH_LY_HD` áp dụng bất kể loại hợp đồng gốc, thêm ví dụ đại lý, nhượng quyền, thuê kho ở 6.6; (4) chứng chỉ của người ngoài công ty vẫn theo tiêu đề (6.12); (5) dấu hiệu thay tiêu đề cho thẻ không có tiêu đề: «Số GCNBH», «Tên chủ xe / Owner's full name» (6.26, 6.17); (6) thứ tự bìa/mặt trong của thẻ không quan trọng; (7) `GCN_DDK_BAN_LE_XD` và `GCN_PCCC_CO_SO` áp dụng cho ghe/tàu bán xăng dầu (6.8, 6.22). **Không đổi định nghĩa, tiêu đề nhận biết hay mã loại nào.** | Phản hồi của người gán nhãn ở lần gán đầu | Nhãn hiện có **chưa được rà lại theo 1.1**: `HD_MUA_BAN`, `BB_THANH_LY_HD`, `CC_TAP_HUAN_VC_HNH`, `GCN_BAO_HIEM`, `DANG_KY_PHUONG_TIEN`, `GCN_DDK_BAN_LE_XD`, `GCN_PCCC_CO_SO` |
| 2026-10-11 | 1.1 | Làm rõ thêm ở mục 6 và 7: `HO_SO_QUAN_LY_PCCC` khi tệp bắt đầu bằng «Sổ theo dõi…» và không có bìa chung (6.23); `DON_DAT_HANG` có khối nhà cung cấp xác nhận (6.27); ví dụ quyết định UBND số «…/QĐ-UBND» là `CONG_VAN_THONG_BAO` (6.34); trang cuối chỉ có chữ ký/con dấu thuộc tài liệu đứng trước (bảng 7.2); hai tài liệu cùng loại dùng chung một trang là một segment (7.3); phiếu xuất kho của nhà cung cấp + biên bản giao nhận luôn là composite khác loại (7.1) | Phản hồi của người gán nhãn; ghi chú `GUIDE:` và «ranh giới?» trong các tệp nhãn | `HO_SO_QUAN_LY_PCCC`, `DON_DAT_HANG`, `CONG_VAN_THONG_BAO`, `PHIEU_XUAT_KHO`, `GCN_DKDN` (tệp có note «ranh giới?») và mọi tệp có segment cuối chỉ gồm chữ ký |
| 2026-10-11 | 1.1 | Thêm mục 8.1: quy tắc cho người gán nhãn chỉ thấy một phần số trang (`PARTIAL:` trong `note`, `confidence` tối đa `medium`, không khẳng định composite/segments cho trang chưa xem) | Annotator B chỉ có văn bản 2 trang đầu; 5 tệp có `review_status = check_composite` trong `data/labels_v2.csv` | 5 tệp `check_composite`; 3 tệp `check_low_conf` |
| 2026-10-11 | 1.1 | Thêm giới hạn của ví dụ có tên tệp thật (cuối mục 7.4), dòng bắt buộc báo cáo đồng thuận **loại trừ tệp nêu tên trong hướng dẫn** (bảng 10.3) và mục 10.6 «Giới hạn đã biết của lần gán nhãn đầu» | Ví dụ ở mục 6 và 7.4 cho phép chép đáp án; 76/304 tài liệu duy nhất có tên được nêu (`agreement_summary.json`) | Mọi báo cáo κ |
| 2026-10-11 | 1.1 | Sửa đường dẫn trong 10.2 và 10.4 cho đúng với tệp thật (`annotation/annotator_A_opus_designer.csv`, `annotation/adjudication.csv` → `scripts/build_labels_v2.py` → `data/labels_v2.csv`); bỏ tên tệp không tồn tại `data/labels_v2_gold.csv`; cập nhật nguồn con số 21 composite ở 7.1 | Đối chiếu với `scripts/build_labels_v2.py` | — |
| 2026-10-11 | 1.1 (sửa câu) | Câu về quyền riêng tư ở đầu tệp: nêu rõ ngoại lệ cho riêng bộ mẫu nghiên cứu được gửi tới LLM bên ngoài; hệ thống chạy thật vẫn on-premise | Thống nhất với `teams/README.md` và quyết định của chủ dự án; không đổi quy tắc gán nhãn | không |
| | | | | |

## 12. Phụ lục: những cái bẫy đã gặp trong kho mẫu

| Bẫy | Thực tế | Cách xử lý |
|---|---|---|
| Thư mục «6. HOP DONG THUE KHO- Vi» | Không có hợp đồng thuê kho nào: 4 hợp đồng mượn bồn, 1 hợp đồng mua bồn, 1 tệp hóa đơn | Gán theo nội dung |
| Thư mục «_1. HOP DONG DAI LY NHUONG QUYEN» | Chỉ 5/25 tệp là hợp đồng nhượng quyền; còn lại là giấy đăng ký doanh nghiệp và giấy đủ điều kiện bán lẻ | Gán theo nội dung |
| Tên tệp «GPKD-…», «GĐKKD…» | Giấy chứng nhận đăng ký doanh nghiệp / hợp tác xã | `GCN_DKDN` |
| Tên tệp «HDKT …», «KT-…» | Tiêu đề thật là «Hợp đồng mua bán hàng hóa (hộ công nghiệp)» | `HD_MUA_BAN` |
| Tên tệp «PCCC 09567+00934…» trong hồ sơ xe | Giấy phép vận chuyển hàng hóa nguy hiểm về cháy, nổ | `GP_VC_HANG_NGUY_HIEM` |
| Tên tệp «Barem …» | Giấy chứng nhận kiểm định xi téc + bảng kết quả | `GCN_KIEM_DINH_DO_LUONG` |
| Tên tệp «1. Xe …», «3. Xe …» | Giấy biên nhận thế chấp của ngân hàng, không phải đăng ký xe | `BIEN_NHAN_THE_CHAP_PT` |
| Tên tệp «TLHD 11.20-…» | Tài liệu đầu tiên là biên bản nghiệm thu, bàn giao hàng hóa | composite, nhãn chính `BB_GIAO_NHAN_HANG_HOA` |
| Tên tệp «CamScanner …» | 4 tệp là bản vẽ, 1 tệp là giấy xác nhận thương nhân phân phối | Gán theo nội dung |
| Trang 1 chỉ có chữ «GIẤY CHỨNG NHẬN» trên bìa đỏ/xanh | Bìa thẻ; loại nằm ở mặt trong | Xem trang còn lại |
| Thân hợp đồng nhắc «Giấy chứng nhận đăng ký kinh doanh số…», «theo giấy ủy quyền số…» | Chỉ là thông tin về các bên | Không đổi loại; nhãn theo tiêu đề |
| Biên bản thanh lý nhắc «hợp đồng nhượng quyền…», «hợp đồng mua bán…» | Vẫn là biên bản thanh lý | `BB_THANH_LY_HD` |
| Ngày ghi trong tên tệp («-12.1.28», «(31-12-2024)») | Thường là ngày **hết hạn** do nhân viên tự ghi | Không dùng để gán nhãn; có thể ghi `note` nếu khác ngày trên giấy |
