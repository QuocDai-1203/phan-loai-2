"""analyze_dev.py - So đặc trưng cổng luật của BB_GIAO_NHAN / PHIEU_XUAT_KHO đơn lẻ (DEV) với lát cắt trong tệp ghép; liệt kê mọi tài liệu DEV mà luật "mơ hồ".

Chỉ DEV (ocr_v2_p12, trang 1-2) và 8 tệp ghép (chẩn đoán). Không mở TEST. In số liệu tổng hợp, không in văn bản/định danh.

  .venv\\Scripts\\python.exe -X utf8 teams\\team3_classification\\experiments\\05_composite_slices\\analyze_dev.py
"""
from __future__ import annotations

import sys
from collections import Counter

import common05 as K  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import common as C  # noqa: E402  (thí nghiệm 02)
from src.classification.doc_classifier import text_for_classification  # noqa: E402
from src.classification.system_one_classifier import HEADER_WINDOW_CHARS, CascadedClassifier  # noqa: E402
from src.common.text_norm import NormalizedText, normalize_text  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def keyword_positions(rules, text: str):
    """{class_id: vị trí sớm nhất (ký tự, trong văn bản đã chuẩn hóa) của một từ khóa khớp 'exact'} trong cửa sổ tiêu đề."""
    norm = NormalizedText(text[:HEADER_WINDOW_CHARS])
    pos = {}
    for cid, kw in rules:
        k = normalize_text(kw)
        i = norm.spaced.find(k) if k else -1
        if i >= 0:
            pos[cid] = min(pos.get(cid, 10 ** 9), i)
    return pos


def main() -> int:
    D = C.Data()
    dev = D.docs("ocr_v2_p12", "DEV")
    sg = pd.read_csv(K.OUT.parent / "04_safety_margin" / "dev_signals.csv", keep_default_na=False).set_index("doc_id")
    clf = CascadedClassifier(kev_endpoint=None)
    rows = []
    for d in dev:
        text = d.text
        m = clf.match_rules(text)
        pos = keyword_positions(clf._rules, text)
        rows.append(dict(doc_id=d.doc_id, true=d.label, rule=m.category or "", amb="|".join(m.ambiguous), pos=pos, n_chars=len(text),
                         s_label=sg.loc[d.doc_id, "s_label"], s_conf=float(sg.loc[d.doc_id, "s_conf"])))
    df = pd.DataFrame(rows)
    print(f"DEV n={len(df)}; luật quyết định {int((df.rule != '').sum())}, mơ hồ {int((df.amb != '').sum())}, không khớp {int(((df.rule == '') & (df.amb == '')).sum())}")
    print("\nTài liệu DEV mà luật MƠ HỒ (theo nhãn đúng và cặp lớp):")
    amb = df[df.amb != ""]
    print(Counter(zip(amb.true, amb.amb)).most_common())
    print("\nBB_GIAO_NHAN và PXK đơn lẻ trong DEV:")
    for lab in ("BB_GIAO_NHAN_HANG_HOA", "PHIEU_XUAT_KHO"):
        s = df[df.true == lab]
        print(f"  {lab}: n={len(s)}; luật đúng={int((s.rule == lab).sum())}, luật sai={int(((s.rule != lab) & (s.rule != '')).sum())}, mơ hồ={int((s.amb != '').sum())}, "
              f"không khớp={int(((s.rule == '') & (s.amb == '')).sum())}; TF-IDF OOF đúng={int((s.s_label == lab).sum())}; "
              f"độ dài trung vị={int(s.n_chars.median())}")
        for _, r in s.iterrows():
            if r.amb:
                print("     mơ hồ", r.amb, {k: v for k, v in r.pos.items()}, "TF-IDF", r.s_label, round(r.s_conf, 3))
    print("\nVị trí từ khóa (ký tự đã chuẩn hóa) của lớp ĐÚNG trong tài liệu DEV đơn lẻ (phân bố):")
    for lab in ("BB_GIAO_NHAN_HANG_HOA", "PHIEU_XUAT_KHO"):
        v = [r.pos.get(lab) for _, r in df[df.true == lab].iterrows() if r.pos.get(lab) is not None]
        print(f"  {lab}: có từ khóa trong cửa sổ {len(v)}/{int((df.true == lab).sum())}; vị trí trung vị {np.median(v):.0f}, max {max(v)}, min {min(v)}")
    print("\nLát cắt BB_GIAO_NHAN trong 8 tệp ghép:")
    ocr = K.load_ocr()
    for r in K.oracle_slices(ocr):
        if r["true"] != "BB_GIAO_NHAN_HANG_HOA":
            continue
        t = text_for_classification(r["slice"])
        m = clf.match_rules(t)
        print(f"  file {r['file_idx']} trang {r['a']}-{r['b']}: n_chars={len(t)} luật={m.category or '-'} mơ hồ={'|'.join(m.ambiguous) or '-'} vị trí={keyword_positions(clf._rules, t)}")
    df.drop(columns=["pos"]).to_csv(K.OUT / "dev_rule_features.csv", index=False)
    return 0


if __name__ == "__main__":
    K.OUT.mkdir(parents=True, exist_ok=True)
    sys.exit(main())
