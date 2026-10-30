# Phương pháp luận nghiên cứu song song độc lập (tài liệu sống)

> Ý tưởng gốc: nhiều nhóm làm cùng lúc mà **không phải chờ nhau**, bằng cách tách phụ thuộc giữa các khâu qua **dữ liệu tham chiếu** và **hợp đồng dữ liệu**. Bản gốc (tiếng Việt, đầy đủ sơ đồ 4 nhóm, "Pipeline Dependency Trap", ngày ghép nối tuần 4) được lưu nguyên văn ở [`original_direction/DECOUPLED_PARALLEL_METHODOLOGY.md`](original_direction/DECOUPLED_PARALLEL_METHODOLOGY.md); mục tiêu và cách đọc bản gốc xem [`original_direction/README.md`](original_direction/README.md).
> Nội dung hiện hành (phụ thuộc giữa các nhóm, đánh giá hai pha, lộ trình, số đo) nằm ở [`PARALLEL_RESEARCH_PLAN.md`](PARALLEL_RESEARCH_PLAN.md) **mục 3 và 4**; tài liệu này không lặp lại mà chỉ ghi ý tưởng và những gì đã đổi.

## Đã thay đổi gì so với bản ban đầu

| Ý trong bản ban đầu | Hiện nay | Ghi chú |
|---|---|---|
| Bẫy phụ thuộc dây chuyền: làm tuần tự OCR → tách → phân loại → trích xuất thì ba nhóm đứng chờ, lỗi cộng dồn, không đo riêng được từng khâu | **Giữ nguyên** | Vẫn là lý do chính của cách tổ chức. Xem plan mục 3 |
| "Tập chuẩn vàng" (`GT_OCR`, `GT_Split`, `GT_Class`, `GT_IE`) gán sẵn, và dữ liệu giả (mock) cho mỗi nhóm | **Đổi**: dữ liệu tham chiếu có thật nhưng do máy tạo | Đầu vào tham chiếu nay là `data/ocr_v2.jsonl`, `data/labels_v2.csv`, `data/splits/`, đáp án ranh giới và silver trường. Chúng **chưa do người kiểm**, nên "đúng" nghĩa là "khớp đáp án máy". Fixture giả `tests/fixtures/sample_pipeline_fixtures.py` chỉ còn dùng cho test đơn vị |
| Hợp đồng Pydantic duy nhất `src/common/contracts.py` giữa các nhóm; thay lõi (RapidOCR → Apple Vision) không gãy khâu sau | **Giữ**, đã mở rộng có kiểm soát | Có test (`tests/test_contracts.py`) và nhật ký thay đổi hợp đồng ở [`teams/README.md`](../teams/README.md). Việc "thay lõi" có thật: OCR cũ → PP-OCRv5 + VietOCR không làm gãy khâu sau |
| 4 nhóm đều độc lập từ ngày đầu | **Đổi**: thêm nhóm 00 (dữ liệu và đánh giá), phụ thuộc vào đáp án | Nhóm 00 dựng nhãn, chia dữ liệu có nhóm, bộ chấm và TEST khóa, nên bốn nhóm còn lại độc lập được trên dữ liệu chung. Một số phụ thuộc thật vẫn còn (ví dụ tệp ghép cần cả nhóm 2 và 3) |
| Đánh giá hai pha: từng thành phần trên đầu vào sạch, rồi toàn trình, so ΔF₁ để tìm nút cổ chai | **Giữ**; đã làm | Bảng E0–E3 và phép đo toàn trình theo tệp (plan mục 4, [`01_end_to_end/RESULTS.md`](../teams/00_data_and_eval/experiments/01_end_to_end/RESULTS.md)). Kết quả chính: ở cấp tệp, tách và không tách không phân biệt được (dev −0,4 điểm [−2,9; +1,9]) |
| Ngày ghép nối ở tuần 4, chạy thử trên 20 tệp phức hợp | **Đổi** | Ghép nối được làm sớm dưới dạng thí nghiệm toàn trình (dev 245 tệp, TEST 59 tệp), điều phối bởi `src/pipeline.py`; lộ trình chung nay là 6–8 tuần (plan mục 7) |
| Đo chi phí, độ trễ, độ chính xác toàn trình | **Giữ**, kèm khoảng tin cậy | Mọi số có cỡ mẫu và khoảng tin cậy; TEST chấm một lần |

## Ý tưởng cốt lõi (còn nguyên giá trị)

1. **Mỗi khâu có đầu vào tham chiếu của riêng nó**, lấy từ đáp án đã biết, để đo năng lực của chính khâu đó mà không dính lỗi khâu trước.
2. **Một hợp đồng dữ liệu** định kiểu đầu ra mỗi khâu (`OCRDocumentResult`, `SplitResult`, `ClassificationResult`, `ExtractionResult`); đổi lõi bên trong không làm gãy khâu sau chừng nào kiểu không đổi.
3. **Hai pha đánh giá**: pha 1 chấm từng khâu trên đầu vào sạch (giới hạn trần), pha 2 chấm cả chuỗi; hiệu giữa hai pha chỉ ra nút cổ chai.
4. **Điều bản gốc chưa lường tới:** đáp án tham chiếu cũng là sản phẩm cần kiểm; đáp án máy làm mọi số "lạc quan" theo cách khó thấy. Vì thế nhóm 00 và quy tắc "TEST khóa, chấm một lần" là một phần của phương pháp, không phải phụ kiện.
