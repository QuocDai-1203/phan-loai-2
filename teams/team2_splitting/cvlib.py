"""cvlib.py - Cross-fitting có nhóm cho các phương pháp tách trang CÓ HỌC (thí nghiệm 03, 04).

Quy tắc (cứng):
* Không huấn luyện / chỉnh trên tệp đang chấm, cũng như trên tệp CÙNG nhóm biểu mẫu (cột `template_group`); riêng 5 bộ chứng từ xuất kho cùng
  một dạng (BSR) được gộp vào MỘT nhóm "FAMILY_bsr" để khi chấm một bộ, các bộ còn lại cũng bị giữ lại (khó hơn nhưng trung thực).
* Không bao giờ huấn luyện trên tài liệu TEST. Tập huấn luyện = tài liệu phạm vi dev (DEV + EXCLUDED_COMPOSITE) ngoài fold đang giữ lại,
  cộng composite tổng hợp sinh từ tài liệu đơn DEV của chính các nhóm huấn luyện.
* Số trên composite thật là CROSS-VALIDATED (dev-like), không phải tập TEST khóa.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "gold"))
import splitlib as sl  # noqa: E402
import make_synthetic as ms  # noqa: E402
from src.splitting.learned import BLANK_CHARS  # noqa: E402

N_FOLDS = 5
FOLD_SEED = 0
N_SYN_TRAIN = 400
N_SYN_EVAL_PER_FOLD = 80


def pkey(doc_id: str, page: int) -> str:
    return f"{doc_id}:{page}"


def cv_group_map(gold: pd.DataFrame, ids: Sequence[str], merge_family: bool = True) -> Dict[str, str]:
    """doc_id -> nhóm chia. Các bộ chứng từ khác loại có CÙNG chuỗi loại segment (cùng nhà cung cấp) được gộp thành FAMILY_bsr."""
    d = gold[gold.doc_id.isin(ids)]
    meta = d.drop_duplicates("doc_id").set_index("doc_id")
    sig = {}
    for did, sub in d[d.eval_group == "mixed"].groupby("doc_id"):
        sig[did] = tuple(sub.sort_values("page").drop_duplicates("segment_idx").page_doc_type)
    from collections import Counter
    cnt = Counter(sig.values())
    out = {}
    for did in ids:
        grp = str(meta.loc[did, "template_group"]) or did
        if merge_family and did in sig and cnt[sig[did]] >= 2:
            grp = "FAMILY_bsr"
        out[did] = grp
    return out


def fold_assignment(gold: pd.DataFrame, ids: Sequence[str], n_splits: int = N_FOLDS, seed: int = FOLD_SEED,
                    merge_family: bool = True) -> Dict[str, int]:
    meta = gold.drop_duplicates("doc_id").set_index("doc_id")
    groups = cv_group_map(gold, ids, merge_family)
    y = [meta.loc[d, "eval_group"] for d in ids]
    sgk = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    fold = {}
    for k, (_, te) in enumerate(sgk.split(np.zeros(len(ids)), y, [groups[d] for d in ids])):
        for i in te:
            fold[ids[i]] = k
    return fold


@dataclass
class TrainData:
    """Dữ liệu huấn luyện của một fold. Khóa trang = 'doc_id:page' (trang trắng tổng hợp: '__blank__:0')."""
    page_text: Dict[str, str]
    page_type: Dict[str, str]
    page_group: Dict[str, str]
    pairs: List[Tuple[str, str, int]]            # (khóa trang trước hiệu dụng, khóa trang sau, nhãn)
    n_real_pairs: int = 0
    n_syn_pairs: int = 0
    train_doc_ids: List[str] = field(default_factory=list)
    syn_seed: int = 0


def _eff_pairs(keys: Sequence[str], texts: Sequence[str], starts: Sequence[int]) -> List[Tuple[str, str, int]]:
    """Cặp (trang không trống gần nhất đứng trước, trang i) cho mọi trang i không trống từ trang thứ 2."""
    out, last = [], None
    for k, t, s in zip(keys, texts, starts):
        if len(t.strip()) < BLANK_CHARS:
            continue
        if last is not None:
            out.append((last, k, int(s)))
        last = k
    return out


def build_train_data(gold: pd.DataFrame, docs: Dict[str, "sl.OCRDocumentResult"], train_ids: Sequence[str], groups: Dict[str, str],
                     n_syn: int = N_SYN_TRAIN, syn_seed: int = 0, use_real_composites: bool = True) -> TrainData:
    meta = gold.drop_duplicates("doc_id").set_index("doc_id")
    page_text, page_type, page_group, pairs = {}, {}, {}, []
    n_real = 0
    for d in train_ids:
        if meta.loc[d, "eval_group"] not in sl.GROUPS + ["single_page"]:
            continue
        if not use_real_composites and meta.loc[d, "eval_group"] in ("mixed", "same_other", "same_bb"):
            continue
        g = sl.gold_for_doc(gold, d, len(docs[d].pages)).set_index("page")
        keys, texts, starts = [], [], []
        for p in docs[d].pages:
            k = pkey(d, p.page_number)
            page_text[k] = p.full_text
            page_type[k] = str(g.loc[p.page_number, "page_doc_type"])
            page_group[k] = groups[d]
            keys.append(k)
            texts.append(p.full_text)
            starts.append(int(g.loc[p.page_number, "is_start"]))
        pr = _eff_pairs(keys, texts, starts)
        pairs += pr
        n_real += len(pr)
    # composite tổng hợp: chỉ từ tài liệu đơn DEV của các nhóm huấn luyện
    pool = ms.build_pool(gold, exclude_docs=set(gold.doc_id) - set(train_ids))
    ms.assert_pool_is_clean(pool, gold)
    n_syn_pairs = 0
    if n_syn > 0 and len(pool) >= 4:
        syn = ms.generate(pool, n_syn, syn_seed, id_prefix="tr")
        for sid, sub in syn.groupby("syn_id", sort=True):
            sub = sub.sort_values("pos")
            keys, texts, starts = [], [], []
            for r in sub.itertuples():
                if r.src_doc_id == ms.BLANK:
                    k, t = f"__blank__:{sid}:{r.pos}", ""
                else:
                    k = pkey(r.src_doc_id, r.src_page)
                    t = page_text.get(k)
                    if t is None:
                        t = next(p.full_text for p in docs[r.src_doc_id].pages if p.page_number == r.src_page)
                        page_text[k] = t
                        gg = sl.gold_for_doc(gold, r.src_doc_id, len(docs[r.src_doc_id].pages)).set_index("page")
                        page_type[k] = str(gg.loc[r.src_page, "page_doc_type"])
                        page_group[k] = groups[r.src_doc_id]
                keys.append(k)
                texts.append(t)
                starts.append(int(r.is_start))
            # chỉ lấy cặp "đường nối" (nhãn 1): cặp trong cùng tài liệu nguồn đã có trong tập thật
            seam = [p for p in _eff_pairs(keys, texts, starts) if p[2] == 1]
            pairs += seam
            n_syn_pairs += len(seam)
    return TrainData(page_text, page_type, page_group, pairs, n_real, n_syn_pairs, list(train_ids), syn_seed)


# ---------------------------------------------------------------------------
# Chạy cross-fitting
# ---------------------------------------------------------------------------
FlagFn = Callable[[Sequence[str]], List[bool]]
FitFn = Callable[[TrainData], "FlagFn | Dict[str, FlagFn]"]   # nhận dữ liệu huấn luyện, trả hàm (hoặc dict hậu tố -> hàm) texts -> cờ "mở tài liệu mới"


def flags_to_starts(flags: Sequence[bool], docs_pages: Sequence[int]) -> Set[int]:
    return {docs_pages[i] for i, f in enumerate(flags) if f and i > 0}


def run_cv(fit_fns: Dict[str, FitFn], gold: pd.DataFrame, docs: Dict[str, "sl.OCRDocumentResult"], dev_ids: Sequence[str],
           test_ids: Sequence[str] = (), n_folds: int = N_FOLDS, fold_seed: int = FOLD_SEED, verbose: bool = True,
           want_synthetic: bool = True, merge_family: bool = True):
    """Trả về (preds_real, preds_syn, syn_gold, syn_docs, final_preds_test):
    preds_real[name][doc_id] = tập trang bắt đầu (OOF) cho mọi tệp dev; preds_syn[name][syn_id] cho composite tổng hợp giữ lại."""
    from collections import defaultdict
    groups = cv_group_map(gold, dev_ids, merge_family)
    fold = fold_assignment(gold, dev_ids, n_folds, fold_seed, merge_family)
    meta = gold.drop_duplicates("doc_id").set_index("doc_id")
    preds_real: Dict[str, Dict[str, Set[int]]] = defaultdict(dict)
    preds_syn: Dict[str, Dict[str, Set[int]]] = defaultdict(dict)
    syn_parts, syn_docs_all = [], {}
    for k in range(n_folds):
        held = [d for d in dev_ids if fold[d] == k]
        train = [d for d in dev_ids if fold[d] != k]
        td = build_train_data(gold, docs, train, groups, syn_seed=100 + k)
        if verbose:
            print(f"[fold {k}] giữ lại {len(held)} tệp, huấn luyện {len(train)} tệp; cặp thật {td.n_real_pairs}, cặp đường nối tổng hợp {td.n_syn_pairs}",
                  flush=True)
        # composite tổng hợp giữ lại: từ tài liệu đơn DEV thuộc fold k
        syn = None
        if want_synthetic:
            pool_k = ms.build_pool(gold, exclude_docs=set(gold.doc_id) - set(held))
            if len(pool_k) >= 4:
                syn = ms.generate(pool_k, N_SYN_EVAL_PER_FOLD, 1000 + k, id_prefix=f"ev{k}_")
                sdocs = ms.synthetic_to_documents(syn, docs)
                syn_parts.append(syn)
                syn_docs_all.update(sdocs)
        for name0, fit in fit_fns.items():
            res = fit(td)
            variants = res if isinstance(res, dict) else {"": res}
            for suffix, flag_fn in variants.items():
                name = name0 + suffix
                for d in held:
                    if meta.loc[d, "eval_group"] not in sl.GROUPS:
                        continue
                    pages = [p.page_number for p in docs[d].pages]
                    preds_real[name][d] = flags_to_starts(flag_fn([p.full_text for p in docs[d].pages]), pages)
                if syn is not None:
                    for sid, sd in sdocs.items():
                        if sid.startswith(f"ev{k}_"):
                            preds_syn[name][sid] = flags_to_starts(flag_fn([p.full_text for p in sd.pages]), [p.page_number for p in sd.pages])
    syn_all = pd.concat(syn_parts, ignore_index=True) if syn_parts else pd.DataFrame()
    syn_gold = ms.synthetic_gold(syn_all) if len(syn_all) else pd.DataFrame()
    final_test: Dict[str, Dict[str, Set[int]]] = defaultdict(dict)
    if test_ids:
        td = build_train_data(gold, docs, list(dev_ids), groups, syn_seed=99)
        for name0, fit in fit_fns.items():
            res = fit(td)
            variants = res if isinstance(res, dict) else {"": res}
            for suffix, flag_fn in variants.items():
                for d in test_ids:
                    if meta.loc[d, "eval_group"] not in sl.GROUPS:
                        continue
                    pages = [p.page_number for p in docs[d].pages]
                    final_test[name0 + suffix][d] = flags_to_starts(flag_fn([p.full_text for p in docs[d].pages]), pages)
    return preds_real, preds_syn, syn_gold, syn_docs_all, final_test, fold


def eval_synthetic(preds_syn: Dict[str, Set[int]], syn_gold: pd.DataFrame, syn_docs: Dict[str, "sl.OCRDocumentResult"]) -> pd.DataFrame:
    """Chấm composite tổng hợp bằng cùng hàm score_file. group = 'syn_<recipe>'."""
    rows = []
    meta = syn_gold.drop_duplicates("doc_id").set_index("doc_id")
    for sid, pred in preds_syn.items():
        doc = syn_docs[sid]
        g = syn_gold[syn_gold.doc_id == sid].sort_values("page")
        rows.append(sl.score_file(sid, meta.loc[sid, "eval_group"], doc, g, pred))
    return pd.DataFrame(rows, columns=sl.PER_FILE_COLS)
