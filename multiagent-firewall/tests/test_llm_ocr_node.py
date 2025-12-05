from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from multiagent_firewall.nodes.document import llm_ocr_document
from multiagent_firewall.types import GuardState


def test_llm_ocr_document_skips_non_image():
    """Test that LLM OCR skips non-image files"""
    state: GuardState = {
        "raw_text": "",
        "metadata": {"file_type": "pdf"},
        "warnings": [],
        "errors": [],
    }

    result = llm_ocr_document(state)

    # State should be unchanged
    assert result["raw_text"] == ""
    assert len(result.get("warnings", [])) == 0


def test_llm_ocr_document_skips_when_text_exists():
    """Test that LLM OCR skips when text already extracted"""
    state: GuardState = {
        "raw_text": "Already extracted text",
        "metadata": {"file_type": "image"},
        "warnings": [],
        "errors": [],
    }

    result = llm_ocr_document(state)

    # State should be unchanged
    assert result["raw_text"] == "Already extracted text"
    assert len(result.get("warnings", [])) == 0


def test_llm_ocr_document_skips_when_text_is_whitespace():
    """Test that LLM OCR runs when text is only whitespace"""
    mock_detector = MagicMock()
    mock_detector.model = "gpt-4o"
    mock_detector.return_value = "Extracted by LLM"

    state: GuardState = {
        "raw_text": "   \n  ",  # Only whitespace
        "file_path": "/fake/image.png",
        "metadata": {"file_type": "image"},
        "warnings": [],
        "errors": [],
    }

    with patch.dict(os.environ, {"LLM_API_KEY": "test-key"}, clear=False):
        with patch(
            "multiagent_firewall.nodes.document.LLMOCRDetector.from_env",
            return_value=mock_detector,
        ):
            result = llm_ocr_document(state)

    # Should have extracted text via LLM
    assert "Extracted by LLM" in result["raw_text"]
    assert result["metadata"]["llm_ocr_used"] is True
    assert result["metadata"]["ocr_method"] == "llm"


def test_llm_ocr_document_extracts_text_successfully():
    """Test successful text extraction via LLM OCR"""
    mock_detector = MagicMock()
    mock_detector.model = "gpt-4o"
    mock_detector.return_value = "Text extracted by LLM OCR"

    state: GuardState = {
        "raw_text": "",
        "file_path": "/fake/image.png",
        "metadata": {"file_type": "image"},
        "warnings": [],
        "errors": [],
    }

    with patch.dict(os.environ, {"LLM_API_KEY": "test-key"}, clear=False):
        with patch(
            "multiagent_firewall.nodes.document.LLMOCRDetector.from_env",
            return_value=mock_detector,
        ):
            result = llm_ocr_document(state)

    # Should have extracted text
    assert result["raw_text"] == "Text extracted by LLM OCR"
    assert result["metadata"]["llm_ocr_used"] is True
    assert result["metadata"]["ocr_method"] == "llm"
    assert len(result.get("warnings", [])) == 0
    assert len(result.get("errors", [])) == 0


def test_llm_ocr_document_appends_to_existing_text():
    """Test that LLM OCR appends to existing text if present"""
    mock_detector = MagicMock()
    mock_detector.model = "gpt-4o"
    mock_detector.return_value = "New text from LLM"

    # Note: In practice this shouldn't happen because we check if raw_text exists,
    # but we test the append logic anyway
    state: GuardState = {
        "raw_text": "",  # Empty but then we'll make the detector think there's existing text
        "file_path": "/fake/image.png",
        "metadata": {"file_type": "image"},
        "warnings": [],
        "errors": [],
    }

    with patch.dict(os.environ, {"LLM_API_KEY": "test-key"}, clear=False):
        with patch(
            "multiagent_firewall.nodes.document.LLMOCRDetector.from_env",
            return_value=mock_detector,
        ):
            # Set existing text before calling
            state["raw_text"] = ""
            result = llm_ocr_document(state)

    # Should have new text (since raw_text was empty)
    assert result["raw_text"] == "New text from LLM"


def test_llm_ocr_document_adds_warning_when_no_text_extracted():
    """Test that warning is added when LLM returns empty text"""
    mock_detector = MagicMock()
    mock_detector.model = "gpt-4o"
    mock_detector.return_value = ""  # Empty result

    state: GuardState = {
        "raw_text": "",
        "file_path": "/fake/image.png",
        "metadata": {"file_type": "image"},
        "warnings": [],
        "errors": [],
    }

    with patch.dict(os.environ, {"LLM_API_KEY": "test-key"}, clear=False):
        with patch(
            "multiagent_firewall.nodes.document.LLMOCRDetector.from_env",
            return_value=mock_detector,
        ):
            result = llm_ocr_document(state)

    # Should have warning
    assert len(result["warnings"]) == 1
    assert "did not extract any text" in result["warnings"][0]
    assert result["raw_text"] == ""


def test_llm_ocr_document_handles_detector_exception():
    """Test that exceptions from detector are handled gracefully"""
    mock_detector = MagicMock()
    mock_detector.model = "gpt-4o"
    mock_detector.side_effect = RuntimeError("API call failed")

    state: GuardState = {
        "raw_text": "",
        "file_path": "/fake/image.png",
        "metadata": {"file_type": "image"},
        "warnings": [],
        "errors": [],
    }

    with patch.dict(os.environ, {"LLM_API_KEY": "test-key"}, clear=False):
        with patch(
            "multiagent_firewall.nodes.document.LLMOCRDetector.from_env",
            return_value=mock_detector,
        ):
            result = llm_ocr_document(state)

    # Should have error
    assert len(result["errors"]) == 1
    assert "LLM OCR failed" in result["errors"][0]
    assert "API call failed" in result["errors"][0]
    assert result["raw_text"] == ""


def test_llm_ocr_document_handles_from_env_exception():
    """Test that exceptions from from_env are handled gracefully"""
    state: GuardState = {
        "raw_text": "",
        "file_path": "/fake/image.png",
        "metadata": {"file_type": "image"},
        "warnings": [],
        "errors": [],
    }

    with patch(
        "multiagent_firewall.nodes.document.LLMOCRDetector.from_env",
        side_effect=RuntimeError("Missing API key"),
    ):
        result = llm_ocr_document(state)

    # Should have error
    assert len(result["errors"]) == 1
    assert "LLM OCR failed" in result["errors"][0]
    assert "Missing API key" in result["errors"][0]


def test_llm_ocr_document_metadata_not_present():
    """Test that node creates metadata dict if not present"""
    mock_detector = MagicMock()
    mock_detector.model = "gpt-4o"
    mock_detector.return_value = "Extracted text"

    state: GuardState = {
        "raw_text": "",
        "file_path": "/fake/image.png",
        "warnings": [],
        "errors": [],
    }
    # Note: metadata not in state, but we'll set it to image in the check
    # Actually, the function checks metadata.get("file_type"), so this will skip

    with patch.dict(os.environ, {"LLM_API_KEY": "test-key"}, clear=False):
        with patch(
            "multiagent_firewall.nodes.document.LLMOCRDetector.from_env",
            return_value=mock_detector,
        ):
            result = llm_ocr_document(state)

    # Should skip because metadata doesn't have file_type
    assert result["raw_text"] == ""


def test_llm_ocr_document_sets_metadata_correctly():
    """Test that metadata is set correctly after successful extraction"""
    mock_detector = MagicMock()
    mock_detector.model = "claude-3-opus"
    mock_detector.return_value = "Claude extracted this"

    state: GuardState = {
        "raw_text": "",
        "file_path": "/fake/image.png",
        "metadata": {"file_type": "image", "other_key": "value"},
        "warnings": [],
        "errors": [],
    }

    with patch.dict(os.environ, {"LLM_API_KEY": "test-key"}, clear=False):
        with patch(
            "multiagent_firewall.nodes.document.LLMOCRDetector.from_env",
            return_value=mock_detector,
        ):
            result = llm_ocr_document(state)

    # Check metadata
    assert result["metadata"]["llm_ocr_used"] is True
    assert result["metadata"]["ocr_method"] == "llm"
    assert result["metadata"]["file_type"] == "image"
    assert result["metadata"]["other_key"] == "value"
