import pytest
from pathlib import Path
from unittest.mock import MagicMock

from multiagent_firewall.detectors import llm
from multiagent_firewall.detection_config import LLM_DETECTOR_PROMPT
from multiagent_firewall.detectors.utils import build_litellm_model_string
from multiagent_firewall.detectors.utils import json_env
from multiagent_firewall.config import GuardConfig


def test_json_env_returns_empty_when_variable_missing(monkeypatch):
    monkeypatch.delenv("TEST_JSON_ENV", raising=False)
    assert json_env("TEST_JSON_ENV") == {}


def test_json_env_parses_valid_json(monkeypatch):
    monkeypatch.setenv("TEST_JSON_ENV", '{"timeout": 30, "retries": 1}')
    assert json_env("TEST_JSON_ENV") == {"timeout": 30, "retries": 1}


def test_json_env_errors_on_invalid_payload(monkeypatch):
    monkeypatch.setenv("TEST_JSON_ENV", "{not-valid json")
    with pytest.raises(RuntimeError):
        json_env("TEST_JSON_ENV")


def test_json_env_requires_object_payload(monkeypatch):
    monkeypatch.setenv("TEST_JSON_ENV", '["a", "b"]')
    with pytest.raises(RuntimeError):
        json_env("TEST_JSON_ENV")


def test_config_from_env_requires_api_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o-mini")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        GuardConfig.from_env()


def test_config_from_env_includes_optional_fields(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "secret-key")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.com")
    monkeypatch.setenv("LLM_API_VERSION", "v1")
    monkeypatch.setenv("LLM_EXTRA_PARAMS", '{"timeout": 10, "top_p": 0.5}')
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("LLM_MODEL", "sonnet")

    config = GuardConfig.from_env()

    assert config.llm.provider == "anthropic"
    assert config.llm.model == "sonnet"
    assert config.llm.client_params["api_key"] == "secret-key"
    assert config.llm.client_params["api_base"] == "https://example.com"
    assert config.llm.client_params["api_version"] == "v1"
    assert config.llm.client_params["timeout"] == 10
    assert config.llm.client_params["top_p"] == 0.5
    assert config.llm_ocr.provider == "anthropic"
    assert config.llm_ocr.model == "sonnet"


def test_config_from_env_uses_llm_ocr_overrides(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o")
    monkeypatch.setenv("LLM_API_KEY", "sk-main")
    monkeypatch.setenv("LLM_OCR_PROVIDER", "anthropic")
    monkeypatch.setenv("LLM_OCR_MODEL", "claude-3")
    monkeypatch.setenv("LLM_OCR_API_KEY", "sk-ocr")

    config = GuardConfig.from_env()

    assert config.llm_ocr.provider == "anthropic"
    assert config.llm_ocr.model == "claude-3"
    assert config.llm_ocr.client_params["api_key"] == "sk-ocr"


def test_config_from_env_parses_ocr_settings(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o")
    monkeypatch.setenv("LLM_API_KEY", "sk-main")
    monkeypatch.setenv("OCR_LANG", "spa")
    monkeypatch.setenv("OCR_CONFIG", "--psm 6")
    monkeypatch.setenv("OCR_CONFIDENCE_THRESHOLD", "120")
    monkeypatch.setenv("TESSERACT_CMD", "/usr/bin/tesseract")

    config = GuardConfig.from_env()

    assert config.ocr.lang == "spa"
    assert config.ocr.config == "--psm 6"
    # Threshold should be clamped to 100
    assert config.ocr.confidence_threshold == 100
    assert config.ocr.tesseract_cmd == "/usr/bin/tesseract"


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


def test_prompt_file_exists():
    """LLM detector prompt file should exist"""
    prompts_dir = Path(__file__).parent.parent / "multiagent_firewall" / "prompts"
    prompt_path = prompts_dir / LLM_DETECTOR_PROMPT
    assert prompt_path.exists()
    assert prompt_path.is_file()


def test_build_prompt_splits_system_and_user():
    """_build_prompt should return system instructions and raw user text separately"""
    detector = llm.LiteLLMDetector(
        provider="dummy",
        model="dummy",
        client_params={},
        llm=MagicMock(),  # bypass real client
    )
    system_prompt, user_prompt, info = detector._build_prompt("sample data")
    assert "sample data" == user_prompt
    assert "{text}" not in system_prompt
    assert info == f"prompts/{LLM_DETECTOR_PROMPT}"


def test_inject_sensitive_fields_replaces_placeholder():
    template = "Header\n{sensitive_fields}\nFooter"
    result = llm._inject_sensitive_fields(template)
    assert "{sensitive_fields}" not in result
    assert "- " in result


def test_inject_sensitive_fields_includes_all_risk_sets():
    block = llm._build_sensitive_fields_block()
    assert "- PASSWORD" in block
    assert "- EMAIL" in block
    assert "- FIRSTNAME" in block
