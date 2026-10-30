"""page_features.py - Đặc trưng văn bản của MỘT trang, dùng chung cho bộ luật v2 và bộ phân loại cặp trang (Nhóm 2).

Mọi so khớp đều không phân biệt dấu/khoảng trắng (src.common.text_norm). Không dùng hộp tọa độ (ocr_v2.jsonl không lưu),
nên "đầu trang" nghĩa là K dòng văn bản đầu tiên (thứ tự đọc của OCR).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple

from src.common.text_norm import NormalizedText, normalize_text

MOTTO = "CỘNG HÒA XÃ HỘI"

# Tiêu đề chứng từ (bản cũ của boundary_detector.TITLE_KEYWORDS, giữ nguyên để so sánh công bằng)
TITLE_KEYWORDS = [
    "HỢP ĐỒNG", "PHỤ LỤC", "THANH LÝ", "PHIẾU XUẤT KHO", "BIÊN BẢN", "CHỨNG THƯ CHẤT LƯỢNG", "CERTIFICATE",
    "GIẤY CHỨNG NHẬN", "ĐƠN ĐẶT HÀNG", "GIẤY XÁC NHẬN", "HỒ SƠ",
]

# Cụm từ thường gặp trên trang chỉ có chữ ký / con dấu
SIGNATURE_PHRASES = [
    "ký", "ký tên", "ghi rõ họ tên", "họ tên", "đại diện", "người lập", "người nhận", "người giao", "thủ trưởng", "giám đốc",
    "kế toán", "thủ kho", "bên a", "bên b", "đóng dấu", "ký, ghi rõ", "văn bản được tải lên hệ thống", "trang",
]

_PAGE_NO_RE = re.compile(r"(?:\btrang|\bpage)\s*(\d{1,3})\s*(?:/|of)\s*(\d{1,3})\b|(?:^|\s)(\d{1,2})\s*/\s*(\d{1,2})\s*$")
_PAGE_ONLY_RE = re.compile(r"\b(?:trang|page)\s*(\d{1,3})\b(?!\s*[/\d])")
_DIGITS_RE = re.compile(r"\d{4,}")
_DATE_RE = re.compile(r"\b\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}\b")
_NUMBER_NO_RE = re.compile(r"(?:so|no)\s*[:.\-]?\s*([a-z0-9][a-z0-9/\-\.]{1,24})")


def split_lines(text: str) -> List[str]:
    return [ln.strip() for ln in (text or "").split("\n") if ln.strip()]


@dataclass
class PageFeat:
    """Đặc trưng một trang (tính một lần, dùng lại cho cặp trang)."""
    n_chars: int
    n_lines: int
    head_norm: str                       # K dòng đầu đã chuẩn hóa, nối bằng dấu cách
    head_tokens: frozenset               # token của head_norm
    tokens: frozenset                    # token toàn trang
    motto_top: bool                      # quốc hiệu trong K dòng đầu
    motto_any: bool
    title_top: Optional[str]             # từ khóa tiêu đề trong N dòng đầu (hoặc None)
    title_at_line_start: bool            # có dòng (trong N dòng đầu) bắt đầu bằng từ khóa tiêu đề
    page_no: Optional[Tuple[int, int]]   # (n, m) nếu thấy "n/m" hoặc "trang n/m"; m=0 nếu chỉ thấy "trang n"
    signature_only: bool
    ids: frozenset                       # số dài, ngày, số hiệu "Số: ..." (để so khác bản)
    doc_no: frozenset                    # chỉ số hiệu "Số: ..." / "No: ..."
    dates: frozenset


def _page_no(lines: Sequence[str]) -> Optional[Tuple[int, int]]:
    """Tìm đánh số trang ở 3 dòng đầu / 3 dòng cuối."""
    cand = list(lines[:3]) + list(lines[-3:])
    for ln in reversed(cand):
        n = normalize_text(ln)
        m = _PAGE_NO_RE.search(n)
        if m:
            a, b = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
            a, b = int(a), int(b)
            if 1 <= a <= b <= 99:
                return a, b
        m = _PAGE_ONLY_RE.search(n)
        if m and len(n) < 40:
            return int(m.group(1)), 0
    return None


def _signature_only(lines: Sequence[str], n_chars: int, max_rest: int = 160) -> bool:
    """Trang gần như chỉ có chữ ký/con dấu: sau khi bỏ các dòng chứa cụm từ chữ ký còn rất ít chữ."""
    if n_chars == 0:
        return True
    rest, n_hit = 0, 0
    for ln in lines:
        nl = normalize_text(ln)
        hit = any(p in nl for p in ("ky ten", "ghi ro ho ten", "dai dien", "nguoi lap", "nguoi nhan", "nguoi giao", "thu truong",
                                    "ke toan", "thu kho", "dong dau", "van ban duoc tai len he thong", "giam doc"))
        n_hit += int(hit)
        if not hit and not re.fullmatch(r"[\W\d_]*", nl):
            rest += len(nl)
    return n_hit >= 1 and rest <= max_rest     # phải có ít nhất một cụm từ chữ ký, nếu không trang ngắn chỉ là trang ngắn


def page_feat(text: str, head_lines: int = 6) -> PageFeat:
    lines = split_lines(text)
    head = " ".join(lines[:head_lines])
    head_norm = NormalizedText(head)
    head_n = NormalizedText(" ".join(lines[:head_lines]))
    toks = frozenset(re.findall(r"\w+", normalize_text(text)))
    htoks = frozenset(re.findall(r"\w+", head_norm.spaced))
    title = next((kw for kw in TITLE_KEYWORDS if head_n.contains(kw)), None)
    kw_norm = [normalize_text(k) for k in TITLE_KEYWORDS]
    at_start = any(normalize_text(ln).lstrip("0123456789.-) ").startswith(k) for ln in lines[:head_lines] for k in kw_norm)
    norm_full = normalize_text(text)
    dates = frozenset(_DATE_RE.findall(norm_full))
    nos = frozenset(m.group(1).strip("./-") for m in _NUMBER_NO_RE.finditer(norm_full) if any(ch.isdigit() for ch in m.group(1)))
    digs = frozenset(_DIGITS_RE.findall(norm_full))
    return PageFeat(
        n_chars=len((text or "").strip()), n_lines=len(lines), head_norm=head_norm.spaced, head_tokens=htoks, tokens=toks,
        motto_top=head_n.contains(MOTTO), motto_any=NormalizedText(text).contains(MOTTO), title_top=title, title_at_line_start=at_start,
        page_no=_page_no(lines), signature_only=_signature_only(lines, len((text or "").strip())),
        ids=frozenset(digs | dates | nos), doc_no=nos, dates=dates,
    )


def jaccard(a: frozenset, b: frozenset) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)
