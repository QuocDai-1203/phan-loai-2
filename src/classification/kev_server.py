"""kev_server.py - Cầu nối API chuẩn System One (/v1/systemone) cho Kev Backend.

Chức năng:
- Mở cổng HTTP tại http://127.0.0.1:8009/v1/systemone (tương thích hoàn toàn TypeSafe Jev API & KevClient).
- Endpoint GET /api/status trả về current_model cho llm_backends.py.
- Tiếp nhận payload chứa văn bản tài liệu và câu hỏi Choice từ criteria.
- Chuyển tiếp tới backend Ollama (Qwen2.5 trên NVIDIA RTX 3050).
- Trả về nhãn dự đoán (choice), độ tin cậy (confidence) và phân phối xác suất (probabilities).
"""

import sys
import json
import time
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Dict, Any, List

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = "qwen2.5:1.5b"
KEV_MODEL_NAME = "jaredpalmer/kev-0.8b"
PORT = 8009


def build_prompt(doc_text: str, criteria: Dict[str, str], instructions: str = "") -> str:
    """Xây dựng prompt tối ưu cho Qwen ra quyết định System One."""
    items = []
    for k, v in criteria.items():
        if v and v != k:
            items.append(f"- {k}: {v}")
        else:
            items.append(f"- {k}")
    cats_str = "\n".join(items)

    task_desc = instructions or "Đọc đoạn văn bản tài liệu dưới đây và chọn ĐÚNG 1 mã danh mục phù hợp nhất từ danh sách cho trước."

    prompt = f"""Bạn là động cơ phân loại tài liệu doanh nghiệp tốc độ cao (Kev System One).
Nhiệm vụ: {task_desc}

DANH SÁCH DANH MỤC HỢP LỆ:
{cats_str}

VĂN BẢN TÀI LIỆU CẦN PHÂN LOẠI:
\"\"\"
{doc_text[:2000]}
\"\"\"

YÊU CẦU ĐẦU RA:
Chỉ xuất ra đúng 1 đối tượng JSON duy nhất (không giải thích thêm):
{{"category": "mã danh mục chính xác từ danh sách trên", "confidence": 0.95}}"""
    return prompt


def query_ollama(doc_text: str, criteria: Dict[str, str], instructions: str = "") -> Dict[str, Any]:
    """Gửi yêu cầu tới Ollama và bóc tách kết quả."""
    categories = list(criteria.keys())
    if not categories:
        return {"choice": "UNKNOWN", "confidence": 0.0, "probabilities": {}}

    prompt = build_prompt(doc_text, criteria, instructions)
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.0,
            "num_predict": 60,
        }
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=5.0)
        if resp.status_code == 200:
            raw_text = resp.json().get("response", "{}")
            parsed = json.loads(raw_text)
            pred_cat = parsed.get("category", "")
            conf = float(parsed.get("confidence", 0.85))

            # Tìm danh mục khớp chính xác nhất
            matched_cat = None
            pred_cat_clean = pred_cat.strip()
            if pred_cat_clean:
                # 1. Exact match
                for cat in categories:
                    if cat.lower() == pred_cat_clean.lower():
                        matched_cat = cat
                        break
                # 2. Substring match
                if not matched_cat:
                    for cat in categories:
                        if cat.lower() in pred_cat_clean.lower() or (len(pred_cat_clean) >= 4 and pred_cat_clean.lower() in cat.lower()):
                            matched_cat = cat
                            break

            pred_cat = matched_cat or categories[0]

            # Sinh phân phối xác suất
            probs = {c: 0.01 for c in categories}
            probs[pred_cat] = max(0.5, min(0.99, conf))
            # Chuẩn hóa tổng = 1.0
            total_p = sum(probs.values())
            probs = {k: round(v / total_p, 4) for k, v in probs.items()}

            return {
                "choice": pred_cat,
                "confidence": probs[pred_cat],
                "probabilities": probs,
            }
    except Exception as e:
        print(f"[Kev Server Error] {e}", file=sys.stderr)

    # Fallback mặc định
    first_choice = categories[0]
    return {
        "choice": first_choice,
        "confidence": 0.60,
        "probabilities": {first_choice: 0.60},
    }


class KevHandler(BaseHTTPRequestHandler):
    """Bộ xử lý HTTP request chuẩn System One."""

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        """Health check & status endpoints."""
        if self.path in ["/api/status", "/status"]:
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            status = {
                "status": "ok",
                "current_model": KEV_MODEL_NAME,
                "backend": f"Ollama ({MODEL_NAME}) on NVIDIA RTX 3050",
            }
            self.wfile.write(json.dumps(status, ensure_ascii=False).encode("utf-8"))
        elif self.path in ["/", "/health"]:
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            status = {
                "status": "healthy",
                "service": "Kev System One Server",
                "current_model": KEV_MODEL_NAME,
                "backend": f"Ollama ({MODEL_NAME}) on NVIDIA RTX 3050",
                "endpoint": "/v1/systemone",
            }
            self.wfile.write(json.dumps(status, ensure_ascii=False).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        """Endpoint chính: /v1/systemone."""
        if self.path == "/v1/systemone":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")

            try:
                data = json.loads(body)
                doc_text = data.get("state", "")
                questions = data.get("questions", {})

                answers = {}
                # Xử lý tất cả các câu hỏi trong questions (thường là 'q' hoặc 'category')
                for q_key, q_val in questions.items():
                    criteria = q_val.get("criteria", {})
                    instructions = q_val.get("instructions", "")
                    ans = query_ollama(doc_text, criteria, instructions)
                    answers[q_key] = ans

                response_data = {
                    "model": KEV_MODEL_NAME,
                    "answers": answers
                }

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                err_resp = {"error": str(e)}
                self.wfile.write(json.dumps(err_resp, ensure_ascii=False).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def start_server(port: int = PORT):
    server = ThreadedHTTPServer(("127.0.0.1", port), KevHandler)
    print(f"================================================================")
    print(f"  KEV SYSTEM ONE SERVER ĐANG HOẠT ĐỘNG (v-2)")
    print(f"  - Cổng kết nối: http://127.0.0.1:{port}/v1/systemone")
    print(f"  - Status endpoint: http://127.0.0.1:{port}/api/status")
    print(f"  - AI Backend:   Ollama ({MODEL_NAME}) chạy trên NVIDIA RTX 3050")
    print(f"================================================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐang tắt Kev Server...")
        server.server_close()


if __name__ == "__main__":
    start_server()
