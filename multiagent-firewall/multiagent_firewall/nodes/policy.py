from __future__ import annotations

from ..types import GuardState


def apply_policy(state: GuardState) -> GuardState:
    risk = (state.get("risk_level") or "none").lower()
    if risk in {"high", "medium"}:
        state["decision"] = "block"
    elif risk == "low" and state.get("detected_fields"):
        state["decision"] = "allow_with_warning"
    else:
        state["decision"] = "allow"
    return state


def generate_remediation(state: GuardState) -> GuardState:
    if state.get("decision") == "block":
        fields = ", ".join(
            item.get("field", "unknown") for item in state.get("detected_fields", [])
        )
        state["remediation"] = (
            f"Sensitive data detected ({fields or 'unspecified'}). "
            "Redact or remove the flagged content before resubmitting."
        )
    else:
        state["remediation"] = ""
    return state
