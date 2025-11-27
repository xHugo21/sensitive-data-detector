from __future__ import annotations

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from multiagent_firewall.nodes.document import (
    read_document,
    sanitize_file_path,
    extract_text_from_file,
    is_image_file,
)
from multiagent_firewall.types import GuardState


def test_sanitize_file_path_decodes_file_uri():
    raw = "file:///tmp/some%20folder/some%20file.txt"
    sanitized = sanitize_file_path(raw)
    assert sanitized.endswith("some file.txt")
    if os.name != "nt":
        assert sanitized == "/tmp/some folder/some file.txt"


def test_sanitize_file_path_handles_regular_path():
    raw = "/tmp/regular/path.txt"
    sanitized = sanitize_file_path(raw)
    assert sanitized == "/tmp/regular/path.txt"


def test_extract_text_from_file_returns_none_for_missing_file(tmp_path):
    missing_path = tmp_path / "missing.txt"
    assert extract_text_from_file(str(missing_path)) is None


def test_extract_text_from_file_reads_plain_text(tmp_path):
    file_path = tmp_path / "doc.txt"
    file_path.write_text("line one\nline two", encoding="utf-8")
    result = extract_text_from_file(str(file_path))
    assert result == "line one\nline two"


def test_extract_text_from_file_reads_pdf(monkeypatch, tmp_path):
    """Test PDF extraction using pdfplumber"""
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(b"%PDF-FAKE")

    class FakePage:
        def __init__(self, text):
            self._text = text

        def extract_text(self):
            return self._text

    class FakePdf:
        def __init__(self):
            self.pages = [
                FakePage("First page"),
                FakePage(None),
                FakePage("Second page"),
            ]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_open(path):
        assert path == str(pdf_path)
        return FakePdf()

    import multiagent_firewall.nodes.document as document_module
    import pdfplumber

    monkeypatch.setattr(pdfplumber, "open", fake_open)

    content = extract_text_from_file(str(pdf_path))
    assert content == "First page\nSecond page"


def test_read_document_with_text_input():
    """If raw_text is provided, skip file extraction"""
    state: GuardState = {
        "raw_text": "existing text",
        "warnings": [],
        "errors": [],
    }
    result = read_document(state)

    assert result["raw_text"] == "existing text"
    assert len(result.get("warnings", [])) == 0


def test_read_document_with_no_input():
    """If neither text nor file provided, set empty string with warning"""
    state: GuardState = {
        "warnings": [],
        "errors": [],
    }
    result = read_document(state)

    assert result["raw_text"] == ""
    assert "No text or file provided" in result["warnings"][0]


def test_read_document_with_file_path(tmp_path):
    """Extract text from file when file_path provided"""
    file_path = tmp_path / "test.txt"
    file_path.write_text("file content", encoding="utf-8")

    state: GuardState = {
        "file_path": str(file_path),
        "warnings": [],
        "errors": [],
    }
    result = read_document(state)

    assert result["raw_text"] == "file content"
    assert len(result.get("errors", [])) == 0


def test_read_document_with_missing_file(tmp_path):
    """Handle missing file gracefully"""
    missing_path = tmp_path / "missing.txt"

    state: GuardState = {
        "file_path": str(missing_path),
        "warnings": [],
        "errors": [],
    }
    result = read_document(state)

    assert result["raw_text"] == ""
    assert len(result["errors"]) > 0
    assert "File not found" in result["errors"][0]


def test_read_document_text_takes_precedence_over_file(tmp_path):
    """If both text and file provided, text takes precedence"""
    file_path = tmp_path / "test.txt"
    file_path.write_text("file content", encoding="utf-8")

    state: GuardState = {
        "raw_text": "direct text",
        "file_path": str(file_path),
        "warnings": [],
        "errors": [],
    }
    result = read_document(state)

    assert result["raw_text"] == "direct text"


def test_is_image_file_detects_png():
    assert is_image_file("photo.png") == True
    assert is_image_file("PHOTO.PNG") == True


def test_is_image_file_detects_jpg():
    assert is_image_file("photo.jpg") == True
    assert is_image_file("photo.jpeg") == True
    assert is_image_file("PHOTO.JPG") == True


def test_is_image_file_rejects_non_images():
    assert is_image_file("document.pdf") == False
    assert is_image_file("text.txt") == False
    assert is_image_file("data.csv") == False


@patch('multiagent_firewall.nodes.document.TesseractOCRDetector.from_env')
def test_read_document_with_image_file_and_ocr_detector(mock_ocr_from_env, tmp_path):
    """Test reading image file with OCR detector"""
    image_path = tmp_path / "screenshot.png"
    image_path.write_bytes(b"fake image data")

    mock_detector = MagicMock()
    mock_detector.return_value = [
        {
            "field": "TEXT_IN_IMAGE",
            "value": "Some text from image",
            "source": "ocr",
        },
        {"field": "EMAIL", "value": "test@example.com", "source": "ocr"},
    ]
    mock_ocr_from_env.return_value = mock_detector

    state: GuardState = {
        "file_path": str(image_path),
        "warnings": [],
        "errors": [],
        "metadata": {},
    }

    result = read_document(state)

    assert result["raw_text"] == "Some text from image test@example.com"
    assert result.get("metadata", {}).get("file_type") == "image"
    assert "ocr_fields" in result
    assert len(result["ocr_fields"]) == 2


@patch('multiagent_firewall.nodes.document.TesseractOCRDetector.from_env')
def test_read_document_with_image_file_no_ocr_detector(mock_ocr_from_env, tmp_path):
    """Test reading image file when OCR detector fails to initialize"""
    image_path = tmp_path / "screenshot.jpg"
    image_path.write_bytes(b"fake image data")
    
    # Simulate OCR detector initialization failure
    mock_ocr_from_env.side_effect = RuntimeError("Tesseract not found")

    state: GuardState = {
        "file_path": str(image_path),
        "warnings": [],
        "errors": [],
        "metadata": {},
    }

    # The function should handle the missing detector gracefully
    with pytest.warns(RuntimeWarning, match="Failed to initialize OCR detector"):
        result = read_document(state)

    assert result["raw_text"] == ""
    assert "Image file detected but no OCR detector available" in result["warnings"][0]
    assert result.get("metadata", {}).get("file_type") == "image"
    assert result.get("ocr_fields") == []


def test_read_document_sets_file_type_metadata_for_pdf(tmp_path):
    pdf_path = tmp_path / "document.pdf"
    pdf_path.write_bytes(b"%PDF-fake")

    state: GuardState = {
        "file_path": str(pdf_path),
        "warnings": [],
        "errors": [],
        "metadata": {},
    }

    result = read_document(state)

    # Even if extraction fails, metadata should be set
    assert result.get("metadata", {}).get("file_type") == "pdf"


def test_read_document_sets_file_type_metadata_for_text(tmp_path):
    text_path = tmp_path / "document.txt"
    text_path.write_text("Some content", encoding="utf-8")

    state: GuardState = {
        "file_path": str(text_path),
        "warnings": [],
        "errors": [],
        "metadata": {},
    }

    result = read_document(state)

    assert result["raw_text"] == "Some content"
    assert result.get("metadata", {}).get("file_type") == "text"


@patch('multiagent_firewall.nodes.document.TesseractOCRDetector.from_env')
def test_read_document_handles_ocr_exception(mock_ocr_from_env, tmp_path):
    """Test handling OCR detector exceptions"""
    image_path = tmp_path / "bad_image.png"
    image_path.write_bytes(b"corrupt image")

    mock_detector = MagicMock()
    mock_detector.side_effect = RuntimeError("OCR service unavailable")
    mock_ocr_from_env.return_value = mock_detector

    state: GuardState = {
        "file_path": str(image_path),
        "warnings": [],
        "errors": [],
        "metadata": {},
    }

    result = read_document(state)

    assert result["raw_text"] == ""
    assert any("OCR detection failed" in e for e in result["errors"])
    assert result.get("ocr_fields") == []
