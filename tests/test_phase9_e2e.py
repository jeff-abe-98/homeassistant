"""Phase 9 end-to-end tests.

Validates the complete pipeline with tools migrated to pi/tools/*:
  - ToolRegistry discovers all 10 built-in tools from pi.tools.*
  - WeatherTool runs end-to-end through _handle_activation (mocked HTTP + LLM)
  - CTATool runs end-to-end through _handle_activation (mocked HTTP + LLM)
  - main() completes one full wake-word activation cycle with all hardware mocked

Run with:  pytest tests/test_phase9_e2e.py -v
"""
from __future__ import annotations

import asyncio
import sqlite3
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import pi.main as _main_module
from pi.llm.hailo_client import ToolCallItem, ToolFunction, ToolMessage
from pi.llm.router import ToolRouter
from pi.memory.db import init_db
from pi.tools.base import BaseTool, ToolRegistry
from shared.config import AppConfig

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_FAKE_PCM = b"\x00\x01" * 8000  # 0.5 s of silence at 16 kHz int16


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_conn(tmp_path) -> sqlite3.Connection:
    conn = init_db(str(tmp_path / "test.db"))
    yield conn
    conn.close()


@pytest.fixture()
def config() -> AppConfig:
    return AppConfig()


def _router_returning_tool(
    registry: ToolRegistry, tool_name: str, params: dict, *, complete_return: str = "Fallback."
) -> ToolRouter:
    """Return a ToolRouter whose LLM always picks a specific tool."""
    from pi.llm.hailo_client import HailoLLMClient

    fn = ToolFunction(name=tool_name, arguments=params)
    msg = ToolMessage(content=None, tool_calls=[ToolCallItem(function=fn)])

    mock_llm = MagicMock(spec=HailoLLMClient)
    mock_llm.chat_with_tools = AsyncMock(return_value=msg)
    mock_llm.complete = AsyncMock(return_value=complete_return)

    return ToolRouter(llm=mock_llm, registry=registry)


def _router_returning_fallback(registry: ToolRegistry, fallback: str = "Sure!") -> ToolRouter:
    """Return a ToolRouter whose LLM always returns a conversational fallback."""
    from pi.llm.hailo_client import HailoLLMClient

    msg = ToolMessage(content=fallback, tool_calls=None)
    mock_llm = MagicMock(spec=HailoLLMClient)
    mock_llm.chat_with_tools = AsyncMock(return_value=msg)
    mock_llm.complete = AsyncMock(return_value=fallback)

    return ToolRouter(llm=mock_llm, registry=registry)


def _run_activation(
    config: AppConfig,
    db_conn: sqlite3.Connection,
    registry: ToolRegistry,
    router: ToolRouter,
    *,
    transcript_text: str = "test utterance",
    speaker: str = "owner",
    skip_reload: bool = False,
) -> tuple[MagicMock, MagicMock, MagicMock]:
    """Patch all I/O and run _handle_activation once. Returns (mock_tts, mock_player, mock_stt).

    skip_reload=True patches _reload_tools to return [] so the registry is not
    hot-reloaded.  Use this when the registered tool has been pre-configured with
    injected mocks that would be lost on reload.
    """
    from contextlib import ExitStack

    from pi.main import _handle_activation

    mock_stt = MagicMock()
    mock_stt.transcribe = AsyncMock(return_value=transcript_text)

    mock_tts = MagicMock()
    mock_tts.synthesize.return_value = b"\x00" * 512

    mock_player = MagicMock()

    known_tool_names = {t.name for t in registry.all()}

    with ExitStack() as stack:
        stack.enter_context(
            patch("pi.main._capture_utterance", AsyncMock(return_value=(_FAKE_PCM, 16000)))
        )
        stack.enter_context(patch("pi.main.identify", return_value=speaker))
        if skip_reload:
            stack.enter_context(patch("pi.main._reload_tools", return_value=[]))

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


# ===========================================================================
# Test 1 — ToolRegistry discovers all pi.tools.* built-in tools
# ===========================================================================


def test_tool_registry_discovers_pi_tools() -> None:
    """ToolRegistry.load() must discover all 10 migrated built-in tools from pi/tools/."""
    registry = ToolRegistry()
    registry.load()
    names = {t.name for t in registry.all()}

    expected = {
        "get_weather",
        "cta_arrivals",
        "get_calendar_events",
        "add_calendar_event",
        "add_task",
        "list_tasks",
        "complete_task",
        "androidtv_control",
        "spotify_control",
        "music_recommendation",
    }
    missing = expected - names
    assert not missing, f"ToolRegistry.load() failed to discover tools: {missing}"
    assert len(names) >= len(expected), f"Expected ≥{len(expected)} tools, got {len(names)}"


# ===========================================================================
# Test 2 — WeatherTool end-to-end via _handle_activation
# ===========================================================================


def test_weather_tool_end_to_end(config, db_conn) -> None:
    """WeatherTool fetches mocked weather JSON and narrates via mocked LLM through the full pipeline."""
    from pi.tools.weather import WeatherTool

    # Build a config that passes the api_key guard
    cfg_with_key = AppConfig()
    cfg_with_key.weather.api_key = "test_owm_key"
    cfg_with_key.weather.location = "Chicago, IL"
    cfg_with_key.weather.units = "imperial"

    # Fake HTTP responses: two GET calls (current + forecast)
    fake_current = MagicMock()
    fake_current.raise_for_status = MagicMock()
    fake_current.json.return_value = {
        "main": {"temp": 72, "humidity": 55},
        "weather": [{"description": "clear sky"}],
        "name": "Chicago",
    }
    fake_forecast = MagicMock()
    fake_forecast.raise_for_status = MagicMock()
    fake_forecast.json.return_value = {"list": [{"main": {"temp": 70}, "weather": [{"description": "clouds"}]}]}

    mock_http_client = AsyncMock()
    mock_http_client.get = AsyncMock(side_effect=[fake_current, fake_forecast])

    tool = WeatherTool()
    registry = ToolRegistry()
    registry.register(tool)

    router = _router_returning_tool(
        registry,
        "get_weather",
        {"query": "what's the weather today"},
        complete_return="It's 72 degrees and clear in Chicago.",
    )

    # Mock httpx.AsyncClient context manager
    mock_client_cm = MagicMock()
    mock_client_cm.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_client_cm.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("shared.config.load", return_value=cfg_with_key),
        patch("httpx.AsyncClient", return_value=mock_client_cm),
    ):
        mock_tts, mock_player, _ = _run_activation(
            config,
            db_conn,
            registry,
            router,
            transcript_text="what's the weather today",
            skip_reload=True,
        )

    mock_tts.synthesize.assert_called_once()
    spoken = mock_tts.synthesize.call_args[0][0]
    assert "72" in spoken or "clear" in spoken.lower() or "chicago" in spoken.lower()
    mock_player.play.assert_called_once()


# ===========================================================================
# Test 3 — CTATool end-to-end via _handle_activation
# ===========================================================================


def test_cta_tool_end_to_end(config, db_conn) -> None:
    """CTATool fetches mocked arrival JSON and narrates via mocked LLM through the full pipeline."""
    from pi.tools.cta import CtaTool

    cfg_with_key = AppConfig()
    cfg_with_key.cta.api_key = "test_cta_key"
    cfg_with_key.cta.stop_id_ohare = 30238
    cfg_with_key.cta.stop_id_forest_park = 30239

    fake_response = MagicMock()
    fake_response.raise_for_status = MagicMock()
    fake_response.json.return_value = {
        "ctatt": {
            "eta": [
                {
                    "destNm": "O'Hare",
                    "stpDe": "Service toward O'Hare",
                    "arrT": "20260618 14:05:00",
                    "prdt": "20260618 14:02:00",
                    "isApp": "0",
                    "isDly": "0",
                    "isSch": "0",
                }
            ]
        }
    }

    mock_http_client = AsyncMock()
    mock_http_client.get = AsyncMock(return_value=fake_response)

    mock_client_cm = MagicMock()
    mock_client_cm.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_client_cm.__aexit__ = AsyncMock(return_value=False)

    tool = CtaTool()
    registry = ToolRegistry()
    registry.register(tool)

    router = _router_returning_tool(
        registry,
        "cta_arrivals",
        {"query": "when's the next Blue Line", "direction": "ohare"},
        complete_return="The next O'Hare-bound train arrives in 3 minutes.",
    )

    with (
        patch("shared.config.load", return_value=cfg_with_key),
        patch("httpx.AsyncClient", return_value=mock_client_cm),
    ):
        mock_tts, mock_player, _ = _run_activation(
            config,
            db_conn,
            registry,
            router,
            transcript_text="when's the next Blue Line toward O'Hare",
            skip_reload=True,
        )

    mock_tts.synthesize.assert_called_once()
    spoken = mock_tts.synthesize.call_args[0][0]
    assert "o'hare" in spoken.lower() or "train" in spoken.lower() or "minute" in spoken.lower()
    mock_player.play.assert_called_once()


# ===========================================================================
# Test 4 — main() runs one full wake-word activation cycle
# ===========================================================================


@pytest.mark.asyncio
async def test_main_loop_single_activation(tmp_path) -> None:
    """main() processes exactly one wake-word activation with all hardware mocked."""
    from pi.main import main as assistant_main

    # One-shot WakeWordDetector: fires the callback on first start(), no-op after.
    fired = [False]

    class _OneShotDetector:
        def __init__(self, config, on_detection):
            self._cb = on_detection

        def start(self) -> None:
            if not fired[0]:
                fired[0] = True
                self._cb()  # → loop.call_soon_threadsafe(wake_event.set)

        def drain(self, n_frames: int = 50) -> None:
            pass

        def close(self) -> None:
            pass

    # Track when _handle_activation finishes the first cycle
    activation_done = asyncio.Event()
    _orig_handle = _main_module._handle_activation

    async def _tracked_handle(*args, **kwargs):
        await _orig_handle(*args, **kwargs)
        activation_done.set()

    # Memory DB in tmp_path
    conn = init_db(str(tmp_path / "memory.db"))

    # Tool request queue in tmp_path
    from pi.tool_requests.queue import ToolRequestQueue
    queue = ToolRequestQueue(str(tmp_path / "tool_requests.db"))

    # Mock heavy components
    mock_stt = MagicMock()
    mock_stt.transcribe = AsyncMock(return_value="what time is it")
    mock_stt.close = MagicMock()

    fallback_msg = ToolMessage(content="I'm not sure how to help with that.", tool_calls=None)
    mock_llm = MagicMock()
    mock_llm.chat_with_tools = AsyncMock(return_value=fallback_msg)
    mock_llm.complete = AsyncMock(return_value="It is three o'clock.")
    mock_llm.close = MagicMock()

    mock_tts = MagicMock()
    mock_tts.sample_rate = 22050
    mock_tts.synthesize = MagicMock(return_value=b"\x00" * 512)

    mock_player = MagicMock()
    mock_player.play = MagicMock()

    mock_prewarm = MagicMock()
    mock_prewarm.start = MagicMock()
    mock_prewarm.cancel = MagicMock()

    mock_registry = MagicMock(spec=ToolRegistry)
    mock_registry.all.return_value = []
    mock_registry.function_schemas.return_value = []
    mock_registry.load.return_value = None
    mock_registry.get.return_value = None

    with (
        patch("pi.main.WakeWordDetector", _OneShotDetector),
        patch("pi.main.HailoTranscriber", return_value=mock_stt),
        patch("pi.main.HailoLLMClient", return_value=mock_llm),
        patch("pi.main.PiperTTS", return_value=mock_tts),
        patch("pi.main.AudioPlayer", return_value=mock_player),
        patch("pi.main.PrewarmScheduler", return_value=mock_prewarm),
        patch("pi.main.ToolRegistry", return_value=mock_registry),
        patch("pi.main.ToolRequestQueue", return_value=queue),
        patch("pi.main.init_db", return_value=conn),
        patch("pi.main._capture_utterance", AsyncMock(return_value=(_FAKE_PCM, 16000))),
        patch("pi.main.identify", return_value="owner"),
        patch("pi.main._handle_activation", _tracked_handle),
    ):
        main_task = asyncio.create_task(assistant_main())
        await asyncio.wait_for(activation_done.wait(), timeout=5.0)
        main_task.cancel()
        try:
            await main_task
        except asyncio.CancelledError:
            pass

    conn.close()
    queue.close()

    assert activation_done.is_set(), "main() should have completed one full activation"
    assert fired[0], "WakeWordDetector should have fired once"
    mock_tts.synthesize.assert_called_once()
    mock_player.play.assert_called_once()
