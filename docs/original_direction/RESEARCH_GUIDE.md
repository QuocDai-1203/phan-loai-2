# Hướng Dẫn Nghiên Cứu Thực Nghiệm: Phân Loại & Trích Xuất Tài Liệu Doanh Nghiệp Việt Nam
### Chuyên Đề: Fast Decision Models (Jev / Kev), Hybrid OCR & Information Extraction

---

## Mục lục
1. [Tổng quan đề tài & Phạm vi nghiên cứu](#1-tổng-quan-đề-tài--phạm-vi-nghiên-cứu)
2. [Cơ chế System One Models: Jev & Kev](#2-cơ-chế-system-one-models-jev--kev)
3. [So sánh kiến trúc: Phân loại trên Ảnh vs Sau khi OCR](#3-so-sánh-kiến-trúc-phân-loại-trên-ảnh-vs-sau-khi-ocr)
4. [Chiến lược Hybrid OCR: Giải quyết chữ in & chữ viết tay tiếng Việt](#4-chiến-lược-hybrid-ocr-giải-quyết-chữ-in--chữ-viết-tay-tiếng-việt)
5. [Tích hợp Trích xuất Thông tin (IE) với barb-1-ie-vi](#5-tích-hợp-trích-xuất-thông-tin-ie-với-barb-1-ie-vi)
6. [Quy trình Benchmark & Đánh giá 19 Danh Mục (Evaluation Protocol)](#6-quy-trình-benchmark--đánh-giá-19-danh-mục-evaluation-protocol)
7. [Mã nguồn mẫu thực nghiệm (Reference Implementations)](#7-mã-nguồn-mẫu-thực-nghiệm-reference-implementations)

---

## 1. Tổng quan đề tài & Phạm vi nghiên cứu

Bài toán đặt ra cho nghiên cứu sinh là: **Xây dựng một hệ thống xử lý tài liệu doanh nghiệp tự động (Intelligent Document Processing - IDP) có khả năng phân loại chính xác 19 nhóm tài liệu thực tế và trích xuất dữ liệu có cấu trúc phục vụ nhập liệu tự động vào hệ thống ERP / kế toán.**

### Đặc thù tài liệu doanh nghiệp tại Việt Nam:
- **Đa dạng về nguồn gốc**: Văn bản sinh ra từ file Word/Excel (có sẵn digital text), bản scan từ máy photocopy (ảnh nén chất lượng trung bình), ảnh chụp từ điện thoại (nghiêng, bóng mờ, thiếu sáng).
- **Hỗn hợp chữ in và chữ viết tay**: Hợp đồng có chữ ký tươi; biên bản giao nhận có số lượng xăng dầu viết tay; biên bản tự kiểm tra PCCC có các ô tích chọn và nhận xét viết tay.
- **Tính pháp lý cao**: Độ chính xác của việc trích xuất Mã số thuế, Tên pháp nhân, Đại diện pháp luật, Số lượng, Đơn giá yêu cầu tiệm cận 100%. Mọi sai sót đều có thể dẫn đến rủi ro kế toán và thuế.

---

## 2. Cơ chế System One Models: Jev & Kev

### 2.1. Giới hạn của LLM thế hệ cũ (Generative LLMs) trong bài toán phân loại
Khi sử dụng LLM thông thường (như GPT-4, Claude, Llama chat) cho bài toán phân loại:
1. **Lãng phí suy luận**: Mô hình sinh văn bản tự do từng token (Auto-regressive generation), tiêu tốn tài nguyên GPU và thời gian xử lý (1-3 giây/request).
2. **Nguy cơ Hallucination**: Mô hình có thể sinh nhãn không nằm trong danh sách cho trước, hoặc thêm thắt lời giải thích ngoài ý muốn dù đã ép kiểu JSON.
3. **Thiếu Calibrated Probabilities**: Logits của LLM chat thường bị lệch (overconfident hoặc underconfident), khó xác định ngưỡng tin cậy để đưa ra quyết định tự động.

### 2.2. Kiến trúc Fast Decision Model: Jev ([TypeSafe AI](https://typesafe.ai/blog/introducing-system-one-models-and-jev)) & Kev ([jaredpalmer/kev](https://github.com/jaredpalmer/kev))
Lấy cảm hứng từ lý thuyết tư duy của Daniel Kahneman:
- **System Two (Chậm, suy nghĩ sâu, sinh chữ)**: LLM sinh văn bản, CoT, reasoning.
- **System One (Nhanh, phản xạ trực giác, ra quyết định)**: Jev / Kev.

Mô hình System One:
- Nhận đầu vào là trạng thái văn bản (`state`).
- Đánh giá song song các câu hỏi định kiểu mà không sinh text:
  - `Choice`: Chọn 1 trong N danh mục, trả về xác suất của từng lựa chọn (`probabilities`) và điểm tin cậy tổng thể (`confidence`).
  - `Noul`: Đánh giá nhị phân True/False (Yes/No) kèm xác suất calibrated.
  - `Score`: Chấm điểm theo thang bậc (ordinal score).
- **Kev** (xây dựng trên nền **Qwen3.5 / Qwen3.8**) cho phép doanh nghiệp tự host trên máy tính nội bộ (qua vLLM trên Linux hoặc MLX trên Mac), bảo đảm 100% dữ liệu không đi ra ngoài.

---

## 3. So sánh kiến trúc: Phân loại trên Ảnh vs Sau khi OCR

Nghiên cứu sinh cần trả lời câu hỏi cốt lõi: **Nên phân loại tài liệu dựa trên ảnh hay dựa trên văn bản sau khi OCR?**

### Phân tích ưu - nhược điểm:

```text
               ┌─────────────────────────────────────────────────────────────┐
               │                    ĐẦU VÀO: TÀI LIỆU PDF                    │
               └──────────────────────────────┬──────────────────────────────┘
                                              │
                    ┌─────────────────────────┴─────────────────────────┐
                    ▼                                                   ▼
       [PHƯƠNG ÁN A: ẢNH / LAYOUT]                         [PHƯƠNG ÁN B: TEXT SAU OCR]
       • Trích xuất trang 1 thành ảnh                      • Chạy OCR toàn bộ trang
       • Đưa vào Vision Model (ViT / LayoutLM)             • Đưa Text vào Jev / Kev / Text Clf
       ─────────────────────────────────                   ─────────────────────────────────
       [+] Rất nhanh (50-100ms)                            [+] Phân biệt được nội dung pháp lý sâu
       [+] Nhận diện tốt tài liệu có form chuẩn            [+] Không bị nhầm lẫn giữa các loại HĐ
           (ĐKKD có hoa văn, PCCC có bảng, GCN HNH)            cùng form in văn bản hành chính
       [-] Dễ nhầm giữa các Hợp đồng cùng layout           [-] Phụ thuộc độ chính xác của OCR
                                                           [-] Chậm hơn vì phải chờ OCR xong
```

### Kiến trúc Đề xuất Tối ưu: **Cascaded Early-Exit (Phân tầng Thích ứng)**
Để đạt cả 3 mục tiêu: **Chính xác nhất**, **Nhanh nhất** và **Tiết kiệm chi phí nhất**, hệ thống thực hiện theo 3 chặng:

1. **Chặng 1 - Digital Layer Bypass (0ms, 0 VNĐ)**:
   - Dùng `PyMuPDF` kiểm tra xem file PDF có lớp chữ số (Digital Text) hay không.
   - Nếu có $\ge 50$ ký tự có nghĩa, đọc thẳng text tiêu đề.
2. **Chặng 2 - Fast Header / Layout Filter (< 100ms)**:
   - Quét tiêu đề trang đầu (hoặc OCR nhanh 1/3 trang đầu).
   - Nếu tiêu đề khớp từ khóa đặc trưng rõ ràng (ví dụ: *"GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP"*, *"PHIẾU XUẤT KHO"*, *"GIẤY ĐỦ ĐIỀU KIỆN KINH DOANH XĂNG DẦU"*):
     $\rightarrow$ Gán nhãn ngay lập tức, **Fast-Exit, không cần OCR các trang sau**.
3. **Chặng 3 - Fast Decision Model (Kev-4B / Jev) (150-300ms)**:
   - Với các văn bản hành chính phức tạp (Hợp đồng mua vào, Hợp đồng kinh tế, Hợp đồng vận chuyển, Hợp đồng thuê kho, Hợp đồng mượn bồn, Thanh lý hợp đồng):
   - Đưa đoạn trích mở đầu và các căn cứ vào `Kev-4B` câu hỏi `Choice`. Mô hình trả về nhãn chính xác cùng `confidence`.
4. **Chặng 4 - Fallback LLM / VLM Reasoning (Chỉ khi cần)**:
   - Chỉ khi điểm tin cậy của Kev `< 0.65`, hệ thống mới định tuyến sang VLM (Gemini Flash / Qwen2.5-VL) để suy luận ngữ cảnh sâu.

---

## 4. Chiến lược Hybrid OCR: Giải quyết chữ in & chữ viết tay tiếng Việt

Chữ viết tay tiếng Việt (đặc biệt là chữ số, ngày tháng, biển số xe, tên tài xế trên *Biên bản giao nhận* hoặc *Phiếu kiểm tra PCCC*) là thách thức lớn nhất của các OCR truyền thống.

### 4.1. Khai thác Apple Vision Framework qua [iOS-OCR-Server](https://github.com/riddleling/iOS-OCR-Server)
Apple Vision Framework (`VNRecognizeTextRequest`) chạy trên chip Apple Silicon (iPhone/iPad/Mac) sở hữu các lợi thế:
- Mô hình nhận diện chữ tiếng Việt có dấu cực chuẩn xác.
- Tự động nhận diện cả chữ in lẫn chữ viết tay trong cùng một lượt quét (không cần tách vùng thủ công).
- Định vị chính xác tọa độ polygon 4 đỉnh (`rect`) của từng khối chữ, không bị lệch khi văn bản bị xoay nghiêng.
- Tốc độ ~100-250ms/trang trên Neural Engine, hoàn toàn offline, miễn phí bản quyền.

**Cách tích hợp vào Python:**
```python
import requests

def call_ios_ocr(image_bytes: bytes, server_url: str = "http://192.168.1.100:8000/upload"):
    files = {"file": ("document.png", image_bytes, "image/png")}
    headers = {"Accept": "application/json"}
    response = requests.post(server_url, files=files, headers=headers, timeout=30)
    data = response.json()
    return data.get("ocr_result", ""), data.get("ocr_boxes", [])
```

### 4.2. Khắc phục lỗi chữ viết tay khó bằng Vision LLM Crop-Correction
Thay vì gửi toàn bộ trang giấy vào LLM Vision (tốn nhiều token và dễ đọc lướt), giải pháp tối ưu là:
1. Nhận danh sách `ocr_boxes` từ Apple Vision hoặc RapidOCR.
2. Với các ô có độ tự tin thấp hoặc chứa thông tin định danh quan trọng (biển số xe, số lượng lít xăng):
3. Cắt (crop) ảnh cục bộ của riêng ô đó.
4. Gửi ảnh crop nhỏ vào Vision LLM (Gemini 2.5 Flash / Qwen2.5-VL) kèm prompt ngữ cảnh:
   > *"Ảnh crop này chứa số lượng lít xăng dầu viết tay trên biên bản giao nhận. Hãy đọc chính xác con số."*

---

## 5. Tích hợp Trích xuất Thông tin (IE) với barb-1-ie-vi

Nghiên cứu sinh có thể tận dụng mã nguồn và mô hình có sẵn tại `Z:\projects\vocvach\barb-1-ie-vi`:
- Mô hình: **`belumind/barb-1-ie-vi`** (kiến trúc GLiNER fine-tune riêng cho tiếng Việt).
- Khả năng: Trích xuất thực thể (NER) và quan hệ (Relation Extraction) theo danh sách nhãn tùy ý mà không cần huấn luyện lại.

### Quy trình phối hợp:
1. **Đầu vào**: Toàn văn bản của tài liệu đã được phân loại (ví dụ: đã biết đây là `_2. HOP DONG KINH TE`).
2. **Thiết lập schema thực thể**:
   - `tổ chức`: Tên Công ty Bên A, Tên Công ty Bên B.
   - `người`: Ông/Bà đại diện hai bên.
   - `chức vụ`: Giám đốc, Phó giám đốc.
   - `mã số thuế`: MST các bên.
   - `xăng dầu`: Chủng loại (Xăng RON 95-III, Dầu DO 0,05S-II).
   - `số lượng`: Khối lượng m3/tháng.
3. **Mã nguồn gọi trích xuất**:
```python
from gliner import GLiNER

model = GLiNER.from_pretrained("belumind/barb-1-ie-vi")
entities = model.predict_entities(text, labels=[
    "tổ chức", "người", "chức vụ", "mã số thuế", "xăng dầu", "số lượng"
])
```

---

## 6. Quy trình Benchmark & Đánh giá 19 Danh Mục (Evaluation Protocol)

### 6.1. Phân chia tập dữ liệu (Dataset Splitting)
Tập dữ liệu 335 file có độ lệch số lượng mẫu giữa các lớp:
- Lớp nhiều mẫu: `_1. HOP DONG DAI LY NHUONG QUYEN` (25), `9. TỔNG HỢP HỒ SƠ CỬA HÀNG` (25).
- Lớp ít mẫu: `TU K.TRA PCCC- VÂN` (5), `8. CUA HANG - TU K.TRA PCCC- VÂN` (5), `6. HOP DONG THUE KHO- Vi` (6).

**Yêu cầu thực nghiệm**:
- Sử dụng **Stratified 5-Fold Cross Validation** để đảm bảo mọi fold đều có tỷ lệ đại diện của các lớp ít mẫu.
- Không gộp chung các lớp ít mẫu nếu chúng đại diện cho quy trình nghiệp vụ độc lập.

### 6.2. Các bộ chỉ số đánh giá (Evaluation Metrics)
1. **Hiệu năng phân loại (Classification Performance)**:
   - **Macro-F1 Score**: Đo lường công bằng giữa các lớp ít mẫu và nhiều mẫu.
   - **Micro-F1 / Overall Accuracy**.
   - **Confusion Matrix**: Phân tích ma trận nhầm lẫn, đặc biệt giữa các cặp dễ nhầm:
     - `_2. HOP DONG KINH TE` vs `_3. HOP DONG DAU VAO-Diem` vs `_1. HOP DONG DAI LY NHUONG QUYEN`.
     - `8. CUA HANG - TU K.TRA PCCC- VÂN` vs `TU K.TRA PCCC- VÂN`.
2. **Chất lượng xác suất (Calibration Quality)**:
   - **Expected Calibration Error (ECE)** và **Brier Score** của mô hình Jev / Kev.
   - Đánh giá khả năng dự đoán: Khi mô hình tự tin $\ge 90\%$, tỷ lệ chính xác thực tế có đạt $\ge 90\%$ hay không.
3. **Hiệu năng hệ thống (Efficiency & Cost)**:
   - **Latency (ms/document)**: Thời gian xử lý trung bình.
   - **Cost per 1,000 documents**: So sánh giữa chạy Kev local (0đ) vs Gemini API vs GPT-4o.

---

## 7. Mã nguồn mẫu thực nghiệm (Reference Implementations)

Cấu trúc mã nguồn đề xuất trong thư mục `src/`:
```text
sdh-phanloaitailieu/
├── src/
│   ├── ocr/
│   │   ├── digital_reader.py      # PyMuPDF fast reader
│   │   ├── apple_vision_client.py # iOS-OCR-Server client
│   │   └── rapid_ocr_engine.py    # Local ONNX engine
│   ├── classification/
│   │   ├── kev_classifier.py      # Kev / Jev System One engine
│   │   ├── rule_fast_filter.py    # Heuristic layout & header regex
│   │   └── hybrid_pipeline.py     # Cascaded controller
│   └── extraction/
│       └── barb_extractor.py      # GLiNER belumind/barb-1-ie-vi
```
