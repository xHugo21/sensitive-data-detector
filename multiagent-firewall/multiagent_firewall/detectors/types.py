from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping

from ..types import GuardState

DetectorResult = Mapping[str, Any]
FieldList = List[Dict[str, Any]]
LLMDetector = Callable[[str, str | None], DetectorResult]
NERDetector = Callable[[str], FieldList]
OCRDetector = Callable[[GuardState], FieldList]
