"""Time tool — returns the current local time and date from the system clock."""
from __future__ import annotations

from datetime import datetime

from pi.tools.base import BaseTool


class TimeTool(BaseTool):
    name = "get_time"
    description = (
        "Get the current local time or date. "
        "Use for any question about what time it is, what day it is, or today's date."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The user's time or date question verbatim.",
            }
        },
        "required": ["query"],
    }

    async def run(self, params: dict, user: str) -> str:
        now = datetime.now()
        return now.strftime("It's %-I:%M %p on %A, %B %-d, %Y.")
