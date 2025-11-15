import os
from pathlib import Path

from core.config import DETECTION_MODE

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PROMPT_DIR = BASE_DIR / "prompts"
PROMPT_DIR = Path(os.getenv("PROMPT_DIR", str(DEFAULT_PROMPT_DIR)))

PROMPT_MAP = {
    "zero-shot": "zero-shot.txt",
    "enriched-zero-shot": "enriched-zero-shot.txt",
    "few-shot": "few-shot.txt",
}

_FALLBACK_PROMPT_MODE = "zero-shot"


def resolve_mode(mode: str | None) -> str:
    candidate = (mode or DETECTION_MODE or "").strip()
    if not candidate:
        return _FALLBACK_PROMPT_MODE
    if candidate in PROMPT_MAP:
        return candidate
    return _FALLBACK_PROMPT_MODE


def load_prompt(mode: str | None) -> str:
    resolved = resolve_mode(mode)
    filename = PROMPT_MAP[resolved]
    path = PROMPT_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").strip()


def inject_text(template: str, text: str) -> str:
    if "{text}" in template:
        return template.replace("{text}", text)
    return f"{template.rstrip()}\n\nText:\n'''{text}'''"
