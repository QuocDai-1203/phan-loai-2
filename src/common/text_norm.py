"""text_norm.py - Chuẩn hóa văn bản tiếng Việt để so khớp từ khóa (dùng chung cho mọi nhóm).

Văn bản OCR thực tế thường mất dấu ("DON DAT HANG"), dính chữ ("DICHVUHIEPHOA")
hoặc lệch khoảng trắng, nên so khớp từ khóa có dấu kiểu "ĐƠN ĐẶT HÀNG" gần như không bao giờ trúng.
Module này chuẩn hóa CẢ HAI PHÍA (văn bản và từ khóa) về cùng một dạng trước khi so sánh:
- NFD + bỏ dấu thanh/dấu mũ, đ/Đ -> d, casefold, gộp mọi khoảng trắng thành 1 dấu cách.
- Dạng "dính" (squashed): bỏ luôn mọi ký tự không phải chữ/số để bắt được chữ OCR dính liền.
"""

import re
import unicodedata
from typing import Iterable, Optional

# Từ khóa dạng dính ngắn hơn ngưỡng này dễ trùng ngẫu nhiên giữa các từ -> chỉ so khớp dạng có khoảng trắng.
SQUASH_MIN_LEN = 6

_WS_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[\W_]+", re.UNICODE)


def normalize_text(text: Optional[str]) -> str:
    """Bỏ dấu, đ->d, casefold, gộp khoảng trắng. Ví dụ: 'Đơn  ĐẶT\nhàng' -> 'don dat hang'."""
    if not text:
        return ""
    text = text.replace("đ", "d").replace("Đ", "D")
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return _WS_RE.sub(" ", stripped.casefold()).strip()


def squash_text(text: Optional[str]) -> str:
    """Dạng 'dính': như normalize_text nhưng bỏ mọi khoảng trắng và dấu câu ('don dat hang' -> 'dondathang')."""
    return _NON_ALNUM_RE.sub("", normalize_text(text))


class NormalizedText:
    """Văn bản đã chuẩn hóa sẵn hai dạng (có khoảng trắng / dính) để so khớp nhiều từ khóa nhanh."""

    def __init__(self, text: Optional[str]):
        self.spaced = normalize_text(text)
        self.squashed = _NON_ALNUM_RE.sub("", self.spaced)

    def match_mode(self, keyword: str) -> Optional[str]:
        """Trả về 'exact' (trúng ở dạng có khoảng trắng), 'glued' (chỉ trúng ở dạng dính) hoặc None."""
        kw_spaced = normalize_text(keyword)
        if not kw_spaced:
            return None
        if kw_spaced in self.spaced:
            return "exact"
        kw_squashed = _NON_ALNUM_RE.sub("", kw_spaced)
        if len(kw_squashed) >= SQUASH_MIN_LEN and kw_squashed in self.squashed:
            return "glued"
        return None

    def contains(self, keyword: str) -> bool:
        return self.match_mode(keyword) is not None

    def contains_any(self, keywords: Iterable[str]) -> bool:
        return any(self.contains(kw) for kw in keywords)


def contains_keyword(text: Optional[str], keyword: str) -> bool:
    """Tiện ích một lần: văn bản có chứa từ khóa không (bất kể dấu / khoảng trắng / chữ dính)."""
    return NormalizedText(text).contains(keyword)
