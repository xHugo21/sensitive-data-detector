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


def _resolve_file_path(test_file: Path, file_path: str) -> str:
    if file_path.startswith("file://"):
        return file_path

    path = Path(file_path).expanduser()
    if not path.is_absolute():
        path = (test_file.parent / file_path).resolve()

    if not path.exists():
        raise FileNotFoundError(f"File test case path does not exist: {path}")
    return str(path)


def load_test_cases() -> List[Tuple[str, str | None, str | None, List[str], str]]:
    test_file = _resolve_cases_file()
    if not test_file.exists():
        raise FileNotFoundError(f"Test cases file not found: {test_file}")

    with open(test_file) as f:
        data = yaml.safe_load(f)

    if not data or "test_cases" not in data:
        raise ValueError(f"No test_cases found in {test_file}")

    cases = []
    for case in data["test_cases"]:
        test_id = case["id"]
        prompt = case.get("prompt")
        file_path = case.get("file_path") or case.get("file")
        if (prompt is None) == (file_path is None):
            raise ValueError(
                f"Test '{test_id}' must set exactly one of 'prompt' or 'file_path'."
            )
        if file_path is not None:
            file_path = _resolve_file_path(test_file, file_path)
        cases.append(
            (
                test_id,
                prompt,
                file_path,
                case.get("expected_entities", []),
                case.get("description", ""),
            )
        )
    if not cases:
        raise ValueError(f"No test cases found in {test_file}")
    return cases


TEST_CASES = load_test_cases()


@pytest.mark.integration
@pytest.mark.parametrize(
    "test_id,prompt,file_path,expected_entities,description",
    TEST_CASES,
    ids=[case[0] for case in TEST_CASES],
)
def test_sensitive_detection(
    orchestrator, test_id, prompt, file_path, expected_entities, description
):
    if prompt is not None:
        result = orchestrator.run(text=prompt)
    else:
        result = orchestrator.run(file_path=file_path)

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
