from __future__ import annotations

from typing import Any, Callable, Dict, List, Sequence

from typing_extensions import NotRequired, TypedDict

FieldList = List[Dict[str, Any]]
RiskEvaluator = Callable[[Sequence[Dict[str, Any]]], str]


class GuardState(TypedDict, total=False):
    # INPUT
    file_path: NotRequired[str | None]
    raw_text: str
    min_block_risk: NotRequired[str | None]

    # PROCESSING
    normalized_text: str
    metadata: Dict[str, Any]
    mode: NotRequired[str | None]

    # DETECTION
    warnings: List[str]
    errors: List[str]
    llm_fields: FieldList
    dlp_fields: FieldList
    ocr_fields: FieldList
    detected_fields: FieldList

    # DECISION
    risk_level: str
    decision: str
    remediation: str
