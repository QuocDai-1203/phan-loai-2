"""schemas.py - Schema trích xuất theo loại tài liệu cho `src/extraction` (bản sao có kiểm tra của `teams/team4_extraction/schema/`).

`schema_data/<DOC_TYPE>.json` do `teams/team4_extraction/schema/build_schema.py` sinh ra từ taxonomy; test `tests/test_extraction_fields.py`
kiểm tra hai bản giống hệt nhau (không để lệch). Loại chưa có schema -> `UnsupportedDocType` (lỗi rõ ràng, không im lặng trả rỗng).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

SCHEMA_DIR = Path(__file__).resolve().parent / "schema_data"
# 4 loại giai đoạn 2 (có luật riêng + quy tắc hạn `any-model=filename`) rồi 17 loại giai đoạn 3 (luật ngày chung + quy tắc hạn `regex=llm`)
PHASE2_TYPES = ("GCN_DDK_BAN_LE_XD", "CC_TAP_HUAN_VC_HNH", "HD_MUA_BAN", "PHIEU_XUAT_KHO")
PHASE3_TYPES = ("BIEN_NHAN_THE_CHAP_PT", "CCCD", "CC_HUAN_LUYEN_PCCC", "CC_NGHIEP_VU_BVMT", "DANG_KY_PHUONG_TIEN", "GCN_ATKT_BVMT_PT",
                "GCN_BAO_HIEM", "GCN_KIEM_DINH_DO_LUONG", "GIAY_UY_QUYEN", "GPLX", "GP_KD_VAN_TAI", "GP_VC_HANG_NGUY_HIEM",
                "GXN_THUONG_NHAN_XD", "HD_MUON_BON", "HD_NHUONG_QUYEN_DAI_LY", "HD_THUE_TAI_SAN", "HD_VAN_CHUYEN")
SUPPORTED_TYPES = PHASE2_TYPES + PHASE3_TYPES


class UnsupportedDocType(ValueError):
    """Loại tài liệu chưa có schema trích xuất."""


@lru_cache(maxsize=None)
def load_schema(doc_type: str) -> Dict[str, Any]:
    p = SCHEMA_DIR / f"{doc_type}.json"
    if doc_type not in SUPPORTED_TYPES or not p.exists():
        raise UnsupportedDocType(f"chưa có schema trích xuất cho loại '{doc_type}' (có: {', '.join(SUPPORTED_TYPES)})")
    return json.loads(p.read_text(encoding="utf-8"))


def field_specs(doc_type: str) -> List[Dict[str, Any]]:
    """Các trường cần trích (bỏ trường dẫn xuất `annotate=False`)."""
    return [f for f in load_schema(doc_type)["x-fields"] if f.get("annotate", True) is not False]
