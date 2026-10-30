# models/ - Mô hình tách trang đã huấn luyện (Nhóm 2)

| Tệp | Nội dung |
|---|---|
| `pair_gb_v0.joblib` | `PairBoundaryModel` (`src/splitting/learned.py`): mô hình loại trang (TF-IDF từ 1-2 + hồi quy logistic) + bộ phân loại cặp trang (HistGradientBoosting nhỏ, 30 đặc trưng) |
| `pair_gb_v0.json` | Mô tả: sha256 của tệp `.joblib`, sha nhãn / đáp án / chia dữ liệu / OCR dùng để huấn luyện, sha danh sách `doc_id` huấn luyện, seed và cấu hình sinh composite tổng hợp, phiên bản scikit-learn / numpy, tên 30 đặc trưng, ngưỡng |

## Tạo lại

```powershell
# từ gốc repo, ~vài phút (CPU)
.venv\Scripts\python.exe -X utf8 teams/team2_splitting/experiments/04_pair_classifier/save_model.py
```

Huấn luyện trên **toàn bộ phạm vi dev** (DEV + EXCLUDED_COMPOSITE, KHÔNG có tài liệu TEST) và 400 composite tổng hợp (seed 99) từ tài liệu đơn DEV. Vì mô hình này đã thấy mọi tài liệu dev nên **không có số đo trên dev cho chính nó**; số đo trung thực là cross-fitting theo nhóm ở [`../experiments/04_pair_classifier/RESULTS.md`](../experiments/04_pair_classifier/RESULTS.md) (mô hình mỗi fold cùng cấu hình) và một lần chấm với tài liệu TEST (`RESULTS_all_incl_test_docs.md`).

## Dùng

```python
from src.splitting.boundary_detector import split_document
result = split_document(ocr_doc, method="model")     # nạp models/pair_gb_v0.joblib, kiểm sha256; thiếu tệp -> FileNotFoundError (không âm thầm quay về luật)
```

`boundary_confidence` của lát cắt = **điểm thô** của bộ phân loại tại trang mở lát cắt (chưa hiệu chỉnh xác suất trên miền thật; lát cắt đầu luôn 1.0 vì trang 1 là trang đầu theo định nghĩa). Đừng dùng nó như xác suất đúng.

## An toàn

`.joblib` là pickle: chỉ nạp tệp do chính repo này sinh. `load_model` so sha256 với `.json` cạnh nó và từ chối nếu lệch (chống tệp bị thay), nhưng sha nằm cùng thư mục nên không chống được kẻ sửa cả hai. Mô hình học từ văn bản OCR của tài liệu thật (có thể chứa thông tin cá nhân trong từ vựng TF-IDF): coi tệp `.joblib` như dữ liệu nội bộ, không công bố ra ngoài.
