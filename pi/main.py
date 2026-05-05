"""Main loop: wake word → capture → send to server → receive response → TTS → play."""
from __future__ import annotations

import asyncio
import logging
import threading

from pi.audio.capture import VoiceCapture
from pi.audio.playback import AudioPlayer
from pi.client import AssistantClient
from pi.tts.piper import PiperTTS
from pi.wake_word.detector import WakeWordDetector
from shared.config import AppConfig
from shared.config import load as load_config
from shared.models import AudioChunk

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


async def _run_utterance(
    client: AssistantClient,
    tts: PiperTTS,
    player: AudioPlayer,
) -> None:
    """Capture one utterance, stream to server, play back the response."""
    loop = asyncio.get_running_loop()
    chunk_queue: asyncio.Queue[AudioChunk] = asyncio.Queue()
    capture = VoiceCapture()

    def _feed() -> None:
        # Runs in a background thread; break on is_final triggers generator cleanup.
        for chunk in capture.stream():
            asyncio.run_coroutine_threadsafe(chunk_queue.put(chunk), loop)
            if chunk.is_final:
                break

    feed_thread = threading.Thread(target=_feed, daemon=True)
    feed_thread.start()

    session_id: str | None = None
    while True:
        chunk = await chunk_queue.get()
        if session_id is None:
            session_id = chunk.session_id
        await client.send_audio_chunk(chunk)
        if chunk.is_final:
            break

    assert session_id is not None

    transcript = await client.receive_transcript(session_id)
    logger.info("Transcript: %s", transcript.text)

    await client.send_transcript(transcript)
    response = await client.receive_response(session_id)
    logger.info("Response: %s", response.text)

    audio = await loop.run_in_executor(None, tts.synthesize, response.text)
    await loop.run_in_executor(None, player.play, audio)

    feed_thread.join(timeout=2.0)


async def main() -> None:
    config: AppConfig = load_config()

    tts = PiperTTS(
        model_path=config.tts.model_path,
        use_cuda=config.tts.use_cuda,
    )
    player = AudioPlayer(sample_rate=tts.sample_rate)

    async with AssistantClient(config) as client:
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
            logger.info("Wake word detected — capturing utterance")

            try:
                await _run_utterance(client, tts, player)
            except Exception:
                logger.exception("Utterance pipeline failed")


if __name__ == "__main__":
    asyncio.run(main())
