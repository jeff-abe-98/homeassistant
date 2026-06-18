# Current Work

**Last updated:** 2026-06-18
**Phase:** Phase 9 — all items complete

---

## Status

Full architectural redesign complete. The original server+Pi split architecture has been superseded. All phases 1–9 are done.

**Spec:** `.project/active/pi-redesign/spec.md`
**Plan:** `plan.md` (completely replaced — all phases 1-9 complete)

Phase 9 items 1–4 are complete.

**Item 4:** Full end-to-end smoke test (done 2026-06-18):
- `tests/test_phase9_e2e.py` created with 4 tests:
  - `test_tool_registry_discovers_pi_tools` — all 10 migrated tools found by ToolRegistry.load()
  - `test_weather_tool_end_to_end` — WeatherTool with mocked httpx + LLM through _handle_activation
  - `test_cta_tool_end_to_end` — CTATool with mocked httpx + LLM through _handle_activation
  - `test_main_loop_single_activation` — full main() loop with one-shot WakeWordDetector, all hardware mocked, TTS + player called
- All 390 tests pass, 18 skipped

**Next:** All plan items complete. No unchecked items remain. Physical Pi deployment pending.

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
