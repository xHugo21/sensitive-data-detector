from __future__ import annotations

import asyncio
from ..detectors import GlinerNERDetector, LiteLLMDetector
from ..detectors.dlp import detect_checksums, detect_keywords, detect_regex_patterns
from ..constants import KEYWORDS, REGEX_PATTERNS
from ..types import FieldList, GuardState
from ..utils import append_error


async def run_llm_detector(state: GuardState, *, fw_config) -> GuardState:
    """
    Run LLM-based detection
    """
    text = state.get("anonymized_text") or state.get("normalized_text") or ""
    anonymized_map = (
        state.get("metadata", {}).get("llm_anonymized_values", {}).get("mapping", {})
        or {}
    )
    reverse_map = {}
    for original, token in anonymized_map.items():
        reverse_map.setdefault(token, set()).add(original)

    anonymized_tokens = set(reverse_map.keys())
    anonymized_stripped = {token.strip("<>") for token in anonymized_tokens}
    anonymized_originals = {
        value for value in anonymized_map.keys() if isinstance(value, str)
    }
    anonymized_originals_normalized = {
        value.strip().lower()
        for value in anonymized_originals
        if isinstance(value, str) and value.strip()
    }

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
        result = await llm_detector.acall(text)
        fields = []
        for item in result.get("detected_fields", []):
            if not isinstance(item, dict):
                continue
            value = item.get("value")
            if isinstance(value, str):
                value_normalized = value.strip().lower()
                if (
                    value in anonymized_tokens
                    or _is_redacted_token(value)
                    or _is_anonymized_token(value)
                    or value in anonymized_stripped
                    or _contains_anonymized_token(
                        value, anonymized_tokens, anonymized_stripped
                    )
                    or value in anonymized_originals
                    or value_normalized in anonymized_originals_normalized
                ):
                    # Skip anonymized tokens and any mapped originals to avoid reintroducing redacted data
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


async def run_dlp_detector(state: GuardState) -> GuardState:
    """
    Run DLP detection

    Runs regex, keyword and checksum detectors
    """
    text = state.get("normalized_text") or ""
    findings: FieldList = []
    errors: list[str] = []

    async def _safe_run(func, *args):
        try:
            return await asyncio.to_thread(func, *args)
        except Exception as exc:
            return exc

    # Run internal detectors in parallel
    results = await asyncio.gather(
        _safe_run(detect_regex_patterns, text, REGEX_PATTERNS),
        _safe_run(detect_keywords, text, KEYWORDS),
        _safe_run(detect_checksums, text),
    )

    regex_res, keyword_res, checksum_res = results

    if isinstance(regex_res, list):
        findings.extend(regex_res)
    else:
        errors.append(f"Regex detector failed: {regex_res}")

    if isinstance(keyword_res, list):
        findings.extend(keyword_res)
    else:
        errors.append(f"Keyword detector failed: {keyword_res}")

    if isinstance(checksum_res, list):
        findings.extend(checksum_res)
    else:
        errors.append(f"Checksum detector failed: {checksum_res}")

    update: GuardState = {"dlp_fields": findings}
    if errors:
        update["errors"] = errors
    return update


async def run_ner_detector(state: GuardState, *, fw_config) -> GuardState:
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
        # Load model first (likely cached)
        ner_detector = GlinerNERDetector(
            model=ner_config.model,
            labels=ner_config.labels,
            label_map=ner_config.label_map,
            min_score=ner_config.min_score,
        )
        # Run inference in thread
        findings = await asyncio.to_thread(ner_detector.detect, text)
        return {"ner_fields": findings}
    except Exception as exc:
        return {
            "ner_fields": [],
            "errors": [f"NER detector failed: {exc}"],
        }
