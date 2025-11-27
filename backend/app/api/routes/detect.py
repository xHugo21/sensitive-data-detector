import os
import tempfile
from fastapi import APIRouter, UploadFile, File, Form
from typing import Optional
from app.utils.logger import debug_log
from multiagent_firewall import GuardOrchestrator
from app.config import MIN_BLOCK_RISK

router = APIRouter()


@router.post("/detect")
async def detect(
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
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
                "risk_level": "unknown",
                "error": "Either text or file must be provided",
            }

        # Handle file upload
        if file:
            tmp_dir = tempfile.gettempdir()
            tmp_path = os.path.join(tmp_dir, file.filename or "uploaded_file")

            with open(tmp_path, "wb") as f:
                f.write(await file.read())

            debug_log(f"[SensitiveDataDetectorBackend] Saved file to {tmp_path}")

            # Use orchestrator with file_path
            result = GuardOrchestrator().run(
                file_path=tmp_path,
                min_block_risk=MIN_BLOCK_RISK,
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
        debug_log("[SensitiveDataDetectorBackend] Processing text:", text)
        result = GuardOrchestrator().run(
            text=text,
            min_block_risk=MIN_BLOCK_RISK,
        )

        debug_log(
            "[SensitiveDataDetectorBackend] Detected fields:",
            result.get("detected_fields", []),
        )
        return result

    except Exception as e:
        debug_log("[SensitiveDataDetectorBackend] Error:", e)
        return {
            "detected_fields": [],
            "risk_level": "unknown",
            "error": str(e),
        }
