"""diagnose.py - Chẩn đoán vì sao biên bản giao nhận trong tệp ghép bị gán PHIEU_XUAT_KHO.

In, cho từng lát cắt đáp án của 8 tệp ghép: quyết định của cổng luật, TF-IDF (artefact huấn luyện trên DEV) và LLM (chỉ đọc cache).
Đầu ra tạm (có doc_id, nội bộ): results/05_composite_slices/diagnose_slices.csv

  .venv\\Scripts\\python.exe -X utf8 teams\\team3_classification\\experiments\\05_composite_slices\\diagnose.py
"""
from __future__ import annotations

import sys

import common05 as K  # noqa: E402  (đặt sys.path)
import pandas as pd  # noqa: E402

from e2e_lib import LayeredCache  # noqa: E402
from src.classification.doc_classifier import DEFAULT_SELECTION_PATH, DEFAULT_SOURCE, DocumentClassifier, load_cascade_config, text_for_classification  # noqa: E402
from src.classification.llm_backends import DEFAULT_SPEC_ID, LLM_SPECS, OllamaBackend  # noqa: E402
from src.classification.tfidf_classifier import TfidfClassifier  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def build_classifier(mode: str = "readonly", **kw) -> DocumentClassifier:
    import json

    cfg = load_cascade_config(DEFAULT_SELECTION_PATH, DEFAULT_SOURCE, DEFAULT_SPEC_ID, 0.01)
    tax = json.loads((K.REPO / "data" / "taxonomy_v2.json").read_text(encoding="utf-8"))
    cache = LayeredCache(K.CACHE_OWN, K.CACHE_EXTRA, mode=mode)
    backend = OllamaBackend(LLM_SPECS[DEFAULT_SPEC_ID], tax, cache, timeout=120.0)
    return DocumentClassifier(TfidfClassifier.load(), backend, cfg, **kw)


def main() -> int:
    K.OUT.mkdir(parents=True, exist_ok=True)
    ocr = K.load_ocr()
    clf = build_classifier()
    rows = []
    for r in K.oracle_slices(ocr):
        sl = r["slice"]
        text = text_for_classification(sl)
        res, tr = clf.classify_text(text, sl.slice_id)
        rows.append(dict(file=r["file_idx"], seg=r["seg_idx"], pages=f"{r['a']}-{r['b']}", true=r["true"], n_chars=len(text), tier=res.tier,
                         pred=res.predicted_category, abstain=res.abstain_reason or "", rule=tr.rule_label, rule_amb="|".join(tr.rule_ambiguous),
                         s_label=tr.s_label, s_conf=round(tr.s_conf, 3) if tr.s_conf is not None else None, llm=tr.llm_label,
                         llm_conf=round(tr.llm_conf, 3) if tr.llm_conf is not None else None, ok=(res.predicted_category == r["true"])))
    df = pd.DataFrame(rows)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    print(df.to_string())
    df.to_csv(K.OUT / "diagnose_slices.csv", index=False)
    print("cache hits/misses:", clf.llm.cache.hits, clf.llm.cache.misses)
    return 0


if __name__ == "__main__":
    sys.exit(main())
