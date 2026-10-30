"""normalize.py - Chuẩn hóa giá trị trường tiếng Việt để so sánh (Nhóm 4, việc T3).

Một giá trị "thô" (đúng như in trên giấy hoặc do mô hình trả) được đưa về một dạng chuẩn để hai cách viết khác nhau
của cùng một sự thật so sánh bằng nhau:

    ngày      "ngày 12 tháng 01 năm 2028", "12/1/28", "12.1.28"  ->  "2028-01-12"  (ISO 8601)
              "tháng 01 năm 2028" -> "2028-01"; "năm 2028" / "2028" -> "2028"  (ngày không đầy đủ: giữ nguyên độ chi tiết)
    số        "10.000,5" -> "10000.5"; "10.000" -> "10000" (quy ước Việt Nam: '.' ngăn nghìn, ',' là dấu thập phân)
    mã số thuế  "0301234567-001" -> "0301234567001" (chỉ chữ số)
    mã định danh (số phiếu, số giấy, biển số)  chữ hoa, bỏ dấu tiếng Việt, bỏ khoảng trắng/dấu ngăn thừa
    văn bản   NFC + casefold + gộp khoảng trắng + bỏ dấu câu ở hai đầu

Quy ước giá trị vắng: `None`, chuỗi rỗng hoặc chỉ khoảng trắng -> trả `None` (không có giá trị).
Nếu giá trị KHÔNG rỗng nhưng không phân tích được theo kiểu yêu cầu (ví dụ ngày rác), hàm trả `"~raw:" + văn bản chuẩn hóa`
chứ KHÔNG trả `None`: một giá trị sai vẫn là "có giá trị" (FP/FN), không được âm thầm coi là bỏ trống.

Chỉ phụ thuộc thư viện chuẩn của Python.
"""

from __future__ import annotations

import datetime as _dt
import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import List, Optional, Tuple

RAW_PREFIX = "~raw:"

_WS = re.compile(r"\s+")


# --------------------------------------------------------------------------------------------------
# Văn bản
# --------------------------------------------------------------------------------------------------
def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def fold_text(s: Optional[str]) -> str:
    """Chữ thường, bỏ dấu tiếng Việt (đ -> d), gộp khoảng trắng. Dùng để so sánh/khớp từ khóa không phân biệt dấu."""
    if not s:
        return ""
    s = unicodedata.normalize("NFC", s).lower().replace("đ", "d")
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return _WS.sub(" ", s).strip()


def fold_keep_len(s: Optional[str]) -> str:
    """Như fold_text nhưng GIỮ NGUYÊN ĐỘ DÀI và vị trí từng ký tự (1 ký tự vào -> 1 ký tự ra): chữ thường, bỏ dấu, đ -> d.
    Cho phép chạy regex không dấu rồi cắt nguyên văn bằng cùng chỉ số."""
    if not s:
        return ""
    out = []
    for ch in unicodedata.normalize("NFC", s):
        lo = ch.lower()
        if lo == "đ":
            out.append("d")
            continue
        base = "".join(c for c in unicodedata.normalize("NFD", lo) if unicodedata.category(c) != "Mn")
        out.append(base[0] if len(base) == 1 else (base[:1] or lo))
    return "".join(out)


def _is_blank(s: Optional[str]) -> bool:
    return s is None or not str(s).strip()


def normalize_text(s: Optional[str], strip_diacritics: bool = False) -> Optional[str]:
    """NFC + casefold + gộp khoảng trắng + bỏ dấu câu ở hai đầu. `strip_diacritics=True`: so sánh không phân biệt dấu."""
    if _is_blank(s):
        return None
    t = unicodedata.normalize("NFC", str(s))
    t = _WS.sub(" ", t).strip().strip(".,;:·-–—_ ").strip()
    t = fold_text(t) if strip_diacritics else t.casefold()
    return t or None


# --------------------------------------------------------------------------------------------------
# Ngày
# --------------------------------------------------------------------------------------------------
_SEP = r"\s*[/\-.]\s*"
_RE_VN_FULL = re.compile(r"(?<!\d)(\d{1,2})\s*(?:tháng|thang|th\.?)\s*(\d{1,2})\s*(?:năm|nam)\s*(\d{4}|\d{2})(?!\d)", re.I)
_RE_VN_MY = re.compile(r"(?:tháng|thang)\s*(\d{1,2})\s*(?:năm|nam)\s*(\d{4})(?!\d)", re.I)
_RE_VN_Y = re.compile(r"(?:năm|nam)\s*(\d{4})(?!\d)", re.I)
_RE_ISO = re.compile(r"(?<!\d)(\d{4})-(\d{1,2})-(\d{1,2})(?!\d)")
_RE_DMY = re.compile(rf"(?<![\d/.])(\d{{1,2}}){_SEP}(\d{{1,2}}){_SEP}(\d{{4}}|\d{{2}})(?![\d]|[/\-.]\d)")
_RE_MY = re.compile(rf"(?<![\d/.])(\d{{1,2}}){_SEP}(\d{{4}})(?![\d]|[/\-.]\d)")
_RE_Y = re.compile(r"^\D*((?:19|20)\d{2})\D*$")


def _year(y: str) -> int:
    n = int(y)
    if len(y) == 2:
        return 2000 + n if n <= 69 else 1900 + n
    return n


def _valid_date(y: int, m: int, d: int) -> Optional[str]:
    try:
        return _dt.date(y, m, d).isoformat()
    except ValueError:
        return None


def find_dates(s: Optional[str]) -> List[Tuple[str, Tuple[int, int]]]:
    """Mọi ngày tìm thấy trong chuỗi: [(iso, (start, end))] theo thứ tự xuất hiện. iso có thể là YYYY-MM-DD / YYYY-MM / YYYY."""
    if _is_blank(s):
        return []
    t = unicodedata.normalize("NFC", str(s))
    found: List[Tuple[str, Tuple[int, int]]] = []
    taken: List[Tuple[int, int]] = []

    def add(iso: Optional[str], m: "re.Match") -> None:
        if iso is None:
            return
        span = m.span()
        if any(not (span[1] <= a or span[0] >= b) for a, b in taken):
            return
        taken.append(span)
        found.append((iso, span))

    for m in _RE_VN_FULL.finditer(t):
        add(_valid_date(_year(m.group(3)), int(m.group(2)), int(m.group(1))), m)
    for m in _RE_ISO.finditer(t):
        add(_valid_date(int(m.group(1)), int(m.group(2)), int(m.group(3))), m)
    for m in _RE_DMY.finditer(t):
        add(_valid_date(_year(m.group(3)), int(m.group(2)), int(m.group(1))), m)
    for m in _RE_VN_MY.finditer(t):
        mo = int(m.group(1))
        add(f"{int(m.group(2)):04d}-{mo:02d}" if 1 <= mo <= 12 else None, m)
    for m in _RE_MY.finditer(t):
        mo = int(m.group(1))
        add(f"{int(m.group(2)):04d}-{mo:02d}" if 1 <= mo <= 12 else None, m)
    for m in _RE_VN_Y.finditer(t):
        add(f"{int(m.group(1)):04d}", m)
    found.sort(key=lambda x: x[1][0])
    return found


def normalize_date(s: Optional[str]) -> Optional[str]:
    """Ngày đầu tiên trong chuỗi -> ISO; chuỗi chỉ có một năm ("1985") -> "1985". Không phân tích được -> RAW_PREFIX + văn bản."""
    if _is_blank(s):
        return None
    dates = find_dates(s)
    if dates:
        return dates[0][0]
    m = _RE_Y.match(str(s).strip())
    if m:
        return m.group(1)
    return RAW_PREFIX + (normalize_text(s) or "")


# --------------------------------------------------------------------------------------------------
# Số
# --------------------------------------------------------------------------------------------------
_RE_NUM = re.compile(r"[-+]?\d[\d.,\s]*\d|[-+]?\d")


def _parse_vn_number(tok: str) -> Optional[Decimal]:
    tok = tok.strip().replace(" ", "").replace(" ", "")
    sign = ""
    if tok[:1] in "+-":
        sign, tok = ("-" if tok[0] == "-" else ""), tok[1:]
    if not tok:
        return None
    has_dot, has_comma = "." in tok, "," in tok
    if has_dot and has_comma:
        # dấu cuối cùng là dấu thập phân (VN: "10.000,5"; chấp nhận cả "10,000.5" kiểu Anh)
        dec = "," if tok.rfind(",") > tok.rfind(".") else "."
        thou = "." if dec == "," else ","
        tok = tok.replace(thou, "").replace(dec, ".")
    elif has_comma:
        parts = tok.split(",")
        # Quy ước Việt Nam: một dấu phẩy = thập phân ("5,500" = 5,5 m3). Nhiều dấu phẩy = ngăn nghìn kiểu Anh.
        tok = tok.replace(",", "") if len(parts) > 2 else tok.replace(",", ".")
    elif has_dot:
        parts = tok.split(".")
        # "10.000", "1.234.567" = ngăn nghìn (nhóm 3 chữ số, nhóm đầu 1-3); "10.5", "0.250" = thập phân
        if len(parts) > 2 or (len(parts[-1]) == 3 and 1 <= len(parts[0]) <= 3 and parts[0] != "0"):
            tok = tok.replace(".", "")
    try:
        return Decimal(sign + tok)
    except InvalidOperation:
        return None


def canonical_decimal(d: Decimal) -> str:
    s = format(d.normalize(), "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def normalize_number(s: Optional[str]) -> Optional[str]:
    """Số kiểu Việt Nam -> chuỗi thập phân chuẩn ("10.000,5" -> "10000.5"). Lấy số đầu tiên; bỏ đơn vị ("m3", "tấn")."""
    if _is_blank(s):
        return None
    m = _RE_NUM.search(str(s).replace(" ", " "))
    if m:
        d = _parse_vn_number(m.group(0))
        if d is not None:
            return canonical_decimal(d)
    return RAW_PREFIX + (normalize_text(s) or "")


# --------------------------------------------------------------------------------------------------
# Mã số thuế và mã định danh
# --------------------------------------------------------------------------------------------------
_RE_MST = re.compile(r"(?<!\d)(\d{10})(?:\s*[-.]?\s*(\d{3}))?(?!\d)")


def normalize_tax_code(s: Optional[str]) -> Optional[str]:
    """Mã số thuế: chỉ chữ số. Nếu trong chuỗi có mẫu 10 chữ số (+ "-001" chi nhánh) thì lấy mẫu đó, ngược lại lấy mọi chữ số."""
    if _is_blank(s):
        return None
    m = _RE_MST.search(str(s))
    if m:
        return m.group(1) + (m.group(2) or "")
    digits = re.sub(r"\D", "", str(s))
    return digits or RAW_PREFIX + (normalize_text(s) or "")


def extract_tax_codes(s: Optional[str]) -> List[str]:
    """Mọi mã số thuế dạng 10 (hoặc 13) chữ số trong một chuỗi (dùng cho trường 'tên + MST' như ben_ban)."""
    if _is_blank(s):
        return []
    return [m.group(1) + (m.group(2) or "") for m in _RE_MST.finditer(str(s))]


_RE_ID_PREFIX = re.compile(r"^\s*(?:số|so|no|n[º°o]\.?)\s*[:.]?\s*", re.I)


def normalize_id(s: Optional[str], kind: str = "document_no") -> Optional[str]:
    """Mã định danh. kind: 'tax_code' | 'plate' (biển số) | 'document_no' (số phiếu/giấy/hợp đồng) | 'generic'.

    Luôn bỏ dấu tiếng Việt và viết hoa (OCR/LLM hay lệch dấu ở 'HĐ' vs 'HD'). 'plate' bỏ mọi ký tự không phải chữ-số
    ("51C-123.45" -> "51C12345"); 'document_no' bỏ khoảng trắng quanh '/', '-', '.' và tiền tố "Số:".
    """
    if _is_blank(s):
        return None
    if kind == "tax_code":
        return normalize_tax_code(s)
    t = fold_text(s).upper()
    if kind == "plate":
        t = re.sub(r"[^A-Z0-9]", "", t)
        return t or RAW_PREFIX + (normalize_text(s) or "")
    t = _RE_ID_PREFIX.sub("", t)
    t = re.sub(r"\s*([/\-.])\s*", r"\1", t)
    t = _WS.sub("", t).strip("./-:;,")
    return t or RAW_PREFIX + (normalize_text(s) or "")


# --------------------------------------------------------------------------------------------------
# Điểm vào chung
# --------------------------------------------------------------------------------------------------
def normalize_value(value: Optional[str], field_type: str, id_kind: Optional[str] = None,
                    strip_diacritics: bool = False) -> Optional[str]:
    """Chuẩn hóa theo kiểu trường của schema (`date`/`number`/`id`/`text`). None nghĩa là không có giá trị.

    `strip_diacritics` chỉ ảnh hưởng kiểu `text` (các kiểu còn lại đã bỏ dấu hoặc không có chữ).
    """
    if _is_blank(value):
        return None
    if field_type == "date":
        return normalize_date(value)
    if field_type == "number":
        return normalize_number(value)
    if field_type == "id":
        return normalize_id(value, id_kind or "document_no")
    if field_type == "text":
        return normalize_text(value, strip_diacritics=strip_diacritics)
    raise ValueError(f"Kiểu trường không hợp lệ: {field_type!r} (cần date/number/id/text)")


def is_raw(norm: Optional[str]) -> bool:
    """True nếu giá trị chuẩn hóa là 'giá trị rác không phân tích được' (RAW_PREFIX)."""
    return bool(norm) and norm.startswith(RAW_PREFIX)


# --------------------------------------------------------------------------------------------------
# So sánh "mềm" cho văn bản (báo cáo SONG SONG với so sánh chặt, không thay thế nó)
# --------------------------------------------------------------------------------------------------
_RE_MST_WORDS = re.compile(r"\b(?:mst|ma so thue|ma so doanh nghiep|msdn)\b")


def lenient_text(s: Optional[str]) -> str:
    """NFC + chữ thường + bỏ dấu tiếng Việt + mọi dấu câu/ký hiệu thành khoảng trắng + gộp khoảng trắng; bỏ chữ 'MST'/'mã số thuế'."""
    if _is_blank(s):
        return ""
    t = fold_text(s)
    t = re.sub(r"[^0-9a-z]+", " ", t)
    t = _RE_MST_WORDS.sub(" ", t)
    return _WS.sub(" ", t).strip()


def lenient_text_equal(a: Optional[str], b: Optional[str]) -> bool:
    """Hai chuỗi văn bản 'giống nhau' theo nghĩa mềm: bằng nhau sau `lenient_text`, hoặc chuỗi ngắn (>= 4 ký tự) là một cụm từ TRỌN VẸN nằm trong chuỗi dài
    (trường gộp 'tên + mã số thuế': 'Công ty A; MST 0301234567' khớp 'Công ty A'). Nếu cả hai đều có mã số thuế mà khác hẳn nhau thì KHÔNG khớp."""
    ta, tb = set(extract_tax_codes(a)), set(extract_tax_codes(b))
    if ta and tb and not (ta & tb):
        return False
    strip = lambda x: re.sub(_RE_MST.pattern, " ", str(x or ""))      # noqa: E731 - bỏ mã số thuế trước khi so tên
    la, lb = lenient_text(strip(a)), lenient_text(strip(b))
    if not la or not lb:
        return la == lb
    if la == lb:
        return True
    short, long_ = sorted((la, lb), key=len)
    return len(short) >= 4 and f" {short} " in f" {long_} "
