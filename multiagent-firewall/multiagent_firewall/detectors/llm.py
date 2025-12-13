from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from ..constants import LLM_PROMPT_MAP
from .utils import (
    build_chat_litellm,
    coerce_litellm_content_to_text,
    load_litellm_env,
)


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


def _resolve_llm_prompt(llm_prompt: str | None) -> str:
    """Resolve LLM prompt: use explicit prompt if valid, otherwise fallback to first key."""
    fallback = next(iter(LLM_PROMPT_MAP))
    if llm_prompt and llm_prompt in LLM_PROMPT_MAP:
        return llm_prompt
    return fallback


def _inject_text(template: str, text: str) -> str:
    """Inject text into template, using {text} placeholder or appending."""
    if "{text}" in template:
        return template.replace("{text}", text)
    return f"{template.rstrip()}\n\nText:\n'''{text}'''"


@dataclass(frozen=True)
class LiteLLMConfig:
    provider: str
    model: str
    client_params: Dict[str, Any]

    # TODO: Consume LLM configuration params from package parameters instead of env variables
    @classmethod
    def from_env(cls) -> "LiteLLMConfig":
        provider, model, client_params = load_litellm_env(
            prefix="LLM",
            default_provider="openai",
            default_model="gpt-4o-mini",
            require_api_key=True,
        )
        return cls(provider=provider, model=model, client_params=client_params)


class LiteLLMDetector:
    _SYSTEM_MESSAGE_FORCE_JSON = (
        "You are to output a single valid JSON object only. No prose, no markdown."
    )

    def __init__(
        self,
        config: LiteLLMConfig,
        *,
        prompt_dir: str | Path | None = None,
        llm: Any | None = None,
    ) -> None:
        self._config = config
        self._provider = config.provider
        self._model = config.model

        # Set up prompt directory - default to the prompts folder
        if prompt_dir:
            self._prompt_dir = Path(prompt_dir)
        else:
            # Default: detectors/../prompts
            self._prompt_dir = Path(__file__).resolve().parent.parent / "prompts"

        if llm is None:
            self._llm = build_chat_litellm(
                provider=self._provider,
                model=self._model,
                client_params=config.client_params,
            )
        else:
            self._llm = llm

        if hasattr(self._llm, "bind"):
            self._json_llm = self._llm.bind(response_format={"type": "json_object"})
        else:
            self._json_llm = None

        self._prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", self._SYSTEM_MESSAGE_FORCE_JSON),
                ("user", "{prompt_content}"),
            ]
        )

    @classmethod
    def from_env(cls, **kwargs: Any) -> "LiteLLMDetector":
        return cls(LiteLLMConfig.from_env(), **kwargs)

    def __call__(self, text: str, llm_prompt: str | None):
        try:
            prompt_content, prompt_info = self._build_prompt(text, llm_prompt)
            try:
                content = self._invoke(prompt_content, json_mode=True)
            except Exception:
                content = self._invoke(prompt_content, json_mode=False)

            result = safe_json_from_text(content) or {"detected_fields": []}
            if "detected_fields" not in result or not isinstance(
                result["detected_fields"], list
            ):
                result["detected_fields"] = []
            result["_prompt_source"] = prompt_info
            result["_model_used"] = self._model
            result["_provider"] = self._provider
            return result
        except Exception as exc:
            return {"detected_fields": [], "risk_level": "unknown", "_error": str(exc)}

    def _build_prompt(
        self,
        text: str,
        llm_prompt: str | None,
    ) -> tuple[str, str]:
        """Build the final prompt by loading template and injecting text."""
        # Resolve the llm_prompt
        resolved_prompt = _resolve_llm_prompt(llm_prompt)

        # Get the prompt filename from the map
        prompt_filename = LLM_PROMPT_MAP.get(resolved_prompt)
        if not prompt_filename:
            raise RuntimeError(f"LLM prompt '{resolved_prompt}' not found in map")

        # Load the prompt template from file
        prompt_path = self._prompt_dir / prompt_filename
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

        template = prompt_path.read_text(encoding="utf-8").replace("\r\n", "\n").strip()

        # Inject the text into the template
        final_prompt = _inject_text(template, text)

        return final_prompt, f"prompts/{prompt_filename}"

    def _invoke(self, prompt_content: str, *, json_mode: bool) -> str:
        model = self._json_llm if json_mode and self._json_llm else self._llm
        messages = self._prompt_template.format_messages(prompt_content=prompt_content)
        response = model.invoke(messages)
        return coerce_litellm_content_to_text(response)
