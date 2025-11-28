from __future__ import annotations

from typing import Any, Dict, List

from typing_extensions import NotRequired, TypedDict

FieldList = List[Dict[str, Any]]


class GuardState(TypedDict, total=False):
    # INPUT
    file_path: NotRequired[str | None]
    raw_text: str
    min_block_risk: NotRequired[str | None]

    # PROCESSING
    normalized_text: str
    metadata: Dict[str, Any]
    llm_prompt: NotRequired[str | None]

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
