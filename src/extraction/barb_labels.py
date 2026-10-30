"""barb_labels.py - Label guardrail cho mô hình trích xuất thực thể tiếng Việt (Nhóm 4).

Kế thừa từ Z:\\projects\\vocvach\\barb-1-ie-vi\\barb_labels.py:
GLiNER mã hóa chuỗi nhãn (LABEL STRING) bằng text encoder.
Các mô hình tiếng Việt được huấn luyện với nhãn CÓ DẤU THANH (ví dụ: 'tổ chức', 'người', 'mã số thuế').
Nếu truyền nhãn không dấu (vd: 'to_chuc') vector sẽ bị lệch và mô hình bị giảm ~35 điểm F1!
"""

import unicodedata
import warnings

ENTITY_LABELS = (
    "người", "tổ chức", "địa điểm", "ngày", "chức vụ",
    "văn bản", "sự kiện", "sản phẩm", "tác phẩm", "giải thưởng",
    "xăng dầu", "số lượng", "tiền tệ", "mã số thuế", "số tài khoản", "số điện thoại", "email",
)

RELATION_LABELS = (
    "sinh ngày", "nằm ở", "thành lập ngày", "quê quán", "qua đời ngày",
    "đặt trụ sở tại", "sáng lập", "thuộc sở hữu", "quan hệ gia đình",
    "kế nhiệm", "học tại", "phát triển bởi", "đoạt giải", "thuộc tổ chức",
    "tác giả", "giữ chức", "diễn ra tại", "ký", "đại diện", "bán cho",
)

_D = "đ"


def _fold(s: str) -> str:
    """Chuyển thành chữ thường, bỏ dấu tiếng Việt, chuẩn hóa khoảng trắng."""
    s = (s or "").strip().lower().replace(_D, "d")
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    for ch in ("_", "-"):
        s = s.replace(ch, " ")
    return " ".join(s.split())


def _plain(s: str) -> str:
    s = (s or "").strip().lower()
    for ch in ("_", "-"):
        s = s.replace(ch, " ")
    return " ".join(s.split())


def _has_diacritics(s: str) -> bool:
    return _fold(s) != _plain(s)


JSON_KEY = {c: _fold(c).replace(" ", "_") for c in ENTITY_LABELS + RELATION_LABELS}
FROM_JSON_KEY = {_fold(c): c for c in ENTITY_LABELS + RELATION_LABELS}


class LabelError(ValueError):
    """Báo lỗi khi nhãn bị mất dấu tiếng Việt."""
    pass


def check_labels(labels, kind="entity"):
    """Bảo vệ: bắt buộc nhãn tiếng Việt phải có dấu đầy đủ."""
    known = set(ENTITY_LABELS if kind == "entity" else RELATION_LABELS)
    bad = []
    for lab in labels:
        if lab in known:
            continue
        canon = FROM_JSON_KEY.get(_fold(lab))
        if canon is not None and canon != lab:
            bad.append((lab, canon))
        else:
            why = []
            if not _has_diacritics(lab):
                why.append("không có dấu tiếng Việt (giảm ~35 F1)")
            if "_" in lab or "-" in lab:
                why.append("dùng '_' hoặc '-' thay vì khoảng trắng (giảm thêm ~10 F1)")
            if why:
                warnings.warn(
                    f"barb: nhãn {lab!r} {' và '.join(why)}. Hãy nhập nhãn tiếng Việt có dấu chuẩn xác.",
                    stacklevel=2,
                )
    if bad:
        lines = [f"    {a!r} -> {b!r}" for a, b in bad]
        raise LabelError(
            f"Phát hiện {len(bad)} nhãn không có dấu tiếng Việt chuẩn:\n"
            + "\n".join(lines)
            + "\n\nVui lòng sử dụng nhãn tiếng Việt có dấu đầy đủ (ví dụ: 'tổ chức' thay vì 'to_chuc')."
        )
    return list(labels)
