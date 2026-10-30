"""field_extractor.py - Trích xuất TRƯỜNG nghiệp vụ cho 4 loại tài liệu (Nhóm 4). Chạy cục bộ hoàn toàn (on-premise).

    from src.extraction.field_extractor import extract_fields, FieldExtractor
    res = extract_fields(doc_slice, "GCN_DDK_BAN_LE_XD")                 # -> ExtractionResult
    res = FieldExtractor().extract(doc_slice, "GCN_DDK_BAN_LE_XD")       # cùng chữ ký với BarbEntityExtractor.extract(slice, label)

Quy trình (phương pháp được chọn trên DEV, xem teams/team4_extraction/experiments/02_methods/RESULTS.md):
  1. luật/regex trên văn bản OCR (`field_rules.apply_rules`)         -- nhanh, chính xác khi OCR sạch
  2. LLM cục bộ (Ollama `qwen3.5:4b`, đầu ra ràng buộc JSON Schema); ghép theo KIỂU trường: văn bản ưu tiên LLM, ngày/số/mã ưu tiên luật,
     trường nào nguồn ưu tiên để trống thì lấy nguồn còn lại
  3. trường HẠN: MẶC ĐỊNH (`auto_accept_expiry=False`) máy không tự nhận ngày nào: mọi hạn có ngày là `needs_review`, ngày gợi ý nằm ở `_expiry_suggestion`,
     quy tắc đã chạy ở `_expiry_rule` và kết quả "sẽ nhận hay không" ở `_expiry_would_accept` (số liệu chạy bóng). Với `auto_accept_expiry=True` máy chỉ TỰ NHẬN
     một ngày khi các nguồn độc lập đồng thuận (`expiry_rules`), ngược lại null + `needs_review` — một ngày hết hạn sai tệ hơn bỏ trống.
  4. ngày/số không phân tích được -> null; chính sách PII (T5): mặc định bỏ số định danh và ngày sinh khỏi kết quả.

Kết quả:
  * `entity_dict[trường]` = ngày ISO / số thập phân / mã chuẩn hóa, hoặc văn bản nguyên chữ như in; None nếu không có; `entities[i].text` = nguyên văn.
  * khóa dành riêng bắt đầu bằng '_': `_sources` {trường: 'regex'|'llm'|...}, `_expiry_would_accept` {trường hạn: bool}, `_expiry` {trường hạn: 'accepted' (chỉ khi auto_accept_expiry=True)|'needs_review'|'not_found'|'no_expiry' (giấy ghi không thời hạn)}, `_expiry_rule` tên quy tắc tự nhận
    đã dùng (theo loại: `any-model=filename` cho 4 loại giai đoạn 2, `regex=llm` cho 17 loại giai đoạn 3),
    `_expiry_suggestion` {trường hạn: ngày ISO gợi ý cho người duyệt khi `needs_review` (không phải giá trị đã nhận; entity_dict[trường] vẫn là None)}.
  * `status`: 'ok' | 'skipped' (không có văn bản) | 'error' (loại chưa hỗ trợ, hoặc MỘT GIAI ĐOẠN thất bại). Khi LLM thất bại mà luật vẫn chạy,
    `status = 'error'`, `error` nêu giai đoạn hỏng, và các trường do luật tìm được VẪN nằm trong kết quả (một phần) — người gọi tự quyết dùng hay không;
    kết quả rỗng không bao giờ được trả với status 'ok' nếu có giai đoạn lỗi.
Không có lời gọi mạng ngoài; mặc định Ollama ở 127.0.0.1. Kiểm thử dùng `llm_client` giả (không cần GPU/mạng).
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from src.common.contracts import DocumentSlice, ExtractionResult
from src.extraction import field_llm, field_vlm
from src.extraction.expiry_rules import EXPIRY_RULES, full_date
from src.extraction.field_result import to_extraction_result
from src.extraction.field_rules import RULES
from src.extraction.generic_date_rules import apply_rules_with_fallback
from src.extraction.normalize import find_dates, fold_keep_len, normalize_value
from src.extraction.schemas import UnsupportedDocType, field_specs

logger = logging.getLogger(__name__)

DEFAULT_EXPIRY_RULE = "any-model=filename"           # 4 loại giai đoạn 2 (có luật riêng); được cập nhật theo dev_selection.json (test kiểm tra khớp)
GENERIC_EXPIRY_RULE = "regex=llm"                    # 17 loại giai đoạn 3 (chỉ có luật ngày chung); chọn trên DEV v2, xem experiments/03_unseen_types/dev_selection3.json
NO_EXPIRY_RX = re.compile(r"(?:khong|vo)\s+thoi\s+han")      # "không thời hạn" / "vô thời hạn" trên văn bản bỏ dấu (GPLX hạng A1, CCCD >= 60 tuổi...)


def expiry_rule_for(doc_type: str, configured: Optional[str] = None) -> str:
    """Quy tắc tự nhận hạn: `configured` nếu người gọi đặt tường minh; mặc định theo loại: loại có luật riêng (giai đoạn 2) giữ
    `any-model=filename` (đã chứng minh trên đó), loại chỉ có luật chung (giai đoạn 3) dùng `regex=llm` (luật ngày chung + LLM đồng thuận,
    không cần tên tệp vì ngày trong tên tệp của loại mới không luôn là ngày hết hạn)."""
    return configured or (DEFAULT_EXPIRY_RULE if doc_type in RULES else GENERIC_EXPIRY_RULE)


@dataclass(frozen=True)
class ExtractConfig:
    use_llm: bool = True
    llm_model: str = field_llm.MODEL
    ollama_url: str = field_llm.OLLAMA_URL
    cache_dir: Optional[Path] = None
    max_chars: int = 6000
    store_personal_ids: bool = False         # T5: mặc định bỏ số định danh + ngày sinh
    store_personal_names: bool = True
    expiry_rule: Optional[str] = None       # None = theo loại (`expiry_rule_for`); đặt tên quy tắc để ép mọi loại dùng một quy tắc
    timeout_s: float = 600.0
    auto_accept_expiry: bool = False        # False (mặc định, chạy bóng): MỌI hạn là `needs_review`; quy tắc vẫn chạy, ghi `_expiry_suggestion`, `_expiry_rule` và `_expiry_would_accept`. True: tự nhận theo quy tắc
    max_vlm_images: int = 4                 # như lúc chấm: 4 ảnh đầu (2 trang đầu, mỗi trang cắt đôi)


def _pages_of(doc_slice: DocumentSlice) -> Dict[int, str]:
    """{trang: văn bản}. Dùng `pages` (bỏ trang lỗi/rỗng); không có thì coi cả `combined_text` là trang `start_page`."""
    pages: Dict[int, str] = {}
    for p in doc_slice.pages:
        if not p.error and (p.full_text or "").strip():
            pages[p.page_number] = p.full_text
    if not pages and (doc_slice.combined_text or "").strip():
        pages[doc_slice.start_page] = doc_slice.combined_text
    return pages


def _finalize(spec: Dict[str, Any], raw: Optional[str], page: Optional[int], source: str) -> Dict[str, Any]:
    """Chuẩn hóa một giá trị; ngày/số không phân tích được -> null (không đưa giá trị rác vào ERP/lịch nhắc)."""
    if raw is None or not str(raw).strip():
        return {"value": None, "normalized": None, "page": None, "source": None}
    v = str(raw).strip()
    norm = normalize_value(v, spec["type"], spec.get("id_kind"))
    if spec["type"] in ("date", "number") and norm is not None and norm.startswith("~raw:"):
        return {"value": None, "normalized": None, "page": None, "source": None, "rejected": "unparseable"}
    return {"value": v, "normalized": norm, "page": page, "source": source}


def extract_field_dict(pages: Dict[int, str], doc_type: str, config: Optional[ExtractConfig] = None, llm_client: Optional[field_llm.LlmClient] = None,
                       filename: Optional[str] = None, page_images: Optional[Sequence[Path]] = None,
                       vlm_client: Optional[field_vlm.VlmClient] = None) -> Dict[str, Any]:
    """Lõi: {trang: văn bản} -> {"fields": {trường: {...}}, "expiry": {trường hạn: trạng thái}, "errors": [giai đoạn lỗi]}. Ném UnsupportedDocType."""
    cfg = config or ExtractConfig()
    specs = {f["name"]: f for f in field_specs(doc_type)}           # UnsupportedDocType nếu chưa có schema
    errors: List[str] = []
    hits = apply_rules_with_fallback(doc_type, pages)
    regex = {n: _finalize(s, hits.get(n, (None, None))[0], hits.get(n, (None, None))[1], "regex") for n, s in specs.items()}

    llm: Dict[str, Dict[str, Any]] = {}
    expiry_names = [n for n, s in specs.items() if s.get("is_expiry")]
    need_llm = cfg.use_llm and (any(not regex[n]["value"] for n in specs) or bool(expiry_names))
    if need_llm:
        try:
            client = llm_client or field_llm.ollama_client(cfg.llm_model, cfg.ollama_url, cfg.timeout_s, cfg.cache_dir)
            flds = field_llm.fields_for(doc_type, cfg.store_personal_ids)
            data = client(field_llm.SYSTEM, field_llm.build_user_prompt(doc_type, flds, pages, cfg.max_chars), field_llm.json_schema(flds))
            for f in flds:
                llm[f["name"]] = _finalize(specs[f["name"]], data.get(f["name"]), None, "llm")
        except field_llm.LlmError as e:
            errors.append(f"giai đoạn LLM thất bại: {e}")
        except Exception as e:  # noqa: BLE001 - mọi lỗi phải hiện ra, không nuốt
            errors.append(f"giai đoạn LLM thất bại: {type(e).__name__}: {e}")

    vlm: Dict[str, Dict[str, Any]] = {}
    if page_images and expiry_names and (cfg.use_llm or vlm_client is not None):
        try:
            vc = vlm_client or field_vlm.ollama_vlm_client(cfg.llm_model, cfg.ollama_url, cfg.timeout_s, cfg.cache_dir)
            flds = field_llm.fields_for(doc_type, cfg.store_personal_ids)
            data = vc(field_vlm.SYSTEM_VLM, field_vlm.build_vlm_prompt(doc_type, flds), field_llm.json_schema(flds), list(page_images)[: cfg.max_vlm_images])
            for n in expiry_names:                       # chỉ dùng kết quả của mô hình thị giác để đối chiếu TRƯỜNG HẠN
                vlm[n] = _finalize(specs[n], data.get(n), None, "vlm")
        except field_llm.LlmError as e:
            errors.append(f"giai đoạn VLM thất bại: {e}")
        except Exception as e:  # noqa: BLE001
            errors.append(f"giai đoạn VLM thất bại: {type(e).__name__}: {e}")

    out: Dict[str, Dict[str, Any]] = {}
    for n, s in specs.items():
        # ghép theo KIỂU (chọn trên DEV): văn bản -> LLM trước, luật sau; ngày/số/mã -> luật trước, LLM sau
        first, second = ((llm.get(n), regex[n]) if s["type"] == "text" else (regex[n], llm.get(n)))
        out[n] = first if (first and first["value"]) else (second if (second and second["value"]) else regex[n])

    expiry: Dict[str, str] = {}
    suggestion: Dict[str, str] = {}
    would_accept: Dict[str, bool] = {}
    fn_date = None
    if filename:
        ds = [iso for iso, _ in find_dates(re.sub(r"\.(pdf|docx?|png|jpe?g|tiff?)$", "", filename, flags=re.I)) if len(iso) == 10]
        fn_date = ds[-1] if ds else None
    rule_name = expiry_rule_for(doc_type, cfg.expiry_rule)
    rule = EXPIRY_RULES[rule_name]
    no_expiry_text = any(NO_EXPIRY_RX.search(fold_keep_len(t)) for t in pages.values())
    for n in expiry_names:
        cands = {"regex": full_date(regex[n]["normalized"]), "llm": full_date((llm.get(n) or {}).get("normalized")),
                 "vlm": full_date((vlm.get(n) or {}).get("normalized")), "filename": fn_date}
        accepted = rule(cands)
        would_accept[n] = bool(accepted)
        if accepted and cfg.auto_accept_expiry:
            src = out[n]["source"] or "regex"
            out[n] = {"value": out[n]["value"] if out[n]["normalized"] == accepted else accepted, "normalized": accepted,
                      "page": out[n].get("page"), "source": src}
            expiry[n] = "accepted"
        else:
            had = bool(accepted or regex[n]["value"] or (llm.get(n) or {}).get("value") or (vlm.get(n) or {}).get("value"))
            out[n] = {"value": None, "normalized": None, "page": None, "source": None}
            # giấy ghi "không thời hạn" và không nguồn nào nêu ngày -> `no_expiry` (KHÔNG tự nhận một ngày bất kỳ; khác `not_found`)
            expiry[n] = "needs_review" if had else ("no_expiry" if no_expiry_text else "not_found")
            sug = accepted or next((c for c in (cands["regex"], cands["llm"], cands["vlm"]) if c), None)
            if sug:
                suggestion[n] = sug              # gợi ý cho người duyệt (KHÔNG tự nhận): ngày đầu tiên tìm được theo thứ tự luật, LLM, VLM
    return {"fields": out, "expiry": expiry, "expiry_suggestion": suggestion, "expiry_rule": rule_name, "expiry_would_accept": would_accept, "errors": errors}


def extract_fields(doc_slice: DocumentSlice, doc_type: str, *, config: Optional[ExtractConfig] = None,
                   llm_client: Optional[field_llm.LlmClient] = None, filename: Optional[str] = None,
                   page_images: Optional[Sequence[Path]] = None, vlm_client: Optional[field_vlm.VlmClient] = None) -> ExtractionResult:
    """Trích trường của một lát cắt đã biết loại. Không ném ngoại lệ: mọi lỗi nằm trong `status`/`error` (xem docstring module)."""
    t0 = time.perf_counter()
    cfg = config or ExtractConfig()

    def done(res: ExtractionResult) -> ExtractionResult:
        res.processing_time_ms = (time.perf_counter() - t0) * 1000
        return res

    pages = _pages_of(doc_slice)
    if not pages:
        return done(ExtractionResult(slice_id=doc_slice.slice_id, document_type=doc_type, status="skipped", error="Lát cắt không có văn bản để trích xuất"))
    try:
        core = extract_field_dict(pages, doc_type, cfg, llm_client, filename, page_images, vlm_client)
    except UnsupportedDocType as e:
        return done(ExtractionResult(slice_id=doc_slice.slice_id, document_type=doc_type, status="error", error=str(e)))
    except Exception as e:  # noqa: BLE001
        logger.exception("trích xuất trường thất bại ở %s", doc_slice.slice_id)
        return done(ExtractionResult(slice_id=doc_slice.slice_id, document_type=doc_type, status="error", error=f"{type(e).__name__}: {e}"))

    types = {f["name"]: f["type"] for f in field_specs(doc_type)}
    # entity_dict: ngày/số/mã ở dạng chuẩn hóa; văn bản giữ NGUYÊN chữ hoa/dấu như in (chuẩn hóa văn bản chỉ để so sánh khi chấm)
    shown = {n: ({**f, "normalized": None} if types.get(n) == "text" else f) for n, f in core["fields"].items()}
    res = to_extraction_result(doc_slice.slice_id, doc_type, shown, store_personal_ids=cfg.store_personal_ids,
                               store_personal_names=cfg.store_personal_names)
    res.entity_dict["_sources"] = {n: f["source"] for n, f in core["fields"].items() if f["value"] and n in res.entity_dict}
    res.entity_dict["_expiry"] = core["expiry"]
    res.entity_dict["_expiry_suggestion"] = core["expiry_suggestion"]
    res.entity_dict["_expiry_rule"] = core["expiry_rule"]          # quy tắc tự nhận hạn đã dùng cho loại này
    res.entity_dict["_expiry_would_accept"] = core["expiry_would_accept"]   # {trường hạn: quy tắc SẼ tự nhận không?}; khi auto_accept_expiry=False đây là dữ liệu chạy bóng
    if core["errors"]:
        res.status, res.error = "error", "; ".join(core["errors"]) + " (kết quả một phần: chỉ các trường do luật tìm được)"
        logger.error("%s: %s", doc_slice.slice_id, res.error)
    return done(res)


class FieldExtractor:
    """Bọc `extract_fields` với cùng chữ ký `extract(doc_slice, category_label) -> ExtractionResult` như `BarbEntityExtractor`,
    để `src/pipeline.py` đổi bộ trích xuất mà không đổi chỗ gọi. `category_label` là mã loại tài liệu (id taxonomy)."""

    def __init__(self, config: Optional[ExtractConfig] = None, llm_client: Optional[field_llm.LlmClient] = None,
                 vlm_client: Optional[field_vlm.VlmClient] = None) -> None:
        self.config = config or ExtractConfig()
        self.llm_client = llm_client
        self.vlm_client = vlm_client

    def extract(self, doc_slice: DocumentSlice, category_label: str, filename: Optional[str] = None,
                page_images: Optional[Sequence[Path]] = None) -> ExtractionResult:
        return extract_fields(doc_slice, category_label, config=self.config, llm_client=self.llm_client, filename=filename,
                              page_images=page_images, vlm_client=self.vlm_client)
