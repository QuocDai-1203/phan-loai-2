"""regex_rules.py - Luật/regex theo từng trường (Nhóm 4, T4 phương pháp 1).

Cài đặt chuẩn nằm ở `src/extraction/field_rules.py` (đã thăng cấp vào `src/`); tệp này chỉ bọc nó vào giao diện phương pháp
(`BaseMethod`: nguồn văn bản, lọc PII, trạng thái lỗi/bỏ qua). Luật được viết/chỉnh trên đơn vị DEV.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

TEAM = Path(__file__).resolve().parents[1]
REPO = TEAM.parents[1]
for _p in (str(TEAM), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from methods.common import BaseMethod, Unit, empty_result, field_specs, set_value  # noqa: E402
from src.extraction.field_rules import RULES, Doc, apply_rules  # noqa: E402,F401


class RegexRules(BaseMethod):
    """Luật theo trường. Chạy được trên mọi nguồn văn bản (`ocr_v2`, `ocr_llm_haiku`, `text_layer`)."""

    name = "regex_rules"

    def __init__(self, source: str = "ocr_v2", store_personal_ids: bool = False, generic: bool = False) -> None:
        super().__init__(source, store_personal_ids)
        self.generic = generic      # True: loại CHƯA có luật riêng dùng luật ngày chung (generic_date_rules, giai đoạn 3); mặc định giữ hành vi v1

    def _extract(self, unit: Unit, pages: Dict[int, str]) -> Dict[str, Dict[str, Any]]:
        out = empty_result(unit.doc_type)
        hits = apply_rules(unit.doc_type, pages)
        if self.generic and unit.doc_type not in RULES:
            from methods.generic_date_rules import generic_rules
            hits = generic_rules([s["name"] for s in field_specs(unit.doc_type)], Doc(pages))
        for spec in field_specs(unit.doc_type):
            v, pg = hits.get(spec["name"], (None, None))
            set_value(out, spec, v, page=pg)
        return out
