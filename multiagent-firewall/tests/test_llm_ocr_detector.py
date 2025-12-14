from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from multiagent_firewall.detectors.ocr import LLMOCRDetector
from multiagent_firewall.types import GuardState
from multiagent_firewall.detectors.utils import build_litellm_model_string


def test_llm_ocr_detector_initialization():
    """Test basic initialization with default parameters"""
    detector = LLMOCRDetector(
        provider="openai", model="gpt-4o", client_params={"api_key": "test-key"}
    )

    assert detector.provider == "openai"
    assert detector.model == "gpt-4o"


def test_llm_ocr_detector_custom_parameters():
    """Test initialization with custom parameters"""
    detector = LLMOCRDetector(
        provider="anthropic",
        model="claude-3-5-sonnet-20241022",
        client_params={
            "api_key": "sk-ant-test",
            "api_base": "https://api.anthropic.com",
        },
    )

    assert detector.provider == "anthropic"
    assert detector.model == "claude-3-5-sonnet-20241022"


def test_llm_ocr_detector_build_model_string_openai():
    """Test model string building for OpenAI (no prefix)"""
    assert build_litellm_model_string("gpt-4o", "openai") == "gpt-4o"


def test_llm_ocr_detector_build_model_string_with_prefix():
    """Test model string building for non-OpenAI providers"""
    assert build_litellm_model_string("claude-3-opus", "anthropic") == "anthropic/claude-3-opus"


def test_llm_ocr_detector_build_model_string_already_prefixed():
    """Test model string when already prefixed"""
    assert build_litellm_model_string("anthropic/claude-3-opus", "anthropic") == "anthropic/claude-3-opus"


def test_llm_ocr_detector_returns_empty_for_missing_file_path():
    """Test detector returns empty string when file_path is not in state"""
    mock_llm = MagicMock()

    with patch("langchain_litellm.ChatLiteLLM", return_value=mock_llm):
        detector = LLMOCRDetector(
            provider="openai", model="gpt-4o", client_params={"api_key": "test-key"}
        )
        state: GuardState = {}

        result = detector(state)
        assert result == ""


def test_llm_ocr_detector_returns_empty_for_nonexistent_file():
    """Test detector returns empty string when file doesn't exist"""
    mock_llm = MagicMock()

    with patch("langchain_litellm.ChatLiteLLM", return_value=mock_llm):
        detector = LLMOCRDetector(
            provider="openai", model="gpt-4o", client_params={"api_key": "test-key"}
        )
        state: GuardState = {"file_path": "/nonexistent/path/image.png"}

        result = detector(state)
        assert result == ""


def test_llm_ocr_detector_extracts_text():
    """Test successful text extraction from image"""
    # Create a temporary image file
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(b"fake image data")

    try:
        # Mock the LLM response
        mock_response = MagicMock()
        mock_response.content = "Extracted text from image"

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response

        with patch(
            "langchain_litellm.ChatLiteLLM", return_value=mock_llm
        ):
            detector = LLMOCRDetector(
                provider="openai", model="gpt-4o", client_params={"api_key": "test-key"}
            )
            state: GuardState = {"file_path": tmp_path}

            result = detector(state)

            assert result == "Extracted text from image"
            assert mock_llm.invoke.called
    finally:
        os.unlink(tmp_path)


def test_llm_ocr_detector_handles_response_without_content_attr():
    """Test handling response that doesn't have content attribute"""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(b"fake image data")

    try:
        # Mock response without content attribute
        mock_response = "Plain string response"

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response

        with patch(
            "langchain_litellm.ChatLiteLLM", return_value=mock_llm
        ):
            detector = LLMOCRDetector(
                provider="openai", model="gpt-4o", client_params={"api_key": "test-key"}
            )
            state: GuardState = {"file_path": tmp_path}

            result = detector(state)

            assert result == "Plain string response"
    finally:
        os.unlink(tmp_path)


def test_llm_ocr_detector_handles_non_string_content():
    """Test handling response with non-string content"""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(b"fake image data")

    try:
        # Mock response with list content (multimodal response)
        mock_response = MagicMock()
        mock_response.content = [{"type": "text", "text": "some text"}]

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response

        with patch(
            "langchain_litellm.ChatLiteLLM", return_value=mock_llm
        ):
            detector = LLMOCRDetector(
                provider="openai", model="gpt-4o", client_params={"api_key": "test-key"}
            )
            state: GuardState = {"file_path": tmp_path}

            result = detector(state)

            # Should return empty string when content is not string
            assert result == ""
    finally:
        os.unlink(tmp_path)


def test_llm_ocr_detector_raises_on_processing_error():
    """Test that processing errors are raised"""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(b"fake image data")

    try:
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = RuntimeError("API call failed")

        with patch(
            "langchain_litellm.ChatLiteLLM", return_value=mock_llm
        ):
            detector = LLMOCRDetector(
                provider="openai", model="gpt-4o", client_params={"api_key": "test-key"}
            )
            state: GuardState = {"file_path": tmp_path}

            with pytest.raises(RuntimeError, match="LLM OCR failed to process image"):
                detector(state)
    finally:
        os.unlink(tmp_path)


def test_llm_ocr_detector_encodes_image_as_base64():
    """Test that image is properly encoded as base64 data URL"""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(b"test image content")

    try:
        mock_response = MagicMock()
        mock_response.content = "Text from image"

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response

        with patch(
            "langchain_litellm.ChatLiteLLM", return_value=mock_llm
        ):
            detector = LLMOCRDetector(
                provider="openai", model="gpt-4o", client_params={"api_key": "test-key"}
            )
            state: GuardState = {"file_path": tmp_path}

            result = detector(state)

            # Verify the invoke was called with proper message structure
            assert mock_llm.invoke.called
            messages = mock_llm.invoke.call_args[0][0]
            assert len(messages) == 2
            system_msg, human_msg = messages
            assert "Extract all visible text" in system_msg.content

            assert hasattr(human_msg, "content")
            content = human_msg.content
            assert len(content) == 1
            assert content[0]["type"] == "image_url"
            assert "data:image/png;base64," in content[0]["image_url"]["url"]

            assert result == "Text from image"
    finally:
        os.unlink(tmp_path)


def test_llm_ocr_detector_handles_different_image_types():
    """Test handling different image MIME types recognized by Python's mimetypes module"""
    # Test with commonly recognized formats
    for ext, mime_type in [(".jpg", "image/jpeg"), (".png", "image/png"), (".gif", "image/gif")]:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp_path = tmp.name
            tmp.write(b"test image")

        try:
            mock_response = MagicMock()
            mock_response.content = "Text"

            mock_llm = MagicMock()
            mock_llm.invoke.return_value = mock_response

            with patch(
                "langchain_litellm.ChatLiteLLM", return_value=mock_llm
            ):
                detector = LLMOCRDetector(
                    provider="openai", model="gpt-4o", client_params={"api_key": "test-key"}
                )
                state: GuardState = {"file_path": tmp_path}

                result = detector(state)

                # Check that proper MIME type was used
                messages = mock_llm.invoke.call_args[0][0]
                image_url = messages[1].content[0]["image_url"]["url"]
                assert f"data:{mime_type};base64," in image_url

                assert result == "Text"
        finally:
            os.unlink(tmp_path)


def test_llm_ocr_detector_handles_unknown_image_type():
    """Test that unknown image types fall back to image/jpeg"""
    # Use a fake extension that Python won't recognize
    with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(b"test image")

    try:
        mock_response = MagicMock()
        mock_response.content = "Text"

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response

        with patch(
            "langchain_litellm.ChatLiteLLM", return_value=mock_llm
        ):
            detector = LLMOCRDetector(
                provider="openai", model="gpt-4o", client_params={"api_key": "test-key"}
            )
            state: GuardState = {"file_path": tmp_path}

            result = detector(state)

            # Check that fallback MIME type was used
            messages = mock_llm.invoke.call_args[0][0]
            image_url = messages[1].content[0]["image_url"]["url"]
            assert "data:image/jpeg;base64," in image_url

            assert result == "Text"
    finally:
        os.unlink(tmp_path)
