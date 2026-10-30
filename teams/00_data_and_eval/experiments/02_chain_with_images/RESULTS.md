# 02 - Chuỗi tới ngày hết hạn, có và không có ảnh trang (VLM)

> `labels_v2.csv` sha1[:10] = `eb3348713a` | ngày 2026-10-16 | tái lập: `.venv\Scripts\python.exe -X utf8 teams/00_data_and_eval/experiments/02_chain_with_images/chain_with_images.py` | văn bản: `data/ocr_v2.jsonl`, PDF trong `docs/_chot_samples_phanloaitailieu/` (chỉ đọc).
> Đáp án = `teams/team4_extraction/gold/fields_silver_v1.jsonl` (do máy làm, chưa người kiểm): viết "so với đáp án máy", không phải độ chính xác thật. **Chỉ DEV, không chạy TEST.**

## Tóm tắt

* **Câu hỏi.** Ở thí nghiệm 01, pipeline gọi `extract_fields(..., page_images=None)` nên nguồn VLM của ngày hết hạn không hoạt động: tự nhận đúng 32/66 (48,5%), thấp hơn ~58% của nhóm 4 (có ảnh). Dựng ảnh trang trong pipeline có lấy lại được phần đó không?
* **Trả lời (82 đơn vị DEV, 66 trường hạn có ngày cụ thể).** Có ảnh: hạn đúng và tự nhận **37/66 (56,1%)**, so với **32/66 (48,5%)** không ảnh. **Sai: 0/37** ở cả hai cấu hình; cận trên 95% (Clopper-Pearson) của tỉ lệ sai trong số tự nhận: 7,8% (có ảnh) so với 8,9% (không ảnh). Cỡ mẫu nhỏ nên cận trên còn rộng.
* **Ghép cặp.** Thêm 5 trường đúng, mất 0 (GCN_DDK_BAN_LE_XD +4, CC_TAP_HUAN_VC_HNH +1, HD_MUA_BAN +0). Hiệu +7,5 điểm, bootstrap ghép cặp lấy mẫu lại theo đơn vị (B = 5000): CI95 [+1,5; +15,2] (không chứa 0). Nhưng kiểm định dấu chính xác (5 đối 0) cho p hai phía = 0,0625: lợi ích **có chiều rõ nhưng ở mức biên**, chưa đủ chắc với n = 66.
* **Giá phải trả.** Một lời gọi VLM mỗi lát cắt thuộc loại có trường hạn (66/82 đơn vị) và thời gian dựng ảnh (bảng dưới). Đo trên GPU dùng chung.
* **Quyết định: mặc định BẬT** (`DEFAULT_USE_VLM = True`; tắt bằng `--no-vlm` hoặc `use_vlm=False`), vì không thêm một trường sai nào và không mất trường đúng nào; lý do không bật là chỉ khi cần giảm độ trễ.

## Cách làm

* Chuỗi tách S10, cascade và chọn lát cắt trùng nhiều trang nhất dựng **giống hệt** `01_end_to_end/chain_extraction.py`; chỉ khác phần trích xuất: `old` = `DocumentPipeline.extract_fields` không ảnh; `new` = cùng hàm kèm `page_images` do chính pipeline dựng.
* Dựng ảnh: `choose_vlm_pages` (cùng quy tắc `gold/build_units.py:choose_pages`: <= 4 trang lấy hết; ngược lại 2 trang đầu, trang cuối, trang có từ khóa hiệu lực/hạn, tối đa 6) rồi `render_pages_for_vlm` (PyMuPDF 200 dpi RGB, trang dọc cắt đôi tại hàng ít mực nhất quanh giữa, cạnh dài <= 1600 px). `FieldExtractor` gửi 4 ảnh đầu (`max_vlm_images`), `num_ctx` 12288, như lúc nhóm 4 đo. Ảnh chỉ nằm trong thư mục tạm, xóa ngay sau mỗi lát cắt; không lưu vào repo.
* Lời gọi VLM qua kho kết quả riêng `_cache/vlm_store.json` (nằm trong `.gitignore`); độ trễ ghi là của lần gọi thật đầu tiên. Lời gọi LLM văn bản đi qua cache đĩa của nhóm 4 như thí nghiệm 01 (nên độ trễ văn bản không nằm trong bảng).
* Không chạy TEST. Cấu hình chưa đóng băng cho TEST ở thí nghiệm này.

## Kết quả (n = 66 trường hạn, 82 đơn vị)

| | Không ảnh | Có ảnh |
|---|---|---|
| Đúng và tự nhận | 32 (48,5%) | 37 (56,1%) |
| Sai (tự nhận nhưng khác đáp án) | 0 | 0 |
| Để trống / chuyển người duyệt | 34 | 29 |
| Cận trên 95% của tỉ lệ sai trong số tự nhận | 8,9% | 7,8% |

Theo loại (đúng và tự nhận, không ảnh -> có ảnh): `CC_TAP_HUAN_VC_HNH` 15 -> 16 (n = 19), `GCN_DDK_BAN_LE_XD` 10 -> 14 (n = 21), `HD_MUA_BAN` 7 -> 7 (n = 26). Không lần gọi VLM nào hỏng ở lượt chạy cuối (82/82 trạng thái `ok`).

Độ trễ (GPU RTX 3060 **dùng chung**, đo lúc chạy, phụ thuộc tải máy):

| Bước | Trung vị | p90 | Ghi chú |
|---|---|---|---|
| Dựng ảnh (trung bình 4 ảnh/lát cắt) | 4,2 s | 6,7 s | CPU, PyMuPDF + lưu PNG `optimize=True` (có thể giảm nếu bỏ nén tối ưu; chưa đổi vì ngoài phạm vi) |
| Lời gọi VLM (66 lời gọi) | 14,7 s | 17,8 s | tối đa 77,9 s (các lời gọi đầu, Ollama nạp lại mô hình do `num_ctx` khác client khác) |

## Hạn chế

* Đáp án là silver máy; luật và prompt của bộ trích xuất đã được chỉnh trên chính các đơn vị DEV này, nên số lạc quan. Thêm 5 trường là nhỏ so với n = 66 (p dấu = 0,0625).
* Cả 82 đơn vị đều là loại mà cascade nhận đúng và bộ tách để nguyên tệp, nên thí nghiệm này không đo ảnh hưởng của lát cắt sai.
* Lượt chạy đầu có hai lần Ollama kẹt (hết giờ 300 s) khi GPU bị tranh chấp; lượt cuối dùng hết giờ 180 s, không thử lại, và không có lần hỏng nào. Độ trễ có thể khác nhiều khi tải GPU khác.
* Quy ước "ngày trong tên tệp = ngày hết hạn" chưa được công ty xác nhận.

## Mã liên quan

`src/pipeline.py` (`choose_vlm_pages`, `default_page_renderer`, `use_vlm`, khóa `render` trong `stage_timings_ms` chỉ xuất hiện khi thật sự dựng ảnh), `scripts/run_pipeline.py` (`--no-vlm`), `tests/test_pipeline_vlm_images.py` (6 test, extractor và bộ dựng ảnh giả, không cần Ollama).
