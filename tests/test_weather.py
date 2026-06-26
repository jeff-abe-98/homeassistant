"""Smoke tests for WeatherTool and WeatherConfig wiring.

Run with: pytest tests/test_weather.py -v
"""
from __future__ import annotations

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
async def test_weather_happy_path_returns_raw_data() -> None:
    """run() returns a plain-text data block; no internal LLM call."""
    from pi.tools.weather import WeatherTool

    tool = WeatherTool()
    assert tool.needs_narration is True

    mock_cfg = MagicMock()
    mock_cfg.weather.api_key = "real-key"
    mock_cfg.weather.location = "Chicago, IL"
    mock_cfg.weather.units = "imperial"

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(side_effect=[_FAKE_CURRENT, _FAKE_FORECAST])

    mock_http_client = AsyncMock()
    mock_http_client.get = AsyncMock(return_value=mock_resp)
    mock_http_ctx = MagicMock()
    mock_http_ctx.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_ctx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("pi.tools.weather.cfg_module.load", return_value=mock_cfg),
        patch("pi.tools.weather.httpx.AsyncClient", return_value=mock_http_ctx),
    ):
        result = await tool.run({"query": "what's the weather today?"}, user="owner")

    # Result should be raw data containing temperature and conditions — not narrated
    assert "72" in result or "clear" in result.lower()
    assert "User question:" in result
