from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping

from ..types import GuardState

DetectorResult = Mapping[str, Any]
FieldList = List[Dict[str, Any]]
LLMDetector = Callable[[str, str | None, str | None], DetectorResult]
DLPDetector = Callable[[str], FieldList]
OCRDetector = Callable[[GuardState], FieldList]

__all__ = [
    "DetectorResult",
    "FieldList",
    "LLMDetector",
    "DLPDetector",
    "OCRDetector",
]
