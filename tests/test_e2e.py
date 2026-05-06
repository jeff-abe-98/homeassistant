"""End-to-end pipeline test: audio stream → STT transcript → LLM response.

Mocks hardware-dependent components (Whisper model, Ollama) and runs a real
FastAPI/uvicorn server with a real WebSocket client to verify the full pipeline.

Run with: pytest tests/test_e2e.py -v
"""
from __future__ import annotations

import asyncio
import socket
import struct
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
import uvicorn

from shared.config import AppConfig, ServerConfig
from shared.models import AudioChunk


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _silent_pcm(seconds: float = 0.3, sample_rate: int = 16000) -> bytes:
    """Silent int16 PCM bytes — stands in for a real captured utterance."""
    n_samples = int(sample_rate * seconds)
    return struct.pack(f"<{n_samples}h", *([0] * n_samples))


@pytest_asyncio.fixture()
async def running_server() -> int:  # type: ignore[override]
    """Start a uvicorn server with mocked STT + LLM; yield the bound port."""
    port = _free_port()

    import server.main as server_app  # ensure module is imported before patching

    mock_stt_cls = MagicMock()
    mock_stt_cls.return_value.transcribe.return_value = "what is 2 plus 2"

    mock_llm_cls = MagicMock()
    mock_llm_cls.return_value.complete = AsyncMock(return_value="Two plus two equals four.")

    with (
        patch("server.main.WhisperTranscriber", mock_stt_cls),
        patch("server.main.OllamaClient", mock_llm_cls),
    ):

        cfg = uvicorn.Config(
            server_app.app,
            host="127.0.0.1",
            port=port,
            lifespan="on",
            log_level="warning",
        )
        server = uvicorn.Server(cfg)
        task = asyncio.create_task(server.serve())

        for _ in range(50):
            await asyncio.sleep(0.1)
            if server.started:
                break
        assert server.started, "Server did not start within 5 s"

        yield port

        server.should_exit = True
        await asyncio.wait_for(task, timeout=5.0)


@pytest.mark.asyncio
async def test_audio_to_response(running_server: int) -> None:
    """Full pipeline: AudioChunk stream → STT Transcript → LLM AssistantResponse."""
    from pi.client import AssistantClient

    config = AppConfig(server=ServerConfig(host="127.0.0.1", port=running_server))
    session_id = str(uuid.uuid4())
    pcm = _silent_pcm()

    async with AssistantClient(config) as client:
        # Send one audio chunk (is_final=True acts as the end-of-utterance marker).
        await client.send_audio_chunk(
            AudioChunk(
                session_id=session_id,
                sequence=0,
                audio_bytes=pcm,
                sample_rate=16000,
                is_final=True,
            )
        )

        transcript = await asyncio.wait_for(
            client.receive_transcript(session_id), timeout=10.0
        )
        assert transcript.text == "what is 2 plus 2"

        await client.send_transcript(transcript)
        response = await asyncio.wait_for(
            client.receive_response(session_id), timeout=10.0
        )
        assert "four" in response.text.lower() or "4" in response.text
