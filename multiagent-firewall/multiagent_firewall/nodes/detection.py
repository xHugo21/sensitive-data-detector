from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping

from ..detectors.dlp import detect_checksums, detect_keywords, detect_regex_patterns
from ..types import FieldList, GuardState

DetectorResult = Mapping[str, Any]
LLMDetector = Callable[[str, str | None, str | None], DetectorResult]
OCRDetector = Callable[[GuardState], FieldList]


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
    keywords: Mapping[str, Any] | None = None,
) -> GuardState:
    text = state.get("normalized_text") or ""
    findings: FieldList = []
    
    try:
        regex_findings = detect_regex_patterns(text, regex_patterns)
        findings.extend(regex_findings)
    except Exception as exc:
        _append_error(state, f"Regex detector failed: {exc}")
    
    try:
        keyword_findings = detect_keywords(text, keywords)
        findings.extend(keyword_findings)
    except Exception as exc:
        _append_error(state, f"Keyword detector failed: {exc}")
    
    try:
        checksum_findings = detect_checksums(text)
        findings.extend(checksum_findings)
    except Exception as exc:
        _append_error(state, f"Checksum detector failed: {exc}")
    
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
    if "errors" not in state:
        state["errors"] = []
    state["errors"].append(message)
