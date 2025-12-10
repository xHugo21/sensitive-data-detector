from __future__ import annotations

from typing import Any, Dict, List

from typing_extensions import NotRequired, TypedDict

FieldList = List[Dict[str, Any]]


class GuardState(TypedDict, total=False):
    # INPUT
    file_path: NotRequired[str | None]
    raw_text: str
    llm_prompt: NotRequired[str | None]
    min_block_risk: NotRequired[str | None]

    # PROCESSING
    anonymized_text: NotRequired[str]
    normalized_text: str
    metadata: Dict[str, Any]
    warnings: List[str]
    errors: List[str]

    # DETECTION
    llm_fields: FieldList
    dlp_fields: FieldList
    detected_fields: FieldList

    # DECISION
    risk_level: str
    decision: str
    remediation: str
