import pytest

from multiagent_firewall import llm


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
    assert llm._maybe_prefix_model(None, "openai") is None
    assert llm._maybe_prefix_model("gpt-4o", "openai") == "gpt-4o"
    assert llm._maybe_prefix_model("claude-3", "anthropic") == "anthropic/claude-3"
    assert (
        llm._maybe_prefix_model("anthropic/claude-3", "anthropic")
        == "anthropic/claude-3"
    )
