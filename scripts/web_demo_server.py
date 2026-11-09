#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
web_demo_server.py
Giao diện Web tương tác trực tiếp kiểm thử trọn gói:
1. Phân loại Cascade 4 Tầng (Luật -> TF-IDF -> LLM Qwen -> Người)
2. Bóc tách trường dữ liệu nghiệp vụ (Field Extraction: Regex + LLM + Expiry)
3. Mạng lưới liên kết hồ sơ chứng từ (Document & Dossier Linking)
4. Human-in-the-Loop Active Learning (Sửa nhãn -> Tự học 2 cấp)
Chạy tại: http://localhost:8089
"""

import sys
import os
from pathlib import Path
import json
import re
import base64
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.classification.doc_classifier import DocumentClassifier
from src.extraction.field_extractor import FieldExtractor, ExtractConfig
from src.extraction.schemas import SUPPORTED_TYPES, field_specs
from src.common.contracts import DocumentSlice, OCRPageResult
from src.ocr.pdf_ocr import ocr_pdf

print("[*] Đang khởi tạo mô hình Phân loại Cascade (Ollama Qwen, th_s=0.60, consensus='s')...")
try:
    clf = DocumentClassifier.from_defaults(
        use_llm=True,
        llm_backend="ollama",
        rule_title_tiebreak=True,
        th_s=0.60,
        consensus="s"
    )
    print("[+] Khởi tạo Bộ phân loại thành công!")
except Exception as e:
    print(f"[!] Khởi tạo với LLM gặp lỗi ({e}), chuyển sang chế độ dự phòng...")
    clf = DocumentClassifier.from_defaults(use_llm=False, rule_title_tiebreak=True, th_s=0.60)

print("[*] Đang khởi tạo Bộ trích xuất trường nghiệp vụ (FieldExtractor)...")
extractor = FieldExtractor(ExtractConfig(use_llm=True, auto_accept_expiry=False))
print("[+] Khởi tạo FieldExtractor thành công!")

FEEDBACK_FILE = PROJECT_ROOT / "data" / "user_feedback.jsonl"
FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)

TAXONOMY_PATH = PROJECT_ROOT / "data" / "taxonomy_v2.json"
ALL_CLASSES = []
try:
    with open(TAXONOMY_PATH, encoding="utf-8") as f:
        tax_data = json.load(f)
        for c in tax_data.get("classes", []):
            ALL_CLASSES.append({"id": c["id"], "name": c.get("name_vi", c["id"])})
except Exception as e:
    print(f"[!] Lỗi nạp taxonomy: {e}")

LEARNED_RULES = []
def load_learned_feedback():
    if not FEEDBACK_FILE.exists():
        return
    try:
        with open(FEEDBACK_FILE, encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                item = json.loads(line)
                label = item.get("corrected_label")
                keyword = item.get("keyword")
                if label and keyword:
                    clf.rules._rules.insert(0, (label, keyword.lower()))
                    LEARNED_RULES.append({"label": label, "keyword": keyword})
        print(f"[+] Đã khôi phục {len(LEARNED_RULES)} luật học từ phản hồi người dùng!")
    except Exception as e:
        print(f"[!] Lỗi khôi phục feedback: {e}")

load_learned_feedback()

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hệ Thống Phân Loại & Bóc Tách Tài Liệu Xăng Dầu</title>
    <style>
        :root {
            --primary: #2563eb;
            --primary-hover: #1d4ed8;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text: #0f172a;
            --border: #e2e8f0;
            --success: #16a34a;
            --danger: #dc2626;
            --warning: #f59e0b;
            --purple: #7e22ce;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 24px;
        }
        .container {
            max-width: 1050px;
            margin: 0 auto;
        }
        .header {
            background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 50%, #38bdf8 100%);
            color: white;
            padding: 26px 32px;
            border-radius: 16px;
            margin-bottom: 24px;
            box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.2);
        }
        .header h1 {
            margin: 0 0 8px 0;
            font-size: 26px;
            font-weight: 800;
        }
        .header p {
            margin: 0;
            opacity: 0.95;
            font-size: 14.5px;
            line-height: 1.5;
        }
        .badges-top {
            display: flex;
            gap: 10px;
            margin-top: 14px;
            flex-wrap: wrap;
        }
        .badge-pill {
            background: rgba(255, 255, 255, 0.2);
            backdrop-filter: blur(4px);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            border: 1px solid rgba(255, 255, 255, 0.3);
        }
        .card {
            background: var(--card-bg);
            border-radius: 14px;
            padding: 24px;
            box-shadow: 0 2px 4px 0 rgba(0, 0, 0, 0.05);
            border: 1px solid var(--border);
            margin-bottom: 24px;
        }
        label {
            display: block;
            font-weight: 700;
            margin-bottom: 8px;
            font-size: 14.5px;
            color: #1e293b;
        }
        .upload-zone {
            border: 2px dashed #93c5fd;
            background: #f0f7ff;
            border-radius: 12px;
            padding: 22px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s ease;
            margin-bottom: 16px;
        }
        .upload-zone:hover {
            background: #e0f2fe;
            border-color: #2563eb;
        }
        .upload-icon {
            font-size: 34px;
            margin-bottom: 6px;
        }
        .upload-title {
            font-size: 15px;
            font-weight: 700;
            color: #1e40af;
        }
        .upload-hint {
            font-size: 13px;
            color: #64748b;
            margin-top: 4px;
        }
        .file-info {
            display: none;
            background: #ecfdf5;
            border: 1px solid #a7f3d0;
            color: #065f46;
            padding: 10px 16px;
            border-radius: 8px;
            font-size: 13.5px;
            margin-bottom: 14px;
            align-items: center;
            justify-content: space-between;
        }
        textarea {
            width: 100%;
            height: 160px;
            padding: 14px;
            border: 1.5px solid var(--border);
            border-radius: 10px;
            font-size: 13.5px;
            font-family: inherit;
            box-sizing: border-box;
            resize: vertical;
            line-height: 1.5;
        }
        textarea:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
        }
        .samples {
            display: flex;
            gap: 8px;
            margin-top: 10px;
            flex-wrap: wrap;
        }
        .sample-chip {
            background: #f1f5f9;
            color: #334155;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12.5px;
            font-weight: 600;
            cursor: pointer;
            border: 1px solid #cbd5e1;
            transition: all 0.2s;
        }
        .sample-chip:hover {
            background: #e2e8f0;
            color: #0f172a;
        }
        .btn-group {
            display: flex;
            gap: 12px;
            margin-top: 16px;
        }
        button {
            background-color: var(--primary);
            color: white;
            border: none;
            padding: 12px 24px;
            font-size: 14.5px;
            font-weight: 700;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }
        button:hover {
            background-color: var(--primary-hover);
        }
        .btn-learn {
            background-color: var(--success);
        }
        .btn-learn:hover {
            background-color: #15803d;
        }
        .spinner {
            display: none;
            width: 16px;
            height: 16px;
            border: 2.5px solid #ffffff;
            border-top: 2.5px solid transparent;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin-left: 10px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        /* Tabs Result */
        .tabs-header {
            display: flex;
            border-bottom: 2px solid var(--border);
            margin-bottom: 20px;
            gap: 8px;
        }
        .tab-btn {
            background: none;
            color: #64748b;
            border: none;
            border-bottom: 3px solid transparent;
            border-radius: 0;
            padding: 10px 18px;
            font-size: 14.5px;
            font-weight: 700;
            cursor: pointer;
            margin-bottom: -2px;
        }
        .tab-btn.active {
            color: var(--primary);
            border-bottom-color: var(--primary);
        }
        .tab-pane {
            display: none;
        }
        .tab-pane.active {
            display: block;
        }

        /* Badges */
        .badge {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 6px;
            font-weight: 800;
            font-size: 13px;
            text-transform: uppercase;
        }
        .badge-rule { background: #dcfce7; color: #15803d; border: 1px solid #86efac; }
        .badge-tfidf { background: #dbeafe; color: #1d4ed8; border: 1px solid #93c5fd; }
        .badge-llm { background: #f3e8ff; color: #7e22ce; border: 1px solid #d8b4fe; }
        .badge-human { background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }

        .res-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 18px;
        }
        .res-item {
            background: #f8fafc;
            padding: 14px 16px;
            border-radius: 10px;
            border: 1px solid var(--border);
        }
        .res-label {
            font-size: 12px;
            color: #64748b;
            margin-bottom: 4px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .res-val {
            font-size: 17px;
            font-weight: 800;
        }

        /* Bảng Extraction */
        .ext-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            font-size: 13.5px;
        }
        .ext-table th, .ext-table td {
            padding: 12px 14px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }
        .ext-table th {
            background: #f1f5f9;
            font-weight: 700;
            color: #334155;
        }
        .ext-table tr:hover {
            background: #f8fafc;
        }
        .tag-source {
            font-size: 11px;
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: 700;
            background: #e2e8f0;
            color: #475569;
        }
        .tag-regex { background: #e0f2fe; color: #0369a1; }
        .tag-llm { background: #f3e8ff; color: #6b21a8; }
        .tag-vlm { background: #fef3c7; color: #92400e; }

        /* Linking Cards */
        .link-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 16px;
            margin-top: 14px;
        }
        .link-card {
            background: #f0fdf4;
            border: 1.5px solid #bbf7d0;
            border-radius: 12px;
            padding: 16px;
        }
        .link-title {
            font-weight: 800;
            font-size: 14.5px;
            color: #166534;
            display: flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 8px;
        }
        .link-body {
            font-size: 13.5px;
            color: #14532d;
            line-height: 1.5;
        }

        /* Human Review */
        .feedback-section {
            margin-top: 24px;
            padding: 20px;
            background: #fdf4ff;
            border: 1.5px solid #f0abfc;
            border-radius: 12px;
        }
        .feedback-title {
            font-size: 16px;
            font-weight: 800;
            color: #86198f;
            margin-bottom: 12px;
        }
        select {
            padding: 10px 14px;
            border-radius: 8px;
            border: 1.5px solid #d8b4fe;
            background: white;
            font-size: 14px;
            color: #3b0764;
            flex: 1;
            min-width: 260px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛢️ Hệ Thống Phân Loại & Bóc Tách Tài Liệu Xăng Dầu</h1>
            <p>Hệ thống tự động hóa hoàn chỉnh: Phân loại Cascade 4 Tầng + Bóc tách trường nghiệp vụ + Liên kết chứng từ (Human-in-the-Loop)</p>
            <div class="badges-top">
                <span class="badge-pill">⚡ Tầng 1: Cổng Luật (Rule Gate)</span>
                <span class="badge-pill">📊 Tầng 2: TF-IDF (th_s = 0.60)</span>
                <span class="badge-pill">🧠 Tầng 3: Qwen LLM (consensus='s')</span>
                <span class="badge-pill">📑 Bóc tách 21 loại văn bản</span>
                <span class="badge-pill">🔗 Liên kết Hợp đồng & Phương tiện</span>
            </div>
        </div>

        <div class="card">
            <label>1. Tải lên tệp tài liệu (.pdf, .txt, .json):</label>
            <div class="upload-zone" id="dropZone" onclick="document.getElementById('fileInput').click()">
                <div class="upload-icon">📂</div>
                <div class="upload-title">Nhấp để chọn tệp PDF / TXT / JSON hoặc kéo thả vào đây</div>
                <div class="upload-hint">Hỗ trợ tệp scan hóa đơn, phiếu xuất kho, đơn đặt hàng, giấy chứng nhận bán lẻ...</div>
                <input type="file" id="fileInput" style="display: none;" accept=".pdf,.txt,.json" onchange="handleFileSelect(this.files)">
            </div>

            <div class="file-info" id="fileInfo">
                <span id="fileInfoText">Đã chọn: filename.pdf</span>
                <span style="cursor: pointer; font-weight: bold;" onclick="clearFile(event)">✕ Bỏ chọn</span>
            </div>

            <label for="docText">2. Hoặc dán trực tiếp nội dung văn bản OCR vào đây:</label>
            <textarea id="docText" placeholder="Nội dung văn bản bóc tách hoặc dán trực tiếp tại đây..."></textarea>
            
            <div style="margin-top: 12px;">
                <span style="font-size: 13px; color: #64748b; font-weight: 700;">Mẫu kiểm thử nhanh:</span>
                <div class="samples">
                    <span class="sample-chip" onclick="loadSample(1)">📋 Mẫu 1: Phiếu xuất kho DO</span>
                    <span class="sample-chip" onclick="loadSample(2)">📜 Mẫu 2: GCN đủ điều kiện bán lẻ (Có hạn)</span>
                    <span class="sample-chip" onclick="loadSample(3)">📦 Mẫu 3: Đơn đặt hàng xăng RON 95</span>
                    <span class="sample-chip" onclick="loadSample(4)">🚛 Mẫu 4: Biên bản giao nhận hàng</span>
                </div>
            </div>

            <div class="btn-group">
                <button id="processBtn" onclick="runProcess()">
                    <span>Phân Loại & Bóc Tách Toàn Diện</span>
                    <div class="spinner" id="spinner"></div>
                </button>
            </div>
        </div>

        <!-- VÙNG KẾT QUẢ TÍCH HỢP -->
        <div class="card" id="resultCard" style="display: none;">
            <div class="tabs-header">
                <button class="tab-btn active" onclick="switchTab('tabClassify')">1. Kết quả Phân loại</button>
                <button class="tab-btn" onclick="switchTab('tabExtract')">2. Dữ liệu Bóc tách</button>
                <button class="tab-btn" onclick="switchTab('tabLinks')">3. Mạng lưới Liên kết (Links)</button>
            </div>

            <!-- TAB 1: PHÂN LOẠI -->
            <div class="tab-pane active" id="tabClassify">
                <div class="res-grid">
                    <div class="res-item">
                        <div class="res-label">Loại tài liệu nhận diện</div>
                        <div class="res-val" id="catVal" style="color: var(--primary);">UNKNOWN</div>
                    </div>
                    <div class="res-item">
                        <div class="res-label">Tầng chốt quyết định</div>
                        <div class="res-val" id="tierVal"><span class="badge badge-rule">rule</span></div>
                    </div>
                    <div class="res-item">
                        <div class="res-label">Độ tin cậy</div>
                        <div class="res-val" id="confVal">90.0%</div>
                    </div>
                    <div class="res-item">
                        <div class="res-label">Thời gian phân loại</div>
                        <div class="res-val" id="timeVal">2.5 ms</div>
                    </div>
                </div>

                <div id="decisionAlert" style="padding: 14px 18px; border-radius: 10px; font-size: 14px; margin-bottom: 14px;"></div>
                <div id="evidenceAlert" style="padding: 12px 16px; border-radius: 8px; font-size: 13.5px; background: #fffbeb; border: 1px solid #fef3c7; color: #92400e;"></div>

                <!-- TẦNG 4 HUMAN FEEDBACK -->
                <div class="feedback-section">
                    <div class="feedback-title">🛠️ Tầng 4: Chuyên viên Thẩm định & Tự Động Học Lại (Human-in-the-Loop)</div>
                    <p style="font-size: 13.5px; color: #701a75; margin-top: 0;">Nếu máy đoán sai hoặc cần người duyệt, bạn chọn loại đúng bên dưới và bấm nút "Dạy lại hệ thống".</p>
                    <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
                        <select id="correctCategorySelect"></select>
                        <button class="btn-learn" id="learnBtn" onclick="submitCorrection()">
                            <span>Dạy Lại Hệ Thống</span>
                            <div class="spinner" id="learnSpinner"></div>
                        </button>
                    </div>
                    <div id="learningStatus" style="display: none; margin-top: 12px; padding: 12px; border-radius: 8px; background: #ecfdf5; border: 1px solid #a7f3d0; color: #065f46; font-size: 13.5px;"></div>
                </div>
            </div>

            <!-- TAB 2: BÓC TÁCH TRƯỜNG -->
            <div class="tab-pane" id="tabExtract">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <div style="font-weight: 700; font-size: 15px; color: #1e293b;">
                        Trạng thái bóc tách: <span id="extStatusBadge" class="badge badge-rule">OK</span>
                    </div>
                    <div id="expiryNotice" style="font-size: 13px; font-weight: 600;"></div>
                </div>

                <table class="ext-table">
                    <thead>
                        <tr>
                            <th style="width: 28%;">Trường nghiệp vụ</th>
                            <th style="width: 52%;">Giá trị bóc tách</th>
                            <th style="width: 20%;">Nguồn trích xuất</th>
                        </tr>
                    </thead>
                    <tbody id="extTableBody">
                    </tbody>
                </table>
            </div>

            <!-- TAB 3: LIÊN KẾT HỒ SƠ -->
            <div class="tab-pane" id="tabLinks">
                <p style="font-size: 14px; color: #475569; margin-top: 0;">Các mắt xích thông tin móc nối tài liệu này với các thực thể nghiệp vụ khác trong doanh nghiệp:</p>
                <div class="link-grid" id="linkCards">
                </div>
            </div>
        </div>
    </div>

    <script>
        const ALL_CLASSES = """ + json.dumps(ALL_CLASSES, ensure_ascii=False) + """;
        let currentFilename = "input.txt";

        // Khởi tạo dropdown lớp
        window.onload = function() {
            const sel = document.getElementById('correctCategorySelect');
            ALL_CLASSES.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.id;
                opt.innerText = `${c.name} (${c.id})`;
                sel.appendChild(opt);
            });
        };

        function switchTab(tabId) {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById(tabId).classList.add('active');
        }

        const SAMPLES = {
            1: `PHIẾU XUẤT KHO THÀNH PHẨM
VHSX
Ngày: 03/01/2026
Ký hiệu: BSR/PXK/DO
Số: 2600238
Đơn vị xuất: Công ty cổ phần Lọc hoá dầu Bình Sơn (BSR)
Đơn vị nhận hàng: Công ty TNHH Thương mại và Dịch vụ tổng hợp Hoà Khánh
Hợp đồng số: 1871/HĐKT/BSR-HOAKHANH/2026 ngày 31 tháng 12 năm 2025
Lệnh xuất hàng số: 28/LXHXB-DO-030126-13-0(8000145400)
Xuất tại bồn: TK-5207C
Biển số xe: 77R03562
Mặt hàng: Nhiên liệu điêzen (DO 0,05S)
Số lượng m3 ở 15°C: 40.469
Số lượng tấn: 33.573
Số lượng m3 thực tế: 41.025
Số chứng thư chất lượng: DO-195-202512310401`,

            2: `CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
SỞ CÔNG THƯƠNG TỈNH ĐỒNG NAI
GIẤY CHỨNG NHẬN ĐỦ ĐIỀU KIỆN BÁN LẺ XĂNG DẦU
Số: 125/GCN-SCT
Cấp lần đầu: Ngày 15 tháng 01 năm 2023
Cấp lại lần thứ: 01
Tên cửa hàng: CỬA HÀNG XĂNG DẦU SỐ 9
Địa chỉ: Số 45 Quốc lộ 1A, Phường Tân Biên, TP Biên Hòa, Đồng Nai
Thương nhân chủ sở hữu: Công ty Cổ phần Xăng dầu Dầu khí Đồng Nai
Thương nhân cung cấp xăng dầu: Tổng Công ty Dầu Việt Nam - CTCP (PVOIL)
Giấy chứng nhận này có giá trị đến hết ngày 15 tháng 01 năm 2028.`,

            3: `CÔNG TY CỔ PHẦN XĂNG DẦU DẦU KHÍ ĐỒNG NAI
ĐƠN ĐẶT HÀNG
Số: ĐH-2601-0002
Ngày đặt: 10/01/2026
Bên đặt hàng: Cửa hàng bán lẻ xăng dầu Trảng Bom
Nhà cung cấp: Tổng Công ty Dầu Việt Nam (PVOIL)
Căn cứ Hợp đồng mua bán số: HĐ-088/2025/PVOIL
Danh mục đặt hàng:
- Xăng RON 95-III: 20.000 lít
- Dầu DO 0.05S: 10.000 lít
Phương thức giao nhận: Nhận tại kho Nhà Bè bằng xe bồn 60C-987.65
Tổng giá trị tạm tính: 590.000.000 VNĐ`,

            4: `CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
BIÊN BẢN GIAO NHẬN HÀNG HÓA
Hôm nay, ngày 05 tháng 02 năm 2026, tại Kho xăng dầu Nhà Bè.
Bên giao: Tổng Công ty Dầu Việt Nam (PVOIL)
Bên nhận: Chi nhánh Xăng dầu Miền Đông
Số biên bản: BBGN-260205-01
Biển số phương tiện: 51D-882.19
Đã tiến hành bàn giao 30.000 lít xăng E5 RON 92.
Kiểm tra niêm phong kẹp chì: Còn nguyên vẹn đúng quy chuẩn.`
        };

        function loadSample(id) {
            document.getElementById('docText').value = SAMPLES[id];
            currentFilename = id === 2 ? "GCN_DDK_BAN_LE_15.01.2028.pdf" : `sample_${id}.txt`;
            clearFile();
        }

        function handleFileSelect(files) {
            if (!files || !files.length) return;
            const file = files[0];
            currentFilename = file.name;
            const ext = file.name.split('.').pop().toLowerCase();

            const fileInfo = document.getElementById('fileInfo');
            const fileInfoText = document.getElementById('fileInfoText');
            fileInfo.style.display = 'flex';
            fileInfoText.innerText = `📄 Đã chọn: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;

            if (ext === 'pdf') {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const base64Data = e.target.result.split(',')[1];
                    document.getElementById('docText').value = `[ĐÃ TẢI TỆP PDF: ${file.name}]\\nHệ thống sẽ tự động bóc tách chữ từ PDF khi bấm nút bên dưới.`;
                    document.getElementById('docText').dataset.pdfBase64 = base64Data;
                };
                reader.readAsDataURL(file);
            } else {
                delete document.getElementById('docText').dataset.pdfBase64;
                const reader = new FileReader();
                reader.onload = function(e) {
                    document.getElementById('docText').value = e.target.result;
                };
                reader.readAsText(file, 'utf-8');
            }
        }

        function clearFile(event) {
            if (event) event.stopPropagation();
            document.getElementById('fileInput').value = '';
            document.getElementById('fileInfo').style.display = 'none';
            delete document.getElementById('docText').dataset.pdfBase64;
        }

        async function runProcess() {
            const text = document.getElementById('docText').value.trim();
            const pdfBase64 = document.getElementById('docText').dataset.pdfBase64;

            if (!text && !pdfBase64) {
                alert('Vui lòng chọn tệp PDF / văn bản hoặc dán nội dung cần kiểm thử!');
                return;
            }

            const btn = document.getElementById('processBtn');
            const spinner = document.getElementById('spinner');
            btn.disabled = true;
            spinner.style.display = 'inline-block';
            document.getElementById('learningStatus').style.display = 'none';

            try {
                const resp = await fetch('/api/process', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        text: text,
                        pdf_base64: pdfBase64,
                        filename: currentFilename
                    })
                });
                const res = await resp.json();

                if (res.status === 'error') {
                    alert('Lỗi xử lý: ' + res.error);
                    return;
                }

                document.getElementById('resultCard').style.display = 'block';

                // 1. Phân loại
                document.getElementById('catVal').innerText = res.classification.category || 'UNKNOWN';
                const tierEl = document.getElementById('tierVal');
                tierEl.innerHTML = `<span class="badge badge-${res.classification.tier}">${res.classification.tier}</span>`;
                document.getElementById('confVal').innerText = (res.classification.confidence * 100).toFixed(1) + '%';
                document.getElementById('timeVal').innerText = res.classification.processing_time_ms.toFixed(1) + ' ms';

                const decAlert = document.getElementById('decisionAlert');
                if (res.classification.decision === 'auto_file') {
                    decAlert.style.background = '#ecfdf5';
                    decAlert.style.border = '1px solid #a7f3d0';
                    decAlert.style.color = '#065f46';
                    decAlert.innerHTML = `<strong>✅ TỰ ĐỘNG XẾP HỒ SƠ (auto_file):</strong> Máy tự tin 100%, không cần con người xem xét.`;
                } else {
                    decAlert.style.background = '#fef2f2';
                    decAlert.style.border = '1px solid #fecaca';
                    decAlert.style.color = '#991b1b';
                    decAlert.innerHTML = `<strong>⚠️ CHUYỂN NGƯỜI DUYỆT (needs_human):</strong> Lý do: ${res.classification.reasons.join(', ')} | Gợi ý: <strong>${res.classification.suggested_category || 'Không có'}</strong>`;
                }

                document.getElementById('evidenceAlert').innerHTML = `<strong>Căn cứ phân loại:</strong> ${res.classification.evidence || 'Phù hợp đặc trưng từ vựng và ngữ nghĩa'}`;

                if (res.classification.category && res.classification.category !== 'UNKNOWN') {
                    document.getElementById('correctCategorySelect').value = res.classification.category;
                }

                // 2. Bóc tách
                const tbody = document.getElementById('extTableBody');
                tbody.innerHTML = '';
                const ext = res.extraction;

                if (ext && ext.fields && Object.keys(ext.fields).length > 0) {
                    document.getElementById('extStatusBadge').innerText = ext.status.toUpperCase();
                    document.getElementById('extStatusBadge').className = ext.status === 'ok' ? 'badge badge-rule' : 'badge badge-human';

                    for (const [k, v] of Object.entries(ext.fields)) {
                        const tr = document.createElement('tr');
                        const src = (ext.sources && ext.sources[k]) ? ext.sources[k] : 'rule';
                        tr.innerHTML = `
                            <td><strong>${k}</strong></td>
                            <td style="color: #0f172a; font-weight: 600;">${v !== null ? v : '<span style="color:#94a3b8; font-weight:normal;">null</span>'}</td>
                            <td><span class="tag-source tag-${src}">${src}</span></td>
                        `;
                        tbody.appendChild(tr);
                    }
                } else {
                    document.getElementById('extStatusBadge').innerText = 'SKIPPED';
                    document.getElementById('extStatusBadge').className = 'badge badge-human';
                    tbody.innerHTML = `<tr><td colspan="3" style="text-align:center; color:#64748b;">Chưa có schema bóc tách hoặc loại tài liệu này được cấu hình bỏ qua bóc tách.</td></tr>`;
                }

                // Cảnh báo hạn
                const expNotice = document.getElementById('expiryNotice');
                if (ext && ext.expiry_suggestion) {
                    expNotice.innerHTML = `⏳ <span style="color:#b45309;">Ngày hết hạn đề xuất: <strong>${ext.expiry_suggestion}</strong></span>`;
                } else {
                    expNotice.innerHTML = '';
                }

                // 3. Liên kết (Links)
                const linkBox = document.getElementById('linkCards');
                linkBox.innerHTML = '';
                const links = res.links || [];

                if (links.length > 0) {
                    links.forEach(l => {
                        const card = document.createElement('div');
                        card.className = 'link-card';
                        card.innerHTML = `
                            <div class="link-title">${l.icon} ${l.title}</div>
                            <div class="link-body">
                                <div>Mã liên kết: <strong>${l.code}</strong></div>
                                <div style="font-size: 12px; color: #166534; margin-top: 4px;">${l.desc}</div>
                            </div>
                        `;
                        linkBox.appendChild(card);
                    });
                } else {
                    linkBox.innerHTML = '<div style="color:#64748b; font-size:13.5px;">Chưa tìm thấy mã liên kết (Số hợp đồng / Biển số xe) trong văn bản này.</div>';
                }

            } catch (err) {
                alert('Lỗi kết nối máy chủ: ' + err);
            } finally {
                btn.disabled = false;
                spinner.style.display = 'none';
            }
        }

        async function submitCorrection() {
            const text = document.getElementById('docText').value.trim();
            const correctedLabel = document.getElementById('correctCategorySelect').value;
            if (!text || !correctedLabel) {
                alert('Vui lòng kiểm tra lại nội dung và loại tài liệu!');
                return;
            }

            const btn = document.getElementById('learnBtn');
            const spinner = document.getElementById('learnSpinner');
            const statusEl = document.getElementById('learningStatus');

            btn.disabled = true;
            spinner.style.display = 'inline-block';
            statusEl.style.display = 'none';

            try {
                const resp = await fetch('/api/feedback', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text, corrected_label: correctedLabel })
                });
                const res = await resp.json();

                if (res.status === 'ok') {
                    statusEl.style.display = 'block';
                    statusEl.innerHTML = `🎉 <strong>Dạy lại thành công!</strong><br>
                    • <strong>Tầng 1:</strong> Đã ghi nhận từ khóa tiêu đề <code>"${res.learned_keyword}"</code>.<br>
                    • <strong>Tầng 2:</strong> Đã cập nhật ma trận xác suất TF-IDF.<br>
                    ➔ <em>Bấm nút <strong>"Phân Loại & Bóc Tách"</strong> ở trên để kiểm chứng: Máy sẽ tự động nhận diện chuẩn xác!</em>`;
                } else {
                    alert('Lỗi: ' + res.error);
                }
            } catch (err) {
                alert('Lỗi: ' + err);
            } finally {
                btn.disabled = false;
                spinner.style.display = 'none';
            }
        }
    </script>
</body>
</html>
"""

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/process":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)

            text = data.get("text", "")
            pdf_base64 = data.get("pdf_base64")
            filename = data.get("filename", "document.pdf")

            # Nếu người dùng tải PDF lên, trích xuất text qua PyMuPDF
            if pdf_base64:
                try:
                    import fitz
                    pdf_bytes = base64.b64decode(pdf_base64)
                    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                    extracted_pages = []
                    for page in doc:
                        extracted_pages.append(page.get_text() or "")
                    text = "\n".join(extracted_pages).strip()
                except Exception as e:
                    print(f"[!] Lỗi đọc PDF: {e}")

            if not text:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "error": "Văn bản rỗng hoặc không đọc được."}).encode("utf-8"))
                return

            t0 = time.perf_counter()
            # 1. Phân loại Cascade 4 tầng
            cls_res, tr = clf.classify_text(text, slice_id="web_demo")
            cat = cls_res.predicted_category
            decision = "needs_human" if cls_res.requires_human_review or cls_res.tier == "human" else "auto_file"
            reasons = [cls_res.abstain_reason] if cls_res.abstain_reason else []

            # 2. Bóc tách trường dữ liệu
            ext_data = {}
            ext_status = "skipped"
            ext_sources = {}
            expiry_sugg = None

            if cat in SUPPORTED_TYPES:
                try:
                    page = OCRPageResult(page_number=1, width=1000, height=1400, full_text=text, ocr_engine="web_ocr", latency_ms=10.0)
                    sl = DocumentSlice(slice_id="web_slice", doc_id="web_doc", start_page=1, end_page=1, page_count=1, pages=[page], combined_text=text)
                    ext_res = extractor.extract(sl, cat, filename=filename)
                    ext_status = ext_res.status
                    ext_data = {k: v for k, v in ext_res.entity_dict.items() if not k.startswith("_")}
                    ext_sources = ext_res.entity_dict.get("_sources", {})
                    expiry_dict = ext_res.entity_dict.get("_expiry_suggestion", {})
                    if expiry_dict:
                        expiry_sugg = next(iter(expiry_dict.values()), None)
                except Exception as ex_ext:
                    print(f"[!] Lỗi bóc tách: {ex_ext}")
                    ext_status = "error"

            # 3. Phân tích Mạng lưới liên kết (Links)
            links = []
            if ext_data.get("hop_dong_can_cu") or ext_data.get("so_hop_dong") or ext_data.get("hop_dong_goc_so"):
                hd_val = ext_data.get("hop_dong_can_cu") or ext_data.get("so_hop_dong") or ext_data.get("hop_dong_goc_so")
                links.append({
                    "icon": "📑",
                    "title": "Liên kết Hợp đồng Gốc",
                    "code": str(hd_val),
                    "desc": "Móc nối chứng từ này vào Hồ sơ Hợp đồng kinh tế tương ứng."
                })
            if ext_data.get("bien_so_phuong_tien") or ext_data.get("bien_so"):
                bs_val = ext_data.get("bien_so_phuong_tien") or ext_data.get("bien_so")
                links.append({
                    "icon": "🚛",
                    "title": "Liên kết Phương tiện Xe bồn",
                    "code": str(bs_val),
                    "desc": "Móc nối với Đăng kiểm, PCCC và Giấy phép vận chuyển hàng nguy hiểm của xe."
                })
            if ext_data.get("so_phieu") or ext_data.get("so_hoa_don") or ext_data.get("so_bien_ban"):
                doc_code = ext_data.get("so_phieu") or ext_data.get("so_hoa_don") or ext_data.get("so_bien_ban")
                links.append({
                    "icon": "🔢",
                    "title": "Mã định danh Chứng từ Kế toán",
                    "code": str(doc_code),
                    "desc": "Dùng để đối soát 3 bên giữa Kho - Vận tải - Kế toán doanh nghiệp."
                })
            if ext_data.get("so_chung_thu_chat_luong"):
                links.append({
                    "icon": "🧪",
                    "title": "Chứng thư Chất lượng Lô hàng",
                    "code": str(ext_data.get("so_chung_thu_chat_luong")),
                    "desc": "Móc nối kết quả đo lường và kiểm nghiệm chất lượng xăng dầu."
                })

            resp_payload = {
                "status": "ok",
                "classification": {
                    "category": cat,
                    "tier": cls_res.tier,
                    "confidence": cls_res.confidence,
                    "processing_time_ms": (time.perf_counter() - t0) * 1000,
                    "decision": decision,
                    "reasons": reasons,
                    "suggested_category": cls_res.suggested_category,
                    "evidence": cls_res.evidence,
                },
                "extraction": {
                    "status": ext_status,
                    "fields": ext_data,
                    "sources": ext_sources,
                    "expiry_suggestion": expiry_sugg
                },
                "links": links
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(resp_payload, ensure_ascii=False).encode("utf-8"))

        elif self.path == "/api/feedback":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)
            text = data.get("text", "").strip()
            corrected_label = data.get("corrected_label", "").strip()

            if not text or not corrected_label:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "error": "Thiếu text hoặc corrected_label"}).encode("utf-8"))
                return

            try:
                raw_lines = [line.strip().lower() for line in text[:1500].splitlines() if len(line.strip()) >= 5]
                learned_keyword = ""
                for line in raw_lines[:8]:
                    if any(w in line for w in ["biên bản", "hợp đồng", "phiếu", "giấy", "chứng nhận", "đơn", "hóa đơn", "công văn"]):
                        learned_keyword = line
                        break
                if not learned_keyword and raw_lines:
                    learned_keyword = raw_lines[0]
                if not learned_keyword:
                    learned_keyword = text[:60].strip().lower()

                clf.rules._rules.insert(0, (corrected_label, learned_keyword))

                if clf.tfidf is not None and hasattr(clf.tfidf, "model") and hasattr(clf.tfidf, "vectorizer"):
                    try:
                        X = clf.tfidf.vectorizer.transform([text])
                        y = np.array([corrected_label])
                        if corrected_label in clf.tfidf.classes:
                            clf.tfidf.model.partial_fit(X, y)
                    except Exception as ex_tfidf:
                        print(f"[!] TF-IDF partial_fit: {ex_tfidf}")

                record = {
                    "corrected_label": corrected_label,
                    "keyword": learned_keyword,
                    "text_snippet": text[:300]
                }
                with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")

                resp_payload = {
                    "status": "ok",
                    "learned_keyword": learned_keyword,
                    "label": corrected_label
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(resp_payload, ensure_ascii=False).encode("utf-8"))

            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def run(port=8089):
    server_address = ("", port)
    httpd = HTTPServer(server_address, RequestHandler)
    print(f"\n" + "=" * 65)
    print(f"[*] WEB DEMO SERVER ĐANG CHẠY TẠI: http://localhost:{port}")
    print(f"[*] HỖ TRỢ: PHÂN LOẠI 4 TẦNG + BÓC TÁCH TRƯỜNG + LIÊN KẾT CHỨNG TỪ")
    print(f"[*] KÍCH HOẠT: TẦNG 4 HUMAN-IN-THE-LOOP ACTIVE LEARNING")
    print(f"=" * 65 + "\n")
    httpd.serve_forever()

if __name__ == "__main__":
    run()
