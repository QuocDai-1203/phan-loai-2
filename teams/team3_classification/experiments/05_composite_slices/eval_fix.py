"""eval_fix.py - Thử các cách sửa lỗi "biên bản giao nhận bị gán PHIEU_XUAT_KHO" và kiểm hồi quy DEV.

(a) 8 tệp ghép (lát cắt theo đáp án): cơ sở vs `rule_title_tiebreak`. CHỈ CHẨN ĐOÁN (một nhà cung cấp).
(b) Hồi quy DEV 237 tài liệu: cascade đầy đủ (TF-IDF huấn luyện theo fold, LLM từ cache CHỈ ĐỌC của 02) cơ sở vs tùy chọn; số quyết định đổi.
(c) T9 phân loại theo trang: từng trang của 8 tệp, gộp các trang liền kề cùng nhãn, so với segments.
(d) Đặc trưng tiêu đề cho TF-IDF (lặp 300 ký tự đầu): OOF DEV + dự đoán lát BB trong tệp ghép.
(e) LLM hỏi riêng các lát BB (cache đĩa riêng) để biết LLM có phân biệt được không.

  .venv\\Scripts\\python.exe -X utf8 teams\\team3_classification\\experiments\\05_composite_slices\\eval_fix.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter

import common05 as K  # noqa: E402  (đặt sys.path)
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import common as C  # noqa: E402
from diagnose import build_classifier  # noqa: E402
from e2e_lib import LayeredCache  # noqa: E402
from src.classification.doc_classifier import DEFAULT_SELECTION_PATH, DEFAULT_SOURCE, DocumentClassifier, load_cascade_config, text_for_classification  # noqa: E402
from src.classification.llm_backends import DEFAULT_SPEC_ID, LLM_SPECS, OllamaBackend  # noqa: E402
from src.classification.llm_cache import DiskCache  # noqa: E402
from src.classification.tfidf_classifier import TfidfClassifier  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BB, PXK = "BB_GIAO_NHAN_HANG_HOA", "PHIEU_XUAT_KHO"


class ReadOnlyCache(DiskCache):
    def cached(self, key, fn, *, retry_errors=False):
        rec = self.get(key)
        if rec is None:
            self.misses += 1
            raise RuntimeError("CacheMiss " + key)
        self.hits += 1
        return rec


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"),) * 2
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


def classify_all(clf, items):
    out = []
    for sid, text in items:
        res, tr = clf.classify_text(text, sid)
        out.append((res.tier, "" if res.tier == "human" else res.predicted_category, res.abstain_reason or "", tr))
    return out


def part_a_c(summary):
    ocr = K.load_ocr()
    base = build_classifier("live")
    fix = build_classifier("live", rule_title_tiebreak=True)
    sl = K.oracle_slices(ocr)
    items = [(f"{r['file_idx']}.{r['seg_idx']}", text_for_classification(r["slice"])) for r in sl]
    rb, rf = classify_all(base, items), classify_all(fix, items)
    rows = []
    for r, b, f in zip(sl, rb, rf):
        rows.append(dict(file=r["file_idx"], seg=r["seg_idx"], true=r["true"], base=b[1], base_tier=b[0], fix=f[1], fix_tier=f[0], tiebreak=f[3].rule_tiebreak))
    df = pd.DataFrame(rows)
    df.to_csv(K.OUT / "composite_slices_base_vs_fix.csv", index=False)
    n = len(df)
    bb = df[df.true == BB]
    ok_b, ok_f = int((df.base == df.true).sum()), int((df.fix == df.true).sum())
    print(f"\n(a) lát cắt theo đáp án (8 tệp, {n} lát): cơ sở đúng {ok_b}/{n} {wilson(ok_b, n)}; tiebreak đúng {ok_f}/{n} {wilson(ok_f, n)}")
    print(f"    riêng lát BB_GIAO_NHAN ({len(bb)}): cơ sở đúng {int((bb.base == bb.true).sum())}, tiebreak đúng {int((bb.fix == bb.true).sum())}; "
          f"cơ sở gán PXK {int((bb.base == PXK).sum())}, tiebreak gán PXK {int((bb.fix == PXK).sum())}")
    fb = df.groupby("file").apply(lambda g: bool((g.base == g.true).all()), include_groups=False)
    ff = df.groupby("file").apply(lambda g: bool((g.fix == g.true).all()), include_groups=False)
    print(f"    tệp đúng cho mọi lát: cơ sở {int(fb.sum())}/8, tiebreak {int(ff.sum())}/8")
    print("    tầng của lát BB (cơ sở):", Counter(bb.base_tier), " (tiebreak):", Counter(bb.fix_tier))
    other = df[df.true != BB]
    print(f"    lát KHÔNG phải BB ({len(other)}): cơ sở đúng {int((other.base == other.true).sum())}, tiebreak đúng {int((other.fix == other.true).sum())}; "
          f"đổi quyết định: {int((df.base != df.fix).sum())} lát")
    summary["a"] = dict(n=n, base_ok=ok_b, fix_ok=ok_f, bb_n=len(bb), bb_base_ok=int((bb.base == bb.true).sum()), bb_fix_ok=int((bb.fix == bb.true).sum()),
                        files_ok_base=int(fb.sum()), files_ok_fix=int(ff.sum()), changed=int((df.base != df.fix).sum()))

    # (c) T9 theo trang
    pg_rows = []
    for fi, r in K.composites().iterrows():
        rec = ocr[r["doc_id"]]
        truth = {}
        for a, b, lab in K.parse_segments(r["segments"]):
            for p in range(a, b + 1):
                truth[p] = lab
        pitems = []
        for p in range(1, rec["page_count"] + 1):
            pitems.append((f"{fi}.p{p}", text_for_classification(K.make_slice(rec, p, p, f"{fi}.p{p}"))))
        pb, pf = classify_all(base, pitems), classify_all(fix, pitems)
        for p, (x, y) in enumerate(zip(pb, pf), start=1):
            pg_rows.append(dict(file=fi, page=p, true=truth[p], base=x[1], base_tier=x[0], fix=y[1], fix_tier=y[0]))
    pg = pd.DataFrame(pg_rows)
    pg.to_csv(K.OUT / "composite_pages_base_vs_fix.csv", index=False)
    N = len(pg)
    for tag in ("base", "fix"):
        ok = int((pg[tag] == pg["true"]).sum())
        hum = int((pg[tag] == "").sum())
        print(f"(c) theo trang, {tag}: đúng {ok}/{N} {tuple(round(x, 3) for x in wilson(ok, N))}; về người {hum}")
    for tag in ("base", "fix"):
        # gộp trang liền kề cùng nhãn (bỏ nhãn rỗng = người) và so với segments: tệp đúng khi mọi trang đúng (gộp không đổi nhãn trang)
        okf = int(pg.groupby("file").apply(lambda g: bool((g[tag] == g["true"]).all()), include_groups=False).sum())
        print(f"    tệp mà MỌI trang đúng loại ({tag}): {okf}/8")
    bbp = pg[pg.true == BB]
    print(f"    trang BB ({len(bbp)}): cơ sở đúng {int((bbp.base == BB).sum())}, tiebreak đúng {int((bbp.fix == BB).sum())}")
    summary["c"] = dict(n_pages=N, base_ok=int((pg.base == pg.true).sum()), fix_ok=int((pg.fix == pg.true).sum()),
                        bb_pages=len(bbp), bb_base_ok=int((bbp.base == BB).sum()), bb_fix_ok=int((bbp.fix == BB).sum()))
    return df, base


def part_b(summary):
    D = C.Data()
    dev = D.docs(DEFAULT_SOURCE, "DEV")
    cfg = load_cascade_config(DEFAULT_SELECTION_PATH, DEFAULT_SOURCE, DEFAULT_SPEC_ID, 0.01)
    tax = json.loads((K.REPO / "data" / "taxonomy_v2.json").read_text(encoding="utf-8"))
    folds = np.array([d.folds[0] for d in dev])
    rows = []
    ro = ReadOnlyCache(K.EXP02 / "_cache" / "ollama")
    for f in sorted(set(folds)):
        tr = [d for d in dev if d.folds[0] != f]
        tf = TfidfClassifier(D.s_classes).fit([d.text for d in tr], [d.label_s for d in tr])
        backend = OllamaBackend(LLM_SPECS[DEFAULT_SPEC_ID], tax, ro)
        c0 = DocumentClassifier(tf, backend, cfg)
        c1 = DocumentClassifier(tf, backend, cfg, rule_title_tiebreak=True)
        for i in np.where(folds == f)[0]:
            d = dev[i]
            r0, t0 = c0.classify_text(d.text, d.doc_id)
            r1, t1 = c1.classify_text(d.text, d.doc_id)
            rows.append(dict(doc_id=d.doc_id, true=d.label, tier0=r0.tier, lab0="" if r0.tier == "human" else r0.predicted_category,
                             tier1=r1.tier, lab1="" if r1.tier == "human" else r1.predicted_category, tiebreak=t1.rule_tiebreak))
    df = pd.DataFrame(rows)
    df.to_csv(K.OUT / "dev_regress_base_vs_tiebreak.csv", index=False)       # chứa doc_id: nội bộ
    n = len(df)
    acc0, acc1 = df.tier0 != "human", df.tier1 != "human"
    err0, err1 = int(((df.lab0 != df.true) & acc0).sum()), int(((df.lab1 != df.true) & acc1).sum())
    same = (df.tier0 == df.tier1) & (df.lab0 == df.lab1)
    print(f"\n(b) DEV n={n}; cơ sở: nhận {int(acc0.sum())}, sai {err0}, tầng {dict(Counter(df.tier0))}; tiebreak: nhận {int(acc1.sum())}, sai {err1}, tầng {dict(Counter(df.tier1))}")
    print(f"    quyết định GIỮ NGUYÊN (tầng và nhãn) {int(same.sum())}/{n}; đổi tầng {int((df.tier0 != df.tier1).sum())}; đổi nhãn {int(((df.lab0 != df.lab1)).sum())}; "
          f"được tiebreak áp dụng {int(df.tiebreak.sum())}; cache LLM trúng {ro.hits}, lỡ {ro.misses}")
    ch = df[df.tier0 != df.tier1]
    print("    các thay đổi tầng:", Counter(zip(ch.tier0, ch.tier1)))
    summary["b"] = dict(n=n, base=dict(accepted=int(acc0.sum()), errors=err0, tiers=dict(Counter(df.tier0))),
                        fix=dict(accepted=int(acc1.sum()), errors=err1, tiers=dict(Counter(df.tier1))), same=int(same.sum()),
                        tier_changed=int((df.tier0 != df.tier1).sum()), label_changed=int((df.lab0 != df.lab1).sum()), tiebreak_applied=int(df.tiebreak.sum()),
                        cache=dict(hits=ro.hits, misses=ro.misses))


def part_d(summary, comp_df):
    D = C.Data()
    dev = D.docs(DEFAULT_SOURCE, "DEV")
    ocr = K.load_ocr()
    hdr = lambda t: t[:300] + "\n" + t
    folds = np.array([d.folds[0] for d in dev])
    res = {}
    for name, tf_text in (("thường", lambda t: t), ("lặp 300 ký tự đầu", hdr)):
        pred = np.empty(len(dev), dtype=object)
        conf = np.zeros(len(dev))
        for f in sorted(set(folds)):
            tr = [d for d in dev if d.folds[0] != f]
            m = TfidfClassifier(D.s_classes).fit([tf_text(d.text) for d in tr], [d.label_s for d in tr])
            te = np.where(folds == f)[0]
            pr = m.predict([tf_text(dev[i].text) for i in te])
            pred[te], conf[te] = pr.labels, pr.confidence
        acc = float(np.mean([p == d.label_s for p, d in zip(pred, dev)]))
        full = TfidfClassifier(D.s_classes).fit([tf_text(d.text) for d in dev], [d.label_s for d in dev])
        bb = [text_for_classification(r["slice"]) for r in K.oracle_slices(ocr) if r["true"] == BB]
        pr = full.predict([tf_text(t) for t in bb])
        res[name] = dict(dev_oof_acc=acc, composite_bb=list(zip(pr.labels, np.round(pr.confidence, 3).tolist())))
        print(f"\n(d) TF-IDF [{name}]: DEV OOF accuracy Track S = {acc:.4f} (n={len(dev)}); các lát BB trong tệp ghép (mô hình huấn luyện trên toàn DEV): {res[name]['composite_bb']}")
    summary["d"] = res


def part_e(summary, base):
    ocr = K.load_ocr()
    out = []
    for r in K.oracle_slices(ocr):
        if r["true"] != BB:
            continue
        ans = base.llm.answer(text_for_classification(r["slice"]))
        out.append((r["file_idx"], ans.label, None if ans.conf is None else round(float(ans.conf), 3), ans.parse_ok, ans.error or ""))
    print("\n(e) LLM (Qwen3.5-4B, mô tả ngắn, 1 bước) hỏi riêng các lát BB trong tệp ghép:", out)
    ok = sum(1 for o in out if o[1] == BB)
    print(f"    LLM đúng {ok}/{len(out)}; nhãn: {Counter(o[1] for o in out)}")
    summary["e"] = dict(n=len(out), ok=ok, answers=out)


def main() -> int:
    K.OUT.mkdir(parents=True, exist_ok=True)
    summary = {}
    comp_df, base = part_a_c(summary)
    part_b(summary)
    part_d(summary, comp_df)
    part_e(summary, base)
    (K.OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
