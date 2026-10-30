#!/usr/bin/env python
import sys, os
# Ensure the project root (parent directory) is in sys.path for src imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
"""
run_pipeline_with_haiku_txt.py

Pipeline sử dụng các file *.txt* được tạo bởi Claude Haiku (thư mục
teams/team1_ocr/gold/silver_llm/haiku/). Thay vì khởi tạo VietOCREngine,
script này đọc nội dung txt, tạo OCRDocumentResult và truyền vào
DocumentPipeline.
"""

import argparse
import re
from pathlib import Path
from typing import List

from src.pipeline import DocumentPipeline
from src.common.contracts import OCRDocumentResult, OCRPageResult

# ----------------------------------------------------------------------
# 1️⃣ Hàm đọc txt đã OCR (Haiku)
# ----------------------------------------------------------------------
def load_haiku_txt(pdf_path: Path) -> OCRDocumentResult:
    """Đọc các file P###.txt trong
    teams/team1_ocr/gold/silver_llm/haiku/ và trả về OCRDocumentResult.
    Giả sử số trang của PDF = số file txt tương ứng.
    """
    txt_dir = Path("teams") / "team1_ocr" / "gold" / "silver_llm" / "haiku"

    txt_files = sorted(txt_dir.glob("P*.txt"))
    if not txt_files:
        raise FileNotFoundError(f"Không tìm thấy file txt OCR trong {txt_dir}")

    pages: List[OCRPageResult] = []
    for txt_file in txt_files:
        m = re.search(r"P(\d{3})\.txt$", txt_file.name, re.I)
        if not m:
            continue
        page_no = int(m.group(1))
        text = txt_file.read_text(encoding="utf-8")
        page = OCRPageResult(
            page_number=page_no,
            width=0,
            height=0,
            full_text=text,
            boxes=[],
            has_header_seal=False,
            has_signature_box=False,
            ocr_engine="haiku_txt",
            source="txt",
            error=None,
            mean_conf=None,
            flags=[],
        )
        pages.append(page)

    return OCRDocumentResult(
        file_name=pdf_path.name,
        total_pages=len(pages),
        pages=pages,
        error=None,
        processing_time_ms=0,
    )

# ----------------------------------------------------------------------
# 2️⃣ Main – chạy pipeline
# ----------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(
        description="Run the document pipeline using pre‑computed Haiku OCR txt files"
    )
    ap.add_argument(
        "pdf",
        type=Path,
        help="Đường dẫn tới PDF cần xử lý (các file txt phải đã tồn tại)"
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("output/pipeline"),
        help="Thư mục lưu JSON kết quả (mặc định ./output/pipeline)"
    )
    args = ap.parse_args()

    # Bật LLM tầng 3 dùng Kev server (đang chạy tại http://127.0.0.1:8009)
    pipeline = DocumentPipeline(ocr=load_haiku_txt, use_llm=True, llm_backend="kev", run_extraction=False)

    result = pipeline.run(args.pdf)

    out_file = args.out / f"{args.pdf.stem}.pipeline.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(result.model_dump_json(indent=1), encoding="utf-8")

    # In tóm tắt ngắn gọn
    print(pipeline.summarize(result))
    print(f"[*] Đã ghi {out_file}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
