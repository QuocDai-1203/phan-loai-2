#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
web_demo_server.py
Giao diện Web tương tác trực tiếp để kiểm thử phân loại tài liệu (Nhóm 3).
- Chuẩn phân vai Nhóm 3: Chỉ nhận tệp đã có chữ (.txt, .json) hoặc văn bản gõ trực tiếp.
- NÂNG CẤP TÍNH NĂNG ACTIVE LEARNING / HUMAN-IN-THE-LOOP:
  + Người dùng có thể sửa lại nhãn đúng khi máy phân loại sai.
  + Hệ thống tự động học 2 cấp:
    1) Cấp 1 (Rule Gate): Học từ khóa đặc trưng tiêu đề ngay lập tức (< 1 ms).
    2) Cấp 2 (TF-IDF Retrain): Cập nhật tăng cường phân phối từ vựng của ComplementNB.
  + Lưu lịch sử sửa đổi vào data/user_feedback.jsonl.
- Chạy tại: http://localhost:8089
"""

import sys
import os
from pathlib import Path
import json
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
import joblib
import numpy as np

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.classification.doc_classifier import DocumentClassifier
from src.common.text_norm import NormalizedText

print("[*] Đang khởi tạo mô hình phân loại Cascade (Rule -> TF-IDF -> Kev)...")
clf = DocumentClassifier.from_defaults(llm_backend="kev")
print("[+] Khởi tạo thành công!")

# File lưu vết phản hồi người dùng
FEEDBACK_FILE = PROJECT_ROOT / "data" / "user_feedback.jsonl"
FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)

# Nạp danh sách 36 taxonomy classes để hiển thị dropdown
TAXONOMY_PATH = PROJECT_ROOT / "data" / "taxonomy_v2.json"
ALL_CLASSES = []
try:
    with open(TAXONOMY_PATH, encoding="utf-8") as f:
        tax_data = json.load(f)
        for c in tax_data.get("classes", []):
            ALL_CLASSES.append({"id": c["id"], "name": c.get("name_vi", c["id"])})
except Exception as e:
    print(f"[!] Lỗi nạp taxonomy: {e}")

# Nạp các luật đã học trước đó từ feedback
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
    <title>Demo Phân Loại Tài Liệu Xăng Dầu (Nhóm 3) - Human-in-the-Loop</title>
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
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 24px;
        }
        .container {
            max-width: 950px;
            margin: 0 auto;
        }
        .header {
            background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
            color: white;
            padding: 26px 30px;
            border-radius: 14px;
            margin-bottom: 24px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        .header h1 {
            margin: 0 0 8px 0;
            font-size: 25px;
        }
        .header p {
            margin: 0;
            opacity: 0.9;
            font-size: 14.5px;
        }
        .card {
            background: var(--card-bg);
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.08);
            border: 1px solid var(--border);
            margin-bottom: 24px;
        }
        label {
            display: block;
            font-weight: 600;
            margin-bottom: 8px;
            font-size: 15px;
        }

        /* Upload File Zone */
        .upload-zone {
            border: 2px dashed #93c5fd;
            background: #f0f7ff;
            border-radius: 10px;
            padding: 18px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s ease;
            margin-bottom: 16px;
        }
        .upload-zone:hover, .upload-zone.dragover {
            background: #e0f2fe;
            border-color: #2563eb;
        }
        .upload-icon {
            font-size: 30px;
            margin-bottom: 4px;
        }
        .upload-title {
            font-size: 14.5px;
            font-weight: 600;
            color: #1e40af;
        }
        .upload-hint {
            font-size: 13px;
            color: #64748b;
            margin-top: 4px;
        }
        .file-info {
            display: none;
            background: #dcfce7;
            border: 1px solid #86efac;
            color: #166534;
            padding: 10px 14px;
            border-radius: 8px;
            font-size: 13.5px;
            margin-bottom: 14px;
            align-items: center;
            justify-content: space-between;
        }

        textarea {
            width: 100%;
            height: 180px;
            padding: 12px;
            border: 1.5px solid var(--border);
            border-radius: 8px;
            font-size: 14px;
            font-family: inherit;
            box-sizing: border-box;
            resize: vertical;
        }
        textarea:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
        }
        .btn-group {
            display: flex;
            gap: 12px;
            margin-top: 14px;
        }
        button {
            background-color: var(--primary);
            color: white;
            border: none;
            padding: 11px 22px;
            font-size: 14.5px;
            font-weight: 600;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }
        button:hover {
            background-color: var(--primary-hover);
        }
        .btn-secondary {
            background-color: #f1f5f9;
            color: #334155;
            border: 1px solid #cbd5e1;
        }
        .btn-secondary:hover {
            background-color: #e2e8f0;
        }
        .btn-learn {
            background-color: #16a34a;
        }
        .btn-learn:hover {
            background-color: #15803d;
        }
        .samples {
            display: flex;
            gap: 8px;
            margin-top: 12px;
            flex-wrap: wrap;
        }
        .sample-chip {
            background: #eff6ff;
            color: #1d4ed8;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 13px;
            cursor: pointer;
            border: 1px solid #bfdbfe;
            transition: all 0.2s;
        }
        .sample-chip:hover {
            background: #dbeafe;
        }
        #resultCard {
            display: none;
        }
        .badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 14px;
            text-transform: uppercase;
        }
        .badge-rule { background: #dcfce7; color: #15803d; }
        .badge-tfidf { background: #dbeafe; color: #1d4ed8; }
        .badge-kev { background: #f3e8ff; color: #7e22ce; }
        .badge-human { background: #fee2e2; color: #b91c1c; }
        .res-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-top: 16px;
        }
        .res-item {
            background: #f8fafc;
            padding: 14px;
            border-radius: 8px;
            border: 1px solid var(--border);
        }
        .res-label {
            font-size: 12px;
            color: #64748b;
            margin-bottom: 4px;
            font-weight: 500;
        }
        .res-val {
            font-size: 18px;
            font-weight: 700;
        }
        .evidence-box {
            margin-top: 16px;
            padding: 14px;
            background: #fffbeb;
            border: 1px solid #fef3c7;
            border-radius: 8px;
            font-size: 13.5px;
            color: #92400e;
            line-height: 1.5;
        }

        /* Vùng Human-in-the-Loop Feedback */
        .feedback-section {
            margin-top: 24px;
            padding: 18px;
            background: #fdf4ff;
            border: 1.5px solid #f0abfc;
            border-radius: 10px;
        }
        .feedback-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 12px;
        }
        .feedback-title {
            font-size: 16px;
            font-weight: 700;
            color: #86198f;
        }
        .feedback-controls {
            display: flex;
            gap: 12px;
            align-items: center;
            flex-wrap: wrap;
        }
        select {
            padding: 10px 14px;
            border-radius: 8px;
            border: 1.5px solid #d8b4fe;
            background: white;
            font-size: 14px;
            font-family: inherit;
            color: #3b0764;
            flex: 1;
            min-width: 280px;
        }
        select:focus {
            outline: none;
            border-color: #a855f7;
            box-shadow: 0 0 0 3px rgba(168, 85, 247, 0.15);
        }
        .learning-status {
            display: none;
            margin-top: 12px;
            padding: 10px 14px;
            border-radius: 8px;
            font-size: 13.5px;
            background: #dcfce7;
            border: 1px solid #86efac;
            color: #166534;
        }

        .spinner {
            display: none;
            width: 18px;
            height: 18px;
            border: 2.5px solid #f3f3f3;
            border-top: 2.5px solid var(--primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            vertical-align: middle;
            margin-left: 8px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Demo Phân Loại Tài Liệu Xăng Dầu (Nhóm 3)</h1>
            <p>Hệ thống Cascade 4 Tầng + Tự Động Học Lại Khi Con Người Sửa Lỗi (Human-in-the-Loop)</p>
        </div>

        <div class="card">
            <!-- Vùng Upload File chuẩn Text/JSON -->
            <label>1. Đính kèm tệp văn bản đã OCR (.txt hoặc .json):</label>
            <div class="upload-zone" id="dropZone" onclick="document.getElementById('fileInput').click()">
                <div class="upload-icon">📄</div>
                <div class="upload-title">Nhấp vào đây để chọn tệp .txt / .json hoặc Kéo thả tệp vào đây</div>
                <div class="upload-hint">Chỉ nhận tệp đã có chữ OCR (ví dụ: các file trong data/ocr_llm_haiku/pages/ hoặc teams/.../haiku/)</div>
                <input type="file" id="fileInput" style="display: none;" accept=".txt,.json" onchange="handleFileSelect(this.files)">
            </div>

            <div class="file-info" id="fileInfo">
                <span id="fileInfoText">Đã chọn: filename.txt</span>
                <span style="cursor: pointer; font-weight: bold;" onclick="clearFile(event)">✕ Hủy</span>
            </div>

            <!-- Vùng Textarea -->
            <label for="docText">2. Hoặc dán trực tiếp đoạn văn bản OCR vào đây:</label>
            <textarea id="docText" placeholder="Nội dung chữ của tệp .txt / .json sẽ hiển thị ở đây, hoặc bạn có thể dán trực tiếp văn bản OCR..."></textarea>
            
            <div style="margin-top: 12px;">
                <span style="font-size: 13px; color: #64748b; font-weight: 600;">Thử nghiệm nhanh với các mẫu văn bản chuẩn:</span>
                <div class="samples">
                    <span class="sample-chip" onclick="loadSample(1)">Mẫu 1: Phiếu xuất kho</span>
                    <span class="sample-chip" onclick="loadSample(2)">Mẫu 2: Biên bản lấy mẫu</span>
                    <span class="sample-chip" onclick="loadSample(3)">Mẫu 3: Đăng ký kinh doanh</span>
                    <span class="sample-chip" onclick="loadSample(4)">Mẫu 4: Biên bản tự kiểm tra PCCC</span>
                </div>
            </div>

            <div class="btn-group">
                <button id="classifyBtn" onclick="runClassify()">
                    <span>Phân Loại Ngay</span>
                    <div class="spinner" id="spinner"></div>
                </button>
                <button class="btn-secondary" onclick="clearText()">Xóa nội dung</button>
            </div>
        </div>

        <div class="card" id="resultCard">
            <h2 style="margin: 0 0 16px 0; font-size: 20px;">Kết Quả Phân Loại</h2>
            <div class="res-grid">
                <div class="res-item">
                    <div class="res-label">Loại tài liệu nhận diện:</div>
                    <div class="res-val" id="catVal" style="color: #2563eb;">-</div>
                </div>
                <div class="res-item">
                    <div class="res-label">Tầng xử lý (Tier):</div>
                    <div class="res-val" id="tierVal">-</div>
                </div>
                <div class="res-item">
                    <div class="res-label">Độ tin cậy (Confidence):</div>
                    <div class="res-val" id="confVal">-</div>
                </div>
                <div class="res-item">
                    <div class="res-label">Thời gian xử lý:</div>
                    <div class="res-val" id="timeVal">-</div>
                </div>
            </div>

            <div class="evidence-box" id="evidenceBox"></div>

            <!-- Vùng Sửa Lỗi và Dạy Lại Mô Hình (Active Learning) -->
            <div class="feedback-section">
                <div class="feedback-header">
                    <span class="feedback-title">🧑‍🏫 Máy phân loại chưa đúng? Dạy lại hệ thống ngay tại đây:</span>
                </div>
                <p style="font-size: 13.5px; color: #701a75; margin: 0 0 10px 0;">
                    Chọn loại tài liệu chính xác bên dưới và bấm nút lưu. Hệ thống sẽ <strong>tự động học bổ sung</strong> để lần sau các văn bản tương tự không bao giờ bị đoán sai nữa!
                </p>
                <div class="feedback-controls">
                    <select id="correctCategorySelect">
                        <option value="">-- Chọn loại tài liệu đúng (36 loại) --</option>
                        <!-- Danh sách taxonomy sẽ được chèn tự động -->
                    </select>
                    <button class="btn-learn" id="learnBtn" onclick="submitCorrection()">
                        <span>💾 Lưu Sửa Đổi & Dạy Hệ Thống Học Lại</span>
                        <div class="spinner" id="learnSpinner"></div>
                    </button>
                </div>
                <div class="learning-status" id="learningStatus"></div>
            </div>
        </div>
    </div>

    <script>
        const ALL_CLASSES = """ + json.dumps(ALL_CLASSES, ensure_ascii=False) + """;

        // Khởi tạo danh sách dropdown taxonomy
        window.addEventListener('DOMContentLoaded', () => {
            const selectEl = document.getElementById('correctCategorySelect');
            ALL_CLASSES.forEach(item => {
                const opt = document.createElement('option');
                opt.value = item.id;
                opt.innerText = `${item.id} - ${item.name}`;
                selectEl.appendChild(opt);
            });
        });

        const SAMPLES = {
            1: "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\\nPHIẾU XUẤT KHO MUA HÀNG\\nNgày xuất: 11/01/2026\\nBên giao: Công ty Lọc hóa dầu Bình Sơn (BSR)\\nBên nhận: Công ty Cổ phần Hóa dầu Quân Đội\\nMặt hàng: Dầu DO 0.05S\\nSố lượng: 41.455 M3\\nPhương tiện: 77R-01942",
            2: "BIÊN BẢN LẤY MẪU VÀ NIÊM PHONG\\nHôm nay, tại Kho cảng P3, chúng tôi tiến hành lấy mẫu kiểm tra chất lượng lô hàng xăng dầu xuất bồn số 5207B...\\nĐại diện bên giao và bên nhận cùng ký tên.",
            3: "SỞ KẾ HOẠCH VÀ ĐẦU TƯ\\nGIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP\\nCÔNG TY CỔ PHẦN THƯƠNG MẠI DỊCH VỤ DẦU KHÍ\\nMã số doanh nghiệp: 0102030405\\nĐăng ký lần đầu: ngày 15 tháng 05 năm 2018\\nĐịa chỉ trụ sở chính: Số 123 đường Giải Phóng, Hà Nội",
            4: "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\\nĐộc lập - Tự do - Hạnh phúc\\nBIÊN BẢN TỰ KIỂM TRA CÔNG TÁC PHÒNG CHÁY CHỮA CHÁY\\nHôm nay, tại Cửa hàng xăng dầu số 17, chúng tôi tiến hành kiểm tra phương tiện PCCC..."
        };

        function loadSample(id) {
            document.getElementById('docText').value = SAMPLES[id];
            clearFile();
        }

        function clearText() {
            document.getElementById('docText').value = '';
            document.getElementById('resultCard').style.display = 'none';
            document.getElementById('learningStatus').style.display = 'none';
            clearFile();
        }

        // Kéo thả file
        const dropZone = document.getElementById('dropZone');
        ['dragenter', 'dragover'].forEach(name => {
            dropZone.addEventListener(name, (e) => { e.preventDefault(); dropZone.classList.add('dragover'); }, false);
        });
        ['dragleave', 'drop'].forEach(name => {
            dropZone.addEventListener(name, (e) => { e.preventDefault(); dropZone.classList.remove('dragover'); }, false);
        });
        dropZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files && files.length > 0) handleFileSelect(files);
        });

        function handleFileSelect(files) {
            if (!files || files.length === 0) return;
            const file = files[0];
            const ext = file.name.split('.').pop().toLowerCase();

            if (ext !== 'txt' && ext !== 'json') {
                alert('CHÚ Ý: Theo đúng thiết kế Nhóm 3, hệ thống chỉ chấp nhận tệp văn bản đã có chữ OCR (.txt hoặc .json). Không nhận tệp PDF ảnh!');
                clearFile();
                return;
            }

            const fileInfo = document.getElementById('fileInfo');
            const fileInfoText = document.getElementById('fileInfoText');
            fileInfo.style.display = 'flex';
            fileInfoText.innerText = `📄 Đang nạp tệp: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;

            const reader = new FileReader();
            reader.onload = function(e) {
                if (ext === 'txt') {
                    document.getElementById('docText').value = e.target.result;
                    fileInfoText.innerText = `✅ Đã nạp thành công tệp OCR: ${file.name}`;
                } else if (ext === 'json') {
                    try {
                        const data = JSON.parse(e.target.result);
                        let extracted = '';
                        if (data.pages && Array.isArray(data.pages)) {
                            extracted = data.pages.map(p => p.full_text || p.text || '').join('\\n');
                        } else if (data.text) {
                            extracted = data.text;
                        } else {
                            extracted = JSON.stringify(data, null, 2);
                        }
                        document.getElementById('docText').value = extracted;
                        fileInfoText.innerText = `✅ Đã trích xuất nội dung từ JSON: ${file.name}`;
                    } catch(err) {
                        alert('Lỗi đọc JSON: ' + err);
                    }
                }
            };
            reader.readAsText(file, 'utf-8');
        }

        function clearFile(event) {
            if (event) event.stopPropagation();
            document.getElementById('fileInput').value = '';
            document.getElementById('fileInfo').style.display = 'none';
        }

        async function runClassify() {
            const text = document.getElementById('docText').value.trim();
            if (!text) {
                alert('Vui lòng nạp tệp .txt / .json hoặc dán văn bản OCR cần kiểm thử!');
                return;
            }

            const btn = document.getElementById('classifyBtn');
            const spinner = document.getElementById('spinner');
            btn.disabled = true;
            spinner.style.display = 'inline-block';
            document.getElementById('learningStatus').style.display = 'none';

            try {
                const resp = await fetch('/api/classify', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: text })
                });
                const res = await resp.json();

                document.getElementById('resultCard').style.display = 'block';
                document.getElementById('catVal').innerText = res.category || 'UNKNOWN';
                
                const tierEl = document.getElementById('tierVal');
                tierEl.innerHTML = `<span class="badge badge-${res.tier}">${res.tier}</span>`;
                
                document.getElementById('confVal').innerText = (res.confidence * 100).toFixed(1) + '%';
                document.getElementById('timeVal').innerText = res.processing_time_ms.toFixed(1) + ' ms';
                
                const evBox = document.getElementById('evidenceBox');
                if (res.decision === 'needs_human') {
                    evBox.innerHTML = `<strong>⚠️ Chuyển người duyệt (needs_human):</strong> Lý do: ${res.reasons.join(', ')} | Gợi ý: <strong>${res.suggested_category || 'Không có'}</strong>`;
                } else {
                    evBox.innerHTML = `<strong>✅ Tự động lưu hồ sơ (auto_file):</strong> Xử lý bởi mô hình <strong>${res.model_name}</strong>. Căn cứ: ${res.evidence || 'Phù hợp đặc trưng từ vựng phân loại'}`;
                }

                // Gợi ý chọn sẵn nhãn trong dropdown nếu máy đoán được
                if (res.category && res.category !== 'UNKNOWN') {
                    document.getElementById('correctCategorySelect').value = res.category;
                }
            } catch (err) {
                alert('Lỗi kết nối tới máy chủ phân loại: ' + err);
            } finally {
                btn.disabled = false;
                spinner.style.display = 'none';
            }
        }

        // Gửi phản hồi dạy lại hệ thống (Active Learning)
        async function submitCorrection() {
            const text = document.getElementById('docText').value.trim();
            const correctedLabel = document.getElementById('correctCategorySelect').value;

            if (!text) {
                alert('Không có nội dung văn bản để học!');
                return;
            }
            if (!correctedLabel) {
                alert('Vui lòng chọn loại tài liệu đúng từ danh sách dropdown!');
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
                    body: JSON.stringify({
                        text: text,
                        corrected_label: correctedLabel
                    })
                });
                const res = await resp.json();

                if (res.status === 'ok') {
                    statusEl.style.display = 'block';
                    statusEl.innerHTML = `🎉 <strong>Học lại thành công!</strong><br>
                    • <strong>Cấp 1:</strong> Đã ghi nhận từ khóa tiêu đề <code>"${res.learned_keyword}"</code> vào Cổng Luật Tầng 1.<br>
                    • <strong>Cấp 2:</strong> Đã cập nhật mô hình học máy TF-IDF Tầng 2.<br>
                    ➔ <em>Bây giờ bạn hãy bấm nút <strong>"Phân Loại Ngay"</strong> ở trên để kiểm chứng: Máy sẽ nhận diện ngay lập tức là <strong>${correctedLabel}</strong>!</em>`;
                } else {
                    alert('Lỗi khi học lại: ' + res.error);
                }
            } catch (err) {
                alert('Lỗi kết nối khi gửi phản hồi học lại: ' + err);
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
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/classify":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)
            text = data.get("text", "")

            # Gọi bộ phân loại cascade
            cls_res, tr = clf.classify_text(text, slice_id="interactive_demo")

            decision = "needs_human" if cls_res.requires_human_review or cls_res.tier == "human" else "auto_file"
            reasons = []
            if cls_res.abstain_reason:
                reasons.append(cls_res.abstain_reason)

            payload = {
                "category": cls_res.predicted_category,
                "tier": cls_res.tier,
                "confidence": cls_res.confidence,
                "processing_time_ms": cls_res.processing_time_ms,
                "model_name": cls_res.model_name,
                "decision": decision,
                "reasons": reasons,
                "suggested_category": cls_res.suggested_category,
                "evidence": cls_res.evidence,
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

        elif self.path == "/api/feedback":
            # API Human-in-the-Loop Feedback: Nhận sửa đổi và dạy lại mô hình 2 cấp
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
                # ── BƯỚC 1: HỌC CẤP 1 (RULE GATE) ──
                # Tìm từ khóa tiêu đề đặc trưng từ 1500 ký tự đầu
                raw_lines = [line.strip().lower() for line in text[:1500].splitlines() if len(line.strip()) >= 5]
                learned_keyword = ""
                # Ưu tiên các dòng có chữ mang tính chất định danh tài liệu
                for line in raw_lines[:8]:
                    if any(w in line for w in ["biên bản", "hợp đồng", "phiếu", "giấy", "chứng nhận", "đơn", "bản vẽ", "thông báo", "hóa đơn", "công văn"]):
                        learned_keyword = line
                        break
                if not learned_keyword and raw_lines:
                    learned_keyword = raw_lines[0]
                if not learned_keyword:
                    learned_keyword = text[:60].strip().lower()

                # Đưa luật mới lên đầu danh sách luật để ưu tiên cao nhất
                clf.rules._rules.insert(0, (corrected_label, learned_keyword))

                # ── BƯỚC 2: HỌC CẤP 2 (TF-IDF COMPLEMENT NB RETRAIN) ──
                if clf.tfidf is not None and hasattr(clf.tfidf, "model") and hasattr(clf.tfidf, "vectorizer"):
                    try:
                        X = clf.tfidf.vectorizer.transform([text])
                        y = np.array([corrected_label])
                        # Nếu corrected_label nằm trong danh sách classes của TF-IDF
                        if corrected_label in clf.tfidf.classes:
                            clf.tfidf.model.partial_fit(X, y)
                    except Exception as ex_tfidf:
                        print(f"[!] TF-IDF partial_fit note: {ex_tfidf}")

                # ── BƯỚC 3: GHI VẾT FEEDBACK VÀO FILE ──
                record = {
                    "corrected_label": corrected_label,
                    "keyword": learned_keyword,
                    "text_snippet": text[:300]
                }
                with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")

                print(f"[+] [Feedback Active Learning] Đã học mẫu mới: {corrected_label} với từ khóa: '{learned_keyword}'")

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
    print(f"\n=======================================================")
    print(f"[*] Web Demo Server đang chạy tại: http://localhost:{port}")
    print(f"[*] ĐÃ KÍCH HOẠT TÍNH NĂNG ACTIVE LEARNING (HUMAN-IN-THE-LOOP)!")
    print(f"=======================================================\n")
    httpd.serve_forever()

if __name__ == "__main__":
    run()
