"""Integration test for CtaTool end-to-end flow.

Requires a real CTA Train Tracker API key in config/settings.yaml.
Skips automatically when the key is still CHANGE_ME or empty.

Register free at https://www.transitchicago.com/developers/traintrackerapply/

Run with: pytest tests/test_cta_integration.py -v -s
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

import shared.config as cfg_module


def _real_cta_key() -> str:
    """Return the CTA API key from config, or empty string if placeholder."""
    cfg = cfg_module.load()
    key = cfg.cta.api_key
    if not key or key == "CHANGE_ME":
        return ""
    return key


_REQUIRES_CTA_KEY = pytest.mark.skipif(
    not _real_cta_key(),
    reason="No real CTA Train Tracker API key configured — set cta.api_key in config/settings.yaml",
)


@_REQUIRES_CTA_KEY
@pytest.mark.asyncio
async def test_cta_next_blue_line_real_api() -> None:
    """'When's the next Blue Line?' hits the real CTA API; LLM is mocked."""
    from server.tools.cta import CtaTool

    tool = CtaTool()

    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(
        return_value="The next Blue Line toward O'Hare arrives in 4 minutes, and toward Forest Park in 7 minutes."
    )

    with patch("server.tools.cta.OllamaClient", return_value=mock_llm):
        result = await tool.run({"query": "When's the next Blue Line?"}, user="owner")

    assert isinstance(result, str), "tool must return a string"
    assert len(result) > 10, "response should be a non-trivial sentence"

    mock_llm.complete.assert_awaited_once()
    call_system, call_user = mock_llm.complete.call_args[0]

    assert "Arrival data:" in call_user, "user message should include 'Arrival data:' section"
    arrivals_json = call_user.split("Arrival data:\n")[1]
    arrivals = json.loads(arrivals_json)
    assert isinstance(arrivals, list), "arrival data must be a list"
    assert len(arrivals) > 0, "CTA API should return at least one arrival"

    first = arrivals[0]
    assert "destination" in first, "each arrival must have a destination field"
    assert "arrival_time" in first, "each arrival must have an arrival_time field"
    assert "is_delayed" in first, "each arrival must have an is_delayed field"

    assert "direction" in call_system.lower() or "group" in call_system.lower(), (
        "system prompt for 'both' direction should mention grouping by direction"
    )


@_REQUIRES_CTA_KEY
@pytest.mark.asyncio
async def test_cta_ohare_direction_real_api() -> None:
    """Directional query toward O'Hare hits only the O'Hare stop on the real API."""
    from server.tools.cta import CtaTool

    tool = CtaTool()
    cfg = cfg_module.load()
    captured: list[tuple[str, str]] = []

    async def _spy_complete(system: str, user_msg: str) -> str:
        captured.append((system, user_msg))
        return "The next Blue Line toward O'Hare arrives in 5 minutes."

    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(side_effect=_spy_complete)

    with patch("server.tools.cta.OllamaClient", return_value=mock_llm):
        result = await tool.run(
            {"query": "next train toward O'Hare", "direction": "ohare"}, user="owner"
        )

    assert isinstance(result, str)
    assert len(result) > 10

    system_prompt, user_msg = captured[0]
    assert "O'Hare" in system_prompt, "system prompt must mention O'Hare for ohare direction"

    arrivals_json = user_msg.split("Arrival data:\n")[1]
    arrivals = json.loads(arrivals_json)
    assert isinstance(arrivals, list)
    assert len(arrivals) > 0

    destinations = {a["destination"] for a in arrivals}
    assert all("O'Hare" in d or "Forest Park" in d for d in destinations), (
        "all arrivals should be standard Blue Line destinations"
    )
