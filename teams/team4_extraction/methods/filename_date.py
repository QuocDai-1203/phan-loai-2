"""filename_date.py - Baseline rẻ cho trường hạn: lấy ngày trong TÊN TỆP (Nhóm 4, T4).

Nhân viên thường gõ ngày hết hạn vào tên tệp (vd. "...-12.1.28.pdf"). Quy ước CHƯA được công ty xác nhận (câu 16 README nhóm 4),
nên đây chỉ là (a) baseline yếu để so sánh và (b) kiểm chéo cho đáp án silver. Không bao giờ dùng làm đáp án.

    filename_date("DDK-ABC-12.1.28.pdf") -> "2028-01-12"
Chỉ trả ngày ĐẦY ĐỦ (d/m/y); lấy ngày CUỐI CÙNG trong tên (tiền tố "BC-", số thứ tự "15." không bị nhận nhầm).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

TEAM = Path(__file__).resolve().parents[1]
if str(TEAM) not in sys.path:
    sys.path.insert(0, str(TEAM))

from eval.normalize import find_dates  # noqa: E402
from methods.common import BaseMethod, Unit, empty_result, field_specs, set_value  # noqa: E402

_EXT = re.compile(r"\.(pdf|docx?|jpe?g|png|tiff?)$", re.I)


def filename_date(file_name: Optional[str]) -> Optional[str]:
    """Ngày đầy đủ cuối cùng trong tên tệp (ISO) hoặc None."""
    if not file_name:
        return None
    stem = _EXT.sub("", file_name.replace("\\", "/").rsplit("/", 1)[-1])
    full = [iso for iso, _ in find_dates(stem) if len(iso) == 10]
    return full[-1] if full else None


class FilenameDate(BaseMethod):
    """Phương pháp: chỉ điền trường hạn (`is_expiry`) bằng ngày trong tên tệp; mọi trường khác để null. Không dùng văn bản."""

    name = "filename_date"
    needs_text = False

    def __init__(self, source: str = "filename", store_personal_ids: bool = False) -> None:
        super().__init__(source, store_personal_ids)

    def _extract(self, unit: Unit, pages: Dict[int, str]) -> Dict[str, Dict[str, Any]]:
        out = empty_result(unit.doc_type)
        d = None if unit.composite else filename_date(unit.file_name)
        for spec in field_specs(unit.doc_type):
            if spec.get("is_expiry") and d:
                set_value(out, spec, d, page=None)
        return out
