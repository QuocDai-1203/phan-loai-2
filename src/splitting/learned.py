"""learned.py - Hai phương pháp tách trang có học (Nhóm 2), chạy hoàn toàn trên CPU, không gọi dịch vụ ngoài.

* `PageTypeModel`  - TF-IDF (từ 1-2) + hồi quy logistic, phân loại LOẠI của từng trang (nhãn = loại của segment chứa trang).
* `TypeMergeSplitter` - (b) gộp trang liên tiếp cùng loại dự đoán; kèm "dấu hiệu bản khác" cho chuỗi cùng loại.
* `PairBoundaryModel` - (c) bộ phân loại cặp trang (trang i-1 hiệu dụng, trang i) -> điểm "trang i mở tài liệu mới".

Quy ước dùng chung (theo mục 7.2 của docs/LABELING_GUIDELINE.md):
* Trang gần như trống (< BLANK_CHARS ký tự) luôn là trang tiếp nối; trang kế tiếp so sánh với trang KHÔNG trống gần nhất đứng trước.
* Trang không trống đầu tiên của tệp không bao giờ là ranh giới (trang 1 mặc định là trang đầu).
* `score` của PairBoundaryModel là điểm thô của bộ phân loại (xác suất CHƯA hiệu chỉnh trên miền thật).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import scipy.sparse as sp
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from src.common.text_norm import normalize_text
from src.splitting.page_features import PageFeat, jaccard, page_feat
from src.splitting.rules_v2 import DEFAULT_CONFIG, is_start_v2

BLANK_CHARS = 30


# ---------------------------------------------------------------------------
# Loại của từng trang
# ---------------------------------------------------------------------------
class PageTypeModel:
    def __init__(self, c: float = 10.0, max_features: int = 40000, seed: int = 0):
        self.c, self.max_features, self.seed = c, max_features, seed
        self.vec: Optional[TfidfVectorizer] = None
        self.clf: Optional[LogisticRegression] = None
        self.classes: List[str] = []

    @staticmethod
    def _prep(t: str) -> str:
        return normalize_text(t)

    def fit(self, texts: Sequence[str], labels: Sequence[str]) -> "PageTypeModel":
        self.vec = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), token_pattern=r"(?u)\b\w+\b", sublinear_tf=True, min_df=2,
                                   lowercase=False, max_features=self.max_features, dtype=np.float32)
        X = self.vec.fit_transform([self._prep(t) for t in texts])
        self.clf = LogisticRegression(C=self.c, max_iter=2000, random_state=self.seed)
        self.clf.fit(X, list(labels))
        self.classes = list(self.clf.classes_)
        return self

    def transform(self, texts: Sequence[str]) -> sp.csr_matrix:
        return self.vec.transform([self._prep(t) for t in texts]).tocsr()

    def proba(self, X) -> np.ndarray:
        return self.clf.predict_proba(X)


def _row_cos(xa, xb) -> float:
    return float(xa.multiply(xb).sum())  # hàng đã L2-chuẩn hóa


def effective_prev(feats: Sequence[PageFeat]) -> List[Optional[int]]:
    """Với mỗi trang i: chỉ số trang không trống gần nhất đứng trước (None nếu chưa có / trang i trống)."""
    out, last = [], None
    for i, f in enumerate(feats):
        if f.n_chars < BLANK_CHARS:
            out.append(None)
            continue
        out.append(last)
        last = i
    return out


# ---------------------------------------------------------------------------
# (b) gộp trang cùng loại
# ---------------------------------------------------------------------------
@dataclass
class TypeMergeConfig:
    tau: float = 0.5               # cả hai trang phải có xác suất loại >= tau mới coi là "đổi loại"
    use_copy_signal: bool = True   # chuỗi cùng loại: tách khi trang trông như trang đầu VÀ số hiệu/ngày khác trang trước
    id_jaccard_max: float = 0.34


class TypeMergeSplitter:
    def __init__(self, type_model: PageTypeModel, cfg: Optional[TypeMergeConfig] = None):
        self.type_model = type_model
        self.cfg = cfg or TypeMergeConfig()
        self.boundary_method = "model"

    def predict_flags(self, texts: Sequence[str]) -> List[bool]:
        feats = [page_feat(t) for t in texts]
        P = self.type_model.proba(self.type_model.transform(texts))
        prev = effective_prev(feats)
        flags = [True] + [False] * (len(texts) - 1)
        for i in range(1, len(texts)):
            j = prev[i]
            if j is None:
                continue
            ti, tj = int(P[i].argmax()), int(P[j].argmax())
            if ti != tj:
                flags[i] = bool(P[i, ti] >= self.cfg.tau and P[j, tj] >= self.cfg.tau)
            elif self.cfg.use_copy_signal:
                looks_first = is_start_v2(feats[j], feats[i], DEFAULT_CONFIG)
                flags[i] = bool(looks_first and jaccard(feats[i].ids, feats[j].ids) <= self.cfg.id_jaccard_max)
        return flags


# ---------------------------------------------------------------------------
# (c) bộ phân loại cặp trang
# ---------------------------------------------------------------------------
FEATURE_NAMES = [
    "cos_tfidf", "jac_tokens", "jac_head", "jac_ids", "ids_both_empty", "docno_equal", "docno_differ", "dates_equal", "dates_differ",
    "type_dot", "type_same_argmax", "type_conf_cur", "type_conf_prev", "p_cur_is_prevtype", "p_prev_is_curtype",
    "motto_cur", "motto_prev", "title_cur", "title_prev", "rule_start",
    "pageno_cur_ge2", "pageno_cur_first_of_many", "pageno_prev_last", "pageno_prev_more",
    "log_chars_cur", "log_chars_prev", "len_ratio", "sig_cur", "sig_prev", "lines_cur",
]


def pair_features(fp: PageFeat, fc: PageFeat, xp, xc, pp: np.ndarray, pc: np.ndarray) -> np.ndarray:
    tp, tc = int(pp.argmax()), int(pc.argmax())
    both_ids_empty = float(not fp.ids and not fc.ids)
    docno_known = bool(fp.doc_no and fc.doc_no)
    dates_known = bool(fp.dates and fc.dates)
    pn_c, pn_p = fc.page_no, fp.page_no
    v = [
        _row_cos(xp, xc), jaccard(fp.tokens, fc.tokens), jaccard(fp.head_tokens, fc.head_tokens), jaccard(fp.ids, fc.ids), both_ids_empty,
        float(docno_known and fp.doc_no == fc.doc_no), float(docno_known and not (fp.doc_no & fc.doc_no)),
        float(dates_known and fp.dates == fc.dates), float(dates_known and not (fp.dates & fc.dates)),
        float(pp @ pc), float(tp == tc), float(pc.max()), float(pp.max()), float(pc[tp]), float(pp[tc]),
        float(fc.motto_top), float(fp.motto_top), float(fc.title_at_line_start), float(fp.title_at_line_start),
        float(is_start_v2(fp, fc, DEFAULT_CONFIG)),
        float(bool(pn_c and pn_c[0] >= 2)), float(bool(pn_c and pn_c[0] == 1 and pn_c[1] >= 2)),
        float(bool(pn_p and pn_p[1] > 0 and pn_p[0] == pn_p[1])), float(bool(pn_p and pn_p[1] > 0 and pn_p[0] < pn_p[1])),
        math.log1p(fc.n_chars), math.log1p(fp.n_chars), math.log1p(fc.n_chars) - math.log1p(fp.n_chars),
        float(fc.signature_only), float(fp.signature_only), float(fc.n_lines),
    ]
    return np.asarray(v, dtype=np.float64)


class PairBoundaryModel:
    """type_model + bộ phân loại cặp. kind='gb' (HistGradientBoosting nhỏ) hoặc 'lr' (hồi quy logistic chuẩn hóa)."""

    def __init__(self, type_model: PageTypeModel, clf, kind: str, threshold: float = 0.5, meta: Optional[dict] = None):
        self.type_model, self.clf, self.kind, self.threshold = type_model, clf, kind, threshold
        self.meta = meta or {}
        self.boundary_method = "model"

    def doc_scores(self, texts: Sequence[str]) -> np.ndarray:
        """Điểm thô cho từng trang (NaN: trang 1, trang trống, hoặc chưa có trang không trống đứng trước)."""
        n = len(texts)
        scores = np.full(n, np.nan)
        feats = [page_feat(t) for t in texts]
        X = self.type_model.transform(texts)
        P = self.type_model.proba(X)
        prev = effective_prev(feats)
        idx = [i for i in range(n) if prev[i] is not None]
        if not idx:
            return scores
        F = np.vstack([pair_features(feats[prev[i]], feats[i], X[prev[i]], X[i], P[prev[i]], P[i]) for i in idx])
        s = self.clf.predict_proba(F)[:, list(self.clf.classes_).index(1)]
        scores[idx] = s
        return scores

    def predict_flags(self, texts: Sequence[str], threshold: Optional[float] = None) -> List[bool]:
        thr = self.threshold if threshold is None else threshold
        s = self.doc_scores(texts)
        return [True] + [bool(not np.isnan(x) and x >= thr) for x in s[1:]]


def make_pair_clf(kind: str, seed: int = 0):
    if kind == "gb":
        return HistGradientBoostingClassifier(max_depth=3, max_iter=150, learning_rate=0.08, l2_regularization=1.0, min_samples_leaf=10,
                                              class_weight="balanced", random_state=seed)
    if kind == "lr":
        return make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=3000, class_weight="balanced", random_state=seed))
    raise ValueError(kind)


def oof_type_probs(texts: Sequence[str], labels: Sequence[str], groups: Sequence[str], classes: Sequence[str], n_splits: int = 4,
                   seed: int = 0) -> np.ndarray:
    """Xác suất loại của từng trang dự đoán BỞI MÔ HÌNH KHÔNG THẤY nhóm của trang đó (để huấn luyện tầng cặp trang không bị lạc quan)."""
    n = len(texts)
    out = np.zeros((n, len(classes)))
    gk = GroupKFold(n_splits=min(n_splits, len(set(groups))))
    texts, labels, groups = list(texts), np.asarray(labels), np.asarray(groups)
    for tr, te in gk.split(np.zeros(n), labels, groups):
        m = PageTypeModel(seed=seed).fit([texts[i] for i in tr], labels[tr])
        p = m.proba(m.transform([texts[i] for i in te]))
        for j, c in enumerate(m.classes):
            out[te, list(classes).index(c)] = p[:, j]
    return out


def fit_pair_model(page_text: Dict[str, str], page_type: Dict[str, str], page_group: Dict[str, str],
                   pairs: Sequence[Tuple[str, str, int]], kind: str = "gb", seed: int = 0, threshold: float = 0.5,
                   inner_splits: int = 4, meta: Optional[dict] = None) -> PairBoundaryModel:
    """Huấn luyện. page_*: dict theo khóa trang (chuỗi bất kỳ, duy nhất). pairs: (khóa trang trước hiệu dụng, khóa trang sau, nhãn 0/1).
    Xác suất loại dùng cho đặc trưng của tầng cặp trang là OOF theo `page_group` (nhóm biểu mẫu)."""
    keys = sorted(page_text)
    texts = [page_text[k] for k in keys]
    tmodel = PageTypeModel(seed=seed).fit(texts, [page_type[k] for k in keys])
    X = tmodel.transform(texts)
    P = oof_type_probs(texts, [page_type[k] for k in keys], [page_group[k] for k in keys], tmodel.classes, inner_splits, seed)
    kidx = {k: i for i, k in enumerate(keys)}
    feats = {k: page_feat(page_text[k]) for k in keys}
    F = np.vstack([pair_features(feats[a], feats[b], X[kidx[a]], X[kidx[b]], P[kidx[a]], P[kidx[b]]) for a, b, _ in pairs])
    y = np.asarray([p[2] for p in pairs], dtype=int)
    clf = make_pair_clf(kind, seed)
    clf.fit(F, y)
    info = dict(kind=kind, n_pairs=int(len(y)), n_pos=int(y.sum()), n_pages=len(keys), seed=seed, features=FEATURE_NAMES)
    info.update(meta or {})
    return PairBoundaryModel(tmodel, clf, kind, threshold, info)


# ---------------------------------------------------------------------------
# Lưu / nạp mô hình (artefact ở teams/team2_splitting/models/)
# ---------------------------------------------------------------------------
import hashlib  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402

MODELS_DIR = Path(__file__).resolve().parents[2] / "teams" / "team2_splitting" / "models"
DEFAULT_MODEL_FILE = "pair_gb_v0.joblib"


def save_model(model: PairBoundaryModel, path: Path, training_info: dict) -> Path:
    """Ghi mô hình + tệp mô tả `<tên>.json` (sha256 của tệp, phiên bản thư viện, sha nhãn huấn luyện...)."""
    import joblib
    import sklearn
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path, compress=3)
    info = dict(training_info)
    info.update(file=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), sklearn=sklearn.__version__, numpy=np.__version__,
                kind=model.kind, threshold=model.threshold, model_meta={k: v for k, v in model.meta.items() if k != "features"},
                features=FEATURE_NAMES)
    path.with_suffix(".json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_model(path: Path) -> PairBoundaryModel:
    """Nạp mô hình, KIỂM sha256 với tệp .json cạnh nó (joblib/pickle chỉ an toàn với tệp tin cậy; sha chống tệp bị thay)."""
    import joblib
    path = Path(path)
    meta_path = path.with_suffix(".json")
    if not path.exists() or not meta_path.exists():
        raise FileNotFoundError(f"thiếu mô hình hoặc tệp mô tả: {path} / {meta_path}. Huấn luyện bằng teams/team2_splitting/experiments/04_pair_classifier/save_model.py")
    info = json.loads(meta_path.read_text(encoding="utf-8"))
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    if sha != info.get("sha256"):
        raise ValueError(f"sha256 của {path.name} không khớp tệp mô tả: không nạp")
    return joblib.load(path)


def load_default_model() -> PairBoundaryModel:
    return load_model(MODELS_DIR / DEFAULT_MODEL_FILE)
