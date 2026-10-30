"""page_heuristics.py - Cờ heuristic theo từ khóa cho một trang OCR (dùng chung cho mọi OCR engine).

CẢNH BÁO: đây KHÔNG phải bộ phát hiện con dấu / chữ ký trên ảnh. Chỉ kiểm tra văn bản OCR có chứa
từ khóa thường đi kèm quốc hiệu hoặc ô ký tên hay không (không phân biệt dấu/khoảng trắng).
"""

from typing import Tuple
from src.common.text_norm import NormalizedText

# Từ khóa gợi ý có quốc hiệu / tiêu ngữ / con dấu ở đầu trang
HEADER_SEAL_KEYWORDS = ["CỘNG HÒA", "VIỆT NAM", "QUỐC GIA"]
# Từ khóa gợi ý có ô ký tên ở cuối trang
SIGNATURE_BOX_KEYWORDS = ["KÝ, GHI RÕ HỌ TÊN", "ĐẠI DIỆN BÊN"]


def detect_keyword_flags(text: str) -> Tuple[bool, bool]:
    """Trả về (has_header_seal, has_signature_box) theo khớp từ khóa trên văn bản OCR."""
    norm = NormalizedText(text)
    return norm.contains_any(HEADER_SEAL_KEYWORDS), norm.contains_any(SIGNATURE_BOX_KEYWORDS)
