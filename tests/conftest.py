"""conftest.py (tests) - Fixture dùng chung: chặn mạng thật và cô lập khỏi data/taxonomy_v2.json của máy hiện tại."""

import pytest
import requests


@pytest.fixture(autouse=True)
def _block_real_http(monkeypatch):
    """Mọi test phải mock HTTP; nếu lỡ gọi thật (Kev, iOS-OCR-Server...) thì báo lỗi ngay thay vì chạm mạng."""
    def deny(self, method, url, *a, **k):
        raise AssertionError(f"Test không được gọi HTTP thật: {method} {url}")

    monkeypatch.setattr(requests.sessions.Session, "request", deny)


@pytest.fixture(autouse=True)
def _legacy_taxonomy_by_default(monkeypatch, tmp_path_factory):
    """Mặc định dùng 19 nhãn legacy, bất kể data/taxonomy_v2.json đã được tạo hay chưa."""
    import src.classification.taxonomy as tx
    monkeypatch.setattr(tx, "DEFAULT_TAXONOMY_PATH", tmp_path_factory.getbasetemp() / "khong_co_taxonomy.json")
