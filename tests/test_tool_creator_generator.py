"""Smoke tests for server/tool_creator/generator.py."""

from __future__ import annotations

import pytest

from server.tool_creator.generator import (
    ToolGenerator,
    _build_user_message,
    _strip_fences,
    _syntax_check,
)

# ---------------------------------------------------------------------------
# _strip_fences
# ---------------------------------------------------------------------------

def test_strip_fences_removes_python_fence():
    src = "```python\nprint('hello')\n```"
    assert _strip_fences(src) == "print('hello')"


def test_strip_fences_removes_plain_fence():
    src = "```\nprint('hello')\n```"
    assert _strip_fences(src) == "print('hello')"


def test_strip_fences_no_fence_unchanged():
    src = "print('hello')"
    assert _strip_fences(src) == "print('hello')"


def test_strip_fences_strips_outer_whitespace():
    src = "  \n```python\ncode\n```\n  "
    assert _strip_fences(src) == "code"


# ---------------------------------------------------------------------------
# _syntax_check
# ---------------------------------------------------------------------------

def test_syntax_check_valid_returns_none():
    assert _syntax_check("x = 1 + 2") is None


def test_syntax_check_invalid_returns_error_string():
    error = _syntax_check("def broken(:")
    assert error is not None
    assert isinstance(error, str)


def test_syntax_check_empty_string_is_valid():
    assert _syntax_check("") is None


# ---------------------------------------------------------------------------
# _build_user_message
# ---------------------------------------------------------------------------

def test_build_user_message_contains_intent():
    msg = _build_user_message("tell jokes", [])
    assert "tell jokes" in msg


def test_build_user_message_lists_existing_names():
    msg = _build_user_message("fetch news", ["get_weather", "cta_arrivals"])
    assert "get_weather" in msg
    assert "cta_arrivals" in msg


def test_build_user_message_no_existing_names():
    msg = _build_user_message("do something", [])
    assert "existing" not in msg.lower() or "not reuse" not in msg


# ---------------------------------------------------------------------------
# ToolGenerator.generate — mocked LLM
# ---------------------------------------------------------------------------

_VALID_TOOL_SOURCE = """\
from server.tools.base import BaseTool

class JokeTool(BaseTool):
    name = "tell_joke"
    description = "Tell a random joke."
    parameters = {
        "type": "object",
        "properties": {},
        "required": []
    }

    async def run(self, params: dict, user: str) -> str:
        return "Why did the chicken cross the road? To get to the other side."
"""


class _FakeLLM:
    """Fake OllamaClient that returns preset responses."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = iter(responses)

    async def complete(self, system_prompt: str, user_message: str) -> str:
        return next(self._responses)


@pytest.mark.asyncio
async def test_generate_returns_source_on_first_valid_attempt():
    llm = _FakeLLM([_VALID_TOOL_SOURCE])
    gen = ToolGenerator(llm=llm)
    src = await gen.generate("tell jokes")
    assert "JokeTool" in src
    assert "tell_joke" in src


@pytest.mark.asyncio
async def test_generate_retries_on_invalid_syntax():
    invalid = "def broken(:"
    llm = _FakeLLM([invalid, _VALID_TOOL_SOURCE])
    gen = ToolGenerator(llm=llm)
    src = await gen.generate("tell jokes")
    assert "JokeTool" in src


@pytest.mark.asyncio
async def test_generate_raises_after_max_retries():
    invalid = "def broken(:"
    llm = _FakeLLM([invalid, invalid, invalid])
    gen = ToolGenerator(llm=llm)
    with pytest.raises(ValueError, match="valid Python"):
        await gen.generate("do something")


@pytest.mark.asyncio
async def test_generate_strips_fences_from_llm_response():
    fenced = f"```python\n{_VALID_TOOL_SOURCE}\n```"
    llm = _FakeLLM([fenced])
    gen = ToolGenerator(llm=llm)
    src = await gen.generate("tell jokes")
    assert "```" not in src
    assert "JokeTool" in src


@pytest.mark.asyncio
async def test_generate_passes_existing_names_to_llm():
    captured: list[str] = []

    class _CaptureLLM:
        async def complete(self, system_prompt: str, user_message: str) -> str:
            captured.append(user_message)
            return _VALID_TOOL_SOURCE

    gen = ToolGenerator(llm=_CaptureLLM())  # type: ignore[arg-type]
    await gen.generate("fetch news headlines", existing_tool_names=["get_weather"])
    assert "get_weather" in captured[0]
