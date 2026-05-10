"""Google Calendar tool — reads events for today or a date range."""

from __future__ import annotations

import datetime
from zoneinfo import ZoneInfo

import shared.config as cfg_module
from server.llm.client import OllamaClient
from server.tools.base import BaseTool
from server.tools.google_auth import build_service, is_configured

_CHICAGO_TZ = ZoneInfo("America/Chicago")


class CalendarTool(BaseTool):
    name = "get_calendar_events"
    description = (
        "Read the user's Google Calendar events. Use for questions like "
        "'what do I have today', 'what's on my schedule tomorrow', "
        "'do I have anything this week', or 'what's happening on Friday'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The user's calendar question verbatim.",
            },
            "when": {
                "type": "string",
                "enum": ["today", "tomorrow", "this_week"],
                "description": (
                    "Time window to query. 'today' = rest of today, "
                    "'tomorrow' = all of tomorrow, 'this_week' = next 7 days."
                ),
            },
        },
        "required": ["query", "when"],
    }

    def __init__(self) -> None:
        self._llm: OllamaClient | None = None

    def _llm_client(self) -> OllamaClient:
        if self._llm is None:
            cfg = cfg_module.load()
            self._llm = OllamaClient(cfg.ollama)
        return self._llm

    async def run(self, params: dict, user: str) -> str:
        if not is_configured():
            return (
                "Google Calendar isn't set up yet — I need OAuth2 credentials. "
                "Check config/google_credentials.json for setup instructions."
            )

        service = build_service("calendar", "v3")
        if service is None:
            return "I couldn't connect to Google Calendar right now."

        when = params.get("when", "today")
        time_min, time_max = _time_window(when)

        try:
            result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy="startTime",
                    maxResults=20,
                )
                .execute()
            )
        except Exception as exc:
            return f"I had trouble reading your calendar: {exc}"

        events = result.get("items", [])
        if not events:
            window_label = {"today": "today", "tomorrow": "tomorrow", "this_week": "this week"}.get(when, when)
            return f"You don't have anything scheduled {window_label}."

        events_text = _format_events(events)
        system = (
            "You are a home assistant. Read back the following calendar events naturally "
            "in plain spoken English. Be concise — two or three sentences. "
            "No markdown, no bullet points."
        )
        user_msg = (
            f"Question: {params.get('query', 'what do I have scheduled')}\n\n"
            f"Calendar events:\n{events_text}"
        )
        return await self._llm_client().complete(system, user_msg)


def _time_window(when: str) -> tuple[str, str]:
    """Return (time_min, time_max) as RFC3339 strings for the requested window."""
    now = datetime.datetime.now(tz=_CHICAGO_TZ)

    if when == "tomorrow":
        start = (now + datetime.timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end = start + datetime.timedelta(days=1)
    elif when == "this_week":
        start = now
        end = now + datetime.timedelta(days=7)
    else:  # today (default)
        start = now
        end = now.replace(hour=23, minute=59, second=59, microsecond=0)

    return start.isoformat(), end.isoformat()


def _format_events(events: list[dict]) -> str:
    """Convert raw Google Calendar event dicts into a readable text block."""
    lines: list[str] = []
    for ev in events:
        title = ev.get("summary", "(no title)")
        start = ev.get("start", {})
        # All-day events use "date"; timed events use "dateTime"
        when = start.get("dateTime") or start.get("date", "")
        if "T" in when:
            dt = datetime.datetime.fromisoformat(when)
            dt_local = dt.astimezone(_CHICAGO_TZ)
            when_str = dt_local.strftime("%-I:%M %p")
        else:
            when_str = "all day"
        lines.append(f"- {when_str}: {title}")
    return "\n".join(lines)
