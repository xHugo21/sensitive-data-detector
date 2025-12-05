import pytest
from pathlib import Path

from multiagent_firewall.detectors import llm
from multiagent_firewall.constants import LLM_PROMPT_MAP
from multiagent_firewall.utils import build_litellm_model_string


def test_json_env_returns_empty_when_variable_missing(monkeypatch):
    monkeypatch.delenv("TEST_JSON_ENV", raising=False)
    assert llm._json_env("TEST_JSON_ENV") == {}


def test_json_env_parses_valid_json(monkeypatch):
    monkeypatch.setenv("TEST_JSON_ENV", '{"timeout": 30, "retries": 1}')
    assert llm._json_env("TEST_JSON_ENV") == {"timeout": 30, "retries": 1}


def test_json_env_errors_on_invalid_payload(monkeypatch):
    monkeypatch.setenv("TEST_JSON_ENV", "{not-valid json")
    with pytest.raises(RuntimeError):
        llm._json_env("TEST_JSON_ENV")


def test_json_env_requires_object_payload(monkeypatch):
    monkeypatch.setenv("TEST_JSON_ENV", '["a", "b"]')
    with pytest.raises(RuntimeError):
        llm._json_env("TEST_JSON_ENV")


def test_config_from_env_requires_api_key(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        llm.LiteLLMConfig.from_env()


def test_config_from_env_includes_optional_fields(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "secret-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.com")
    monkeypatch.setenv("LLM_API_VERSION", "v1")
    monkeypatch.setenv("LLM_EXTRA_PARAMS", '{"timeout": 10, "top_p": 0.5}')
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("LLM_MODEL", "sonnet")
    monkeypatch.setenv("LLM_SUPPORTS_JSON_MODE", "false")

    config = llm.LiteLLMConfig.from_env()

    assert config.provider == "anthropic"
    assert config.model == "sonnet"
    assert config.supports_json_mode is False
    assert config.client_params["api_key"] == "secret-key"
    assert config.client_params["api_base"] == "https://example.com"
    assert config.client_params["api_version"] == "v1"
    assert config.client_params["timeout"] == 10
    assert config.client_params["top_p"] == 0.5


def test_maybe_prefix_model_handles_providers():
    """Test build_litellm_model_string utility function"""
    # OpenAI doesn't get prefixed
    assert build_litellm_model_string("gpt-4o", "openai") == "gpt-4o"
    # Other providers get prefixed
    assert build_litellm_model_string("claude-3", "anthropic") == "anthropic/claude-3"
    # Already prefixed models stay as-is
    assert (
        build_litellm_model_string("anthropic/claude-3", "anthropic")
        == "anthropic/claude-3"
    )


# Prompt mapping and resolution tests


def test_prompt_map_has_expected_modes():
    """Test that LLM_PROMPT_MAP contains the expected detection modes"""
    assert "zero-shot" in LLM_PROMPT_MAP
    assert "enriched-zero-shot" in LLM_PROMPT_MAP
    assert "few-shot" in LLM_PROMPT_MAP
    assert len(LLM_PROMPT_MAP) >= 3


def test_prompt_map_values_are_filenames():
    """Test that LLM_PROMPT_MAP values are valid .txt filenames"""
    for _, filename in LLM_PROMPT_MAP.items():
        assert isinstance(filename, str)
        assert filename.endswith(".txt")
        assert "/" not in filename  # Should be just filenames, not paths


def test_prompt_files_exist():
    """Test that all prompt files referenced in LLM_PROMPT_MAP actually exist"""
    # Get the prompts directory
    prompts_dir = Path(__file__).parent.parent / "multiagent_firewall" / "prompts"

    for llm_prompt, filename in LLM_PROMPT_MAP.items():
        prompt_path = prompts_dir / filename
        assert (
            prompt_path.exists()
        ), f"Prompt file missing for mode '{llm_prompt}': {prompt_path}"
        assert prompt_path.is_file(), f"Prompt path is not a file: {prompt_path}"


def test_resolve_llm_prompt_with_valid_mode():
    """Test that _resolve_llm_prompt returns the mode when it's valid"""
    assert llm._resolve_llm_prompt("zero-shot") == "zero-shot"
    assert llm._resolve_llm_prompt("few-shot") == "few-shot"
    assert llm._resolve_llm_prompt("enriched-zero-shot") == "enriched-zero-shot"


def test_resolve_llm_prompt_with_none():
    """Test that _resolve_llm_prompt falls back to first LLM_PROMPT_MAP key when mode is None"""
    expected_fallback = next(iter(LLM_PROMPT_MAP))
    assert llm._resolve_llm_prompt(None) == expected_fallback


def test_resolve_llm_prompt_with_invalid_mode():
    """Test that _resolve_llm_prompt falls back to first LLM_PROMPT_MAP key for invalid mode"""
    expected_fallback = next(iter(LLM_PROMPT_MAP))
    assert llm._resolve_llm_prompt("invalid-mode") == expected_fallback
    assert llm._resolve_llm_prompt("") == expected_fallback


def test_inject_text_with_placeholder():
    """Test that _inject_text replaces {text} placeholder correctly"""
    template = "Analyze the following: {text}"
    result = llm._inject_text(template, "sample data")
    assert result == "Analyze the following: sample data"
    assert "{text}" not in result


def test_inject_text_without_placeholder():
    """Test that _inject_text appends text when no placeholder exists"""
    template = "Analyze the following input."
    result = llm._inject_text(template, "sample data")
    assert result.startswith("Analyze the following input.")
    assert "sample data" in result
    assert "Text:" in result


def test_inject_text_preserves_formatting():
    """Test that _inject_text preserves multiline templates"""
    template = "Line 1\nLine 2\n{text}\nLine 4"
    result = llm._inject_text(template, "inserted")
    assert "Line 1" in result
    assert "Line 2" in result
    assert "inserted" in result
    assert "Line 4" in result
