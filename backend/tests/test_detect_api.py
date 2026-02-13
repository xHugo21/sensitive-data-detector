from fastapi.testclient import TestClient

from app.main import app
from app.api.routes import detect as detect_route


class DummyOrchestrator:
    def __init__(self, config):
        self.calls = []
        self.config = config

    async def run(self, text=None, *, file_path=None, min_block_level=None):
        self.calls.append((text, file_path, min_block_level))
        return {"detected_fields": [{"field": "EMAIL"}], "risk_level": "low"}


def test_detect_endpoint_with_text_uses_orchestrator(monkeypatch):
    """Test detect endpoint with text parameter"""
    dummy = DummyOrchestrator("dummy-config")
    monkeypatch.setattr(detect_route, "GUARD_CONFIG", "dummy-config")
    monkeypatch.setattr(detect_route, "DEFAULT_BLOCK_LEVEL", "medium")
    monkeypatch.setattr(detect_route, "GuardOrchestrator", lambda config: dummy)

    client = TestClient(app)
    resp = client.post("/detect", data={"text": "hello"})

    assert resp.status_code == 200
    assert resp.json()["detected_fields"] == [{"field": "EMAIL"}]
    call_text, call_file, call_threshold = dummy.calls[0]
    assert call_text == "hello"
    assert call_file is None
    assert call_threshold == "medium"


def test_detect_endpoint_with_min_block_level_override(monkeypatch):
    """Test detect endpoint with explicit min_block_level parameter"""
    dummy = DummyOrchestrator("dummy-config")
    monkeypatch.setattr(detect_route, "GUARD_CONFIG", "dummy-config")
    monkeypatch.setattr(detect_route, "DEFAULT_BLOCK_LEVEL", "high")
    monkeypatch.setattr(detect_route, "GuardOrchestrator", lambda config: dummy)

    client = TestClient(app)
    resp = client.post("/detect", data={"text": "hello", "min_block_level": "low"})

    assert resp.status_code == 200
    call_text, call_file, call_threshold = dummy.calls[0]
    assert call_threshold == "low"


def test_detect_endpoint_with_file(monkeypatch, tmp_path):
    """Test detect endpoint with file upload"""
    dummy = DummyOrchestrator("dummy-config")
    monkeypatch.setattr(detect_route, "GUARD_CONFIG", "dummy-config")
    monkeypatch.setattr(detect_route, "DEFAULT_BLOCK_LEVEL", "medium")
    monkeypatch.setattr(detect_route, "GuardOrchestrator", lambda config: dummy)

    client = TestClient(app)
    file_path = tmp_path / "sample.txt"
    file_path.write_text("file text content", encoding="utf-8")

    with file_path.open("rb") as f:
        resp = client.post(
            "/detect",
            files={"file": ("sample.txt", f, "text/plain")},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert dummy.calls
    call_text, call_file_path, call_threshold = dummy.calls[0]
    assert call_text is None
    assert call_file_path is not None
    assert call_threshold == "medium"


def test_detect_endpoint_requires_input():
    """Test that detect endpoint requires either text or file"""
    client = TestClient(app)
    resp = client.post("/detect", data={})

    assert resp.status_code == 200
    body = resp.json()
    assert "error" in body
    assert "text or file must be provided" in body["error"].lower()
