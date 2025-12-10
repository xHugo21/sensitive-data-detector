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

    masked = result.get("llm_input_text", "")
    assert "<<EMAIL_1>>" in masked
    assert "<<NAME_1>>" in masked
    placeholders = result.get("metadata", {}).get("llm_placeholders", {})
    assert placeholders.get("enabled") is True
    assert placeholders.get("mapping", {}).get("john@example.com") == "<<EMAIL_1>>"


def test_anonymize_llm_input_disabled(monkeypatch):
    state: GuardState = {
        "normalized_text": "Email john@example.com",
        "detected_fields": [{"field": "EMAIL", "value": "john@example.com"}],
        "metadata": {},
        "warnings": [],
        "errors": [],
    }

    result = anonymize_llm_input(state)

    assert result.get("llm_input_text") != "Email john@example.com"
    placeholders = result.get("metadata", {}).get("llm_placeholders")
    assert placeholders is not None
    assert placeholders.get("enabled") is True
