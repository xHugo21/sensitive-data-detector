from __future__ import annotations

import pytest
from multiagent_firewall.nodes.detection import (
    run_dlp_detector,
    run_llm_detector,
    run_ocr_detector,
)
from multiagent_firewall.types import GuardState


def test_run_llm_detector_success():
    def mock_llm_detector(text: str, prompt: str | None, mode: str | None) -> dict:
        return {
            "detected_fields": [
                {"field": "EMAIL", "value": "test@example.com"},
                {"field": "NAME", "value": "John Doe"},
            ]
        }
    
    state: GuardState = {
        "normalized_text": "Contact John Doe at test@example.com",
        "prompt": None,
        "mode": None,
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    
    result = run_llm_detector(state, mock_llm_detector)
    
    assert "llm_fields" in result
    assert len(result["llm_fields"]) == 2
    assert all(f["source"] == "llm_detector" for f in result["llm_fields"])


def test_run_llm_detector_empty_text():
    def mock_llm_detector(text: str, prompt: str | None, mode: str | None) -> dict:
        return {"detected_fields": []}
    
    state: GuardState = {
        "normalized_text": "",
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    
    result = run_llm_detector(state, mock_llm_detector)
    
    assert result["llm_fields"] == []


def test_run_llm_detector_exception():
    def mock_llm_detector(text: str, prompt: str | None, mode: str | None) -> dict:
        raise RuntimeError("LLM service unavailable")
    
    state: GuardState = {
        "normalized_text": "Some text",
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    
    result = run_llm_detector(state, mock_llm_detector)
    
    assert result["llm_fields"] == []
    assert any("LLM detector failed" in e for e in result.get("errors", []))


def test_run_dlp_detector_with_regex():
    regex_patterns = {
        "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    }
    
    state: GuardState = {
        "normalized_text": "Contact us at support@example.com",
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    
    result = run_dlp_detector(state, regex_patterns)
    
    assert "dlp_fields" in result
    assert len(result["dlp_fields"]) >= 1
    email_findings = [f for f in result["dlp_fields"] if f["field"] == "EMAIL"]
    assert len(email_findings) >= 1
    assert email_findings[0]["source"] == "dlp_regex"


def test_run_dlp_detector_with_keywords():
    keywords = {
        "API_KEY": ["api_key", "apikey"],
    }
    
    state: GuardState = {
        "normalized_text": "My api_key is secret123",
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    
    result = run_dlp_detector(state, {}, keywords)
    
    assert "dlp_fields" in result
    keyword_findings = [f for f in result["dlp_fields"] if f["source"] == "dlp_keyword"]
    assert len(keyword_findings) >= 1


def test_run_dlp_detector_with_checksums():
    state: GuardState = {
        "normalized_text": "Card number: 4532015112830366",
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    
    result = run_dlp_detector(state, {})
    
    assert "dlp_fields" in result
    checksum_findings = [f for f in result["dlp_fields"] if f["source"] == "dlp_checksum"]
    assert len(checksum_findings) >= 1


def test_run_dlp_detector_empty_text():
    state: GuardState = {
        "normalized_text": "",
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    
    result = run_dlp_detector(state, {})
    
    assert result["dlp_fields"] == []


def test_run_ocr_detector_with_detector():
    def mock_ocr_detector(state: GuardState) -> list:
        return [
            {"field": "TEXT_IN_IMAGE", "value": "Some text", "source": "ocr"},
        ]
    
    state: GuardState = {
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    
    result = run_ocr_detector(state, mock_ocr_detector)
    
    assert "ocr_fields" in result
    assert len(result["ocr_fields"]) == 1


def test_run_ocr_detector_without_detector():
    state: GuardState = {
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    
    result = run_ocr_detector(state, None)
    
    assert result.get("ocr_fields") == []


def test_run_ocr_detector_exception():
    def mock_ocr_detector(state: GuardState) -> list:
        raise RuntimeError("OCR service unavailable")
    
    state: GuardState = {
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    
    result = run_ocr_detector(state, mock_ocr_detector)
    
    assert result["ocr_fields"] == []
    assert any("OCR detector failed" in e for e in result.get("errors", []))
