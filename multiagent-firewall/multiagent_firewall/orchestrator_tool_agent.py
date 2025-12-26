from __future__ import annotations

from dataclasses import dataclass
from functools import partial
import json
import re
from typing import Callable, Iterable

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END

from . import nodes
from .config import GuardConfig
from .detectors.utils import build_chat_litellm, coerce_litellm_content_to_text
from .routers import (
    route_after_dlp_ner,
    route_after_merge_final,
    should_read_document,
    should_run_llm,
    should_run_llm_ocr,
)
from .types import GuardState
from .utils import append_error, append_warning

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    fn: Callable[[GuardState], GuardState]


class ToolCallingGuardOrchestrator:
    """Orchestrates the sensitive data detection pipeline via an LLM tool router."""

    def __init__(self, config: GuardConfig, *, max_steps: int = 20) -> None:
        self._config = config
        self._max_steps = max_steps
        self._tools = self._build_tools()
        self._tool_lookup = {tool.name: tool for tool in self._tools}
        self._system_prompt = _build_system_prompt(self._tools)
        self._llm = build_chat_litellm(
            provider=self._config.llm.provider,
            model=self._config.llm.model,
            client_params=self._config.llm.client_params,
        )
        if hasattr(self._llm, "bind"):
            self._json_llm = self._llm.bind(response_format={"type": "json_object"})
        else:
            self._json_llm = None

    def run(
        self,
        text: str | None = None,
        *,
        file_path: str | None = None,
        min_block_risk: str | None = None,
    ) -> GuardState:
        initial_state = self.build_initial_state(
            text=text,
            file_path=file_path,
            min_block_risk=min_block_risk,
        )
        return self._run_agent(initial_state)

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
        return initial_state, self._stream_agent(initial_state, stream_mode=stream_mode)

    def _build_tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                "read_document",
                "Extract text from file_path into raw_text and set metadata.",
                partial(nodes.read_document, fw_config=self._config),
            ),
            ToolSpec(
                "llm_ocr",
                "Extract text from an image via LLM OCR when raw_text is empty.",
                partial(nodes.llm_ocr_document, fw_config=self._config),
            ),
            ToolSpec(
                "normalize",
                "Normalize raw_text into normalized_text.",
                nodes.normalize,
            ),
            ToolSpec(
                "dlp_detector",
                "Run regex/keyword/checksum detection on normalized_text.",
                nodes.run_dlp_detector,
            ),
            ToolSpec(
                "ner_detector",
                "Run NER detection on normalized_text.",
                partial(nodes.run_ner_detector, fw_config=self._config),
            ),
            ToolSpec(
                "merge_dlp_ner",
                "Merge DLP/NER/LLM fields into detected_fields.",
                nodes.merge_detections,
            ),
            ToolSpec(
                "anonymize_dlp_ner",
                "Anonymize detected_fields over normalized_text into anonymized_text.",
                partial(
                    nodes.anonymize_text,
                    fw_config=self._config,
                    findings_key="detected_fields",
                    text_keys=("normalized_text",),
                ),
            ),
            ToolSpec(
                "risk_dlp_ner",
                "Compute risk_level from detected_fields.",
                nodes.evaluate_risk,
            ),
            ToolSpec(
                "policy_dlp_ner",
                "Apply policy to set decision based on risk.",
                nodes.apply_policy,
            ),
            ToolSpec(
                "llm_detector",
                "Run LLM detector on anonymized_text or normalized_text.",
                partial(nodes.run_llm_detector, fw_config=self._config),
            ),
            ToolSpec(
                "merge_final",
                "Merge all detections (including LLM) into detected_fields.",
                nodes.merge_detections,
            ),
            ToolSpec(
                "risk_final",
                "Compute final risk_level after LLM detection.",
                nodes.evaluate_risk,
            ),
            ToolSpec(
                "policy_final",
                "Apply policy after final risk evaluation.",
                nodes.apply_policy,
            ),
            ToolSpec(
                "remediation",
                "Generate remediation message from decision and detected_fields.",
                nodes.generate_remediation,
            ),
            ToolSpec(
                "final_anonymize",
                "Apply final anonymization over anonymized_text/normalized_text.",
                partial(
                    nodes.anonymize_text,
                    fw_config=self._config,
                    findings_key="detected_fields",
                    text_keys=("anonymized_text", "normalized_text"),
                ),
            ),
        ]

    def _run_agent(self, state: GuardState) -> GuardState:
        history: list[str] = []
        for _ in range(self._max_steps):
            allowed = self._allowed_tools(state, history)
            if not allowed:
                if self._can_finish(state, history):
                    break
                append_warning(state, "Tool agent had no valid next steps.")
                break

            tool_name = self._select_tool(state, history, allowed)
            tool = self._tool_lookup.get(tool_name)
            if not tool:
                append_warning(state, f"Unknown tool requested: {tool_name}")
                tool_name = allowed[0]
                tool = self._tool_lookup.get(tool_name)
                if not tool:
                    append_error(state, f"Fallback tool missing: {tool_name}")
                    break
            self._apply_tool(state, tool)
            history.append(tool.name)
        else:
            append_warning(state, "Tool agent stopped after max_steps without finishing.")
        return state

    def _stream_agent(
        self,
        state: GuardState,
        *,
        stream_mode: str | list[str],
    ):
        modes = _normalize_stream_modes(stream_mode)
        history: list[str] = []

        def iterator():
            for _ in range(self._max_steps):
                allowed = self._allowed_tools(state, history)
                if not allowed:
                    if self._can_finish(state, history):
                        break
                    append_warning(state, "Tool agent had no valid next steps.")
                    break

                tool_name = self._select_tool(state, history, allowed)
                tool = self._tool_lookup.get(tool_name)
                if not tool:
                    append_warning(state, f"Unknown tool requested: {tool_name}")
                    tool_name = allowed[0]
                    tool = self._tool_lookup.get(tool_name)
                    if not tool:
                        append_error(state, f"Fallback tool missing: {tool_name}")
                        break

                if "tasks" in modes:
                    yield ("tasks", {"name": tool.name})

                update = self._apply_tool(state, tool)

                if "updates" in modes:
                    yield ("updates", {tool.name: update})

                if "tasks" in modes:
                    yield ("tasks", {"name": tool.name, "result": True})

                history.append(tool.name)
            else:
                append_warning(
                    state, "Tool agent stopped after max_steps without finishing."
                )

        return iterator()

    def _apply_tool(self, state: GuardState, tool: ToolSpec) -> GuardState:
        try:
            update = tool.fn(state)
        except Exception as exc:
            append_error(state, f"Tool {tool.name} failed: {exc}")
            return state
        if isinstance(update, dict):
            state.update(update)
            return update
        return state

    def _select_tool(
        self,
        state: GuardState,
        history: list[str],
        allowed: list[str],
    ) -> str:
        if len(allowed) == 1:
            return allowed[0]
        summary = _summarize_state(state, history)
        user_prompt = _build_user_prompt(summary, allowed)
        messages = [
            SystemMessage(content=self._system_prompt),
            HumanMessage(content=user_prompt),
        ]
        try:
            model = self._json_llm if self._json_llm else self._llm
            response = model.invoke(messages)
            content = coerce_litellm_content_to_text(response)
            payload = _safe_json_from_text(content)
            tool_name = str(payload.get("tool") or "").strip()
            if tool_name in allowed:
                return tool_name
        except Exception as exc:
            append_warning(state, f"Tool planner failed: {exc}")
        return allowed[0]

    def _allowed_tools(self, state: GuardState, history: list[str]) -> list[str]:
        def has_run(name: str) -> bool:
            return name in history

        allowed: list[str] = []

        file_path_set = bool(state.get("file_path"))
        wants_read = should_read_document(state) == "read_document"
        if file_path_set and wants_read and not has_run("read_document"):
            return ["read_document"]

        if has_run("read_document") and should_run_llm_ocr(state) == "llm_ocr":
            if not has_run("llm_ocr"):
                return ["llm_ocr"]

        if not has_run("normalize"):
            if not file_path_set or has_run("read_document"):
                if should_run_llm_ocr(state) != "llm_ocr" or has_run("llm_ocr"):
                    return ["normalize"]

        if has_run("normalize") and not has_run("dlp_detector"):
            allowed.append("dlp_detector")
        if has_run("normalize") and not has_run("ner_detector"):
            allowed.append("ner_detector")
        if allowed:
            return allowed

        if (
            has_run("dlp_detector")
            and has_run("ner_detector")
            and not has_run("merge_dlp_ner")
        ):
            return ["merge_dlp_ner"]

        if has_run("merge_dlp_ner"):
            post_dlp = route_after_dlp_ner(state)
            if post_dlp == "risk_dlp_ner" and not has_run("risk_dlp_ner"):
                return ["risk_dlp_ner"]
            if post_dlp == "llm_detector" and not has_run("llm_detector"):
                return ["llm_detector"]

        if has_run("risk_dlp_ner") and not has_run("policy_dlp_ner"):
            return ["policy_dlp_ner"]

        if has_run("policy_dlp_ner"):
            next_step = should_run_llm(state)
            if next_step == "remediation" and not has_run("remediation"):
                return ["remediation"]
            if next_step == "anonymize_dlp_ner" and not has_run("anonymize_dlp_ner"):
                return ["anonymize_dlp_ner"]

        if has_run("anonymize_dlp_ner") and not has_run("llm_detector"):
            return ["llm_detector"]

        if has_run("llm_detector") and not has_run("merge_final"):
            return ["merge_final"]

        if has_run("merge_final"):
            post_merge = route_after_merge_final(state)
            if post_merge == "risk_final" and not has_run("risk_final"):
                return ["risk_final"]
            if post_merge == "remediation" and not has_run("remediation"):
                return ["remediation"]

        if has_run("risk_final") and not has_run("policy_final"):
            return ["policy_final"]

        if has_run("policy_final") and not has_run("remediation"):
            return ["remediation"]

        if has_run("remediation") and not has_run("final_anonymize"):
            return ["final_anonymize"]

        return []

    def _can_finish(self, state: GuardState, history: list[str]) -> bool:
        if "final_anonymize" in history:
            return True
        if "merge_final" in history and route_after_merge_final(state) == END:
            return True
        return False


def _summarize_state(state: GuardState, history: Iterable[str]) -> dict:
    return {
        "file_path_set": bool(state.get("file_path")),
        "file_type": state.get("metadata", {}).get("file_type"),
        "raw_text_len": len(state.get("raw_text") or ""),
        "normalized_text_len": len(state.get("normalized_text") or ""),
        "anonymized_text_len": len(state.get("anonymized_text") or ""),
        "dlp_fields": len(state.get("dlp_fields") or []),
        "ner_fields": len(state.get("ner_fields") or []),
        "llm_fields": len(state.get("llm_fields") or []),
        "detected_fields": len(state.get("detected_fields") or []),
        "risk_level": state.get("risk_level"),
        "decision": state.get("decision"),
        "min_block_risk": state.get("min_block_risk"),
        "force_llm_detector": bool(state.get("force_llm_detector")),
        "warnings": len(state.get("warnings") or []),
        "errors": len(state.get("errors") or []),
        "tools_run": list(history),
    }


def _build_user_prompt(summary: dict, allowed: list[str]) -> str:
    return (
        "State summary:\n"
        f"{json.dumps(summary, ensure_ascii=True, sort_keys=True)}\n"
        f"Allowed tools: {', '.join(allowed)}\n"
        "Pick the next tool from the allowed list."
    )


def _build_system_prompt(tools: list[ToolSpec]) -> str:
    lines = [
        "You are a tool-calling router for a sensitive data detection pipeline.",
        "Return JSON only: {\"tool\": \"<name>\", \"reason\": \"...\"}.",
        "Pick exactly one tool from the allowed list provided by the user.",
        "Avoid repeating tools unless new data was added.",
        "Do not invent tools; do not return analysis.",
        "Available tools:",
    ]
    for tool in tools:
        lines.append(f"- {tool.name}: {tool.description}")
    return "\n".join(lines)


def _safe_json_from_text(text: str) -> dict:
    if not text:
        return {}
    match = _JSON_RE.search(text)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except Exception:
        return {}


def _normalize_stream_modes(stream_mode: str | list[str]) -> set[str]:
    if isinstance(stream_mode, str):
        return {stream_mode}
    return set(stream_mode)


def _normalize_risk(value: str | None) -> str:
    allowed = {"none", "low", "medium", "high"}
    if value is None:
        return "medium"
    normalized = value.strip().lower()
    if normalized not in allowed:
        return "medium"
    return normalized
