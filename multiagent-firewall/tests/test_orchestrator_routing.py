"""
Test orchestrator routing logic to ensure correct node execution paths.

This module tests all possible routing scenarios through the multiagent firewall
to validate that nodes execute in the correct order and conditional branches work as expected.
"""

from unittest.mock import MagicMock, patch, AsyncMock
import pytest

from multiagent_firewall import GuardOrchestrator, GuardConfig
from multiagent_firewall.config import LLMConfig, OCRConfig
from multiagent_firewall.types import GuardState


@pytest.fixture
def guard_config():
    """Minimal config for testing."""
    return GuardConfig(
        llm=LLMConfig(
            provider="openai",
            model="gpt-4o-mini",
            client_params={"api_key": "test-key"},
        ),
        ocr=OCRConfig(),
    )


class TestNoDetectionsRouting:
    """Test routing when no sensitive data is detected."""

    @pytest.mark.asyncio
    async def test_no_dlp_no_llm_skips_all_processing(self, guard_config):
        """When neither DLP/NER nor LLM detect anything, skip risk/policy/remediation/anonymization."""
        executed_nodes = []

        def track_node(node_name):
            def wrapper(state, **kwargs):
                executed_nodes.append(node_name)
                return state

            return wrapper

        with (
            patch(
                "multiagent_firewall.nodes.run_dlp_detector",
                side_effect=track_node("dlp_detector"),
            ),
            patch(
                "multiagent_firewall.nodes.merge_detections",
                side_effect=track_node("merge"),
            ),
            patch(
                "multiagent_firewall.nodes.evaluate_risk",
                side_effect=track_node("risk"),
            ),
            patch(
                "multiagent_firewall.nodes.apply_policy",
                return_value={"decision": "warn"},
            ),
            patch(
                "multiagent_firewall.nodes.generate_remediation",
                side_effect=track_node("remediation"),
            ),
            patch(
                "multiagent_firewall.nodes.anonymize_text",
                side_effect=track_node("anonymize"),
            ),
            patch("multiagent_firewall.nodes.detection.LiteLLMDetector") as mock_llm,
        ):
            mock_detector = MagicMock()
            mock_detector.acall = AsyncMock(return_value={"detected_fields": []})
            mock_llm.return_value = mock_detector

            orchestrator = GuardOrchestrator(guard_config)
            result = await orchestrator.run(text="Hello world")

        # Should execute: dlp_detector, merge (dlp), llm_detector, merge (final)
        # Should NOT execute: risk, policy, remediation, anonymize
        assert "dlp_detector" in executed_nodes
        assert "risk" not in executed_nodes
        assert "policy" not in executed_nodes
        assert "remediation" not in executed_nodes
        assert "anonymize" not in executed_nodes

        # Check defaults are set
        assert result.get("decision") == "allow"
        assert result.get("risk_level") == "none"

    @pytest.mark.asyncio
    async def test_route_merge_dlp_ner_to_llm_detector_directly(self, guard_config):
        """When DLP/NER find nothing, route directly to llm_detector (skip anonymize_dlp_ner)."""
        routing_path = []

        def track_dlp(state):
            routing_path.append("dlp_detector")
            state["dlp_fields"] = []
            state["detected_fields"] = []
            return state

        def track_merge_dlp_ner(state):
            routing_path.append("merge_dlp_ner")
            return state

        def track_anonymize_dlp_ner(state, **kwargs):
            routing_path.append("anonymize_dlp_ner")
            return state

        def track_llm_detector(state, **kwargs):
            routing_path.append("llm_detector")
            return state

        with (
            patch(
                "multiagent_firewall.orchestrator.nodes.run_dlp_detector",
                side_effect=track_dlp,
            ),
            patch(
                "multiagent_firewall.nodes.merge_detections",
                side_effect=track_merge_dlp_ner,
            ),
            patch(
                "multiagent_firewall.nodes.anonymize_text",
                side_effect=track_anonymize_dlp_ner,
            ),
            patch("multiagent_firewall.nodes.detection.LiteLLMDetector") as mock_llm,
        ):
            mock_detector = MagicMock()
            mock_detector.acall = AsyncMock(return_value={"detected_fields": []})
            mock_llm.return_value = mock_detector

            orchestrator = GuardOrchestrator(guard_config)
            await orchestrator.run(text="Clean text")

        # Verify anonymize_dlp_ner was NOT called (direct route to llm_detector)
        assert "dlp_detector" in routing_path
        assert "merge_dlp_ner" in routing_path
        assert "anonymize_dlp_ner" not in routing_path


class TestDLPOnlyRouting:
    """Test routing when only DLP detects sensitive data."""

    @pytest.mark.asyncio
    async def test_dlp_findings_trigger_risk_policy_chain(self, guard_config):
        """When DLP finds data, execute risk_dlp_ner -> policy_dlp_ner -> anonymize_dlp_ner -> llm_detector."""
        executed_nodes = []

        def fake_dlp(state):
            executed_nodes.append("dlp_detector")
            state["dlp_fields"] = [{"type": "EMAIL", "value": "test@example.com"}]
            return state

        def fake_merge(state):
            executed_nodes.append("merge")
            state["detected_fields"] = state.get("dlp_fields", [])
            return state

        def fake_risk(state):
            executed_nodes.append("risk")
            state["risk_level"] = "low"
            return state

        def fake_policy(state):
            executed_nodes.append("policy")
            state["decision"] = "warn"
            return state

        def fake_anonymize(state, **kwargs):
            executed_nodes.append("anonymize")
            return state

        def fake_remediation(state):
            executed_nodes.append("remediation")
            return state

        with (
            patch(
                "multiagent_firewall.orchestrator.nodes.run_dlp_detector",
                side_effect=fake_dlp,
            ),
            patch("multiagent_firewall.nodes.merge_detections", side_effect=fake_merge),
            patch("multiagent_firewall.nodes.evaluate_risk", side_effect=fake_risk),
            patch("multiagent_firewall.nodes.apply_policy", side_effect=fake_policy),
            patch(
                "multiagent_firewall.nodes.anonymize_text", side_effect=fake_anonymize
            ),
            patch(
                "multiagent_firewall.nodes.generate_remediation",
                side_effect=fake_remediation,
            ),
            patch("multiagent_firewall.nodes.detection.LiteLLMDetector") as mock_llm,
        ):
            mock_detector = MagicMock()
            mock_detector.acall = AsyncMock(return_value={"detected_fields": []})
            mock_llm.return_value = mock_detector

            orchestrator = GuardOrchestrator(guard_config)
            await orchestrator.run(text="Contact: test@example.com")

        # Should execute DLP risk/policy chain
        assert "dlp_detector" in executed_nodes
        assert "risk" in executed_nodes
        assert "policy" in executed_nodes
        assert "anonymize" in executed_nodes  # anonymize_dlp_ner + final_anonymize
        assert "remediation" in executed_nodes

    @pytest.mark.asyncio
    async def test_dlp_block_skips_llm_detector(self, guard_config):
        """When DLP policy blocks, skip llm_detector entirely."""
        executed_nodes = []

        def fake_dlp(state):
            executed_nodes.append("dlp_detector")
            state["dlp_fields"] = [{"type": "SSN", "value": "123-45-6789"}]
            state["detected_fields"] = state["dlp_fields"]
            return state

        def fake_risk(state):
            executed_nodes.append("risk")
            state["risk_level"] = "high"
            return state

        def fake_policy(state):
            executed_nodes.append("policy")
            state["decision"] = "block"
            return state

        def fake_llm(state, **kwargs):
            executed_nodes.append("llm_detector")
            return state

        def fake_remediation(state):
            executed_nodes.append("remediation")
            return state

        def fake_anonymize(state, **kwargs):
            executed_nodes.append("anonymize")
            return state

        with (
            patch(
                "multiagent_firewall.orchestrator.nodes.run_dlp_detector",
                side_effect=fake_dlp,
            ),
            patch("multiagent_firewall.nodes.merge_detections", return_value={}),
            patch("multiagent_firewall.nodes.evaluate_risk", side_effect=fake_risk),
            patch("multiagent_firewall.nodes.apply_policy", side_effect=fake_policy),
            patch("multiagent_firewall.nodes.run_llm_detector", side_effect=fake_llm),
            patch(
                "multiagent_firewall.nodes.generate_remediation",
                side_effect=fake_remediation,
            ),
            patch(
                "multiagent_firewall.nodes.anonymize_text", side_effect=fake_anonymize
            ),
        ):
            orchestrator = GuardOrchestrator(guard_config)
            result = await orchestrator.run(text="SSN: 123-45-6789")

        # Should skip llm_detector when blocked
        assert "dlp_detector" in executed_nodes
        assert "risk" in executed_nodes
        assert "policy" in executed_nodes
        assert "llm_detector" not in executed_nodes
        assert "remediation" in executed_nodes
        assert "anonymize" in executed_nodes
        assert result.get("decision") == "block"

    @pytest.mark.asyncio
    async def test_dlp_block_runs_llm_detector_when_forced(self, guard_config):
        """When FORCE_LLM_DETECTOR is enabled, always run llm_detector."""
        executed_nodes = []
        forced_config = GuardConfig(
            llm=guard_config.llm,
            ocr=guard_config.ocr,
            force_llm_detector=True,
        )

        def fake_dlp(state):
            executed_nodes.append("dlp_detector")
            state["dlp_fields"] = [{"type": "SSN", "value": "123-45-6789"}]
            state["detected_fields"] = state["dlp_fields"]
            return state

        def fake_merge(state):
            return state

        def fake_risk(state):
            executed_nodes.append("risk")
            state["risk_level"] = "high"
            return state

        def fake_policy(state):
            executed_nodes.append("policy")
            state["decision"] = "block"
            return state

        def fake_llm(state, **kwargs):
            executed_nodes.append("llm_detector")
            state["llm_fields"] = []
            return state

        def fake_remediation(state):
            executed_nodes.append("remediation")
            return state

        def fake_anonymize(state, **kwargs):
            executed_nodes.append("anonymize")
            return state

        with (
            patch(
                "multiagent_firewall.orchestrator.nodes.run_dlp_detector",
                side_effect=fake_dlp,
            ),
            patch("multiagent_firewall.nodes.merge_detections", side_effect=fake_merge),
            patch("multiagent_firewall.nodes.evaluate_risk", side_effect=fake_risk),
            patch("multiagent_firewall.nodes.apply_policy", side_effect=fake_policy),
            patch("multiagent_firewall.nodes.run_llm_detector", side_effect=fake_llm),
            patch(
                "multiagent_firewall.nodes.generate_remediation",
                side_effect=fake_remediation,
            ),
            patch(
                "multiagent_firewall.nodes.anonymize_text", side_effect=fake_anonymize
            ),
        ):
            orchestrator = GuardOrchestrator(forced_config)
            result = await orchestrator.run(text="SSN: 123-45-6789")

        assert "dlp_detector" in executed_nodes
        assert "risk" in executed_nodes
        assert "policy" in executed_nodes
        assert "llm_detector" in executed_nodes
        assert "remediation" in executed_nodes
        assert "anonymize" in executed_nodes
        assert result.get("decision") == "block"


class TestLLMOnlyRouting:
    """Test routing when only LLM detects sensitive data."""

    @pytest.mark.asyncio
    async def test_llm_findings_trigger_final_risk_policy(self, guard_config):
        """When LLM finds new data, execute risk_final -> policy_final -> remediation."""
        executed_nodes = []

        def fake_dlp(state):
            executed_nodes.append("dlp_detector")
            state["dlp_fields"] = []
            return state

        def fake_llm_detector(state, **kwargs):
            executed_nodes.append("llm_detector")
            state["llm_fields"] = [{"type": "OTHER", "value": "sensitive info"}]
            return state

        def fake_merge(state):
            executed_nodes.append("merge")
            # Simulate merge_final adding llm_fields to detected_fields
            if state.get("llm_fields"):
                state["detected_fields"] = state["llm_fields"]
            return state

        def fake_risk(state):
            executed_nodes.append("risk")
            state["risk_level"] = "medium"
            return state

        def fake_policy(state):
            executed_nodes.append("policy")
            state["decision"] = "warn"
            return state

        def fake_remediation(state):
            executed_nodes.append("remediation")
            return state

        def fake_anonymize(state, **kwargs):
            executed_nodes.append("anonymize")
            return state

        with (
            patch(
                "multiagent_firewall.orchestrator.nodes.run_dlp_detector",
                side_effect=fake_dlp,
            ),
            patch("multiagent_firewall.nodes.merge_detections", side_effect=fake_merge),
            patch(
                "multiagent_firewall.nodes.run_llm_detector",
                side_effect=fake_llm_detector,
            ),
            patch("multiagent_firewall.nodes.evaluate_risk", side_effect=fake_risk),
            patch("multiagent_firewall.nodes.apply_policy", side_effect=fake_policy),
            patch(
                "multiagent_firewall.nodes.generate_remediation",
                side_effect=fake_remediation,
            ),
            patch(
                "multiagent_firewall.nodes.anonymize_text", side_effect=fake_anonymize
            ),
        ):
            orchestrator = GuardOrchestrator(guard_config)
            await orchestrator.run(text="Some text with sensitive info")

        # Should execute final risk/policy after LLM detection
        assert "dlp_detector" in executed_nodes
        assert "llm_detector" in executed_nodes
        assert "risk" in executed_nodes  # risk_final
        assert "policy" in executed_nodes  # policy_final
        assert "remediation" in executed_nodes
        assert "anonymize" in executed_nodes  # final_anonymize


class TestBothDetectorsRouting:
    """Test routing when both DLP and LLM detect sensitive data."""

    @pytest.mark.asyncio
    async def test_both_findings_execute_all_risk_policy_nodes(self, guard_config):
        """When both detectors find data, execute DLP risk/policy AND final risk/policy."""
        risk_count = 0
        policy_count = 0

        def fake_dlp(state):
            state["dlp_fields"] = [{"type": "EMAIL", "value": "test@example.com"}]
            return state

        def fake_merge(state):
            if "llm_fields" in state:
                # merge_final: combine dlp + llm
                state["detected_fields"] = state.get("dlp_fields", []) + state.get(
                    "llm_fields", []
                )
            else:
                # merge_dlp_ner: just dlp
                state["detected_fields"] = state.get("dlp_fields", [])
            return state

        def count_risk(state):
            nonlocal risk_count
            risk_count += 1
            state["risk_level"] = "medium"
            return state

        def count_policy(state):
            nonlocal policy_count
            policy_count += 1
            state["decision"] = "warn"
            return state

        with (
            patch(
                "multiagent_firewall.orchestrator.nodes.run_dlp_detector",
                side_effect=fake_dlp,
            ),
            patch("multiagent_firewall.nodes.merge_detections", side_effect=fake_merge),
            patch("multiagent_firewall.nodes.evaluate_risk", side_effect=count_risk),
            patch("multiagent_firewall.nodes.apply_policy", side_effect=count_policy),
            patch("multiagent_firewall.nodes.detection.LiteLLMDetector") as mock_llm,
            patch("multiagent_firewall.nodes.anonymize_text", return_value={}),
            patch("multiagent_firewall.nodes.generate_remediation", return_value={}),
        ):
            mock_detector = MagicMock()
            mock_detector.acall = AsyncMock(
                return_value={
                    "detected_fields": [{"type": "OTHER", "value": "secret data"}]
                }
            )
            mock_llm.return_value = mock_detector

            orchestrator = GuardOrchestrator(guard_config)
            await orchestrator.run(text="Email: test@example.com and secret data")

        # Should call risk and policy twice: once for DLP, once for final
        assert risk_count == 2
        assert policy_count == 2


class TestRemediationAnonymizationSequence:
    """Test that remediation and final_anonymize always run together."""

    @pytest.mark.asyncio
    async def test_remediation_always_followed_by_final_anonymize(self, guard_config):
        """When remediation runs, final_anonymize must always run next."""
        execution_order = []

        def track_remediation(state):
            execution_order.append("remediation")
            return state

        def track_anonymize(state, **kwargs):
            execution_order.append("anonymize")
            return state

        def fake_dlp(state):
            state["dlp_fields"] = [{"type": "EMAIL", "value": "test@example.com"}]
            state["detected_fields"] = state["dlp_fields"]
            return state

        with (
            patch(
                "multiagent_firewall.orchestrator.nodes.run_dlp_detector",
                side_effect=fake_dlp,
            ),
            patch(
                "multiagent_firewall.nodes.generate_remediation",
                side_effect=track_remediation,
            ),
            patch(
                "multiagent_firewall.nodes.anonymize_text", side_effect=track_anonymize
            ),
            patch("multiagent_firewall.nodes.merge_detections", return_value={}),
            patch(
                "multiagent_firewall.nodes.evaluate_risk",
                return_value={"risk_level": "low"},
            ),
            patch(
                "multiagent_firewall.nodes.apply_policy",
                return_value={"decision": "warn"},
            ),
            patch("multiagent_firewall.nodes.detection.LiteLLMDetector") as mock_llm,
        ):
            mock_detector = MagicMock()
            mock_detector.acall = AsyncMock(return_value={"detected_fields": []})
            mock_llm.return_value = mock_detector

            orchestrator = GuardOrchestrator(guard_config)
            await orchestrator.run(text="Email: test@example.com")

        # Verify remediation is followed by anonymize
        remediation_idx = execution_order.index("remediation")
        anonymize_indices = [
            i for i, x in enumerate(execution_order) if x == "anonymize"
        ]

        # final_anonymize should be the last anonymize call and come after remediation
        assert len(anonymize_indices) >= 1
        assert max(anonymize_indices) > remediation_idx

    @pytest.mark.asyncio
    async def test_no_detections_skips_both_remediation_and_anonymize(
        self, guard_config
    ):
        """When no fields detected, skip both remediation and final_anonymize."""
        remediation_called = False
        anonymize_called = False

        def track_remediation(state):
            nonlocal remediation_called
            remediation_called = True
            return state

        def track_anonymize(state, **kwargs):
            nonlocal anonymize_called
            anonymize_called = True
            return state

        with (
            patch(
                "multiagent_firewall.nodes.generate_remediation",
                side_effect=track_remediation,
            ),
            patch(
                "multiagent_firewall.nodes.anonymize_text", side_effect=track_anonymize
            ),
            patch("multiagent_firewall.nodes.detection.LiteLLMDetector") as mock_llm,
        ):
            mock_detector = MagicMock()
            mock_detector.acall = AsyncMock(return_value={"detected_fields": []})
            mock_llm.return_value = mock_detector

            orchestrator = GuardOrchestrator(guard_config)
            await orchestrator.run(text="Clean text")

        # Neither should run when no detections
        assert not remediation_called
        assert not anonymize_called


class TestAnonymizeLLMConditional:
    """Test that anonymize_dlp_ner only runs when pre-LLM findings exist."""

    @pytest.mark.asyncio
    async def test_anonymize_dlp_ner_runs_only_with_dlp_findings(self, guard_config):
        """anonymize_dlp_ner should only execute when pre-LLM findings exist."""
        anonymize_calls = []

        def track_anonymize(state, **kwargs):
            findings_key = kwargs.get("findings_key", "unknown")
            anonymize_calls.append(findings_key)
            return state

        def fake_dlp_with_findings(state):
            state["dlp_fields"] = [{"type": "EMAIL", "value": "test@example.com"}]
            return state

        def fake_merge(state):
            # Simulate merge keeping detected_fields
            if state.get("dlp_fields"):
                state["detected_fields"] = state["dlp_fields"]
            return state

        with (
            patch(
                "multiagent_firewall.orchestrator.nodes.run_dlp_detector",
                side_effect=fake_dlp_with_findings,
            ),
            patch(
                "multiagent_firewall.nodes.anonymize_text", side_effect=track_anonymize
            ),
            patch(
                "multiagent_firewall.nodes.merge_detections",
                side_effect=fake_merge,
            ),
            patch(
                "multiagent_firewall.nodes.evaluate_risk",
                return_value={"risk_level": "low"},
            ),
            patch(
                "multiagent_firewall.nodes.apply_policy",
                return_value={"decision": "warn"},
            ),
            patch("multiagent_firewall.nodes.detection.LiteLLMDetector") as mock_llm,
            patch("multiagent_firewall.nodes.generate_remediation", return_value={}),
        ):
            mock_detector = MagicMock()
            mock_detector.acall = AsyncMock(return_value={"detected_fields": []})
            mock_llm.return_value = mock_detector

            orchestrator = GuardOrchestrator(guard_config)
            await orchestrator.run(text="Email: test@example.com")

        # Should have called anonymize_text at least twice: anonymize_dlp_ner + final_anonymize
        assert anonymize_calls.count("detected_fields") >= 2

    @pytest.mark.asyncio
    async def test_anonymize_dlp_ner_skipped_without_dlp_findings(self, guard_config):
        """anonymize_dlp_ner should be skipped when no pre-LLM findings exist."""
        anonymize_calls = []

        def track_anonymize(state, **kwargs):
            findings_key = kwargs.get("findings_key", "unknown")
            anonymize_calls.append(findings_key)
            return state

        def fake_dlp_no_findings(state):
            state["dlp_fields"] = []
            return state

        with (
            patch(
                "multiagent_firewall.orchestrator.nodes.run_dlp_detector",
                side_effect=fake_dlp_no_findings,
            ),
            patch(
                "multiagent_firewall.nodes.anonymize_text", side_effect=track_anonymize
            ),
            patch("multiagent_firewall.nodes.detection.LiteLLMDetector") as mock_llm,
        ):
            mock_detector = MagicMock()
            mock_detector.acall = AsyncMock(return_value={"detected_fields": []})
            mock_llm.return_value = mock_detector

            orchestrator = GuardOrchestrator(guard_config)
            await orchestrator.run(text="Clean text")

        # Should NOT have called anonymize_dlp_ner or final_anonymize since no detections
        assert len(anonymize_calls) == 0


class TestDefaultValuesPresent:
    """Test that output always contains decision and risk_level fields."""

    @pytest.mark.asyncio
    async def test_decision_and_risk_level_always_present(self, guard_config):
        """decision and risk_level should always be in output, even with no detections."""
        with patch("multiagent_firewall.nodes.detection.LiteLLMDetector") as mock_llm:
            mock_detector = MagicMock()
            mock_detector.acall = AsyncMock(return_value={"detected_fields": []})
            mock_llm.return_value = mock_detector

            orchestrator = GuardOrchestrator(guard_config)
            result = await orchestrator.run(text="Clean text")

        assert "decision" in result
        assert "risk_level" in result
        assert result["decision"] == "allow"
        assert result["risk_level"] == "none"

    @pytest.mark.asyncio
    async def test_defaults_overridden_when_findings_detected(self, guard_config):
        """Default values should be overridden by policy nodes when findings exist."""

        def fake_dlp(state):
            state["dlp_fields"] = [{"type": "EMAIL", "value": "test@example.com"}]
            state["detected_fields"] = state["dlp_fields"]
            return state

        def fake_risk(state):
            state["risk_level"] = "low"
            return state

        def fake_policy(state):
            state["decision"] = "warn"
            return state

        with (
            patch(
                "multiagent_firewall.orchestrator.nodes.run_dlp_detector",
                side_effect=fake_dlp,
            ),
            patch("multiagent_firewall.nodes.evaluate_risk", side_effect=fake_risk),
            patch("multiagent_firewall.nodes.apply_policy", side_effect=fake_policy),
            patch("multiagent_firewall.nodes.merge_detections", return_value={}),
            patch("multiagent_firewall.nodes.anonymize_text", return_value={}),
            patch("multiagent_firewall.nodes.generate_remediation", return_value={}),
            patch("multiagent_firewall.nodes.detection.LiteLLMDetector") as mock_llm,
        ):
            mock_detector = MagicMock()
            mock_detector.acall = AsyncMock(return_value={"detected_fields": []})
            mock_llm.return_value = mock_detector

            orchestrator = GuardOrchestrator(guard_config)
            result = await orchestrator.run(text="Email: test@example.com")

        # Should be overridden from defaults
        assert result.get("decision") == "warn"
        assert result.get("risk_level") == "low"
