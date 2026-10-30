"""ocrlib.py - ham dung chung cho bake-off: chuan hoa, metric, sap xep dong, degrade, boc cac engine.

Moi engine tra ve  list[(box4pts, text, conf)]  tren anh BGR (numpy).  Cac engine duoc nap lazy
de mot engine loi cai dat khong lam hong cac engine khac.
"""
from __future__ import annotations
import re, time, unicodedata
import numpy as np
import cv2
from rapidfuzz.distance import Levenshtein
import os

# Gioi han so luong tu onnxruntime (mac dinh = so core = 64 -> tranh nhau khi chay nhieu tien trinh)
_ORT_THREADS = int(os.environ.get("OCR_ORT_THREADS", "6"))
try:
    import onnxruntime as _ort
    _OrigSO = _ort.SessionOptions

    def _SessionOptions():
        o = _OrigSO()
        o.intra_op_num_threads = _ORT_THREADS
        o.inter_op_num_threads = 1
        return o
    _ort.SessionOptions = _SessionOptions
except Exception:  # pragma: no cover
    pass

# ---------------------------------------------------------------- chuan hoa / metric
_WS = re.compile(r"\s+")


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def norm(s: str) -> str:
    """NFC + gop moi khoang trang thanh 1 dau cach."""
    return _WS.sub(" ", nfc(s)).strip()


def strip_diacritics(s: str) -> str:
    """Bo dau thanh/dau mu (giu chu D-gach: dong nhat 'đ'->'d')."""
    s = nfc(s).replace("đ", "d").replace("Đ", "D")
    return unicodedata.normalize("NFC", "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c)))


def is_accented(c: str) -> bool:
    """Ky tu co dau tieng Viet: sau khi tach NFD con dau ket hop, hoac la đ/Đ."""
    if c in "đĐ":
        return True
    return any(unicodedata.combining(x) for x in unicodedata.normalize("NFD", c))


def cer(ref: str, hyp: str) -> float:
    return Levenshtein.distance(ref, hyp) / max(len(ref), 1)


def wer(ref: str, hyp: str) -> float:
    r, h = ref.split(), hyp.split()
    return Levenshtein.distance(r, h) / max(len(r), 1)


def diac_recall(ref: str, hyp: str) -> float:
    """Ty le ky tu co dau trong GT duoc tai tao lai (so sanh theo tui ky tu, khong phu thuoc thu tu):
    sum_c min(count_ref(c), count_hyp(c)) / sum_c count_ref(c)  voi c la ky tu co dau."""
    from collections import Counter
    cr = Counter(c for c in ref if is_accented(c))
    ch = Counter(c for c in hyp if is_accented(c))
    tot = sum(cr.values())
    if tot == 0:
        return float("nan")
    return sum(min(v, ch.get(k, 0)) for k, v in cr.items()) / tot


def bag_f1(ref: str, hyp: str) -> float:
    """F1 theo tui tu (bo qua thu tu), so khop chinh xac sau NFC."""
    from collections import Counter
    cr, ch = Counter(ref.split()), Counter(hyp.split())
    ov = sum((cr & ch).values())
    if not ov:
        return 0.0
    p, r = ov / sum(ch.values()), ov / sum(cr.values())
    return 2 * p * r / (p + r)


def all_metrics(gt: str, hyp: str) -> dict:
    """Tat ca metric tinh KHONG phan biet hoa/thuong (casefold) vi mot so PDF born-digital luu chu thuong trong text layer
    nhung HIEN THI chu hoa (CSS text-transform / small caps) - OCR doc dung nhung bi tinh sai. `cer_cs` giu ban co phan biet."""
    g0, h0 = norm(gt), norm(hyp)
    g, h = nfc(g0.casefold()), nfc(h0.casefold())
    gn, hn = strip_diacritics(g), strip_diacritics(h)
    return dict(
        cer=cer(g, h), wer=wer(g, h),
        cer_nodiac=cer(gn, hn),
        cer_nospace=cer(g.replace(" ", ""), h.replace(" ", "")),
        diac_recall=diac_recall(g, h), bag_f1=bag_f1(g, h),
        cer_cs=cer(g0, h0), tok_ratio=len(h.split()) / max(len(g.split()), 1),
        n_gt=len(g), n_hyp=len(h),
    )


# ---------------------------------------------------------------- sap xep theo dong (dung chung cho GT va engine)
def boxes_to_text(items) -> str:
    """items: list[(x0,y0,x1,y1,text)] -> chuoi: gom dong theo toa do y (dung sai 0.6*chieu cao dong), trong dong sap theo x."""
    items = [i for i in items if i[4] and i[4].strip()]
    if not items:
        return ""
    items = sorted(items, key=lambda t: (t[1] + t[3]) / 2)
    rows, cur = [], [items[0]]
    for it in items[1:]:
        yc = (it[1] + it[3]) / 2
        ref_yc = np.mean([(c[1] + c[3]) / 2 for c in cur])
        hh = np.median([c[3] - c[1] for c in cur])
        if abs(yc - ref_yc) <= 0.6 * max(hh, 1):
            cur.append(it)
        else:
            rows.append(cur); cur = [it]
    rows.append(cur)
    lines = [" ".join(t[4].strip() for t in sorted(r, key=lambda t: t[0])) for r in rows]
    return "\n".join(lines)


def poly_to_rect(p):
    p = np.asarray(p, dtype=float).reshape(-1, 2)
    return p[:, 0].min(), p[:, 1].min(), p[:, 0].max(), p[:, 1].max()


def result_to_text(res) -> str:
    return boxes_to_text([(*poly_to_rect(b), t) for b, t, _ in res])


def gt_words_text(page) -> str:
    """Ground truth tu text layer, sap xep hinh hoc cung cach: moi tu -> (x0,y0,x1,y1,w); gom dong nhu tren."""
    words = page.get_text("words")
    return boxes_to_text([(w[0], w[1], w[2], w[3], w[4]) for w in words])


# ---------------------------------------------------------------- degrade
def degrade(img_bgr: np.ndarray, seed: int) -> np.ndarray:
    """Mo phong anh scan/chup dien thoai. Co dinh seed -> tai lap duoc.
    1) xoay nhe |goc|<=2 do, 2) blur Gauss sigma 0.8-1.4, 3) giam tuong phan (alpha 0.6-0.8) + lech sang,
    4) nhieu Gauss sigma 6-10, 5) JPEG q=40."""
    rng = np.random.default_rng(seed)
    h, w = img_bgr.shape[:2]
    ang = float(rng.uniform(-2, 2))
    M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1.0)
    out = cv2.warpAffine(img_bgr, M, (w, h), flags=cv2.INTER_LINEAR, borderValue=(255, 255, 255))
    out = cv2.GaussianBlur(out, (0, 0), float(rng.uniform(0.8, 1.4)))
    alpha, beta = float(rng.uniform(0.6, 0.8)), float(rng.uniform(10, 40))
    out = np.clip(out.astype(np.float32) * alpha + beta, 0, 255)
    out = out + rng.normal(0, float(rng.uniform(6, 10)), out.shape)
    out = np.clip(out, 0, 255).astype(np.uint8)
    ok, buf = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, 40])
    return cv2.imdecode(buf, cv2.IMREAD_COLOR)


# ---------------------------------------------------------------- engine wrappers
class Engine:
    name = "?"
    device = "cpu"
    def __call__(self, img_bgr):  # -> list[(box, text, conf)]
        raise NotImplementedError


class RapidV1(Engine):
    name = "rapidocr_onnxruntime-1.2.3(default zh/en)"
    def __init__(self):
        from rapidocr_onnxruntime import RapidOCR
        self.o = RapidOCR()
    def __call__(self, img):
        res, _ = self.o(img)
        return [(b, t, float(s)) for b, t, s in (res or [])]


class RapidV3(Engine):
    """rapidocr >= 3. cfg: dict ten tham so -> gia tri."""
    def __init__(self, name, **params):
        from rapidocr import RapidOCR
        self.name = name
        self.o = RapidOCR(params=params)
    def __call__(self, img):
        r = self.o(img)
        if r.boxes is None or r.txts is None:
            return []
        return [(b, t, float(s)) for b, t, s in zip(r.boxes, r.txts, r.scores)]


# ---------------------------------------------------------------- PDF helpers
from pathlib import Path
CORPUS = Path(r"Z:\projects\sdh-phanloaitailieu\docs\_chot_samples_phanloaitailieu")
_IDX = {}


def pdf_index() -> dict:
    """{rel_NFC_posix: Path that su tren ddia}. Can thiet vi ten tep tren dia co the o dang NFC hoac NFD."""
    if not _IDX:
        for p in CORPUS.rglob("*"):
            if p.is_file() and p.suffix.lower() == ".pdf":
                _IDX[nfc(p.relative_to(CORPUS).as_posix())] = p
    return _IDX


def open_pdf(rel):
    import fitz
    return fitz.open(pdf_index()[nfc(rel)])


def render_page(doc, pno, dpi=200) -> np.ndarray:
    pix = doc[pno].get_pixmap(dpi=dpi, alpha=False)
    a = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)
    return cv2.cvtColor(a, cv2.COLOR_RGB2BGR) if pix.n == 3 else cv2.cvtColor(a, cv2.COLOR_GRAY2BGR)


# ---------------------------------------------------------------- detector + VietOCR
def crop_quad(img, quad):
    """Cat vung chu (4 diem) thanh dong ngang bang perspective transform (giong rapidocr)."""
    q = np.asarray(quad, dtype=np.float32).reshape(4, 2)
    w = int(max(np.linalg.norm(q[0] - q[1]), np.linalg.norm(q[2] - q[3])))
    h = int(max(np.linalg.norm(q[0] - q[3]), np.linalg.norm(q[1] - q[2])))
    w, h = max(w, 1), max(h, 1)
    dst = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    M = cv2.getPerspectiveTransform(q, dst)
    out = cv2.warpPerspective(img, M, (w, h), borderMode=cv2.BORDER_REPLICATE, flags=cv2.INTER_CUBIC)
    if h / w >= 1.5:
        out = np.rot90(out)
    return out


def expand_quad(quad, pad_x: float, pad_y: float):
    """Nong hop 4 diem doc theo canh: pad_x/pad_y la ty le chieu cao dong (tinh tu tam ra moi phia)."""
    q = np.asarray(quad, dtype=np.float32).reshape(4, 2)
    top, left = q[1] - q[0], q[3] - q[0]
    h = max(np.linalg.norm(left), 1.0)
    u = top / max(np.linalg.norm(top), 1e-6)
    v = left / max(np.linalg.norm(left), 1e-6)
    px, py = pad_x * h, pad_y * h
    return np.stack([q[0] - u * px - v * py, q[1] + u * px - v * py, q[2] + u * px + v * py, q[3] - u * px + v * py])


def needs_bgnorm(img) -> bool:
    """Giay nen mau/hoa van: do bao hoa trung vi cua trang >= 15 (phien ban dau con them 'xam trung vi < 245' nhung no lam
    tang CER tren trang scan xam/degraded nen da bo; xem RESULTS.md)."""
    small = cv2.resize(img, (0, 0), fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    return bool(np.median(hsv[:, :, 1]) >= 15)


def bg_normalize(img):
    """Chuan hoa nen: voi giay mau/hoa van (do bao hoa nen cao) lay kenh V=max(B,G,R), nguoc lai lay xam;
    sau do chia cho nen uoc luong bang closing -> nen ~trang, chu toi."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    gray = hsv[:, :, 2] if float(np.median(hsv[:, :, 1])) > 60 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    k = max(15, (min(gray.shape) // 60) | 1)
    bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    bg = cv2.GaussianBlur(bg, (0, 0), k / 3)
    out = np.clip(gray.astype(np.float32) / np.maximum(bg.astype(np.float32), 1) * 255.0, 0, 255).astype(np.uint8)
    return cv2.cvtColor(out, cv2.COLOR_GRAY2BGR)


class DetOnly:
    """Bo phat hien dong chu DB (PP-OCR) dung rapidocr v3, khong nhan dang."""
    def __init__(self, det_version="PP-OCRv5", det_type="mobile", max_side=0):
        from rapidocr import RapidOCR, OCRVersion, ModelType
        prm = {"Det.ocr_version": OCRVersion(det_version), "Det.model_type": ModelType(det_type)}
        if max_side:
            prm.update({"Det.limit_side_len": max_side, "Det.limit_type": "max"})
        self.o = RapidOCR(params=prm)
    def __call__(self, img):
        r = self.o(img, use_det=True, use_cls=False, use_rec=False)
        if r.boxes is None:
            return [], []
        return list(r.boxes), list(r.scores) if getattr(r, "scores", None) is not None else [1.0] * len(r.boxes)


class VietOCRPipe(Engine):
    def __init__(self, model="vgg_transformer", det_version="PP-OCRv5", det_type="mobile", device="cuda:0", batch=16, beam=False,
                 pad_x=0.0, pad_y=0.0, bgnorm=False, max_width=None, det_max_side=0):
        from vietocr.tool.predictor import Predictor
        from vietocr.tool.config import Cfg
        self.name = f"detector({det_version}-{det_type})+vietocr-{model}" + (f"+pad{pad_x}" if pad_x else "") + (f"+bgnorm({bgnorm})" if bgnorm else "") + (f"+w{max_width}" if max_width else "") + (f"+detmax{det_max_side}" if det_max_side else "")
        self.pad_x, self.pad_y, self.bgnorm = pad_x, pad_y, bgnorm
        self.det = DetOnly(det_version, det_type, det_max_side)
        cfg = Cfg.load_config_from_name(model)
        cfg["cnn"]["pretrained"] = False
        cfg["device"] = device
        cfg["predictor"]["beamsearch"] = beam
        if max_width:
            cfg["dataset"]["image_max_width"] = max_width
        self.device = device
        self.batch = batch
        self.p = Predictor(cfg)
    def __call__(self, img):
        from PIL import Image
        if self.bgnorm in ("auto", "sat"):
            if needs_bgnorm(img):
                img = bg_normalize(img)
        elif self.bgnorm:
            img = bg_normalize(img)
        boxes, _ = self.det(img)
        if not boxes:
            return []
        crops = [Image.fromarray(cv2.cvtColor(crop_quad(img, expand_quad(b, self.pad_x, self.pad_y) if self.pad_x else b), cv2.COLOR_BGR2RGB)) for b in boxes]
        # sap theo chieu rong de batch hieu qua (vietocr tu pad theo bucket); giu chi so goc
        out = [None] * len(crops)
        order = sorted(range(len(crops)), key=lambda i: crops[i].size[0] / max(crops[i].size[1], 1))
        for s in range(0, len(order), self.batch):
            idx = order[s:s + self.batch]
            res = self.p.predict_batch([crops[i] for i in idx], return_prob=True)
            txts, probs = res
            for i, t, pr in zip(idx, txts, probs):
                out[i] = (t, float(pr))
        return [(b, t, c) for b, (t, c) in zip(boxes, out)]


class EasyOCREng(Engine):
    def __init__(self, gpu=True):
        import easyocr
        self.name = "easyocr-" + easyocr.__version__ + "(vi,en)"
        self.device = "cuda:0" if gpu else "cpu"
        self.r = easyocr.Reader(["vi", "en"], gpu=gpu, verbose=False)
    def __call__(self, img):
        res = self.r.readtext(img, paragraph=False)
        return [(b, t, float(c)) for b, t, c in res]
