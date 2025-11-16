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

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
DETECTION_MODE = os.getenv("DETECTION_MODE", "zero-shot").strip() or "zero-shot"


def _str_to_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


DEBUG_MODE = _str_to_bool(os.getenv("DEBUG_MODE"), False)

LLM_SUPPORTS_JSON_MODE = _str_to_bool(
    os.getenv("LLM_SUPPORTS_JSON_MODE"),
    LLM_PROVIDER in {"openai", "groq"},
)
