"""local_vlm_json.py - Mô hình thị giác cục bộ (Ollama, qwen3.5:4b có năng lực `vision`) đọc ẢNH trang, trả JSON theo schema (T4, tùy chọn).

Vì sao: chữ viết tay và chữ dưới con dấu làm OCR hỏng gần hoàn toàn (xem README nhóm 1); đọc thẳng ảnh có thể tránh bước OCR.
Ảnh lấy từ `gold/pages/<unit_id>/` (đã render ở bước chuẩn bị silver: 200 dpi, trang dọc cắt đôi, cạnh dài <= 1600 px) — nên chỉ
chạy được cho các đơn vị đã có ảnh. `max_images` ảnh đầu tiên (mặc định 4) của các trang được chọn được gửi; đơn vị dài có thể bị cắt
bớt trang -> trường nằm ở trang không gửi sẽ là null (ghi vào `last_call['n_images_sent']`).

Cùng giao diện và cùng schema ràng buộc như `LocalLlmJson`; không dùng văn bản OCR. Phải chạy on-premise: Ollama cục bộ.
Bộ nhớ GPU dùng chung: nếu Ollama báo thiếu bộ nhớ, `extract` ném MethodUnavailable với thông điệp gốc (không trả rỗng giả).
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

from methods.common import BaseMethod, MethodUnavailable, Unit, empty_result, load_schema, set_value  # noqa: E402
from methods.local_llm_json import MODEL, SYSTEM, field_instructions, fields_for, json_schema  # noqa: E402
from methods.ollama_client import chat_json  # noqa: E402

PAGES_DIR = TEAM / "gold" / "pages"
SYSTEM_VLM = SYSTEM.replace("từ giấy tờ", "từ ẢNH các trang giấy tờ")
VLM_VARIANTS = {"v1": SYSTEM_VLM}


def unit_images(unit: Unit, max_images: int = 4, pages_dir: Path = None) -> List[Path]:
    d = Path(pages_dir or PAGES_DIR) / unit.unit_id
    if not d.exists():
        raise MethodUnavailable(f"chưa có ảnh trang của đơn vị (chạy gold/build_units.py): {d.name}")
    return sorted(d.glob("p*.png"))[:max_images]


class LocalVlmJson(BaseMethod):
    name = "local_vlm_json"
    needs_text = False

    def __init__(self, source: str = "image", store_personal_ids: bool = False, model: str = MODEL, max_images: int = 4,
                 variant: str = "v1", pages_dir: Path = None) -> None:
        super().__init__(source, store_personal_ids)
        self.pages_dir = pages_dir          # None = gold/pages (v1); giai đoạn 3 truyền gold/v2/pages_v2
        self.model = model
        self.variant = variant
        self.max_images = max_images
        self.last_call: Dict[str, Any] = {}

    def _extract(self, unit: Unit, pages: Dict[int, str]) -> Dict[str, Dict[str, Any]]:
        imgs = unit_images(unit, self.max_images, self.pages_dir)
        if not imgs:
            raise MethodUnavailable("không có ảnh trang nào cho đơn vị")
        fields = fields_for(unit, self.store_personal_ids)
        title = load_schema(unit.doc_type)["title"]
        user = (f"Loại tài liệu: {title}\n\nCác ảnh đính kèm là các trang của tài liệu theo thứ tự "
                f"(tên tệp pNN_a/pNN_b là nửa trên/nửa dưới của trang NN).\n\nCác trường cần trích:\n{field_instructions(fields)}")
        res = chat_json(self.model, VLM_VARIANTS[self.variant], user, json_schema(fields), images=imgs, options={"num_ctx": 12288})
        self.last_call = {"latency_ms": res["latency_ms"], "cached": res["cached"], "n_images_sent": len(imgs), **res["stats"]}
        out = empty_result(unit.doc_type)
        for spec in fields:
            set_value(out, spec, res["data"].get(spec["name"]))
        return out
