"""Activation heatmap: aggregate activations by (day_of_week, hour)."""
from __future__ import annotations

import sqlite3


def has_enough_data(conn: sqlite3.Connection, min_days: int = 14) -> bool:
    """Return True if activations span at least min_days distinct calendar days."""
    row = conn.execute(
        "SELECT COUNT(DISTINCT date(timestamp, 'unixepoch')) FROM activations"
    ).fetchone()
    return (row[0] if row else 0) >= min_days


def build_heatmap(conn: sqlite3.Connection) -> dict[tuple[int, int], int]:
    """Return {(day_of_week, hour): activation_count} for all activations.

    day_of_week uses Python weekday convention: 0=Monday .. 6=Sunday
    hour: 0..23
    """
    rows = conn.execute(
        """
        SELECT
            CAST(strftime('%w', timestamp, 'unixepoch') AS INTEGER) AS dow_sqlite,
            CAST(strftime('%H', timestamp, 'unixepoch') AS INTEGER) AS hour,
            COUNT(*) AS cnt
        FROM activations
        GROUP BY dow_sqlite, hour
        """
    ).fetchall()
    heatmap: dict[tuple[int, int], int] = {}
    for dow_sqlite, hour, cnt in rows:
        # SQLite %w: 0=Sunday..6=Saturday  →  Python weekday: 0=Monday..6=Sunday
        dow_py = (dow_sqlite - 1) % 7
        heatmap[(dow_py, hour)] = cnt
    return heatmap


def find_low_usage_windows(heatmap: dict[tuple[int, int], int]) -> list[dict]:
    """Return the lowest-usage hour for each day of week (0=Mon..6=Sun).

    Returns 7 dicts sorted by day_of_week:
      {"day_of_week": int, "hour": int, "count": int}

    On ties the earliest hour wins (prefer overnight slots for remote agent runs).
    """
    windows = []
    for dow in range(7):
        best_hour = min(range(24), key=lambda h: (heatmap.get((dow, h), 0), h))
        windows.append({
            "day_of_week": dow,
            "hour": best_hour,
            "count": heatmap.get((dow, best_hour), 0),
        })
    return windows
