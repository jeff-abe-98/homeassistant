"""Session-scoped conversation memory backed by SQLite."""
from __future__ import annotations

import sqlite3
import time
from typing import Optional


def log_activation(conn: sqlite3.Connection, speaker: str = "unknown") -> None:
    """Record a wake-word activation event in the activations table.

    Call this each time the wake word fires, before starting a Session.
    """
    conn.execute(
        "INSERT INTO activations (speaker, timestamp) VALUES (?, ?)",
        (speaker, time.time()),
    )
    conn.commit()


class Session:
    """Tracks one interaction's conversation turns in SQLite.

    Typical lifecycle:
        session = Session(conn)
        session.start(speaker="owner")
        session.add_turn(transcript="what's the weather?", response="It's 72°F...")
        context = session.get_context_turns(6)   # inject into next LLM call
        session.end()
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._session_id: Optional[int] = None

    def start(self, speaker: str = "unknown") -> None:
        """Open a new session row and record start time."""
        cur = self._conn.execute(
            "INSERT INTO sessions (speaker, started_at) VALUES (?, ?)",
            (speaker, time.time()),
        )
        self._conn.commit()
        self._session_id = cur.lastrowid

    def add_turn(self, transcript: str, response: str) -> None:
        """Append a user + assistant turn pair to the current session."""
        if self._session_id is None:
            raise RuntimeError("Session.start() must be called before add_turn()")
        now = time.time()
        self._conn.executemany(
            "INSERT INTO turns (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            [
                (self._session_id, "user", transcript, now),
                (self._session_id, "assistant", response, now),
            ],
        )
        self._conn.commit()

    def end(self) -> None:
        """Mark the session as ended by recording ended_at."""
        if self._session_id is None:
            return
        self._conn.execute(
            "UPDATE sessions SET ended_at = ? WHERE id = ?",
            (time.time(), self._session_id),
        )
        self._conn.commit()

    def get_context_turns(self, n: int = 6) -> list[dict]:
        """Return the last *n* messages (across all sessions) in chronological order.

        Output format matches the LLM messages list:
            [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]

        Pass the result directly as ``context_turns`` to ``ToolRouter.route()``
        or ``build_system_prompt()``.
        """
        rows = self._conn.execute(
            "SELECT role, content FROM turns ORDER BY timestamp DESC, id DESC LIMIT ?",
            (n,),
        ).fetchall()
        return [{"role": role, "content": content} for role, content in reversed(rows)]
