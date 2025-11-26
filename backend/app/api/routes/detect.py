from fastapi import APIRouter
from app.api.models.request import DetectReq
from app.utils.logger import debug_log
from multiagent_firewall import GuardOrchestrator

router = APIRouter()


@router.post("/detect")
def detect(req: DetectReq):
    debug_log("Extracted text:", req.text)
    debug_log("Mode:", req.mode)
    result = GuardOrchestrator().run(
        req.text,
        mode=req.mode,
    )
    debug_log("Detected fields:", result.get("detected_fields", []))
    return result
