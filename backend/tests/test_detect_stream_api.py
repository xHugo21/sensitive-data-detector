import json

from fastapi.testclient import TestClient

from app.main import app
from app.api.routes import detect as detect_route


class DummyOrchestrator:
    def __init__(self, config):
        self.calls = []
        self.config = config

    def stream_updates(
        self,
        *,
        text=None,
        file_path=None,
        min_block_risk=None,
        stream_mode=None,
    ):
        self.calls.append((text, file_path, min_block_risk, stream_mode))
        initial_state = {"raw_text": text or "", "detected_fields": []}
        updates = iter(
            [
                (
                    "updates",
                    {
                        "merge_dlp_ner": {
                            "detected_fields": [{"field": "EMAIL"}],
                        }
                    },
                ),
                ("tasks", {"id": "1", "name": "llm_detector", "input": {}}),
                (
                    "tasks",
                    {
                        "id": "1",
                        "name": "llm_detector",
                        "result": {"detected_fields": []},
                    },
                ),
            ]
        )
        return initial_state, updates


def test_detect_stream_emits_running_nodes(monkeypatch):
    dummy = DummyOrchestrator("dummy-config")
    monkeypatch.setattr(detect_route, "GUARD_CONFIG", "dummy-config")
    monkeypatch.setattr(detect_route, "MIN_BLOCK_RISK", "medium")
    monkeypatch.setattr(detect_route, "GuardOrchestrator", lambda config: dummy)

    client = TestClient(app)
    resp = client.post("/detect/stream", data={"text": "hello"})

    assert resp.status_code == 200
    lines = [json.loads(line) for line in resp.text.splitlines() if line.strip()]
    node_events = [event for event in lines if event.get("type") == "node"]
    assert node_events
    assert node_events[0]["node"] == "llm_detector"
    assert node_events[0]["status"] == "running"
    assert node_events[0]["detected_count"] == 1
    assert lines[-1]["type"] == "result"
    assert lines[-1]["result"]["raw_text"] == "hello"
    assert lines[-1]["result"]["detected_fields"] == [{"field": "EMAIL"}]
    assert dummy.calls[0][3] == ["tasks", "updates"]


def test_detect_stream_requires_input():
    client = TestClient(app)
    resp = client.post("/detect/stream", data={})

    assert resp.status_code == 400
    body = resp.json()
    assert "error" in body
