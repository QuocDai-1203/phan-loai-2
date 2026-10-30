"""train_tfidf_classifier.py - Huấn luyện bộ TF-IDF đã chốt (`tfidf_word_cnb_raw_C0.1`) trên TOÀN BỘ DEV và lưu vào models/classification/.

  * Huấn luyện CHỈ trên tài liệu DEV của `data/splits/splits.csv` (237 tài liệu); script KHÔNG đọc nhãn/văn bản của TEST
    (`load_documents(split="DEV")` chặn TEST) và kiểm lại không có doc_id nào thuộc TEST trước khi lưu.
  * Văn bản = nguồn `ocr_v2_p12` (trang 1-2 của data/ocr_v2.jsonl nối bằng '\\n'), nhãn = Track S (`label_s`) của data/labels_v2.csv.
  * Ghi: <out>/model.joblib + <out>/meta.json (sha1 nhãn, danh sách doc_id huấn luyện, nguồn văn bản, phiên bản sklearn, ngày).

  .venv\\Scripts\\python.exe -X utf8 scripts\\train_tfidf_classifier.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
for p in (REPO, REPO / "teams" / "00_data_and_eval" / "eval"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from harness import DEFAULT_LABELS, load_benchmark, load_documents, load_or_make_splits  # noqa: E402
from src.classification.tfidf_classifier import CONFIG_NAME, DEFAULT_DIR, TfidfClassifier  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    ap.add_argument("--source", default="ocr_v2_p12")
    ap.add_argument("--out", type=Path, default=DEFAULT_DIR)
    ap.add_argument("--min-docs", type=int, default=10)
    a = ap.parse_args()

    bench = load_benchmark(a.labels, a.min_docs)
    splits = load_or_make_splits(bench)
    dev = load_documents(bench, splits, a.source, split="DEV")             # TEST không đọc được ở đây
    test_ids = set(splits.loc[splits["split"] == "TEST", "doc_id"])
    leaked = [d.doc_id for d in dev if d.doc_id in test_ids]
    if leaked or any(d.split != "DEV" for d in dev):
        print("LỖI: tập huấn luyện lẫn tài liệu TEST", leaked[:5])
        return 2
    empty = [d.doc_id for d in dev if not d.text.strip()]
    if empty:
        print(f"LỖI: {len(empty)} tài liệu DEV không có văn bản ở nguồn {a.source}: {empty[:5]}")
        return 2
    clf = TfidfClassifier(bench.s_classes).fit([d.text for d in dev], [d.label_s for d in dev])
    meta = clf.save(a.out, labels_file=str(a.labels.relative_to(REPO)) if a.labels.is_relative_to(REPO) else str(a.labels),
                    labels_sha1_10=bench.labels_sha, text_source=a.source, train_doc_ids=[d.doc_id for d in dev],
                    train_labels=[d.label_s for d in dev], train_split="DEV",
                    notes="Huấn luyện trên toàn bộ DEV (237 tài liệu), không dùng TEST. Cấu hình chốt: 01/dev_selection.json final_configs[ocr_v2_p12][0].")
    print(f"đã lưu {a.out}: {CONFIG_NAME}, n_train={meta.n_train}, nhãn sha1[:10]={meta.labels_sha1_10}, sklearn={meta.sklearn_version}")
    print("số tài liệu mỗi lớp:", meta.class_counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
