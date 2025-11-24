from fastapi.testclient import TestClient

from app.main import app
from app.api.routes import detect as detect_route


def test_detect_endpoint_uses_orchestrator(monkeypatch):
    class DummyOrchestrator:
        def __init__(self):
            self.calls = []

        def run(self, text, *, mode=None):
            self.calls.append((text, mode))
            return {"detected_fields": [{"field": "EMAIL"}], "risk_level": "Low"}

    dummy = DummyOrchestrator()
    monkeypatch.setattr(detect_route, "GuardOrchestrator", lambda: dummy)

    client = TestClient(app)
    resp = client.post("/detect", json={"text": "hello", "mode": "m"})

    assert resp.status_code == 200
    assert resp.json()["detected_fields"] == [{"field": "EMAIL"}]
    assert dummy.calls == [("hello", "m")]


def test_detect_file_endpoint_adds_snippet(monkeypatch, tmp_path):
    class DummyOrchestrator:
        def __init__(self):
            self.calls = []

        def run(self, text, *, mode=None):
            self.calls.append((text, mode))
            return {"detected_fields": [], "risk_level": "None"}

    dummy = DummyOrchestrator()
    monkeypatch.setattr(detect_route, "GuardOrchestrator", lambda: dummy)
    monkeypatch.setattr(detect_route, "read_document", lambda path: "file text content")

    client = TestClient(app)
    file_path = tmp_path / "sample.txt"
    file_path.write_text("file text content", encoding="utf-8")

    with file_path.open("rb") as f:
        resp = client.post(
            "/detect_file",
            data={"mode": "zero-shot"},
            files={"file": ("sample.txt", f, "text/plain")},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["extracted_snippet"] == "file text content"
    assert dummy.calls
    text, mode = dummy.calls[0]
    assert text == "file text content"
    assert mode == "zero-shot"
