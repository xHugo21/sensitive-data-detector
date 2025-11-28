from pydantic import BaseModel


class DetectReq(BaseModel):
    text: str
    llm_prompt: str | None = None
