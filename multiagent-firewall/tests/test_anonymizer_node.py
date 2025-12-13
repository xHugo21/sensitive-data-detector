from __future__ import annotations

import os

from multiagent_firewall.nodes.anonymizer import anonymize_llm_input
from multiagent_firewall.types import GuardState


def test_anonymize_llm_input_masks_detected_fields(monkeypatch):
    state: GuardState = {
        "normalized_text": "Contact John Doe at john@example.com",
        "detected_fields": [
            {"field": "EMAIL", "value": "john@example.com"},
            {"field": "NAME", "value": "John Doe"},
        ],
        "metadata": {},
        "warnings": [],
        "errors": [],
    }

    result = anonymize_llm_input(state)

    masked = result.get("anonymized_text", "")
    assert "<<REDACTED:EMAIL>>" in masked
    assert "<<REDACTED:NAME>>" in masked
    anonymized = result.get("metadata", {}).get("llm_anonymized_values", {})
    assert anonymized.get("enabled") is True
    assert anonymized.get("mapping", {}).get("john@example.com") == "<<REDACTED:EMAIL>>"


def test_anonymize_llm_input_disabled(monkeypatch):
    state: GuardState = {
        "normalized_text": "Email john@example.com",
        "detected_fields": [{"field": "EMAIL", "value": "john@example.com"}],
        "metadata": {},
        "warnings": [],
        "errors": [],
    }

    result = anonymize_llm_input(state)

    assert result.get("anonymized_text") != "Email john@example.com"
    anonymized = result.get("metadata", {}).get("llm_anonymized_values")
    assert anonymized is not None
    assert anonymized.get("enabled") is True
