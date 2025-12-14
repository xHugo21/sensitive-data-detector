from __future__ import annotations

from ..detectors import LiteLLMDetector
from ..detectors.dlp import detect_checksums, detect_keywords, detect_regex_patterns
from ..constants import KEYWORDS, REGEX_PATTERNS
from ..types import FieldList, GuardState
from ..utils import append_error


def run_llm_detector(state: GuardState, *, fw_config) -> GuardState:
    """
    Run LLM-based detection
    """
    text = state.get("anonymized_text") or state.get("normalized_text") or ""
    anonymized_map = (
        state.get("metadata", {})
        .get("llm_anonymized_values", {})
        .get("mapping", {})
        or {}
    )
    reverse_map = {}
    for original, token in anonymized_map.items():
        reverse_map.setdefault(token, set()).add(original)

    anonymized_tokens = set(reverse_map.keys())
    anonymized_stripped = {token.strip("<>") for token in anonymized_tokens}

    if not text:
        state["llm_fields"] = []
        return state
    try:
        llm_config = fw_config.llm
        llm_detector = LiteLLMDetector(
            provider=llm_config.provider,
            model=llm_config.model,
            client_params=llm_config.client_params,
        )
        result = llm_detector(text)
        fields = []
        for item in result.get("detected_fields", []):
            if not isinstance(item, dict):
                continue
            value = item.get("value")
            if isinstance(value, str):
                if value in reverse_map and len(reverse_map[value]) == 1:
                    item = {**item, "value": next(iter(reverse_map[value]))}
                elif (
                    value in anonymized_tokens
                    or _is_redacted_token(value)
                    or _is_anonymized_token(value)
                    or value in anonymized_stripped
                ):
                    # Skip unknown anonymized values to avoid surfacing obfuscated values
                    continue
            fields.append({**item, "source": _normalize_llm_source(item.get("source"))})
        state["llm_fields"] = fields
    except Exception as exc:
        append_error(state, f"LLM detector failed: {exc}")
        state["llm_fields"] = []
    return state


def _normalize_llm_source(raw_source: object | None) -> str:
    """Normalize the LLM detector source label so it is identifiable as LLM output."""
    if not raw_source:
        return "llm_detector"
    if isinstance(raw_source, str):
        normalized = raw_source.strip().lower()
        if normalized == "explicit":
            return "llm_explicit"
        if normalized == "inferred":
            return "llm_inferred"
        if normalized.startswith("llm_"):
            return normalized
    return str(raw_source)


def _is_anonymized_token(value: str) -> bool:
    return value.startswith("<<") and value.endswith(">>")


def _is_redacted_token(value: str) -> bool:
    core = value.strip("<>")
    return core.startswith("REDACTED:")


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
