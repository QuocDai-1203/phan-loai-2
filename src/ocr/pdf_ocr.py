"""pdf_ocr.py - OCR một tệp PDF bằng engine đã chốt (VietOCR) và trả `OCRDocumentResult` đúng hợp đồng.

Chuyển nguyên văn từ `scripts/build_ocr_dataset.py` (quy tắc dùng text layer, xử lý từng trang, ghi nhận lỗi). Mỗi trang ghi rõ
`source`, `ocr_engine`, `mean_conf`, `error`, `flags`; lỗi KHÔNG bao giờ bị nuốt: trang lỗi có `error` khác None và `full_text` rỗng.

Quy tắc dùng text layer (một trang được coi là TIN CẬY khi thoả đồng thời):
  1. có >= MIN_LETTERS (30) chữ cái trong lớp chữ;
  2. chữ HIỂN THỊ (không phải render mode 3 / vô hình) chiếm >= 50% số ký tự (lớp OCR của máy scan là chữ vô hình);
  3. trang KHÔNG phải một ảnh phủ >= 80% diện tích kèm lớp chữ (dấu hiệu máy scan/CamScanner nhúng OCR kém);
  4. tỉ lệ ký tự rác (U+FFFD, vùng private-use U+E000-F8FF, ký tự điều khiển) < 2%.
  Trang có lớp chữ nhưng không đạt => `source = "embedded_ocr_layer+ocr"` (bỏ lớp chữ, OCR lại ảnh).
  Trang không có lớp chữ => `source = "ocr"`.  Trang đạt => `source = "text_layer"`.
"""
from __future__ import annotations

import re
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.common.contracts import OCRDocumentResult, OCRPageResult
from src.ocr.page_heuristics import detect_keyword_flags

MIN_LETTERS = 30
FULLPAGE_IMG = 0.80
MIN_VISIBLE_SHARE = 0.50
MAX_GARBAGE = 0.02
DEFAULT_DPI = 200
DEFAULT_MAX_PAGES = 30
# Trang ma engine ap xoay (flag `rotated_*`) nhung chi ra < ngưỡng ký tự: xoay do mot vet den cua may scan/vai ky tu rac bi hieu la
# "dong chu dung" (T2, 05_rotation/RESULTS.md: 8/8 trang gan trong bi xoay nham co 3-7 ky tu, con 40 trang xoay thang deu >= 169).
# Cac trang do duoc coi la TRANG TRONG: bo ket qua, ghi co `rotation_rejected_low_text:<do>` + `empty_text`.  0/None = tat (nhu ocr_v2.jsonl).
DEFAULT_MIN_CHARS_FOR_ROTATION = 30

_WS = re.compile(r"[ \t\r\f\v]+")


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def clean_text(s: str) -> str:
    """NFC, bỏ khoảng trắng thừa cuối dòng, gộp dòng trống liên tiếp (giữ ngắt dòng)."""
    s = nfc(s).replace("\r\n", "\n").replace("\r", "\n")
    lines = [_WS.sub(" ", ln).strip() for ln in s.split("\n")]
    out, blank = [], 0
    for ln in lines:
        if ln:
            out.append(ln)
            blank = 0
        else:
            blank += 1
            if blank == 1 and out:
                out.append("")
    return "\n".join(out).strip()


def assess_text_layer(page) -> dict:
    """Trả về {trusted: bool, reason: str, text: str, n_letters, ...}. Xem quy tắc ở docstring đầu tệp."""
    import fitz
    text = nfc(page.get_text("text") or "")
    letters = sum(1 for c in text if c.isalpha())
    res = dict(text=text, n_letters=letters, trusted=False, reason="")
    if letters == 0 and not text.strip():
        res["reason"] = "no_text_layer"
        return res
    vis = invis = 0
    try:
        for sp in page.get_texttrace():
            n = len(sp.get("chars", ()))
            if sp.get("type") == 3 or sp.get("opacity", 1) == 0:
                invis += n
            else:
                vis += n
    except Exception:
        pass
    area = page.rect.width * page.rect.height
    cov = 0.0
    try:
        for info in page.get_image_info():
            r = fitz.Rect(info["bbox"]) & page.rect
            cov += r.width * r.height
    except Exception:
        pass
    cov = min(cov / area, 1.0) if area else 0.0
    garbage = sum(1 for c in text if c == "�" or "" <= c <= "" or (ord(c) < 32 and c not in "\n\t\r"))
    gshare = garbage / max(len(text), 1)
    res.update(vis=vis, invis=invis, img_cov=cov, garbage=gshare)
    if letters < MIN_LETTERS:
        res["reason"] = f"too_few_letters({letters})"
    elif vis + invis and vis / (vis + invis) < MIN_VISIBLE_SHARE:
        res["reason"] = "invisible_text(render_mode_3)"
    elif cov >= FULLPAGE_IMG:
        res["reason"] = f"fullpage_image({cov:.2f})+text"
    elif gshare >= MAX_GARBAGE:
        res["reason"] = f"garbage_chars({gshare:.2f})"
    else:
        res["trusted"] = True
        res["reason"] = "ok"
    return res


def render(page, dpi):
    import cv2
    import numpy as np
    pix = page.get_pixmap(dpi=dpi, alpha=False)
    a = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)
    return cv2.cvtColor(a, cv2.COLOR_RGB2BGR) if pix.n == 3 else cv2.cvtColor(a, cv2.COLOR_GRAY2BGR)


@dataclass
class PageOutcome:
    """Kết quả một trang ở dạng "bản ghi" (cùng các khóa với một trang trong data/ocr_v2.jsonl) + kích thước để dựng hợp đồng."""
    page: int
    source: Optional[str] = None
    engine: Optional[str] = None
    dpi: Optional[int] = None
    text: str = ""
    n_chars: int = 0
    mean_conf: Optional[float] = None
    seconds: float = 0.0
    error: Optional[str] = None
    flags: List[str] = field(default_factory=list)
    embedded_layer_rejected: Optional[str] = None
    width: int = 0
    height: int = 0

    def to_record(self) -> Dict[str, Any]:
        """Đúng khóa và thứ tự khóa của bản ghi trang trong ocr_v2.jsonl (`flags`/`embedded_layer_rejected` chỉ có khi có giá trị)."""
        pg: Dict[str, Any] = dict(page=self.page, source=self.source, engine=self.engine, dpi=self.dpi, text=self.text,
                                  n_chars=self.n_chars, mean_conf=self.mean_conf, seconds=self.seconds, error=self.error)
        if self.flags:
            pg["flags"] = list(self.flags)
        if self.embedded_layer_rejected is not None:
            pg["embedded_layer_rejected"] = self.embedded_layer_rejected
        return pg

    def to_contract(self) -> OCRPageResult:
        flags = list(self.flags)
        if self.embedded_layer_rejected is not None:
            flags.append(f"embedded_layer_rejected:{self.embedded_layer_rejected}")
        seal, sig = detect_keyword_flags(self.text) if self.text else (False, False)
        return OCRPageResult(
            page_number=self.page, width=self.width, height=self.height, full_text=self.text, boxes=[],
            has_header_seal=seal, has_signature_box=sig, ocr_engine=self.engine or "none",
            source=self.source or "ocr", error=self.error, mean_conf=self.mean_conf, flags=flags)


def ocr_page(page, pno: int, engine, dpi: int = DEFAULT_DPI,
             min_chars_for_rotation: Optional[int] = DEFAULT_MIN_CHARS_FOR_ROTATION) -> PageOutcome:
    """OCR một trang (pno đếm từ 0). Không raise: mọi lỗi nằm trong `error` của kết quả.

    `min_chars_for_rotation`: nếu engine tự xoay trang (flag `rotated_*`) nhưng văn bản sau xoay ngắn hơn ngưỡng này thì bỏ văn bản
    (trang gần trống), thay flag xoay bằng `rotation_rejected_low_text:<độ>`. Trang bình thường (>= ngưỡng ký tự, hoặc không xoay) không đổi."""
    import fitz
    t0 = time.perf_counter()
    scale = dpi / 72.0
    try:
        w, h = int(round(page.rect.width * scale)), int(round(page.rect.height * scale))
    except Exception:
        w = h = 0
    pg = PageOutcome(page=pno + 1, width=w, height=h)
    try:
        tl = assess_text_layer(page)
        if tl["trusted"]:
            pg.source, pg.engine, pg.dpi = "text_layer", f"pymupdf-{fitz.VersionBind}/get_text", None
            pg.text = clean_text(tl["text"])
        else:
            img = render(page, dpi)
            text, conf, flags = engine.ocr(img)
            pg.source = "embedded_ocr_layer+ocr" if tl["text"].strip() else "ocr"
            pg.engine, pg.dpi, pg.text, pg.mean_conf = engine.name, dpi, clean_text(text), conf
            pg.flags = list(flags)
            if min_chars_for_rotation and len(pg.text) < min_chars_for_rotation:
                rot = [f for f in pg.flags if f.startswith("rotated_")]
                if rot:
                    pg.flags = [f for f in pg.flags if not f.startswith("rotated_")] + [f"rotation_rejected_low_text:{rot[0].split('_')[1]}"]
                    pg.text, pg.mean_conf = "", None
            if pg.source == "embedded_ocr_layer+ocr":
                pg.embedded_layer_rejected = tl["reason"]
        if not pg.text:
            pg.flags.append("empty_text")
    except Exception as e:  # noqa: BLE001  - lỗi được GHI NHẬN, không nuốt
        pg.error = f"{type(e).__name__}: {e}"
    pg.n_chars = len(pg.text)
    pg.seconds = round(time.perf_counter() - t0, 3)
    return pg


def ocr_pdf_pages(path, engine, dpi: int = DEFAULT_DPI, max_pages: int = DEFAULT_MAX_PAGES,
                  min_chars_for_rotation: Optional[int] = DEFAULT_MIN_CHARS_FOR_ROTATION) -> Tuple[int, List[PageOutcome]]:
    """-> (tổng số trang của tệp, kết quả các trang đã xử lý (tối đa max_pages)). Tệp không mở được -> ném ValueError("open_failed: ...")."""
    import fitz
    try:
        doc = fitz.open(str(path))
    except Exception as e:  # tệp hỏng
        raise ValueError(f"open_failed: {type(e).__name__}: {e}") from e
    try:
        n = len(doc)
        return n, [ocr_page(doc[i], i, engine, dpi, min_chars_for_rotation) for i in range(min(n, max_pages))]
    finally:
        doc.close()


def ocr_pdf(path, engine=None, dpi: int = DEFAULT_DPI, max_pages: int = DEFAULT_MAX_PAGES,
            min_chars_for_rotation: Optional[int] = DEFAULT_MIN_CHARS_FOR_ROTATION) -> OCRDocumentResult:
    """OCR cả tệp PDF -> `OCRDocumentResult`. `engine=None` dùng engine mặc định chung (CPU; truyền engine riêng để chọn GPU).
    Tệp dài hơn `max_pages`: chỉ các trang đầu có mặt trong `pages` (so `len(pages)` với `total_pages` để biết bị cắt)."""
    t0 = time.perf_counter()
    path = Path(path)
    if engine is None:
        from src.ocr.vietocr_engine import get_default_engine
        engine = get_default_engine()
    try:
        total, outs = ocr_pdf_pages(path, engine, dpi, max_pages, min_chars_for_rotation)
    except ValueError as e:
        return OCRDocumentResult(file_name=path.name, total_pages=0, pages=[], error=str(e),
                                 processing_time_ms=(time.perf_counter() - t0) * 1000)
    pages = [o.to_contract() for o in outs]
    errs = [f"Trang {o.page}: {o.error}" for o in outs if o.error]
    return OCRDocumentResult(file_name=path.name, total_pages=total, pages=pages, error="; ".join(errs) or None,
                             processing_time_ms=(time.perf_counter() - t0) * 1000)
