import os
from pathlib import Path
from typing import Mapping

DEFAULT_PROMPT_DIR = Path(__file__).resolve().parent
PROMPT_DIR = Path(os.getenv("PROMPT_DIR", str(DEFAULT_PROMPT_DIR)))

PROMPT_MAP = {
    "zero-shot": "zero-shot.txt",
    "enriched-zero-shot": "enriched-zero-shot.txt",
    "few-shot": "few-shot.txt",
}

_FALLBACK_PROMPT_MODE = "zero-shot"
DETECTION_MODE = os.getenv("DETECTION_MODE", "zero-shot").strip() or "zero-shot"


def resolve_mode(mode: str | None) -> str:
    candidate = (mode or DETECTION_MODE or "").strip()
    if not candidate:
        return _FALLBACK_PROMPT_MODE
    if candidate in PROMPT_MAP:
        return candidate
    return _FALLBACK_PROMPT_MODE


def load_prompt(
    mode: str | None,
    prompt_dir: Path | None = None,
    prompt_map: Mapping[str, str] | None = None,
) -> str:
    mapping = prompt_map or PROMPT_MAP
    resolved = resolve_mode(mode)
    filename = mapping.get(resolved)
    if not filename:
        raise FileNotFoundError(f"Prompt mapping for mode '{resolved}' not found")
    path = (prompt_dir or PROMPT_DIR) / filename
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").strip()


def inject_text(template: str, text: str) -> str:
    if "{text}" in template:
        return template.replace("{text}", text)
    return f"{template.rstrip()}\n\nText:\n'''{text}'''"


__all__ = [
    "DETECTION_MODE",
    "PROMPT_DIR",
    "PROMPT_MAP",
    "inject_text",
    "load_prompt",
    "resolve_mode",
    "_FALLBACK_PROMPT_MODE",
]
