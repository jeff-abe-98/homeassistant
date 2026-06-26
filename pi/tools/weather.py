"""Weather tool — fetches OpenWeatherMap data and returns raw facts for narration."""

from __future__ import annotations

import httpx

import shared.config as cfg_module
from pi.tools.base import BaseTool

_OWM_CURRENT = "https://api.openweathermap.org/data/2.5/weather"
_OWM_FORECAST = "https://api.openweathermap.org/data/2.5/forecast"


class WeatherTool(BaseTool):
    name = "get_weather"
    needs_narration = True  # run() returns raw data; caller must call router.narrate()
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

    async def run(self, params: dict, user: str) -> str:
        cfg = cfg_module.load()
        api_key = cfg.weather.api_key
        location = cfg.weather.location
        units = cfg.weather.units

        if not api_key or api_key == "CHANGE_ME":
            return "Weather isn't set up yet — I need an OpenWeatherMap API key."

        async with httpx.AsyncClient(timeout=10.0) as client:
            current_resp, forecast_resp = await _fetch_both(client, location, api_key, units)

        query = params.get("query", "current weather")
        return _summarize_weather(current_resp, forecast_resp, query, units)


def _summarize_weather(current: dict, forecast: dict, query: str, units: str = "imperial") -> str:
    """Condense OWM response into a plain-text data block for LLM narration."""
    unit_sym = "°F" if units == "imperial" else "°C"
    main = current.get("main", {})
    weather = current.get("weather", [{}])[0]
    wind = current.get("wind", {})
    name = current.get("name", "your location")

    lines = [
        f"Location: {name}",
        f"Temperature: {main.get('temp')}{unit_sym} (feels like {main.get('feels_like')}{unit_sym})",
        f"Conditions: {weather.get('description', '')}",
        f"Humidity: {main.get('humidity')}%",
        f"Wind: {wind.get('speed', 0)} mph",
    ]

    items = forecast.get("list", [])[:5]
    if items:
        lines.append("Upcoming forecast:")
        for item in items:
            dt_txt = item.get("dt_txt", "")[:13]  # "YYYY-MM-DD HH"
            temp = item.get("main", {}).get("temp", "?")
            desc = item.get("weather", [{}])[0].get("description", "")
            lines.append(f"  {dt_txt}: {temp}{unit_sym}, {desc}")

    lines.append(f"User question: {query}")
    return "\n".join(lines)


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
