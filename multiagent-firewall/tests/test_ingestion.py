from __future__ import annotations

import os
import pytest
from pathlib import Path

from multiagent_firewall.nodes.ingestion import (
    read_document,
    sanitize_file_path,
    extract_text_from_file,
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

    import multiagent_firewall.nodes.ingestion as ingestion_module
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
    assert "Failed to extract text" in result["errors"][0]


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
