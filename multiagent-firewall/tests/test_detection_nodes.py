from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from multiagent_firewall.nodes.detection import (
    run_dlp_detector,
    run_llm_detector,
)
from multiagent_firewall.types import GuardState


@patch('multiagent_firewall.nodes.detection.LiteLLMDetector.from_env')
def test_run_llm_detector_success(mock_llm_from_env):
    """Test LLM detector with successful detection"""
    mock_detector = MagicMock()
    mock_detector.return_value = {
        "detected_fields": [
            {"field": "EMAIL", "value": "test@example.com"},
            {"field": "NAME", "value": "John Doe"},
        ]
    }
    mock_llm_from_env.return_value = mock_detector
    
    state: GuardState = {
        "normalized_text": "Contact John Doe at test@example.com",
        "llm_prompt": None,
        "warnings": [],
        "errors": [],
    }
    
    result = run_llm_detector(state)
    
    assert "llm_fields" in result
    assert len(result.get("llm_fields", [])) == 2
    assert all(f["source"] == "llm_detector" for f in result.get("llm_fields", []))


@patch('multiagent_firewall.nodes.detection.LiteLLMDetector.from_env')
def test_run_llm_detector_empty_text(mock_llm_from_env):
    """Test LLM detector with empty text"""
    mock_detector = MagicMock()
    mock_detector.return_value = {"detected_fields": []}
    mock_llm_from_env.return_value = mock_detector
    
    state: GuardState = {
        "normalized_text": "",
        "warnings": [],
        "errors": [],
    }
    
    result = run_llm_detector(state)
    
    assert result.get("llm_fields") == []


@patch('multiagent_firewall.nodes.detection.LiteLLMDetector.from_env')
def test_run_llm_detector_exception(mock_llm_from_env):
    """Test LLM detector handles exceptions gracefully"""
    mock_detector = MagicMock()
    mock_detector.side_effect = RuntimeError("LLM service unavailable")
    mock_llm_from_env.return_value = mock_detector
    
    state: GuardState = {
        "normalized_text": "Some text",
        "warnings": [],
        "errors": [],
    }
    
    result = run_llm_detector(state)
    
    assert result.get("llm_fields") == []
    assert any("LLM detector failed" in e for e in result.get("errors", []))


@patch('multiagent_firewall.nodes.detection.LiteLLMDetector.from_env')
def test_run_llm_detector_normalizes_source_labels(mock_llm_from_env):
    """LLM findings should be tagged as LLM-derived rather than Explicit/Inferred"""
    mock_detector = MagicMock()
    mock_detector.return_value = {
        "detected_fields": [
            {"field": "EMAIL", "value": "test@example.com", "source": "Explicit"},
            {"field": "NAME", "value": "John Doe", "source": "Inferred"},
        ]
    }
    mock_llm_from_env.return_value = mock_detector

    state: GuardState = {
        "normalized_text": "Contact John Doe at test@example.com, ZIP 12345",
        "llm_prompt": None,
        "warnings": [],
        "errors": [],
    }

    result = run_llm_detector(state)

    sources = [f["source"] for f in result.get("llm_fields", [])]
    assert sources == ["llm_explicit", "llm_inferred"]


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
    assert email_findings[0]["source"] == "dlp_regex"


def test_run_dlp_detector_with_keywords():
    """Test DLP detector with keywords (uses constants by default)"""
    state: GuardState = {
        "normalized_text": "key header -----BEGIN PRIVATE KEY----- data",
        "warnings": [],
        "errors": [],
    }
    
    result = run_dlp_detector(state)
    
    assert "dlp_fields" in result
    dlp_fields = result.get("dlp_fields", [])
    keyword_findings = [f for f in dlp_fields if f["source"] == "dlp_keyword"]
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
    checksum_findings = [f for f in dlp_fields if f["source"] == "dlp_checksum"]
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
