from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping, Sequence

from typing_extensions import NotRequired, TypedDict

DetectorResult = Mapping[str, Any]
FieldList = List[Dict[str, Any]]
RiskEvaluator = Callable[[Sequence[Dict[str, Any]]], str]
LLMDetector = Callable[[str, str | None, str | None], DetectorResult]
DLPDetector = Callable[[str], FieldList]
OCRDetector = Callable[["GuardState"], FieldList]


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


def default_regex_patterns() -> Dict[str, str]:
    return {
        "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "PHONE_NUMBER": r"\b\+?\d[\d\s\-\(\)]{7,}\d\b",
    }
