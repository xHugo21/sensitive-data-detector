# server.py
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from Middleware import detect_sensitive_data, compute_risk_level  # tus funciones

class DetectReq(BaseModel):
    text: str
    mode: str | None = "Zero-shot"            # "Zero-shot", "Zero-shot enriquecido", "Few-shot"
    prompt: str | None = None                 # si quieres forzar prompt
    min_length: int | None = 0                # filtro opcional

app = FastAPI()

# CORS: permite llamadas desde extensión/userscript
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # o restringe si quieres
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/detect")
def detect(req: DetectReq):
    txt = (req.text or "").strip()
    if req.min_length and len(txt) < req.min_length:
        return {"detected_fields": [], "risk_level": "None"}

    result = detect_sensitive_data(txt, prompt=req.prompt, mode=req.mode)
    risk = compute_risk_level(result.get("detected_fields", []))
    return {"detected_fields": result.get("detected_fields", []), "risk_level": risk}

if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8787, reload=True)
