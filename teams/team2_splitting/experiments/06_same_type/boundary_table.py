r"""Thí nghiệm 06 - bảng phân tích từng ranh giới cùng loại (doc_id, trang, loại, các dấu hiệu "bản khác") + thống kê dấu hiệu theo nhóm.
KHÔNG in giá trị định danh (số hiệu, ngày...), chỉ in cờ khớp/khác. Chạy: .venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/06_same_type/boundary_table.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lib06 as L  # noqa: E402
import splitlib as sl  # noqa: E402
import pandas as pd  # noqa: E402
from src.splitting.identity import identity_features, page_identity  # noqa: E402
from src.splitting.learned import effective_prev  # noqa: E402
from src.splitting.learned_id import same_template_new_copy  # noqa: E402
from src.splitting.page_features import jaccard, page_feat  # noqa: E402


def main():
    gold = sl.load_gold()
    ids = sl.scope_doc_ids(gold, "dev")
    docs = sl.load_documents(ids)
    meta = gold.drop_duplicates("doc_id").set_index("doc_id")
    segs, sc = L.load_s10_labels(), L.load_scores()
    rows = []
    for d in ids:
        grp = meta.loc[d, "eval_group"]
        if grp not in sl.GROUPS:
            continue
        pages = [p.page_number for p in docs[d].pages]
        texts = [p.full_text for p in docs[d].pages]
        feats = [page_feat(t) for t in texts]
        idn = [page_identity(t) for t in texts]
        prev = effective_prev(feats)
        gg = sl.gold_for_doc(gold, d, len(texts)).set_index("page")
        s10 = L.simulate(sc[d], pages, segs[d])
        for i in range(1, len(texts)):
            j = prev[i]
            y = int(gg.loc[pages[i], "is_start"])
            if j is None:
                rows.append(dict(doc_id=d, group=grp, page=pages[i], type=gg.loc[pages[i], "page_doc_type"], y=y, blank=1))
                continue
            f = identity_features(idn[j], idn[i])
            pn_c, pn_p = feats[i].page_no, feats[j].page_no
            rows.append(dict(
                doc_id=d, group=grp, page=pages[i], type=gg.loc[pages[i], "page_doc_type"], y=y, blank=0, score=round(sc[d][i], 2),
                s10=int(pages[i] in s10), jac_head=round(jaccard(feats[j].head_tokens, feats[i].head_tokens), 2),
                title_top=int(feats[i].title_at_line_start), motto_top=int(feats[i].motto_top),
                pageno_restart=int(bool(pn_c and pn_c[0] == 1 and pn_c[1] >= 1)), pageno_prev_last=int(bool(pn_p and pn_p[1] > 0 and pn_p[0] == pn_p[1])),
                sig_cur=int(feats[i].signature_only), chars_cur=feats[i].n_chars,
                no_both=int(f[0]), no_differ=int(f[1]), date_both=int(f[3]), date_differ=int(f[4]), num_only_frac=round(f[5], 2),
                id_rule=int(same_template_new_copy(feats[j], feats[i], idn[j], idn[i]))))
    df = pd.DataFrame(rows)
    df.to_csv(HERE / "results" / "pair_signals_dev.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    so = df[df.group == "same_other"]
    print(so.drop(columns=["group"]).to_string(index=False))
    print()
    d2 = df[df.blank == 0]
    agg = d2.groupby(["group", "y"]).agg(n=("y", "size"), s10=("s10", "sum"), title_top=("title_top", "sum"), motto_top=("motto_top", "sum"),
                                         pageno_restart=("pageno_restart", "sum"), pageno_prev_last=("pageno_prev_last", "sum"), sig_cur=("sig_cur", "sum"),
                                         jac_ge_05=("jac_head", lambda s: int((s >= 0.5).sum())), no_both=("no_both", "sum"), no_differ=("no_differ", "sum"),
                                         date_differ=("date_differ", "sum"), id_rule=("id_rule", "sum"))
    print(agg.to_string())


if __name__ == "__main__":
    main()
