"""gliner_fields.py - GLiNER (`src/extraction/barb_extractor.py`) + gán thực thể -> trường nghiệp vụ (Nhóm 4, T4 phương pháp 2).

Hai điểm khác bản gốc (đúng hai "bẫy" của README nhóm 4):
  1. KHÔNG đọc "4000 ký tự đầu". Với mỗi trường ta tìm các neo từ khóa ("hết ngày", "bên bán", "thuộc sở hữu"...) trong MỌI
     trang của đơn vị và chỉ đưa vào GLiNER các ĐOẠN QUANH neo (cửa sổ <= 900 ký tự, gộp phần giao nhau) cộng một cửa sổ đầu trang.
  2. GLiNER chỉ trả "ngày", "tổ chức"... chứ không biết ngày nào là hạn. Ta gán thực thể vào trường bằng từ khóa BÊN TRÁI thực thể
     (ví dụ thực thể "ngày" mà ngay trước nó là "hết"/"đến" -> ngay_het_han).

Giới hạn (nói thẳng): 10 nhãn cố định của `BarbEntityExtractor` KHÔNG có "số hiệu/số phiếu/biển số", nên các trường mã định danh
(so_giay, so_phieu, bien_so...) luôn để null (not_found) ở phương pháp này; bộ chấm sẽ tính chúng là FN. Mô hình chạy trên CPU
(GPU đang chật) và nạp một lần cho cả tiến trình. Không nạp được -> `MethodUnavailable` kèm lỗi nguyên văn.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

TEAM = Path(__file__).resolve().parents[1]
REPO = TEAM.parents[1]
for _p in (str(TEAM), str(REPO)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from eval.normalize import fold_keep_len, normalize_date, is_raw  # noqa: E402
from methods.common import (BaseMethod, MethodUnavailable, Unit, build_windows, empty_result, field_specs,  # noqa: E402
                            set_value)
from src.common.contracts import DocumentSlice  # noqa: E402
from src.extraction.barb_extractor import BarbEntityExtractor  # noqa: E402

MODEL_NAME = "belumind/barb-1-ie-vi"
_MODEL: Dict[str, Any] = {}
_LOAD_ERROR: Dict[str, str] = {}


def load_gliner_cpu(model_name: str = MODEL_NAME):
    """Nạp GLiNER lên CPU đúng một lần. Lỗi (thiếu thư viện, không có mạng/cache, hết RAM) -> MethodUnavailable với lỗi nguyên văn."""
    if model_name in _MODEL:
        return _MODEL[model_name]
    if model_name in _LOAD_ERROR:
        raise MethodUnavailable(_LOAD_ERROR[model_name])
    try:
        from gliner import GLiNER
        m = GLiNER.from_pretrained(model_name)
        try:
            m = m.to("cpu")
        except Exception:  # noqa: BLE001 - một số bản gliner không có .to
            pass
    except Exception as e:  # noqa: BLE001
        _LOAD_ERROR[model_name] = f"Không nạp được GLiNER '{model_name}': {type(e).__name__}: {e}"
        raise MethodUnavailable(_LOAD_ERROR[model_name]) from e
    _MODEL[model_name] = m
    return m


# ---- gán thực thể -> trường -----------------------------------------------------------------------
# (nhãn GLiNER, regex trên văn bản không dấu của ~70 ký tự BÊN TRÁI thực thể, chọn "first" | "last")
DATE_L = "ngày"
ORG_L = "tổ chức"
ASSIGN: Dict[str, Dict[str, Tuple[str, str, str]]] = {
    "GCN_DDK_BAN_LE_XD": {
        "ngay_het_han": (DATE_L, r"(het|den)\s*(ngay)?\s*[:,]?\s*$", "first"),
        "ngay_cap": (DATE_L, r"(,\s*$|\bcap\s+lan\s+thu\s+\w+\s*:?\s*$)", "first"),
        "ten_cua_hang": (ORG_L, r"cua\s+hang\s+ban\s+l\w+\s+x\w+\s+d\w+\s*[:,]?\s*$", "first"),
        "thuong_nhan_chu_so_huu": (ORG_L, r"thuoc\s+so\s+huu[^:]{0,30}:\s*$", "first"),
        "thuong_nhan_cung_cap": (ORG_L, r"ten\s+thuong\s+nhan\s*[:,]?\s*$", "first"),
        "co_quan_cap": (ORG_L, r"giam\s+doc\s*$", "first"),
    },
    "CC_TAP_HUAN_VC_HNH": {
        "hieu_luc_tu": (DATE_L, r"\btu\s*(ngay)?\s*[:,]?\s*$", "last"),
        "ngay_het_han": (DATE_L, r"\bden\s*(ngay)?\s*[:,]?\s*$", "last"),
        "ngay_cap": (DATE_L, r",\s*$", "first"),
        "nam_sinh": (DATE_L, r"ngay\s+sinh\s*[:,]?\s*$", "first"),
        "ho_ten": ("người", r"ho\s+va\s+ten\s*[:,]?\s*$", "first"),
        "don_vi_cong_tac": (ORG_L, r"don\s+vi\s+cong\s+tac\s*[:,]?\s*$", "first"),
        "don_vi_cap": (ORG_L, r"\bdo\s*$", "first"),
    },
    "HD_MUA_BAN": {
        "ngay_ky": (DATE_L, r"hom\s+nay\s*,?\s*$", "first"),
        "ben_ban": (ORG_L, r"ben\s+(ban|a)[^:\n]{0,25}:\s*$", "first"),
        "ben_mua": (ORG_L, r"ben\s+(mua|b)[^:\n]{0,25}:\s*$", "first"),
        "hieu_luc_den": (DATE_L, r"hieu\s+luc[^.\n]{0,60}\bden\s*(het)?\s*(ngay)?\s*$", "first"),
        "hieu_luc_tu": (DATE_L, r"hop\s+dong[^.\n]{0,20}hieu\s+luc\s+tu\s*(ngay)?\s*$", "first"),
        "mat_hang": ("xăng dầu", r"", "first"),
    },
    "PHIEU_XUAT_KHO": {
        "ngay_xuat": (DATE_L, r"^\s*ngay\s*:\s*$|\bngay\s*:\s*$", "first"),
        "ben_giao": (ORG_L, r"ben\s+giao\s*:\s*$", "first"),
        "ben_nhan": (ORG_L, r"ben\s+nhan\s*:\s*$", "first"),
        "mat_hang": ("xăng dầu", r"", "first"),
    },
}
# trường số lượng: gán theo đơn vị nằm trong văn bản thực thể "số lượng"
QUANTITY = {"so_luong_tan": r"\btan\b|\bmt\b", "so_luong_m3_15c": r"m3.*15|15.*m3", "so_luong_m3_thuc_te": r"m3"}
_MST_AFTER = re.compile(r"ma\s*so\s*thue\s*[:：]*\s*(\d{10}(?:\s*-\s*\d{3})?)")


class GlinerFields(BaseMethod):
    """GLiNER + gán thực thể vào trường bằng từ khóa bên trái. Chạy trên mọi nguồn văn bản."""

    name = "gliner_fields"

    def __init__(self, source: str = "ocr_v2", store_personal_ids: bool = False, model: Any = None) -> None:
        super().__init__(source, store_personal_ids)
        self._model = model
        self._extractor: Optional[BarbEntityExtractor] = None

    def _get_extractor(self) -> BarbEntityExtractor:
        if self._extractor is None:
            self._extractor = BarbEntityExtractor(model=self._model or load_gliner_cpu())
        return self._extractor

    def entities(self, unit: Unit, pages: Dict[int, str]) -> List[Dict[str, Any]]:
        """Chạy BarbEntityExtractor trên các cửa sổ; trả [{label,text,score,page,start,end,win_text}] với chỉ số trong văn bản trang."""
        ex = self._get_extractor()
        found: List[Dict[str, Any]] = []
        for (pg, a, b) in build_windows(pages):
            text = pages[pg][a:b]
            if not text.strip():
                continue
            res = ex.extract(DocumentSlice(slice_id=f"{unit.unit_id}:{pg}:{a}", start_page=pg, end_page=pg, page_count=1, combined_text=text),
                             unit.doc_type)
            if res.status != "ok":
                raise MethodUnavailable(f"GLiNER lỗi trên cửa sổ: {res.error}")
            for e in res.entities:
                found.append({"label": e.label, "text": e.text, "score": e.confidence, "page": pg,
                              "start": a + (e.start_char or 0), "end": a + (e.end_char or 0)})
        # bỏ trùng (cửa sổ giao nhau)
        uniq, seen = [], set()
        for e in found:
            k = (e["page"], e["start"], e["end"], e["label"])
            if k not in seen:
                seen.add(k)
                uniq.append(e)
        return uniq

    def _extract(self, unit: Unit, pages: Dict[int, str]) -> Dict[str, Dict[str, Any]]:
        ents = self.entities(unit, pages)
        folded = {p: fold_keep_len(t) for p, t in pages.items()}
        out = empty_result(unit.doc_type)
        rules = ASSIGN.get(unit.doc_type, {})
        specs = {s["name"]: s for s in field_specs(unit.doc_type)}
        for fname, (label, left_rx, pick) in rules.items():
            if fname not in specs:
                continue
            rx = re.compile(left_rx, re.I) if left_rx else None
            cands = []
            for e in ents:
                if e["label"] != label:
                    continue
                left = folded[e["page"]][max(0, e["start"] - 70): e["start"]]
                if rx is not None and not rx.search(left):
                    continue
                if specs[fname]["type"] == "date":
                    nd = normalize_date(e["text"])
                    if is_raw(nd) or len(nd or "") != 10:       # chỉ ngày đầy đủ
                        continue
                cands.append(e)
            if not cands:
                continue
            e = cands[-1] if pick == "last" else sorted(cands, key=lambda x: (x["page"], x["start"]))[0]
            val = e["text"]
            if specs[fname]["type"] == "text" and fname in {"ben_ban", "ben_mua", "thuong_nhan_chu_so_huu"}:
                tail = folded[e["page"]][e["end"]: e["end"] + 260]
                m = _MST_AFTER.search(tail)
                if m:
                    val = f"{val}; MST {re.sub(r'[^0-9-]', '', m.group(1)).replace('-', '')}"
            set_value(out, specs[fname], val, page=e["page"], confidence=round(float(e["score"]), 3))
        # số lượng theo đơn vị trong văn bản thực thể
        for fname, urx in QUANTITY.items():
            if fname not in specs or unit.doc_type != "PHIEU_XUAT_KHO":
                continue
            for e in ents:
                if e["label"] == "số lượng" and re.search(urx, fold_keep_len(e["text"])) and re.search(r"\d", e["text"]):
                    set_value(out, specs[fname], e["text"], page=e["page"], confidence=round(float(e["score"]), 3))
                    break
        return out
