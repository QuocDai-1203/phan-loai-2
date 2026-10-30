# Gold set cho OCR: hướng dẫn tạo đáp án do người duyệt

Mục tiêu: có một bộ "đáp án thật" (ground truth) cho **25 trang scan thật** để đo chính xác CER/WER của các
engine OCR. Hiện tại ta chỉ có pseudo-gold (text layer của PDF born-digital), sạch hơn scan thật rất nhiều
(xem `teams/team1_ocr/experiments/01_engine_bakeoff/RESULTS.md`).

Quy trình hiện hành (việc T1 trong [`../README.md`](../README.md)): **người sửa bản nháp do LLM chép**, không gõ từ đầu cả 25 trang.
Cả 25 trang đã có bản nháp của Claude Haiku trong `silver_llm/haiku/Pnnn.txt` (nối `Tnn` với `Pnnn` bằng cặp
`(relative_path, page)` của `gold_pages_todo.csv` và `(relative_path, page0)` của `../experiments/03_llm_silver/pages.csv`).
Riêng 5 trang overlap thì một người vẫn **gõ từ đầu**, để đo xem việc sửa nháp có làm người sửa bỏ sót lỗi của nháp hay không.

## File cần làm

`gold_pages_todo.csv`: danh sách 25 trang (mỗi dòng 1 trang).

| cột | ý nghĩa |
|---|---|
| `transcription_id` | mã T01..T25, dùng đặt tên file đáp án |
| `relative_path` | đường dẫn PDF, tính từ `docs/_chot_samples_phanloaitailieu/` |
| `page` | chỉ số trang **bắt đầu từ 0** (trang đầu = 0). Trong trình đọc PDF là trang `page + 1` |
| `why_chosen` | `printed` (chữ in), `handwriting` (viết tay), `stamp` (con dấu đè chữ), `table` (bảng), `low quality` (mờ/nhiễu/nghiêng/xoay) |
| `overlap_double_transcribe` | `yes` = 5 trang mà **hai người** cùng gõ, để đo mức đồng thuận |

## Cách làm

1. Mở trang bằng PDF viewer (hoặc render PNG: `fitz.open(pdf)[page].get_pixmap(dpi=150)`) và luôn đối chiếu với **ảnh**.
2. **20 trang thường** (`overlap_double_transcribe = no`): chép bản nháp Haiku vào `transcripts_draft/<transcription_id>.txt`
   (giữ nguyên, không sửa), rồi sửa một bản sao theo "Quy tắc gõ" bên dưới và lưu thành `transcripts/<transcription_id>.txt`.
   Ghi lại thời gian sửa từng trang. Bản nháp dùng ký hiệu riêng (`[dấu: ...]`, `[chữ ký]`, `[trang xoay]`, dấu `|` ngăn ô bảng):
   đổi hết về quy ước của tệp này. **Không** lấy đầu ra của engine OCR cục bộ làm nháp: đáp án sẽ thiên về lỗi của chính
   engine đang được chấm.
3. **5 trang overlap** (`yes`: T01, T06, T11, T16, T21): người A **gõ từ đầu, không xem nháp** (`Tnn.a.txt`); người B sửa nháp
   như bước 2 (`Tnn.b.txt`). CER giữa hai bản cho biết thiên lệch do neo vào nháp; nếu B bỏ sót nhiều lỗi mà A bắt được thì
   các trang cùng loại `why_chosen` phải gõ từ đầu.
4. Mọi tệp UTF-8, **không BOM**, trong `teams/team1_ocr/gold/transcripts/`.

Lưu ý khi dùng nháp LLM: mô hình từng **bịa nội dung** cho trang mà ảnh không nạp được, và đọc chữ viết tay kém ổn định
(Haiku và Sonnet lệch nhau nhiều nhất ở chữ viết tay, xem `../experiments/03_llm_silver/haiku_vs_sonnet_pages.csv`).
Vì vậy dòng nào cũng phải soát với ảnh, kể cả dòng trông hợp lý.

## Quy tắc gõ (để máy so sánh được)

- **Unicode NFC**: gõ bằng bộ gõ tiếng Việt thông thường là đủ; trước khi lưu chạy
  `python -c "import unicodedata,sys;p=sys.argv[1];t=open(p,encoding='utf-8').read();open(p,'w',encoding='utf-8',newline='\n').write(unicodedata.normalize('NFC',t))" file.txt`.
- **Giữ ngắt dòng** đúng như trên ảnh: mỗi dòng chữ trên trang là một dòng trong file. Không nối dòng,
  không tự sửa lỗi chính tả hay "chuẩn hoá" câu chữ của văn bản gốc (giữ nguyên cả lỗi, như `HỘI HỦ NGHĨA`).
- **Thứ tự đọc**: từ trên xuống, trái sang phải. Với bảng: đi từng hàng của bảng, các ô trong hàng ngăn nhau
  bằng một ký tự tab. Với văn bản 2 cột/tiêu đề 2 bên (quốc hiệu, tên công ty): gõ cột trái trước rồi cột phải.
- **Chữ viết tay**: gõ theo cách đọc tốt nhất của bạn. Phần **không đọc được** viết `[?]` (một `[?]` cho mỗi từ
  hoặc cụm không đọc được). Nếu chỉ chắc một phần: gõ phần chắc và để `[?]` cho phần còn lại.
- **Con dấu**: gõ chữ trong dấu nếu đọc được (đặt trong dòng riêng); chữ bị dấu che mất thì `[?]`.
  Không mô tả hình ảnh (không viết "con dấu tròn đỏ").
- **Chữ ký** và hình/logo không có chữ: bỏ qua; nếu có chữ ký kèm họ tên in thì gõ họ tên.
- **Dấu chấm gạch ngang điền chỗ trống** (`..........`, `__`): thay bằng đúng ba dấu chấm `...`.
- **Số/ngày**: gõ nguyên văn, không đổi định dạng (`10.000.000`, `08/10/2024`).
- **Thông tin cá nhân**: các trang này chứa số CMND/CCCD, điện thoại thật. Gõ đầy đủ vào file đáp án nhưng
  **không** chép chúng ra chat, issue hay báo cáo; thư mục `transcripts/` không được đẩy lên nơi công khai.
- Trang gần như trống: file chứa đúng một dòng `[EMPTY]`.
- Trang bị xoay 90°: gõ theo nội dung (đọc theo chiều đúng) và ghi dòng đầu `[ROTATED]`.

## Đo mức đồng thuận (5 trang overlap)

Với mỗi cặp `Tnn.a.txt` (gõ từ đầu), `Tnn.b.txt` (sửa nháp), tính CER của b so với a (và ngược lại), sau khi chuẩn hoá NFC và gộp khoảng trắng:

```python
import unicodedata, re
from rapidfuzz.distance import Levenshtein
norm = lambda s: re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip()
a, b = norm(open("T01.a.txt", encoding="utf-8").read()), norm(open("T01.b.txt", encoding="utf-8").read())
print("CER(b vs a) =", Levenshtein.distance(a, b) / max(len(a), 1))
```

Ngưỡng tham khảo: trang in <= 1% là ổn; chữ viết tay có thể 5-10% (phần lớn do `[?]`). Chênh lệch lớn hơn nghĩa là
quy tắc ở trên chưa đủ rõ: hai người ngồi lại thống nhất rồi sửa file này. Khi đo CER của engine với gold, các ký hiệu
`[?]`, `[EMPTY]`, `[ROTATED]` bị loại khỏi cả hai phía trước khi so.

## Sau khi gõ xong

Chạy `eval_on_gold.py` (xem mục "Đo trên gold thật" trong RESULTS.md của
`01_engine_bakeoff`) để thay con số pseudo-gold bằng con số trên scan thật.
