"""field_rules.py - Luật/regex theo từng trường cho 4 loại tài liệu (Nhóm 4). Chạy hoàn toàn cục bộ, chỉ dùng thư viện chuẩn.

    hits = apply_rules("GCN_DDK_BAN_LE_XD", {1: "văn bản trang 1", 2: "..."})   # {trường: (giá trị nguyên văn | None, trang | None)}

Đặc điểm:
  * Chạy trên văn bản KHÔNG DẤU nhưng GIỮ NGUYÊN CHỈ SỐ (`fold_keep_len`), nên chịu được OCR làm hỏng dấu ("hết"/"hêt"/"hét")
    mà giá trị trả về vẫn cắt từ văn bản gốc đúng như in.
  * Ngày: chỉ nhận ngày ĐẦY ĐỦ (ngày-tháng-năm). OCR cắt mất năm -> trường để null (not_found), không đoán.
  * Mỗi quy tắc trả (giá_trị, trang). Không khớp -> null; không bao giờ điền giá trị mặc định.
  * Luật được viết/chỉnh trên các đơn vị DEV (teams/team4_extraction/experiments/02_methods); TEST chỉ chấm một lần với bản đã đóng băng.

Giới hạn đã biết: trường văn bản gộp (bên bán + MST) chỉ lấy một dòng; hợp đồng dài nhiều trang chỉ tìm câu "hợp đồng có hiệu lực ... đến ngày ...";
OCR hỏng ở con dấu/chữ viết tay thì luật không cứu được (xem RESULTS.md).
"""

from __future__ import annotations

import re
from typing import Callable, Dict, List, Optional, Tuple

from src.extraction.normalize import fold_keep_len

# ---- mảnh regex dùng chung (trên văn bản đã bỏ dấu, chữ thường) ---------------------------------
D_VN = r"\d{1,2}\s*(?:thang|th)\s*\d{1,2}\s*nam\s*\d{4}"          # 12 tháng 01 năm 2028
D_NUM = r"\d{1,2}\s*[/.\-]\s*\d{1,2}\s*[/.\-]\s*\d{2,4}"           # 12/1/28, 12.01.2028
DATE = rf"(?:{D_VN}|{D_NUM})"
TAXC = r"\d{10}(?:\s*-\s*\d{3})?"

Hit = Tuple[Optional[str], Optional[int]]
Span = Optional[Tuple[int, int]]


class Doc:
    """Một đơn vị: nguyên văn + bản bỏ dấu cùng độ dài theo từng trang."""

    def __init__(self, pages: Dict[int, str]) -> None:
        self.pages = pages
        self.fold = {p: fold_keep_len(t) for p, t in pages.items()}
        self.order = sorted(pages)

    def search(self, pat: str, flags: int = re.I, first_chars: Optional[int] = None, group: int = 1, last: bool = False,
               pages: Optional[List[int]] = None, start_after: Optional[Tuple[int, int]] = None) -> Tuple[Optional[str], Optional[int], Span]:
        """Tìm regex (trên bản bỏ dấu) và trả (đoạn NGUYÊN VĂN của `group`, trang, (đầu, cuối) của đoạn)."""
        rx = re.compile(pat, flags)
        found: Tuple[Optional[str], Optional[int], Span] = (None, None, None)
        for p in (pages or self.order):
            if p not in self.fold:
                continue
            f = self.fold[p]
            lo = start_after[1] if start_after and start_after[0] == p else 0
            hi = min(first_chars, len(f)) if first_chars else len(f)
            ms = list(rx.finditer(f, lo, hi))
            if not ms:
                continue
            m = ms[-1] if last else ms[0]
            s, e = m.span(group)
            if s < 0:
                continue
            found = (self.pages[p][s:e].strip(), p, (s, e))
            if not last:
                return found
        return found


def _clean(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v = re.sub(r"\s+", " ", v).strip(" ;,:.-")
    return v or None


def _line_value(doc: Doc, label_pat: str, **kw) -> Hit:
    """Giá trị sau nhãn, tới hết dòng."""
    v, p, _ = doc.search(rf"{label_pat}\s*[:：]?[ \t]*([^\n]+)", **kw)
    return _clean(v), p


# ==================================================================================================
# GCN_DDK_BAN_LE_XD
# ==================================================================================================
def rules_gcn_ddk(doc: Doc) -> Dict[str, Hit]:
    r: Dict[str, Hit] = {}
    first = doc.order[:1]
    v, p, _ = doc.search(rf"het\s+ngay\s*[:,]?\s*({D_VN}|{D_NUM})")
    r["ngay_het_han"] = (_clean(v), p)
    # số giấy: phải có "GCN" hoặc "SCT" (tránh nhầm số quyết định/nghị định ở phần căn cứ khi tiêu đề bị OCR hỏng)
    v, p, _ = doc.search(r"\bso\s*[:.]?\s*(\d+\s*/\s*[a-z0-9\-/]*(?:gcn|sct)[a-z0-9\-/]*)", first_chars=700, pages=first)
    r["so_giay"] = (_clean(v), p)
    # ngày cấp: chỉ dạng "..., ngày D tháng M năm Y" (dạng d/m/y số là ngày của văn bản căn cứ, không phải ngày cấp)
    v, p, _ = doc.search(rf",\s*ngay\s*({D_VN})", first_chars=900, pages=first)
    if v is None:
        v, p, _ = doc.search(rf"cap lan thu[^:\n]{{0,15}}:?\s*ngay\s*({D_VN})", pages=first)
    r["ngay_cap"] = (_clean(v), p)
    v, p, _ = doc.search(r"giam doc\s+(so cong thuong[^\n]*)", pages=first)
    r["co_quan_cap"] = (_clean(v), p)
    v, p, pos = doc.search(r"\b(?!tai\b)t[a-z]{2,3}\s+cua\s+hang\s+ban\s+l[a-z]\s+x[a-z]ng\s+d[a-z]u\s*[:：]?\s*"
                           r"([^\n]+(?:\n(?!\s*(?:dia\s+chi|dien\s+thoai))[^\n]+)?)", pages=first)
    name = _clean(v)
    if name:
        name = re.split(r"\s+dia chi\b", name, flags=re.I)[0].strip(" ;,.")
    r["ten_cua_hang"] = (name, p)
    after = (p, pos[1]) if (pos and p) else None
    v, p2, _ = doc.search(r"dia chi\s*[:：]\s*([^\n]+)", start_after=after, pages=[p] if p else None)
    r["dia_chi_cua_hang"] = (_clean(v), p2)
    v, p, pos = doc.search(r"thuoc\s+so\s+huu\s*(?:cua)?\s*(?:doanh\s+nghiep)?\s*[:：]?\s*"
                           r"((?:cong\s+ty|doanh\s+nghiep|c\.?ty|cty|ho\s+kinh|hop\s+tac|tong\s+cong|chi\s+nhanh|ca\s+nhan|ong\b|ba\b)[^\n]+?)"
                           r"\s*(?:\.\s|\.$|\n|dia\s+chi\s+tru\s+so)")
    owner = _clean(v)
    after = (p, pos[1]) if (pos and p) else None
    v2, _, _ = doc.search(rf"ma so thue\s*[:：]?\s*({TAXC})", start_after=after, pages=[p] if p else None)
    if owner and v2:
        mst = re.sub(r"\s+", "", v2)
        owner = f"{owner}; MST {mst}"
    r["thuong_nhan_chu_so_huu"] = (owner, p)
    v, p, _ = doc.search(r"ten thuong nhan\s*[:：,]?\s*([^\n]+)")
    r["thuong_nhan_cung_cap"] = (_clean(v), p)
    v, p, _ = doc.search(r"(cap lan thu\s*\w+|cap (?:bo sung|doi|lai)[^:\n]{0,20})", pages=first)
    r["lan_cap"] = (_clean(v), p)
    return r


# ==================================================================================================
# CC_TAP_HUAN_VC_HNH (thẻ 2 mặt)
# ==================================================================================================
def rules_cc_tap_huan(doc: Doc) -> Dict[str, Hit]:
    r: Dict[str, Hit] = {}
    # khoảng hiệu lực: "Từ ngày … đến ngày …" NẰM CUỐI trang (cái đầu là ngày tổ chức lớp học, có dấu ':')
    rx = rf"tu\s+ngay\s+({D_VN}|{D_NUM})\s+den\s+ngay\s+({D_VN}|{D_NUM})"
    v1, p1, _ = doc.search(rx, group=1, last=True)
    v2, p2, _ = doc.search(rx, group=2, last=True)
    r["hieu_luc_tu"] = (_clean(v1), p1)
    r["ngay_het_han"] = (_clean(v2), p2)
    v, p, _ = doc.search(r"\bso\s*[:.]\s*(\d+\s*/\s*\d{4}\s*-\s*[a-z]+|\d+\s*-\s*\d{4}\s*/\s*[a-z]+)")
    r["so_gcn"] = (_clean(v), p)
    v, p, _ = doc.search(rf"[a-z ]{{3,25}},\s*ngay\s*({D_VN}|{D_NUM})")
    r["ngay_cap"] = (_clean(v), p)
    # dữ liệu cá nhân: vẫn trích để đo nội bộ, nhưng đầu ra mặc định bỏ nam_sinh
    v, p = _line_value(doc, r"ho\s+va\s+ten")
    if v:
        v = re.split(r"\s+(?:nam\s*/|ngay sinh)", v, flags=re.I)[0].strip()
    r["ho_ten"] = (_clean(v), p)
    v, p, _ = doc.search(rf"ngay\s+sinh\s*[:：]?\s*({D_NUM}|\d{{4}})")
    r["nam_sinh"] = (_clean(v), p)
    v, p, _ = doc.search(r"nghe\s+nghiep\s*[:：]?\s*([^\n]{2,40})")
    if v:
        v = re.split(r"\s{2,}|\bdon vi\b", v)[0]
        if re.search(r"cccd|cmnd|gmnd|ho chieu|so\s*:", fold_keep_len(v)):
            v = None            # nhãn kế bên bị OCR trộn vào dòng
    r["nghe_nghiep"] = (_clean(v), p if v else None)
    v, p, _ = doc.search(r"don\s+vi\s+cong\s+tac\s*[:：]?\s*([^\n]+)")
    r["don_vi_cong_tac"] = (_clean(v), p)
    v, p, _ = doc.search(r"\bdo\s+((?:cong\s+ty|trung\s+tam|truong|doanh\s+nghiep)[^\n]{3,80}?)\s+to\s+chuc")
    if v is None:
        v, p, _ = doc.search(r"((?:cong\s+ty|trung\s+tam)[^\n]{3,80})\n[^\n]*\n?\s*giay\s+chung\s+nhan\s+hoan\s+thanh", pages=doc.order[:1])
    r["don_vi_cap"] = (_clean(v), p)
    return r


# ==================================================================================================
# HD_MUA_BAN
# ==================================================================================================
def _party(doc: Doc, role: str) -> Hit:
    """Tên + MST của bên bán/bên mua. Nhãn 'BÊN BÁN (BÊN A): TÊN' hoặc 'BÊN A: TÊN' (A mặc định = bên bán nếu nhãn không nói rõ).
    Nhãn phải ở ĐẦU DÒNG (tránh "... thanh toán cho Bên A ..." trong thân hợp đồng)."""
    first = doc.order[:1]
    lab = {"ban": r"(?:ben\s+ban|ben\s+a\b|ben\s+cung\s+cap)", "mua": r"(?:ben\s+mua|ben\s+b\b)"}[role]
    v, p, pos = doc.search(
        rf"{lab}[^:\n]{{0,25}}[:：]?[ \t]*((?:cong\s+ty|doanh\s+nghiep|ong\b|ba\b|hop\s+tac|chi\s+nhanh|tong\s+cong\s+ty)[^\n]+)",
        first_chars=6000, pages=first)
    name = _clean(v)
    if not name or p is None or pos is None:
        return None, None
    f = doc.fold[p]
    m = re.compile(r"ben\s+(?:ban|mua|a|b)\b", re.I).search(f, pos[1])
    end = m.start() if m else len(f)
    m2 = re.search(rf"ma\s*so\s*thue\s*[:：]*\s*({TAXC})", f[pos[1]:end])
    mst = re.sub(r"\s+", "", m2.group(1)) if m2 else None
    return (f"{name}; MST {mst}" if mst else name), p


def rules_hd_mua_ban(doc: Doc) -> Dict[str, Hit]:
    r: Dict[str, Hit] = {}
    first = doc.order[:1]
    v, p, _ = doc.search(r"\bso\s*[:.]\s*([0-9a-z][0-9a-z/\-\.]*\d[0-9a-z/\-\.]*)", first_chars=900, pages=first)
    r["so_hop_dong"] = (_clean(v), p)
    v, p, _ = doc.search(rf"hom\s+nay\s*,?\s*(?:ngay\s*)?({D_VN}|{D_NUM})", pages=first)
    r["ngay_ky"] = (_clean(v), p)
    r["ben_ban"] = _party(doc, "ban")
    r["ben_mua"] = _party(doc, "mua")
    # mặt hàng: từ khóa nhiên liệu/dầu nhờn đầu tiên trong vùng ngay sau "Điều 1"
    v, p, pos = doc.search(r"dieu\s*(?:1|i)\b([^\n]*\n?[^\n]*\n?[^\n]*\n?[^\n]*)", first_chars=7000)
    prod = None
    if v and p is not None and pos is not None:
        seg = doc.fold[p][pos[0]:pos[1]]
        m = re.search(r"((?:xang|dau\s+(?:diesel|do\b|nhon|hoa|mazut|may)|diesel|nhot|bon\s+inox|romooc|thiet\s+bi)[^,;\n]{0,50})", seg)
        if m:
            prod = doc.pages[p][pos[0] + m.start(1): pos[0] + m.end(1)]
    r["mat_hang"] = (_clean(prod), p if prod else None)
    v, p, _ = doc.search(r"((?:han\s+muc\s+cong\s+no|cong\s+no\s+toi\s+da)[^\n]{0,160})")
    if v is None:   # điều khoản mẫu "Thời hạn thanh toán công nợ (nếu còn tồn đọng) phải dứt điểm trước khi hợp đồng hết hiệu lực"
        v, p, _ = doc.search(r"(thoi\s+han\s+thanh\s+toan\s+cong\s+no[^\n]{0,120}\n?[^\n]{0,40}?hieu\s+luc)")
    r["han_muc_cong_no"] = (_clean(v), p)
    # điều khoản hiệu lực: chỉ nhận câu bắt đầu bằng "Hợp đồng (này) có hiệu lực" (tránh "luật ... có hiệu lực từ ngày")
    sent = r"hop\s+dong\s*(?:nay)?\s*co\s+hieu\s+luc"
    v, p, _ = doc.search(rf"{sent}\s*(?:tu\s+ngay\s+(?:ky|{DATE})\s*)?den\s+(?:het\s+)?(?:ngay\s*)?({DATE})")
    r["hieu_luc_den"] = (_clean(v), p)
    v, p, _ = doc.search(rf"{sent}\s*tu\s+ngay\s+({DATE})")
    if v is None:
        v2, _, _ = doc.search(rf"{sent}\s*(?:tu\s+)?ngay\s+(k[yi]\b)")
        if v2:
            v, p = r["ngay_ky"]            # "từ ngày ký" -> bằng ngày ký
    r["hieu_luc_tu"] = (_clean(v), p)
    return r


# ==================================================================================================
# PHIEU_XUAT_KHO (biểu mẫu BSR số hóa)
# ==================================================================================================
_NUMLINE = re.compile(r"^\s*\d[\d.,]*\s*$")


def _quantity_table(doc: Doc) -> Tuple[Hit, List[str]]:
    """Tên thành phẩm = dòng sau tiêu đề cột 'M3 thực tế'; rồi bốn số liên tiếp: Bbls | m3 15°C | tấn | m3 thực tế."""
    for pg in doc.order:
        lines = doc.pages[pg].split("\n")
        fl = doc.fold[pg].split("\n")
        for i, ln in enumerate(fl):
            if not re.search(r"m3\s+thuc\s+te\s*$", ln.strip()):
                continue
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j >= len(lines) or _NUMLINE.match(lines[j]):
                continue
            nums: List[str] = []
            for k in range(j + 1, min(len(lines), j + 8)):
                if _NUMLINE.match(lines[k]):
                    nums.append(lines[k].strip())
                    if len(nums) == 4:
                        break
            return (_clean(lines[j]), pg), nums
    return (None, None), []


def rules_phieu_xuat_kho(doc: Doc) -> Dict[str, Hit]:
    r: Dict[str, Hit] = {}
    v, p, _ = doc.search(r"\bso\s*[:.]\s*(\d{4,})\b", first_chars=600)
    r["so_phieu"] = (_clean(v), p)
    r["ky_hieu"] = _line_value(doc, r"ky\s+hieu", first_chars=600)
    v, p, _ = doc.search(rf"^ngay\s*[:.]\s*({D_NUM}|{D_VN})", flags=re.I | re.M, first_chars=600)
    r["ngay_xuat"] = (_clean(v), p)
    r["ben_giao"] = _line_value(doc, r"^ben\s+giao", flags=re.I | re.M)
    v, p, _ = doc.search(r"^ben\s+nhan\s*[:：]\s*([^\n]+)", flags=re.I | re.M)
    r["ben_nhan"] = (_clean(v), p)
    v, p, _ = doc.search(rf"hop\s+dong\s+so\s*([^\s]+\s*(?:ngay\s*)?{DATE})")
    r["hop_dong_can_cu"] = (_clean(v), p)
    # số lệnh xuất hàng kèm mã trong ngoặc (SAP) như người chú thích chép: "753/LXHXB-DO-290126-297-0 (8000148753)"
    v, p, _ = doc.search(r"lenh\s+xuat\s+hang\s*[:：]\s*([^\n(]+(?:\([^)\n]*\))?)")
    r["lenh_xuat_hang"] = (_clean(v), p)
    v, p, _ = doc.search(r"xuat\s+tai\s+bon(?:\s+so)?\s*[:：]\s*([^\n]+?)(?:\s{2,}|\s+kho\s*:|\n|$)")
    r["bon_xuat"] = (_clean(v), p)
    v, p, _ = doc.search(r"^phuong\s+tien\s*[:：]\s*([^\n]*\d[^\n]*)", flags=re.I | re.M)
    if v:
        v = re.split(r"\s+(?:den|bat dau|ket thuc)\s", v, flags=re.I)[0]
    r["bien_so_phuong_tien"] = (_clean(v), p)
    v, p, _ = doc.search(r"\b([a-z]{1,5}-\d{3}-\d{8,}[a-z0-9]*)")
    r["so_chung_thu_chat_luong"] = (v.upper() if v else None, p)
    prod, nums = _quantity_table(doc)
    r["mat_hang"] = prod
    if len(nums) == 4:
        pg = prod[1]
        r["so_luong_m3_15c"], r["so_luong_tan"], r["so_luong_m3_thuc_te"] = (nums[1], pg), (nums[2], pg), (nums[3], pg)
    return r


RULES: Dict[str, Callable[[Doc], Dict[str, Hit]]] = {
    "GCN_DDK_BAN_LE_XD": rules_gcn_ddk,
    "CC_TAP_HUAN_VC_HNH": rules_cc_tap_huan,
    "HD_MUA_BAN": rules_hd_mua_ban,
    "PHIEU_XUAT_KHO": rules_phieu_xuat_kho,
}


def apply_rules(doc_type: str, pages: Dict[int, str]) -> Dict[str, Hit]:
    """Áp luật của `doc_type` lên {trang: văn bản}. Loại chưa có luật -> {} (không phải lỗi: các trường sẽ là null)."""
    fn = RULES.get(doc_type)
    return fn(Doc(pages)) if fn else {}
