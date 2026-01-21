"""
Loads detection configuration from detection.json and exposes it as module-level constants.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_CONFIG_PATH = Path(__file__).parent / "detection.json"


def _load_config() -> dict[str, Any]:
    """Load and validate detection.json. Fails fast if missing or malformed."""
    if not _CONFIG_PATH.exists():
        raise FileNotFoundError(f"Detection config not found: {_CONFIG_PATH}")
    try:
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {_CONFIG_PATH}: {e}") from e


_config = _load_config()

# Prompt filenames
LLM_DETECTOR_PROMPT: str = _config["prompts"]["llm_detector"]
OCR_DETECTOR_PROMPT: str = _config["prompts"]["ocr_detector"]

# Regex patterns for DLP detection
REGEX_PATTERNS: dict[str, dict[str, Any]] = _config["regex_patterns"]

# Keyword lists for DLP detection
KEYWORDS: dict[str, list[str]] = _config["keywords"]

# NER label mappings
NER_LABELS: dict[str, str] = _config["ner_labels"]

# Risk scoring configuration
RISK_SCORE: dict[str, int] = _config["risk"]["scores"]

_raw_thresholds = _config["risk"]["thresholds"]
RISK_SCORE_THRESHOLDS: dict[str, Any] = {
    k: tuple(v) if isinstance(v, list) else v for k, v in _raw_thresholds.items()
}

# Risk field sets (converted from arrays to sets)
HIGH_RISK_FIELDS: set[str] = set(_config["risk_fields"]["high"])
MEDIUM_RISK_FIELDS: set[str] = set(_config["risk_fields"]["medium"])
LOW_RISK_FIELDS: set[str] = set(_config["risk_fields"]["low"])
