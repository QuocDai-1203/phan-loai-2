"""Kiểm thử bộ tách trang: khớp tiêu đề không phân biệt dấu, boundary_confidence là cờ luật,
luật v2 (không tách trang chữ ký / trang trống / "2/2"), và phương pháp "model" (nối đúng hợp đồng SplitResult)."""

import pytest

from src.common.contracts import OCRDocumentResult, OCRPageResult
from src.splitting.boundary_detector import (
    DEFAULT_METHOD, RULE_BOUNDARY_FLAG, is_new_document_start, split_document,
)


def page(n, text, error=None):
    return OCRPageResult(page_number=n, width=1, height=1, full_text=text, error=error)


def doc_of(*texts, errors=None):
    errors = errors or {}
    pages = [page(i + 1, t, errors.get(i + 1)) for i, t in enumerate(texts)]
    return OCRDocumentResult(file_name="a.pdf", total_pages=len(pages), pages=pages)


def test_title_detection_is_diacritic_and_glued_insensitive():
    assert is_new_document_start(page(2, "Hợp đồng số 01"), False)
    assert is_new_document_start(page(2, "HOP DONG so 01"), False)
    assert is_new_document_start(page(2, "PHIEUXUATKHO so 01"), False)
    assert is_new_document_start(page(2, "CONG HOA XA HOI CHU NGHIA VIET NAM"), False)
    assert not is_new_document_start(page(2, "dieu 5: thanh toan bang chuyen khoan"), False)


def test_split_marks_confidence_as_rule_flag_and_propagates_ocr_errors():
    doc = OCRDocumentResult(
        file_name="a.pdf", total_pages=3,
        pages=[page(1, "HOP DONG KINH TE"), page(2, "", error="OCR hỏng"), page(3, "BIEN BAN GIAO NHAN")],
    )
    result = split_document(doc)
    assert [s.page_count for s in result.slices] == [2, 1]
    assert all(s.boundary_confidence == RULE_BOUNDARY_FLAG and s.boundary_method == "rule" for s in result.slices)
    assert result.slices[0].ocr_errors == ["OCR hỏng"] and result.slices[1].ocr_errors == []


def test_default_method_is_the_old_rule_and_unknown_method_is_rejected():
    assert DEFAULT_METHOD == "rule"
    with pytest.raises(ValueError):
        split_document(doc_of("x"), method="magic")


def test_old_rule_still_splits_on_repeated_title_signature_page():
    # hành vi cũ được giữ nguyên (và là hành vi SAI đã đo ở experiments/01_rule_baseline): trang chữ ký lặp tiêu đề bị tách
    from tests.fixtures.sample_pipeline_fixtures import MOCK_OCR_DOCUMENT_BSR as d
    assert [(s.start_page, s.end_page) for s in split_document(d).slices] == [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)]


def test_rule_v2_keeps_signature_page_with_repeated_title_together():
    from tests.fixtures.sample_pipeline_fixtures import MOCK_OCR_DOCUMENT_BSR as d
    r = split_document(d, method="rule_v2")
    assert [(s.start_page, s.end_page) for s in r.slices] == [(1, 2), (3, 3), (4, 4), (5, 5)]
    assert all(s.boundary_method == "rule_v2" and s.boundary_confidence == RULE_BOUNDARY_FLAG for s in r.slices)


LONG = " ".join(["noi dung dai cua trang tiep theo cua van ban"] * 8)


def test_rule_v2_motto_only_counts_at_top_of_page():
    far = "\n".join(["dong thuong"] * 12 + ["CONG HOA XA HOI CHU NGHIA VIET NAM"]) + LONG
    top = "CONG HOA XA HOI CHU NGHIA VIET NAM\nDoc lap - Tu do - Hanh phuc\n" + LONG
    r_far = split_document(doc_of("HOP DONG so 1\n" + LONG, far), method="rule_v2")
    r_top = split_document(doc_of("HOP DONG so 1\n" + LONG, top), method="rule_v2")
    assert len(r_far.slices) == 1 and len(r_top.slices) == 2


def test_rule_v2_blank_page_and_page_number_are_continuations():
    first = "HOP DONG so 1\n" + LONG
    blank = ""
    p2of2 = "HOP DONG so 1\nTrang 2/2\n" + LONG
    r = split_document(doc_of(first, blank, p2of2, "BIEN BAN GIAO NHAN\n" + LONG), method="rule_v2")
    assert [(s.start_page, s.end_page) for s in r.slices] == [(1, 3), (4, 4)]


def test_rule_v2_short_page_without_signature_words_can_still_start_a_document():
    short = "CHUNG THU CHAT LUONG\nCertificate of Quality\nKy hieu lo: DLO-1 NHIEN LIEU DIEZEN"
    r = split_document(doc_of("PHIEU XUAT KHO\n" + LONG, short), method="rule_v2")
    assert len(r.slices) == 2


def test_rule_v2_propagates_ocr_errors():
    r = split_document(doc_of("HOP DONG\n" + LONG, "", "BIEN BAN\n" + LONG, errors={2: "OCR hỏng"}), method="rule_v2")
    assert r.slices[0].ocr_errors == ["OCR hỏng"] and r.slices[1].ocr_errors == []


def test_empty_document_returns_empty_result_for_every_method():
    empty = OCRDocumentResult(file_name="e.pdf", total_pages=0, pages=[])
    for m in ("rule", "rule_v2"):
        assert split_document(empty, method=m).slices == []
