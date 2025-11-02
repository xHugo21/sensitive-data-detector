# server.py (resumen)
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# Allow importing detector modules from ./server without packaging the folder
import os
import sys

BASE_DIR = os.path.dirname(__file__)
SERVER_DIR = os.path.join(BASE_DIR, "server")
if SERVER_DIR not in sys.path:
    sys.path.append(SERVER_DIR)

from detector_gpt_oss_120b import detect_sensitive_data, compute_risk_level

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en producción: restringe
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "API OK. POST /analyze"}

@app.post("/analyze")
async def analyze(request: Request):
    body = await request.json()
    text = body.get("text", "")
    pii = detect_sensitive_data(text)  # devuelve {"detected_fields":[...]}
    level = compute_risk_level(pii.get("detected_fields", []))
    pii["risk_level"] = level
    return pii
