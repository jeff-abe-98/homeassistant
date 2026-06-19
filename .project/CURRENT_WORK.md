# Current Work

**Last updated:** 2026-06-19
**Phase:** Phase 10 — Documentation & Setup (items 1–4 complete)

---

## Status

Full architectural redesign complete (Phases 1–9). Phase 10 in progress.

**Phase 10 item 4 (done 2026-06-19):**
- Created `scripts/first-run-check.sh`: 7-section preflight script — (1) hailortcli installed + AI HAT+ 2 PCIe detected, (2) no CHANGE_ME placeholders + androidtv IP configured, (3) LLM/STT/TTS model .hef/.onnx files present, (4) Google OAuth credentials + token files, (5) Spotify per-user token files, (6) ≥2 voice profiles enrolled, (7) systemd homeassistant-pi.service + scheduler.timer active. Exits non-zero on any failure; PASS/FAIL lines guide the user to the right docs section.

**Phase 10 item 3 (done 2026-06-19):**
- Created `docs/api-keys-setup.md`: step-by-step instructions for all 5 external credentials — CTA (registration URL + field mapping), OpenWeatherMap (free tier key, 10-min activation note), Google OAuth (4-part guide: Cloud project → enable APIs → OAuth consent + credentials → first-run token flow), Spotify (create app once, dual-user auth, Emily test-user note), Android TV (IP finding, static DHCP, first-time pairing flow). Credential file summary table at the end.

**Phase 10 item 2 (done 2026-06-19):**
- Created `docs/setup-guide.md`: 11-step first-time setup covering OS flash, HailoRT driver install + verification, repo clone, pip install, LLM/STT/TTS model downloads, settings.yaml configuration table, Google OAuth first-run flow, voice enrollment for both users (with device-index tip), systemd service install, test phrases, and optional custom wake word training.

**Phase 10 item 1 (done 2026-06-19):**
- Created `README.md`: project overview, hardware table (~$270 total), quick-start commands, feature table, project structure, doc links, autonomous tool creation walkthrough, config reference.

**Next:** Phase 10 item 5 — `docs/troubleshooting.md`

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
