"""Boc PaddleOCR 3.x (neu cai duoc) theo giao dien Engine cua ocrlib. lang='vi' -> mo hinh latin PP-OCRv5."""
from ocrlib import Engine


class PaddleEng(Engine):
    def __init__(self, lang="vi"):
        import paddleocr
        from paddleocr import PaddleOCR
        self.name = f"paddleocr-{paddleocr.__version__}(lang={lang})"
        self.device = "cpu"
        self.o = PaddleOCR(lang=lang, use_doc_orientation_classify=False, use_doc_unwarping=False,
                           use_textline_orientation=False, enable_mkldnn=False, cpu_threads=8)

    def __call__(self, img):
        res = self.o.predict(img)
        out = []
        for r in res:
            polys = r["rec_polys"] if "rec_polys" in r else r["dt_polys"]
            for b, t, s in zip(polys, r["rec_texts"], r["rec_scores"]):
                out.append((b, t, float(s)))
        return out
