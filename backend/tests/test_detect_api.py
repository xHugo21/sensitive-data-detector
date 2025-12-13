from fastapi.testclient import TestClient

from app.main import app
from app.api.routes import detect as detect_route


def test_detect_endpoint_with_text_uses_orchestrator(monkeypatch):
    """Test detect endpoint with text parameter"""
    # Mock config values in the detect route module
    monkeypatch.setattr(detect_route, "MIN_BLOCK_RISK", "medium")
    
    class DummyOrchestrator:
        def __init__(self):
            self.calls = []

        def run(self, text=None, *, file_path=None, min_block_risk=None):
            self.calls.append(("text", text, min_block_risk))
            return {"detected_fields": [{"field": "EMAIL"}], "risk_level": "low"}

    dummy = DummyOrchestrator()
    monkeypatch.setattr(detect_route, "GuardOrchestrator", lambda: dummy)

    client = TestClient(app)
    resp = client.post("/detect", data={"text": "hello"})

    assert resp.status_code == 200
    assert resp.json()["detected_fields"] == [{"field": "EMAIL"}]
    assert dummy.calls[0][0] == "text"
    assert dummy.calls[0][1] == "hello"
    assert dummy.calls[0][2] == "medium"


def test_detect_endpoint_with_file(monkeypatch, tmp_path):
    """Test detect endpoint with file upload"""
    # Mock config values in the detect route module
    monkeypatch.setattr(detect_route, "MIN_BLOCK_RISK", "high")
    
    class DummyOrchestrator:
        def __init__(self):
            self.calls = []

        def run(self, text=None, *, file_path=None, min_block_risk=None):
            self.calls.append(("file", file_path, min_block_risk))
            return {
                "detected_fields": [],
                "risk_level": "none",
                "raw_text": "file text content"
            }

    dummy = DummyOrchestrator()
    monkeypatch.setattr(detect_route, "GuardOrchestrator", lambda: dummy)

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
    assert body["extracted_snippet"] == "file text content"
    assert dummy.calls
    call_type, call_file_path, call_threshold = dummy.calls[0]
    assert call_type == "file"
    assert call_file_path is not None
    assert call_threshold == "high"


def test_detect_endpoint_requires_input():
    """Test that detect endpoint requires either text or file"""
    client = TestClient(app)
    resp = client.post("/detect", data={})

    assert resp.status_code == 200
    body = resp.json()
    assert "error" in body
    assert "text or file must be provided" in body["error"].lower()
