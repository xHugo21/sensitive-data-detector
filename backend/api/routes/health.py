from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def root():
    return {"status": "ok", "service": "Sensitive LLM Detector"}


@router.get("/health")
def health():
    return {"ok": True}
