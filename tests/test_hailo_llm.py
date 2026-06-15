"""Smoke tests for HailoLLMClient, ToolRouter, and build_system_prompt.

All tests mock hailo_platform so they run without Hailo hardware.
Run with: pytest tests/test_hailo_llm.py -v
"""
from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.config import HailoConfig
from shared.models import Transcript


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(model_path: str = "/models/llm.hef", timeout: float = 5.0):
    """Return a HailoLLMClient with hailo_platform fully mocked."""
    from pi.llm.hailo_client import HailoLLMClient

    mock_vdevice = MagicMock()
    mock_llm_instance = MagicMock()

    with (
        patch("pi.llm.hailo_client._HAILO_AVAILABLE", True),
        patch("pi.llm.hailo_client._VDevice", return_value=mock_vdevice),
        patch("pi.llm.hailo_client._HailoLLM", return_value=mock_llm_instance),
    ):
        cfg = HailoConfig(llm_model_path=model_path)
        client = HailoLLMClient(cfg, timeout=timeout)
        # Force lazy init now so tests can configure mock_llm_instance
        with (
            patch("pi.llm.hailo_client._VDevice", return_value=mock_vdevice),
            patch("pi.llm.hailo_client._HailoLLM", return_value=mock_llm_instance),
        ):
            client._vdevice = mock_vdevice
            client._llm = mock_llm_instance

    return client, mock_llm_instance


# ---------------------------------------------------------------------------
# HailoLLMClient — import guard
# ---------------------------------------------------------------------------


def test_hailo_client_raises_without_hardware() -> None:
    """ImportError if hailo_platform is not installed."""
    from pi.llm.hailo_client import HailoLLMClient

    with patch("pi.llm.hailo_client._HAILO_AVAILABLE", False):
        with pytest.raises(ImportError, match="hailo_platform"):
            HailoLLMClient(HailoConfig())


# ---------------------------------------------------------------------------
# HailoLLMClient — chat / complete
# ---------------------------------------------------------------------------


def test_chat_returns_model_output() -> None:
    client, mock_llm = _make_client()
    mock_llm.generate.return_value = "Sunny skies today."

    result = asyncio.run(client.chat([{"role": "user", "content": "Weather?"}]))

    assert result == "Sunny skies today."
    mock_llm.generate.assert_called_once()


def test_complete_builds_two_message_list() -> None:
    client, mock_llm = _make_client()
    mock_llm.generate.return_value = "Hello, Owner!"

    result = asyncio.run(client.complete("You are helpful.", "Hi"))

    assert result == "Hello, Owner!"
    call_args = mock_llm.generate.call_args[0][0]
    assert call_args[0]["role"] == "system"
    assert call_args[1]["role"] == "user"
    assert call_args[1]["content"] == "Hi"


def test_generate_joins_iterator_output() -> None:
    client, mock_llm = _make_client()
    mock_llm.generate.return_value = iter(["It ", "is ", "sunny."])

    result = asyncio.run(client.chat([{"role": "user", "content": "Weather?"}]))

    assert result == "It is sunny."


# ---------------------------------------------------------------------------
# HailoLLMClient — chat_with_tools
# ---------------------------------------------------------------------------


def test_chat_with_tools_parses_tool_call() -> None:
    from pi.llm.hailo_client import ToolMessage

    client, mock_llm = _make_client()
    mock_llm.generate.return_value = (
        '<tool_call>{"name": "cta_arrivals", "arguments": {"direction": "ohare"}}</tool_call>'
    )

    msg = asyncio.run(
        client.chat_with_tools(
            [{"role": "user", "content": "When's the next train?"}],
            tools=[{
                "type": "function",
                "function": {
                    "name": "cta_arrivals",
                    "description": "CTA arrivals",
                    "parameters": {"properties": {"direction": {}}},
                },
            }],
        )
    )

    assert isinstance(msg, ToolMessage)
    assert msg.tool_calls is not None
    assert msg.tool_calls[0].function.name == "cta_arrivals"
    assert msg.tool_calls[0].function.arguments == {"direction": "ohare"}
    assert msg.content is None


def test_chat_with_tools_no_tool_call_returns_content() -> None:
    from pi.llm.hailo_client import ToolMessage

    client, mock_llm = _make_client()
    mock_llm.generate.return_value = "I don't know how to help with that."

    msg = asyncio.run(
        client.chat_with_tools(
            [{"role": "user", "content": "Tell me a joke."}],
            tools=[],
        )
    )

    assert isinstance(msg, ToolMessage)
    assert msg.tool_calls is None
    assert msg.content == "I don't know how to help with that."


def test_chat_with_tools_injects_schema_into_system_prompt() -> None:
    client, mock_llm = _make_client()
    mock_llm.generate.return_value = "plain response"

    asyncio.run(
        client.chat_with_tools(
            [{"role": "system", "content": "Base prompt."}],
            tools=[{
                "type": "function",
                "function": {"name": "weather", "description": "Get weather", "parameters": {}},
            }],
        )
    )

    messages_passed = mock_llm.generate.call_args[0][0]
    system_content = messages_passed[0]["content"]
    assert "weather" in system_content
    assert "Base prompt." in system_content


def test_chat_with_tools_adds_system_if_missing() -> None:
    client, mock_llm = _make_client()
    mock_llm.generate.return_value = "response"

    asyncio.run(
        client.chat_with_tools(
            [{"role": "user", "content": "hello"}],
            tools=[{
                "type": "function",
                "function": {"name": "mytool", "description": "desc", "parameters": {}},
            }],
        )
    )

    messages_passed = mock_llm.generate.call_args[0][0]
    assert messages_passed[0]["role"] == "system"
    assert "mytool" in messages_passed[0]["content"]


# ---------------------------------------------------------------------------
# HailoLLMClient — error handling
# ---------------------------------------------------------------------------


def test_llm_timeout_raises_llm_timeout_error() -> None:
    from pi.llm.hailo_client import LLMTimeoutError

    client, mock_llm = _make_client(timeout=0.001)
    import time

    mock_llm.generate.side_effect = lambda *a, **kw: time.sleep(1)

    with pytest.raises(LLMTimeoutError):
        asyncio.run(client.chat([{"role": "user", "content": "slow?"}]))


def test_llm_runtime_error_raises_llm_error() -> None:
    from pi.llm.hailo_client import LLMError

    client, mock_llm = _make_client()
    mock_llm.generate.side_effect = RuntimeError("NPU crash")

    with pytest.raises(LLMError, match="NPU crash"):
        asyncio.run(client.chat([{"role": "user", "content": "go"}]))


def test_close_releases_resources() -> None:
    client, mock_llm = _make_client()
    mock_vdevice = client._vdevice

    client.close()

    mock_llm.release.assert_called_once()
    mock_vdevice.release.assert_called_once()
    assert client._llm is None
    assert client._vdevice is None


# ---------------------------------------------------------------------------
# ToolRouter
# ---------------------------------------------------------------------------


def _make_router(llm_response: str | None = None, tool_call_json: str | None = None):
    """Return a ToolRouter with mocked client and a registry with one fake tool."""
    from pi.llm.hailo_client import HailoLLMClient, ToolCallItem, ToolFunction, ToolMessage
    from pi.llm.router import ToolRouter

    mock_llm = MagicMock(spec=HailoLLMClient)

    if tool_call_json:
        data = json.loads(tool_call_json)
        fn = ToolFunction(name=data["name"], arguments=data.get("arguments", {}))
        msg = ToolMessage(content=None, tool_calls=[ToolCallItem(function=fn)])
    else:
        msg = ToolMessage(content=llm_response or "Here's your answer.", tool_calls=None)

    mock_llm.chat_with_tools = AsyncMock(return_value=msg)
    mock_llm.complete = AsyncMock(return_value=llm_response or "Here's your answer.")

    mock_registry = MagicMock()
    mock_registry.function_schemas.return_value = [
        {
            "type": "function",
            "function": {
                "name": "cta_arrivals",
                "description": "CTA train arrivals",
                "parameters": {"properties": {"direction": {}}},
            },
        }
    ]

    router = ToolRouter(llm=mock_llm, registry=mock_registry)
    return router, mock_llm, mock_registry


def test_router_returns_tool_call_when_matched() -> None:
    from pi.llm.router import ToolCall

    router, _, _ = _make_router(
        tool_call_json='{"name": "cta_arrivals", "arguments": {"direction": "ohare"}}'
    )
    transcript = Transcript(session_id="s1", text="When's the next train?", user="owner")

    tool_call, fallback = asyncio.run(router.route(transcript))

    assert isinstance(tool_call, ToolCall)
    assert tool_call.tool_name == "cta_arrivals"
    assert tool_call.params == {"direction": "ohare"}
    assert fallback == ""


def test_router_returns_fallback_when_no_tool() -> None:
    router, _, _ = _make_router(llm_response="It's 65 degrees and sunny.")
    transcript = Transcript(session_id="s1", text="Tell me a joke.", user="emily")

    tool_call, fallback = asyncio.run(router.route(transcript))

    assert tool_call is None
    assert fallback == "It's 65 degrees and sunny."


def test_router_uses_plain_complete_when_no_schemas() -> None:
    from pi.llm.hailo_client import HailoLLMClient
    from pi.llm.router import ToolRouter

    mock_llm = MagicMock(spec=HailoLLMClient)
    mock_llm.complete = AsyncMock(return_value="No tools available.")

    mock_registry = MagicMock()
    mock_registry.function_schemas.return_value = []

    router = ToolRouter(llm=mock_llm, registry=mock_registry)
    transcript = Transcript(session_id="s1", text="Hello!", user="unknown")

    tool_call, fallback = asyncio.run(router.route(transcript))

    assert tool_call is None
    assert fallback == "No tools available."
    mock_llm.complete.assert_called_once()


def test_router_passes_context_turns_to_messages() -> None:
    router, mock_llm, _ = _make_router(llm_response="Sure!")
    transcript = Transcript(session_id="s1", text="What about now?", user="owner")
    context = [
        {"role": "user", "content": "Play jazz."},
        {"role": "assistant", "content": "Playing jazz now."},
    ]

    asyncio.run(router.route(transcript, context_turns=context))

    call_args = mock_llm.chat_with_tools.call_args
    messages = call_args[0][0]
    roles = [m["role"] for m in messages]
    assert "user" in roles
    assert "assistant" in roles


# ---------------------------------------------------------------------------
# build_system_prompt
# ---------------------------------------------------------------------------


def test_prompt_known_user_includes_name() -> None:
    from pi.llm.prompts import build_system_prompt

    prompt = build_system_prompt(user="owner")
    assert "Owner" in prompt


def test_prompt_unknown_user_has_ask_who() -> None:
    from pi.llm.prompts import build_system_prompt

    prompt = build_system_prompt(user="unknown")
    assert "who" in prompt.lower()


def test_prompt_with_context_turns_mentions_memory() -> None:
    from pi.llm.prompts import build_system_prompt

    prompt = build_system_prompt(
        user="emily",
        context_turns=[{"role": "user", "content": "hi"}],
    )
    assert "context" in prompt.lower() or "conversation" in prompt.lower()


def test_prompt_with_tool_instructions_included() -> None:
    from pi.llm.prompts import build_system_prompt

    prompt = build_system_prompt(
        user="owner",
        tool_instructions="Use the flux_capacitor tool for time travel.",
    )
    assert "flux_capacitor" in prompt


def test_prompt_empty_tool_instructions_skipped() -> None:
    from pi.llm.prompts import build_system_prompt

    prompt = build_system_prompt(user="owner", tool_instructions="")
    assert "Additional tool guidance" not in prompt
