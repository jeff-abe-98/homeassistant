# Current Work

**Last updated:** 2026-06-17
**Phase:** Phase 6 complete — all 3 items done; Phase 7 next

---

## Status

Full architectural redesign in progress. The original server+Pi split architecture has been superseded. A new spec and plan have been written for a fully Pi-based system (Pi 5 8GB + AI HAT+ 2).

**Spec:** `.project/active/pi-redesign/spec.md`
**Plan:** `plan.md` (completely replaced — all old phases 1-7 complete and archived)

Phase 6 is complete (all 3 items done):

**Item 1:** `pi/tool_requests/models.py` + `pi/tool_requests/queue.py` — ToolRequest Pydantic model and SQLite WAL-backed queue. 20 smoke tests pass.

**Item 2:** `pi/tool_requests/github_sync.py` — `is_online()` TCP DNS check, `sync()` writes JSON files + git push + marks pushed + rollback on failure. `pi/main.py` — capability gap heuristic + priority dialogue + enqueue + sync.

**Item 3:** `tests/test_github_sync.py` — 19 smoke tests: is_online (success/OSError/timeout/custom args), sync (empty queue, JSON written, content verified, marks pushed, count returned, multiple files, git call order, rollback on add/commit/push failure/timeout, pending-only filter). 39 tests pass total across tool_requests + github_sync.

**Next:** Phase 7 item 1 — `pi/scheduler/heatmap.py` + `pi/scheduler/schedule_writer.py` + default schedule + systemd timer.

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
