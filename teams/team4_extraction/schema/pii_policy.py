"""pii_policy.py - Chính sách dữ liệu cá nhân (Nhóm 4, việc T5).

    filter_output(fields, store_personal_ids=False)   đầu ra MẶC ĐỊNH: bỏ khóa số định danh và ngày sinh
    redact_for_log(fields)                            bản an toàn để ghi log/báo cáo: mọi trường PII -> "[REDACTED]"
    safe_repr(fields)                                 chuỗi in được (đã che) — dùng thay cho print(fields)
    RedactingFilter                                   logging.Filter che các giá trị PII đã đăng ký khỏi mọi bản ghi log

Nguồn sự thật: `schema/pii_fields.json` (sinh từ taxonomy bởi build_schema.py).
Cờ cấu hình: `store_personal_ids` (mặc định False: số định danh + ngày sinh bị bỏ khỏi đầu ra),
`store_personal_names` (mặc định True: họ tên giữ lại để gắn nhắc hạn với người, nhưng vẫn không bao giờ vào log/báo cáo).
Câu hỏi 12 cho công ty chưa có trả lời: các mặc định này là TẠM THỜI.
"""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Set

PII_FILE = Path(__file__).resolve().parent / "pii_fields.json"
REDACTED = "[REDACTED]"
DROPPED_BY_DEFAULT = ("personal_id", "birth_date")


@lru_cache(maxsize=1)
def load_pii() -> Dict[str, Any]:
    return json.loads(PII_FILE.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _category_map() -> Dict[str, str]:
    return {f["name"]: f["category"] for f in load_pii()["fields"]}


def pii_category(field_name: str) -> Optional[str]:
    """'personal_id' | 'birth_date' | 'personal_name' | None."""
    return _category_map().get(field_name)


def is_pii(field_name: str) -> bool:
    return pii_category(field_name) is not None


def filter_output(fields: Mapping[str, Any], store_personal_ids: bool = False, store_personal_names: bool = True) -> Dict[str, Any]:
    """Đầu ra mặc định gửi đi (ERP, tệp kết quả): bỏ khóa personal_id + birth_date khi `store_personal_ids` là False."""
    out: Dict[str, Any] = {}
    for k, v in fields.items():
        cat = pii_category(k)
        if cat in DROPPED_BY_DEFAULT and not store_personal_ids:
            continue
        if cat == "personal_name" and not store_personal_names:
            continue
        out[k] = v
    return out


def redact_for_log(fields: Mapping[str, Any]) -> Dict[str, Any]:
    """Bản dùng cho log/báo cáo: giá trị của MỌI trường PII (kể cả họ tên) thành [REDACTED] (giữ khóa để biết trường có mặt)."""
    return {k: (REDACTED if is_pii(k) and v not in (None, "") else v) for k, v in fields.items()}


def safe_repr(fields: Mapping[str, Any]) -> str:
    return json.dumps(redact_for_log(fields), ensure_ascii=False, sort_keys=True)


class RedactingFilter(logging.Filter):
    """Che mọi giá trị PII đã `register()` khỏi thông điệp log (phòng khi lỡ f-string giá trị vào log).

    Chỉ là lưới an toàn thứ hai; cách đúng là không đưa giá trị vào log (dùng `safe_repr`)."""

    def __init__(self) -> None:
        super().__init__()
        self._secrets: Set[str] = set()

    def register(self, fields: Mapping[str, Any]) -> None:
        for k, v in fields.items():
            if is_pii(k) and isinstance(v, str) and len(v.strip()) >= 3:
                self._secrets.add(v.strip())

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        for s in sorted(self._secrets, key=len, reverse=True):
            msg = re.sub(re.escape(s), REDACTED, msg, flags=re.I)
        record.msg, record.args = msg, ()
        return True
