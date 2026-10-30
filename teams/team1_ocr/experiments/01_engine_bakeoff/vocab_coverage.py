"""Dem so chu cai tieng Viet co dau nam trong tu dien nhan dang cua tung mo hinh (bang chung cho cau hoi 'dau di dau')."""
import glob, os, sys, unicodedata
import numpy as np
import onnxruntime as ort

LOWER = "àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"
ALL = LOWER + LOWER.upper().replace("Đ", "Đ")
ALL = "".join(sorted(set(ALL)))

def ort_chars(path):
    s = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
    m = s.get_modelmeta().custom_metadata_map
    return m.get("character", "").split("\n")

def report(name, chars):
    cs = set(chars)
    lower_ok = [c for c in LOWER if c in cs]
    upper_ok = [c for c in LOWER.upper() if c in cs]
    print(f"{name}: dict={len(cs)} ky tu | chu thuong co dau VN co mat {len(lower_ok)}/{len(LOWER)} | chu hoa {len(upper_ok)}/{len(LOWER)}"
          f" | thieu (thuong): {''.join(c for c in LOWER if c not in cs)}")

import rapidocr_onnxruntime, rapidocr
v1 = os.path.join(os.path.dirname(rapidocr_onnxruntime.__file__), "models")
print("v1 models:", os.listdir(v1))
for f in glob.glob(v1 + "/*rec*.onnx"):
    try: report("rapidocr_onnxruntime 1.2.3 " + os.path.basename(f), ort_chars(f))
    except Exception as e: print("  ERR", f, e)
for f in sorted(glob.glob(os.path.join(os.path.dirname(rapidocr.__file__), "models", "*rec*.onnx"))):
    try: report("rapidocr 3.10 " + os.path.basename(f), ort_chars(f))
    except Exception as e: print("  ERR", f, e)
# VietOCR / EasyOCR vocab
from vietocr.tool.config import Cfg
v = Cfg.load_config_from_name("vgg_seq2seq")["vocab"]
report("vietocr vgg_seq2seq", list(v))
import easyocr
from easyocr.config import recognition_models
print("easyocr vi charset (from config):", [k for k in recognition_models['gen2'] if 'viet' in k])
