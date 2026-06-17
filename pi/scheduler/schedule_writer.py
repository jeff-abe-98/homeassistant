"""Write schedule.json from the activation heatmap; git push when content changes.

Run daily via systemd timer:  python -m pi.scheduler.schedule_writer
"""
from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from pi.memory.db import init_db
from pi.scheduler.heatmap import build_heatmap, find_low_usage_windows, has_enough_data

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_MEMORY_DB_PATH = "memory.db"
_DEFAULT_SCHEDULE: dict = {"default": True, "hour": 3, "minute": 0}


def write_schedule(
    conn,
    schedule_path: str | Path | None = None,
    repo_root: str | Path | None = None,
) -> bool:
    """Compute schedule from heatmap, write schedule.json, and git push if changed.

    Returns True if the file was updated (and push was attempted), False if unchanged.
    """
    root = Path(repo_root).resolve() if repo_root is not None else _REPO_ROOT
    path = Path(schedule_path) if schedule_path is not None else root / "schedule.json"

    if not has_enough_data(conn):
        new_data: dict = _DEFAULT_SCHEDULE
    else:
        heatmap = build_heatmap(conn)
        windows = find_low_usage_windows(heatmap)
        new_data = {"windows": windows}

    new_text = json.dumps(new_data, indent=2) + "\n"

    if path.exists() and path.read_text() == new_text:
        logger.info("schedule.json unchanged — skipping push")
        return False

    path.write_text(new_text)
    logger.info("schedule.json updated")

    _git_push(root, path)
    return True


def _git_push(repo_root: Path, schedule_path: Path) -> None:
    try:
        rel = str(schedule_path.relative_to(repo_root))
    except ValueError:
        rel = str(schedule_path)

    try:
        subprocess.run(
            ["git", "-C", str(repo_root), "add", rel],
            check=True, capture_output=True, timeout=30,
        )
        subprocess.run(
            ["git", "-C", str(repo_root), "commit", "-m", "scheduler: update schedule.json"],
            check=True, capture_output=True, timeout=30,
        )
        subprocess.run(
            ["git", "-C", str(repo_root), "push", "-u", "origin", "main"],
            check=True, capture_output=True, timeout=60,
        )
        logger.info("schedule.json pushed to GitHub")
    except subprocess.CalledProcessError as exc:
        logger.error("git operation failed: %s", exc.stderr.decode(errors="replace").strip())
    except subprocess.TimeoutExpired:
        logger.error("git push timed out")


def main() -> None:
    conn = init_db(_MEMORY_DB_PATH)
    try:
        write_schedule(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
