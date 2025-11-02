import json
import re
import time
import os
from pathlib import Path
from tqdm import tqdm
from openai import OpenAI
from openai import RateLimitError, APIError
from pathlib import Path

# ================== Config ==================
client = OpenAI()

MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.0"))
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "4096"))

# LÍMITES opcionales (desactívalos si no los necesitas)
MAX_RPM = int(os.getenv("MAX_RPM", "3"))
TOKEN_LIMIT_PER_MINUTE = int(os.getenv("TOKEN_LIMIT_PER_MINUTE", "60000"))
MAX_DAILY_REQUESTS = int(os.getenv("MAX_DAILY_REQUESTS", "1000"))
TOKEN_LIMIT_PER_DAY = int(os.getenv("TOKEN_LIMIT_PER_DAY", "200000"))

PROMPT_MODE = os.getenv("PROMPT_MODE", "ZS_prompt").strip()   # p.ej. ZS_prompt, ZS_enriched, FS_prompt
PROMPT_DIR = Path(__file__).resolve().parent.parent / "PROMPTS"


jsonl_path = "../english_pii_43k.jsonl"
OUT_JSON   = "pii_detection_sample_gpt_4o_mini_ZS_1000.json"

# ================== Rate-limit local (opcional) ==================
REQUEST_COUNT = 0
START_TIME = time.time()
TOTAL_DAILY_REQUESTS = 0
TOTAL_TOKENS_TODAY = 0
TOKEN_HISTORY = []  # lista de (timestamp, tokens)

def approx_token_count(s: str) -> int:
    return max(1, len(s.encode("utf-8")) // 4)

def rate_limit(prompt_tokens_est: int, max_output_tokens: int = MAX_OUTPUT_TOKENS):
    """Control local simple de RPM/TPM/RPD/TPD (opcional)."""
    global REQUEST_COUNT, START_TIME, TOTAL_DAILY_REQUESTS, TOKEN_HISTORY, TOTAL_TOKENS_TODAY
    token_budget = prompt_tokens_est + max_output_tokens

    if TOTAL_DAILY_REQUESTS >= MAX_DAILY_REQUESTS:
        raise RuntimeError("🚫 Límite diario de requests alcanzado (RPD).")
    if TOTAL_TOKENS_TODAY + token_budget > TOKEN_LIMIT_PER_DAY:
        raise RuntimeError("🚫 Límite diario de tokens alcanzado (TPD).")

    now = time.time()
    TOKEN_HISTORY = [t for t in TOKEN_HISTORY if now - t[0] < 60]
    tokens_last_minute = sum(t[1] for t in TOKEN_HISTORY)

    if tokens_last_minute + token_budget > TOKEN_LIMIT_PER_MINUTE and TOKEN_HISTORY:
        wait_time = max(0.0, 60 - (now - TOKEN_HISTORY[0][0]))
        if wait_time > 0:
            print(f"⏳ Token limit (TPM): esperando {wait_time:.2f}s…")
            time.sleep(wait_time)
        now = time.time()
        TOKEN_HISTORY = [t for t in TOKEN_HISTORY if now - t[0] < 60]

    REQUEST_COUNT += 1
    elapsed = now - START_TIME
    if REQUEST_COUNT > MAX_RPM:
        if elapsed < 60:
            wait_remaining = 60 - elapsed
            print(f"⏳ Request limit (RPM): esperando {wait_remaining:.2f}s…")
            time.sleep(wait_remaining)
        REQUEST_COUNT = 1
        START_TIME = time.time()

    TOTAL_DAILY_REQUESTS += 1
    TOTAL_TOKENS_TODAY += token_budget
    TOKEN_HISTORY.append((time.time(), token_budget))

def backoff_sleep(attempt: int):
    wait = min(60, 2 ** attempt)
    print(f"🔁 Reintentando en {wait:.0f}s…")
    time.sleep(wait)

# ================== Prompts externos ==================
def load_prompt(mode: str, text: str) -> tuple[str, str]:
    """
    Carga PROMPTS/<mode>.txt y asegura que el texto de entrada esté presente.
    Devuelve (prompt_final, ruta_del_prompt).
    """
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

# ================== Llamada a OpenAI ==================
def call_openai_json(prompt: str, temperature: float = TEMPERATURE, max_tokens: int = MAX_OUTPUT_TOKENS):
    # rate limit local (opcional)
    #rate_limit(approx_token_count(prompt), max_output_tokens=max_tokens)

    for attempt in range(5):
        try:
            resp = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            return resp.choices[0].message.content or ""
        except (RateLimitError, APIError) as e:
            print(f"⚠️ API error: {e}")
            if attempt == 4:
                return ""
            backoff_sleep(attempt)

# ================== Utilidades de parseo ==================
def extract_json_block(text: str):
    """Extrae JSON válido incluso si viene con texto alrededor."""
    if not text:
        return None
    # Si el endpoint respeta response_format=json_object, ya debería ser solo JSON.
    # Aun así, por seguridad:
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None

# ================== Detección ==================
def detect_sensitive_data_with_positions(text: str, mode: str = PROMPT_MODE, show_prompts: bool = False):
    try:
        prompt, prompt_path = load_prompt(mode, text)

        if show_prompts:
            print(f"📄 Usando archivo de prompt: {prompt_path}")
            print("\n🧾 Prompt de entrada:\n", prompt)

        content = call_openai_json(prompt, temperature=TEMPERATURE, max_tokens=MAX_OUTPUT_TOKENS)

        if show_prompts:
            print("\n📤 Respuesta cruda del modelo:\n", content)

        result = extract_json_block(content) or {}
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

# ================== Main ==================
if __name__ == "__main__":
    output = []
    print(f"📥 Analizando las primeras muestras con {MODEL_NAME}\nPROMPT_DIR={PROMPT_DIR}  PROMPT_MODE={PROMPT_MODE}\n")

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(tqdm(f, total=1000)):
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

    out_path = Path(OUT_JSON)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Guardado en {out_path.resolve()}")
