# Có nên tinh chỉnh (finetune) Kev-0.8B trên dữ liệu của công ty không? - kế hoạch và khuyến nghị

> Viết cho sinh viên tiếp tục đề tài và cho người quyết định. Số đo lấy từ [`RESULTS.md`](RESULTS.md) (cùng thư mục) và thí nghiệm 02; **chưa huấn luyện gì**. Nhãn là nhãn máy (`labels_v2.csv`, sha1[:10] `eb3348713a`). Ngày 2026-10-16.

## 1. Câu hỏi và câu trả lời ngắn

*Hỏi:* Nếu Kev 0.8 phân loại chưa chính xác, có nên chuẩn bị dữ liệu để tinh chỉnh nó với các loại tài liệu hay sai không? Tinh chỉnh trên chính dữ liệu của mình thì nhận diện tài liệu cùng chủng loại có chính xác hơn không?

*Trả lời:*

1. **"Cùng chủng loại" thì thường có, nhưng đó chính là điều khó chứng minh nhất.** Tinh chỉnh trên tài liệu của công ty gần như chắc chắn làm Kev nhận tốt hơn **chính các biểu mẫu/nhà cung cấp đã thấy**. Câu hỏi thật là nó có tốt hơn trên **biểu mẫu/khách hàng chưa thấy** không, và tốt hơn **so với các phương án rẻ hơn đã có**. Với dữ liệu hiện có (237 tài liệu, nhãn do máy), ta chưa đủ để đo điều đó một cách đáng tin.
2. **Đừng làm ngay. Lý do là số đo, không phải nguyên tắc:** (a) Kev (chỉ tên loại) đã đạt 0,962 [0,929; 0,980] trên DEV, chỉ có **9 lỗi**; trần cải thiện là 3,8 điểm; (b) lỗi **không tập trung** theo biểu mẫu/nhà cung cấp (7 cặp nhầm khác nhau trong 9 lỗi), nên không có "mẫu hay sai" rõ để dạy lại; (c) **Qwen3.5-4B đã có và đạt 0,996**, và hệ thống chạy mặc định bằng Qwen, không bằng Kev; (d) điểm yếu thật của Kev - hiệu chỉnh (ECE 0,441) - đã sửa được **không cần tinh chỉnh** (ECE 0,023 bằng một hệ số làm sắc chọn bằng cross-fit); (e) nhãn do máy, nên tinh chỉnh có nguy cơ học lại chính lỗi của máy.
3. **Nên làm gì thay thế, theo thứ tự:** nhân viên kiểm nhãn (T2 của README nhóm 3) -> thu thêm tài liệu của khách hàng/biểu mẫu mới để có tập kiểm thật (T5) -> chỉ khi đó mới chạy thí nghiệm tinh chỉnh dưới giao thức ở §4. Dữ liệu và fold đã chuẩn bị sẵn nên việc này sẽ nhanh khi đến lúc.

## 2. Khi nào tinh chỉnh trên dữ liệu nhà giúp, và khi nào không

| Tình huống | Tinh chỉnh có giúp không? | Vì sao / bằng chứng ở dự án này |
|---|---|---|
| **Cùng biểu mẫu, cùng nhà cung cấp** xuất hiện lặp lại ở khâu vận hành (phiếu xuất kho, đơn đặt hàng của vài khách hàng quen) | **Có, thường nhiều** | Mô hình học đầu thư, bố cục chữ, cách OCR hỏng của chính mẫu đó. Đây là cách TF-IDF đã đạt 0,977 macro-F1 DEV cho 10 loại lớn (01). **Nhưng** số "cùng mẫu" cũng dễ bị phóng đại: 42% tài liệu DEV thuộc nhóm cùng mẫu, nên chia ngẫu nhiên làm điểm cao giả (xem §4). |
| **Loại lớn, nhiều mẫu** | Có, nhưng đã đủ tốt | Loại >= 10 tài liệu: Kev đã đúng >= 93,8% mỗi loại; TF-IDF/luật cũng gần 100%. Lợi ích thêm nhỏ. |
| **Loại hiếm (1-7 tài liệu)** | **Không chắc; có thể có hại** | TF-IDF huấn luyện trên dữ liệu nhà **không bao giờ nhận loại hiếm** (recall 0, 02 §5). Embedding few-shot trên dữ liệu nhà đạt accuracy 0,895 và recall hiếm 0,67 - **thấp hơn Kev zero-shot** (0,962; 0,905). Học từ 1-3 tài liệu dễ quá khớp. Giữ nguyên `--init_from` (không học lại từ đầu) bảo vệ được một phần. |
| **Loại mới sau này** (công ty thêm loại) | **Không** | Mô hình tinh chỉnh bị gắn với taxonomy lúc huấn luyện; loại mới cần dữ liệu mới và huấn luyện lại, trong khi zero-shot chỉ cần thêm tên (T6 trong README nhóm 3). |
| **Dữ liệu ít** (237 tài liệu) | **Khó đo, dễ nhiễu** | Tài liệu Kev tự ghi: với 400 bản ghi, mức tăng trong ví dụ của họ "nằm trong nhiễu"; tăng rõ ở 1.000-5.000 bản ghi. Ta có 237 gốc (377 dòng sau tăng mẫu). |
| **Nhãn do máy** | **Rủi ro vòng tròn** | Nhãn do hai mô hình AI gán theo một hướng dẫn; tinh chỉnh Kev (mô hình AI) trên nhãn đó học **cách gán nhãn của máy**, kể cả lỗi (như `cb8636a17725`, nghi nhãn máy sai: cả Kev và Qwen đều không đồng ý). Điểm cao sau tinh chỉnh có thể chỉ là "khớp máy". Cần nhân viên kiểm trước. |
| **Mô tả dài làm Kev sụp** (0,30) | Tinh chỉnh *có thể* sửa, nhưng không cần | Dùng chỉ-tên-loại đã đạt 0,962; vấn đề được tránh bằng cách viết tiêu chí ngắn. |
| **Muốn bỏ Qwen/Ollama, chỉ chạy Kev** (nhẹ hơn: 1,55 GB so với 3,05 GB VRAM; ~0,3-0,9 s so với ~1,2 s/tài liệu) | **Đây là lý do duy nhất đáng cân nhắc** | Cần Kev tinh chỉnh >= Qwen trên giữ-ra; hiện cách xa 3,4 điểm. Cascade với Kev (0,975) và với Qwen (0,992) chưa tách được trên DEV, nhưng cả hai là số tự chọn ngưỡng trên DEV. |

## 3. So với các lựa chọn rẻ hơn đã có

| Phương án | Đã là "huấn luyện trên dữ liệu nhà"? | Kết quả đã đo (DEV, 237) | Chi phí thêm |
|---|---|---|---|
| Cổng luật từ khóa tiêu đề | Gián tiếp (từ khóa viết sau khi xem mẫu) | Quyết định 76,4% tài liệu, 0 sai | 3 ms |
| TF-IDF + ComplementNB | **Có**, thuần túy | Track S macro-F1 0,977; không nhận loại hiếm | 3 ms, nhỏ |
| Embedding bge-m3 few-shot | **Có** | Accuracy toàn taxonomy 0,895 | 73 ms |
| Qwen3.5-4B zero-shot | Không | 0,996 (236/237) | ~1,2 s, 3,05 GB |
| Kev-0.8B zero-shot (chỉ tên) | Không | 0,962; ECE 0,441 -> **0,023 sau làm sắc** | ~0,3-0,9 s, 1,55 GB |
| Đồng thuận Kev + Qwen | Không | nhận 95,8%, 0 sai (02 §6) | cả hai mô hình |
| **Kev tinh chỉnh** | **Có** | **chưa đo** | huấn luyện + kiểm nhãn + vận hành thêm một mô hình riêng của công ty |

Điểm cần nhớ: "huấn luyện trên dữ liệu nhà" **đã có** trong hệ thống (TF-IDF, embedding), và chính nó cho thấy giới hạn của hướng này ở dữ liệu nhỏ: nó giỏi loại lớn và vô dụng với loại hiếm. Tinh chỉnh Kev khác ở chỗ khởi đầu từ một mô hình đã biết đọc và chỉ điều chỉnh, nhưng nó vẫn chịu hai giới hạn chung: ít mẫu cho loại hiếm, và nhãn do máy.

## 4. Giao thức đánh giá nếu quyết định thử

Mục tiêu duy nhất của thí nghiệm: **Kev tinh chỉnh có hơn Kev gốc (và không kém Qwen quá nhiều) trên tài liệu CHƯA THẤY không?**

1. **Dữ liệu.** Chạy `build_finetune_dataset.py` (đã có): 5 fold theo **nhóm** (hợp của nhóm không cắt và nhóm cùng mẫu), TEST không vào, 31 tài liệu DEV chung nhóm với TEST **phải bỏ** khỏi huấn luyện nếu sau này chấm TEST. Nhãn: dùng nhãn **đã được nhân viên kiểm** (T2); nếu chưa có, ghi "đáp án máy" ở mọi bảng.
2. **Chia.** Group 5-fold trên DEV: huấn luyện trên 4 fold (kể cả tăng mẫu và hard-negative), chấm trên fold giữ ra (**chỉ tài liệu gốc**). Gộp 5 fold = 237 dự đoán mỗi tài liệu đúng một lần. Lặp 3 hạt giống nếu còn ngân sách.
3. **Giữ ra theo nhà cung cấp.** Repo **chưa có** cột nhà cung cấp; nhóm cùng mẫu là xấp xỉ. Cần công ty cung cấp nhà cung cấp/khách hàng cho mỗi tài liệu để chạy "bỏ lại một nhà cung cấp": nếu điểm chỉ tăng ở chia theo nhóm cùng mẫu mà không tăng ở bỏ-nhà-cung-cấp, mô hình mới đang thuộc lòng biểu mẫu.
4. **Hiệu chỉnh.** Khớp nhiệt độ/hệ số làm sắc trên một phần giữ ra riêng (kể cả cho Kev gốc, để so công bằng); không khớp trên fold dùng để chấm.
5. **So sánh bắt buộc**, cùng tài liệu, cặp: Kev gốc (chỉ tên) | Kev gốc + làm sắc | Kev tinh chỉnh | Qwen3.5-4B (cache 02) | TF-IDF/embedding trong cùng group-fold (để biết "dữ liệu nhà" thuần túy làm được gì).
6. **Tiêu chí chấp nhận** (đặt trước khi chạy, cụ thể):
   - accuracy gộp giữ ra của Kev tinh chỉnh hơn Kev gốc **>= +2 điểm**, **cận dưới CI bootstrap cặp > 0** và McNemar p < 0,05;
   - **không thoái lui**: recall loại hiếm (63 tài liệu) không giảm quá 2 điểm (hiện 0,905); không loại nào mất >= 2 tài liệu so với Kev gốc;
   - tự nhận @sai<=1% **>= 0,949** (số của Kev gốc) với <= số lỗi tương ứng;
   - ECE sau khớp trên phần giữ ra <= 0,10;
   - mô hình tinh chỉnh **không tụt** trên tập kiểm hồi quy: 28 lát của tệp ghép (27/28 hiện nay) và TEST (một lần duy nhất, cấu hình đóng băng ghi `dev_selection.json` trước).
   - để *thay* Qwen trong cascade: ngoài các điều trên, phải **không tách được kém** Qwen ở giữ-ra theo nhà cung cấp (hiệu cặp có cận dưới >= -1 điểm).
7. **Cỡ mẫu tối thiểu.** Công thức McNemar của chính `skills/kev-finetune/scripts/plan_size.py` (đã tính lại): phát hiện mức tăng **+3 điểm** với 80% power, 1% tài liệu thoái lui: **~434 tài liệu giữ ra**; với 0,5% thoái lui ~347; **+2 điểm: ~783**; +1 điểm: ~1.568. Hiện có 237. Với 9 lỗi của Kev, kết quả chỉ có ý nghĩa nếu tinh chỉnh sửa >= 6 lỗi mà không làm hỏng tài liệu nào (McNemar chính xác 6-0: p = 0,031; 5-0: p = 0,063). **Vì vậy cần ~430-800 tài liệu có nhãn người kiểm, trong đó có tài liệu của khách hàng chưa thấy**, trước khi một kết luận "có hơn" có giá trị. Loại hiếm: cần >= 10 tài liệu mỗi loại hiếm muốn tuyên bố (hiện 17/32 loại có <= 4).

## 5. Chi phí ước lượng (chưa đo; là ước tính của người viết kế hoạch)

- **Công cụ.** Repo Kev cục bộ có `python -m kev.train --init_from jaredpalmer/kev-0.8b --base Qwen/Qwen3.5-0.8B-Base --lr 2e-5 --batch 1 --accum 8 --dtype bf16 --checkpointing 1` (README Kev: 0,8B vừa GPU 4 GB). **Không dùng** kỹ năng `kev-finetune` chạy trên Modal: nó đẩy tài liệu lên đám mây, trái ràng buộc on-premise.
- **VRAM.** RTX 3060 12 GB đang dùng chung; Ollama giữ `qwen3.5:4b` (~6 GB đã quan sát). LoRA 0,8B bf16 batch 1 cần thêm vài GB (ước lượng 4-6 GB với gradient checkpointing và chuỗi ~1.300 token). Có thể chạy khi Ollama rảnh; không chạy cùng lúc với máy chủ Kev đang phục vụ.
- **Thời gian.** Mỗi fold ~300 dòng x ~1.300 token ≈ 0,4 triệu token mỗi epoch; 5 fold x 2 epoch ≈ 4 triệu token. Giả định (không đo) 1.500-4.000 token/giây trên 3060: ~20-45 phút cho cả 5 fold. Chạy thử **một fold** để đo thực rồi mới chạy cả 5.
- **Rủi ro kỹ thuật cần kiểm trước:** trạng thái ~1.300 token dài hơn phân phối huấn luyện chính của Kev (<= 384 token, một phần tới 7.552); thử cả hai: 2000 ký tự (đúng lúc suy luận) và 1000 ký tự. Phải kiểm Kev tinh chỉnh không tụt khi dùng `permute`/thứ tự lựa chọn khác (thiên vị thứ tự hiện là 8% tài liệu đổi nhãn).
- **Công người lớn nhất không phải GPU:** kiểm nhãn (150-400 tài liệu), thu thêm tài liệu khách hàng mới, và vận hành một mô hình riêng (tải, theo dõi trôi, huấn luyện lại khi thêm loại).

## 6. Khuyến nghị

**Không tinh chỉnh ngay.** Thứ tự đề xuất:

1. (Ngay, rẻ) Nếu muốn dùng Kev làm tầng 3 hoặc tín hiệu đồng thuận: thêm hệ số làm sắc (khớp bằng cross-fit trên DEV, k = 4) vào `KevBackend`/`CascadedClassifier` để ngưỡng tin cậy có nghĩa; **kiểm lại** trên bộ nhãn người kiểm trước khi tin con số 0,023. Không cần huấn luyện.
2. (P0) Nhân viên kiểm nhãn (T2); xem trước `cb8636a17725` và bảy loại có lỗi.
3. (P1) Thu thêm tài liệu khách hàng/biểu mẫu mới (T5), kèm cột nhà cung cấp, để có tập giữ ra thật.
4. Khi (2) và (3) xong và có >= ~430 tài liệu giữ ra: chạy thí nghiệm §4 trên một fold trước, rồi cả 5 fold. Nếu đạt tiêu chí §4.6 thì mới đưa vào cascade; nếu không, giữ Qwen3.5-4B làm tầng 3 và dùng Kev chỉ làm tín hiệu đồng thuận.

**Điều có thể thay đổi khuyến nghị này:** nếu người kiểm nhãn thấy Kev sai có hệ thống ở một nhóm biểu mẫu thực tế của công ty (ví dụ cùng một nhà cung cấp lặp lại hàng trăm lần mỗi tháng), thì tinh chỉnh vào đúng nhóm đó đáng giá hơn nhiều so với các số trung bình ở đây; DEV hiện tại không có hiện tượng đó.
