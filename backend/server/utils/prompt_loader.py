import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PROMPT_DIR = BASE_DIR / "prompts"
PROMPT_DIR = Path(os.getenv("PROMPT_DIR", str(DEFAULT_PROMPT_DIR)))

PROMPT_MAP = {
    "Zero-shot": "ZS_prompt.txt",
    "Zero-shot enriquecido": "ZS_enriquecido_prompt.txt",
    "Few-shot": "FS_prompt.txt",
}

def load_prompt(mode: str) -> str:
    if not mode:
        mode = "Few-shot"
    filename = PROMPT_MAP.get(mode, PROMPT_MAP["Few-shot"])
    path = PROMPT_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").strip()

def inject_text(template: str, text: str) -> str:
    if "{text}" in template:
        return template.replace("{text}", text)
    return f"{template.rstrip()}\n\nText:\n'''{text}'''"
