"""predictors.py - Predictor (giao diện harness) cho thí nghiệm 02: embedding bge-m3 và LLM/Kev zero-shot.

Mọi lời gọi mô hình đi qua DiskCache (khóa = mô hình + yêu cầu); chạy lại là miễn phí và tất định.
"""

from __future__ import annotations

import hashlib
import pickle
from typing import Dict, List, Optional, Sequence

import numpy as np
from sklearn.linear_model import LogisticRegression

from common import (MIN_TEXT_CHARS, POOL, UNKNOWN, Doc, Prediction, Predictor, clean_text, get_cache,
                    load_taxonomy_json)
from src.classification.zero_shot import (NO_ANSWER, Answer, KevClient, LabelSet, OllamaClient, build_label_set,
                                          kev_one_stage, kev_two_stage, ollama_one_stage, ollama_two_stage,
                                          ollama_user_prompt)


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------
class EmbeddingStore:
    """Embedding bge-m3 (Ollama) của n ký tự đầu của văn bản đã làm sạch; L2-chuẩn hóa; cache đĩa theo văn bản."""

    def __init__(self, n_chars: int = 512, model: str = "bge-m3", cache_name: str = "emb"):
        self.n_chars, self.model = n_chars, model
        self.client = OllamaClient(get_cache(cache_name))
        self._mem: Dict[str, np.ndarray] = {}
        self.latency_ms: Dict[str, float] = {}

    def text_of(self, d: Doc) -> str:
        return clean_text(d.text, self.n_chars) or "(trống)"

    def get_texts(self, texts: Sequence[str]) -> np.ndarray:
        rows = []
        for t in texts:
            k = hashlib.sha1(t.encode("utf-8")).hexdigest()
            if k not in self._mem:
                rec = self.client.embed(self.model, [t])[0]
                v = np.asarray(rec["embedding"], dtype=np.float32)
                self._mem[k] = v / (np.linalg.norm(v) + 1e-9)
                self.latency_ms[k] = float(rec.get("latency_ms", 0.0))
            rows.append(self._mem[k])
        return np.vstack(rows)

    def get(self, docs: Sequence[Doc]) -> np.ndarray:
        return self.get_texts([self.text_of(d) for d in docs])

    def doc_latency_ms(self, d: Doc) -> float:
        return self.latency_ms.get(hashlib.sha1(self.text_of(d).encode("utf-8")).hexdigest(), 0.0)


def _softmax(z: np.ndarray, temp: float) -> np.ndarray:
    z = z / temp
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


class EmbLR(Predictor):
    """Embedding + LogisticRegression (Track S)."""
    track = "S"

    def __init__(self, store: EmbeddingStore, classes: Sequence[str], c: float = 10.0):
        self.store, self.classes, self.c = store, list(classes), c
        self.name = f"bge_n{store.n_chars}_lr_C{c:g}"

    def fit(self, train_docs):
        X = self.store.get(train_docs)
        y = [d.target(self.track) for d in train_docs]
        self.model = LogisticRegression(C=self.c, max_iter=3000, class_weight="balanced").fit(X, y)
        return self

    def predict(self, docs):
        pr = self.model.predict_proba(self.store.get(docs))
        full = np.zeros((len(docs), len(self.classes)))
        for j, c in enumerate(self.model.classes_):
            full[:, self.classes.index(c)] = pr[:, j]
        return Prediction([self.classes[i] for i in full.argmax(1)], full, list(self.classes))


class EmbCentroid(Predictor):
    """Tâm lớp (trung bình embedding) + cosine gần nhất. track='Z' + min_train=2 là biến thể few-shot trên toàn taxonomy:
    chỉ lớp có >= min_train tài liệu huấn luyện mới có tâm (lớp khác không thể được dự đoán). proba = softmax(sim / temp)."""

    def __init__(self, store: EmbeddingStore, classes: Sequence[str], track: str = "S", min_train: int = 1, temp: float = 0.05):
        self.store, self.classes, self.track, self.min_train, self.temp = store, list(classes), track, min_train, temp
        self.name = f"bge_n{store.n_chars}_centroid_{track}_min{min_train}"

    def fit(self, train_docs):
        X = self.store.get(train_docs)
        y = np.array([d.target(self.track) for d in train_docs])
        self.names, cents = [], []
        for c in self.classes:
            m = y == c
            if m.sum() >= self.min_train:
                v = X[m].mean(0)
                cents.append(v / (np.linalg.norm(v) + 1e-9))
                self.names.append(c)
        self.C = np.vstack(cents)
        return self

    def predict(self, docs):
        sim = self.store.get(docs) @ self.C.T
        pr = _softmax(sim, self.temp)
        full = np.zeros((len(docs), len(self.classes)))
        for j, c in enumerate(self.names):
            full[:, self.classes.index(c)] = pr[:, j]
        return Prediction([self.names[i] for i in sim.argmax(1)], full, list(self.classes))


class EmbKNN(Predictor):
    """k láng giềng gần nhất theo cosine, bỏ phiếu có trọng số exp(sim/temp)."""

    def __init__(self, store: EmbeddingStore, classes: Sequence[str], track: str = "S", k: int = 3, temp: float = 0.05):
        self.store, self.classes, self.track, self.k, self.temp = store, list(classes), track, k, temp
        self.name = f"bge_n{store.n_chars}_knn{k}_{track}"

    def fit(self, train_docs):
        self.X = self.store.get(train_docs)
        self.y = np.array([self.classes.index(d.target(self.track)) for d in train_docs])
        return self

    def predict(self, docs):
        sim = self.store.get(docs) @ self.X.T
        full = np.zeros((len(docs), len(self.classes)))
        kk = min(self.k, sim.shape[1])
        for i in range(len(docs)):
            idx = np.argsort(-sim[i])[:kk]
            w = np.exp((sim[i, idx] - sim[i, idx].max()) / self.temp)
            for j, wt in zip(idx, w):
                full[i, self.y[j]] += wt
            full[i] /= full[i].sum()
        return Prediction([self.classes[i] for i in full.argmax(1)], full, list(self.classes))


class EmbZeroShot(Predictor):
    """Không huấn luyện: embedding của mô tả lớp (tên + mô tả ngắn) làm nguyên mẫu; cosine gần nhất. Track Z."""
    track = "Z"

    def __init__(self, store: EmbeddingStore, classes: Sequence[str], desc: str = "short", temp: float = 0.05):
        self.store, self.classes, self.temp = store, list(classes), temp
        self.ls = build_label_set(load_taxonomy_json(), desc)
        self.name = f"bge_n{store.n_chars}_zeroshot_{desc}"
        texts = [f"{c['name_vi']}. {self.ls.desc[c['id']]}" for c in load_taxonomy_json()["classes"] if c["id"] in self.ls.ids]
        self.names = [c["id"] for c in load_taxonomy_json()["classes"] if c["id"] in self.ls.ids]
        self.C = store.get_texts(texts)

    def predict(self, docs):
        sim = self.store.get(docs) @ self.C.T
        pr = _softmax(sim, self.temp)
        full = np.zeros((len(docs), len(self.classes)))
        for j, c in enumerate(self.names):
            if c in self.classes:
                full[:, self.classes.index(c)] = pr[:, j]
        return Prediction([self.names[i] for i in sim.argmax(1)], full, list(self.classes))


# ---------------------------------------------------------------------------
# LLM / Kev zero-shot
# ---------------------------------------------------------------------------
class ZeroShotPredictor(Predictor):
    """Zero-shot toàn taxonomy (Track Z). spec:
       engine 'kev' | 'ollama'; model (Ollama); stages 1|2; desc 'short'|'long'; chars (số ký tự đầu của văn bản);
       icl (số ví dụ mỗi lớp trong prompt, chỉ Ollama; lấy CHỈ từ tài liệu huấn luyện trong `fit`).
       predict() lưu self.answers (cùng thứ tự docs) để dùng cho calibration/cascade."""
    track = "Z"

    def __init__(self, spec: dict, classes: Sequence[str], tag: str = "kev-0.8b"):
        self.spec = dict(spec)
        self.name = spec["id"]
        self.ls: LabelSet = build_label_set(load_taxonomy_json(), spec.get("desc", "short"))
        # nhãn mô hình được phép trả = toàn taxonomy (kể cả loại không có tài liệu nào trong bộ nhãn): trả loại đó là SAI, không phải abstain
        self.classes = sorted(set(classes) | set(self.ls.ids))
        self.chars = int(spec.get("chars", 2000))
        self.examples: Optional[Dict[str, List[str]]] = None
        if spec["engine"] == "kev":
            self.kev = KevClient(get_cache("kev"), tag=tag)
        else:
            self.oll = OllamaClient(get_cache("ollama"))
        self.answers: List[Answer] = []

    def fit(self, train_docs):
        n = int(self.spec.get("icl", 0))
        if n:
            by: Dict[str, List[Doc]] = {}
            for d in train_docs:
                if d.label in self.ls.ids:
                    by.setdefault(d.label, []).append(d)
            self.examples = {}
            for c, ds in by.items():
                ds = sorted(ds, key=lambda d: hashlib.sha1(d.doc_id.encode()).hexdigest())[:n]
                self.examples[c] = [clean_text(d.text, 160).replace("\n", " / ") for d in ds]
        return self

    def num_ctx(self) -> int:
        if self.spec.get("num_ctx"):
            return int(self.spec["num_ctx"])
        base = 18000 if self.spec.get("desc") == "long" else 6144
        if self.examples:
            base += 4096
        return base

    def answer(self, d: Doc) -> Answer:
        text = clean_text(d.text, self.chars)
        if len(text) < MIN_TEXT_CHARS:
            return Answer(NO_ANSWER, None, None, 0.0, False, "văn bản quá ngắn")
        sp = self.spec
        if sp["engine"] == "kev":
            return (kev_two_stage if sp.get("stages", 1) == 2 else kev_one_stage)(self.kev, text, self.ls)
        if sp.get("stages", 1) == 2:
            return ollama_two_stage(self.oll, sp["model"], text, self.ls, self.num_ctx())
        return ollama_one_stage(self.oll, sp["model"], text, self.ls, self.num_ctx(), self.examples)

    def predict(self, docs):
        self.answers = [self.answer(d) for d in docs]
        return answers_to_prediction(self.answers, self.classes)


def answers_to_prediction(answers: Sequence[Answer], classes: Sequence[str]) -> Prediction:
    """Nhãn (NO_ANSWER -> UNKNOWN), ma trận xác suất (Kev: phân phối thật, chuẩn hóa lại trên các lớp; Ollama: conf ở lớp chọn,
    phần còn lại chia đều), độ trễ. Dùng để chấm bằng harness (accuracy, macro-F1, ECE...)."""
    classes = list(classes)
    k = len(classes)
    labels, P, lat = [], np.full((len(answers), k), np.nan), []
    for i, a in enumerate(answers):
        lat.append(a.latency_ms)
        lab = a.label if a.parse_ok and a.label in classes else UNKNOWN
        labels.append(lab)
        if lab == UNKNOWN or a.conf is None:
            continue
        if a.probs:
            row = np.zeros(k)
            for c, p in a.probs.items():
                if c in classes:
                    row[classes.index(c)] = p
            P[i] = row / max(row.sum(), 1e-9)
        else:
            row = np.full(k, (1 - a.conf) / max(k - 1, 1))
            row[classes.index(lab)] = a.conf
            P[i] = row
    return Prediction(labels, P, classes, np.asarray(lat))
