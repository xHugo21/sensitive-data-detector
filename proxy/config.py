import os
from dotenv import load_dotenv

load_dotenv()


def _parse_float(value: str | None, default: float) -> float:
    try:
        return float(value) if value is not None else default
    except ValueError:
        return default


def _parse_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
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


def _parse_list(value: str | None, default: list[str]) -> list[str]:
    if value is None or not value.strip():
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
BACKEND_DETECT_ENDPOINT = os.getenv("BACKEND_DETECT_ENDPOINT", "/detect")
BACKEND_TIMEOUT_SECONDS = _parse_float(os.getenv("BACKEND_TIMEOUT_SECONDS"), 10.0)
BACKEND_DETECTION_MODE = os.getenv("BACKEND_DETECTION_MODE", "").strip()

PROXY_HOST = os.getenv("PROXY_HOST", "127.0.0.1")
PROXY_PORT = _parse_int(os.getenv("PROXY_PORT"), 8080)
PROXY_MIN_BLOCK_RISK = _parse_risk(os.getenv("PROXY_MIN_BLOCK_RISK"), "low")

INTERCEPTED_HOSTS = _parse_list(
    os.getenv("INTERCEPTED_HOSTS"),
    [
        "api.openai.com",
        "api.githubcopilot.com",
        "api.groq.com",
    ],
)

INTERCEPTED_PATHS = _parse_list(
    os.getenv("INTERCEPTED_PATHS"),
    [
        "/v1/chat/completions",
        "/v1/completions",
        "/v1/engines/",
    ],
)
