from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def root():
    return {"status": "ok", "service": "Sensitive LLM Detector"}

@router.get("/healthz")
def health():
    return {"ok": True}
