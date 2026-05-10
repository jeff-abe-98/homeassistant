"""Smoke tests for server/tools/calendar.py."""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from server.tools.calendar import (
    AddCalendarEventTool,
    CalendarTool,
    _format_events,
    _parse_natural_date,
    _time_window,
)

_CHICAGO_TZ = ZoneInfo("America/Chicago")


class TestTimeWindow:
    def test_today_start_is_now_and_end_is_same_day(self):
        time_min, time_max = _time_window("today")
        start = datetime.datetime.fromisoformat(time_min)
        end = datetime.datetime.fromisoformat(time_max)
        assert end > start
        assert start.date() == end.date()

    def test_tomorrow_spans_exactly_one_day(self):
        time_min, time_max = _time_window("tomorrow")
        start = datetime.datetime.fromisoformat(time_min)
        end = datetime.datetime.fromisoformat(time_max)
        tomorrow = (datetime.datetime.now(tz=_CHICAGO_TZ) + datetime.timedelta(days=1)).date()
        assert start.date() == tomorrow
        assert (end - start).total_seconds() == 24 * 3600

    def test_this_week_spans_seven_days(self):
        time_min, time_max = _time_window("this_week")
        start = datetime.datetime.fromisoformat(time_min)
        end = datetime.datetime.fromisoformat(time_max)
        diff = end - start
        assert abs(diff.total_seconds() - 7 * 24 * 3600) < 2

    def test_unknown_when_defaults_to_today(self):
        time_min, time_max = _time_window("bogus")
        start = datetime.datetime.fromisoformat(time_min)
        end = datetime.datetime.fromisoformat(time_max)
        assert start.date() == end.date()


class TestFormatEvents:
    def test_timed_event_shows_time(self):
        events = [{"summary": "Doctor", "start": {"dateTime": "2026-05-10T09:30:00-05:00"}}]
        result = _format_events(events)
        assert "Doctor" in result
        assert "9:30 AM" in result

    def test_all_day_event_shows_all_day(self):
        events = [{"summary": "Birthday", "start": {"date": "2026-05-10"}}]
        result = _format_events(events)
        assert "Birthday" in result
        assert "all day" in result

    def test_no_title_falls_back_to_placeholder(self):
        events = [{"start": {"date": "2026-05-10"}}]
        result = _format_events(events)
        assert "(no title)" in result

    def test_multiple_events_preserve_order(self):
        events = [
            {"summary": "First", "start": {"dateTime": "2026-05-10T08:00:00-05:00"}},
            {"summary": "Second", "start": {"dateTime": "2026-05-10T14:00:00-05:00"}},
        ]
        result = _format_events(events)
        assert result.index("First") < result.index("Second")


class TestCalendarToolRun:
    @pytest.mark.asyncio
    async def test_not_configured_returns_setup_message(self):
        tool = CalendarTool()
        with patch("server.tools.calendar.is_configured", return_value=False):
            result = await tool.run({"query": "what's today", "when": "today"}, "owner")
        assert "set up" in result.lower() or "credentials" in result.lower()

    @pytest.mark.asyncio
    async def test_service_none_returns_connection_error(self):
        tool = CalendarTool()
        with (
            patch("server.tools.calendar.is_configured", return_value=True),
            patch("server.tools.calendar.build_service", return_value=None),
        ):
            result = await tool.run({"query": "what's today", "when": "today"}, "owner")
        assert "couldn't connect" in result.lower()

    @pytest.mark.asyncio
    async def test_no_events_returns_empty_schedule_message(self):
        mock_service = MagicMock()
        mock_service.events().list().execute.return_value = {"items": []}
        tool = CalendarTool()
        with (
            patch("server.tools.calendar.is_configured", return_value=True),
            patch("server.tools.calendar.build_service", return_value=mock_service),
        ):
            result = await tool.run({"query": "what's today", "when": "today"}, "owner")
        assert "don't have anything" in result.lower()

    @pytest.mark.asyncio
    async def test_events_narrated_via_llm(self):
        events = [{"summary": "Team standup", "start": {"dateTime": "2026-05-10T09:00:00-05:00"}}]
        mock_service = MagicMock()
        mock_service.events().list().execute.return_value = {"items": events}
        tool = CalendarTool()
        mock_llm_response = "You have a Team standup at nine AM."
        with (
            patch("server.tools.calendar.is_configured", return_value=True),
            patch("server.tools.calendar.build_service", return_value=mock_service),
            patch.object(tool, "_llm_client") as mock_client_fn,
        ):
            mock_client_fn.return_value.complete = AsyncMock(return_value=mock_llm_response)
            result = await tool.run({"query": "what do I have today", "when": "today"}, "owner")
        assert result == mock_llm_response

    @pytest.mark.asyncio
    async def test_api_exception_returns_friendly_message(self):
        mock_service = MagicMock()
        mock_service.events().list().execute.side_effect = Exception("network failure")
        tool = CalendarTool()
        with (
            patch("server.tools.calendar.is_configured", return_value=True),
            patch("server.tools.calendar.build_service", return_value=mock_service),
        ):
            result = await tool.run({"query": "what's today", "when": "today"}, "owner")
        assert "trouble" in result.lower()

    @pytest.mark.asyncio
    async def test_tomorrow_query_uses_correct_window(self):
        """Verify the service is called with a time_min that falls on tomorrow."""
        captured: dict = {}

        def fake_list(**kwargs):
            captured.update(kwargs)
            return MagicMock(**{"execute.return_value": {"items": []}})

        mock_service = MagicMock()
        mock_service.events().list.side_effect = fake_list
        tool = CalendarTool()
        with (
            patch("server.tools.calendar.is_configured", return_value=True),
            patch("server.tools.calendar.build_service", return_value=mock_service),
        ):
            await tool.run({"query": "what's tomorrow", "when": "tomorrow"}, "owner")

        tomorrow = (datetime.datetime.now(tz=_CHICAGO_TZ) + datetime.timedelta(days=1)).date()
        start = datetime.datetime.fromisoformat(captured["timeMin"])
        assert start.date() == tomorrow


class TestParseNaturalDate:
    def test_returns_datetime_when_dateparser_available(self):
        fixed_dt = datetime.datetime(2026, 5, 14, 15, 0, tzinfo=_CHICAGO_TZ)
        with patch.dict("sys.modules", {"dateparser": MagicMock(parse=MagicMock(return_value=fixed_dt))}):
            result = _parse_natural_date("Thursday at 3pm")
        assert result == fixed_dt

    def test_returns_none_when_dateparser_unavailable(self):
        with patch.dict("sys.modules", {"dateparser": None}):
            result = _parse_natural_date("tomorrow at noon")
        assert result is None

    def test_returns_none_when_dateparser_returns_none(self):
        mock_dp = MagicMock()
        mock_dp.parse.return_value = None
        with patch.dict("sys.modules", {"dateparser": mock_dp}):
            result = _parse_natural_date("this is not a date")
        assert result is None


class TestAddCalendarEventTool:
    @pytest.mark.asyncio
    async def test_not_configured_returns_setup_message(self):
        tool = AddCalendarEventTool()
        with patch("server.tools.calendar.is_configured", return_value=False):
            result = await tool.run({"title": "Dentist", "when": "Thursday at 3pm"}, "owner")
        assert "set up" in result.lower() or "credentials" in result.lower()

    @pytest.mark.asyncio
    async def test_service_none_returns_connection_error(self):
        tool = AddCalendarEventTool()
        with (
            patch("server.tools.calendar.is_configured", return_value=True),
            patch("server.tools.calendar.build_service", return_value=None),
        ):
            result = await tool.run({"title": "Dentist", "when": "Thursday at 3pm"}, "owner")
        assert "couldn't connect" in result.lower()

    @pytest.mark.asyncio
    async def test_missing_title_returns_error(self):
        tool = AddCalendarEventTool()
        with (
            patch("server.tools.calendar.is_configured", return_value=True),
            patch("server.tools.calendar.build_service", return_value=MagicMock()),
        ):
            result = await tool.run({"title": "", "when": "Thursday at 3pm"}, "owner")
        assert "title" in result.lower()

    @pytest.mark.asyncio
    async def test_unparseable_date_returns_friendly_error(self):
        tool = AddCalendarEventTool()
        with (
            patch("server.tools.calendar.is_configured", return_value=True),
            patch("server.tools.calendar.build_service", return_value=MagicMock()),
            patch("server.tools.calendar._parse_natural_date", return_value=None),
        ):
            result = await tool.run({"title": "Dentist", "when": "blorp"}, "owner")
        assert "couldn't understand" in result.lower()
        assert "blorp" in result

    @pytest.mark.asyncio
    async def test_event_created_returns_confirmation_with_title(self):
        fixed_dt = datetime.datetime(2026, 5, 14, 15, 0, tzinfo=_CHICAGO_TZ)
        mock_service = MagicMock()
        mock_service.events().insert().execute.return_value = {"htmlLink": "https://example.com"}
        tool = AddCalendarEventTool()
        with (
            patch("server.tools.calendar.is_configured", return_value=True),
            patch("server.tools.calendar.build_service", return_value=mock_service),
            patch("server.tools.calendar._parse_natural_date", return_value=fixed_dt),
        ):
            result = await tool.run({"title": "Dentist", "when": "Thursday at 3pm"}, "owner")
        assert "Dentist" in result
        assert "done" in result.lower() or "added" in result.lower()

    @pytest.mark.asyncio
    async def test_api_exception_returns_friendly_message(self):
        fixed_dt = datetime.datetime(2026, 5, 14, 15, 0, tzinfo=_CHICAGO_TZ)
        mock_service = MagicMock()
        mock_service.events().insert().execute.side_effect = Exception("network error")
        tool = AddCalendarEventTool()
        with (
            patch("server.tools.calendar.is_configured", return_value=True),
            patch("server.tools.calendar.build_service", return_value=mock_service),
            patch("server.tools.calendar._parse_natural_date", return_value=fixed_dt),
        ):
            result = await tool.run({"title": "Dentist", "when": "Thursday at 3pm"}, "owner")
        assert "trouble" in result.lower()

    @pytest.mark.asyncio
    async def test_emily_event_gets_emily_prefix(self):
        fixed_dt = datetime.datetime(2026, 5, 14, 15, 0, tzinfo=_CHICAGO_TZ)
        captured: dict = {}

        def fake_insert(**kwargs):
            captured.update(kwargs)
            return MagicMock(**{"execute.return_value": {"htmlLink": ""}})

        mock_service = MagicMock()
        mock_service.events().insert.side_effect = fake_insert
        tool = AddCalendarEventTool()
        with (
            patch("server.tools.calendar.is_configured", return_value=True),
            patch("server.tools.calendar.build_service", return_value=mock_service),
            patch("server.tools.calendar._parse_natural_date", return_value=fixed_dt),
        ):
            result = await tool.run({"title": "Dentist", "when": "Thursday at 3pm"}, "emily")

        body = captured.get("body", {})
        assert body.get("summary") == "Emily Dentist"
        assert "Emily Dentist" in result

    @pytest.mark.asyncio
    async def test_emily_event_already_prefixed_no_double_prefix(self):
        fixed_dt = datetime.datetime(2026, 5, 14, 15, 0, tzinfo=_CHICAGO_TZ)
        captured: dict = {}

        def fake_insert(**kwargs):
            captured.update(kwargs)
            return MagicMock(**{"execute.return_value": {"htmlLink": ""}})

        mock_service = MagicMock()
        mock_service.events().insert.side_effect = fake_insert
        tool = AddCalendarEventTool()
        with (
            patch("server.tools.calendar.is_configured", return_value=True),
            patch("server.tools.calendar.build_service", return_value=mock_service),
            patch("server.tools.calendar._parse_natural_date", return_value=fixed_dt),
        ):
            await tool.run({"title": "Emily Dentist", "when": "Thursday at 3pm"}, "emily")

        body = captured.get("body", {})
        assert body.get("summary") == "Emily Dentist"

    @pytest.mark.asyncio
    async def test_owner_event_not_prefixed(self):
        fixed_dt = datetime.datetime(2026, 5, 14, 15, 0, tzinfo=_CHICAGO_TZ)
        captured: dict = {}

        def fake_insert(**kwargs):
            captured.update(kwargs)
            return MagicMock(**{"execute.return_value": {"htmlLink": ""}})

        mock_service = MagicMock()
        mock_service.events().insert.side_effect = fake_insert
        tool = AddCalendarEventTool()
        with (
            patch("server.tools.calendar.is_configured", return_value=True),
            patch("server.tools.calendar.build_service", return_value=mock_service),
            patch("server.tools.calendar._parse_natural_date", return_value=fixed_dt),
        ):
            await tool.run({"title": "Dentist", "when": "Thursday at 3pm"}, "owner")

        body = captured.get("body", {})
        assert body.get("summary") == "Dentist"

    @pytest.mark.asyncio
    async def test_custom_duration_sets_correct_end_time(self):
        fixed_dt = datetime.datetime(2026, 5, 14, 14, 0, tzinfo=_CHICAGO_TZ)
        captured: dict = {}

        def fake_insert(**kwargs):
            captured.update(kwargs)
            return MagicMock(**{"execute.return_value": {"htmlLink": ""}})

        mock_service = MagicMock()
        mock_service.events().insert.side_effect = fake_insert
        tool = AddCalendarEventTool()
        with (
            patch("server.tools.calendar.is_configured", return_value=True),
            patch("server.tools.calendar.build_service", return_value=mock_service),
            patch("server.tools.calendar._parse_natural_date", return_value=fixed_dt),
        ):
            await tool.run({"title": "Meeting", "when": "2pm", "duration_minutes": 90}, "owner")

        body = captured.get("body", {})
        end_str = body.get("end", {}).get("dateTime", "")
        end_dt = datetime.datetime.fromisoformat(end_str)
        assert (end_dt - fixed_dt) == datetime.timedelta(minutes=90)
