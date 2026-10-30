"""Kiểm thử dấu hiệu "bản khác" (T5): định danh trích bằng regex, quy tắc cùng mẫu / số hiệu khác, và chính sách `model+merge+id`."""

import numpy as np
import pytest

from src.common.contracts import OCRDocumentResult, OCRPageResult
from src.splitting.identity import ID_FEATURE_NAMES, edit_distance, identity_features, page_identity
from src.splitting.learned_id import ID_PAIR_FEATURE_NAMES, id_rule_pages, same_template_new_copy
from src.splitting.page_features import page_feat
from src.splitting.policy import PRESETS, SplitPolicy, split_with_policy
from src.splitting.type_merge import merge_groups


def _sheet(no: str, date: str = "09 tháng 02 năm 2023") -> str:
    return (f"CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nGIẤY BIÊN NHẬN THẾ CHẤP PHƯƠNG TIỆN GIAO THÔNG\nSố {no}\nNgày {date}\n"
            "Xác nhận đang nhận thế chấp và giữ bản chính giấy chứng nhận đăng ký của phương tiện\n1. Thông tin bên thế chấp\n"
            "2. Thông tin chi tiết về phương tiện\nNgười nhận ký tên ghi rõ họ tên\n" + "nội dung biên nhận thế chấp " * 4)


def _doc(texts):
    pages = [OCRPageResult(page_number=i + 1, width=0, height=0, full_text=t) for i, t in enumerate(texts)]
    return OCRDocumentResult(file_name="m.pdf", total_pages=len(pages), pages=pages)


def test_edit_distance():
    assert edit_distance("abc", "abc") == 0 and edit_distance("abc", "abd") == 1 and edit_distance("", "ab") == 2


def test_identity_has_no_value_in_repr_and_features_are_flags():
    ida, idb = page_identity(_sheet("01/2023/HD")), page_identity(_sheet("02/2023/HD"))
    assert "01/2023" not in repr(ida) and "2023hd" not in repr(ida)          # giá trị định danh không rò ra repr/log
    f = dict(zip(ID_FEATURE_NAMES, identity_features(ida, idb)))
    assert f["id_head_no_both"] == 1.0 and f["id_head_no_differ"] == 1.0 and f["id_head_date_differ"] == 0.0
    same = dict(zip(ID_FEATURE_NAMES, identity_features(ida, ida)))
    assert same["id_head_no_differ"] == 0.0 and same["id_head_no_dist"] == 0.0


def test_no_identity_means_no_comparison():
    a, b = page_identity("Trang tiếp theo\nnội dung không có định danh"), page_identity(_sheet("01/2023"))
    f = dict(zip(ID_FEATURE_NAMES, identity_features(a, b)))
    assert f["id_head_no_both"] == 0.0 and f["id_head_no_differ"] == 0.0


def test_same_template_new_copy_rule():
    t1, t2, t1b = _sheet("01/2023/HD"), _sheet("02/2023/HD"), _sheet("01/2023/HD", "10 tháng 02 năm 2023")
    pf = lambda t: (page_feat(t), page_identity(t))  # noqa: E731
    assert same_template_new_copy(pf(t1)[0], pf(t2)[0], pf(t1)[1], pf(t2)[1]) is True          # cùng mẫu, số khác
    assert same_template_new_copy(pf(t1)[0], pf(t1b)[0], pf(t1)[1], pf(t1b)[1]) is False             # cùng số (chỉ khác ngày): cùng một giấy
    other = "Điều 5. Trách nhiệm các bên\nSố 77/ABC được nhắc ở đây\n" + "điều khoản khác " * 20      # khác mẫu
    assert same_template_new_copy(pf(t1)[0], pf(other)[0], pf(t1)[1], pf(other)[1]) is False


def test_id_rule_pages_skips_first_and_blank():
    fl = id_rule_pages([_sheet("01/2023"), "", _sheet("02/2023"), _sheet("02/2023")])
    assert fl == [False, False, True, False]          # trang trống bị bỏ qua; so với trang không trống gần nhất đứng trước


class _Stub:
    threshold = 0.5

    def __init__(self, scores):
        self.s = np.array([np.nan] + list(scores[1:]), dtype=float)

    def doc_scores(self, texts):
        assert len(texts) == len(self.s)
        return self.s


def test_policy_preset_registered_but_not_default():
    from src.splitting.policy import DEFAULT_PRESET
    assert "model+merge+id" in PRESETS and PRESETS["model+merge+id"].id_rule and DEFAULT_PRESET == "model+merge"
    assert not PRESETS["model+merge"].id_rule
    with pytest.raises(ValueError):
        SplitPolicy("x", "rule", id_rule=True)


def test_policy_id_rule_adds_boundary_the_model_missed_and_merge_keeps_it():
    doc = _doc([_sheet("01/2023"), _sheet("02/2023"), _sheet("02/2023")])
    stub = _Stub([0, 0.06, 0.05])                               # mô hình cặp trang bỏ sót mọi ranh giới
    base, _ = split_with_policy(doc, PRESETS["model+merge"], stub)
    assert [(s.start_page, s.end_page) for s in base.slices] == [(1, 3)]
    res, info = split_with_policy(doc, PRESETS["model+merge+id"], stub)
    assert [(s.start_page, s.end_page) for s in res.slices] == [(1, 1), (2, 3)]
    assert res.slices[1].boundary_confidence == 1.0 and res.slices[1].boundary_method == "model"
    assert info.scores is not None and info.scores[1] == pytest.approx(0.06)      # điểm thô của mô hình không bị ghi đè trong PolicyInfo
    # lát cắt thêm bởi quy tắc có điểm 1.0 >= keep_above nên merge_groups giữ nguyên dù hai bên cùng loại
    confs = [s.boundary_confidence for s in res.slices]
    assert merge_groups(["A", "A"], set(), confs, PRESETS["model+merge+id"].keep_above) == [[0], [1]]


def test_id_rule_does_not_split_same_number_pages():
    doc = _doc([_sheet("01/2023"), _sheet("01/2023", "11 tháng 02 năm 2023")])
    res, _ = split_with_policy(doc, PRESETS["model+merge+id"], _Stub([0, 0.1]))
    assert len(res.slices) == 1


def test_feature_name_count():
    assert len(ID_PAIR_FEATURE_NAMES) == 30 + len(ID_FEATURE_NAMES) + 2
