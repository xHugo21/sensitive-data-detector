from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from multiagent_firewall.orchestrator import GuardOrchestrator
from multiagent_firewall.types import GuardState


def test_orchestrator_initialization():
    """Test orchestrator initializes and builds graph"""
    orchestrator = GuardOrchestrator()
    
    # Verify the graph was built
    assert orchestrator._graph is not None


@patch('multiagent_firewall.nodes.detection.LiteLLMDetector.from_env')
def test_orchestrator_run_basic(mock_llm_from_env):
    """Test basic orchestrator run"""
    mock_detector = MagicMock()
    mock_detector.return_value = {"detected_fields": []}
    mock_llm_from_env.return_value = mock_detector
    
    orchestrator = GuardOrchestrator()
    result = orchestrator.run(text="Hello world")
    
    assert isinstance(result, dict)
    assert "raw_text" in result
    assert result.get("raw_text") == "Hello world"


@patch('multiagent_firewall.nodes.detection.LiteLLMDetector.from_env')
def test_orchestrator_run_with_prompt_and_mode(mock_llm_from_env):
    """Test orchestrator run with mode parameter"""
    mock_detector = MagicMock()
    mock_detector.return_value = {"detected_fields": []}
    mock_llm_from_env.return_value = mock_detector
    
    orchestrator = GuardOrchestrator()
    result = orchestrator.run(
        text="Test text",
        mode="strict",
    )
    
    assert result.get("mode") == "strict"


@patch('multiagent_firewall.nodes.detection.LiteLLMDetector.from_env')
def test_orchestrator_run_empty_text(mock_llm_from_env):
    """Test orchestrator with empty text"""
    mock_detector = MagicMock()
    mock_detector.return_value = {"detected_fields": []}
    mock_llm_from_env.return_value = mock_detector
    
    orchestrator = GuardOrchestrator()
    result = orchestrator.run(text="")
    
    assert result.get("raw_text") == ""
    assert "warnings" in result


def test_orchestrator_graph_structure():
    """Test orchestrator graph structure"""
    orchestrator = GuardOrchestrator()
    graph = orchestrator._graph
    
    assert graph is not None


@patch('multiagent_firewall.nodes.detection.LiteLLMDetector.from_env')
def test_orchestrator_run_with_sensitive_data(mock_llm_from_env):
    """Test orchestrator with sensitive data detection"""
    mock_detector = MagicMock()
    mock_detector.return_value = {
        "detected_fields": [
            {"field": "EMAIL", "value": "test@example.com"},
            {"field": "PASSWORD", "value": "secret123"},
        ]
    }
    mock_llm_from_env.return_value = mock_detector
    
    orchestrator = GuardOrchestrator()
    result = orchestrator.run(text="My email is test@example.com and password is secret123")
    
    assert "detected_fields" in result
    assert "risk_level" in result
    assert "decision" in result
    assert all("risk" in f for f in result["detected_fields"])
    risk_map = {f["field"]: f["risk"] for f in result["detected_fields"]}
    assert risk_map.get("PASSWORD") == "high"
    assert risk_map.get("EMAIL") == "medium"


@patch('multiagent_firewall.nodes.detection.LiteLLMDetector.from_env')
def test_orchestrator_run_with_file_path(mock_llm_from_env, tmp_path):
    """Test orchestrator with file_path parameter"""
    mock_detector = MagicMock()
    mock_detector.return_value = {"detected_fields": []}
    mock_llm_from_env.return_value = mock_detector
    
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("File content with SSN 123-45-6789", encoding="utf-8")
    
    orchestrator = GuardOrchestrator()
    result = orchestrator.run(file_path=str(test_file))
    
    assert "raw_text" in result
    assert "File content with SSN" in result["raw_text"]
    assert "detected_fields" in result


@patch('multiagent_firewall.nodes.detection.LiteLLMDetector.from_env')
def test_orchestrator_text_takes_precedence_over_file(mock_llm_from_env, tmp_path):
    """Test that text parameter takes precedence over file_path"""
    mock_detector = MagicMock()
    mock_detector.return_value = {"detected_fields": []}
    mock_llm_from_env.return_value = mock_detector
    
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("File content", encoding="utf-8")
    
    orchestrator = GuardOrchestrator()
    result = orchestrator.run(text="Direct text", file_path=str(test_file))
    
    assert result.get("raw_text") == "Direct text"

