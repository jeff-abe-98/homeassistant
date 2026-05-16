"""Tests for graceful error recovery in server/main.py and server/llm/client.py."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.models import AssistantResponse, AudioChunk, Transcript


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _transcript(text: str = "what's the weather?", user: str = "owner") -> Transcript:
    return Transcript(session_id=str(uuid.uuid4()), text=text, user=user)


def _audio_chunk(is_final: bool = True) -> AudioChunk:
    return AudioChunk(
        session_id=str(uuid.uuid4()),
        sequence=0,
        audio_bytes=b"\x00" * 100,
        sample_rate=16000,
        is_final=is_final,
    )


def _mock_websocket() -> MagicMock:
    ws = MagicMock()
    ws.send_text = AsyncMock()
    return ws


# ---------------------------------------------------------------------------
# OllamaClient — timeout raises LLMTimeoutError
# ---------------------------------------------------------------------------

def test_ollama_client_raises_llm_timeout_error_on_slow_response():
    from server.llm.client import LLMTimeoutError, OllamaClient
    from shared.config import OllamaConfig

    cfg = OllamaConfig(timeout=0.01)
    client = OllamaClient(cfg)

    async def _slow(*args, **kwargs):
        await asyncio.sleep(10)

    async def _run():
        client._client.chat = _slow
        with pytest.raises(LLMTimeoutError):
            await client.chat([{"role": "user", "content": "hello"}])

    asyncio.run(_run())


def test_ollama_client_wraps_connection_error_as_llm_error():
    from server.llm.client import LLMError, OllamaClient
    from shared.config import OllamaConfig

    cfg = OllamaConfig(timeout=5.0)
    client = OllamaClient(cfg)

    async def _fail(*args, **kwargs):
        raise ConnectionRefusedError("Ollama not running")

    async def _run():
        client._client.chat = _fail
        with pytest.raises(LLMError):
            await client.chat([{"role": "user", "content": "hello"}])

    asyncio.run(_run())


def test_ollama_client_chat_with_tools_raises_llm_timeout_error():
    from server.llm.client import LLMTimeoutError, OllamaClient
    from shared.config import OllamaConfig

    cfg = OllamaConfig(timeout=0.01)
    client = OllamaClient(cfg)

    async def _slow(*args, **kwargs):
        await asyncio.sleep(10)

    async def _run():
        client._client.chat = _slow
        with pytest.raises(LLMTimeoutError):
            await client.chat_with_tools(
                [{"role": "user", "content": "hello"}], []
            )

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# _handle_transcript — LLM timeout / connection error → friendly message
# ---------------------------------------------------------------------------

def test_handle_transcript_llm_timeout_returns_friendly_message():
    transcript = _transcript("tell me a joke")
    ws = _mock_websocket()

    # Router fails (LLM unreachable), then direct-LLM fallback also times out.
    mock_router = MagicMock()
    mock_router.route = AsyncMock(side_effect=RuntimeError("LLM unavailable"))

    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(side_effect=asyncio.TimeoutError())

    with (
        patch("server.main._router", mock_router),
        patch("server.main._llm", mock_llm),
    ):
        from server.main import _handle_transcript
        response = asyncio.run(_handle_transcript(transcript, ws))

    assert response is not None
    assert "trouble" in response.text.lower() or "problem" in response.text.lower()


def test_handle_transcript_llm_connection_error_returns_friendly_message():
    transcript = _transcript("tell me a joke")
    ws = _mock_websocket()

    # Router fails, then direct-LLM fallback also fails with connection error.
    mock_router = MagicMock()
    mock_router.route = AsyncMock(side_effect=RuntimeError("LLM unavailable"))

    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(side_effect=ConnectionRefusedError("Ollama not running"))

    with (
        patch("server.main._router", mock_router),
        patch("server.main._llm", mock_llm),
    ):
        from server.main import _handle_transcript
        response = asyncio.run(_handle_transcript(transcript, ws))

    assert response is not None
    assert "trouble" in response.text.lower() or "problem" in response.text.lower()


def test_handle_transcript_llm_error_message_is_informative():
    """The error message should not expose internal details."""
    transcript = _transcript("what is 2 + 2?")
    ws = _mock_websocket()

    # Router fails, then direct-LLM fallback also raises an unexpected error.
    mock_router = MagicMock()
    mock_router.route = AsyncMock(side_effect=RuntimeError("LLM unavailable"))

    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(side_effect=RuntimeError("model crash"))

    with (
        patch("server.main._router", mock_router),
        patch("server.main._llm", mock_llm),
    ):
        from server.main import _handle_transcript
        response = asyncio.run(_handle_transcript(transcript, ws))

    assert "model crash" not in response.text
    assert "RuntimeError" not in response.text


# ---------------------------------------------------------------------------
# _handle_transcript — tool API failure → friendly message
# ---------------------------------------------------------------------------

def test_handle_transcript_tool_api_failure_returns_friendly_message():
    transcript = _transcript("what's the weather?")
    ws = _mock_websocket()

    mock_tool = MagicMock()
    mock_tool.run = AsyncMock(side_effect=RuntimeError("OWM API 500"))

    mock_router = MagicMock()
    mock_router.route = AsyncMock(
        return_value=(MagicMock(tool_name="weather", params={}), "")
    )

    mock_registry = MagicMock()
    mock_registry.get.return_value = mock_tool

    with (
        patch("server.main._router", mock_router),
        patch("server.main._registry", mock_registry),
    ):
        from server.main import _handle_transcript
        response = asyncio.run(_handle_transcript(transcript, ws))

    assert response is not None
    assert "problem" in response.text.lower() or "sorry" in response.text.lower()


def test_handle_transcript_tool_timeout_returns_friendly_message():
    transcript = _transcript("what's the weather?")
    ws = _mock_websocket()

    mock_tool = MagicMock()
    mock_tool.run = AsyncMock(side_effect=asyncio.TimeoutError())

    mock_router = MagicMock()
    mock_router.route = AsyncMock(
        return_value=(MagicMock(tool_name="weather", params={}), "")
    )

    mock_registry = MagicMock()
    mock_registry.get.return_value = mock_tool

    with (
        patch("server.main._router", mock_router),
        patch("server.main._registry", mock_registry),
    ):
        from server.main import _handle_transcript
        response = asyncio.run(_handle_transcript(transcript, ws))

    assert response is not None
    assert response.session_id == transcript.session_id


def test_handle_transcript_tool_error_message_does_not_expose_internals():
    transcript = _transcript("what's the weather?")
    ws = _mock_websocket()

    mock_tool = MagicMock()
    mock_tool.run = AsyncMock(side_effect=RuntimeError("secret API key invalid"))

    mock_router = MagicMock()
    mock_router.route = AsyncMock(
        return_value=(MagicMock(tool_name="weather", params={}), "")
    )

    mock_registry = MagicMock()
    mock_registry.get.return_value = mock_tool

    with (
        patch("server.main._router", mock_router),
        patch("server.main._registry", mock_registry),
    ):
        from server.main import _handle_transcript
        response = asyncio.run(_handle_transcript(transcript, ws))

    assert "secret API key" not in response.text
    assert "RuntimeError" not in response.text


# ---------------------------------------------------------------------------
# _handle_transcript — router failure → graceful fallback to LLM
# ---------------------------------------------------------------------------

def test_handle_transcript_router_failure_falls_through_to_llm():
    transcript = _transcript("what is 2 plus 2?")
    ws = _mock_websocket()

    mock_router = MagicMock()
    mock_router.route = AsyncMock(side_effect=RuntimeError("Ollama model not loaded"))

    mock_llm = AsyncMock()
    # Router failed → no fallback_text → one direct LLM call as last resort.
    mock_llm.complete = AsyncMock(return_value="Four.")

    with (
        patch("server.main._router", mock_router),
        patch("server.main._llm", mock_llm),
    ):
        from server.main import _handle_transcript
        response = asyncio.run(_handle_transcript(transcript, ws))

    assert response is not None
    assert "four" in response.text.lower() or "4" in response.text


def test_handle_transcript_router_timeout_falls_through_to_llm():
    transcript = _transcript("what is the capital of France?")
    ws = _mock_websocket()

    mock_router = MagicMock()
    mock_router.route = AsyncMock(side_effect=asyncio.TimeoutError())

    mock_llm = AsyncMock()
    # Router failed → no fallback_text → one direct LLM call as last resort.
    mock_llm.complete = AsyncMock(return_value="Paris.")

    with (
        patch("server.main._router", mock_router),
        patch("server.main._llm", mock_llm),
    ):
        from server.main import _handle_transcript
        response = asyncio.run(_handle_transcript(transcript, ws))

    assert response is not None
    assert "paris" in response.text.lower()


# ---------------------------------------------------------------------------
# _handle_transcript — router fallback text used directly for conversation
# ---------------------------------------------------------------------------

def test_handle_transcript_router_fallback_text_used_as_reply():
    transcript = _transcript("what is 2 plus 2?")
    ws = _mock_websocket()

    # Router returns no tool and the LLM's conversational reply inline (1 LLM call total).
    mock_router = MagicMock()
    mock_router.route = AsyncMock(return_value=(None, "Two plus two is four."))

    with (
        patch("server.main._router", mock_router),
    ):
        from server.main import _handle_transcript
        response = asyncio.run(_handle_transcript(transcript, ws))

    assert response is not None
    assert "four" in response.text.lower() or "4" in response.text


# ---------------------------------------------------------------------------
# _handle_audio_chunk — STT failure → returns None (no crash)
# ---------------------------------------------------------------------------

def test_stt_failure_returns_none_without_raising():
    chunk = _audio_chunk(is_final=True)

    mock_stt = MagicMock()
    mock_stt.transcribe = MagicMock(side_effect=RuntimeError("CUDA OOM"))

    with patch("server.main._stt", mock_stt):
        from server.main import _handle_audio_chunk
        result = asyncio.run(_handle_audio_chunk(chunk))

    assert result is None


def test_stt_failure_cleans_up_audio_buffer():
    """Audio buffer for the session should be consumed even when STT fails."""
    chunk = _audio_chunk(is_final=True)
    from server.main import _audio_buffers

    mock_stt = MagicMock()
    mock_stt.transcribe = MagicMock(side_effect=RuntimeError("CUDA OOM"))

    with patch("server.main._stt", mock_stt):
        from server.main import _handle_audio_chunk
        asyncio.run(_handle_audio_chunk(chunk))

    assert chunk.session_id not in _audio_buffers


def test_non_final_audio_chunk_is_buffered_without_stt():
    chunk = _audio_chunk(is_final=False)

    mock_stt = MagicMock()

    with patch("server.main._stt", mock_stt):
        from server.main import _handle_audio_chunk
        result = asyncio.run(_handle_audio_chunk(chunk))

    assert result is None
    mock_stt.transcribe.assert_not_called()
