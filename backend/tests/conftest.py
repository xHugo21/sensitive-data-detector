import os

# Ensure required LLM env vars exist so GuardConfig.from_env() succeeds in CI
os.environ.setdefault("LLM_PROVIDER", "openai")
os.environ.setdefault("LLM_MODEL", "gpt-4o-mini")
os.environ.setdefault("LLM_API_KEY", "test-api-key")
