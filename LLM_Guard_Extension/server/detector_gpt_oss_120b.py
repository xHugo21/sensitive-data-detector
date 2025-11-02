# detector.py
import os
import re
import json
from pathlib import Path
from urllib.parse import urlparse, unquote
import pdfplumber

# === Cliente Groq (LLM) ===
# pip install groq pdfplumber
from groq import Groq

# Cliente Groq; requiere GROQ_API_KEY en el entorno
_groq_api_key = os.getenv("GROQ_API_KEY")
if not _groq_api_key:
    raise RuntimeError(
        "Falta GROQ_API_KEY en el entorno. Exporta tu clave: "
        "Linux/macOS: export GROQ_API_KEY='...' | Windows PowerShell: $env:GROQ_API_KEY='...'"
    )
groq_client = Groq(api_key=_groq_api_key)

# Modelo por defecto (puedes override con GROQ_MODEL)
GROQ_MODEL = os.getenv("GROQ_MODEL", "OpenAI/gpt-oss-120B")

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
    # Por defecto usa Few-shot (FS_prompt)
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

def read_document(file_path: str) -> str | None:
    """
    Lee un documento (PDF o TXT) y devuelve su texto.
    """
    print(f"[read_document] intentando abrir: {file_path}")

    try:
        file_path = sanitize_file_path(file_path)
        if not os.path.exists(file_path):
            print(f"[read_document] ❌ Archivo no encontrado: {file_path}")
            return None

        # PDF
        if file_path.lower().endswith(".pdf"):
            print("[read_document] Detectado PDF, llamando a read_pdf...")
            text = read_pdf(file_path)
            if text and text.strip():
                print(f"[read_document] ✅ Texto leído ({len(text)} chars)")
                return text
            else:
                print(f"[read_document] ⚠️ read_pdf no devolvió texto")
                return None

        # TXT
        elif file_path.lower().endswith(".txt"):
            print("[read_document] Detectado TXT")
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

        else:
            print(f"[read_document] ❌ Formato no soportado: {file_path}")
            return None

    except Exception as e:
        print(f"[read_document] Error leyendo {file_path}:", e)
        return None

# detector.py
def read_pdf(file_path: str) -> str | None:
    """
    Extrae texto de PDF probando varios métodos en cascada.
    Añade logs para depuración.
    """
    text = ""

    print(f"\n[read_pdf] Intentando leer PDF: {file_path}")

    # 1) pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            chunks = []
            for i, p in enumerate(pdf.pages, 1):
                t = p.extract_text() or ""
                print(f"[read_pdf] pdfplumber página {i}: {len(t)} chars")
                if t.strip():
                    chunks.append(t)
            text = "\n".join(chunks).strip()
        print(f"[read_pdf] pdfplumber total: {len(text)} chars")
    except Exception as e:
        print("[read_pdf] pdfplumber error:", e)

    # 2) PyPDF2
    if len(text) < 50:
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            chunks = []
            for i, page in enumerate(reader.pages, 1):
                t = page.extract_text() or ""
                print(f"[read_pdf] PyPDF2 página {i}: {len(t)} chars")
                if t.strip():
                    chunks.append(t)
            alt = "\n".join(chunks).strip()
            print(f"[read_pdf] PyPDF2 total: {len(alt)} chars")
            if len(alt) > len(text):
                text = alt
        except Exception as e:
            print("[read_pdf] PyPDF2 error:", e)

    # 3) pdfminer.six
    if len(text) < 50:
        try:
            from pdfminer.high_level import extract_text as pdfminer_extract
            alt2 = (pdfminer_extract(file_path) or "").strip()
            print(f"[read_pdf] pdfminer total: {len(alt2)} chars")
            if len(alt2) > len(text):
                text = alt2
        except Exception as e:
            print("[read_pdf] pdfminer error:", e)

    # 4) OCR con pytesseract
    if len(text) < 50:
        try:
            from pdf2image import convert_from_path
            import pytesseract
            print("[read_pdf] Activando OCR con Tesseract...")
            pages = convert_from_path(file_path, dpi=200)
            ocr_chunks = []
            for i, img in enumerate(pages, 1):
                t = pytesseract.image_to_string(img)
                print(f"[read_pdf] OCR página {i}: {len(t)} chars")
                if t.strip():
                    ocr_chunks.append(t)
            text = "\n".join(ocr_chunks).strip()
            print(f"[read_pdf] OCR total: {len(text)} chars")
        except Exception as e:
            print("[read_pdf] OCR error:", e)

    if text.strip():
        print(f"[read_pdf] Éxito: total {len(text)} chars extraídos")
        return text
    else:
        print("[read_pdf] ❌ No se pudo extraer texto del PDF")
        return None

# ================== Detección con LLM (Groq) ==================
def _safe_json_from_text(s: str) -> dict:
    """
    Intenta extraer y parsear JSON desde un texto posiblemente ruidoso.
    Repara cierres faltantes en listas y objetos si es necesario.
    """
    if not s:
        return {}

    # Buscar el bloque más grande que empieza con { y termina en }
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}

    candidate = s[start:end+1]

    try:
        return json.loads(candidate)
    except Exception as e:
        print("[_safe_json_from_text] Error parseando:", e, flush=True)

        # 🔹 Intento de reparación: cerrar arrays/objetos abiertos
        fixed = candidate.strip()
        if not fixed.endswith("}"):
            fixed += "}"
        if fixed.count("{") > fixed.count("}"):
            fixed += "}" * (fixed.count("{") - fixed.count("}"))
        if fixed.count("[") > fixed.count("]"):
            fixed += "]" * (fixed.count("[") - fixed.count("]"))

        try:
            return json.loads(fixed)
        except Exception as e2:
            print("[_safe_json_from_text] Error incluso tras reparar:", e2, flush=True)
            return {"detected_fields": []}

def detect_sensitive_data(text: str, prompt: str | None = None, mode: str = "Few-shot"):
    """
    Analiza 'text' con el LLM de Groq (modelo GROQ_MODEL) guiado por un prompt.
    - Si 'prompt' viene definido, se usa tal cual (+ inyección de texto).
    - Si no, se carga la plantilla de PROMPTS según 'mode' (por defecto Few-shot -> FS_prompt.txt).
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

        # 2) Llamada al modelo Groq
        # Nota: muchos modelos en Groq NO soportan response_format; instruimos al sistema
        # para que devuelva SOLO JSON y parseamos de forma robusta.
        sys_msg = (
            "Responde ÚNICAMENTE con un objeto JSON válido. "
            "No escribas texto adicional, ni explicaciones, ni formato markdown. "
            "El JSON debe contener como mínimo la clave 'detected_fields'."
        )

        try:
            resp = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": final_prompt},
                ],
                temperature=0,
                max_tokens=1500,
                # Groq sigue la API estilo OpenAI; evitar parámetros no soportados por algunos modelos.
            )
            content = (resp.choices[0].message.content or "").strip()
            print("[detect_sensitive_data] Respuesta cruda del modelo:", content[:500], flush=True)
        except Exception as e:
            # Reintento con una instrucción equivalente en español
            resp = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "Devuelve únicamente un objeto JSON válido. Sin texto adicional ni markdown.",
                    },
                    {"role": "user", "content": final_prompt},
                ],
                temperature=0,
                max_tokens=1500,
            )
            content = (resp.choices[0].message.content or "").strip()

        # 3) Parseo robusto
        result = _safe_json_from_text(content) or {"detected_fields": []}
        print("[detect_sensitive_data] JSON parseado:", result, flush=True)
        if "detected_fields" not in result or not isinstance(result["detected_fields"], list):
            result["detected_fields"] = []

        # Meta
        result["_prompt_source"] = prompt_info
        result["_model_used"] = GROQ_MODEL
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

# ================== Helper para PDF ==================
def detect_sensitive_pdf(file_path: str, mode: str = "Few-shot", prompt: str | None = None):
    """
    Analiza un PDF completo usando el LLM.
    - Divide el texto en fragmentos si es muy largo.
    - Agrega todos los campos detectados.
    Devuelve {"detected_fields": [...], "risk_level": "..."}.
    """
    text = read_pdf(file_path)
    if not text:
        return {"detected_fields": [], "risk_level": "None", "_error": "No se pudo leer el PDF"}

    # dividir en fragmentos de ~3000 caracteres
    chunk_size = 3000
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

    all_fields = []
    for i, chunk in enumerate(chunks, 1):
        print(f"[PDF Detector] Analizando fragmento {i}/{len(chunks)}...")
        result = detect_sensitive_data(chunk, prompt=prompt, mode=mode)
        all_fields.extend(result.get("detected_fields", []))

    # recalcular riesgo global
    final_risk = compute_risk_level(all_fields)
    return {
        "detected_fields": all_fields,
        "risk_level": final_risk,
        "_model_used": GROQ_MODEL,
        "_chunks": len(chunks),
    }
