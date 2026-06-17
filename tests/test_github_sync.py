"""Smoke tests for pi/tool_requests/github_sync.py.

Covers:
  - is_online(): returns True when TCP connect succeeds
  - is_online(): returns False when TCP connect raises OSError
  - is_online(): accepts custom host/port/timeout
  - sync(): returns 0 immediately when queue is empty
  - sync(): writes one JSON file per pending request
  - sync(): JSON content matches ToolRequest fields
  - sync(): calls git add, commit, push in order
  - sync(): marks all synced requests as pushed in queue
  - sync(): returns count of pushed requests
  - sync(): rolls back JSON files when git add fails
  - sync(): rolls back JSON files when git commit fails
  - sync(): rolls back JSON files when git push fails
  - sync(): rolls back when subprocess times out
  - sync(): does not mark requests pushed on failure

Run with: pytest tests/test_github_sync.py -v
"""
from __future__ import annotations

import json
import socket
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from pi.tool_requests.models import ToolRequest
from pi.tool_requests.queue import ToolRequestQueue
from pi.tool_requests.github_sync import is_online, sync


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_path(tmp_path):
    return str(tmp_path / "sync_test.db")


@pytest.fixture()
def q(db_path):
    queue = ToolRequestQueue(db_path)
    yield queue
    queue.close()


@pytest.fixture()
def repo_root(tmp_path):
    """A temporary directory that acts as the git repo root."""
    pending_dir = tmp_path / "tool_requests" / "pending"
    pending_dir.mkdir(parents=True)
    return str(tmp_path)


def _req(**kwargs) -> ToolRequest:
    defaults = dict(intent="set reminder", user_query="remind me to call mom")
    defaults.update(kwargs)
    return ToolRequest(**defaults)


def _make_run_ok():
    """Return a subprocess.run mock that always succeeds."""
    mock = MagicMock(return_value=MagicMock(returncode=0))
    return mock


# ---------------------------------------------------------------------------
# is_online
# ---------------------------------------------------------------------------


def test_is_online_success():
    with patch("socket.create_connection") as mock_conn:
        mock_conn.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        assert is_online() is True


def test_is_online_failure_os_error():
    with patch("socket.create_connection", side_effect=OSError("network unreachable")):
        assert is_online() is False


def test_is_online_failure_timeout():
    with patch("socket.create_connection", side_effect=socket.timeout("timed out")):
        assert is_online() is False


def test_is_online_custom_host_port():
    with patch("socket.create_connection") as mock_conn:
        mock_conn.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        result = is_online(host="1.1.1.1", port=53, timeout=1.0)
        assert result is True
        args, kwargs = mock_conn.call_args
        assert args[0] == ("1.1.1.1", 53)
        assert kwargs.get("timeout", args[1] if len(args) > 1 else None) == 1.0


# ---------------------------------------------------------------------------
# sync: empty queue
# ---------------------------------------------------------------------------


def test_sync_empty_queue(q, repo_root):
    count = sync(q, repo_root=repo_root)
    assert count == 0


def test_sync_empty_queue_no_git_calls(q, repo_root):
    with patch("subprocess.run") as mock_run:
        sync(q, repo_root=repo_root)
        mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# sync: success path
# ---------------------------------------------------------------------------


def test_sync_writes_json_file(q, repo_root):
    req = _req()
    q.enqueue(req)

    with patch("subprocess.run", return_value=MagicMock(returncode=0)):
        sync(q, repo_root=repo_root)

    json_path = Path(repo_root) / "tool_requests" / "pending" / f"{req.id}.json"
    assert json_path.exists()


def test_sync_json_content_matches_request(q, repo_root):
    req = _req(intent="check weather", user_query="what's the weather today", speaker="owner")
    q.enqueue(req)

    with patch("subprocess.run", return_value=MagicMock(returncode=0)):
        sync(q, repo_root=repo_root)

    json_path = Path(repo_root) / "tool_requests" / "pending" / f"{req.id}.json"
    data = json.loads(json_path.read_text())
    assert data["intent"] == "check weather"
    assert data["user_query"] == "what's the weather today"
    assert data["speaker"] == "owner"
    assert data["id"] == req.id


def test_sync_marks_requests_pushed(q, repo_root):
    req = _req()
    q.enqueue(req)

    with patch("subprocess.run", return_value=MagicMock(returncode=0)):
        sync(q, repo_root=repo_root)

    assert q.get_pending() == []


def test_sync_returns_count(q, repo_root):
    q.enqueue(_req(intent="a"))
    q.enqueue(_req(intent="b"))
    q.enqueue(_req(intent="c"))

    with patch("subprocess.run", return_value=MagicMock(returncode=0)):
        count = sync(q, repo_root=repo_root)

    assert count == 3


def test_sync_writes_file_per_request(q, repo_root):
    r1 = _req(intent="first")
    r2 = _req(intent="second")
    q.enqueue(r1)
    q.enqueue(r2)

    with patch("subprocess.run", return_value=MagicMock(returncode=0)):
        sync(q, repo_root=repo_root)

    pending_dir = Path(repo_root) / "tool_requests" / "pending"
    assert (pending_dir / f"{r1.id}.json").exists()
    assert (pending_dir / f"{r2.id}.json").exists()


def test_sync_calls_git_add_commit_push(q, repo_root):
    req = _req()
    q.enqueue(req)

    git_calls = []
    def capture_run(cmd, **kwargs):
        git_calls.append(cmd)
        return MagicMock(returncode=0)

    with patch("subprocess.run", side_effect=capture_run):
        sync(q, repo_root=repo_root)

    assert any("add" in cmd for cmd in git_calls)
    assert any("commit" in cmd for cmd in git_calls)
    assert any("push" in cmd for cmd in git_calls)

    ops = []
    for cmd in git_calls:
        if "add" in cmd:
            ops.append("add")
        elif "commit" in cmd:
            ops.append("commit")
        elif "push" in cmd:
            ops.append("push")
    assert ops == ["add", "commit", "push"]


# ---------------------------------------------------------------------------
# sync: failure paths
# ---------------------------------------------------------------------------


def test_sync_git_add_failure_rolls_back_files(q, repo_root):
    req = _req()
    q.enqueue(req)

    def fail_on_add(cmd, **kwargs):
        if "add" in cmd:
            raise subprocess.CalledProcessError(1, cmd, stderr=b"error")
        return MagicMock(returncode=0)

    with patch("subprocess.run", side_effect=fail_on_add):
        count = sync(q, repo_root=repo_root)

    assert count == 0
    json_path = Path(repo_root) / "tool_requests" / "pending" / f"{req.id}.json"
    assert not json_path.exists()


def test_sync_git_add_failure_does_not_mark_pushed(q, repo_root):
    req = _req()
    q.enqueue(req)

    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, ["git"], stderr=b"")):
        sync(q, repo_root=repo_root)

    assert len(q.get_pending()) == 1


def test_sync_git_commit_failure_rolls_back(q, repo_root):
    req = _req()
    q.enqueue(req)

    call_count = [0]
    def fail_on_commit(cmd, **kwargs):
        call_count[0] += 1
        if "commit" in cmd:
            raise subprocess.CalledProcessError(1, cmd, stderr=b"nothing to commit")
        return MagicMock(returncode=0)

    with patch("subprocess.run", side_effect=fail_on_commit):
        count = sync(q, repo_root=repo_root)

    assert count == 0
    json_path = Path(repo_root) / "tool_requests" / "pending" / f"{req.id}.json"
    assert not json_path.exists()


def test_sync_git_push_failure_rolls_back(q, repo_root):
    req = _req()
    q.enqueue(req)

    def fail_on_push(cmd, **kwargs):
        if "push" in cmd:
            raise subprocess.CalledProcessError(1, cmd, stderr=b"remote rejected")
        return MagicMock(returncode=0)

    with patch("subprocess.run", side_effect=fail_on_push):
        count = sync(q, repo_root=repo_root)

    assert count == 0
    json_path = Path(repo_root) / "tool_requests" / "pending" / f"{req.id}.json"
    assert not json_path.exists()


def test_sync_timeout_rolls_back(q, repo_root):
    req = _req()
    q.enqueue(req)

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(["git"], 30)):
        count = sync(q, repo_root=repo_root)

    assert count == 0
    json_path = Path(repo_root) / "tool_requests" / "pending" / f"{req.id}.json"
    assert not json_path.exists()


def test_sync_timeout_does_not_mark_pushed(q, repo_root):
    req = _req()
    q.enqueue(req)

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(["git"], 30)):
        sync(q, repo_root=repo_root)

    assert len(q.get_pending()) == 1


def test_sync_only_syncs_pending_not_pushed(q, repo_root):
    r1 = _req(intent="already pushed")
    r2 = _req(intent="still pending")
    q.enqueue(r1)
    q.enqueue(r2)
    q.mark_pushed(r1.id)

    with patch("subprocess.run", return_value=MagicMock(returncode=0)):
        count = sync(q, repo_root=repo_root)

    assert count == 1
    pending_dir = Path(repo_root) / "tool_requests" / "pending"
    assert not (pending_dir / f"{r1.id}.json").exists()
    assert (pending_dir / f"{r2.id}.json").exists()
