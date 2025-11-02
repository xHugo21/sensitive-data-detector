# detector.py
import os
import re
import json
from pathlib import Path
from urllib.parse import urlparse, unquote
import pdfplumber
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ================== Cliente OpenAI ==================
client = OpenAI()

# Modelo por defecto (puedes sobreescribir con OPENAI_MODEL en el entorno)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ================== Rutas de PROMPTS ==================
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_PROMPT_DIR = BASE_DIR / "PROMPTS"
PROMPT_DIR = Path(os.getenv("PROMPT_DIR", str(DEFAULT_PROMPT_DIR)))

PROMPT_MAP = {
    "Zero-shot": "ZS_prompt.txt",
    "Zero-shot enriquecido": "ZS_enriquecido_prompt.txt",
    "Few-shot": "FS_prompt.txt",
}

def _load_prompt_from_dir(mode: str) -> str:
    """Carga el prompt según el modo desde PROMPT_DIR."""
    if not mode:
        mode = "Few-shot"
    filename = PROMPT_MAP.get(mode, PROMPT_MAP["Few-shot"])
    path = PROMPT_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
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
            return None
        if file_path.lower().endswith(".pdf"):
            return read_pdf(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
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
    except Exception:
        return None

# ================== Detección con OpenAI ==================
def _safe_json_from_text(s: str) -> dict:
    """Intenta extraer el primer objeto JSON válido del string."""
    if not s:
        return {}
    m = re.search(r"\{.*\}", s, re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except Exception:
        return {}

def detect_sensitive_data(text: str, prompt: str | None = None, mode: str = "Few-shot"):
    """
    Analiza 'text' con el LLM (OpenAI gpt-4o-mini) guiado por un prompt.
    - Si 'prompt' viene definido, se usa tal cual (+ inyección de texto).
    - Si no, se carga la plantilla de PROMPTS según 'mode' (por defecto Few-shot).
    Devuelve un dict con, al menos, {"detected_fields": [...]}.
    """
    try:
        # 1) Construir prompt efectivo (por defecto Few-shot)
        if prompt and prompt.strip():
            final_prompt = _inject_text(prompt.strip(), text)
            prompt_info = "custom"
        else:
            template = _load_prompt_from_dir(mode or "Few-shot")
            final_prompt = _inject_text(template, text)
            prompt_info = f"PROMPTS/{PROMPT_MAP.get(mode or 'Few-shot', 'FS_prompt.txt')}"

        sys_msg = "You are to output a single valid JSON object only. No prose, no markdown."

        try:
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": final_prompt},
                ],
                temperature=0,
                max_tokens=1500,
                response_format={"type": "json_object"},  # 👈 OpenAI lo soporta
            )
            content = (resp.choices[0].message.content or "").strip()
        except Exception:
            # Fallback si falla el parámetro response_format
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "Devuelve únicamente un objeto JSON válido. Sin texto adicional."},
                    {"role": "user", "content": final_prompt},
                ],
                temperature=0,
                max_tokens=1500,
            )
            content = (resp.choices[0].message.content or "").strip()

        result = _safe_json_from_text(content) or {"detected_fields": []}
        if "detected_fields" not in result or not isinstance(result["detected_fields"], list):
            result["detected_fields"] = []
        result["_prompt_source"] = prompt_info
        result["_model_used"] = OPENAI_MODEL
        return result
    except Exception as e:
        return {"detected_fields": [], "risk_level": "Unknown", "_error": str(e)}

# ================== Cálculo de riesgo ==================
def compute_risk_level(detected_fields):
    """
    Suma de puntuaciones por campo detectado:
      - Alto: 6 puntos
      - Medio: 2 puntos
      - Bajo: 1 punto
    No se deduplican campos: cada aparición suma.
    Umbrales:
      - High: score >= 6
      - Medium: 4 <= score <= 5
      - Low: 1 <= score <= 3
      - None: score == 0
    """
    def norm(name: str) -> str:
        # Normaliza el label: mayúsculas, sin espacios ni guiones/bajos
        return (name or "").strip().upper().replace("-", "").replace("_", "")

    high_risk = {
        "PASSWORD","CREDENTIALS","SSN","DNI","PASSPORTNUMBER",
        "CREDITCARDNUMBER","IP","IPV4","IPV6","MAC",
        "CREDITCARDCVV","ACCOUNTNUMBER","IBAN","PIN","GENETICDATA",
        "BIOMETRICDATA","STREET","VEHICLEVIN","HEALTHDATA","CRIMINALRECORD",
        "CONFIDENTIALDOC","LITECOINADDRESS","BITCOINADDRESS","ETHEREUMADDRESS",
        "PHONEIMEI"
    }

    medium_risk = {
        "EMAIL","PHONENUMBER","URL","CLIENTDATA","EMPLOYEEDATA","SALARYDETAILS",
        "COMPANYNAME","JOBTITLE","JOBTYPE","JOBAREA","ACCOUNTNAME","PROJECTNAME",
        "CODENAME","EDUCATIONHISTORY","CV","SOCIALMEDIAHANDLE","SECONDARYADDRESS",
        "CITY","STATE","COUNTY","ZIPCODE","BUILDINGNUMBER","USERAGENT","VEHICLEVRM",
        "NEARBYGPSCOORDINATE","BIC","MASKEDNUMBER","AMOUNT","CURRENCY",
        "CURRENCYSYMBOL","CURRENCYNAME","CURRENCYCODE","CREDITCARDISSUER","USERNAME",
        "INFRASTRUCTURE"
    }

    low_risk = {
        "PREFIX","FIRSTNAME","MIDDLENAME","LASTNAME","AGE","DOB","GENDER","SEX",
        "HAIRCOLOR","EYECOLOR","HEIGHT","WEIGHT","SKINTONE","OTHER FEATURES",
        "RACIALORIGIN","RELIGION","POLITICALOPINION","PHILOSOPHICALBELIEF","TRADEUNION",
        "DATE","TIME","ORDINALDIRECTION","SEXUALORIENTATION","CHILDRENDATA",
        "LEGALDISCLOSURE"
    }

    score = 0
    for f in detected_fields:
        field = norm(f.get("field", ""))
        if field in high_risk:
            score += 6
        elif field in medium_risk:
            score += 2
        elif field in low_risk:
            score += 1
        else:
            score += 2  # conservador

    if score >= 6:
        return "High"
    if 4 <= score <= 5:
        return "Medium"
    if 1 <= score <= 3:
        return "Low"
    return "None"
