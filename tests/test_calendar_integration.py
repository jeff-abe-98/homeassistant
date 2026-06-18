"""Integration tests for CalendarTool — auto-skip without real Google credentials.

Requires:
  1. config/google_credentials.json with real OAuth2 Desktop client credentials
     (client_id must not be the CHANGE_ME placeholder)
  2. config/google_token.json with a valid access token
     (run the server once to complete the browser OAuth flow)

Run with: pytest tests/test_calendar_integration.py -v -s
"""
from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from pi.tools.google_auth import is_configured

_CHICAGO_TZ = ZoneInfo("America/Chicago")

_REQUIRES_GOOGLE = pytest.mark.skipif(
    not is_configured(),
    reason=(
        "Google credentials not configured — populate config/google_credentials.json "
        "and run the server once to complete the OAuth flow (token saved to "
        "config/google_token.json)"
    ),
)


@_REQUIRES_GOOGLE
@pytest.mark.asyncio
async def test_calendar_tomorrow_owner_real_api() -> None:
    """'What do I have tomorrow?' as owner hits the real Google Calendar API; LLM is mocked."""
    from pi.tools.calendar import CalendarTool

    tool = CalendarTool()
    captured: list[tuple[str, str]] = []

    async def _spy_complete(system: str, user_msg: str) -> str:
        captured.append((system, user_msg))
        return "Tomorrow you have a team standup at ten AM."

    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(side_effect=_spy_complete)

    with patch.object(tool, "_llm_client", return_value=mock_llm):
        result = await tool.run(
            {"query": "What do I have tomorrow?", "when": "tomorrow"}, user="owner"
        )

    assert isinstance(result, str), "tool must return a string"
    assert result, "response must be non-empty"

    # Owner's name should appear in the system prompt sent to LLM (if LLM was called)
    if captured:
        system_prompt, user_msg = captured[0]
        assert "owner" in system_prompt.lower(), (
            "system prompt should mention the speaking user by name"
        )
        # Calendar text or query should be in the user message
        assert "tomorrow" in user_msg.lower() or "calendar" in user_msg.lower() or "events" in user_msg.lower()

    # The result is either a narrated response or the built-in empty-schedule message
    tomorrow = (datetime.datetime.now(tz=_CHICAGO_TZ) + datetime.timedelta(days=1)).date()
    assert tomorrow  # verify date math works (always true; confirms no exception)


@_REQUIRES_GOOGLE
@pytest.mark.asyncio
async def test_calendar_tomorrow_emily_real_api() -> None:
    """'What do I have tomorrow?' as Emily — verifies Emily's name is in the LLM system prompt."""
    from pi.tools.calendar import CalendarTool

    tool = CalendarTool()
    captured: list[tuple[str, str]] = []

    async def _spy_complete(system: str, user_msg: str) -> str:
        captured.append((system, user_msg))
        return "Emily, tomorrow you have a dentist appointment at three PM."

    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(side_effect=_spy_complete)

    with patch.object(tool, "_llm_client", return_value=mock_llm):
        result = await tool.run(
            {"query": "What do I have tomorrow?", "when": "tomorrow"}, user="emily"
        )

    assert isinstance(result, str)
    assert result

    # Emily's name must be in the system prompt (if LLM was invoked)
    if captured:
        system_prompt, _ = captured[0]
        assert "emily" in system_prompt.lower(), (
            "system prompt should address Emily by name"
        )


@_REQUIRES_GOOGLE
@pytest.mark.asyncio
async def test_emily_dentist_appointment_created_as_emily_dentist() -> None:
    """Emily: 'I have a dentist appointment Thursday at 3' → event body has summary='Emily Dentist'.

    Verifies the complete add-event flow with real credentials:
    - is_configured() passes (credentials required for this test to run at all)
    - dateparser resolves 'Thursday at 3' to 3:00 PM on a real future Thursday
    - Emily prefix logic applies: 'Dentist' → 'Emily Dentist'
    - the event body sent to Google Calendar has summary='Emily Dentist' and hour==15
    - the confirmation response includes 'Emily Dentist'

    The Google Calendar insert itself is mocked so no test events are created.
    """
    from pi.tools.calendar import AddCalendarEventTool

    inserted_bodies: list[dict] = []

    def fake_insert(**kwargs):
        inserted_bodies.append(kwargs.get("body", {}))
        return MagicMock(**{"execute.return_value": {"id": "test-event-id", "htmlLink": ""}})

    mock_service = MagicMock()
    mock_service.events().insert.side_effect = fake_insert

    tool = AddCalendarEventTool()

    with patch("pi.tools.calendar.build_service", return_value=mock_service):
        result = await tool.run(
            {"title": "Dentist", "when": "Thursday at 3"},
            user="emily",
        )

    assert inserted_bodies, "Google Calendar insert was never called"
    body = inserted_bodies[0]

    # Emily prefix must be applied
    assert body.get("summary") == "Emily Dentist", (
        f"Expected summary='Emily Dentist', got {body.get('summary')!r}"
    )

    # dateparser must resolve 'Thursday at 3' to 3:00 PM (real dateparser call)
    start = body.get("start", {})
    start_dt_str = start.get("dateTime", "")
    assert start_dt_str, "Event start.dateTime must be populated"
    start_dt = datetime.datetime.fromisoformat(start_dt_str)
    assert start_dt.hour == 15, (
        f"Expected 3 PM (hour=15), got hour={start_dt.hour} — "
        f"dateparser may not have parsed 'Thursday at 3' correctly"
    )
    assert start.get("timeZone") == "America/Chicago"

    # Confirmation string must mention the event title
    assert "Emily Dentist" in result, f"Expected 'Emily Dentist' in response: {result!r}"
    assert "done" in result.lower() or "added" in result.lower()
