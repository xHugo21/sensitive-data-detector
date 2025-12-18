import os
from pathlib import Path
from typing import List, Tuple

import pytest
import yaml

from multiagent_firewall.config import GuardConfig
from multiagent_firewall.orchestrator import GuardOrchestrator


LLM_API_KEY = os.getenv("LLM_API_KEY")


def load_test_cases() -> List[Tuple[str, str, List[str], str]]:
    test_file = Path(__file__).parent / "prompts_test_cases.yaml"
    with open(test_file) as f:
        data = yaml.safe_load(f)
    return [
        (
            case["id"],
            case["prompt"],
            case.get("expected_entities", []),
            case.get("description", ""),
        )
        for case in data["test_cases"]
    ]


@pytest.fixture(scope="module")
def orchestrator():
    if not LLM_API_KEY:
        pytest.skip("LLM_API_KEY not set. Skipping integration tests.")

    config = GuardConfig.from_env()
    return GuardOrchestrator(config)


@pytest.mark.integration
@pytest.mark.parametrize(
    "test_id,prompt,expected_entities,description",
    load_test_cases(),
    ids=[case[0] for case in load_test_cases()],
)
def test_sensitive_detection(
    orchestrator, test_id, prompt, expected_entities, description
):
    result = orchestrator.run(text=prompt)

    detected_fields = result.get("detected_fields", [])

    # Extract detected field types
    detected_types = [
        field.get("type", field.get("field", "")).upper() for field in detected_fields
    ]

    # Check that all expected entities are detected
    if expected_entities:
        for expected_entity in expected_entities:
            assert any(expected_entity.upper() in dt for dt in detected_types), (
                f"Test '{test_id}' failed: {description}\n"
                f"Expected entity '{expected_entity}' not found.\n"
                f"Detected types: {detected_types}\n"
                f"Detected fields: {detected_fields}"
            )
    else:
        # If no expected entities, verify that no fields were detected
        assert len(detected_fields) == 0, (
            f"Test '{test_id}' failed: {description}\n"
            f"Expected no entities, but detected: {detected_types}\n"
            f"Detected fields: {detected_fields}"
        )


@pytest.mark.integration
def test_orchestrator_returns_complete_state(orchestrator):
    prompt = "My SOCIALSECURITYNUMBER is 123-45-6789"
    result = orchestrator.run(text=prompt)

    assert "raw_text" in result
    assert "normalized_text" in result
    assert "detected_fields" in result
    assert "risk_level" in result
    assert "decision" in result
    assert "remediation" in result
    assert result["raw_text"] == prompt


@pytest.mark.integration
def test_orchestrator_handles_empty_input(orchestrator):
    result = orchestrator.run(text="")

    assert result["raw_text"] == ""
    assert "detected_fields" in result
    assert "risk_level" in result
