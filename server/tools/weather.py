"""Weather tool — fetches OpenWeatherMap data and narrates via LLM."""

from __future__ import annotations

import json

import httpx

import shared.config as cfg_module
from server.llm.client import OllamaClient
from server.tools.base import BaseTool

_OWM_CURRENT = "https://api.openweathermap.org/data/2.5/weather"
_OWM_FORECAST = "https://api.openweathermap.org/data/2.5/forecast"


class WeatherTool(BaseTool):
    name = "get_weather"
    description = (
        "Get the current weather conditions or multi-day forecast for the user's location. "
        "Use for any question about weather, temperature, rain, wind, or forecast."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "The user's weather question verbatim, e.g. "
                    "'what's the weather today', 'will it rain tomorrow', 'how cold is it'"
                ),
            }
        },
        "required": ["query"],
    }

    def __init__(self) -> None:
        self._llm: OllamaClient | None = None

    def _llm_client(self) -> OllamaClient:
        if self._llm is None:
            cfg = cfg_module.load()
            self._llm = OllamaClient(cfg.ollama)
        return self._llm

    async def run(self, params: dict, user: str) -> str:
        cfg = cfg_module.load()
        api_key = cfg.weather.api_key
        location = cfg.weather.location
        units = cfg.weather.units

        if not api_key or api_key == "CHANGE_ME":
            return "Weather isn't set up yet — I need an OpenWeatherMap API key."

        async with httpx.AsyncClient(timeout=10.0) as client:
            current_resp, forecast_resp = await _fetch_both(client, location, api_key, units)

        payload = {
            "current": current_resp,
            "forecast": forecast_resp,
        }

        system = (
            "You are a home assistant. Narrate the following weather data naturally "
            "in plain spoken English. Be concise — two or three sentences. "
            "Answer the user's specific question if one is given. "
            "No markdown, no bullet points."
        )
        user_msg = (
            f"Question: {params.get('query', 'current weather')}\n\n"
            f"Weather data:\n{json.dumps(payload, indent=2)}"
        )
        return await self._llm_client().complete(system, user_msg)


async def _fetch_both(
    client: httpx.AsyncClient, location: str, api_key: str, units: str = "imperial"
) -> tuple[dict, dict]:
    import asyncio

    async def _get_current() -> dict:
        r = await client.get(_OWM_CURRENT, params={"q": location, "appid": api_key, "units": units})
        r.raise_for_status()
        return r.json()

    async def _get_forecast() -> dict:
        r = await client.get(_OWM_FORECAST, params={"q": location, "appid": api_key, "units": units, "cnt": 16})
        r.raise_for_status()
        return r.json()

    return await asyncio.gather(_get_current(), _get_forecast())
