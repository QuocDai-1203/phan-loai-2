"""rules_v2.py - Bộ luật tách trang đã sửa (Nhóm 2). Giữ NGUYÊN bản cũ ở boundary_detector.is_new_document_start.

Khác bản cũ (mỗi điểm đều có thể tắt riêng bằng RuleConfig để chạy ablation, xem teams/team2_splitting/experiments/02_rule_v2):
1. Quốc hiệu chỉ tính khi nằm trong `head_lines` dòng đầu (bản cũ: bất kỳ đâu trong trang).
2. Không tách ở trang gần như trống (< `min_chars` = 50 ký tự) hoặc chỉ có chữ ký/con dấu.
3. Không tách ở trang có đánh số "n/m" hoặc "trang n" với n >= 2 (ví dụ chữ ký "2/2").
4. Không tách ở trang ngắn lặp lại đầu trang của trang trước (tiêu đề lặp ở trang tiếp nối).
5. Tiêu đề phải mở đầu một dòng trong `head_lines` dòng đầu (bản cũ: xuất hiện ở bất kỳ vị trí nào của 6 dòng đầu).

`boundary_confidence` do các hàm gọi tạo ra là CỜ CỦA LUẬT, không phải xác suất.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from src.splitting.page_features import PageFeat, jaccard, page_feat


@dataclass(frozen=True)
class RuleConfig:
    head_lines: int = 6
    min_chars: int = 50
    use_min_chars: bool = True
    use_signature_veto: bool = True
    use_page_no_veto: bool = True
    use_repeat_header_veto: bool = True
    repeat_jaccard: float = 0.6
    repeat_len_ratio: float = 0.6
    motto_top_only: bool = True
    title_at_line_start: bool = True


DEFAULT_CONFIG = RuleConfig()


def is_start_v2(prev: PageFeat, cur: PageFeat, cfg: RuleConfig = DEFAULT_CONFIG) -> bool:
    if cfg.use_min_chars and cur.n_chars < cfg.min_chars:
        return False
    if cfg.use_signature_veto and cur.signature_only:
        return False
    if cfg.use_page_no_veto and cur.page_no and cur.page_no[0] >= 2:
        return False
    if (cfg.use_repeat_header_veto and jaccard(cur.head_tokens, prev.head_tokens) >= cfg.repeat_jaccard
            and cur.n_chars < cfg.repeat_len_ratio * max(prev.n_chars, 1)):
        return False
    motto = cur.motto_top if cfg.motto_top_only else cur.motto_any
    title = cur.title_at_line_start if cfg.title_at_line_start else cur.title_top is not None
    return bool(motto or title)


def rule_starts(texts: Sequence[str], cfg: RuleConfig = DEFAULT_CONFIG) -> List[bool]:
    """texts: văn bản từng trang theo thứ tự. Trả về cờ 'mở tài liệu mới' cho từng trang (trang 1 luôn True)."""
    feats = [page_feat(t, cfg.head_lines) for t in texts]
    return [True] + [is_start_v2(feats[i - 1], feats[i], cfg) for i in range(1, len(feats))]
