"""Smoke tests for ToolRouter.narrate() — single LLM call for tool output narration.

Verifies that:
- narrate() calls the LLM exactly once per invocation
- the routing context (user, question) is included in the narration prompt
- tools with needs_narration=True trigger narrate() in the activation pipeline
Run with: pytest tests/test_narration.py -v
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.config import HailoConfig
from shared.models import Transcript


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_router():
    """Return a ToolRouter with a fully mocked HailoLLMClient."""
    from pi.llm.hailo_client import HailoLLMClient, ToolMessage
    from pi.llm.router import ToolRouter

    mock_llm = MagicMock(spec=HailoLLMClient)
    mock_llm.complete = AsyncMock(return_value="Narrated response.")
    mock_llm.chat_with_tools = AsyncMock(
        return_value=ToolMessage(content="Conversational reply.", tool_calls=None)
    )

    mock_registry = MagicMock()
    mock_registry.function_schemas.return_value = []

    router = ToolRouter(mock_llm, mock_registry)
    return router, mock_llm


# ---------------------------------------------------------------------------
# narrate() — basic behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_narrate_calls_llm_complete_once() -> None:
    """narrate() must call LLM exactly once (not twice)."""
    router, mock_llm = _make_router()

    result = await router.narrate("get_weather", "Temperature: 72°F, clear sky", "owner")

    assert result == "Narrated response."
    mock_llm.complete.assert_awaited_once()


@pytest.mark.asyncio
async def test_narrate_includes_tool_result_in_prompt() -> None:
    """Raw tool data must appear in the user message sent to the LLM."""
    router, mock_llm = _make_router()
    raw_data = "Temperature: 72°F, clear sky\nUser question: what's the weather"

    await router.narrate("get_weather", raw_data, "owner")

    call_args = mock_llm.complete.call_args
    user_msg = call_args[0][1]
    assert "72°F" in user_msg or raw_data in user_msg


@pytest.mark.asyncio
async def test_narrate_includes_original_question_from_route() -> None:
    """narrate() uses the question stored by the preceding route() call."""
    from pi.llm.hailo_client import ToolMessage

    router, mock_llm = _make_router()
    mock_llm.chat_with_tools = AsyncMock(
        return_value=ToolMessage(
            content=None,
            tool_calls=None,
        )
    )

    transcript = Transcript(session_id="s1", text="what is the weather today", user="owner")
    await router.route(transcript)

    await router.narrate("get_weather", "Temperature: 65°F", "owner")

    call_args = mock_llm.complete.call_args
    user_msg = call_args[0][1]
    assert "what is the weather today" in user_msg


@pytest.mark.asyncio
async def test_narrate_includes_user_in_system_prompt() -> None:
    """User identity must appear in the system prompt for personalised narration."""
    router, mock_llm = _make_router()

    await router.narrate("cta_arrivals", "To O'Hare: arrives 12:04", "emily")

    call_args = mock_llm.complete.call_args
    system_prompt = call_args[0][0]
    assert "emily" in system_prompt.lower()


@pytest.mark.asyncio
async def test_narrate_tool_name_in_prompt() -> None:
    """Tool name should appear in the user message so the LLM knows the source."""
    router, mock_llm = _make_router()

    await router.narrate("cta_arrivals", "No arrivals found.", "owner")

    call_args = mock_llm.complete.call_args
    user_msg = call_args[0][1]
    assert "cta_arrivals" in user_msg


# ---------------------------------------------------------------------------
# needs_narration flag
# ---------------------------------------------------------------------------


def test_weather_tool_needs_narration() -> None:
    from pi.tools.weather import WeatherTool
    assert WeatherTool.needs_narration is True


def test_cta_tool_needs_narration() -> None:
    from pi.tools.cta import CtaTool
    assert CtaTool.needs_narration is True


def test_calendar_tool_needs_narration() -> None:
    from pi.tools.calendar import CalendarTool
    assert CalendarTool.needs_narration is True


def test_add_calendar_event_does_not_need_narration() -> None:
    from pi.tools.calendar import AddCalendarEventTool
    assert not getattr(AddCalendarEventTool, "needs_narration", False)


def test_base_tool_needs_narration_default_false() -> None:
    from pi.tools.base import BaseTool
    assert BaseTool.needs_narration is False


# ---------------------------------------------------------------------------
# One LLM call total: route (no tool) + narrate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_route_no_tool_plus_narrate_is_two_llm_calls() -> None:
    """route() (no-tool, schemas present) + narrate() = 2 total generate_all calls."""
    from pi.llm.hailo_client import HailoLLMClient, ToolMessage
    from pi.llm.router import ToolRouter

    mock_llm = MagicMock(spec=HailoLLMClient)
    call_count = 0

    async def _chat_with_tools(messages, tools):
        nonlocal call_count
        call_count += 1
        return ToolMessage(content="Conversational reply.", tool_calls=None)

    async def _complete(system, user):
        nonlocal call_count
        call_count += 1
        return "Narrated."

    mock_llm.chat_with_tools = _chat_with_tools
    mock_llm.complete = _complete

    mock_registry = MagicMock()
    mock_registry.function_schemas.return_value = [{"type": "function", "function": {"name": "get_weather", "description": "weather", "parameters": {}}}]

    router = ToolRouter(mock_llm, mock_registry)
    transcript = Transcript(session_id="s1", text="what's the weather", user="owner")

    await router.route(transcript)
    await router.narrate("get_weather", "Temperature: 72°F", "owner")

    assert call_count == 2


# ---------------------------------------------------------------------------
# _summarize_weather helper
# ---------------------------------------------------------------------------


def test_summarize_weather_contains_key_fields() -> None:
    from pi.tools.weather import _summarize_weather

    current = {
        "name": "Chicago",
        "main": {"temp": 72, "feels_like": 70, "humidity": 55},
        "weather": [{"description": "clear sky"}],
        "wind": {"speed": 8},
    }
    forecast = {
        "list": [
            {"dt_txt": "2026-06-26 15:00:00", "main": {"temp": 68}, "weather": [{"description": "partly cloudy"}]}
        ]
    }
    result = _summarize_weather(current, forecast, "what's the weather today")

    assert "Chicago" in result
    assert "72" in result
    assert "clear sky" in result
    assert "User question:" in result
    assert "Upcoming forecast:" in result
