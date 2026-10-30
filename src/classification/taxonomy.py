"""taxonomy.py - Nạp danh mục (taxonomy) các lớp tài liệu cho bộ phân loại (Nhóm 3).

Ưu tiên đọc `data/taxonomy_v2.json`; nếu chưa có thì dùng 19 tên thư mục kế thừa (legacy).
Schema của tệp taxonomy:
    {"version": "2.0", "classes": [
        {"id": "GCN_DKKD", "name_vi": "...", "description": "...",
         "keywords": ["..."], "legacy_folders": ["..."]}]}
- `id` là nhãn đầu ra; `description` là tiêu chí gửi cho Kev; `keywords` là mẫu cho cổng luật (rule gate);
- `legacy_folders` ánh xạ tên thư mục cũ -> id để đánh giá trên dữ liệu gán nhãn cũ.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_TAXONOMY_PATH = PROJECT_ROOT / "data" / "taxonomy_v2.json"

# Danh mục 19 nhãn chuẩn kế thừa (tên thư mục mẫu) - dùng khi chưa có taxonomy_v2.json
CATEGORIES_19 = [
    "10. GCN VC HNH",
    "5. TỔNG HỢP HỒ SƠ XE",
    "6. CUA HANG - BB MAU- VÂN",
    "6. HOP DONG MUON BON",
    "6. HOP DONG THUE KHO- Vi",
    "8. CUA HANG - TU K.TRA PCCC- VÂN",
    "8. GCN Lop dao tao van chuyen hang chay no",
    "9. TỔNG HỢP HỒ SƠ CỬA HÀNG",
    "TU K.TRA PCCC- VÂN",
    "_1. Giay DKKD khach hang",
    "_1. HOP DONG DAI LY NHUONG QUYEN",
    "_2. Giay Du Dieu Kien Khach hang",
    "_2. HOP DONG KINH TE",
    "_3. HOP DONG DAU VAO-Diem",
    "_4. THANH LÝ HỢP ĐỒNG",
    "_5. HOP DONG VAN CHUYEN",
    "_Biên bản giao nhận 2026",
    "_PHIẾU XUẤT KHO MUA HÀNG 2026",
    "_Đơn đặt hàng - mua vào 2026",
]

# Từ khóa tiêu đề cho cổng luật ở chế độ legacy. Viết sao cũng được (sẽ được chuẩn hóa bỏ dấu khi so khớp).
# Chỉ lấy từ chính tên lớp / các luật cũ, KHÔNG tinh chỉnh theo dữ liệu đánh giá.
# Lưu ý: hai lớp PCCC dưới đây dùng chung từ khóa vì không thể phân biệt bằng văn bản -> cổng luật sẽ báo mơ hồ.
# Hai lớp "TỔNG HỢP HỒ SƠ" là gói tài liệu hỗn hợp nên không có luật tiêu đề.
LEGACY_KEYWORDS: Dict[str, List[str]] = {
    "_1. Giay DKKD khach hang": ["đăng ký doanh nghiệp", "đăng ký kinh doanh"],
    "_2. Giay Du Dieu Kien Khach hang": ["đủ điều kiện kinh doanh xăng dầu", "đủ điều kiện kinh doanh"],
    "_PHIẾU XUẤT KHO MUA HÀNG 2026": ["phiếu xuất kho"],
    "_Đơn đặt hàng - mua vào 2026": ["đơn đặt hàng"],
    "_4. THANH LÝ HỢP ĐỒNG": ["thanh lý hợp đồng"],
    "6. HOP DONG MUON BON": ["hợp đồng mượn bồn"],
    "6. HOP DONG THUE KHO- Vi": ["hợp đồng thuê kho"],
    "10. GCN VC HNH": ["vận chuyển hàng hóa nguy hiểm"],
    "8. GCN Lop dao tao van chuyen hang chay no": ["đào tạo vận chuyển hàng cháy nổ"],
    "TU K.TRA PCCC- VÂN": ["tự kiểm tra pccc"],
    "8. CUA HANG - TU K.TRA PCCC- VÂN": ["tự kiểm tra pccc"],
    "_Biên bản giao nhận 2026": ["biên bản giao nhận"],
    "_1. HOP DONG DAI LY NHUONG QUYEN": ["hợp đồng đại lý", "nhượng quyền"],
    "_5. HOP DONG VAN CHUYEN": ["hợp đồng vận chuyển"],
    "_3. HOP DONG DAU VAO-Diem": ["hợp đồng đầu vào"],
    "_2. HOP DONG KINH TE": ["hợp đồng kinh tế"],
    "6. CUA HANG - BB MAU- VÂN": ["biên bản lấy mẫu"],
}


@dataclass
class TaxonomyClass:
    """Một lớp tài liệu trong taxonomy."""
    id: str
    name_vi: str = ""
    description: str = ""
    keywords: List[str] = field(default_factory=list)
    legacy_folders: List[str] = field(default_factory=list)

    @property
    def criteria_text(self) -> str:
        """Văn bản tiêu chí gửi cho Kev (ưu tiên description, rồi tên, rồi id)."""
        return self.description or self.name_vi or f"Tài liệu loại {self.id}"


@dataclass
class Taxonomy:
    """Tập các lớp + nguồn gốc (để báo cáo/ghi log trung thực taxonomy nào đang dùng)."""
    classes: List[TaxonomyClass]
    version: str = "legacy-19"
    source: str = "builtin_legacy_19"

    @property
    def class_ids(self) -> List[str]:
        return [c.id for c in self.classes]

    @property
    def legacy_to_id(self) -> Dict[str, str]:
        """Ánh xạ tên thư mục cũ -> id lớp (đầy đủ cho chế độ legacy, theo `legacy_folders` cho taxonomy v2)."""
        mapping: Dict[str, str] = {}
        for c in self.classes:
            for folder in c.legacy_folders:
                mapping[folder] = c.id
        return mapping


def legacy_taxonomy() -> Taxonomy:
    """Taxonomy kế thừa: 19 tên thư mục, id = tên thư mục."""
    classes = [
        TaxonomyClass(
            id=cat,
            name_vi=cat,
            description=f"Tài liệu loại {cat}",
            keywords=list(LEGACY_KEYWORDS.get(cat, [])),
            legacy_folders=[cat],
        )
        for cat in CATEGORIES_19
    ]
    return Taxonomy(classes=classes)


def load_taxonomy_file(path: Union[str, Path]) -> Taxonomy:
    """Đọc taxonomy từ JSON. Tệp hỏng/sai schema -> ValueError (không lặng lẽ quay về legacy)."""
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ValueError(f"Không đọc được taxonomy {path}: {e}") from e

    items = raw.get("classes") if isinstance(raw, dict) else None
    if not isinstance(items, list) or not items:
        raise ValueError(f"Taxonomy {path} thiếu danh sách 'classes' hợp lệ")

    classes: List[TaxonomyClass] = []
    seen = set()
    for i, item in enumerate(items):
        if not isinstance(item, dict) or not str(item.get("id", "")).strip():
            raise ValueError(f"Taxonomy {path}: lớp thứ {i} thiếu 'id'")
        cid = str(item["id"]).strip()
        if cid in seen:
            raise ValueError(f"Taxonomy {path}: id trùng lặp '{cid}'")
        seen.add(cid)
        classes.append(
            TaxonomyClass(
                id=cid,
                name_vi=str(item.get("name_vi", "")),
                description=str(item.get("description", "")),
                keywords=[str(k) for k in item.get("keywords", []) or []],
                legacy_folders=[str(f) for f in item.get("legacy_folders", []) or []],
            )
        )
    return Taxonomy(classes=classes, version=str(raw.get("version", "")), source=str(path))


def load_taxonomy(path: Optional[Union[str, Path]] = None) -> Taxonomy:
    """Nạp taxonomy: `path` nếu truyền vào (bắt buộc phải tồn tại), ngược lại data/taxonomy_v2.json nếu có, else legacy 19."""
    if path is not None:
        return load_taxonomy_file(path)
    if DEFAULT_TAXONOMY_PATH.exists():
        return load_taxonomy_file(DEFAULT_TAXONOMY_PATH)
    return legacy_taxonomy()
