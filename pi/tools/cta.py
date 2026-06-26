"""CTA Train Tracker tool — Blue Line arrivals at Western & Milwaukee."""

from __future__ import annotations

from datetime import datetime

import httpx

import shared.config as cfg_module
from pi.tools.base import BaseTool

_CTA_ARRIVALS_URL = "https://lapi.transitchicago.com/api/1.0/ttarrivals.aspx"

_DIRECTION_LABELS = {
    "ohare": "O'Hare-bound",
    "forest_park": "Forest Park-bound",
    "both": "both directions",
}


class CtaTool(BaseTool):
    name = "cta_arrivals"
    needs_narration = True  # run() returns raw data; caller must call router.narrate()
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
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        query = params.get("query", "next Blue Line train")
        direction_label = _DIRECTION_LABELS.get(direction, "both directions")

        lines = [
            f"Current time: {now_str}",
            f"Direction filter: {direction_label}",
            "CTA Blue Line arrivals at Western & Milwaukee:",
        ]
        for a in arrivals:
            delayed = " [DELAYED]" if a.get("is_delayed") else ""
            approaching = " [APPROACHING]" if a.get("is_approaching") else ""
            lines.append(
                f"  To {a['destination']}: arrives {a['arrival_time']}{approaching}{delayed}"
            )
        if not arrivals:
            lines.append("  No arrivals found.")
        lines.append(f"User question: {query}")
        return "\n".join(lines)


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
