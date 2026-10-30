r"""Ghép các bản chép từng trang của LLM (data/ocr_llm_haiku/pages/<doc_id>_p<N>.txt) thành một file
data/ocr_llm_haiku.jsonl cùng schema với data/ocr_v2.jsonl (một dòng = một tài liệu, có mảng `pages`).

Bản chép do Claude Haiku đọc ảnh trang (200 dpi, cắt đôi trang) tạo ra - xem
teams/team1_ocr/experiments/03_llm_silver/ để biết cách đo độ chính xác của nó.
Chỉ có 2 trang đầu của mỗi tài liệu DUY NHẤT; tài liệu trùng byte dùng chung bản chép của bản đại diện.

Chạy:  .venv\Scripts\python -X utf8 scripts\assemble_llm_ocr.py

CỔNG KIỂM LÔ (T6, teams/team1_ocr/README.md): chỉ ghép lô đã qua
teams/team1_ocr/experiments/03_llm_silver/validate_batch.py, tức thư mục --pages-dir có `_validation.json` trạng thái `valid` và hash
nội dung các tệp .txt còn khớp (sửa tệp sau khi kiểm thì bị từ chối). Lô chưa qua kiểm -> thoát mã 2, không ghi gì.
Bỏ qua cổng (ví dụ lô Haiku cũ làm trước khi có validate_batch.py): `--skip-validation "lý do"`; mỗi lần bỏ qua được GHI LOG vào
`<pages-dir>/../_validation_skipped.log` (thời gian, lô, hash, lý do) và in cảnh báo.
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
_PAGE = re.compile(r"^(?P<doc>[0-9a-f]{12})_p(?P<page>\d+)\.txt$")
_MARK = re.compile(r"\[[^\]\n]{0,200}\]")


def strip_markers(text: str) -> str:
    """Bỏ chú thích của người chép ([dấu: ...], [chữ ký], [?], [trang xoay]...) và dấu phân cách ô bảng."""
    return re.sub(r"[ \t]+", " ", _MARK.sub(" ", text).replace("|", " ")).strip()


STAMP_NAME = "_validation.json"


def content_hash(pages_dir) -> str:
    """Phải giống hệt validate_batch.content_hash: sha1 theo (tên tệp, nội dung) của mọi *.txt không bắt đầu bằng '_'."""
    h = hashlib.sha1()
    for p in sorted(Path(pages_dir).glob("*.txt")):
        if not p.name.startswith("_"):
            h.update(p.name.encode("utf-8") + b"\x00" + p.read_bytes() + b"\x00")
    return h.hexdigest()


def check_batch_validated(pages_dir) -> str:
    """Trả về "" nếu lô đã qua kiểm và nội dung không đổi; ngược lại trả lý do từ chối."""
    f = Path(pages_dir) / STAMP_NAME
    if not f.exists():
        return f"chưa kiểm: không có {f} (chạy teams/team1_ocr/experiments/03_llm_silver/validate_batch.py)"
    try:
        st = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return f"{f} hỏng: {e}"
    if st.get("status") != "valid":
        return f"lô KHÔNG HỢP LỆ theo {f}: " + "; ".join(st.get("reasons") or ["(không rõ lý do)"])
    if st.get("content_sha1") != content_hash(pages_dir):
        return f"nội dung lô đã đổi sau khi kiểm (hash trong {f} không khớp); kiểm lại bằng validate_batch.py"
    return ""


def log_skip(pages_dir, reason: str, why_refused: str) -> Path:
    log = Path(pages_dir).parent / "_validation_skipped.log"
    rec = dict(time=datetime.now(timezone.utc).isoformat(timespec="seconds"), pages_dir=str(pages_dir),
               content_sha1=content_hash(pages_dir), reason=reason, would_have_been_refused_because=why_refused)
    with open(log, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return log


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages-dir", default=str(ROOT / "data" / "ocr_llm_haiku" / "pages"))
    ap.add_argument("--manifest", default=str(ROOT / "data" / "manifest.csv"))
    ap.add_argument("--out", default=str(ROOT / "data" / "ocr_llm_haiku.jsonl"))
    ap.add_argument("--engine", default="claude-haiku (vision, 200dpi, trang cắt đôi)")
    ap.add_argument("--skip-validation", metavar="LÝ DO", default=None,
                    help="bỏ qua cổng kiểm lô (validate_batch.py); bắt buộc nêu lý do, được ghi log")
    args = ap.parse_args()

    refused = check_batch_validated(args.pages_dir)
    if refused:
        if not args.skip_validation or not args.skip_validation.strip():
            print(f"TỪ CHỐI ghép lô {args.pages_dir}: {refused}", file=sys.stderr)
            print('  (bỏ qua có ghi log: --skip-validation "lý do")', file=sys.stderr)
            return 2
        log = log_skip(args.pages_dir, args.skip_validation.strip(), refused)
        print(f"CẢNH BÁO: bỏ qua cổng kiểm lô ({refused}). Lý do: {args.skip_validation.strip()}. Đã ghi log {log}", file=sys.stderr)

    m = pd.read_csv(args.manifest, encoding="utf-8-sig", dtype=str).fillna("")
    m["page_count"] = m["page_count"].astype(int)
    m["key"] = m.apply(lambda r: r["exact_dup_group"] or r["doc_id"], axis=1)
    rep = m.sort_values("relative_path").drop_duplicates("key").set_index("key")["doc_id"].to_dict()

    by_doc = {}
    for p in sorted(Path(args.pages_dir).glob("*.txt")):
        mm = _PAGE.match(p.name)
        if mm:
            by_doc.setdefault(mm["doc"], {})[int(mm["page"])] = p.read_text(encoding="utf-8")

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    n_docs = n_pages = 0
    missing = []
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        for r in m.sort_values("relative_path").itertuples():
            src = by_doc.get(rep[r.key], {})
            if not src:
                missing.append(r.relative_path)
                continue
            pages = []
            for pg in sorted(src):
                raw = src[pg]
                pages.append({
                    "page": pg, "source": "llm_vision", "engine": args.engine, "dpi": 200,
                    "text": strip_markers(raw), "text_raw": raw, "n_chars": len(strip_markers(raw)),
                    "n_uncertain": raw.count("[?]"), "rotated": "[trang xoay]" in raw,
                    "mean_conf": None, "seconds": None, "error": None,
                })
            f.write(json.dumps({
                "doc_id": r.doc_id, "relative_path": r.relative_path, "file_name": r.file_name,
                "folder_label": r.folder_label or None, "page_count": r.page_count,
                "pages_processed": len(pages), "pages_truncated": len(pages) < r.page_count,
                "transcript_of": rep[r.key], "pages": pages, "ocr_engine": args.engine, "created_at": now,
            }, ensure_ascii=False) + "\n")
            n_docs += 1
            n_pages += len(pages)
    print(f"Đã ghi {args.out}: {n_docs} tài liệu, {n_pages} trang")
    if missing:
        print(f"THIẾU bản chép cho {len(missing)} tài liệu:")
        for x in missing:
            print("  -", x)
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
