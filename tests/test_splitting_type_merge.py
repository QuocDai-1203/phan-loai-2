"""Kiểm thử hiệu chỉnh tách trang nhận biết loại (src/splitting/type_merge.py) và chính sách tách (src/splitting/policy.py). Không GPU, không mạng."""
import json

import pytest

from src.common.contracts import DocumentSlice, OCRDocumentResult, OCRPageResult, SplitResult
from src.splitting.boundary_detector import split_document
from src.splitting.policy import DEFAULT_PRESET, PRESETS, SplitPolicy, resolve_policy, split_with_policy
from src.splitting.type_merge import load_one_sheet_types, merge_groups, merge_same_type

NAN = float("nan")


def page(n, text="nội dung " * 20, error=None):
    return OCRPageResult(page_number=n, width=0, height=0, full_text=text, ocr_engine="fake", source="ocr", error=error)


def doc_of(*texts):
    pages = [page(i, t) for i, t in enumerate(texts, 1)]
    return OCRDocumentResult(file_name="x.pdf", total_pages=len(pages), pages=pages)


def one_slice_each(n, conf=None, errors=None):
    conf = conf or [1.0] * n
    errors = errors or {}
    sl = [DocumentSlice(slice_id=f"slice_{i:03d}", start_page=i, end_page=i, page_count=1, combined_text=f"trang {i}",
                        pages=[page(i, f"trang {i}", errors.get(i))], boundary_confidence=conf[i - 1], boundary_method="model",
                        ocr_errors=[errors[i]] if i in errors else []) for i in range(1, n + 1)]
    return SplitResult(source_file="x.pdf", total_pages=n, slices=sl)


# ---------- cờ "một tờ = một tài liệu" suy ra từ taxonomy ----------
def test_one_sheet_types_are_derived_from_the_taxonomy_text_not_hardcoded():
    assert load_one_sheet_types() == frozenset({"BB_LAY_MAU"})        # "Mỗi biên bản dài MỘT trang" trong mô tả BB_LAY_MAU


def test_one_sheet_types_reads_whatever_the_taxonomy_says(tmp_path):
    tx = {"classes": [{"id": "A", "description": "Mỗi phiếu dài MỘT trang, nhiều phiếu liền nhau."},
                      {"id": "B", "description": "Văn bản một trang do bên mua gửi."}, {"id": "C"}]}
    p = tmp_path / "tax.json"
    p.write_text(json.dumps(tx, ensure_ascii=False), encoding="utf-8")
    assert load_one_sheet_types(p) == frozenset({"A"})


# ---------- gộp ----------
def test_adjacent_slices_with_the_same_accepted_type_are_merged_but_different_types_are_not():
    split = one_slice_each(4)
    merged, groups = merge_same_type(split, ["PXK", "PXK", "CTCL", "CTCL"], frozenset())
    assert groups == [[0, 1], [2, 3]]
    assert [(s.start_page, s.end_page, s.page_count) for s in merged.slices] == [(1, 2, 2), (3, 4, 2)]
    assert [s.slice_id for s in merged.slices] == ["slice_001", "slice_002"]
    assert merged.slices[0].boundary_method == "model+type_merge" and merged.slices[0].combined_text.count("TIẾP THEO") == 1
    assert [p.page_number for p in merged.slices[0].pages] == [1, 2]


def test_one_sheet_types_are_never_merged():
    merged, groups = merge_same_type(one_slice_each(3), ["BB_LAY_MAU"] * 3, {"BB_LAY_MAU"})
    assert groups == [[0], [1], [2]] and len(merged.slices) == 3


def test_rejected_slices_are_never_merged_and_do_not_bridge():
    merged, groups = merge_same_type(one_slice_each(5), ["A", None, "A", "", "A"], frozenset())
    assert groups == [[0], [1], [2], [3], [4]]                         # không có bằng chứng cùng loại -> giữ nguyên
    assert merged.slices[0].boundary_method == "model"


def test_nothing_to_merge_returns_the_same_split_object():
    split = one_slice_each(2)
    merged, groups = merge_same_type(split, ["A", "B"], frozenset())
    assert merged is split and groups == [[0], [1]]


def test_merge_keeps_first_slice_confidence_and_joins_ocr_errors():
    split = one_slice_each(3, conf=[1.0, 0.8, 0.9], errors={2: "lỗi trang 2", 3: "lỗi trang 3"})
    merged, _ = merge_same_type(split, ["A", "A", "A"], frozenset())
    s = merged.slices[0]
    assert len(merged.slices) == 1 and s.boundary_confidence == 1.0 and s.ocr_errors == ["lỗi trang 2", "lỗi trang 3"] and s.page_count == 3


def test_keep_above_keeps_a_very_confident_boundary_even_if_both_sides_have_the_same_type():
    split = one_slice_each(4, conf=[1.0, 0.8, 0.995, 0.6])
    _, groups = merge_same_type(split, ["A", "A", "A", "A"], frozenset(), keep_above=0.99)
    assert groups == [[0, 1], [2, 3]]                                  # ranh giới 0,995 được giữ; 0,8 và 0,6 bị gộp
    assert merge_groups(["A", "A"], frozenset(), [1.0, 0.5], keep_above=0.99) == [[0, 1]]
    with pytest.raises(ValueError):
        merge_groups(["A", "A"], frozenset(), None, keep_above=0.99)


def test_label_count_must_match_slice_count():
    with pytest.raises(ValueError):
        merge_same_type(one_slice_each(2), ["A"], frozenset())


# ---------- phương pháp none + chính sách ----------
def test_split_document_none_is_one_slice_for_the_whole_file():
    r = split_document(doc_of("HOP DONG a", "BIEN BAN b", "c"), method="none")
    assert len(r.slices) == 1 and (r.slices[0].start_page, r.slices[0].end_page) == (1, 3) and r.slices[0].boundary_method == "none"
    assert split_document(OCRDocumentResult(file_name="e.pdf", total_pages=0, pages=[]), method="none").slices == []


def test_default_policy_is_model_plus_merge_with_the_dev_chosen_numbers():
    p = resolve_policy(None)
    assert DEFAULT_PRESET == "model+merge" and p.name == "model+merge" and not p.id_rule
    assert (p.method, p.threshold, p.merge_same_type, p.keep_above, p.flag_min) == ("model", 0.7, True, 0.99, None)
    assert resolve_policy("rule").method == "rule" and resolve_policy(p) is p
    assert set(PRESETS) == {"none", "rule", "rule_v2", "model", "model+merge", "model+merge+id", "triage"}
    with pytest.raises(ValueError):
        resolve_policy("khong_co")
    with pytest.raises(ValueError):
        SplitPolicy(method="magic")
    with pytest.raises(ValueError):
        SplitPolicy(keep_above=0.9)                                    # keep_above vô nghĩa khi không gộp


class FakeModel:
    threshold = 0.5

    def __init__(self, scores):
        self.scores, self.calls = scores, 0

    def doc_scores(self, texts):
        self.calls += 1
        assert len(texts) == len(self.scores)
        return list(self.scores)


def test_model_policy_applies_its_own_threshold_and_scores_once():
    doc = doc_of("a" * 40, "b" * 40, "c" * 40)
    m = FakeModel([NAN, 0.6, 0.8])
    r, info = split_with_policy(doc, SplitPolicy("t", "model", 0.7), m)
    assert [(s.start_page, s.end_page) for s in r.slices] == [(1, 2), (3, 3)] and r.slices[1].boundary_confidence == pytest.approx(0.8)
    assert m.calls == 1 and info.max_score == pytest.approx(0.8) and not info.flagged
    r2, _ = split_with_policy(doc, SplitPolicy("t", "model", None), FakeModel([NAN, 0.6, 0.8]))     # None -> ngưỡng của mô hình (0,5)
    assert len(r2.slices) == 3


def test_triage_policy_does_not_split_but_flags_files_with_a_high_boundary_score():
    doc = doc_of("a" * 40, "b" * 40)
    r, info = split_with_policy(doc, PRESETS["triage"], FakeModel([NAN, 0.31]))
    assert len(r.slices) == 1 and info.flagged and info.scores[1] == pytest.approx(0.31)
    _, info2 = split_with_policy(doc, PRESETS["triage"], FakeModel([NAN, 0.29]))
    assert not info2.flagged
    _, info3 = split_with_policy(doc_of("a" * 40), PRESETS["triage"], FakeModel([NAN]))              # tệp 1 trang không bao giờ bị đánh dấu
    assert not info3.flagged


def test_rule_policies_never_load_the_pair_model(monkeypatch):
    import src.splitting.learned as learned
    monkeypatch.setattr(learned, "load_default_model", lambda: (_ for _ in ()).throw(AssertionError("không được nạp mô hình")))
    for name in ("none", "rule", "rule_v2"):
        r, info = split_with_policy(doc_of("HOP DONG\n" + "x" * 80, "y" * 80), PRESETS[name])
        assert info.scores is None and r.slices
