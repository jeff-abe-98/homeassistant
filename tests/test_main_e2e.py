"""End-to-end smoke tests for the unified pi/main.py loop.

Tests _handle_activation with mocked STT, LLM, tools, TTS, and audio player
so the full pipeline can run without physical Hailo hardware, microphone, or speaker.

Run with: pytest tests/test_main_e2e.py -v
"""
from __future__ import annotations

import asyncio
import sqlite3
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pi.memory.db import init_db
from pi.memory.session import Session
from pi.tools.base import BaseTool, ToolRegistry
from shared.config import AppConfig


# ---------------------------------------------------------------------------
# Fake tool
# ---------------------------------------------------------------------------


class EchoTool(BaseTool):
    """Minimal tool used across tests — echoes back who triggered it."""

    name = "echo"
    description = "Echoes a test response."
    parameters = {"type": "object", "properties": {}, "required": []}

    async def run(self, params: dict, user: str) -> str:
        return f"Echo: hello, {user}!"


class BrokenTool(BaseTool):
    """Tool that always raises — tests graceful failure handling."""

    name = "broken"
    description = "Always fails."
    parameters = {"type": "object", "properties": {}, "required": []}

    async def run(self, params: dict, user: str) -> str:
        raise RuntimeError("tool exploded")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_conn(tmp_path) -> sqlite3.Connection:
    conn = init_db(str(tmp_path / "test.db"))
    yield conn
    conn.close()


@pytest.fixture()
def config() -> AppConfig:
    return AppConfig()


@pytest.fixture()
def registry_with_echo() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(EchoTool())
    return reg


@pytest.fixture()
def registry_with_broken() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(BrokenTool())
    return reg


@pytest.fixture()
def empty_registry() -> ToolRegistry:
    return ToolRegistry()


# ---------------------------------------------------------------------------
# Helper — build a mock router returning a specific response
# ---------------------------------------------------------------------------


def _make_router(registry: ToolRegistry, *, tool_name: str | None = None, fallback: str = "Sure!"):
    """Return a ToolRouter whose LLM is fully mocked."""
    from pi.llm.hailo_client import HailoLLMClient, ToolCallItem, ToolFunction, ToolMessage
    from pi.llm.router import ToolRouter

    mock_llm = MagicMock(spec=HailoLLMClient)

    if tool_name:
        fn = ToolFunction(name=tool_name, arguments={})
        msg = ToolMessage(content=None, tool_calls=[ToolCallItem(function=fn)])
    else:
        msg = ToolMessage(content=fallback, tool_calls=None)

    mock_llm.chat_with_tools = AsyncMock(return_value=msg)
    mock_llm.complete = AsyncMock(return_value=fallback)

    return ToolRouter(llm=mock_llm, registry=registry)


# ---------------------------------------------------------------------------
# Helper — run _handle_activation with standard mocks
# ---------------------------------------------------------------------------

_FAKE_PCM = b"\x00\x01" * 8000  # 0.5 s of silence at 16kHz int16


def _run_activation(
    config: AppConfig,
    db_conn: sqlite3.Connection,
    registry: ToolRegistry,
    router: Any,
    *,
    transcript_text: str = "test utterance",
    speaker: str = "owner",
    known_tool_names: set | None = None,
) -> None:
    """Patch all I/O and run _handle_activation once."""
    from pi.main import _handle_activation

    if known_tool_names is None:
        known_tool_names = {t.name for t in registry.all()}

    mock_stt = MagicMock()
    mock_stt.transcribe = AsyncMock(return_value=transcript_text)

    mock_tts = MagicMock()
    mock_tts.synthesize.return_value = b"\x00" * 512

    mock_player = MagicMock()

    with (
        patch("pi.main._capture_utterance", AsyncMock(return_value=(_FAKE_PCM, 16000))),
        patch("pi.main.identify", return_value=speaker),
    ):
        asyncio.run(
            _handle_activation(
                config=config,
                stt=mock_stt,
                router=router,
                registry=registry,
                tts=mock_tts,
                player=mock_player,
                conn=db_conn,
                known_tool_names=known_tool_names,
            )
        )

    return mock_tts, mock_player, mock_stt


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_tool_call_path_runs_without_error(config, db_conn, registry_with_echo) -> None:
    """Router selects echo tool → tool runs → TTS synthesises the result."""
    router = _make_router(registry_with_echo, tool_name="echo")

    mock_tts, mock_player, _ = _run_activation(config, db_conn, registry_with_echo, router)

    mock_tts.synthesize.assert_called_once()
    spoken = mock_tts.synthesize.call_args[0][0]
    assert "Echo: hello, owner!" in spoken
    mock_player.play.assert_called_once()


def test_fallback_path_runs_without_error(config, db_conn, empty_registry) -> None:
    """No tools registered → router returns conversational fallback → TTS synthesises it."""
    router = _make_router(empty_registry, fallback="I can help with that!")

    mock_tts, mock_player, _ = _run_activation(config, db_conn, empty_registry, router)

    mock_tts.synthesize.assert_called_once()
    spoken = mock_tts.synthesize.call_args[0][0]
    assert "I can help with that!" in spoken
    mock_player.play.assert_called_once()


def test_empty_transcript_skips_llm_step(config, db_conn, empty_registry) -> None:
    """Blank STT output → no TTS call (pipeline short-circuits cleanly)."""
    router = _make_router(empty_registry, fallback="Should not be spoken")

    mock_tts, mock_player, _ = _run_activation(
        config, db_conn, empty_registry, router, transcript_text=""
    )

    mock_tts.synthesize.assert_not_called()
    mock_player.play.assert_not_called()


def test_whitespace_only_transcript_skips_llm_step(config, db_conn, empty_registry) -> None:
    """Whitespace-only transcript is treated as empty — no TTS call."""
    router = _make_router(empty_registry, fallback="Nope")

    mock_tts, mock_player, _ = _run_activation(
        config, db_conn, empty_registry, router, transcript_text="   \t\n"
    )

    mock_tts.synthesize.assert_not_called()


def test_broken_tool_returns_error_message(config, db_conn, registry_with_broken) -> None:
    """Tool.run raises → graceful error message is synthesised instead of crashing."""
    router = _make_router(registry_with_broken, tool_name="broken")

    mock_tts, _, _ = _run_activation(config, db_conn, registry_with_broken, router)

    mock_tts.synthesize.assert_called_once()
    spoken = mock_tts.synthesize.call_args[0][0]
    assert "sorry" in spoken.lower() or "trouble" in spoken.lower()


def test_unknown_tool_name_falls_back_gracefully(config, db_conn, registry_with_echo) -> None:
    """Router picks a tool that's not in the registry → graceful fallback message.

    registry_with_echo has the 'echo' tool (so schemas are non-empty and the LLM
    is asked to route), but the mock LLM returns 'nonexistent_tool' which doesn't
    exist in the registry → main.py falls back to a descriptive error message.
    """
    router = _make_router(registry_with_echo, tool_name="nonexistent_tool")

    mock_tts, _, _ = _run_activation(config, db_conn, registry_with_echo, router)

    mock_tts.synthesize.assert_called_once()
    spoken = mock_tts.synthesize.call_args[0][0]
    assert "nonexistent_tool" in spoken or "not available" in spoken.lower()


def test_new_tool_announcement_prepended(config, db_conn, registry_with_echo) -> None:
    """When echo tool is new (not in known_names), its name is announced in the response."""
    router = _make_router(registry_with_echo, fallback="Here you go.")

    # known_tool_names starts empty → echo is "new"
    mock_tts, _, _ = _run_activation(
        config, db_conn, registry_with_echo, router, known_tool_names=set()
    )

    spoken = mock_tts.synthesize.call_args[0][0]
    assert "echo" in spoken.lower()
    assert "By the way" in spoken


def test_session_turn_saved_to_memory(config, db_conn, registry_with_echo) -> None:
    """After activation, one turn should be persisted in the memory DB."""
    router = _make_router(registry_with_echo, tool_name="echo")

    _run_activation(config, db_conn, registry_with_echo, router)

    # Verify at least one turn was written to the DB
    rows = db_conn.execute("SELECT * FROM turns").fetchall()
    assert len(rows) >= 1


def test_activation_logged_to_db(config, db_conn, registry_with_echo) -> None:
    """log_activation is called → activations table has an entry."""
    router = _make_router(registry_with_echo, fallback="Hello!")

    _run_activation(config, db_conn, registry_with_echo, router)

    rows = db_conn.execute("SELECT * FROM activations").fetchall()
    assert len(rows) >= 1


def test_emily_speaker_flows_through_correctly(config, db_conn, registry_with_echo) -> None:
    """Speaker 'emily' is passed to the tool and recorded in memory."""
    router = _make_router(registry_with_echo, tool_name="echo")

    mock_tts, _, _ = _run_activation(
        config, db_conn, registry_with_echo, router, speaker="emily"
    )

    spoken = mock_tts.synthesize.call_args[0][0]
    assert "emily" in spoken.lower()

    rows = db_conn.execute("SELECT speaker FROM activations").fetchall()
    assert rows[0][0] == "emily"
