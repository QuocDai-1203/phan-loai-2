"""append_results.py - Thêm các dòng vào `teams/team4_extraction/results/results_table.csv` từ results_<split>_<gold>.json (chỉ THÊM dòng, không sửa dòng cũ).

Giao thức đánh giá (reports/03_evaluation_protocol.md, mục 9) chỉ định nghĩa bảng chung `teams/team3_classification/results/results_table.csv` cho
PHÂN LOẠI; trích xuất trường có chỉ số khác nên dùng bảng riêng này, cùng quy tắc "chỉ thêm dòng" và ghi `labels_sha` (băm của đáp án silver dùng để chấm).

    .venv\\Scripts\\python.exe -X utf8 .../append_results.py DEV all [--note "..."]
"""
import csv
import datetime as dt
import hashlib
import json
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEAM = HERE.parents[1]
OUT = TEAM / "results" / "results_table.csv"
COLS = ["run_id", "timestamp", "split", "method", "text_source", "gold", "n_units", "n_failed", "f1_strict", "f1_strict_lo", "f1_strict_hi", "f1_lenient",
        "f1_lenient_lo", "f1_lenient_hi", "doc_level_strict", "doc_level_lenient", "expiry_n", "expiry_correct", "expiry_correct_lo", "expiry_correct_hi",
        "expiry_empty", "expiry_wrong", "expiry_wrong_lo", "expiry_wrong_hi", "silver_sha", "notes"]


def main() -> int:
    split, gold = sys.argv[1], sys.argv[2]
    note = sys.argv[sys.argv.index("--note") + 1] if "--note" in sys.argv else ""
    d = json.loads((HERE / f"results_{split}_{gold}.json").read_text(encoding="utf-8"))
    sha = hashlib.sha1((TEAM / "gold" / "fields_silver_v1.jsonl").read_bytes()).hexdigest()[:10]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    new = not OUT.exists()
    run = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
    with open(OUT, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, COLS)
        if new:
            w.writeheader()
        for name, c in d["configs"].items():
            m, _, src = name.partition("@")
            s, l, e = c["normalized"], c["lenient"], c["normalized"]["expiry_all"]
            w.writerow({"run_id": run, "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "split": split, "method": m, "text_source": src,
                        "gold": gold, "n_units": c["units"], "n_failed": s["n_failed"], "f1_strict": s["overall"]["f1"], "f1_strict_lo": s["overall"]["f1_ci_lo"],
                        "f1_strict_hi": s["overall"]["f1_ci_hi"], "f1_lenient": l["overall"]["f1"], "f1_lenient_lo": l["overall"]["f1_ci_lo"],
                        "f1_lenient_hi": l["overall"]["f1_ci_hi"], "doc_level_strict": s["doc_level"]["rate"], "doc_level_lenient": l["doc_level"]["rate"],
                        "expiry_n": e["n_gold_present"], "expiry_correct": e["correct_rate"], "expiry_correct_lo": e["correct_rate_ci_lo"],
                        "expiry_correct_hi": e["correct_rate_ci_hi"], "expiry_empty": e["empty_rate"], "expiry_wrong": e["wrong_rate"],
                        "expiry_wrong_lo": e["wrong_rate_ci_lo"], "expiry_wrong_hi": e["wrong_rate_ci_hi"], "silver_sha": sha, "notes": note})
    print(f"đã thêm {len(d['configs'])} dòng vào {OUT} (run_id {run})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
