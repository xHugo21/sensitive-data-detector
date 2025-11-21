from __future__ import annotations

import re
from typing import Mapping, Sequence

from ..types import (
    DLPDetector,
    FieldList,
    GuardState,
    LLMDetector,
    OCRDetector,
)


def run_llm_detector(
    state: GuardState,
    llm_detector: LLMDetector,
) -> GuardState:
    text = state.get("normalized_text") or ""
    if not text:
        state["llm_fields"] = []
        return state
    try:
        result = llm_detector(
            text,
            state.get("prompt"),
            state.get("mode"),
        )
        fields = [
            {**item, "source": item.get("source", "llm_detector")}
            for item in result.get("detected_fields", [])
            if isinstance(item, dict)
        ]
        state["llm_fields"] = fields
    except Exception as exc:
        _append_error(state, f"LLM detector failed: {exc}")
        state["llm_fields"] = []
    return state


def run_dlp_detector(
    state: GuardState,
    regex_patterns: Mapping[str, str],
    extra_dlp_detectors: Sequence[DLPDetector],
) -> GuardState:
    text = state.get("normalized_text") or ""
    findings: FieldList = []
    for field_name, pattern in regex_patterns.items():
        for match in re.findall(pattern, text):
            value = match if isinstance(match, str) else " ".join(match)
            cleaned = value.strip()
            if not cleaned:
                continue
            findings.append(
                {"field": field_name, "value": cleaned, "source": "dlp_regex"}
            )
    for detector in extra_dlp_detectors:
        try:
            extra = detector(text) or []
            for item in extra:
                if isinstance(item, dict):
                    findings.append(item)
        except Exception as exc:
            _append_error(state, f"DLP detector failed: {exc}")
    state["dlp_fields"] = findings
    return state


def run_ocr_detector(
    state: GuardState,
    ocr_detector: OCRDetector | None,
) -> GuardState:
    if not ocr_detector:
        state.setdefault("ocr_fields", [])
        return state
    try:
        state["ocr_fields"] = ocr_detector(state) or []
    except Exception as exc:
        _append_error(state, f"OCR detector failed: {exc}")
        state["ocr_fields"] = []
    return state


def _append_error(state: GuardState, message: str) -> None:
    state.setdefault("errors", [])
    state["errors"].append(message)
