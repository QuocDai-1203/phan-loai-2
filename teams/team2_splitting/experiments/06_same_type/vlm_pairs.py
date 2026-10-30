r"""Thí nghiệm 06b - VLM `qwen3.5:4b` (Ollama cục bộ) nhìn HAI ẢNH trang liền kề: "cùng một tờ giấy hay hai bản khác nhau?".

Ảnh render bằng PyMuPDF TRONG BỘ NHỚ (không ghi đĩa), gửi base64 tới 127.0.0.1:11434. Chỉ gọi cho các cặp "có thể cùng loại" trong phạm vi dev:
mọi cặp của tệp composite cùng loại / khác loại / BB_LAY_MAU, và cặp của tệp âm có đầu trang giống nhau (jaccard token đầu trang >= 0,4).
Giới hạn <= 300 lời gọi; cache đĩa `_cache/` (khóa = sha256 ảnh + prompt + tùy chọn); num_ctx = 32768 để không buộc Ollama nạp lại mô hình.
    .venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/06_same_type/vlm_pairs.py [--probe]
Ghi `results/vlm_pairs_dev.csv` (doc_id, trang, nhóm, nhãn đáp án, nhãn VLM, độ trễ). `p_diff` lấy từ logprob KHÔNG ràng buộc theo schema nên không đáng tin: chỉ dùng nhãn cứng.
"""
import argparse
import base64
import hashlib
import io
import json
import math
import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lib06 as L  # noqa: E402
import splitlib as sl  # noqa: E402
from src.classification.llm_cache import DiskCache, make_key  # noqa: E402
from src.splitting.learned import effective_prev  # noqa: E402
from src.splitting.page_features import jaccard, page_feat  # noqa: E402

MODEL = "qwen3.5:4b"
NUM_CTX = 32768
URL = "http://127.0.0.1:11434"
LABELS = ["SAME_SHEET", "DIFFERENT_COPY"]
MAX_CALLS = 300
PDF_ROOT = sl.REPO / "docs" / "_chot_samples_phanloaitailieu"
SYSTEM = ("Bạn xem hai ảnh quét của hai trang LIÊN TIẾP trong cùng một tệp PDF: ảnh thứ nhất là trang A, ảnh thứ hai là trang B. "
          "Trả lời SAME_SHEET nếu hai trang thuộc CÙNG MỘT tờ giấy / một tài liệu (trang tiếp theo, mặt sau, phần chữ ký, phụ lục của chính giấy đó). "
          "Trả lời DIFFERENT_COPY nếu mỗi trang là một giấy riêng, dù cùng biểu mẫu: hai bản khác nhau đã được điền thông tin riêng (khác số, khác ngày, khác người).")
USER = "Hai trang này là SAME_SHEET hay DIFFERENT_COPY?"


def render(pdf: Path, pages, dpi: int = 100, max_side: int = 1100):
    import fitz
    from PIL import Image
    out = []
    doc = fitz.open(pdf)
    try:
        for p in pages:
            pix = doc[p - 1].get_pixmap(dpi=dpi, colorspace=fitz.csRGB)
            im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            if max(im.size) > max_side:
                k = max_side / max(im.size)
                im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=85)
            out.append(buf.getvalue())
    finally:
        doc.close()
    return out


def ask(cache: DiskCache, imgs, timeout: float = 240.0) -> dict:
    import requests
    hashes = [hashlib.sha256(b).hexdigest()[:16] for b in imgs]
    opts = {"temperature": 0, "seed": 0, "num_ctx": NUM_CTX, "num_predict": 64}
    schema = {"type": "object", "properties": {"type": {"type": "string", "enum": LABELS}}, "required": ["type"]}
    key = make_key("t5-vlm-pair-v1", MODEL, SYSTEM, USER, opts, hashes)

    def call():
        body = {"model": MODEL, "stream": False, "think": False, "format": schema, "keep_alive": "10m", "options": opts,
                "logprobs": True, "top_logprobs": 5,
                "messages": [{"role": "system", "content": SYSTEM},
                             {"role": "user", "content": USER, "images": [base64.b64encode(b).decode("ascii") for b in imgs]}]}
        t0 = time.perf_counter()
        try:
            r = requests.post(f"{URL}/api/chat", json=body, timeout=timeout)
            lat = (time.perf_counter() - t0) * 1000
            if r.status_code != 200:
                return {"error": f"HTTP {r.status_code}: {r.text[:200]}", "latency_ms": lat}
            d = r.json()
            return {"content": (d.get("message") or {}).get("content", ""), "logprobs": d.get("logprobs"), "latency_ms": lat, "error": ""}
        except requests.RequestException as e:
            return {"error": f"{type(e).__name__}: {e}", "latency_ms": (time.perf_counter() - t0) * 1000}

    return cache.cached(key, call, retry_errors=True)


def p_different(rec: dict):
    """P(DIFFERENT_COPY) chuẩn hóa trên hai nhãn, từ logprob của token đầu tiên khác nhau giữa hai nhãn (SAME/DIFF)."""
    lp = rec.get("logprobs")
    toks = lp if isinstance(lp, list) else ((lp or {}).get("content") or [])
    for t in toks:
        tops = {x.get("token", "").strip().upper(): x.get("logprob") for x in (t.get("top_logprobs") or [])}
        tops[t.get("token", "").strip().upper()] = t.get("logprob")
        s = [v for k, v in tops.items() if k.startswith("SAME") and v is not None]
        d = [v for k, v in tops.items() if k.startswith("DIFF") and v is not None]
        if s or d:
            ps = math.exp(max(s)) if s else 0.0
            pd_ = math.exp(max(d)) if d else 0.0
            return pd_ / (ps + pd_) if (ps + pd_) > 0 else None
    try:
        return 1.0 if json.loads(rec["content"])["type"] == "DIFFERENT_COPY" else 0.0
    except Exception:  # noqa: BLE001
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    args = ap.parse_args()
    gold = sl.load_gold()
    ids = sl.scope_doc_ids(gold, "dev")
    docs = sl.load_documents(ids)
    meta = gold.drop_duplicates("doc_id").set_index("doc_id")
    man = pd.read_csv(sl.REPO / "data" / "manifest.csv", dtype=str, encoding="utf-8-sig", keep_default_na=False).set_index("doc_id")
    cands = []
    for d in ids:
        g = meta.loc[d, "eval_group"]
        if g not in sl.GROUPS:
            continue
        texts = [p.full_text for p in docs[d].pages]
        feats = [page_feat(t) for t in texts]
        prev = effective_prev(feats)
        gg = sl.gold_for_doc(gold, d, len(texts)).set_index("page")
        for i in range(1, len(texts)):
            j = prev[i]
            if j is None:
                continue
            jac = jaccard(feats[j].head_tokens, feats[i].head_tokens)
            if g != "negative" or jac >= 0.4:
                cands.append((d, g, docs[d].pages[j].page_number, docs[d].pages[i].page_number, int(gg.loc[docs[d].pages[i].page_number, "is_start"]), jac))
    if args.probe:
        cands = [c for c in cands if c[1] == "same_other"][:3]
    assert len(cands) <= MAX_CALLS, len(cands)
    print(f"{len(cands)} cặp ứng viên (giới hạn {MAX_CALLS})", flush=True)
    cache = DiskCache(HERE / "_cache")
    rows = []
    t0 = time.perf_counter()
    for k, (d, g, pa, pb, y, jac) in enumerate(cands):
        try:
            imgs = render(PDF_ROOT / man.loc[d, "relative_path"], [pa, pb])
            rec = ask(cache, imgs)
        except (FileNotFoundError, RuntimeError) as e:          # PDF không mở được (đường dẫn Unicode/tệp thiếu): ghi lỗi, không dừng cả lượt
            rec = {"error": f"render: {type(e).__name__}", "latency_ms": 0}
        label = ""
        try:
            label = json.loads(rec["content"])["type"] if not rec.get("error") else ""
        except Exception:  # noqa: BLE001
            pass
        rows.append(dict(doc_id=d, group=g, page_prev=pa, page=pb, y=y, jac_head=round(jac, 3), vlm_label=label,
                         p_diff=p_different(rec) if not rec.get("error") else None, latency_ms=round(rec.get("latency_ms") or 0), error=rec.get("error") or ""))
        if k % 10 == 0:
            print(f"  {k + 1}/{len(cands)}  {time.perf_counter() - t0:.0f} s  loi={sum(1 for r in rows if r['error'])}", flush=True)
    df = pd.DataFrame(rows)
    print(df.groupby(["group", "y"]).agg(n=("y", "size"), diff=("vlm_label", lambda s: int((s == "DIFFERENT_COPY").sum())), err=("error", lambda s: int((s != "").sum())),
                                          med_lat=("latency_ms", "median")))
    if not args.probe:
        (HERE / "results").mkdir(exist_ok=True)
        df.to_csv(HERE / "results" / "vlm_pairs_dev.csv", index=False)


if __name__ == "__main__":
    main()
