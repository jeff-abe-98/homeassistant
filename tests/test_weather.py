"""Smoke tests for WeatherTool and WeatherConfig wiring.

Run with: pytest tests/test_weather.py -v
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.config import AppConfig, WeatherConfig


# ---------------------------------------------------------------------------
# Config wiring
# ---------------------------------------------------------------------------

def test_weather_config_defaults() -> None:
    cfg = AppConfig()
    assert cfg.weather.api_key == ""
    assert cfg.weather.location == "Chicago, IL"
    assert cfg.weather.units == "imperial"


def test_weather_config_loaded_from_yaml(tmp_path) -> None:
    settings = tmp_path / "settings.yaml"
    settings.write_text(
        "weather:\n  api_key: test-key-123\n  location: 'Austin, TX'\n  units: metric\n"
    )
    import shared.config as cfg_module
    cfg = cfg_module.load(str(settings))
    assert cfg.weather.api_key == "test-key-123"
    assert cfg.weather.location == "Austin, TX"
    assert cfg.weather.units == "metric"


# ---------------------------------------------------------------------------
# WeatherTool.run() — missing / placeholder key
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_weather_missing_key_returns_error() -> None:
    from pi.tools.weather import WeatherTool

    tool = WeatherTool()
    mock_cfg = MagicMock()
    mock_cfg.weather.api_key = ""
    mock_cfg.weather.location = "Chicago, IL"
    mock_cfg.weather.units = "imperial"

    with patch("pi.tools.weather.cfg_module.load", return_value=mock_cfg):
        result = await tool.run({"query": "what's the weather?"}, user="owner")

    assert "api key" in result.lower() or "set up" in result.lower()


@pytest.mark.asyncio
async def test_weather_placeholder_key_returns_error() -> None:
    from pi.tools.weather import WeatherTool

    tool = WeatherTool()
    mock_cfg = MagicMock()
    mock_cfg.weather.api_key = "CHANGE_ME"
    mock_cfg.weather.location = "Chicago, IL"
    mock_cfg.weather.units = "imperial"

    with patch("pi.tools.weather.cfg_module.load", return_value=mock_cfg):
        result = await tool.run({"query": "will it rain?"}, user="owner")

    assert "set up" in result.lower() or "api key" in result.lower()


# ---------------------------------------------------------------------------
# WeatherTool.run() — happy path (mocked HTTP + LLM)
# ---------------------------------------------------------------------------

_FAKE_CURRENT = {"main": {"temp": 72, "humidity": 55}, "weather": [{"description": "clear sky"}]}
_FAKE_FORECAST = {"list": [{"dt_txt": "2026-05-09 12:00:00", "main": {"temp": 68}}]}


@pytest.mark.asyncio
async def test_weather_happy_path() -> None:
    from pi.tools.weather import WeatherTool

    tool = WeatherTool()

    mock_cfg = MagicMock()
    mock_cfg.weather.api_key = "real-key"
    mock_cfg.weather.location = "Chicago, IL"
    mock_cfg.weather.units = "imperial"
    mock_cfg.ollama.host = "http://localhost:11434"
    mock_cfg.ollama.model = "llama3.1:8b-instruct-q4_K_M"

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(side_effect=[_FAKE_CURRENT, _FAKE_FORECAST])

    mock_http_client = AsyncMock()
    mock_http_client.get = AsyncMock(return_value=mock_resp)
    mock_http_ctx = MagicMock()
    mock_http_ctx.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value="It is currently 72 degrees and clear in Chicago.")

    with (
        patch("pi.tools.weather.cfg_module.load", return_value=mock_cfg),
        patch("pi.tools.weather.httpx.AsyncClient", return_value=mock_http_ctx),
        patch("pi.tools.weather.HailoLLMClient", return_value=mock_llm),
    ):
        result = await tool.run({"query": "what's the weather today?"}, user="owner")

    assert "72" in result or "clear" in result.lower()
    mock_llm.complete.assert_awaited_once()
    call_args = mock_llm.complete.call_args
    payload_str = call_args[0][1]  # second positional arg (user message)
    payload = json.loads(payload_str.split("Weather data:\n")[1])
    assert "current" in payload
    assert "forecast" in payload
