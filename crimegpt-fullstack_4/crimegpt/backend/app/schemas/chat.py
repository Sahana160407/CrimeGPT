from pydantic import BaseModel


class ChatMessage(BaseModel):
    sender: str
    text: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] | None = []


class FirNumberRequest(BaseModel):
    firNumber: str


class SpeakRequest(BaseModel):
    text: str
