"""llm_cache.py - Bộ nhớ đệm đĩa tất định cho lời gọi mô hình cục bộ (Kev, Ollama, embedding).

Khóa = sha256 của (tên mô hình + toàn bộ nội dung yêu cầu). Cùng yêu cầu -> cùng câu trả lời đã lưu, nên chạy lại
thí nghiệm miễn phí và tất định. Mỗi bản ghi lưu cả `latency_ms` đo ở lần gọi thật đầu tiên để báo cáo độ trễ
mà không phải gọi lại mô hình.

Thư mục `_cache/` được git-ignore. Không đưa dữ liệu ra dịch vụ ngoài: mô hình chạy trên máy này.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional


def make_key(*parts: Any) -> str:
    """sha256 của biểu diễn JSON chuẩn tắc (sort_keys, ensure_ascii=False) của các phần."""
    blob = json.dumps(parts, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class DiskCache:
    """Mỗi khóa một tệp JSON `root/<2 ký tự đầu>/<khóa>.json`. Ghi nguyên tử (tệp tạm + rename)."""

    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.hits = 0
        self.misses = 0

    def _path(self, key: str) -> Path:
        return self.root / key[:2] / f"{key}.json"

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        p = self._path(key)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def put(self, key: str, value: Dict[str, Any]) -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(p.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(value, f, ensure_ascii=False)
            os.replace(tmp, p)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def cached(self, key: str, fn, *, retry_errors: bool = False) -> Dict[str, Any]:
        """Trả bản ghi đã lưu; nếu chưa có thì gọi `fn()` (phải trả dict JSON-hóa được) và lưu.
        Bản ghi có trường `error` khác rỗng chỉ được dùng lại khi retry_errors=False."""
        rec = self.get(key)
        if rec is not None and not (retry_errors and rec.get("error")):
            self.hits += 1
            return rec
        self.misses += 1
        rec = fn()
        self.put(key, rec)
        return rec
