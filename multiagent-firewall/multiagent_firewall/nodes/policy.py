from __future__ import annotations

from ..types import GuardState


_RISK_ORDER = {
    "none": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
}


def _risk_value(name: str | None) -> int:
    return _RISK_ORDER.get((name or "").strip().lower(), 0)


def apply_policy(state: GuardState) -> GuardState:
    risk_level = state.get("risk_level")
    threshold = state.get("min_block_risk") or "medium"

    risk_value = _risk_value(risk_level)
    threshold_value = _risk_value(threshold) or _RISK_ORDER["medium"]

    if risk_value >= threshold_value and risk_value > 0:
        state["decision"] = "block"
    elif state.get("detected_fields"):
        state["decision"] = "warn"
    else:
        state["decision"] = "allow"
    return state


def generate_remediation(state: GuardState) -> GuardState:
    decision = state.get("decision")

    if decision == "block":
        unique_fields = {
            item.get("field", "unknown") for item in state.get("detected_fields", [])
        }
        fields = ", ".join(unique_fields)
        state["remediation"] = (
            f"Sensitive data detected ({fields or 'unspecified'}). "
            "Redact or remove the flagged content before resubmitting."
        )
    elif decision == "warn":
        unique_fields = {
            item.get("field", "unknown") for item in state.get("detected_fields", [])
        }
        fields = ", ".join(unique_fields)
        state["remediation"] = (
            f"Sensitive data detected ({fields or 'unspecified'}). "
            "Consider redacting or removing sensitive information before interacting with remote LLMs."
        )
    else:
        state["remediation"] = ""
    return state
