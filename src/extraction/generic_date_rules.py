"""generic_date_rules.py - Luật CHUNG cho trường ngày của loại tài liệu chưa có luật riêng (Nhóm 4, giai đoạn 3, thí nghiệm 03_unseen_types).

Bản chuẩn nằm ở đây (`src/extraction`, phương án dự phòng cho loại không có luật riêng, qua `apply_rules_with_fallback`; `field_rules.py` giữ nguyên vì đã đóng băng giai đoạn 2); `teams/team4_extraction/methods/generic_date_rules.py`
là bản đóng băng của thí nghiệm (test `tests/test_extraction_generic_types.py` kiểm tra hai bản có cùng luật).

Vì sao: ở giai đoạn 2 luật chỉ viết cho 4 loại; 17 loại mới (silver v2) không có luật nên luật trả toàn null. Đây là MỘT vòng cải tiến
chung (không theo từng tài liệu): thêm nhãn ngày thường gặp ở mọi giấy phép/giấy chứng nhận/hợp đồng, nhìn từ các đơn vị DEV v2.
Chỉ xử lý trường kiểu `date` (hạn, hiệu lực từ, ngày ký, ngày cấp) — chỗ luật bền nhất; không đụng chữ/mã (để LLM lo).

Quy tắc an toàn: chỉ nhận ngày ĐẦY ĐỦ; "không thời hạn/vô thời hạn" -> null (không bịa ngày); mọi trường không khớp -> null.
Chạy trên văn bản không dấu giữ nguyên chỉ số (`Doc` của src/extraction/field_rules.py), giá trị trả về là nguyên văn.
Nhãn viết theo tên trường nên dùng chung cho mọi loại có trường cùng tên (ngay_het_han, hieu_luc_den, thoi_han_thue_den, hieu_luc_tu, thoi_han_thue_tu, ngay_ky, ngay_cap).
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from src.extraction.field_rules import D_NUM, D_VN, DATE, RULES, Doc, Hit, _clean, apply_rules

H = r"\d{1,2}\s*(?:gio|h)\s*\d{0,2}\s*(?:phut)?\s*[,;]?\s*"        # "16 giờ 00," BẮT BUỘC đứng trước ngày (giấy bảo hiểm); thiếu giờ thì "đến ngày" có thể là kỳ học

# --- hạn: thứ tự ưu tiên, câu đầu tiên khớp thắng ---------------------------------------------------
EXPIRY_PATTERNS: List[str] = [
    # câu hiệu lực của hợp đồng/giấy ủy quyền: "có hiệu lực [kể] từ ngày ký|<ngày> đến [hết] [ngày] <ngày>"
    rf"hieu\s+luc\s*(?:ke\s+)?(?:tu\s+ngay\s+(?:ky\b|{DATE})\s*)?den\s+(?:het\s+)?(?:ngay\s*)?({DATE})",
    rf"thoi\s+han\s+(?:thue|hop\s+dong|hieu\s+luc)[^\n.]{{0,60}}?den\s+(?:het\s+)?(?:ngay\s*)?({DATE})",
    # "có giá trị đến [hết ngày] <ngày>" kể cả có chữ Expires / (date of expiry) xen giữa
    rf"gia\s+tr[ij]\s+den\s*(?:het\s+)?(?:ngay)?[^0-9\n]{{0,28}}?({DATE})",
    rf"gia\s+tr[ij]\s+(?:den|toi)[^0-9\n]{{0,28}}?({DATE})",
    rf"(?:thoi\s+han|han\s+su\s+dung|het\s+han|han\s+den)\s*(?:cua\s+giay\s+phep|cua\s+giay)?\s*[:：]?\s*(?:ngay\s*)?({DATE})",
    rf"(?:expires?|date\s+of\s+expir\w*|valid\s+until)[^0-9\n]{{0,20}}?({DATE})",
    # giấy bảo hiểm: "Đến: 16 giờ 00, ngày 26/11/2024"
    rf"\bden\s*[:：]?\s*{H}ngay\s*({DATE})",
]
FROM_PATTERNS: List[str] = [
    rf"hieu\s+luc\s*(?:ke\s+)?tu\s+ngay\s+({DATE})",
    rf"thoi\s+han\s+(?:thue|hop\s+dong|hieu\s+luc)[^\n.]{{0,60}}?tu\s+ngay\s+({DATE})",
    rf"\btu\s*[:：]?\s*{H}ngay\s*({DATE})",
]
SIGN_PATTERNS: List[str] = [
    rf"hom\s+nay\s*,?\s*(?:ngay\s*)?({DATE})",
    rf"k[yi]\s+ngay\s*({DATE})",
    rf",\s*ngay\s*({D_VN})",
]
ISSUE_PATTERNS: List[str] = [rf"[a-z ]{{3,25}},\s*ngay\s*({D_VN}|{D_NUM})"]       # "Bình Định, ngày 06 tháng 04 năm 2021" (lấy cái CUỐI: chữ ký ở cuối)

EXPIRY_FIELDS = {"ngay_het_han", "hieu_luc_den", "thoi_han_thue_den"}
FROM_FIELDS = {"hieu_luc_tu", "thoi_han_thue_tu"}


BAD_GAP = re.compile(r"(?:khong|vo)\s+thoi\s+han|ngay\s+cap|date\s+of\s+(?:issue|birth)|ngay\s+sinh|issued")


def _first(doc: Doc, patterns: List[str], pages: Optional[List[int]] = None, last: bool = False) -> Hit:
    """Câu đầu tiên (theo thứ tự ưu tiên) có khớp mà đoạn nhãn->ngày KHÔNG chứa 'không thời hạn' / 'ngày cấp' / 'ngày sinh' (tránh nhảy sang ngày khác)."""
    for pat in patterns:
        rx = re.compile(pat, re.I)
        for pg in (pages or doc.order):
            f = doc.fold.get(pg, "")
            ms = [m for m in rx.finditer(f) if not BAD_GAP.search(m.group(0))]
            if ms:
                m = ms[-1] if last else ms[0]
                s_, e_ = m.span(1)
                return _clean(doc.pages[pg][s_:e_]), pg
    return None, None


def generic_rules(field_names: List[str], doc: Doc) -> Dict[str, Hit]:
    """Luật chung cho các trường ngày có trong `field_names`; trường khác không có mặt trong kết quả (-> null)."""
    out: Dict[str, Hit] = {}
    for n in field_names:
        if n in EXPIRY_FIELDS:
            out[n] = _first(doc, EXPIRY_PATTERNS)
        elif n in FROM_FIELDS:
            out[n] = _first(doc, FROM_PATTERNS)
        elif n == "ngay_ky":
            out[n] = _first(doc, SIGN_PATTERNS)
        elif n == "ngay_cap":
            out[n] = _first(doc, ISSUE_PATTERNS, pages=doc.order[-1:], last=True)
    return out


def apply_rules_with_fallback(doc_type: str, pages: Dict[int, str], generic: bool = True) -> Dict[str, Hit]:
    """Điểm vào của `field_extractor`: loại có luật riêng (`field_rules.RULES`) -> đúng `apply_rules` như giai đoạn 2 (không đổi, kể cả từng byte
    của `field_rules.py` vì tệp đó đã đóng băng); loại không có luật riêng nhưng có schema -> luật ngày chung; loại không có schema -> {}."""
    if doc_type in RULES or not generic:
        return apply_rules(doc_type, pages)
    from src.extraction.schemas import UnsupportedDocType, field_specs
    try:
        names = [f["name"] for f in field_specs(doc_type)]
    except UnsupportedDocType:
        return {}
    return generic_rules(names, Doc(pages))
