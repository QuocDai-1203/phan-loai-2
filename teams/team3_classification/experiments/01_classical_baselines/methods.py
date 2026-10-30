"""methods.py - Các Predictor cổ điển (CPU) cho thí nghiệm 01: TF-IDF + LR/SVC/CNB, majority, cổng luật, baseline ảnh.

Mọi lớp tuân theo giao diện `harness.Predictor`. Siêu tham số được liệt kê CỐ ĐỊNH trong `CONFIGS` (lưới rất nhỏ);
việc chọn cấu hình diễn ra trong CV trên DEV (xem run_all.py), KHÔNG bao giờ trên TEST.
"""

from __future__ import annotations

import io
import pickle
import sys
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
for p in (REPO, REPO / "teams" / "00_data_and_eval" / "eval"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from sklearn.calibration import CalibratedClassifierCV  # noqa: E402
from sklearn.decomposition import PCA  # noqa: E402
from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.naive_bayes import ComplementNB  # noqa: E402
from sklearn.svm import LinearSVC  # noqa: E402

from harness import POOL, UNKNOWN, Doc, Prediction, Predictor  # noqa: E402
from src.common.text_norm import normalize_text  # noqa: E402

import unicodedata  # noqa: E402
import re  # noqa: E402

_WS = re.compile(r"\s+")


def raw_norm(text: str) -> str:
    """Không bỏ dấu: chỉ NFC + casefold + gộp khoảng trắng."""
    return _WS.sub(" ", unicodedata.normalize("NFC", text or "").casefold()).strip()


# ---------------------------------------------------------------------------
# Đặc trưng văn bản
# ---------------------------------------------------------------------------
class VecCache:
    """Bộ nhớ đệm vectorizer theo (spec, tập train): tránh fit TF-IDF lại cho mỗi giá trị C. Chỉ để tăng tốc CV;
    đo độ trễ luôn dùng predictor KHÔNG có cache."""

    def __init__(self):
        self.vec: Dict[tuple, tuple] = {}
        self.test: Dict[tuple, object] = {}

    @staticmethod
    def key_docs(docs: Sequence[Doc]) -> int:
        return hash(tuple((d.doc_id, hash(d.text)) for d in docs))


def make_vectorizer(kind: str) -> TfidfVectorizer:
    if kind == "word":
        return TfidfVectorizer(analyzer="word", ngram_range=(1, 2), token_pattern=r"(?u)\b\w+\b", sublinear_tf=True,
                               min_df=2, lowercase=False, dtype=np.float32)
    if kind == "char":
        return TfidfVectorizer(analyzer="char", ngram_range=(2, 5), sublinear_tf=True, min_df=2, lowercase=False,
                               dtype=np.float32)
    raise ValueError(kind)


class TextPredictor(Predictor):
    """TF-IDF (word 1-2 / char 2-5) [+ bỏ dấu] + bộ phân loại tuyến tính. Track S, trả xác suất (SVC: hiệu chỉnh sigmoid)."""
    track = "S"

    def __init__(self, classes: Sequence[str], vec: str, fold: bool, clf: str, c: float, cache: Optional[VecCache] = None):
        self.classes = list(classes)
        self.vec_kind, self.fold, self.clf_kind, self.c = vec, fold, clf, c
        self.cache = cache
        self.name = config_name(vec, fold, clf, c)

    # -- xử lý văn bản
    def _prep(self, text: str) -> str:
        return normalize_text(text) if self.fold else raw_norm(text)

    def _vec_key(self, docs):
        return (self.vec_kind, self.fold, VecCache.key_docs(docs))

    def fit(self, train_docs):
        y = [d.target(self.track) for d in train_docs]
        key = self._vec_key(train_docs)
        if self.cache is not None and key in self.cache.vec:
            self.vectorizer, X = self.cache.vec[key]
        else:
            self.vectorizer = make_vectorizer(self.vec_kind)
            X = self.vectorizer.fit_transform([self._prep(d.text) for d in train_docs])
            if self.cache is not None:
                self.cache.vec[key] = (self.vectorizer, X)
        self._train_key = key
        counts = np.bincount([self.classes.index(v) for v in y], minlength=len(self.classes))
        if self.clf_kind == "lr":
            self.model = LogisticRegression(C=self.c, max_iter=3000, class_weight="balanced")
            self.model.fit(X, y)
        elif self.clf_kind == "svc":
            base = LinearSVC(C=self.c, class_weight="balanced", max_iter=20000)
            cv = int(min(3, counts[counts > 0].min()))
            if cv >= 2:
                self.model = CalibratedClassifierCV(base, cv=cv, method="sigmoid")
            else:  # quá ít mẫu để hiệu chỉnh -> dùng softmax của decision_function
                self.model = base
            self.model.fit(X, y)
        elif self.clf_kind == "cnb":
            self.model = ComplementNB(alpha=self.c)
            self.model.fit(X, y)
        else:
            raise ValueError(self.clf_kind)
        self.model_classes = list(self.model.classes_)
        return self

    def _proba(self, X) -> np.ndarray:
        m = self.model
        if hasattr(m, "predict_proba"):
            pr = m.predict_proba(X)
        else:
            z = m.decision_function(X)
            z = z - z.max(axis=1, keepdims=True)
            pr = np.exp(z)
            pr /= pr.sum(axis=1, keepdims=True)
        full = np.zeros((pr.shape[0], len(self.classes)))
        for j, c in enumerate(self.model_classes):
            full[:, self.classes.index(c)] = pr[:, j]
        return full

    def predict(self, docs):
        if self.cache is not None:
            tk = (self._train_key, VecCache.key_docs(docs))
            X = self.cache.test.get(tk)
            if X is None:
                X = self.vectorizer.transform([self._prep(d.text) for d in docs])
                self.cache.test[tk] = X
        else:
            X = self.vectorizer.transform([self._prep(d.text) for d in docs])
        pr = self._proba(X)
        labels = [self.classes[i] for i in pr.argmax(axis=1)]
        return Prediction(labels, pr, list(self.classes))

    def size_bytes(self) -> int:
        return len(pickle.dumps((self.vectorizer, self.model), protocol=pickle.HIGHEST_PROTOCOL))


def config_name(vec: str, fold: bool, clf: str, c: float) -> str:
    return f"tfidf_{vec}_{clf}_{'fold' if fold else 'raw'}_C{c:g}"


# ---------------------------------------------------------------------------
# Majority, cổng luật
# ---------------------------------------------------------------------------
class MajorityPredictor(Predictor):
    name = "majority"
    track = "S"

    def __init__(self, classes: Sequence[str]):
        self.classes = list(classes)

    def fit(self, train_docs):
        cnt = np.array([sum(d.label_s == c for d in train_docs) for c in self.classes], dtype=float)
        self.prior = cnt / cnt.sum()
        self.top = self.classes[int(cnt.argmax())]
        return self

    def predict(self, docs):
        return Prediction([self.top] * len(docs), np.tile(self.prior, (len(docs), 1)), list(self.classes))

    def size_bytes(self):
        return len(pickle.dumps(self.prior))


class RuleGatePredictor(Predictor):
    """Cổng luật tiêu đề của CascadedClassifier, Kev TẮT (kev_endpoint=None). Không tinh chỉnh luật.
    track='Z': nhãn đầy đủ + UNKNOWN khi abstain. track='S': ánh xạ sang Track S (loại không thuộc Track S hoặc UNKNOWN -> RARE_OR_OTHER)."""

    def __init__(self, track: str = "Z", s_classes: Optional[Sequence[str]] = None):
        from src.classification.system_one_classifier import CascadedClassifier

        self.track = track
        self.name = "rule_gate" if track == "Z" else "rule_gate_mapped_to_S"
        self.s_classes = list(s_classes or [])
        self.clf = CascadedClassifier(kev_endpoint=None)

    def predict(self, docs):
        from src.common.contracts import DocumentSlice

        out = []
        for d in docs:
            sl = DocumentSlice(slice_id=d.doc_id, start_page=1, end_page=1, page_count=1, combined_text=d.text or "")
            res = self.clf.classify_slice(sl)
            lab = res.predicted_category
            if lab not in set(self.clf.taxonomy.class_ids):
                lab = UNKNOWN
            if self.track == "S":
                lab = lab if lab in self.s_classes and lab != POOL else POOL
            out.append(lab)
        return Prediction(out)

    def size_bytes(self):
        return 0


# ---------------------------------------------------------------------------
# Baseline ảnh (page 1 -> thumbnail xám -> PCA/HOG -> LR)
# ---------------------------------------------------------------------------
THUMB_W, THUMB_H = 64, 90
HOG_W, HOG_H = 96, 128


def render_page1(pdf_path: Path, width: int = 192) -> np.ndarray:
    """Render trang 1 sang ảnh xám uint8 có bề rộng ~width px (PyMuPDF)."""
    import fitz

    with fitz.open(str(pdf_path)) as doc:
        page = doc[0]
        zoom = width / max(page.rect.width, 1.0)
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csGRAY, alpha=False)
        return np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width).copy()


def image_features(gray: np.ndarray) -> Dict[str, np.ndarray]:
    import cv2
    from skimage.feature import hog

    thumb = cv2.resize(gray, (THUMB_W, THUMB_H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    big = cv2.resize(gray, (HOG_W, HOG_H), interpolation=cv2.INTER_AREA)
    h = hog(big, orientations=9, pixels_per_cell=(16, 16), cells_per_block=(2, 2), feature_vector=True).astype(np.float32)
    return {"thumb": thumb.ravel(), "hog": h}


def build_visual_cache(docs: Sequence[Doc], cache_path: Path) -> Dict[str, Dict[str, np.ndarray]]:
    """Cache đặc trưng ảnh theo doc_id (git-ignored `_cache/`). Chỉ tính phần còn thiếu."""
    cache: Dict[str, Dict[str, np.ndarray]] = {}
    if cache_path.exists():
        z = np.load(cache_path, allow_pickle=True)
        cache = z["cache"].item()
    todo = [d for d in docs if d.doc_id not in cache]
    for d in todo:
        cache[d.doc_id] = image_features(render_page1(d.pdf_path))
    if todo:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cache_path, cache=np.array(cache, dtype=object))
    return cache


class VisualPredictor(Predictor):
    """kind='thumb': thumbnail 64x90 -> PCA(<=50) -> LR ; kind='hog': HOG -> LR.
    cache=None => render PDF trực tiếp trong predict (dùng để đo độ trễ thật, gồm cả bước render)."""
    track = "S"

    def __init__(self, classes: Sequence[str], kind: str, c: float, cache: Optional[dict] = None):
        self.classes = list(classes)
        self.kind, self.c, self.cache = kind, c, cache
        self.name = f"visual_{kind}_lr_C{c:g}"

    def _feat(self, docs):
        rows = []
        for d in docs:
            f = self.cache.get(d.doc_id) if self.cache is not None else None
            if f is None:
                f = image_features(render_page1(d.pdf_path))
            rows.append(f[self.kind])
        return np.vstack(rows)

    def fit(self, train_docs):
        X = self._feat(train_docs)
        y = [d.target(self.track) for d in train_docs]
        if self.kind == "thumb":
            self.pca = PCA(n_components=min(50, X.shape[0] - 1), random_state=0)
            X = self.pca.fit_transform(X)
        else:
            self.pca = None
        self.model = LogisticRegression(C=self.c, max_iter=3000, class_weight="balanced")
        self.model.fit(X, y)
        return self

    def predict(self, docs):
        X = self._feat(docs)
        if self.pca is not None:
            X = self.pca.transform(X)
        pr = self.model.predict_proba(X)
        full = np.zeros((pr.shape[0], len(self.classes)))
        for j, c in enumerate(self.model.classes_):
            full[:, self.classes.index(c)] = pr[:, j]
        return Prediction([self.classes[i] for i in full.argmax(axis=1)], full, list(self.classes))

    def size_bytes(self):
        return len(pickle.dumps((self.pca, self.model)))


# ---------------------------------------------------------------------------
# Lưới cấu hình (rất nhỏ)
# ---------------------------------------------------------------------------
# (family, vec, clf, [C...]) ; mỗi họ chạy với fold in (True, False)
TEXT_GRID = [
    ("word_lr", "word", "lr", [1.0, 10.0, 100.0]),
    ("char_lr", "char", "lr", [1.0, 10.0, 100.0]),
    ("char_svc", "char", "svc", [0.1, 1.0]),
    ("word_cnb", "word", "cnb", [0.1, 0.5]),
]
VISUAL_GRID = [("thumb", [1.0, 10.0]), ("hog", [1.0, 10.0])]


def text_configs() -> List[dict]:
    out = []
    for fam, vec, clf, cs in TEXT_GRID:
        for fold in (True, False):
            for c in cs:
                out.append(dict(family=fam, vec=vec, clf=clf, fold=fold, c=c, name=config_name(vec, fold, clf, c)))
    return out


def build_predictor(cfg: dict, classes: Sequence[str], vec_cache: Optional[VecCache] = None, visual_cache: Optional[dict] = None) -> Predictor:
    kind = cfg["kind"] if "kind" in cfg else "text"
    if cfg.get("family") == "majority":
        return MajorityPredictor(classes)
    if cfg.get("family") == "visual":
        return VisualPredictor(classes, cfg["vkind"], cfg["c"], visual_cache)
    if cfg.get("family") == "rule_gate_S":
        return RuleGatePredictor("S", classes)
    if cfg.get("family") == "rule_gate_Z":
        return RuleGatePredictor("Z")
    return TextPredictor(classes, cfg["vec"], cfg["fold"], cfg["clf"], cfg["c"], vec_cache)


def visual_configs() -> List[dict]:
    return [dict(family="visual", vkind=k, c=c, name=f"visual_{k}_lr_C{c:g}") for k, cs in VISUAL_GRID for c in cs]
