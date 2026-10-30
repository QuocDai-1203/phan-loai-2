"""vietocr_engine.py - Engine OCR đã CHỐT ở bake-off (teams/team1_ocr/experiments/01_engine_bakeoff/RESULTS.md).

Bộ phát hiện dòng chữ DB của PP-OCRv5 (rapidocr >= 3, ONNX) + bộ nhận dạng VietOCR `vgg_seq2seq` (có đủ bộ dấu tiếng Việt),
tự xoay trang 90/180 độ, chuẩn hóa nền chỉ khi giấy có màu.

Mã này được CHUYỂN NGUYÊN VĂN từ `scripts/build_ocr_dataset.py` (kết quả phải trùng `data/ocr_v2.jsonl`); script đó nay
chỉ import từ đây. Khác biệt duy nhất so với bản cũ là cách nạp mô hình để chạy OFFLINE:

  * trọng số VietOCR đọc từ `models/ocr/vietocr/<model>.pth` (không tải về %TEMP%);
  * cấu hình VietOCR đọc từ `models/ocr/vietocr/<model>.yml` nếu có, ngược lại từ bản kèm trong kho `src/ocr/configs/<model>.yml`
    (thư viện vietocr mặc định tải cấu hình từ vocr.vn mỗi lần khởi động nên không chạy được khi mất mạng);
  * mô hình phát hiện dòng của rapidocr đọc từ `models/ocr/rapidocr/ch_PP-OCRv5_det_mobile.onnx`
    (mặc định rapidocr tự tải vào `<site-packages>/rapidocr/models/`).

Thiếu tệp nào -> `OcrModelsMissingError` với hướng dẫn cụ thể (không âm thầm tải từ mạng, không âm thầm đổi engine).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

REPO = Path(__file__).resolve().parent.parent.parent
ENV_MODELS_DIR = "SDH_OCR_MODELS_DIR"
DEFAULT_MODELS_DIR = REPO / "models" / "ocr"
BUNDLED_CONFIG_DIR = Path(__file__).resolve().parent / "configs"      # cấu hình suy diễn kèm trong kho (nhỏ, có version control)

VIETOCR_MODELS = {"viet_seq2seq": "vgg_seq2seq", "viet_transformer": "vgg_transformer"}
RAPIDOCR_DET_FILE = "ch_PP-OCRv5_det_mobile.onnx"
# Địa chỉ do thư viện vietocr 0.3.13 dùng khi tải trọng số (chỉ dùng cho hướng dẫn; mã này KHÔNG tự tải).
VIETOCR_WEIGHTS_URL = "https://vocr.vn/data/vietocr/{model}.pth"


class OcrModelsMissingError(RuntimeError):
    """Thiếu tệp mô hình OCR trong thư mục models/ocr. Thông báo nêu rõ phải đặt tệp nào ở đâu."""


@dataclass(frozen=True)
class OcrModelPaths:
    models_dir: Path
    vietocr_weights: Path
    vietocr_config: Path
    rapidocr_det: Path


def models_dir(override: Optional[os.PathLike] = None) -> Path:
    if override is not None:
        return Path(override)
    env = os.environ.get(ENV_MODELS_DIR)
    return Path(env) if env else DEFAULT_MODELS_DIR


def resolve_model_paths(vietocr_model: str = "vgg_seq2seq", override: Optional[os.PathLike] = None) -> OcrModelPaths:
    """Đường dẫn các tệp mô hình; ném OcrModelsMissingError (liệt kê TẤT CẢ tệp thiếu) nếu không đủ."""
    root = models_dir(override)
    cfg_local, cfg_bundled = root / "vietocr" / f"{vietocr_model}.yml", BUNDLED_CONFIG_DIR / f"{vietocr_model}.yml"
    p = OcrModelPaths(
        models_dir=root,
        vietocr_weights=root / "vietocr" / f"{vietocr_model}.pth",
        vietocr_config=cfg_local if cfg_local.is_file() else cfg_bundled,
        rapidocr_det=root / "rapidocr" / RAPIDOCR_DET_FILE,
    )
    missing = []
    if not p.vietocr_weights.is_file():
        missing.append(f"  - {p.vietocr_weights}\n      trọng số VietOCR. Máy có mạng: `python scripts/setup_ocr_models.py --download`; "
                       f"máy không mạng: chép tệp {vietocr_model}.pth từ máy khác "
                       f"(nguồn gốc: {VIETOCR_WEIGHTS_URL.format(model=vietocr_model)}).")
    if not p.vietocr_config.is_file():
        missing.append(f"  - {cfg_local} (hoặc {cfg_bundled})\n      cấu hình suy diễn VietOCR. Kho chỉ kèm vgg_seq2seq; với mô hình khác, "
                       f"chép tệp .yml cấu hình đúng mô hình đó (lấy bằng vietocr.tool.config.Cfg.load_config_from_name rồi Cfg.save, cần mạng một lần).")
    if not p.rapidocr_det.is_file():
        missing.append(f"  - {p.rapidocr_det}\n      mô hình phát hiện dòng PP-OCRv5 của rapidocr. Chép từ "
                       f"<site-packages>/rapidocr/models/{RAPIDOCR_DET_FILE} (xuất hiện sau lần chạy đầu có mạng) bằng "
                       f"`python scripts/setup_ocr_models.py`, hoặc chép tay từ máy khác.")
    if missing:
        raise OcrModelsMissingError(
            f"Thiếu mô hình OCR trong {root} (đặt biến môi trường {ENV_MODELS_DIR} để dùng thư mục khác). "
            "Hệ thống chạy OFFLINE nên không tự tải. Tệp cần có:\n" + "\n".join(missing) +
            "\nChi tiết: models/README.md.")
    return p


# --------------------------------------------------------------------------------------- tiền xử lý ảnh
def boxes_to_text(items) -> str:
    """items: [(x0,y0,x1,y1,text)] -> chuỗi theo hàng (gom theo y, trong hàng sắp theo x)."""
    import numpy as np
    items = [i for i in items if i[4] and i[4].strip()]
    if not items:
        return ""
    items = sorted(items, key=lambda t: (t[1] + t[3]) / 2)
    rows, cur = [], [items[0]]
    for it in items[1:]:
        yc = (it[1] + it[3]) / 2
        ref = float(np.mean([(c[1] + c[3]) / 2 for c in cur]))
        hh = float(np.median([c[3] - c[1] for c in cur]))
        if abs(yc - ref) <= 0.6 * max(hh, 1):
            cur.append(it)
        else:
            rows.append(cur)
            cur = [it]
    rows.append(cur)
    return "\n".join(" ".join(t[4].strip() for t in sorted(r, key=lambda t: t[0])) for r in rows)


def needs_bgnorm(img) -> bool:
    """Giấy nền màu/hoa văn (độ bão hoà trung vị của trang >= 15/255). Ngưỡng chọn sau khi thấy kết quả bake-off:
    GCN ĐKKD nền hoa văn vàng (sat=28) valid_syl 0.58 -> 0.89, thẻ GCN nền xanh (sat=149) +0.01; trang xám/ảnh chụp
    (sat<=3) không lợi, và trang trắng bị giảm chất lượng nhẹ (CER +0.02) nên KHÔNG chuẩn hoá."""
    import cv2
    import numpy as np
    small = cv2.resize(img, (0, 0), fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    return bool(np.median(hsv[:, :, 1]) >= 15)


def bg_normalize(img):
    """Chuẩn hoá nền: giấy màu (bão hoà nền cao) lấy kênh V=max(B,G,R), ngược lại lấy xám; chia cho nền ước lượng bằng
    closing => nền ~trắng, chữ tối. Triệt hoa văn vàng của GCN ĐKKD, nền xanh của thẻ GCN. Chỉ bật khi needs_bgnorm
    (trên trang trắng sạch nó làm CER tăng ~0.03 trong bake-off)."""
    import cv2
    import numpy as np
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    gray = hsv[:, :, 2] if float(np.median(hsv[:, :, 1])) > 60 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    k = max(15, (min(gray.shape) // 60) | 1)
    bg = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    bg = cv2.GaussianBlur(bg, (0, 0), k / 3)
    out = np.clip(gray.astype(np.float32) / np.maximum(bg.astype(np.float32), 1) * 255.0, 0, 255).astype(np.uint8)
    return cv2.cvtColor(out, cv2.COLOR_GRAY2BGR)


# --------------------------------------------------------------------------------------- engine
class VietOCREngine:
    """Phát hiện dòng chữ (PP-OCRv5 det, rapidocr>=3) + nhận dạng VietOCR, có tự xoay trang 90/180 độ.

    `model`: tên VietOCR (`vgg_seq2seq` nhanh, mặc định; `vgg_transformer` chậm hơn nhiều, thường chính xác hơn - cần tự đặt
    `vgg_transformer.pth/.yml` vào models/ocr/vietocr/, kho chỉ kèm vgg_seq2seq).
    """

    def __init__(self, model: str = "vgg_seq2seq", device: str = "cpu", threads: int = 8, batch: int = 16,
                 max_width: int | None = None, det_max_side: int = 0, models_override: Optional[os.PathLike] = None):
        paths = resolve_model_paths(model, models_override)      # thiếu tệp -> lỗi rõ ràng TRƯỚC khi import torch
        import torch
        from rapidocr import ModelType, OCRVersion, RapidOCR
        from vietocr.tool.config import Cfg
        from vietocr.tool.predictor import Predictor
        import rapidocr, vietocr  # noqa: F401
        from importlib.metadata import version

        torch.set_num_threads(threads)
        self.device = device
        self.batch = batch
        self.model = model
        self.paths = paths
        det_params = {"Det.ocr_version": OCRVersion.PPOCRV5, "Det.model_type": ModelType.MOBILE,
                      "Det.model_path": str(paths.rapidocr_det),
                      "EngineConfig.onnxruntime.intra_op_num_threads": max(1, min(threads, 8))}
        if det_max_side:  # thu nhỏ ảnh cho bộ phát hiện (cắt dòng vẫn lấy từ ảnh gốc 200 dpi): nhanh hơn
            det_params.update({"Det.limit_side_len": det_max_side, "Det.limit_type": "max"})
        self.det = RapidOCR(params=det_params)
        cfg = Cfg.load_config_from_file(str(paths.vietocr_config))   # không tải gì từ mạng
        cfg["cnn"]["pretrained"] = False
        cfg["device"] = device
        cfg["weights"] = str(paths.vietocr_weights)                  # đường dẫn cục bộ: Predictor không tải
        cfg["predictor"]["beamsearch"] = False
        if max_width:
            cfg["dataset"]["image_max_width"] = max_width
        self.p = Predictor(cfg)
        self.name = (f"rapidocr-{version('rapidocr')}/PP-OCRv5_det_mobile + vietocr-{version('vietocr')}/{model}"
                     f"@{device}")

    # --- hình học
    @staticmethod
    def _crop(img, quad):
        import cv2
        import numpy as np
        q = np.asarray(quad, dtype=np.float32).reshape(4, 2)
        w = max(int(max(np.linalg.norm(q[0] - q[1]), np.linalg.norm(q[2] - q[3]))), 1)
        h = max(int(max(np.linalg.norm(q[0] - q[3]), np.linalg.norm(q[1] - q[2]))), 1)
        M = cv2.getPerspectiveTransform(q, np.float32([[0, 0], [w, 0], [w, h], [0, h]]))
        return cv2.warpPerspective(img, M, (w, h), borderMode=cv2.BORDER_REPLICATE, flags=cv2.INTER_CUBIC)

    def _detect(self, img):
        r = self.det(img, use_det=True, use_cls=False, use_rec=False)
        return [] if r.boxes is None else [b for b in r.boxes]

    def _rec(self, crops_bgr):
        """crops: list ndarray BGR (đã ngang) -> list[(text, prob)]"""
        import cv2
        from PIL import Image
        imgs = [Image.fromarray(cv2.cvtColor(c, cv2.COLOR_BGR2RGB)) for c in crops_bgr]
        out = [None] * len(imgs)
        order = sorted(range(len(imgs)), key=lambda i: imgs[i].size[0] / max(imgs[i].size[1], 1))
        for s in range(0, len(order), self.batch):
            idx = order[s:s + self.batch]
            txts, probs = self.p.predict_batch([imgs[i] for i in idx], return_prob=True)
            for i, t, pr in zip(idx, txts, probs):
                out[i] = (t, float(pr))
        return out

    def _sample_conf(self, crops):
        import numpy as np
        if not crops:
            return 0.0
        return float(np.mean([p for _, p in self._rec(crops)]))

    # --- trang
    def ocr(self, img) -> Tuple[str, Optional[float], List[str]]:
        """img BGR -> (text, mean_conf, flags). Raise nếu lỗi thật."""
        import numpy as np
        H, W = img.shape[:2]
        flags: List[str] = []
        if needs_bgnorm(img):
            img = bg_normalize(img)
            flags.append("bg_normalized")
        boxes = self._detect(img)
        if not boxes:
            return "", None, flags + ["no_boxes"]
        rects = [(float(np.asarray(b)[:, 0].min()), float(np.asarray(b)[:, 1].min()),
                  float(np.asarray(b)[:, 0].max()), float(np.asarray(b)[:, 1].max())) for b in boxes]
        # 1) trang xoay 90 độ? (đa số hộp là hộp đứng, tính theo độ dài)
        vlen = sum(max(r[2] - r[0], r[3] - r[1]) for r in rects if (r[3] - r[1]) > 1.5 * (r[2] - r[0]))
        tlen = sum(max(r[2] - r[0], r[3] - r[1]) for r in rects)
        rot = 0  # độ xoay áp lên crop: 0, 90 (ngược chiều kim đồng hồ), 270, 180
        crops = [self._crop(img, b) for b in boxes]
        if tlen and vlen / tlen > 0.6:
            # chọn hướng xoay theo độ tin cậy trên mẫu 12 dòng dài nhất
            order = sorted(range(len(crops)), key=lambda i: -max(crops[i].shape[:2]))[:12]
            cands = {90: [np.rot90(crops[i], 1) for i in order], 270: [np.rot90(crops[i], 3) for i in order]}
            scores = {k: self._sample_conf(v) for k, v in cands.items()}
            rot = max(scores, key=scores.get)
            flags.append(f"rotated_{rot}")
        if rot:
            k = {90: 1, 270: 3}[rot]
            crops = [np.rot90(c, k) for c in crops]
        else:
            # dòng nằm ngang: kiểm tra có bị lật ngược 180 độ không (lấy mẫu)
            order = sorted(range(len(crops)), key=lambda i: -crops[i].shape[1])[:10]
            base = self._sample_conf([crops[i] for i in order])
            if base < 0.80:
                flipped = self._sample_conf([np.rot90(crops[i], 2) for i in order])
                if flipped > base + 0.10:
                    rot = 180
                    crops = [np.rot90(c, 2) for c in crops]
                    flags.append("rotated_180")
        res = self._rec(crops)
        # toạ độ trong khung đã xoay để sắp xếp đọc theo hàng
        items = []
        for (x0, y0, x1, y1), (t, _) in zip(rects, res):
            if rot == 90:      # xoay trang ngược chiều kim đồng hồ: (x,y)->(y, W-x)
                items.append((y0, W - x1, y1, W - x0, t))
            elif rot == 270:   # xoay thuận chiều: (x,y)->(H-y, x)
                items.append((H - y1, x0, H - y0, x1, t))
            elif rot == 180:
                items.append((W - x1, H - y1, W - x0, H - y0, t))
            else:
                items.append((x0, y0, x1, y1, t))
        confs = [p for _, p in res if p == p]  # bỏ NaN (VietOCR trả NaN khi chuỗi rỗng)
        return boxes_to_text(items), (float(np.mean(confs)) if confs else None), flags


_DEFAULT_ENGINE: Optional[VietOCREngine] = None
_DEFAULT_KEY: Optional[tuple] = None


def get_default_engine(model: str = "vgg_seq2seq", device: str = "cpu", threads: int = 8, batch: int = 16,
                       max_width: int | None = None, det_max_side: int = 0) -> VietOCREngine:
    """Engine dùng chung trong tiến trình (nạp mô hình tốn vài giây). Đổi tham số -> dựng lại."""
    global _DEFAULT_ENGINE, _DEFAULT_KEY
    key = (model, device, threads, batch, max_width, det_max_side)
    if _DEFAULT_ENGINE is None or _DEFAULT_KEY != key:
        _DEFAULT_ENGINE = VietOCREngine(model, device, threads, batch, max_width, det_max_side)
        _DEFAULT_KEY = key
    return _DEFAULT_ENGINE
