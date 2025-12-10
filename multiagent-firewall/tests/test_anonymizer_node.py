from __future__ import annotations

import os

from multiagent_firewall.nodes.anonymizer import anonymize_llm_input
from multiagent_firewall.types import GuardState


def test_anonymize_llm_input_masks_detected_fields(monkeypatch):
    monkeypatch.setenv("ANONYMIZE_FOR_REMOTE_LLM", "true")
    monkeypatch.setenv("LLM_PROVIDER", "openai")

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


def test_anonymize_llm_input_skips_for_ollama(monkeypatch):
    monkeypatch.setenv("ANONYMIZE_FOR_REMOTE_LLM", "true")
    monkeypatch.setenv("LLM_PROVIDER", "ollama")

    state: GuardState = {
        "normalized_text": "Token sk-abc",
        "detected_fields": [{"field": "TOKEN", "value": "sk-abc"}],
        "metadata": {},
        "warnings": [],
        "errors": [],
    }

    result = anonymize_llm_input(state)

    assert result.get("llm_input_text") == "Token sk-abc"
    placeholders = result.get("metadata", {}).get("llm_placeholders")
    assert placeholders is None or placeholders.get("enabled") is not True


def test_anonymize_llm_input_disabled(monkeypatch):
    monkeypatch.delenv("ANONYMIZE_FOR_REMOTE_LLM", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "openai")

    state: GuardState = {
        "normalized_text": "Email john@example.com",
        "detected_fields": [{"field": "EMAIL", "value": "john@example.com"}],
        "metadata": {},
        "warnings": [],
        "errors": [],
    }

    result = anonymize_llm_input(state)

    assert result.get("llm_input_text") == "Email john@example.com"
    placeholders = result.get("metadata", {}).get("llm_placeholders")
    assert placeholders is None or placeholders.get("enabled") is not True
