"""expiry_rules.py - Quy tắc TỰ NHẬN / TỪ CHỐI cho trường hạn dựa trên sự đồng thuận giữa các nguồn độc lập (Nhóm 4).

Một ngày hết hạn sai còn tệ hơn bỏ trống (lịch nhắc sai), nên máy chỉ TỰ NHẬN một ngày khi các nguồn đồng thuận; ngược lại chuyển người duyệt.
Nguồn (mỗi nguồn là ngày ISO đầy đủ `YYYY-MM-DD` hoặc None):
    regex     luật trên văn bản OCR
    llm       LLM cục bộ trên văn bản OCR  (cùng văn bản OCR với regex => hai nguồn này KHÔNG độc lập khi OCR đọc sai chữ số)
    vlm       mô hình thị giác cục bộ đọc ảnh trang (độc lập với OCR)
    filename  ngày trong tên tệp (quy tắc đặt tên chưa được công ty xác nhận)
Tên quy tắc -> hàm (candidates) -> ngày | None. Dùng chung giữa `src/extraction` và thí nghiệm (`experiments/02_methods/combine.py`).
"""

from __future__ import annotations

from collections import Counter
from typing import Callable, Dict, Optional, Sequence

Candidates = Dict[str, Optional[str]]


def full_date(n: Optional[str]) -> Optional[str]:
    """Chỉ chấp nhận ngày ISO đầy đủ (không phải 'YYYY-MM' hay giá trị rác)."""
    return n if (isinstance(n, str) and len(n) == 10 and not n.startswith("~")) else None


def agree(c: Candidates, need: Sequence[str]) -> Optional[str]:
    vals = [c.get(s) for s in need]
    return vals[0] if vals and vals[0] and all(v == vals[0] for v in vals) else None


def k_of(c: Candidates, names: Sequence[str], k: int) -> Optional[str]:
    """Ngày được >= k nguồn trong `names` nêu, với điều kiện không hòa phiếu với một ngày khác."""
    cnt = Counter(c[s] for s in names if c.get(s))
    if not cnt:
        return None
    (val, n), = cnt.most_common(1)
    if n >= k and sum(1 for _v, m in cnt.items() if m == n) == 1:
        return val
    return None


EXPIRY_RULES: Dict[str, Callable[[Candidates], Optional[str]]] = {
    "regex": lambda c: c.get("regex"),
    "llm": lambda c: c.get("llm"),
    "vlm": lambda c: c.get("vlm"),
    "filename": lambda c: c.get("filename"),
    "regex=llm": lambda c: agree(c, ["regex", "llm"]),
    "llm=vlm": lambda c: agree(c, ["llm", "vlm"]),
    "regex=vlm": lambda c: agree(c, ["regex", "vlm"]),
    "regex=llm=vlm": lambda c: agree(c, ["regex", "llm", "vlm"]),
    "2-of-3 (regex,llm,vlm)": lambda c: k_of(c, ["regex", "llm", "vlm"], 2),
    "vlm=filename": lambda c: agree(c, ["vlm", "filename"]),
    "llm=filename": lambda c: agree(c, ["llm", "filename"]),
    "regex=filename": lambda c: agree(c, ["regex", "filename"]),
    "2-of-4 (regex,llm,vlm,filename)": lambda c: k_of(c, ["regex", "llm", "vlm", "filename"], 2),
    "(llm=vlm) or (any-two incl. filename)": lambda c: agree(c, ["llm", "vlm"]) or k_of(c, ["regex", "llm", "vlm", "filename"], 2),
    "(regex=vlm) or (llm=vlm) or (any OCR-method = filename)": lambda c: (agree(c, ["regex", "vlm"]) or agree(c, ["llm", "vlm"])
                                                                          or agree(c, ["regex", "filename"]) or agree(c, ["llm", "filename"])),
    "any-model=filename": lambda c: (agree(c, ["vlm", "filename"]) or agree(c, ["llm", "filename"]) or agree(c, ["regex", "filename"])),
    "(llm=vlm) or any-model=filename": lambda c: (agree(c, ["vlm", "filename"]) or agree(c, ["llm", "filename"]) or agree(c, ["regex", "filename"])
                                                  or agree(c, ["llm", "vlm"])),
}
