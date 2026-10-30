r"""Dựng thư mục mẫu ĐÃ PHÂN LOẠI ĐÚNG theo taxonomy v2: data/classified_v2/<NHÓM>/<LOẠI>/<tệp>.pdf

- Nguồn: PDF gốc trong docs/_chot_samples_phanloaitailieu/ (KHÔNG sửa, chỉ sao chép) + nhãn data/labels_v2.csv.
- Mỗi tài liệu duy nhất xuất hiện đúng MỘT lần (bản trùng byte được gộp; INDEX.csv ghi mọi đường dẫn gốc).
- _COMPOSITE_KHAC_LOAI/ : tệp chứa nhiều tài liệu KHÁC loại (kèm dải trang trong INDEX.csv) - chuẩn cho nhóm tách tài liệu.
- _CAN_KIEM_TRA/<LOẠI>/  : nhãn chưa đủ chắc (annotator B không tự tin, hoặc nhãn do phân xử) - cần người của công ty duyệt.
- Thư mục này là SẢN PHẨM SINH RA: muốn sửa nhãn thì sửa data/labels_v2.csv (hoặc adjudication.csv) rồi chạy lại script.

Chạy:  .venv\Scripts\python -X utf8 scripts\build_classified_folder.py
"""
import argparse
import json
import shutil
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "docs" / "_chot_samples_phanloaitailieu"
MIXED_DIR = "_COMPOSITE_KHAC_LOAI"
REVIEW_DIR = "_CAN_KIEM_TRA"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "data" / "classified_v2"))
    args = ap.parse_args()
    out = Path(args.out).resolve()
    if out.name != "classified_v2" or ROOT not in out.parents:
        raise SystemExit("Từ chối ghi: --out phải là một thư mục tên classified_v2 nằm trong repo")

    m = pd.read_csv(ROOT / "data" / "manifest.csv", encoding="utf-8-sig", dtype=str).fillna("")
    lab = pd.read_csv(ROOT / "data" / "labels_v2.csv", encoding="utf-8-sig", dtype=str).fillna("")
    tax = json.load(open(ROOT / "data" / "taxonomy_v2.json", encoding="utf-8"))
    groups = {g["id"]: g["name_vi"] for g in tax["groups"]}
    cls = {c["id"]: c for c in tax["classes"]}
    index = {unicodedata.normalize("NFC", p.relative_to(SAMPLES).as_posix()): p for p in SAMPLES.rglob("*.pdf")}
    d = m.merge(lab, on="doc_id")
    d["key"] = d.apply(lambda r: r["exact_dup_group"] or r["doc_id"], axis=1)
    all_paths = d.groupby("key").relative_path.apply(lambda s: " | ".join(sorted(s))).to_dict()
    reps = d[d.is_duplicate_of == ""].sort_values("relative_path")

    if out.exists():
        shutil.rmtree(out)  # chỉ xóa thư mục do chính script này sinh ra
    out.mkdir(parents=True)
    rows, used = [], set()
    for r in reps.itertuples():
        if r.composite_mixed == "1":
            sub = Path(MIXED_DIR)
        elif r.review_status in ("check_low_conf", "adjudicated"):
            sub = Path(REVIEW_DIR) / r.doc_type
        else:
            sub = Path(r.group) / r.doc_type
        name = r.file_name
        if (sub / name).as_posix().lower() in used:  # hai tài liệu khác nhau trùng tên tệp
            name = f"{Path(name).stem}__{r.doc_id[:6]}{Path(name).suffix}"
        used.add((sub / name).as_posix().lower())
        (out / sub).mkdir(parents=True, exist_ok=True)
        shutil.copy2(index[unicodedata.normalize("NFC", r.relative_path)], out / sub / name)
        rows.append(dict(doc_id=r.doc_id, classified_path=(sub / name).as_posix(), doc_type=r.doc_type, name_vi=r.name_vi,
                         group=r.group, page_count=r.page_count, is_composite=r.is_composite, composite_mixed=r.composite_mixed,
                         segments=r.segments, review_status=r.review_status, confidence=r.confidence, evidence=r.evidence,
                         legacy_paths=all_paths[r.key], note=r.note))
    idx = pd.DataFrame(rows)
    idx.to_csv(out / "INDEX.csv", index=False, encoding="utf-8-sig")

    main_part = idx[~idx.classified_path.str.startswith("_")]
    cnt = main_part.groupby(["group", "doc_type"]).size()
    L = ["# Bộ mẫu đã phân loại theo taxonomy v2", "",
         "> Thư mục này được **sinh tự động** bởi `scripts/build_classified_folder.py` từ `data/labels_v2.csv`.",
         "> Đừng sửa tay ở đây: sửa nhãn trong `data/labels_v2.csv` (hoặc `teams/00_data_and_eval/annotation/adjudication.csv`) rồi chạy lại script.", "",
         "## Cách đọc", "",
         "- `<NHÓM>/<LOẠI>/tệp.pdf`: loại tài liệu xác định theo **nội dung** (tiêu đề, cơ quan ban hành, bố cục), không theo nơi công ty lưu hồ sơ.",
         "  Định nghĩa từng loại: `docs/LABELING_GUIDELINE.md`; danh mục máy đọc được: `data/taxonomy_v2.json`.",
         f"- `{MIXED_DIR}/`: một tệp PDF chứa nhiều tài liệu **khác loại**. Dải trang của từng phần nằm ở cột `segments` trong `INDEX.csv`. Dùng làm chuẩn cho bài toán tách tài liệu, không dùng cho bài phân loại đơn nhãn.",
         f"- `{REVIEW_DIR}/<LOẠI>/`: nhãn đề xuất nhưng chưa đủ chắc, cần người phụ trách hồ sơ của công ty xem lại.",
         "- `INDEX.csv`: một dòng mỗi tài liệu — `doc_id`, đường dẫn mới, loại, số trang, tệp ghép hay không, trạng thái duyệt, căn cứ gán nhãn, và **mọi** đường dẫn gốc trong `docs/_chot_samples_phanloaitailieu/` (bản trùng byte đã gộp làm một).", "",
         "## Trạng thái nhãn", "",
         "Nhãn do hai annotator là mô hình AI gán độc lập (một bên xem ảnh trang, một bên đọc văn bản chép lại) rồi đối chiếu; **chưa có người của công ty duyệt**.",
         "Cột `review_status`: `agreed` = hai bên trùng nhau; `check_composite` = hai bên trùng loại nhưng chỉ một bên (bên xem đủ trang) ghi nhận tệp ghép; `check_low_conf` = bên đọc văn bản không tự tin; `adjudicated` = hai bên khác nhau, nhãn do phân xử.", "",
         "| review_status | số tài liệu |", "|---|---|"]
    for k, v in idx.review_status.value_counts().items():
        L.append(f"| {k} | {v} |")
    L += ["", f"Tổng: **{len(idx)} tài liệu duy nhất** (từ {len(d)} tệp gốc), trong đó {int((idx.composite_mixed == '1').sum())} tệp ghép khác loại và "
          f"{int(idx.classified_path.str.startswith(REVIEW_DIR).sum())} tệp cần kiểm tra.", "",
          "## Số tài liệu theo loại (không tính hai thư mục đặc biệt)", "", "| Nhóm | Mã loại | Tên loại | Số tài liệu | Dữ liệu |", "|---|---|---|---|---|"]
    for g in groups:
        for c in tax["classes"]:
            if c["group"] == g and (g, c["id"]) in cnt.index:
                n = int(cnt[(g, c["id"])])
                L.append(f"| {groups[g]} | `{c['id']}` | {c['name_vi']} | {n} | {'đủ để huấn luyện/đánh giá' if n >= 10 else 'THIẾU — cần thu thập thêm'} |")
    absent = [c["id"] for c in tax["classes"] if c["id"] not in set(main_part.doc_type)]
    if absent:
        L += ["", "Loại có trong taxonomy nhưng chưa có tệp đơn nào trong bộ mẫu: " + ", ".join(f"`{x}`" for x in absent) + "."]
    (out / "README.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"Đã dựng {out}: {len(idx)} tài liệu | thư mục loại: {len(cnt)} | ghép khác loại: {int((idx.composite_mixed == '1').sum())} | cần kiểm tra: {int(idx.classified_path.str.startswith(REVIEW_DIR).sum())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
