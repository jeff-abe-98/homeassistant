from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

import shared.config as cfg_module
from shared.config import AppConfig
from shared.models import AssistantResponse, AudioChunk, Transcript
from server.llm.client import OllamaClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_config: AppConfig | None = None
_llm: OllamaClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _config, _llm
    _config = cfg_module.load()
    _llm = OllamaClient(_config.ollama)
    logger.info("Server ready — model: %s", _config.ollama.model)
    yield
    logger.info("Server shut down")


app = FastAPI(title="Home Assistant Server", lifespan=lifespan)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.info("Client connected: %s", websocket.client)
    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)

            if "audio_bytes" in msg:
                result = await _handle_audio_chunk(AudioChunk.model_validate(msg))
                if result is not None:
                    await websocket.send_text(result.model_dump_json())
            elif "text" in msg:
                result = await _handle_transcript(Transcript.model_validate(msg))
                if result is not None:
                    await websocket.send_text(result.model_dump_json())

    except WebSocketDisconnect:
        logger.info("Client disconnected: %s", websocket.client)


async def _handle_audio_chunk(chunk: AudioChunk) -> Transcript | None:
    """Receive AudioChunk stream, run STT, return Transcript. Implemented in next task."""
    return None


async def _handle_transcript(transcript: Transcript) -> AssistantResponse | None:
    """Receive Transcript, run LLM, return AssistantResponse. Implemented in next task."""
    return None
