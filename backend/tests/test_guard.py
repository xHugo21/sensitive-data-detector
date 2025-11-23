from app import guard


def test_run_guard_pipeline_delegates_to_orchestrator(monkeypatch):
    calls: list[tuple[str, str | None, str | None, dict | None]] = []

    class DummyOrchestrator:
        def run(self, text, *, prompt=None, mode=None, metadata=None):
            calls.append((text, prompt, mode, metadata))
            return {"detected_fields": [], "risk_level": "None"}

    monkeypatch.setattr(guard, "_orchestrator", DummyOrchestrator())

    result = guard.run_guard_pipeline(
        "sample text",
        prompt="custom prompt",
        mode="zero-shot",
        metadata={"source": "test"},
    )

    assert calls == [("sample text", "custom prompt", "zero-shot", {"source": "test"})]
    assert result["detected_fields"] == []
    assert result["risk_level"] == "None"
