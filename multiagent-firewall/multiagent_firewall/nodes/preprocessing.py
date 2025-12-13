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
    return (name or "").strip().upper().replace("-", "").replace("_", "")


def _canonical_fields_by_normalized() -> dict[str, str]:
    canonical: dict[str, str] = {}
    for group in (HIGH_RISK_FIELDS, MEDIUM_RISK_FIELDS, LOW_RISK_FIELDS):
        for field in group:
            canonical[_normalize_field_name(field)] = field
    return canonical


_CANONICAL_FIELDS = _canonical_fields_by_normalized()


def _canonicalize_field(item: dict) -> dict:
    raw_field = item.get("field") or item.get("type") or ""
    raw_source = item.get("source")
    source = raw_source if isinstance(raw_source, str) else ""

    normalized = _normalize_field_name(str(raw_field))
    canonical = _CANONICAL_FIELDS.get(normalized)
    if canonical:
        return {**item, "field": canonical}
    if source and source.lower().startswith("llm_"):
        return {**item, "field": "OTHER"}
    return item


def normalize(state: GuardState) -> GuardState:
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
    if key not in state:
        state[key] = []
    state[key].append(value)


def _field_risk(item: dict) -> str:
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
