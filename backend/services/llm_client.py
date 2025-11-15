import json
import os
from typing import Any, Dict

import litellm
from core.config import LLM_PROVIDER


def _json_env(var_name: str) -> Dict[str, Any]:
    raw = os.getenv(var_name)
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{var_name} must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError(f"{var_name} must encode a JSON object with key/value pairs")
    return parsed


def _build_client_config() -> Dict[str, Any]:
    provider = LLM_PROVIDER

    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    api_version = os.getenv("LLM_API_VERSION")

    if not api_key:
        raise RuntimeError(
            f"Missing API key for provider '{provider}'. Set LLM_API_KEY in your backend environment."
        )

    config: Dict[str, Any] = {"api_key": api_key}
    if base_url:
        config["api_base"] = base_url
    if api_version:
        config["api_version"] = api_version

    # Allow arbitrary LiteLLM kwargs via JSON blob.
    config.update(_json_env("LLM_EXTRA_PARAMS"))

    return config


def _maybe_prefix_model(model: str | None, provider: str) -> str | None:
    if not model:
        return model
    if provider == "openai":
        return model
    if model.startswith(f"{provider}/"):
        return model
    if "/" in model:
        return model
    return f"{provider}/{model}"


class _ChatCompletionAdapter:
    def __init__(self, base_config: Dict[str, Any], provider: str):
        self._base_config = base_config
        self._provider = provider

    def create(self, **kwargs):
        params = dict(self._base_config)
        params.update(kwargs)
        params["model"] = _maybe_prefix_model(params.get("model"), self._provider)
        return litellm.completion(**params)


class _ChatAdapter:
    def __init__(self, base_config: Dict[str, Any], provider: str):
        self.completions = _ChatCompletionAdapter(base_config, provider)


class LiteLLMClient:
    def __init__(self, base_config: Dict[str, Any], provider: str):
        self.chat = _ChatAdapter(base_config, provider)


client = LiteLLMClient(_build_client_config(), LLM_PROVIDER)
