from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from langchain_litellm import ChatLiteLLM
from langchain_core.prompts import ChatPromptTemplate

from .prompts import PROMPT_MAP, inject_text, load_prompt, resolve_mode


def safe_json_from_text(s: str) -> dict:
    if not s:
        return {}
    match = re.search(r"\{.*\}", s, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except Exception:
        return {}


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


def _str_to_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _maybe_prefix_model(model: str | None, provider: str) -> str | None:
    if not model:
        return model
    if provider == "openai":
        return model
    if model.startswith(f"{provider}/"):
        return model
    return f"{provider}/{model}"


@dataclass(frozen=True)
class LiteLLMConfig:
    provider: str
    model: str
    supports_json_mode: bool
    client_params: Dict[str, Any]

    @classmethod
    def from_env(cls) -> "LiteLLMConfig":
        provider = os.getenv("LLM_PROVIDER", "openai").lower()
        model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        api_key = os.getenv("LLM_API_KEY")
        base_url = os.getenv("LLM_BASE_URL")
        api_version = os.getenv("LLM_API_VERSION")
        supports_json_mode = _str_to_bool(
            os.getenv("LLM_SUPPORTS_JSON_MODE"),
            provider in {"openai", "groq"},
        )

        if not api_key:
            raise RuntimeError(
                f"Missing API key for provider '{provider}'. "
                "Set LLM_API_KEY in your environment."
            )

        client_params: Dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_params["api_base"] = base_url
        if api_version:
            client_params["api_version"] = api_version
        client_params.update(_json_env("LLM_EXTRA_PARAMS"))

        return cls(
            provider=provider,
            model=model,
            supports_json_mode=supports_json_mode,
            client_params=client_params,
        )


class LiteLLMDetector:
    _SYSTEM_MESSAGE = "You are to output a single valid JSON object only. No prose, no markdown."

    def __init__(
        self,
        config: LiteLLMConfig,
        *,
        prompt_dir: str | Path | None = None,
        prompt_map: Dict[str, str] | None = None,
        llm: Any | None = None,
    ) -> None:
        self._config = config
        self._provider = config.provider
        self._model = config.model
        self._prompt_dir = Path(prompt_dir) if prompt_dir else None
        self._prompt_map = dict(PROMPT_MAP)
        if prompt_map:
            self._prompt_map.update(prompt_map)

        model_id = _maybe_prefix_model(self._model, self._provider)
        if llm is None:
            self._llm = ChatLiteLLM(model=model_id, **config.client_params)
        else:
            self._llm = llm

        if hasattr(self._llm, "bind"):
            self._json_llm = self._llm.bind(response_format={"type": "json_object"})
        else:
            self._json_llm = None

        self._prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", self._SYSTEM_MESSAGE),
                ("user", "{prompt_content}"),
            ]
        )

    @classmethod
    def from_env(cls, **kwargs: Any) -> "LiteLLMDetector":
        return cls(LiteLLMConfig.from_env(), **kwargs)

    def __call__(self, text: str, prompt: str | None, mode: str | None):
        try:
            prompt_content, prompt_info = self._build_prompt(text, prompt, mode)
            try:
                content = self._invoke(prompt_content, json_mode=self._config.supports_json_mode)
            except Exception:
                content = self._invoke(prompt_content, json_mode=False)

            result = safe_json_from_text(content) or {"detected_fields": []}
            if "detected_fields" not in result or not isinstance(result["detected_fields"], list):
                result["detected_fields"] = []
            result["_prompt_source"] = prompt_info
            result["_model_used"] = self._model
            result["_provider"] = self._provider
            return result
        except Exception as exc:
            return {"detected_fields": [], "risk_level": "Unknown", "_error": str(exc)}

    def _build_prompt(
        self,
        text: str,
        prompt: str | None,
        mode: str | None,
    ) -> tuple[str, str]:
        if prompt and prompt.strip():
            final_prompt = inject_text(prompt.strip(), text)
            return final_prompt, "custom"

        resolved = resolve_mode(mode)
        prompt_filename = self._prompt_map.get(resolved)
        if not prompt_filename:
            raise RuntimeError(f"Prompt mode '{resolved}' not found")

        template = load_prompt(
            resolved,
            prompt_dir=self._prompt_dir,
            prompt_map=self._prompt_map,
        )
        final_prompt = inject_text(template, text)
        return final_prompt, f"prompts/{prompt_filename}"

    def _invoke(self, prompt_content: str, *, json_mode: bool) -> str:
        model = self._json_llm if json_mode and self._json_llm else self._llm
        messages = self._prompt_template.format_messages(prompt_content=prompt_content)
        response = model.invoke(messages)
        content = getattr(response, "content", None)
        if content is None:
            return str(response)
        return (content or "").strip()
