r"""Đo độ đồng thuận giữa hai annotator trên các tài liệu DUY NHẤT và xuất danh sách bất đồng để phân xử.

Chạy:  .venv\Scripts\python -X utf8 teams\00_data_and_eval\annotation\agreement.py
"""
import glob, json, re, unicodedata
from pathlib import Path
import pandas as pd
from sklearn.metrics import cohen_kappa_score

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def main():
    m = pd.read_csv(ROOT / "data/manifest.csv", encoding="utf-8-sig", dtype=str).fillna("")
    m["key"] = m.apply(lambda r: r["exact_dup_group"] or r["doc_id"], axis=1)
    reps = m.sort_values("relative_path").drop_duplicates("key")
    a = pd.read_csv(HERE / "annotator_A_opus_designer.csv", encoding="utf-8-sig", dtype=str).fillna("")
    b = pd.concat([pd.read_csv(f, encoding="utf-8-sig", dtype=str).fillna("") for f in sorted(glob.glob(str(HERE / "annotator_B_sonnet_part*.csv")))])
    b.to_csv(HERE / "annotator_B_sonnet.csv", index=False, encoding="utf-8-sig")
    # nhãn A phải nhất quán trong nhóm trùng byte
    aa = a.merge(m[["doc_id", "key"]], on="doc_id")
    bad = aa.groupby("key").doc_type.nunique()
    assert (bad <= 1).all(), f"Annotator A gán khác nhau trong nhóm trùng: {bad[bad > 1].index.tolist()}"
    d = reps[["doc_id", "file_name", "folder_label", "page_count", "template_group"]].merge(
        a.add_suffix("_A").rename(columns={"doc_id_A": "doc_id"}), on="doc_id").merge(
        b.add_suffix("_B").rename(columns={"doc_id_B": "doc_id"}), on="doc_id", how="left")
    assert d.doc_type_B.notna().all(), "Thiếu nhãn annotator B"
    # tệp được nêu tên trong ví dụ của guideline -> annotator có thể đã thấy lời giải
    guide = unicodedata.normalize("NFC", (ROOT / "docs/LABELING_GUIDELINE.md").read_text(encoding="utf-8"))
    d["in_guideline"] = d.file_name.map(lambda f: unicodedata.normalize("NFC", re.sub(r"\.pdf$", "", f, flags=re.I)) in guide)
    tax = json.load(open(ROOT / "data/taxonomy_v2.json", encoding="utf-8"))
    grp = {c["id"]: c["group"] for c in tax["classes"]}
    d["agree"] = d.doc_type_A == d.doc_type_B
    d["agree_group"] = d.doc_type_A.map(grp) == d.doc_type_B.map(grp)
    out = {}
    for name, s in (("tất cả", d), ("không nêu trong guideline", d[~d.in_guideline]), ("có nêu trong guideline", d[d.in_guideline])):
        if len(s) < 2:
            continue
        out[name] = dict(n=len(s), agree=round(s.agree.mean(), 4), kappa=round(cohen_kappa_score(s.doc_type_A, s.doc_type_B), 4),
                         agree_group=round(s.agree_group.mean(), 4))
    comp = dict(both=int(((d.is_composite_A == "1") & (d.is_composite_B == "1")).sum()),
                only_A=int(((d.is_composite_A == "1") & (d.is_composite_B != "1")).sum()),
                only_B=int(((d.is_composite_A != "1") & (d.is_composite_B == "1")).sum()),
                kappa=round(cohen_kappa_score(d.is_composite_A == "1", d.is_composite_B == "1"), 4))
    dis = d[~d.agree | (d.is_composite_A != d.is_composite_B) | d.confidence_B.isin(["low", "medium"])]
    cols = ["doc_id", "file_name", "page_count", "doc_type_A", "doc_type_B", "is_composite_A", "is_composite_B", "segments_A", "segments_B",
            "confidence_B", "evidence_B", "note_A", "note_B", "in_guideline"]
    dis[cols].to_csv(HERE / "disagreements.csv", index=False, encoding="utf-8-sig")
    d.to_csv(HERE / "labels_A_vs_B.csv", index=False, encoding="utf-8-sig")
    summary = dict(doc_type=out, composite=comp, n_type_disagreements=int((~d.agree).sum()), n_to_adjudicate=len(dis),
                   confusion_pairs=d[~d.agree].groupby(["doc_type_A", "doc_type_B"]).size().sort_values(ascending=False).head(30).reset_index(name="n").values.tolist())
    json.dump(summary, open(HERE / "agreement_summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
