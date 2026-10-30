r"""Tạo "gói gán nhãn" cho annotator: mỗi tài liệu DUY NHẤT một khối gồm doc_id, tên tệp, số trang và văn bản
2 trang đầu (lấy từ data/ocr_llm_haiku.jsonl). KHÔNG đưa tên thư mục gốc để annotator không bị dẫn dắt.

Chạy:  .venv\Scripts\python -X utf8 teams\00_data_and_eval\annotation\build_packets.py --parts 3 --seed 7
"""
import argparse, json, random
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ocr", default=str(ROOT / "data" / "ocr_llm_haiku.jsonl"))
    ap.add_argument("--parts", type=int, default=3)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--p1-chars", type=int, default=1800)
    ap.add_argument("--p2-chars", type=int, default=900)
    args = ap.parse_args()

    m = pd.read_csv(ROOT / "data" / "manifest.csv", encoding="utf-8-sig", dtype=str).fillna("")
    m["key"] = m.apply(lambda r: r["exact_dup_group"] or r["doc_id"], axis=1)
    reps = m.sort_values("relative_path").drop_duplicates("key")
    ocr = {}
    for line in open(args.ocr, encoding="utf-8"):
        j = json.loads(line)
        ocr[j["doc_id"]] = j
    docs = list(reps.itertuples())
    random.Random(args.seed).shuffle(docs)
    out = HERE / "packets"
    out.mkdir(exist_ok=True)
    n = len(docs)
    for k in range(args.parts):
        chunk = docs[k * n // args.parts:(k + 1) * n // args.parts]
        lines = []
        for r in chunk:
            j = ocr[r.doc_id]
            pages = {p["page"]: p for p in j["pages"]}
            lines.append(f"===== doc_id: {r.doc_id} | tệp: {r.file_name} | số trang: {r.page_count} =====")
            for pg, lim in ((1, args.p1_chars), (2, args.p2_chars)):
                if pg in pages:
                    t = pages[pg]["text_raw"].strip()
                    lines.append(f"--- trang {pg}" + (" (bị cắt bớt)" if len(t) > lim else "") + " ---")
                    lines.append(t[:lim])
            lines.append("")
        (out / f"packet_{k + 1:02d}.txt").write_text("\n".join(lines), encoding="utf-8")
        (out / f"packet_{k + 1:02d}_ids.txt").write_text("\n".join(r.doc_id for r in chunk), encoding="utf-8")
        print(f"packet_{k + 1:02d}: {len(chunk)} tài liệu, {sum(len(x) for x in lines):,} ký tự")


if __name__ == "__main__":
    main()
