"""local_llm_json.py - LLM cục bộ (Ollama, qwen3.5:4b) trích trường với đầu ra ràng buộc JSON Schema (Nhóm 4, T4 phương pháp 3).

Quy trình: văn bản OCR của đơn vị (hoặc các đoạn liên quan nếu dài, xem `common.passages_text`) + danh sách trường của schema T1
-> một lời gọi /api/chat với `format` = JSON Schema sinh từ `schema/<DOC_TYPE>.json` -> {trường: chuỗi | null}.
Chạy on-premise hoàn toàn. Có cache đĩa (`ollama_client.CACHE`), nên chạy lại miễn phí và tất định (temperature 0).

Dữ liệu cá nhân: khi `store_personal_ids=False` (mặc định) schema gửi cho mô hình KHÔNG có số định danh/ngày sinh (không hỏi thì
không trích — tối thiểu hóa dữ liệu), và `BaseMethod.extract` còn lọc thêm một lần nữa.

Giới hạn: không có trang cho từng giá trị (page=None); mô hình nhỏ có thể "điền cho đủ" — vì vậy prompt yêu cầu null khi không thấy,
và đầu ra được chấm bằng bộ chấm có đếm riêng "sai giá trị" ở trường hạn.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

TEAM = Path(__file__).resolve().parents[1]
REPO = TEAM.parents[1]
for _p in (str(TEAM), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from methods.common import BaseMethod, Unit, empty_result, field_specs, load_schema, passages_text, set_value  # noqa: E402
from methods.ollama_client import chat_json  # noqa: E402
from schema.pii_policy import DROPPED_BY_DEFAULT, pii_category  # noqa: E402

MODEL = "qwen3.5:4b"

SYSTEM = (
    "Bạn là bộ trích xuất trường dữ liệu từ giấy tờ doanh nghiệp tiếng Việt. Chỉ dùng thông tin CÓ TRONG tài liệu được cung cấp. "
    "Với mỗi trường: chép NGUYÊN VĂN giá trị như in (ví dụ ngày giữ dạng 'ngày 12 tháng 01 năm 2028' hoặc '12/01/2028'). "
    "Nếu tài liệu không có hoặc bạn không đọc chắc được trường đó, trả null. Tuyệt đối không bịa, không suy ngày từ chỗ khác, "
    "không tự cộng/trừ ngày, không điền giá trị 'cho hợp lý'. Trả đúng một đối tượng JSON theo schema, không giải thích."
)


PROMPT_VARIANTS = {"v1": SYSTEM}   # biến thể prompt; chọn biến thể thắng trên DEV rồi đóng băng (dev_selection.json)


def fields_for(unit: Unit, store_personal_ids: bool) -> List[Dict[str, Any]]:
    """Các trường sẽ hỏi mô hình: bỏ trường dẫn xuất và (mặc định) số định danh/ngày sinh."""
    out = []
    for f in field_specs(unit.doc_type):
        if not store_personal_ids and pii_category(f["name"]) in DROPPED_BY_DEFAULT:
            continue
        out.append(f)
    return out


def json_schema(fields: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"type": "object", "properties": {f["name"]: {"type": ["string", "null"]} for f in fields},
            "required": [f["name"] for f in fields], "additionalProperties": False}


def field_instructions(fields: List[Dict[str, Any]]) -> str:
    lines = []
    for f in fields:
        hint = f" {f['annotator_hint']}" if f.get("annotator_hint") else ""
        lines.append(f"- {f['name']}: {f['desc']}.{hint}")
    return "\n".join(lines)


class LocalLlmJson(BaseMethod):
    """Ollama + JSON Schema, đầu vào là văn bản OCR (mọi nguồn: ocr_v2, ocr_llm_haiku, text_layer)."""

    name = "local_llm_json"

    def __init__(self, source: str = "ocr_v2", store_personal_ids: bool = False, model: str = MODEL, max_chars: int = 6000,
                 variant: str = "v1") -> None:
        super().__init__(source, store_personal_ids)
        self.model = model
        self.variant = variant
        self.max_chars = max_chars
        self.last_call: Dict[str, Any] = {}

    def _extract(self, unit: Unit, pages: Dict[int, str]) -> Dict[str, Dict[str, Any]]:
        fields = fields_for(unit, self.store_personal_ids)
        title = load_schema(unit.doc_type)["title"]
        user = (f"Loại tài liệu: {title}\n\nCác trường cần trích:\n{field_instructions(fields)}\n\n"
                f"Văn bản OCR (có thể sai chính tả/dấu; mỗi đoạn có đầu '[trang N]'):\n<<<\n{passages_text(pages, self.max_chars)}\n>>>")
        res = chat_json(self.model, PROMPT_VARIANTS[self.variant], user, json_schema(fields))
        self.last_call = {"latency_ms": res["latency_ms"], "cached": res["cached"], **res["stats"]}
        out = empty_result(unit.doc_type)
        specs = {f["name"]: f for f in fields}
        for name, spec in specs.items():
            set_value(out, spec, res["data"].get(name))
        return out
