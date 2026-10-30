# Thí nghiệm 06 - Đo lại Kev-0.8B trên máy chủ mới và chuẩn bị (chưa huấn luyện) dữ liệu tinh chỉnh (Nhóm 3)

> Nhãn `data/labels_v2.csv` sha1[:10] `eb3348713a` (nhãn **do máy gán**, chưa nhân viên kiểm). Ngày 2026-10-16. Nguồn văn bản: `ocr_v2_p12` (OCR local, trang 1-2, 2000 ký tự đầu sau `clean_prompt_text`, đúng như thí nghiệm 02). **Chỉ DEV (237 tài liệu); TEST không được mở.**
> Tái lập (từ gốc repo): `.venv\Scripts\python.exe -X utf8 teams\team3_classification\experiments\06_kev_reeval_finetune\run_kev_reeval.py --stage run` rồi `--stage analyze`; dữ liệu tinh chỉnh: `...\build_finetune_dataset.py`. Lời gọi Kev được cache ở `_cache/` (không commit; tag cache `kev-0.8b-srv20261016` khác tag cũ nên **không** dùng lại số cũ). Đầu ra có `doc_id` (nội bộ) ở `teams/team3_classification/results/06_kev_reeval_finetune/`.
> Kết luận về tinh chỉnh và giao thức đánh giá: [`FINETUNE_PLAN.md`](FINETUNE_PLAN.md).
> **Đã đo** = số trong tệp này; **Suy luận** = chưa kiểm chứng. "So với đáp án máy" = so với `labels_v2.csv`, không phải độ chính xác thật.

## 0. Tóm tắt

| # | Kết luận | Mức |
|---|---|---|
| 1 | Máy chủ Kev **đã đổi API** (`/api/status` trả 404; thông tin mô hình ở `GET /v1/models`) nhưng **mô hình và kết quả không đổi**: cùng `jaredpalmer/kev-0.8b`, nhiệt độ 2,351; nhãn dự đoán của 237 tài liệu DEV **trùng 100%** với lần đo giai đoạn 1 (cấu hình chỉ-tên-loại), xác suất lệch tối đa 0,011 (bf16). Accuracy **0,962 (228/237) [Wilson 0,929; 0,980]**. | Đã đo |
| 2 | Qwen3.5-4B (mô tả ngắn, cache giai đoạn 1) trên đúng 237 tài liệu đó: **0,996 (236/237)**. Hiệu (Kev - Qwen) = **-0,034, bootstrap cặp [-0,059; -0,013]**; McNemar chính xác: Kev đúng riêng 0, Qwen đúng riêng 8, p = 0,008. Kev **kém hơn có ý nghĩa** ở cấp tài liệu đơn lẻ. | Đã đo |
| 3 | Hai biến thể rẻ, **chọn trên DEV, không đóng băng cho TEST**: (a) tên + 4 từ khóa: **0,932 [0,893; 0,958], tệ hơn** (cặp với chỉ-tên: -0,030 [-0,068; 0,004], p = 0,14, không tách được nhưng AUROC rơi 0,961 -> 0,738); (b) `permute` 6 thứ tự: **0,962, không đổi** (3 tài liệu đúng-riêng mỗi bên), chậm ~4 lần. Không biến thể nào đáng giữ. | Đã đo |
| 4 | Lỗi **không tập trung theo biểu mẫu/nhà cung cấp**: 9 lỗi, 7 cặp (đúng -> nhầm) khác nhau, chỉ 1 cặp lặp (`HO_SO_QUAN_LY_PCCC` -> `CONG_VAN_THONG_BAO`, 3 lần) ; 2/9 lỗi nằm trong nhóm cùng mẫu và không nhóm nào có >= 2 lỗi. Có tập trung theo **loại hiếm**: 3/7 `HO_SO_QUAN_LY_PCCC` sai. 3/9 lỗi là Kev trả `OTHER` với độ tin cậy thấp (0,13-0,15; `OTHER` không bao giờ được tự xếp hồ sơ). | Đã đo; n rất nhỏ |
| 5 | Hiệu chỉnh: ECE phục vụ = **0,441** (giống hệt giai đoạn 1). Nhiệt độ 2,35 làm Kev **quá thiếu tự tin** với 35 lựa chọn (tin cậy trung bình 0,524 trong khi đúng 96,2%). Làm sắc phân phối sau khi phục vụ (p^k, k chọn bằng cross-fit theo fold trên DEV, luôn chọn k = 4) hạ ECE xuống **0,023** mà không đổi nhãn dự đoán. Không cần tinh chỉnh để sửa điểm này. | Đã đo (DEV, n = 237) |
| 6 | Lát cắt đáp án của 8 tệp ghép (một nhà cung cấp, 28 lát): Kev đúng **27/28 [Wilson 0,823; 0,994]**, cả ba biến thể; 7/7 lát biên bản giao nhận đúng (TF-IDF cơ sở sai 6/7 ở 05). Chẩn đoán, không tổng quát hóa. | Đã đo; n = 28 |

## 1. Máy chủ và API

`GET /v1/models` (2026-10-16): `kev-latest` (và bí danh `jev-latest`), `run = jaredpalmer/kev-0.8b`, `base = Qwen/Qwen3.5-0.8B-Base`, LoRA 16, bf16, torch/cuda, temperature 2,3511, release 2026-10-01. Điểm cuối: `/v1/systemone` (cùng hợp đồng `Choice` như trước), `/v1/systemone/permute`, `/v1/systemone/separate`. `/api/status` và `/api/predict` (máy chủ demo cũ) **không còn** (404).

Hệ quả cho mã: `kev_server_model()` (`system_one_classifier.py`) và `KevBackend.server_model()` (`llm_backends.py`, tầng 3 khi `llm_backend="kev"`) đọc `/api/status` nên trả `None` và `KevBackend` báo "Kev không khả dụng" dù máy chủ chạy. **Đã sửa tối thiểu**: hàm mới `zero_shot.fetch_kev_model_name` thử `/v1/models` (`models[0].run`) rồi mới `/api/status`; hai nơi gọi dùng hàm này; thêm test `tests/test_zero_shot.py::test_fetch_kev_model_name_new_and_old_server`. `run_all.py` của 02 (`kev_model_name`) **không sửa** (ngoài phạm vi; muốn chạy lại 02 với Kev cần đổi `KEV_STATUS`). Lời gọi `/v1/systemone` của `KevClient` không cần đổi.

## 2. Kev trên DEV (237 tài liệu, `ocr_v2_p12`)

`name` = tiêu chí là TÊN loại (cấu hình giai đoạn 1); `name_kw` = tên + 4 từ khóa đầu của `taxonomy_v2.json` (từ khóa được viết sau khi xem tài liệu mẫu - xem vòng tròn nhãn/mô tả ở 02 §3); `perm_name` = `/v1/systemone/permute`, 6 thứ tự, trung bình xác suất. Hai biến thể sau **chọn trên DEV**.

| phương pháp | đúng/237 | accuracy [Wilson 95%] | macro-F1 [CI bootstrap] (20 loại >= 3 tài liệu) | recall hiếm (63) | ECE | AUROC | tự nhận @sai<=1% (DEV, tự chọn) | trung vị treo tường (ms)* |
|---|---|---|---|---|---|---|---|---|
| Kev chỉ tên (máy chủ mới) | 228 | 0,962 [0,929; 0,980] | 0,963 [0,905; 0,988] | 0,905 | 0,441 | 0,961 | 0,949 (2 sai/225) | 302 (p95 928) |
| Kev chỉ tên (giai đoạn 1, đối chứng) | 228 | 0,962 [0,929; 0,980] | 0,963 [0,905; 0,988] | 0,905 | 0,441 | 0,961 | 0,949 | 839 |
| Kev tên + 4 từ khóa (DEV) | 221 | 0,932 [0,893; 0,958] | 0,879 [0,829; 0,974] | 0,841 | 0,451 | 0,738 | 0,228 (0 sai/54) | 1.124 |
| Kev permute 6 thứ tự (DEV) | 228 | 0,962 [0,929; 0,980] | 0,958 [0,898; 0,987] | 0,889 | 0,443 | 0,948 | 0,890 (2 sai/211) | 1.149 |
| Qwen3.5-4B mô tả ngắn (02, cache) | 236 | 0,996 [0,976; 0,999] | 0,990 [0,968; 1,000] | 0,984 | 0,114 | 0,750 | 0,992 (0 sai/235) | 1.374 |

\* Độ trễ treo tường **khi GPU dùng chung** (người khác đang dùng 91% GPU lúc chạy; các lượt khác nhau, không so được chặt: 302 ms so với 839 ms của lần cũ **không** chứng minh máy chủ mới nhanh hơn). Thời gian máy chủ báo trung vị 260 ms (`chỉ tên`), 1.078 ms (`+từ khóa`, văn bản tiêu chí dài hơn nhiều).

So cặp (cùng 237 tài liệu; bootstrap cặp 2000 lần theo tài liệu; mỗi tài liệu là một tệp duy nhất):

| A | B | A đúng riêng | B đúng riêng | McNemar p | A - B [CI bootstrap] |
|---|---|---|---|---|---|
| Kev chỉ tên (mới) | Kev chỉ tên (cũ) | 0 | 0 | 1,0 | 0,000 (cùng nhãn) |
| Kev chỉ tên (mới) | Qwen3.5-4B | 0 | 8 | 0,008 | -0,034 [-0,059; -0,013] |
| Kev permute | Kev chỉ tên | 3 | 3 | 1,0 | 0,000 [-0,021; 0,021] |
| Kev +từ khóa | Kev chỉ tên | 5 | 12 | 0,14 | -0,030 [-0,068; 0,004] (không tách được) |
| Kev +từ khóa | Qwen3.5-4B | 0 | 15 | < 0,001 | -0,063 [-0,097; -0,034] |

Cascade đầu-cuối (luật -> TF-IDF -> LLM, 02 §7, bảng `e4_cascade_dev.csv`, ngưỡng tự chọn trên DEV nên lạc quan, **không cặp** được vì bảng không lưu từng tài liệu): tầng 3 = Kev chỉ tên: accuracy 0,975 [0,954; 0,992], tự nhận 233/237 với 2 sai; tầng 3 = Qwen3.5: 0,992 [0,979; 1,000], 236/237 với 1 sai. Cross-fit: cả hai 0 sai trong phần được nhận (96,6% so với 98,3%). Khoảng của hai cascade chồng nhau: **không tách được** ở mức cascade, dù tách được ở mức mô hình đơn.

**Kev vs Qwen bù lỗi nhau?** Trong 9 lỗi của Kev, Qwen đúng 8. Đồng thuận Kev + Qwen (02 §6) từng nhận 95,8% DEV với 0 sai; biến thể mới không đổi điều đó vì nhãn Kev không đổi.

## 3. Hiệu chỉnh và thiên vị thứ tự

- **Nhiệt độ phục vụ 2,351**: tin cậy trung bình của nhãn chọn là 0,524; độ đúng 0,962; ECE 0,441. Giả thiết p ∝ exp(z/T), áp p^k để đổi nhiệt độ hiệu dụng T' = 2,351/k:

| k | T' | ECE | NLL | tin cậy TB |
|---|---|---|---|---|
| 1,0 (đang phục vụ) | 2,35 | 0,441 | 0,705 | 0,524 |
| 2,0 | 1,18 | 0,096 | 0,192 | 0,873 |
| 2,35 (T = 1) | 1,00 | 0,061 | 0,153 | 0,910 |
| 4,0 | 0,59 | 0,023 | 0,117 | 0,968 |

  Chọn k bằng NLL trên 4 fold DEV, áp lên fold thứ 5 (cross-fit): luôn k = 4, **ECE cross-fit 0,023** (n = 237, ước lượng nhiễu vì chỉ 9 lỗi). **Suy luận:** nhiệt độ 2,35 được khớp trên bộ ít lựa chọn của Kev; với 35 lựa chọn tên ngắn xác suất bị dàn mỏng. Sửa bằng một hệ số trên DEV là đủ cho mục đích ngưỡng, và đã khả thi mà không huấn luyện lại. (Thứ hạng `AUROC` 0,961 không đổi khi chỉ làm sắc đều; không tính lại sau biến đổi.) 
- **Thiên vị thứ tự (permute)**: 8,0% tài liệu (19/237) đổi nhãn tùy thứ tự lựa chọn; accuracy theo từng thứ tự trong 6 thứ tự: 0,962; 0,962; 0,954; 0,954; 0,928; 0,975 (chênh 4,7 điểm giữa thứ tự tốt và xấu nhất). Lấy trung bình 6 thứ tự: 0,962 - **không cải thiện**, chỉ ổn định hơn một chút; đổi lại gấp 6 lần số lượt tính.

## 4. Lỗi của Kev (chỉ-tên, DEV): 9/237

Danh sách `doc_id` để người kiểm (`errors_dev.csv` có đủ cột): đúng -> Kev gọi; Qwen3.5 đúng?

| doc_id | đáp án máy | Kev gọi | độ tin cậy | Qwen đúng? |
|---|---|---|---|---|
| 1983c7d32e67 | HO_SO_QUAN_LY_PCCC | CONG_VAN_THONG_BAO | 0,286 | có |
| 7ee3bbfe72eb | HO_SO_QUAN_LY_PCCC | CONG_VAN_THONG_BAO | 0,265 | có |
| c5b05d623858 | HO_SO_QUAN_LY_PCCC | CONG_VAN_THONG_BAO | 0,252 | có |
| 228e06f4536e | DON_DAT_HANG | HD_MUA_BAN | 0,289 | có |
| f8048de5a956 | BB_GIAO_NHAN_HANG_HOA | HD_VAN_CHUYEN | 0,438 | có |
| 920c2d44f32f | GP_VC_HANG_NGUY_HIEM | HD_VAN_CHUYEN | 0,342 | có |
| 6ac314e2f770 | HD_MUA_BAN | OTHER | 0,154 | có |
| bcf218315fa4 | CC_NGHIEP_VU_BVMT | OTHER | 0,134 | có |
| cb8636a17725 | BAN_VE_KY_THUAT | OTHER | 0,151 | **không (cũng OTHER)** |

- **Tập trung hay rải rác?** Rải rác theo biểu mẫu: 9 lỗi, 7 cặp khác nhau; 1 cặp lặp 3 lần; chỉ 2 lỗi thuộc nhóm cùng mẫu (`template_group`), và không nhóm nào có >= 2 lỗi; 42% tài liệu DEV thuộc một nhóm cùng mẫu nhưng chỉ 2/9 lỗi (22%) rơi vào đó (n quá nhỏ để khẳng định khác biệt). Có tập trung ở **mức loại**: `HO_SO_QUAN_LY_PCCC` đúng 4/7, trong khi mọi loại có >= 10 tài liệu đúng >= 93,8%. (Loại này có đúng 7 tài liệu trong DEV; kết luận từng loại chỉ là giai thoại.) **Suy luận:** `CONG_VAN_THONG_BAO` là loại "chung chung" hút các hồ sơ có đầu thư công văn; một mẫu huấn luyện của loại hiếm này có thể sửa, nhưng 7 mẫu là quá ít để biết.
- **Lỗi nào là nhãn máy có thể sai?** Chỉ **`cb8636a17725`** (cả Kev và Qwen đều gọi `OTHER`, đáp án máy là bản vẽ kỹ thuật; ở 02 đây cũng là lỗi duy nhất của Qwen). 8/9 lỗi còn lại Qwen (khác họ) đồng ý với đáp án máy, nên nhiều khả năng lỗi thuộc về Kev. Đề nghị người xem `cb8636a17725` trước.
- Lỗi nguy hiểm (nhãn sai với tin cậy cao) là `f8048de5a956` (0,438, `BB_GIAO_NHAN_HANG_HOA` -> `HD_VAN_CHUYEN`); lỗi kiểu này được chặn nhờ cổng luật và đồng thuận Kev + Qwen (02 §6), không nhờ ngưỡng tin cậy của Kev.

## 5. Lát cắt của tệp ghép (diagnostic)

28 lát đáp án của 8 tệp ghép (cùng một nhà cung cấp, 05): cả `name`, `name_kw`, `perm_name` đúng **27/28 [Wilson 0,823; 0,994]**. Lát sai duy nhất là một `PHIEU_XUAT_KHO` (gọi `HD_MUA_BAN`, hoặc `HD_VAN_CHUYEN` ở permute); **7/7 lát `BB_GIAO_NHAN_HANG_HOA` đúng** (cơ sở TF-IDF/luật ở 05 sai 6/7). n = 28 và một nhà cung cấp: chỉ là chẩn đoán rằng Kev không mắc lỗi riêng của TF-IDF ở đây.

## 6. Dữ liệu tinh chỉnh đã chuẩn bị (KHÔNG huấn luyện)

`build_finetune_dataset.py` -> `_data/` (**gitignore**, chứa văn bản OCR; thêm dòng `.gitignore`), số đếm ở `dataset_manifest.json` (commit, không có văn bản):

| | |
|---|---|
| Tài liệu gốc (DEV, ocr_v2_p12) | 237 (32 loại: 15 loại >= 5 tài liệu = 205 tài liệu; 9 loại 2-4 = 24; 8 loại chỉ 1 tài liệu) |
| Tăng mẫu loại hiếm (cắt từ chính tài liệu: trang 1, 1000 ký tự đầu, bỏ 500 ký tự đầu) | 42 (19 + 17 + 6), mục tiêu 6 bản/loại hiếm, tối đa 3 bản/tài liệu |
| Hard-negative (lựa chọn rút gọn: nhãn đúng + loại hay nhầm + 3 loại nhiễu, thứ tự xáo) | 98, từ 7 cặp nhầm đo ở §4 (hai chiều) + `confusable_with` của taxonomy |
| Tổng số dòng huấn luyện | 377 |
| Fold | 5 fold theo **nhóm** (hợp của nhóm không cắt ở `splits_strict.csv` và `template_group`): 168 nhóm, lớn nhất 18; 47-48 tài liệu gốc/fold; loại hiếm 9/6/15/18/15; **0 nhóm bị tách** giữa các fold; bản tăng mẫu ở cùng fold với tài liệu gốc |
| Độ dài | trung bình ~1.292 token, lớn nhất ~1.984 (ước lượng bằng bộ tách Qwen3.5 cục bộ; giới hạn của trình huấn luyện 2.048/yêu cầu, 0 dòng vượt) |
| TEST | **không có** (assert); nhưng **31 tài liệu DEV chia sẻ nhóm với tài liệu TEST** (cờ `shares_group_with_test`): phải bỏ khỏi huấn luyện nếu sau này chấm TEST |

Định dạng: repo Kev cục bộ (`Z:\projects\kev`, `README.md` mục *Fine-Tune on Your Own Data*, `skills\kev-finetune\references\data-format.md`) cho biết trình huấn luyện `python -m kev.train --data train.jsonl --init_from jaredpalmer/kev-0.8b ...` nhận **một yêu cầu System One mỗi dòng cộng `label`**. Dữ liệu xuất theo đúng định dạng đó: `_data/kev/fold{k}/train.jsonl` (mọi dòng khác fold k, gồm tăng mẫu và hard-negative) và `heldout.jsonl` (chỉ tài liệu gốc của fold k); `question` id `category`, `instructions` = `INSTR_VI`, `criteria` = {mã loại: TÊN loại} - đúng chuỗi lúc suy luận. Dạng trung tính (`text/choices/label` + `kind/fold/group`) ở `_data/neutral.jsonl`. Lưu ý trong tài liệu Kev: trạng thái huấn luyện chủ yếu <= 384 token, bản tinh chỉnh tài liệu tới 7.552 token; của ta ~1.300 token, nên đây là lệch phân phối đáng lưu ý (xem FINETUNE_PLAN).

## 7. Hạn chế

- DEV chỉ 237 tài liệu, 9 lỗi; mọi so sánh "lỗi tập trung" dựa vào vài điểm dữ liệu. 17/32 loại trong DEV chỉ có 1-4 tài liệu: không đo được tinh chỉnh cho chúng bằng nhóm-fold (loại 1 tài liệu luôn nằm trọn trong fold giữ ra).
- Nhãn do máy; vòng tròn nhãn/mô tả (02 §3). `name_kw` dùng từ khóa viết sau khi xem tài liệu.
- Độ trễ đo khi GPU dùng chung, các lượt đo khác thời điểm.
- Hệ số làm sắc (k = 4) chọn trên DEV, chưa kiểm trên TEST; TEST **không chạy** và cũng không có cấu hình nào được đóng băng cho TEST (không có `dev_selection.json` vì không chạy TEST).
- Không đo Kev-4B (đổi mô hình toàn cục của máy chủ dùng chung; không có quyền).
