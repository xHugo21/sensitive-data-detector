import pytest

from services import llm_client


def test_json_env_returns_empty_when_variable_missing(monkeypatch):
    monkeypatch.delenv("TEST_JSON_ENV", raising=False)
    assert llm_client._json_env("TEST_JSON_ENV") == {}


def test_json_env_parses_valid_json(monkeypatch):
    monkeypatch.setenv("TEST_JSON_ENV", '{"timeout": 30, "retries": 1}')
    assert llm_client._json_env("TEST_JSON_ENV") == {"timeout": 30, "retries": 1}


def test_json_env_errors_on_invalid_payload(monkeypatch):
    monkeypatch.setenv("TEST_JSON_ENV", "{not-valid json")
    with pytest.raises(RuntimeError):
        llm_client._json_env("TEST_JSON_ENV")


def test_json_env_requires_object_payload(monkeypatch):
    monkeypatch.setenv("TEST_JSON_ENV", '["a", "b"]')
    with pytest.raises(RuntimeError):
        llm_client._json_env("TEST_JSON_ENV")


def test_build_client_config_requires_api_key(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        llm_client._build_client_config()


def test_build_client_config_includes_optional_fields(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "secret-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.com")
    monkeypatch.setenv("LLM_API_VERSION", "v1")
    monkeypatch.setenv("LLM_EXTRA_PARAMS", '{"timeout": 10, "top_p": 0.5}')

    config = llm_client._build_client_config()

    assert config["api_key"] == "secret-key"
    assert config["api_base"] == "https://example.com"
    assert config["api_version"] == "v1"
    assert config["timeout"] == 10
    assert config["top_p"] == 0.5


def test_maybe_prefix_model_handles_providers():
    assert llm_client._maybe_prefix_model(None, "openai") is None
    assert llm_client._maybe_prefix_model("gpt-4o", "openai") == "gpt-4o"
    assert (
        llm_client._maybe_prefix_model("claude-3", "anthropic") == "anthropic/claude-3"
    )
    assert (
        llm_client._maybe_prefix_model("anthropic/claude-3", "anthropic")
        == "anthropic/claude-3"
    )
