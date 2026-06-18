# Current Work

**Last updated:** 2026-06-18
**Phase:** Phase 9 — item 1 done (tools migrated from archive/server/tools/ to pi/tools/)

---

## Status

Full architectural redesign in progress. The original server+Pi split architecture has been superseded. A new spec and plan have been written for a fully Pi-based system (Pi 5 8GB + AI HAT+ 2).

**Spec:** `.project/active/pi-redesign/spec.md`
**Plan:** `plan.md` (completely replaced — all old phases 1-7 complete and archived)

Phase 9 item 1 is complete.

**Item 1:** Copy tools from `archive/server/tools/` into `pi/tools/` (done 2026-06-18):
- 9 tool files copied: androidtv.py, calendar.py, cta.py, google_auth.py, music_profile.py, music_recommendations.py, spotify.py, tasks.py, weather.py
- All `server.tools.*` → `pi.tools.*` imports updated
- `server.llm.client.OllamaClient` → `pi.llm.hailo_client.HailoLLMClient` (constructor: `cfg.ollama` → `cfg.hailo`)
- `ToolRegistry.load()` updated to scan `pi.tools` (built-ins) + `tools.generated` (AI-created)
- `_discover_tools` skips `base` module to prevent reload issues
- All 10 files parse cleanly; 136 existing tests pass

**Next:** Phase 9 item 2 — verify all 7 tools end-to-end with mocked external APIs; all smoke tests pass under new import paths.

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
