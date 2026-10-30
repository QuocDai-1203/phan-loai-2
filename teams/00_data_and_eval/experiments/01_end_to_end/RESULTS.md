# 01 - End-to-end: tách trang rồi phân loại, đo theo TỆP (CP3), kèm chuỗi trích xuất ngày hết hạn

> Viết cho sinh viên năm cuối ngành AI. Mọi con số trong tệp này do các lệnh ở mục "Lệnh" sinh ra (tệp này được ghép bằng `run.py --stage assemble` từ `results/dev_report.md`, `results/test_report.md` và `notes.md`). **Đáp án ranh giới và loại là đáp án máy (`boundary_gold_v0.csv`, `labels_v2.csv`), chưa có người của công ty kiểm.**

## Tóm tắt (đọc mục này trước)

* **Câu hỏi.** Các thí nghiệm trước đo từng khâu riêng lẻ. Khi nối khâu tách trang với cascade phân loại, tách có làm hệ thống tốt lên hay tệ đi **trên cơ cấu tệp thật** (92% tệp là tài liệu đơn hoặc nhiều trang không ghép; composite chỉ ~7%)?
* **Trả lời trên dev (n = 245 tệp duy nhất).** Tách trang **không làm tăng** tỉ lệ *tệp đúng hoàn toàn* so với không tách (S0 = 92,3%). Biến thể tốt nhất chỉ **ngang** S0 (S10: 91,9%, hiệu −0,4 điểm, CI ghép cặp [−2,9; +1,9] chứa 0: "không tách được"). Luật cũ và luật v2 **làm hại** rõ rệt (S1 53,4%, S2 67,5%: tách vụn 104/155 và 70/155 tệp nhiều trang vốn đúng khi để nguyên). Điểm khác nằm ở cấp **tài liệu**: tách đúng giao thêm tài liệu của tệp ghép (S10: 279/318 tài liệu đáp án giao đúng và tự động = 87,7% so với 70,4% của S0; hiệu +17,3 điểm, CI [+5,0; +29,4]) và giảm tỉ lệ **sai lặng lẽ** (tự xử lý mà sai) từ 7,3% xuống 4,9% của tổng số tệp (hiệu −2,4 điểm, CI [−3,8; −1,1]).
* **Mặc định chọn trên dev: S10 = `model+merge`** (bộ phân loại cặp trang, ngưỡng 0,7, rồi gộp lát cắt liền kề được phân loại cùng loại, trừ loại "một tờ = một tài liệu" `BB_LAY_MAU` và trừ ranh giới có điểm >= 0,99). Quy tắc chọn ở mục "Lưới chọn tham số". Đã đóng băng trước khi chấm TEST.
* **TEST (59 tệp, chấm MỘT lần):** S10 và S0 cùng 56/59 tệp đúng hoàn toàn (94,9%, không tách được); S10 giao đúng 65/68 tài liệu so với 56/68 của S0. TEST chỉ có 2 tệp composite (cả hai là `BB_LAY_MAU`), nên không kết luận được gì về composite khác loại.
* **Không biến thể nào đạt mục tiêu sai lặng lẽ <= 1%** trên dev (S10: 4,9% tổng số tệp; chỉ các biến thể đẩy nhiều tệp về người, S8 và S9, xuống dưới 2%). Điểm nghẽn của composite khác loại **không phải tách mà là phân loại lát cắt**: dù tách đúng 8/8 (S3), chỉ 2/8 tệp đúng loại cho mọi tài liệu vì biên bản giao nhận bị gán `PHIEU_XUAT_KHO` (6/7 lần).
* **Chuỗi tới ngày hết hạn** (82 đơn vị dev có schema; mục cuối): loại đúng 82/82, hạn đúng-và-tự-nhận 32/66, **sai 0**, không mất gì so với chạy tách biệt; nhưng tự nhận chỉ 48% (so với 58% ở thí nghiệm trích xuất) vì pipeline chưa đưa ảnh trang cho nguồn VLM.

## Thiết lập

* **Đơn vị** = tệp (tài liệu duy nhất; bản sao byte-giống-hệt đã gộp). Văn bản = `data/ocr_v2.jsonl` (OCR cục bộ, **không OCR lại**), tối đa 30 trang/tệp; tệp 93 trang chỉ chấm 30 trang đầu (đáp án cắt ở trang có văn bản).
* **Phạm vi dev** = `DEV` + `EXCLUDED_COMPOSITE` (245 tệp: 71 tệp 1 trang, 155 nhiều trang không ghép, 8 composite khác loại, 6 composite cùng loại ngoài `BB_LAY_MAU`, 5 `BB_LAY_MAU`). **TEST** = 59 tệp (21 / 36 / 0 / 0 / 2), mở đúng một lần ở `--stage test --final-test`.
* **Chia dữ liệu và nhãn:** `data/splits/splits.csv` (đã khóa), `data/labels_v2.csv` (sha1[:10] `eb3348713a`), đáp án ranh giới `teams/team2_splitting/gold/boundary_gold_v0.csv`. Đáp án `segments` do một annotator AI xem đủ trang; **chưa người kiểm** (xem `teams/team2_splitting/gold/README.md`).
* **Vệ sinh chống rò rỉ.** Không thành phần nào được chấm trên tệp nó đã học hoặc cùng nhóm biểu mẫu: (1) điểm cặp trang là **cross-fitted** (5 fold theo nhóm biểu mẫu, gộp 5 bộ chứng từ BSR một nhóm; mã `teams/team2_splitting/cvlib.py`, không dùng `models/*.joblib`); (2) TF-IDF của cascade huấn luyện lại **theo fold DEV** như `03_src_cascade` (8 composite khác loại, không thuộc DEV, dùng mô hình huấn luyện trên DEV bỏ các tài liệu cùng `group`); (3) LLM phân loại và luật không huấn luyện. Ngưỡng `th_s`, `th_llm` của cascade đã được chọn trên DEV ở thí nghiệm 02 (đúng như phần "dev" của các thí nghiệm trước). Kiểm: S0 trùng bộ ba (tầng, nhãn) với `03_src_cascade` trên 237/237 tài liệu DEV (cuối mục "Lưới chọn tham số"). Với TEST: điểm cặp trang từ mô hình huấn luyện trên toàn dev, TF-IDF = artefact `models/classification/...` (huấn luyện trên DEV).
* **Cơ cấu tệp thật.** Tỉ trọng nhóm lấy theo kho mẫu 304 tệp duy nhất (1 trang 30,3%; nhiều trang không ghép 62,8%; composite khác loại 2,6%; cùng loại ngoài BB_LAY_MAU 2,0%; BB_LAY_MAU 2,3%). "Toàn bộ, theo cơ cấu tệp thật" = trung bình có trọng số các tỉ lệ nhóm; CI = bootstrap phân tầng (2000 lần, lấy mẫu lại TỆP trong từng nhóm, seed `BOOT_SEED`), so sánh ghép cặp dùng cùng chỉ số lấy mẫu. **Ô theo nhóm dùng khoảng Clopper-Pearson** (bootstrap suy biến thành [0;0] khi k = 0 hoặc n); CI "toàn bộ" vì thế **hẹp giả** khi các nhóm composite quan sát 0/n (nhóm composite nặng ~6,9% tổng trọng số, tỉ lệ thật của chúng có thể tới 37-52% theo cận trên Clopper-Pearson).
* **Chỉ số.** (a) tách đúng hoàn toàn: các lát cắt = đúng các segment đáp án; (b) mọi segment đáp án khớp lát cắt trùng nhiều trang nhất và lát cắt đó được **tự nhận đúng loại** (bị từ chối về người tính là chưa đúng); (c) tệp đúng hoàn toàn = (a) ∧ (b); (d) *tự xử lý hoàn toàn* = mọi lát cắt được tự nhận (và, với biến thể có định tuyến, bộ tách không "không chắc"); *sai lặng lẽ* = tự xử lý mà (c) sai; (e) hại so với S0 = số tệp S0 đúng mà biến thể làm hỏng / số tệp S0 sai mà biến thể sửa. Thêm cấp **tài liệu**: một tài liệu đáp án "giao đúng và tự động" khi có lát cắt đúng khoảng trang đó, được tự nhận đúng loại, trong tệp tự xử lý hoàn toàn.
* **Ghi chú** viết "không tách được" khi CI của hiệu chứa 0.

## Các biến thể

| | Mô tả |
|---|---|
| S0 | không tách: cả tệp là một tài liệu (hiện trạng của các thí nghiệm phân loại) |
| S1 / S2 | `split_document` method `rule` (luật cũ) / `rule_v2` |
| S3 | `model` (bộ phân loại cặp trang c2), ngưỡng 0,5 |
| S4 | S3 + **gộp lát cắt liền kề được phân loại cùng loại**, trừ loại một-tờ (`BB_LAY_MAU`, suy ra từ mô tả taxonomy "Mỗi biên bản dài MỘT trang", `src/splitting/type_merge.py`) |
| S5 | S2 + gộp cùng loại |
| S6 | `model` với **ngưỡng cao hơn chọn trên dev** (hiệu chỉnh 2: chỉ nhận ranh giới trên ngưỡng) |
| S7 | S6 cách chọn nhưng có gộp cùng loại |
| S10 | `model` ngưỡng 0,7 + gộp cùng loại **trừ ranh giới điểm >= 0,99** (bộ tách rất chắc thì tin bộ tách) |
| S8 | S7 + tệp có điểm cặp trang trong một dải "không chắc" -> chuyển người (định tuyến 1) |
| S9 | **không tách**; tệp có điểm cặp trang >= cờ -> chuyển người "nghi composite" (định tuyến 2, chế độ `triage`) |

(Tên S10 giữ nguyên vì sinh sau S1-S9 trong lúc thiết kế; S8 xây trên S7, tức ngưỡng cao.)

## Lệnh (từ gốc repo; Windows, `.venv`)

```powershell
$py = ".venv\Scripts\python.exe"; $d = "teams/00_data_and_eval/experiments/01_end_to_end"
& $py -X utf8 $d/run.py --stage dev                      # đếm lời gọi LLM thiếu; thêm --call-llm để gọi Ollama (qua cache đĩa), ~10 phút, 111 văn bản mới
& $py -X utf8 $d/run.py --stage test --final-test --call-llm     # MỘT lần; sổ đăng ký test_run_registry.json chặn lần hai
& $py -X utf8 $d/run.py --stage assemble                  # ghép RESULTS.md
& $py -X utf8 $d/cost_sample.py                           # chi phí qua lớp pipeline thật, 20 tệp, 3 chính sách
& $py -X utf8 $d/cost_sample_extract.py                   # độ trễ theo tệp CÓ trích xuất, 14 tệp
& $py -X utf8 $d/stall_analysis.py                        # độ trễ lời gọi Ollama trong các cache (vì sao 195 s)
& $py -X utf8 $d/chain_extraction.py                      # chuỗi tách -> loại -> trích xuất -> hạn, 82 đơn vị dev
```
Đầu ra: `dev_selection.json` (lựa chọn đóng băng), `test_run_registry.json`, `results/*.md|json` và `per_file_*.csv` (**chứa `doc_id`, chỉ dùng nội bộ**). Sổ đăng ký TEST là sổ riêng của thí nghiệm này (cơ chế của `03_src_cascade/test_run_registry.json` là một tệp một lần chạy, nên ở đây tạo tệp cùng kiểu); lần mở TEST này **khác** lần mở TEST phân loại ở 02/03 (đo chuỗi, không đo lại phân loại).


## Kết quả trên phạm vi dev (n = 245 tệp: tệp 1 trang 71, nhiều trang, không ghép 155, composite khác loại 8, composite cùng loại (ngoài BB_LAY_MAU) 6, BB_LAY_MAU 5)

**(c) Tệp đúng hoàn toàn = (a) tách đúng ∧ (b) mọi tài liệu đáp án có đúng loại**

| biến thể | tệp 1 trang (n=71) | nhiều trang, không ghép (n=155) | composite khác loại (n=8) | composite cùng loại (ngoài BB_LAY_MAU) (n=6) | BB_LAY_MAU (n=5) | **toàn bộ, theo cơ cấu tệp thật** |
|---|---|---|---|---|---|---|
| S0 (không tách (cả tệp = một tài liệu)) | 70/71 = 99% [92%; 100%] | 154/155 = 99% [96%; 100%] | 0/8 = 0% [0%; 37%] | 0/6 = 0% [0%; 46%] | 0/5 = 0% [0%; 52%] | **92,3% [91,0%; 93,1%]** |
| S1 (luật cũ) | 70/71 = 99% [92%; 100%] | 50/155 = 32% [25%; 40%] | 1/8 = 12% [0%; 53%] | 2/6 = 33% [4%; 78%] | 5/5 = 100% [48%; 100%] | **53,4% [48,7%; 58,1%]** |
| S2 (luật v2) | 70/71 = 99% [92%; 100%] | 84/155 = 54% [46%; 62%] | 2/8 = 25% [3%; 65%] | 2/6 = 33% [4%; 78%] | 5/5 = 100% [48%; 100%] | **67,5% [62,7%; 72,8%]** |
| S3 (mô hình cặp trang, ngưỡng 0,5) | 70/71 = 99% [92%; 100%] | 128/155 = 83% [76%; 88%] | 2/8 = 25% [3%; 65%] | 2/6 = 33% [4%; 78%] | 4/5 = 80% [28%; 99%] | **84,9% [80,6%; 88,8%]** |
| S4 (S3 + gộp lát cắt liền kề cùng loại (trừ loại một-tờ)) | 70/71 = 99% [92%; 100%] | 144/155 = 93% [88%; 96%] | 2/8 = 25% [3%; 65%] | 0/6 = 0% [0%; 46%] | 4/5 = 80% [28%; 99%] | **90,7% [87,8%; 93,5%]** |
| S5 (S2 + gộp lát cắt liền kề cùng loại) | 70/71 = 99% [92%; 100%] | 138/155 = 89% [83%; 93%] | 2/8 = 25% [3%; 65%] | 0/6 = 0% [0%; 46%] | 5/5 = 100% [48%; 100%] | **88,7% [85,5%; 92,0%]** |
| S6 (mô hình, ngưỡng tau6=0.98 chọn trên dev) | 70/71 = 99% [92%; 100%] | 151/155 = 97% [94%; 99%] | 1/8 = 12% [0%; 53%] | 0/6 = 0% [0%; 46%] | 0/5 = 0% [0%; 52%] | **91,4% [89,4%; 93,2%]** |
| S7 (mô hình, ngưỡng tau7=0.98 + gộp cùng loại) | 70/71 = 99% [92%; 100%] | 153/155 = 99% [95%; 100%] | 1/8 = 12% [0%; 53%] | 0/6 = 0% [0%; 46%] | 0/5 = 0% [0%; 52%] | **92,2% [90,6%; 93,4%]** |
| S10 (mô hình tau=0.7 + gộp cùng loại TRỪ ranh giới có điểm >= 0.99) | 70/71 = 99% [92%; 100%] | 148/155 = 95% [91%; 98%] | 2/8 = 25% [3%; 65%] | 0/6 = 0% [0%; 46%] | 3/5 = 60% [15%; 95%] | **91,9% [89,2%; 94,4%]** |
| S8 (S7 + tệp có điểm cặp trang trong [0.05; 0.95) -> người (splitter không chắc)) | 70/71 = 99% [92%; 100%] | 153/155 = 99% [95%; 100%] | 1/8 = 12% [0%; 53%] | 0/6 = 0% [0%; 46%] | 0/5 = 0% [0%; 52%] | **92,2% [90,6%; 93,4%]** |
| S9 (không tách; tệp có điểm cặp trang >= 0.3 -> người (nghi composite)) | 70/71 = 99% [92%; 100%] | 154/155 = 99% [96%; 100%] | 0/8 = 0% [0%; 37%] | 0/6 = 0% [0%; 46%] | 0/5 = 0% [0%; 52%] | **92,3% [91,0%; 93,1%]** |

**(a) Tách đúng hoàn toàn (các lát cắt = đúng các segment đáp án)**

| biến thể | tệp 1 trang (n=71) | nhiều trang, không ghép (n=155) | composite khác loại (n=8) | composite cùng loại (ngoài BB_LAY_MAU) (n=6) | BB_LAY_MAU (n=5) | **toàn bộ, theo cơ cấu tệp thật** |
|---|---|---|---|---|---|---|
| S0 (không tách (cả tệp = một tài liệu)) | 71/71 = 100% [95%; 100%] | 155/155 = 100% [98%; 100%] | 0/8 = 0% [0%; 37%] | 0/6 = 0% [0%; 46%] | 0/5 = 0% [0%; 52%] | **93,1% [93,1%; 93,1%]** |
| S1 (luật cũ) | 71/71 = 100% [95%; 100%] | 50/155 = 32% [25%; 40%] | 5/8 = 62% [24%; 91%] | 2/6 = 33% [4%; 78%] | 5/5 = 100% [48%; 100%] | **55,1% [50,4%; 59,7%]** |
| S2 (luật v2) | 71/71 = 100% [95%; 100%] | 85/155 = 55% [47%; 63%] | 7/8 = 88% [47%; 100%] | 2/6 = 33% [4%; 78%] | 5/5 = 100% [48%; 100%] | **70,0% [65,1%; 75,3%]** |
| S3 (mô hình cặp trang, ngưỡng 0,5) | 71/71 = 100% [95%; 100%] | 129/155 = 83% [76%; 89%] | 8/8 = 100% [63%; 100%] | 2/6 = 33% [4%; 78%] | 4/5 = 80% [28%; 99%] | **87,7% [83,6%; 91,5%]** |
| S4 (S3 + gộp lát cắt liền kề cùng loại (trừ loại một-tờ)) | 71/71 = 100% [95%; 100%] | 145/155 = 94% [88%; 97%] | 3/8 = 38% [9%; 76%] | 0/6 = 0% [0%; 46%] | 4/5 = 80% [28%; 99%] | **91,9% [89,0%; 94,4%]** |
| S5 (S2 + gộp lát cắt liền kề cùng loại) | 71/71 = 100% [95%; 100%] | 139/155 = 90% [84%; 94%] | 3/8 = 38% [9%; 76%] | 0/6 = 0% [0%; 46%] | 5/5 = 100% [48%; 100%] | **89,9% [86,7%; 93,0%]** |
| S6 (mô hình, ngưỡng tau6=0.98 chọn trên dev) | 71/71 = 100% [95%; 100%] | 152/155 = 98% [94%; 100%] | 6/8 = 75% [35%; 97%] | 0/6 = 0% [0%; 46%] | 0/5 = 0% [0%; 52%] | **93,8% [92,2%; 95,3%]** |
| S7 (mô hình, ngưỡng tau7=0.98 + gộp cùng loại) | 71/71 = 100% [95%; 100%] | 154/155 = 99% [96%; 100%] | 2/8 = 25% [3%; 65%] | 0/6 = 0% [0%; 46%] | 0/5 = 0% [0%; 52%] | **93,3% [92,2%; 94,4%]** |
| S10 (mô hình tau=0.7 + gộp cùng loại TRỪ ranh giới có điểm >= 0.99) | 71/71 = 100% [95%; 100%] | 149/155 = 96% [92%; 99%] | 7/8 = 88% [47%; 100%] | 0/6 = 0% [0%; 46%] | 3/5 = 60% [15%; 95%] | **94,3% [91,9%; 96,4%]** |
| S8 (S7 + tệp có điểm cặp trang trong [0.05; 0.95) -> người (splitter không chắc)) | 71/71 = 100% [95%; 100%] | 154/155 = 99% [96%; 100%] | 2/8 = 25% [3%; 65%] | 0/6 = 0% [0%; 46%] | 0/5 = 0% [0%; 52%] | **93,3% [92,2%; 94,4%]** |
| S9 (không tách; tệp có điểm cặp trang >= 0.3 -> người (nghi composite)) | 71/71 = 100% [95%; 100%] | 155/155 = 100% [98%; 100%] | 0/8 = 0% [0%; 37%] | 0/6 = 0% [0%; 46%] | 0/5 = 0% [0%; 52%] | **93,1% [93,1%; 93,1%]** |

**(b) Mọi segment đáp án khớp một lát cắt (trùng nhiều trang nhất) được TỰ NHẬN đúng loại**

| biến thể | tệp 1 trang (n=71) | nhiều trang, không ghép (n=155) | composite khác loại (n=8) | composite cùng loại (ngoài BB_LAY_MAU) (n=6) | BB_LAY_MAU (n=5) | **toàn bộ, theo cơ cấu tệp thật** |
|---|---|---|---|---|---|---|
| S0 (không tách (cả tệp = một tài liệu)) | 70/71 = 99% [92%; 100%] | 154/155 = 99% [96%; 100%] | 0/8 = 0% [0%; 37%] | 6/6 = 100% [54%; 100%] | 5/5 = 100% [48%; 100%] | **96,5% [95,3%; 97,4%]** |
| S1 (luật cũ) | 70/71 = 99% [92%; 100%] | 151/155 = 97% [94%; 99%] | 2/8 = 25% [3%; 65%] | 6/6 = 100% [54%; 100%] | 5/5 = 100% [48%; 100%] | **96,0% [94,0%; 97,8%]** |
| S2 (luật v2) | 70/71 = 99% [92%; 100%] | 146/155 = 94% [89%; 97%] | 2/8 = 25% [3%; 65%] | 6/6 = 100% [54%; 100%] | 5/5 = 100% [48%; 100%] | **94,0% [91,4%; 96,4%]** |
| S3 (mô hình cặp trang, ngưỡng 0,5) | 70/71 = 99% [92%; 100%] | 153/155 = 99% [95%; 100%] | 2/8 = 25% [3%; 65%] | 6/6 = 100% [54%; 100%] | 5/5 = 100% [48%; 100%] | **96,8% [95,2%; 98,3%]** |
| S4 (S3 + gộp lát cắt liền kề cùng loại (trừ loại một-tờ)) | 70/71 = 99% [92%; 100%] | 153/155 = 99% [95%; 100%] | 2/8 = 25% [3%; 65%] | 6/6 = 100% [54%; 100%] | 5/5 = 100% [48%; 100%] | **96,8% [95,2%; 98,3%]** |
| S5 (S2 + gộp lát cắt liền kề cùng loại) | 70/71 = 99% [92%; 100%] | 147/155 = 95% [90%; 98%] | 2/8 = 25% [3%; 65%] | 6/6 = 100% [54%; 100%] | 5/5 = 100% [48%; 100%] | **94,4% [91,9%; 96,7%]** |
| S6 (mô hình, ngưỡng tau6=0.98 chọn trên dev) | 70/71 = 99% [92%; 100%] | 154/155 = 99% [96%; 100%] | 1/8 = 12% [0%; 53%] | 6/6 = 100% [54%; 100%] | 5/5 = 100% [48%; 100%] | **96,9% [95,6%; 98,0%]** |
| S7 (mô hình, ngưỡng tau7=0.98 + gộp cùng loại) | 70/71 = 99% [92%; 100%] | 154/155 = 99% [96%; 100%] | 1/8 = 12% [0%; 53%] | 6/6 = 100% [54%; 100%] | 5/5 = 100% [48%; 100%] | **96,9% [95,6%; 98,0%]** |
| S10 (mô hình tau=0.7 + gộp cùng loại TRỪ ranh giới có điểm >= 0.99) | 70/71 = 99% [92%; 100%] | 153/155 = 99% [95%; 100%] | 2/8 = 25% [3%; 65%] | 6/6 = 100% [54%; 100%] | 5/5 = 100% [48%; 100%] | **96,8% [95,2%; 98,4%]** |
| S8 (S7 + tệp có điểm cặp trang trong [0.05; 0.95) -> người (splitter không chắc)) | 70/71 = 99% [92%; 100%] | 154/155 = 99% [96%; 100%] | 1/8 = 12% [0%; 53%] | 6/6 = 100% [54%; 100%] | 5/5 = 100% [48%; 100%] | **96,9% [95,6%; 98,0%]** |
| S9 (không tách; tệp có điểm cặp trang >= 0.3 -> người (nghi composite)) | 70/71 = 99% [92%; 100%] | 154/155 = 99% [96%; 100%] | 0/8 = 0% [0%; 37%] | 6/6 = 100% [54%; 100%] | 5/5 = 100% [48%; 100%] | **96,5% [95,3%; 97,4%]** |

### (d) Định tuyến: tự xử lý hoàn toàn và sai lặng lẽ

| biến thể | tự xử lý hoàn toàn | tự xử lý VÀ đúng | sai lặng lẽ (tự xử lý mà sai) | sai lặng lẽ / tự xử lý | thô: tự xử lý / tệp | thô: sai / tự xử lý (Clopper-Pearson 95%) |
|---|---|---|---|---|---|---|
| S0 (không tách (cả tệp = một tài liệu)) | 99,6% [98,7%; 100,0%] | 92,3% [91,0%; 93,1%] | 7,31% [6,91%; 8,12%] | 7,34% [6,91%; 8,19%] | 244/245 | 20/244 = 8,20% [5,08%; 12,38%] |
| S1 (luật cũ) | 92,8% [89,4%; 95,9%] | 53,4% [48,7%; 58,1%] | 39,37% [34,25%; 44,23%] | 42,44% [37,42%; 47,37%] | 227/245 | 99/227 = 43,61% [37,06%; 50,33%] |
| S2 (luật v2) | 95,9% [93,5%; 98,4%] | 67,5% [62,7%; 72,8%] | 28,42% [23,56%; 33,13%] | 29,63% [24,50%; 34,55%] | 235/245 | 72/235 = 30,64% [24,81%; 36,96%] |
| S3 (mô hình cặp trang, ngưỡng 0,5) | 96,4% [94,0%; 98,5%] | 84,9% [80,6%; 88,8%] | 11,53% [7,96%; 15,43%] | 11,96% [8,19%; 15,96%] | 236/245 | 30/236 = 12,71% [8,74%; 17,65%] |
| S4 (S3 + gộp lát cắt liền kề cùng loại (trừ loại một-tờ)) | 96,4% [94,0%; 98,5%] | 90,7% [87,8%; 93,5%] | 5,70% [3,77%; 7,74%] | 5,91% [3,91%; 8,05%] | 236/245 | 16/236 = 6,78% [3,92%; 10,78%] |
| S5 (S2 + gộp lát cắt liền kề cùng loại) | 95,9% [93,5%; 98,4%] | 88,7% [85,5%; 92,0%] | 7,19% [4,91%; 9,55%] | 7,50% [5,08%; 9,99%] | 235/245 | 20/235 = 8,51% [5,28%; 12,84%] |
| S6 (mô hình, ngưỡng tau6=0.98 chọn trên dev) | 99,2% [97,9%; 100,0%] | 91,4% [89,4%; 93,2%] | 7,79% [6,33%; 9,34%] | 7,86% [6,41%; 9,46%] | 243/245 | 21/243 = 8,64% [5,43%; 12,91%] |
| S7 (mô hình, ngưỡng tau7=0.98 + gộp cùng loại) | 99,2% [97,9%; 100,0%] | 92,2% [90,6%; 93,4%] | 6,98% [5,92%; 8,12%] | 7,04% [6,02%; 8,16%] | 243/245 | 19/243 = 7,82% [4,77%; 11,94%] |
| S10 (mô hình tau=0.7 + gộp cùng loại TRỪ ranh giới có điểm >= 0.99) | 96,8% [94,4%; 98,8%] | 91,9% [89,2%; 94,4%] | 4,94% [3,37%; 6,49%] | 5,11% [3,48%; 6,69%] | 237/245 | 14/237 = 5,91% [3,27%; 9,71%] |
| S8 (S7 + tệp có điểm cặp trang trong [0.05; 0.95) -> người (splitter không chắc)) | 61,7% [56,8%; 66,8%] | 59,8% [54,9%; 64,7%] | 1,97% [0,99%; 2,96%] | 3,20% [1,51%; 5,04%] | 150/245 | 6/150 = 4,00% [1,48%; 8,50%] |
| S9 (không tách; tệp có điểm cặp trang >= 0.3 -> người (nghi composite)) | 77,9% [73,1%; 82,3%] | 76,5% [72,0%; 80,9%] | 1,45% [0,33%; 2,57%] | 1,86% [0,43%; 3,30%] | 189/245 | 4/189 = 2,12% [0,58%; 5,33%] |

### Cấp tài liệu (cho thấy thứ mà file-level che giấu)

| biến thể | tài liệu đáp án giao ĐÚNG và tự động | tài liệu đáp án (tổng) | trong đó của các nhóm composite (n tài liệu) |
|---|---|---|---|
| S0 (không tách (cả tệp = một tài liệu)) | 224/318 = 70,4% [56,3%; 84,7%] | 318 | 0/92 |
| S1 (luật cũ) | 195/318 = 61,3% [52,3%; 69,8%] | 318 | 75/92 |
| S2 (luật v2) | 232/318 = 73,0% [65,8%; 79,4%] | 318 | 78/92 |
| S3 (mô hình cặp trang, ngưỡng 0,5) | 273/318 = 85,8% [80,6%; 90,3%] | 318 | 75/92 |
| S4 (S3 + gộp lát cắt liền kề cùng loại (trừ loại một-tờ)) | 279/318 = 87,7% [82,3%; 92,5%] | 318 | 65/92 |
| S5 (S2 + gộp lát cắt liền kề cùng loại) | 276/318 = 86,8% [81,4%; 91,7%] | 318 | 68/92 |
| S6 (mô hình, ngưỡng tau6=0.98 chọn trên dev) | 241/318 = 75,8% [61,4%; 89,2%] | 318 | 20/92 |
| S7 (mô hình, ngưỡng tau7=0.98 + gộp cùng loại) | 239/318 = 75,2% [60,9%; 88,9%] | 318 | 16/92 |
| S10 (mô hình tau=0.7 + gộp cùng loại TRỪ ranh giới có điểm >= 0.99) | 279/318 = 87,7% [83,2%; 92,6%] | 318 | 61/92 |
| S8 (S7 + tệp có điểm cặp trang trong [0.05; 0.95) -> người (splitter không chắc)) | 153/318 = 48,1% [38,1%; 58,7%] | 318 | 10/92 |
| S9 (không tách; tệp có điểm cặp trang >= 0.3 -> người (nghi composite)) | 185/318 = 58,2% [46,2%; 70,8%] | 318 | 0/92 |

### (e) Phân tích hại so với S0

Mỗi ô: (tệp S0 đúng hoàn toàn mà biến thể làm hỏng) hỏng / (tệp S0 sai mà biến thể sửa được) sửa.

| biến thể | tệp 1 trang | nhiều trang, không ghép | composite khác loại | composite cùng loại (ngoài BB_LAY_MAU) | BB_LAY_MAU | hiệu có trọng số (biến thể - S0) của (c), CI ghép cặp | kết luận |
|---|---|---|---|---|---|---|---|
| S1 (luật cũ) | 0 hỏng / 0 sửa | 104 hỏng / 0 sửa | 0 hỏng / 1 sửa | 0 hỏng / 2 sửa | 0 hỏng / 5 sửa | -38.9 điểm [-43.6; -34.3] | tách được: kém hơn |
| S2 (luật v2) | 0 hỏng / 0 sửa | 70 hỏng / 0 sửa | 0 hỏng / 2 sửa | 0 hỏng / 2 sửa | 0 hỏng / 5 sửa | -24.8 điểm [-29.6; -19.4] | tách được: kém hơn |
| S3 (mô hình cặp trang, ngưỡng 0,5) | 0 hỏng / 0 sửa | 26 hỏng / 0 sửa | 0 hỏng / 2 sửa | 0 hỏng / 2 sửa | 0 hỏng / 4 sửa | -7.4 điểm [-11.5; -3.6] | tách được: kém hơn |
| S4 (S3 + gộp lát cắt liền kề cùng loại (trừ loại một-tờ)) | 0 hỏng / 0 sửa | 10 hỏng / 0 sửa | 0 hỏng / 2 sửa | 0 hỏng / 0 sửa | 0 hỏng / 4 sửa | -1.6 điểm [-4.3; +0.9] | không tách được |
| S5 (S2 + gộp lát cắt liền kề cùng loại) | 0 hỏng / 0 sửa | 16 hỏng / 0 sửa | 0 hỏng / 2 sửa | 0 hỏng / 0 sửa | 0 hỏng / 5 sửa | -3.5 điểm [-6.7; -0.5] | tách được: kém hơn |
| S6 (mô hình, ngưỡng tau6=0.98 chọn trên dev) | 0 hỏng / 0 sửa | 3 hỏng / 0 sửa | 0 hỏng / 1 sửa | 0 hỏng / 0 sửa | 0 hỏng / 0 sửa | -0.9 điểm [-2.4; +0.5] | không tách được |
| S7 (mô hình, ngưỡng tau7=0.98 + gộp cùng loại) | 0 hỏng / 0 sửa | 1 hỏng / 0 sửa | 0 hỏng / 1 sửa | 0 hỏng / 0 sửa | 0 hỏng / 0 sửa | -0.1 điểm [-1.2; +1.0] | không tách được |
| S10 (mô hình tau=0.7 + gộp cùng loại TRỪ ranh giới có điểm >= 0.99) | 0 hỏng / 0 sửa | 6 hỏng / 0 sửa | 0 hỏng / 2 sửa | 0 hỏng / 0 sửa | 0 hỏng / 3 sửa | -0.4 điểm [-2.9; +1.9] | không tách được |
| S8 (S7 + tệp có điểm cặp trang trong [0.05; 0.95) -> người (splitter không chắc)) | 0 hỏng / 0 sửa | 1 hỏng / 0 sửa | 0 hỏng / 1 sửa | 0 hỏng / 0 sửa | 0 hỏng / 0 sửa | -0.1 điểm [-1.2; +1.0] | không tách được |
| S9 (không tách; tệp có điểm cặp trang >= 0.3 -> người (nghi composite)) | 0 hỏng / 0 sửa | 0 hỏng / 0 sửa | 0 hỏng / 0 sửa | 0 hỏng / 0 sửa | 0 hỏng / 0 sửa | +0.0 điểm [+0.0; +0.0] | không tách được |

### Số lời gọi LLM và số lát cắt mỗi tệp

| biến thể | tệp 1 trang | nhiều trang, không ghép | composite khác loại | composite cùng loại (ngoài BB_LAY_MAU) | BB_LAY_MAU | tổng lời gọi LLM / tổng lát cắt |
|---|---|---|---|---|---|---|
| S0 (không tách (cả tệp = một tài liệu)) | 0.06 LLM, 1.00 lát | 0.04 LLM, 1.00 lát | 0.12 LLM, 1.00 lát | 0.50 LLM, 1.00 lát | 0.00 LLM, 1.00 lát | 14 / 245 |
| S1 (luật cũ) | 0.06 LLM, 1.00 lát | 0.63 LLM, 2.51 lát | 0.38 LLM, 3.62 lát | 0.83 LLM, 2.00 lát | 0.00 LLM, 10.20 lát | 110 / 552 |
| S2 (luật v2) | 0.06 LLM, 1.00 lát | 0.55 LLM, 1.97 lát | 0.25 LLM, 3.38 lát | 0.67 LLM, 1.83 lát | 0.00 LLM, 10.20 lát | 95 / 466 |
| S3 (mô hình cặp trang, ngưỡng 0,5) | 0.06 LLM, 1.00 lát | 0.25 LLM, 1.31 lát | 0.25 LLM, 3.50 lát | 0.83 LLM, 1.83 lát | 0.00 LLM, 9.80 lát | 49 / 362 |
| S4 (S3 + gộp lát cắt liền kề cùng loại (trừ loại một-tờ)) | 0.06 LLM, 1.00 lát | 0.25 LLM, 1.12 lát | 0.25 LLM, 2.88 lát | 0.83 LLM, 1.17 lát | 0.00 LLM, 9.80 lát | 49 / 323 |
| S5 (S2 + gộp lát cắt liền kề cùng loại) | 0.06 LLM, 1.00 lát | 0.55 LLM, 1.39 lát | 0.25 LLM, 2.88 lát | 0.67 LLM, 1.00 lát | 0.00 LLM, 10.20 lát | 95 / 366 |
| S6 (mô hình, ngưỡng tau6=0.98 chọn trên dev) | 0.06 LLM, 1.00 lát | 0.05 LLM, 1.02 lát | 0.12 LLM, 3.25 lát | 0.50 LLM, 1.00 lát | 0.00 LLM, 1.40 lát | 15 / 268 |
| S7 (mô hình, ngưỡng tau7=0.98 + gộp cùng loại) | 0.06 LLM, 1.00 lát | 0.05 LLM, 1.01 lát | 0.12 LLM, 2.75 lát | 0.50 LLM, 1.00 lát | 0.00 LLM, 1.40 lát | 15 / 262 |
| S10 (mô hình tau=0.7 + gộp cùng loại TRỪ ranh giới có điểm >= 0.99) | 0.06 LLM, 1.00 lát | 0.15 LLM, 1.06 lát | 0.25 LLM, 3.38 lát | 0.83 LLM, 1.17 lát | 0.00 LLM, 9.00 lát | 35 / 314 |
| S8 (S7 + tệp có điểm cặp trang trong [0.05; 0.95) -> người (splitter không chắc)) | 0.06 LLM, 1.00 lát | 0.05 LLM, 1.01 lát | 0.12 LLM, 2.75 lát | 0.50 LLM, 1.00 lát | 0.00 LLM, 1.40 lát | 15 / 262 |
| S9 (không tách; tệp có điểm cặp trang >= 0.3 -> người (nghi composite)) | 0.06 LLM, 1.00 lát | 0.04 LLM, 1.00 lát | 0.12 LLM, 1.00 lát | 0.50 LLM, 1.00 lát | 0.00 LLM, 1.00 lát | 14 / 245 |

### So sánh ghép cặp (hiệu của (c) có trọng số, CI 95% bootstrap ghép cặp)

| cặp | hiệu | CI | kết luận |
|---|---|---|---|
| S4 - S3 | +5.8 điểm | [+2.8; +9.0] | tách được |
| S10 - S4 | +1.2 điểm | [-0.5; +2.8] | không tách được |
| S10 - S7 | -0.3 điểm | [-2.6; +1.7] | không tách được |
| S7 - S6 | +0.8 điểm | [+0.0; +2.0] | không tách được |
| S4 - S5 | +2.0 điểm | [-0.9; +4.9] | không tách được |
| S3 - S2 | +17.4 điểm | [+12.5; +22.3] | tách được |
| S2 - S1 | +14.1 điểm | [+10.1; +18.6] | tách được |
| S10 - S0 | -0.4 điểm | [-2.9; +1.9] | không tách được |
| S7 - S0 | -0.1 điểm | [-1.2; +1.0] | không tách được |

## Lưới chọn tham số trên dev (cùng một quy tắc cho mọi lựa chọn)

**Quy tắc:** (1) cổng tệp thường: cận dưới CI 95% ghép cặp của hiệu (c) so với S0 >= -3 điểm; (2) cổng an toàn: sai lặng lẽ / tự xử lý không cao hơn S0 (không áp dụng khi chọn S6); (3) trong các biến thể qua cổng, giao đúng và tự động nhiều tài liệu đáp án nhất; hòa (hiệu cấp tài liệu so với tốt nhất có CI ghép cặp chứa 0) -> ít núm điều chỉnh hơn, rồi ít lời gọi LLM hơn. Quy tắc đặt SAU khi xem số dev (mục tiêu ban đầu 1% sai lặng lẽ không biến thể nào đạt); không dùng TEST.

#### S6: tau, không gộp

| biến thể | Δ(c) so S0 | CI lo | CI hi | sai lặng lẽ/tự xử lý | tài liệu đúng+tự động | tài liệu (số) | LLM/tệp | cổng tệp thường | cổng an toàn | núm |
|---|---|---|---|---|---|---|---|---|---|---|
| M0.5 | -0.0738 | -0.1149 | -0.0358 | 0.1196 | 0.8585 | 273 | 0.1941 | False | False | 2 |
| M0.7 | -0.0379 | -0.0736 | -0.0051 | 0.0861 | 0.8648 | 275 | 0.1374 | False | False | 3 |
| M0.9 | -0.0307 | -0.0575 | -0.0046 | 0.0825 | 0.7830 | 249 | 0.0895 | False | False | 3 |
| M0.95 | -0.0096 | -0.0291 | 0.0068 | 0.0756 | 0.7704 | 245 | 0.0626 | True | False | 3 |
| M0.98 | -0.0089 | -0.0243 | 0.0051 | 0.0786 | 0.7579 | 241 | 0.0586 | True | False | 3 |

#### S7: tau, có gộp

| biến thể | Δ(c) so S0 | CI lo | CI hi | sai lặng lẽ/tự xử lý | tài liệu đúng+tự động | tài liệu (số) | LLM/tệp | cổng tệp thường | cổng an toàn | núm |
|---|---|---|---|---|---|---|---|---|---|---|
| M0.5+m | -0.0155 | -0.0434 | 0.0093 | 0.0591 | 0.8774 | 279 | 0.1941 | False | True | 3 |
| M0.7+m | -0.0039 | -0.0286 | 0.0189 | 0.0511 | 0.8648 | 275 | 0.1374 | True | True | 4 |
| M0.9+m | -0.0170 | -0.0372 | -0.0008 | 0.0685 | 0.7673 | 244 | 0.0895 | False | True | 4 |
| M0.95+m | -0.0048 | -0.0177 | 0.0066 | 0.0707 | 0.7579 | 241 | 0.0626 | True | True | 4 |
| M0.98+m | -0.0008 | -0.0122 | 0.0099 | 0.0704 | 0.7516 | 239 | 0.0586 | True | True | 4 |

#### S10: (tau, kappa), có gộp trừ ranh giới điểm >= kappa

| biến thể | Δ(c) so S0 | CI lo | CI hi | sai lặng lẽ/tự xử lý | tài liệu đúng+tự động | tài liệu (số) | LLM/tệp | cổng tệp thường | cổng an toàn | núm |
|---|---|---|---|---|---|---|---|---|---|---|
| K0.5/0.9+m | -0.0292 | -0.0622 | 0.0037 | 0.0733 | 0.8931 | 284 | 0.1941 | False | True | 4 |
| K0.5/0.95+m | -0.0163 | -0.0466 | 0.0105 | 0.0599 | 0.8962 | 285 | 0.1941 | False | True | 4 |
| K0.5/0.98+m | -0.0196 | -0.0485 | 0.0067 | 0.0633 | 0.8899 | 283 | 0.1941 | False | True | 4 |
| K0.5/0.99+m | -0.0155 | -0.0434 | 0.0093 | 0.0591 | 0.8899 | 283 | 0.1941 | False | True | 4 |
| K0.7/0.9+m | -0.0176 | -0.0487 | 0.0112 | 0.0652 | 0.8805 | 280 | 0.1374 | False | True | 5 |
| K0.7/0.95+m | -0.0047 | -0.0312 | 0.0194 | 0.0519 | 0.8836 | 281 | 0.1374 | False | True | 5 |
| K0.7/0.98+m | -0.0080 | -0.0334 | 0.0156 | 0.0553 | 0.8774 | 279 | 0.1374 | False | True | 5 |
| K0.7/0.99+m | -0.0039 | -0.0286 | 0.0189 | 0.0511 | 0.8774 | 279 | 0.1374 | True | True | 5 |

### Dải S8 (trên S7; chọn: tự xử lý và đúng lớn nhất với sai lặng lẽ <= 2%, không đạt thì sai thấp nhất)

| dải | tự_xử_lý | tự_xử_lý_và_đúng | sai_lặng_lẽ_trên_tự_xử_lý |
|---|---|---|---|
| 0.02-0.6 | 0.6464 | 0.6016 | 0.0692 |
| 0.02-0.7 | 0.6296 | 0.5895 | 0.0637 |
| 0.02-0.8 | 0.6042 | 0.5732 | 0.0512 |
| 0.02-0.9 | 0.5996 | 0.5732 | 0.0439 |
| 0.02-0.95 | 0.5808 | 0.5611 | 0.0340 |
| 0.05-0.6 | 0.6861 | 0.6381 | 0.0700 |
| 0.05-0.7 | 0.6694 | 0.6259 | 0.0649 |
| 0.05-0.8 | 0.6439 | 0.6097 | 0.0531 |
| 0.05-0.9 | 0.6393 | 0.6097 | 0.0463 |
| 0.05-0.95 | 0.6173 | 0.5976 | 0.0320 |
| 0.1-0.6 | 0.7373 | 0.6827 | 0.0741 |
| 0.1-0.7 | 0.7205 | 0.6705 | 0.0694 |
| 0.1-0.8 | 0.6951 | 0.6543 | 0.0587 |
| 0.1-0.9 | 0.6905 | 0.6543 | 0.0524 |
| 0.1-0.95 | 0.6685 | 0.6422 | 0.0394 |
| 0.2-0.6 | 0.8417 | 0.7759 | 0.0782 |
| 0.2-0.7 | 0.8249 | 0.7638 | 0.0742 |
| 0.2-0.8 | 0.7995 | 0.7475 | 0.0650 |
| 0.2-0.9 | 0.7916 | 0.7475 | 0.0557 |
| 0.2-0.95 | 0.7655 | 0.7313 | 0.0447 |
| 0.3-0.6 | 0.8822 | 0.8165 | 0.0746 |
| 0.3-0.7 | 0.8655 | 0.8043 | 0.0707 |
| 0.3-0.8 | 0.8400 | 0.7881 | 0.0619 |
| 0.3-0.9 | 0.8322 | 0.7881 | 0.0530 |
| 0.3-0.95 | 0.8061 | 0.7719 | 0.0424 |

### Cờ S9 (trên S0; cùng cách chọn)

| cờ_tối_thiểu | tự_xử_lý | tự_xử_lý_và_đúng | sai_lặng_lẽ_trên_tự_xử_lý |
|---|---|---|---|
| 0.3 | 0.7790 | 0.7645 | 0.0186 |
| 0.5 | 0.8357 | 0.8172 | 0.0222 |
| 0.7 | 0.8763 | 0.8577 | 0.0211 |
| 0.9 | 0.9085 | 0.8821 | 0.0291 |
| 0.95 | 0.9440 | 0.9064 | 0.0398 |

**Chọn:** S6 = M0.98, S7 = M0.98+m, S10 = K0.7/0.99+m, S8 dải (0.05, 0.95), S9 cờ 0.3.

### Chọn mặc định cuối trong S0..S10

| biến thể | Δ(c) so S0 | CI lo | CI hi | sai lặng lẽ/tự xử lý | tài liệu đúng+tự động | tài liệu (số) | LLM/tệp | cổng tệp thường | cổng an toàn | núm |
|---|---|---|---|---|---|---|---|---|---|---|
| S0 | 0.0000 | 0.0000 | 0.0000 | 0.0734 | 0.7044 | 224 | 0.0545 | True | True | 0 |
| S1 | -0.3887 | -0.4358 | -0.3433 | 0.4244 | 0.6132 | 195 | 0.4406 | False | False | 1 |
| S2 | -0.2476 | -0.2962 | -0.1941 | 0.2963 | 0.7296 | 232 | 0.3813 | False | False | 1 |
| S3 | -0.0738 | -0.1149 | -0.0358 | 0.1196 | 0.8585 | 273 | 0.1941 | False | False | 2 |
| S4 | -0.0155 | -0.0434 | 0.0093 | 0.0591 | 0.8774 | 279 | 0.1941 | False | True | 3 |
| S5 | -0.0353 | -0.0669 | -0.0051 | 0.0750 | 0.8679 | 276 | 0.3813 | False | False | 2 |
| S6 | -0.0089 | -0.0243 | 0.0051 | 0.0786 | 0.7579 | 241 | 0.0586 | True | False | 3 |
| S7 | -0.0008 | -0.0122 | 0.0099 | 0.0704 | 0.7516 | 239 | 0.0586 | True | True | 4 |
| S10 | -0.0039 | -0.0286 | 0.0189 | 0.0511 | 0.8774 | 279 | 0.1374 | True | True | 5 |
| S8 | -0.0008 | -0.0122 | 0.0099 | 0.0320 | 0.4811 | 153 | 0.0586 | True | True | 5 |
| S9 | 0.0000 | 0.0000 | 0.0000 | 0.0186 | 0.5818 | 185 | 0.0545 | True | True | 1 |

**Mặc định chọn trên dev: S10.**

### Kiểm tra: S0 có trùng thí nghiệm 03_src_cascade không?

S0 (cả tệp = một lát cắt, văn bản = 2 trang đầu) trùng bộ ba (tầng, nhãn) với `regress_dev_per_doc.csv` của 03 trên 237/237 tài liệu DEV.


## Kết quả TEST (MỘT lần, cấu hình đóng băng = **S10**: {"name": "S10", "base": "model", "tau": 0.7, "merge": true, "band": null, "keep": 0.99})

n = 59 tệp TEST: tệp 1 trang 21, nhiều trang, không ghép 36, BB_LAY_MAU 2. Không có composite khác loại và composite cùng loại ngoài BB_LAY_MAU trong TEST.

| biến thể | tệp đúng hoàn toàn (c) | Clopper-Pearson 95% | tự xử lý | sai lặng lẽ / tự xử lý (CP 95%) | tự xử lý và đúng | lời gọi LLM | lát cắt |
|---|---|---|---|---|---|---|---|
| S0 | 56/59 = 94,9% | [85,9%; 98,9%] | 59/59 | 3/59 [1,1%; 14,1%] | 56/59 | 4 | 59 |
| CHOSEN | 56/59 = 94,9% | [85,9%; 98,9%] | 58/59 | 2/58 [0,4%; 11,9%] | 56/59 | 5 | 70 |

**(c) theo nhóm**

| biến thể | tệp 1 trang (n=21) | nhiều trang, không ghép (n=36) | BB_LAY_MAU (n=2) | **toàn bộ, theo cơ cấu tệp thật** |
|---|---|---|---|---|
| S0 | 20/21 = 95% [86%; 100%] | 36/36 = 100% [100%; 100%] | 0/2 = 0% [0%; 0%] | **96,1% [93,1%; 97,6%]** |
| CHOSEN | 20/21 = 95% [86%; 100%] | 34/36 = 94% [86%; 100%] | 2/2 = 100% [100%; 100%] | **94,8% [88,1%; 100,0%]** |

| biến thể | tự xử lý hoàn toàn | tự xử lý VÀ đúng | sai lặng lẽ (tự xử lý mà sai) | sai lặng lẽ / tự xử lý | thô: tự xử lý / tệp | thô: sai / tự xử lý (Clopper-Pearson 95%) |
|---|---|---|---|---|---|---|
| S0 | 100,0% [100,0%; 100,0%] | 96,1% [93,1%; 97,6%] | 3,92% [2,41%; 6,95%] | 3,92% [2,41%; 6,95%] | 59/59 | 3/59 = 5,08% [1,06%; 14,15%] |
| CHOSEN | 98,2% [94,5%; 100,0%] | 94,8% [88,1%; 100,0%] | 3,34% [0,00%; 8,83%] | 3,40% [0,00%; 8,83%] | 58/59 | 2/58 = 3,45% [0,42%; 11,91%] |

| biến thể | tài liệu đáp án giao ĐÚNG và tự động | tài liệu đáp án (tổng) | trong đó của các nhóm composite (n tài liệu) |
|---|---|---|---|
| S0 | 56/68 = 82,4% [60,5%; 100,0%] | 68 | 0/11 |
| CHOSEN | 65/68 = 95,6% [89,8%; 100,0%] | 68 | 11/11 |

Mỗi ô: (tệp S0 đúng hoàn toàn mà biến thể làm hỏng) hỏng / (tệp S0 sai mà biến thể sửa được) sửa.

| biến thể | tệp 1 trang | nhiều trang, không ghép | BB_LAY_MAU | hiệu có trọng số (biến thể - S0) của (c), CI ghép cặp | kết luận |
|---|---|---|---|---|---|
| CHOSEN | 0 hỏng / 0 sửa | 2 hỏng / 0 sửa | 0 hỏng / 2 sửa | -1.2 điểm [-6.7; +2.4] | không tách được |

## Đọc kết quả (phân tích bằng lời)

**1. Vì sao "tách" không thắng ở cấp tệp.** 92% tệp (tệp 1 trang và nhiều trang không ghép) đã đúng khi để nguyên: S0 đúng 70/71 và 154/155 (lỗi duy nhất mỗi nhóm là phân loại, không phải tách). Bất kỳ bộ tách nào cắt nhầm một tệp loại này là *làm hỏng* một tệp đang đúng. Luật cũ làm hỏng 104/155 tệp nhiều trang, luật v2 70/155, bộ phân loại cặp trang ở ngưỡng 0,5 vẫn 26/155. Trong khi phần "sửa" chỉ có 19 tệp composite (7% cơ cấu), nên ngay cả sửa hết cũng chỉ bù được tối đa ~7 điểm. Bảng "hại so với S0" ở trên là bằng chứng trực tiếp (số tệp hỏng / sửa theo từng nhóm).

**2. Hai hiệu chỉnh nhận biết loại đều có ích, nhưng theo cách khác nhau.**
* *Gộp lát cắt liền kề cùng loại* (S4 so với S3): +5,8 điểm (CI [+2,8; +9,0], tách được). Lý do: phần lớn tách nhầm trong tệp nhiều trang nằm giữa hai trang mà bộ phân loại gán cùng một loại (ví dụ trang chữ ký 2/2); gộp chúng lại cứu 16 trong 26 tệp bị hỏng. Cái giá: composite *cùng loại ngoài `BB_LAY_MAU`* (hóa đơn hai bản, biên nhận thế chấp...) bị gộp nhầm (S3 đúng hoàn toàn 2/6, S4 0/6); và composite khác loại bị gộp khi bộ phân loại gán nhầm cùng loại (S4 chỉ còn 3/8 tách đúng so với 8/8 của S3).
* *Giữ ranh giới rất chắc* (`keep >= 0,99`, S10 so với S4): cứu lại phần lớn composite khác loại khỏi gộp nhầm (tách đúng 7/8), hiệu cấp tệp +1,2 điểm [−0,5; +2,8] ("không tách được") nhưng có ý nghĩa ở cấp tài liệu và an toàn.
* *Ngưỡng cao hơn* (S6, S7 chọn ngưỡng 0,98): gần như hết hại (−0,9 / −0,1 điểm so với S0) nhưng cũng hết lợi: ngưỡng cao làm mất ranh giới của các tệp `BB_LAY_MAU` (điểm ~0,8) và S7 chỉ giao đúng 75,2% tài liệu (S0 70,4%, S10 87,7%).
* *Định tuyến về người* (S8, S9) giảm sai lặng lẽ nhưng trả bằng tự động hóa: S9 (không tách, cờ 0,3) hạ sai lặng lẽ xuống 1,45% tổng số tệp (1,86% trong số tự xử lý) nhưng chỉ 77,9% tệp tự xử lý hoàn toàn; vì cờ 0,3 bật nhầm trên nhiều tệp nhiều trang bình thường. S8 trên nền ngưỡng 0,98 không đáng giá (61,7% tự xử lý, sai 3,2%).

**3. Điểm nghẽn thật của composite khác loại là phân loại lát cắt.** Khi tách đúng tuyệt đối (S3: 8/8 tệp), chỉ 2/8 tệp có mọi tài liệu đúng loại. Trong 7 trang "biên bản giao nhận hàng hóa" của các bộ chứng từ này, bộ phân loại gán `PHIEU_XUAT_KHO` 6 lần (đây chính là cặp "dễ nhầm" ghi trong taxonomy), còn `CHUNG_THU_CHAT_LUONG` (không có tài liệu đơn nào để học) đúng 6/6 nhờ cổng luật. Hệ quả: cải thiện bộ tách không đủ; muốn xử lý tốt bộ chứng từ cần thêm luật/ví dụ cho `BB_GIAO_NHAN_HANG_HOA` so với `PHIEU_XUAT_KHO`. Đây là kết quả trên **8 tệp của một nhà cung cấp**, đọc như giả thuyết cần kiểm bằng thêm mẫu.

**4. Cái giá của S10 ở tệp thường.** Trên 155 tệp nhiều trang không ghép, S10 hỏng 6 tệp S0 đúng (S0 154/155 -> S10 148/155) và chỉ còn 149/155 tệp nhóm này tự xử lý hoàn toàn (S0: 155/155); đổi lại sửa 3 tệp `BB_LAY_MAU`, 2 composite khác loại. Ở TEST: S10 hỏng 2/36 tệp nhiều trang, sửa 2/2 `BB_LAY_MAU`.

## Mặc định khuyến nghị và vì sao

**`model+merge` (S10) làm mặc định của pipeline** (`DocumentPipeline(split_policy=None)`, `scripts/run_pipeline.py --splitter model+merge`). Lý do, theo thứ tự bằng chứng:
1. Nó qua cả hai cổng đã đặt trên dev: *không hại tệp thường* (cận dưới CI hiệu so với S0 là −2,9 điểm, trong ngưỡng −3) và *sai lặng lẽ / tự xử lý không cao hơn S0* (5,1% so với 7,3%).
2. Trong các biến thể qua cổng, nó giao đúng-và-tự-động nhiều tài liệu đáp án nhất (279/318); S7 và S6 qua cổng nhưng kém xa ở cấp tài liệu (75-76%).
3. Không tách (S0) đúng nhiều tệp hơn một chút nhưng **bỏ rơi hoàn toàn tệp ghép** (0/92 tài liệu thuộc composite được giao đúng) và sai lặng lẽ nhiều nhất.

**Trung thực về độ vững của lựa chọn.** S10 và S7 (ngưỡng 0,98 + gộp) hòa ở cấp tệp; cấp tài liệu S10 hơn rõ (87,7% so với 75,2%). Quy tắc chọn (cổng + tài liệu) đặt **sau khi xem số dev** vì mục tiêu ban đầu "sai lặng lẽ <= 1%" (giao thức §7) không biến thể nào đạt; tham số (tau=0,7, kappa=0,99) chọn trong lưới nhỏ (5 tau, 8 cặp tau-kappa) trên 245 tệp, nên lạc quan. Các cặp (tau, kappa) lân cận cho kết quả gần như nhau (bảng lưới), nên mặc định ít nhạy, nhưng chỉ `K0,7/0,99` qua cổng tệp thường. **Nếu doanh nghiệp coi sai lặng lẽ đắt hơn nhân sự duyệt**, chế độ `--splitter triage` (S9) là lựa chọn thay thế: không tách, đưa 22% tệp về người, sai lặng lẽ 1,9% trong số tự xử lý. Nếu muốn hành vi cũ: `--splitter rule` (hại rõ: S1 53,4%).

## Chi phí

* **Số lời gọi LLM phân loại mỗi tệp** (dev, 245 tệp, đếm từ lần chạy thật; bảng "Số lời gọi LLM và số lát cắt mỗi tệp"): S0 0,06 (14 lời gọi), S1 0,45 (110), S2 0,39 (95), S3 0,20 (49), S10 0,14 (35). Tách nhân số lát cắt rồi nhân số lời gọi: luật cũ gấp 7,9 lần S0. Mỗi lời gọi chỉ xảy ra khi luật và TF-IDF từ chối (~5% văn bản). Gộp không tốn thêm lời gọi (dùng lại kết quả lát đầu).
* **Qua lớp pipeline thật** (`cost_sample.py`, 20 tệp dev, cache LLM trống = lời gọi thật, GPU dùng chung, không tính OCR): tách (mô hình cặp trang) trung vị 28 ms, p95 86 ms; nạp mô hình cặp trang 236 ms một lần, dựng bộ phân loại 50 ms; phân loại trung vị 12 ms, p95 859 ms (do 2 lời gọi LLM ~0,9 s). Chính sách `none`: 2 lời gọi LLM / 20 tệp, `rule`: 7, `model+merge`: 2.
* **Độ trễ theo tệp có trích xuất** (`cost_sample_extract.py`, 14 tệp, chính sách mặc định, mọi lời gọi LLM là thật): tổng trung vị **4,3 s**, p95 12,1 s, tối đa 12,2 s; trong đó tách ~31 ms, phân loại ~12 ms, **trích xuất ~4,2 s mỗi lát cắt** (lời gọi Qwen3.5-4B), bộ chứng từ 4 lát cắt mất ~12 s (hai lát có schema). OCR không nằm trong số này. Trích xuất chiếm >98% thời gian xử lý sau OCR.

## Vì sao lần chạy thử tốn 195 s để phân loại một tệp ghép

Bằng chứng (`stall_analysis.py`, `results/stall_latency.json`; chỉ đọc cache):
* Cả ba bản ghi của lần chạy thử (cache `cache/llm/ollama`) có `latency_ms` ≈ `total_duration` phía máy chủ Ollama (chênh 7-19 ms): thời gian **nằm hoàn toàn ở máy chủ**, không phải ở mạng, tokenization hay phía mã khách. Hai lời gọi thành công mất 18,5 s và 28,5 s; lời gọi thứ ba chạm giới hạn **180 s** của `OllamaBackend`.
* Các lời gọi chậm không nặng hơn lời gọi nhanh (~1.900 token đầu vào, 13-16 token đầu ra, cả hai nhóm). Trên 4.366 lời gọi của thí nghiệm 02: trung vị 858 ms, p99 5,2 s, nhưng 28 lời gọi (0,6%) mất 15 s đến 6,8 phút, trong đó một chuỗi 10 lời gọi liên tiếp đều ≈ 20 s (18-22 s).
* Đo trực tiếp lúc chạy thí nghiệm này (qwen3.5:4b vừa bị dỡ khỏi VRAM, ba yêu cầu giống hệt lựa chọn của bộ phân loại, `num_ctx=6144`): **cả ba** đều có `load_duration` 26-32 s (wall 27-33 s) — mô hình bị nạp lại ở *mỗi* yêu cầu dù vừa dùng xong, tức có client khác trên cùng Ollama đang đẩy mô hình ra/vào. Trước đó `/api/ps` từng báo `context_length = 12288` cho qwen3.5:4b trong khi bộ phân loại xin 6144: tồn tại client xin cấu hình khác, và Ollama nạp lại mô hình mỗi khi cấu hình đang nạp khác cấu hình được xin. Người gọi khác không được xác định (log máy chủ rỗng).
* **Kết luận (suy luận từ các phép đo trên, không phải bằng chứng trực tiếp về ca 195 s):** do máy chủ Ollama dùng chung, mỗi lời gọi có thể phải chờ một lần nạp lại mô hình (≈ 18-32 s) và/hoặc xếp hàng sau lời gọi dài của agent khác (prompt hàng nghìn token, `num_ctx` 32768 ở thí nghiệm tách trang). Giới hạn cũ 180 s biến một hàng đợi kẹt thành 3 phút; một tệp ghép 4 lát cắt nhân lên. Cấu hình của chính bộ phân loại (`num_ctx` 6144, `keep_alive` 10 phút) **không** phải nguyên nhân: nó trùng với bộ trích xuất (6144).
* **Đã sửa** (`src/classification/llm_backends.py`, `src/pipeline.py`): hết giờ mỗi lời gọi Ollama 180 -> 60 s mặc định (`DEFAULT_OLLAMA_TIMEOUT_S`), pipeline đặt 45 s; **ngân sách LLM 90 s/tệp**; sau một lần hết giờ, các lát cắt còn lại của tệp không gọi LLM nữa (về người, lý do `llm_timeout` / `llm_skipped`); hết giờ ở 2 tệp liên tiếp mở **mạch ngắt** 60 s; lỗi kết nối thử lại đúng 1 lần (`GuardedLlm`, có test với đồng hồ giả). Trường hợp xấu nhất của một tệp giảm từ vài phút xuống ~45-90 s. Khuyến nghị vận hành (chưa làm): mọi client của qwen3.5:4b trên cùng Ollama dùng chung `num_ctx` 6144, hoặc tách một máy chủ Ollama riêng cho pipeline.

## Chuỗi tới ngày hết hạn (chỉ đơn vị DEV; `chain_extraction.py`)

Mục này **không** dùng TEST của thí nghiệm trích xuất. 82 đơn vị dev thuộc 4 loại có schema (`teams/team4_extraction/gold/units.csv`: DEV 76 + 6 đơn vị phiếu xuất kho nằm trong 6 tệp composite khác loại). Chuỗi chạy như sản xuất trên văn bản `ocr_v2`: bộ tách **S10**, cascade (dự đoán cross-fitted như trên), `FieldExtractor` theo **loại đã dự đoán** (luật + Qwen3.5-4B ghép theo kiểu; hạn chỉ tự nhận khi một mô hình đọc trùng ngày trong tên tệp; PII tắt; **không có ảnh trang**), đối chiếu với `fields_silver_v1.jsonl` (silver do LLM đọc ảnh, Opus phân xử 58 mục, **chưa người kiểm**). Luật và prompt của bộ trích xuất đã được chỉnh trên chính các đơn vị này: số ở đây lạc quan về phần trích xuất. Chấm 66 trường hạn có ngày cụ thể trong silver (CC_TAP_HUAN_VC_HNH 19, GCN_DDK_BAN_LE_XD 21, HD_MUA_BAN 26; phiếu xuất kho không có trường hạn).

| | Cô lập (đúng trang, đúng loại thật) | Cả chuỗi (S10 -> cascade -> trích xuất) |
|---|---|---|
| đơn vị có **loại đúng** (lát cắt trùng nhiều trang nhất, được tự nhận) | — | **82 / 82** (6/6 phiếu xuất kho trong composite; 80/82 lát cắt đúng khoảng trang, 2 lát dư trang không làm đổi loại) |
| hạn **đúng** (tự nhận và trùng silver) | 32 / 66 = 48,5% | 32 / 66 = 48,5% |
| hạn **bỏ trống** (về người; kèm ngày gợi ý) | 34 / 66 = 51,5% (26 `needs_review`, 8 `not_found`) | 34 / 66 = 51,5% |
| hạn **sai** (tự nhận mà sai) | 0 / 66 | 0 / 66 |
| tự nhận / sai trong số tự nhận | 32 tự nhận, 0 sai, cận trên Clopper-Pearson 95% một phía của tỉ lệ sai **8,9%** | như bên trái |
| ngày gợi ý (cho hạn bỏ trống) đúng | 22 / 25 | 22 / 25 |

Theo loại, chuỗi tự nhận đúng: `CC_TAP_HUAN_VC_HNH` 15/19, `GCN_DDK_BAN_LE_XD` 10/21, `HD_MUA_BAN` 7/26, sai 0 ở cả ba. Chuỗi **không mất gì** so với cô lập trên tập này (0 trường khác kết quả): ở đây cả bốn loại có schema đều là loại mà cổng luật/TF-IDF nhận đúng và bộ tách để nguyên tệp. Phần mất thật nằm ở chỗ khác: **tự nhận 48,5%, thấp hơn 58% (37/64) mà thí nghiệm trích xuất báo cho DEV**, vì quy tắc `any-model=filename` của họ tính cả mô hình đọc ảnh (VLM) là một nguồn, còn pipeline hiện **không đưa ảnh trang** vào `extract_fields` (`page_images=None`); chạy cô lập với cùng cấu hình sản xuất cũng chỉ ra 48,5%, nên khoảng chênh ~10 điểm là do thiếu nguồn VLM (rất có thể; không tách riêng được tác động của 2 đơn vị composite). Muốn lấy lại: render hai trang đầu thành ảnh trong bước OCR (đã có sẵn ảnh trang) và truyền `page_images` — chưa làm. Pipeline phản ánh quyết định hạn trong định tuyến từng lát cắt (`SliceRouting.expiry`, `expiry_suggestion`, `field_review`) và đếm ở `file_routing.n_field_review`: lát cắt vẫn `auto_file` nhưng ngày hạn `needs_review` đi qua người; loại chưa có schema trả về `extraction_status = skipped`, `extraction_note = no_schema...` (không phải lỗi).

## Thay đổi mã

* `src/splitting/type_merge.py` (gộp cùng loại, cờ một-tờ suy ra từ taxonomy), `src/splitting/policy.py` (chính sách tách, preset, mặc định `model+merge`), `split_document(method="none")`.
* `src/pipeline.py`: chính sách tách chọn được (`split_policy=`), gộp theo loại sau phân loại, `GuardedLlm` (hết giờ / ngân sách / mạch ngắt), tóm tắt cấp tệp `file_routing`, hook `extract_fields(slice, category, filename, page_images)` nối `FieldExtractor`, quyết định hạn trong định tuyến. `scripts/run_pipeline.py`: `--splitter`, `--llm-timeout`, `--llm-file-budget`.
* `src/common/contracts.py` (chỉ thêm): chú thích `boundary_method` liệt kê `rule_v2`/`none`/`+type_merge`; `FileRoutingSummary`; `SliceRouting.expiry`... ; `DocumentProcessingPipelineResult.file_routing`. `src/classification/llm_backends.py`: mặc định hết giờ 60 s, `make_backend(timeout=)`.
* Test: `tests/test_splitting_type_merge.py` (14), `tests/test_pipeline.py` (mở rộng; không GPU, không mạng).

## Chưa chứng minh

1. **Đáp án máy.** Ranh giới và loại là `boundary_gold_v0` / `labels_v2` (một annotator AI xem đủ trang, chưa người kiểm; 5 tệp `check_composite` rủi ro cao nhất). Mọi con số "đúng" là "đúng theo nhãn tạm". Có thể còn tệp ghép bị bỏ sót trong 191 tệp "không composite".
2. **Số composite rất nhỏ**: dev chỉ 19 tệp (8 khác loại, 6 cùng loại ngoài BB_LAY_MAU, 5 BB_LAY_MAU), TEST chỉ 2 (đều BB_LAY_MAU). CI bootstrap "toàn bộ" hẹp giả ở các nhóm quan sát 0/n; mọi kết luận về composite chỉ là chiều hướng.
3. **Một nhà cung cấp, một mẫu phiếu xuất kho.** 8 composite khác loại thuộc vài bộ chứng từ cùng dạng (gồm 5 bộ BSR cùng nhà cung cấp, đã gộp một nhóm khi cross-fit); kết quả tốt có thể là nhớ bố cục. Phân loại của các lát cắt composite có thể hơi lạc quan vì `template_group` (băm ảnh) không bắt được "cùng nhà cung cấp" với tài liệu đơn trong DEV.
4. **TEST n = 59**: S10 và S0 cùng 56/59, cùng khoảng Clopper-Pearson [85,9%; 98,9%]; hiệu −1,2 điểm [−6,7; +2,4]. Không đủ để khẳng định gì ngoài "không tệ đi trên tệp thường". Lần mở TEST này (đo chuỗi) khác lần mở TEST phân loại trước và chỉ chấm cấu hình đóng băng + S0.
5. **Lựa chọn trên dev có tối ưu hóa**: cổng 3 điểm, quy tắc cổng + tài liệu, lưới tau/kappa đều chọn sau khi xem số dev; phần lạc quan chưa đo được. Ngưỡng `th_s`/`th_llm` của cascade cũng được chọn trên DEV ở thí nghiệm 02.
6. **Sai lặng lẽ <= 1% chưa đạt** ở mọi biến thể tách; chưa đo trên mẫu ngẫu nhiên phần tự xử lý.
7. **Không đo OCR** (dùng văn bản đã có) và không đo tệp > 30 trang (tệp 93 trang chỉ có văn bản 30 trang); độ trễ đo khi GPU/Ollama dùng chung.
8. **Chuỗi trích xuất**: silver LLM, prompt/luật chỉnh trên chính đơn vị này; chỉ 4 loại có schema, đều do cascade nhận dễ (loại có composite khó như `BB_GIAO_NHAN_HANG_HOA` không có schema nên không nằm trong chuỗi); quy ước "ngày trong tên tệp = ngày hết hạn" chưa được công ty xác nhận; thiếu ảnh trang trong pipeline.
9. **Tương thích với artefact**: pipeline dùng `models/` (đã thấy mọi tệp dev) nên số "qua lớp pipeline thật" chỉ nói về chi phí; trên 20 tệp mẫu, tách của pipeline trùng thí nghiệm ở 19/20 tệp (cross-fit vs artefact).
