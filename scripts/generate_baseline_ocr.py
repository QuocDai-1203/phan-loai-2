"""generate_baseline_ocr.py - Công cụ sinh tập dữ liệu OCR Text Baseline cho Nhóm 3.

Mục đích:
- Giải phóng Nhóm 3 khỏi sự phụ thuộc vào Nhóm 1.
- Tự động duyệt qua 335 tệp PDF trong `docs/_chot_samples_phanloaitailieu/`.
- Quét OCR trang đầu tiên (hoặc các trang) bằng RapidOCR / PyMuPDF.
- Xuất ra tệp dữ liệu chuẩn hóa `data/baseline_ocr_335.jsonl` kèm nhãn Ground Truth 19 danh mục.
- Nhóm 3 có thể nạp ngay file này để train/eval mô hình Kev-4B hoặc Jev mà không cần đợi Nhóm 1.
"""

import os
import sys
import json
import time
from pathlib import Path

# Đảm bảo in tiếng Việt chuẩn trên Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import fitz  # PyMuPDF
import numpy as np

try:
    from rapidocr_onnxruntime import RapidOCR
    _ocr_engine = RapidOCR()
except Exception as e:
    print(f"Cảnh báo: Không thể khởi tạo RapidOCR ({e})")
    _ocr_engine = None


def extract_page_text(doc: fitz.Document, page_num: int = 0) -> str:
    """Trích xuất text từ trang PDF: ưu tiên text layer, fallback sang RapidOCR."""
    if page_num >= len(doc):
        return ""
    
    page = doc[page_num]
    digital_text = page.get_text("text").strip()
    
    # Nếu có lớp chữ số (Digital Text) dài hơn 50 ký tự
    if len(digital_text) >= 50:
        return digital_text
    
    # Nếu là bản scan ảnh -> Chạy RapidOCR
    if _ocr_engine is None:
        return ""
    
    pix = page.get_pixmap(dpi=150)
    img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
    res, _ = _ocr_engine(img_np)
    
    if not res:
        return ""
    
    lines = [item[1] for item in res if item and len(item) > 1]
    return "\n".join(lines).strip()


def build_baseline_dataset(
    input_dir: str = r"Z:\projects\sdh-phanloaitailieu\docs\_chot_samples_phanloaitailieu",
    output_file: str = r"Z:\projects\sdh-phanloaitailieu\data\baseline_ocr_335.jsonl",
    max_pages_per_doc: int = 1,
):
    """Quét toàn bộ thư mục 19 danh mục và xuất ra tệp JSONL."""
    input_path = Path(input_dir)
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"[*] Bắt đầu quét dữ liệu từ: {input_path}")
    print(f"[*] Tệp đầu ra: {output_path}")
    
    categories = [d for d in os.listdir(input_path) if (input_path / d).is_dir()]
    print(f"[*] Tìm thấy {len(categories)} danh mục thư mục.")
    
    total_processed = 0
    start_time = time.time()
    
    with open(output_path, "w", encoding="utf-8") as f_out:
        for cat in sorted(categories):
            cat_dir = input_path / cat
            pdf_files = [f for f in os.listdir(cat_dir) if f.lower().endswith(".pdf")]
            print(f"\n---> Danh mục [{cat}] ({len(pdf_files)} tệp)...")
            
            for file_name in pdf_files:
                file_path = cat_dir / file_name
                try:
                    doc = fitz.open(file_path)
                    page_texts = []
                    pages_to_read = min(len(doc), max_pages_per_doc)
                    
                    total_pages_in_doc = len(doc)
                    for p_idx in range(pages_to_read):
                        t = extract_page_text(doc, p_idx)
                        if t:
                            page_texts.append(t)
                    
                    doc.close()
                    full_text = "\n\n--- HẾT TRANG ---\n\n".join(page_texts).strip()
                    
                    record = {
                        "file_name": file_name,
                        "relative_path": f"{cat}/{file_name}",
                        "category_label": cat,
                        "page_count": total_pages_in_doc,
                        "text_length": len(full_text),
                        "ocr_text": full_text,
                    }
                    
                    f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
                    f_out.flush()
                    total_processed += 1
                    print(f"  [+] Đã OCR: {file_name} ({len(full_text)} ký tự)")
                    
                except Exception as err:
                    print(f"  [-] Lỗi tệp {file_name}: {err}")
    
    elapsed = time.time() - start_time
    print(f"\n=======================================================")
    print(f"[V] Hoàn tất! Đã trích xuất {total_processed} tệp trong {elapsed:.1f} giây.")
    print(f"[V] Tệp dữ liệu sẵn sàng cho Nhóm 3: {output_path}")
    print(f"=======================================================")


if __name__ == "__main__":
    # Script cũ (trang 1, RapidOCR mất dấu) - đã được thay bằng scripts/build_ocr_dataset.py -> data/ocr_v2.jsonl.
    # Chỉ giữ để tái lập baseline cũ; phải truyền --force vì nó GHI ĐÈ data/baseline_ocr_335.jsonl.
    if "--force" not in sys.argv[1:]:
        print("Script cũ, đã thay bằng scripts/build_ocr_dataset.py (data/ocr_v2.jsonl).")
        print("Chạy lại sẽ GHI ĐÈ data/baseline_ocr_335.jsonl. Nếu thật sự muốn: thêm --force.")
        sys.exit(2)
    build_baseline_dataset()
