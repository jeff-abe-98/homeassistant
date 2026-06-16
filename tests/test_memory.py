"""Smoke tests for pi/memory/db.py and pi/memory/session.py.

Covers:
  - init_db creates all three tables
  - Session lifecycle (start / add_turn / end)
  - get_context_turns ordering and limit
  - Persistence across simulated restart (re-open the same DB file)
  - Activation logging

Run with: pytest tests/test_memory.py -v
"""
from __future__ import annotations

import sqlite3
import time

import pytest

from pi.memory.db import init_db
from pi.memory.session import Session, log_activation


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_path(tmp_path):
    return str(tmp_path / "memory.db")


@pytest.fixture()
def conn(db_path):
    c = init_db(db_path)
    yield c
    c.close()


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------


def test_init_db_creates_tables(conn):
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert {"sessions", "turns", "activations"}.issubset(tables)


def test_init_db_idempotent(db_path):
    c1 = init_db(db_path)
    c1.close()
    c2 = init_db(db_path)
    tables = {
        row[0]
        for row in c2.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "sessions" in tables
    c2.close()


def test_init_db_wal_mode(conn):
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode == "wal"


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------


def test_session_start_inserts_row(conn):
    s = Session(conn)
    s.start(speaker="owner")
    row = conn.execute("SELECT speaker, ended_at FROM sessions WHERE id=1").fetchone()
    assert row[0] == "owner"
    assert row[1] is None


def test_session_end_sets_ended_at(conn):
    s = Session(conn)
    s.start(speaker="owner")
    s.end()
    ended_at = conn.execute("SELECT ended_at FROM sessions WHERE id=1").fetchone()[0]
    assert ended_at is not None
    assert ended_at <= time.time()


def test_session_add_turn_without_start_raises(conn):
    s = Session(conn)
    with pytest.raises(RuntimeError, match="start()"):
        s.add_turn("hello", "hi there")


def test_session_add_turn_inserts_user_and_assistant(conn):
    s = Session(conn)
    s.start(speaker="emily")
    s.add_turn("what's the weather?", "It's sunny and 72°F.")
    rows = conn.execute(
        "SELECT role, content FROM turns ORDER BY id"
    ).fetchall()
    assert rows[0] == ("user", "what's the weather?")
    assert rows[1] == ("assistant", "It's sunny and 72°F.")


def test_multiple_turns_stored_in_order(conn):
    s = Session(conn)
    s.start(speaker="owner")
    s.add_turn("turn 1 user", "turn 1 assistant")
    s.add_turn("turn 2 user", "turn 2 assistant")
    rows = conn.execute(
        "SELECT role, content FROM turns ORDER BY id"
    ).fetchall()
    assert [r[0] for r in rows] == ["user", "assistant", "user", "assistant"]
    assert rows[2][1] == "turn 2 user"


def test_session_end_is_noop_if_not_started(conn):
    s = Session(conn)
    s.end()  # should not raise


# ---------------------------------------------------------------------------
# get_context_turns
# ---------------------------------------------------------------------------


def test_get_context_turns_empty(conn):
    s = Session(conn)
    s.start()
    assert s.get_context_turns(6) == []


def test_get_context_turns_returns_chronological_order(conn):
    s = Session(conn)
    s.start(speaker="owner")
    s.add_turn("first question", "first answer")
    s.add_turn("second question", "second answer")
    turns = s.get_context_turns(10)
    assert turns[0] == {"role": "user", "content": "first question"}
    assert turns[1] == {"role": "assistant", "content": "first answer"}
    assert turns[2] == {"role": "user", "content": "second question"}
    assert turns[3] == {"role": "assistant", "content": "second answer"}


def test_get_context_turns_respects_limit(conn):
    s = Session(conn)
    s.start()
    for i in range(5):
        s.add_turn(f"q{i}", f"a{i}")
    turns = s.get_context_turns(4)
    assert len(turns) == 4


def test_get_context_turns_returns_most_recent(conn):
    s = Session(conn)
    s.start()
    for i in range(5):
        s.add_turn(f"q{i}", f"a{i}")
    turns = s.get_context_turns(2)
    assert turns[0]["content"] == "q4"
    assert turns[1]["content"] == "a4"


def test_get_context_turns_dict_keys(conn):
    s = Session(conn)
    s.start()
    s.add_turn("hello", "hi")
    turns = s.get_context_turns(6)
    for t in turns:
        assert set(t.keys()) == {"role", "content"}
        assert t["role"] in ("user", "assistant")


# ---------------------------------------------------------------------------
# Persistence across simulated restart
# ---------------------------------------------------------------------------


def test_persistence_across_restart(db_path):
    c1 = init_db(db_path)
    s1 = Session(c1)
    s1.start(speaker="owner")
    s1.add_turn("remember me?", "of course!")
    s1.end()
    c1.close()

    c2 = init_db(db_path)
    s2 = Session(c2)
    s2.start(speaker="owner")
    turns = s2.get_context_turns(10)
    c2.close()

    assert any(t["content"] == "remember me?" for t in turns)
    assert any(t["content"] == "of course!" for t in turns)


def test_multiple_sessions_all_persisted(db_path):
    c1 = init_db(db_path)
    for i in range(3):
        s = Session(c1)
        s.start(speaker="owner")
        s.add_turn(f"session {i} question", f"session {i} answer")
        s.end()
    row = c1.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    assert row == 3
    c1.close()

    c2 = init_db(db_path)
    row = c2.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    assert row == 3
    c2.close()


# ---------------------------------------------------------------------------
# Activation logging
# ---------------------------------------------------------------------------


def test_log_activation_inserts_row(conn):
    before = time.time()
    log_activation(conn, speaker="emily")
    after = time.time()
    row = conn.execute(
        "SELECT speaker, timestamp FROM activations WHERE id=1"
    ).fetchone()
    assert row[0] == "emily"
    assert before <= row[1] <= after


def test_log_activation_default_speaker(conn):
    log_activation(conn)
    row = conn.execute("SELECT speaker FROM activations WHERE id=1").fetchone()
    assert row[0] == "unknown"


def test_log_activation_multiple(conn):
    log_activation(conn, speaker="owner")
    log_activation(conn, speaker="emily")
    log_activation(conn, speaker="owner")
    count = conn.execute("SELECT COUNT(*) FROM activations").fetchone()[0]
    assert count == 3


def test_log_activation_timestamps_ascending(conn):
    log_activation(conn, speaker="owner")
    time.sleep(0.01)
    log_activation(conn, speaker="owner")
    rows = conn.execute(
        "SELECT timestamp FROM activations ORDER BY id"
    ).fetchall()
    assert rows[0][0] <= rows[1][0]
