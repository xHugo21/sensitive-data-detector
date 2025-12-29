from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from multiagent_firewall.nodes.detection import (
    run_dlp_detector,
    run_llm_detector,
)
from multiagent_firewall.types import GuardState


@patch("multiagent_firewall.nodes.detection.LiteLLMDetector")
def test_run_llm_detector_success(mock_llm_detector, guard_config):
    """Test LLM detector with successful detection"""
    mock_detector = MagicMock()
    mock_detector.return_value = {
        "detected_fields": [
            {"field": "EMAIL", "value": "test@example.com"},
            {"field": "FIRSTNAME", "value": "John"},
        ]
    }
    mock_llm_detector.return_value = mock_detector

    state: GuardState = {
        "normalized_text": "Contact John Doe at test@example.com",
        "warnings": [],
        "errors": [],
    }

    result = run_llm_detector(state, fw_config=guard_config)

    assert "llm_fields" in result
    assert len(result.get("llm_fields", [])) == 2
    assert all(
        f.get("sources") == ["llm_explicit"] for f in result.get("llm_fields", [])
    )
    assert [f["field"] for f in result.get("llm_fields", [])] == [
        "EMAIL",
        "FIRSTNAME",
    ]


@patch("multiagent_firewall.nodes.detection.LiteLLMDetector")
def test_run_llm_detector_empty_text(mock_llm_detector, guard_config):
    """Test LLM detector with empty text"""
    mock_detector = MagicMock()
    mock_detector.return_value = {"detected_fields": []}
    mock_llm_detector.return_value = mock_detector

    state: GuardState = {
        "normalized_text": "",
        "warnings": [],
        "errors": [],
    }

    result = run_llm_detector(state, fw_config=guard_config)

    assert result.get("llm_fields") == []


@patch("multiagent_firewall.nodes.detection.LiteLLMDetector")
def test_run_llm_detector_exception(mock_llm_detector, guard_config):
    """Test LLM detector handles exceptions gracefully"""
    mock_detector = MagicMock()
    mock_detector.side_effect = RuntimeError("LLM service unavailable")
    mock_llm_detector.return_value = mock_detector

    state: GuardState = {
        "normalized_text": "Some text",
        "warnings": [],
        "errors": [],
    }

    result = run_llm_detector(state, fw_config=guard_config)

    assert result.get("llm_fields") == []
    assert any("LLM detector failed" in e for e in result.get("errors", []))


@patch("multiagent_firewall.nodes.detection.LiteLLMDetector")
def test_run_llm_detector_normalizes_source_labels(mock_llm_detector, guard_config):
    """LLM findings should be tagged as LLM-derived rather than Explicit/Inferred"""
    mock_detector = MagicMock()
    mock_detector.return_value = {
        "detected_fields": [
            {"field": "EMAIL", "value": "test@example.com", "sources": ["Explicit"]},
            {"field": "LASTNAME", "value": "Doe", "sources": ["Inferred"]},
        ]
    }
    mock_llm_detector.return_value = mock_detector

    state: GuardState = {
        "normalized_text": "Contact John Doe at test@example.com, ZIP 12345",
        "warnings": [],
        "errors": [],
    }

    result = run_llm_detector(state, fw_config=guard_config)

    sources = [f["sources"] for f in result.get("llm_fields", [])]
    assert sources == [["llm_explicit"], ["llm_inferred"]]
    assert [f["field"] for f in result.get("llm_fields", [])] == [
        "EMAIL",
        "LASTNAME",
    ]


@patch("multiagent_firewall.nodes.detection.LiteLLMDetector")
def test_run_llm_detector_skips_anonymized_tokens(mock_llm_detector, guard_config):
    """Anonymized tokens and mapped originals should be dropped"""
    mock_detector = MagicMock()
    mock_detector.return_value = {
        "detected_fields": [
            {
                "field": "DATE",
                "value": "<<REDACTED:DATE>>",
                "sources": ["Explicit"],
            },
            {
                "field": "DATE",
                "value": "2024-05-12",
                "sources": ["Explicit"],
            },
            {"field": "USERNAME", "value": "john_doe_2024", "sources": ["Explicit"]},
            {
                "field": "EMAIL",
                "value": "<<REDACTED:UNKNOWN>>",
                "sources": ["Explicit"],
            },
            {
                "field": "DATE",
                "value": "+REDACTED:DATE",
                "sources": ["Explicit"],
            },
        ]
    }
    mock_llm_detector.return_value = mock_detector

    state: GuardState = {
        "normalized_text": "My username is john_doe_2024 and it is 2024-05-12",
        "anonymized_text": "My username is john_doe_2024 and it is <<REDACTED:DATE>>",
        "metadata": {
            "llm_anonymized_values": {
                "mapping": {"2024-05-12": "<<REDACTED:DATE>>"}
            }
        },
        "warnings": [],
        "errors": [],
    }

    result = run_llm_detector(state, fw_config=guard_config)

    values = {f["field"]: f["value"] for f in result.get("llm_fields", [])}
    assert values["USERNAME"] == "john_doe_2024"
    assert "DATE" not in values
    assert "EMAIL" not in values  # unknown anonymized token skipped
    assert all(
        any(source.startswith("llm_") for source in f.get("sources", []))
        for f in result.get("llm_fields", [])
    )


def test_run_dlp_detector_with_regex():
    """Test DLP detector with regex patterns (uses constants by default)"""
    state: GuardState = {
        "normalized_text": "Contact us at support@example.com",
        "warnings": [],
        "errors": [],
    }

    result = run_dlp_detector(state)

    assert "dlp_fields" in result
    dlp_fields = result.get("dlp_fields", [])
    assert len(dlp_fields) >= 1
    email_findings = [f for f in dlp_fields if f["field"] == "EMAIL"]
    assert len(email_findings) >= 1
    assert email_findings[0]["sources"] == ["dlp_regex"]


def test_run_dlp_detector_with_keywords():
    """Test DLP detector with keywords (uses constants by default)"""
    state: GuardState = {
        "normalized_text": "Password: SuperSecret123!",
        "warnings": [],
        "errors": [],
    }

    result = run_dlp_detector(state)

    assert "dlp_fields" in result
    dlp_fields = result.get("dlp_fields", [])
    keyword_findings = [f for f in dlp_fields if "dlp_keyword" in f.get("sources", [])]
    assert len(keyword_findings) >= 1


def test_run_dlp_detector_with_checksums():
    """Test DLP detector with checksum validation"""
    state: GuardState = {
        "normalized_text": "Card number: 4532015112830366",
        "warnings": [],
        "errors": [],
    }

    result = run_dlp_detector(state)

    assert "dlp_fields" in result
    dlp_fields = result.get("dlp_fields", [])
    checksum_findings = [
        f for f in dlp_fields if "dlp_checksum" in f.get("sources", [])
    ]
    assert len(checksum_findings) >= 1


def test_run_dlp_detector_empty_text():
    """Test DLP detector with empty text"""
    state: GuardState = {
        "normalized_text": "",
        "warnings": [],
        "errors": [],
    }

    result = run_dlp_detector(state)

    assert result.get("dlp_fields") == []
