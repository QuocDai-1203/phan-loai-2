#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
batch_classify_336.py
Chạy phân loại tự động trên toàn bộ 336 tài liệu trong kho mẫu.
Dùng văn bản OCR từ data/ocr_llm_haiku.jsonl (2 trang đầu).
Đối chiếu với đáp án chuẩn data/labels_v2.csv.
Output: output/batch_classification_336.csv + tóm tắt tổng kết.
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import time
import pandas as pd
from pathlib import Path
from src.classification.doc_classifier import DocumentClassifier

PROJECT = Path(__file__).resolve().parent.parent

# ──────────────────────────────────────────────────────────
# 1. Nạp dữ liệu
# ──────────────────────────────────────────────────────────
print("[1/4] Nạp dữ liệu nhãn và OCR Haiku...")

labels_df = pd.read_csv(PROJECT / "data" / "labels_v2.csv")
labels_map = dict(zip(labels_df["doc_id"], labels_df["doc_type"]))

haiku_map = {}
with open(PROJECT / "data" / "ocr_llm_haiku.jsonl", encoding="utf-8") as f:
    for line in f:
        d = json.loads(line)
        doc_id = d.get("doc_id")
        pages = d.get("pages", [])
        # Lấy text 2 trang đầu, ghép bằng \n
        texts = []
        for p in pages[:2]:
            t = p.get("text") or p.get("full_text") or ""
            if t.strip():
                texts.append(t.strip())
        haiku_map[doc_id] = "\n".join(texts)

print(f"    -> {len(labels_map)} nhãn, {len(haiku_map)} tài liệu có OCR Haiku")

# ──────────────────────────────────────────────────────────
# 2. Khởi tạo bộ phân loại
# ──────────────────────────────────────────────────────────
print("[2/4] Khởi tạo bộ phân loại Cascade (Rule -> TF-IDF -> Kev)...")
clf = DocumentClassifier.from_defaults(llm_backend="kev")
print("    -> OK!")

# ──────────────────────────────────────────────────────────
# 3. Vòng lặp chính: phân loại từng tài liệu
# ──────────────────────────────────────────────────────────
print(f"[3/4] Đang phân loại {len(labels_map)} tài liệu...")

records = []
correct = 0
total_auto = 0
tiers = {"rule": 0, "tfidf": 0, "kev": 0, "llm": 0, "human": 0}

t_start = time.perf_counter()

for i, (doc_id, true_label) in enumerate(labels_map.items(), 1):
    text = haiku_map.get(doc_id, "")
    res, _ = clf.classify_text(text or "", slice_id=doc_id)

    pred = res.predicted_category
    tier = res.tier
    conf = res.confidence
    is_auto = not res.requires_human_review and tier != "human"
    is_correct = (pred == true_label) if is_auto else None

    tiers[tier] = tiers.get(tier, 0) + 1
    if is_auto:
        total_auto += 1
        if is_correct:
            correct += 1

    records.append({
        "doc_id": doc_id,
        "true_label": true_label,
        "predicted": pred,
        "tier": tier,
        "confidence": round(conf, 4),
        "decision": "auto_file" if is_auto else "needs_human",
        "correct": is_correct,
        "suggested": res.suggested_category,
        "processing_ms": round(res.processing_time_ms, 1),
    })

    if i % 50 == 0:
        elapsed = time.perf_counter() - t_start
        print(f"    [{i}/{len(labels_map)}] Đã xử lý {i} tài liệu | {elapsed:.1f}s qua")

total_time = time.perf_counter() - t_start

# ──────────────────────────────────────────────────────────
# 4. Ghi kết quả và báo cáo
# ──────────────────────────────────────────────────────────
print("[4/4] Ghi kết quả CSV và tóm tắt...")

out_dir = PROJECT / "output"
out_dir.mkdir(exist_ok=True)
df_out = pd.DataFrame(records)
csv_path = out_dir / "batch_classification_336.csv"
df_out.to_csv(csv_path, index=False, encoding="utf-8-sig")

n_total = len(records)
n_auto = total_auto
n_human = n_total - n_auto
accuracy = correct / n_auto if n_auto > 0 else 0
auto_rate = n_auto / n_total

print("\n" + "=" * 58)
print("       BÁO CÁO ĐÁNH GIÁ TOÀN KHO 336 TÀI LIỆU")
print("=" * 58)
print(f"  Tổng số tài liệu:          {n_total}")
print(f"  Tự động phân loại (auto):  {n_auto} ({auto_rate*100:.1f}%)")
print(f"  Chuyển người duyệt:        {n_human} ({(1-auto_rate)*100:.1f}%)")
print(f"  Độ chính xác (auto):       {correct}/{n_auto} ({accuracy*100:.1f}%)")
print(f"  Thời gian tổng cộng:       {total_time:.1f} giây")
print(f"  Tốc độ trung bình:         {n_total/total_time:.1f} tài liệu/giây")
print()
print("  Phân bổ theo Tầng xử lý:")
for tier_name, cnt in sorted(tiers.items(), key=lambda x: -x[1]):
    if cnt > 0:
        print(f"    Tầng {tier_name:8s}: {cnt:4d} tài liệu ({cnt/n_total*100:.1f}%)")
print("=" * 58)
print(f"  [*] Kết quả CSV: {csv_path}")
