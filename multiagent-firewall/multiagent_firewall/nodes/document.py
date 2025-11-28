from __future__ import annotations

import os
import warnings
from urllib.parse import urlparse, unquote

from ..detectors import TesseractOCRDetector
from ..types import GuardState, FieldList
from ..utils import append_error, append_warning

# Supported image file extensions for automatic OCR detection
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif", ".webp"}


def sanitize_file_path(file_path: str) -> str:
    """
    Sanitize file path by decoding file:// URLs and handling platform differences.
    """
    if file_path.startswith("file://"):
        parsed_path = urlparse(file_path).path
        parsed_path = unquote(parsed_path)
        if os.name == "nt":
            # Windows: remove leading slash from /C:/path
            parsed_path = parsed_path.lstrip("/")
        return parsed_path
    return file_path


def is_image_file(file_path: str) -> bool:
    """
    Check if file is an image based on extension.
    """
    _, ext = os.path.splitext(file_path)
    return ext.lower() in IMAGE_EXTENSIONS


def read_pdf(file_path: str) -> str | None:
    """
    Extract text from PDF file using pdfplumber.
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
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


def extract_text_from_file(file_path: str) -> str | None:
    """
    Extract text from file based on extension.
    """
    try:
        file_path = sanitize_file_path(file_path)

        if not os.path.exists(file_path):
            return None

        if file_path.lower().endswith(".pdf"):
            return read_pdf(file_path)
        else:
            # Try as plain text for all other formats
            return read_text_file(file_path)
    except Exception:
        return None


def extract_text_from_ocr_fields(ocr_fields: FieldList) -> str:
    """
    Extract text from OCR fields to populate raw_text.
    """
    if not ocr_fields:
        return ""

    text_parts = []
    for field in ocr_fields:
        if isinstance(field, dict) and field.get("value"):
            text_parts.append(str(field["value"]))

    return " ".join(text_parts)


def _get_default_ocr_detector():
    """
    Get default OCR detector from environment.

    Returns None if Tesseract is not available or fails to initialize.
    """
    try:
        # TODO: Same as LiteLLM, pass this arguments as parameters to the package instead of loading from env
        return TesseractOCRDetector.from_env()
    except Exception as e:
        # Log warning but don't crash
        warnings.warn(
            f"Failed to initialize OCR detector: {e}. "
            "Image text extraction won't be executed. Install Tesseract.",
            RuntimeWarning,
        )
        return None


def read_document(state: GuardState) -> GuardState:
    """
    Document ingestion node: Extracts text from file if file_path provided.

    - For images: Run OCR detector if available
    - For PDFs: Extract text using pdfplumber
    - For other files: Read as plain text
    """
    # Get file_path if provided
    file_path = state.get("file_path")

    # Sanitize and validate file path
    try:
        assert isinstance(file_path, str), "file_path must be a string"
        file_path_clean = sanitize_file_path(file_path)

        if not os.path.exists(file_path_clean):
            append_error(state, f"File not found: {file_path}")
            state["raw_text"] = ""
            return state

        # Detect file type and handle accordingly
        if is_image_file(file_path_clean):
            # Handle image files with OCR
            if "metadata" not in state:
                state["metadata"] = {}
            state["metadata"]["file_type"] = "image"

            ocr_detector = _get_default_ocr_detector()
            if ocr_detector:
                try:
                    # Call OCR detector with current state
                    ocr_fields = ocr_detector(state) or []
                    state["ocr_fields"] = ocr_fields

                    # Extract text from OCR results
                    text = extract_text_from_ocr_fields(ocr_fields)
                    state["raw_text"] = text

                    if not text:
                        append_warning(
                            state, f"No text extracted from image: {file_path}"
                        )
                except Exception as e:
                    append_error(state, f"OCR detection failed: {str(e)}")
                    state["raw_text"] = ""
                    state["ocr_fields"] = []
            else:
                append_warning(
                    state,
                    f"Image file detected but no OCR detector available: {file_path}",
                )
                state["raw_text"] = ""
                state["ocr_fields"] = []
        else:
            # Handle PDF and text files
            text = extract_text_from_file(file_path_clean)

            if text is None:
                append_error(state, f"Failed to extract text from file: {file_path}")
                state["raw_text"] = ""
            else:
                state["raw_text"] = text

            # Set file type metadata
            if "metadata" not in state:
                state["metadata"] = {}
            if file_path_clean.lower().endswith(".pdf"):
                state["metadata"]["file_type"] = "pdf"
            else:
                state["metadata"]["file_type"] = "text"

    except Exception as e:
        append_error(state, f"Document extraction error: {str(e)}")
        state["raw_text"] = ""

    return state


__all__ = [
    "read_document",
    "sanitize_file_path",
    "extract_text_from_file",
    "is_image_file",
]
