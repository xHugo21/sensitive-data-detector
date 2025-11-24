from pydantic import BaseModel

class DetectReq(BaseModel):
    text: str
    mode: str | None = None
