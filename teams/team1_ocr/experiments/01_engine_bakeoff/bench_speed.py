import sys, time, os, pandas as pd
dev, thr, lim = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
os.environ["OCR_ORT_THREADS"] = str(min(thr, 8))
import torch; torch.set_num_threads(thr)
from ocrlib import *
from rapidocr import RapidOCR, OCRVersion, ModelType
s = pd.read_csv("sample_scan_pages.csv").iloc[::5]
e = VietOCRPipe("vgg_seq2seq", device=dev)
if lim:
    e.det.o = RapidOCR(params={"Det.ocr_version": OCRVersion.PPOCRV5, "Det.model_type": ModelType.MOBILE, "Det.limit_side_len": lim, "Det.limit_type": "max"})
imgs = [render_page(open_pdf(r.relative_path), int(r.page), 200) for r in s.itertuples()]
e(imgs[0])
t = time.perf_counter(); c = time.process_time(); n = 0
for im in imgs:
    r = e(im); n += len(r)
w = time.perf_counter() - t; cp = time.process_time() - c
print(f"RESULT dev={dev} thr={thr} detlimit={lim}: {w/len(imgs):.2f} s/page wall, {cp/len(imgs):.1f} cpu-s/page, boxes/page {n/len(imgs):.0f}", flush=True)
