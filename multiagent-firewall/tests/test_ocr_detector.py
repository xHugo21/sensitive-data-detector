from __future__ import annotations

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from multiagent_firewall.detectors.ocr import TesseractOCRDetector
from multiagent_firewall.types import GuardState


def test_tesseract_detector_initialization():
    """Test basic initialization with default parameters"""
    detector = TesseractOCRDetector()
    
    assert detector.lang == 'eng'
    assert detector.config == ''
    assert detector.confidence_threshold == 0
    assert detector.tesseract_cmd is None


def test_tesseract_detector_custom_parameters():
    """Test initialization with custom parameters"""
    with patch.dict('sys.modules', {'pytesseract': MagicMock()}):
        detector = TesseractOCRDetector(
            lang='spa',
            config='--psm 6',
            confidence_threshold=70,
            tesseract_cmd='/usr/local/bin/tesseract'
        )
        
        assert detector.lang == 'spa'
        assert detector.config == '--psm 6'
        assert detector.confidence_threshold == 70
        assert detector.tesseract_cmd == '/usr/local/bin/tesseract'


def test_tesseract_detector_from_env_defaults():
    """Test from_env with default values"""
    with patch.dict(os.environ, {}, clear=False):
        detector = TesseractOCRDetector.from_env()
        
        assert detector.lang == 'eng'
        assert detector.config == ''
        assert detector.confidence_threshold == 0
        assert detector.tesseract_cmd is None


def test_tesseract_detector_from_env_custom():
    """Test from_env with custom environment variables"""
    env_vars = {
        'OCR_LANG': 'spa+eng',
        'OCR_CONFIG': '--psm 6 --oem 3',
        'OCR_CONFIDENCE_THRESHOLD': '75',
        'TESSERACT_CMD': '/custom/path/tesseract',
    }
    
    with patch.dict(os.environ, env_vars, clear=False):
        with patch.dict('sys.modules', {'pytesseract': MagicMock()}):
            detector = TesseractOCRDetector.from_env()
            
            assert detector.lang == 'spa+eng'
            assert detector.config == '--psm 6 --oem 3'
            assert detector.confidence_threshold == 75
            assert detector.tesseract_cmd == '/custom/path/tesseract'


def test_tesseract_detector_from_env_invalid_threshold():
    """Test from_env handles invalid threshold gracefully"""
    with patch.dict(os.environ, {'OCR_CONFIDENCE_THRESHOLD': 'invalid'}, clear=False):
        detector = TesseractOCRDetector.from_env()
        assert detector.confidence_threshold == 0  # Falls back to default


def test_tesseract_detector_from_env_threshold_clamping():
    """Test threshold is clamped between 0 and 100"""
    # Test upper bound
    with patch.dict(os.environ, {'OCR_CONFIDENCE_THRESHOLD': '200'}, clear=False):
        detector = TesseractOCRDetector.from_env()
        assert detector.confidence_threshold == 100
    
    # Test lower bound
    with patch.dict(os.environ, {'OCR_CONFIDENCE_THRESHOLD': '-50'}, clear=False):
        detector = TesseractOCRDetector.from_env()
        assert detector.confidence_threshold == 0


def test_tesseract_detector_returns_empty_for_missing_file_path():
    """Test detector returns empty string when file_path is not in state"""
    detector = TesseractOCRDetector()
    state: GuardState = {}
    
    result = detector(state)
    assert result == ""


def test_tesseract_detector_returns_empty_for_nonexistent_file():
    """Test detector returns empty string when file doesn't exist"""
    detector = TesseractOCRDetector()
    state: GuardState = {
        "file_path": "/nonexistent/path/image.png"
    }
    
    result = detector(state)
    assert result == ""


def test_tesseract_detector_extracts_text():
    """Test successful text extraction from image"""
    import tempfile
    
    # Create mocks
    mock_pytesseract = MagicMock()
    mock_pil = MagicMock()
    mock_image = MagicMock()
    
    # Setup PIL mock
    mock_pil.Image.open.return_value = mock_image
    
    # Mock Tesseract OCR data output
    mock_pytesseract.image_to_data.return_value = {
        'level': [1, 2, 3, 4, 5],
        'page_num': [1, 1, 1, 1, 1],
        'block_num': [0, 1, 1, 1, 1],
        'par_num': [0, 0, 1, 1, 1],
        'line_num': [0, 0, 0, 1, 2],
        'word_num': [0, 0, 0, 1, 1],
        'left': [0, 10, 20, 30, 40],
        'top': [0, 10, 20, 30, 40],
        'width': [100, 90, 80, 70, 60],
        'height': [50, 45, 40, 35, 30],
        'conf': ['-1', '-1', '-1', '95', '87'],
        'text': ['', '', '', 'Hello', 'World']
    }
    mock_pytesseract.Output.DICT = 'dict'
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        with patch.dict('sys.modules', {'pytesseract': mock_pytesseract, 'PIL': mock_pil}):
            detector = TesseractOCRDetector(confidence_threshold=50)
            state: GuardState = {"file_path": tmp_path}
            
            result = detector(state)
            
            # Should return plain text string with words separated by spaces
            assert result == "Hello World"
    finally:
        os.unlink(tmp_path)


def test_tesseract_detector_filters_by_confidence():
    """Test that low-confidence results are filtered out"""
    import tempfile
    
    mock_pytesseract = MagicMock()
    mock_pil = MagicMock()
    mock_image = MagicMock()
    
    mock_pil.Image.open.return_value = mock_image
    
    mock_pytesseract.image_to_data.return_value = {
        'level': [5, 5],
        'page_num': [1, 1],
        'block_num': [1, 1],
        'par_num': [1, 1],
        'line_num': [1, 1],
        'word_num': [1, 2],
        'left': [10, 20],
        'top': [10, 20],
        'width': [50, 50],
        'height': [20, 20],
        'conf': ['95', '30'],
        'text': ['HighConfidence', 'LowConfidence']
    }
    mock_pytesseract.Output.DICT = 'dict'
    
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        with patch.dict('sys.modules', {'pytesseract': mock_pytesseract, 'PIL': mock_pil}):
            detector = TesseractOCRDetector(confidence_threshold=50)
            state: GuardState = {"file_path": tmp_path}
            
            result = detector(state)
            
            # Only high confidence result should be included
            assert result == "HighConfidence"
    finally:
        os.unlink(tmp_path)


def test_tesseract_detector_skips_empty_text():
    """Test that empty or whitespace-only text is skipped"""
    import tempfile
    
    mock_pytesseract = MagicMock()
    mock_pil = MagicMock()
    mock_image = MagicMock()
    
    mock_pil.Image.open.return_value = mock_image
    
    mock_pytesseract.image_to_data.return_value = {
        'level': [5, 5, 5],
        'page_num': [1, 1, 1],
        'block_num': [1, 1, 1],
        'par_num': [1, 1, 1],
        'line_num': [1, 1, 1],
        'word_num': [1, 2, 3],
        'left': [10, 20, 30],
        'top': [10, 20, 30],
        'width': [50, 50, 50],
        'height': [20, 20, 20],
        'conf': ['95', '95', '95'],
        'text': ['ValidText', '   ', '']
    }
    mock_pytesseract.Output.DICT = 'dict'
    
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        with patch.dict('sys.modules', {'pytesseract': mock_pytesseract, 'PIL': mock_pil}):
            detector = TesseractOCRDetector()
            state: GuardState = {"file_path": tmp_path}
            
            result = detector(state)
            
            # Only valid text should be included
            assert result == "ValidText"
    finally:
        os.unlink(tmp_path)


def test_tesseract_detector_raises_on_processing_error():
    """Test that processing errors are raised"""
    import tempfile
    
    mock_pytesseract = MagicMock()
    mock_pil = MagicMock()
    mock_image = MagicMock()
    
    mock_pil.Image.open.return_value = mock_image
    mock_pytesseract.image_to_data.side_effect = RuntimeError("OCR processing failed")
    
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        with patch.dict('sys.modules', {'pytesseract': mock_pytesseract, 'PIL': mock_pil}):
            detector = TesseractOCRDetector()
            state: GuardState = {"file_path": tmp_path}
            
            with pytest.raises(RuntimeError, match="Tesseract OCR failed to process image"):
                detector(state)
    finally:
        os.unlink(tmp_path)
