from .llm import LiteLLMConfig, LiteLLMDetector
from .ocr import TesseractOCRDetector, LLMOCRDetector
from .types import DetectorResult, FieldList, LLMDetector, OCRDetector

__all__ = [
    "LiteLLMConfig",
    "LiteLLMDetector",
    "TesseractOCRDetector",
    "LLMOCRDetector",
    "DetectorResult",
    "FieldList",
    "LLMDetector",
    "OCRDetector",
]
