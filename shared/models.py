from __future__ import annotations
from pydantic import BaseModel


class AudioChunk(BaseModel):
    session_id: str
    sequence: int
    audio_bytes: bytes  # serialized as base64 in JSON (Pydantic v2 default)
    sample_rate: int = 16000
    is_final: bool = False


class Transcript(BaseModel):
    session_id: str
    text: str


class SpeakerResult(BaseModel):
    session_id: str
    user: str
    confidence: float


class AssistantResponse(BaseModel):
    session_id: str
    text: str
