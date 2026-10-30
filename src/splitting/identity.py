"""identity.py - Dấu hiệu "BẢN KHÁC" giữa hai trang liền kề (Nhóm 2, T5: nhiều bản cùng loại trong một tệp).

Hai tờ cùng biểu mẫu (biên nhận thế chấp, giấy chứng nhận kiểm định, biên bản giao hàng...) có chữ gần như giống hệt nhau; chỉ định danh
(số văn bản / số giấy chứng nhận, ngày, số lượng trong bảng) khác. Mô-đun này trích định danh bằng regex trên văn bản của từng trang và
SO SÁNH giữa trang i-1 và trang i: kết quả chỉ là cờ khớp/khác và số đếm. **Giá trị định danh chỉ sống trong bộ nhớ của lời gọi hàm**:
không có hàm nào ghi, trả hay in giá trị (chỉ `PageIdentity` nội bộ giữ chúng, không có `__repr__` giá trị ra log).

Lưu ý OCR: số hiệu thường bị đọc sai một-hai ký tự giữa hai trang của CÙNG một tờ (nhất là trang dính hai mặt); vì vậy ngoài cờ "khác"
còn có khoảng cách sửa chuẩn hóa để bộ phân loại tự cân nhắc, và chỉ so khi CẢ HAI trang có định danh.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import FrozenSet, List, Optional, Sequence

from src.common.text_norm import normalize_text

HEAD_LINES = 12

# nhãn số hiệu: "số", "no", "n°"... theo sau là giá trị chữ-số (phải có ít nhất 1 chữ số)
_NO_RE = re.compile(r"(?:^|[^a-z0-9])(?:so|no|n0|nº|n°)\s*(?:\(\s*n\s*\??\s*\))?\s*[:.\-]?\s*([a-z0-9][a-z0-9/\-\.]{1,24})")
_DATE_RE = re.compile(r"\b(\d{1,2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{2,4})\b")
_DATE_VN_RE = re.compile(r"ngay\s*(\d{1,2})\s*thang\s*(\d{1,2})\s*nam\s*(\d{2,4})")
_NUM_RE = re.compile(r"\d{3,}")


def _alnum(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s)


def edit_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a or not b:
        return max(len(a), len(b))
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


@dataclass(frozen=True)
class PageIdentity:
    head_no: Optional[str] = field(default=None, repr=False)          # số hiệu đầu tiên trong HEAD_LINES dòng đầu (đã bỏ dấu câu)
    head_dates: FrozenSet[str] = field(default_factory=frozenset, repr=False)
    numbers: FrozenSet[str] = field(default_factory=frozenset, repr=False)   # mọi dãy >= 3 chữ số toàn trang
    n_chars: int = 0


def page_identity(text: str) -> PageIdentity:
    lines = [ln for ln in (text or "").split("\n") if ln.strip()]
    head = normalize_text(" \n ".join(lines[:HEAD_LINES]))
    full = normalize_text(text)
    head_no = None
    for m in _NO_RE.finditer(head):
        v = _alnum(m.group(1))
        if any(ch.isdigit() for ch in v) and len(v) >= 2:
            head_no = v
            break
    dates = {f"{int(a)}/{int(b)}/{int(c) % 100}" for a, b, c in _DATE_RE.findall(head)}
    dates |= {f"{int(a)}/{int(b)}/{int(c) % 100}" for a, b, c in _DATE_VN_RE.findall(head)}
    return PageIdentity(head_no=head_no, head_dates=frozenset(dates), numbers=frozenset(_NUM_RE.findall(full)), n_chars=len((text or "").strip()))


ID_FEATURE_NAMES = [
    "id_head_no_both", "id_head_no_differ", "id_head_no_dist",
    "id_head_date_both", "id_head_date_differ",
    "id_num_only_frac", "id_num_shared", "id_num_only_total",
]


def identity_features(a: PageIdentity, b: PageIdentity) -> List[float]:
    """So khớp định danh của trang trước (a) và trang sau (b). Trả danh sách số theo `ID_FEATURE_NAMES` (chỉ cờ/đếm/khoảng cách, không có giá trị)."""
    both_no = bool(a.head_no and b.head_no)
    differ_no = float(both_no and a.head_no != b.head_no)
    dist_no = 0.0
    if both_no:
        dist_no = edit_distance(a.head_no, b.head_no) / max(len(a.head_no), len(b.head_no))
    both_dt = bool(a.head_dates and b.head_dates)
    differ_dt = float(both_dt and not (a.head_dates & b.head_dates))
    # số dài chỉ có ở MỘT trong hai trang (không có số "gần giống" khoảng cách sửa <= 1 ở trang kia)
    def only(x: FrozenSet[str], y: FrozenSet[str]) -> int:
        n = 0
        for v in x - y:
            if len(v) >= 5 and any(abs(len(v) - len(w)) <= 1 and edit_distance(v, w) <= 1 for w in y):
                continue
            n += 1
        return n

    shared = len(a.numbers & b.numbers)
    oa, ob = only(a.numbers, b.numbers), only(b.numbers, a.numbers)
    tot = oa + ob
    frac = tot / (tot + shared) if (tot + shared) else 0.0
    return [float(both_no), differ_no, dist_no, float(both_dt), differ_dt, frac, float(shared), float(tot)]
