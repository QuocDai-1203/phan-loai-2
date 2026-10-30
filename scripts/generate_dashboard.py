import json
import os
import sys
from pathlib import Path

def generate_html_report(json_path: Path, output_html_path: Path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    file_name = data.get("file_name", "Unknown")
    total_pages = data.get("total_pages", 0)
    fr = data.get("file_routing", {})
    decision = fr.get("decision", "unknown").upper()
    n_slices = fr.get("n_slices", 0)
    n_auto = fr.get("n_auto", 0)
    n_needs_human = fr.get("n_needs_human", 0)
    auto_rate = f"{(n_auto / n_slices * 100):.1f}%" if n_slices else "0%"

    timings = data.get("stage_timings_ms", {})
    warnings = data.get("warnings", [])
    clfs = data.get("classifications", [])
    routing = {r["slice_id"]: r for r in data.get("routing", [])}

    # Statistics for categories and tiers
    cat_counts = {}
    tier_counts = {}
    for c in clfs:
        cat = c.get("predicted_category", "UNKNOWN")
        tier = c.get("tier", "unknown")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    sorted_cats = sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)
    cat_labels = [k for k, v in sorted_cats]
    cat_values = [v for k, v in sorted_cats]

    tier_labels = list(tier_counts.keys())
    tier_values = list(tier_counts.values())

    table_rows = []
    for c in clfs:
        s_id = c.get("slice_id")
        r_info = routing.get(s_id, {})
        r_decision = r_info.get("decision", "unknown")
        cat = c.get("predicted_category", "UNKNOWN")
        tier = c.get("tier", "")
        conf = c.get("confidence")
        conf_str = f"{conf:.4f}" if isinstance(conf, (int, float)) else "N/A"
        reasons = ", ".join(r_info.get("reasons", [])) or "None"
        
        badge_class = "badge-success" if r_decision == "auto_file" else "badge-danger"
        table_rows.append(f"""
        <tr>
            <td><strong>{s_id}</strong></td>
            <td><span class="badge {badge_class}">{r_decision.upper()}</span></td>
            <td><span class="category-name">{cat}</span></td>
            <td><span class="badge badge-info">{tier}</span></td>
            <td>{conf_str}</td>
            <td><small class="text-muted">{reasons}</small></td>
        </tr>
        """)

    warnings_html = "".join([f"<li>⚠️ {w}</li>" for w in warnings]) if warnings else "<li>Không có cảnh báo</li>"

    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Báo Cáo Phân Loại: {file_name}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #0f172a;
            --text-sub: #64748b;
            --primary: #2563eb;
            --success: #16a34a;
            --warning: #d97706;
            --danger: #dc2626;
            --border: #e2e8f0;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Inter', sans-serif;
            background: var(--bg);
            color: var(--text-main);
            padding: 24px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--card-bg);
            padding: 20px 24px;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        h1 {{ font-size: 22px; font-weight: 700; color: var(--text-main); }}
        .header-meta {{ color: var(--text-sub); font-size: 14px; margin-top: 4px; }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .kpi-card {{
            background: var(--card-bg);
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            border-left: 4px solid var(--primary);
        }}
        .kpi-title {{ font-size: 13px; font-weight: 600; color: var(--text-sub); text-transform: uppercase; letter-spacing: 0.5px; }}
        .kpi-value {{ font-size: 28px; font-weight: 700; margin-top: 8px; color: var(--text-main); }}
        .kpi-sub {{ font-size: 13px; color: var(--text-sub); margin-top: 4px; }}
        
        .charts-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 24px;
        }}
        .chart-card {{
            background: var(--card-bg);
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .chart-title {{ font-size: 16px; font-weight: 600; margin-bottom: 16px; }}
        
        .table-card {{
            background: var(--card-bg);
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            margin-bottom: 24px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}
        th, td {{ padding: 12px 14px; text-align: left; border-bottom: 1px solid var(--border); }}
        th {{ background: #f1f5f9; color: var(--text-sub); font-weight: 600; }}
        tr:hover {{ background: #f8fafc; }}
        
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
        }}
        .badge-success {{ background: #dcfce7; color: var(--success); }}
        .badge-danger {{ background: #fee2e2; color: var(--danger); }}
        .badge-info {{ background: #e0f2fe; color: #0284c7; }}
        
        .info-card {{
            background: #fffbeb;
            border: 1px solid #fef3c7;
            padding: 16px 20px;
            border-radius: 10px;
            color: #92400e;
            font-size: 14px;
            margin-bottom: 24px;
        }}
        .info-card ul {{ margin-left: 20px; margin-top: 8px; }}
        .info-card li {{ margin-bottom: 4px; }}
        
        .timing-bar {{
            display: flex;
            gap: 12px;
            margin-top: 10px;
            font-size: 13px;
        }}
        .timing-item {{
            background: #f1f5f9;
            padding: 6px 12px;
            border-radius: 6px;
            font-weight: 500;
        }}
    </style>
</head>
<body>
<div class="container">
    <header>
        <div>
            <h1>📊 Bảng Điều Khiển Xử Lý Tài Liệu (Pipeline Dashboard)</h1>
            <div class="header-meta">Tệp: <strong>{file_name}</strong> | Tổng số trang PDF: <strong>{total_pages}</strong></div>
        </div>
        <div>
            <span class="badge {('badge-success' if decision == 'AUTO_FILE' else 'badge-danger')}" style="font-size: 15px; padding: 8px 16px;">
                QUYẾT ĐỊNH: {decision}
            </span>
        </div>
    </header>

    <div class="kpi-grid">
        <div class="kpi-card" style="border-left-color: #2563eb;">
            <div class="kpi-title">Tổng số lát cắt (Slices)</div>
            <div class="kpi-value">{n_slices}</div>
            <div class="kpi-sub">Đã gộp từ các trang liên tiếp</div>
        </div>
        <div class="kpi-card" style="border-left-color: #16a34a;">
            <div class="kpi-title">Tự Động Xếp (Auto-file)</div>
            <div class="kpi-value" style="color: #16a34a;">{n_auto}</div>
            <div class="kpi-sub">Đạt tỷ lệ: <strong>{auto_rate}</strong></div>
        </div>
        <div class="kpi-card" style="border-left-color: #dc2626;">
            <div class="kpi-title">Cần Người Duyệt (Needs Human)</div>
            <div class="kpi-value" style="color: #dc2626;">{n_needs_human}</div>
            <div class="kpi-sub">Độ tin cậy thấp hoặc chưa có LLM</div>
        </div>
        <div class="kpi-card" style="border-left-color: #8b5cf6;">
            <div class="kpi-title">Tổng Thời Gian Chạy</div>
            <div class="kpi-value">~{(sum(timings.values())/1000):.2f}s</div>
            <div class="kpi-sub">OCR txt: {timings.get('ocr', 0):.0f}ms | Split: {timings.get('split', 0):.0f}ms</div>
        </div>
    </div>

    <div class="info-card">
        <strong>⚠️ Ghi chú & Cảnh báo trong quá trình chạy:</strong>
        <ul>
            {warnings_html}
        </ul>
        <div class="timing-bar">
            <span class="timing-item">OCR: {timings.get('ocr', 0):.1f} ms</span>
            <span class="timing-item">Tách lát cắt: {timings.get('split', 0):.1f} ms</span>
            <span class="timing-item">Phân loại: {timings.get('classify', 0):.1f} ms</span>
            <span class="timing-item">Trích xuất: {timings.get('extract', 0):.1f} ms</span>
        </div>
    </div>

    <div class="charts-grid">
        <div class="chart-card">
            <div class="chart-title">📌 Phân bổ quyết định xử lý</div>
            <canvas id="chartDecision" height="240"></canvas>
        </div>
        <div class="chart-card">
            <div class="chart-title">⚙️ Tầng ra quyết định (Tier phân loại)</div>
            <canvas id="chartTier" height="240"></canvas>
        </div>
    </div>

    <div class="chart-card" style="margin-bottom: 24px;">
        <div class="chart-title">📂 Số lượng lát cắt theo từng Loại Tài Liệu nhận diện</div>
        <canvas id="chartCategory" height="120"></canvas>
    </div>

    <div class="table-card">
        <div class="chart-title">📋 Chi tiết từng lát cắt ({n_slices} lát)</div>
        <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr>
                        <th>Lát cắt (Slice)</th>
                        <th>Quyết định</th>
                        <th>Loại tài liệu gán</th>
                        <th>Tầng phân loại (Tier)</th>
                        <th>Độ tin cậy (Conf)</th>
                        <th>Lý do / Trạng thái</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(table_rows)}
                </tbody>
            </table>
        </div>
    </div>
</div>

<script>
    // Chart 1: Decision Pie
    new Chart(document.getElementById('chartDecision'), {{
        type: 'doughnut',
        data: {{
            labels: ['Tự động (Auto)', 'Cần người duyệt'],
            datasets: [{{
                data: [{n_auto}, {n_needs_human}],
                backgroundColor: ['#16a34a', '#dc2626'],
                hoverOffset: 4
            }}]
        }},
        options: {{
            responsive: true,
            plugins: {{ legend: {{ position: 'bottom' }} }}
        }}
    }});

    // Chart 2: Tier Bar
    new Chart(document.getElementById('chartTier'), {{
        type: 'bar',
        data: {{
            labels: {json.dumps(tier_labels)},
            datasets: [{{
                label: 'Số lát cắt',
                data: {json.dumps(tier_values)},
                backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444'],
                borderRadius: 6
            }}]
        }},
        options: {{
            responsive: true,
            plugins: {{ legend: {{ display: false }} }},
            scales: {{ y: {{ beginAtZero: true }} }}
        }}
    }});

    // Chart 3: Categories Horizontal Bar
    new Chart(document.getElementById('chartCategory'), {{
        type: 'bar',
        data: {{
            labels: {json.dumps(cat_labels)},
            datasets: [{{
                label: 'Số lượng',
                data: {json.dumps(cat_values)},
                backgroundColor: '#2563eb',
                borderRadius: 4
            }}]
        }},
        options: {{
            indexAxis: 'y',
            responsive: true,
            plugins: {{ legend: {{ display: false }} }},
            scales: {{ x: {{ beginAtZero: true }} }}
        }}
    }});
</script>
</body>
</html>
"""
    output_html_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"✅ Đã tạo giao diện HTML tại: {output_html_path.resolve()}")

if __name__ == "__main__":
    json_file = Path("output/pipeline/20260109-04.pipeline.json")
    out_html = Path("output/pipeline_dashboard.html")
    generate_html_report(json_file, out_html)
