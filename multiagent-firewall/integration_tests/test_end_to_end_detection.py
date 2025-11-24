import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest
import yaml

from multiagent_firewall.orchestrator import GuardOrchestrator


LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4")
LLM_API_KEY = os.getenv("LLM_API_KEY")

RESULTS_CACHE_FILE = Path(__file__).parent / ".test_results_cache.json"


def load_test_cases() -> List[Tuple[str, str, bool, List[str], str]]:
    test_file = Path(__file__).parent / "prompts_test_cases.yaml"
    with open(test_file) as f:
        data = yaml.safe_load(f)
    return [
        (
            case["id"],
            case["prompt"],
            case["expected_sensitive"],
            case.get("expected_entities", []),
            case.get("description", ""),
        )
        for case in data["test_cases"]
    ]


def cache_result(test_id: str, expected: bool, actual: bool):
    if RESULTS_CACHE_FILE.exists():
        with open(RESULTS_CACHE_FILE) as f:
            cache = json.load(f)
    else:
        cache = {}

    cache[test_id] = {"expected": expected, "actual": actual}

    with open(RESULTS_CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def load_cached_results() -> Dict[str, Dict[str, bool]]:
    if RESULTS_CACHE_FILE.exists():
        with open(RESULTS_CACHE_FILE) as f:
            return json.load(f)
    return {}


@pytest.fixture(scope="module")
def orchestrator():
    if not LLM_API_KEY:
        pytest.skip("LLM_API_KEY not set. Skipping integration tests.")

    os.environ["LITELLM_MODEL"] = LLM_MODEL
    os.environ["LITELLM_API_KEY"] = LLM_API_KEY

    return GuardOrchestrator()


@pytest.mark.integration
@pytest.mark.parametrize(
    "test_id,prompt,expected_sensitive,expected_entities,description", load_test_cases()
)
def test_sensitive_detection(
    orchestrator, test_id, prompt, expected_sensitive, expected_entities, description
):
    result = orchestrator.run(text=prompt)

    detected_fields = result.get("detected_fields", [])
    risk_level = result.get("risk_level", "")
    decision = result.get("decision", "")

    risk_level_normalized = risk_level.lower() if risk_level else ""
    is_sensitive = risk_level_normalized in ["high", "critical"] or decision == "block"

    cache_result(test_id, expected_sensitive, is_sensitive)

    assert is_sensitive == expected_sensitive, (
        f"Test '{test_id}' failed: {description}\n"
        f"Expected sensitive: {expected_sensitive}, Got: {is_sensitive}\n"
        f"Detected fields: {detected_fields}\n"
        f"Risk level: {risk_level}\n"
        f"Decision: {decision}"
    )

    if expected_sensitive and expected_entities:
        detected_types = [
            field.get("type", field.get("field", "")).upper()
            for field in detected_fields
        ]
        for expected_entity in expected_entities:
            assert any(expected_entity.upper() in dt for dt in detected_types), (
                f"Test '{test_id}' failed: Expected entity '{expected_entity}' not found.\n"
                f"Detected types: {detected_types}"
            )


@pytest.mark.integration
def test_orchestrator_returns_complete_state(orchestrator):
    prompt = "My SSN is 123-45-6789"
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


@pytest.mark.integration
def test_metrics_calculation():
    cached_results = load_cached_results()

    if not cached_results:
        pytest.skip("No cached results found. Run individual tests first.")

    results = {
        "true_positive": 0,
        "true_negative": 0,
        "false_positive": 0,
        "false_negative": 0,
    }

    for test_id, data in cached_results.items():
        expected_sensitive = data["expected"]
        is_sensitive = data["actual"]

        if expected_sensitive and is_sensitive:
            results["true_positive"] += 1
        elif not expected_sensitive and not is_sensitive:
            results["true_negative"] += 1
        elif not expected_sensitive and is_sensitive:
            results["false_positive"] += 1
        elif expected_sensitive and not is_sensitive:
            results["false_negative"] += 1

    total = sum(results.values())
    accuracy = (
        (results["true_positive"] + results["true_negative"]) / total
        if total > 0
        else 0
    )
    precision = (
        results["true_positive"]
        / (results["true_positive"] + results["false_positive"])
        if (results["true_positive"] + results["false_positive"]) > 0
        else 0
    )
    recall = (
        results["true_positive"]
        / (results["true_positive"] + results["false_negative"])
        if (results["true_positive"] + results["false_negative"]) > 0
        else 0
    )
    f1_score = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0
    )

    print("\n" + "=" * 50)
    print("INTEGRATION TEST METRICS")
    print("=" * 50)
    print(f"Total test cases: {total}")
    print(f"True Positives: {results['true_positive']}")
    print(f"True Negatives: {results['true_negative']}")
    print(f"False Positives: {results['false_positive']}")
    print(f"False Negatives: {results['false_negative']}")
    print(f"Accuracy: {accuracy:.2%}")
    print(f"Precision: {precision:.2%}")
    print(f"Recall: {recall:.2%}")
    print(f"F1 Score: {f1_score:.2%}")
    print("=" * 50)

    assert (
        accuracy >= 0.5
    ), f"Accuracy {accuracy:.2%} is below acceptable threshold of 50%"
