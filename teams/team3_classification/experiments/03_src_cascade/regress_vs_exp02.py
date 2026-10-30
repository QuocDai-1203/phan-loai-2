"""regress_vs_exp02.py - Kiểm hồi quy: `src.classification.doc_classifier.DocumentClassifier` so với cascade của thí nghiệm 02.

Cấu hình: nguồn `ocr_v2_p12`, tầng 3 = `q35_s1_short_c2000` (Qwen3.5-4B, mô tả ngắn, 1 bước), mức sai <= 1%
(ngưỡng đọc từ results/02_llm_and_cascade/tables/dev_selection_02.json).

DEV (mặc định):
  * THAM CHIẾU = chính mã thí nghiệm: `signals.rule_signals`, `signals.tfidf_signals` (TF-IDF out-of-fold, seed 0, 5 fold),
    `signals.llm_signals` -> `cascade.run_cascade`. Ghép với dòng đã lưu `tables/e4_cascade_dev.csv` để chắc rằng THAM CHIẾU tái lập đúng
    số của thí nghiệm 02.
  * MỚI = `DocumentClassifier` với `TfidfClassifier` huấn luyện lại trên 4 fold, dự đoán fold còn lại (đúng quy tắc OOF), tầng 3 là
    `OllamaBackend` đọc cache đĩa của thí nghiệm 02 ở chế độ CHỈ ĐỌC: một lần lỡ cache là lỗi (không gọi Ollama).
  * So từng tài liệu bộ ba (tier, nhãn, được nhận) và các tín hiệu trung gian.

--final-test-once: chạy DUY NHẤT MỘT LẦN trên TEST (mô hình TF-IDF = chính tệp trong models/classification/, huấn luyện trên toàn DEV) chỉ để
xác nhận tái lập dòng TEST đã báo cáo; KHÔNG dùng để chỉnh gì. Sổ đăng ký results/03_src_cascade/test_run_registry.json chặn chạy lần hai.

  .venv\\Scripts\\python.exe -X utf8 teams\\team3_classification\\experiments\\03_src_cascade\\regress_vs_exp02.py
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
EXP02 = HERE.parent / "02_llm_and_cascade"
for p in (REPO, REPO / "teams" / "00_data_and_eval" / "eval", HERE.parent / "01_classical_baselines", EXP02):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import common as C  # noqa: E402  (thí nghiệm 02)
import predictors as P  # noqa: E402
import signals as SG  # noqa: E402
from run_all import SPECS  # noqa: E402
from src.classification.cascade import CascadeParams, Signals, run_cascade  # noqa: E402
from src.classification.doc_classifier import DocumentClassifier, load_cascade_config  # noqa: E402
from src.classification.llm_backends import LLM_SPECS, OllamaBackend  # noqa: E402
from src.classification.llm_cache import DiskCache  # noqa: E402
from src.classification.tfidf_classifier import TfidfClassifier  # noqa: E402
from src.common.contracts import DocumentSlice  # noqa: E402

SOURCE, T3 = "ocr_v2_p12", "q35_s1_short_c2000"
OUT = REPO / "teams" / "team3_classification" / "results" / "03_src_cascade"
REGISTRY = OUT / "test_run_registry.json"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class CacheMiss(RuntimeError):
    pass


class ReadOnlyCache(DiskCache):
    """Cache chỉ đọc: lỗi nếu thiếu khóa (chứng minh mọi lời gọi LLM được phục vụ từ cache có sẵn, không gọi mô hình)."""

    def __init__(self, root):
        super().__init__(root)
        self.error_records = 0

    def cached(self, key, fn, *, retry_errors=False):
        rec = self.get(key)
        if rec is None:
            self.misses += 1
            raise CacheMiss(key)
        self.hits += 1
        self.error_records += bool(rec.get("error"))
        return rec


def reference_params() -> CascadeParams:
    """Đọc ngưỡng độc lập với src (đọc JSON thô) để THAM CHIẾU không phụ thuộc mã đang kiểm."""
    sel = json.loads(C.SEL02.read_text(encoding="utf-8"))
    e = [x for x in sel["cascade"][SOURCE]["entries"] if x["name"] == f"full[{T3}]" and abs(x["max_error"] - 0.01) < 1e-12][0]["params"]
    return CascadeParams(**e)


def new_classifier(tfidf: TfidfClassifier, ro: ReadOnlyCache) -> DocumentClassifier:
    cfg = load_cascade_config(C.SEL02, SOURCE, T3, 0.01)
    assert cfg.measured, cfg.note
    backend = OllamaBackend(LLM_SPECS[T3], C.load_taxonomy_json(), ro)
    return DocumentClassifier(tfidf, backend, cfg)


def slice_of(d) -> DocumentSlice:
    return DocumentSlice(slice_id=d.doc_id, start_page=1, end_page=1, page_count=1, combined_text=d.text)


def run_dev() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    D = C.Data()
    dev = D.docs(SOURCE, "DEV")
    y = np.array([d.label for d in dev])
    ids = [d.doc_id for d in dev]
    params = reference_params()
    print(f"DEV: {len(dev)} tài liệu; tham số: {params.describe()}")

    # --- THAM CHIẾU (mã thí nghiệm 02, LLM chỉ đọc cache) ---
    ro_ref = ReadOnlyCache(C.CACHE_DIR / "ollama")
    P.get_cache = lambda name, _r=ro_ref: _r             # ZeroShotPredictor lấy cache qua tên này
    r_lab, _ = SG.rule_signals(dev)
    s_lab, s_conf, _, cfg_name = SG.tfidf_signals(D, SOURCE, "DEV")
    l_lab, l_conf, _, answers = SG.llm_signals(D, SOURCE, "DEV", SPECS[T3])
    l_lab = ["" if x == C.UNKNOWN else x for x in l_lab]
    sig = Signals(rule=r_lab, s_label=s_lab, s_conf=np.asarray(s_conf, float), llm_label=l_lab, llm_conf=np.asarray(l_conf, float))
    ref = run_cascade(sig, params)
    ref_err = int(((ref["label"].to_numpy() != y) & ref["accepted"].to_numpy()).sum())
    print(f"THAM CHIẾU: tf-idf={cfg_name}; nhận {int(ref['accepted'].sum())}/{len(dev)}, sai {ref_err}; tầng {dict(Counter(ref['tier']))}; "
          f"cache LLM: {ro_ref.hits} hit, {ro_ref.misses} miss, {ro_ref.error_records} bản ghi lỗi")
    stored = pd.read_csv(C.TABLES / "e4_cascade_dev.csv")
    row = stored[(stored["source"] == SOURCE) & (stored["name"] == f"full[{T3}]") & (stored["max_error"] == 0.01)].iloc[0]
    ok_ref = (int(row["n_accepted"]) == int(ref["accepted"].sum()) and int(row["errors"]) == ref_err
              and abs(row["share_rule"] - (ref["tier"] == "rule").mean()) < 1e-9 and abs(row["share_tfidf"] - (ref["tier"] == "tfidf").mean()) < 1e-9
              and abs(row["share_llm"] - (ref["tier"] == "llm").mean()) < 1e-9)
    print(f"  khớp dòng đã lưu e4_cascade_dev.csv (n_accepted={int(row['n_accepted'])}, errors={int(row['errors'])}, "
          f"luật/tfidf/llm={row['share_rule']:.4f}/{row['share_tfidf']:.4f}/{row['share_llm']:.4f}): {ok_ref}")

    # --- MỚI: TF-IDF huấn luyện theo fold, cascade qua DocumentClassifier ---
    ro_new = ReadOnlyCache(C.CACHE_DIR / "ollama")
    folds = np.array([d.folds[0] for d in dev])
    rows = []
    for f in sorted(set(folds)):
        tr = [d for d in dev if d.folds[0] != f]
        tfidf = TfidfClassifier(D.s_classes).fit([d.text for d in tr], [d.label_s for d in tr])
        clf = new_classifier(tfidf, ro_new)
        for i in np.where(folds == f)[0]:
            d = dev[i]
            res, tr_ = clf.classify_text(d.text, d.doc_id)
            new_label = "" if res.tier == "human" else res.predicted_category
            r = ref.iloc[i]
            same_tier, same_label, same_acc = res.tier == r["tier"], new_label == r["label"], (res.tier != "human") == bool(r["accepted"])
            sig_ok = (tr_.rule_label == r_lab[i]
                      and (tr_.s_label is None or (tr_.s_label == s_lab[i] and abs(tr_.s_conf - s_conf[i]) < 1e-9))
                      and (tr_.llm_label is None or (tr_.llm_label == l_lab[i] and (np.isnan(l_conf[i]) if tr_.llm_conf is None else abs(tr_.llm_conf - l_conf[i]) < 1e-12))))
            rows.append(dict(doc_id=d.doc_id, fold=int(f), true=d.label, ref_tier=r["tier"], new_tier=res.tier, ref_label=r["label"],
                             new_label=new_label, ref_accepted=bool(r["accepted"]), new_accepted=res.tier != "human", match=same_tier and same_label and same_acc,
                             signals_match=sig_ok, new_abstain=res.abstain_reason, model_name=res.model_name))
    df = pd.DataFrame(rows).set_index("doc_id").loc[ids].reset_index()
    n_match, n_sig = int(df["match"].sum()), int(df["signals_match"].sum())
    n_acc = int(df["new_accepted"].sum())
    n_err = int(((df["new_label"] != df["true"]) & df["new_accepted"]).sum())
    print(f"\nMỚI: nhận {n_acc}/{len(df)}, sai {n_err}; tầng {dict(Counter(df['new_tier']))}; "
          f"cache LLM: {ro_new.hits} hit, {ro_new.misses} miss, {ro_new.error_records} bản ghi lỗi")
    print(f"TRÙNG (tier, nhãn, được nhận): {n_match} / {len(df)};  tín hiệu trung gian trùng: {n_sig} / {len(df)}")
    bad = df[~df["match"]]
    if len(bad):
        print("KHÔNG TRÙNG:")
        print(bad.to_string())
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "regress_dev_per_doc.csv", index=False)      # chứa doc_id: chỉ dùng nội bộ
    summary = dict(created=datetime.now(timezone.utc).isoformat(timespec="seconds"), source=SOURCE, t3=T3, max_error=0.01,
                   params=params.describe(), n_docs=len(df), n_match=n_match, n_signals_match=n_sig,
                   reference=dict(n_accepted=int(ref["accepted"].sum()), errors=ref_err, tiers=dict(Counter(ref["tier"])), matches_stored_e4_dev_row=bool(ok_ref)),
                   new=dict(n_accepted=n_acc, errors=n_err, tiers=dict(Counter(df["new_tier"]))),
                   llm_cache=dict(hits=ro_new.hits, misses=ro_new.misses, error_records=ro_new.error_records),
                   labels_sha1_10=D.bench.labels_sha)
    (OUT / "regress_dev_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0 if (n_match == len(df) and ro_new.misses == 0 and ok_ref) else 1


def run_test_once() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if REGISTRY.exists():
        print("TEST đã được chạy cho kiểm hồi quy này; từ chối chạy lại:", REGISTRY.read_text(encoding="utf-8"))
        return 3
    D = C.Data()
    test = D.docs(SOURCE, "TEST", final_test=True)               # lần mở TEST duy nhất của kiểm hồi quy này
    y = np.array([d.label for d in test])
    ro = ReadOnlyCache(C.CACHE_DIR / "ollama")
    tfidf = TfidfClassifier.load()                                # mô hình đã lưu, huấn luyện trên toàn DEV
    meta = tfidf.meta
    assert meta.train_split == "DEV" and not (set(meta.train_doc_ids) & {d.doc_id for d in test})
    clf = new_classifier(tfidf, ro)
    res = [clf.classify_text(d.text, d.doc_id)[0] for d in test]
    tiers = Counter(r.tier for r in res)
    acc = np.array([r.tier != "human" for r in res])
    lab = np.array(["" if r.tier == "human" else r.predicted_category for r in res])
    err = int(((lab != y) & acc).sum())
    stored = pd.read_csv(C.TABLES / "e4_cascade_test.csv")
    row = stored[(stored["source"] == SOURCE) & (stored["name"] == f"full[{T3}]") & (stored["max_error"] == 0.01)].iloc[0]
    n = len(test)
    same = (int(row["n_accepted"]) == int(acc.sum()) and int(row["errors"]) == err
            and abs(row["share_rule"] - tiers["rule"] / n) < 1e-9 and abs(row["share_tfidf"] - tiers["tfidf"] / n) < 1e-9
            and abs(row["share_llm"] - tiers["llm"] / n) < 1e-9)
    out = dict(created=datetime.now(timezone.utc).isoformat(timespec="seconds"), n=n, n_accepted=int(acc.sum()), errors=err, tiers=dict(tiers),
               stored=dict(n_accepted=int(row["n_accepted"]), errors=int(row["errors"]), share_rule=float(row["share_rule"]),
                           share_tfidf=float(row["share_tfidf"]), share_llm=float(row["share_llm"])), reproduces_stored_row=bool(same),
               llm_cache=dict(hits=ro.hits, misses=ro.misses), tfidf_labels_sha1_10=meta.labels_sha1_10,
               note="Chạy MỘT lần để xác nhận tái lập dòng TEST đã báo cáo của thí nghiệm 02; không dùng để chỉnh bất cứ thứ gì.")
    REGISTRY.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if same and ro.misses == 0 else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--final-test-once", action="store_true")
    a = ap.parse_args()
    sys.exit(run_test_once() if a.final_test_once else run_dev())
