import os
from openai import OpenAI
from ..core.config import LLM_PROVIDER

def create_llm_client():
    provider = LLM_PROVIDER
    
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not found in environment")
        return OpenAI(api_key=api_key)
    
    elif provider == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY not found in environment")
        return OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1"
        )
    
    elif provider == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        return OpenAI(
            api_key="ollama",
            base_url=base_url
        )
    
    else:
        raise RuntimeError(f"Unsupported LLM_PROVIDER: {provider}. Use 'openai', 'groq', or 'ollama'")

client = create_llm_client()
