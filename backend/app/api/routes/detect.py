import os
import tempfile
from fastapi import APIRouter, UploadFile, File, Form
from typing import Optional
from app.utils import debug_log
from multiagent_firewall import GuardOrchestrator
from app.config import GUARD_CONFIG, DEFAULT_BLOCK_LEVEL

router = APIRouter()


@router.post("/detect")
async def detect(
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    min_block_level: Optional[str] = Form(None),
):
    """
    Unified detection endpoint that accepts either text or file.

    Args:
        text: Direct text input
        file: File upload (PDF, TXT, etc.)
        min_block_level: Minimum risk level to trigger blocking actions

    Returns:
        Detection results with risk level, detected fields, and remediation
    """
    try:
        # Use provided level or fallback to global default
        block_level = min_block_level or DEFAULT_BLOCK_LEVEL

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
            result = await GuardOrchestrator(GUARD_CONFIG).run(
                file_path=tmp_path,
                min_block_level=block_level,
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
        result = await GuardOrchestrator(GUARD_CONFIG).run(
            text=text,
            min_block_level=block_level,
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
