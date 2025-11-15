import os

# Ensure backend modules always see a value for the api key
os.environ.setdefault("LLM_API_KEY", "test-api-key")
