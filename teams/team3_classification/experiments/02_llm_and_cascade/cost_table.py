"""cost_table.py - Bảng chi phí / riêng tư: ghép các số ĐO (độ trễ, VRAM, chất lượng TEST kèm CI) từ các CSV của thí nghiệm 01 và 02.

Các cột kiểu "cần dữ liệu gán nhãn", "loại mới không huấn luyện lại" là phán đoán thiết kế có dẫn chứng bằng số đo ở mục E1/E2 (RESULTS.md); chúng được ghi rõ là phán đoán.
Không có giá tiền nào được bịa: phần đám mây chỉ có ước lượng bậc độ lớn về token (cloud_token_estimate.json), gắn nhãn "ước lượng".
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from common import REPO, TABLES, dump_json
from eval_metrics import fmt_ci

T01 = REPO / "teams" / "team3_classification" / "results" / "01_classical_baselines" / "tables"
OCR_NOTE = "3-6 s/trang (1 tiến trình VietOCR); thông lượng 0.39 trang/s (6 worker GPU) = 2.6 s/trang [team1 02_dataset_v2]"


def _rd(name: str) -> pd.DataFrame:
    p = TABLES / f"{name}.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


def _cp(k: int, n: int):
    """Khoảng tin cậy 95% Clopper-Pearson hai phía cho tỉ lệ k/n (khi bootstrap cho CI suy biến [1;1])."""
    from scipy.stats import beta

    lo = 0.0 if k == 0 else float(beta.ppf(0.025, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(0.975, k + 1, n - k))
    return lo, hi


def _dph(ms):
    return 3.6e6 / ms if (ms == ms and ms and ms > 0) else np.nan


def build_cost_table(src: str = "ocr_v2_p12") -> pd.DataFrame:
    lat, e4, e2, e1 = _rd("latency_vram_quiet"), _rd("e4_cascade_test"), _rd("e2_zeroshot_test"), _rd("e1_embed_test")

    def latrow(prefix: str):
        r = lat[lat["method"].astype(str).str.startswith(prefix)] if len(lat) else lat
        return (float(r.latency_ms_median.iloc[0]), float(r.latency_ms_p95.iloc[0]), float(r.vram_mb.iloc[0]) if r.vram_mb.iloc[0] == r.vram_mb.iloc[0] else np.nan) if len(r) else (np.nan, np.nan, np.nan)

    rows = []
    rg = pd.read_csv(T01 / "rule_gate_test_track_z.csv")
    rr = rg[rg.source == src].iloc[0]
    l, p95, v = latrow("rule_gate")
    rows.append(dict(design="Cổng luật từ khóa tiêu đề", on_prem="có", labelled_data="không (từ khóa do người viết)", new_type_no_retrain="một phần: phải viết từ khóa",
                     vram_gb=0.0, latency_ms_median=l, latency_ms_p95=p95, docs_per_hour=_dph(l), text_source=src,
                     quality=f"TEST Track Z: coverage {rr.coverage:.3f}, đúng trên phần quyết định {rr.accuracy_on_covered:.3f} (tất định, không CI)", services="không"))
    tm = pd.read_csv(T01 / "test_main.csv")
    tr = tm[(tm.source == src) & (tm["rank"].astype(str).str.startswith("1"))].iloc[0]
    st = pd.read_csv(T01 / "selective_test.csv")
    sr = st[(st.source == src) & (st.config == tr.config) & (st.max_error == 0.01)].iloc[0]
    l, p95, v = latrow("tfidf")
    rows.append(dict(design="TF-IDF + ComplementNB (Track S)", on_prem="có", labelled_data="có: >= 5-10 tài liệu/loại (01, mục 7c)", new_type_no_retrain="không: cần mẫu và huấn luyện lại (~0.4 s)",
                     vram_gb=0.0, latency_ms_median=l, latency_ms_p95=p95, docs_per_hour=_dph(l), text_source=src,
                     quality=f"TEST macro-F1 (10 lớp + gộp) {fmt_ci(tr.macro_f1, tr.f1_lo, tr.f1_hi)}; auto-file <=1% sai {fmt_ci(sr.test_coverage, sr.test_coverage_lo, sr.test_coverage_hi)} (trần {sr.test_ceiling_non_pool:.2f}; loại hiếm luôn cho người)",
                     services="không"))
    for _, r in e1.iterrows() if len(e1) else []:
        if r.source == src and r.track == "Z":
            l, p95, v = latrow("bge-m3")
            rows.append(dict(design="Embedding bge-m3 few-shot (tâm lớp, >= 2 mẫu/loại)", on_prem="có", labelled_data="có, rất ít: 2 mẫu/loại", new_type_no_retrain="một phần: thêm >= 2 mẫu, không huấn luyện",
                             vram_gb=(v / 1024 if v == v else np.nan), latency_ms_median=l, latency_ms_p95=p95, docs_per_hour=_dph(l), text_source=src,
                             quality=f"TEST Track Z macro-F1 {fmt_ci(r.macro_f1, r.macro_f1_lo, r.macro_f1_hi)} ({int(r.n_types_scored)} loại), recall loại hiếm {r.rare_recall:.2f}", services="Ollama (bge-m3)"))
    for _, r in e2[e2.source == src].iterrows() if len(e2) else []:
        fam = "Kev-0.8B" if str(r.method).startswith("kev") else ("Qwen3.5-4B" if "q35" in str(r.method) else "Qwen2.5-3B")
        l, p95, v = latrow(str(r.method))
        rows.append(dict(design=f"Zero-shot {fam} ({r.method})", on_prem="có", labelled_data="không (chỉ mô tả loại)", new_type_no_retrain="có: thêm mô tả (độ tin cậy: xem recall loại hiếm, E2)",
                         vram_gb=(v / 1024 if v == v else np.nan), latency_ms_median=l, latency_ms_p95=p95, docs_per_hour=_dph(l), text_source=src,
                         quality=f"TEST Track Z macro-F1 {fmt_ci(r.macro_f1, r.macro_f1_lo, r.macro_f1_hi)}, accuracy {fmt_ci(r.accuracy, r.accuracy_lo, r.accuracy_hi)}, recall loại hiếm {r.rare_recall:.2f}",
                         services="Kev server (GPU)" if fam.startswith("Kev") else "Ollama (GPU)"))
    def t3_quiet(t3: str):
        """(median, p95, vram_mb) của tầng-3 đo lúc máy rảnh; biến thể hai bước chỉ lấy VRAM (độ trễ hai bước không đo lúc rảnh)."""
        if t3 == "embfs":
            return latrow("bge-m3")
        key = {"kev": "kev_s1_name", "q35": "q35_s1_short", "q25": "q25_s1_short"}[t3.split("_")[0]]
        m, p95, v = latrow(key)
        return (np.nan, np.nan, v) if "_s2_" in t3 else (m, p95, v)

    l_rule, _, _ = latrow("rule_gate")
    l_tf, p_tf, _ = latrow("tfidf")
    for _, r in e4[(e4.source == src) & (e4.name.astype(str).str.startswith("full[")) & (e4.max_error == 0.01)].iterrows() if len(e4) else []:
        l3, p3, v3 = t3_quiet(r.t3)
        reach_tf, reach_llm = 1 - r.share_rule, 1 - r.share_rule - r.share_tfidf
        mean_q = l_rule + reach_tf * l_tf + reach_llm * l3      # trung bình ước tính với độ trễ đo lúc rảnh
        if reach_llm >= 0.05:
            p95_q = l_rule + l_tf + p3
        elif reach_tf >= 0.05:
            p95_q = l_rule + p_tf
        else:
            p95_q = l_rule
        cp = _cp(int(r.n_accepted), int(r.n_docs))
        rows.append(dict(design=f"Cascade luật -> TF-IDF -> {r.t3} -> người", on_prem="có", labelled_data="có (TF-IDF, embedding) + mô tả loại", new_type_no_retrain="có ở tầng 3 (xem E2/E4)",
                         vram_gb=(v3 / 1024 if v3 == v3 else np.nan), latency_ms_median=l_rule + (l_tf if reach_tf > 0.5 else 0.0), latency_ms_p95=p95_q, docs_per_hour=_dph(mean_q), text_source=src,
                         quality=f"TEST tự nhận {r.coverage:.3f} (Clopper-Pearson 95% [{cp[0]:.3f}; {cp[1]:.3f}]), {int(r.errors)} sai / {int(r.n_accepted)} nhận (cận trên sai {r.risk_upper95_exact:.3f}); tầng-3 xử lý {reach_llm:.0%} tài liệu; trung bình ước tính " + (f"{mean_q:.0f} ms/tài liệu (lúc rảnh)" if mean_q == mean_q else "n/a"),
                         services="Kev/Ollama (GPU)" + (" + Ollama bge-m3" if r.t3 == "embfs" else "")))
    rows.append(dict(design="Phiên âm đám mây (LLM-vision) + TF-IDF", on_prem="KHÔNG: ảnh tài liệu gửi nhà cung cấp ngoài", labelled_data="có (TF-IDF)", new_type_no_retrain="không (TF-IDF); có nếu thêm LLM",
                     vram_gb=0.0, latency_ms_median=np.nan, latency_ms_p95=np.nan, docs_per_hour=np.nan, text_source="haiku_p12",
                     quality="cận trên: 01 TEST macro-F1 0.974 [0.928; 1.000] - KHÔNG phải số triển khai", services="API đám mây + quyết định riêng tư của công ty"))
    df = pd.DataFrame(rows)
    df["ocr_s_per_page"] = [OCR_NOTE if d != "Phiên âm đám mây (LLM-vision) + TF-IDF" else "không đo (phụ thuộc nhà cung cấp và mạng)" for d in df["design"]]
    # ước lượng token đám mây (bậc độ lớn)
    n_pages, n_chars = 0, 0
    with open(REPO / "data" / "ocr_llm_haiku.jsonl", encoding="utf-8") as f:
        for line in f:
            for pg in json.loads(line).get("pages", []):
                n_pages += 1
                n_chars += len(pg.get("text") or "")
    dump_json(TABLES / "cloud_token_estimate.json", dict(
        pages_transcribed=n_pages, mean_chars_per_page=n_chars / max(n_pages, 1),
        est_output_tokens_per_page=n_chars / max(n_pages, 1) / 3,
        note="ƯỚC LƯỢNG bậc độ lớn: giả định ~3 ký tự/token cho tiếng Việt; token ảnh đầu vào giả định ~1.5-3k/trang (không đo). KHÔNG có giá tiền."))
    return df
