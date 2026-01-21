from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict

from langchain_core.messages import SystemMessage, HumanMessage

from ..config.detection import (
    HIGH_RISK_FIELDS,
    LOW_RISK_FIELDS,
    MEDIUM_RISK_FIELDS,
    LLM_DETECTOR_PROMPT,
)
from .utils import (
    build_chat_litellm,
    coerce_litellm_content_to_text,
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


def _build_sensitive_fields_block() -> str:
    """Build the sensitive fields list for prompts (no risk labels, stable order)."""
    lines: list[str] = []
    for group in (HIGH_RISK_FIELDS, MEDIUM_RISK_FIELDS, LOW_RISK_FIELDS):
        for field in sorted(group, key=lambda s: s.lower()):
            lines.append(f"- {field}")
    return "\n".join(lines)


def _inject_sensitive_fields(template: str) -> str:
    """Inject sensitive fields into template, using {sensitive_fields} placeholder when present."""
    if "{sensitive_fields}" not in template:
        return template
    block = _build_sensitive_fields_block()
    return template.replace("{sensitive_fields}", block)


class LiteLLMDetector:
    def __init__(
        self,
        *,
        provider: str,
        model: str,
        client_params: Dict[str, Any],
        prompt_dir: str | Path | None = None,
        llm: Any | None = None,
    ) -> None:
        self._provider = provider
        self._model = model

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
                client_params=client_params,
            )
        else:
            self._llm = llm

        if hasattr(self._llm, "bind"):
            self._json_llm = self._llm.bind(response_format={"type": "json_object"})
        else:
            self._json_llm = None

        # No prompt template needed: we build explicit SystemMessage + HumanMessage
        self._prompt_template = None

    def __call__(self, text: str):
        try:
            system_prompt, user_prompt, prompt_info = self._build_prompt(text)
            try:
                content = self._invoke(system_prompt, user_prompt, json_mode=True)
            except Exception:
                content = self._invoke(system_prompt, user_prompt, json_mode=False)

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

    async def acall(self, text: str):
        try:
            system_prompt, user_prompt, prompt_info = self._build_prompt(text)
            try:
                content = await self._ainvoke(
                    system_prompt, user_prompt, json_mode=True
                )
            except Exception:
                content = await self._ainvoke(
                    system_prompt, user_prompt, json_mode=False
                )

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
    ) -> tuple[str, str, str]:
        """
        Build the final prompt by loading template and injecting fields.

        Returns (system_prompt, user_prompt, prompt_info)
        """
        # Load the prompt template from file
        prompt_path = self._prompt_dir / LLM_DETECTOR_PROMPT
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

        template = prompt_path.read_text(encoding="utf-8").replace("\r\n", "\n").strip()

        template = _inject_sensitive_fields(template)

        # system: instructions + sensitive fields
        system_prompt = template
        # user: raw text only
        user_prompt = text

        return system_prompt, user_prompt, f"prompts/{LLM_DETECTOR_PROMPT}"

    def _invoke(self, system_prompt: str, user_prompt: str, *, json_mode: bool) -> str:
        model = self._json_llm if json_mode and self._json_llm else self._llm
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        response = model.invoke(messages)
        return coerce_litellm_content_to_text(response)

    async def _ainvoke(
        self, system_prompt: str, user_prompt: str, *, json_mode: bool
    ) -> str:
        model = self._json_llm if json_mode and self._json_llm else self._llm
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        response = await model.ainvoke(messages)
        return coerce_litellm_content_to_text(response)
