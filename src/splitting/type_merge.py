"""type_merge.py - Hiệu chỉnh tách trang NHẬN BIẾT LOẠI: gộp lát cắt liền kề mà bộ phân loại gán CÙNG một loại.

Vì sao: bộ tách (nhất là luật) hay cắt vụn một tài liệu nhiều trang; hai lát cắt liền kề cùng được nhận cùng một loại thì rất có thể
là một tài liệu (phép thử ở mục 7.2 của docs/LABELING_GUIDELINE.md: "cùng loại, cùng chủ thể, chỉ là trang tiếp theo -> không tách").
Ngoại lệ có thật: loại "một tờ = một tài liệu" (hiện chỉ `BB_LAY_MAU`: "Mỗi biên bản dài MỘT trang", nhiều biên bản liền nhau là nhiều
tài liệu cùng loại, mục 7.3/7.4) KHÔNG bị gộp. Cờ này được SUY RA từ mô tả loại trong `data/taxonomy_v2.json`, không chỉnh theo số đo.

Hàm thuần (không gọi mô hình, không đọc đĩa trừ `load_one_sheet_types`): nhận kết quả tách + nhãn đã nhận của từng lát cắt.
Lát cắt không có nhãn được nhận (bộ phân loại từ chối) KHÔNG bao giờ được gộp: không có bằng chứng cùng loại.
Số đo end-to-end: teams/00_data_and_eval/experiments/01_end_to_end/RESULTS.md.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Collection, Iterable, List, Optional, Sequence, Tuple

from src.common.contracts import DocumentSlice, SplitResult
from src.splitting.boundary_detector import _slice_text

TAXONOMY_PATH = Path(__file__).resolve().parents[2] / "data" / "taxonomy_v2.json"
# "Mỗi biên bản dài MỘT trang" (mô tả BB_LAY_MAU): mỗi tờ là một tài liệu, nhiều tờ cùng loại liền nhau KHÔNG phải một tài liệu.
ONE_SHEET_PATTERN = re.compile(r"mỗi\s+(?:\S+\s+){1,3}dài\s+một\s+trang", re.IGNORECASE)
MERGE_SUFFIX = "+type_merge"


def load_one_sheet_types(taxonomy_path: Path | str = TAXONOMY_PATH) -> frozenset:
    """Các loại mà mô tả trong taxonomy nói mỗi tài liệu chỉ dài MỘT trang (=> nhiều tờ liền nhau là nhiều tài liệu)."""
    tj = json.loads(Path(taxonomy_path).read_text(encoding="utf-8"))
    return frozenset(c["id"] for c in tj["classes"] if ONE_SHEET_PATTERN.search(c.get("description", "")))


def merge_groups(labels: Sequence[Optional[str]], one_sheet: Collection[str], confidences: Optional[Sequence[float]] = None,
                 keep_above: Optional[float] = None) -> List[List[int]]:
    """Nhóm các chỉ số lát cắt liền kề sẽ được gộp. `labels[i]` = loại đã được NHẬN của lát cắt i, hoặc None/'' nếu bị từ chối.
    `keep_above` (tùy chọn): ranh giới mở lát cắt i có `confidences[i]` >= keep_above được GIỮ dù hai bên cùng loại (bộ tách rất chắc chắn
    thì tin bộ tách; chỉ dùng được khi `confidences` là điểm của mô hình, vì cờ của luật là hằng số 0,95)."""
    if keep_above is not None and confidences is None:
        raise ValueError("keep_above cần confidences")
    groups: List[List[int]] = []
    for i, lab in enumerate(labels):
        strong = keep_above is not None and confidences[i] >= keep_above
        if groups and lab and labels[groups[-1][-1]] == lab and lab not in one_sheet and not strong:
            groups[-1].append(i)
        else:
            groups.append([i])
    return groups


def merge_same_type(split: SplitResult, labels: Sequence[Optional[str]], one_sheet: Collection[str],
                    keep_above: Optional[float] = None) -> Tuple[SplitResult, List[List[int]]]:
    """Gộp lát cắt liền kề cùng loại (trừ loại một-tờ). Trả (SplitResult mới, nhóm chỉ số lát cắt gốc của từng lát cắt mới).

    `keep_above`: xem `merge_groups` (dùng `boundary_confidence` của lát cắt làm điểm ranh giới).

    Lát cắt mới: `slice_id` đánh lại, `boundary_confidence` và `boundary_method` của lát cắt ĐẦU (thêm hậu tố `+type_merge` nếu đã gộp),
    văn bản/trang/lỗi OCR nối theo thứ tự. Không có gì để gộp thì trả lại đúng `split` ban đầu.
    """
    if len(labels) != len(split.slices):
        raise ValueError(f"cần {len(split.slices)} nhãn, nhận {len(labels)}")
    groups = merge_groups(labels, one_sheet, [s.boundary_confidence for s in split.slices] if keep_above is not None else None, keep_above)
    if len(groups) == len(split.slices):
        return split, groups
    out: List[DocumentSlice] = []
    for n, g in enumerate(groups, 1):
        parts = [split.slices[i] for i in g]
        if len(parts) == 1:
            out.append(parts[0].model_copy(update={"slice_id": f"slice_{n:03d}"}))
            continue
        pages = [p for s in parts for p in s.pages]
        out.append(DocumentSlice(
            slice_id=f"slice_{n:03d}", start_page=parts[0].start_page, end_page=parts[-1].end_page,
            page_count=sum(s.page_count for s in parts),
            combined_text=_slice_text(pages) if pages else "\n\n--- TIẾP THEO ---\n\n".join(s.combined_text for s in parts),
            pages=pages, boundary_confidence=parts[0].boundary_confidence,
            boundary_method=parts[0].boundary_method + MERGE_SUFFIX, ocr_errors=[e for s in parts for e in s.ocr_errors]))
    return SplitResult(source_file=split.source_file, total_pages=split.total_pages, slices=out,
                       processing_time_ms=split.processing_time_ms), groups
