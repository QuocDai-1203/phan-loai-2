# 03 - Quy trình đánh giá (văn bản quy chuẩn)

Áp dụng cho **mọi thí nghiệm phân loại** (Nhóm 3 và các nhóm khác khi chấm loại tài liệu). Mục tiêu: mọi con số trong báo cáo
tái lập được bằng **một lệnh** và được chứng minh bằng phép đo, không phải cảm tính. Từ khóa **PHẢI / KHÔNG ĐƯỢC / NÊN** hiểu theo nghĩa
quy chuẩn (bắt buộc / cấm / khuyến nghị).

Mã nguồn tham chiếu: `teams/00_data_and_eval/eval/` (`harness.py`, `eval_metrics.py`, `eval_splits.py`), kiểm thử ở
`teams/00_data_and_eval/tests/test_harness.py`. Thí nghiệm mẫu: `teams/team3_classification/experiments/01_classical_baselines/`.

## 1. Đơn vị đánh giá

1. Đơn vị là **tài liệu duy nhất** (unique document), không phải file. Các file byte-giống-hệt (`exact_dup_group` trong
   `data/manifest.csv`) gộp thành một; chọn đại diện là dòng có `is_duplicate_of` rỗng trong `data/labels_v2.csv` (nếu không có cột đó: `doc_id` nhỏ nhất).
2. Các bản sao **PHẢI** mang cùng nhãn; harness kiểm tra và báo mọi xung đột (hiện tại: 0). Bản sao luôn nằm cùng split với đại diện.
3. File là **composite hỗn hợp** (cột `composite_mixed == "1"` trong `labels_v2.csv`, gồm nhiều loại tài liệu khác nhau trong một PDF) **bị loại**
   khỏi benchmark một nhãn; danh sách ở `data/splits/excluded_composites.csv` để nhóm tách trang (Nhóm 2) dùng. File composite đồng loại
   (`is_composite=1` nhưng `composite_mixed=0`) vẫn ở lại.
4. Nhãn chuẩn là `labels_v2.csv` (cột `doc_type`). Mọi script **PHẢI** nhận tham số `--labels` và **KHÔNG ĐƯỢC** gắn cứng điều gì phụ thuộc vào nhãn.
   Cột `folder_label` trong manifest là nhãn thư mục cũ, không đáng tin, **không dùng làm đáp án**.

## 2. Hai track nhãn

| Track | Không gian nhãn | Dùng cho |
|---|---|---|
| **S** (supervised, tập đóng) | Mỗi loại có >= `--min-docs` (mặc định 10) tài liệu duy nhất là một lớp; **mọi loại còn lại gộp thành `RARE_OR_OTHER`** | Mô hình cần dữ liệu huấn luyện |
| **Z** (zero-shot, toàn taxonomy) | Cả 34 loại (+ `OTHER`, `UNREADABLE`) | Phương pháp không cần dữ liệu huấn luyện (cổng luật, LLM...) |

- Lý do hai track: chỉ ~10 loại đủ dữ liệu để học; ~24 loại hiếm (1-9 tài liệu) không thể đánh giá bằng huấn luyện. Hệ thống phải học cách **chuyển
  tài liệu lạ cho người** (`RARE_OR_OTHER`) thay vì ép vào loại sai.
- Track S **PHẢI** báo cáo số loại và số tài liệu nằm trong lớp gộp.
- Track Z báo: accuracy, macro-F1 **chỉ trên các loại có >= 3 tài liệu** (nêu số loại được chấm), `coverage` (tỉ lệ không abstain) và accuracy-on-covered.
  Abstain (`UNKNOWN`) tính là sai trong accuracy/macro-F1.

## 3. Chia dữ liệu

1. `group` = `template_group` nếu có, ngược lại = `doc_id`. Tài liệu cùng biểu mẫu (khác khách hàng/ngày) **không bao giờ** nằm ở hai phía train/test.
2. Bước 1: `StratifiedGroupKFold(5)` lấy một fold (~20%) làm **TEST khóa**; ~80% còn lại là **DEV**. Phân tầng theo loại đầy đủ (`doc_type`).
3. Bước 2: DEV chia 5 fold `StratifiedGroupKFold`, lặp với **3 seed** (cột `fold`, `fold_s1`, `fold_s2`). Mọi chọn mô hình, chọn đặc trưng,
   chỉnh ngưỡng **chỉ** dùng CV trên DEV (dự đoán out-of-fold).
4. Tất định: seed chia TEST = 42 (hằng số `SPLIT_SEED`), seed fold = 42000 + {0,1,2}. Sinh lại bằng
   `write_splits(load_benchmark(<labels>))` (cũng được `run_all.py` gọi). File ở `data/splits/` (xem `data/splits/README.md`):
   `splits.csv` (chính), `splits_strict.csv`, `excluded_composites.csv`, `splits_meta.json` (ghi sha nhãn).
5. **Nhóm quá lớn.** Một biểu mẫu có thể chiếm gần hết một lớp (ví dụ một mẫu = 23/24 chứng chỉ tập huấn). Chia nghiêm ngặt sẽ đẩy cả lớp
   sang một phía. Quy ước chính thức: nhóm > 5 tài liệu được cắt tất định thành các nhóm con <= 5 (`max_group_size=5`); đổi lại có rò rỉ
   biểu mẫu nhẹ giữa nhóm con. Biến thể nghiêm ngặt (`splits_strict.csv`) vẫn được xuất và so sánh trong báo cáo; **báo cáo phải nêu rõ dùng biến thể nào**.
6. Chia ngây thơ (ngẫu nhiên theo file, bỏ qua nhóm và bản sao) **chỉ** được dùng để minh họa mức phồng điểm do rò rỉ, tuyệt đối không dùng để chọn hay báo cáo mô hình.
7. `data/splits/` là tập chia **đã khóa** (sửa ngày 2026-10-11, thay quy tắc cũ "nhãn đổi thì phải sinh lại"): các tệp chia không chứa nhãn, nên khi nhãn được sửa thì tài liệu giữ nguyên DEV/TEST/fold và `load_or_make_splits` chỉ cảnh báo rằng sha nhãn khác `labels_sha1_10`. Kết quả tính trên nhãn cũ vẫn hết hiệu lực để so sánh (bảng kết quả ghi `labels_sha` từng dòng); chấm lại TEST trên nhãn đã sửa phải ghi lý do (`--allow-rescore`). Harness dừng với `SplitsOutOfDateError` khi benchmark có tài liệu chưa được gán tập; chia lại là việc có chủ ý (`rebuild=True`) và khi đó TEST cũ coi như đã bị nhìn thấy.

## 4. Quy tắc truy cập TEST

- TEST chỉ được mở bằng lệnh **riêng, tường minh** (`run_all.py --final-test`, hoặc `load_documents(..., "TEST", final_test=True)`); mặc định hàm tải dữ liệu ném `PermissionError`.
- Mỗi **cấu hình cuối** được chấm TEST **một lần**. Cấu hình cuối được chốt trước, chỉ dựa trên DEV, và ghi vào `dev_selection.json` (kèm sha nhãn).
  `--final-test` từ chối chạy nếu nhãn đã đổi hoặc TEST đã chấm cho bộ nhãn đó (trừ khi có `--allow-rescore`, và phải nêu lý do trong báo cáo).
- KHÔNG ĐƯỢC: chỉnh siêu tham số, ngưỡng, đặc trưng, prompt hay luật sau khi đã nhìn điểm TEST; chọn "mô hình tốt nhất" bằng điểm TEST;
  đọc lỗi TEST để sửa luật/prompt. Nếu muốn cải tiến sau khi nhìn TEST: coi TEST đã "cháy", tạo vòng dữ liệu mới.
- Huấn luyện lại mô hình cuối trên **toàn bộ DEV** rồi mới chấm TEST.

## 5. Chỉ số bắt buộc (mỗi lần chạy)

- Accuracy, **macro-F1**, weighted-F1; precision / recall / F1 / support từng lớp; ma trận nhầm lẫn (CSV); các nhầm lẫn lớn nhất.
- Macro-F1 = trung bình F1 trên các lớp có support >= ngưỡng trong nhãn **thật** của tập đang chấm (Track S: 1; Track Z: 3). Nhãn dự đoán ngoài không gian nhãn
  (vd. `UNKNOWN`) luôn tính là sai.
- Mô hình có xác suất: **ECE** (10 bin đều, theo xác suất lớp dự đoán) và **Brier** đa lớp.
- **Độ trễ** mỗi tài liệu (median và p95; trích đặc trưng + suy luận; 1 luồng; batch = 1; **không gồm OCR**; phương pháp ảnh gồm cả bước render) và **kích thước mô hình trên đĩa**.
- Phương pháp gọi dịch vụ ngoài (LLM...) ghi thêm chi phí/độ trễ gọi và nêu rõ **có chạy được on-premise hay không**.

## 6. Độ bất định và so sánh

- **DEV:** trung bình ± độ lệch chuẩn qua các fold, qua cả 3 seed gán fold (3 x 5 = 15 điểm). Số này hơi lạc quan khi cấu hình được chọn trong chính DEV; điều đó phải được nêu.
- **TEST:** khoảng tin cậy 95% **percentile bootstrap, 2000 lần lấy mẫu lại theo tài liệu** (`BOOT_N`, `BOOT_SEED` cố định).
- So sánh hai mô hình trên TEST dùng **bootstrap ghép cặp** (cùng mẫu lại cho cả hai): báo hiệu số, CI 95%, p-value hai phía. Khi CI của hiệu chứa 0, **phải viết rõ "không tách được hai phương pháp"**;
  không được tuyên bố hơn kém chỉ vì điểm chấm lệch nhau.
- Với TEST chỉ ~60 tài liệu và nhiều lớp chỉ 2-7 mẫu, CI rộng là bình thường; đừng che nó.

## 7. Dự đoán có chọn lọc (KPI nghiệp vụ)

- Với mô hình có xác suất: vẽ **risk-coverage** từ dự đoán out-of-fold trên DEV. Dự đoán `RARE_OR_OTHER` **không bao giờ** được tự nhận (luôn đưa cho người).
- **Auto-file rate** = tỉ lệ tài liệu (trên mọi tài liệu) có thể tự nhận mà tỉ lệ sai trên phần được nhận <= 1% (và <= 2%). **Ngưỡng chọn trên DEV**, sau đó áp nguyên ngưỡng lên TEST và báo coverage + tỉ lệ sai kèm CI bootstrap.
- Trần lý thuyết của auto-file rate = tỉ lệ tài liệu thuộc các loại Track S (không gộp); luôn in kèm.

## 8. Phân tích lỗi

Với mô hình tốt nhất: xuất CSV mọi tài liệu sai (TEST và DEV out-of-fold) gồm `doc_id`, tên file, nhãn thật, nhãn dự đoán, confidence, 150 ký tự đầu của văn bản
**đã che chữ số**; tóm tắt theo loại, bản quét/số hóa, độ dài văn bản, có biểu mẫu chung hay không. Không đưa định danh cá nhân vào báo cáo `.md`
(CSV lỗi có tên file nên **không** commit ra ngoài repo nội bộ).

## 9. Bảng kết quả dùng chung

File: `teams/team3_classification/results/results_table.csv` (chỉ **thêm dòng**, không sửa dòng cũ). Cột:
`run_id` (thời gian UTC + 6 hex ngẫu nhiên, không phụ thuộc git), `timestamp`, `method`, `track` (S|Z), `text_source`, `split` (`DEV_CV` = trung bình CV, `DEV_ALL`,
`TEST`), `n`, `accuracy` (+`_ci_lo/_ci_hi`), `macro_f1` (+`_ci_lo/_ci_hi`, `macro_f1_std`), `coverage`, `acc_on_covered`, `latency_ms_median/p95`, `labels_file`, `labels_sha`, `notes`.

```python
import sys; sys.path.insert(0, "teams/00_data_and_eval/eval")
from harness import *
bench  = load_benchmark("data/labels_v2.csv")
splits = load_or_make_splits(bench)
dev    = load_documents(bench, splits, "haiku_p12", "DEV")
cv     = cross_validate(lambda: MyPredictor(), dev, bench.s_classes, track="S", seed=0)   # Predictor.fit/predict
append_result_row(dict(run_id=new_run_id(), method="my_method", track="S", text_source="haiku_p12", split="DEV_CV",
                       n=len(dev), accuracy=..., macro_f1=..., labels_file="labels_v2.csv", labels_sha=bench.labels_sha, notes="..."))
```

`text_source` hiện có: `legacy_p1`, `haiku_p1`, `haiku_p12`, `ocr_v2_p1`, `ocr_v2_p12` (khi `data/ocr_v2.jsonl` có), cộng `image_p1` cho phương pháp ảnh.

## 10. Khi báo cáo

- Nêu **nhãn nào** (file + sha), **nguồn văn bản nào**, **biến thể split nào**.
- Phân biệt rõ điều đã đo và điều suy luận. Số trên nhãn tạm thời ghi "tạm thời".
- Nhãn hiện là do hai lượt gán nhãn độc lập của **các mô hình cùng họ theo cùng một hướng dẫn** và chưa được nhân viên công ty kiểm chứng; lỗi hệ thống chung vẫn có thể tồn tại,
  và độ đồng thuận tuyệt đối (kappa = 1.0 trên doc_type) không chứng minh nhãn đúng.
- Điều kiện "OCR gần hoàn hảo" (LLM-vision) **không có sẵn on-premise**: kết quả trên nguồn đó là cận trên, không phải con số triển khai.
