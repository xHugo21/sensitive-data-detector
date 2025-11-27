from __future__ import annotations

from typing import Sequence
from ..types import GuardState
from ..constants import (
    HIGH_RISK_FIELDS,
    MEDIUM_RISK_FIELDS,
    LOW_RISK_FIELDS,
    RISK_SCORE_THRESHOLDS,
)


def evaluate_risk(state: GuardState) -> GuardState:
    """
    Evaluate risk level based on detected fields.

    Uses the default compute_risk_level function as the single
    source of truth for risk evaluation logic.
    """
    detected = state.get("detected_fields", [])
    state["risk_level"] = compute_risk_level(detected)
    return state


def compute_risk_level(detected_fields: Sequence[dict]) -> str:
    """
    Compute risk level based on detected field types.
    """

    def norm(name: str) -> str:
        return (name or "").strip().upper().replace("-", "").replace("_", "")

    high_threshold = RISK_SCORE_THRESHOLDS["High"]
    medium_range = RISK_SCORE_THRESHOLDS["Medium"]
    low_range = RISK_SCORE_THRESHOLDS["Low"]

    score = 0
    for field_info in detected_fields:
        field = norm(field_info.get("field", ""))
        if field in HIGH_RISK_FIELDS:
            score += high_threshold
        elif field in MEDIUM_RISK_FIELDS:
            score += 2
        elif field in LOW_RISK_FIELDS:
            score += 1
        else:
            score += 2

    if score >= high_threshold:
        return "High"
    if medium_range[0] <= score <= medium_range[1]:
        return "Medium"
    if low_range[0] <= score <= low_range[1]:
        return "Low"
    return "None"


__all__ = ["compute_risk_level", "evaluate_risk"]
