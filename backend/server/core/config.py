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
