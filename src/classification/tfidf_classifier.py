"""tfidf_classifier.py - Bộ phân loại TF-IDF đã CHỐT (Track S): `tfidf_word_cnb_raw_C0.1`, có huấn luyện / lưu / nạp.

Cấu hình đã chốt cho điều kiện triển khai (nguồn văn bản `ocr_v2_p12`) trên DEV của thí nghiệm 01
(`teams/team3_classification/results/01_classical_baselines/tables/dev_selection.json`, `final_configs["ocr_v2_p12"][0]`):
  * văn bản: NFC + casefold + gộp khoảng trắng, KHÔNG bỏ dấu (`raw`);
  * TF-IDF theo từ, n-gram 1-2, sublinear_tf, min_df=2, không lowercase thêm (đã casefold ở bước trên);
  * `ComplementNB(alpha=0.1)`; độ tin cậy = xác suất lớn nhất (`predict_proba(...).max`).
Lớp mục tiêu là Track S: 10 loại có >= 10 tài liệu + `RARE_OR_OTHER` ("hãy đưa cho người"). TF-IDF không bao giờ được tự nhận
`RARE_OR_OTHER` (xem `cascade.run_cascade`).

Mã tái hiện NGUYÊN VĂN `TextPredictor` của `teams/.../01_classical_baselines/methods.py` để quyết định trùng từng tài liệu
(kiểm hồi quy: teams/team3_classification/experiments/03_src_cascade/).

Tệp lưu (thư mục `models/classification/<config>/`):
  model.joblib  : {vectorizer, model, classes, model_classes}  (pickle của scikit-learn: chỉ nạp tệp do chính mình huấn luyện)
  meta.json     : siêu dữ liệu truy vết - xem `TfidfMeta`.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

logger = logging.getLogger(__name__)

REPO = Path(__file__).resolve().parent.parent.parent
CONFIG_NAME = "tfidf_word_cnb_raw_C0.1"
ALPHA = 0.1
POOL = "RARE_OR_OTHER"
DEFAULT_DIR = REPO / "models" / "classification" / CONFIG_NAME

_WS = re.compile(r"\s+")


def raw_norm(text: str) -> str:
    """Không bỏ dấu: chỉ NFC + casefold + gộp khoảng trắng."""
    return _WS.sub(" ", unicodedata.normalize("NFC", text or "").casefold()).strip()


def make_vectorizer():
    from sklearn.feature_extraction.text import TfidfVectorizer
    return TfidfVectorizer(analyzer="word", ngram_range=(1, 2), token_pattern=r"(?u)\b\w+\b", sublinear_tf=True,
                           min_df=2, lowercase=False, dtype=np.float32)


class TfidfModelError(RuntimeError):
    """Không nạp được mô hình TF-IDF (thiếu tệp, sai checksum, siêu dữ liệu hỏng)."""


@dataclass
class TfidfMeta:
    config: str
    classes: List[str]
    labels_file: str
    labels_sha1_10: str
    text_source: str                      # vd 'ocr_v2_p12': trang 1-2 của OCR local, nối bằng '\n'
    train_split: str                      # 'DEV'
    train_doc_ids: List[str]              # CHỈ tài liệu DEV (kiểm khi huấn luyện)
    n_train: int
    class_counts: Dict[str, int]
    sklearn_version: str
    numpy_version: str
    python_version: str
    created_at: str
    model_sha256: str = ""
    notes: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TfidfPrediction:
    labels: List[str]
    confidence: np.ndarray                # xác suất lớn nhất của từng tài liệu
    proba: np.ndarray                     # (n, len(classes)) theo thứ tự `classes`
    classes: List[str]


class TfidfClassifier:
    def __init__(self, classes: Sequence[str], alpha: float = ALPHA):
        self.classes = list(classes)
        self.alpha = alpha
        self.name = CONFIG_NAME
        self.vectorizer = None
        self.model = None
        self.model_classes: List[str] = []
        self.meta: Optional[TfidfMeta] = None

    # --- huấn luyện / dự đoán
    def fit(self, texts: Sequence[str], labels: Sequence[str]) -> "TfidfClassifier":
        from sklearn.naive_bayes import ComplementNB
        unknown = sorted(set(labels) - set(self.classes))
        if unknown:
            raise ValueError(f"nhãn ngoài danh sách lớp: {unknown}")
        self.vectorizer = make_vectorizer()
        X = self.vectorizer.fit_transform([raw_norm(t) for t in texts])
        self.model = ComplementNB(alpha=self.alpha)
        self.model.fit(X, list(labels))
        self.model_classes = list(self.model.classes_)
        return self

    def predict(self, texts: Sequence[str]) -> TfidfPrediction:
        if self.model is None:
            raise TfidfModelError("TfidfClassifier chưa được huấn luyện hoặc nạp")
        X = self.vectorizer.transform([raw_norm(t) for t in texts])
        pr = self.model.predict_proba(X)
        full = np.zeros((pr.shape[0], len(self.classes)))
        for j, c in enumerate(self.model_classes):
            full[:, self.classes.index(c)] = pr[:, j]
        labels = [self.classes[i] for i in full.argmax(axis=1)]
        return TfidfPrediction(labels, full.max(axis=1), full, list(self.classes))

    # --- lưu / nạp
    def save(self, directory: Path | str, *, labels_file: str, labels_sha1_10: str, text_source: str, train_doc_ids: Sequence[str],
             train_labels: Sequence[str], train_split: str = "DEV", notes: str = "", extra: Optional[Dict[str, Any]] = None) -> TfidfMeta:
        """Ghi model.joblib + meta.json. `train_doc_ids` phải là tài liệu của `train_split` (người gọi chịu trách nhiệm; script huấn luyện kiểm)."""
        import platform
        import joblib
        import sklearn
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "model.joblib"
        joblib.dump({"vectorizer": self.vectorizer, "model": self.model, "classes": self.classes,
                     "model_classes": self.model_classes, "alpha": self.alpha}, path, compress=3)
        counts: Dict[str, int] = {}
        for y in train_labels:
            counts[y] = counts.get(y, 0) + 1
        meta = TfidfMeta(
            config=CONFIG_NAME, classes=list(self.classes), labels_file=str(labels_file), labels_sha1_10=labels_sha1_10,
            text_source=text_source, train_split=train_split, train_doc_ids=sorted(train_doc_ids), n_train=len(train_doc_ids),
            class_counts=dict(sorted(counts.items())), sklearn_version=sklearn.__version__, numpy_version=np.__version__,
            python_version=platform.python_version(), created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            model_sha256=_sha256(path), notes=notes, extra=extra or {})
        (directory / "meta.json").write_text(json.dumps(asdict(meta), ensure_ascii=False, indent=1), encoding="utf-8")
        self.meta = meta
        return meta

    @classmethod
    def load(cls, directory: Path | str = DEFAULT_DIR, *, strict_versions: bool = False) -> "TfidfClassifier":
        """Nạp mô hình. Sai checksum -> TfidfModelError. Khác phiên bản scikit-learn -> cảnh báo (hoặc lỗi nếu strict_versions)."""
        import joblib
        import sklearn
        directory = Path(directory)
        mp, jp = directory / "model.joblib", directory / "meta.json"
        if not mp.is_file() or not jp.is_file():
            raise TfidfModelError(
                f"Chưa có mô hình TF-IDF tại {directory}. Huấn luyện bằng: "
                f".venv\\Scripts\\python.exe -X utf8 scripts\\train_tfidf_classifier.py (xem models/README.md)")
        try:
            meta = TfidfMeta(**json.loads(jp.read_text(encoding="utf-8")))
        except (ValueError, TypeError) as e:
            raise TfidfModelError(f"meta.json hỏng ({jp}): {e}") from e
        if _sha256(mp) != meta.model_sha256:
            raise TfidfModelError(f"model.joblib không khớp checksum trong meta.json ({mp}); huấn luyện lại.")
        if meta.sklearn_version != sklearn.__version__:
            msg = (f"mô hình TF-IDF huấn luyện bằng scikit-learn {meta.sklearn_version}, đang chạy {sklearn.__version__}: "
                   "kết quả có thể lệch; huấn luyện lại bằng scripts/train_tfidf_classifier.py")
            if strict_versions:
                raise TfidfModelError(msg)
            logger.warning(msg)
        blob = joblib.load(mp)
        obj = cls(blob["classes"], blob.get("alpha", ALPHA))
        obj.vectorizer, obj.model, obj.model_classes, obj.meta = blob["vectorizer"], blob["model"], blob["model_classes"], meta
        return obj


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
