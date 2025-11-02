import os
import re
import json
import pdfplumber
from urllib.parse import urlparse, unquote
from colorama import Fore, Style
from openai import OpenAI
from pathlib import Path

client = OpenAI()

# ================== Rutas de PROMPTS ==================
# PROMPTS está una carpeta por encima de este archivo (ajusta si hace falta)
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_PROMPT_DIR = BASE_DIR.parent / "PROMPTS"

# Permite override por variable de entorno PROMPT_DIR
PROMPT_DIR = Path(os.getenv("PROMPT_DIR", str(DEFAULT_PROMPT_DIR)))

PROMPT_MAP = {
    "Zero-shot": "ZS_prompt.txt",
    "Zero-shot enriquecido": "ZS_enriquecido_prompt.txt",
    "Few-shot": "FS_prompt.txt",
}

def _load_prompt_from_dir(mode: str) -> str:
    """Carga el prompt según el modo desde PROMPT_DIR."""
    filename = PROMPT_MAP.get(mode, PROMPT_MAP["Zero-shot"])
    path = PROMPT_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"❌ Prompt file not found: {path}")
    return path.read_text(encoding="utf-8").replace("\r\n", "\n").strip()

def _inject_text(template: str, text: str) -> str:
    """Inserta el texto en {text} si existe; si no, lo añade al final."""
    if "{text}" in template:
        return template.replace("{text}", text)
    return f"{template.rstrip()}\n\nText:\n'''{text}'''"

# ================== Utilidades de I/O ==================
def sanitize_file_path(file_path):
    if file_path.startswith("file://"):
        parsed_path = urlparse(file_path).path
        parsed_path = unquote(parsed_path)
        if os.name == "nt":
            parsed_path = parsed_path.lstrip("/")
        return parsed_path
    return file_path

def read_document(file_path):
    try:
        file_path = sanitize_file_path(file_path)
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return None
        if file_path.lower().endswith(".pdf"):
            return read_pdf(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return None

def read_pdf(file_path):
    try:
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                extracted_text = page.extract_text()
                if extracted_text:
                    text += extracted_text + "\n"
        return text.strip()
    except Exception as e:
        print(f"❌ Error reading PDF: {e}")
        return None

# ================== Detección con OpenAI ==================
def detect_sensitive_data(text: str, prompt: str | None = None, mode: str = "Zero-shot"):
    """
    - Si 'prompt' se proporciona, se usa tal cual (con inyección de texto).
    - Si no, se carga desde PROMPTS según 'mode'.
    - Devuelve un dict con al menos {"detected_fields": [...]}
    """
    try:
        # 1) Construir prompt efectivo
        if prompt and prompt.strip():
            final_prompt = _inject_text(prompt.strip(), text)
            prompt_info = "custom"
        else:
            template = _load_prompt_from_dir(mode)
            final_prompt = _inject_text(template, text)
            prompt_info = f"PROMPTS/{PROMPT_MAP.get(mode, 'ZS_prompt.txt')}"

        # 2) Llamada al modelo (JSON forzado si está disponible)
        try:
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {
                        "role": "system",
                        "content": "You are to output a single valid JSON object only. No prose, no markdown."
                    },
                    {"role": "user", "content": final_prompt},
                ],
                temperature=0,
                max_tokens=1500,
                response_format={"type": "json_object"},  # si tu SDK lo soporta
            )
            content = (response.choices[0].message.content or "").strip()
        except Exception:
            # Fallback si tu endpoint no soporta response_format
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {
                        "role": "system",
                        "content": "Devuelve únicamente un objeto JSON válido. Sin texto adicional, sin markdown."
                    },
                    {"role": "user", "content": final_prompt},
                ],
                temperature=0,
                max_tokens=1500,
            )
            content = (response.choices[0].message.content or "").strip()

        # 3) Parsear JSON (robusto)
        match = re.search(r"\{.*\}", content, re.DOTALL)
        result = json.loads(match.group(0)) if match else {"detected_fields": []}

        # Asegurar clave
        if "detected_fields" not in result or not isinstance(result["detected_fields"], list):
            result["detected_fields"] = []

        # (Opcional) Meta
        result["_prompt_source"] = prompt_info
        return result

    except Exception as e:
        print(f"❌ Error in detection: {e}")
        return {"detected_fields": [], "risk_level": "Unknown"}

# ================== Cálculo de riesgo ==================
def compute_risk_level(detected_fields):
    high_risk = {"PASSWORD", "CREDENTIALS", "SSN", "DNI", "PASSPORTNUMBER", "CREDITCARDNUMBER", "IP", "IPv4", "IPv6", "MAC", "CREDITCARDCVV", "ACCOUNTNUMBER", "IBAN", "PIN", "GENETICDATA", "BIOMETRICDATA", "STREET", "VEHICLEVIN", "HEALTHDATA", "CRIMINALRECORD", "CONFIDENTIALDOC", "LITECOINADDRESS", "BITCOINADDRESS", "ETHEREUMADDRESS", "PHONEIMEI"}
    medium_risk = {"EMAIL", "PHONENUMBER", "URL", "CLIENTDATA", "EMPLOYEEDATA", "SALARYDETAILS", "COMPANYNAME", "JOBTITLE", "JOBTYPE", "JOBAREA", "ACCOUNTNAME", "PROJECTNAME", "CODENAME", "EDUCATIONHISTORY", "CV", "SOCIALMEDIAHANDLE", "SECONDARYADDRESS", "CITY", "STATE", "COUNTY", "ZIPCODE", "BUILDINGNUMBER", "USERAGENT", "VEHICLEVRM", "NEARBYGPSCOORDINATE", "BIC", "MASKEDNUMBER", "AMOUNT", "CURRENCY", "CURRENCYSYMBOL", "CURRENCYNAME", "CURRENCYCODE", "CREDITCARDISSUER", "USERNAME", "INFRASTRUCTURE"}
    low_risk = {"PREFIX", "FIRSTNAME", "MIDDLENAME", "LASTNAME", "AGE", "DOB", "GENDER", "SEX", "HAIRCOLOR", "EYECOLOR", "HEIGHT", "WEIGHT", "SKINTONE", "OTHER FEATURES", "RACIALORIGIN", "RELIGION", "POLITICALOPINION", "PHILOSOPHICALBELIEF", "TRADEUNION", "DATE", "TIME", "ORDINALDIRECTION", "SEXUALORIENTATION", "CHILDRENDATA", "LEGALDISCLOSURE"}

    score = 0
    for f in detected_fields:
        field = (f.get("field") or "").upper()
        if field in high_risk:
            score += 3
        elif field in medium_risk:
            score += 2
        elif field in low_risk:
            score += 1
        else:
            score += 2  # por defecto conservador

    if score >= 9:
        return "High"
    if score >= 4:
        return "Medium"
    if score > 0:
        return "Low"
    return "None"

# ================== Salida por consola ==================
def display_results(pii_data):
    risk_level = pii_data.get("risk_level", "Unknown")
    fields = pii_data.get("detected_fields", [])

    print(Fore.BLUE + "\n🔍 Summary View:" + Style.RESET_ALL)
    print(f"🔒 Risk Level: {risk_level}")
    if fields:
        print(Fore.LIGHTWHITE_EX + "\n📌 Detected Fields:" + Style.RESET_ALL)
        for f in fields:
            print(f"  🔹 {f.get('field','?')}: {f.get('value','')} ({f.get('source','')})")
    else:
        print(Fore.GREEN + "✅ No sensitive data detected." + Style.RESET_ALL)

# ================== CLI simple (opcional) ==================
if __name__ == "__main__":
    while True:
        user_input = input("\n🔹 Enter a message or file path (type 'exit' to quit): ").strip()
        if user_input.lower() == "exit":
            print("\n🚪 Exiting...")
            break

        mode = input("🧠 Detection mode ('Zero-shot', 'Zero-shot enriquecido', 'Few-shot'): ").strip()
        if os.path.isfile(sanitize_file_path(user_input)):
            print("📂 Reading document...")
            text = read_document(user_input) or ""
        else:
            text = user_input

        if not text.strip():
            print("❌ Texto vacío. No se puede analizar.")
            continue

        pii = detect_sensitive_data(text, prompt=None, mode=mode)
        pii["risk_level"] = compute_risk_level(pii.get("detected_fields", []))
        display_results(pii)

        if pii.get("detected_fields"):
            confirm = input(Fore.RED + Style.BRIGHT + "\n❗ Contains sensitive data. Send to LLM? (yes/no): " + Style.RESET_ALL).lower()
            if confirm not in ["yes", "y"]:
                print("❌ Not sent.")
                continue

        # Ejemplo: integra tu generador externo (p.ej., Gemini) si lo tienes
        # from chatgpt_wrapper import generate_response_with_gemini
        # response = generate_response_with_gemini(text)
        # print("\n📝 LLM Response:\n", response)
        # result = detect_sensitive_data(response, mode=mode)
        # result["risk_level"] = compute_risk_level(result.get("detected_fields", []))
        # display_results(result)
