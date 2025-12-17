from __future__ import annotations

from multiagent_firewall.nodes.anonymizer import anonymize_text
from multiagent_firewall.types import GuardState


def test_anonymize_text_masks_dlp_fields(monkeypatch, guard_config):
    state: GuardState = {
        "normalized_text": "Contact John Doe at john@example.com",
        "dlp_fields": [
            {"field": "EMAIL", "value": "john@example.com"},
            {"field": "NAME", "value": "John Doe"},
        ],
        "metadata": {},
        "warnings": [],
        "errors": [],
    }

    result = anonymize_text(
        state,
        fw_config=guard_config,
        findings_key="dlp_fields",
        text_keys=("normalized_text",),
    )

    masked = result.get("anonymized_text", "")
    assert "<<REDACTED:EMAIL>>" in masked
    assert "<<REDACTED:NAME>>" in masked
    anonymized = result.get("metadata", {}).get("llm_anonymized_values", {})
    assert anonymized.get("enabled") is True
    assert anonymized.get("mapping", {}).get("john@example.com") == "<<REDACTED:EMAIL>>"


def test_anonymize_text_disabled(monkeypatch, guard_config):
    state: GuardState = {
        "normalized_text": "Email john@example.com",
        "dlp_fields": [{"field": "EMAIL", "value": "john@example.com"}],
        "metadata": {},
        "warnings": [],
        "errors": [],
    }

    result = anonymize_text(
        state,
        fw_config=guard_config,
        findings_key="dlp_fields",
        text_keys=("normalized_text",),
    )

    assert result.get("anonymized_text") != "Email john@example.com"
    anonymized = result.get("metadata", {}).get("llm_anonymized_values")
    assert anonymized is not None
    assert anonymized.get("enabled") is True


def test_anonymize_text_handles_llm_fields_after_dlp(guard_config):
    state: GuardState = {
        "normalized_text": "Email john@example.com and password secret123",
        "dlp_fields": [{"field": "EMAIL", "value": "john@example.com"}],
        "metadata": {
            "llm_anonymized_values": {"mapping": {"john@example.com": "<<REDACTED:EMAIL>>"}}
        },
        "warnings": [],
        "errors": [],
    }

    result = anonymize_text(
        state,
        fw_config=guard_config,
        findings_key="dlp_fields",
        text_keys=("normalized_text",),
    )
    result["llm_fields"] = [{"field": "PASSWORD", "value": "secret123"}]
    result = anonymize_text(
        result,
        fw_config=guard_config,
        findings_key="llm_fields",
        text_keys=("anonymized_text", "normalized_text", "raw_text"),
    )

    masked = result.get("anonymized_text", "")
    mapping = (
        result.get("metadata", {})
        .get("llm_anonymized_values", {})
        .get("mapping", {})
    )

    assert "<<REDACTED:EMAIL>>" in masked
    assert "<<REDACTED:PASSWORD>>" in masked
    assert "john@example.com" not in masked
    assert "secret123" not in masked
    assert mapping.get("john@example.com") == "<<REDACTED:EMAIL>>"
    assert mapping.get("secret123") == "<<REDACTED:PASSWORD>>"


def test_anonymize_text_masks_case_insensitive_llm_values(guard_config):
    state: GuardState = {
        "normalized_text": "hi my name is andres",
        "llm_fields": [{"field": "FIRSTNAME", "value": "ANDRES", "source": "llm_explicit"}],
        "metadata": {},
        "warnings": [],
        "errors": [],
    }

    result = anonymize_text(
        state,
        fw_config=guard_config,
        findings_key="llm_fields",
        text_keys=("normalized_text",),
    )

    masked = result.get("anonymized_text", "")
    mapping = (
        result.get("metadata", {})
        .get("llm_anonymized_values", {})
        .get("mapping", {})
    )

    assert "<<REDACTED:FIRSTNAME>>" in masked
    assert "andres" not in masked.lower()
    assert mapping.get("ANDRES") == "<<REDACTED:FIRSTNAME>>"
