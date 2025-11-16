import os
import tempfile
from fastapi import APIRouter, UploadFile, File, Form
from api.models.request import DetectReq
from core.detector import detect_sensitive_data
from core.risk import compute_risk_level
from services.document_reader import read_document
from utils.logger import debug_log

router = APIRouter()


@router.post("/detect")
def detect(req: DetectReq):
    debug_log("\n===== TEXTO EXTRAÍDO =====")
    debug_log(req.text)
    debug_log("\n===== MODO =====")
    debug_log(req.mode)
    debug_log("========================================\n")
    result = detect_sensitive_data(req.text, prompt=req.prompt, mode=req.mode)
    debug_log("\n===== DETECTED FIELDS =====")
    debug_log(result.get("detected_fields", []))
    debug_log("========================================\n")
    result["risk_level"] = compute_risk_level(result.get("detected_fields", []))
    return result


@router.post("/detect_file")
async def detect_file(
    file: UploadFile = File(...),
    mode: str | None = Form(None),
    prompt: str = Form(None),
):
    try:
        tmp_dir = tempfile.gettempdir()
        tmp_path = os.path.join(tmp_dir, file.filename or "uploaded_file")
        with open(tmp_path, "wb") as f:
            f.write(await file.read())

        debug_log(f"[detect_file] Guardado en {tmp_path}")

        text = read_document(tmp_path)
        if not text:
            debug_log("[detect_file] ❌ No se pudo extraer texto")
            return {
                "detected_fields": [],
                "risk_level": "Unknown",
                "error": "No text extracted",
                "extracted_snippet": "",
            }

        debug_log("\n===== TEXTO EXTRAÍDO =====")
        debug_log(text)
        debug_log("========================================\n")

        result = detect_sensitive_data(text, prompt=prompt, mode=mode)
        result["risk_level"] = compute_risk_level(result.get("detected_fields", []))
        result["extracted_snippet"] = text[:400]

        return result

    except Exception as e:
        debug_log("[detect_file] ⚠️ Error:", e)
        return {
            "detected_fields": [],
            "risk_level": "Unknown",
            "error": str(e),
            "extracted_snippet": "",
        }
