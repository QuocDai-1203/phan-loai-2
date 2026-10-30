"""regress_vs_ocr_v2.py - Kiểm hồi quy engine OCR trong src/ocr so với data/ocr_v2.jsonl (chỉ ĐỌC tệp này).

Với mỗi doc_id: OCR lại bằng `src.ocr.pdf_ocr.ocr_pdf_pages` (engine VietOCR nạp từ models/ocr), so từng trang với bản ghi trong
data/ocr_v2.jsonl: `source`, `text` (so từng ký tự), `flags`. Kết quả ghi vào _scratch/ (KHÔNG ghi data/).

  .venv\\Scripts\\python.exe -X utf8 teams\\team1_ocr\\experiments\\07_src_engine\\regress_vs_ocr_v2.py --device cpu \\
      --doc-ids 741b37405405 91e3dcb5fa4e 5139035b5c3f
"""
from __future__ import annotations

import argparse
import difflib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from build_ocr_dataset import CORPUS, list_pdfs, make_doc_id  # noqa: E402
from src.ocr.pdf_ocr import ocr_pdf_pages  # noqa: E402
from src.ocr.vietocr_engine import VietOCREngine  # noqa: E402


def char_diff(a: str, b: str, ctx: int = 12) -> list[str]:
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal":
            out.append(f"{tag}: ocr_v2[{i1}:{i2}]={a[max(0, i1 - ctx):i2 + ctx]!r} | src[{j1}:{j2}]={b[max(0, j1 - ctx):j2 + ctx]!r}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ocr-v2", type=Path, default=REPO / "data" / "ocr_v2.jsonl")
    ap.add_argument("--doc-ids", nargs="+", required=True)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--out", type=Path, default=HERE / "_scratch" / "regress.json")
    args = ap.parse_args()
    if args.out.resolve().is_relative_to(REPO / "data"):
        print("từ chối ghi vào data/")
        return 2

    recs = {}
    for line in args.ocr_v2.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            if r["doc_id"] in args.doc_ids:
                recs[r["doc_id"]] = r
    missing = [d for d in args.doc_ids if d not in recs]
    if missing:
        print("không có trong ocr_v2.jsonl:", missing)
        return 2
    pdfs = list_pdfs(CORPUS)
    path_of = {make_doc_id(rel): p for rel, p in pdfs.items()}

    t0 = time.perf_counter()
    engine = VietOCREngine("vgg_seq2seq", args.device, args.threads)
    t_load = time.perf_counter() - t0
    print(f"engine: {engine.name} (nạp {t_load:.1f}s)")
    report = {"engine": engine.name, "device": args.device, "docs": []}
    all_equal = True
    for did in args.doc_ids:
        ref = recs[did]
        t1 = time.perf_counter()
        n, outs = ocr_pdf_pages(path_of[did], engine, dpi=200, max_pages=30)
        dt = time.perf_counter() - t1
        d = {"doc_id": did, "pages": [], "seconds": round(dt, 1), "page_count": n}
        for o in outs:
            rp = ref["pages"][o.page - 1]
            same_text = o.text == rp["text"]
            diffs = [] if same_text else char_diff(rp["text"], o.text)
            all_equal &= same_text and o.source == rp["source"] and o.error is None
            d["pages"].append({
                "page": o.page, "source_new": o.source, "source_ref": rp["source"], "text_equal": same_text,
                "n_chars_new": o.n_chars, "n_chars_ref": rp["n_chars"],
                "mean_conf_new": o.mean_conf, "mean_conf_ref": rp["mean_conf"], "flags_new": o.flags, "flags_ref": rp.get("flags"),
                "error": o.error, "n_char_edits": len(diffs), "diff_head": diffs[:10]})
        report["docs"].append(d)
        print(f"{did}: " + ", ".join(f"p{p['page']} {p['source_new']} text_equal={p['text_equal']} edits={p['n_char_edits']}" for p in d["pages"]) + f"  ({dt:.1f}s)")
        # đường hợp đồng: dựng OCRPageResult từ cùng kết quả, round-trip JSON phải giữ nguyên văn bản/nguồn/engine/conf
        for o in outs:
            pc = o.to_contract()
            back = type(pc).model_validate_json(pc.model_dump_json())
            assert back == pc and back.full_text == o.text and back.source == o.source and back.mean_conf == o.mean_conf
    report["all_equal"] = all_equal
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print("TẤT CẢ TRÙNG" if all_equal else "CÓ KHÁC BIỆT (xem " + str(args.out) + ")")
    return 0 if all_equal else 1


if __name__ == "__main__":
    sys.exit(main())
