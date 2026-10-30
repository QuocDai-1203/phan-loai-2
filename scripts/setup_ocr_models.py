"""setup_ocr_models.py - Chuẩn bị thư mục models/ocr để OCR chạy OFFLINE (xem models/README.md).

Mặc định KHÔNG dùng mạng: chỉ chép tệp đã có trên máy vào models/ocr:
  * trọng số VietOCR  : %TEMP%/vgg_seq2seq.pth (nơi thư viện vietocr tải về lần đầu)  -> models/ocr/vietocr/vgg_seq2seq.pth
  * mô hình phát hiện : <site-packages>/rapidocr/models/ch_PP-OCRv5_det_mobile.onnx   -> models/ocr/rapidocr/
Cờ tùy chọn, CHỈ chạy khi bạn chủ động gõ (cần mạng, tải từ vocr.vn):
  --download         tải trọng số VietOCR nếu chưa có
  --download-config  tải cấu hình chính thức của vietocr, so với src/ocr/configs/vgg_seq2seq.yml và in chỗ khác nhau
                     (không ghi đè tệp trong kho)

  .venv\\Scripts\\python.exe -X utf8 scripts\\setup_ocr_models.py
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.ocr.vietocr_engine import (BUNDLED_CONFIG_DIR, RAPIDOCR_DET_FILE, VIETOCR_WEIGHTS_URL,  # noqa: E402
                                    OcrModelsMissingError, models_dir, resolve_model_paths)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--models-dir", type=Path, default=None)
    ap.add_argument("--model", default="vgg_seq2seq")
    ap.add_argument("--download", action="store_true", help="tải trọng số VietOCR từ vocr.vn nếu chưa có (CẦN MẠNG)")
    ap.add_argument("--download-config", action="store_true", help="tải cấu hình chính thức để so với tệp trong kho (CẦN MẠNG)")
    a = ap.parse_args()
    root = models_dir(a.models_dir)
    w = root / "vietocr" / f"{a.model}.pth"
    det = root / "rapidocr" / RAPIDOCR_DET_FILE
    w.parent.mkdir(parents=True, exist_ok=True)
    det.parent.mkdir(parents=True, exist_ok=True)

    if not w.is_file():
        tmp = Path(tempfile.gettempdir()) / f"{a.model}.pth"
        if tmp.is_file():
            shutil.copy2(tmp, w)
            print(f"đã chép {tmp} -> {w}")
        elif a.download:
            import requests
            url = VIETOCR_WEIGHTS_URL.format(model=a.model)
            print("tải", url)
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(w, "wb") as f:
                    for c in r.iter_content(1 << 20):
                        f.write(c)
        else:
            print(f"THIẾU {w} (không có trong %TEMP%; thêm --download nếu máy có mạng, hoặc chép tay)")
    if not det.is_file():
        try:
            import rapidocr
            src = Path(rapidocr.__file__).parent / "models" / RAPIDOCR_DET_FILE
        except ImportError:
            src = Path("<chưa cài rapidocr>")
        if src.is_file():
            shutil.copy2(src, det)
            print(f"đã chép {src} -> {det}")
        else:
            print(f"THIẾU {det} và không thấy {src}: chạy một lần có mạng để rapidocr tải, hoặc chép tay")

    if a.download_config:
        from vietocr.tool.config import Cfg
        import yaml
        official = dict(Cfg.load_config_from_name(a.model))
        ours = yaml.safe_load((BUNDLED_CONFIG_DIR / f"{a.model}.yml").read_text(encoding="utf-8"))
        for k in ("vocab", "backbone", "cnn", "seq_modeling", "transformer"):
            same = official.get(k) == ours.get(k)
            print(f"  {k}: {'GIỐNG' if same else 'KHÁC <<<<<'}")
        for k in ("image_height", "image_min_width", "image_max_width"):
            same = official["dataset"].get(k) == ours["dataset"].get(k)
            print(f"  dataset.{k}: {'GIỐNG' if same else 'KHÁC <<<<<'} ({official['dataset'].get(k)} vs {ours['dataset'].get(k)})")

    try:
        p = resolve_model_paths(a.model, a.models_dir)
    except OcrModelsMissingError as e:
        print(e)
        return 1
    for name, path in (("vietocr weights", p.vietocr_weights), ("vietocr config", p.vietocr_config), ("rapidocr det", p.rapidocr_det)):
        print(f"OK {name:16s} {path}  sha256={sha256(path)[:16]}…  {path.stat().st_size/1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
