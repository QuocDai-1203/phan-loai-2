"""signals.py - Tính "tín hiệu" của từng tầng (cổng luật, TF-IDF, LLM/Kev, embedding) cho một nguồn văn bản và một split.

DEV : TF-IDF và embedding few-shot cho dự đoán OUT-OF-FOLD (seed 0, 5 fold) - đúng quy tắc "ngưỡng chỉ chỉnh trên OOF của DEV".
TEST: huấn luyện trên TOÀN BỘ DEV rồi dự đoán TEST (chỉ khi final_test=True).
LLM/Kev zero-shot không cần huấn luyện nên dự đoán trực tiếp trên mọi tài liệu của split.
"""

from __future__ import annotations

import json
import time
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from common import (POOL, SEL01, UNKNOWN, Data, Doc, Prediction, cross_validate, get_cache, log)
from methods import RuleGatePredictor, VecCache, build_predictor, text_configs
from predictors import EmbCentroid, EmbeddingStore, ZeroShotPredictor, answers_to_prediction
from src.classification.cascade import Signals

CFG_BY_NAME = {c["name"]: c for c in text_configs()}


def tfidf_config_for(source: str) -> dict:
    sel = json.loads(SEL01.read_text(encoding="utf-8"))
    if source not in sel["final_configs"]:
        raise KeyError(f"{source} chưa có trong dev_selection.json của thí nghiệm 01 - chạy lại 01/run_all.py (giai đoạn DEV)")
    return CFG_BY_NAME[sel["final_configs"][source][0]]


def _time_each(predictor, docs: Sequence[Doc]) -> np.ndarray:
    out = []
    for d in docs:
        t0 = time.perf_counter()
        predictor.predict([d])
        out.append((time.perf_counter() - t0) * 1000)
    return np.asarray(out)


def rule_signals(docs: Sequence[Doc]) -> tuple[List[str], np.ndarray]:
    p = RuleGatePredictor("Z")
    lat = _time_each(p, docs)
    labels = p.predict(docs).labels
    return ["" if l == UNKNOWN else l for l in labels], lat


def tfidf_signals(data: Data, source: str, split: str, final_test: bool = False, seed: int = 0, cfg: Optional[dict] = None):
    """-> (labels, conf, latency_ms, config_name). split='DEV': OOF; split='TEST': fit trên DEV."""
    cfg = cfg or tfidf_config_for(source)
    classes = data.s_classes
    dev = data.docs(source, "DEV")
    if split == "DEV":
        cv = cross_validate(lambda: build_predictor(cfg, classes, VecCache()), dev, classes, "S", seed)
        oof = cv.oof.set_index("doc_id").loc[[d.doc_id for d in dev]]
        proba = pd.DataFrame(cv.proba, index=cv.oof["doc_id"]).loc[[d.doc_id for d in dev]].to_numpy()
        labels = oof["y_pred"].tolist()
        conf = proba.max(axis=1)
        p_time = build_predictor(cfg, classes).fit(dev)
        lat = _time_each(p_time, dev)
        return labels, conf, lat, cfg["name"]
    test = data.docs(source, "TEST", final_test=final_test)
    p = build_predictor(cfg, classes).fit(dev)
    pr = p.predict(test)
    return pr.labels, pr.confidence, _time_each(p, test), cfg["name"]


def emb_fewshot_signals(data: Data, source: str, split: str, store: EmbeddingStore, final_test: bool = False, seed: int = 0, min_train: int = 2):
    """Centroid few-shot trên toàn taxonomy (Track Z). -> (labels, conf, latency_ms). Nhãn UNKNOWN nếu không có tâm nào."""
    classes = data.z_classes
    dev = data.docs(source, "DEV")
    if split == "DEV":
        cv = cross_validate(lambda: EmbCentroid(store, classes, "Z", min_train), dev, classes, "Z", seed, min_support=3, abstain_label=UNKNOWN)
        oof = cv.oof.set_index("doc_id").loc[[d.doc_id for d in dev]]
        return oof["y_pred"].tolist(), oof["conf"].to_numpy(), np.array([store.doc_latency_ms(d) for d in dev])
    test = data.docs(source, "TEST", final_test=final_test)
    p = EmbCentroid(store, classes, "Z", min_train).fit(dev)
    pr = p.predict(test)
    return pr.labels, pr.confidence, np.array([store.doc_latency_ms(d) for d in test])


def llm_signals(data: Data, source: str, split: str, spec: dict, final_test: bool = False, tag: str = "kev-0.8b"):
    """-> (labels, conf, latency_ms, answers). Zero-shot (không huấn luyện) nên dự đoán trực tiếp; ICL lấy ví dụ từ DEV
    (với DEV: cần CV - dùng `icl_cv_signals`)."""
    docs = data.docs(source, split, final_test=final_test)
    p = ZeroShotPredictor(spec, data.z_classes, tag=tag)
    if spec.get("icl"):
        p.fit(data.docs(source, "DEV"))
    pr = p.predict(docs)
    conf = np.array([np.nan if (a.conf is None or not a.parse_ok) else a.conf for a in p.answers])
    return pr.labels, conf, pr.latency_ms, p.answers


def icl_cv_signals(data: Data, source: str, spec: dict, seed: int = 0, tag: str = "kev-0.8b"):
    """ICL trên DEV với ví dụ CHỈ lấy từ các fold khác (không rò rỉ)."""
    dev = data.docs(source, "DEV")
    labels, conf, lat, answers = {}, {}, {}, {}
    for f in sorted({d.folds[seed] for d in dev}):
        tr = [d for d in dev if d.folds[seed] != f]
        te = [d for d in dev if d.folds[seed] == f]
        p = ZeroShotPredictor(spec, data.z_classes, tag=tag).fit(tr)
        pr = p.predict(te)
        for d, l, a, t in zip(te, pr.labels, p.answers, pr.latency_ms):
            labels[d.doc_id], conf[d.doc_id] = l, (np.nan if (a.conf is None or not a.parse_ok) else a.conf)
            lat[d.doc_id], answers[d.doc_id] = t, a
    ids = [d.doc_id for d in dev]
    return [labels[i] for i in ids], np.array([conf[i] for i in ids]), np.array([lat[i] for i in ids]), [answers[i] for i in ids]
