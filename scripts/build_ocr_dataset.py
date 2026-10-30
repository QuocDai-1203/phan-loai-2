"""build_ocr_dataset.py - Dựng data/ocr_v2.jsonl: OCR TẤT CẢ các trang (tối đa 30/tài liệu), có truy vết nguồn.

Khác với baseline (generate_baseline_ocr.py: chỉ trang 1, mất dấu tiếng Việt, không nói text đến từ đâu):
  * mọi trang đều được xử lý, mỗi trang ghi rõ `source`, `engine`, `dpi`, `mean_conf`, `seconds`, `error`;
  * text layer của PDF chỉ được dùng khi "đáng tin" (xem `assess_text_layer`), còn lại OCR bằng engine đã chọn
    trong bake-off (teams/team1_ocr/experiments/01_engine_bakeoff/RESULTS.md): bộ phát hiện dòng chữ DB của
    PP-OCRv5 (rapidocr) + VietOCR nhận dạng (có đủ bộ dấu tiếng Việt);
  * lỗi không bao giờ bị nuốt: trang lỗi có `error` khác null, script tiếp tục và thoát mã 1 ở cuối.

Quy tắc dùng text layer (một trang được coi là TIN CẬY khi thoả đồng thời):
  1. có >= MIN_LETTERS (30) chữ cái trong lớp chữ;
  2. chữ HIỂN THỊ (không phải render mode 3 / vô hình) chiếm >= 50% số ký tự (lớp OCR của máy scan là chữ vô hình);
  3. trang KHÔNG phải một ảnh phủ >= 80% diện tích kèm lớp chữ (dấu hiệu máy scan/CamScanner nhúng OCR kém);
  4. tỉ lệ ký tự rác (U+FFFD, vùng private-use U+E000-F8FF, ký tự điều khiển) < 2%.
  Trang có lớp chữ nhưng không đạt => `source = "embedded_ocr_layer+ocr"` (bỏ lớp chữ, OCR lại ảnh).
  Trang không có lớp chữ => `source = "ocr"`.  Trang đạt => `source = "text_layer"`.

Giới hạn 30 trang/tài liệu (`pages_truncated=true` nếu vượt): 6/336 tài liệu dài 46-93 trang (biên bản lấy mẫu, sổ PCCC);
trang sau trang 30 hầu hết là biểu mẫu lặp lại, còn chi phí OCR tăng tuyến tính (~dài nhất 93 trang = 8% tổng thời gian).
Phân loại tài liệu chỉ cần phần đầu. Đổi bằng --max-pages.

doc_id = sha1(rel.encode('utf-8')).hexdigest()[:12], rel = đường dẫn tương đối so với
docs/_chot_samples_phanloaitailieu, dấu '/', Unicode NFC (khớp scripts/build_manifest.py).

Từ 2026-10-12 toàn bộ logic OCR (quy tắc text layer, chuẩn hóa nền, tự xoay, VietOCR) nằm trong `src/ocr/` (`vietocr_engine.py`,
`pdf_ocr.py`); script này chỉ lo phần điều phối kho tài liệu (doc_id, trùng byte, cache, ghi JSONL) và import từ đó. Mô hình đọc từ
`models/ocr/` (xem models/README.md), không tải từ mạng.

Cách chạy (từ thư mục gốc repo):
  .venv\\Scripts\\python.exe -X utf8 scripts\\build_ocr_dataset.py --limit 3                 # chạy thử
  .venv\\Scripts\\python.exe -X utf8 scripts\\build_ocr_dataset.py --workers 4 --resume      # chạy đầy đủ, tiếp tục được
Kết quả từng tài liệu được cache ở teams/team1_ocr/experiments/02_dataset_v2/_cache/docs/<doc_id>.json
(không commit) => --resume bỏ qua tài liệu đã xong (cùng engine/dpi/max-pages).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.ocr.pdf_ocr import (FULLPAGE_IMG, MAX_GARBAGE, MIN_LETTERS, MIN_VISIBLE_SHARE, assess_text_layer,  # noqa: E402,F401
                             clean_text, nfc, ocr_pdf_pages, render)
from src.ocr.vietocr_engine import (VIETOCR_MODELS, VietOCREngine, bg_normalize, boxes_to_text,  # noqa: E402,F401
                                    needs_bgnorm)

CORPUS = REPO / "docs" / "_chot_samples_phanloaitailieu"
OUT_DEFAULT = REPO / "data" / "ocr_v2.jsonl"
CACHE_DEFAULT = REPO / "teams" / "team1_ocr" / "experiments" / "02_dataset_v2" / "_cache" / "docs"

SCHEMA_VERSION = 2


# --------------------------------------------------------------------------------------- tiện ích chung
def make_doc_id(rel: str) -> str:
    return hashlib.sha1(nfc(rel).encode("utf-8")).hexdigest()[:12]


def list_pdfs(root: Path) -> dict:
    """{rel_NFC: Path_trên_đĩa} (tên tệp trên đĩa có thể là NFC hoặc NFD nên phải map)."""
    out = {}
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() == ".pdf":
            out[nfc(p.relative_to(root).as_posix())] = p
    return dict(sorted(out.items()))


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def make_engine(args):
    return VietOCREngine(VIETOCR_MODELS[args.engine], args.device, args.threads, batch=args.batch, max_width=args.max_width,
                         det_max_side=args.det_max_side, models_override=args.models_dir)


# --------------------------------------------------------------------------------------- tài liệu
_ENGINE = None
_ARGS = None


def _init_worker(args):
    global _ENGINE, _ARGS
    _ARGS = args
    _ENGINE = make_engine(args)


def process_doc(rel: str, path: str) -> dict:
    """Xử lý một tài liệu trong worker. Không raise: mọi lỗi nằm trong `error` của từng trang."""
    args = _ARGS
    folder = rel.split("/")[0] if "/" in rel else None
    rec = dict(doc_id=make_doc_id(rel), relative_path=rel, file_name=rel.split("/")[-1], folder_label=folder,
               page_count=0, pages_processed=0, pages_truncated=False, pages=[], ocr_engine=_ENGINE.name,
               created_at=None)
    try:
        n, outs = ocr_pdf_pages(path, _ENGINE, dpi=args.dpi, max_pages=args.max_pages)
    except ValueError as e:  # tệp hỏng (open_failed)
        rec["pages"] = [dict(page=1, source=None, engine=None, dpi=None, text="", n_chars=0, mean_conf=None,
                             seconds=0.0, error=str(e))]
        rec["created_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return rec
    rec["page_count"] = n
    rec["pages_truncated"] = n > args.max_pages
    rec["pages"] = [o.to_record() for o in outs]
    rec["pages_processed"] = len(rec["pages"])
    rec["created_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return rec


# --------------------------------------------------------------------------------------- điều phối
def cache_key(args) -> str:
    return f"{SCHEMA_VERSION}|{args.engine}|{args.dpi}|{args.max_pages}|{args.max_width}|bgsat15|det{args.det_max_side}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", type=Path, default=CORPUS)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--cache", type=Path, default=CACHE_DEFAULT, help="thư mục cache theo tài liệu (không commit)")
    ap.add_argument("--engine", choices=["viet_seq2seq", "viet_transformer"], default="viet_seq2seq")
    ap.add_argument("--device", default="cpu", help="cpu hoặc cuda:0 (GPU dùng chung có thể bị tranh chấp, xem RESULTS.md)")
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--max-pages", type=int, default=30)
    ap.add_argument("--models-dir", type=Path, default=None, help="thư mục mô hình OCR (mặc định models/ocr hoặc $SDH_OCR_MODELS_DIR)")
    ap.add_argument("--max-width", type=int, default=None, help="ghi đè image_max_width của VietOCR (mặc định 512)")
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--det-max-side", type=int, default=0, help="cạnh dài tối đa của ảnh đưa vào bộ phát hiện (0 = mặc định rapidocr, ảnh gốc)")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--threads", type=int, default=8, help="số luồng torch/onnx mỗi worker")
    ap.add_argument("--limit", type=int, default=0, help="chỉ xử lý N tài liệu đầu (chạy thử); không ghi đè --out")
    ap.add_argument("--resume", action="store_true", help="bỏ qua tài liệu đã có trong cache cùng cấu hình")
    args = ap.parse_args(argv)

    t_start = time.time()
    pdfs = list_pdfs(args.root)
    items = list(pdfs.items())
    if args.limit:
        # lấy mẫu rải đều thay vì N tài liệu đầu (cùng thư mục) để smoke test có ý nghĩa
        step = max(len(items) // args.limit, 1)
        items = items[::step][:args.limit]
    out = args.out
    if args.limit and out == OUT_DEFAULT:
        out = REPO / "teams" / "team1_ocr" / "experiments" / "02_dataset_v2" / "_cache" / "ocr_v2_smoke.jsonl"
    args.cache.mkdir(parents=True, exist_ok=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    key = cache_key(args)

    # Tệp trùng byte-by-byte (cùng sha256): OCR một lần, các bản còn lại sao chép kết quả (đánh dấu trong `flags`)
    sha = {rel: sha256_file(p) for rel, p in items}
    primary_of = {}
    for rel, _ in items:                      # items đã sắp theo rel => bản đầu tiên là primary
        primary_of.setdefault(sha[rel], rel)
    primaries = [(rel, p) for rel, p in items if primary_of[sha[rel]] == rel]
    n_dup = len(items) - len(primaries)

    ids = {rel: make_doc_id(rel) for rel, _ in items}
    if len(set(ids.values())) != len(ids):
        print("LỖI: doc_id trùng nhau", file=sys.stderr)
        return 2

    def cache_file(rel):
        return args.cache / f"{ids[rel]}.json"

    todo = []
    for rel, p in primaries:
        cf = cache_file(rel)
        if args.resume and cf.exists():
            try:
                d = json.loads(cf.read_text(encoding="utf-8"))
                if d.get("_key") == key and not any(pg.get("error") for pg in d["rec"]["pages"]):
                    continue  # tài liệu xong và không lỗi; có lỗi thì làm lại
            except Exception:
                pass
        todo.append((rel, str(p)))
    print(f"[*] {len(items)} PDF ({n_dup} trùng byte với tệp khác => sao chép kết quả), cần OCR {len(todo)} "
          f"(đã xong {len(primaries) - len(todo)}); engine={args.engine} "
          f"device={args.device} dpi={args.dpi} workers={args.workers}", flush=True)

    done = 0
    if todo:
        # sắp tài liệu dài lên trước để cân tải giữa các worker (kết quả cuối vẫn sắp theo relative_path)
        todo.sort(key=lambda t: -os.path.getsize(t[1]))
        if args.workers <= 1:
            _init_worker(args)
            results = (process_doc(r, p) for r, p in todo)
            for rec in results:
                _save(cache_file(rec["relative_path"]), key, rec)
                done += 1
                _progress(done, len(todo), rec, t_start)
        else:
            with ProcessPoolExecutor(max_workers=args.workers, initializer=_init_worker, initargs=(args,)) as ex:
                futs = {ex.submit(process_doc, r, p): r for r, p in todo}
                for f in as_completed(futs):
                    rec = f.result()
                    _save(cache_file(rec["relative_path"]), key, rec)
                    done += 1
                    _progress(done, len(todo), rec, t_start)

    # --- lắp ráp tệp cuối, sắp theo relative_path
    recs = []
    missing = []
    for rel, _ in items:
        prim = primary_of[sha[rel]]
        cf = cache_file(prim)
        if not cf.exists():
            missing.append(rel)
            continue
        rec = json.loads(cf.read_text(encoding="utf-8"))["rec"]
        if prim != rel:
            rec["doc_id"] = ids[rel]
            rec["relative_path"] = rel
            rec["file_name"] = rel.split("/")[-1]
            rec["folder_label"] = rel.split("/")[0] if "/" in rel else None
            rec["created_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            for pg in rec["pages"]:
                pg["seconds"] = 0.0
                pg["flags"] = list(pg.get("flags", [])) + [f"copied_from_exact_duplicate:{ids[prim]}"]
        recs.append(rec)
    recs.sort(key=lambda r: r["relative_path"])
    tmp = out.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp.replace(out)

    return summarize(recs, missing, out, time.time() - t_start)


def _save(path: Path, key: str, rec: dict):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"_key": key, "rec": rec}, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _progress(done, total, rec, t0):
    el = time.time() - t0
    print(f"  [{done}/{total}] {rec['relative_path'][:70]} p={rec['pages_processed']}/{rec['page_count']} "
          f"({el/60:.1f} phút)", flush=True)


def summarize(recs, missing, out, elapsed) -> int:
    from collections import Counter
    pages = [pg for r in recs for pg in r["pages"]]
    src = Counter(pg["source"] for pg in pages)
    errs = [(r["relative_path"], pg["page"], pg["error"]) for r in recs for pg in r["pages"] if pg["error"]]
    empty = sum(1 for pg in pages if not pg["error"] and pg["n_chars"] < 5)
    trunc = sum(1 for r in recs if r["pages_truncated"])
    print("=" * 70)
    print(f"Tài liệu: {len(recs)} | trang xử lý: {len(pages)} | tài liệu bị cắt >max-pages: {trunc}")
    print(f"Trang theo nguồn: {dict(src)}")
    print(f"Trang gần như trống (<5 ký tự, không lỗi): {empty}")
    print(f"Lỗi: {len(errs)} trang | tài liệu thiếu kết quả: {len(missing)}")
    for rel, pno, e in errs[:20]:
        print(f"   LỖI {rel} trang {pno}: {e}")
    ocr_pages = [pg for pg in pages if pg["source"] and "ocr" in pg["source"]]
    if ocr_pages:
        secs = sum(pg["seconds"] for pg in ocr_pages)
        print(f"Giây OCR tổng (cộng dồn các worker): {secs:.0f} -> {secs/len(ocr_pages):.1f} giây/trang OCR")
    print(f"Tổng thời gian thực: {elapsed/60:.1f} phút ({len(pages)/max(elapsed,1e-9):.2f} trang/giây)")
    print(f"Đã ghi: {out}")
    return 1 if (errs or missing) else 0


if __name__ == "__main__":
    sys.exit(main())
