from __future__ import annotations

from .types import GuardState


def should_read_document(state: GuardState) -> str:
    """Route to document reader only if file_path is provided."""
    if state.get("file_path"):
        return "read_document"
    return "normalize"


def should_run_llm_ocr(state: GuardState) -> str:
    """Route to llm_ocr if image file with no extracted text."""
    metadata = state.get("metadata", {})
    raw_text = (state.get("raw_text") or "").strip()
    is_image = metadata.get("file_type") == "image"

    if is_image and not raw_text:
        return "llm_ocr"
    return "normalize"


def should_run_llm(state: GuardState) -> str:
    """Route to anonymize_llm unless policy already blocks."""
    decision = (state.get("decision") or "").lower()
    if decision == "block":
        return "remediation"
    return "anonymize_llm" if _use_anonymizer(state) else "llm_detector"


def route_after_dlp(state: GuardState) -> str:
    """Skip DLP risk/policy if no DLP detections were found."""
    state["_dlp_detected_count"] = len(state.get("detected_fields") or [])
    if state.get("dlp_fields"):
        return "risk_dlp"
    return "anonymize_llm" if _use_anonymizer(state) else "llm_detector"


def route_after_merge_final(state: GuardState) -> str:
    """Avoid redundant final risk/policy when nothing new was added."""
    detected_fields = state.get("detected_fields") or []
    llm_fields = state.get("llm_fields") or []
    dlp_detected_count = state.get("_dlp_detected_count")

    if not detected_fields:
        return "risk_final"

    no_new_fields = (
        dlp_detected_count is not None and len(detected_fields) == dlp_detected_count
    )
    if no_new_fields and state.get("decision"):
        return "remediation"
    if not llm_fields and state.get("decision"):
        return "remediation"

    return "risk_final"


def _use_anonymizer(state: GuardState) -> bool:
    provider = (state.get("llm_provider") or "openai").strip().lower()
    return provider != "ollama"
