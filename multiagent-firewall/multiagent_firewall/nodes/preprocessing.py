from __future__ import annotations

import re
from typing import Any

from ..types import FieldList, GuardState
from ..config.detection import HIGH_RISK_FIELDS, MEDIUM_RISK_FIELDS, LOW_RISK_FIELDS

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
    sources = _collect_sources(item)

    normalized = _normalize_field_name(str(raw_field))
    if normalized in _ALLOWED_FIELDS_NORMALIZED:
        return {**item, "field": normalized}
    if any(source.lower().startswith("llm_") for source in sources):
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
    """Merge LLM + DLP + NER detections, de-duplicate, and compute per-field risk."""
    merged: FieldList = []
    seen: dict[tuple[str, str], int] = {}
    for key in ("llm_fields", "dlp_fields", "ner_fields"):
        for item in state.get(key, []) or []:
            if not isinstance(item, dict):
                continue
            item = _canonicalize_field(item)
            field = (item.get("field") or "").strip()
            value = (item.get("value") or "").strip()
            signature = (field.lower(), value.lower())
            sources = _collect_sources(item)
            if signature in seen:
                existing = merged[seen[signature]]
                existing["sources"] = _merge_sources(
                    existing.get("sources") or [], sources
                )
                continue
            item = dict(item)
            item.pop("source", None)
            item["sources"] = sources
            item["risk"] = item.get("risk") or _field_risk(item)
            merged.append(item)
            seen[signature] = len(merged) - 1
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


def _collect_sources(item: dict) -> list[str]:
    """Collect sources from `sources` (list) or legacy `source` (string)."""
    raw_sources = item.get("sources")
    if raw_sources is None:
        raw_sources = item.get("source")
    if isinstance(raw_sources, list):
        candidates = raw_sources
    elif raw_sources is None:
        candidates = []
    else:
        candidates = [raw_sources]
    sources: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, str):
            continue
        cleaned = candidate.strip()
        if not cleaned:
            continue
        if cleaned not in sources:
            sources.append(cleaned)
    return sources


def _merge_sources(existing: list[str], incoming: list[str]) -> list[str]:
    """Merge sources, preserving order and removing duplicates."""
    combined: list[str] = []
    for candidate in existing + incoming:
        if not isinstance(candidate, str):
            continue
        cleaned = candidate.strip()
        if not cleaned:
            continue
        if cleaned not in combined:
            combined.append(cleaned)
    return combined
