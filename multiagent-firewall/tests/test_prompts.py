from multiagent_firewall import prompts


def test_resolve_mode_prefers_detection_mode_default(monkeypatch):
    monkeypatch.setenv("DETECTION_MODE", "few-shot")
    assert prompts.resolve_mode(None) == "few-shot"


def test_resolve_mode_falls_back_for_unknown(monkeypatch):
    monkeypatch.delenv("DETECTION_MODE", raising=False)
    resolved = prompts.resolve_mode("unknown-mode")
    assert resolved == prompts._FALLBACK_PROMPT_MODE


def test_load_prompt_reads_prompt_file():
    text = prompts.load_prompt("zero-shot")
    assert isinstance(text, str)
    assert text


def test_inject_text_replaces_placeholder():
    template = "Prompt: {text}"
    assert prompts.inject_text(template, "value") == "Prompt: value"


def test_inject_text_appends_block_when_missing_placeholder():
    template = "Summarize the following input."
    result = prompts.inject_text(template, "sample")
    assert result.startswith(template)
    assert "sample" in result
