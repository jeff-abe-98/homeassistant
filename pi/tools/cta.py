"""CTA Train Tracker tool — Blue Line arrivals at Western & Milwaukee."""

from __future__ import annotations

import json
from datetime import datetime

import httpx

import shared.config as cfg_module
from pi.llm.hailo_client import HailoLLMClient
from pi.tools.base import BaseTool

_CTA_ARRIVALS_URL = "https://lapi.transitchicago.com/api/1.0/ttarrivals.aspx"


class CtaTool(BaseTool):
    name = "cta_arrivals"
    description = (
        "Get upcoming CTA Blue Line train arrival times at Western & Milwaukee. "
        "Use for any question about the Blue Line train, 'L', or CTA arrivals. "
        "Handles direction: toward O'Hare (northwest) or toward Forest Park (southeast)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "The user's question verbatim, e.g. "
                    "'when is the next Blue Line', 'next train toward O'Hare'"
                ),
            },
            "direction": {
                "type": "string",
                "enum": ["ohare", "forest_park", "both"],
                "description": (
                    "Train direction: 'ohare' for O'Hare-bound, "
                    "'forest_park' for Forest Park-bound, "
                    "'both' if unspecified (default: 'both')"
                ),
            },
        },
        "required": ["query"],
    }

    def __init__(self) -> None:
        self._llm: HailoLLMClient | None = None

    def _llm_client(self) -> HailoLLMClient:
        if self._llm is None:
            cfg = cfg_module.load()
            self._llm = HailoLLMClient(cfg.hailo)
        return self._llm

    async def run(self, params: dict, user: str) -> str:
        cfg = cfg_module.load()
        api_key = cfg.cta.api_key

        if not api_key or api_key == "CHANGE_ME":
            return "CTA isn't set up yet — I need a CTA Train Tracker API key."

        direction = params.get("direction", "both")
        if direction == "ohare":
            stop_ids = [cfg.cta.stop_id_ohare]
        elif direction == "forest_park":
            stop_ids = [cfg.cta.stop_id_forest_park]
        else:
            stop_ids = [cfg.cta.stop_id_ohare, cfg.cta.stop_id_forest_park]

        stpid = ",".join(str(s) for s in stop_ids)

        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                _CTA_ARRIVALS_URL,
                params={"key": api_key, "stpid": stpid, "outputType": "JSON"},
            )
            r.raise_for_status()
            data = r.json()

        arrivals = _parse_arrivals(data)

        if direction == "ohare":
            direction_note = "The user asked specifically about trains toward O'Hare. Focus only on O'Hare-bound arrivals."
        elif direction == "forest_park":
            direction_note = "The user asked specifically about trains toward Forest Park. Focus only on Forest Park-bound arrivals."
        else:
            direction_note = "The user did not specify a direction. Group arrivals by direction (O'Hare and Forest Park)."

        system = (
            "You are a home assistant. Narrate the following CTA Blue Line arrival data naturally "
            "in plain spoken English. Be concise — one or two sentences. "
            "State arrival times relative to now (e.g. 'in 3 minutes', 'in 8 minutes'). "
            f"{direction_note} No markdown, no bullet points."
        )
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_msg = (
            f"Question: {params.get('query', 'next Blue Line train')}\n"
            f"Current time: {now_str}\n\n"
            f"Arrival data:\n{json.dumps(arrivals, indent=2)}"
        )
        return await self._llm_client().complete(system, user_msg)


def _parse_arrivals(data: dict) -> list[dict]:
    """Extract relevant fields from CTA API response."""
    try:
        etas = data.get("ctatt", {}).get("eta", []) or []
    except (AttributeError, TypeError):
        return []

    results = []
    for eta in etas:
        results.append(
            {
                "destination": eta.get("destNm", ""),
                "stop_description": eta.get("stpDe", ""),
                "arrival_time": eta.get("arrT", ""),
                "predicted_at": eta.get("prdt", ""),
                "is_approaching": eta.get("isApp", "0") == "1",
                "is_delayed": eta.get("isDly", "0") == "1",
                "is_scheduled": eta.get("isSch", "0") == "1",
            }
        )
    return results
