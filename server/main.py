from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

import shared.config as cfg_module
from shared.config import AppConfig
from shared.models import AssistantResponse, AudioChunk, Transcript
from server.llm.client import OllamaClient
from server.llm.prompts import build_system_prompt
from server.llm.router import ToolRouter
from server.stt.transcriber import WhisperTranscriber
from server.tools.base import ToolRegistry
from server.tool_creator.generator import ToolGenerator
from server.tool_creator.validator import validate
from server.tool_creator.installer import install

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_config: AppConfig | None = None
_llm: OllamaClient | None = None
_stt: WhisperTranscriber | None = None
_registry: ToolRegistry | None = None
_router: ToolRouter | None = None
_generator: ToolGenerator | None = None
_audio_buffers: dict[str, list[AudioChunk]] = {}

_NEEDS_TOOL_SYSTEM = (
    "You classify user requests. "
    "Reply with exactly 'yes' if the request requires any external capability "
    "(data lookup, device control, API call, home automation, media control, etc.). "
    "Reply with exactly 'no' if it is purely conversational (chat, math, general knowledge)."
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _config, _llm, _stt, _registry, _router, _generator
    _config = cfg_module.load()
    _llm = OllamaClient(_config.ollama)
    _stt = WhisperTranscriber(
        model=_config.whisper.model,
        device=_config.whisper.device,
        compute_type=_config.whisper.compute_type,
    )
    _registry = ToolRegistry()
    _registry.load()
    _router = ToolRouter(_llm, _registry)
    _generator = ToolGenerator(_llm)
    logger.info(
        "Server ready — LLM: %s  STT: %s  tools: %d",
        _config.ollama.model,
        _config.whisper.model,
        len(_registry.all()),
    )
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
                result = await _handle_transcript(Transcript.model_validate(msg), websocket)
                if result is not None:
                    await websocket.send_text(result.model_dump_json())

    except WebSocketDisconnect:
        logger.info("Client disconnected: %s", websocket.client)


async def _handle_audio_chunk(chunk: AudioChunk) -> Transcript | None:
    _audio_buffers.setdefault(chunk.session_id, []).append(chunk)
    if not chunk.is_final:
        return None
    chunks = _audio_buffers.pop(chunk.session_id)
    chunks.sort(key=lambda c: c.sequence)
    combined = b"".join(c.audio_bytes for c in chunks)
    sample_rate = chunks[0].sample_rate
    text = await asyncio.get_event_loop().run_in_executor(
        None, _stt.transcribe, combined, sample_rate
    )
    logger.info("STT [%s]: %r", chunk.session_id, text)
    return Transcript(session_id=chunk.session_id, text=text)


async def _needs_new_tool(text: str) -> bool:
    """Ask the LLM whether the request requires an external capability not yet available."""
    reply = await _llm.complete(_NEEDS_TOOL_SYSTEM, text)
    return reply.strip().lower().startswith("yes")


async def _create_and_notify(transcript: Transcript, websocket: WebSocket) -> None:
    """Background task: generate → validate → install a new tool, then notify the user."""
    try:
        existing_names = [t.name for t in _registry.all()]
        source = await _generator.generate(transcript.text, existing_names)
        result = await validate(source)
        if not result.success:
            logger.warning(
                "Tool creation validation failed for %r: %s", transcript.text, result.error
            )
            return
        inst = install(source, result.tool_name, _registry)
        if not inst.success:
            logger.warning(
                "Tool creation install failed for %r: %s", transcript.text, inst.error
            )
            return
        logger.info("New tool installed: %s at %s", inst.tool_name, inst.path)
        notification = AssistantResponse(
            session_id=transcript.session_id,
            text="I can do that now — want to try?",
        )
        try:
            await websocket.send_text(notification.model_dump_json())
        except Exception:
            logger.warning("Could not send tool-ready notification — WebSocket may be closed")
    except Exception:
        logger.exception("Background tool creation failed for intent %r", transcript.text)


async def _handle_transcript(transcript: Transcript, websocket: WebSocket) -> AssistantResponse | None:
    tool_call = await _router.route(transcript)

    if tool_call is not None:
        tool = _registry.get(tool_call.tool_name)
        if tool is not None:
            logger.info("Tool [%s]: %s %s", transcript.session_id, tool_call.tool_name, tool_call.params)
            reply = await tool.run(tool_call.params, transcript.user)
            logger.info("Tool result [%s]: %r", transcript.session_id, reply)
            return AssistantResponse(session_id=transcript.session_id, text=reply)
        logger.warning("Tool %r selected but not found in registry", tool_call.tool_name)

    # No existing tool matched. Check if this request needs a new tool to be created.
    if await _needs_new_tool(transcript.text):
        logger.info("Triggering tool creation for intent: %r", transcript.text)
        asyncio.create_task(_create_and_notify(transcript, websocket))
        return AssistantResponse(
            session_id=transcript.session_id,
            text="I don't know how to do that yet, but I'll figure it out. I'll let you know when I can.",
        )

    system_prompt = build_system_prompt(transcript.user)
    reply = await _llm.complete(system_prompt, transcript.text)
    logger.info("LLM [%s]: %r", transcript.session_id, reply)
    return AssistantResponse(session_id=transcript.session_id, text=reply)
