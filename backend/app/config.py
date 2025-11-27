import os
from dotenv import load_dotenv

load_dotenv()

PORT = int(os.getenv("PORT", "8000"))

ALLOW_ORIGINS = [
    "https://chatgpt.com",
    "https://chat.openai.com",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

def _str_to_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


DEBUG_MODE = _str_to_bool(os.getenv("DEBUG_MODE"), False)


def _parse_risk(value: str | None, default: str) -> str:
    allowed = {"low", "medium", "high"}
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized not in allowed:
        return default
    return normalized


MIN_BLOCK_RISK = _parse_risk(os.getenv("MIN_BLOCK_RISK"), "medium")
