import os
import tempfile
from fastapi import APIRouter, UploadFile, File, Form
from app.api.models.request import DetectReq
from app.guard import run_guard_pipeline
from app.services.document_reader import read_document
from app.utils.logger import debug_log

router = APIRouter()


@router.post("/detect")
def detect(req: DetectReq):
    debug_log("Extracted text:", req.text)
    debug_log("Mode:", req.mode)
    result = run_guard_pipeline(
        req.text,
        prompt=req.prompt,
        mode=req.mode,
        metadata={"source": "text"},
    )
    debug_log("Detected fields:", result.get("detected_fields", []))
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

        debug_log(f"[detect_file] Saved to {tmp_path}")

        text = read_document(tmp_path)
        if not text:
            debug_log("[detect_file] Could not extract text")
            return {
                "detected_fields": [],
                "risk_level": "Unknown",
                "error": "No text extracted",
                "extracted_snippet": "",
            }

        debug_log("Extracted text from file:", text)

        result = run_guard_pipeline(
            text,
            prompt=prompt,
            mode=mode,
            metadata={
                "source": "file",
                "filename": file.filename,
                "content_type": file.content_type,
            },
        )
        result["extracted_snippet"] = text[:400]

        return result

    except Exception as e:
        debug_log("[detect_file] Error:", e)
        return {
            "detected_fields": [],
            "risk_level": "Unknown",
            "error": str(e),
            "extracted_snippet": "",
        }
