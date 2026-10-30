"""extract_signals.py - Gom tín hiệu DEV (out-of-fold) cho thí nghiệm 04: luật, TF-IDF, ba cấu hình LLM (q35_s1, q35_s2, q25_s1).

Chỉ DEV. LLM đọc cache đĩa của thí nghiệm 02 ở chế độ CHỈ ĐỌC (thiếu khóa = lỗi, không gọi Ollama).
Đầu ra (chứa doc_id: chỉ dùng nội bộ): results/04_safety_margin/dev_signals.csv

  .venv\\Scripts\\python.exe -X utf8 teams\\team3_classification\\experiments\\04_safety_margin\\extract_signals.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
EXP02 = HERE.parent / "02_llm_and_cascade"
for p in (REPO, REPO / "teams" / "00_data_and_eval" / "eval", HERE.parent / "01_classical_baselines", EXP02):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import common as C  # noqa: E402
import predictors as P  # noqa: E402
import signals as SG  # noqa: E402
from run_all import SPECS  # noqa: E402
from src.classification.llm_cache import DiskCache  # noqa: E402

SOURCE = "ocr_v2_p12"
LLMS = {"q35s1": "q35_s1_short_c2000", "q35s2": "q35_s2_short_c2000", "q25s1": "q25_s1_short_c2000"}
OUT = REPO / "teams" / "team3_classification" / "results" / "04_safety_margin"


class ReadOnlyCache(DiskCache):
    def __init__(self, root):
        super().__init__(root)

    def cached(self, key, fn, *, retry_errors=False):
        rec = self.get(key)
        if rec is None:
            self.misses += 1
            raise RuntimeError("CacheMiss " + key)
        self.hits += 1
        return rec


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    D = C.Data()
    dev = D.docs(SOURCE, "DEV")
    ro = ReadOnlyCache(C.CACHE_DIR / "ollama")
    P.get_cache = lambda name, _r=ro: _r
    r_lab, _ = SG.rule_signals(dev)
    s_lab, s_conf, _, cfg = SG.tfidf_signals(D, SOURCE, "DEV")
    df = pd.DataFrame(dict(doc_id=[d.doc_id for d in dev], fold=[d.folds[0] for d in dev], y=[d.label for d in dev],
                           rule=r_lab, s_label=s_lab, s_conf=np.asarray(s_conf, float)))
    for k, spec_id in LLMS.items():
        lab, conf, _, _ = SG.llm_signals(D, SOURCE, "DEV", SPECS[spec_id])
        df[f"{k}_label"] = ["" if x == C.UNKNOWN else x for x in lab]
        df[f"{k}_conf"] = np.asarray(conf, float)
    df.to_csv(OUT / "dev_signals.csv", index=False)
    print(f"n={len(df)} tfidf={cfg} cache hits={ro.hits} misses={ro.misses} labels_sha={D.bench.labels_sha}")
    for k in LLMS:
        print(k, "acc", float((df[f"{k}_label"] == df["y"]).mean()), "nan_conf", int(df[f"{k}_conf"].isna().sum()))
    print("rule acc on decided", float((df["rule"][df["rule"] != ""] == df["y"][df["rule"] != ""]).mean()), int((df["rule"] != "").sum()))
    return 0 if ro.misses == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
