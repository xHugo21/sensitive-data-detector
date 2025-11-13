import os
import tempfile
from fastapi import APIRouter, UploadFile, File, Form
from ...api.models.request import DetectReq
from ...core.detector import detect_sensitive_data
from ...core.risk import compute_risk_level
from ...services.document_reader import read_document

router = APIRouter()

@router.post("/detect")
def detect(req: DetectReq):
    result = detect_sensitive_data(req.text, prompt=req.prompt, mode=req.mode or "Zero-shot")
    result["risk_level"] = compute_risk_level(result.get("detected_fields", []))
    return result

@router.post("/detect_file")
async def detect_file(file: UploadFile = File(...), mode: str = Form("Zero-shot"), prompt: str = Form(None)):
    try:
        tmp_dir = tempfile.gettempdir()
        tmp_path = os.path.join(tmp_dir, file.filename or "uploaded_file")
        with open(tmp_path, "wb") as f:
            f.write(await file.read())

        print(f"[detect_file] Guardado en {tmp_path}", flush=True)

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
        print(text, flush=True)
        print("========================================\n", flush=True)

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
