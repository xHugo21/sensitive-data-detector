from collections import deque
import time
import requests
import json
import re
import os
from requests.exceptions import HTTPError, RequestException
from pathlib import Path

# Usa el prompt "PROMPTS/ZS_prompt.txt" por defecto; también permite cambiarlo por ENV
PROMPT_MODE = os.getenv("PROMPT_MODE", "ZS_enriquecido_prompt").strip()

# 🌐 Groq Configuración
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("Groq API key not found. Please set GROQ_API_KEY.")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "openai/gpt-oss-120b"

# 🔒 Límites CONFIGURABLES (pon aquí tus cuotas reales de pago desde la consola)
# Si NO defines estas variables, el script se basará principalmente en los headers 429 / Retry-After.
REQUESTS_PER_MINUTE = int(os.getenv("GROQ_RPM", "0"))        # 0 = desactivar control local de RPM
TOKENS_PER_MINUTE   = int(os.getenv("GROQ_TPM", "0"))        # 0 = desactivar control local de TPM
REQUESTS_PER_DAY    = int(os.getenv("GROQ_RPD", "0"))        # 0 = desactivar control local de RPD

# 🕓 Ventanas deslizantes (si decides usar control local además de los headers)
token_window = deque()    # (timestamp, num_tokens)
minute_window = deque()   # timestamps para RPM
daily_window = deque()    # timestamps para RPD

def estimate_tokens(text: str) -> int:
    """Aproximación: tokens ≈ bytes_utf8/4."""
    try:
        return max(1, len(text.encode("utf-8")) // 4)
    except Exception:
        return 1000

def _sleep_until(ts_reset: float):
    wait_s = max(0.0, ts_reset - time.time())
    if wait_s > 0:
        print(f"⏳ Waiting {wait_s:.1f}s due to server rate limits…")
        time.sleep(wait_s)

def _respect_rate_limit_headers(resp):
    """
    Si el servidor mandó 'Retry-After' o cabeceras de reset, esperamos lo indicado.
    Groq puede devolver 'Retry-After' en 429.
    """
    h = resp.headers or {}
    # 1) Retry-After
    ra = h.get("Retry-After")
    if ra:
        try:
            wait_s = float(ra)
            print(f"⏳ Retry-After: {wait_s}s")
            time.sleep(wait_s)
            return True
        except ValueError:
            pass
    # 2) Algunos proxies/servicios usan cabeceras estilo x-ratelimit-reset-requests/seconds
    # Si encuentras cabeceras concretas en tu org, puedes parsearlas aquí.
    return False  # no había nada utilizable

def _local_rate_limits(prompt_tokens: int, max_output_tokens: int):
    """
    Control local opcional (útil si conoces tus cuotas exactas).
    Si alguna cuota está a 0, se ignora y confiamos en los headers del servidor.
    """
    now = time.time()
    budget = prompt_tokens + max_output_tokens

    # Limpiar ventanas
    while token_window and now - token_window[0][0] >= 60:
        token_window.popleft()
    while minute_window and now - minute_window[0] >= 60:
        minute_window.popleft()
    while daily_window and now - daily_window[0] >= 86400:
        daily_window.popleft()

    # TPM
    if TOKENS_PER_MINUTE > 0:
        used_tpm = sum(n for _, n in token_window)
        if used_tpm + budget > TOKENS_PER_MINUTE:
            wait_time = 60 - (now - token_window[0][0])
            print(f"⏳ Local TPM cap: waiting {int(wait_time)+1}s…")
            time.sleep(max(0, wait_time) + 1)
            return _local_rate_limits(prompt_tokens, max_output_tokens)

    # RPM
    if REQUESTS_PER_MINUTE > 0 and len(minute_window) >= REQUESTS_PER_MINUTE:
        wait_time = 60 - (now - minute_window[0])
        print(f"⏳ Local RPM cap: waiting {int(wait_time)+1}s…")
        time.sleep(max(0, wait_time) + 1)
        return _local_rate_limits(prompt_tokens, max_output_tokens)

    # RPD
    if REQUESTS_PER_DAY > 0 and len(daily_window) >= REQUESTS_PER_DAY:
        raise Exception("🚫 Local RPD cap reached.")

    token_window.append((now, budget))
    minute_window.append(now)
    daily_window.append(now)

def generate_with_groq(prompt: str, retries: int = 4, temperature: float = 0.0, max_tokens: int = 4096) -> str:
    """Envía prompt al modelo con control local opcional + respeto de headers del servidor."""
    # Control local (si definiste cuotas en env)
    prompt_tokens = estimate_tokens(prompt)
    _local_rate_limits(prompt_tokens, max_tokens)

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    for attempt in range(retries):
        try:
            resp = requests.post(GROQ_URL, headers=headers, json=data, timeout=120)
            if resp.status_code == 429:
                print("⚠️ 429 Too Many Requests.")
                if _respect_rate_limit_headers(resp):
                    continue
                # Sin headers claros: backoff exponencial
                wait_s = 10 * (attempt + 1)
                print(f"⏳ Backing off {wait_s}s…")
                time.sleep(wait_s)
                continue

            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

        except HTTPError as e:
            print(f"❌ HTTP {resp.status_code if resp else '??'}: {e}")
            if 500 <= (resp.status_code if resp else 500) < 600:
                wait_s = 5 * (attempt + 1)
                print(f"⏳ Server error, retrying in {wait_s}s…")
                time.sleep(wait_s)
                continue
            raise
        except RequestException as e:
            wait_s = 5 * (attempt + 1)
            print(f"⚠️ Network error: {e}. Retrying in {wait_s}s…")
            time.sleep(wait_s)
            continue

    raise Exception("❌ Failed after multiple retries.")

def extract_json_block(text: str):
    try:
        cleaned = re.sub(r"```(json)?", "", text).strip("` \n")
        decoder = json.JSONDecoder()
        obj, _ = decoder.raw_decode(cleaned)
        return obj
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        return None

PROMPT_DIR = Path(__file__).resolve().parent.parent / "PROMPTS"

def load_prompt(mode: str, text: str) -> str:
    """Carga PROMPTS/<mode>.txt y asegura que el texto de entrada esté presente."""
    prompt_path = os.path.join(PROMPT_DIR, f"{mode}.txt")
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"❌ Prompt file not found: {prompt_path}")
    with open(prompt_path, "r", encoding="utf-8") as f:
        template = f.read()

    template = template.replace("\r\n", "\n")  # normaliza saltos de línea

    if "{text}" in template:
        prompt = template.replace("{text}", text)
        injected = True
    else:
        # fallback: añade el texto explícitamente al final
        prompt = f"{template.rstrip()}\n\nText:\n'''{text}'''"
        injected = False

    return prompt


def detect_sensitive_data_with_positions(text: str, mode: str = PROMPT_MODE, show_prompts: bool = False):
   
    try:
        prompt_path = os.path.join(os.getenv("PROMPT_DIR", "PROMPTS"), f"{mode}.txt")
        prompt = load_prompt(mode, text)

        if show_prompts:
            print(f"📄 Usando archivo de prompt: {prompt_path}")
            print("\n🧾 Prompt de entrada:\n", prompt)

        response_text = generate_with_groq(prompt, temperature=0.0, max_tokens=8192)

        # Mostrar la respuesta cruda del modelo solo si es la primera muestra
        if show_prompts:
            print("\n📤 Respuesta cruda del modelo:\n", response_text)

        result = extract_json_block(response_text) or {}
        fields = result.get("detected_fields", []) or []

        out = []
        for f in fields:
            value = (f.get("value") or "").strip()
            if not value:
                continue
            label = (f.get("field") or "UNKNOWN").strip()
            source = (f.get("source") or "UNKNOWN").strip()
            for m in re.finditer(re.escape(value), text):
                out.append({
                    "value": value,
                    "start": m.start(),
                    "end": m.end(),
                    "label": label,
                    "source": source
                })
        return out
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

if __name__ == "__main__":
    # === Ejecución por lotes (ejemplo) ===
    jsonl_path = "pii-masking-200k/english_pii_43k.jsonl"
    output = []
    print("📥 Analizando las primeras muestras con openai/gpt-oss-120b (Groq pago)…\n")

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if idx >= 1000:
                break
            item = json.loads(line)
            text = item["source_text"]

            # Encabezado de muestra analizada
            print(f"\n🔹 Entrada #{item['id']}")
            print(f"📝 Texto a analizar:\n{text}\n")

            # Solo en la primera muestra imprime prompt y salida cruda
            predicted = detect_sensitive_data_with_positions(
                text,
                mode=PROMPT_MODE,
                show_prompts=(idx == 0)
            )

            # Para todas las muestras imprime solo campos detectados
            if predicted:
                for p in predicted:
                    print(f"  - {p['label']} ({p['source']}): \"{p['value']}\" [start={p['start']}, end={p['end']}]")
            else:
                print("  - No se detectó PII.")

            output.append({"id": item["id"], "text": text, "predicted_labels": predicted})



    out_name = "RESULTADOS/GPT-OSS-120b/pii_detection_sample_gpt-oss-120b_Groq_paid_1000_ZS_enriquecido.json"
    with open(out_name, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Guardado en {out_name}")