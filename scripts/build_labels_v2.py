r"""Hợp nhất nhãn của hai annotator thành bộ nhãn chính thức data/labels_v2.csv (một dòng cho MỖI tệp PDF trong manifest).

Quy tắc:
- doc_type: chỉ nhận khi hai annotator trùng nhau. Nếu khác nhau, đọc quyết định phân xử trong
  teams/00_data_and_eval/annotation/adjudication.csv (cột doc_id, doc_type, is_composite, segments, note);
  thiếu quyết định thì dừng và báo lỗi - không tự chọn.
- is_composite / segments: lấy của annotator A (người đã xem toàn bộ trang). Annotator B chỉ thấy 2 trang đầu.
- review_status:
    agreed            hai annotator trùng loại, B tự tin cao
    check_composite   chỉ một annotator đánh dấu tệp ghép -> cần người xem lại ranh giới
    check_low_conf    annotator B ghi độ tin cậy medium/low
    adjudicated       nhãn do phân xử quyết định
- Tệp trùng byte (exact_dup_group) nhận cùng nhãn với bản đại diện.

Chạy:  .venv\Scripts\python -X utf8 scripts\build_labels_v2.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ANN = ROOT / "teams" / "00_data_and_eval" / "annotation"


def main() -> int:
    m = pd.read_csv(ROOT / "data" / "manifest.csv", encoding="utf-8-sig", dtype=str).fillna("")
    m["key"] = m.apply(lambda r: r["exact_dup_group"] or r["doc_id"], axis=1)
    reps = m.sort_values("relative_path").drop_duplicates("key")
    a = pd.read_csv(ANN / "annotator_A_opus_designer.csv", encoding="utf-8-sig", dtype=str).fillna("").set_index("doc_id")
    b = pd.read_csv(ANN / "annotator_B_sonnet.csv", encoding="utf-8-sig", dtype=str).fillna("").set_index("doc_id")
    adj_path = ANN / "adjudication.csv"
    adj = pd.read_csv(adj_path, encoding="utf-8-sig", dtype=str).fillna("").set_index("doc_id") if adj_path.exists() else None
    tax = json.load(open(ROOT / "data" / "taxonomy_v2.json", encoding="utf-8"))
    cls = {c["id"]: c for c in tax["classes"]}

    by_key, missing = {}, []
    for r in reps.itertuples():
        ra, rb = a.loc[r.doc_id], b.loc[r.doc_id]
        row = dict(doc_type=ra.doc_type, is_composite=ra.is_composite, segments=ra.segments,
                   confidence=rb.confidence or "high", evidence=rb.evidence, note="; ".join(x for x in (ra.note, rb.note) if x))
        if adj is not None and r.doc_id in adj.index:
            d = adj.loc[r.doc_id]
            row.update(doc_type=d.doc_type, is_composite=d.is_composite or row["is_composite"], segments=d.segments or row["segments"],
                       note="; ".join(x for x in (row["note"], d.note) if x))
            status = "adjudicated"
        elif ra.doc_type != rb.doc_type:
            missing.append((r.doc_id, r.file_name, ra.doc_type, rb.doc_type))
            continue
        elif ra.is_composite != rb.is_composite:
            status = "check_composite"
        elif rb.confidence in ("medium", "low"):
            status = "check_low_conf"
        else:
            status = "agreed"
        assert row["doc_type"] in cls, row["doc_type"]
        # ghép khác loại = segments chứa từ 2 loại khác nhau (tính lại sau phân xử); thiếu segments thì theo ghi chú của A
        seg_types = {s.split(":", 1)[1] for s in row["segments"].split(";") if ":" in s}
        mixed = len(seg_types) > 1 if seg_types else "composite khác loại" in ra.note
        row.update(review_status=status, composite_mixed="1" if mixed else "0",
                   group=cls[row["doc_type"]]["group"], name_vi=cls[row["doc_type"]]["name_vi"])
        by_key[r.key] = row
    if missing:
        print(f"CÒN {len(missing)} tài liệu hai annotator bất đồng mà chưa có phân xử trong {adj_path}:")
        for x in missing:
            print("  ", *x)
        return 1

    out = []
    for r in m.sort_values("relative_path").itertuples():
        row = dict(doc_id=r.doc_id, **by_key[r.key])
        row["is_duplicate_of"] = "" if r.doc_id in set(reps.doc_id) else reps.set_index("key").loc[r.key, "doc_id"]
        out.append(row)
    cols = ["doc_id", "doc_type", "is_composite", "segments", "confidence", "evidence", "note",
            "group", "name_vi", "composite_mixed", "review_status", "is_duplicate_of"]
    df = pd.DataFrame(out)[cols]
    df.to_csv(ROOT / "data" / "labels_v2.csv", index=False, encoding="utf-8-sig")
    u = df[df.is_duplicate_of == ""]
    print(f"Đã ghi data/labels_v2.csv: {len(df)} tệp, {len(u)} tài liệu duy nhất, {u.doc_type.nunique()} loại")
    print("review_status (duy nhất):", u.review_status.value_counts().to_dict())
    print("tệp ghép:", int((u.is_composite == "1").sum()), "| ghép khác loại:", int((u.composite_mixed == "1").sum()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
