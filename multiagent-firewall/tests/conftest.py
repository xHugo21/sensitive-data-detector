from __future__ import annotations

import pytest
import json
from pathlib import Path
from multiagent_firewall.config import (
    GuardConfig,
    LLMConfig,
    OCRConfig,
    detection,
)


@pytest.fixture
def guard_config() -> GuardConfig:
    return GuardConfig(
        llm=LLMConfig(
            provider="openai",
            model="gpt-4o-mini",
            client_params={"api_key": "test-api-key"},
        ),
        llm_ocr=None,
        ocr=OCRConfig(),
        debug=False,
    )


@pytest.fixture(scope="session")
def stable_detection_config() -> dict:
    config_path = Path(__file__).parent / "fixtures" / "stable_detection.json"
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(autouse=True)
def patch_detection_config(stable_detection_config):
    # Backup original values
    original_regex = detection.REGEX_PATTERNS.copy()
    original_keywords = detection.KEYWORDS.copy()
    original_ner = detection.NER_LABELS.copy()
    original_risk_scores = detection.RISK_SCORE.copy()
    original_risk_thresholds = detection.RISK_SCORE_THRESHOLDS.copy()
    original_high = detection.HIGH_RISK_FIELDS.copy()
    original_medium = detection.MEDIUM_RISK_FIELDS.copy()
    original_low = detection.LOW_RISK_FIELDS.copy()

    # Update with stable config
    detection.REGEX_PATTERNS.clear()
    detection.REGEX_PATTERNS.update(stable_detection_config["regex_patterns"])

    detection.KEYWORDS.clear()
    detection.KEYWORDS.update(stable_detection_config["keywords"])

    detection.NER_LABELS.clear()
    detection.NER_LABELS.update(stable_detection_config["ner_labels"])

    detection.RISK_SCORE.clear()
    detection.RISK_SCORE.update(stable_detection_config["risk"]["scores"])

    # Special handling for thresholds (convert lists to tuples)
    thresholds = stable_detection_config["risk"]["thresholds"]
    converted_thresholds = {
        k: tuple(v) if isinstance(v, list) else v for k, v in thresholds.items()
    }
    detection.RISK_SCORE_THRESHOLDS.clear()
    detection.RISK_SCORE_THRESHOLDS.update(converted_thresholds)

    detection.HIGH_RISK_FIELDS.clear()
    detection.HIGH_RISK_FIELDS.update(stable_detection_config["risk_fields"]["high"])

    detection.MEDIUM_RISK_FIELDS.clear()
    detection.MEDIUM_RISK_FIELDS.update(
        stable_detection_config["risk_fields"]["medium"]
    )

    detection.LOW_RISK_FIELDS.clear()
    detection.LOW_RISK_FIELDS.update(stable_detection_config["risk_fields"]["low"])

    yield

    # Restore original values
    detection.REGEX_PATTERNS.clear()
    detection.REGEX_PATTERNS.update(original_regex)

    detection.KEYWORDS.clear()
    detection.KEYWORDS.update(original_keywords)

    detection.NER_LABELS.clear()
    detection.NER_LABELS.update(original_ner)

    detection.RISK_SCORE.clear()
    detection.RISK_SCORE.update(original_risk_scores)

    detection.RISK_SCORE_THRESHOLDS.clear()
    detection.RISK_SCORE_THRESHOLDS.update(original_risk_thresholds)

    detection.HIGH_RISK_FIELDS.clear()
    detection.HIGH_RISK_FIELDS.update(original_high)

    detection.MEDIUM_RISK_FIELDS.clear()
    detection.MEDIUM_RISK_FIELDS.update(original_medium)

    detection.LOW_RISK_FIELDS.clear()
    detection.LOW_RISK_FIELDS.update(original_low)
