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


class AddCalendarEventTool(BaseTool):
    name = "add_calendar_event"
    description = (
        "Add a new event to the user's Google Calendar. Use for requests like "
        "'add a dentist appointment Thursday at 3', 'schedule lunch tomorrow at noon', "
        "'put a meeting on my calendar Monday at 10am', 'I have a dentist Thursday at 3'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "The event title.",
            },
            "when": {
                "type": "string",
                "description": (
                    "Natural language date/time, e.g. 'Thursday at 3pm', "
                    "'tomorrow at noon', 'next Monday at 10am'."
                ),
            },
            "duration_minutes": {
                "type": "integer",
                "description": "Event duration in minutes (default 60).",
            },
        },
        "required": ["title", "when"],
    }

    async def run(self, params: dict, user: str) -> str:
        if not is_configured():
            return (
                "Google Calendar isn't set up yet — I need OAuth2 credentials. "
                "Check config/google_credentials.json for setup instructions."
            )

        service = build_service("calendar", "v3")
        if service is None:
            return "I couldn't connect to Google Calendar right now."

        title = params.get("title", "").strip()
        when_str = params.get("when", "").strip()
        duration = int(params.get("duration_minutes", 60))

        if not title:
            return "I need an event title to add it to your calendar."

        start_dt = _parse_natural_date(when_str)
        if start_dt is None:
            return (
                f"I couldn't understand '{when_str}' as a date. "
                "Try something like 'Thursday at 3pm' or 'tomorrow at noon'."
            )

        end_dt = start_dt + datetime.timedelta(minutes=duration)

        event_body = {
            "summary": title,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "America/Chicago"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "America/Chicago"},
        }

        try:
            created = (
                service.events().insert(calendarId="primary", body=event_body).execute()
            )
        except Exception as exc:
            return f"I had trouble adding that to your calendar: {exc}"

        _ = created  # htmlLink available but not needed for voice response
        when_label = start_dt.strftime("%-I:%M %p on %A, %B %-d")
        return f"Done — I've added '{title}' at {when_label} to your calendar."


def _parse_natural_date(when_str: str) -> datetime.datetime | None:
    """Parse a natural language date/time string into a tz-aware datetime."""
    try:
        import dateparser  # optional; graceful degradation if not installed
    except ImportError:
        return None

    return dateparser.parse(
        when_str,
        settings={
            "PREFER_DATES_FROM": "future",
            "TIMEZONE": "America/Chicago",
            "RETURN_AS_TIMEZONE_AWARE": True,
        },
    )


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
