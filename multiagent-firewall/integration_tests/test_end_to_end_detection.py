import os
from pathlib import Path
from typing import List, Tuple

import pytest
import yaml

TEST_CASES_ENV_VAR = "INTEGRATION_TESTS_FILE"
DEFAULT_CASES_FILE = "prompts_test_cases.yaml"


def _resolve_cases_file() -> Path:
    env_value = os.getenv(TEST_CASES_ENV_VAR)
    if env_value:
        return Path(env_value)
    return Path(__file__).parent / DEFAULT_CASES_FILE


def load_test_cases() -> List[Tuple[str, str, List[str]]]:
    test_file = _resolve_cases_file()
    if not test_file.exists():
        raise FileNotFoundError(f"Test cases file not found: {test_file}")

    with open(test_file) as f:
        data = yaml.safe_load(f)

    if not data or "test_cases" not in data:
        raise ValueError(f"No test_cases found in {test_file}")

    cases = []
    for index, case in enumerate(data["test_cases"], start=1):
        if not isinstance(case, dict):
            raise ValueError(f"Test case {index} must be a mapping.")

        allowed_keys = {"prompt", "expected_entities"}
        extra_keys = set(case.keys()) - allowed_keys
        if extra_keys:
            extra_keys_list = ", ".join(sorted(extra_keys))
            raise ValueError(
                f"Test case {index} has unsupported keys: {extra_keys_list}"
            )

        if "prompt" not in case:
            raise ValueError(f"Test case {index} must include 'prompt'.")

        prompt = case["prompt"]
        if prompt is None:
            raise ValueError(f"Test case {index} has null prompt.")

        expected_entities = case.get("expected_entities") or []
        if not isinstance(expected_entities, list):
            raise ValueError(
                f"Test case {index} expected_entities must be a list."
            )

        test_id = f"case_{index:03d}"
        cases.append((test_id, prompt, expected_entities))
    if not cases:
        raise ValueError(f"No test cases found in {test_file}")
    return cases


TEST_CASES = load_test_cases()


@pytest.mark.integration
@pytest.mark.parametrize(
    "test_id,prompt,expected_entities",
    TEST_CASES,
    ids=[case[0] for case in TEST_CASES],
)
def test_sensitive_detection(
    orchestrator, test_id, prompt, expected_entities
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
                f"Test '{test_id}' failed.\n"
                f"Expected entity '{expected_entity}' not found.\n"
                f"Detected types: {detected_types}\n"
                f"Detected fields: {detected_fields}"
            )
    else:
        # If no expected entities, verify that no fields were detected
        assert len(detected_fields) == 0, (
            f"Test '{test_id}' failed.\n"
            f"Expected no entities, but detected: {detected_types}\n"
            f"Detected fields: {detected_fields}"
        )
