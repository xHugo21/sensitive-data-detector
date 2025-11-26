import os
import tempfile
from fastapi import APIRouter, UploadFile, File, Form
from typing import Optional
from app.utils.logger import debug_log
from multiagent_firewall import GuardOrchestrator

router = APIRouter()


@router.post("/detect")
async def detect(
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    mode: Optional[str] = Form(None),
):
    """
    Unified detection endpoint that accepts either text or file.

    Args:
        text: Direct text input
        file: File upload (PDF, TXT, etc.)
        mode: Detection mode (zero-shot, few-shot, enriched-zero-shot)

    Returns:
        Detection results with risk level, detected fields, and remediation
    """
    try:
        # Validate that at least one input is provided
        if not text and not file:
            return {
                "detected_fields": [],
                "risk_level": "Unknown",
                "error": "Either text or file must be provided",
            }

        # Handle file upload
        if file:
            tmp_dir = tempfile.gettempdir()
            tmp_path = os.path.join(tmp_dir, file.filename or "uploaded_file")

            with open(tmp_path, "wb") as f:
                f.write(await file.read())

            debug_log(f"[backend] Saved file to {tmp_path}")

            # Use orchestrator with file_path
            result = GuardOrchestrator().run(
                file_path=tmp_path,
                mode=mode,
            )

            # Add snippet of extracted text
            if result.get("raw_text"):
                result["extracted_snippet"] = result["raw_text"][:400]

            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except:
                pass

            return result

        # Handle text input
        debug_log("[backend] Processing text:", text)
        debug_log("[backend] Mode:", mode)

        result = GuardOrchestrator().run(
            text=text,
            mode=mode,
        )

        debug_log("[backend] Detected fields:", result.get("detected_fields", []))
        return result

    except Exception as e:
        debug_log("[backend] Error:", e)
        return {
            "detected_fields": [],
            "risk_level": "Unknown",
            "error": str(e),
        }
