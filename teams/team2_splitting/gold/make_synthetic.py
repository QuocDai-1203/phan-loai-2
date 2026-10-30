r"""make_synthetic.py - Sinh COMPOSITE TỔNG HỢP (seed cố định) từ tài liệu đơn, CHỈ để huấn luyện / chỉnh phương pháp học.

Chạy từ gốc repo:
    .venv\Scripts\python.exe -X utf8 teams/team2_splitting/gold/make_synthetic.py            # seed 20261012, 400 composite
    .venv\Scripts\python.exe -X utf8 teams/team2_splitting/gold/make_synthetic.py --seed 7 --n 200 --out /tmp/x.csv

Quy tắc chống rò rỉ (được kiểm tra bằng `assert_pool_is_clean`):
  * chỉ lấy tài liệu có `split == "DEV"` trong data/splits/splits.csv (KHÔNG lấy TEST, không lấy EXCLUDED_COMPOSITE);
  * chỉ lấy tài liệu ĐƠN (nhóm `negative` hoặc `single_page` của đáp án) => không bao giờ có trang của 21 composite thật;
  * khi dùng trong CV, thí nghiệm gọi `generate()` với `pool` đã loại các nhóm biểu mẫu của fold bị giữ lại.

Công thức (recipe), tỉ lệ cố định ở RECIPE_WEIGHTS:
  bundle    - bộ chứng từ chuyến hàng: phiếu xuất kho -> biên bản giao nhận -> biên bản lấy mẫu (loại nào có tài liệu đơn)
  contract  - hợp đồng (HD_*) + giấy chứng nhận đăng ký doanh nghiệp
  same_type - N (2..6) tài liệu CÙNG loại liên tiếp (một nửa lấy cùng nhóm biểu mẫu, một nửa khác nhóm)
  mixed     - 2..5 tài liệu loại bất kỳ, có thể chèn trang trắng sau tài liệu (trang trắng thuộc tài liệu đứng trước, mục 7.2)

Mỗi tài liệu nguồn đóng góp: toàn bộ trang nếu <= 6 trang, ngược lại 3 trang đầu + trang cuối đã OCR.
Hạn chế (cần nói khi đọc kết quả): mọi trang đến từ các lần quét độc lập nên ranh giới tổng hợp dễ hơn thật; kho không có tài liệu đơn
loại CHUNG_THU_CHAT_LUONG, và chỉ có 2 tài liệu đơn BB_LAY_MAU ở DEV, nên công thức `bundle` không tái tạo đủ bộ 4 chứng từ.
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import splitlib as sl  # noqa: E402

DEFAULT_SEED = 20261012
RECIPE_WEIGHTS = {"bundle": 0.25, "contract": 0.15, "same_type": 0.30, "mixed": 0.30}
BLANK = "__blank__"
MAX_FULL = 6


def build_pool(gold: pd.DataFrame, exclude_groups: Optional[set] = None, exclude_docs: Optional[set] = None) -> pd.DataFrame:
    """Bảng tài liệu đơn đủ điều kiện: doc_id, doc_type, template_group, n_avail (số trang có văn bản)."""
    d = gold[(gold.split == "DEV") & gold.eval_group.isin(["negative", "single_page"])]
    d = d[d.ocr_available.astype(str) == "1"]
    pool = (d.groupby("doc_id").agg(doc_type=("page_doc_type", "first"), template_group=("template_group", "first"),
                                    n_avail=("page", "max")).reset_index())
    if exclude_groups:
        pool = pool[~pool.template_group.isin(exclude_groups)]
    if exclude_docs:
        pool = pool[~pool.doc_id.isin(exclude_docs)]
    return pool.reset_index(drop=True)


def assert_pool_is_clean(pool: pd.DataFrame, gold: pd.DataFrame) -> None:
    meta = gold.drop_duplicates("doc_id").set_index("doc_id")
    bad = pool[~pool.doc_id.map(lambda x: meta.loc[x, "split"] == "DEV" and meta.loc[x, "eval_group"] in ("negative", "single_page"))]
    assert bad.empty, f"pool chứa tài liệu không hợp lệ: {bad.doc_id.tolist()[:5]}"


def _pages_of(doc_id: str, n_avail: int) -> List[int]:
    if n_avail <= MAX_FULL:
        return list(range(1, n_avail + 1))
    return [1, 2, 3, n_avail]


def _pick(rng: random.Random, pool: pd.DataFrame, pred) -> Optional[pd.Series]:
    sub = pool[pool.doc_type.map(pred)]
    if sub.empty:
        return None
    return sub.iloc[rng.randrange(len(sub))]


def _recipe_docs(rng: random.Random, pool: pd.DataFrame, recipe: str) -> List[pd.Series]:
    if recipe == "bundle":
        seq = []
        for t in ("PHIEU_XUAT_KHO", "BB_GIAO_NHAN_HANG_HOA", "BB_LAY_MAU", "CHUNG_THU_CHAT_LUONG"):
            r = _pick(rng, pool, lambda x, t=t: x == t)
            if r is not None:
                seq.append(r)
        return seq if len(seq) >= 2 else []
    if recipe == "contract":
        a = _pick(rng, pool, lambda x: str(x).startswith("HD_"))
        b = _pick(rng, pool, lambda x: x == "GCN_DKDN")
        return [a, b] if a is not None and b is not None else []
    if recipe == "same_type":
        counts = pool.doc_type.value_counts()
        types = [t for t, c in counts.items() if c >= 2]
        if not types:
            return []
        t = rng.choice(sorted(types))
        sub = pool[pool.doc_type == t]
        k = min(len(sub), rng.randint(2, 6))
        if rng.random() < 0.5:   # cùng nhóm biểu mẫu nếu có thể
            g = sub.template_group.value_counts()
            big = [x for x, c in g.items() if c >= 2]
            if big:
                sub = sub[sub.template_group == rng.choice(sorted(big))]
                k = min(len(sub), k)
        idx = rng.sample(range(len(sub)), k)
        return [sub.iloc[i] for i in idx]
    if recipe == "mixed":
        k = rng.randint(2, 5)
        types = sorted(pool.doc_type.unique())
        out, used = [], set()
        for _ in range(k):
            t = rng.choice(types)
            sub = pool[(pool.doc_type == t) & (~pool.doc_id.isin(used))]
            if sub.empty:
                continue
            r = sub.iloc[rng.randrange(len(sub))]
            used.add(r.doc_id)
            out.append(r)
        return out if len(out) >= 2 else []
    raise ValueError(recipe)


def generate(pool: pd.DataFrame, n: int, seed: int, id_prefix: str = "syn") -> pd.DataFrame:
    """Trả về bảng các trang tổng hợp: syn_id, pos (1..), src_doc_id, src_page (0 với trang trắng), is_start, page_doc_type, recipe."""
    rng = random.Random(seed)
    names = list(RECIPE_WEIGHTS)
    weights = [RECIPE_WEIGHTS[k] for k in names]
    rows, made, tries = [], 0, 0
    while made < n and tries < n * 20:
        tries += 1
        recipe = rng.choices(names, weights)[0]
        docs = [d for d in _recipe_docs(rng, pool, recipe) if d is not None]
        if len(docs) < 2:
            continue
        syn_id = f"{id_prefix}{made:04d}"
        pos = 0
        for k, d in enumerate(docs):
            pages = _pages_of(d.doc_id, int(d.n_avail))
            for j, p in enumerate(pages):
                pos += 1
                rows.append(dict(syn_id=syn_id, pos=pos, src_doc_id=d.doc_id, src_page=p, is_start=int(j == 0),
                                 page_doc_type=d.doc_type, recipe=recipe, segment_idx=k))
            if recipe == "mixed" and rng.random() < 0.25 and k < len(docs) - 1:
                pos += 1   # trang trắng, thuộc tài liệu đứng trước
                rows.append(dict(syn_id=syn_id, pos=pos, src_doc_id=BLANK, src_page=0, is_start=0, page_doc_type=d.doc_type,
                                 recipe=recipe, segment_idx=k))
        made += 1
    return pd.DataFrame(rows)


def synthetic_to_documents(syn: pd.DataFrame, ocr_docs: Dict[str, "sl.OCRDocumentResult"]) -> Dict[str, "sl.OCRDocumentResult"]:
    """Dựng OCRDocumentResult cho từng composite tổng hợp từ văn bản của tài liệu nguồn (trang trắng = chuỗi rỗng)."""
    out = {}
    for sid, sub in syn.groupby("syn_id", sort=True):
        pages = []
        for r in sub.sort_values("pos").itertuples():
            if r.src_doc_id == BLANK:
                txt = ""
            else:
                txt = next(p.full_text for p in ocr_docs[r.src_doc_id].pages if p.page_number == r.src_page)
            pages.append(sl.OCRPageResult(page_number=int(r.pos), width=0, height=0, full_text=txt))
        out[sid] = sl.OCRDocumentResult(file_name=f"{sid}.pdf", total_pages=len(pages), pages=pages)
    return out


def synthetic_gold(syn: pd.DataFrame) -> pd.DataFrame:
    """Đáp án dạng giống boundary_gold (cột doc_id=syn_id, page=pos, eval_group='syn_<recipe>') để dùng lại hàm chấm."""
    g = syn.rename(columns={"syn_id": "doc_id", "pos": "page"}).copy()
    g["eval_group"] = "syn_" + g["recipe"]
    return g[["doc_id", "page", "is_start", "segment_idx", "page_doc_type", "eval_group", "src_doc_id", "src_page"]]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--out", default=str(HERE / "synthetic_v0.csv"))
    a = ap.parse_args(argv)
    gold = sl.load_gold()
    pool = build_pool(gold)
    assert_pool_is_clean(pool, gold)
    syn = generate(pool, a.n, a.seed)
    syn.to_csv(a.out, index=False, encoding="utf-8")
    print(f"pool: {len(pool)} tài liệu đơn DEV ({pool.doc_type.nunique()} loại); sinh {syn.syn_id.nunique()} composite, {len(syn)} trang, "
          f"{int(syn[syn.pos >= 2].is_start.sum())} ranh giới; seed={a.seed}")
    summ = syn.groupby("recipe").agg(composites=("syn_id", "nunique"), pages=("pos", "size"))
    summ["boundaries"] = syn[syn.pos >= 2].groupby("recipe").is_start.sum()
    print(summ.to_string())
    print("đã ghi", a.out)


if __name__ == "__main__":
    main()
