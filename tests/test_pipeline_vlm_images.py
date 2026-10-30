"""Pipeline dựng ảnh trang cho nguồn VLM của ngày hết hạn: bộ dựng ảnh, LLM và VLM đều giả (không GPU, không mạng, không PDF thật)."""
from pathlib import Path

from src.common.contracts import DocumentSlice, OCRDocumentResult, OCRPageResult, SplitResult
from src.extraction.field_extractor import ExtractConfig, FieldExtractor
from src.pipeline import AUTO_FILE, DocumentPipeline, choose_vlm_pages

GCN = "Số: 83/GCNĐĐK-SCT\nGiấy chứng nhận này có giá trị đến hết ngày 09 tháng 4 năm 2024.\n"
PXK = "PHIẾU XUẤT KHO số 1"


def page(n, text):
    return OCRPageResult(page_number=n, width=10, height=10, full_text=text, ocr_engine="fake@cpu", source="ocr")


def one_slice(doc):
    return SplitResult(source_file=doc.file_name, total_pages=doc.total_pages,
                       slices=[DocumentSlice(slice_id="slice_001", start_page=doc.pages[0].page_number, end_page=doc.pages[-1].page_number,
                                             page_count=len(doc.pages), combined_text="\n".join(p.full_text for p in doc.pages), pages=doc.pages)])


class Clf:
    def __init__(self, label):
        self.label = label

    def classify_slice(self, sl):
        from src.common.contracts import ClassificationResult
        return ClassificationResult(slice_id=sl.slice_id, predicted_category=self.label, tier="rule", confidence=1.0)


class FakeLlm:
    def __call__(self, system, user, schema):
        return {k: None for k in schema["properties"]}


class FakeVlm:
    def __init__(self, date):
        self.date, self.calls = date, []

    def __call__(self, system, user, schema, images):
        self.calls.append(list(images))
        return {k: (self.date if k == "ngay_het_han" else None) for k in schema["properties"]}


class Renderer:
    def __init__(self):
        self.calls, self.dirs = [], []

    def __call__(self, pdf, pages, out_dir):
        self.calls.append((Path(pdf).name, list(pages)))
        out_dir.mkdir(parents=True, exist_ok=True)
        files = []
        for p in pages:
            f = out_dir / f"p{p:02d}.png"
            f.write_bytes(b"x")
            files.append(f)
        self.dirs.append(out_dir)
        return files


def make(pages, label, vlm, renderer, **kw):
    ocr = lambda path: OCRDocumentResult(file_name=Path(path).name, total_pages=len(pages), pages=pages)
    ex = FieldExtractor(ExtractConfig(auto_accept_expiry=True, expiry_rule="regex=vlm"), llm_client=FakeLlm(), vlm_client=vlm)
    return DocumentPipeline(ocr=ocr, splitter=one_slice, classifier=Clf(label), extractor=ex, page_renderer=renderer, **kw)


def test_choose_vlm_pages_matches_team4_rule():
    assert choose_vlm_pages([1, 2, 3, 4], {}) == [1, 2, 3, 4]
    pages = list(range(1, 11))
    texts = {5: "Có hiệu lực đến ngày", 7: "thời hạn, hết hạn, có giá trị đến", 3: "không có gì"}
    assert choose_vlm_pages(pages, texts) == [1, 2, 5, 7, 10]
    many = {p: "hiệu lực" * (p % 5 + 1) for p in range(3, 10)}
    out = choose_vlm_pages(pages, many)
    assert len(out) == 6 and out[:2] == [1, 2] and 10 in out


def test_images_rendered_passed_timed_and_deleted():
    vlm, rend = FakeVlm("09/04/2024"), Renderer()
    res = make([page(1, GCN), page(2, "tiếp")], "GCN_DDK_BAN_LE_XD", vlm, rend).run("a.pdf")
    assert rend.calls == [("a.pdf", [1, 2])]
    assert len(vlm.calls) == 1 and [p.name for p in vlm.calls[0]] == ["p01.png", "p02.png"]
    r = res.routing[0]
    assert r.decision == AUTO_FILE and r.expiry == {"ngay_het_han": "accepted"}
    assert res.extractions[0].entity_dict["ngay_het_han"] == "2024-04-09"
    assert "render" in res.stage_timings_ms and res.stage_timings_ms["render"] >= 0
    assert not rend.dirs[0].exists() and not rend.dirs[0].parent.exists()        # ảnh giấy tờ không nằm lại trên đĩa


def test_no_vlm_flag_means_no_rendering_and_no_render_timing():
    vlm, rend = FakeVlm("09/04/2024"), Renderer()
    res = make([page(1, GCN)], "GCN_DDK_BAN_LE_XD", vlm, rend, use_vlm=False).run("a.pdf")
    assert rend.calls == [] and vlm.calls == [] and "render" not in res.stage_timings_ms
    assert res.routing[0].expiry == {"ngay_het_han": "needs_review"}


def test_no_render_when_llm_off_or_type_has_no_expiry_field():
    rend = Renderer()
    make([page(1, GCN)], "GCN_DDK_BAN_LE_XD", FakeVlm("09/04/2024"), rend, use_llm=False).run("a.pdf")
    make([page(1, PXK)], "PHIEU_XUAT_KHO", FakeVlm("09/04/2024"), rend).run("a.pdf")
    make([page(1, "x")], "BB_GIAO_NHAN_HANG_HOA", FakeVlm("09/04/2024"), rend).run("a.pdf")
    assert rend.calls == []


def test_render_failure_is_a_warning_and_extraction_continues():
    def boom(pdf, pages, out_dir):
        raise RuntimeError("không mở được PDF")
    res = make([page(1, GCN)], "GCN_DDK_BAN_LE_XD", FakeVlm("09/04/2024"), boom).run("a.pdf")
    assert any(w.startswith("render slice_001") and "không mở được PDF" in w for w in res.warnings)
    assert res.extractions[0].status == "ok" and res.routing[0].expiry == {"ngay_het_han": "needs_review"}


def test_non_field_extractor_never_triggers_rendering():
    class Plain:
        def extract(self, sl, cat):
            from src.common.contracts import ExtractionResult
            return ExtractionResult(slice_id=sl.slice_id, document_type=cat, status="ok")
    rend = Renderer()
    ocr = lambda path: OCRDocumentResult(file_name="a.pdf", total_pages=1, pages=[page(1, GCN)])
    res = DocumentPipeline(ocr=ocr, splitter=one_slice, classifier=Clf("GCN_DDK_BAN_LE_XD"), extractor=Plain(), page_renderer=rend).run("a.pdf")
    assert rend.calls == [] and res.extractions[0].status == "ok"
