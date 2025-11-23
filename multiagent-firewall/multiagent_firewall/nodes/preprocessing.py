from __future__ import annotations

import re
from typing import Any

from ..types import FieldList, GuardState

_whitespace_re = re.compile(r"\s+")


def normalize(state: GuardState) -> GuardState:
    text = state.get("raw_text") or ""
    normalized = _whitespace_re.sub(" ", text).strip()
    state["normalized_text"] = normalized
    if not normalized:
        _append(state, "warnings", "No text provided for analysis.")
    return state


def merge_detections(state: GuardState) -> GuardState:
    merged: FieldList = []
    seen = set()
    for key in ("llm_fields", "dlp_fields", "ocr_fields"):
        for item in state.get(key, []) or []:
            if not isinstance(item, dict):
                continue
            field = (item.get("field") or "").strip()
            value = (item.get("value") or "").strip()
            signature = (field.lower(), value.lower())
            if signature in seen:
                continue
            seen.add(signature)
            merged.append(item)
    state["detected_fields"] = merged
    return state


def _append(state: GuardState, key: str, value: Any) -> None:
    if key not in state:
        state[key] = []
    state[key].append(value)
