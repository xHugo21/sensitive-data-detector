from app.utils import prompt_loader


def test_resolve_mode_prefers_detection_mode_default(monkeypatch):
    monkeypatch.setattr(prompt_loader, "DETECTION_MODE", "few-shot", raising=False)
    assert prompt_loader.resolve_mode(None) == "few-shot"


def test_resolve_mode_falls_back_for_unknown(monkeypatch):
    monkeypatch.setattr(prompt_loader, "DETECTION_MODE", "", raising=False)
    resolved = prompt_loader.resolve_mode("unknown-mode")
    assert resolved == prompt_loader._FALLBACK_PROMPT_MODE


def test_load_prompt_reads_prompt_file():
    text = prompt_loader.load_prompt("zero-shot")
    assert isinstance(text, str)
    assert text


def test_inject_text_replaces_placeholder():
    template = "Prompt: {text}"
    assert prompt_loader.inject_text(template, "value") == "Prompt: value"


def test_inject_text_appends_block_when_missing_placeholder():
    template = "Summarize the following input."
    result = prompt_loader.inject_text(template, "sample")
    assert result.startswith(template)
    assert "sample" in result
