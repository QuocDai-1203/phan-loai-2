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
