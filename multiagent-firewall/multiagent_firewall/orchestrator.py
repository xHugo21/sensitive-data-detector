from __future__ import annotations

from typing import cast
from functools import partial

from langgraph.graph import END, StateGraph

from . import nodes
from .config import GuardConfig
from .routers import (
    route_after_dlp_ner,
    route_after_merge_final,
    should_read_document,
    should_run_llm,
    should_run_llm_ocr,
)
from .types import GuardState
from .utils import debug_invoke


class GuardOrchestrator:
    """Orchestrates the sensitive data detection pipeline."""

    def __init__(self, config: GuardConfig) -> None:
        self._config = config
        self._graph = self._build_graph()

    def run(
        self,
        text: str | None = None,
        *,
        file_path: str | None = None,
        min_block_risk: str | None = None,
    ) -> GuardState:
        """
        Run the detection pipeline.

        Args:
            text: Direct text input
            file_path: Path to file on disk (automatically detects images)
            min_block_risk: Minimum risk level ("none", "low", "medium", "high") required to trigger blocking actions

        Returns:
            GuardState with detection results
        """
        initial_state = self.build_initial_state(
            text=text,
            file_path=file_path,
            min_block_risk=min_block_risk,
        )
        if self._config.debug:
            return debug_invoke(self._graph, initial_state)
        return cast(GuardState, self._graph.invoke(initial_state))

    def build_initial_state(
        self,
        *,
        text: str | None = None,
        file_path: str | None = None,
        min_block_risk: str | None = None,
    ) -> GuardState:
        return {
            "raw_text": text or "",
            "file_path": file_path,
            "min_block_risk": _normalize_risk(min_block_risk),
            "llm_provider": self._config.llm.provider,
            "force_llm_detector": self._config.force_llm_detector,
            "metadata": {},
            "warnings": [],
            "errors": [],
            "decision": "allow",
            "risk_level": "none",
        }

    def stream_updates(
        self,
        *,
        text: str | None = None,
        file_path: str | None = None,
        min_block_risk: str | None = None,
        stream_mode: str | list[str] = "updates",
    ):
        initial_state = self.build_initial_state(
            text=text,
            file_path=file_path,
            min_block_risk=min_block_risk,
        )
        return initial_state, self._graph.stream(
            initial_state,
            stream_mode=stream_mode,
        )

    def _build_graph(self):
        graph = StateGraph(GuardState)

        graph.add_node(
            "read_document",
            partial(nodes.read_document, fw_config=self._config),
        )
        graph.add_node(
            "llm_ocr",
            partial(nodes.llm_ocr_document, fw_config=self._config),
        )
        graph.add_node("normalize", nodes.normalize)
        graph.add_node("dlp_detector", nodes.run_dlp_detector)
        graph.add_node(
            "ner_detector",
            partial(nodes.run_ner_detector, fw_config=self._config),
        )
        graph.add_node("merge_dlp_ner", nodes.merge_detections)
        graph.add_node(
            "anonymize_dlp_ner",
            partial(
                nodes.anonymize_text,
                fw_config=self._config,
                findings_key="detected_fields",
                text_keys=("normalized_text",),
            ),
        )
        graph.add_node("risk_dlp_ner", nodes.evaluate_risk)
        graph.add_node("policy_dlp_ner", nodes.apply_policy)
        graph.add_node(
            "llm_detector",
            partial(nodes.run_llm_detector, fw_config=self._config),
        )
        graph.add_node("merge_final", nodes.merge_detections)
        graph.add_node("risk_final", nodes.evaluate_risk)
        graph.add_node("policy_final", nodes.apply_policy)
        graph.add_node("remediation", nodes.generate_remediation)
        graph.add_node(
            "final_anonymize",
            partial(
                nodes.anonymize_text,
                fw_config=self._config,
                findings_key="detected_fields",
                text_keys=("anonymized_text", "normalized_text"),
            ),
        )

        graph.set_conditional_entry_point(
            should_read_document,
        )
        graph.add_conditional_edges(
            "read_document",
            should_run_llm_ocr,
        )
        graph.add_edge("llm_ocr", "normalize")
        graph.add_edge("normalize", "dlp_detector")
        graph.add_edge("normalize", "ner_detector")
        graph.add_edge("dlp_detector", "merge_dlp_ner")
        graph.add_edge("ner_detector", "merge_dlp_ner")
        graph.add_conditional_edges(
            "merge_dlp_ner",
            route_after_dlp_ner,
        )
        graph.add_edge("risk_dlp_ner", "policy_dlp_ner")
        graph.add_conditional_edges(
            "policy_dlp_ner",
            should_run_llm,
        )
        graph.add_edge("anonymize_dlp_ner", "llm_detector")
        graph.add_edge("llm_detector", "merge_final")
        graph.add_conditional_edges(
            "merge_final",
            route_after_merge_final,
        )
        graph.add_edge("risk_final", "policy_final")
        graph.add_edge("policy_final", "remediation")
        graph.add_edge("remediation", "final_anonymize")
        graph.add_edge("final_anonymize", END)

        return graph.compile()


def _normalize_risk(value: str | None) -> str:
    allowed = {"none", "low", "medium", "high"}
    if value is None:
        return "medium"
    normalized = value.strip().lower()
    if normalized not in allowed:
        return "medium"
    return normalized
