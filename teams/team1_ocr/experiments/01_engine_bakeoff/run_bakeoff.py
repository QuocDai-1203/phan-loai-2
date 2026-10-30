"""run_bakeoff.py - chay 1 engine tren 1 tap trang, ghi ket qua tho (text + thoi gian) vao _cache/raw/*.jsonl

Vi du:
  .venv/Scripts/python.exe -X utf8 run_bakeoff.py --engine rapid_v1 --set gold --dpi 200
  .venv/Scripts/python.exe -X utf8 run_bakeoff.py --engine viet_transformer --set scan --dpi 200
--set gold  : chay 2 bien the (clean, degraded) tren sample_gold_pages.csv
--set scan  : chay tren sample_scan_pages.csv (khong co GT)
Co the chay lai: dong da co (engine,set,variant,dpi,rel,page) se bi bo qua.
"""
import argparse, json, sys, time, hashlib
from pathlib import Path
import cv2, numpy as np, pandas as pd
from ocrlib import *

HERE = Path(__file__).parent
CACHE = HERE / "_cache"
IMG = CACHE / "img"; RAW = CACHE / "raw"
IMG.mkdir(parents=True, exist_ok=True); RAW.mkdir(parents=True, exist_ok=True)


def make_engine(name):
    if name == "paddle":
        from paddle_wrap import PaddleEng
        return PaddleEng()
    if name == "rapid_v1":
        return RapidV1()
    if name.startswith("rapid_v") and name != "rapid_v1":
        from rapidocr import LangRec, OCRVersion, ModelType
    if name == "rapid_v5_latin":
        return RapidV3("rapidocr-3.10 PP-OCRv5 det(mobile)+latin rec(mobile)",
                       **{"Rec.lang_type": LangRec.LATIN, "Rec.ocr_version": OCRVersion.PPOCRV5, "Rec.model_type": ModelType.MOBILE,
                          "Det.ocr_version": OCRVersion.PPOCRV5, "Det.model_type": ModelType.MOBILE})
    if name == "rapid_v6_multi":
        return RapidV3("rapidocr-3.10 PP-OCRv6 multi small",
                       **{"Rec.lang_type": LangRec.CH, "Rec.ocr_version": OCRVersion.PPOCRV6, "Rec.model_type": ModelType.SMALL,
                          "Det.ocr_version": OCRVersion.PPOCRV6, "Det.model_type": ModelType.SMALL})
    if name == "viet_transformer":
        return VietOCRPipe("vgg_transformer")
    if name == "viet_transformer_gpu_b8":
        return VietOCRPipe("vgg_transformer", batch=8)
    if name == "viet_seq2seq":
        return VietOCRPipe("vgg_seq2seq")
    if name == "viet_seq2seq_cpu":
        return VietOCRPipe("vgg_seq2seq", device="cpu")
    if name == "viet_transformer_cpu":
        return VietOCRPipe("vgg_transformer", device="cpu")
    if name == "viet_transformer_detv6":
        return VietOCRPipe("vgg_transformer", det_version="PP-OCRv6", det_type="small")
    if name == "viet_seq2seq_pad":
        return VietOCRPipe("vgg_seq2seq", device="cpu", pad_x=0.3, pad_y=0.1)
    if name == "viet_seq2seq_pad_bg":
        return VietOCRPipe("vgg_seq2seq", device="cpu", pad_x=0.3, pad_y=0.1, bgnorm=True)
    if name == "viet_seq2seq_d1280":  # cau hinh dung cho build_ocr_dataset (GPU): det thu nho 1280 + bgnorm tu dong theo do bao hoa
        return VietOCRPipe("vgg_seq2seq", device="cuda:0", bgnorm="sat", det_max_side=1280)
    if name == "viet_seq2seq_bgsat":
        return VietOCRPipe("vgg_seq2seq", device="cuda:0", bgnorm="sat")
    if name == "viet_seq2seq_bgauto":
        return VietOCRPipe("vgg_seq2seq", device="cpu", bgnorm="auto")
    if name == "viet_seq2seq_pad_bg_w1024":
        return VietOCRPipe("vgg_seq2seq", device="cpu", pad_x=0.3, pad_y=0.1, bgnorm=True, max_width=1024)
    if name == "viet_seq2seq_pad_w1024":
        return VietOCRPipe("vgg_seq2seq", device="cpu", pad_x=0.3, pad_y=0.1, max_width=1024)
    if name == "easyocr":
        return EasyOCREng(True)
    if name == "easyocr_cpu":
        return EasyOCREng(False)
    raise SystemExit("engine khong biet: " + name)


def get_image(rel, page, dpi, variant):
    key = hashlib.sha1(f"{rel}|{page}|{dpi}|{variant}".encode("utf-8")).hexdigest()[:16]
    f = IMG / f"{key}.png"
    if f.exists():
        return cv2.imdecode(np.fromfile(str(f), np.uint8), cv2.IMREAD_COLOR)
    doc = open_pdf(rel)
    clean = render_page(doc, page, dpi)
    img = clean if variant == "clean" else degrade(clean, seed=int(hashlib.sha1(f"{rel}|{page}".encode()).hexdigest()[:8], 16))
    ok, buf = cv2.imencode(".png", img)
    buf.tofile(str(f))
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", required=True)
    ap.add_argument("--set", choices=["gold", "scan"], required=True)
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--stride", type=int, default=1, help="chi lay moi N trang trong danh sach (cho engine rat cham)")
    ap.add_argument("--threads", type=int, default=16, help="so luong tu torch (CPU)")
    ap.add_argument("--tag", default="main", help="'timing' = chay do toc do rieng, khong tinh vao metric")
    a = ap.parse_args()

    pages = pd.read_csv(HERE / ("sample_gold_pages.csv" if a.set == "gold" else "sample_scan_pages.csv"))
    if a.stride > 1:
        pages = pages.iloc[::a.stride].reset_index(drop=True)
    if a.limit:
        pages = pages.head(a.limit)
    variants = ["clean", "degraded"] if a.set == "gold" else ["scan"]
    out_f = RAW / f"{a.engine}__{a.set}__{a.dpi}__{a.tag}.jsonl"
    try:
        import torch; torch.set_num_threads(a.threads)
    except Exception:
        pass
    done = set()
    if out_f.exists():
        for line in out_f.open(encoding="utf-8"):
            r = json.loads(line); done.add((r["variant"], r["relative_path"], r["page"]))
    t0 = time.time()
    eng = make_engine(a.engine)
    print(f"[{a.engine}] khoi tao {time.time()-t0:.1f}s, device={eng.device}", flush=True)
    # warm-up de thoi gian/trang khong tinh khoi tao + nap model
    warm = get_image(pages.relative_path[0], int(pages.page[0]), a.dpi, "clean" if a.set == "gold" else "scan")
    eng(warm)
    n = 0
    with out_f.open("a", encoding="utf-8") as fo:
        for v in variants:
            for r in pages.itertuples():
                if (v, r.relative_path, int(r.page)) in done:
                    continue
                img = get_image(r.relative_path, int(r.page), a.dpi, "clean" if v == "scan" else v)
                if v == "scan":
                    pass
                err = None
                t = time.perf_counter()
                try:
                    res = eng(img)
                except Exception as e:  # noqa
                    res, err = [], f"{type(e).__name__}: {e}"
                dt = time.perf_counter() - t
                txt = result_to_text(res)
                confs = [c for _, _, c in res if c is not None]
                rec = dict(tag=a.tag, threads=a.threads, engine=a.engine, engine_name=eng.name, device=eng.device, set=a.set, variant=v, dpi=a.dpi,
                           relative_path=r.relative_path, page=int(r.page), folder=r.folder, text=txt,
                           n_boxes=len(res), mean_conf=float(np.mean(confs)) if confs else None, seconds=dt, error=err)
                fo.write(json.dumps(rec, ensure_ascii=False) + "\n"); fo.flush()
                n += 1
                if n % 10 == 0:
                    print(f"  {n} trang, {dt:.2f}s/trang gan nhat", flush=True)
    print(f"[{a.engine}] xong {n} trang moi, tong {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
