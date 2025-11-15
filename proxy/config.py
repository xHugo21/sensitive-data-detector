import os
from dotenv import load_dotenv

load_dotenv()


def _parse_float(value: str | None, default: float) -> float:
    try:
        return float(value) if value is not None else default
    except ValueError:
        return default


def _parse_risk(value: str | None, default: str) -> str:
    allowed = {"none", "low", "medium", "high"}
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized not in allowed:
        return default
    return normalized


BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
BACKEND_DETECT_ENDPOINT = os.getenv("BACKEND_DETECT_ENDPOINT", "/detect")
BACKEND_TIMEOUT_SECONDS = _parse_float(os.getenv("BACKEND_TIMEOUT_SECONDS"), 10.0)

PROXY_MIN_BLOCK_RISK = _parse_risk(os.getenv("PROXY_MIN_BLOCK_RISK"), "low")
UPSTREAM_TIMEOUT_SECONDS = _parse_float(os.getenv("UPSTREAM_TIMEOUT_SECONDS"), 30.0)

OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com").rstrip("/")
COPILOT_API_BASE = os.getenv("COPILOT_API_BASE", "https://api.githubcopilot.com").rstrip("/")
GROQ_API_BASE = os.getenv("GROQ_API_BASE", "https://api.groq.com").rstrip("/")
