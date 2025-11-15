from types import SimpleNamespace

from core import detector


def _response(payload: str):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=payload))]
    )


class DummyClient:
    def __init__(self, payload: str):
        self.payload = payload
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create)  # type: ignore[attr-defined]
        )

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        return _response(self.payload)


def test_safe_json_from_text_extracts_json_object():
    text = "Answer: {'detected_fields': []} trailing"
    result = detector.safe_json_from_text(text.replace("'", '"'))
    assert result == {"detected_fields": []}


def test_safe_json_from_text_returns_empty_on_failure():
    assert detector.safe_json_from_text("No JSON here") == {}


def test_detect_sensitive_data_uses_custom_prompt(monkeypatch):
    client = DummyClient('{"detected_fields":[{"field":"EMAIL"}],"risk_level":"Low"}')
    monkeypatch.setattr(detector, "client", client)

    result = detector.detect_sensitive_data("sample text", prompt="Custom: {text}")

    assert result["detected_fields"] == [{"field": "EMAIL"}]
    assert result["_prompt_source"] == "custom"
    assert result["_model_used"] == detector.LLM_MODEL
    assert result["_provider"] == detector.LLM_PROVIDER
    assert client.calls
    assert client.calls[0]["messages"][1]["content"].startswith("Custom:")


def test_detect_sensitive_data_recovers_from_llm_errors(monkeypatch):
    class FlakyClient:
        def __init__(self):
            self.calls: list[dict] = []
            self._first = True
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=self._create)  # type: ignore[attr-defined]
            )

        def _create(self, **kwargs):
            self.calls.append(kwargs)
            if self._first:
                self._first = False
                raise RuntimeError("boom")
            return _response("nonsense output")

    client = FlakyClient()
    monkeypatch.setattr(detector, "client", client)
    monkeypatch.setattr(detector, "load_prompt", lambda mode: "Template {text}")

    result = detector.detect_sensitive_data("to analyze")

    assert result["detected_fields"] == []
    assert result["_prompt_source"].startswith("prompts/")
    assert len(client.calls) == 2
