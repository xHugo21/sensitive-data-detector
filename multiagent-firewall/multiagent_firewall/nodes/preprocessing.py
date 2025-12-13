from __future__ import annotations

import re
from typing import Any

from ..types import FieldList, GuardState
from ..constants import HIGH_RISK_FIELDS, MEDIUM_RISK_FIELDS, LOW_RISK_FIELDS

_whitespace_re = re.compile(r"\s+")
_system_reminder_re = re.compile(
    r"<system-reminder>.*?</system-reminder>", flags=re.DOTALL | re.IGNORECASE
)


def _normalize_field_name(name: str) -> str:
    """Normalize a field label for matching (case/format-insensitive)."""
    return (name or "").strip().upper().replace("-", "").replace("_", "")


_ALLOWED_FIELDS_NORMALIZED = {
    _normalize_field_name(field)
    for group in (HIGH_RISK_FIELDS, MEDIUM_RISK_FIELDS, LOW_RISK_FIELDS)
    for field in group
}


def _canonicalize_field(item: dict) -> dict:
    """Canonicalize `field` names and relabel unknown LLM fields to OTHER."""
    raw_field = item.get("field") or item.get("type") or ""
    raw_source = item.get("source")
    source = raw_source if isinstance(raw_source, str) else ""

    normalized = _normalize_field_name(str(raw_field))
    if normalized in _ALLOWED_FIELDS_NORMALIZED:
        return {**item, "field": normalized}
    if source and source.lower().startswith("llm_"):
        return {**item, "field": "OTHER"}
    return item


def normalize(state: GuardState) -> GuardState:
    """Normalize raw text (strip system artifacts and collapse whitespace)."""
    text = state.get("raw_text") or ""

    # Remove system tags (e.g., OpenCode CLI artifacts)
    text = _system_reminder_re.sub("", text)

    # Normalize whitespace
    normalized = _whitespace_re.sub(" ", text).strip()

    state["normalized_text"] = normalized
    if not normalized:
        _append(state, "warnings", "No text provided for analysis.")
    return state


def merge_detections(state: GuardState) -> GuardState:
    """Merge LLM + DLP detections, de-duplicate, and compute per-field risk."""
    merged: FieldList = []
    seen = set()
    for key in ("llm_fields", "dlp_fields"):
        for item in state.get(key, []) or []:
            if not isinstance(item, dict):
                continue
            item = _canonicalize_field(item)
            field = (item.get("field") or "").strip()
            value = (item.get("value") or "").strip()
            signature = (field.lower(), value.lower())
            if signature in seen:
                continue
            seen.add(signature)
            item = dict(item)
            item["risk"] = item.get("risk") or _field_risk(item)
            merged.append(item)
    state["detected_fields"] = merged
    return state


def _append(state: GuardState, key: str, value: Any) -> None:
    """Append a value to a list stored on the state (creating it if needed)."""
    if key not in state:
        state[key] = []
    state[key].append(value)


def _field_risk(item: dict) -> str:
    """Assign a risk label based on the canonical field name."""
    name = item.get("field") or item.get("type") or ""
    field = str(name).strip()
    if field == "OTHER":
        return "high"
    if field in HIGH_RISK_FIELDS:
        return "high"
    if field in MEDIUM_RISK_FIELDS:
        return "medium"
    if field in LOW_RISK_FIELDS:
        return "low"
    return "medium"
