# Current Work

**Last updated:** 2026-06-17
**Phase:** Phase 7 — item 1 done (heatmap + schedule_writer + systemd timer)

---

## Status

Full architectural redesign in progress. The original server+Pi split architecture has been superseded. A new spec and plan have been written for a fully Pi-based system (Pi 5 8GB + AI HAT+ 2).

**Spec:** `.project/active/pi-redesign/spec.md`
**Plan:** `plan.md` (completely replaced — all old phases 1-7 complete and archived)

Phase 7 item 1 is complete:

**Item 1:** `pi/scheduler/heatmap.py` — `has_enough_data(conn, min_days=14)` counts distinct activation days; `build_heatmap(conn)` groups activations by (day_of_week, hour) using Python weekday convention (0=Mon..6=Sun); `find_low_usage_windows(heatmap)` returns lowest-count hour per day (earliest-hour tie-break).

`pi/scheduler/schedule_writer.py` — `write_schedule(conn, schedule_path, repo_root)` writes default `{"default": True, "hour": 3, "minute": 0}` before 14 days of data; after 14 days writes `{"windows": [...]}` from heatmap; only git-pushes when content changes; `main()` entry point for `python -m pi.scheduler.schedule_writer`.

`deploy/homeassistant-scheduler.service` + `deploy/homeassistant-scheduler.timer` — oneshot service + daily timer with `Persistent=true` so runs catch up after Pi downtime.

**Next:** Phase 7 item 2 — Smoke tests: heatmap aggregation, window finding, default before data, schedule.json format.

## Documents

| File | Purpose |
|------|---------|
| `requirements.md` | Full project requirements (still valid) |
| `.project/active/pi-redesign/spec.md` | New architecture spec — read before implementing anything |
| `plan.md` | New phased implementation plan — agent works from here |
| `docs/technical-stack.md` | Updated stack decisions |
| `docs/parts-list.md` | Updated hardware list |

## Key Architecture Decisions

- **Single unified process** on Pi — no WebSocket client/server split
- **HailoRT** for LLM + STT inference on Hailo-10H NPU (replaces Ollama + Faster Whisper)
- **Wake word:** "Clanker" (openWakeWord, unchanged)
- **Tool creation:** Claude Code remote scheduled agent reads/writes via GitHub repo — Pi never calls Claude API directly
- **Tool requests:** Local SQLite queue → push to GitHub when online → agent builds → Pi pulls + loads
- **Scheduling:** Pi usage heatmap drives when the remote agent runs; agent self-reschedules via CronDelete + CronCreate
- **Conversation memory:** SQLite, session-scoped, recent turns injected into LLM prompt
- **Android TV:** `androidtvremote2` (confirmed correct)
- **All existing tools preserved**

## Agent Instructions

1. Read `.project/active/pi-redesign/spec.md` fully before starting any phase
2. Read `plan.md` — find first unchecked item in Phase 1
3. Read `docs/technical-stack.md` for stack context
4. Implement the item
5. Check it off in `plan.md` with a brief note
6. Continue until phase is complete or blocker hit

## Open Questions

None — spec is approved, plan is ready.

## Hardware Notes

- Pi 5 8GB + AI HAT+ 2 + USB mic + A2 SD card + PSU/case ≈ $270
- Hardware arrived 2026-06-15 — Hailo-10H detected on PCIe
- Physical Pi + AI HAT+ 2 needed for real inference (enrollment, Hailo validation)
