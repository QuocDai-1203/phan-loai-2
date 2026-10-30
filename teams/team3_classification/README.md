# Nhóm 3 — Phân loại (nhận loại tài liệu và biết khi nào phải từ chối)

## Mục tiêu (doanh nghiệp nhận được gì)

Với mỗi tài liệu đã được tách khỏi tệp quét, hệ thống trả lời hai câu hỏi: **đây là loại gì** (một `id` trong [`data/taxonomy_v2.json`](../../data/taxonomy_v2.json)) và **có đủ chắc để tự xếp hồ sơ không**. Tài liệu đủ chắc được lưu thẳng vào đúng hồ sơ và chuyển cho khâu trích xuất; tài liệu không đủ chắc được đưa cho nhân viên kèm gợi ý. Giá trị cho công ty là số tài liệu **không cần người xem** ở một mức sai mà công ty chấp nhận, chứ không phải độ chính xác trung bình. Toàn bộ phải chạy tại chỗ (on-premise). Đầu vào `DocumentSlice`, đầu ra `ClassificationResult` (xem [`teams/README.md`](../README.md) mục 3).

Bốn thuật ngữ dùng suốt tài liệu này:

- **Track S / Track Z.** Hai cách chấm của [giao thức đánh giá](../00_data_and_eval/reports/03_evaluation_protocol.md). Track S (có huấn luyện): 10 loại có từ 10 tài liệu trở lên là 10 lớp, mọi loại còn lại gộp thành lớp `RARE_OR_OTHER` ("hãy đưa cho người"). Track Z (zero-shot, tức không dùng dữ liệu huấn luyện của mình): chấm trên toàn bộ taxonomy, kể cả loại hiếm.
- **Tự xếp hồ sơ (auto-file).** Tỉ lệ tài liệu, tính trên mọi tài liệu, mà hệ thống tự nhận trong khi tỉ lệ sai trên phần đã nhận không vượt mức đặt trước (1% hoặc 2%). Ngưỡng chọn trên DEV rồi áp nguyên lên TEST.
- **Cascade.** Chuỗi các tầng từ rẻ đến đắt; tầng đầu tiên đủ tự tin thì nhận tài liệu, không tầng nào nhận thì chuyển cho người (từ chối, tiếng Anh là abstain).
- **Cross-fit.** Cách ước lượng trung thực hơn trên DEV: chọn ngưỡng trên 4 fold, áp lên fold thứ 5, lặp cho cả 5 fold. Con số "chọn ngưỡng và chấm trên cùng DEV" luôn lạc quan hơn con số cross-fit.

## Hiện trạng

### Đã làm và đo được (ngày 2026-10-11)

Mọi số dưới đây dùng nhãn `data/labels_v2.csv` (sha1[:10] `eb3348713a`), chia chính thức `data/splits/splits.csv` (DEV 237 tài liệu, TEST khóa 59 tài liệu), và — trừ khi ghi khác — nguồn văn bản `ocr_v2_p12` (OCR cục bộ VietOCR, trang 1–2: điều kiện gần triển khai nhất). Khoảng trong ngoặc vuông là khoảng tin cậy 95%. "01" là [`experiments/01_classical_baselines/RESULTS.md`](experiments/01_classical_baselines/RESULTS.md), "02" là [`experiments/02_llm_and_cascade/RESULTS.md`](experiments/02_llm_and_cascade/RESULTS.md).

| Hạng mục | Kết quả | Nguồn |
|---|---|---|
| Baseline rẻ: TF-IDF (từ 1–2) + ComplementNB, Track S | DEV macro-F1 0,977 ± 0,019 (15 điểm = 3 seed × 5 fold). TEST macro-F1 **0,946 [0,847; 1,000]**, accuracy 0,949 [0,881; 1,000], n = 59. Không tách được khỏi văn bản Haiku (Δ = +0,028, khoảng [0,000; 0,109], p = 0,74) | 01 §0, §6 |
| Tự xếp hồ sơ chỉ bằng TF-IDF | Mức sai ≤ 1%: **61,0% [49,2; 72,9]**, 0 lỗi trong 36 tài liệu được nhận (cận trên 95% của tỉ lệ sai: 8,0%). Mức sai ≤ 2%: 78,0% [67,8; 88,1], 1 lỗi trong 46. Trần lý thuyết 81,4% vì loại hiếm luôn chuyển cho người | 01 §0, §9 |
| Cổng luật từ khóa tiêu đề, Track Z | Quyết định được 76,4% tài liệu DEV và 84,7% TEST; trên phần đã quyết định đúng 100% (cả DEV và TEST); trung vị 3 ms | 01 §10, §13 |
| Embedding `bge-m3` | Track S: DEV 0,955 ± 0,046 (không hơn TF-IDF). Few-shot toàn taxonomy (tâm lớp, cần ≥ 2 mẫu mỗi loại): macro-F1 DEV 0,894 [0,710; 0,937], TEST 0,913 [0,708; 0,978]; nhớ lại (recall) loại hiếm chỉ 0,67 DEV và 6/11 TEST | 02 §4 |
| **Qwen3.5-4B zero-shot** (Ollama; mô tả ngắn, 1 bước, 2000 ký tự đầu) | Accuracy DEV 0,996 (1 lỗi trên 237), TEST **0,983 [0,949; 1,000]**. Recall loại hiếm 62/63 DEV, 10/11 TEST. Lỗi cú pháp 0 (đầu ra bị ràng buộc bằng JSON schema) | 02 §5 |
| **Kev-0.8B zero-shot** | Chỉ đưa **tên loại**: accuracy DEV 0,962, TEST 0,932 [0,864; 0,983]. Mô tả ngắn: 0,781 (1 bước), 0,848 (2 bước). Mô tả **dài**: 0,300 và 0,397. Trên OCR cũ: 0,498 | 02 §5, §8 |
| **Đo lại Kev-0.8B trên máy chủ mới (2026-10-16)** | API đã đổi (`/api/status` 404, dùng `/v1/models`; đã sửa `kev_server_model`/`KevBackend`), mô hình và kết quả **không đổi**: chỉ-tên-loại accuracy DEV 0,962 [0,929; 0,980] (228/237), nhãn trùng 100% lần đo cũ. Kém Qwen3.5 (0,996) có ý nghĩa: hiệu -0,034, bootstrap cặp [-0,059; -0,013]. 9 lỗi, không tập trung theo biểu mẫu (7 cặp nhầm khác nhau; riêng `HO_SO_QUAN_LY_PCCC` 3/7 sai). ECE 0,441 hạ xuống 0,023 chỉ bằng làm sắc phân phối (cross-fit DEV), không cần tinh chỉnh. Từ khóa thêm vào tiêu chí làm tệ hơn (0,932); `permute` không đổi (0,962) | 06 |
| Qwen2.5-3B zero-shot | Accuracy DEV 0,764, TEST 0,797 [0,695; 0,898] | 02 §5 |
| Mô hình có biết khi nào nó không biết | Kev (tên loại): AUROC 0,961 nhưng ECE 0,441. Qwen3.5 một bước: AUROC 0,750 (chỉ có 1 lỗi để xếp hạng); hai bước: 0,978. Đồng thuận Kev + Qwen: nhận 227/237 DEV với 0 lỗi (cận trên 1,3%), 56/59 TEST với 1 lỗi (cận trên 8,2%) | 02 §6 |
| **Cascade** luật → TF-IDF → Qwen3.5-4B → người, mức sai ≤ 1% | DEV: tự nhận 236/237, 1 sai; cross-fit 98,3% với 0 sai. TEST: tự nhận **59/59** (Clopper–Pearson [0,939; 1,000]), **1 sai** (cận trên 95% của tỉ lệ sai: 7,8%). Sáu ứng viên tầng 3 cho 96,6–100% trên TEST với 0–1 sai. So với TF-IDF đơn (64,4% khi chỉnh ngưỡng trên nhãn Track Z): Δ = +0,356 [0,237; 0,475] | 02 §7 |
| Tầng nào quyết định bao nhiêu | TEST: luật 85%, TF-IDF 8%, LLM 7%, người 0%. DEV: 76%, 18%, 5%, 0% | 02 §7 |
| Bỏ từng tầng (ablation) | Chỉ luật: 76,4% DEV (0 sai), 84,7% TEST. Luật + TF-IDF: 95,4% DEV (2 sai), 96,6% TEST (1 sai). Bỏ luật: DEV cross-fit 97,9% (0 sai), TEST 98,3% (1 sai). Bỏ TF-IDF: 99,2% DEV (0 sai), 100% TEST (1 sai) | 02 §7 |
| Phụ thuộc chất lượng OCR | OCR cũ mất dấu (`legacy_p1`): Qwen3.5 còn 0,945 DEV / 0,915 TEST, Kev còn 0,498 / 0,458; cascade vẫn 96,6% TEST (0 sai) nhờ luật và TF-IDF. Văn bản Haiku (cận trên, không on-premise): Qwen3.5 1,000 / 1,000 | 02 §5, §8 |
| Chi phí (đo lúc máy rảnh, 38 tài liệu, 1 luồng) | Luật 3 ms; TF-IDF 3 ms; `bge-m3` 73 ms, 0,62 GB VRAM; Kev-0.8B 860 ms, 1,55 GB; Qwen2.5-3B 783 ms, 2,80 GB; Qwen3.5-4B 1.193 ms (p95 1.730), 3,05 GB. Cascade với Qwen3.5: ước tính 85 ms mỗi tài liệu; đo trực tiếp khi chấm TEST: trung bình 54 ms, p95 649 ms | 02 §7, §9 |

Ba điều phải đọc cùng bảng trên:

1. **TEST chỉ có 59 tài liệu.** Một lỗi là 1,7 điểm phần trăm. "0 lỗi" chỉ chứng minh được tỉ lệ sai dưới khoảng 5–8%, không chứng minh được dưới 1%.
2. **Nhãn do mô hình AI gán, chưa có nhân viên công ty kiểm.** Hai lượt gán của mô hình cùng họ trùng nhau 304/304 không chứng minh nhãn đúng.
3. **Vòng tròn nhãn/mô tả.** Mô tả loại và từ khóa của cổng luật được viết sau khi xem chính bộ mẫu này, và nhãn do mô hình gán theo chính các mô tả đó. Điểm của LLM zero-shot và "đúng 100%" của cổng luật vì vậy có thể lạc quan. Phép kiểm đã làm: bỏ hẳn mô tả, chỉ đưa tên loại, Qwen3.5 vẫn đạt 0,970 và Kev 0,962 trên DEV (02 §5) — làm giảm lo ngại nhưng không loại trừ.

### Chưa đo / chưa làm

- **Mức sai ≤ 1% chưa được chứng minh.** Cần khoảng 300 tài liệu tự nhận liên tiếp không lỗi (quy tắc ba: 0 lỗi trong n tài liệu cho cận trên 95% xấp xỉ 3/n); mức 0,5% cần khoảng 600 (02 §10).
- **Tổng quát hóa sang biểu mẫu, khách hàng và loại chưa từng thấy: chưa đo.** Hai loại lớn `CC_TAP_HUAN_VC_HNH` và `PHIEU_XUAT_KHO` gần như chỉ có một biểu mẫu; khi chia nghiêm ngặt theo biểu mẫu, recall của TF-IDF trên hai loại này là 0,05 và 0,00 (01 §8).
- **Kev-4B chưa chạy** (02 §3 nêu lý do: đổi mô hình toàn cục của máy chủ dùng chung, cần khoảng 8,4 GB VRAM). Mọi số "Kev" là Kev-0.8B.
- **Hiệu chỉnh độ tin cậy** (nhiệt độ, isotonic): **đã làm trên DEV (2026-10-15)**, [`04_safety_margin/RESULTS.md`](experiments/04_safety_margin/RESULTS.md): không đổi thứ hạng, LLM chính không học được hiệu chỉnh vì 0 lỗi; conformal chưa làm. Đồng thuận hai nguồn nay là tùy chọn `consensus` của cascade (tắt mặc định); trên DEV chưa đo được lợi ích (0 lỗi ở mọi mức), chỉ đo được cái giá (−1,7 đến −5,9 điểm độ phủ).
- **Dao động giữa các lần chạy và giữa các phiên bản mô hình:** chưa đo; mỗi cấu hình chạy một lần với `temperature = 0`, `seed = 0` (02 §11).
- **Thông lượng khi nhiều người dùng, GPU không dùng chung:** chưa đo.
- **Ảnh trang làm đầu vào** (mô hình thị giác cục bộ, kết hợp ảnh + văn bản cho tài liệu OCR gần rỗng): chưa làm.
- **8 tệp ghép khác loại**: đã chẩn đoán lỗi `BB_GIAO_NHAN` → `PHIEU_XUAT_KHO` (luật mơ hồ + ngưỡng TF-IDF dễ) và thử sửa bằng tùy chọn `rule_title_tiebreak` (tắt mặc định, cả trong pipeline: pipeline chỉ ghi nhãn nó SẼ chọn ở `routing[i].shadow["title_tiebreak_label"]`, không gọi thêm LLM; 8 tệp một nhà cung cấp, hồi quy DEV 25 quyết định đổi tầng, 0 đổi nhãn): [`05_composite_slices/RESULTS.md`](experiments/05_composite_slices/RESULTS.md). Chưa chứng minh tổng quát hóa.
- ~~Cascade chưa là một thành phần chạy đầu-cuối trong `src/`~~ — **đã có từ 2026-10-12** (T1 bên dưới): `DocumentClassifier`, kiểm hồi quy 237/237 tài liệu DEV trùng thí nghiệm 02, [`03_src_cascade/RESULTS.md`](experiments/03_src_cascade/RESULTS.md). Vẫn **chưa đo** gì mới: cascade trong `src/` chỉ tái tạo số của 02, kèm mọi hạn chế của 02. Tầng Kev của `src/` đã sửa nhưng **chưa được đo lại**.

## Những gì đã có

| Đường dẫn | Là gì | Ghi chú |
|---|---|---|
| `src/classification/taxonomy.py` | Nạp `data/taxonomy_v2.json` (nếu thiếu tệp thì dùng 19 tên thư mục cũ) | có test `tests/test_taxonomy.py` |
| `src/classification/doc_classifier.py` | **`DocumentClassifier`** (`from_defaults()`, `classify_slice(DocumentSlice) -> ClassificationResult`): luật → TF-IDF → LLM → người, quyết định nhận/từ chối bằng `cascade.run_cascade`, ngưỡng đọc từ `dev_selection_02.json` (`load_cascade_config`), từ chối ⇒ `tier="human"` kèm gợi ý. **Đường phân loại mặc định của pipeline** | test: `tests/test_classif_doc_classifier.py`; hồi quy: `experiments/03_src_cascade/` |
| `src/classification/tfidf_classifier.py` | `TfidfClassifier`: `tfidf_word_cnb_raw_C0.1`, `fit/predict/save/load`; `meta.json` ghi sha nhãn, `doc_id` huấn luyện (chỉ DEV), nguồn văn bản, phiên bản sklearn, ngày, checksum | artefact ở `models/classification/` (không commit; dựng lại: `scripts/train_tfidf_classifier.py`); test: `tests/test_classif_tfidf.py` |
| `src/classification/llm_backends.py` | Tầng 3: `OllamaBackend` (mặc định Qwen3.5-4B) và `KevBackend` (chỉ tên loại; tên mô hình lấy từ `/api/status`) qua `zero_shot.py` + `DiskCache` (`cache/llm/`) | `LLM_SPECS` sao nguyên các cấu hình đã đo ở 02 |
| `src/classification/system_one_classifier.py` | `CascadedClassifier`: cổng luật (1500 ký tự đầu, so khớp không dấu) → tầng Kev **tùy chọn, tắt mặc định** (`kev_endpoint=None`) → `UNKNOWN`. `DocumentClassifier` dùng nó cho tầng luật | tầng Kev đã sửa theo bẫy 3: tiêu chí = tên loại, `model_name` từ máy chủ; chưa đo lại |
| `src/classification/cascade.py` | Logic thuần của cascade 4 tầng trên **tín hiệu đã tính sẵn** (`Signals`, `CascadeParams`, `run_cascade`, `tune`, `tier_shares`); không gọi mô hình | có test `tests/test_cascade.py` |
| `src/classification/zero_shot.py` | `KevClient` (câu hỏi `Choice`), `OllamaClient` (JSON schema, logprob, embedding), `build_label_set`, biến thể một bước và hai bước | có test `tests/test_zero_shot.py` |
| `src/classification/llm_cache.py` | `DiskCache`: bộ nhớ đệm đĩa, khóa = mô hình + toàn bộ yêu cầu | chạy lại tất định, không gọi lại mô hình |
| `experiments/01_classical_baselines/` | `run_all.py`, `methods.py` (TF-IDF + LR/SVC/ComplementNB, cổng luật, baseline ảnh), `exp_lib.py` | mô hình TF-IDF đã chốt nay cũng có ở `src/classification/tfidf_classifier.py` (cùng mã, có lưu/nạp) |
| `experiments/04_safety_margin/` | `extract_signals.py`, `run_margin.py`, `RESULTS.md`: hiệu chỉnh, thang biên an toàn, kiểm mẫu | chỉ DEV; kết quả ở `results/04_safety_margin/` (`dev_signals.csv` chứa `doc_id`) |
| `experiments/05_composite_slices/` | `common05.py`, `diagnose.py`, `analyze_dev.py`, `eval_fix.py`, `RESULTS.md`: lỗi BB→PXK trong tệp ghép | `_cache/` không commit; `results/05_composite_slices/` chứa `doc_id` |
| `experiments/06_kev_reeval_finetune/` | `run_kev_reeval.py` (đo lại Kev DEV + lát tệp ghép), `build_finetune_dataset.py` (dữ liệu tinh chỉnh, **chưa huấn luyện**), `FINETUNE_PLAN.md`, `RESULTS.md`, `dataset_manifest.json` | `_cache/`, `_data/` (văn bản OCR) không commit; `results/06_kev_reeval_finetune/` chứa `doc_id` (nội bộ) |
| `experiments/03_src_cascade/` | `regress_vs_exp02.py` (hồi quy DEV từng tài liệu + một lần xác nhận TEST), `RESULTS.md` | kết quả: 237/237 trùng |
| `results/03_src_cascade/` | `regress_dev_summary.json`, `regress_dev_per_doc.csv` (**chứa `doc_id`**), `test_run_registry.json` | |
| `experiments/02_llm_and_cascade/` | `run_all.py`, `predictors.py`, `signals.py` (ghép tín hiệu từng tầng), `evalz.py`, `curated.py`, `cost_table.py`, `common.py` | `_cache/` không commit |
| `results/results_table.csv` | Bảng kết quả chung, chỉ thêm dòng (183 dòng khi viết) | cột và quy tắc: giao thức mục 9 |
| `results/01_classical_baselines/{tables,figs}/` | CSV từng bảng, ma trận nhầm lẫn, `dev_selection.json`, danh sách lỗi | CSV lỗi có tên tệp: chỉ dùng nội bộ |
| `results/02_llm_and_cascade/{tables,figs,preds}/` | `e1_*`…`e5_*`, `e4_cascade_{dev,test}.csv`, `cost_privacy.csv`, `latency_vram_quiet.csv`, `dev_selection_02.json`, `test_scored_02.json` (sổ đăng ký các lần chấm TEST) | `preds/` chứa `doc_id`: chỉ dùng nội bộ |
| `results/rule_gate_baseline/` | Số **lịch sử** của cách làm cũ (xem bẫy 14) | không so với các bảng khác |
| `scripts/evaluate_classifier_baseline.py` | Chấm `CascadedClassifier` của `src/` trên một tệp JSONL; có `--labels` để chấm theo loại v2 | đầu ra mặc định ở `results/rule_gate_runs/` |

## Việc cần làm (theo thứ tự ưu tiên)

Công sức là **ước lượng của người viết kế hoạch**, không phải số đo. Cỡ mẫu lấy từ bảng "thí nghiệm tiếp theo" ở 02 §10.

### T1 (P0) — Đưa cascade vào `src/classification` thành bộ phân loại chạy đầu-cuối

- **Trạng thái (2026-10-12): ĐÃ XONG cả 5 bước.** Kiểm hồi quy: **237 / 237 tài liệu DEV trùng** (tầng, nhãn, được nhận) và trùng cả tín hiệu trung gian với thí nghiệm 02, 0 lần lỡ cache LLM; một lần chạy TEST duy nhất chỉ để xác nhận tái lập dòng TEST đã báo cáo (59/59 tự nhận, 1 sai, luật/TF-IDF/LLM = 50/5/4) — chi tiết, lệnh, khác biệt có chủ ý: [`experiments/03_src_cascade/RESULTS.md`](experiments/03_src_cascade/RESULTS.md). Hợp đồng: `tier` có thêm `tfidf`/`llm`/`human`, thêm `suggested_*` (nhật ký thay đổi #1 ở [`teams/README.md`](../README.md) mục 6; **nhóm 00 chưa xác nhận**). Tầng Kev đã sửa (tên loại, `model_name` từ máy chủ, tắt mặc định) nhưng **chưa đo lại**.
- **Cách gọi:**

```python
from src.classification.doc_classifier import DocumentClassifier
clf = DocumentClassifier.from_defaults()                  # TF-IDF từ models/classification/, ngưỡng từ dev_selection_02.json, Ollama qwen3.5:4b
res = clf.classify_slice(doc_slice)                       # DocumentSlice -> ClassificationResult
# res.tier in {"rule","tfidf","llm","human"}; "human" => res.predicted_category == "UNKNOWN", requires_human_review == True,
# gợi ý ở res.suggested_category / suggested_confidence / suggestion_source, lý do ở res.abstain_reason, lỗi hạ tầng ở res.error
DocumentClassifier.from_defaults(use_llm=False)           # chỉ luật + TF-IDF (không cần Ollama)
DocumentClassifier.from_defaults(llm_backend="kev")       # tầng 3 = Kev (chỉ tên loại); xem cảnh báo measured=False trong clf.describe()
```

  Lý do về người (`abstain_reason`): `empty_text`, `text_too_short` (< 25 ký tự), `llm_low_confidence`, `llm_other` (LLM trả `OTHER`), `llm_error` (Ollama/Kev không trả lời hoặc hết giờ; `error` ghi lý do, **không có nhãn thay thế âm thầm**), `llm_disabled`. Pipeline toàn trình: `scripts/run_pipeline.py` (xem [`src/pipeline.py`](../../src/pipeline.py)).
- **Vì sao:** thiết kế đề xuất (02 §10) mới tồn tại như thí nghiệm: TF-IDF nằm trong `experiments/01_classical_baselines/methods.py`, tín hiệu từng tầng được ghép trong `experiments/02_llm_and_cascade/signals.py`, còn `CascadedClassifier` trong `src/` chỉ có luật + Kev. Các nhóm 2 và 4 và bộ điều phối toàn trình cần một hàm `DocumentSlice → ClassificationResult`.
- **Các bước:**
  1. Chuyển bộ phân loại TF-IDF đã chốt (`tfidf_word_cnb_raw_C0.1`) vào `src/classification/`, có lưu và nạp mô hình đã huấn luyện, ghi kèm sha của nhãn huấn luyện.
  2. Viết lớp điều phối gọi lần lượt luật → TF-IDF → LLM qua `zero_shot.py`, dùng `cascade.run_cascade` cho quyết định nhận/từ chối, với tham số đọc từ `results/02_llm_and_cascade/tables/dev_selection_02.json`.
  3. Hợp đồng: `ClassificationResult.tier` hiện chỉ có `rule`/`kev`/`none`. Đề nghị nhóm 00 mở rộng (`tfidf`, `llm`, `human`) theo quy tắc ở `teams/README.md` mục 1; cập nhật `tests/test_contracts.py`.
  4. Sửa tầng Kev của `CascadedClassifier` theo bẫy 3, hoặc gỡ nó khỏi đường mặc định.
  5. Kiểm hồi quy: trên DEV, quyết định của lớp mới phải trùng từng tài liệu với dự đoán đã lưu của thí nghiệm 02 cho cùng cấu hình (mọi lời gọi LLM lấy từ cache).
- **Bắt đầu từ:** `src/classification/cascade.py`, `experiments/02_llm_and_cascade/signals.py`, `experiments/01_classical_baselines/methods.py`.
- **Sản phẩm:** mã trong `src/classification/` kèm test trong `tests/`.
- **Xong khi:** `pytest -q` qua; kiểm hồi quy trùng 237/237 tài liệu DEV; `tier` và `model_name` ghi đúng thành phần đã chạy; không mở TEST.
- **Công sức (ước lượng):** 3–4 ngày.
- **Điều kiện tiên quyết:** nhóm 00 đồng ý thay đổi hợp đồng.

### T2 (P0) — Chạy lại khi nhãn đã được nhân viên công ty kiểm

- **Vì sao:** mọi con số ở trên tính trên nhãn do mô hình gán. Việc kiểm nhãn là T1 của [nhóm 00](../00_data_and_eval/README.md); 02 §10 đề nghị rà toàn bộ 24 loại hiếm và 30–50 tài liệu thường ngẫu nhiên (khoảng 150 tài liệu).
- **Các bước:** (1) chạy lại giai đoạn DEV của 01 và 02 với nhãn mới (LLM lấy từ cache nên rẻ); (2) so từng bảng với bản cũ, ghi số tài liệu đổi nhãn theo loại; (3) về TEST: `data/splits/` là tập chia **đã khóa**, thành viên DEV/TEST không đổi khi nhãn được sửa. Chấm lại TEST trên nhãn đã sửa là lần chấm thứ hai của cùng cấu hình, phải nêu lý do trong báo cáo (giao thức mục 4); không chỉnh bất kỳ thứ gì giữa hai lần chấm.
- **Sản phẩm:** `RESULTS.md` của hai thí nghiệm được sinh lại; một mục "so với nhãn trước khi kiểm".
- **Xong khi:** mọi bảng mang sha nhãn mới; các đoạn "Đọc kết quả" viết tay đã được rà lại.
- **Công sức (ước lượng):** 1–2 ngày.
- **Điều kiện tiên quyết:** nhóm 00 xong T1.

### T3 (P0) — Ngưỡng có biên an toàn và kiểm mẫu ngẫu nhiên

- **Trạng thái (2026-10-15): làm xong phần mã và đo trên DEV** — [`experiments/04_safety_margin/RESULTS.md`](experiments/04_safety_margin/RESULTS.md) (thư mục thực tế là `04_safety_margin`, không phải `03_`). Có `CascadeParams.consensus`, `audit_rate`/`decision_log` trong `DocumentClassifier`, bảng tự xếp/sai/cận trên theo 9 mức biên. **Kết luận: dữ liệu DEV chưa đủ để chọn giữa các mức** (0 lỗi cross-fit ở mọi mức, cận trên ≈ 1,3% do cỡ mẫu); chọn thật cần T4. Mặc định chưa đổi.

- **Vì sao:** ngưỡng chọn trên DEV hiện dễ dãi đến mức tầng 3 nhận hầu như mọi thứ (phần cho người gần 0%), vì LLM chỉ sai 1/237 trên DEV nên không còn tín hiệu để đặt ngưỡng chặt (02 §7).
- **Các bước:** (1) hiệu chỉnh độ tin cậy (nhiệt độ hoặc isotonic) trên dự đoán out-of-fold của DEV, báo lại ECE và đường risk-coverage; (2) thêm chế độ "hai LLM đồng thuận" vào `cascade.py`; (3) thêm tham số giữ lại một tỉ lệ kiểm mẫu ngẫu nhiên trên phần tự nhận (02 §10 đề xuất 5–10%) và ghi log mọi quyết định (tầng, độ tin cậy); (4) báo số cross-fit, không chỉ số chọn-và-chấm trên cùng DEV.
- **Sản phẩm:** `experiments/03_safety_margin/` với `RESULTS.md`; cập nhật `src/classification/cascade.py` kèm test.
- **Xong khi:** có bảng tự xếp hồ sơ và số sai theo từng mức biên an toàn, kèm cận trên Clopper–Pearson; nêu rõ dữ liệu hiện có chưa đủ để chọn giữa các mức nếu khoảng tin cậy chồng nhau.
- **Công sức (ước lượng):** 3–4 ngày.

### T4 (P0, cần công ty) — Chạy bóng để đo tỉ lệ sai thật

- **Vì sao:** đây là cách duy nhất để chứng minh mức sai ≤ 1%.
- **Các bước:** chạy cascade ở chế độ bóng 2–4 tuần: nhân viên vẫn xếp hồ sơ như cũ, hệ thống ghi dự đoán và mọi bất đồng. Cỡ mẫu: ít nhất 1000 tài liệu thật; cần khoảng 300 tài liệu tự nhận liên tiếp không lỗi để nói "sai ≤ 1%", khoảng 600 để nói "≤ 0,5%" (02 §10, dòng 1).
- **Sản phẩm:** `experiments/04_shadow/RESULTS.md`: tỉ lệ tự nhận, số sai, cận trên 95%, phân tích từng bất đồng (mô hình sai hay người sai).
- **Xong khi:** có số đo trên ít nhất 1000 tài liệu và công ty đã chọn mức sai chấp nhận.
- **Điều kiện tiên quyết:** T1; OCR đã vào `src/` ([nhóm 1](../team1_ocr/README.md), T4); quyết định của công ty.

### T5 (P1) — Tập TEST mới từ khách hàng và biểu mẫu chưa từng thấy

- **Vì sao:** để đo tổng quát hóa và để thoát vòng tròn nhãn/mô tả.
- **Các bước:** nhân viên công ty gán nhãn mà không thấy dự đoán của mô hình. Cỡ mẫu (02 §10, dòng 2): ít nhất 150 tài liệu từ ít nhất 10 khách hàng hoặc biểu mẫu, gồm ít nhất 5 loại mới × 5 tài liệu. Muốn khoảng tin cậy ±15 điểm cho recall của từng loại cần 20 tài liệu mỗi loại (24 loại hiếm, tức khoảng 480 tài liệu). Tài liệu mới vào một tập riêng, không trộn vào chia cũ (nhóm 00, T3).
- **Xong khi:** có bảng kết quả của cấu hình đã chốt trên tập mới, chấm đúng một lần.

### T6 (P1) — Kiểm chứng "thêm loại mới không cần huấn luyện lại"

- **Các bước:** nhân viên viết mô tả ngắn cho 5–10 loại mới **trước khi xem tài liệu**, mỗi loại ít nhất 10 tài liệu; đo tầng 3 (02 §10, dòng 3). Đây là phép thử không bị vòng tròn mô tả.
- **Xong khi:** có recall từng loại mới kèm khoảng tin cậy và cỡ mẫu.

### T7 (P1) — Chọn mô hình tầng 3 theo VRAM

- **Các bước:** so Kev-4B (nếu có GPU riêng), các cỡ Qwen3.5 khác, và kết hợp ảnh + văn bản cho tài liệu OCR gần rỗng, trên tập của T5 (02 §10, dòng 6). Không dùng lại TEST cũ để chọn.

### T8 (P1) — Kiểm thử tải

- **Các bước:** hàng đợi tuần tự cho Kev và Ollama trên GPU chuyên dụng, một ngày dữ liệu; báo thông lượng, p95 độ trễ, độ ổn định (02 §10, dòng 7).

### T9 (P1) — Phân loại theo trang cho nhóm tách tài liệu

- **Trạng thái (2026-10-15): một phần.** Đã phân loại từng trang của 8 tệp ghép (cơ sở 26/34 đúng, với `rule_title_tiebreak` 32/34; chẩn đoán, một nhà cung cấp) và tìm ra nguyên nhân lỗi BB/PXK: [`experiments/05_composite_slices/RESULTS.md`](experiments/05_composite_slices/RESULTS.md). Chưa có bộ gộp trang liền kề thành lát cắt dùng cho nhóm 2.

- **Các bước:** cùng [nhóm 2](../team2_splitting/README.md) (T3.1): phân loại từng trang rồi gộp các trang liên tiếp cùng loại. Dữ liệu: 8 tệp ghép khác loại trong `data/splits/excluded_composites.csv` (20 ranh giới). `data/ocr_llm_haiku.jsonl` chỉ có 2 trang đầu nên phải dùng `data/ocr_v2.jsonl`.

### T11 (P2) — Tinh chỉnh Kev-0.8B trên dữ liệu của công ty (chưa làm; khuyến nghị: chưa)

- **Trạng thái (2026-10-16): đã chuẩn bị dữ liệu và kế hoạch, chưa huấn luyện.** Đo lại Kev trên máy chủ mới ([`06`](experiments/06_kev_reeval_finetune/RESULTS.md)): 0,962 DEV, 9 lỗi rải rác, kém Qwen3.5 0,034. Dữ liệu 377 dòng, 5 fold theo nhóm, định dạng huấn luyện của Kev ở `experiments/06_kev_reeval_finetune/_data/` (không commit). Kế hoạch, giao thức, tiêu chí chấp nhận và cỡ mẫu: [`FINETUNE_PLAN.md`](experiments/06_kev_reeval_finetune/FINETUNE_PLAN.md).
- **Điều kiện để bắt đầu:** nhãn do nhân viên kiểm (T2) và >= ~430 tài liệu giữ ra có nhà cung cấp, gồm khách hàng chưa thấy (T5). Trước đó chỉ làm việc rẻ: hệ số làm sắc cho độ tin cậy Kev.
- **Công sức (ước lượng):** 2-3 ngày chạy một fold đo thực rồi 5 fold; công kiểm nhãn lớn hơn.

### T10 (P2) — Phân loại theo 8 nhóm làm phương án dự phòng

- **Các bước:** khi loại cụ thể không chắc, trả về nhóm cấp 1 của taxonomy để người duyệt chọn trong ít lựa chọn hơn (01 §15).

## Cách chạy lại những gì đã có

Chạy từ gốc repo, PowerShell (dựng môi trường: [handbook](../../docs/HANDBOOK_FOR_RESEARCHERS.md) mục 2). Các lệnh dưới đây chép từ mục "Lệnh chạy chính xác" của hai `RESULTS.md`; **không lệnh nào được chạy lại khi viết README này**.

Thí nghiệm 01 (chỉ cần CPU):

```powershell
$py = ".venv\Scripts\python.exe"
$e1 = "teams\team3_classification\experiments\01_classical_baselines\run_all.py"
& $py -X utf8 $e1 --labels data\labels_v2.csv --jobs 16        # giai đoạn DEV: mọi bảng, biểu đồ, cấu hình đã chốt (khoảng 8 phút với --jobs 28)
& $py -X utf8 $e1 --labels data\labels_v2.csv --render-dev-only   # chỉ vẽ lại các bảng DEV trong RESULTS.md từ CSV đã lưu
& $py -X utf8 $e1 --labels data\labels_v2.csv --final-test     # TEST khóa: ĐÃ CHẤM cho bộ nhãn eb3348713a, lệnh sẽ từ chối chạy lại
```

Thí nghiệm 02 (cần Kev ở `127.0.0.1:8009` với mô hình `kev-0.8b`, và Ollama ở `127.0.0.1:11434` với `qwen3.5:4b`, `qwen2.5:3b`, `bge-m3`; khi `_cache/` còn thì các lời gọi mô hình không phải chạy lại):

```powershell
$e2 = "teams\team3_classification\experiments\02_llm_and_cascade\run_all.py"
& $py -X utf8 $e2 --stage embed                       # E1: embedding
& $py -X utf8 $e2 --stage zeroshot --family kev       # E2: Kev (chạy xong mới chạy Ollama)
& $py -X utf8 $e2 --stage zeroshot --family ollama    # E2: Ollama
& $py -X utf8 $e2 --stage zeroshot_sources            # E5: cấu hình tốt nhất trên haiku_p12, legacy_p1
& $py -X utf8 $e2 --stage calib                       # E3: calibration, đồng thuận
& $py -X utf8 $e2 --stage cascade                     # E4: chọn ngưỡng trên DEV out-of-fold + ablation
& $py -X utf8 $e2 --stage latency                     # độ trễ + VRAM, bỏ qua cache: chỉ chạy khi máy rảnh
& $py -X utf8 $e2 --stage report                      # vẽ lại các bảng trong RESULTS.md từ CSV
& $py -X utf8 $e2 --final-test                        # TEST khóa: ĐÃ CHẤM, lệnh sẽ từ chối chạy lại
& $py -X utf8 -m pytest -q                            # 327 test qua ngày 2026-10-16 (gồm test do các nhóm khác thêm); 162 ngày 2026-10-12, nền trước đó là 79
```

Cascade trong `src/` (thêm 2026-10-12; các lệnh dưới đã chạy khi viết, kết quả ở [`03_src_cascade/RESULTS.md`](experiments/03_src_cascade/RESULTS.md)):

```powershell
& $py -X utf8 scripts\train_tfidf_classifier.py                                                  # dựng lại models\classification\tfidf_word_cnb_raw_C0.1 (chỉ DEV, vài giây)
& $py -X utf8 teams\team3_classification\experiments\03_src_cascade\regress_vs_exp02.py          # hồi quy DEV 237 tài liệu (cache LLM chỉ đọc)
& $py -X utf8 scripts\run_pipeline.py <tệp.pdf> --out output\pipeline                           # OCR -> tách -> phân loại -> trích xuất (cần Ollama; --no-llm --no-extract để chạy nhẹ)
```

(Lệnh `regress_vs_exp02.py --final-test-once` đã dùng đúng một lần và bị sổ đăng ký chặn chạy lại.)

Chấm riêng mã trong `src/` (`CascadedClassifier`) theo nhãn v2, chỉ cổng luật, không gọi Kev:

```powershell
& $py -X utf8 scripts\evaluate_classifier_baseline.py --input data\ocr_v2.jsonl --labels data\labels_v2.csv --kev-endpoint ""
```

Script ghép theo `doc_id`, bỏ bản trùng byte và tệp ghép khác loại, và mặc định ghi vào `results/rule_gate_runs/<tên đầu vào>__<bộ nhãn>/` (không ghi đè thư mục lịch sử `rule_gate_baseline/`). Không truyền `--labels` thì nó chấm theo nhãn thư mục cũ, chỉ để tái lập baseline cũ. Để so sánh mô hình, dùng bộ chấm chung (harness), không dùng script này.

Ghi chú khi chạy lại:

- **`data/splits/` là tập chia đã khóa.** Các lệnh trên chỉ đọc nó. Sửa nhãn không làm tài liệu đổi DEV/TEST hay đổi fold (bộ chấm chỉ cảnh báo rằng sha nhãn đã khác lúc chia). Nếu benchmark có tài liệu chưa được gán tập (ví dụ thêm tài liệu mới), bộ chấm dừng với `SplitsOutOfDateError` thay vì âm thầm chia lại. Chia lại là quyết định có chủ ý — `load_or_make_splits(bench, rebuild=True)` hoặc cờ `--rebuild-splits` của `run_all.py` thí nghiệm 01 — và có giá: TEST mới khác TEST cũ, mọi số TEST đã báo cáo phải chấm lại. Cờ `--keep-splits` xuất hiện trong 01 §0 vẫn được nhận nhưng không còn tác dụng (giữ tập chia đã là mặc định). Chi tiết: [`data/splits/README.md`](../../data/splits/README.md).
- Giai đoạn DEV **thêm dòng mới** vào `results/results_table.csv` (bảng chỉ-thêm-dòng). 01 §0 dùng `--results-sources` để chỉ ghi dòng của nguồn mới; xem phần `argparse` cuối `run_all.py` trước khi chạy.
- `--final-test` từ chối chạy khi nhãn đã đổi hoặc TEST đã được chấm cho bộ nhãn đó; `--allow-rescore` tồn tại nhưng mỗi lần dùng phải có lý do ghi trong `RESULTS.md`.
- Thử đường chấm TEST của 02 mà không mở TEST: đặt biến môi trường `EXP02_SMOKE=1` trước lệnh `--final-test` (dùng tài liệu DEV, không ghi bảng chung, không ghi sổ đăng ký; 02 §2).
- Các bảng nằm giữa `<!-- BEGIN:... -->` và `<!-- END:... -->` trong `RESULTS.md` do script sinh; đừng sửa tay. Các đoạn "Đọc kết quả" là viết tay và phải rà lại sau mỗi lần chạy với nhãn khác.

## Bẫy thường gặp (đã gặp thật)

1. **Không chạy Kev và Ollama song song trên cùng GPU.** Đã xảy ra: Ollama đứng 1–6 phút mỗi lời gọi (02 §11). Chạy tuần tự từng giai đoạn.
2. **Máy chủ Kev xử lý tuần tự.** Ba tiến trình cùng gọi làm độ trễ treo tường lên 15–64 giây dù thời gian mô hình chỉ 0,35 giây; gọi song song không nhanh hơn và làm chậm mọi người dùng khác (02 §3).
3. **Kev sụp với mô tả dài** (accuracy 0,300 một bước, 0,397 hai bước, so với 0,962 khi chỉ đưa tên loại; 02 §5). Với Kev, viết tiêu chí thật ngắn. **Đã sửa (2026-10-12):** `CascadedClassifier.classify_with_kev` từng gửi `description` dài và ghi `model_name="kev-4b"` trong khi máy chủ chạy Kev-0.8B; nay gửi **tên loại**, ghi `model_name` theo `/api/status` của máy chủ (`kev-unverified` nếu không hỏi được), và Kev tắt mặc định. Cấu hình sau khi sửa khớp cấu hình đã đo ở 02 về tiêu chí và câu hỏi, nhưng **chưa chạy lại trên tài liệu**; chế độ đồng thuận embedding (`agree=emb`) của cascade Kev chưa có trong `src/`.
4. **Độ tin cậy của Kev không phải xác suất.** Xếp hạng tốt (AUROC 0,961) nhưng giá trị tuyệt đối rất thấp (ECE 0,441: xác suất rải trên 35 lựa chọn). Đặt ngưỡng theo thứ hạng.
5. **Đừng dùng logprob một bước của Qwen làm ngưỡng từ chối** (AUROC 0,750, và trên OCR cũ vẫn chỉ 0,77); dùng biến thể hai bước hoặc đồng thuận (02 §6).
6. **TEST chỉ chấm một lần.** Không đọc lỗi TEST để sửa luật hay prompt; nếu đã làm, coi TEST đã "cháy" và phải có vòng dữ liệu mới (giao thức mục 4).
7. **Ngưỡng DEV dễ dãi.** Xem T3. Đừng đưa nguyên ngưỡng này vào hệ thống thật mà không có kiểm mẫu.
8. **"0 lỗi" không phải "sai dưới 1%".** 0 lỗi trong 36 tài liệu cho cận trên 8,0%; 1 lỗi trong 59 cho 7,8%.
9. **Macro-F1 Track Z trên TEST chỉ chấm 10 loại** (loại có ít nhất 3 tài liệu thật trong TEST). Vì vậy Kev (tên loại) có macro-F1 0,991 trong khi accuracy chỉ 0,932 và recall loại hiếm 0,73 (02 §9). Luôn đọc accuracy và recall loại hiếm cùng macro-F1.
10. **TF-IDF không bao giờ nhận loại hiếm** (recall 0 trên Track Z, đúng thiết kế: `RARE_OR_OTHER` luôn cho người). Lỗi nguy hiểm của nó là chiều ngược lại: tài liệu hiếm bị ép vào loại đã biết (5 trong 6 lỗi DEV trên nguồn Haiku; 01 §11).
11. **Hai mô hình cùng học trên một dữ liệu đồng thuận thì không đáng tin.** TF-IDF + embedding cùng nhãn: 5 lỗi trong 175 tài liệu DEV. Hai mô hình khác họ (Kev + Qwen): 0 lỗi trong 227 (02 §6).
12. **Hai con số tự xếp hồ sơ của cùng một mô hình TF-IDF:** 61,0% (01, ngưỡng chọn trên nhãn Track S) và 64,4% (02, ngưỡng chỉnh lại trên nhãn Track Z). Khi trích dẫn phải nói con số nào.
13. **Độ trễ đo lúc chạy lưới bị phồng** vì GPU/CPU dùng chung; chỉ dùng số của `--stage latency` (đo riêng lúc máy rảnh). `num_predict=96` được thêm làm lưới an toàn cho Ollama nhưng không nằm trong khóa cache (02 §11).
14. **`results/rule_gate_baseline/summary.json` là số lịch sử:** taxonomy 19 thư mục cũ, nhãn = thư mục, Kev tắt (accuracy 0,293 trên 334 bản ghi). Không so với bất kỳ bảng nào ở trên.
15. **OCR kém phá Kev nhiều hơn phá các tầng khác** (0,962 → 0,498 trên DEV khi chuyển sang OCR cũ). Không dùng Kev-0.8B làm tầng cuối nếu OCR kém.
16. **Tài liệu có dưới 25 ký tự văn bản** được chuyển thẳng cho người, không gọi mô hình; nhãn `OTHER` không bao giờ được tự xếp hồ sơ (02 §3).
17. **`preds/` và các CSV lỗi chứa `doc_id` hoặc tên tệp:** chỉ dùng nội bộ, không đưa vào báo cáo `.md`.
18. **Một lần chạy DEV của 01 từng sập** (`ValueError: After pruning, no terms remain`) rồi không tái hiện được; nghi do chạy 28 tiến trình lúc máy bận (01 §0). Nếu gặp lại, giảm `--jobs` và ghi lại.
19. **Artefact TF-IDF trong `models/` đã thấy toàn bộ DEV.** Chạy nó lại trên DEV là chấm trên dữ liệu huấn luyện; muốn số trung thực trên DEV phải huấn luyện theo fold (cách `03_src_cascade/regress_vs_exp02.py` làm). Pickle còn phụ thuộc phiên bản scikit-learn (cảnh báo khi nạp).
20. **Khóa cache LLM theo từng ký tự của lời nhắc và theo mô hình.** Đổi `OLLAMA_SYSTEM`, cách làm sạch văn bản (`zero_shot.clean_prompt_text`), danh sách loại hoặc mô tả trong `taxonomy_v2.json` ⇒ mọi lời gọi lỡ cache và gọi lại Ollama thật, và kết quả có thể khác thí nghiệm 02. Đổi taxonomy nghĩa là phải đo lại.
21. **LLM bị chiếm GPU ⇒ hết giờ 180 giây.** Quan sát thật khi chạy `run_pipeline.py` trên máy dùng chung: một lát cắt bị `ReadTimeout`, được ghi `abstain_reason=llm_error` và chuyển cho người (đúng thiết kế); chạy lại thì có kết quả. Triển khai thật cần GPU không dùng chung và có hàng đợi (T8). **Đã xử lý phần "treo" (2026-10-12):** nguyên nhân là phía máy chủ Ollama dùng chung (nạp lại mô hình ≈ 26-32 s mỗi lần + hàng đợi), không phải prompt; `OllamaBackend` nay hết giờ 60 s (trước 180 s) và `src/pipeline.py` thêm ngân sách LLM 90 s/tệp, mạch ngắt và lý do `llm_timeout`/`llm_skipped` (xem `teams/00_data_and_eval/experiments/01_end_to_end/RESULTS.md`). Cascade và số đo không đổi.
22. **Văn bản đưa vào cascade là 2 trang đầu của lát cắt** (đúng nguồn `ocr_v2_p12` đã đo), không phải cả lát cắt. Lát cắt do nhóm 2 quyết định: nếu bộ tách cắt một tài liệu thành nhiều lát (đã thấy: tệp ghép 5 trang → 3 lát, hai lát đầu cùng loại), mỗi lát được phân loại riêng.

## Câu hỏi cần hỏi doanh nghiệp

1. Mức sai nào chấp nhận được cho việc tự xếp hồ sơ (1%, 2%, khác)? Một lần xếp sai tốn gì so với một lần người phải xem?
2. Công ty có đồng ý chạy bóng 2–4 tuần trên ít nhất 1000 tài liệu thật (T4) không? Ai ghi nhận bất đồng?
3. Ai ở công ty gán nhãn cho tập TEST mới (T5), và có thể lấy mẫu từ những khách hàng, nhà cung cấp, cửa hàng nào chưa có trong bộ mẫu?
4. Những loại tài liệu nào công ty dự kiến sẽ có thêm? Nhân viên có thể viết mô tả một câu cho từng loại trước khi đưa mẫu (T6) không?
5. Máy chạy thật có GPU không, bao nhiêu VRAM, có dùng chung với việc khác không? (máy dev: RTX 3060 12 GB, dùng chung)
6. Kiểm mẫu ngẫu nhiên 5–10% trên phần tự xếp có chấp nhận được về công sức không? Ai làm, qua công cụ nào?
7. Khi hệ thống từ chối, nhân viên muốn thấy gì: gợi ý một loại, ba loại có khả năng nhất, hay nhóm cấp 1?
