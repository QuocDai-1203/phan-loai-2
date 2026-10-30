"""Tùy chọn giai đoạn 3 của pipeline: `--splitter model+merge+id`, `--title-tiebreak`, nén PNG nhanh và khóa cache VLM theo điểm ảnh.
Không GPU, không mạng; PDF thử được dựng bằng PyMuPDF trong thư mục tạm."""
from pathlib import Path

import numpy as np
import pytest

from src.common.contracts import ClassificationResult, DocumentSlice, OCRDocumentResult, OCRPageResult, SplitResult
from src.pipeline import DocumentPipeline
from src.splitting.policy import PRESETS, resolve_policy


# --------------------------------------------------------------------------------------- CLI
def _run_cli(monkeypatch, tmp_path, extra):
    import scripts.run_pipeline as rp
    seen = {}

    class FakePipe:
        def __init__(self, **kw):
            seen.update(kw)

        def run(self, path):
            raise RuntimeError("stop")        # không cần chạy thật: chỉ kiểm tham số dựng pipeline

    monkeypatch.setattr(rp, "DocumentPipeline", FakePipe)
    pdf = tmp_path / "in" / "a.pdf"
    pdf.parent.mkdir(exist_ok=True)
    pdf.write_bytes(b"%PDF-1.4")
    with pytest.raises(RuntimeError, match="stop"):
        rp.main([str(pdf), "--out", str(tmp_path / "out")] + extra)
    return seen


def test_cli_accepts_model_merge_id_and_title_tiebreak(monkeypatch, tmp_path):
    kw = _run_cli(monkeypatch, tmp_path, ["--splitter", "model+merge+id", "--title-tiebreak"])
    assert kw["split_policy"] == "model+merge+id" and kw["title_tiebreak"] is True
    assert resolve_policy(kw["split_policy"]).id_rule is True


def test_cli_defaults_unchanged(monkeypatch, tmp_path):
    kw = _run_cli(monkeypatch, tmp_path, [])
    assert kw["split_policy"] == "model+merge" and kw["title_tiebreak"] is False and kw["auto_accept_expiry"] is False   # về mặc định an toàn (báo cáo 04 N1/N2)
    assert PRESETS["model+merge"].id_rule is False
    on = _run_cli(monkeypatch, tmp_path, ["--auto-accept-expiry"])
    assert on["auto_accept_expiry"] is True and on["split_policy"] == "model+merge"


def test_pipeline_default_has_no_id_no_tiebreak_no_auto_expiry():
    p = DocumentPipeline(classifier=FlagClf())
    assert p.policy.name == "model+merge" and p.title_tiebreak is False and p.auto_accept_expiry is False


def test_cli_rejects_unknown_splitter(monkeypatch, tmp_path):
    import scripts.run_pipeline as rp
    with pytest.raises(SystemExit):
        rp.main([str(tmp_path / "a.pdf"), "--splitter", "khong-co"])


# --------------------------------------------------------------------------------------- tiebreak truyền vào bộ phân loại
class FlagClf:
    rule_title_tiebreak = False
    llm = None

    def classify_slice(self, sl):
        return ClassificationResult(slice_id=sl.slice_id, predicted_category="HOA_DON", tier="rule", confidence=1.0)


def _doc(path):
    p = OCRPageResult(page_number=1, width=10, height=10, full_text="x", ocr_engine="fake@cpu", source="ocr")
    return OCRDocumentResult(file_name=Path(path).name, total_pages=1, pages=[p])


def _one(doc):
    return SplitResult(source_file=doc.file_name, total_pages=1, slices=[DocumentSlice(slice_id="slice_001", start_page=1, end_page=1, page_count=1,
                                                                                         combined_text="x", pages=doc.pages)])


@pytest.mark.parametrize("flag", [False, True])
def test_title_tiebreak_reaches_classifier(flag):
    clf = FlagClf()
    DocumentPipeline(ocr=_doc, splitter=_one, classifier=clf, run_extraction=False, title_tiebreak=flag).run("a.pdf")
    assert clf.rule_title_tiebreak is flag


def test_title_tiebreak_does_not_touch_classifier_without_the_attribute():
    class Plain:
        llm = None

        def classify_slice(self, sl):
            return FlagClf().classify_slice(sl)

    p = Plain()
    DocumentPipeline(ocr=_doc, splitter=_one, classifier=p, run_extraction=False, title_tiebreak=True).run("a.pdf")
    assert not hasattr(p, "rule_title_tiebreak")


# --------------------------------------------------------------------------------------- ảnh VLM: nén nhanh, cùng điểm ảnh, khóa cache theo điểm ảnh
def _make_pdf(path: Path):
    import fitz
    d = fitz.open()
    for i in range(2):
        pg = d.new_page(width=420, height=595)
        pg.insert_text((50, 100 + 20 * i), "Giay chung nhan co gia tri den het ngay 09/04/2024", fontsize=12)
        pg.draw_rect(fitz.Rect(60, 300, 300, 420), color=(0.1, 0.2, 0.7), fill=(0.9, 0.9, 0.6))
    d.save(path)
    d.close()


def test_render_uses_fast_png_and_identical_pixels(tmp_path):
    from PIL import Image

    from src.extraction import field_vlm
    pdf = tmp_path / "t.pdf"
    _make_pdf(pdf)
    paths = field_vlm.render_pages_for_vlm(pdf, [1, 2], tmp_path / "img")
    assert [p.name for p in paths] == ["p01_a.png", "p01_b.png", "p02_a.png", "p02_b.png"]
    for p in paths:
        with Image.open(p) as im:
            ref = tmp_path / ("opt_" + p.name)
            im.convert("RGB").save(ref, optimize=True)         # cách lưu cũ
            a = np.asarray(im.convert("RGB"))
        with Image.open(ref) as r:
            assert np.array_equal(a, np.asarray(r.convert("RGB")))             # cùng điểm ảnh
        assert field_vlm.image_content_hash(p) == field_vlm.image_content_hash(ref)  # khóa cache theo điểm ảnh


def test_content_hash_changes_with_pixels_and_falls_back_for_non_images(tmp_path):
    from PIL import Image

    from src.extraction import field_vlm
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    Image.new("RGB", (8, 8), (255, 255, 255)).save(a)
    im = Image.new("RGB", (8, 8), (255, 255, 255))
    im.putpixel((3, 3), (0, 0, 0))
    im.save(b)
    assert field_vlm.image_content_hash(a) != field_vlm.image_content_hash(b)
    junk = tmp_path / "x.png"
    junk.write_bytes(b"x")
    assert len(field_vlm.image_content_hash(junk)) == 16
