import json
import os
import tempfile
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional
from app.utils import debug_log
from multiagent_firewall import GuardOrchestrator, ToolCallingGuardOrchestrator
from app.config import GUARD_CONFIG, MIN_BLOCK_RISK, USE_TOOL_CALLING_ORCHESTRATOR

router = APIRouter()


def _get_orchestrator():
    if USE_TOOL_CALLING_ORCHESTRATOR:
        return ToolCallingGuardOrchestrator(GUARD_CONFIG)
    return GuardOrchestrator(GUARD_CONFIG)


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
            result = _get_orchestrator().run(
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
        result = _get_orchestrator().run(
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


@router.post("/detect/stream")
async def detect_stream(
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    if not text and not file:
        return JSONResponse(
            status_code=400,
            content={
                "detected_fields": [],
                "risk_level": "unknown",
                "error": "Either text or file must be provided",
            },
        )

    tmp_path = None
    if file:
        tmp_dir = tempfile.gettempdir()
        tmp_path = os.path.join(tmp_dir, file.filename or "uploaded_file")

        with open(tmp_path, "wb") as f:
            f.write(await file.read())

        debug_log(f"[SensitiveDataDetectorBackend] Saved file to {tmp_path}")

    orchestrator = _get_orchestrator()
    initial_state, updates = orchestrator.stream_updates(
        text=text,
        file_path=tmp_path,
        min_block_risk=MIN_BLOCK_RISK,
        stream_mode=["tasks", "updates"],
    )

    def iter_events():
        state = dict(initial_state)
        try:
            for chunk in updates:
                mode = "updates"
                payload = chunk
                if isinstance(chunk, tuple) and len(chunk) == 2:
                    mode, payload = chunk

                if mode == "tasks":
                    if isinstance(payload, dict):
                        node = payload.get("name")
                        if not node or str(node).startswith("__"):
                            continue
                        status = (
                            "completed"
                            if "result" in payload or payload.get("error")
                            else "running"
                        )
                        detected_fields = state.get("detected_fields", [])
                        detected_count = (
                            len(detected_fields)
                            if isinstance(detected_fields, list)
                            else 0
                        )
                        yield json.dumps(
                            jsonable_encoder(
                                {
                                    "type": "node",
                                    "node": node,
                                    "status": status,
                                    "detected_count": detected_count,
                                }
                            )
                        ) + "\n"
                    continue

                if mode == "updates" and isinstance(payload, dict):
                    for node, update in payload.items():
                        if not isinstance(update, dict):
                            continue
                        state.update(update)
            if state.get("raw_text"):
                state["extracted_snippet"] = state["raw_text"][:400]
            yield json.dumps(
                jsonable_encoder({"type": "result", "result": state})
            ) + "\n"
        except Exception as exc:
            payload = {"type": "error", "error": str(exc)}
            yield json.dumps(jsonable_encoder(payload)) + "\n"
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    return StreamingResponse(iter_events(), media_type="application/x-ndjson")
