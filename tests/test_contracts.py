"""Kiểm thử hợp đồng dữ liệu (contracts.py): giá trị mặc định tương thích ngược và round-trip JSON."""

from src.common.contracts import (
    UNKNOWN_CATEGORY,
    ClassificationResult,
    DocumentSlice,
    ExtractionResult,
    OCRDocumentResult,
    OCRPageResult,
)
from tests.fixtures.sample_pipeline_fixtures import (
    MOCK_CLASSIFICATION_PXK,
    MOCK_OCR_DOCUMENT_BSR,
    MOCK_SPLIT_RESULT_BSR,
)


def test_legacy_page_construction_still_works_with_new_defaults():
    page = OCRPageResult(page_number=1, width=10, height=10, full_text="abc")
    assert page.error is None
    assert page.source == "ocr"


def test_ocr_document_round_trip_keeps_new_fields():
    page = OCRPageResult(page_number=1, width=1, height=1, full_text="", source="text_layer",
                         ocr_engine="digital", error="boom")
    doc = OCRDocumentResult(file_name="a.pdf", total_pages=1, pages=[page], error="Trang 1: boom")
    restored = OCRDocumentResult.model_validate_json(doc.model_dump_json())
    assert restored == doc
    assert restored.pages[0].source == "text_layer" and restored.error == "Trang 1: boom"


def test_fixture_documents_round_trip():
    for obj in (MOCK_OCR_DOCUMENT_BSR, MOCK_SPLIT_RESULT_BSR, MOCK_CLASSIFICATION_PXK):
        assert type(obj).model_validate_json(obj.model_dump_json()) == obj


def test_classification_result_defaults_are_not_a_confident_claim():
    res = ClassificationResult(slice_id="s", predicted_category=UNKNOWN_CATEGORY)
    assert res.confidence == 0.0
    assert res.tier == "none" and res.model_name == "none"
    assert res.error is None and res.fallback_used is False


def test_extraction_result_defaults_to_ok_and_round_trips():
    res = ExtractionResult(slice_id="s", document_type="x", status="error", error="không nạp được mô hình")
    assert ExtractionResult.model_validate(res.model_dump()) == res
    assert ExtractionResult(slice_id="s", document_type="x").status == "ok"


def test_slice_boundary_defaults():
    s = DocumentSlice(slice_id="s", start_page=1, end_page=1, page_count=1, combined_text="x")
    assert s.boundary_method == "rule" and s.ocr_errors == []


# ---------- Thay đổi hợp đồng #1 (2026-10-12): chỉ THÊM, tương thích ngược ----------
def test_contract_change_1_old_payloads_without_new_fields_still_validate():
    from src.common.contracts import DocumentProcessingPipelineResult
    old_page = {"page_number": 1, "width": 1, "height": 1, "full_text": "x", "ocr_engine": "rapid_ocr", "source": "ocr"}
    page = OCRPageResult.model_validate(old_page)
    assert page.mean_conf is None and page.flags == []
    old_cls = {"slice_id": "s", "predicted_category": "UNKNOWN", "tier": "none"}
    cls = ClassificationResult.model_validate(old_cls)
    assert cls.suggested_category is None and cls.suggested_confidence is None and cls.suggestion_source is None
    old_pipeline = {"file_name": "a.pdf", "total_pages": 1, "is_composite_bundle": False,
                    "ocr_result": {"file_name": "a.pdf", "total_pages": 1},
                    "split_result": {"source_file": "a.pdf", "total_pages": 1}}
    res = DocumentProcessingPipelineResult.model_validate(old_pipeline)
    assert res.routing == [] and res.stage_timings_ms == {} and res.warnings == []


def test_contract_change_1_every_pre_existing_field_and_default_is_unchanged():
    f = ClassificationResult.model_fields
    for name, default in dict(confidence=0.0, model_name="none", requires_human_review=False, processing_time_ms=0.0, tier="none",
                              confidence_kind="none", abstain_reason=None, evidence=None, error=None, fallback_used=False).items():
        assert f[name].default == default, name
    p = OCRPageResult.model_fields
    for name, default in dict(full_text="", has_header_seal=False, has_signature_box=False, ocr_engine="apple_vision", source="ocr", error=None).items():
        assert p[name].default == default, name


def test_classification_tiers_cover_new_cascade_tiers_and_human_result_round_trips():
    from src.common.contracts import CLASSIFICATION_TIERS
    for t in ("rule", "kev", "none", "tfidf", "llm", "human"):
        assert t in CLASSIFICATION_TIERS
    res = ClassificationResult(slice_id="s", predicted_category=UNKNOWN_CATEGORY, tier="human", requires_human_review=True,
                               abstain_reason="llm_low_confidence", suggested_category="HD_MUA_BAN", suggested_confidence=0.2,
                               suggestion_source="llm")
    assert ClassificationResult.model_validate_json(res.model_dump_json()) == res
    assert res.confidence == 0.0 and res.predicted_category == UNKNOWN_CATEGORY      # từ chối vẫn là UNKNOWN, gợi ý nằm ở trường riêng


def test_slice_routing_round_trip():
    from src.common.contracts import SliceRouting
    r = SliceRouting(slice_id="s", decision="needs_human", reasons=["ocr_error"], suggested_category="X")
    assert SliceRouting.model_validate_json(r.model_dump_json()) == r and r.category == UNKNOWN_CATEGORY
