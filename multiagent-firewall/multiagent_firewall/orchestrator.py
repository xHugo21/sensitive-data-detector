from __future__ import annotations

from functools import partial
from typing import Any, Dict, Mapping, Sequence

from langgraph.graph import END, StateGraph

from . import nodes
from .detectors import LiteLLMDetector
from .constants import REGEX_PATTERNS, KEYWORDS
from .nodes.detection import LLMDetector, OCRDetector
from .nodes.risk import compute_risk_level
from .types import GuardState, RiskEvaluator


def _should_run_ocr(state: GuardState) -> str:
    if state.get("has_image", False):
        return "ocr_detector"
    return "dlp_detector"


def _should_run_llm(state: GuardState) -> str:
    risk_level = (state.get("risk_level") or "").lower()
    if risk_level in {"low", "none"}:
        return "llm_detector"
    return "remediation"


class GuardOrchestrator:

    def __init__(
        self,
        *,
        risk_evaluator: RiskEvaluator | None = None,
        llm_detector: LLMDetector | None = None,
        regex_patterns: Mapping[str, str] | None = None,
        keywords: Mapping[str, Sequence[str]] | None = None,
        ocr_detector: OCRDetector | None = None,
    ) -> None:
        self._llm_detector = llm_detector or LiteLLMDetector.from_env()
        self._risk_evaluator = risk_evaluator or compute_risk_level
        self._regex_patterns = regex_patterns or REGEX_PATTERNS
        self._keywords = keywords or KEYWORDS
        self._ocr_detector = ocr_detector
        self._graph = self._build_graph()

    def run(
        self,
        text: str = None,
        *,
        file_path: str = None,
        mode: str | None = None,
        has_image: bool = False,
    ) -> GuardState:
        """
        Run the detection pipeline.
        
        Args:
            text: Direct text input
            file_path: Path to file on disk
            mode: Detection mode (zero-shot, few-shot, enriched-zero-shot)
            has_image: Force image processing (optional, for backward compatibility)
        
        Returns:
            GuardState with detection results
        """
        initial_state: GuardState = {
            "raw_text": text or "",
            "file_path": file_path,
            "mode": mode,
            "metadata": {},
            "has_image": has_image,
            "warnings": [],
            "errors": [],
        }
        return self._graph.invoke(initial_state)

    def _build_graph(self):
        graph = StateGraph(GuardState)
        
        # Add read_document node first
        graph.add_node("read_document", nodes.read_document)
        graph.add_node("normalize", nodes.normalize)
        graph.add_node(
            "ocr_detector",
            partial(nodes.run_ocr_detector, ocr_detector=self._ocr_detector),
        )
        graph.add_node(
            "dlp_detector",
            partial(
                nodes.run_dlp_detector,
                regex_patterns=self._regex_patterns,
                keywords=self._keywords,
            ),
        )
        graph.add_node("merge_dlp", nodes.merge_detections)
        graph.add_node(
            "risk_dlp",
            partial(nodes.evaluate_risk, risk_evaluator=self._risk_evaluator),
        )
        graph.add_node("policy_dlp", nodes.apply_policy)
        graph.add_node(
            "llm_detector",
            partial(nodes.run_llm_detector, llm_detector=self._llm_detector),
        )
        graph.add_node("merge_final", nodes.merge_detections)
        graph.add_node(
            "risk_final",
            partial(nodes.evaluate_risk, risk_evaluator=self._risk_evaluator),
        )
        graph.add_node("policy_final", nodes.apply_policy)
        graph.add_node("remediation", nodes.generate_remediation)

        # Start with read_document, then normalize
        graph.set_entry_point("read_document")
        graph.add_edge("read_document", "normalize")
        graph.add_conditional_edges("normalize", _should_run_ocr)
        graph.add_edge("ocr_detector", "dlp_detector")
        graph.add_edge("dlp_detector", "merge_dlp")
        graph.add_edge("merge_dlp", "risk_dlp")
        graph.add_edge("risk_dlp", "policy_dlp")
        graph.add_conditional_edges("policy_dlp", _should_run_llm)
        graph.add_edge("llm_detector", "merge_final")
        graph.add_edge("merge_final", "risk_final")
        graph.add_edge("risk_final", "policy_final")
        graph.add_edge("policy_final", "remediation")
        graph.add_edge("remediation", END)
        return graph.compile()
