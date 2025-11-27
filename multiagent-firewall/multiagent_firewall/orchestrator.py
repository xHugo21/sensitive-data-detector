from __future__ import annotations

import os

from functools import partial
from typing import Any, Dict, Mapping, Sequence

from langgraph.graph import END, StateGraph

from . import nodes
from .detectors import TesseractOCRDetector, LiteLLMDetector
from .constants import REGEX_PATTERNS, KEYWORDS
from .nodes.detection import LLMDetector, OCRDetector
from .nodes.risk import compute_risk_level
from .types import GuardState, RiskEvaluator
from .utils import debug_invoke


def _should_read_document(state: GuardState) -> str:
    """Route to document reader only if file_path is provided."""
    if state.get("file_path"):
        return "read_document"
    return "normalize"


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
        self._ocr_detector = (
            ocr_detector if ocr_detector is not None else self._create_default_ocr()
        )
        self._graph = self._build_graph()

    def run(
        self,
        text: str = None,
        *,
        file_path: str = None,
        mode: str | None = None,
        min_block_risk: str | None = None,
    ) -> GuardState:
        """
        Run the detection pipeline.

        Args:
            text: Direct text input
            file_path: Path to file on disk (automatically detects images)
            mode: Detection mode (zero-shot, few-shot, enriched-zero-shot)

        Returns:
            GuardState with detection results
        """
        initial_state: GuardState = {
            "raw_text": text or "",
            "file_path": file_path,
            "mode": mode,
            "min_block_risk": (min_block_risk or "medium").lower(),
            "metadata": {},
            "warnings": [],
            "errors": [],
        }
        if bool(os.getenv("DEBUG_MODE")):
            return debug_invoke(self._graph, initial_state)
        else:
            return self._graph.invoke(initial_state)

    def _create_default_ocr(self) -> OCRDetector | None:
        """
        Create default OCR detector from environment.

        Returns None if Tesseract is not available or fails to initialize.
        This allows graceful degradation when OCR dependencies are missing.
        """
        try:
            return TesseractOCRDetector.from_env()
        except Exception as e:
            # Log warning but don't crash - OCR is optional
            import warnings

            warnings.warn(
                f"Failed to initialize OCR detector: {e}. "
                "Image text extraction will be disabled. "
                "Install Tesseract: https://github.com/tesseract-ocr/tesseract",
                RuntimeWarning,
            )
            return None

    def _build_graph(self):
        graph = StateGraph(GuardState)

        graph.add_node(
            "read_document",
            partial(nodes.read_document, ocr_detector=self._ocr_detector),
        )
        graph.add_node("normalize", nodes.normalize)
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

        # Conditional entry: only read_document if file_path provided
        graph.set_conditional_entry_point(
            _should_read_document,
            path_map={"read_document": "read_document", "normalize": "normalize"},
        )
        graph.add_edge("read_document", "normalize")
        graph.add_edge("normalize", "dlp_detector")
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
