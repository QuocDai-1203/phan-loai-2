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
