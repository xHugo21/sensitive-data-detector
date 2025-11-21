import re
import json
from app.services.llm_client import client
from app.utils.prompt_loader import load_prompt, inject_text, PROMPT_MAP, resolve_mode
from app.core.config import (
    LLM_MODEL,
    LLM_PROVIDER,
    LLM_SUPPORTS_JSON_MODE,
)

def safe_json_from_text(s: str) -> dict:
    if not s:
        return {}
    m = re.search(r"\{.*\}", s, re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {}

def detect_sensitive_data(
    text: str,
    prompt: str | None = None,
    mode: str | None = None,
):
    try:
        mode_to_use = resolve_mode(mode)
        if prompt and prompt.strip():
            final_prompt = inject_text(prompt.strip(), text)
            prompt_info = "custom"
        else:
            template = load_prompt(mode_to_use)
            final_prompt = inject_text(template, text)
            prompt_filename = PROMPT_MAP[mode_to_use]
            prompt_info = f"prompts/{prompt_filename}"

        sys_msg = "You are to output a single valid JSON object only. No prose, no markdown."

        supports_json_mode = LLM_SUPPORTS_JSON_MODE

        try:
            if supports_json_mode:
                resp = client.chat.completions.create(
                    model=LLM_MODEL,
                    messages=[
                        {"role": "system", "content": sys_msg},
                        {"role": "user", "content": final_prompt},
                    ],
                    temperature=0,
                    max_tokens=1500,
                    response_format={"type": "json_object"},
                )
            else:
                resp = client.chat.completions.create(
                    model=LLM_MODEL,
                    messages=[
                        {"role": "system", "content": sys_msg},
                        {"role": "user", "content": final_prompt},
                    ],
                    temperature=0,
                    max_tokens=1500,
                )
            content = (resp.choices[0].message.content or "").strip()
        except Exception:
            resp = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": "Devuelve únicamente un objeto JSON válido. Sin texto adicional."},
                    {"role": "user", "content": final_prompt},
                ],
                temperature=0,
                max_tokens=1500,
            )
            content = (resp.choices[0].message.content or "").strip()

        result = safe_json_from_text(content) or {"detected_fields": []}
        if "detected_fields" not in result or not isinstance(result["detected_fields"], list):
            result["detected_fields"] = []
        result["_prompt_source"] = prompt_info
        result["_model_used"] = LLM_MODEL
        result["_provider"] = LLM_PROVIDER
        return result
    except Exception as e:
        return {"detected_fields": [], "risk_level": "Unknown", "_error": str(e)}
