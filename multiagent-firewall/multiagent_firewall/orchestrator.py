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


def _should_run_llm_ocr(state: GuardState) -> str:
    """Route to llm_ocr if image file with no extracted text."""
    metadata = state.get("metadata", {})
    raw_text = (state.get("raw_text") or "").strip()
    is_image = metadata.get("file_type") == "image"

    if is_image and not raw_text:
        return "llm_ocr"
    return "normalize"


def _should_run_llm(state: GuardState) -> str:
    """Route to llm_detector unless policy already blocks."""
    decision = (state.get("decision") or "").lower()
    if decision == "block":
        return "remediation"
    return "llm_detector"


def _route_after_dlp(state: GuardState) -> str:
    """Skip DLP risk/policy if no DLP detections were found."""
    state["_dlp_detected_count"] = len(state.get("detected_fields") or [])
    if state.get("dlp_fields"):
        return "risk_dlp"
    return "llm_detector"


def _route_after_merge_final(state: GuardState) -> str:
    """Avoid redundant final risk/policy when nothing new was added."""
    detected_fields = state.get("detected_fields") or []
    llm_fields = state.get("llm_fields") or []
    dlp_detected_count = state.get("_dlp_detected_count")

    if not detected_fields:
        return "risk_final"

    no_new_fields = (
        dlp_detected_count is not None
        and len(detected_fields) == dlp_detected_count
    )
    if no_new_fields and state.get("decision"):
        return "remediation"
    if not llm_fields and state.get("decision"):
        return "remediation"

    return "risk_final"


class GuardOrchestrator:
    """Orchestrates the sensitive data detection pipeline."""

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
            min_block_risk: Minimum risk level ("none", "low", "medium", "high") required to trigger blocking actions

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
        graph = StateGraph(GuardState)

        graph.add_node("read_document", nodes.read_document)
        graph.add_node("llm_ocr", nodes.llm_ocr_document)
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
        graph.add_conditional_edges(
            "read_document",
            _should_run_llm_ocr,
            path_map={"llm_ocr": "llm_ocr", "normalize": "normalize"},
        )
        graph.add_edge("llm_ocr", "normalize")
        graph.add_edge("normalize", "dlp_detector")
        graph.add_edge("dlp_detector", "merge_dlp")
        graph.add_conditional_edges(
            "merge_dlp",
            _route_after_dlp,
            path_map={"risk_dlp": "risk_dlp", "llm_detector": "llm_detector"},
        )
        graph.add_edge("risk_dlp", "policy_dlp")
        graph.add_conditional_edges("policy_dlp", _should_run_llm)
        graph.add_edge("llm_detector", "merge_final")
        graph.add_conditional_edges(
            "merge_final",
            _route_after_merge_final,
            path_map={
                "risk_final": "risk_final",
                "remediation": "remediation",
            },
        )
        graph.add_edge("risk_final", "policy_final")
        graph.add_edge("policy_final", "remediation")
        graph.add_edge("remediation", END)

        return graph.compile()
