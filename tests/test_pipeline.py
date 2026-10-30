"""Kiểm thử src/pipeline.py bằng thành phần giả: không GPU, không mạng, không mô hình thật."""

import json
from pathlib import Path

import pytest

from src.common.contracts import (UNKNOWN_CATEGORY, ClassificationResult, DocumentProcessingPipelineResult, DocumentSlice, ExtractionResult,
                                  OCRDocumentResult, OCRPageResult, SplitResult)
from src.pipeline import AUTO_FILE, NEEDS_HUMAN, DocumentPipeline, resolve_device, route_slice


def page(n, text="nội dung", error=None):
    return OCRPageResult(page_number=n, width=10, height=10, full_text=text, error=error, ocr_engine="fake@cpu", source="ocr")


def fake_ocr(pages, total=None, error=None):
    def run(path):
        return OCRDocumentResult(file_name=Path(path).name, total_pages=total or len(pages), pages=pages, error=error)
    return run


def split_each_page(doc):
    slices = [DocumentSlice(slice_id=f"slice_{i:03d}", start_page=p.page_number, end_page=p.page_number, page_count=1,
                            combined_text=p.full_text, pages=[p], ocr_errors=[p.error] if p.error else [])
              for i, p in enumerate(doc.pages, 1)]
    return SplitResult(source_file=doc.file_name, total_pages=doc.total_pages, slices=slices)


class FakeClassifier:
    """Trả kết quả theo từ khóa trong văn bản lát cắt."""

    def __init__(self):
        self.seen = []

    def classify_slice(self, sl):
        self.seen.append(sl.slice_id)
        t = sl.combined_text
        if "BOOM" in t:
            raise RuntimeError("bộ phân loại hỏng giả lập")
        if "TỰ NHẬN" in t:
            return ClassificationResult(slice_id=sl.slice_id, predicted_category="PHIEU_XUAT_KHO", confidence=0.9, tier="rule",
                                        model_name="keyword_rule_gate", confidence_kind="heuristic")
        return ClassificationResult(slice_id=sl.slice_id, predicted_category=UNKNOWN_CATEGORY, tier="human", requires_human_review=True,
                                    abstain_reason="llm_low_confidence", suggested_category="HD_MUA_BAN", suggestion_source="llm")


class FakeExtractor:
    def __init__(self, fail=False, status="ok"):
        self.calls, self.fail, self.status = [], fail, status

    def extract(self, sl, label):
        self.calls.append((sl.slice_id, label))
        if self.fail:
            raise RuntimeError("GLiNER không nạp được")
        return ExtractionResult(slice_id=sl.slice_id, document_type=label, status=self.status,
                                error=None if self.status == "ok" else "lỗi giả")


def make(pages, **kw):
    kw.setdefault("ocr", fake_ocr(pages))
    kw.setdefault("splitter", split_each_page)
    kw.setdefault("classifier", FakeClassifier())
    kw.setdefault("extractor", FakeExtractor())
    return DocumentPipeline(**kw)


def test_end_to_end_with_fakes_builds_the_contract_result_with_timings_and_routing():
    pipe = make([page(1, "TỰ NHẬN a"), page(2, "mơ hồ b")])
    res = pipe.run("x/tai_lieu.pdf")
    assert isinstance(res, DocumentProcessingPipelineResult)
    assert res.file_name == "tai_lieu.pdf" and res.total_pages == 2 and res.is_composite_bundle is True
    assert len(res.split_result.slices) == len(res.classifications) == len(res.routing) == 2
    assert [r.decision for r in res.routing] == [AUTO_FILE, NEEDS_HUMAN]
    assert res.routing[0].category == "PHIEU_XUAT_KHO" and res.routing[0].reasons == []
    assert res.routing[1].category == UNKNOWN_CATEGORY and res.routing[1].reasons == ["classification:llm_low_confidence"]
    assert res.routing[1].suggested_category == "HD_MUA_BAN"
    assert set(res.stage_timings_ms) == {"ocr", "split", "classify", "extract"} and all(v >= 0 for v in res.stage_timings_ms.values())
    assert res.total_processing_time_ms >= sum(res.stage_timings_ms.values()) - 1
    assert DocumentProcessingPipelineResult.model_validate_json(res.model_dump_json()) == res          # JSON round-trip


def test_extraction_runs_only_for_auto_filed_slices_with_the_accepted_label():
    ext = FakeExtractor()
    res = make([page(1, "TỰ NHẬN a"), page(2, "mơ hồ b")], extractor=ext).run("a.pdf")
    assert ext.calls == [("slice_001", "PHIEU_XUAT_KHO")]
    assert [e.slice_id for e in res.extractions] == ["slice_001"] and res.routing[0].extraction_status == "ok"
    assert res.routing[1].extraction_status is None


def test_no_extract_never_builds_the_extractor():
    def factory():
        raise AssertionError("không được nạp bộ trích xuất khi --no-extract")

    res = DocumentPipeline(ocr=fake_ocr([page(1, "TỰ NHẬN")]), splitter=split_each_page, classifier=FakeClassifier(),
                           extractor_factory=factory, run_extraction=False).run("a.pdf")
    assert res.extractions == [] and res.stage_timings_ms["extract"] == 0.0


def test_extraction_exception_is_recorded_not_fatal_and_keeps_the_filing_decision():
    res = make([page(1, "TỰ NHẬN")], extractor=FakeExtractor(fail=True)).run("a.pdf")
    assert res.routing[0].decision == AUTO_FILE and res.routing[0].extraction_status == "error"
    assert res.extractions[0].status == "error" and "GLiNER" in res.extractions[0].error
    assert any(w.startswith("extract slice_001") for w in res.warnings)


def test_extractor_returning_error_status_is_a_warning():
    res = make([page(1, "TỰ NHẬN")], extractor=FakeExtractor(status="error")).run("a.pdf")
    assert res.routing[0].extraction_status == "error" and any("lỗi giả" in w for w in res.warnings)


def test_classifier_exception_sends_slice_to_human_with_the_error():
    res = make([page(1, "BOOM"), page(2, "TỰ NHẬN")]).run("a.pdf")
    c = res.classifications[0]
    assert c.tier == "human" and c.predicted_category == UNKNOWN_CATEGORY and c.abstain_reason == "classifier_exception"
    assert "RuntimeError" in c.error and res.routing[0].decision == NEEDS_HUMAN and "classifier_error" in res.routing[0].reasons
    assert res.routing[1].decision == AUTO_FILE                                       # lát cắt khác không bị ảnh hưởng


def test_classifier_that_cannot_be_built_marks_every_slice_for_humans():
    def factory():
        raise FileNotFoundError("thiếu models/classification")

    res = DocumentPipeline(ocr=fake_ocr([page(1), page(2)]), splitter=split_each_page, classifier_factory=factory,
                           run_extraction=False).run("a.pdf")
    assert [r.decision for r in res.routing] == [NEEDS_HUMAN, NEEDS_HUMAN]
    assert all(c.abstain_reason == "classifier_unavailable" and "thiếu models" in c.error for c in res.classifications)
    assert any("không dựng được bộ phân loại" in w for w in res.warnings)


def test_ocr_error_forces_human_even_if_classifier_is_confident():
    res = make([page(1, "TỰ NHẬN", error="RuntimeError: ảnh hỏng")]).run("a.pdf")
    assert res.routing[0].decision == NEEDS_HUMAN and res.routing[0].reasons == ["ocr_error"]
    assert res.extractions == []                                                      # không trích xuất khi chưa xếp hồ sơ


def test_document_level_ocr_error_and_truncation_are_reported_as_warnings():
    res = make([page(1, "TỰ NHẬN")], ocr=fake_ocr([page(1, "TỰ NHẬN")], total=5, error="Trang 2: lỗi")).run("a.pdf")
    assert any("ocr: Trang 2: lỗi" in w for w in res.warnings)
    assert any("chỉ xử lý 1/5 trang" in w for w in res.warnings)


def test_empty_document_yields_no_slices_and_no_crash():
    res = make([], ocr=fake_ocr([], total=0, error="open_failed: x")).run("a.pdf")
    assert res.split_result.slices == [] and res.classifications == [] and res.is_composite_bundle is False
    assert any("open_failed" in w for w in res.warnings)


def test_no_llm_warning_is_reported():
    res = make([page(1, "TỰ NHẬN")], use_llm=False).run("a.pdf")
    assert any("--no-llm" in w for w in res.warnings)


def test_route_slice_requires_review_flag_blocks_auto_file():
    sl = DocumentSlice(slice_id="s", start_page=1, end_page=1, page_count=1, combined_text="x")
    cls = ClassificationResult(slice_id="s", predicted_category="X", tier="kev", requires_human_review=True)
    r = route_slice(sl, cls)
    assert r.decision == NEEDS_HUMAN and r.reasons == ["classification:requires_review"] and r.category == UNKNOWN_CATEGORY


def test_resolve_device_passthrough():
    assert resolve_device("cpu") == "cpu" and resolve_device("cuda:0") == "cuda:0"


# ---------- CLI ----------
def test_cli_writes_json_outside_the_pdf_folder_and_refuses_same_folder(tmp_path, monkeypatch, capsys):
    import importlib.util
    spec = importlib.util.spec_from_file_location("run_pipeline", Path(__file__).resolve().parent.parent / "scripts" / "run_pipeline.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    pdf = tmp_path / "src" / "a.pdf"
    pdf.parent.mkdir()
    pdf.write_bytes(b"%PDF-1.4")

    class Stub(DocumentPipeline):
        def __init__(self, **kw):
            super().__init__(ocr=fake_ocr([page(1, "TỰ NHẬN")]), splitter=split_each_page, classifier=FakeClassifier(),
                             extractor=FakeExtractor(), **{k: v for k, v in kw.items() if k in ("run_extraction", "use_llm")})

    monkeypatch.setattr(mod, "DocumentPipeline", Stub)
    out = tmp_path / "out"
    assert mod.main([str(pdf), "--out", str(out), "--no-llm"]) == 0
    data = json.loads((out / "a.pipeline.json").read_text(encoding="utf-8"))
    assert data["routing"][0]["decision"] == "auto_file" and "stage_timings_ms" in data
    assert "auto_file" in capsys.readouterr().out
    assert mod.main([str(pdf), "--out", str(pdf.parent)]) == 2                      # không ghi cạnh PDF nguồn
    assert mod.main([str(tmp_path / "khong_co.pdf")]) == 2


# =====================================================================================================================
# Chính sách tách mặc định, gộp theo loại, triage, hết giờ LLM, tóm tắt cấp tệp, hook trích xuất  (không GPU, không mạng)
# =====================================================================================================================
from src.classification.zero_shot import NO_ANSWER, Answer
from src.common.contracts import FileRoutingSummary
from src.pipeline import GuardedLlm, REASON_POSSIBLE_COMPOSITE, is_llm_timeout

NAN = float("nan")


class FakeModel:
    """Giả PairBoundaryModel: điểm cố định theo tệp (độ dài phải khớp số trang)."""
    threshold = 0.5

    def __init__(self, scores):
        self.scores = scores

    def doc_scores(self, texts):
        assert len(texts) == len(self.scores)
        return list(self.scores)


class KeywordClassifier:
    """Loại theo từ khóa trong văn bản lát cắt: 'PXK' -> PHIEU_XUAT_KHO, 'LM' -> BB_LAY_MAU, 'CTCL' -> CHUNG_THU_CHAT_LUONG; còn lại về người."""
    llm = None

    def __init__(self):
        self.seen = []

    def classify_slice(self, sl):
        self.seen.append(sl.slice_id)
        for kw, cat in (("PXK", "PHIEU_XUAT_KHO"), ("LM", "BB_LAY_MAU"), ("CTCL", "CHUNG_THU_CHAT_LUONG")):
            if kw in sl.combined_text:
                return ClassificationResult(slice_id=sl.slice_id, predicted_category=cat, confidence=0.9, tier="rule", model_name="fake")
        return ClassificationResult(slice_id=sl.slice_id, predicted_category=UNKNOWN_CATEGORY, tier="human", requires_human_review=True,
                                    abstain_reason="no_rule")


def pipe_with(pages, scores, policy=None, clf=None, **kw):
    return DocumentPipeline(ocr=fake_ocr(pages), classifier=clf or KeywordClassifier(), extractor=FakeExtractor(), split_model=FakeModel(scores),
                            split_policy=policy, one_sheet_types=frozenset({"BB_LAY_MAU"}), **kw)


def test_default_pipeline_policy_is_model_plus_merge_and_custom_splitter_overrides_it():
    assert DocumentPipeline(classifier=KeywordClassifier()).policy.name == "model+merge"
    assert DocumentPipeline(splitter=split_each_page).policy.name == "custom"
    assert DocumentPipeline(split_policy="rule").policy.method == "rule"
    with pytest.raises(ValueError):
        DocumentPipeline(split_policy="khong_co")


def test_default_policy_splits_at_the_threshold_then_merges_adjacent_same_type_slices():
    pages = [page(1, "PXK trang 1"), page(2, "PXK trang 2 chữ ký"), page(3, "CTCL chứng thư")]
    res = pipe_with(pages, [NAN, 0.8, 0.9]).run("a.pdf")          # 0,8 và 0,9 >= 0,7 => 3 lát cắt thô; hai lát PXK đầu bị gộp (điểm < 0,99)
    assert [(s.start_page, s.end_page) for s in res.split_result.slices] == [(1, 2), (3, 3)]
    assert [r.category for r in res.routing] == ["PHIEU_XUAT_KHO", "CHUNG_THU_CHAT_LUONG"] and res.is_composite_bundle
    fr = res.file_routing
    assert isinstance(fr, FileRoutingSummary) and fr.decision == AUTO_FILE and (fr.n_slices_before_merge, fr.n_slices, fr.n_auto) == (3, 2, 2)
    assert fr.splitter == "model+merge" and any("gộp 3 -> 2" in w for w in res.warnings)
    assert res.split_result.slices[0].boundary_method == "model+type_merge"
    assert DocumentProcessingPipelineResult.model_validate_json(res.model_dump_json()) == res


def test_very_confident_boundary_survives_the_merge_and_scores_below_threshold_do_not_split():
    pages = [page(1, "PXK a"), page(2, "PXK b"), page(3, "PXK c")]
    res = pipe_with(pages, [NAN, 0.995, 0.6]).run("a.pdf")          # 0,995 >= keep_above(0,99) giữ; 0,6 < 0,7 không tách
    assert [(s.start_page, s.end_page) for s in res.split_result.slices] == [(1, 1), (2, 3)]


def test_one_sheet_types_are_not_merged_in_the_pipeline():
    pages = [page(1, "LM biên bản 1"), page(2, "LM biên bản 2"), page(3, "LM biên bản 3")]
    res = pipe_with(pages, [NAN, 0.8, 0.8]).run("a.pdf")
    assert len(res.split_result.slices) == 3 and [r.category for r in res.routing] == ["BB_LAY_MAU"] * 3
    assert res.file_routing.n_slices_before_merge == 3


def test_rejected_slices_are_not_merged_and_send_the_file_to_a_human():
    pages = [page(1, "PXK a"), page(2, "không rõ"), page(3, "không rõ khác")]
    res = pipe_with(pages, [NAN, 0.8, 0.8]).run("a.pdf")
    assert len(res.split_result.slices) == 3
    fr = res.file_routing
    assert fr.decision == NEEDS_HUMAN and (fr.n_auto, fr.n_needs_human) == (1, 2) and "classification:no_rule" in fr.reasons


def test_none_policy_keeps_the_whole_file_as_one_slice_and_needs_no_model():
    pages = [page(1, "PXK a"), page(2, "CTCL b")]
    res = DocumentPipeline(ocr=fake_ocr(pages), classifier=KeywordClassifier(), extractor=FakeExtractor(), split_policy="none").run("a.pdf")
    assert len(res.split_result.slices) == 1 and res.split_result.slices[0].boundary_method == "none" and res.file_routing.splitter == "none"


def test_triage_policy_sends_a_suspected_composite_to_a_human_and_never_extracts():
    ext = FakeExtractor()
    pages = [page(1, "PXK a"), page(2, "PXK b")]
    res = DocumentPipeline(ocr=fake_ocr(pages), classifier=KeywordClassifier(), extractor=ext, split_model=FakeModel([NAN, 0.4]),
                           split_policy="triage").run("a.pdf")
    assert len(res.split_result.slices) == 1
    r = res.routing[0]
    assert r.decision == NEEDS_HUMAN and r.category == UNKNOWN_CATEGORY and r.suggested_category == "PHIEU_XUAT_KHO"
    assert REASON_POSSIBLE_COMPOSITE in r.reasons and res.file_routing.decision == NEEDS_HUMAN and ext.calls == []
    low = DocumentPipeline(ocr=fake_ocr(pages), classifier=KeywordClassifier(), extractor=ext, split_model=FakeModel([NAN, 0.1]),
                           split_policy="triage").run("a.pdf")
    assert low.file_routing.decision == AUTO_FILE and ext.calls == [("slice_001", "PHIEU_XUAT_KHO")]


def test_empty_file_summary_and_old_json_without_file_routing_still_loads():
    res = make([], ocr=fake_ocr([], total=0, error="open_failed: x")).run("a.pdf")
    assert res.file_routing.decision == NEEDS_HUMAN and res.file_routing.reasons == ["no_slices"]
    data = json.loads(res.model_dump_json())
    data.pop("file_routing")
    assert DocumentProcessingPipelineResult.model_validate(data).file_routing is None


def test_extract_fields_hook_is_the_single_point_extraction_goes_through():
    calls = []

    class MyPipe(DocumentPipeline):
        def extract_fields(self, sl, category, filename=None, page_images=None):
            calls.append((sl.slice_id, category, filename))
            return ExtractionResult(slice_id=sl.slice_id, document_type=category, status="ok")

    res = MyPipe(ocr=fake_ocr([page(1, "PXK a"), page(2, "không rõ")]), splitter=split_each_page, classifier=KeywordClassifier()).run("a.pdf")
    assert calls == [("slice_001", "PHIEU_XUAT_KHO", "a.pdf")] and res.routing[0].extraction_status == "ok" and res.routing[1].extraction_status is None


# ---------- hết giờ LLM: một lời gọi kẹt không được làm tệp đứng ----------
class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class FakeLlm:
    tier_name, model_name = "llm", "fake-llm"

    def __init__(self, clock, script):
        self.clock, self.script, self.calls = clock, list(script), 0

    def answer(self, text):
        self.calls += 1
        kind, secs = self.script.pop(0) if self.script else ("ok", 1.0)
        self.clock.t += secs
        if kind == "timeout":
            return Answer(NO_ANSWER, None, None, secs * 1000, False, "ReadTimeout: HTTPConnectionPool(...): Read timed out. (read timeout=45)")
        if kind == "conn":
            return Answer(NO_ANSWER, None, None, 0.0, False, "ConnectionError: refused")
        return Answer("PHIEU_XUAT_KHO", 0.9, None, secs * 1000, True, "")


def test_is_llm_timeout_matches_requests_style_errors_only():
    assert is_llm_timeout("ReadTimeout: x") and is_llm_timeout("ConnectTimeout: y") and not is_llm_timeout("HTTP 500") and not is_llm_timeout(None)


def test_guard_skips_the_rest_of_the_file_after_a_timeout_and_resets_per_file():
    clock = Clock()
    g = GuardedLlm(FakeLlm(clock, [("ok", 1.0), ("timeout", 45.0)]), file_budget_s=90, clock=clock)
    assert g.answer("a").parse_ok
    assert not g.answer("b").parse_ok and g.timeouts == 1
    skipped = g.answer("c")
    assert not skipped.parse_ok and skipped.error.startswith("llm_skipped") and g.calls == 2 and g.skipped == 1
    g.end_file()
    g.start_file()
    assert g.answer("d").parse_ok and g.calls == 1                              # tệp mới: LLM dùng lại được (mạch ngắt chưa mở sau 1 tệp xấu)


def test_guard_enforces_the_per_file_budget():
    clock = Clock()
    g = GuardedLlm(FakeLlm(clock, [("ok", 40.0), ("ok", 40.0), ("ok", 40.0)]), file_budget_s=75, clock=clock)
    assert g.answer("a").parse_ok and g.answer("b").parse_ok
    r = g.answer("c")                                                           # đã chờ 80 s >= 75 s
    assert r.error.startswith("llm_skipped") and "ngân sách" in r.error and g.calls == 2


def test_guard_circuit_opens_after_two_consecutive_bad_files_and_closes_after_cooldown():
    clock = Clock()
    llm = FakeLlm(clock, [("timeout", 45.0), ("timeout", 45.0)])
    g = GuardedLlm(llm, file_budget_s=90, cooldown_s=60, clock=clock)
    for _ in range(2):
        g.start_file()
        assert not g.answer("x").parse_ok
        g.end_file()
    g.start_file()
    r = g.answer("y")
    assert "mạch ngắt" in r.error and llm.calls == 2                            # không gọi thêm trong thời gian nguội
    clock.t += 61
    g.start_file()
    assert g.answer("z").parse_ok and llm.calls == 3


def test_guard_retries_a_connection_error_exactly_once():
    clock = Clock()
    llm = FakeLlm(clock, [("conn", 0.0), ("ok", 1.0)])
    assert GuardedLlm(llm, clock=clock).answer("a").parse_ok and llm.calls == 2
    llm2 = FakeLlm(clock, [("conn", 0.0), ("conn", 0.0), ("ok", 1.0)])
    r = GuardedLlm(llm2, clock=clock).answer("a")
    assert not r.parse_ok and r.error.startswith("ConnectionError") and llm2.calls == 2


class LlmClassifier:
    """Phân loại bằng LLM giả cho MỌI lát cắt (để thử đường hết giờ qua pipeline)."""

    def __init__(self, llm):
        self.llm = llm

    def classify_slice(self, sl):
        a = self.llm.answer(sl.combined_text)
        if a.parse_ok:
            return ClassificationResult(slice_id=sl.slice_id, predicted_category=a.label, confidence=a.conf or 0.0, tier="llm", model_name="fake")
        return ClassificationResult(slice_id=sl.slice_id, predicted_category=UNKNOWN_CATEGORY, tier="human", requires_human_review=True,
                                    abstain_reason="llm_error", error=a.error)


def test_pipeline_does_not_stall_on_a_stuck_llm_and_routes_with_explicit_reasons():
    clock = Clock()
    llm = FakeLlm(clock, [("ok", 1.0), ("timeout", 45.0)])
    pages = [page(1, "a"), page(2, "b"), page(3, "c"), page(4, "d")]
    res = DocumentPipeline(ocr=fake_ocr(pages), splitter=split_each_page, classifier=LlmClassifier(llm), run_extraction=False, clock=clock,
                           llm_timeout_s=45, llm_file_budget_s=90).run("a.pdf")
    assert llm.calls == 2                                                        # lát 3, 4 KHÔNG gọi LLM sau khi lát 2 hết giờ
    assert [r.decision for r in res.routing] == [AUTO_FILE, NEEDS_HUMAN, NEEDS_HUMAN, NEEDS_HUMAN]
    assert "llm_timeout" in res.routing[1].reasons and "llm_skipped" in res.routing[2].reasons and "llm_skipped" in res.routing[3].reasons
    fr = res.file_routing
    assert fr.decision == NEEDS_HUMAN and fr.n_llm_calls == 2 and fr.llm_ms == pytest.approx(46000.0) and {"llm_timeout", "llm_skipped"} <= set(fr.reasons)


def test_pipeline_sets_the_timeout_on_the_real_backend_client():
    class Client:
        timeout = 180.0

    class Backend:
        client = Client()
        tier_name, model_name = "llm", "x"

        def answer(self, text):
            return Answer("A", 1.0, None, 0.0, True, "")

    clf = LlmClassifier(Backend())
    DocumentPipeline(ocr=fake_ocr([page(1)]), splitter=split_each_page, classifier=clf, run_extraction=False, llm_timeout_s=30).run("a.pdf")
    assert Backend.client.timeout == 30 and isinstance(clf.llm, GuardedLlm)


def test_route_slice_names_llm_timeout_and_skip():
    sl = DocumentSlice(slice_id="s", start_page=1, end_page=1, page_count=1, combined_text="x")
    t = route_slice(sl, ClassificationResult(slice_id="s", predicted_category=UNKNOWN_CATEGORY, tier="human", abstain_reason="llm_error",
                                             error="ReadTimeout: x", requires_human_review=True))
    s = route_slice(sl, ClassificationResult(slice_id="s", predicted_category=UNKNOWN_CATEGORY, tier="human", abstain_reason="llm_error",
                                             error="llm_skipped: mạch ngắt", requires_human_review=True))
    assert t.reasons == ["classification:llm_error", "classifier_error", "llm_timeout"]
    assert s.reasons == ["classification:llm_error", "classifier_error", "llm_skipped"]


def test_cli_passes_splitter_and_llm_timeout_options_and_prints_the_file_routing(tmp_path, monkeypatch, capsys):
    import importlib.util
    spec = importlib.util.spec_from_file_location("run_pipeline2", Path(__file__).resolve().parent.parent / "scripts" / "run_pipeline.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    seen = {}

    class Stub(DocumentPipeline):
        def __init__(self, **kw):
            seen.update(kw)
            super().__init__(ocr=fake_ocr([page(1, "PXK a")]), classifier=KeywordClassifier(), extractor=FakeExtractor(), split_policy="none",
                             run_extraction=kw.get("run_extraction", True))

    monkeypatch.setattr(mod, "DocumentPipeline", Stub)
    pdf = tmp_path / "in" / "a.pdf"
    pdf.parent.mkdir()
    pdf.write_bytes(b"%PDF-1.4")
    assert mod.main([str(pdf), "--out", str(tmp_path / "out"), "--splitter", "rule_v2", "--llm-timeout", "20", "--llm-file-budget", "50"]) == 0
    assert seen["split_policy"] == "rule_v2" and seen["llm_timeout_s"] == 20 and seen["llm_file_budget_s"] == 50
    assert "Định tuyến cấp tệp" in capsys.readouterr().out
    with pytest.raises(SystemExit):
        mod.main([str(pdf), "--out", str(tmp_path / "out"), "--splitter", "khong_co"])


# =====================================================================================================================
# Trích xuất trường (FieldExtractor) nối vào pipeline: loại chưa có schema, quy tắc hạn any-model=filename, định tuyến duyệt hạn
# =====================================================================================================================
GCN_TEXT = ("UBND TỈNH KHÁNH HÒA CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nSố: 83/GCNĐĐK-SCT Khánh Hoà, ngày 10 tháng 4 năm 2019\n"
            "1. Tên cửa hàng bán lẻ xăng dầu: Tàu dầu Mẫu 01;\nĐiều 3. Giấy chứng nhận này có giá trị đến\nhết ngày 09 tháng 4 năm 2024.\n")


class ConstClassifier:
    """Luôn trả một loại cố định (đã được nhận) cho mọi lát cắt."""
    llm = None

    def __init__(self, category):
        self.category = category

    def classify_slice(self, sl):
        return ClassificationResult(slice_id=sl.slice_id, predicted_category=self.category, confidence=0.9, tier="rule", model_name="fake")


class FakeFieldLlm:
    def __init__(self, **values):
        self.values, self.calls = values, 0

    def __call__(self, system, user, schema):
        self.calls += 1
        return {k: self.values.get(k) for k in schema["properties"]}


def field_pipe(category, llm_values, pdf_text=GCN_TEXT):
    from src.extraction.field_extractor import ExtractConfig, FieldExtractor
    llm = FakeFieldLlm(**llm_values)
    ex = FieldExtractor(ExtractConfig(auto_accept_expiry=True), llm_client=llm)
    return DocumentPipeline(ocr=fake_ocr([page(1, pdf_text)]), splitter=split_each_page, classifier=ConstClassifier(category), extractor=ex), llm


def test_default_extractor_is_the_field_extractor_and_cannot_touch_the_network_in_this_test(monkeypatch):
    from src.extraction.field_extractor import FieldExtractor
    p = DocumentPipeline(ocr=fake_ocr([page(1)]), splitter=split_each_page, classifier=ConstClassifier("X"))
    assert isinstance(p._get_extractor(), FieldExtractor)
    assert p._get_extractor().config.use_llm is True and p._get_extractor().config.store_personal_ids is False      # PII tắt mặc định
    assert DocumentPipeline(classifier=ConstClassifier("X"), use_llm=False)._get_extractor().config.use_llm is False


def test_type_without_schema_is_reported_as_not_extracted_not_as_an_error():
    pipe, llm = field_pipe("BB_LAY_MAU", {})
    res = pipe.run("x.pdf")
    r = res.routing[0]
    assert r.decision == AUTO_FILE and r.extraction_status == "skipped" and r.extraction_note.startswith("no_schema")
    assert res.extractions[0].status == "skipped" and llm.calls == 0 and not any("extract" in w for w in res.warnings)
    assert r.expiry == {} and r.field_review is False and res.file_routing.n_field_review == 0


def test_expiry_is_auto_accepted_when_a_model_agrees_with_the_filename_and_surfaced_in_routing():
    pipe, _ = field_pipe("GCN_DDK_BAN_LE_XD", {"ngay_het_han": "09/04/2024"})
    res = pipe.run("DDK-Cua hang-09.4.24.pdf")
    r = res.routing[0]
    assert res.extractions[0].entity_dict["ngay_het_han"] == "2024-04-09"
    assert r.expiry == {"ngay_het_han": "accepted"} and r.field_review is False and r.expiry_suggestion == {} and r.extraction_status == "ok"


def test_expiry_without_a_filename_match_goes_to_review_with_a_suggestion_and_keeps_the_filing_decision():
    pipe, _ = field_pipe("GCN_DDK_BAN_LE_XD", {"ngay_het_han": "09/04/2024"})
    res = pipe.run("scan_0001.pdf")                                          # tên tệp không chứa ngày => không tự nhận
    r = res.routing[0]
    assert r.decision == AUTO_FILE and r.category == "GCN_DDK_BAN_LE_XD"
    assert res.extractions[0].entity_dict["ngay_het_han"] is None
    assert r.expiry == {"ngay_het_han": "needs_review"} and r.expiry_suggestion == {"ngay_het_han": "2024-04-09"} and r.field_review is True
    assert res.file_routing.n_field_review == 1 and res.file_routing.decision == AUTO_FILE


def test_llm_failure_in_extraction_is_a_visible_partial_result_not_a_crash():
    from src.extraction import field_llm
    from src.extraction.field_extractor import ExtractConfig, FieldExtractor

    def boom(system, user, schema):
        raise field_llm.LlmError("Ollama tắt")

    pipe = DocumentPipeline(ocr=fake_ocr([page(1, GCN_TEXT)]), splitter=split_each_page, classifier=ConstClassifier("GCN_DDK_BAN_LE_XD"),
                            extractor=FieldExtractor(ExtractConfig(auto_accept_expiry=True), llm_client=boom))
    res = pipe.run("DDK-09.4.24.pdf")
    assert res.routing[0].extraction_status == "error" and "LLM" in res.routing[0].extraction_note and any(w.startswith("extract slice_001") for w in res.warnings)
    assert res.extractions[0].entity_dict["so_giay"] == "83/GCNDDK-SCT"        # trường do luật tìm được vẫn còn
    assert res.routing[0].decision == AUTO_FILE


def test_injected_extractor_receives_the_pdf_file_name_only_if_it_accepts_it():
    seen = {}

    class WithName:
        def extract(self, sl, label, filename=None):
            seen["fn"] = filename
            return ExtractionResult(slice_id=sl.slice_id, document_type=label)

    make([page(1, "TỰ NHẬN")], extractor=WithName()).run("thu_muc/ten tep.pdf")
    assert seen["fn"] == "ten tep.pdf"
    res = make([page(1, "TỰ NHẬN")], extractor=FakeExtractor()).run("a.pdf")           # FakeExtractor.extract(sl, label) không nhận filename
    assert res.routing[0].extraction_status == "ok"
