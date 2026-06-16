"""SQLite database initialisation for conversation memory."""
from __future__ import annotations

import sqlite3


def init_db(path: str) -> sqlite3.Connection:
    """Open (or create) the memory database and ensure the schema exists.

    Uses WAL mode for better read concurrency during the main loop.
    Returns the open connection; caller is responsible for closing it.
    """
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            speaker    TEXT    NOT NULL DEFAULT 'unknown',
            started_at REAL    NOT NULL,
            ended_at   REAL
        );

        CREATE TABLE IF NOT EXISTS turns (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id),
            role       TEXT    NOT NULL CHECK(role IN ('user', 'assistant')),
            content    TEXT    NOT NULL,
            timestamp  REAL    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS activations (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            speaker   TEXT    NOT NULL DEFAULT 'unknown',
            timestamp REAL    NOT NULL
        );
    """)
    conn.commit()
    return conn
