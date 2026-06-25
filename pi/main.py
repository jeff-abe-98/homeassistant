"""Unified Pi voice assistant — wake word → STT → LLM → tool/TTS → audio."""
from __future__ import annotations

import asyncio
import logging
import sqlite3
import threading
import time
import uuid

import numpy as np

from pi.audio.capture import SAMPLE_RATE, VoiceCapture
from pi.audio.playback import AudioPlayer
from pi.llm.hailo_client import HailoLLMClient
from pi.llm.router import ToolRouter
from pi.memory.db import init_db
from pi.memory.session import Session, log_activation
from pi.scheduler.prewarm import PrewarmScheduler
from pi.speaker_id.identify import identify
from pi.stt.hailo_transcriber import HailoTranscriber
from pi.tool_requests import github_sync
from pi.tool_requests.models import ToolRequest
from pi.tool_requests.queue import ToolRequestQueue
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

_INABILITY_PHRASES = (
    "don't know how to do that",
    "not sure how to help",
    "can't do that",
    "i'm unable",
    "unable to do that",
    "don't have the ability",
    "not something i can",
    "i don't know how",
    "can't help with that",
    "not able to",
    "don't know how to",
)

# Keyword fallback for when the 1.5B model fails to produce a <tool_call>.
# Each entry maps a registered tool name to trigger phrases.
_KEYWORD_ROUTES: list[tuple[str, tuple[str, ...]]] = [
    ("get_weather",        ("weather", "temperature", "forecast", "rain", "snow",
                            "wind", "sunny", "cloudy", "humidity", "degrees",
                            "hot outside", "cold outside", "warm outside")),
    ("cta_arrivals",       ("train", "cta", "blue line", "el ", "arrival",
                            "transit", "next train", "when does the")),
    ("get_calendar_events",("calendar", "my schedule", "what do i have",
                            "what's on my", "appointments", "events today",
                            "events tomorrow")),
    ("add_calendar_event", ("add.*to.*calendar", "schedule.*meeting",
                            "put.*on.*calendar", "set.*appointment")),
    ("spotify_control",    ("play ", "pause", "skip", "next song", "stop music",
                            "spotify", "shuffle", "volume")),
    ("list_tasks",         ("my tasks", "to.?do list", "what.*remind",
                            "show.*tasks", "list.*tasks")),
    ("add_task",           ("add.*task", "remind me to", "add.*to.?do",
                            "note.*down", "remember to")),
    ("androidtv_control",  ("turn on.*tv", "turn off.*tv", "open.*netflix",
                            "open.*youtube", "tv control", "on the tv")),
]


def _executor_timed(fn, *args, label: str = ""):
    """Wrap a callable so the thread-pool queue-wait time is logged on entry."""
    t_submit = time.perf_counter()

    def _run():
        logger.debug(
            "LATENCY executor_queue_wait=%.3fms task=%s",
            (time.perf_counter() - t_submit) * 1000,
            label,
        )
        return fn(*args)

    return _run


def _keyword_route(text: str) -> str | None:
    """Return a tool name if the transcript clearly matches one via keywords."""
    import re
    lower = text.lower()
    for tool_name, keywords in _KEYWORD_ROUTES:
        for kw in keywords:
            if re.search(kw, lower):
                return tool_name
    return None


def _is_capability_gap(fallback_text: str) -> bool:
    """Return True if the LLM response indicates a missing capability."""
    lower = fallback_text.lower()
    return any(phrase in lower for phrase in _INABILITY_PHRASES)


# ---------------------------------------------------------------------------
# Audio capture
# ---------------------------------------------------------------------------


_MAX_CAPTURE_SECONDS = 12


async def _capture_utterance(
    t_wake: float = 0.0,
    silence_duration_ms: int = 800,
    capture: VoiceCapture | None = None,
    capture_stream=None,
) -> tuple[bytes, int]:
    """Capture one spoken utterance via VAD. Returns (pcm_bytes, sample_rate).

    Hard-cuts at _MAX_CAPTURE_SECONDS if VAD never fires the silence threshold.
    t_wake: perf_counter timestamp when wake-word event fired, for latency logging.
    capture + capture_stream: when provided, reads from the already-open stream
    instead of opening a new one — eliminates per-activation PyAudio open cost.
    """
    t0 = time.perf_counter()
    if t_wake:
        logger.debug("LATENCY wake_to_capture_start=%.1fms", (t0 - t_wake) * 1000)

    loop = asyncio.get_running_loop()
    chunk_queue: asyncio.Queue[AudioChunk] = asyncio.Queue()

    _active_capture: VoiceCapture
    if capture is not None and capture_stream is not None:
        _active_capture = capture
        _active_capture._stop_event.clear()

        def _feed() -> None:
            for chunk in _active_capture.capture_from_stream(capture_stream, t_stream_open=t0):
                asyncio.run_coroutine_threadsafe(chunk_queue.put(chunk), loop)
                if chunk.is_final:
                    break
    else:
        _active_capture = VoiceCapture(silence_duration_ms=silence_duration_ms)

        def _feed() -> None:
            for chunk in _active_capture.stream():
                asyncio.run_coroutine_threadsafe(chunk_queue.put(chunk), loop)
                if chunk.is_final:
                    break

    feed_thread = threading.Thread(target=_feed, daemon=True)
    feed_thread.start()

    pcm_chunks: list[bytes] = []
    sample_rate = SAMPLE_RATE
    deadline = loop.time() + _MAX_CAPTURE_SECONDS
    t_first_chunk: float | None = None

    while True:
        remaining = deadline - loop.time()
        if remaining <= 0:
            logger.warning("VAD capture hit %ds limit — cutting off", _MAX_CAPTURE_SECONDS)
            _active_capture.stop()
            break
        try:
            chunk = await asyncio.wait_for(chunk_queue.get(), timeout=remaining)
        except asyncio.TimeoutError:
            logger.warning("VAD capture hit %ds limit — cutting off", _MAX_CAPTURE_SECONDS)
            _active_capture.stop()
            break
        if t_first_chunk is None:
            t_first_chunk = time.perf_counter()
            logger.debug(
                "LATENCY capture_stream_first_chunk=%.1fms",
                (t_first_chunk - t0) * 1000,
            )
        sample_rate = chunk.sample_rate
        if chunk.audio_bytes:
            pcm_chunks.append(chunk.audio_bytes)
        if chunk.is_final:
            break

    feed_thread.join(timeout=2.0)
    t_pcm_done = time.perf_counter()

    raw = b"".join(pcm_chunks)
    # Resample from capture rate (48 kHz) down to 16 kHz required by Whisper STT.
    if raw and sample_rate != 16000:
        audio_int16 = np.frombuffer(raw, dtype=np.int16)
        t_dec = time.perf_counter()
        # Integer decimation (stride-3, 48→16 kHz) is adequate for Whisper speech input.
        audio_int16 = audio_int16[::3]
        logger.debug(
            "LATENCY decimation_48k_to_16k=%.2fms out_samples=%d",
            (time.perf_counter() - t_dec) * 1000, len(audio_int16),
        )
        raw = audio_int16.tobytes()
        sample_rate = 16000

    utterance_seconds = len(raw) / (16000 * 2) if raw else 0.0
    logger.debug(
        "LATENCY capture_total=%.1fms utterance_audio=%.2fs",
        (t_pcm_done - t0) * 1000,
        utterance_seconds,
    )
    return raw, sample_rate


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
# Capability-gap handling (unknown requests → queue → GitHub sync)
# ---------------------------------------------------------------------------


async def _handle_capability_gap(
    transcript_text: str,
    user: str,
    initial_response: str,
    stt: HailoTranscriber,
    tts: PiperTTS,
    player: AudioPlayer,
    tool_queue: ToolRequestQueue,
    loop: asyncio.AbstractEventLoop,
    silence_duration_ms: int = 800,
    capture: VoiceCapture | None = None,
    capture_stream=None,
) -> str:
    """Ask for priority (if queue non-empty), enqueue, sync to GitHub.

    Returns the spoken confirmation text to be synthesised by _handle_activation.
    """
    priority = "mid"
    highest = tool_queue.get_highest_priority()

    if highest:
        question = (
            f"{initial_response} "
            f"Is this more urgent than: {highest.intent}?"
        )
        q_audio = await loop.run_in_executor(None, tts.synthesize, question)
        await loop.run_in_executor(None, player.play, q_audio)

        pcm_bytes, sample_rate = await _capture_utterance(
            silence_duration_ms=silence_duration_ms,
            capture=capture,
            capture_stream=capture_stream,
        )
        priority_text = await stt.transcribe(pcm_bytes, sample_rate)
        pt_lower = priority_text.lower()

        if any(kw in pt_lower for kw in ("yes", "more", "urgent", "important", "higher")):
            priority = "high"
        elif any(kw in pt_lower for kw in ("no", "less", "later", "lower", "not really")):
            priority = "low"

    req = ToolRequest(
        intent=transcript_text,
        user_query=transcript_text,
        speaker=user,
        priority=priority,
    )
    tool_queue.enqueue(req)
    logger.info("Enqueued tool request %s (priority=%s): %r", req.id, priority, transcript_text)

    if github_sync.is_online():
        pushed = github_sync.sync(tool_queue)
        if pushed:
            return "I've added that to my list and sent it off to be worked on."
        return "I've noted that, but had trouble syncing. I'll send it when I can."
    else:
        return "I'll remember that for when I'm back online."


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
    tool_queue: ToolRequestQueue | None = None,
    t_wake: float = 0.0,
    capture: VoiceCapture | None = None,
    capture_stream=None,
) -> None:
    """Process one wake-word activation end-to-end."""
    loop = asyncio.get_running_loop()

    # Pick up any tools the remote agent pushed since the last activation
    new_tool_names = _reload_tools(registry, known_tool_names)

    # Capture the spoken utterance
    pcm_bytes, sample_rate = await _capture_utterance(
        t_wake=t_wake,
        silence_duration_ms=config.audio.silence_duration_ms,
        capture=capture,
        capture_stream=capture_stream,
    )

    # Identify speaker on CPU while STT runs on Hailo NPU (concurrent)
    t_identify_stt = time.perf_counter()
    user, transcript_text = await asyncio.gather(
        loop.run_in_executor(None, _executor_timed(identify, pcm_bytes, sample_rate, label="identify")),
        stt.transcribe(pcm_bytes, sample_rate),
    )
    logger.debug(
        "LATENCY identify_stt_parallel=%.1fms speaker=%s transcript_chars=%d",
        (time.perf_counter() - t_identify_stt) * 1000, user, len(transcript_text),
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
    t_route = time.perf_counter()
    tool_call, fallback_text = await router.route(transcript, context_turns)
    logger.debug(
        "LATENCY llm_route=%.1fms tool=%s",
        (time.perf_counter() - t_route) * 1000,
        tool_call.tool_name if tool_call else "none",
    )

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
                t_tool = time.perf_counter()
                response_text = await tool.run(tool_call.params, user)
                logger.debug(
                    "LATENCY tool_run name=%s %.1fms",
                    tool_call.tool_name, (time.perf_counter() - t_tool) * 1000,
                )
            except Exception:
                logger.exception("Tool %r failed", tool_call.tool_name)
                response_text = (
                    "Sorry, I had trouble completing that. Please try again."
                )
    else:
        raw_fallback = fallback_text or ""
        # Small model often misses tool calls — try keyword routing as a fallback.
        kw_tool_name = _keyword_route(transcript_text)
        kw_tool = registry.get(kw_tool_name) if kw_tool_name else None
        if kw_tool:
            logger.info("Keyword fallback → %s", kw_tool_name)
            try:
                t_tool = time.perf_counter()
                response_text = await kw_tool.run({"query": transcript_text}, user)
                logger.debug(
                    "LATENCY tool_run name=%s %.1fms",
                    kw_tool_name, (time.perf_counter() - t_tool) * 1000,
                )
            except Exception:
                logger.exception("Keyword-fallback tool %r failed", kw_tool_name)
                response_text = "Sorry, I had trouble completing that. Please try again."
        elif tool_queue is not None and _is_capability_gap(raw_fallback):
            response_text = await _handle_capability_gap(
                transcript_text,
                user,
                raw_fallback or "I don't know how to do that yet.",
                stt,
                tts,
                player,
                tool_queue,
                loop,
                silence_duration_ms=config.audio.silence_duration_ms,
                capture=capture,
                capture_stream=capture_stream,
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
    t_tts = time.perf_counter()
    audio = await loop.run_in_executor(None, _executor_timed(tts.synthesize, response_text, label="tts_synthesize"))
    logger.debug(
        "LATENCY tts_synthesize=%.1fms bytes=%d response_chars=%d",
        (time.perf_counter() - t_tts) * 1000, len(audio), len(response_text),
    )
    t_play = time.perf_counter()
    await loop.run_in_executor(None, _executor_timed(player.play, audio, label="audio_play"))
    logger.debug("LATENCY audio_play_total=%.1fms", (time.perf_counter() - t_play) * 1000)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main() -> None:
    config: AppConfig = load_config()
    loop = asyncio.get_running_loop()

    from hailo_platform import VDevice as _VDevice
    _shared_vdevice = _VDevice()
    stt = HailoTranscriber(config.hailo, vdevice=_shared_vdevice)
    llm = HailoLLMClient(config.hailo, vdevice=_shared_vdevice)

    logger.info("Loading STT model…")
    stt._ensure_loaded()
    logger.info("Loading LLM model…")
    llm._ensure_loaded()
    logger.info("Models ready.")

    conn = init_db(_MEMORY_DB_PATH)
    tool_queue = ToolRequestQueue(config.tool_requests.db_path)

    registry = ToolRegistry()
    registry.load()
    known_tool_names: set[str] = {t.name for t in registry.all()}
    router = ToolRouter(llm, registry)

    tts = PiperTTS(config.tts.model_path, use_cuda=config.tts.use_cuda)
    player = AudioPlayer(
        sample_rate=tts.sample_rate,
        device=config.audio.output_device,
        output_sample_rate=config.audio.output_sample_rate,
        channels=1,
    )

    prewarm = PrewarmScheduler(llm, stt, "schedule.json", conn)
    prewarm.start(loop)

    # Open 48 kHz capture stream once at startup to eliminate per-activation PyAudio open cost.
    capture = VoiceCapture(silence_duration_ms=config.audio.silence_duration_ms)
    capture_stream = capture.open_stream()

    wake_event = asyncio.Event()
    detector = WakeWordDetector(
        config=config.wake_word,
        on_detection=lambda: loop.call_soon_threadsafe(wake_event.set),
    )
    detector.start()

    try:
        while True:
            logger.info("Listening for wake word…")
            await wake_event.wait()
            t_wake = time.perf_counter()
            wake_event.clear()
            logger.debug("LATENCY wake_word_detected; starting activation handler")

            # Discard audio that accumulated in the 16 kHz wake-word buffer during the
            # previous activation so the next listen cycle begins with fresh audio.
            detector.drain()

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
                    tool_queue=tool_queue,
                    t_wake=t_wake,
                    capture=capture,
                    capture_stream=capture_stream,
                )
            except Exception:
                logger.exception("Activation pipeline failed")

            detector.start()  # Restart listening on the already-open stream
    finally:
        prewarm.cancel()
        detector.close()
        capture.close()
        llm.close()
        stt.close()
        try:
            _shared_vdevice.release()
        except Exception:
            pass
        conn.close()
        tool_queue.close()


if __name__ == "__main__":
    asyncio.run(main())
