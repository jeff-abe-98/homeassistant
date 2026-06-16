"""Smoke tests for pi/tool_requests/models.py and pi/tool_requests/queue.py.

Covers:
  - ToolRequest model defaults (UUID, timestamp, status)
  - enqueue / get_pending round-trip
  - Priority ordering (high > mid > low, FIFO within same priority)
  - get_highest_priority returns top item
  - mark_pushed / mark_complete / mark_failed status transitions
  - mark_failed stores error string
  - get_unannounced_complete returns complete + failed with announced=0
  - mark_announced suppresses items from get_unannounced_complete
  - Context list JSON round-trip
  - Persistence across queue re-open (same DB file)

Run with: pytest tests/test_tool_requests.py -v
"""
from __future__ import annotations

import time

import pytest

from pi.tool_requests.models import ToolRequest
from pi.tool_requests.queue import ToolRequestQueue


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_path(tmp_path):
    return str(tmp_path / "tool_requests.db")


@pytest.fixture()
def q(db_path):
    queue = ToolRequestQueue(db_path)
    yield queue
    queue.close()


def _req(**kwargs) -> ToolRequest:
    defaults = dict(intent="play music", user_query="play some jazz")
    defaults.update(kwargs)
    return ToolRequest(**defaults)


# ---------------------------------------------------------------------------
# Model defaults
# ---------------------------------------------------------------------------


def test_model_defaults():
    req = ToolRequest(intent="set a timer", user_query="set a timer for 5 minutes")
    assert len(req.id) == 36  # UUID4 format
    assert req.timestamp > 0
    assert req.status == "pending"
    assert req.priority == "mid"
    assert req.speaker == "unknown"
    assert req.context == []
    assert req.error is None


def test_model_priority_rank():
    assert ToolRequest(intent="x", user_query="x", priority="high").priority_rank == 0
    assert ToolRequest(intent="x", user_query="x", priority="mid").priority_rank == 1
    assert ToolRequest(intent="x", user_query="x", priority="low").priority_rank == 2


# ---------------------------------------------------------------------------
# Enqueue / get_pending
# ---------------------------------------------------------------------------


def test_enqueue_and_get_pending(q):
    req = _req()
    q.enqueue(req)
    pending = q.get_pending()
    assert len(pending) == 1
    assert pending[0].id == req.id
    assert pending[0].intent == req.intent
    assert pending[0].user_query == req.user_query
    assert pending[0].status == "pending"


def test_get_pending_empty(q):
    assert q.get_pending() == []


def test_get_pending_excludes_non_pending(q):
    r1 = _req(intent="a")
    r2 = _req(intent="b")
    r3 = _req(intent="c")
    q.enqueue(r1)
    q.enqueue(r2)
    q.enqueue(r3)
    q.mark_pushed(r2.id)
    pending = q.get_pending()
    ids = [r.id for r in pending]
    assert r1.id in ids
    assert r3.id in ids
    assert r2.id not in ids


# ---------------------------------------------------------------------------
# Priority ordering
# ---------------------------------------------------------------------------


def test_get_pending_priority_order(q):
    low = _req(intent="low", priority="low")
    high = _req(intent="high", priority="high")
    mid = _req(intent="mid", priority="mid")
    # enqueue out of order
    q.enqueue(low)
    q.enqueue(mid)
    q.enqueue(high)
    pending = q.get_pending()
    assert [r.priority for r in pending] == ["high", "mid", "low"]


def test_get_pending_fifo_within_priority(q):
    r1 = _req(intent="first", priority="mid")
    time.sleep(0.01)
    r2 = _req(intent="second", priority="mid")
    q.enqueue(r1)
    q.enqueue(r2)
    pending = q.get_pending()
    assert pending[0].id == r1.id
    assert pending[1].id == r2.id


# ---------------------------------------------------------------------------
# get_highest_priority
# ---------------------------------------------------------------------------


def test_get_highest_priority(q):
    q.enqueue(_req(intent="low", priority="low"))
    q.enqueue(_req(intent="high", priority="high"))
    q.enqueue(_req(intent="mid", priority="mid"))
    top = q.get_highest_priority()
    assert top is not None
    assert top.priority == "high"


def test_get_highest_priority_empty(q):
    assert q.get_highest_priority() is None


def test_get_highest_priority_none_pending(q):
    req = _req()
    q.enqueue(req)
    q.mark_pushed(req.id)
    assert q.get_highest_priority() is None


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------


def test_mark_pushed(q):
    req = _req()
    q.enqueue(req)
    q.mark_pushed(req.id)
    assert q.get_pending() == []


def test_mark_complete(q):
    req = _req()
    q.enqueue(req)
    q.mark_pushed(req.id)
    q.mark_complete(req.id)
    unannounced = q.get_unannounced_complete()
    assert len(unannounced) == 1
    assert unannounced[0].status == "complete"


def test_mark_failed_stores_error(q):
    req = _req()
    q.enqueue(req)
    q.mark_failed(req.id, error="LLM timeout")
    unannounced = q.get_unannounced_complete()
    assert len(unannounced) == 1
    assert unannounced[0].status == "failed"
    assert unannounced[0].error == "LLM timeout"


# ---------------------------------------------------------------------------
# Announcement queue
# ---------------------------------------------------------------------------


def test_get_unannounced_complete_empty(q):
    assert q.get_unannounced_complete() == []


def test_get_unannounced_complete_pending_not_included(q):
    req = _req()
    q.enqueue(req)
    assert q.get_unannounced_complete() == []


def test_mark_announced_suppresses(q):
    req = _req()
    q.enqueue(req)
    q.mark_complete(req.id)
    assert len(q.get_unannounced_complete()) == 1
    q.mark_announced(req.id)
    assert q.get_unannounced_complete() == []


def test_mixed_announced_and_not(q):
    r1 = _req(intent="a")
    r2 = _req(intent="b")
    q.enqueue(r1)
    q.enqueue(r2)
    q.mark_complete(r1.id)
    q.mark_complete(r2.id)
    q.mark_announced(r1.id)
    unannounced = q.get_unannounced_complete()
    assert len(unannounced) == 1
    assert unannounced[0].id == r2.id


# ---------------------------------------------------------------------------
# Context JSON round-trip
# ---------------------------------------------------------------------------


def test_context_round_trip(q):
    ctx = [
        {"role": "user", "content": "play jazz"},
        {"role": "assistant", "content": "I don't know how to do that yet"},
    ]
    req = _req(context=ctx)
    q.enqueue(req)
    pending = q.get_pending()
    assert pending[0].context == ctx


# ---------------------------------------------------------------------------
# Speaker field
# ---------------------------------------------------------------------------


def test_speaker_stored(q):
    req = _req(speaker="emily")
    q.enqueue(req)
    assert q.get_pending()[0].speaker == "emily"


# ---------------------------------------------------------------------------
# Persistence across re-open
# ---------------------------------------------------------------------------


def test_persistence_across_restart(db_path):
    r1 = _req(intent="first")
    r2 = _req(intent="second")

    q1 = ToolRequestQueue(db_path)
    q1.enqueue(r1)
    q1.enqueue(r2)
    q1.mark_pushed(r1.id)
    q1.close()

    q2 = ToolRequestQueue(db_path)
    pending = q2.get_pending()
    assert len(pending) == 1
    assert pending[0].id == r2.id
    q2.close()
