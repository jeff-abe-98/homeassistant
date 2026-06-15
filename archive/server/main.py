from __future__ import annotations

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

import shared.config as cfg_module
from shared.config import AppConfig
from shared.models import AssistantResponse, AudioChunk, Transcript
from server.llm.client import OllamaClient
from server.llm.prompts import build_system_prompt
from server.llm.router import ToolRouter
from server.logging_config import setup_logging
from server.stt.transcriber import WhisperTranscriber
from server.tools.base import ToolRegistry
from server.tool_creator.generator import ToolGenerator
from server.tool_creator.validator import validate
from server.tool_creator.installer import install
logger = logging.getLogger(__name__)

_config: AppConfig | None = None
_llm: OllamaClient | None = None
_stt: WhisperTranscriber | None = None
_registry: ToolRegistry | None = None
_router: ToolRouter | None = None
_generator: ToolGenerator | None = None
_audio_buffers: dict[str, list[AudioChunk]] = {}

# Phrases that suggest the LLM cannot fulfil the request with its built-in knowledge.
# When matched in the router's fallback text, we trigger background tool creation.
_CANNOT_HELP_PHRASES = frozenset({
    "i don't have", "i do not have", "i can't", "i cannot", "unable to",
    "don't have access", "do not have access", "i'm not able", "i am not able",
    "not capable", "no tool", "don't know how", "can't help with that",
    "not something i can", "not able to", "don't support", "no capability",
})

_LLM_ERROR_MSG = "Sorry, I'm having trouble connecting right now. Please try again in a moment."
_TOOL_ERROR_MSG = "Sorry, I ran into a problem with that. Please try again."


def _heuristic_needs_tool(text: str) -> bool:
    """Return True if the LLM response indicates an unmet capability."""
    lower = text.lower()
    return any(phrase in lower for phrase in _CANNOT_HELP_PHRASES)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _config, _llm, _stt, _registry, _router, _generator
    _config = cfg_module.load()
    setup_logging(_config)
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
    active_sessions: set[str] = set()
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Ignoring malformed JSON from client: %r", raw[:200])
                continue

            if "audio_bytes" in msg:
                chunk = AudioChunk.model_validate(msg)
                active_sessions.add(chunk.session_id)
                result = await _handle_audio_chunk(chunk)
                if result is not None:
                    active_sessions.discard(result.session_id)
                    await websocket.send_text(result.model_dump_json())
            elif "text" in msg:
                result = await _handle_transcript(Transcript.model_validate(msg), websocket)
                if result is not None:
                    await websocket.send_text(result.model_dump_json())

    except WebSocketDisconnect:
        logger.info("Client disconnected: %s", websocket.client)
    finally:
        # Clean up audio buffers orphaned by a mid-stream disconnect
        for sid in active_sessions:
            _audio_buffers.pop(sid, None)
        if active_sessions:
            logger.info("Cleaned up %d orphaned audio buffer(s)", len(active_sessions))


async def _handle_audio_chunk(chunk: AudioChunk) -> Transcript | None:
    _audio_buffers.setdefault(chunk.session_id, []).append(chunk)
    if not chunk.is_final:
        return None
    chunks = _audio_buffers.pop(chunk.session_id)
    chunks.sort(key=lambda c: c.sequence)
    combined = b"".join(c.audio_bytes for c in chunks)
    sample_rate = chunks[0].sample_rate
    t0 = time.perf_counter()
    try:
        text = await asyncio.get_event_loop().run_in_executor(
            None, _stt.transcribe, combined, sample_rate
        )
    except Exception:
        logger.exception("STT failed for session [%s] — dropping chunk", chunk.session_id)
        return None
    logger.info("STT [%s] %.2fs: %r", chunk.session_id, time.perf_counter() - t0, text)
    return Transcript(session_id=chunk.session_id, text=text)


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
    t0 = time.perf_counter()
    tool_call: object = None
    fallback_text = ""

    # Single LLM call: route to an existing tool OR get a conversational response.
    try:
        tool_call, fallback_text = await _router.route(transcript)
        logger.info(
            "Route [%s] %.2fs — %s",
            transcript.session_id,
            time.perf_counter() - t0,
            f"tool={tool_call.tool_name}" if tool_call else "no tool",
        )
    except Exception:
        logger.exception(
            "Tool router failed for [%s] — falling back to direct LLM", transcript.session_id
        )

    # --- Existing tool matched ---
    if tool_call is not None:
        tool = _registry.get(tool_call.tool_name)
        if tool is not None:
            logger.info(
                "Tool [%s]: %s %s", transcript.session_id, tool_call.tool_name, tool_call.params
            )
            t1 = time.perf_counter()
            try:
                reply = await tool.run(tool_call.params, transcript.user)
            except Exception:
                logger.exception(
                    "Tool %r raised an error for [%s]", tool_call.tool_name, transcript.session_id
                )
                return AssistantResponse(session_id=transcript.session_id, text=_TOOL_ERROR_MSG)
            logger.info(
                "Tool [%s] %.2fs: %r", transcript.session_id, time.perf_counter() - t1, reply
            )
            return AssistantResponse(session_id=transcript.session_id, text=reply)
        logger.warning("Tool %r selected but not found in registry", tool_call.tool_name)

    # --- No existing tool: use the LLM's conversational response from the router call ---
    if fallback_text:
        if _heuristic_needs_tool(fallback_text):
            logger.info("Triggering tool creation for intent: %r", transcript.text)
            asyncio.create_task(_create_and_notify(transcript, websocket))
            return AssistantResponse(
                session_id=transcript.session_id,
                text="I don't know how to do that yet, but I'll figure it out. I'll let you know when I can.",
            )
        logger.info(
            "LLM [%s] %.2fs: %r", transcript.session_id, time.perf_counter() - t0, fallback_text
        )
        return AssistantResponse(session_id=transcript.session_id, text=fallback_text)

    # --- Router failed entirely: direct LLM call as last resort ---
    try:
        t1 = time.perf_counter()
        system_prompt = build_system_prompt(transcript.user)
        reply = await _llm.complete(system_prompt, transcript.text)
        logger.info(
            "LLM fallback [%s] %.2fs: %r", transcript.session_id, time.perf_counter() - t1, reply
        )
    except Exception:
        logger.exception("LLM completion failed for [%s]", transcript.session_id)
        return AssistantResponse(session_id=transcript.session_id, text=_LLM_ERROR_MSG)

    return AssistantResponse(session_id=transcript.session_id, text=reply)
