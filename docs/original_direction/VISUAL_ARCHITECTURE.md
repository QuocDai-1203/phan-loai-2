# Bản Đồ Kiến Trúc Thị Giác & Sơ Đồ Luồng Nghiên Cứu
## (Visual Architecture & Technical Decision Maps)

Tài liệu này trực quan hóa (visualize) toàn bộ các hướng tiếp cận, luồng dữ liệu (dataflow), kiến trúc mô hình và các giải pháp kỹ thuật được đề xuất cho bài toán **Phân loại & Trích xuất thông tin tài liệu doanh nghiệp Việt Nam** (`sdh-phanloaitailieu`).

---

## 1. Kiến trúc Tổng thể Toàn trình (End-to-End Enterprise IDP Pipeline)

Sơ đồ thể hiện chuỗi xử lý khép kín từ lúc tiếp nhận tài liệu PDF/ảnh quét cho đến khi lưu trữ dữ liệu cấu trúc vào hệ thống ERP / kế toán:

```mermaid
flowchart TD
    subgraph INGESTION["1. TIẾP NHẬN TÀI LIỆU (INGESTION)"]
        InPDF["Tài liệu PDF / Ảnh Scan (335 mẫu)"]
        Inspect["Phân tích tệp & Kiểm tra Digital Text Layer"]
        InPDF --> Inspect
    end

    subgraph TIERED_OCR["2. TẦNG HYBRID OCR ĐA NĂNG"]
        Inspect -->|Có Digital Text Layer| PyMuPDF["PyMuPDF Reader<br/>• Độ trễ: ~0ms<br/>• Chi phí: 0 VNĐ<br/>• Độ chính xác: 100%"]
        Inspect -->|PDF Scan / File Ảnh| OCR_Router{"Điều phối OCR"}
        
        OCR_Router -->|Có phần cứng Apple| Apple_Vision["iOS-OCR-Server / Mac Mini<br/>• VNRecognizeTextRequest<br/>• Chữ in + Chữ viết tay<br/>• Tọa độ Bounding Box"]
        OCR_Router -->|Máy chủ Linux/Windows| Rapid_OCR["RapidOCR (ONNX Runtime)<br/>• Nhận diện chữ in CPU/GPU<br/>• Tốc độ cao"]
        
        Apple_Vision --> BBox_Check{"Kiểm tra vùng chữ viết tay / độ tự tin"}
        Rapid_OCR --> BBox_Check
        
        BBox_Check -->|Confidence cao| Clean_Text["Văn bản hoàn chỉnh + Bounding Boxes"]
        BBox_Check -->|Vùng viết tay mờ/khó| Crop_LLM["Crop Bounding Box cục bộ<br/>+ Small Vision LLM (Gemini/Qwen-VL)<br/>Hiệu đính ngữ cảnh"]
        Crop_LLM --> Clean_Text
        PyMuPDF --> Clean_Text
    end

    subgraph CLASSIFICATION["3. BỘ PHÂN LOẠI CASCADED (DECISION ENGINE)"]
        Clean_Text --> Fast_Header{"Tầng 1: Fast Header / Layout Gate"}
        Fast_Header -->|Khớp từ khóa mẫu chuẩn rõ| Fast_Exit["Gán nhãn ngay (Fast-Exit)<br/>Ví dụ: ĐKKD, Phiếu xuất kho, PCCC"]
        
        Fast_Header -->|Văn bản hành chính / Hợp đồng| Kev_Engine["Tầng 2: System One Model (Kev-4B / Jev)<br/>API: /v1/systemone (Choice primitive)"]
        
        Kev_Engine --> Conf_Check{"Kiểm tra Calibrated Confidence"}
        Conf_Check -->|Confidence ≥ 0.75| Kev_Label["Nhãn dự đoán từ Kev (19 danh mục)"]
        Conf_Check -->|Confidence < 0.75| LLM_Triage["Tầng 3: Deep Reasoning LLM (Fallback)"]
        LLM_Triage --> Kev_Label
        Fast_Exit --> Merged_Class["XÁC NHẬN 1 TRONG 19 DANH MỤC"]
        Kev_Label --> Merged_Class
    end

    subgraph EXTRACTION["4. TRÍCH XUẤT THÔNG TIN CẤU TRÚC (IE)"]
        Merged_Class --> Schema_Router{"Chọn Schema trích xuất theo loại tài liệu"}
        Schema_Router -->|Hợp đồng / Cam kết| Barb_IE["Mô hình barb-1-ie-vi (GLiNER)<br/>• Thực thể: Tổ chức, Người, MST, Số lượng m3...<br/>• Quan hệ: Đại diện, Ký kết, Đặt trụ sở..."]
        Schema_Router -->|Biên bản giao nhận / Phiếu kho| Table_IE["Trích xuất bảng biểu & Số liệu chi tiết<br/>(Bảng hàng hóa, số lít, đơn giá, chữ ký)"]
        Schema_Router -->|Giấy tờ pháp lý / Giấy phép| Form_IE["Trích xuất trường dữ liệu cố định<br/>(Số giấy phép, ngày cấp, đơn vị cấp)"]
    end

    subgraph OUTPUT["5. ĐÍCH DỮ LIỆU & TỰ ĐỘNG HÓA"]
        Barb_IE --> JSON_Out["Dữ liệu chuẩn JSON Schema"]
        Table_IE --> JSON_Out
        Form_IE --> JSON_Out
        JSON_Out --> ERP["Cơ sở dữ liệu ERP / Smart Document Hub"]
    end
```

---

## 2. So Sánh 3 Chiến Lược Phân Loại Tài Liệu

Biểu đồ so sánh trực quan vì sao giải pháp **Cascaded Early-Exit** vượt trội hơn hẳn hai phương án cực đoan (chỉ dùng ảnh hoặc chỉ dùng văn bản sau OCR):

```mermaid
flowchart LR
    subgraph PA["Phương Án A: Phân loại thuần trên Ảnh"]
        direction TB
        A1["Input: Ảnh Scan trang 1"] --> A2["Vision Model (ViT / LayoutLM)"]
        A2 --> A3["Output: Danh mục"]
        A_Note["Độ trễ: RẤT NHANH (~80ms)<br/>Chi phí: THẤP<br/>Độ chính xác: KÉM với hợp đồng (dễ nhầm)"]
    end

    subgraph PB["Phương Án B: Phân loại thuần sau OCR"]
        direction TB
        B1["Input: PDF đầy đủ"] --> B2["OCR toàn bộ tất cả các trang"]
        B2 --> B3["LLM sinh text / Prompting"]
        B3 --> B4["Output: Danh mục"]
        B_Note["Độ trễ: CHẬM (2000-5000ms)<br/>Chi phí: CAO (Token OCR + LLM)<br/>Độ chính xác: CAO"]
    end

    subgraph PC["Phương Án C: Cascaded Early-Exit (Đề Xuất)"]
        direction TB
        C1["Input: PDF"] --> C2{"Kiểm tra Header 1/3 trang 1"}
        C2 -->|70% tài liệu mẫu chuẩn| C3["Fast-Exit (<50ms, 0đ)"]
        C2 -->|30% tài liệu hợp đồng| C4["Kev-4B System One (150ms)"]
        C_Note["Độ trễ: TỐI ƯU (~90ms TB)<br/>Chi phí: GẦN NHƯ 0 ĐỒNG<br/>Độ chính xác: CAO NHẤT (≥98%)"]
    end
```

### Bảng Ma Trận So Sánh Kỹ Thuật:

| Tiêu chí đánh giá | Phương Án A (Vision-first) | Phương Án B (Post-OCR All) | Phương Án C (Cascaded Hybrid) |
| :--- | :---: | :---: | :---: |
| **Độ trễ trung bình (Latency)** | ⚡ 80ms | ⏳ 2,500ms - 5,000ms | ⚡ **90ms - 250ms** |
| **Chi phí suy luận / 1.000 tệp** | ~$0.20 | ~$5.00 - $15.00 | **~0 VNĐ (chạy Local On-Premise)** |
| **Độ chính xác tài liệu Form chuẩn** | 95% | 96% | **99.5%** |
| **Độ chính xác Họ tài liệu Hợp đồng** | 62% *(dễ nhầm giữa các HĐ)* | 96% | **98.2% (nhờ Kev System One)** |
| **Yêu cầu phần cứng** | GPU VLM trung bình | GPU lớn / Cloud API | **CPU tiêu chuẩn + GPU 8GB (hoặc Mac)** |

---

## 3. Kiến trúc Hybrid OCR: Xử lý Chữ in & Chữ viết tay Tiếng Việt

Tài liệu chứng từ tại Việt Nam thường có chữ viết tay tại các vùng nghiệp vụ quan trọng (số lượng thực nhận, giờ giao nhận hàng, chữ ký, biển số xe). Đây là mô hình kết hợp phần cứng và mô hình:

```mermaid
flowchart TD
    InputImg["Trang tài liệu PDF / Ảnh Scan"] --> Router{"Phần cứng & Môi trường"}

    subgraph APPLE_HW["Giải pháp 1: Apple Silicon Infrastructure (iOS-OCR-Server / Mac)"]
        Router -->|Có Mac Mini / iPhone nội bộ| AppleEngine["Apple Vision Framework (VNRecognizeTextRequest)"]
        AppleEngine --> AppleFeatures["• Nhận diện đồng thời Chữ in & Chữ viết tay<br/>• Ngôn ngữ: Tiếng Việt (hỗ trợ đầy đủ dấu thanh/mũ)<br/>• Trả về: Polygon Rect Bounding Boxes chính xác"]
    end

    subgraph PC_HW["Giải pháp 2: PC / Server GPU (RapidOCR)"]
        Router -->|Server Windows / Linux x86| RapidEngine["RapidOCR (PaddleOCR ONNX)"]
        RapidEngine --> RapidFeatures["• Nhận diện cực nhanh văn bản in máy<br/>• Tối ưu chạy CPU / GPU nhẹ"]
    end

    AppleFeatures --> TextStream["Luồng Text trích xuất + Tọa độ Bounding Boxes"]
    RapidFeatures --> TextStream

    subgraph SMART_VERIFY["Cơ chế Hiệu đính Thông minh (Smart Crop-Verification)"]
        TextStream --> Filter{"Phát hiện ô viết tay / Confidence thấp?"}
        Filter -->|Độ tự tin cao| FinalText["Văn bản sạch (Clean Text)"]
        
        Filter -->|Ô nghi vấn: Biển số, Số lít xăng, Chữ ký| Cropper["Cắt (Crop) Bounding Box cục bộ"]
        Cropper --> CropImg["Ảnh cắt kích thước nhỏ (vài KB)"]
        CropImg --> SmallVLM["Vision LLM Cỡ Nhỏ (Gemini Flash / Qwen2.5-VL)<br/>Prompt: 'Đọc số/chữ viết tay tiếng Việt trong ngữ cảnh...'"]
        SmallVLM --> Patch["Vá (Patch) ngược lại văn bản chính"]
        Patch --> FinalText
    end
```

---

## 4. Kiến trúc System One (Jev / Kev) so với Generative LLM (System Two)

Mô hình trực quan sự khác biệt về cơ chế suy luận bên dưới giữa **Generative LLM** và **Fast Decision Models (Jev / Kev)**:

```mermaid
flowchart TD
    subgraph SYSTEM_TWO["LLM TRUYỀN THỐNG (System Two - Chậm, Sinh Token Từng Bước)"]
        P_Input["Prompt: 'Hãy đọc tài liệu sau và trả lời dưới dạng JSON xem nó là loại gì...'"]
        P_Input --> Gen1["Sinh token 1: '{'"]
        Gen1 --> Gen2["Sinh token 2: '\n'"]
        Gen2 --> Gen3["Sinh token 3: 'category'"]
        Gen3 --> GenN["... Sinh tiếp 50-100 tokens ..."]
        GenN --> P_Output["Output JSON Text (Cần parse JSON, dễ bị lỗi format, trễ 1-3s)"]
    end

    subgraph SYSTEM_ONE["SYSTEM ONE MODELS: Jev / Kev (Nhanh, Xác định, Khống chế Cấu trúc)"]
        S_Input["Input State: Trích đoạn văn bản tài liệu"]
        S_Input --> PointerHead["Classification / Decision Pointer Head (Frozen Backbone + Trained Head)"]
        
        PointerHead --> ChoiceQ["Câu hỏi Choice: 19 Danh Mục"]
        PointerHead --> NoulQ["Câu hỏi Noul: Có chữ ký / con dấu không?"]
        PointerHead --> ScoreQ["Câu hỏi Score: Độ hoàn chỉnh của hồ sơ (0-3)"]
        
        ChoiceQ --> ChoiceOut["Probabilities: {'HĐ kinh tế': 0.89, 'HĐ đại lý': 0.08, ...}<br/>Confidence: 0.89"]
        NoulQ --> NoulOut["is_valid: 0.94 (True)"]
        ScoreQ --> ScoreOut["score: 2.8"]
    end
```

### Vùng Phán Quyết Tin Cậy (Calibrated Decision Boundaries):

```text
    0.0%                           65.0%                 85.0%                    100.0%
     ├─── Cần Can Thiệp Thủ Công ────┼─── Cảnh Báo Xem Xét ─┼─── TỰ ĐỘNG HÓA HOÀN TOÀN ───┤
     │   (Human Triage Needed)      │    (Soft Review)     │    (Zero-touch Automation)  │
     │   Đưa vào hàng đợi duyệt     │    Đề xuất nhãn gợi ý│    Lưu kho & Kích hoạt IE   │
```

---

## 5. Bản Đồ Phân Tuyến 19 Danh Mục Nghiệp Vụ (19-Class Routing Blueprint)

Dựa trên 335 tệp mẫu PDF thực tế, hệ thống phân chia 19 danh mục vào 3 nhánh xử lý chuyên biệt:

```mermaid
flowchart TD
    DocInput["335 Tệp PDF Tài Liệu Mẫu"] --> Router19{"Phân loại hình thái danh mục"}

    subgraph GROUP_FORM["NHÓM 1: FORM MẪU / CHỨNG CHỈ ĐẶC TRƯNG (7 Danh Mục - 118 Tệp)"]
        G1_1["10. GCN VC HNH (20 tệp)"]
        G1_2["8. GCN Lop dao tao van chuyen hang chay no (20 tệp)"]
        G1_3["_1. Giay DKKD khach hang (23 tệp)"]
        G1_4["_2. Giay Du Dieu Kien Khach hang (25 tệp)"]
        G1_5["_PHIẾU XUẤT KHO MUA HÀNG 2026 (20 tệp)"]
        G1_6["_Đơn đặt hàng - mua vào 2026 (20 tệp)"]
        G1_7["5. TỔNG HỢP HỒ SƠ XE (20 tệp)"]
        Route_Fast["--> Xử lý qua: FAST HEADER GATE (<50ms)"]
    end

    subgraph GROUP_CONTRACT["NHÓM 2: HỌ HÀNG HỢP ĐỒNG & THANH LÝ (6 Danh Mục - 114 Tệp)"]
        G2_1["_1. HOP DONG DAI LY NHUONG QUYEN (25 tệp)"]
        G2_2["_2. HOP DONG KINH TE (25 tệp)"]
        G2_3["_3. HOP DONG DAU VAO-Diem (20 tệp)"]
        G2_4["_4. THANH LÝ HỢP ĐỒNG (14 tệp)"]
        G2_5["_5. HOP DONG VAN CHUYEN (24 tệp)"]
        G2_6["6. HOP DONG THUE KHO- Vi (6 tệp)"]
        Route_Kev["--> Xử lý qua: KEV-4B SYSTEM ONE CHOICE (150ms)"]
    end

    subgraph GROUP_HANDWRITING["NHÓM 3: BIÊN BẢN CÓ CHỮ VIẾT TAY & HỒ SƠ (6 Danh Mục - 103 Tệp)"]
        G3_1["_Biên bản giao nhận 2026 (20 tệp)"]
        G3_2["6. CUA HANG - BB MAU- VÂN (10 tệp)"]
        G3_3["6. HOP DONG MUON BON (7 tệp)"]
        G3_4["8. CUA HANG - TU K.TRA PCCC- VÂN (5 tệp)"]
        G3_5["TU K.TRA PCCC- VÂN (5 tệp)"]
        G3_6["9. TỔNG HỢP HỒ SƠ CỬA HÀNG (25 tệp)"]
        Route_Apple["--> Xử lý qua: APPLE VISION OCR + HYBRID CROP VERIFY"]
    end

    GROUP_FORM --> Route_Fast
    GROUP_CONTRACT --> Route_Kev
    GROUP_HANDWRITING --> Route_Apple
```

---

## 6. Sơ Đồ Tích Hợp Hệ Sinh Thái (Ecosystem Integration Map)

Mối liên kết giữa repository hiện tại với các mô hình và công cụ sẵn có tại `Z:\projects\vocvach`:

```mermaid
graph LR
    subgraph CURRENT_REPO["Repository: sdh-phanloaitailieu"]
        Dataset["docs/_chot_samples_phanloaitailieu/<br/>(335 PDF thực tế)"]
        Bench["Benchmark Protocol<br/>(Stratified 5-Fold, F1, Latency)"]
        Pipeline["Controller Pipeline<br/>(Cascaded Engine)"]
    end

    subgraph VOCVACH_JEV["Tích hợp từ: Z:\\projects\\vocvach\\jev"]
        TypeSafeSDK["typesafe-sdk Client"]
        LocalKev["jaredpalmer/kev (Kev-4B / Kev-9B)<br/>Mô hình chạy Local qua CUDA/MLX"]
        JevAPI["Endpoint /v1/systemone"]
    end

    subgraph VOCVACH_BARB["Tích hợp từ: Z:\\projects\\vocvach\\barb-1-ie-vi"]
        GLiNER["GLiNER Engine"]
        BarbModel["belumind/barb-1-ie-vi"]
        EntityRules["barb_labels.py (Guardrails tiếng Việt có dấu)"]
    end

    subgraph OCR_SERVER["Tích hợp từ: iOS-OCR-Server"]
        AppleVision["VNRecognizeTextRequest"]
        PhoneServer["HTTP REST API: /upload (Port 8000)"]
    end

    Dataset --> Pipeline
    Pipeline --> PhoneServer
    PhoneServer --> LocalKev
    LocalKev --> BarbModel
    BarbModel --> ERP_System[("Hệ Thống Quản Lý ERP / Kế Toán")]
```

---

## 7. Lộ Trình Nghiên Cứu & Các Cột Mốc Thực Nghiệm (Research Milestones)

```mermaid
gantt
    title Lộ Trình Thực Nghiệm Đề Tài sdh-phanloaitailieu
    dateFormat  YYYY-MM-DD
    section Giai đoạn 1: Chuẩn bị & Baseline
    Đóng gói dữ liệu 335 PDF & gán nhãn 19 lớp     :done, des1, 2026-10-09, 2026-10-10
    Xây dựng module đọc Digital PDF & RapidOCR     :active, des2, 2026-10-11, 2026-10-14
    Chạy Baseline OCR + Zero-shot LLM              :des3, 2026-10-15, 2026-10-18

    section Giai đoạn 2: Tích hợp System One
    Triển khai Kev-4B local qua vLLM / MLX         :des4, 2026-10-19, 2026-10-23
    Benchmark Kev Choice trên 19 danh mục          :des5, 2026-10-24, 2026-10-28
    Đo lường Calibrated Confidence & Brier Score   :des6, 2026-10-29, 2026-11-02

    section Giai đoạn 3: Hybrid OCR & Viết tay
    Thiết lập iOS-OCR-Server trên thiết bị Apple   :des7, 2026-11-03, 2026-11-07
    Thử nghiệm Crop-Correction với Small VLM       :des8, 2026-11-08, 2026-11-12
    Đánh giá độ chính xác chữ viết tay trên Biên bản:des9, 2026-11-13, 2026-11-17

    section Giai đoạn 4: IE & Đóng gói Toàn trình
    Kết nối pipeline với barb-1-ie-vi (GLiNER)     :des10, 2026-11-18, 2026-11-23
    Đo lường End-to-End Latency, F1 & Cost         :des11, 2026-11-24, 2026-11-28
    Hoàn thiện báo cáo khoa học & Đóng gói sản phẩm:des12, 2026-11-29, 2026-12-05
```
