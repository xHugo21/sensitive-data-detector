from __future__ import annotations

from typing import Sequence
from ..types import GuardState
from ..config.detection import (
    RISK_SCORE,
    RISK_SCORE_THRESHOLDS,
)


def evaluate_risk(state: GuardState) -> GuardState:
    """
    Evaluate risk level based on detected fields.
    """
    detected = state.get("detected_fields", [])
    state["risk_level"] = compute_risk_level(detected)
    return state


def compute_risk_level(detected_fields: Sequence[dict]) -> str:
    """
    Compute risk level based on detected field types.

    Uses pre-computed risk values from each field's 'risk' attribute.
    Expects all fields to have been processed through merge_detections first.
    """

    high_threshold = RISK_SCORE_THRESHOLDS["high"]
    medium_range = RISK_SCORE_THRESHOLDS["medium"]
    low_range = RISK_SCORE_THRESHOLDS["low"]

    score = 0
    for field_info in detected_fields:
        risk_value = field_info.get("risk", "").lower()
        score += RISK_SCORE.get(risk_value, 0)  # Default to 0 for missing/unknown risk

    if score >= high_threshold:
        return "high"
    if medium_range[0] <= score <= medium_range[1]:
        return "medium"
    if low_range[0] <= score <= low_range[1]:
        return "low"
    return "none"


__all__ = ["compute_risk_level", "evaluate_risk"]
