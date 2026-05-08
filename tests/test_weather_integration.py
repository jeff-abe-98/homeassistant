"""Integration test for WeatherTool end-to-end flow.

Requires a real OpenWeatherMap API key in config/settings.yaml.
Skips automatically when the key is still CHANGE_ME or empty.

Run with: pytest tests/test_weather_integration.py -v -s
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

import shared.config as cfg_module


def _real_owm_key() -> str:
    """Return the OWM key from config, or empty string if placeholder."""
    cfg = cfg_module.load()
    key = cfg.weather.api_key
    if not key or key == "CHANGE_ME":
        return ""
    return key


_REQUIRES_OWM_KEY = pytest.mark.skipif(
    not _real_owm_key(),
    reason="No real OpenWeatherMap API key configured — set weather.api_key in config/settings.yaml",
)


@_REQUIRES_OWM_KEY
@pytest.mark.asyncio
async def test_weather_today_real_api() -> None:
    """'What's the weather today?' hits the real OWM API; LLM is mocked."""
    from server.tools.weather import WeatherTool

    tool = WeatherTool()
    cfg = cfg_module.load()

    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(
        return_value=(
            "Right now in Chicago it is partly cloudy and around 68 degrees. "
            "Expect light winds and a chance of showers later tonight."
        )
    )

    with patch("server.tools.weather.OllamaClient", return_value=mock_llm):
        result = await tool.run({"query": "What's the weather today?"}, user="owner")

    assert isinstance(result, str), "tool must return a string"
    assert len(result) > 10, "response should be a non-trivial sentence"
    # The mocked LLM call must have received the real OWM payload
    mock_llm.complete.assert_awaited_once()
    call_system, call_user = mock_llm.complete.call_args[0]
    assert "current" in call_user, "system message should include 'current' weather key"
    assert "forecast" in call_user, "system message should include 'forecast' key"
    assert cfg.weather.location in call_user, "location should appear in the payload"


@_REQUIRES_OWM_KEY
@pytest.mark.asyncio
async def test_weather_forecast_real_api() -> None:
    """'Will it rain tomorrow?' also hits real OWM; verifies forecast data is passed."""
    import json

    from server.tools.weather import WeatherTool

    tool = WeatherTool()
    cfg = cfg_module.load()

    captured: list[str] = []

    async def _spy_complete(system: str, user_msg: str) -> str:
        captured.append(user_msg)
        return "There is a 40 percent chance of rain tomorrow afternoon, with a high of 62 degrees."

    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(side_effect=_spy_complete)

    with patch("server.tools.weather.OllamaClient", return_value=mock_llm):
        result = await tool.run({"query": "Will it rain tomorrow?"}, user="owner")

    assert isinstance(result, str)
    assert len(result) > 10

    user_msg = captured[0]
    payload_str = user_msg.split("Weather data:\n")[1]
    payload = json.loads(payload_str)
    assert "current" in payload, "payload must include 'current' from OWM"
    assert "forecast" in payload, "payload must include 'forecast' from OWM"
    assert isinstance(payload["forecast"].get("list"), list), "forecast.list should be a list"
    assert len(payload["forecast"]["list"]) > 0, "forecast list should not be empty"
