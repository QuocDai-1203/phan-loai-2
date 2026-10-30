"""field_result.py - Đưa kết quả trích xuất theo TRƯỜNG (Nhóm 4) vào hợp đồng `ExtractionResult`, áp chính sách dữ liệu cá nhân (T5).

    fields = {"ngay_het_han": {"value": "ngày 12 tháng 01 năm 2028", "normalized": "2028-01-12", "page": 2},
              "nam_sinh": {...}, ...}
    res = to_extraction_result("slice_001", "CC_TAP_HUAN_VC_HNH", fields)        # store_personal_ids=False (mặc định)

Mặc định (`store_personal_ids=False`): các trường số định danh (CCCD/CMND, giấy phép lái xe) và ngày/năm sinh bị BỎ khỏi `entities`
và `entity_dict`; chỉ tên trường bị bỏ được ghi vào `dropped_pii_fields` (không có giá trị). Họ tên giữ lại (`store_personal_names=True`)
vì cần gắn nhắc hạn với người, nhưng không bao giờ được đưa vào log (dùng `safe_summary`). Danh sách trường PII nằm ở
`src/extraction/schema_data/pii_fields.json` (bản sao của `teams/team4_extraction/schema/pii_fields.json`, sinh từ taxonomy; test kiểm tra giống hệt) — thiếu tệp này là lỗi, không phải "không có PII".

`entity_dict[field]` là giá trị đã chuẩn hóa nếu có (`normalized`), ngược lại là giá trị nguyên văn; nguyên văn nằm ở `entities[i].text`.
Hợp đồng chưa có chỗ cho `page` của từng giá trị: xem đề xuất ở báo cáo nhóm 4 (thêm `page: Optional[int]` vào `ExtractedEntity`).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from src.common.contracts import ExtractedEntity, ExtractionResult

PII_FILE = Path(__file__).resolve().parent / "schema_data" / "pii_fields.json"   # bản sao của teams/team4_extraction/schema/ (test kiểm tra giống hệt)
DROPPED_BY_DEFAULT = ("personal_id", "birth_date")


@lru_cache(maxsize=1)
def _pii_categories() -> Dict[str, str]:
    data = json.loads(PII_FILE.read_text(encoding="utf-8"))      # thiếu tệp -> FileNotFoundError (không im lặng bỏ qua)
    return {f["name"]: f["category"] for f in data["fields"]}


def pii_category(field_name: str) -> Optional[str]:
    """'personal_id' | 'birth_date' | 'personal_name' | None."""
    return _pii_categories().get(field_name)


def to_extraction_result(slice_id: str, document_type: str, fields: Mapping[str, Any], store_personal_ids: bool = False,
                         store_personal_names: bool = True, processing_time_ms: float = 0.0,
                         status: str = "ok", error: Optional[str] = None) -> ExtractionResult:
    """Chuyển {trường: {value, normalized, page} | chuỗi | None} thành ExtractionResult. Trường null không sinh thực thể
    (nhưng vẫn có khóa `entity_dict[field] = None` để phân biệt 'máy không tìm thấy' với 'trường không thuộc schema')."""
    cats = _pii_categories()
    entities: List[ExtractedEntity] = []
    entity_dict: Dict[str, Any] = {}
    dropped: List[str] = []
    for name, rec in fields.items():
        cat = cats.get(name)
        if (cat in DROPPED_BY_DEFAULT and not store_personal_ids) or (cat == "personal_name" and not store_personal_names):
            dropped.append(name)
            continue
        value = rec.get("value") if isinstance(rec, Mapping) else rec
        norm = rec.get("normalized") if isinstance(rec, Mapping) else None
        if value is None or not str(value).strip():
            entity_dict[name] = None
            continue
        entities.append(ExtractedEntity(label=name, text=str(value), confidence=float(rec.get("confidence", 1.0)) if isinstance(rec, Mapping) else 1.0))
        entity_dict[name] = norm if norm else str(value)
    if dropped:
        entity_dict["dropped_pii_fields"] = sorted(dropped)
    return ExtractionResult(slice_id=slice_id, document_type=document_type, entities=entities, entity_dict=entity_dict,
                            processing_time_ms=processing_time_ms, status=status, error=error)


def safe_summary(result: ExtractionResult) -> str:
    """Chuỗi an toàn để log: tên trường và có/không có giá trị, KHÔNG có giá trị nào."""
    present = sorted(k for k, v in result.entity_dict.items() if k != "dropped_pii_fields" and not k.startswith("_") and v not in (None, ""))
    absent = sorted(k for k, v in result.entity_dict.items() if k != "dropped_pii_fields" and not k.startswith("_") and v in (None, ""))
    return (f"slice={result.slice_id} type={result.document_type} status={result.status} "
            f"present={present} null={absent} dropped_pii={result.entity_dict.get('dropped_pii_fields', [])}")
