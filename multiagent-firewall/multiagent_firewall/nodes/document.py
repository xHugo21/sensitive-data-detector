from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse, unquote

from ..types import GuardState


def sanitize_file_path(file_path: str) -> str:
    """
    Sanitize file path by decoding file:// URLs and handling platform differences.
    
    Args:
        file_path: File path that may be a file:// URL or regular path
        
    Returns:
        Sanitized file path
    """
    if file_path.startswith("file://"):
        parsed_path = urlparse(file_path).path
        parsed_path = unquote(parsed_path)
        if os.name == "nt":
            # Windows: remove leading slash from /C:/path
            parsed_path = parsed_path.lstrip("/")
        return parsed_path
    return file_path


def read_pdf(file_path: str) -> str | None:
    """
    Extract text from PDF file using pdfplumber.
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        Extracted text or None if extraction fails
    """
    try:
        import pdfplumber
        
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                extracted_text = page.extract_text()
                if extracted_text:
                    text += extracted_text + "\n"
        return text.strip()
    except Exception:
        return None


def read_text_file(file_path: str) -> str | None:
    """
    Read plain text file.
    
    Args:
        file_path: Path to text file
        
    Returns:
        File contents or None if read fails
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


def extract_text_from_file(file_path: str) -> str | None:
    """
    Extract text from file based on extension.
    
    Args:
        file_path: Path to file
        
    Returns:
        Extracted text or None if extraction fails
    """
    try:
        file_path = sanitize_file_path(file_path)
        
        if not os.path.exists(file_path):
            return None
        
        # Check file extension
        if file_path.lower().endswith(".pdf"):
            return read_pdf(file_path)
        else:
            # Try as plain text for all other formats
            return read_text_file(file_path)
    except Exception:
        return None


def read_document(state: GuardState) -> GuardState:
    """
    Document ingestion node: Extracts text from file if file_path provided.
    
    Priority:
    1. If raw_text is already provided, use it (skip file extraction)
    2. If file_path provided, extract text from file
    3. If neither provided, set empty string with warning
    
    Args:
        state: Current guard state
        
    Returns:
        Updated state with raw_text populated
    """
    # If raw_text already provided, skip file extraction
    if state.get("raw_text"):
        return state
    
    # Get file_path if provided
    file_path = state.get("file_path")
    
    if not file_path:
        # No input provided
        state["raw_text"] = ""
        _append_warning(state, "No text or file provided for analysis")
        return state
    
    # Extract text from file
    try:
        text = extract_text_from_file(file_path)
        
        if text is None:
            _append_error(state, f"Failed to extract text from file: {file_path}")
            state["raw_text"] = ""
        else:
            state["raw_text"] = text
    except Exception as e:
        _append_error(state, f"Document extraction error: {str(e)}")
        state["raw_text"] = ""
    
    return state


def _append_warning(state: GuardState, message: str) -> None:
    """Add warning to state."""
    if "warnings" not in state:
        state["warnings"] = []
    state["warnings"].append(message)


def _append_error(state: GuardState, message: str) -> None:
    """Add error to state."""
    if "errors" not in state:
        state["errors"] = []
    state["errors"].append(message)


__all__ = ["read_document", "sanitize_file_path", "extract_text_from_file"]
