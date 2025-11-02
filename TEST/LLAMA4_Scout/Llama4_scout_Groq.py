from collections import deque
from pathlib import Path
import time
import requests
import json
import re
import os
from requests.exceptions import HTTPError, RequestException
from pathlib import Path
# ================== Configuración ==================
PROMPT_MODE = os.getenv("PROMPT_MODE", "ZS_enriquecido_prompt").strip()
PROMPT_DIR = Path(__file__).resolve().parent.parent / "PROMPTS"

# 🌐 Groq Configuración
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("Groq API key not found. Please set GROQ_API_KEY.")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "meta-llama/llama-4-scout-17b-16e-instruct"  # ajusta si quieres

# 🔒 Límites de uso (puedes moverlos a ENV si prefieres)
REQUESTS_PER_MINUTE = int(os.getenv("GROQ_RPM", "30"))
REQUESTS_PER_DAY    = int(os.getenv("GROQ_RPD", "1000"))
TOKENS_PER_MINUTE   = int(os.getenv("GROQ_TPM", "30000"))

# 🕓 Ventanas deslizantes
token_window = deque()    # (timestamp, num_tokens)
minute_window = deque()   # timestamps para RPM
daily_window = deque()    # timestamps para RPD

# ================== Utilidades ==================
def estimate_tokens(text: str) -> int:
    """Aproximación: tokens ≈ bytes_utf8/4."""
    try:
        return max(1, len(text.encode("utf-8")) // 4)
    except Exception:
        return 1000  # fallback conservador

def check_usage_limits(prompt: str, max_output_tokens: int = 4096):
    """Verifica y respeta los límites de tokens y requests (local)."""
    now = time.time()
    tokens = estimate_tokens(prompt) + max_output_tokens

    # Limpieza de ventanas
    while token_window and now - token_window[0][0] >= 60:
        token_window.popleft()
    while minute_window and now - minute_window[0] >= 60:
        minute_window.popleft()
    while daily_window and now - daily_window[0] >= 86400:
        daily_window.popleft()

    used_tokens = sum(n for _, n in token_window)

    # TPM
    if TOKENS_PER_MINUTE > 0 and used_tokens + tokens > TOKENS_PER_MINUTE:
        wait_time = 60 - (now - token_window[0][0])
        print(f"⏳ Token limit reached ({TOKENS_PER_MINUTE}/min). Waiting {int(wait_time)+1}s...")
        time.sleep(max(0, wait_time) + 1)
        return check_usage_limits(prompt, max_output_tokens)

    # RPM
    if REQUESTS_PER_MINUTE > 0 and len(minute_window) >= REQUESTS_PER_MINUTE:
        wait_time = 60 - (now - minute_window[0])
        print(f"⏳ Request limit reached ({REQUESTS_PER_MINUTE}/min). Waiting {int(wait_time)+1}s...")
        time.sleep(max(0, wait_time) + 1)
        return check_usage_limits(prompt, max_output_tokens)

    # RPD
    if REQUESTS_PER_DAY > 0 and len(daily_window) >= REQUESTS_PER_DAY:
        raise Exception("🚫 Daily request limit reached.")

    # Registrar uso
    token_window.append((now, tokens))
    minute_window.append(now)
    daily_window.append(now)

def _respect_retry_after(resp) -> bool:
    """Respeta Retry-After si está presente."""
    try:
        ra = resp.headers.get("Retry-After")
        if ra:
            wait_s = float(ra)
            print(f"⏳ Retry-After: {wait_s}s")
            time.sleep(wait_s)
            return True
    except Exception:
        pass
    return False

# ================== Llamada a Groq ==================
def generate_with_groq(
    prompt: str,
    retries: int = 3,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    timeout: int = 120
) -> str:
    """Envía prompt al modelo Groq con control de uso, backoff y reintentos."""
    #check_usage_limits(prompt, max_output_tokens=max_tokens)

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    for attempt in range(retries):
        try:
            resp = requests.post(GROQ_URL, headers=headers, json=data, timeout=timeout)
            if resp.status_code == 429:
                print("⚠️ 429 Too Many Requests.")
                if _respect_retry_after(resp):
                    continue
                wait_s = 10 * (attempt + 1)
                print(f"⏳ Backing off {wait_s}s…")
                time.sleep(wait_s)
                continue

            # 5xx -> backoff y reintento
            if 500 <= resp.status_code < 600:
                wait_s = 5 * (attempt + 1)
                print(f"⚠️ {resp.status_code} server error. Retrying in {wait_s}s…")
                time.sleep(wait_s)
                continue

            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

        except (HTTPError, RequestException) as e:
            wait_s = 5 * (attempt + 1)
            print(f"⚠️ Network/HTTP error: {e}. Retrying in {wait_s}s…")
            time.sleep(wait_s)
            continue

    raise Exception("❌ Failed after multiple retries.")

# ================== Parsing de salida ==================
def extract_json_block(text: str):
    """Extrae el JSON incluso si vino envuelto en ``` o backticks."""
    try:
        cleaned = re.sub(r"```(json)?", "", text).strip("` \n")
        decoder = json.JSONDecoder()
        obj, _ = decoder.raw_decode(cleaned)
        return obj
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        return None

# ================== Prompts externos ==================
def load_prompt(mode: str, text: str) -> str:
    """Carga PROMPTS/<mode>.txt y asegura que el texto de entrada esté presente."""
    prompt_path = Path(PROMPT_DIR) / f"{mode}.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"❌ Prompt file not found: {prompt_path}")
    template = prompt_path.read_text(encoding="utf-8").replace("\r\n", "\n")

    if "{text}" in template:
        prompt = template.replace("{text}", text)
    else:
        # Fallback: anexa el texto al final si el template no lo incluye
        prompt = f"{template.rstrip()}\n\nText:\n'''{text}'''"

    return prompt, str(prompt_path)

# ================== Detección ==================
def detect_sensitive_data_with_positions(text: str, mode: str = PROMPT_MODE, show_prompts: bool = False):
    try:
        prompt, prompt_path = load_prompt(mode, text)

        if show_prompts:
            print(f"📄 Usando archivo de prompt: {prompt_path}")
            print("\n🧾 Prompt de entrada:\n", prompt)

        # Ajusta temperatura si quieres más recall
        response_text = generate_with_groq(prompt, temperature=0.2, max_tokens=8192)

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
            # Marca posiciones de todas las apariciones del valor
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

# ================== Main (batch) ==================
if __name__ == "__main__":
    jsonl_path = "pii-masking-200k/english_pii_43k.jsonl"
    output = []
    print(f"📥 Analizando las primeras muestras con {MODEL_NAME} (Groq)…  Modo prompt: {PROMPT_MODE}\n")

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if idx >= 1000:
                break
            item = json.loads(line)
            text = item["source_text"]

            print(f"\n🔹 Entrada #{item['id']}")
            print(f"📝 Texto a analizar:\n{text}\n")

            predicted = detect_sensitive_data_with_positions(
                text,
                mode=PROMPT_MODE,
                show_prompts=(idx == 0)  # Solo en la primera muestra
            )

            if predicted:
                for p in predicted:
                    print(f"  - {p['label']} ({p['source']}): \"{p['value']}\" [start={p['start']}, end={p['end']}]")
            else:
                print("  - No se detectó PII.")

            output.append({"id": item["id"], "text": text, "predicted_labels": predicted})

    out_path = Path("RESULTADOS") / "pii_detection_sample_llama4_scout_Groq_1000_ZS_enriquecido.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Guardado en {out_path.resolve()}")
