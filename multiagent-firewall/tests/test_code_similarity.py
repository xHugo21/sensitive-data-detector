from __future__ import annotations

import pytest
import textwrap
import time
from unittest.mock import patch, MagicMock
from pathlib import Path

from multiagent_firewall.detectors.code_similarity import (
    CodeSimilarityDetector,
    _looks_like_code,
    _extract_code_segments,
    CodeMatch,
)
from multiagent_firewall.nodes.detection import run_code_similarity_detector


# --- Tests for Helper Functions ---


def test_looks_like_code():
    """Test heuristic code detection."""
    # Strong code indicators
    assert _looks_like_code("def my_function():\n    return True")
    assert _looks_like_code("import os\nfrom pathlib import Path")
    assert _looks_like_code("class MyClass:\n    pass")
    assert _looks_like_code("function test() { return 0; }")
    assert _looks_like_code("#include <stdio.h>")
    assert _looks_like_code("public class Main { public static void main() {} }")

    # Non-code text
    assert not _looks_like_code("This is a plain english sentence.")
    assert not _looks_like_code("Here is a list of items:\n1. Apple\n2. Banana")
    assert not _looks_like_code("Simple configuration file\nkey=value\nfoo=bar")


def test_extract_code_segments_fenced():
    """Test extraction of fenced code blocks."""
    text = textwrap.dedent("""
        Here is some code:
        ```python
        def foo():
            pass
        ```
        And more code:
        ```
        var x = 1;
        ```
    """)
    # Use small min_length because test snippets are short
    segments = _extract_code_segments(text, min_length=5)
    assert len(segments) == 2
    assert "def foo():" in segments[0]
    assert "var x = 1;" in segments[1]


def test_extract_code_segments_indented():
    """Test extraction of indented code blocks."""
    text = textwrap.dedent("""
        Check this out:

            def indented_func():
                return "indented"

        That was code.
    """)
    segments = _extract_code_segments(text, min_length=5)
    assert len(segments) == 1
    assert "def indented_func():" in segments[0]


def test_extract_code_segments_heuristic():
    """Test heuristic extraction from mixed text."""
    # Use 2 spaces indentation to avoid triggering the indented block regex (4 spaces)
    text = textwrap.dedent("""
        Below is a function without fences.

        function calculate(a, b) {
          return a + b;
        }

        End of example.
    """)
    segments = _extract_code_segments(text, min_length=5)
    assert len(segments) == 1
    assert "function calculate(a, b)" in segments[0]
    assert "return a + b;" in segments[0]


# --- Tests for CodeSimilarityDetector ---


@pytest.fixture
def mock_git_repo():
    # Use create=True because Repo might not be imported if git is missing
    with patch(
        "multiagent_firewall.detectors.code_similarity.Repo", create=True
    ) as mock:
        yield mock


@pytest.fixture
def mock_detector_init(mock_git_repo):
    """Fixture to initialize detector with mocked dependencies."""
    with (
        patch("multiagent_firewall.detectors.code_similarity.GIT_AVAILABLE", True),
        patch(
            "multiagent_firewall.detectors.code_similarity.RAPIDFUZZ_AVAILABLE", True
        ),
    ):
        detector = CodeSimilarityDetector(
            repo_urls=["https://github.com/test/repo.git"],
            cache_dir="/tmp/cache",
            refresh_interval=3600,
            min_snippet_length=10,  # Set small length for tests
        )
        return detector


def test_detector_initialization_missing_deps():
    """Test initialization fails if dependencies are missing."""
    with patch("multiagent_firewall.detectors.code_similarity.GIT_AVAILABLE", False):
        with pytest.raises(ImportError, match="GitPython is required"):
            CodeSimilarityDetector(repo_urls=[])

    with (
        patch("multiagent_firewall.detectors.code_similarity.GIT_AVAILABLE", True),
        patch(
            "multiagent_firewall.detectors.code_similarity.RAPIDFUZZ_AVAILABLE", False
        ),
    ):
        with pytest.raises(ImportError, match="rapidfuzz is required"):
            CodeSimilarityDetector(repo_urls=[])


def test_should_index_file(mock_detector_init, tmp_path):
    """Test file filtering logic."""
    detector = mock_detector_init

    # Create dummy files for testing
    valid_file = tmp_path / "main.py"
    valid_file.write_text("print('hello')")

    ignored_dir_file = tmp_path / "node_modules" / "pkg" / "index.js"
    ignored_dir_file.parent.mkdir(parents=True, exist_ok=True)
    ignored_dir_file.write_text("console.log('hi')")

    ignored_ext_file = tmp_path / "README.md"
    ignored_ext_file.write_text("# Readme")

    # Valid file
    assert detector._should_index_file(valid_file)

    # Ignored directories
    assert not detector._should_index_file(ignored_dir_file)
    assert not detector._should_index_file(Path(".git/config"))

    # Ignored extensions
    assert not detector._should_index_file(ignored_ext_file)


def test_normalize_code(mock_detector_init):
    """Test code normalization."""
    detector = mock_detector_init
    code = """
    def func():
        # This is a comment
        x = 1
        
        # Another comment
        return x
    """
    normalized = detector._normalize_code(code)
    expected = "def func():\nx = 1\nreturn x"
    assert normalized == expected


@patch(
    "multiagent_firewall.detectors.code_similarity.CodeSimilarityDetector._ensure_repo"
)
@patch(
    "multiagent_firewall.detectors.code_similarity.CodeSimilarityDetector._build_index"
)
@patch("multiagent_firewall.detectors.code_similarity.fuzz", create=True)
def test_find_matches_in_repo(
    mock_fuzz, mock_build_index, mock_ensure_repo, mock_detector_init
):
    """Test finding matches in a repository."""
    detector = mock_detector_init
    repo_url = "https://github.com/test/repo.git"

    # Mock index
    # Note: min_snippet_length is set to 10 in mock_detector_init
    mock_index = MagicMock()
    mock_index.files = {"src/main.py": "def secret_function():\n    pass"}
    mock_index.last_updated = (
        time.time()
    )  # Ensure it is fresh so _build_index is not called
    detector._indexes[repo_url] = mock_index

    # Mock fuzz matching
    mock_fuzz.partial_ratio.return_value = 90.0  # High similarity match

    matches = detector._find_matches_in_repo(
        "def secret_function():", repo_url, "normalized_input"
    )

    assert len(matches) == 1
    assert matches[0].file_path == "src/main.py"
    assert matches[0].similarity == 90.0
    assert matches[0].repo_url == repo_url


@patch(
    "multiagent_firewall.detectors.code_similarity.CodeSimilarityDetector._find_all_matches"
)
def test_detect_returns_findings(mock_find_all_matches, mock_detector_init):
    """Test detect method returns formatted findings."""
    detector = mock_detector_init

    mock_match = CodeMatch(
        file_path="src/secret.py",
        similarity=95.0,
        matched_snippet="def secret():...",
        repo_url="https://github.com/test/repo.git",
    )
    mock_find_all_matches.return_value = [mock_match]

    findings = detector.detect("some code")

    assert len(findings) == 1
    finding = findings[0]
    assert finding["field"] == "PROPRIETARY_CODE"
    assert "src/secret.py" in finding["value"]
    assert finding["metadata"]["similarity"] == 95.0
    assert finding["sources"] == ["code_similarity:src/secret.py"]


# --- Tests for Node Wrapper ---


@pytest.fixture
def mock_fw_config():
    config = MagicMock()
    config.code_analysis.enabled = True
    config.code_analysis.repo_urls = ["https://github.com/test/repo.git"]
    config.code_analysis.auth_token = None
    config.code_analysis.similarity_threshold = 85.0
    config.code_analysis.refresh_interval = 3600
    config.code_analysis.cache_dir = None
    config.code_analysis.min_snippet_length = 10
    return config


@pytest.mark.asyncio
async def test_run_code_similarity_detector_disabled(mock_fw_config):
    """Test node returns empty list when disabled."""
    mock_fw_config.code_analysis.enabled = False
    state = {"raw_text": "code"}
    result = await run_code_similarity_detector(state, fw_config=mock_fw_config)
    assert result["code_similarity_fields"] == []


@pytest.mark.asyncio
async def test_run_code_similarity_detector_no_urls(mock_fw_config):
    """Test node returns empty list when no repo URLs configured."""
    mock_fw_config.code_analysis.repo_urls = []
    state = {"raw_text": "code"}
    result = await run_code_similarity_detector(state, fw_config=mock_fw_config)
    assert result["code_similarity_fields"] == []


@pytest.mark.asyncio
@patch("multiagent_firewall.nodes.detection.CodeSimilarityDetector")
async def test_run_code_similarity_detector_success(
    mock_detector_class, mock_fw_config
):
    """Test successful detection flow."""
    mock_instance = MagicMock()
    mock_instance.detect.return_value = [
        {"field": "PROPRIETARY_CODE", "value": "match"}
    ]
    mock_detector_class.return_value = mock_instance

    state = {"raw_text": "def secret_code(): pass"}
    result = await run_code_similarity_detector(state, fw_config=mock_fw_config)

    assert len(result["code_similarity_fields"]) == 1
    assert result["code_similarity_fields"][0]["value"] == "match"
    mock_detector_class.assert_called_once()


@pytest.mark.asyncio
@patch("multiagent_firewall.nodes.detection.CodeSimilarityDetector")
async def test_run_code_similarity_detector_exception(
    mock_detector_class, mock_fw_config
):
    """Test exception handling in node."""
    mock_detector_class.side_effect = Exception("Setup failed")

    state = {"raw_text": "code"}
    result = await run_code_similarity_detector(state, fw_config=mock_fw_config)

    assert result["code_similarity_fields"] == []
    assert "Code similarity detector failed: Setup failed" in result["errors"][0]
