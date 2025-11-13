from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import PORT, ALLOW_ORIGINS
from api.routes.health import router as health_router
from api.routes.detect import router as detect_router

app = FastAPI(title="Sensitive LLM Detector", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_origin_regex=r"chrome-extension://.*",
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

app.include_router(health_router)
app.include_router(detect_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=PORT, reload=True)
