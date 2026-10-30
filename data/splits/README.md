# data/splits - chia DEV / TEST có nhóm

Sinh bởi `teams/00_data_and_eval/eval/harness.py::write_splits`, **tất định**. Đây là tập chia **đã khóa**: các tệp ở đây không
chứa nhãn, nên khi nhãn được sửa thì tài liệu vẫn ở nguyên DEV/TEST (harness chỉ cảnh báo rằng sha nhãn đã khác
`labels_sha1_10` trong `splits_meta.json`). Harness chỉ từ chối chạy (`SplitsOutOfDateError`) khi có tài liệu của benchmark chưa được
gán tập, ví dụ thêm tài liệu mới. Chia lại là việc có chủ ý (`load_or_make_splits(bench, rebuild=True)`, hoặc cờ `--rebuild-splits`
của `01_classical_baselines/run_all.py`): TEST sẽ đổi, mọi số TEST đã báo cáo phải chấm lại và TEST cũ coi như đã bị nhìn thấy. Quy tắc đầy đủ: `teams/00_data_and_eval/reports/03_evaluation_protocol.md`.

## Các file

| File | Nội dung |
|---|---|
| `splits.csv` | **Chia chính thức** (nhóm lớn bị cắt <= 5 tài liệu, xem dưới). Một dòng cho MỖI file PDF của manifest |
| `splits_strict.csv` | Biến thể nghiêm ngặt: không cắt nhóm (mỗi `template_group` nguyên khối). Dùng để đo "tổng quát hóa sang biểu mẫu mới" |
| `excluded_composites.csv` | File gồm nhiều loại tài liệu khác nhau (`composite_mixed=1`): bị loại khỏi benchmark một nhãn, dành cho Nhóm 2 (tách trang) |
| `splits_meta.json` | Nhãn dùng, sha, `min_docs`, số tài liệu DEV/TEST, thời điểm sinh |

## Cột của `splits*.csv`

| Cột | Ý nghĩa |
|---|---|
| `doc_id` | Mã file (như `data/manifest.csv`) |
| `split` | `DEV`, `TEST` hoặc `EXCLUDED_COMPOSITE` |
| `fold` | Fold DEV (0-4) theo seed 0; `-1` với TEST / composite |
| `fold_s1`, `fold_s2` | Như `fold` nhưng với seed gán fold thứ 2 và 3 (dùng để báo trung bình ± std qua 3 seed) |
| `group` | Nhóm chia: `template_group` nếu có, ngược lại `doc_id`; nhóm lớn có hậu tố `.k` trong `splits.csv` |
| `rep_doc_id` | Đại diện của nhóm bản sao byte-giống-hệt (file nào cũng cùng split với đại diện) |
| `is_rep` | 1 nếu chính file này là đại diện. **Đơn vị đánh giá = các dòng `is_rep == 1`** |

## Cách chia

1. Đơn vị = tài liệu duy nhất (gộp bản sao). Composite hỗn hợp bị loại.
2. `StratifiedGroupKFold(5, shuffle, seed=42)` theo `doc_type`, group như trên -> fold 0 là **TEST khóa** (~20%), còn lại **DEV** (~80%).
3. DEV chia tiếp `StratifiedGroupKFold(5)` với 3 seed (42000, 42001, 42002) -> `fold`, `fold_s1`, `fold_s2`.
4. Cắt nhóm lớn: một biểu mẫu có thể chiếm ~95% một lớp (vd. chứng chỉ tập huấn VCHNH), chia nguyên khối sẽ đẩy cả lớp vào một phía.
   `splits.csv` chia nhóm lớn thành các nhóm con <= 5 tài liệu bằng thứ tự băm `sha1(doc_id)`; nên tài liệu cùng biểu mẫu vẫn có thể
   nằm ở hai phía (rò rỉ biểu mẫu nhẹ). `splits_strict.csv` không làm vậy. Mức chênh điểm giữa hai biến thể nằm trong
   `teams/team3_classification/experiments/01_classical_baselines/RESULTS.md`.

## Dùng

```python
import sys; sys.path.insert(0, "teams/00_data_and_eval/eval")
from harness import *
bench  = load_benchmark("data/labels_v2.csv")
splits = load_or_make_splits(bench)                      # đọc tập chia đã khóa; chỉ sinh mới khi chưa có
dev    = load_documents(bench, splits, "haiku_p12", "DEV")
test   = load_documents(bench, splits, "haiku_p12", "TEST", final_test=True)   # chỉ trong lệnh chấm cuối
```

**Không** sửa tay các file này. **Không** dùng `TEST` để chọn mô hình/ngưỡng/prompt.
