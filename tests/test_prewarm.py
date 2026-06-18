"""Smoke tests for pi/scheduler/prewarm.py.

Covers:
  - _minutes_until_prewarm: always positive, at most one week
  - PrewarmScheduler.start: no-op on default/missing schedule, schedules callbacks with data
  - PrewarmScheduler.cancel: cancels all handles and clears list
  - PrewarmScheduler._do_prewarm: calls _ensure_loaded on both, survives errors

Run with: pytest tests/test_prewarm.py -v
"""
from __future__ import annotations

import asyncio
import calendar
import json
import unittest.mock
from pathlib import Path

import pytest

from pi.memory.db import init_db
from pi.scheduler.prewarm import PrewarmScheduler, _TOP_N, _WEEK_MINUTES, _minutes_until_prewarm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def utc_ts(year: int, month: int, day: int, hour: int = 12, minute: int = 0) -> float:
    return float(calendar.timegm((year, month, day, hour, minute, 0, 0, 0, 0)))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn():
    c = init_db(":memory:")
    yield c
    c.close()


@pytest.fixture()
def conn_with_data():
    """DB with activations across 14 days, clustered at Mon 9am and Tue 18pm."""
    c = init_db(":memory:")
    for d in range(14):
        ts = utc_ts(2024, 1, d + 1, hour=12)
        c.execute("INSERT INTO activations (speaker, timestamp) VALUES ('owner', ?)", (ts,))
    # Add extra activations to create distinguishable high-usage slots
    for _ in range(5):
        c.execute(
            "INSERT INTO activations (speaker, timestamp) VALUES ('owner', ?)",
            (utc_ts(2024, 1, 1, hour=9),),  # Monday 9am
        )
    for _ in range(3):
        c.execute(
            "INSERT INTO activations (speaker, timestamp) VALUES ('owner', ?)",
            (utc_ts(2024, 1, 2, hour=18),),  # Tuesday 18pm
        )
    c.commit()
    yield c
    c.close()


@pytest.fixture()
def mock_llm():
    llm = unittest.mock.MagicMock()
    llm._ensure_loaded = unittest.mock.Mock()
    return llm


@pytest.fixture()
def mock_stt():
    stt = unittest.mock.MagicMock()
    stt._ensure_loaded = unittest.mock.Mock()
    return stt


@pytest.fixture()
def mock_loop():
    loop = unittest.mock.MagicMock(spec=asyncio.AbstractEventLoop)
    loop.call_later.side_effect = lambda *args, **kwargs: unittest.mock.MagicMock()
    return loop


# ---------------------------------------------------------------------------
# _minutes_until_prewarm
# ---------------------------------------------------------------------------


def test_minutes_until_prewarm_always_positive():
    for day in range(7):
        for hour in range(24):
            assert _minutes_until_prewarm(day, hour) > 0


def test_minutes_until_prewarm_at_most_one_week():
    for day in range(7):
        for hour in range(24):
            assert _minutes_until_prewarm(day, hour) <= _WEEK_MINUTES


def test_minutes_until_prewarm_hour_zero_wraps():
    # hour=0 means prewarm at day-1 at 23:55 — must still be positive
    result = _minutes_until_prewarm(0, 0)
    assert result > 0


# ---------------------------------------------------------------------------
# start — no-op cases
# ---------------------------------------------------------------------------


def test_start_noop_when_schedule_file_missing(conn, mock_llm, mock_stt, mock_loop, tmp_path):
    scheduler = PrewarmScheduler(mock_llm, mock_stt, tmp_path / "schedule.json", conn)
    scheduler.start(mock_loop)
    mock_loop.call_later.assert_not_called()


def test_start_noop_when_default_true(conn, mock_llm, mock_stt, mock_loop, tmp_path):
    path = tmp_path / "schedule.json"
    path.write_text(json.dumps({"default": True, "hour": 3, "minute": 0}))
    scheduler = PrewarmScheduler(mock_llm, mock_stt, path, conn)
    scheduler.start(mock_loop)
    mock_loop.call_later.assert_not_called()


def test_start_noop_when_empty_db_even_if_schedule_has_windows(mock_llm, mock_stt, mock_loop, tmp_path):
    c = init_db(":memory:")
    path = tmp_path / "schedule.json"
    path.write_text(json.dumps({"windows": [{"day_of_week": i, "hour": 3, "count": 0} for i in range(7)]}))
    scheduler = PrewarmScheduler(mock_llm, mock_stt, path, c)
    scheduler.start(mock_loop)
    mock_loop.call_later.assert_not_called()
    c.close()


def test_start_noop_handles_corrupted_json(conn, mock_llm, mock_stt, mock_loop, tmp_path):
    path = tmp_path / "schedule.json"
    path.write_text("not valid json {{{")
    scheduler = PrewarmScheduler(mock_llm, mock_stt, path, conn)
    scheduler.start(mock_loop)
    mock_loop.call_later.assert_not_called()


# ---------------------------------------------------------------------------
# start — active cases
# ---------------------------------------------------------------------------


def test_start_schedules_callbacks_when_data_present(conn_with_data, mock_llm, mock_stt, mock_loop, tmp_path):
    path = tmp_path / "schedule.json"
    path.write_text(json.dumps({"windows": []}))
    scheduler = PrewarmScheduler(mock_llm, mock_stt, path, conn_with_data)
    scheduler.start(mock_loop)
    assert mock_loop.call_later.call_count > 0


def test_start_schedules_at_most_top_n_callbacks(conn_with_data, mock_llm, mock_stt, mock_loop, tmp_path):
    path = tmp_path / "schedule.json"
    path.write_text(json.dumps({"windows": []}))
    scheduler = PrewarmScheduler(mock_llm, mock_stt, path, conn_with_data)
    scheduler.start(mock_loop)
    assert mock_loop.call_later.call_count <= _TOP_N


def test_start_all_delays_are_positive(conn_with_data, mock_llm, mock_stt, mock_loop, tmp_path):
    path = tmp_path / "schedule.json"
    path.write_text(json.dumps({"windows": []}))
    scheduler = PrewarmScheduler(mock_llm, mock_stt, path, conn_with_data)
    scheduler.start(mock_loop)
    for call_args in mock_loop.call_later.call_args_list:
        delay = call_args[0][0]
        assert delay > 0


def test_start_stores_handles(conn_with_data, mock_llm, mock_stt, mock_loop, tmp_path):
    path = tmp_path / "schedule.json"
    path.write_text(json.dumps({"windows": []}))
    scheduler = PrewarmScheduler(mock_llm, mock_stt, path, conn_with_data)
    scheduler.start(mock_loop)
    assert len(scheduler._handles) == mock_loop.call_later.call_count


# ---------------------------------------------------------------------------
# cancel
# ---------------------------------------------------------------------------


def test_cancel_clears_handles(conn_with_data, mock_llm, mock_stt, mock_loop, tmp_path):
    path = tmp_path / "schedule.json"
    path.write_text(json.dumps({"windows": []}))
    scheduler = PrewarmScheduler(mock_llm, mock_stt, path, conn_with_data)
    scheduler.start(mock_loop)
    assert scheduler._handles  # has entries after start
    scheduler.cancel()
    assert scheduler._handles == []


def test_cancel_calls_cancel_on_each_handle(conn_with_data, mock_llm, mock_stt, mock_loop, tmp_path):
    path = tmp_path / "schedule.json"
    path.write_text(json.dumps({"windows": []}))
    scheduler = PrewarmScheduler(mock_llm, mock_stt, path, conn_with_data)
    scheduler.start(mock_loop)
    handles = list(scheduler._handles)
    scheduler.cancel()
    for h in handles:
        h.cancel.assert_called_once()


def test_cancel_noop_when_no_handles(conn, mock_llm, mock_stt, mock_loop, tmp_path):
    scheduler = PrewarmScheduler(mock_llm, mock_stt, tmp_path / "s.json", conn)
    scheduler.cancel()  # must not raise
    assert scheduler._handles == []


# ---------------------------------------------------------------------------
# _do_prewarm
# ---------------------------------------------------------------------------


def test_do_prewarm_calls_ensure_loaded_on_llm_and_stt(conn, mock_llm, mock_stt, tmp_path):
    scheduler = PrewarmScheduler(mock_llm, mock_stt, tmp_path / "s.json", conn)
    scheduler._do_prewarm()
    mock_llm._ensure_loaded.assert_called_once()
    mock_stt._ensure_loaded.assert_called_once()


def test_do_prewarm_continues_to_stt_when_llm_raises(conn, mock_stt, tmp_path):
    mock_llm = unittest.mock.MagicMock()
    mock_llm._ensure_loaded.side_effect = RuntimeError("hailo unavailable")
    scheduler = PrewarmScheduler(mock_llm, mock_stt, tmp_path / "s.json", conn)
    scheduler._do_prewarm()  # must not raise
    mock_stt._ensure_loaded.assert_called_once()


def test_do_prewarm_does_not_raise_when_stt_fails(conn, mock_llm, tmp_path):
    mock_stt = unittest.mock.MagicMock()
    mock_stt._ensure_loaded.side_effect = RuntimeError("stt failure")
    scheduler = PrewarmScheduler(mock_llm, mock_stt, tmp_path / "s.json", conn)
    scheduler._do_prewarm()  # must not raise
    mock_llm._ensure_loaded.assert_called_once()
