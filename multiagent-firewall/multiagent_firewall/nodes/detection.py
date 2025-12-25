from __future__ import annotations

from ..detectors import GlinerNERDetector, LiteLLMDetector
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
                    or _contains_anonymized_token(
                        value, anonymized_tokens, anonymized_stripped
                    )
                ):
                    # Skip unknown anonymized values to avoid surfacing obfuscated values
                    continue
            raw_sources = item.get("sources")
            if raw_sources is None:
                raw_sources = item.get("source")
            if isinstance(raw_sources, list):
                source_items = raw_sources
            elif raw_sources is None:
                source_items = []
            else:
                source_items = [raw_sources]
            normalized_sources: list[str] = []
            for raw_source in source_items:
                normalized = _normalize_llm_source(raw_source)
                if normalized and normalized not in normalized_sources:
                    normalized_sources.append(normalized)
            if not normalized_sources:
                normalized_sources.append("llm_explicit")
            cleaned = {k: v for k, v in item.items() if k not in ("source", "sources")}
            cleaned["sources"] = normalized_sources
            fields.append(cleaned)
        state["llm_fields"] = fields
    except Exception as exc:
        append_error(state, f"LLM detector failed: {exc}")
        state["llm_fields"] = []
    return state


def _normalize_llm_source(raw_source: object | None) -> str:
    """Normalize the LLM detector source label so it is identifiable as LLM output."""
    if not raw_source:
        return ""
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


def _contains_anonymized_token(
    value: str, tokens: set[str], stripped_tokens: set[str]
) -> bool:
    if not value:
        return False
    for token in tokens:
        if token and token in value:
            return True
    for token in stripped_tokens:
        if token and token in value:
            return True
    return False


def run_dlp_detector(state: GuardState) -> GuardState:
    """
    Run DLP detection

    Runs regex, keyword and checksum detectors
    """
    text = state.get("normalized_text") or ""
    findings: FieldList = []
    errors: list[str] = []

    try:
        regex_findings = detect_regex_patterns(text, REGEX_PATTERNS)
        findings.extend(regex_findings)
    except Exception as exc:
        errors.append(f"Regex detector failed: {exc}")

    try:
        keyword_findings = detect_keywords(text, KEYWORDS)
        findings.extend(keyword_findings)
    except Exception as exc:
        errors.append(f"Keyword detector failed: {exc}")

    try:
        checksum_findings = detect_checksums(text)
        findings.extend(checksum_findings)
    except Exception as exc:
        errors.append(f"Checksum detector failed: {exc}")

    update: GuardState = {"dlp_fields": findings}
    if errors:
        update["errors"] = errors
    return update


def run_ner_detector(state: GuardState, *, fw_config) -> GuardState:
    """
    Run NER-based detection
    """
    text = state.get("normalized_text") or ""
    if not text:
        return {"ner_fields": []}

    ner_config = getattr(fw_config, "ner", None)
    if not ner_config or not ner_config.enabled:
        return {"ner_fields": []}

    try:
        ner_detector = GlinerNERDetector(
            model=ner_config.model,
            labels=ner_config.labels,
            label_map=ner_config.label_map,
            min_score=ner_config.min_score,
        )
        return {"ner_fields": ner_detector.detect(text)}
    except Exception as exc:
        return {
            "ner_fields": [],
            "errors": [f"NER detector failed: {exc}"],
        }
