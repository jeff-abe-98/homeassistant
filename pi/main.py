"""Unified Pi voice assistant — wake word → STT → LLM → tool/TTS → audio."""
from __future__ import annotations

import asyncio
import logging
import sqlite3
import threading
import uuid

from pi.audio.capture import SAMPLE_RATE, VoiceCapture
from pi.audio.playback import AudioPlayer
from pi.llm.hailo_client import HailoLLMClient
from pi.llm.router import ToolRouter
from pi.memory.db import init_db
from pi.memory.session import Session, log_activation
from pi.speaker_id.identify import identify
from pi.stt.hailo_transcriber import HailoTranscriber
from pi.tools.base import ToolRegistry
from pi.tts.piper import PiperTTS
from pi.wake_word.detector import WakeWordDetector
from shared.config import AppConfig
from shared.config import load as load_config
from shared.models import AudioChunk, Transcript

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

_MEMORY_DB_PATH = "memory.db"


# ---------------------------------------------------------------------------
# Audio capture
# ---------------------------------------------------------------------------


async def _capture_utterance() -> tuple[bytes, int]:
    """Capture one spoken utterance via VAD. Returns (pcm_bytes, sample_rate)."""
    loop = asyncio.get_running_loop()
    chunk_queue: asyncio.Queue[AudioChunk] = asyncio.Queue()
    capture = VoiceCapture()

    def _feed() -> None:
        for chunk in capture.stream():
            asyncio.run_coroutine_threadsafe(chunk_queue.put(chunk), loop)
            if chunk.is_final:
                break

    feed_thread = threading.Thread(target=_feed, daemon=True)
    feed_thread.start()

    pcm_chunks: list[bytes] = []
    sample_rate = SAMPLE_RATE

    while True:
        chunk = await chunk_queue.get()
        sample_rate = chunk.sample_rate
        if chunk.audio_bytes:
            pcm_chunks.append(chunk.audio_bytes)
        if chunk.is_final:
            break

    feed_thread.join(timeout=2.0)
    return b"".join(pcm_chunks), sample_rate


# ---------------------------------------------------------------------------
# Tool hot-reload
# ---------------------------------------------------------------------------


def _reload_tools(registry: ToolRegistry, known_names: set[str]) -> list[str]:
    """Reload registry; return sorted names of tools new since last call."""
    registry.load()
    current_names = {t.name for t in registry.all()}
    new_names = sorted(current_names - known_names)
    known_names.clear()
    known_names.update(current_names)
    return new_names


# ---------------------------------------------------------------------------
# Per-activation pipeline
# ---------------------------------------------------------------------------


async def _handle_activation(
    config: AppConfig,
    stt: HailoTranscriber,
    router: ToolRouter,
    registry: ToolRegistry,
    tts: PiperTTS,
    player: AudioPlayer,
    conn: sqlite3.Connection,
    known_tool_names: set[str],
) -> None:
    """Process one wake-word activation end-to-end."""
    loop = asyncio.get_running_loop()

    # Pick up any tools the remote agent pushed since the last activation
    new_tool_names = _reload_tools(registry, known_tool_names)

    # Capture the spoken utterance
    pcm_bytes, sample_rate = await _capture_utterance()

    # Identify speaker on CPU while STT runs on Hailo NPU
    user, transcript_text = await asyncio.gather(
        loop.run_in_executor(None, identify, pcm_bytes, sample_rate),
        stt.transcribe(pcm_bytes, sample_rate),
    )
    logger.info("Speaker: %s  Transcript: %r", user, transcript_text)

    log_activation(conn, user)

    if not transcript_text.strip():
        logger.info("Empty transcript — skipping LLM step")
        return

    # Load recent conversation context from memory
    session = Session(conn)
    session.start(user)
    context_turns = session.get_context_turns(config.memory.context_turns)

    # Route the utterance through the LLM
    transcript = Transcript(
        session_id=str(uuid.uuid4()),
        text=transcript_text,
        user=user,
    )
    tool_call, fallback_text = await router.route(transcript, context_turns)

    # Execute the selected tool, or fall back to the LLM's conversational reply
    if tool_call:
        tool = registry.get(tool_call.tool_name)
        if tool is None:
            logger.warning("Router chose unknown tool %r", tool_call.tool_name)
            response_text = (
                fallback_text
                or f"I tried to use {tool_call.tool_name}, but it wasn't available."
            )
        else:
            try:
                response_text = await tool.run(tool_call.params, user)
            except Exception:
                logger.exception("Tool %r failed", tool_call.tool_name)
                response_text = (
                    "Sorry, I had trouble completing that. Please try again."
                )
    else:
        response_text = fallback_text or "I'm not sure how to help with that."

    # Announce tools that arrived from the remote agent since the last activation
    if new_tool_names:
        tool_list = ", ".join(new_tool_names)
        response_text = f"By the way, I can now {tool_list}. {response_text}"

    # Persist the conversation turn in session memory
    session.add_turn(transcript_text, response_text)
    session.end()

    # Synthesise and play the response
    audio = await loop.run_in_executor(None, tts.synthesize, response_text)
    await loop.run_in_executor(None, player.play, audio)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main() -> None:
    config: AppConfig = load_config()

    stt = HailoTranscriber(config.hailo)
    llm = HailoLLMClient(config.hailo)
    conn = init_db(_MEMORY_DB_PATH)

    registry = ToolRegistry()
    registry.load()
    known_tool_names: set[str] = {t.name for t in registry.all()}
    router = ToolRouter(llm, registry)

    tts = PiperTTS(config.tts.model_path, use_cuda=config.tts.use_cuda)
    player = AudioPlayer(sample_rate=tts.sample_rate)

    try:
        while True:
            wake_event = asyncio.Event()
            loop = asyncio.get_running_loop()
            detector = WakeWordDetector(
                config=config.wake_word,
                on_detection=lambda: loop.call_soon_threadsafe(wake_event.set),
            )
            detector.start()
            logger.info("Listening for wake word…")
            await wake_event.wait()
            detector.stop()
            logger.info("Wake word detected — processing utterance")

            try:
                await _handle_activation(
                    config,
                    stt,
                    router,
                    registry,
                    tts,
                    player,
                    conn,
                    known_tool_names,
                )
            except Exception:
                logger.exception("Activation pipeline failed")
    finally:
        llm.close()
        stt.close()
        conn.close()


if __name__ == "__main__":
    asyncio.run(main())
