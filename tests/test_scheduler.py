"""Smoke tests for pi/scheduler/heatmap.py and pi/scheduler/schedule_writer.py.

Covers:
  - has_enough_data: False < 14 distinct days, True >= 14 days
  - build_heatmap: counts by (day_of_week, hour), SQLite→Python weekday conversion
  - find_low_usage_windows: 7 entries, lowest-count hour, earliest-hour tie-break
  - write_schedule: default JSON before data, windows JSON after data, unchanged skip

Run with: pytest tests/test_scheduler.py -v
"""
from __future__ import annotations

import calendar
import json
import unittest.mock

import pytest

from pi.memory.db import init_db
from pi.scheduler.heatmap import build_heatmap, find_low_usage_windows, has_enough_data
from pi.scheduler.schedule_writer import write_schedule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def utc_ts(year: int, month: int, day: int, hour: int = 12, minute: int = 0) -> float:
    """Return Unix timestamp for the given UTC datetime."""
    return float(calendar.timegm((year, month, day, hour, minute, 0, 0, 0, 0)))


def insert_activation(conn, ts: float, speaker: str = "owner") -> None:
    conn.execute("INSERT INTO activations (speaker, timestamp) VALUES (?, ?)", (speaker, ts))
    conn.commit()


# 2024-01-01 was a Monday; %w=1 in SQLite → Python weekday 0
# 2024-01-07 was a Sunday;  %w=0 in SQLite → Python weekday 6


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn():
    c = init_db(":memory:")
    yield c
    c.close()


@pytest.fixture()
def conn_14_days():
    """DB with activations on 14 distinct UTC calendar days (Mon Jan 1 – Sun Jan 14 2024)."""
    c = init_db(":memory:")
    for d in range(14):
        ts = utc_ts(2024, 1, d + 1, hour=12)
        c.execute("INSERT INTO activations (speaker, timestamp) VALUES ('owner', ?)", (ts,))
    c.commit()
    yield c
    c.close()


# ---------------------------------------------------------------------------
# has_enough_data
# ---------------------------------------------------------------------------


def test_has_enough_data_empty_returns_false(conn):
    assert has_enough_data(conn) is False


def test_has_enough_data_13_days_returns_false(conn):
    for d in range(13):
        insert_activation(conn, utc_ts(2024, 1, d + 1))
    assert has_enough_data(conn) is False


def test_has_enough_data_14_days_returns_true(conn_14_days):
    assert has_enough_data(conn_14_days) is True


def test_has_enough_data_many_same_day_is_still_one(conn):
    for _ in range(100):
        insert_activation(conn, utc_ts(2024, 1, 1, hour=9))
    assert has_enough_data(conn) is False


def test_has_enough_data_custom_min_days(conn):
    for d in range(3):
        insert_activation(conn, utc_ts(2024, 1, d + 1))
    assert has_enough_data(conn, min_days=3) is True
    assert has_enough_data(conn, min_days=4) is False


# ---------------------------------------------------------------------------
# build_heatmap
# ---------------------------------------------------------------------------


def test_build_heatmap_empty_db_returns_empty_dict(conn):
    assert build_heatmap(conn) == {}


def test_build_heatmap_counts_activations_by_hour(conn):
    for _ in range(3):
        insert_activation(conn, utc_ts(2024, 1, 1, hour=9))   # Monday 9am
    for _ in range(2):
        insert_activation(conn, utc_ts(2024, 1, 1, hour=10))  # Monday 10am
    heatmap = build_heatmap(conn)
    assert heatmap[(0, 9)] == 3
    assert heatmap[(0, 10)] == 2


def test_build_heatmap_aggregates_same_dow_across_weeks(conn):
    insert_activation(conn, utc_ts(2024, 1, 1, hour=9))   # Mon Jan 1
    insert_activation(conn, utc_ts(2024, 1, 8, hour=9))   # Mon Jan 8
    heatmap = build_heatmap(conn)
    assert heatmap[(0, 9)] == 2


def test_build_heatmap_distinct_days_of_week(conn):
    insert_activation(conn, utc_ts(2024, 1, 1, hour=9))  # Monday  → dow 0
    insert_activation(conn, utc_ts(2024, 1, 2, hour=9))  # Tuesday → dow 1
    insert_activation(conn, utc_ts(2024, 1, 3, hour=9))  # Wednesday → dow 2
    heatmap = build_heatmap(conn)
    assert heatmap.get((0, 9)) == 1
    assert heatmap.get((1, 9)) == 1
    assert heatmap.get((2, 9)) == 1


def test_build_heatmap_sunday_maps_to_python_weekday_6(conn):
    # 2024-01-07 is Sunday: SQLite %w=0 → Python weekday 6
    insert_activation(conn, utc_ts(2024, 1, 7, hour=14))
    heatmap = build_heatmap(conn)
    assert heatmap.get((6, 14)) == 1


def test_build_heatmap_only_nonempty_slots_returned(conn):
    insert_activation(conn, utc_ts(2024, 1, 1, hour=6))
    heatmap = build_heatmap(conn)
    assert len(heatmap) == 1


# ---------------------------------------------------------------------------
# find_low_usage_windows
# ---------------------------------------------------------------------------


def test_find_low_usage_windows_always_7_entries_empty():
    assert len(find_low_usage_windows({})) == 7


def test_find_low_usage_windows_always_7_entries_populated(conn_14_days):
    heatmap = build_heatmap(conn_14_days)
    assert len(find_low_usage_windows(heatmap)) == 7


def test_find_low_usage_windows_all_days_0_to_6():
    windows = find_low_usage_windows({})
    assert {w["day_of_week"] for w in windows} == set(range(7))


def test_find_low_usage_windows_sorted_by_day():
    windows = find_low_usage_windows({})
    days = [w["day_of_week"] for w in windows]
    assert days == sorted(days)


def test_find_low_usage_windows_picks_lowest_count_hour():
    # All Monday hours filled at 10, except hour 7 which is 1
    heatmap = {(0, h): 10 for h in range(24)}
    heatmap[(0, 7)] = 1
    windows = find_low_usage_windows(heatmap)
    mon = next(w for w in windows if w["day_of_week"] == 0)
    assert mon["hour"] == 7
    assert mon["count"] == 1


def test_find_low_usage_windows_tie_break_earliest_hour():
    # Monday: hours 3 and 5 tied at count 1; all others at 10
    heatmap = {(0, h): 10 for h in range(24)}
    heatmap[(0, 3)] = 1
    heatmap[(0, 5)] = 1
    windows = find_low_usage_windows(heatmap)
    mon = next(w for w in windows if w["day_of_week"] == 0)
    assert mon["hour"] == 3


def test_find_low_usage_windows_unobserved_hours_default_zero():
    # Empty heatmap → all hours are 0 → earliest hour (0) wins for every day
    windows = find_low_usage_windows({})
    for w in windows:
        assert w["hour"] == 0
        assert w["count"] == 0


def test_find_low_usage_windows_window_dict_keys():
    windows = find_low_usage_windows({})
    for w in windows:
        assert set(w.keys()) == {"day_of_week", "hour", "count"}


# ---------------------------------------------------------------------------
# write_schedule — default schedule before enough data
# ---------------------------------------------------------------------------


def test_write_schedule_default_json_before_data(conn, tmp_path):
    schedule_path = tmp_path / "schedule.json"
    with unittest.mock.patch("pi.scheduler.schedule_writer.subprocess.run"):
        write_schedule(conn, schedule_path=schedule_path, repo_root=tmp_path)
    data = json.loads(schedule_path.read_text())
    assert data == {"default": True, "hour": 3, "minute": 0}


def test_write_schedule_default_is_valid_json(conn, tmp_path):
    schedule_path = tmp_path / "schedule.json"
    with unittest.mock.patch("pi.scheduler.schedule_writer.subprocess.run"):
        write_schedule(conn, schedule_path=schedule_path, repo_root=tmp_path)
    json.loads(schedule_path.read_text())  # must not raise


def test_write_schedule_windows_json_after_14_days(conn_14_days, tmp_path):
    schedule_path = tmp_path / "schedule.json"
    with unittest.mock.patch("pi.scheduler.schedule_writer.subprocess.run"):
        write_schedule(conn_14_days, schedule_path=schedule_path, repo_root=tmp_path)
    data = json.loads(schedule_path.read_text())
    assert "windows" in data
    assert "default" not in data
    assert len(data["windows"]) == 7


def test_write_schedule_windows_format_valid(conn_14_days, tmp_path):
    schedule_path = tmp_path / "schedule.json"
    with unittest.mock.patch("pi.scheduler.schedule_writer.subprocess.run"):
        write_schedule(conn_14_days, schedule_path=schedule_path, repo_root=tmp_path)
    data = json.loads(schedule_path.read_text())
    for w in data["windows"]:
        assert set(w.keys()) == {"day_of_week", "hour", "count"}
        assert 0 <= w["day_of_week"] <= 6
        assert 0 <= w["hour"] <= 23
        assert w["count"] >= 0


def test_write_schedule_returns_true_on_first_write(conn, tmp_path):
    schedule_path = tmp_path / "schedule.json"
    with unittest.mock.patch("pi.scheduler.schedule_writer.subprocess.run"):
        result = write_schedule(conn, schedule_path=schedule_path, repo_root=tmp_path)
    assert result is True


def test_write_schedule_returns_false_when_unchanged(conn, tmp_path):
    schedule_path = tmp_path / "schedule.json"
    with unittest.mock.patch("pi.scheduler.schedule_writer.subprocess.run"):
        write_schedule(conn, schedule_path=schedule_path, repo_root=tmp_path)
        result = write_schedule(conn, schedule_path=schedule_path, repo_root=tmp_path)
    assert result is False


def test_write_schedule_calls_git_when_changed(conn, tmp_path):
    schedule_path = tmp_path / "schedule.json"
    with unittest.mock.patch("pi.scheduler.schedule_writer.subprocess.run") as mock_run:
        write_schedule(conn, schedule_path=schedule_path, repo_root=tmp_path)
    assert mock_run.called


def test_write_schedule_no_git_when_unchanged(conn, tmp_path):
    schedule_path = tmp_path / "schedule.json"
    with unittest.mock.patch("pi.scheduler.schedule_writer.subprocess.run") as mock_run:
        write_schedule(conn, schedule_path=schedule_path, repo_root=tmp_path)
        mock_run.reset_mock()
        write_schedule(conn, schedule_path=schedule_path, repo_root=tmp_path)
    assert not mock_run.called
