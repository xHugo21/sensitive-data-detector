from __future__ import annotations

from typing import Sequence
from ..types import GuardState, RiskEvaluator
from ..constants import HIGH_RISK_FIELDS, MEDIUM_RISK_FIELDS, LOW_RISK_FIELDS


def evaluate_risk(
    state: GuardState,
    risk_evaluator: RiskEvaluator,
) -> GuardState:
    detected = state.get("detected_fields", [])
    state["risk_level"] = risk_evaluator(detected)
    return state


def compute_risk_level(detected_fields: Sequence[dict]) -> str:
    def norm(name: str) -> str:
        return (name or "").strip().upper().replace("-", "").replace("_", "")

    high_risk = HIGH_RISK_FIELDS
    medium_risk = MEDIUM_RISK_FIELDS
    low_risk = LOW_RISK_FIELDS

    score = 0
    for field_info in detected_fields:
        field = norm(field_info.get("field", ""))
        if field in high_risk:
            score += 6
        elif field in medium_risk:
            score += 2
        elif field in low_risk:
            score += 1
        else:
            score += 2

    if score >= 6:
        return "High"
    if 4 <= score <= 5:
        return "Medium"
    if 1 <= score <= 3:
        return "Low"
    return "None"


__all__ = ["compute_risk_level"]
