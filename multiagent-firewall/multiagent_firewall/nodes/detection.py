from __future__ import annotations

from ..detectors import LiteLLMDetector
from ..detectors.dlp import detect_checksums, detect_keywords, detect_regex_patterns
from ..constants import REGEX_PATTERNS, KEYWORDS
from ..types import FieldList, GuardState
from ..utils import append_error


def run_llm_detector(state: GuardState) -> GuardState:
    """
    Run LLM-based detection
    """
    text = state.get("normalized_text") or ""
    if not text:
        state["llm_fields"] = []
        return state
    try:
        llm_detector = LiteLLMDetector.from_env()
        result = llm_detector(
            text,
            state.get("llm_prompt"),
        )
        fields = [
            {**item, "source": item.get("source", "llm_detector")}
            for item in result.get("detected_fields", [])
            if isinstance(item, dict)
        ]
        state["llm_fields"] = fields
    except Exception as exc:
        append_error(state, f"LLM detector failed: {exc}")
        state["llm_fields"] = []
    return state


def run_dlp_detector(state: GuardState) -> GuardState:
    """
    Run DLP detection

    Runs regex, keyword and checksum detectors
    """
    text = state.get("normalized_text") or ""
    findings: FieldList = []

    try:
        regex_findings = detect_regex_patterns(text, REGEX_PATTERNS)
        findings.extend(regex_findings)
    except Exception as exc:
        append_error(state, f"Regex detector failed: {exc}")

    try:
        keyword_findings = detect_keywords(text, KEYWORDS)
        findings.extend(keyword_findings)
    except Exception as exc:
        append_error(state, f"Keyword detector failed: {exc}")

    try:
        checksum_findings = detect_checksums(text)
        findings.extend(checksum_findings)
    except Exception as exc:
        append_error(state, f"Checksum detector failed: {exc}")

    state["dlp_fields"] = findings
    return state
