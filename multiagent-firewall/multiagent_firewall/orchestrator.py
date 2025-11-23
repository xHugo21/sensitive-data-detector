from __future__ import annotations

from functools import partial
from typing import Any, Dict, Mapping, Sequence

from langgraph.graph import END, StateGraph

from . import nodes
from .llm_detector import LiteLLMDetector
from .types import (
    DLPDetector,
    GuardState,
    LLMDetector,
    OCRDetector,
    RiskEvaluator,
    default_regex_patterns,
)


class GuardOrchestrator:

    def __init__(
        self,
        *,
        risk_evaluator: RiskEvaluator,
        llm_detector: LLMDetector | None = None,
        regex_patterns: Mapping[str, str] | None = None,
        extra_dlp_detectors: Sequence[DLPDetector] | None = None,
        ocr_detector: OCRDetector | None = None,
    ) -> None:
        self._llm_detector = llm_detector or LiteLLMDetector.from_env()
        self._risk_evaluator = risk_evaluator
        self._regex_patterns = regex_patterns or default_regex_patterns()
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

    def _build_graph(self):
        graph = StateGraph(GuardState)
        graph.add_node("normalize", nodes.normalize)
        graph.add_node(
            "llm_detector",
            partial(nodes.run_llm_detector, llm_detector=self._llm_detector),
        )
        graph.add_node(
            "dlp_detector",
            partial(
                nodes.run_dlp_detector,
                regex_patterns=self._regex_patterns,
                extra_dlp_detectors=self._extra_dlp_detectors,
            ),
        )
        graph.add_node(
            "ocr_detector",
            partial(nodes.run_ocr_detector, ocr_detector=self._ocr_detector),
        )
        graph.add_node("merge", nodes.merge_detections)
        graph.add_node(
            "risk",
            partial(nodes.evaluate_risk, risk_evaluator=self._risk_evaluator),
        )
        graph.add_node("policy", nodes.apply_policy)
        graph.add_node("remediation", nodes.generate_remediation)

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
