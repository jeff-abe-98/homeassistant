"""Smoke tests for the tool-creator integration in server/main.py.

Tests _needs_new_tool, _handle_transcript (tool-creator branch), and
_create_and_notify using asyncio.run() to avoid needing pytest-asyncio.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.models import AssistantResponse, Transcript


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _transcript(text: str = "turn off the sprinklers", user: str = "owner") -> Transcript:
    return Transcript(session_id=str(uuid.uuid4()), text=text, user=user)


def _mock_websocket() -> MagicMock:
    ws = MagicMock()
    ws.send_text = AsyncMock()
    return ws


# ---------------------------------------------------------------------------
# _needs_new_tool
# ---------------------------------------------------------------------------

def test_needs_new_tool_returns_true_when_llm_says_yes():
    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value="yes")
    with patch("server.main._llm", mock_llm):
        from server.main import _needs_new_tool
        result = asyncio.run(_needs_new_tool("turn off the sprinklers"))
    assert result is True


def test_needs_new_tool_returns_true_for_yes_with_trailing_text():
    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value="yes, this requires an external API")
    with patch("server.main._llm", mock_llm):
        from server.main import _needs_new_tool
        result = asyncio.run(_needs_new_tool("turn off the sprinklers"))
    assert result is True


def test_needs_new_tool_returns_false_when_llm_says_no():
    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value="no")
    with patch("server.main._llm", mock_llm):
        from server.main import _needs_new_tool
        result = asyncio.run(_needs_new_tool("what is 2 plus 2?"))
    assert result is False


def test_needs_new_tool_returns_false_for_other_llm_response():
    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value="Two plus two equals four.")
    with patch("server.main._llm", mock_llm):
        from server.main import _needs_new_tool
        result = asyncio.run(_needs_new_tool("what is 2 plus 2?"))
    assert result is False


def test_needs_new_tool_case_insensitive():
    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value="YES")
    with patch("server.main._llm", mock_llm):
        from server.main import _needs_new_tool
        result = asyncio.run(_needs_new_tool("dim the kitchen lights"))
    assert result is True


# ---------------------------------------------------------------------------
# _handle_transcript — existing tool matched
# ---------------------------------------------------------------------------

def test_handle_transcript_runs_existing_tool_when_router_matches():
    transcript = _transcript("what's the weather?")
    ws = _mock_websocket()

    mock_tool = MagicMock()
    mock_tool.run = AsyncMock(return_value="Sunny, 72°F.")

    mock_router = MagicMock()
    mock_router.route = AsyncMock(return_value=MagicMock(tool_name="weather", params={}))

    mock_registry = MagicMock()
    mock_registry.get.return_value = mock_tool

    with (
        patch("server.main._router", mock_router),
        patch("server.main._registry", mock_registry),
    ):
        from server.main import _handle_transcript
        response = asyncio.run(_handle_transcript(transcript, ws))

    assert response is not None
    assert "72" in response.text or "Sunny" in response.text


# ---------------------------------------------------------------------------
# _handle_transcript — no tool matched, needs new tool
# ---------------------------------------------------------------------------

def test_handle_transcript_returns_notification_when_needs_new_tool():
    transcript = _transcript("turn off the sprinklers")
    ws = _mock_websocket()

    mock_router = MagicMock()
    mock_router.route = AsyncMock(return_value=None)

    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value="yes")

    mock_generator = MagicMock()
    mock_generator.generate = AsyncMock(return_value="# tool source")

    mock_registry = MagicMock()
    mock_registry.all.return_value = []

    async def _run():
        with (
            patch("server.main._router", mock_router),
            patch("server.main._llm", mock_llm),
            patch("server.main._generator", mock_generator),
            patch("server.main._registry", mock_registry),
            patch("server.main.validate", AsyncMock(return_value=MagicMock(success=False, error="test"))),
        ):
            from server.main import _handle_transcript
            response = await _handle_transcript(transcript, ws)
            # Let background task settle
            await asyncio.sleep(0)
            return response

    response = asyncio.run(_run())

    assert response is not None
    assert "don't know how to do that yet" in response.text
    assert "figure it out" in response.text


def test_handle_transcript_notification_text_exact():
    transcript = _transcript("dim the kitchen lights")
    ws = _mock_websocket()

    mock_router = MagicMock()
    mock_router.route = AsyncMock(return_value=None)

    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value="yes")

    mock_registry = MagicMock()
    mock_registry.all.return_value = []

    async def _run():
        with (
            patch("server.main._router", mock_router),
            patch("server.main._llm", mock_llm),
            patch("server.main._registry", mock_registry),
            patch("server.main._generator", AsyncMock()),
            patch("server.main.validate", AsyncMock(return_value=MagicMock(success=False, error="x"))),
        ):
            from server.main import _handle_transcript
            return await _handle_transcript(transcript, ws)

    response = asyncio.run(_run())
    assert response.text == (
        "I don't know how to do that yet, but I'll figure it out. I'll let you know when I can."
    )


# ---------------------------------------------------------------------------
# _handle_transcript — no tool matched, plain conversation
# ---------------------------------------------------------------------------

def test_handle_transcript_falls_back_to_llm_for_conversation():
    transcript = _transcript("what is 2 plus 2?")
    ws = _mock_websocket()

    mock_router = MagicMock()
    mock_router.route = AsyncMock(return_value=None)

    mock_llm = AsyncMock()
    # First call: _needs_new_tool → "no"; second call: plain LLM → answer
    mock_llm.complete = AsyncMock(side_effect=["no", "Two plus two equals four."])

    with (
        patch("server.main._router", mock_router),
        patch("server.main._llm", mock_llm),
    ):
        from server.main import _handle_transcript
        response = asyncio.run(_handle_transcript(transcript, ws))

    assert response is not None
    assert "four" in response.text.lower() or "4" in response.text


# ---------------------------------------------------------------------------
# _create_and_notify — pipeline paths
# ---------------------------------------------------------------------------

def test_create_and_notify_logs_warning_on_validation_failure():
    transcript = _transcript("lock the garage door")
    ws = _mock_websocket()

    mock_generator = MagicMock()
    mock_generator.generate = AsyncMock(return_value="# source")

    mock_registry = MagicMock()
    mock_registry.all.return_value = []

    mock_validate = AsyncMock(return_value=MagicMock(success=False, error="no BaseTool subclass"))

    async def _run():
        with (
            patch("server.main._generator", mock_generator),
            patch("server.main._registry", mock_registry),
            patch("server.main.validate", mock_validate),
        ):
            from server.main import _create_and_notify
            await _create_and_notify(transcript, ws)

    asyncio.run(_run())
    # validation failed → no notification sent
    ws.send_text.assert_not_called()


def test_create_and_notify_logs_warning_on_install_failure():
    transcript = _transcript("open the blinds")
    ws = _mock_websocket()

    mock_generator = MagicMock()
    mock_generator.generate = AsyncMock(return_value="# source")

    mock_registry = MagicMock()
    mock_registry.all.return_value = []

    mock_validate = AsyncMock(
        return_value=MagicMock(success=True, tool_name="blind_control", tool_description="Controls blinds")
    )
    mock_install = MagicMock(return_value=MagicMock(success=False, error="write error"))

    async def _run():
        with (
            patch("server.main._generator", mock_generator),
            patch("server.main._registry", mock_registry),
            patch("server.main.validate", mock_validate),
            patch("server.main.install", mock_install),
        ):
            from server.main import _create_and_notify
            await _create_and_notify(transcript, ws)

    asyncio.run(_run())
    ws.send_text.assert_not_called()


def test_create_and_notify_sends_completion_notification_on_success():
    transcript = _transcript("water the plants")
    ws = _mock_websocket()

    mock_generator = MagicMock()
    mock_generator.generate = AsyncMock(return_value="# source")

    mock_registry = MagicMock()
    mock_registry.all.return_value = []

    mock_validate = AsyncMock(
        return_value=MagicMock(success=True, tool_name="plant_watering", tool_description="Waters plants")
    )
    mock_install = MagicMock(
        return_value=MagicMock(success=True, tool_name="plant_watering", path="/tmp/plant_watering.py")
    )

    async def _run():
        with (
            patch("server.main._generator", mock_generator),
            patch("server.main._registry", mock_registry),
            patch("server.main.validate", mock_validate),
            patch("server.main.install", mock_install),
        ):
            from server.main import _create_and_notify
            await _create_and_notify(transcript, ws)

    asyncio.run(_run())
    ws.send_text.assert_called_once()
    sent_json = ws.send_text.call_args[0][0]
    response = AssistantResponse.model_validate_json(sent_json)
    assert response.session_id == transcript.session_id
    assert "I can do that now" in response.text


def test_create_and_notify_suppresses_websocket_send_error():
    transcript = _transcript("turn off the porch light")
    ws = _mock_websocket()
    ws.send_text = AsyncMock(side_effect=RuntimeError("connection closed"))

    mock_generator = MagicMock()
    mock_generator.generate = AsyncMock(return_value="# source")

    mock_registry = MagicMock()
    mock_registry.all.return_value = []

    mock_validate = AsyncMock(
        return_value=MagicMock(success=True, tool_name="porch_light", tool_description="Controls porch light")
    )
    mock_install = MagicMock(
        return_value=MagicMock(success=True, tool_name="porch_light", path="/tmp/porch_light.py")
    )

    async def _run():
        with (
            patch("server.main._generator", mock_generator),
            patch("server.main._registry", mock_registry),
            patch("server.main.validate", mock_validate),
            patch("server.main.install", mock_install),
        ):
            from server.main import _create_and_notify
            # Should not raise even though send_text raises
            await _create_and_notify(transcript, ws)

    asyncio.run(_run())  # must not raise
