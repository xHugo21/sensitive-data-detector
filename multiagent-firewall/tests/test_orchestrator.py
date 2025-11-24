from __future__ import annotations

import pytest
from unittest.mock import MagicMock
from multiagent_firewall.orchestrator import GuardOrchestrator
from multiagent_firewall.types import GuardState


def test_orchestrator_initialization_custom():
    def custom_risk_evaluator(fields):
        return "High"
    
    def custom_llm_detector(text, prompt, mode):
        return {"detected_fields": []}
    
    custom_regex = {"EMAIL": r"\b[\w.-]+@[\w.-]+\.\w+\b"}
    custom_keywords = {"SECRET": ["secret"]}
    
    orchestrator = GuardOrchestrator(
        risk_evaluator=custom_risk_evaluator,
        llm_detector=custom_llm_detector,
        regex_patterns=custom_regex,
        keywords=custom_keywords,
    )
    
    assert orchestrator._risk_evaluator == custom_risk_evaluator
    assert orchestrator._llm_detector == custom_llm_detector
    assert orchestrator._regex_patterns == custom_regex
    assert orchestrator._keywords == custom_keywords
    assert orchestrator._graph is not None


def test_orchestrator_run_basic():
    def mock_llm_detector(text, prompt, mode):
        return {"detected_fields": []}
    
    orchestrator = GuardOrchestrator(llm_detector=mock_llm_detector)
    result = orchestrator.run("Hello world")
    
    assert isinstance(result, dict)
    assert "raw_text" in result
    assert result.get("raw_text") == "Hello world"


def test_orchestrator_run_with_metadata():
    def mock_llm_detector(text, prompt, mode):
        return {"detected_fields": []}
    
    orchestrator = GuardOrchestrator(llm_detector=mock_llm_detector)
    metadata = {"user_id": "123", "session": "abc"}
    result = orchestrator.run(
        "Test text",
        prompt="Analyze this",
        mode="strict",
        metadata=metadata,
    )
    
    assert result.get("prompt") == "Analyze this"
    assert result.get("mode") == "strict"
    assert result.get("metadata") == metadata


def test_orchestrator_run_empty_text():
    def mock_llm_detector(text, prompt, mode):
        return {"detected_fields": []}
    
    orchestrator = GuardOrchestrator(llm_detector=mock_llm_detector)
    result = orchestrator.run("")
    
    assert result.get("raw_text") == ""
    assert "warnings" in result


def test_orchestrator_graph_structure():
    def mock_llm_detector(text, prompt, mode):
        return {"detected_fields": []}
    
    orchestrator = GuardOrchestrator(llm_detector=mock_llm_detector)
    graph = orchestrator._graph
    
    assert graph is not None


def test_orchestrator_run_with_sensitive_data():
    def mock_llm_detector(text, prompt, mode):
        return {
            "detected_fields": [
                {"field": "EMAIL", "value": "test@example.com"},
                {"field": "PASSWORD", "value": "secret123"},
            ]
        }
    
    orchestrator = GuardOrchestrator(llm_detector=mock_llm_detector)
    result = orchestrator.run("My email is test@example.com and password is secret123")
    
    assert "detected_fields" in result
    assert "risk_level" in result
    assert "decision" in result
