"""
Configuration package for multiagent-firewall.

Re-exports from submodules for convenient access:
- Detection rules: from config.detection
- Environment/runtime config: from config.env
"""

from .detection import (
    HIGH_RISK_FIELDS,
    KEYWORDS,
    LLM_DETECTOR_PROMPT,
    LOW_RISK_FIELDS,
    MEDIUM_RISK_FIELDS,
    NER_LABELS,
    OCR_DETECTOR_PROMPT,
    REGEX_PATTERNS,
    RISK_SCORE,
    RISK_SCORE_THRESHOLDS,
)
from .env import (
    GuardConfig,
    LLMConfig,
    NERConfig,
    OCRConfig,
)

__all__ = [
    # Detection
    "HIGH_RISK_FIELDS",
    "KEYWORDS",
    "LLM_DETECTOR_PROMPT",
    "LOW_RISK_FIELDS",
    "MEDIUM_RISK_FIELDS",
    "NER_LABELS",
    "OCR_DETECTOR_PROMPT",
    "REGEX_PATTERNS",
    "RISK_SCORE",
    "RISK_SCORE_THRESHOLDS",
    # Env
    "GuardConfig",
    "LLMConfig",
    "NERConfig",
    "OCRConfig",
]
