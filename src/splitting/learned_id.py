"""learned_id.py - Bộ phân loại cặp trang c2 + đặc trưng "BẢN KHÁC" (T5), và quy tắc "cùng mẫu, số hiệu khác".

Chỉ THÊM (không sửa `learned.py`; mô hình đã lưu `pair_gb_v0.joblib` vẫn là bản 30 đặc trưng):
* `IdPairBoundaryModel` = `PairBoundaryModel` + 8 đặc trưng định danh (`identity.py`) + 2 tích "mẫu giống x định danh khác" (40 đặc trưng).
* `fit_pair_model_id` - cùng giao diện `fit_pair_model`.
* `same_template_new_copy` - quy tắc: hai trang cùng mẫu (đầu trang giống) mà số hiệu ở đầu trang KHÁC => bản khác.
  `id_rule_flags` dùng nó để (a) THÊM ranh giới khi mô hình bỏ sót, `id_block_merge` để (b) chặn gộp lát cắt cùng loại.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from src.splitting.identity import ID_FEATURE_NAMES, identity_features, page_identity
from src.splitting.learned import (FEATURE_NAMES, PageTypeModel, PairBoundaryModel, effective_prev, make_pair_clf, oof_type_probs,
                                   pair_features)
from src.splitting.page_features import PageFeat, jaccard, page_feat

ID_PAIR_FEATURE_NAMES = FEATURE_NAMES + ID_FEATURE_NAMES + ["id_tmpl_x_no_differ", "id_tmpl_x_date_differ"]
TEMPLATE_JACCARD_MIN = 0.7      # đầu trang (6 dòng) giống nhau tối thiểu ngần này thì coi là "cùng mẫu"; giữa vùng bằng phẳng 0,5-0,8 của bảng độ nhạy (thí nghiệm 06)


def same_template_new_copy(fp: PageFeat, fc: PageFeat, ip, ic, jac_min: float = TEMPLATE_JACCARD_MIN) -> bool:
    """True nếu hai trang cùng mẫu (jaccard token đầu trang >= jac_min) VÀ cả hai có số hiệu đầu trang VÀ số hiệu khác nhau."""
    if jaccard(fp.head_tokens, fc.head_tokens) < jac_min:
        return False
    return bool(ip.head_no and ic.head_no and ip.head_no != ic.head_no)


def id_pair_features(fp, fc, xp, xc, pp, pc, ip, ic) -> np.ndarray:
    base = pair_features(fp, fc, xp, xc, pp, pc)
    idf = identity_features(ip, ic)
    tmpl = jaccard(fp.head_tokens, fc.head_tokens)
    # idf[1] = cờ số hiệu khác, idf[4] = cờ ngày khác
    return np.concatenate([base, np.asarray(idf, dtype=np.float64), [tmpl * idf[1], tmpl * idf[4]]])


class IdPairBoundaryModel(PairBoundaryModel):
    """PairBoundaryModel với đặc trưng định danh. Cùng `doc_scores` / `predict_flags` nên dùng được ở mọi nơi PairBoundaryModel dùng được."""

    def doc_scores(self, texts: Sequence[str]) -> np.ndarray:
        n = len(texts)
        scores = np.full(n, np.nan)
        feats = [page_feat(t) for t in texts]
        ids = [page_identity(t) for t in texts]
        X = self.type_model.transform(texts)
        P = self.type_model.proba(X)
        prev = effective_prev(feats)
        idx = [i for i in range(n) if prev[i] is not None]
        if not idx:
            return scores
        F = np.vstack([id_pair_features(feats[prev[i]], feats[i], X[prev[i]], X[i], P[prev[i]], P[i], ids[prev[i]], ids[i]) for i in idx])
        s = self.clf.predict_proba(F)[:, list(self.clf.classes_).index(1)]
        scores[idx] = s
        return scores


def fit_pair_model_id(page_text: Dict[str, str], page_type: Dict[str, str], page_group: Dict[str, str],
                      pairs: Sequence[Tuple[str, str, int]], kind: str = "gb", seed: int = 0, threshold: float = 0.5,
                      inner_splits: int = 4, meta: Optional[dict] = None) -> IdPairBoundaryModel:
    """Như `fit_pair_model` nhưng có đặc trưng định danh. Xác suất loại cho tầng cặp là OOF theo nhóm."""
    keys = sorted(page_text)
    texts = [page_text[k] for k in keys]
    tmodel = PageTypeModel(seed=seed).fit(texts, [page_type[k] for k in keys])
    X = tmodel.transform(texts)
    P = oof_type_probs(texts, [page_type[k] for k in keys], [page_group[k] for k in keys], tmodel.classes, inner_splits, seed)
    kidx = {k: i for i, k in enumerate(keys)}
    feats = {k: page_feat(page_text[k]) for k in keys}
    ids = {k: page_identity(page_text[k]) for k in keys}
    F = np.vstack([id_pair_features(feats[a], feats[b], X[kidx[a]], X[kidx[b]], P[kidx[a]], P[kidx[b]], ids[a], ids[b]) for a, b, _ in pairs])
    y = np.asarray([p[2] for p in pairs], dtype=int)
    clf = make_pair_clf(kind, seed)
    clf.fit(F, y)
    info = dict(kind=kind, n_pairs=int(len(y)), n_pos=int(y.sum()), n_pages=len(keys), seed=seed, features=ID_PAIR_FEATURE_NAMES)
    info.update(meta or {})
    return IdPairBoundaryModel(tmodel, clf, kind, threshold, info)


# ---------------------------------------------------------------------------
# Quy tắc "bản khác" trên cả tệp (không cần mô hình)
# ---------------------------------------------------------------------------
def id_rule_pages(texts: Sequence[str], jac_min: float = TEMPLATE_JACCARD_MIN) -> List[bool]:
    """Cờ theo trang: trang i (so với trang không trống gần nhất đứng trước) là "bản khác cùng mẫu". Trang 0 luôn False."""
    feats = [page_feat(t) for t in texts]
    ids = [page_identity(t) for t in texts]
    prev = effective_prev(feats)
    out = [False] * len(texts)
    for i in range(1, len(texts)):
        j = prev[i]
        if j is not None:
            out[i] = same_template_new_copy(feats[j], feats[i], ids[j], ids[i], jac_min)
    return out
