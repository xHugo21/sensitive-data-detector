from __future__ import annotations

from typing import Any, Callable, Dict, List, Sequence

from typing_extensions import NotRequired, TypedDict

FieldList = List[Dict[str, Any]]
RiskEvaluator = Callable[[Sequence[Dict[str, Any]]], str]


class GuardState(TypedDict, total=False):
    raw_text: str
    normalized_text: str
    metadata: Dict[str, Any]
    prompt: NotRequired[str | None]
    mode: NotRequired[str | None]
    warnings: List[str]
    errors: List[str]
    llm_fields: FieldList
    dlp_fields: FieldList
    ocr_fields: FieldList
    detected_fields: FieldList
    risk_level: str
    decision: str
    remediation: str
