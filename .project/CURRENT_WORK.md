# Current Work

**Last updated:** 2026-06-19
**Phase:** Phase 10 — Documentation & Setup (just added)

---

## Status

Full architectural redesign complete (Phases 1–9). Session 152 processed inbox:

**Wake word training script bug fixes (done 2026-06-19):**
- `_load_positives`: `np.stack([])` would crash before `main()` error check — fixed with empty array guard
- `_load_negatives_from_dir`: same empty-list crash — fixed
- `_download_negatives`: same empty-list crash — fixed
- `_train()`: `best_state=None` if `--epochs 0` — fixed by initializing from model state before the loop

**Phase 10 added to `plan.md`** (5 items: README, setup guide, API keys guide, first-run-check script, troubleshooting guide)

**Next:** Phase 10 item 1 — `README.md`

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
