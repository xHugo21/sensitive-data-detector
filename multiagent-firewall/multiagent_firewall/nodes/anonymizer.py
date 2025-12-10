from __future__ import annotations

import os
import re
from typing import Dict

from ..types import GuardState


def anonymize_llm_input(state: GuardState) -> GuardState:
    """Obfuscate detected sensitive values before sending text to remote LLMs."""
    text = state.get("normalized_text") or ""
    detected = state.get("detected_fields") or []

    if not text or not detected:
        state["anonymized_text"] = text
        return state

    anonymized_map: Dict[str, str] = {}
    field_counts: Dict[str, int] = {}

    for item in detected:
        if not isinstance(item, dict):
            continue
        value = item.get("value")
        if not value or not isinstance(value, str):
            continue
        field = (item.get("field") or item.get("type") or "FIELD").strip().upper()

        # Reuse the same anonymized token if we've already seen this exact value
        if value in anonymized_map:
            continue

        field_counts[field] = field_counts.get(field, 0) + 1
        anonymized_token = f"<<{field}_{field_counts[field]}>>"
        anonymized_map[value] = anonymized_token

    # Apply replacements longest-first to avoid partial overlaps
    masked_text = text
    for original, anonymized_token in sorted(
        anonymized_map.items(), key=lambda kv: len(kv[0]), reverse=True
    ):
        masked_text = re.sub(re.escape(original), anonymized_token, masked_text)

    state["anonymized_text"] = masked_text

    metadata = state.setdefault("metadata", {})
    metadata["llm_anonymized_values"] = {
        "enabled": True,
        "provider": _provider(),
        "mapping": anonymized_map,
    }
    return state


def _provider() -> str:
    return (os.getenv("LLM_PROVIDER") or "openai").strip().lower()
