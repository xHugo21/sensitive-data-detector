from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Mapping, Sequence, TypedDict

from typing_extensions import NotRequired

from langgraph.graph import END, StateGraph


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


class GuardOrchestrator:
    """Orchestrates the firewall graph and exposes a simple run() API."""

    def __init__(
        self,
        *,
        llm_detector: LLMDetector,
        risk_evaluator: RiskEvaluator,
        regex_patterns: Mapping[str, str] | None = None,
        extra_dlp_detectors: Sequence[DLPDetector] | None = None,
        ocr_detector: OCRDetector | None = None,
    ) -> None:
        self._llm_detector = llm_detector
        self._risk_evaluator = risk_evaluator
        self._regex_patterns = regex_patterns or _default_regex_patterns()
        self._extra_dlp_detectors = list(extra_dlp_detectors or [])
        self._ocr_detector = ocr_detector
        self._graph = self._build_graph()

    def run(
        self,
        text: str,
        *,
        prompt: str | None = None,
        mode: str | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> GuardState:
        initial_state: GuardState = {
            "raw_text": text or "",
            "prompt": prompt,
            "mode": mode,
            "metadata": metadata or {},
            "warnings": [],
            "errors": [],
        }
        return self._graph.invoke(initial_state)

    # --- Graph building -------------------------------------------------

    def _build_graph(self):
        graph = StateGraph(GuardState)
        graph.add_node("normalize", self._normalize_node)
        graph.add_node("llm_detector", self._llm_detector_node)
        graph.add_node("dlp_detector", self._dlp_detector_node)
        graph.add_node("ocr_detector", self._ocr_detector_node)
        graph.add_node("merge", self._merge_detections_node)
        graph.add_node("risk", self._risk_node)
        graph.add_node("policy", self._policy_node)
        graph.add_node("remediation", self._remediation_node)

        graph.set_entry_point("normalize")
        graph.add_edge("normalize", "llm_detector")
        graph.add_edge("llm_detector", "dlp_detector")
        graph.add_edge("dlp_detector", "ocr_detector")
        graph.add_edge("ocr_detector", "merge")
        graph.add_edge("merge", "risk")
        graph.add_edge("risk", "policy")
        graph.add_edge("policy", "remediation")
        graph.add_edge("remediation", END)
        return graph.compile()

    # --- Nodes ----------------------------------------------------------

    _whitespace_re = re.compile(r"\s+")

    def _normalize_node(self, state: GuardState) -> GuardState:
        text = state.get("raw_text") or ""
        normalized = self._whitespace_re.sub(" ", text).strip()
        state["normalized_text"] = normalized
        if not normalized:
            _append(state, "warnings", "No text provided for analysis.")
        return state

    def _llm_detector_node(self, state: GuardState) -> GuardState:
        text = state.get("normalized_text") or ""
        if not text:
            state["llm_fields"] = []
            return state
        try:
            result = self._llm_detector(
                text,
                state.get("prompt"),
                state.get("mode"),
            )
            fields = [
                {**item, "source": item.get("source", "llm_detector")}
                for item in result.get("detected_fields", [])
                if isinstance(item, dict)
            ]
            state["llm_fields"] = fields
        except Exception as exc:  # pragma: no cover - defensive
            _append(state, "errors", f"LLM detector failed: {exc}")
            state["llm_fields"] = []
        return state

    def _dlp_detector_node(self, state: GuardState) -> GuardState:
        text = state.get("normalized_text") or ""
        findings: FieldList = []
        for field_name, pattern in self._regex_patterns.items():
            for match in re.findall(pattern, text):
                value = match if isinstance(match, str) else " ".join(match)
                cleaned = value.strip()
                if not cleaned:
                    continue
                findings.append(
                    {"field": field_name, "value": cleaned, "source": "dlp_regex"}
                )
        for detector in self._extra_dlp_detectors:
            try:
                extra = detector(text) or []
                for item in extra:
                    if isinstance(item, dict):
                        findings.append(item)
            except Exception as exc:  # pragma: no cover - defensive
                _append(state, "errors", f"DLP detector failed: {exc}")
        state["dlp_fields"] = findings
        return state

    def _ocr_detector_node(self, state: GuardState) -> GuardState:
        if not self._ocr_detector:
            state.setdefault("ocr_fields", [])
            return state
        try:
            state["ocr_fields"] = self._ocr_detector(state) or []
        except Exception as exc:  # pragma: no cover - defensive
            _append(state, "errors", f"OCR detector failed: {exc}")
            state["ocr_fields"] = []
        return state

    def _merge_detections_node(self, state: GuardState) -> GuardState:
        merged: FieldList = []
        seen = set()
        for key in ("llm_fields", "dlp_fields", "ocr_fields"):
            for item in state.get(key, []) or []:
                if not isinstance(item, dict):
                    continue
                field = (item.get("field") or "").strip()
                value = (item.get("value") or "").strip()
                signature = (field.lower(), value.lower())
                if signature in seen:
                    continue
                seen.add(signature)
                merged.append(item)
        state["detected_fields"] = merged
        return state

    def _risk_node(self, state: GuardState) -> GuardState:
        detected = state.get("detected_fields", [])
        state["risk_level"] = self._risk_evaluator(detected)
        return state

    def _policy_node(self, state: GuardState) -> GuardState:
        risk = (state.get("risk_level") or "none").lower()
        if risk in {"high", "medium"}:
            state["decision"] = "block"
        elif risk == "low" and state.get("detected_fields"):
            state["decision"] = "allow_with_warning"
        else:
            state["decision"] = "allow"
        return state

    def _remediation_node(self, state: GuardState) -> GuardState:
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


def _append(state: GuardState, key: str, value: Any) -> None:
    state.setdefault(key, [])
    state[key].append(value)


def _default_regex_patterns() -> Dict[str, str]:
    return {
        "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "PHONE_NUMBER": r"\b\+?\d[\d\s\-\(\)]{7,}\d\b",
    }
