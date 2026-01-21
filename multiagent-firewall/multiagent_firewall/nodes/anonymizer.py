from __future__ import annotations

import re
from typing import Dict, Iterable, Sequence

from ..types import GuardState


def anonymize_text(
    state: GuardState,
    *,
    fw_config,
    findings_key: str,
    text_keys: Sequence[str],
) -> GuardState:
    """Obfuscate sensitive values found in `findings_key` and update anonymized_text."""
    text = _select_text(state, text_keys)
    findings = state.get(findings_key) or []

    state["anonymized_text"] = _apply_anonymization(
        text=text, findings=findings, state=state, fw_config=fw_config
    )
    return state


def _select_text(state: GuardState, keys: Sequence[str]) -> str:
    for key in keys:
        value = state.get(key)
        if isinstance(value, str):
            return value
    return ""


def _apply_anonymization(
    *, text: str, findings: Iterable[dict], state: GuardState, fw_config
) -> str:
    existing_map = _existing_map(state)
    masked_text, anonymized_map = _anonymize_text(text, findings, existing_map)
    _store_mapping(state, anonymized_map, fw_config)
    return masked_text


def _anonymize_text(
    text: str, findings: Iterable[dict], existing_map: Dict[str, str] | None
) -> tuple[str, Dict[str, str]]:
    anonymized_map: Dict[str, str] = dict(existing_map or {})

    counters: Dict[str, int] = {}
    for token in anonymized_map.values():
        match = re.match(r"<<REDACTED:(.+)_(\d+)>>", token)
        if match:
            f_name = match.group(1)
            try:
                num = int(match.group(2))
                counters[f_name] = max(counters.get(f_name, 0), num)
            except ValueError:
                pass

    if not text or not findings:
        return text, anonymized_map

    for item in findings:
        if not isinstance(item, dict):
            continue
        value = item.get("value")
        if not value or not isinstance(value, str):
            continue
        field = (item.get("field") or item.get("type") or "FIELD").strip().upper()

        if value in anonymized_map:
            continue

        count = counters.get(field, 0) + 1
        counters[field] = count

        anonymized_token = f"<<REDACTED:{field}_{count}>>"
        anonymized_map[value] = anonymized_token

    masked_text = _apply_mapping(text, anonymized_map)
    return masked_text, anonymized_map


def _apply_mapping(text: str, mapping: Dict[str, str]) -> str:
    if not text or not mapping:
        return text

    masked_text = text
    for original, anonymized_token in sorted(
        mapping.items(), key=lambda kv: len(kv[0]), reverse=True
    ):
        masked_text = re.sub(
            re.escape(original),
            anonymized_token,
            masked_text,
            flags=re.IGNORECASE,
        )
    return masked_text


def _store_mapping(state: GuardState, mapping: Dict[str, str], fw_config) -> None:
    metadata = state.setdefault("metadata", {})
    metadata["llm_anonymized_values"] = {
        "enabled": True,
        "provider": _provider(fw_config),
        "mapping": mapping,
    }


def _existing_map(state: GuardState) -> Dict[str, str]:
    return (
        state.get("metadata", {}).get("llm_anonymized_values", {}).get("mapping", {})
        or {}
    )


def _provider(fw_config) -> str:
    return (fw_config.llm.provider or "openai").strip().lower()
