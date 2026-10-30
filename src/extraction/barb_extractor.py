"""barb_extractor.py - Module trích xuất thông tin thực thể (IE) cho Nhóm 4.

Kế thừa từ Z:\\projects\\vocvach\\barb-1-ie-vi:
- Sử dụng mô hình GLiNER: belumind/barb-1-ie-vi.
- Trích xuất: tổ chức, người, chức vụ, địa điểm, ngày, xăng dầu, số lượng, mã số thuế, số tài khoản...
- Xuất ra ExtractionResult tuân thủ contracts.py.

Trung thực về lỗi: nếu mô hình không nạp được hoặc dự đoán thất bại, kết quả có `status="error"` + `error`
(và có log) - tuyệt đối không trả về kết quả rỗng giả làm thành công.
Mô hình được nạp lười (lần dùng đầu tiên) để import module không tải mô hình / không gọi mạng.
"""

import logging
import time
from typing import List, Dict, Any, Optional
from src.common.contracts import DocumentSlice, ExtractedEntity, ExtractedTable, ExtractionResult
from src.extraction.barb_labels import check_labels

logger = logging.getLogger(__name__)

# Nhãn thực thể mặc định cho hợp đồng & chứng từ xăng dầu
DEFAULT_CONTRACT_LABELS = [
    "tổ chức", "người", "chức vụ", "địa điểm", "ngày",
    "mã số thuế", "số tài khoản", "xăng dầu", "số lượng", "tiền tệ"
]

_MODEL_CACHE: Dict[str, Any] = {}


def _load_gliner(model_name: str):
    """Nạp mô hình GLiNER (có thể tải từ Hugging Face lần đầu). Ném lỗi nếu thiếu thư viện/mô hình."""
    import torch
    from gliner import GLiNER
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return GLiNER.from_pretrained(model_name).to(device)


def load_model(model_name: str = "belumind/barb-1-ie-vi"):
    """Nạp (và cache) mô hình theo tên; lỗi được ném ra cho caller xử lý, không nuốt."""
    if model_name not in _MODEL_CACHE:
        _MODEL_CACHE[model_name] = _load_gliner(model_name)
    return _MODEL_CACHE[model_name]


class BarbEntityExtractor:
    """Bộ trích xuất thực thể chuyên biệt cho tài liệu doanh nghiệp Việt Nam."""

    def __init__(self, model_name: str = "belumind/barb-1-ie-vi", model: Optional[Any] = None):
        """`model`: truyền sẵn mô hình (có `predict_entities`) để tái dùng/kiểm thử; None -> nạp lười theo model_name."""
        self.model_name = model_name
        self.model = model
        self.load_error: Optional[str] = None

    def _ensure_model(self) -> bool:
        """Đảm bảo có mô hình; ghi `load_error` + log nếu không nạp được."""
        if self.model is not None:
            return True
        try:
            self.model = load_model(self.model_name)
            self.load_error = None
            return True
        except Exception as e:  # thiếu gliner/torch, không có mạng/cache, hết RAM...
            self.load_error = f"Không nạp được mô hình GLiNER '{self.model_name}': {type(e).__name__}: {e}"
            logger.error(self.load_error)
            return False

    def _failed(self, doc_slice: DocumentSlice, category_label: str, status: str, error: str, start_t: float) -> ExtractionResult:
        return ExtractionResult(
            slice_id=doc_slice.slice_id,
            document_type=category_label,
            processing_time_ms=(time.time() - start_t) * 1000,
            status=status,
            error=error,
        )

    def extract(self, doc_slice: DocumentSlice, category_label: str) -> ExtractionResult:
        """Trích xuất thực thể từ văn bản của lát cắt tài liệu."""
        start_t = time.time()
        text = doc_slice.combined_text.strip()

        if not text:
            return self._failed(doc_slice, category_label, "skipped", "Lát cắt không có văn bản để trích xuất", start_t)

        if not self._ensure_model():
            return self._failed(doc_slice, category_label, "error", self.load_error or "Không có mô hình", start_t)

        extracted_entities: List[ExtractedEntity] = []
        entity_dict: Dict[str, Any] = {}

        try:
            valid_labels = check_labels(DEFAULT_CONTRACT_LABELS, "entity")
            preds = self.model.predict_entities(text[:4000], labels=valid_labels, threshold=0.4)

            for item in preds:
                ent = ExtractedEntity(
                    label=item.get("label", ""),
                    text=item.get("text", ""),
                    start_char=item.get("start"),
                    end_char=item.get("end"),
                    confidence=float(item.get("score", 1.0)),
                )
                extracted_entities.append(ent)

                # Gom nhóm vào dictionary nghiệp vụ
                lbl = ent.label
                if lbl not in entity_dict:
                    entity_dict[lbl] = []
                if ent.text not in entity_dict[lbl]:
                    entity_dict[lbl].append(ent.text)
        except Exception as e:
            msg = f"Trích xuất thực thể thất bại: {type(e).__name__}: {e}"
            logger.exception("Trích xuất thực thể thất bại ở %s", doc_slice.slice_id)
            return self._failed(doc_slice, category_label, "error", msg, start_t)

        elapsed = (time.time() - start_t) * 1000

        return ExtractionResult(
            slice_id=doc_slice.slice_id,
            document_type=category_label,
            entities=extracted_entities,
            entity_dict=entity_dict,
            tables=[],
            processing_time_ms=elapsed,
        )
