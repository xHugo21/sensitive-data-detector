from __future__ import annotations

import os
from typing import cast

from langgraph.graph import END, StateGraph

from . import nodes
from .types import GuardState
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
    """
    Orchestrates the sensitive data detection pipeline.

    This class builds the detection graph.
    """

    def __init__(self) -> None:
        self._graph = self._build_graph()

    def run(
        self,
        text: str | None = None,
        *,
        file_path: str | None = None,
        llm_prompt: str | None = None,
        min_block_risk: str | None = None,
    ) -> GuardState:
        """
        Run the detection pipeline.

        Args:
            text: Direct text input
            file_path: Path to file on disk (automatically detects images)
            llm_prompt: LLM prompt template (zero-shot, few-shot, enriched-zero-shot)

        Returns:
            GuardState with detection results
        """
        initial_state: GuardState = {
            "raw_text": text or "",
            "file_path": file_path,
            "llm_prompt": llm_prompt,
            "min_block_risk": (min_block_risk or "medium").lower(),
            "metadata": {},
            "warnings": [],
            "errors": [],
        }
        if bool(os.getenv("DEBUG_MODE")):
            return debug_invoke(self._graph, initial_state)
        return cast(GuardState, self._graph.invoke(initial_state))

    def _build_graph(self):
        """
        Build the detection pipeline graph.

        All nodes use their internal default detectors and configurations,
        which are the single sources of truth for the application.
        """
        graph = StateGraph(GuardState)

        graph.add_node("read_document", nodes.read_document)
        graph.add_node("normalize", nodes.normalize)
        graph.add_node("dlp_detector", nodes.run_dlp_detector)
        graph.add_node("merge_dlp", nodes.merge_detections)
        graph.add_node("risk_dlp", nodes.evaluate_risk)
        graph.add_node("policy_dlp", nodes.apply_policy)
        graph.add_node("llm_detector", nodes.run_llm_detector)
        graph.add_node("merge_final", nodes.merge_detections)
        graph.add_node("risk_final", nodes.evaluate_risk)
        graph.add_node("policy_final", nodes.apply_policy)
        graph.add_node("remediation", nodes.generate_remediation)

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
