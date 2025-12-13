from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from multiagent_firewall.orchestrator import GuardOrchestrator
from multiagent_firewall.nodes import policy, risk
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
def test_orchestrator_run_empty_text(mock_llm_from_env):
    """Test orchestrator with empty text"""
    mock_detector = MagicMock()
    mock_detector.return_value = {"detected_fields": []}
    mock_llm_from_env.return_value = mock_detector
    
    orchestrator = GuardOrchestrator()
    result = orchestrator.run(text="")
    
    assert result.get("raw_text") == ""
    assert "warnings" in result


def test_orchestrator_skips_dlp_policy_when_no_dlp_hits():
    """DLP misses should route straight to LLM and bypass DLP risk/policy."""
    mock_detector = MagicMock()
    mock_detector.return_value = {"detected_fields": []}

    with (
        patch("multiagent_firewall.nodes.detection.LiteLLMDetector.from_env") as mock_llm_from_env,
        patch("multiagent_firewall.nodes.evaluate_risk", wraps=risk.evaluate_risk) as mock_evaluate_risk,
        patch("multiagent_firewall.nodes.apply_policy", wraps=policy.apply_policy) as mock_apply_policy,
    ):
        mock_llm_from_env.return_value = mock_detector

        orchestrator = GuardOrchestrator()
        result = orchestrator.run(text="The sky is clear today.")

    assert mock_evaluate_risk.call_count == 1  # final risk/policy only
    assert mock_apply_policy.call_count == 1
    assert result.get("risk_level") == "none"
    assert result.get("decision") == "allow"


@patch("multiagent_firewall.orchestrator.nodes.run_dlp_detector")
@patch("multiagent_firewall.nodes.detection.LiteLLMDetector.from_env")
def test_orchestrator_short_circuits_on_empty_text(mock_llm_from_env, mock_dlp_detector):
    """Empty text should still run DLP and allow."""
    mock_llm_from_env.return_value = MagicMock()
    mock_dlp_detector.side_effect = lambda state: state
    orchestrator = GuardOrchestrator()

    result = orchestrator.run(text="")

    mock_dlp_detector.assert_called_once()
    mock_llm_from_env.assert_not_called()
    assert result.get("decision") == "allow"
    assert result.get("risk_level") == "none"
    assert not result.get("detected_fields")


@patch("multiagent_firewall.nodes.detection.LiteLLMDetector.from_env")
def test_orchestrator_reuses_dlp_decision_when_llm_adds_nothing(mock_llm_from_env):
    """Skip final risk/policy when LLM does not add new fields."""
    mock_detector = MagicMock()
    mock_detector.return_value = {"detected_fields": []}
    mock_llm_from_env.return_value = mock_detector

    with (
        patch("multiagent_firewall.nodes.evaluate_risk", wraps=risk.evaluate_risk) as mock_evaluate_risk,
        patch("multiagent_firewall.nodes.apply_policy", wraps=policy.apply_policy) as mock_apply_policy,
    ):
        orchestrator = GuardOrchestrator()
        result = orchestrator.run(text="Reach me at test@example.com", min_block_risk="high")

    assert mock_evaluate_risk.call_count == 1  # Only DLP path
    assert mock_apply_policy.call_count == 1
    assert result.get("decision") == "allow_with_warning"
    assert result.get("risk_level") == "low"


@patch("multiagent_firewall.nodes.run_llm_detector")
@patch("multiagent_firewall.nodes.apply_policy")
@patch("multiagent_firewall.nodes.evaluate_risk")
@patch("multiagent_firewall.orchestrator.nodes.run_dlp_detector")
def test_orchestrator_skips_llm_when_policy_blocks(mock_dlp, mock_evaluate_risk, mock_apply_policy, mock_run_llm):
    """If policy decides to block, LLM detector should be skipped."""
    def fake_dlp(state: GuardState):
        state["dlp_fields"] = [{"type": "EMAIL", "value": "x@example.com"}]
        state["detected_fields"] = state["dlp_fields"]
        return state

    mock_dlp.side_effect = fake_dlp
    mock_evaluate_risk.side_effect = lambda state: state | {"risk_level": "high"}

    def block_policy(state: GuardState):
        state["decision"] = "block"
        return state

    mock_apply_policy.side_effect = block_policy

    orchestrator = GuardOrchestrator()
    result = orchestrator.run(text="x@example.com")

    mock_run_llm.assert_not_called()
    assert result.get("decision") == "block"


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
def test_orchestrator_combines_text_and_file(mock_llm_from_env, tmp_path):
    """Test that both text and file_path content are combined in raw_text"""
    mock_detector = MagicMock()
    mock_detector.return_value = {"detected_fields": []}
    mock_llm_from_env.return_value = mock_detector
    
    # Create a test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("File content", encoding="utf-8")
    
    orchestrator = GuardOrchestrator()
    result = orchestrator.run(text="Direct text", file_path=str(test_file))
    
    # Both should be present in raw_text
    assert "Direct text" in result.get("raw_text")
    assert "File content" in result.get("raw_text")


@patch('multiagent_firewall.nodes.detection.LiteLLMDetector.from_env')
def test_orchestrator_preserves_text_on_file_error(mock_llm_from_env, tmp_path):
    """Test that direct text is preserved when file reading fails"""
    mock_detector = MagicMock()
    mock_detector.return_value = {"detected_fields": []}
    mock_llm_from_env.return_value = mock_detector
    
    # Create path to non-existent file
    missing_file = tmp_path / "missing.txt"
    
    orchestrator = GuardOrchestrator()
    result = orchestrator.run(text="Direct text", file_path=str(missing_file))
    
    # Direct text should be preserved even though file reading failed
    assert result.get("raw_text") == "Direct text"
    assert len(result.get("errors", [])) > 0
    assert any("File not found" in error for error in result.get("errors", []))
