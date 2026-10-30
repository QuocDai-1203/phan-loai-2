"""curated.py - Các bảng gọn (Markdown) dùng trong RESULTS.md, dựng từ CSV đã lưu (không tính lại mô hình, không đụng TEST).

Mỗi hàm trả về một chuỗi Markdown; run_all.py --stage report ghi chúng vào các khối <!-- BEGIN:c_... -->.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from common import SOURCES_MAIN, TABLES, md_table
from cost_table import _cp
from eval_metrics import fmt_ci

SRC = "ocr_v2_p12"
T01 = TABLES.parent.parent / "01_classical_baselines" / "tables"
LAB = {  # nhãn gọn cho phương pháp
    "kev_s1_short_c2000": "Kev-0.8B, mô tả ngắn, 1 bước", "kev_s2_short_c2000": "Kev-0.8B, mô tả ngắn, 2 bước",
    "kev_s1_long_c2000": "Kev-0.8B, mô tả DÀI, 1 bước", "kev_s2_long_c2000": "Kev-0.8B, mô tả DÀI, 2 bước",
    "kev_s1_short_c800": "Kev-0.8B, mô tả ngắn, 800 ký tự", "kev_s2_short_c800": "Kev-0.8B, mô tả ngắn, 2 bước, 800 ký tự",
    "kev_s1_name_c2000": "Kev-0.8B, chỉ TÊN loại, 1 bước", "kev_s2_name_c2000": "Kev-0.8B, chỉ TÊN loại, 2 bước", "kev_s1_name_c800": "Kev-0.8B, chỉ TÊN loại, 800 ký tự",
    "q35_s1_short_c2000": "Qwen3.5-4B, mô tả ngắn, 1 bước", "q35_s1_long_c2000": "Qwen3.5-4B, mô tả DÀI, 1 bước", "q35_s2_short_c2000": "Qwen3.5-4B, mô tả ngắn, 2 bước",
    "q35_s1_short_c2000_icl1": "Qwen3.5-4B, mô tả ngắn + 1 ví dụ/loại", "q35_s1_name_c2000": "Qwen3.5-4B, chỉ TÊN loại", "q35_s1_short_c800": "Qwen3.5-4B, mô tả ngắn, 800 ký tự",
    "q25_s1_short_c2000": "Qwen2.5-3B, mô tả ngắn, 1 bước",
}


def _f(x, d=3):
    return "" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{d}f}"


def c_e1() -> str:
    s = pd.read_csv(TABLES / "e1_embed_track_s_dev.csv")
    z = pd.read_csv(TABLES / "e1_embed_track_z_dev.csv")
    t = pd.read_csv(TABLES / "e1_embed_test.csv") if (TABLES / "e1_embed_test.csv").exists() else None
    sel = json.loads((TABLES / "dev_selection_02.json").read_text(encoding="utf-8"))["embed"]
    rows = []
    for src in SOURCES_MAIN:
        e = sel[src]
        r = s[(s.source == src) & (s.n_chars == e["S"]["n_chars"]) & (s.method == e["S"]["method"])].iloc[0]
        tf = pd.read_csv(T01 / "dev_all_configs.csv")
        tfb = tf[(tf.source == src) & tf.family.isin(["word_lr", "char_lr", "char_svc", "word_cnb"])].sort_values("macro_f1_mean", ascending=False).iloc[0]
        row = {"nguồn": src, "phương pháp (Track S, 11 lớp)": f"bge-m3 {e['S']['n_chars']} ký tự + {e['S']['method']}", "DEV macro-F1 (15 điểm)": f"{r.macro_f1_mean:.3f} ± {r.macro_f1_std:.3f}"}
        if t is not None:
            q = t[(t.source == src) & (t.track == "S")].iloc[0]
            row["TEST macro-F1 [CI]"] = fmt_ci(q.macro_f1, q.macro_f1_lo, q.macro_f1_hi)
        row["đối chiếu TF-IDF (01): DEV"] = f"{tfb.macro_f1_mean:.3f} ± {tfb.macro_f1_std:.3f}"
        rows.append(row)
    out = "**Track S** (10 lớp + `RARE_OR_OTHER`; chọn 1 trong 12 cấu hình embedding theo macro-F1 DEV):\n\n" + md_table(pd.DataFrame(rows)) + "\n\n"
    rows = []
    for src in SOURCES_MAIN:
        for _, r in z[(z.source == src) & (z.n_chars == 2000)].iterrows():
            row = {"nguồn": src, "phương pháp (Track Z, 34 loại)": {"centroid_min2": "few-shot: tâm lớp, >= 2 mẫu/loại (out-of-fold)", "zeroshot_short": "zero-shot: so khớp mô tả loại (không mẫu)"}[r.method],
                   "DEV macro-F1 [CI]": f"{r.oof_macro_f1:.3f} [{r.oof_macro_f1_lo:.3f}; {r.oof_macro_f1_hi:.3f}]", "DEV accuracy": _f(r.oof_accuracy), "DEV recall loại hiếm": _f(r.oof_rare_recall),
                   "DEV recall loại thường": _f(r.oof_freq_recall)}
            if t is not None and r.method == "centroid_min2":
                q = t[(t.source == src) & (t.track == "Z")].iloc[0]
                row["TEST macro-F1 [CI]"] = fmt_ci(q.macro_f1, q.macro_f1_lo, q.macro_f1_hi)
                row["TEST recall loại hiếm"] = _f(q.rare_recall, 2)
            rows.append(row)
    out += "**Track Z** (20 loại có >= 3 tài liệu được chấm ở DEV, 10 ở TEST; 92% tài liệu DEV có loại thật với >= 2 mẫu ở các fold huấn luyện = \"với tới được\"):\n\n" + md_table(pd.DataFrame(rows).fillna(""))
    return out


def c_e2_dev() -> str:
    r = pd.read_csv(TABLES / "e2_zeroshot_dev.csv")
    r = r[r.source == SRC].copy()
    z = pd.read_csv(TABLES / "e1_embed_track_z_dev.csv")
    rows = []
    order = list(LAB)
    r["o"] = r.method.map({m: i for i, m in enumerate(order)})
    for _, x in r.sort_values("o").iterrows():
        rows.append({"phương pháp": LAB.get(x.method, x.method), "accuracy": _f(x.accuracy), "macro-F1 [CI 95%]": f"{x.macro_f1:.3f} [{x.macro_f1_lo:.3f}; {x.macro_f1_hi:.3f}]",
                     "recall loại hiếm (63)": _f(x.rare_recall, 2), "recall loại thường": _f(x.freq_recall, 2), "lỗi cú pháp": _f(x.parse_fail, 3),
                     "độ trễ trung vị (ms)*": f"{x.latency_ms_median:.0f}"})
    for m, lab in (("zeroshot_short", "bge-m3 so khớp mô tả (không mẫu)"), ("centroid_min2", "bge-m3 few-shot (>= 2 mẫu/loại, out-of-fold)")):
        x = z[(z.source == SRC) & (z.n_chars == 2000) & (z.method == m)].iloc[0]
        rows.append({"phương pháp": lab, "accuracy": _f(x.oof_accuracy), "macro-F1 [CI 95%]": f"{x.oof_macro_f1:.3f} [{x.oof_macro_f1_lo:.3f}; {x.oof_macro_f1_hi:.3f}]",
                     "recall loại hiếm (63)": _f(x.oof_rare_recall, 2), "recall loại thường": _f(x.oof_freq_recall, 2), "lỗi cú pháp": "", "độ trễ trung vị (ms)*": "73"})
    tf = pd.read_csv(TABLES.parent.parent / "02_llm_and_cascade" / "tables" / "e4_cascade_dev.csv")
    x = tf[(tf.source == SRC) & (tf.name == "tfidf_only(classical)") & (tf.max_error == 0.01)].iloc[0]
    rows.append({"phương pháp": "đối chiếu: TF-IDF (01) quy về Track Z, RARE_OR_OTHER = abstain", "accuracy": _f(x.accuracy), "macro-F1 [CI 95%]": f"{x.macro_f1:.3f} [{x.macro_f1_lo:.3f}; {x.macro_f1_hi:.3f}]",
                 "recall loại hiếm (63)": "0.00", "recall loại thường": "", "lỗi cú pháp": "", "độ trễ trung vị (ms)*": "3"})
    return md_table(pd.DataFrame(rows))


def c_e2_src() -> str:
    d = pd.read_csv(TABLES / "e2_zeroshot_dev.csv")
    t = pd.read_csv(TABLES / "e2_zeroshot_test.csv")
    sel = json.loads((TABLES / "dev_selection_02.json").read_text(encoding="utf-8"))
    ms = [sel["zeroshot_best"]["kev"], "kev_s2_short_c2000", sel["zeroshot_best"]["q35"], "q35_s2_short_c2000", sel["zeroshot_best"]["q25"]]
    rows = []
    for m in dict.fromkeys(ms):
        row = {"phương pháp": LAB.get(m, m)}
        for src in SOURCES_MAIN:
            x = d[(d.method == m) & (d.source == src)]
            y = t[(t.method == m) & (t.source == src)]
            row[f"{src} DEV acc / macro-F1"] = f"{x.accuracy.iloc[0]:.3f} / {x.macro_f1.iloc[0]:.3f}" if len(x) else ""
            row[f"{src} TEST acc [CI] / macro-F1"] = (f"{fmt_ci(y.accuracy.iloc[0], y.accuracy_lo.iloc[0], y.accuracy_hi.iloc[0])} / {y.macro_f1.iloc[0]:.3f}") if len(y) else ""
        rows.append(row)
    return md_table(pd.DataFrame(rows))


def c_e2_rare() -> str:
    p = pd.read_csv(TABLES / "e2_rare_per_type_dev.csv")
    cols = ["type", "n_in_split", "kev_s1_name_c2000", "q35_s1_short_c2000", "q35_s2_short_c2000", "q25_s1_short_c2000", "tfidf_best", "embfs_n2000", "embzs_n2000"]
    p = p[cols].rename(columns={"type": "loại hiếm", "n_in_split": "n (DEV)", "kev_s1_name_c2000": "Kev-0.8B tên", "q35_s1_short_c2000": "Qwen3.5 1 bước", "q35_s2_short_c2000": "Qwen3.5 2 bước",
                                "q25_s1_short_c2000": "Qwen2.5-3B", "tfidf_best": "TF-IDF (01)", "embfs_n2000": "bge few-shot", "embzs_n2000": "bge mô tả"})
    s = pd.read_csv(TABLES / "e2_rare_summary_dev.csv").set_index("method")
    tot = {"loại hiếm": "**tổng (63 tài liệu)**", "n (DEV)": 63, "Kev-0.8B tên": s.loc["kev_s1_name_c2000", "rare_recall"], "Qwen3.5 1 bước": s.loc["q35_s1_short_c2000", "rare_recall"],
           "Qwen3.5 2 bước": s.loc["q35_s2_short_c2000", "rare_recall"], "Qwen2.5-3B": s.loc["q25_s1_short_c2000", "rare_recall"], "TF-IDF (01)": s.loc["tfidf_best", "rare_recall"],
           "bge few-shot": s.loc["embfs_n2000", "rare_recall"], "bge mô tả": s.loc["embzs_n2000", "rare_recall"]}
    p = pd.concat([p, pd.DataFrame([tot])], ignore_index=True)
    return md_table(p.round(2), "{:.2f}")


def c_e3() -> str:
    c = pd.read_csv(TABLES / "e3_calibration_dev.csv")
    c = c[c.source == SRC]
    keep = ["kev_s1_name_c2000", "kev_s2_name_c2000", "kev_s1_short_c2000", "q35_s1_short_c2000", "q35_s2_short_c2000", "q35_s1_name_c2000", "q25_s1_short_c2000", "tfidf_best", "embfs_n2000", "embzs_n2000", "rule_gate"]
    rows = []
    for m in keep:
        x = c[c.method == m]
        if not len(x):
            continue
        x = x.iloc[0]
        rows.append({"phương pháp (DEV, ocr_v2_p12)": LAB.get(m, {"tfidf_best": "TF-IDF (01), Track S -> Z", "embfs_n2000": "bge-m3 few-shot", "embzs_n2000": "bge-m3 so khớp mô tả", "rule_gate": "cổng luật (không có confidence)"}.get(m, m)),
                     "accuracy": _f(x.accuracy), "ECE": _f(x.ece), "AUROC (đúng/sai)": _f(x.auroc_correct), "AURC (thấp = tốt)": _f(x.aurc),
                     "auto-file@<=1%": f"{x.autofile_1pct:.3f} ({int(x.errors_1pct)} sai/{int(x.n_accepted_1pct)})", "auto-file@<=2%": _f(x.autofile_2pct)})
    return md_table(pd.DataFrame(rows))


def c_e3_agree() -> str:
    d = pd.read_csv(TABLES / "e3_agreement_dev.csv")
    t = pd.read_csv(TABLES / "e3_agreement_test.csv")
    rows = []
    for src in (SRC, "legacy_p1"):
        for combo in d[d.source == src].agree_all_of:
            x = d[(d.source == src) & (d.agree_all_of == combo)].iloc[0]
            y = t[(t.source == src) & (t.agree_all_of == combo)]
            rows.append({"nguồn": src, "đồng thuận của": combo.replace("kev_s1_name_c2000+kev_s2_name_c2000", "Kev tên 1 bước + 2 bước").replace("q35_s1_short_c2000+q35_s2_short_c2000", "Qwen3.5 1 bước + 2 bước"),
                         "DEV nhận": f"{int(x.n_accepted)}/237 ({x.coverage:.3f})", "DEV sai": int(x.errors), "DEV cận trên sai 95%": _f(x.risk_upper95_exact),
                         "TEST nhận": f"{int(y.n_accepted.iloc[0])}/59 ({y.coverage.iloc[0]:.3f})" if len(y) else "", "TEST sai": int(y.errors.iloc[0]) if len(y) else "",
                         "TEST cận trên sai 95%": _f(y.risk_upper95_exact.iloc[0]) if len(y) else ""})
    return md_table(pd.DataFrame(rows))


def _e4_rows(df: pd.DataFrame, src: str, tol: float, n_docs: int, test: bool) -> pd.DataFrame:
    g = df[(df.source == src) & (df.max_error == tol)]
    rows = []
    for _, r in g.iterrows():
        k, n = int(r.n_accepted), n_docs
        lo, hi = _cp(k, n)
        row = {"cấu hình": r["name"].replace("full[", "đầy đủ [tầng-3 = ").replace("]", "]") if r["name"].startswith("full[") else r["name"],
               "tự nhận (k/n)": f"{k}/{n} = {k / n:.3f}", "CP 95%": f"[{lo:.3f}; {hi:.3f}]", "sai": int(r.errors), "cận trên sai 95%": _f(r.risk_upper95_exact),
               "macro-F1": _f(r.macro_f1), "luật %": f"{100 * r.share_rule:.0f}", "TF-IDF %": f"{100 * r.share_tfidf:.0f}", "LLM/emb %": f"{100 * r.share_llm:.0f}", "người %": f"{100 * r.share_human:.0f}",
               "ms/tài liệu (rảnh)*": "" if pd.isna(r.latency_quiet_est_ms) else f"{r.latency_quiet_est_ms:.0f}"}
        if not test:
            row["cross-fit tự nhận (sai)"] = f"{r.cf_coverage:.3f} ({int(r.cf_errors)})"
        rows.append(row)
    return pd.DataFrame(rows)


def c_e4(test: bool, src: str = SRC, tol: float = 0.01) -> str:
    df = pd.read_csv(TABLES / ("e4_cascade_test.csv" if test else "e4_cascade_dev.csv"))
    n = 59 if test else 237
    return md_table(_e4_rows(df, src, tol, n, test).fillna(""))


def c_e4_pair() -> str:
    p = pd.read_csv(TABLES / "e4_cascade_test_paired.csv")
    p = p[p.max_error == 0.01]
    rows = []
    for _, r in p.iterrows():
        rows.append({"nguồn": r.source, "cascade (tầng-3)": r.A.replace("full[", "").replace("]", ""),
                     "Δ tự nhận [CI]": fmt_ci(r.d_autofile, r.d_autofile_lo, r.d_autofile_hi), "Δ nhận ĐÚNG [CI]": fmt_ci(r.d_correct_autofiled, r.d_correct_lo, r.d_correct_hi),
                     "Δ nhận SAI [CI]": fmt_ci(r.d_wrong_autofiled, r.d_wrong_lo, r.d_wrong_hi), "Δ macro-F1 [CI]": fmt_ci(r.d_macro_f1, r.d_macro_f1_lo, r.d_macro_f1_hi), "p (macro-F1)": _f(r.macro_f1_p)})
    return md_table(pd.DataFrame(rows))


def c_cost() -> str:
    c = pd.read_csv(TABLES / "cost_privacy.csv")
    drop = ("kev_s2_short_c2000", "q35_s2_short_c2000", "q25_s1_short_c2000 -> người")
    c = c[~c.design.apply(lambda d: any(x in d for x in drop))]
    c = c[~c.design.str.contains("Qwen2.5-3B") | True]
    show = c[["design", "on_prem", "labelled_data", "new_type_no_retrain", "vram_gb", "latency_ms_median", "latency_ms_p95", "docs_per_hour", "ocr_s_per_page", "quality", "services"]].copy()
    show.columns = ["thiết kế", "on-premise?", "cần dữ liệu gán nhãn?", "loại MỚI không huấn luyện lại?", "VRAM (GB)", "độ trễ trung vị (ms)", "p95 (ms)",
                    "tài liệu/giờ (1 luồng, chỉ phân loại)", "OCR (s/trang)", "chất lượng (ocr_v2_p12, TEST, 59 tài liệu)", "dịch vụ phải chạy"]
    fmt = {"VRAM (GB)": lambda v: f"{v:.2f}", "độ trễ trung vị (ms)": lambda v: f"{v:,.0f}", "p95 (ms)": lambda v: f"{v:,.0f}", "tài liệu/giờ (1 luồng, chỉ phân loại)": lambda v: f"{v:,.0f}"}
    for col, f in fmt.items():
        show[col] = [("" if pd.isna(v) else f(v)) for v in show[col]]
    return md_table(show.fillna(""))
