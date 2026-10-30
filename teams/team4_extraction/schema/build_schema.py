"""build_schema.py - Sinh schema trích xuất theo loại từ `key_fields` của taxonomy (Nhóm 4, việc T1 + T5).

Chạy (từ gốc repo):
    .venv\\Scripts\\python.exe -X utf8 teams\\team4_extraction\\schema\\build_schema.py

Đọc `data/taxonomy_v2.json` (`classes[].key_fields`) và ghi, cạnh tệp này:
    <DOC_TYPE>.json     JSON Schema (draft 2020-12) của đầu ra phẳng {tên_trường: chuỗi | null} + siêu dữ liệu từng trường
                        trong khóa `x-fields` (type, id_kind, is_expiry, is_pii, pii_category, typical_ink, required, ...)
    pii_fields.json     danh sách trường dữ liệu cá nhân của TOÀN taxonomy + chính sách mặc định (T5)

Danh sách TRƯỜNG luôn lấy từ taxonomy (test `test_t4_schema.py` kiểm tra khớp 100%). Phần siêu dữ liệu nghiệp vụ (kiểu, bắt buộc,
mực...) là quyết định của nhóm 4 nằm trong các bảng bên dưới; trường mới xuất hiện trong taxonomy mà chưa có trong bảng sẽ làm script
dừng với lỗi rõ ràng (không đoán kiểu).

Quy ước giá trị vắng (ghi vào mỗi schema, khóa `x-missing_value_convention`):
    null + reason "not_present"  giấy KHÔNG ghi trường này (đáp án đúng là null)
    null + reason "not_found"    giấy có ghi nhưng máy không tìm thấy (lỗi của máy)
    null + reason "illegible"    có ghi nhưng không đọc được (mờ, che dấu, chữ viết tay) -> loại khỏi điểm

`typical_ink` (printed | handwritten | under_stamp | unknown): CHỈ khác `unknown` khi đã nhìn trang mẫu DEV thật (xem INK_VERIFIED).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
TAXONOMY = REPO / "data" / "taxonomy_v2.json"

TARGET_TYPES = ["GCN_DDK_BAN_LE_XD", "CC_TAP_HUAN_VC_HNH", "HD_MUA_BAN", "PHIEU_XUAT_KHO"]

MISSING_CONVENTION = {
    "null_with_reason": {
        "not_present": "Giấy không ghi trường này (đáp án đúng là null). Với silver: 'không có trên các trang được cho xem'.",
        "not_found": "Giấy có ghi nhưng bộ trích xuất không tìm thấy (lỗi của phương pháp, tính là FN).",
        "illegible": "Có ghi nhưng không đọc được (mờ, dưới con dấu, chữ viết tay). Đáp án illegible bị LOẠI khỏi điểm.",
    },
    "note": "Giá trị vắng luôn là null, không bao giờ là chuỗi rỗng, 'N/A', '-' hay số 0.",
}

# ---------------------------------------------------------------------------------------------
# Siêu dữ liệu nghiệp vụ theo trường. type: date | number | id | text.  id_kind: tax_code | plate | document_no | generic
# required: trường phải đúng thì tài liệu mới "đúng cấp tài liệu" (TẠM THỜI, chờ công ty duyệt: câu 11, 13, 14).
# annotate=False: trường dẫn xuất/định tuyến, không có trên trang -> silver KHÔNG điền, bộ chấm bỏ qua.
# multi: trường có thể có nhiều giá trị trên giấy (ghi gộp trong một chuỗi, cách nhau bằng '; ').
# ---------------------------------------------------------------------------------------------
M: Dict[str, Dict[str, Dict[str, Any]]] = {
    "GCN_DDK_BAN_LE_XD": {
        "so_giay": dict(type="id", id_kind="document_no", required=True,
                        hint="Số in sau 'Số:' ở đầu giấy chứng nhận, ví dụ dạng nn/GCN-SCT hoặc tương tự. Chép đúng cả dấu '/' và '-'."),
        "ngay_cap": dict(type="date", required=True, hint="Ngày ký cấp giấy (dòng 'ngày … tháng … năm …' ở cuối hoặc đầu giấy), KHÔNG phải ngày hết hạn."),
        "co_quan_cap": dict(type="text", hint="Tên Sở Công Thương cấp giấy."),
        "ten_cua_hang": dict(type="text", required=True, hint="Tên cửa hàng bán lẻ xăng dầu được chứng nhận."),
        "dia_chi_cua_hang": dict(type="text", hint="Địa chỉ cửa hàng (không phải địa chỉ trụ sở thương nhân nếu hai địa chỉ khác nhau)."),
        "thuong_nhan_chu_so_huu": dict(type="text", hint="Tên thương nhân chủ sở hữu cửa hàng, kèm mã số thuế nếu giấy in. Chép nguyên cụm như in."),
        "thuong_nhan_cung_cap": dict(type="text", hint="Thương nhân cung cấp xăng dầu cho cửa hàng, nếu giấy ghi."),
        "lan_cap": dict(type="text", hint="'cấp lần thứ …' hoặc 'cấp bổ sung/sửa đổi'; chép cụm như in."),
        "ngay_het_han": dict(type="date", required=True,
                             hint="Dòng 'có giá trị đến hết ngày … tháng … năm …'. Nếu giấy chỉ ghi thời hạn (vd. '05 năm kể từ ngày cấp') mà KHÔNG có ngày cụ thể, "
                                  "value = cụm thời hạn như in, normalized = null, status ok và note = 'chi_ghi_thoi_han'. Không tự cộng ngày."),
    },
    "CC_TAP_HUAN_VC_HNH": {
        "so_gcn": dict(type="id", id_kind="document_no", required=True, hint="Số giấy chứng nhận / số thẻ."),
        "ho_ten": dict(type="text", hint="Họ tên người được cấp."),
        "nam_sinh": dict(type="date", hint="Ngày/năm sinh (có thể chỉ có năm)."),
        "nghe_nghiep": dict(type="text", hint="Nghề nghiệp/chức danh (lái xe, áp tải, thủ kho...)."),
        "don_vi_cong_tac": dict(type="text", hint="Đơn vị công tác của người được cấp."),
        "don_vi_cap": dict(type="text", hint="Đơn vị tổ chức tập huấn và cấp giấy (thường ở tiêu đề)."),
        "ngay_cap": dict(type="date", required=True, hint="Ngày cấp giấy."),
        "hieu_luc_tu": dict(type="date", hint="'Có giá trị từ ngày …'."),
        "ngay_het_han": dict(type="date", required=True,
                             hint="'Có giá trị đến ngày …' (thường 2 năm). Chép đúng ngày in trên giấy; KHÔNG tự cộng 2 năm từ ngày cấp."),
    },
    "HD_MUA_BAN": {
        "so_hop_dong": dict(type="id", id_kind="document_no", required=True, hint="Số/ký hiệu hợp đồng ở đầu văn bản."),
        "ngay_ky": dict(type="date", required=True, hint="Ngày ký hợp đồng (đầu hoặc cuối văn bản). Nếu ngày ghi 'ngày … tháng … năm …' để trống thì not_present."),
        "ben_ban": dict(type="text", required=True, hint="Tên bên bán, kèm mã số thuế nếu có. Chép như in (Bên A/Bên B tùy văn bản — dựa vào vai trò BÁN, không dựa vào chữ A/B)."),
        "ben_mua": dict(type="text", required=True, hint="Tên bên mua, kèm mã số thuế nếu có."),
        "vai_tro_cong_ty": dict(type="text", enum=["ben_ban", "ben_mua"], annotate=False,
                                hint="Trường định tuyến (công ty chủ quản là bên bán hay bên mua): KHÔNG có trên trang, silver không điền."),
        "mat_hang": dict(type="text", hint="Mặt hàng mua bán chính (xăng dầu, dầu nhờn, thiết bị...)."),
        "han_muc_cong_no": dict(type="text", hint="Hạn mức và/hoặc thời hạn công nợ nếu hợp đồng nêu; chép cụm như in."),
        "hieu_luc_tu": dict(type="date", hint="Ngày bắt đầu hiệu lực nếu điều khoản hiệu lực nêu ngày cụ thể."),
        "hieu_luc_den": dict(type="date",
                             hint="Ngày hết hiệu lực nếu điều khoản hiệu lực nêu NGÀY cụ thể. Nếu chỉ nêu khoảng thời gian ('có hiệu lực 12 tháng'), "
                                  "value = cụm như in, normalized = null, note = 'chi_ghi_thoi_han'. Nếu hợp đồng không nêu hạn: not_present."),
    },
    "PHIEU_XUAT_KHO": {
        "so_phieu": dict(type="id", id_kind="document_no", required=True, hint="Số phiếu xuất kho (in/đóng số)."),
        "ky_hieu": dict(type="id", id_kind="generic", hint="Ký hiệu/mẫu số phiếu (nếu có)."),
        "ngay_xuat": dict(type="date", required=True, hint="Ngày xuất kho."),
        "ben_giao": dict(type="text", hint="Bên giao (kho/nhà máy/đơn vị xuất)."),
        "ben_nhan": dict(type="text", required=True, hint="Bên nhận (khách hàng/đơn vị nhận hàng)."),
        "hop_dong_can_cu": dict(type="text", hint="Số và ngày hợp đồng căn cứ, chép cụm như in."),
        "lenh_xuat_hang": dict(type="id", id_kind="document_no", hint="Số lệnh xuất hàng."),
        "bon_xuat": dict(type="text", hint="Bồn/kho xuất."),
        "bien_so_phuong_tien": dict(type="id", id_kind="plate", required=True, multi=True,
                                    hint="Biển số xe (và rơ moóc nếu có). Nếu có hai biển, ghi cả hai cách nhau '; '."),
        "mat_hang": dict(type="text", required=True, hint="Tên thành phẩm (xăng RON 95-III, dầu DO 0,05S-II...)."),
        "so_luong_m3_15c": dict(type="number", hint="Số lượng m3 quy về 15°C."),
        "so_luong_tan": dict(type="number", hint="Số lượng tấn."),
        "so_luong_m3_thuc_te": dict(type="number", hint="Số lượng m3 thực tế (ở nhiệt độ đo)."),
        "so_chung_thu_chat_luong": dict(type="id", id_kind="document_no", hint="Số chứng thư chất lượng (COQ) ghi trên phiếu."),
    },
}

# ---------------------------------------------------------------------------------------------
# Giai đoạn 3: 17 loại còn lại có trường hạn. Cùng quy ước với bảng trên. Mực (typical_ink) luôn "unknown" cho tới khi nhìn ảnh thật.
# Trường hạn (is_expiry theo taxonomy): xem x-expiry_fields trong mỗi schema.
# ---------------------------------------------------------------------------------------------
_HAN_HD = ("Ngày hết hiệu lực nếu điều khoản nêu NGÀY cụ thể. Nếu chỉ nêu khoảng thời gian ('có hiệu lực 12 tháng', 'theo thời hạn thuê'), "
           "value = cụm như in, normalized = null, status ok, note = 'chi_ghi_thoi_han'. Không nêu hạn: not_present. Không tự cộng ngày.")
_HAN_GIAY = ("Chép đúng ngày in trên giấy. Nếu giấy chỉ ghi khoảng thời gian không kèm ngày: value = cụm như in, normalized = null, "
             "note = 'chi_ghi_thoi_han'. Không tự cộng ngày từ ngày cấp. Không ghi hạn: not_present.")
M_P3: Dict[str, Dict[str, Dict[str, Any]]] = {
    "HD_VAN_CHUYEN": {
        "so_hop_dong": dict(type="id", id_kind="document_no", required=True, hint="Số/ký hiệu hợp đồng ở đầu văn bản."),
        "ngay_ky": dict(type="date", required=True, hint="Ngày ký hợp đồng. Nếu 'ngày … tháng … năm …' để trống thì not_present."),
        "ben_chu_hang": dict(type="text", required=True, hint="Bên thuê vận chuyển (chủ hàng), kèm MST nếu có. Dựa vào vai trò, không dựa vào chữ A/B."),
        "ben_van_chuyen": dict(type="text", required=True, hint="Bên nhận vận chuyển, kèm MST nếu có."),
        "vai_tro_cong_ty": dict(type="text", enum=["chu_hang", "van_chuyen"], annotate=False,
                                hint="Trường định tuyến: KHÔNG có trên trang, silver không điền."),
        "tuyen_van_chuyen": dict(type="text", hint="Nơi nhận hàng và nơi giao hàng, chép cụm như in."),
        "gia_cuoc": dict(type="text", hint="Đơn giá cước và cách tính, chép cụm như in (không chuẩn hóa)."),
        "hieu_luc_tu": dict(type="date", hint="Ngày bắt đầu hiệu lực nếu điều khoản nêu ngày cụ thể."),
        "hieu_luc_den": dict(type="date", hint=_HAN_HD),
    },
    "HD_MUON_BON": {
        "so_hop_dong": dict(type="id", id_kind="document_no", required=True, hint="Số/ký hiệu hợp đồng."),
        "ngay_ky": dict(type="date", required=True, hint="Ngày ký hợp đồng."),
        "ben_cho_muon": dict(type="text", required=True, hint="Bên cho mượn bồn, kèm MST nếu có."),
        "ben_muon": dict(type="text", required=True, hint="Bên mượn bồn (khách hàng), kèm MST nếu có."),
        "so_luong_bon": dict(type="number", hint="Số lượng bồn (một số nguyên)."),
        "dung_tich_bon": dict(type="text", hint="Dung tích mỗi bồn (lít); nhiều bồn khác dung tích thì chép cụm như in."),
        "ngay_nhan_bon": dict(type="date", hint="Ngày trên biên bản NHẬN bồn nếu tài liệu có biên bản này."),
        "ngay_tra_bon": dict(type="date", hint="Ngày trên biên bản TRẢ/thu hồi bồn nếu có."),
        "hieu_luc_den": dict(type="date", hint=_HAN_HD),
    },
    "HD_THUE_TAI_SAN": {
        "so_hop_dong": dict(type="id", id_kind="document_no", required=True, hint="Số/ký hiệu hợp đồng."),
        "ngay_ky": dict(type="date", required=True, hint="Ngày ký hợp đồng."),
        "ben_cho_thue": dict(type="text", required=True, hint="Bên cho thuê, kèm MST nếu có."),
        "ben_thue": dict(type="text", required=True, hint="Bên thuê, kèm MST nếu có."),
        "tai_san_thue": dict(type="text", hint="Tài sản thuê và địa chỉ, chép cụm như in."),
        "gia_thue": dict(type="text", hint="Giá thuê và kỳ thanh toán, chép cụm như in."),
        "thoi_han_thue_tu": dict(type="date", hint="Ngày bắt đầu thuê nếu nêu ngày cụ thể."),
        "thoi_han_thue_den": dict(type="date", hint=_HAN_HD),
    },
    "HD_NHUONG_QUYEN_DAI_LY": {
        "so_hop_dong": dict(type="id", id_kind="document_no", required=True, hint="Số/ký hiệu hợp đồng."),
        "ngay_ky": dict(type="date", required=True, hint="Ngày ký hợp đồng."),
        "ben_nhuong_quyen": dict(type="text", required=True, hint="Bên nhượng quyền/giao đại lý, kèm MST nếu có."),
        "ben_nhan_nhuong_quyen": dict(type="text", required=True, hint="Bên nhận nhượng quyền/đại lý, kèm MST nếu có."),
        "cua_hang": dict(type="text", hint="Tên và địa chỉ cửa hàng thuộc hợp đồng, chép cụm như in."),
        "hieu_luc_tu": dict(type="date", hint="Ngày bắt đầu hiệu lực nếu nêu ngày cụ thể."),
        "hieu_luc_den": dict(type="date", hint=_HAN_HD),
    },
    "GIAY_UY_QUYEN": {
        "so_van_ban": dict(type="id", id_kind="document_no", hint="Số giấy ủy quyền (thường có)."),
        "ngay_ky": dict(type="date", required=True, hint="Ngày ký giấy ủy quyền."),
        "to_chuc_uy_quyen": dict(type="text", hint="Tên tổ chức của bên ủy quyền."),
        "nguoi_uy_quyen": dict(type="text", hint="Họ tên và chức vụ người ủy quyền."),
        "nguoi_duoc_uy_quyen": dict(type="text", hint="Họ tên và chức vụ người được ủy quyền."),
        "noi_dung_uy_quyen": dict(type="text", hint="Phạm vi công việc được ủy quyền, tóm gọn đúng cụm in đầu tiên (không chép cả đoạn)."),
        "hieu_luc_tu": dict(type="date", hint="Hiệu lực từ ngày … nếu có."),
        "ngay_het_han": dict(type="date", required=True, hint="'Hiệu lực đến hết ngày …'. " + _HAN_GIAY),
    },
    "GXN_THUONG_NHAN_XD": {
        "so_giay": dict(type="id", id_kind="document_no", required=True, hint="Số giấy xác nhận."),
        "ngay_cap": dict(type="date", required=True, hint="Ngày ký cấp giấy."),
        "co_quan_cap": dict(type="text", hint="Cơ quan cấp (Sở/Bộ Công Thương)."),
        "ten_thuong_nhan": dict(type="text", required=True, hint="Tên thương nhân được xác nhận."),
        "ma_so_thue": dict(type="id", id_kind="tax_code", hint="Mã số thuế thương nhân."),
        "loai_thuong_nhan": dict(type="text", enum=["dau_moi", "phan_phoi", "tong_dai_ly", "dai_ly_ban_le"], annotate=False,
                                 hint="Trường phân loại: silver không điền (suy từ tiêu đề; chấm riêng nếu cần)."),
        "lan_cap": dict(type="text", hint="'cấp lần thứ …'; chép cụm như in."),
        "ngay_het_han": dict(type="date", required=True, hint="'Có giá trị đến hết ngày …'. " + _HAN_GIAY),
    },
    "GP_KD_VAN_TAI": {
        "so_giay_phep": dict(type="id", id_kind="document_no", required=True, hint="Số giấy phép."),
        "ngay_cap": dict(type="date", required=True, hint="Ngày cấp."),
        "co_quan_cap": dict(type="text", hint="Cơ quan cấp (Sở Giao thông vận tải...)."),
        "don_vi_duoc_cap": dict(type="text", required=True, hint="Tên đơn vị được cấp."),
        "loai_hinh_van_tai": dict(type="text", hint="Các loại hình vận tải được phép, chép cụm như in."),
        "lan_cap": dict(type="text", hint="'cấp lần thứ …' / 'cấp đổi'; chép cụm như in."),
        "ngay_het_han": dict(type="date", hint="Ngày hết hạn nếu giấy ghi thời hạn. " + _HAN_GIAY),
    },
    "CC_HUAN_LUYEN_PCCC": {
        "so_chung_nhan": dict(type="id", id_kind="document_no", required=True, hint="Số chứng nhận."),
        "ho_ten": dict(type="text", hint="Họ tên người được cấp."),
        "nam_sinh": dict(type="date", hint="Năm hoặc ngày sinh (dữ liệu cá nhân: KHÔNG chép giá trị)."),
        "noi_lam_viec": dict(type="text", hint="Nơi làm việc/đơn vị của người được cấp."),
        "noi_dung_huan_luyen": dict(type="text", hint="Nội dung huấn luyện (PCCC, CNCH), chép cụm như in."),
        "co_quan_cap": dict(type="text", hint="Cơ quan cấp."),
        "ngay_cap": dict(type="date", required=True, hint="Ngày cấp."),
        "ngay_het_han": dict(type="date", required=True, hint="Ngày hết giá trị CHỈ khi in/ghi trên thẻ. " + _HAN_GIAY),
    },
    "CC_NGHIEP_VU_BVMT": {
        "so_vao_so": dict(type="id", id_kind="document_no", required=True, hint="Số vào sổ / số chứng nhận."),
        "ho_ten": dict(type="text", hint="Họ tên người được cấp."),
        "nam_sinh": dict(type="date", hint="Ngày/năm sinh (dữ liệu cá nhân: KHÔNG chép giá trị)."),
        "noi_dung_khoa_hoc": dict(type="text", hint="Tên lớp/nội dung bồi dưỡng, chép cụm như in."),
        "thoi_gian_hoc": dict(type="text", hint="Từ ngày – đến ngày, chép cụm như in."),
        "co_so_dao_tao": dict(type="text", hint="Cơ sở đào tạo/cơ quan cấp."),
        "ngay_cap": dict(type="date", required=True, hint="Ngày cấp."),
        "ngay_het_han": dict(type="date", hint="'Có giá trị đến ngày …' nếu có ghi. " + _HAN_GIAY),
    },
    "GPLX": {
        "so_gplx": dict(type="id", id_kind="document_no", required=True, hint="Số giấy phép lái xe (dữ liệu cá nhân: KHÔNG chép giá trị)."),
        "ho_ten": dict(type="text", hint="Họ tên."),
        "ngay_sinh": dict(type="date", hint="Ngày sinh (dữ liệu cá nhân: KHÔNG chép giá trị)."),
        "hang": dict(type="text", required=True, hint="Hạng giấy phép (B2, C, FC...), chép như in."),
        "ngay_cap": dict(type="date", required=True, hint="Ngày cấp."),
        "noi_cap": dict(type="text", hint="Nơi cấp."),
        "ngay_het_han": dict(type="date", required=True, hint="'Có giá trị đến' (có thể ghi 'Không thời hạn': khi đó value = cụm như in, normalized = null, note = 'khong_thoi_han'). Không tự cộng ngày."),
    },
    "CCCD": {
        "so_dinh_danh": dict(type="id", id_kind="document_no", required=True, hint="Số căn cước/CMND (dữ liệu cá nhân: KHÔNG chép giá trị)."),
        "ho_ten": dict(type="text", hint="Họ tên."),
        "ngay_sinh": dict(type="date", hint="Ngày sinh (dữ liệu cá nhân: KHÔNG chép giá trị)."),
        "ngay_cap": dict(type="date", hint="Ngày cấp."),
        "ngay_het_han": dict(type="date", required=True, hint="'Có giá trị đến' (có thể là 'Không thời hạn': value = cụm như in, normalized = null, note = 'khong_thoi_han'). Không tự cộng ngày."),
    },
    "DANG_KY_PHUONG_TIEN": {
        "bien_so": dict(type="id", id_kind="plate", required=True, multi=True, hint="Biển số đăng ký / số đăng ký phương tiện thủy. Nhiều biển: cách nhau '; '."),
        "loai_phuong_tien": dict(type="text", hint="Ô tô đầu kéo, sơ mi rơ moóc, xi téc, tàu/ghe... chép như in."),
        "chu_so_huu": dict(type="text", hint="Tên chủ xe/chủ phương tiện (có thể là tổ chức hoặc cá nhân), chép như in."),
        "nhan_hieu": dict(type="text", hint="Nhãn hiệu, số loại."),
        "so_khung": dict(type="id", id_kind="generic", hint="Số khung."),
        "so_may": dict(type="id", id_kind="generic", hint="Số máy."),
        "nam_san_xuat": dict(type="date", hint="Năm sản xuất/năm đóng (chỉ năm: normalized = YYYY)."),
        "so_chung_nhan": dict(type="id", id_kind="document_no", hint="Số chứng nhận đăng ký."),
        "ngay_dang_ky": dict(type="date", hint="Ngày đăng ký."),
        "co_quan_cap": dict(type="text", hint="Cơ quan cấp."),
        "ngay_het_han": dict(type="date", hint="'Đăng ký xe có giá trị đến ngày …' (niên hạn) nếu có. " + _HAN_GIAY),
    },
    "BIEN_NHAN_THE_CHAP_PT": {
        "so_bien_nhan": dict(type="id", id_kind="document_no", required=True, hint="Số giấy biên nhận."),
        "ngay_cap": dict(type="date", required=True, hint="Ngày cấp."),
        "ngan_hang": dict(type="text", hint="Ngân hàng, chi nhánh cấp."),
        "ben_the_chap": dict(type="text", hint="Bên thế chấp, chép như in."),
        "bien_so": dict(type="id", id_kind="plate", multi=True, hint="Biển kiểm soát phương tiện. Nhiều biển: cách nhau '; '."),
        "loai_phuong_tien": dict(type="text", hint="Loại phương tiện, nhãn hiệu."),
        "so_khung": dict(type="id", id_kind="generic", hint="Số khung."),
        "so_may": dict(type="id", id_kind="generic", hint="Số máy."),
        "so_gcn_dang_ky": dict(type="id", id_kind="document_no", hint="Số giấy chứng nhận đăng ký xe được thế chấp."),
        "lan_cap": dict(type="text", hint="'cấp lần thứ …'; chép cụm như in."),
        "ngay_het_han": dict(type="date", required=True, hint="'Có hiệu lực đến hết ngày …'. " + _HAN_GIAY),
    },
    "GCN_ATKT_BVMT_PT": {
        "so_gcn": dict(type="id", id_kind="document_no", required=True, hint="Số giấy chứng nhận."),
        "bien_so": dict(type="id", id_kind="plate", required=True, multi=True, hint="Biển số xe / số đăng ký phương tiện."),
        "ten_phuong_tien": dict(type="text", hint="Tên phương tiện nếu có."),
        "chu_phuong_tien": dict(type="text", hint="Chủ phương tiện, chép như in."),
        "co_quan_dang_kiem": dict(type="text", hint="Đơn vị đăng kiểm cấp."),
        "ngay_cap": dict(type="date", required=True, hint="Ngày cấp."),
        "ngay_het_han": dict(type="date", required=True, hint="'Có hiệu lực đến ngày …' (hạn đăng kiểm). " + _HAN_GIAY),
    },
    "GCN_KIEM_DINH_DO_LUONG": {
        "so_gcn": dict(type="id", id_kind="document_no", required=True, hint="Số giấy chứng nhận kiểm định."),
        "doi_tuong": dict(type="text", hint="Đối tượng kiểm định (cột đo, xi téc ô tô...)."),
        "so_thiet_bi": dict(type="id", id_kind="generic", hint="Số/serial thiết bị, số xi téc."),
        "bien_so": dict(type="id", id_kind="plate", multi=True, hint="Biển số xe mang xi téc nếu có."),
        "noi_su_dung": dict(type="text", hint="Nơi sử dụng (cửa hàng số..., tàu...)."),
        "don_vi_su_dung": dict(type="text", hint="Đơn vị sử dụng."),
        "to_chuc_kiem_dinh": dict(type="text", hint="Tổ chức kiểm định."),
        "so_tem_kiem_dinh": dict(type="id", id_kind="generic", hint="Số tem kiểm định."),
        "ngay_cap": dict(type="date", required=True, hint="Ngày cấp."),
        "ngay_het_han": dict(type="date", required=True, hint="'Thời hạn đến / Valid until'. " + _HAN_GIAY),
    },
    "GP_VC_HANG_NGUY_HIEM": {
        "so_giay_phep": dict(type="id", id_kind="document_no", required=True, hint="Số giấy phép."),
        "ngay_cap": dict(type="date", required=True, hint="Ngày cấp."),
        "co_quan_cap": dict(type="text", hint="Cơ quan cấp."),
        "don_vi_duoc_cap": dict(type="text", required=True, hint="Đơn vị được cấp."),
        "bien_so_phuong_tien": dict(type="id", id_kind="plate", multi=True, hint="Danh sách biển số xe/rơ moóc được phép, cách nhau '; ' (nếu danh sách dài ở trang phụ lục thì chép những biển đọc được và note = 'danh_sach_dai')."),
        "ten_hang": dict(type="text", hint="Tên hàng nguy hiểm, số hiệu UN."),
        "khoi_luong": dict(type="text", hint="Khối lượng vận chuyển, chép cụm như in."),
        "ngay_het_han": dict(type="date", required=True, hint="'Thời hạn của giấy phép'. " + _HAN_GIAY),
    },
    "GCN_BAO_HIEM": {
        "so_gcn_bao_hiem": dict(type="id", id_kind="document_no", required=True, hint="Số giấy chứng nhận bảo hiểm."),
        "cong_ty_bao_hiem": dict(type="text", hint="Doanh nghiệp bảo hiểm."),
        "loai_bao_hiem": dict(type="text", enum=["tnds_bat_buoc", "tu_nguyen_vat_chat_xe", "chay_no_bat_buoc", "tau_thuyen", "khac"], annotate=False,
                              hint="Trường phân loại: silver không điền (suy từ tiêu đề)."),
        "nguoi_duoc_bao_hiem": dict(type="text", hint="Chủ xe/người được bảo hiểm, chép như in."),
        "doi_tuong_bao_hiem": dict(type="text", hint="Biển số xe hoặc tên cơ sở/cửa hàng/tàu được bảo hiểm, chép như in."),
        "so_tien_bao_hiem": dict(type="text", hint="Số tiền/mức trách nhiệm bảo hiểm, chép cụm như in (có thể nhiều mức)."),
        "phi_bao_hiem": dict(type="number", hint="Tổng phí bảo hiểm (một số tiền)."),
        "hieu_luc_tu": dict(type="date", hint="Thời hạn bảo hiểm từ (có thể kèm giờ: chỉ ngày)."),
        "ngay_het_han": dict(type="date", required=True, hint="Thời hạn bảo hiểm đến (có thể kèm giờ: chỉ ngày). " + _HAN_GIAY),
    },
}
M.update(M_P3)
PHASE3_TYPES = list(M_P3)

# Trường đã được XÁC MINH mực trên trang mẫu DEV (cập nhật khi nhìn ảnh thật). Còn lại = "unknown".
# Định dạng: {doc_type: {field: ("printed"|"handwritten"|"under_stamp", "mô tả ngắn nơi đã kiểm")}}
def _ink(kind: str, where: str, names: List[str]) -> Dict[str, Any]:
    return {n: (kind, where) for n in names}


# Đã nhìn ảnh trang thật của một đơn vị DEV mỗi loại (n = 1 mỗi loại: đây là QUAN SÁT SƠ BỘ, không phải thống kê).
_GCN_SEEN = "1 đơn vị DEV (ảnh trang 1-2)"
_CC_SEEN = "1 đơn vị DEV (ảnh mặt trong thẻ)"
_PXK_SEEN = "1 đơn vị DEV (ảnh trang 1, bản số hóa)"
INK_VERIFIED: Dict[str, Dict[str, Any]] = {
    # ngay_het_han ở mẫu đã xem là chữ in nhưng bị con dấu "chứng thực bản sao" đè một phần: OCR hỏng ở đó.
    "GCN_DDK_BAN_LE_XD": _ink("printed", _GCN_SEEN, [
        "so_giay", "ngay_cap", "co_quan_cap", "ten_cua_hang", "dia_chi_cua_hang", "thuong_nhan_chu_so_huu",
        "thuong_nhan_cung_cap", "lan_cap", "ngay_het_han"]),
    "CC_TAP_HUAN_VC_HNH": _ink("printed", _CC_SEEN, [
        "so_gcn", "ho_ten", "nam_sinh", "nghe_nghiep", "don_vi_cong_tac", "don_vi_cap", "ngay_cap", "hieu_luc_tu", "ngay_het_han"]),
    "PHIEU_XUAT_KHO": _ink("printed", _PXK_SEEN, [
        "so_phieu", "ky_hieu", "ngay_xuat", "ben_giao", "ben_nhan", "hop_dong_can_cu", "lenh_xuat_hang", "bon_xuat",
        "bien_so_phuong_tien", "mat_hang", "so_luong_m3_15c", "so_luong_tan", "so_luong_m3_thuc_te"]),
}

TYPE_NOTES = {
    "GCN_DDK_BAN_LE_XD": "Giấy chứng nhận cửa hàng đủ điều kiện bán lẻ xăng dầu. Trường hạn: ngay_het_han.",
    "CC_TAP_HUAN_VC_HNH": "Giấy chứng nhận hoàn thành tập huấn vận chuyển hàng hóa nguy hiểm (thẻ 2 mặt). Trường hạn: ngay_het_han. Có dữ liệu cá nhân.",
    "HD_MUA_BAN": "Hợp đồng mua bán (xăng dầu, dầu nhờn, thiết bị...). Trường hạn: hieu_luc_den (có thể không có).",
    "PHIEU_XUAT_KHO": "Phiếu xuất kho (chứng từ kế toán). Không có trường hạn.",
}


TYPE_NOTES.update({
    "HD_VAN_CHUYEN": "Hợp đồng vận chuyển hàng hóa. Trường hạn: hieu_luc_den (có thể không có hoặc chỉ ghi khoảng thời gian).",
    "HD_MUON_BON": "Hợp đồng mượn bồn chứa dầu (kèm biên bản nhận/trả bồn). Trường hạn: hieu_luc_den (nếu có ghi).",
    "HD_THUE_TAI_SAN": "Hợp đồng thuê kho/cửa hàng/tài sản. Trường hạn: thoi_han_thue_den.",
    "HD_NHUONG_QUYEN_DAI_LY": "Hợp đồng nhượng quyền bán lẻ/đại lý xăng dầu. Trường hạn: hieu_luc_den.",
    "GIAY_UY_QUYEN": "Giấy ủy quyền. Trường hạn: ngay_het_han (hiệu lực đến hết ngày, nếu có). Có tên cá nhân.",
    "GXN_THUONG_NHAN_XD": "Giấy xác nhận thương nhân xăng dầu. Trường hạn: ngay_het_han.",
    "GP_KD_VAN_TAI": "Giấy phép kinh doanh vận tải bằng xe ô tô. Trường hạn: ngay_het_han (nếu có ghi).",
    "CC_HUAN_LUYEN_PCCC": "Chứng nhận huấn luyện nghiệp vụ PCCC và CNCH. Trường hạn: ngay_het_han. Có dữ liệu cá nhân.",
    "CC_NGHIEP_VU_BVMT": "Chứng nhận nghiệp vụ bảo vệ môi trường trong kinh doanh xăng dầu. Trường hạn: ngay_het_han (nếu có). Có dữ liệu cá nhân.",
    "GPLX": "Giấy phép lái xe. Trường hạn: ngay_het_han. Số giấy phép và ngày sinh là dữ liệu cá nhân (không chép giá trị).",
    "CCCD": "Căn cước công dân/CMND. Trường hạn: ngay_het_han. Số định danh và ngày sinh là dữ liệu cá nhân (không chép giá trị).",
    "DANG_KY_PHUONG_TIEN": "Chứng nhận đăng ký xe/rơ moóc/phương tiện thủy. Trường hạn: ngay_het_han (niên hạn, nếu có).",
    "BIEN_NHAN_THE_CHAP_PT": "Giấy biên nhận thế chấp phương tiện. Trường hạn: ngay_het_han.",
    "GCN_ATKT_BVMT_PT": "Giấy chứng nhận an toàn kỹ thuật và BVMT phương tiện (đăng kiểm). Trường hạn: ngay_het_han.",
    "GCN_KIEM_DINH_DO_LUONG": "Giấy chứng nhận kiểm định phương tiện đo. Trường hạn: ngay_het_han.",
    "GP_VC_HANG_NGUY_HIEM": "Giấy phép vận chuyển hàng hóa nguy hiểm. Trường hạn: ngay_het_han.",
    "GCN_BAO_HIEM": "Giấy chứng nhận bảo hiểm. Trường hạn: ngay_het_han (thời hạn bảo hiểm đến).",
})


def pii_category(name: str) -> str | None:
    """Phân loại trường theo TÊN (dùng chung cho schema và pii_fields.json). None = không phải dữ liệu cá nhân."""
    n = name.lower()
    if n in {"so_dinh_danh", "so_gplx", "so_cccd", "so_cmnd"}:
        return "personal_id"
    if n in {"ngay_sinh", "nam_sinh"}:
        return "birth_date"
    if n == "ho_ten" or n.startswith("nguoi_"):
        return "personal_name"
    return None


def load_taxonomy() -> Dict[str, Any]:
    return json.loads(TAXONOMY.read_text(encoding="utf-8"))


def _prop_schema(meta: Dict[str, Any], desc: str) -> Dict[str, Any]:
    p: Dict[str, Any] = {"type": ["string", "null"], "description": desc}
    if "enum" in meta:
        p = {"type": ["string", "null"], "enum": meta["enum"] + [None], "description": desc}
    return p


def build_schema(cls: Dict[str, Any], tax_version: str) -> Dict[str, Any]:
    dt = cls["id"]
    if dt not in M:
        raise SystemExit(f"Loại {dt} chưa có bảng siêu dữ liệu trong build_schema.py")
    unknown = [f["name"] for f in cls["key_fields"] if f["name"] not in M[dt]]
    extra = [n for n in M[dt] if n not in {f["name"] for f in cls["key_fields"]}]
    if unknown or extra:
        raise SystemExit(f"{dt}: taxonomy và bảng siêu dữ liệu lệch nhau (thiếu trong bảng: {unknown}; thừa trong bảng: {extra}). "
                         "Cập nhật M trong build_schema.py, không đoán kiểu.")
    props: Dict[str, Any] = {}
    xf: List[Dict[str, Any]] = []
    for f in cls["key_fields"]:
        name, meta = f["name"], M[dt][f["name"]]
        cat = pii_category(name)
        ink = INK_VERIFIED.get(dt, {}).get(name)
        entry: Dict[str, Any] = {
            "name": name,
            "desc": f["desc"],
            "annotator_hint": meta.get("hint", ""),
            "type": meta["type"],
            "is_expiry": bool(f.get("is_expiry")),
            "is_pii": cat is not None,
            "pii_category": cat,
            "typical_ink": ink[0] if ink else "unknown",
            "required": bool(meta.get("required")) and cat in (None, "personal_name"),
            "multi": bool(meta.get("multi")),
            "annotate": meta.get("annotate", True),
            # silver: nếu là số định danh/ngày sinh thì người chú thích KHÔNG chép giá trị (chỉ có/không có)
            "silver_policy": ("skip" if meta.get("annotate", True) is False
                              else "withhold_value" if cat in ("personal_id", "birth_date") else "transcribe"),
        }
        if meta["type"] == "id":
            entry["id_kind"] = meta.get("id_kind", "generic")
        if "enum" in meta:
            entry["enum"] = meta["enum"]
        if ink:
            entry["typical_ink_verified_on"] = ink[1]
        xf.append(entry)
        props[name] = _prop_schema(meta, f["desc"])
    out = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"sdh-phanloaitailieu/team4/schema/{dt}",
        "title": f"{dt} - {cls.get('name_vi', dt)}",
        "description": TYPE_NOTES[dt],
        "type": "object",
        "properties": props,
        "required": [f["name"] for f in cls["key_fields"]],  # mọi khóa phải có mặt trong đầu ra (giá trị có thể null)
        "additionalProperties": False,
        "x-doc_type": dt,
        "x-taxonomy_version": tax_version,
        "x-status": "draft - chờ nhóm 00 và người của công ty duyệt (câu 11, 13, 14)",
        "x-missing_value_convention": MISSING_CONVENTION,
        "x-fields": xf,
    }
    if dt in PHASE3_TYPES:      # schema 4 loại giai đoạn 2 giữ nguyên từng byte (src/extraction/schema_data là bản sao của chúng)
        out["x-expiry_fields"] = [e["name"] for e in xf if e["is_expiry"]]    # các trường "hạn": bộ chấm/nhắc hạn dùng danh sách này
    return out


def build_pii(tax: Dict[str, Any]) -> Dict[str, Any]:
    fields: Dict[str, Dict[str, Any]] = {}
    for c in tax["classes"]:
        for f in c.get("key_fields", []):
            cat = pii_category(f["name"])
            if cat:
                e = fields.setdefault(f["name"], {"name": f["name"], "category": cat, "doc_types": []})
                e["doc_types"].append(c["id"])
    return {
        "version": 1,
        "status": "tạm thời - chờ công ty trả lời câu 12 (README nhóm 4)",
        "generated_from": "data/taxonomy_v2.json (mọi lớp, mọi key_fields)",
        "config_defaults": {
            "store_personal_ids": False,
            "store_personal_names": True,
        },
        "categories": {
            "personal_id": {"description": "Số căn cước/CMND, số giấy phép lái xe.",
                            "default_in_output": "dropped unless store_personal_ids=true", "in_logs_and_reports": "never"},
            "birth_date": {"description": "Ngày/năm sinh.",
                           "default_in_output": "dropped unless store_personal_ids=true", "in_logs_and_reports": "never"},
            "personal_name": {"description": "Họ tên cá nhân (người được cấp, người đại diện, lái xe, người nhận...).",
                              "default_in_output": "kept unless store_personal_names=false (cần để gắn nhắc hạn với người)",
                              "in_logs_and_reports": "never"},
        },
        "rules": [
            "Đầu ra mặc định (filter_output) bỏ hẳn khóa của personal_id và birth_date khi store_personal_ids=false.",
            "Log, báo cáo, bảng lỗi: giá trị của MỌI trường trong 'fields' (kể cả personal_name) được thay bằng [REDACTED] hoặc bỏ.",
            "Đáp án silver: người chú thích không chép giá trị personal_id/birth_date (chỉ ghi có hay không và trang).",
        ],
        "fields": sorted(fields.values(), key=lambda e: (e["category"], e["name"])),
    }


def main() -> int:
    tax = load_taxonomy()
    classes = {c["id"]: c for c in tax["classes"]}
    for dt in TARGET_TYPES + PHASE3_TYPES:
        sch = build_schema(classes[dt], str(tax.get("version")))
        (HERE / f"{dt}.json").write_text(json.dumps(sch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"ghi {dt}.json: {len(sch['x-fields'])} trường")
    pii = build_pii(tax)
    (HERE / "pii_fields.json").write_text(json.dumps(pii, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"ghi pii_fields.json: {len(pii['fields'])} trường PII")
    return 0


if __name__ == "__main__":
    sys.exit(main())
