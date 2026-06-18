"""Syncs pending tool requests to GitHub by writing JSON files and pushing."""
from __future__ import annotations

import logging
import socket
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from .models import ToolRequest
from .queue import ToolRequestQueue

if TYPE_CHECKING:
    from pi.tools.base import ToolRegistry

logger = logging.getLogger(__name__)

# Resolved once at import time — pi/tool_requests/ → pi/ → repo root
_REPO_ROOT = str(Path(__file__).resolve().parent.parent.parent)

_ONLINE_CHECK_HOST = "8.8.8.8"
_ONLINE_CHECK_PORT = 53
_ONLINE_CHECK_TIMEOUT = 3.0


def is_online(
    host: str = _ONLINE_CHECK_HOST,
    port: int = _ONLINE_CHECK_PORT,
    timeout: float = _ONLINE_CHECK_TIMEOUT,
) -> bool:
    """Return True if a TCP connection to host:port succeeds within timeout."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def sync(queue: ToolRequestQueue, repo_root: str = _REPO_ROOT) -> int:
    """Write pending requests as JSON to tool_requests/pending/ and git push.

    On success, marks each request as 'pushed' in the queue and returns the
    count of requests pushed.  On any git failure the written JSON files are
    removed and 0 is returned.
    """
    pending = queue.get_pending()
    if not pending:
        return 0

    root = Path(repo_root).resolve()
    pending_dir = root / "tool_requests" / "pending"
    pending_dir.mkdir(parents=True, exist_ok=True)

    written: list[tuple] = []
    for req in pending:
        path = pending_dir / f"{req.id}.json"
        path.write_text(req.model_dump_json(indent=2))
        written.append((req, path))

    rel_paths = [str(p.relative_to(root)) for _, p in written]

    try:
        subprocess.run(
            ["git", "-C", str(root), "add"] + rel_paths,
            check=True,
            capture_output=True,
            timeout=30,
        )
        subprocess.run(
            [
                "git", "-C", str(root), "commit", "-m",
                f"tool_requests: add {len(written)} pending request(s)",
            ],
            check=True,
            capture_output=True,
            timeout=30,
        )
        subprocess.run(
            ["git", "-C", str(root), "push", "-u", "origin", "main"],
            check=True,
            capture_output=True,
            timeout=60,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode(errors="replace").strip()
        logger.error("git operation failed: %s", stderr)
        _remove_written(written)
        return 0
    except subprocess.TimeoutExpired:
        logger.error("git push timed out")
        _remove_written(written)
        return 0

    for req, _ in written:
        queue.mark_pushed(req.id)

    logger.info("Synced %d tool request(s) to GitHub", len(written))
    return len(written)


def pull_completed_tools(
    queue: ToolRequestQueue,
    registry: "ToolRegistry",
    repo_root: str = _REPO_ROOT,
) -> list[str]:
    """git pull, process tool_requests/complete/ JSONs, reload ToolRegistry.

    Updates local queue status for any requests the remote agent completed or
    failed, then reloads the registry to pick up new tool .py files.  Returns
    the sorted names of tools newly registered since the call.  Returns [] on
    git failure — the caller retries on the next activation.
    """
    root = Path(repo_root).resolve()

    try:
        subprocess.run(
            ["git", "-C", str(root), "pull", "--ff-only", "origin", "main"],
            check=True,
            capture_output=True,
            timeout=60,
        )
    except subprocess.CalledProcessError as exc:
        logger.warning("git pull failed: %s", exc.stderr.decode(errors="replace").strip())
        return []
    except subprocess.TimeoutExpired:
        logger.warning("git pull timed out")
        return []

    complete_dir = root / "tool_requests" / "complete"
    if complete_dir.exists():
        for json_path in complete_dir.glob("*.json"):
            try:
                req = ToolRequest.model_validate_json(json_path.read_text())
            except Exception:
                continue
            try:
                if req.status == "complete":
                    queue.mark_complete(req.id)
                elif req.status == "failed":
                    queue.mark_failed(req.id, req.error or "unknown error")
            except Exception:
                pass

    before = {t.name for t in registry.all()}
    registry.load()
    after = {t.name for t in registry.all()}
    new_names = sorted(after - before)

    if new_names:
        logger.info("Pulled %d new tool(s): %s", len(new_names), ", ".join(new_names))

    return new_names


def _remove_written(written: list[tuple]) -> None:
    for _, path in written:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
