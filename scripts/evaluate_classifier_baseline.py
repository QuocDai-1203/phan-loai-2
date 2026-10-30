"""evaluate_classifier_baseline.py - Đánh giá Baseline Classifier trên bộ tài liệu mẫu (Nhóm 3).

Dành cho Nhóm 3 (Phân loại văn bản):
- Đọc data/baseline_ocr_335.jsonl (cột category_label + ocr_text) hoặc data/ocr_v2.jsonl
  (cột folder_label + pages: [{page, text, ...}], các trang được nối lại).
- Nhãn thật: mặc định là nhãn THƯ MỤC CŨ trong JSONL (nơi lưu hồ sơ, không phải loại tài liệu - chỉ để tái lập
  baseline cũ). Truyền --labels data/labels_v2.csv để chấm theo loại tài liệu v2 (ghép theo doc_id; bỏ bản trùng
  byte và tệp ghép khác loại). Bản ghi có trường nhãn nhưng rỗng (2 PDF nằm ở gốc bộ mẫu) bị bỏ qua và được đếm.
- Chạy CascadedClassifier (cổng luật tiêu đề -> Kev đang chạy ở --kev-endpoint -> abstain); --kev-endpoint "" để chỉ chấm cổng luật.
- Báo cáo: accuracy, macro-F1, precision/recall/F1 từng lớp (sklearn), coverage (tỉ lệ tài liệu bộ phân loại
  KHÔNG abstain), accuracy-on-covered, số lượng theo tầng (rule/kev/none).
- Ghi ma trận nhầm lẫn (CSV) và tóm tắt (JSON) vào thư mục --out.

TRUNG THỰC: nếu Kev server không chạy, kết quả chỉ phản ánh CỔNG LUẬT TỪ KHÓA, không phải mô hình.
Script in cảnh báo lớn và ghi `kev_online=false` vào JSON để không ai nhầm hai thứ này.
Quy ước: abstain (UNKNOWN) tính là sai trong accuracy/macro-F1 toàn bộ; accuracy-on-covered chỉ tính trên
phần không abstain. Macro-F1 lấy trung bình trên các lớp có mặt trong nhãn thật (support > 0).
"""

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

# Thêm project root vào sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Đảm bảo in Tiếng Việt trên Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from sklearn.metrics import precision_recall_fscore_support

from src.classification.system_one_classifier import CascadedClassifier
from src.classification.taxonomy import load_taxonomy
from src.common.contracts import UNKNOWN_CATEGORY, DocumentSlice

DEFAULT_INPUT = "data/baseline_ocr_335.jsonl"
# Mỗi cặp (đầu vào, bộ nhãn) ghi vào một thư mục riêng; rule_gate_baseline/ là kết quả lịch sử, không ghi đè.
DEFAULT_OUT_ROOT = "teams/team3_classification/results/rule_gate_runs"
LABEL_FIELD_CANDIDATES = ("category_label", "folder_label")


def load_label_map(path: Path) -> Dict[str, str]:
    """doc_id -> doc_type từ labels_v2.csv, chỉ giữ tài liệu duy nhất và không phải tệp ghép khác loại."""
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return {r["doc_id"]: r["doc_type"] for r in csv.DictReader(f)
                if not r.get("is_duplicate_of") and r.get("composite_mixed", "0") != "1"}


def load_records(
    path: Path,
    label_field: Optional[str] = None,
    label_map: Optional[Dict[str, str]] = None,
    skipped: Optional[Counter] = None,
) -> List[Dict[str, Any]]:
    """Đọc JSONL thành danh sách {file_name, label, text, page_count}; hỗ trợ cả định dạng baseline và ocr_v2.

    label_map (doc_id -> loại) thay cho nhãn trong JSONL khi được truyền. Bản ghi bị bỏ qua được đếm vào `skipped`.
    """
    records: List[Dict[str, Any]] = []
    skipped = Counter() if skipped is None else skipped
    with open(path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            if not line.strip():
                continue
            item = json.loads(line)

            if label_map is not None:
                label = label_map.get(item.get("doc_id"))
                if label is None:
                    skipped["khong_co_trong_labels (trùng byte / ghép khác loại / thiếu doc_id)"] += 1
                    continue
            else:
                field = label_field or next((c for c in LABEL_FIELD_CANDIDATES if c in item), None)
                if field is None or field not in item:
                    raise ValueError(f"Dòng {idx}: không tìm thấy nhãn (đã thử {label_field or LABEL_FIELD_CANDIDATES})")
                label = item[field]
                if label in (None, ""):
                    skipped["nhan_rong"] += 1
                    continue

            if isinstance(item.get("ocr_text"), str):
                text = item["ocr_text"]
            else:
                text = "\n\n".join(str(p.get("text") or "") for p in item.get("pages", []))

            page_count = item.get("page_count") or len(item.get("pages", [])) or 1
            records.append({
                "file_name": item.get("file_name", f"doc_{idx}"),
                "label": label,
                "text": text,
                "page_count": int(page_count),
            })
    return records


def compute_metrics(y_true: List[str], y_pred: List[str], tiers: List[str]) -> Dict[str, Any]:
    """Tính accuracy, macro-F1, P/R/F1 từng lớp, coverage, accuracy-on-covered, số lượng theo tầng."""
    total = len(y_true)
    covered_idx = [i for i, p in enumerate(y_pred) if p != UNKNOWN_CATEGORY]
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    correct_covered = sum(1 for i in covered_idx if y_true[i] == y_pred[i])

    labels = sorted(set(y_true))  # chỉ các lớp có support > 0
    prec, rec, f1, sup = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0
    )
    per_class = {
        lbl: {"precision": float(p), "recall": float(r), "f1": float(f), "support": int(s)}
        for lbl, p, r, f, s in zip(labels, prec, rec, f1, sup)
    }

    tier_counts = Counter(tiers)
    tier_accuracy: Dict[str, Optional[float]] = {}
    for tier in tier_counts:
        idx = [i for i, t in enumerate(tiers) if t == tier and y_pred[i] != UNKNOWN_CATEGORY]
        tier_accuracy[tier] = (sum(1 for i in idx if y_true[i] == y_pred[i]) / len(idx)) if idx else None

    return {
        "total": total,
        "correct": correct,
        "accuracy": correct / total if total else 0.0,
        "macro_f1": float(sum(f1) / len(f1)) if len(f1) else 0.0,
        "coverage": len(covered_idx) / total if total else 0.0,
        "covered": len(covered_idx),
        "accuracy_on_covered": (correct_covered / len(covered_idx)) if covered_idx else None,
        "tier_counts": dict(tier_counts),
        "tier_accuracy_on_covered": tier_accuracy,
        "per_class": per_class,
    }


def write_confusion_matrix(path: Path, y_true: List[str], y_pred: List[str]) -> None:
    """Ghi ma trận nhầm lẫn CSV: hàng = nhãn thật, cột = nhãn dự đoán (UNKNOWN = abstain ở cột cuối)."""
    true_labels = sorted(set(y_true))
    pred_labels = sorted(set(y_pred) - {UNKNOWN_CATEGORY} | set(true_labels))
    if UNKNOWN_CATEGORY in y_pred:
        pred_labels.append(UNKNOWN_CATEGORY)
    counts = Counter(zip(y_true, y_pred))
    with open(path, "w", encoding="utf-8-sig", newline="") as f:  # utf-8-sig để Excel đọc đúng tiếng Việt
        writer = csv.writer(f)
        writer.writerow(["true \\ predicted"] + pred_labels)
        for t in true_labels:
            writer.writerow([t] + [counts.get((t, p), 0) for p in pred_labels])


def check_kev(classifier: CascadedClassifier) -> Dict[str, Any]:
    """Thăm dò Kev một lần: online nếu gọi thành công mà không có lỗi."""
    probe = classifier.classify_with_kev("kiem tra ket noi")
    return {"kev_online": probe["error"] is None, "kev_error": probe["error"]}


def run_evaluation(
    input_path: str = DEFAULT_INPUT,
    out_dir: Optional[str] = None,
    label_field: Optional[str] = None,
    labels_path: Optional[str] = None,
    taxonomy_path: Optional[str] = None,
    kev_endpoint: Optional[str] = "http://127.0.0.1:8009/v1/systemone",
    allow_heuristic_fallback: bool = False,
    verbose: bool = True,
) -> Dict[str, Any]:
    in_path = Path(input_path)
    if not in_path.is_absolute() and not in_path.exists():
        in_path = PROJECT_ROOT / input_path
    if out_dir is None:
        out_path = PROJECT_ROOT / DEFAULT_OUT_ROOT / f"{in_path.stem}__{'labels_v2' if labels_path else 'folder_labels'}"
    else:
        out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    taxonomy = load_taxonomy(taxonomy_path)
    classifier = CascadedClassifier(
        kev_endpoint=kev_endpoint, taxonomy=taxonomy, allow_heuristic_fallback=allow_heuristic_fallback
    )
    kev = check_kev(classifier)
    legacy_to_id = taxonomy.legacy_to_id
    skipped: Counter = Counter()
    label_map = load_label_map(Path(labels_path)) if labels_path else None
    records = load_records(in_path, label_field, label_map, skipped)

    y_true: List[str] = []
    y_pred: List[str] = []
    tiers: List[str] = []
    abstain_reasons: Counter = Counter()
    unmapped: Counter = Counter()
    mismatches: List[Dict[str, Any]] = []

    for idx, rec in enumerate(records, 1):
        true_label = legacy_to_id.get(rec["label"])
        if true_label is None:  # nhãn không có trong ánh xạ legacy -> giữ nguyên, đếm để cảnh báo
            true_label = rec["label"]
            if true_label not in taxonomy.class_ids:
                unmapped[true_label] += 1

        mock_slice = DocumentSlice(
            slice_id=f"slice_{idx}",
            start_page=1,
            end_page=rec["page_count"],
            page_count=rec["page_count"],
            combined_text=rec["text"],
        )
        res = classifier.classify_slice(mock_slice)

        y_true.append(true_label)
        y_pred.append(res.predicted_category)
        tiers.append(res.tier)
        if res.abstain_reason:
            abstain_reasons[res.abstain_reason] += 1
        if res.predicted_category != true_label:
            mismatches.append({
                "file_name": rec["file_name"],
                "true_label": true_label,
                "pred_label": res.predicted_category,
                "tier": res.tier,
                "model_used": res.model_name,
                "confidence": res.confidence,
                "confidence_kind": res.confidence_kind,
                "text_preview": rec["text"][:120].replace("\n", " "),
            })

    metrics = compute_metrics(y_true, y_pred, tiers)
    system = "rule_gate + kev (mô hình thật: xem model_used của từng dự đoán)" if kev["kev_online"] else "rule_gate_only (KEV OFFLINE - KHÔNG phải kết quả của mô hình)"
    summary: Dict[str, Any] = {
        "system_evaluated": system,
        "kev_online": kev["kev_online"],
        "kev_error": kev["kev_error"],
        "kev_endpoint": kev_endpoint,
        "allow_heuristic_fallback": allow_heuristic_fallback,
        "warning": None if kev["kev_online"] else (
            "Kev server không khả dụng: số liệu dưới đây là của cổng luật từ khóa (tier 'rule'); "
            "các tài liệu luật không quyết định được đều bị abstain (UNKNOWN)."
        ),
        "input": str(in_path),
        "labels": str(labels_path) if labels_path else "nhãn thư mục cũ trong JSONL",
        "skipped_records": dict(skipped),
        "taxonomy": {"version": taxonomy.version, "source": taxonomy.source, "num_classes": len(taxonomy.classes)},
        "unmapped_true_labels": dict(unmapped),
        "abstain_reasons": dict(abstain_reasons),
        **metrics,
    }

    write_confusion_matrix(out_path / "confusion_matrix.csv", y_true, y_pred)
    with open(out_path / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    if verbose:
        _print_report(summary, mismatches, out_path)
    return summary


def _print_report(summary: Dict[str, Any], mismatches: List[Dict[str, Any]], out_path: Path) -> None:
    if not summary["kev_online"]:
        bar = "!" * 80
        print(bar)
        print("!! CẢNH BÁO: KEV SERVER OFFLINE - KẾT QUẢ DƯỚI ĐÂY LÀ CỦA CỔNG LUẬT TỪ KHÓA, KHÔNG PHẢI MÔ HÌNH !!")
        print(f"!! Lý do: {summary['kev_error']}")
        print(bar)

    acc = summary["accuracy"] * 100
    aoc = summary["accuracy_on_covered"]
    print("=" * 80)
    print("BÁO CÁO ĐÁNH GIÁ BASELINE CLASSIFIER (Nhóm 3)")
    print(f"Hệ thống đánh giá: {summary['system_evaluated']}")
    print(f"Tổng số tài liệu: {summary['total']} | Đúng: {summary['correct']} | Accuracy: {acc:.2f}%")
    print(f"Macro-F1: {summary['macro_f1']:.4f}")
    print(f"Coverage (không abstain): {summary['coverage'] * 100:.2f}% ({summary['covered']}/{summary['total']})")
    print(f"Accuracy-on-covered: {'n/a' if aoc is None else f'{aoc * 100:.2f}%'}")
    print(f"Số lượng theo tầng: {summary['tier_counts']}")
    print(f"Lý do abstain: {summary['abstain_reasons']}")
    if summary["skipped_records"]:
        print(f"Bản ghi bị bỏ qua: {summary['skipped_records']}")
    if summary["unmapped_true_labels"]:
        print(f"CẢNH BÁO: nhãn thật không có trong taxonomy: {summary['unmapped_true_labels']}")
    print("=" * 80)
    print(f"{'Lớp (Ground Truth)':<44} | {'P':>6} | {'R':>6} | {'F1':>6} | {'N':>4}")
    print("-" * 80)
    for lbl, m in sorted(summary["per_class"].items()):
        print(f"{lbl:<44} | {m['precision']:>6.2f} | {m['recall']:>6.2f} | {m['f1']:>6.2f} | {m['support']:>4}")
    print("=" * 80)
    print(f"{len(mismatches)} tài liệu dự đoán sai/abstain (10 mẫu đầu):")
    print("-" * 80)
    for m in mismatches[:10]:
        print(f"- File: {m['file_name']}")
        print(f"  Thực tế:   {m['true_label']}")
        print(f"  Dự đoán:   {m['pred_label']} (tier={m['tier']}, {m['model_used']}, {m['confidence_kind']}={m['confidence']:.2f})")
        print(f"  Trích đoạn: {m['text_preview']}...")
        print()
    print(f"Đã ghi: {out_path / 'confusion_matrix.csv'} và {out_path / 'summary.json'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Đánh giá baseline classifier (cổng luật + Kev).")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="JSONL đầu vào (baseline_ocr_335 hoặc ocr_v2)")
    parser.add_argument("--label-field", default=None, help="Tên trường nhãn (mặc định tự dò category_label/folder_label)")
    parser.add_argument("--labels", default=None,
                        help="CSV nhãn v2 (doc_id, doc_type), vd data/labels_v2.csv; mặc định dùng nhãn thư mục cũ trong JSONL")
    parser.add_argument("--out", default=None,
                        help=f"Thư mục ghi confusion_matrix.csv và summary.json (mặc định {DEFAULT_OUT_ROOT}/<đầu vào>__<bộ nhãn>)")
    parser.add_argument("--taxonomy", default=None, help="Đường dẫn taxonomy JSON (mặc định data/taxonomy_v2.json nếu có)")
    parser.add_argument("--kev-endpoint", default="http://127.0.0.1:8009/v1/systemone")
    parser.add_argument("--allow-heuristic-fallback", action="store_true",
                        help="Cho phép heuristic fallback khi Kev lỗi (kết quả được gắn cờ fallback_used)")
    args = parser.parse_args()
    run_evaluation(
        input_path=args.input,
        out_dir=args.out,
        label_field=args.label_field,
        labels_path=args.labels,
        taxonomy_path=args.taxonomy,
        kev_endpoint=args.kev_endpoint,
        allow_heuristic_fallback=args.allow_heuristic_fallback,
    )


if __name__ == "__main__":
    main()
