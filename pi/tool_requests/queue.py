"""SQLite-backed queue for tool creation requests."""
from __future__ import annotations

import json
import sqlite3

from .models import ToolRequest


class ToolRequestQueue:
    def __init__(self, db_path: str) -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS tool_requests (
                id         TEXT PRIMARY KEY,
                timestamp  REAL NOT NULL,
                intent     TEXT NOT NULL,
                user_query TEXT NOT NULL,
                speaker    TEXT NOT NULL DEFAULT 'unknown',
                priority   TEXT NOT NULL DEFAULT 'mid'
                               CHECK(priority IN ('low', 'mid', 'high')),
                status     TEXT NOT NULL DEFAULT 'pending'
                               CHECK(status IN ('pending', 'pushed', 'complete', 'failed')),
                context    TEXT NOT NULL DEFAULT '[]',
                error      TEXT,
                announced  INTEGER NOT NULL DEFAULT 0
            );
        """)
        self._conn.commit()

    def enqueue(self, request: ToolRequest) -> None:
        self._conn.execute(
            """
            INSERT INTO tool_requests
                (id, timestamp, intent, user_query, speaker, priority, status, context, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request.id,
                request.timestamp,
                request.intent,
                request.user_query,
                request.speaker,
                request.priority,
                request.status,
                json.dumps(request.context),
                request.error,
            ),
        )
        self._conn.commit()

    def get_pending(self) -> list[ToolRequest]:
        rows = self._conn.execute(
            "SELECT * FROM tool_requests WHERE status = 'pending'"
            " ORDER BY CASE priority WHEN 'high' THEN 0 WHEN 'mid' THEN 1 ELSE 2 END, timestamp"
        ).fetchall()
        return [self._row_to_model(r) for r in rows]

    def get_highest_priority(self) -> ToolRequest | None:
        row = self._conn.execute(
            "SELECT * FROM tool_requests WHERE status = 'pending'"
            " ORDER BY CASE priority WHEN 'high' THEN 0 WHEN 'mid' THEN 1 ELSE 2 END, timestamp"
            " LIMIT 1"
        ).fetchone()
        return self._row_to_model(row) if row else None

    def mark_pushed(self, request_id: str) -> None:
        self._conn.execute(
            "UPDATE tool_requests SET status = 'pushed' WHERE id = ?", (request_id,)
        )
        self._conn.commit()

    def mark_complete(self, request_id: str) -> None:
        self._conn.execute(
            "UPDATE tool_requests SET status = 'complete' WHERE id = ?", (request_id,)
        )
        self._conn.commit()

    def mark_failed(self, request_id: str, error: str) -> None:
        self._conn.execute(
            "UPDATE tool_requests SET status = 'failed', error = ? WHERE id = ?",
            (error, request_id),
        )
        self._conn.commit()

    def get_unannounced_complete(self) -> list[ToolRequest]:
        rows = self._conn.execute(
            "SELECT * FROM tool_requests WHERE status IN ('complete', 'failed') AND announced = 0"
            " ORDER BY timestamp"
        ).fetchall()
        return [self._row_to_model(r) for r in rows]

    def mark_announced(self, request_id: str) -> None:
        self._conn.execute(
            "UPDATE tool_requests SET announced = 1 WHERE id = ?", (request_id,)
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    @staticmethod
    def _row_to_model(row: sqlite3.Row) -> ToolRequest:
        d = dict(row)
        d["context"] = json.loads(d["context"])
        d.pop("announced", None)
        return ToolRequest(**d)
