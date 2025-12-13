from __future__ import annotations

import json
import os
from typing import Any, Dict


def build_litellm_model_string(model: str, provider: str) -> str:
    """Build LiteLLM model id from provider + model."""
    if provider == "openai":
        return model
    if model.startswith(f"{provider}/"):
        return model
    return f"{provider}/{model}"


def build_chat_litellm(*, provider: str, model: str, client_params: Dict[str, Any]):
    """Construct a ChatLiteLLM client using normalized model id + params."""
    from langchain_litellm import ChatLiteLLM

    model_id = build_litellm_model_string(model, provider)
    return ChatLiteLLM(model=model_id, **client_params)


def coerce_litellm_content_to_text(response: Any) -> str:
    """Coerce a LangChain/LiteLLM response into a plain string."""
    content = getattr(response, "content", None)
    if content is None:
        return str(response).strip()
    if isinstance(content, str):
        return content.strip()
    return ""


def json_env(var_name: str) -> Dict[str, Any]:
    """Parse an env var as a JSON object (or return {})."""
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


def json_env_with_fallback(primary: str, fallback: str | None) -> Dict[str, Any]:
    """Merge JSON env objects, with primary overriding fallback."""
    merged: Dict[str, Any] = {}
    if fallback:
        merged.update(json_env(fallback))
    merged.update(json_env(primary))
    return merged


def env_with_fallback(primary: str, fallback: str | None) -> str | None:
    """Read an env var with optional fallback env var name."""
    value = os.getenv(primary)
    if value:
        return value
    if fallback:
        return os.getenv(fallback)
    return None


def load_litellm_env(
    *,
    prefix: str,
    fallback_prefix: str | None = None,
    default_provider: str,
    default_model: str,
    require_api_key: bool = True,
) -> tuple[str, str, Dict[str, Any]]:
    """Load LiteLLM env configuration for a prefix with optional fallback prefix."""
    provider = (
        env_with_fallback(f"{prefix}_PROVIDER", f"{fallback_prefix}_PROVIDER")
        or default_provider
    ).strip()
    model = (
        env_with_fallback(f"{prefix}_MODEL", f"{fallback_prefix}_MODEL")
        or default_model
    ).strip()

    api_key = env_with_fallback(f"{prefix}_API_KEY", f"{fallback_prefix}_API_KEY")
    base_url = env_with_fallback(f"{prefix}_BASE_URL", f"{fallback_prefix}_BASE_URL")
    api_version = env_with_fallback(
        f"{prefix}_API_VERSION", f"{fallback_prefix}_API_VERSION"
    )

    extra_params = json_env_with_fallback(
        f"{prefix}_EXTRA_PARAMS",
        f"{fallback_prefix}_EXTRA_PARAMS" if fallback_prefix else None,
    )

    if require_api_key and not api_key:
        raise RuntimeError(f"Missing API key for provider '{provider}'.")

    client_params: Dict[str, Any] = {}
    if api_key:
        client_params["api_key"] = api_key
    if base_url:
        client_params["api_base"] = base_url
    if api_version:
        client_params["api_version"] = api_version
    client_params.update(extra_params)

    return provider.lower(), model, client_params
