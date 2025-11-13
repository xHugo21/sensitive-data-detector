# app.py
import os
import tempfile
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .detector import detect_sensitive_data, compute_risk_level, read_document

load_dotenv()

# ===================== Configuración =====================
PORT = int(os.getenv("PORT", "8000"))

ALLOW_ORIGINS = [
    "https://chatgpt.com",
    "https://chat.openai.com",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

app = FastAPI(title="Sensitive LLM Detector", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_origin_regex=r"chrome-extension://.*",
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

# ===================== Modelos =====================
class DetectReq(BaseModel):
    text: str
    mode: str | None = "Zero-shot"
    prompt: str | None = None

# ===================== Endpoints =====================
@app.get("/")
def root():
    return {"status": "ok", "service": "Sensitive LLM Detector"}

@app.get("/healthz")
def health():
    return {"ok": True}

@app.post("/detect")
def detect(req: DetectReq):
    """
    Analiza texto plano enviado por el usuario.
    """
    result = detect_sensitive_data(req.text, prompt=req.prompt, mode=req.mode or "Zero-shot")
    result["risk_level"] = compute_risk_level(result.get("detected_fields", []))
    return result

@app.post("/detect_file")
async def detect_file(file: UploadFile = File(...), mode: str = Form("Zero-shot"), prompt: str = Form(None)):
    try:
        # Guardar archivo temporal (compatible con Windows/Linux/Mac)
        tmp_dir = tempfile.gettempdir()
        tmp_path = os.path.join(tmp_dir, file.filename)
        with open(tmp_path, "wb") as f:
            f.write(await file.read())

        print(f"[detect_file] Guardado en {tmp_path}", flush=True)  # 🔹 log inmediato

        # Leer documento
        text = read_document(tmp_path)
        if not text:
            print("[detect_file] ❌ No se pudo extraer texto", flush=True)
            return {
                "detected_fields": [],
                "risk_level": "Unknown",
                "error": "No text extracted",
                "extracted_snippet": ""
            }

        print("\n===== TEXTO EXTRAÍDO =====", flush=True)
        print(text, flush=True)  # 🔹 imprime el texto completo
        print("========================================\n", flush=True)

        # Pasar al detector
        result = detect_sensitive_data(text, prompt=prompt, mode=mode)
        result["risk_level"] = compute_risk_level(result.get("detected_fields", []))
        result["extracted_snippet"] = text[:400]

        return result

    except Exception as e:
        print("[detect_file] ⚠️ Error:", e, flush=True)
        return {
            "detected_fields": [],
            "risk_level": "Unknown",
            "error": str(e),
            "extracted_snippet": ""
        }
# ===================== Dev server =====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=PORT, reload=True)
