"""Prewarm HailoRT models before high-usage windows to reduce first-activation latency."""
from __future__ import annotations

import asyncio
import datetime
import json
import logging
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

from pi.scheduler.heatmap import build_heatmap

if TYPE_CHECKING:
    from pi.llm.hailo_client import HailoLLMClient
    from pi.stt.hailo_transcriber import HailoTranscriber

log = logging.getLogger(__name__)

_PREWARM_ADVANCE_MINUTES = 5
_TOP_N = 3
_WEEK_MINUTES = 7 * 24 * 60


def _minutes_until_prewarm(target_day: int, target_hour: int) -> int:
    """Return whole minutes until the prewarm time for (target_day, target_hour).

    Prewarm fires _PREWARM_ADVANCE_MINUTES before the target window.
    target_day: Python weekday 0=Monday..6=Sunday.
    Returns a positive integer in (0, _WEEK_MINUTES].
    """
    now = datetime.datetime.now()
    current_minute_of_week = now.weekday() * 1440 + now.hour * 60 + now.minute

    prewarm_minute_of_week = target_day * 1440 + target_hour * 60 - _PREWARM_ADVANCE_MINUTES
    if prewarm_minute_of_week < 0:
        prewarm_minute_of_week += _WEEK_MINUTES

    delta = prewarm_minute_of_week - current_minute_of_week
    if delta <= 0:
        delta += _WEEK_MINUTES
    return delta


class PrewarmScheduler:
    """Schedules asyncio callbacks to load HailoRT models before high-usage windows.

    No-op when schedule.json is in default mode (fewer than 14 days of activation data).
    """

    def __init__(
        self,
        llm: "HailoLLMClient",
        stt: "HailoTranscriber",
        schedule_path: Path | str,
        db_conn: sqlite3.Connection,
    ) -> None:
        self._llm = llm
        self._stt = stt
        self._schedule_path = Path(schedule_path)
        self._db_conn = db_conn
        self._handles: list[asyncio.TimerHandle] = []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_default_schedule(self) -> bool:
        """Return True when schedule.json is missing or indicates < 14 days of data."""
        try:
            data = json.loads(self._schedule_path.read_text())
            return bool(data.get("default", False))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return True

    def _top_windows(self) -> list[tuple[int, int]]:
        """Return up to _TOP_N (day_of_week, hour) pairs with the highest activation count."""
        heatmap = build_heatmap(self._db_conn)
        if not heatmap:
            return []
        ranked = sorted(heatmap.items(), key=lambda kv: kv[1], reverse=True)
        return [slot for slot, _ in ranked[:_TOP_N]]

    def _do_prewarm(self) -> None:
        """Load both HailoRT models sequentially. Errors are logged, not propagated."""
        try:
            self._llm._ensure_loaded()
            log.info("Prewarm: LLM loaded")
        except Exception:
            log.exception("Prewarm: LLM load failed")
        try:
            self._stt._ensure_loaded()
            log.info("Prewarm: STT loaded")
        except Exception:
            log.exception("Prewarm: STT load failed")

    def _schedule_one(
        self, loop: asyncio.AbstractEventLoop, day: int, hour: int
    ) -> None:
        delay_seconds = _minutes_until_prewarm(day, hour) * 60

        def _fire() -> None:
            log.info("Prewarm: firing for weekday=%d hour=%02d", day, hour)
            loop.run_in_executor(None, self._do_prewarm)
            handle = loop.call_later(_WEEK_MINUTES * 60, _fire)
            self._handles.append(handle)

        handle = loop.call_later(delay_seconds, _fire)
        self._handles.append(handle)
        log.info(
            "Prewarm scheduled: weekday=%d hour=%02d in %.0fs",
            day, hour, delay_seconds,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        """Schedule prewarm callbacks; no-op if < 14 days of activation data."""
        if self._is_default_schedule():
            log.info("PrewarmScheduler: schedule.json in default mode — skipping")
            return

        windows = self._top_windows()
        if not windows:
            log.info("PrewarmScheduler: no activation data in DB — skipping")
            return

        for day, hour in windows:
            self._schedule_one(loop, day, hour)

        log.info("PrewarmScheduler: scheduled %d prewarm callbacks", len(windows))

    def cancel(self) -> None:
        """Cancel all pending prewarm callbacks."""
        for handle in self._handles:
            handle.cancel()
        self._handles.clear()
