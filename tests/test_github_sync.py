"""Smoke tests for pi/tool_requests/github_sync.py.

Covers:
  - is_online(): returns True when TCP connect succeeds
  - is_online(): returns False when TCP connect raises OSError
  - is_online(): accepts custom host/port/timeout
  - sync(): returns 0 immediately when queue is empty
  - sync(): writes one JSON file per pending request
  - sync(): JSON content matches ToolRequest fields
  - sync(): calls git add, commit, push in order
  - pull_completed_tools(): git pull failure returns []
  - pull_completed_tools(): git pull timeout returns []
  - pull_completed_tools(): no complete dir returns []
  - pull_completed_tools(): empty complete dir returns []
  - pull_completed_tools(): complete JSON marks request complete in queue
  - pull_completed_tools(): failed JSON marks request failed in queue
  - pull_completed_tools(): bad JSON skipped, others still processed
  - pull_completed_tools(): new tool file detected, name returned
  - pull_completed_tools(): already-known tool not returned again
  - pull_completed_tools(): announcement queue populated (get_unannounced_complete)
  - pull_completed_tools(): instructions.md picked up by build_system_prompt
  - pull_completed_tools(): git pull called with correct command
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
from pi.tool_requests.github_sync import is_online, pull_completed_tools, sync


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


# ---------------------------------------------------------------------------
# Helpers for pull_completed_tools tests
# ---------------------------------------------------------------------------


def _make_registry(initial_tools: list | None = None) -> MagicMock:
    reg = MagicMock()
    _tools = list(initial_tools or [])
    reg.all.side_effect = lambda: list(_tools)

    def _load():
        pass

    reg.load.side_effect = _load
    return reg, _tools


def _write_complete_json(complete_dir: Path, req: ToolRequest) -> None:
    complete_dir.mkdir(parents=True, exist_ok=True)
    (complete_dir / f"{req.id}.json").write_text(req.model_dump_json(indent=2))


# ---------------------------------------------------------------------------
# pull_completed_tools: git pull failures
# ---------------------------------------------------------------------------


def test_pull_git_pull_failure_returns_empty(q, tmp_path):
    reg, _ = _make_registry()
    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, ["git"], stderr=b"auth fail")):
        result = pull_completed_tools(q, reg, repo_root=str(tmp_path))
    assert result == []


def test_pull_git_pull_timeout_returns_empty(q, tmp_path):
    reg, _ = _make_registry()
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(["git"], 60)):
        result = pull_completed_tools(q, reg, repo_root=str(tmp_path))
    assert result == []


def test_pull_git_pull_failure_does_not_call_registry_load(q, tmp_path):
    reg, _ = _make_registry()
    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, ["git"], stderr=b"")):
        pull_completed_tools(q, reg, repo_root=str(tmp_path))
    reg.load.assert_not_called()


# ---------------------------------------------------------------------------
# pull_completed_tools: missing / empty complete dir
# ---------------------------------------------------------------------------


def test_pull_no_complete_dir_returns_empty(q, tmp_path):
    reg, _ = _make_registry()
    with patch("subprocess.run", return_value=MagicMock(returncode=0)):
        result = pull_completed_tools(q, reg, repo_root=str(tmp_path))
    assert result == []


def test_pull_empty_complete_dir_returns_empty(q, tmp_path):
    (tmp_path / "tool_requests" / "complete").mkdir(parents=True)
    reg, _ = _make_registry()
    with patch("subprocess.run", return_value=MagicMock(returncode=0)):
        result = pull_completed_tools(q, reg, repo_root=str(tmp_path))
    assert result == []


# ---------------------------------------------------------------------------
# pull_completed_tools: queue status updates
# ---------------------------------------------------------------------------


def test_pull_complete_json_marks_queue_complete(q, tmp_path):
    req = _req(intent="play jazz")
    q.enqueue(req)
    q.mark_pushed(req.id)

    done = ToolRequest(id=req.id, intent=req.intent, user_query=req.user_query, status="complete")
    complete_dir = tmp_path / "tool_requests" / "complete"
    _write_complete_json(complete_dir, done)

    reg, _ = _make_registry()
    with patch("subprocess.run", return_value=MagicMock(returncode=0)):
        pull_completed_tools(q, reg, repo_root=str(tmp_path))

    completed = q.get_unannounced_complete()
    assert any(r.id == req.id for r in completed)


def test_pull_failed_json_marks_queue_failed(q, tmp_path):
    req = _req(intent="call mom")
    q.enqueue(req)
    q.mark_pushed(req.id)

    failed = ToolRequest(id=req.id, intent=req.intent, user_query=req.user_query, status="failed", error="LLM timeout")
    complete_dir = tmp_path / "tool_requests" / "complete"
    _write_complete_json(complete_dir, failed)

    reg, _ = _make_registry()
    with patch("subprocess.run", return_value=MagicMock(returncode=0)):
        pull_completed_tools(q, reg, repo_root=str(tmp_path))

    unannounced = q.get_unannounced_complete()
    match = next((r for r in unannounced if r.id == req.id), None)
    assert match is not None
    assert match.status == "failed"


def test_pull_bad_json_skipped_others_processed(q, tmp_path):
    req = _req(intent="check trains")
    q.enqueue(req)
    q.mark_pushed(req.id)

    complete_dir = tmp_path / "tool_requests" / "complete"
    complete_dir.mkdir(parents=True)
    (complete_dir / "corrupt.json").write_text("{not valid json")

    done = ToolRequest(id=req.id, intent=req.intent, user_query=req.user_query, status="complete")
    _write_complete_json(complete_dir, done)

    reg, _ = _make_registry()
    with patch("subprocess.run", return_value=MagicMock(returncode=0)):
        pull_completed_tools(q, reg, repo_root=str(tmp_path))

    assert any(r.id == req.id for r in q.get_unannounced_complete())


# ---------------------------------------------------------------------------
# pull_completed_tools: new tool detection
# ---------------------------------------------------------------------------


def test_pull_new_tool_name_returned(q, tmp_path):
    mock_tool = MagicMock()
    mock_tool.name = "jazz_player"

    reg = MagicMock()
    loaded = [False]

    def _all():
        return [mock_tool] if loaded[0] else []

    def _load():
        loaded[0] = True

    reg.all.side_effect = _all
    reg.load.side_effect = _load

    with patch("subprocess.run", return_value=MagicMock(returncode=0)):
        result = pull_completed_tools(q, reg, repo_root=str(tmp_path))

    assert result == ["jazz_player"]


def test_pull_already_known_tool_not_returned(q, tmp_path):
    mock_tool = MagicMock()
    mock_tool.name = "weather"

    reg = MagicMock()
    reg.all.return_value = [mock_tool]
    reg.load.return_value = None

    with patch("subprocess.run", return_value=MagicMock(returncode=0)):
        result = pull_completed_tools(q, reg, repo_root=str(tmp_path))

    assert result == []


def test_pull_git_pull_command_correct(q, tmp_path):
    reg, _ = _make_registry()
    git_calls = []

    def capture(cmd, **kwargs):
        git_calls.append(cmd)
        return MagicMock(returncode=0)

    with patch("subprocess.run", side_effect=capture):
        pull_completed_tools(q, reg, repo_root=str(tmp_path))

    assert len(git_calls) == 1
    cmd = git_calls[0]
    assert "git" in cmd
    assert "pull" in cmd
    assert "--ff-only" in cmd


# ---------------------------------------------------------------------------
# pull_completed_tools: announcement queue integration
# ---------------------------------------------------------------------------


def test_pull_unannounced_complete_populated(q, tmp_path):
    r1 = _req(intent="check weather")
    r2 = _req(intent="check trains")
    q.enqueue(r1)
    q.enqueue(r2)
    q.mark_pushed(r1.id)
    q.mark_pushed(r2.id)

    complete_dir = tmp_path / "tool_requests" / "complete"
    for req in [r1, r2]:
        done = ToolRequest(id=req.id, intent=req.intent, user_query=req.user_query, status="complete")
        _write_complete_json(complete_dir, done)

    reg, _ = _make_registry()
    with patch("subprocess.run", return_value=MagicMock(returncode=0)):
        pull_completed_tools(q, reg, repo_root=str(tmp_path))

    unannounced = q.get_unannounced_complete()
    ids = {r.id for r in unannounced}
    assert r1.id in ids
    assert r2.id in ids


# ---------------------------------------------------------------------------
# pull_completed_tools: instruction loading into system prompt
# ---------------------------------------------------------------------------


def test_pull_instructions_md_loaded_into_system_prompt(q, tmp_path):
    from pi.llm.prompts import build_system_prompt
    import pi.llm.prompts as prompts_mod
    from pathlib import Path as _Path

    instr_dir = tmp_path / "tools" / "generated"
    instr_dir.mkdir(parents=True)
    (instr_dir / "jazz_player_instructions.md").write_text(
        "Trigger: 'play some jazz' or 'put on jazz'\nRequired: genre param"
    )

    with patch.object(prompts_mod, "_GENERATED_TOOLS_DIR", instr_dir):
        prompt = build_system_prompt(user="owner")

    assert "play some jazz" in prompt
    assert "genre param" in prompt
