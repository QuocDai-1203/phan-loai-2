# gold/ - Đáp án ranh giới mức trang (Nhóm 2)

## Cảnh báo quan trọng

`boundary_gold_v0.csv` là phiên bản **máy**: ranh giới suy ra từ cột `segments` của `data/labels_v2.csv`, mà `segments` do **một annotator AI (annotator A) đã xem đủ trang** gán. Annotator B chỉ thấy 2 trang đầu nên **không xác nhận được** ranh giới. **Chưa có người của công ty hoặc người kiểm nào xem lại.** Vì vậy:

- mọi con số tính trên `v0` là "đo theo nhãn tạm", không phải "đúng với thực tế";
- **không tạo `boundary_gold_v1.csv`** cho tới khi có người xem đủ trang 21 tệp composite (176 trang) và lật nhanh các tệp "không composite" nhiều trang để bắt tệp ghép bị bỏ sót (việc này cần người, xem T1 bước 3 trong [`../README.md`](../README.md));
- 5 tệp `check_composite` (nhãn ghi `review_status = check_composite`, annotator A tự đánh dấu chưa chắc) là nơi rủi ro nhãn cao nhất:
  `36aff038b19e` (hóa đơn, cùng loại), `72449aceeff3` (chứng chỉ nghiệp vụ BVMT, cùng loại), `9f4c4dae0c73`, `87c88bf6d0f1`, `57374da27cae` (ba tệp composite khác loại).
- trong 191 tệp "không composite" có thể còn tệp ghép bị bỏ sót (chưa ai kiểm).

## Tái lập bằng một lệnh

```powershell
# từ gốc repo
.venv\Scripts\python.exe -X utf8 teams/team2_splitting/gold/build_boundary_gold.py
```

Kết quả phải in `1113 809 145` (trang / vị trí "giữa hai trang liên tiếp" / ranh giới thật) rồi bảng theo nhóm; script cảnh báo ra stderr nếu nhãn đã đổi làm số lệch. Script chỉ đọc `data/labels_v2.csv`, `data/manifest.csv`, `data/splits/splits.csv`, `data/ocr_v2.jsonl` (để đánh dấu trang có văn bản), không ghi vào `data/`.

Ghi ra: `boundary_gold_v0.csv` (UTF-8 có BOM) và `boundary_gold_v0.meta.json` (sha nhãn, sha manifest, số đếm từng nhóm, danh sách 5 tệp `check_composite`).

## Cột của `boundary_gold_v0.csv` (một dòng = một trang của một tài liệu duy nhất)

| Cột | Ý nghĩa |
|---|---|
| `doc_id` | Mã tệp (tài liệu duy nhất; bản sao byte-giống-hệt đã gộp, lấy dòng `is_duplicate_of` rỗng) |
| `page` | Số trang, **đếm từ 1** (`gold_pages_todo.csv` của nhóm 1 đếm từ 0, đừng lẫn) |
| `is_start` | 1 nếu trang đầu một segment (tài liệu). **Chỉ chấm trên trang >= 2** (trang 1 luôn là trang đầu) |
| `segment_idx` | Số thứ tự segment trong tệp (từ 0) |
| `page_doc_type` | Loại của segment chứa trang (id taxonomy v2) |
| `n_pages` | Số trang thật của PDF (`manifest.page_count`) |
| `kind` | `mixed` (composite khác loại), `same_type` (composite cùng loại), `single` (không composite) |
| `eval_group` | Nhóm báo cáo: `mixed` (8 tệp), `same_other` (6 tệp cùng loại ngoài `BB_LAY_MAU`), `same_bb` (7 tệp `BB_LAY_MAU`), `negative` (191 tệp nhiều trang không composite), `single_page` (92 tệp 1 trang, không có vị trí nào để chấm) |
| `split` | `DEV`, `TEST` hoặc `EXCLUDED_COMPOSITE` theo `data/splits/splits.csv` (chia đã khóa) |
| `template_group` | Nhóm biểu mẫu (manifest); `doc_id` nếu không có nhóm |
| `review_status` | `agreed`, `check_low_conf`, hoặc `check_composite` (từ `labels_v2.csv`) |
| `ocr_available` | 1 nếu `data/ocr_v2.jsonl` có văn bản của trang này (văn bản chỉ tới trang 30/tài liệu), 0 nếu không |

## Số đếm (tính lại bởi script)

| Nhóm (`eval_group`) | Tệp | Trang | Vị trí (trang >= 2) | Ranh giới thật |
|---|---|---|---|---|
| `mixed` | 8 | 34 | 26 | 20 |
| `same_other` | 6 | 17 | 11 | 7 |
| `same_bb` | 7 | 125 | 118 | 118 |
| `negative` | 191 | 845 | 654 | 0 |
| `single_page` | 92 | 92 | 0 | 0 |
| **Tổng** | **304** | **1113** | **809** | **145** |

Chỉ 27 ranh giới thật nằm ngoài `BB_LAY_MAU`; 118/145 thuộc 7 tệp mà mọi trang là một biên bản. **Không được chỉ báo F1 gộp.**

Trong phạm vi `dev` (DEV + EXCLUDED_COMPOSITE, không có TEST) mà các thí nghiệm dùng để chỉnh: 8 / 6 / 5 / 155 tệp. Hai tệp `BB_LAY_MAU` còn lại (`d51eeba77210`, `7888ea753973`; 9 ranh giới) và 36 tệp âm thuộc TEST, chỉ được mở một lần với cờ `--final-test` (xem README của từng thí nghiệm). Lưu ý tệp `BB_LAY_MAU` 93 trang chỉ có văn bản tới trang 30, nên trong phép chấm nó đóng góp 29 vị trí chứ không phải 92.

## Composite tổng hợp (`make_synthetic.py`)

`synthetic_v0.csv` (seed 20261012, 400 composite) do `make_synthetic.py` sinh từ tài liệu đơn `DEV`, **chỉ để huấn luyện / chỉnh** phương pháp có học. Quy tắc chống rò rỉ và hạn chế (miền tổng hợp dễ hơn thật; kho không có tài liệu đơn `CHUNG_THU_CHAT_LUONG`) ghi ở đầu script. Lệnh: `.venv\Scripts\python.exe -X utf8 teams/team2_splitting/gold/make_synthetic.py`.
