from __future__ import annotations

from typing import Any, Dict

from multiagent_firewall import GuardOrchestrator

from app.core.detector import detect_sensitive_data
from app.core.risk import compute_risk_level

_orchestrator = GuardOrchestrator(
    llm_detector=detect_sensitive_data,
    risk_evaluator=compute_risk_level,
)


def run_guard_pipeline(
    text: str,
    *,
    prompt: str | None = None,
    mode: str | None = None,
    metadata: Dict[str, Any] | None = None,
):
    return _orchestrator.run(
        text,
        prompt=prompt,
        mode=mode,
        metadata=metadata,
    )
