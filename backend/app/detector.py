from multiagent_firewall import LiteLLMDetector

from app.core.risk import compute_risk_level
from app.services.document_reader import read_document

_llm_detector = LiteLLMDetector.from_env()

detect_sensitive_data = _llm_detector

__all__ = ["detect_sensitive_data", "compute_risk_level", "read_document"]
