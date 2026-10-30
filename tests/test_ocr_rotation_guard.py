"""Kiểm thử điều kiện "không xoay trang ít chữ" của src/ocr/pdf_ocr.py (T2, teams/team1_ocr/experiments/05_rotation).

Engine tự xoay trang khi đa số hộp chữ là hộp đứng; vết đen mép giấy của máy scan trên trang trống cũng là một hộp đứng nên trang trống
bị "xoay" và ra vài ký tự rác. Quy tắc: engine báo `rotated_*` mà văn bản < ngưỡng ký tự -> coi là trang trống. Engine giả, không GPU."""
import fitz
import pytest

from src.ocr.pdf_ocr import DEFAULT_MIN_CHARS_FOR_ROTATION, ocr_page, ocr_pdf, ocr_pdf_pages

LONG = "Phiếu xuất kho số 123 hàng hóa xăng dầu của công ty kinh doanh " * 2      # 120+ ký tự


class FakeEngine:
    name = "fake@cpu"

    def __init__(self, text, flags):
        self.text, self.flags = text, flags

    def ocr(self, img):
        return self.text, 0.9, list(self.flags)


def blank_pdf(path, n=1):
    doc = fitz.open()
    for _ in range(n):
        doc.new_page(width=300, height=400)
    doc.save(str(path))
    doc.close()
    return path


def run(tmp_path, text, flags, **kw):
    pdf = blank_pdf(tmp_path / "b.pdf")
    doc = fitz.open(str(pdf))
    try:
        return ocr_page(doc[0], 0, FakeEngine(text, flags), **kw)
    finally:
        doc.close()


def test_default_threshold_is_30_and_below_the_shortest_correctly_rotated_page():
    assert DEFAULT_MIN_CHARS_FOR_ROTATION == 30      # trang xoay đúng ngắn nhất trong mẫu T2 có 169 ký tự; trang trống bị xoay nhầm có 3-7


def test_rotated_page_with_few_chars_is_treated_as_blank(tmp_path):
    p = run(tmp_path, "a, 3\nx", ["rotated_270"])
    assert p.text == "" and p.n_chars == 0 and p.mean_conf is None and p.error is None
    assert "rotated_270" not in p.flags
    assert "rotation_rejected_low_text:270" in p.flags and "empty_text" in p.flags


def test_rotated_page_with_enough_text_is_unchanged(tmp_path):
    p = run(tmp_path, LONG, ["bg_normalized", "rotated_90"])
    assert p.text == LONG.strip() and p.flags == ["bg_normalized", "rotated_90"] and p.mean_conf == pytest.approx(0.9)


def test_short_page_that_was_not_rotated_is_unchanged(tmp_path):
    p = run(tmp_path, "Số 5", ["bg_normalized"])      # trang ngắn bình thường (tem, phiếu nhỏ) không bị đụng tới
    assert p.text == "Số 5" and p.flags == ["bg_normalized"]


def test_threshold_boundary_is_strict_less_than(tmp_path):
    text = "x" * 30
    assert run(tmp_path, text, ["rotated_90"]).text == text                                   # đúng 30 ký tự: giữ
    assert run(tmp_path, "x" * 29, ["rotated_90"]).text == ""                                 # 29: bỏ


@pytest.mark.parametrize("off", [0, None])
def test_guard_can_be_switched_off_to_reproduce_ocr_v2(tmp_path, off):
    p = run(tmp_path, "a, 3", ["rotated_270"], min_chars_for_rotation=off)
    assert p.text == "a, 3" and p.flags == ["rotated_270"]


def test_parameter_is_passed_through_ocr_pdf_and_ocr_pdf_pages(tmp_path):
    pdf = blank_pdf(tmp_path / "two.pdf", n=2)
    eng = FakeEngine("ab", ["rotated_90"])
    res = ocr_pdf(pdf, eng)
    assert [p.full_text for p in res.pages] == ["", ""] and all("rotation_rejected_low_text:90" in p.flags for p in res.pages)
    assert res.error is None
    res_off = ocr_pdf(pdf, eng, min_chars_for_rotation=0)
    assert [p.full_text for p in res_off.pages] == ["ab", "ab"]
    outs = ocr_pdf_pages(pdf, eng, min_chars_for_rotation=100)[1]
    assert [o.text for o in outs] == ["", ""]
