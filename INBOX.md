# Inbox

Edit this file directly in GitHub to communicate with the development agent.
The agent reads this at the start of every run.

---

## Open Questions
*Decisions or info needed before the agent can proceed. Agent will check these off when resolved, or note why it's blocked.*

<!-- Example: - [ ] What should the wake word be? -->

## Ideas & Improvements
*New features, changes to existing features, or improvements. Agent will triage these into plan.md and check them off.*
 - [x] Seeing as we are blocked by getting the pi setup, we sjould do the parts list as the next step. move it from its current spot in phase 6 to the top of the todo list. initially i was rhinking a pi 5 and a ReSpeaker 2-Mic Pi HAT *(moved up in plan.md and implemented — `docs/parts-list.md` created; Pi 5 8 GB + ReSpeaker 2-Mic Pi HAT + accessories ~$130–140; server GPU upgrade RTX 4060 Ti 16 GB + PSU ~$500–550; includes driver notes)*
 - [x] Make sure that when you are reading this at start up, you are also writing here. *(added to plan.md Phase 6)*
 - [x] Add a parts list. this should be split into parts for the Pi, and parts for the server. *(added to plan.md Phase 6)*

## Notes
*Anything else — reminders, context, thoughts.*

<!-- Example: Emily's Spotify account is premium, mine is not yet -->

---

## Agent Startup Log
*The agent writes a brief status note here at the start of each session.*

### 2026-06-18 (session 149)
**Status:** Phase 9 items 1–2 done; implementing Phase 9 item 3 — update deploy files (pi.service, install-pi-service.sh) and CLAUDE.md
**Next task:** Phase 9 item 4 — full end-to-end smoke test
**Blockers:** None

### 2026-06-18 (session 148)
**Status:** Phase 9 item 1 done (tools migrated); implementing Phase 9 item 2 — verify all 7 tools smoke tests pass under new pi.tools.* import paths
**Next task:** Phase 9 item 3 — update deploy files
**Blockers:** None

### 2026-06-18 (session 147)
**Status:** Phase 8 complete; implementing Phase 9 item 1 — copy tools from archive/server/tools/ into pi/tools/ with updated imports
**Next task:** Phase 9 item 2 — verify all 7 tools end-to-end with mocked external APIs
**Blockers:** None

### 2026-06-18 (session 146)
**Status:** Phase 8 item 1 done — `.claude/agents/tool-builder.md` agent definition; implementing Phase 8 item 2 — `pull_completed_tools()` in `pi/tool_requests/github_sync.py`
**Next task:** Phase 8 item 2 — `pull_completed_tools()` + smoke tests
**Blockers:** None

### 2026-06-17 (session 145)
**Status:** Phase 7 complete; implementing Phase 8 item 1 — `.claude/agents/tool-builder.md` agent definition
**Next task:** Phase 8 item 1 — `.claude/agents/tool-builder.md`
**Blockers:** None

### 2026-06-18 (session 144)
**Status:** Phase 7 item 3 done — `pi/scheduler/prewarm.py` (PrewarmScheduler) + `pi/main.py` integration; 17 smoke tests pass
**Next task:** Phase 8 item 1 — `.claude/agents/tool-builder.md` agent definition
**Blockers:** None

### 2026-06-17 (session 143)
**Status:** Phase 7 item 2 done (27 smoke tests for scheduler: heatmap, windows, write_schedule)
**Next task:** Phase 7 item 3 — `pi/scheduler/prewarm.py` + integrate into `pi/main.py`
**Blockers:** None

### 2026-06-17 (session 142)
**Status:** Phase 6 complete; starting Phase 7 item 1 — heatmap.py + schedule_writer.py + systemd timer
**Next task:** Phase 7 item 1 — `pi/scheduler/heatmap.py` + `pi/scheduler/schedule_writer.py` + default schedule + systemd timer
**Blockers:** None

### 2026-06-17 (session 141)
**Status:** Phase 6 item 3 done (smoke tests: offline detection + sync with mocked git, 19 tests); Phase 6 complete
**Next task:** Phase 7 item 1 — `pi/scheduler/heatmap.py` + `pi/scheduler/schedule_writer.py` + default schedule + systemd timer
**Blockers:** None

### 2026-06-17 (session 140)
**Status:** Phase 6 item 1 done (models + queue); implementing Phase 6 item 2 — github_sync.py + main.py integration
**Next task:** Phase 6 item 3 — Smoke tests: offline detection, sync with mocked git
**Blockers:** None

### 2026-06-16 (session 139)
**Status:** Phase 5 complete; starting Phase 6 — Tool Request Queue (models + SQLite-backed queue)
**Next task:** Phase 6 item 1 — `pi/tool_requests/models.py` + `pi/tool_requests/queue.py`
**Blockers:** None

### 2026-06-16 (session 138)
**Status:** Phase 5 item 1 done; implementing Phase 5 item 2 — end-to-end smoke tests for unified main loop
**Next task:** Phase 5 item 2 — End-to-end smoke test (mocked STT + LLM + tool → full loop)
**Blockers:** None

### 2026-06-16 (session 137)
**Status:** Phase 4 complete; starting Phase 5 — unified `pi/main.py` main loop
**Next task:** Phase 5 item 1 — rewrite `pi/main.py` as unified async loop; create `pi/tools/base.py` ToolRegistry; delete `pi/client.py`
**Blockers:** None

### 2026-06-16 (session 136)
**Status:** Phase 4 complete — implementing Phase 4 item 2 (smoke tests for memory module)
**Next task:** Phase 5 item 1 — `pi/main.py` unified async main loop
**Blockers:** None

### 2026-06-16 (session 135)
**Status:** Phase 3 complete; starting Phase 4 — Conversation Memory; first item is db.py + session.py + activation logging
**Next task:** Phase 4 item 1 — `pi/memory/db.py` + `pi/memory/session.py` + activation logging + context injection
**Blockers:** None

### 2026-06-16 (session 134)
**Status:** Phase 2 complete; starting Phase 3 — HailoRT STT Client; first item combines research + implementation + tests in one task
**Next task:** Phase 3 item 1 — Research Hailo Whisper API + implement `pi/stt/hailo_transcriber.py` + smoke tests
**Blockers:** None

### 2026-06-15 (session 133)
**Status:** Phase 1 complete; drivers installed; starting Phase 2 item 1 — research Hailo GenAI Python API for LLM inference
**Next task:** Phase 2 item 1 — document Hailo GenAI API in `.project/research/hailo-llm.md`
**Blockers:** None

### 2026-06-15 (session 132)
**Status:** Phase 1 complete; hardware arrived — Hailo-10H detected on PCIe; created `install-hailo-drivers.sh` to install `hailo-h10-all` and enable PCIe Gen 3
**Next task:** Phase 2 item 1 — Research Hailo GenAI Python API (after driver reboot verified)
**Blockers:** None

### 2026-06-15 (session 131)
**Status:** Pi-only redesign Phase 1 starting; first unchecked item is updating docs/parts-list.md with new hardware (Pi 5 + AI HAT+ 2, no server).
**Next task:** Phase 1 item 1 — Update `docs/parts-list.md`.
**Blockers:** No GitHub PAT in session prompt — git push will need manual push or PAT provided.

### 2026-06-01 (session 130)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-06-01 (session 129)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-31 (session 128)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-31 (session 127)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-31 (session 126)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-31 (session 125)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-31 (session 124)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-30 (session 123)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-30 (session 122)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-30 (session 121)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-30 (session 120)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-29 (session 119)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-29 (session 118)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-29 (session 117)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-29 (session 116)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-29 (session 115)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-28 (session 114)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-28 (session 113)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-28 (session 112)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-28 (session 111)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-27 (session 110)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-27 (session 109)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-27 (session 108)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-27 (session 107)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-26 (session 106)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-26 (session 105)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-26 (session 104)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-26 (session 103)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-26 (session 102)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-25 (session 101)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-25 (session 100)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-25 (session 99)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-25 (session 98)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-24 (session 97)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-24 (session 96)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-24 (session 95)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-24 (session 94)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-24 (session 93)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-23 (session 92)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-23 (session 91)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-23 (session 90)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-23 (session 89)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-22 (session 88)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-22 (session 87)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-22 (session 86)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-22 (session 85)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-22 (session 84)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-21 (session 83)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-21 (session 82)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-21 (session 81)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-21 (session 80)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-21 (session 79)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-20 (session 78)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-20 (session 77)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-20 (session 76)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-20 (session 75)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-19 (session 74)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-19 (session 73)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-19 (session 72)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-19 (session 71)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-18 (session 70)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-18 (session 69)
**Status:** All phases 1–7 complete; inbox empty; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-18 (session 68)
**Status:** All phases 1–7 complete; no new inbox items; no actionable plan items remain (Phase 2 hardware-blocked).
**Next task:** No unchecked plan items — Phase 2 enrollment/tests require physical Pi + microphone.
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-18 (session 67)
**Status:** All phases 1–7 complete. Last done: Phase 7 voice interface — `MusicRecommendationTool` auto-discovered by ToolRegistry, trigger phrases wired, 21 recommendation tests pass.
**Next task:** No unchecked plan items remain (Phase 2 hardware-blocked items require physical Pi).
**Blockers:** Phase 2 enrollment + speaker-ID tests require physical Pi + microphone; Google Auth needs manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-18 (session 66)
**Status:** Phase 7 in progress. Last done: recommendation engine (`server/tools/music_recommendations.py` — `MusicRecommendationTool`, `_recommend`, `_cold_start`). Implementing voice interface: "Play something I'd like" → recommendation-driven playlist.
**Next task:** Phase 7 — Voice interface: "Play something I'd like" → recommendation-driven playlist
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-17 (session 65)
**Status:** Phase 7 in progress. Last done: listening history collection (`server/tools/music_profile.py` — `record_play`, `record_skip`, `build_profile`). Implementing recommendation engine (`server/tools/music_recommendations.py`).
**Next task:** Phase 7 — Recommendation engine (collaborative filtering or embedding-based)
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-17 (session 64)
**Status:** Phase 7 in progress. Last done: designed the per-user taste model (`docs/music-recommendations.md`). Now implementing listening history collection: `server/tools/music_profile.py` (SQLite plays table, `record_play`, `record_skip`, `build_profile`).
**Next task:** Phase 7 — Listening history collection from Spotify API
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-17 (session 63)
**Status:** Phase 6 complete. Starting Phase 7 (Music Recommendations) — first item: design the per-user taste model.
**Next task:** Phase 7 — Design per-user taste model (`docs/music-recommendations.md`)
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-17 (session 62)
**Status:** Phase 6 in progress. Implementing last unchecked Phase 6 item: formalizing the agent startup check-in by creating `CLAUDE.md` with all agent workflow steps (startup log write, inbox processing, plan execution, PROGRESS.md update, commit/push).
**Next task:** Phase 6 complete — Phase 7 (Music Recommendations) or user-directed work.
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-16 (session 61)
**Status:** Phase 6 in progress. Latency profiling — eliminated 3-LLM-call-per-conversational-request bottleneck: `ToolRouter.route()` now returns `(ToolCall | None, str)` — the fallback text from `chat_with_tools` is reused directly as the conversational reply (no separate `_llm.complete` call); replaced `_needs_new_tool` LLM classifier with `_heuristic_needs_tool()` keyword check; added `time.perf_counter()` timing logs for STT, routing, and tool steps; result: conversational requests go from 3 LLM calls → 1; tool requests unchanged; 282 tests pass (18 skipped).
**Next task:** Phase 6 — Agent startup check-in (last unchecked Phase 6 item).
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-16 (session 60)
**Status:** Phase 6 in progress. Tuned wake word sensitivity: added `min_activation_count` (consecutive 80ms frames required before trigger; default 3 ≈ 240ms) and `cooldown_seconds` (suppress re-trigger; default 2.0) to `WakeWordConfig`; updated detector and `config/settings.yaml`; 14 new tests pass, 281 total.
**Next task:** Phase 6 — Latency profiling — identify and fix slow spots in the pipeline.
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-16 (session 59)
**Status:** Phase 6 in progress. Implemented logging: `LoggingConfig` in `shared/config.py`; `server/logging_config.py` with `setup_logging(cfg)` (RotatingFileHandler 10 MB/5 backups + StreamHandler, `timestamp | LEVEL | name | message` format); wired into `server/main.py` lifespan; `logging:` section in `config/settings.yaml`; 9 new tests pass, 266 total.
**Next task:** Phase 6 — Wake word false positive rate — tune sensitivity.
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-16 (session 58)
**Status:** Phase 6 in progress. Implemented error handling: `LLMTimeoutError`/`LLMError` in `OllamaClient` (asyncio.wait_for, 30s configurable timeout); `server/main.py` wraps router, `tool.run()`, `_needs_new_tool`, and `_llm.complete()` in try/except — friendly messages returned, server never crashes; STT failure returns None; WebSocket loop handles JSON decode errors; active session tracking cleans up orphaned audio buffers on client disconnect; 15 new tests pass.
**Next task:** Phase 6 — Logging: structured logs to file with rotation.
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-15 (session 57)
**Status:** Phase 6 in progress. Created `deploy/homeassistant-pi.service` — systemd unit (Type=simple, After=network-online.target sound.target, Restart=on-failure, RestartSec=5s, StartLimitBurst=5, journald logging, entry point `python -m pi.main`); `deploy/install-pi-service.sh` — creates service user, adds it to audio group (PyAudio mic + sounddevice output), rsyncs project, creates venv + installs requirements-pi.txt, substitutes install path + user into unit file, enables + starts service.
**Next task:** Phase 6 — Error handling: graceful recovery from LLM timeout, API failures, network drop.
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-15 (session 56)
**Status:** Phase 6 in progress. Created `deploy/homeassistant-server.service` — systemd unit (Type=simple, User=homeassistant, WorkingDirectory, uvicorn ExecStart, Restart=on-failure, RestartSec=5s, StartLimitBurst=5, journald logging); `deploy/install-server-service.sh` — creates system user, rsyncs project, creates venv + installs requirements, substitutes install path + user into unit file, enables + starts service.
**Next task:** Phase 6 — Systemd service for Pi client (auto-start on boot).
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-15 (session 55)
**Status:** Phase 5 complete. Wrote `tests/test_tool_creator_e2e.py` — end-to-end test: novel request returns "I don't know how to do that yet" immediately; background pipeline (generator→validator subprocess→installer) completes; tool appears in registry + file on disk + WebSocket "I can do that now" notification sent; second request routed to new tool returns its output; 1 new test, 55 tool-creator tests pass total.
**Next task:** Phase 6 — Systemd service for server (auto-start, auto-restart).
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-15 (session 54)
**Status:** Phase 5 in progress. Integrated tool creator into `server/main.py` — `_needs_new_tool(text)` LLM binary classifier; `_create_and_notify(transcript, websocket)` background task (generate → validate → install → send "I can do that now"); `_handle_transcript` updated with websocket param; user notification returned immediately when new tool is needed; completion notification sent via WebSocket after install; 13 smoke tests pass. Also checked off user + completion notification plan items as they were implemented in the same change.
**Next task:** Phase 5 — Test: ask for something novel → tool is created and works on second request.
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-15 (session 53)
**Status:** Phase 5 in progress. Created `server/tool_creator/installer.py` — `InstallResult` dataclass; `_safe_module_name` sanitises tool name to snake_case module filename; `install(source, tool_name, registry)` writes source to `server/tools/generated/<name>.py`, force-reloads module if previously imported, finds concrete BaseTool subclass, calls `registry.register(tool)`; handles overwrite; 15 smoke tests pass.
**Next task:** Phase 5 — Integrate tool creator into main request flow (if no tool matches intent → trigger tool creator).
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-14 (session 52)
**Status:** Phase 5 in progress. Created `server/tool_creator/validator.py` — `ValidationResult` dataclass; `validate(source, timeout)` static-import-checks then spawns subprocess that loads the tool, instantiates it, verifies name/description/parameters, calls `run({}, "test_user")`, confirms str return; tools returning error strings (e.g. "API key not configured") are valid. 11 smoke tests; 214 total pass.
**Next task:** Phase 5 — `server/tool_creator/installer.py` — write validated tool to `tools/generated/`, register it.
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-14 (session 51)
**Status:** Phase 5 in progress. Created `server/tool_creator/sandbox.py` — `ALLOWED_IMPORTS` frozenset; `check_imports(source)` static AST walk for disallowed modules; `SandboxResult` dataclass; `run_in_sandbox(source, timeout)` spawns subprocess with CPU (5s) and memory (256MB) limits via `resource.setrlimit` preexec_fn, wall-clock timeout via `asyncio.wait_for`. 18 new smoke tests; 203 total pass, 18 skipped.
**Next task:** Phase 5 — `server/tool_creator/validator.py` — run generated tool with test inputs, check for errors.
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-14 (session 50)
**Status:** Phase 5 started. Created `server/tool_creator/generator.py` — `ToolGenerator.generate(intent, existing_tool_names)` prompts OllamaClient with a system prompt showing the BaseTool interface; strips markdown fences; validates syntax via `ast.parse`; retries up to 3× with error message injected; raises ValueError after max retries. 15 new smoke tests; 185 total pass, 18 skipped.
**Next task:** Phase 5 — `server/tool_creator/sandbox.py` — subprocess runner with resource limits and import allowlist.
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-14 (session 49)
**Status:** Phase 4 complete. Created `tests/test_spotify_integration.py` — two integration tests: Owner "Play jazz" (verifies owner account, search→playlist, start_playback with TV device ID) and Emily "Play my Discover Weekly" (verifies emily account, user playlist lookup, start_playback with correct URI); both skip when credentials are CHANGE_ME; 170 smoke pass, 2 new skipped. Also fixed pytest environment (pyyaml + httpx).
**Next task:** Phase 5 — Autonomous Tool Creation — `server/tool_creator/generator.py`.
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware; Android TV and Spotify integration tests skip until real devices/credentials configured.

### 2026-05-14 (session 48)
**Status:** Phase 4 in progress. Implemented Spotify playback controls — `pause` (`sp.pause_playback()`), `skip` (`sp.next_track()`), `previous` (`sp.previous_track()`), `volume` (`sp.volume(level)` with 0–100 clamping, error message if level not provided); 7 new smoke tests; 61 spotify tests, 170 total pass.
**Next task:** Phase 4 — Spotify — Test: Owner says "Play some jazz" → plays on TV through Owner's account.
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware; Android TV integration tests skip until real TV host configured.

### 2026-05-13 (session 47)
**Status:** Phase 4 in progress. Implemented Spotify search-and-play — `_find_user_playlist` (pagination, case-insensitive, strips "my " prefix), `_search_spotify` (personal hints→user playlists, mood/genre→catalog playlist, specific queries→track), `_search_and_play` (calls `sp.start_playback`); `_ensure_tv_ready` factored out of `_ensure_playing_on_tv`; `play` action uses search when `query` param present; 19 new tests; 54 spotify tests, 163 total pass.
**Next task:** Phase 4 — Spotify — Controls: pause, skip, volume.
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware; Android TV integration tests skip until real TV host configured.

### 2026-05-13 (session 46)
**Status:** Phase 4 in progress. Implemented combined Spotify+TV launch flow — `_find_tv_device_id(sp)` (always fresh, never cached), `_launch_spotify_on_tv(atv_cfg)` (androidtvremote2 LEANBACK_LAUNCHER intent), `_ensure_playing_on_tv(sp, cfg)` (launch best-effort → poll devices() 1s/15s → transfer_playback force_play); `play` action wired; 15 new smoke tests, 35 spotify tests pass (144 total).
**Next task:** Phase 4 — Spotify — Play by song / artist / playlist / mood query.
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware; Android TV integration tests skip until real TV host configured.

### 2026-05-13 (session 45)
**Status:** Phase 4 in progress. Created `server/tools/spotify.py` — spotipy OAuth2 per user; `_is_configured()`, `_get_spotify()` (SpotifyOAuth with token cache, open_browser=False), `SpotifyTool` per-user routing + `now_playing` action; `SpotifyUserConfig` extended with `redirect_uri` and `token_file`; `spotipy>=2.24.0` added to requirements; 20 smoke tests pass; pytest env fixed (httpx + pytest-asyncio reinstalled via uv).
**Next task:** Phase 4 — Spotify — Combined launch flow (androidtv launches Spotify → poll `sp.devices()` → transfer playback to TV).
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware; Android TV integration tests skip until real TV host configured.

### 2026-05-13 (session 44)
**Status:** Phase 4 in progress. Created `tests/test_androidtv_integration.py` — 3 integration tests for "Put on Netflix" flow (correct Netflix package, case-insensitive name, disconnect-on-error); all skip when androidtv.host is placeholder; 24 smoke tests + 3 skipped pass.
**Next task:** Phase 4 — Spotify — `server/tools/spotify.py` (spotipy OAuth2 per user, Owner + Emily separate accounts).
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware; Android TV integration tests skip until real TV host configured.

### 2026-05-13 (session 43)
**Status:** Phase 4 in progress. Added media key events to `server/tools/androidtv.py` — `_KEYCODE_MEDIA_PLAY/PAUSE/NEXT/PREVIOUS` constants; `play`, `pause`, `next`, `previous` actions in `AndroidTvTool`; 4 new smoke tests; 24 androidtv tests pass.
**Next task:** Phase 4 — Android TV — Test: "Put on Netflix" → Netflix opens on TV.
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware.

### 2026-05-12 (session 42)
**Status:** Phase 4 in progress. Implemented `launch_app` action in `server/tools/androidtv.py` — `_APP_PACKAGES` dict (10 apps), `_resolve_package()` (friendly name or raw package), `_launch_intent()` (LEANBACK_LAUNCHER intent URI); `AndroidTvTool` extended with `launch_app` action + optional `app` parameter; calls `atv.send_launch_app()`; 11 new smoke tests; 105 total pass, 13 skipped.
**Next task:** Phase 4 — Android TV — Send media key events (play, pause, next, previous).
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware.

### 2026-05-12 (session 41)
**Status:** Phase 4 started. Implemented `server/tools/androidtv.py` — `androidtvremote2` connection infrastructure; `_connect()` (cert auto-generate + async_connect); `AndroidTvTool` power_on/power_off with KEYCODE_WAKEUP/SLEEP; guards unconfigured host; cert paths added to `AndroidTvConfig`; `androidtvremote2>=0.1.1` in requirements; 9 new smoke tests; 94 total pass, 13 skipped.  
**Next task:** Phase 4 — Android TV — launch app by package name (Spotify, Netflix, YouTube).  
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware.

### 2026-05-12 (session 40)
**Status:** Phase 3 complete. Added 2 integration tests to `tests/test_tasks_integration.py` — "Mark oat milk as done" flow for Owner and Emily; both verify `tasks().patch()` uses correct per-user list ID and `body={"status": "completed"}`; auto-skip without Google credentials; 85 smoke tests pass.  
**Next task:** Phase 4 — Android TV — `server/tools/androidtv.py` (`androidtvremote2` connection to TV).  
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware.

### 2026-05-12 (session 39)
**Status:** Phase 3 in progress. Added 2 integration tests to `tests/test_tasks_integration.py` — "What's on my list?" flow for Owner and Emily; both verify `tasks().list()` targets the correct per-user list ID and passes `showCompleted=False`; LLM is mocked; auto-skip without Google credentials; 32 smoke tests pass.  
**Next task:** Phase 3 — Google Tasks — Test: "Mark oat milk as done" → completes the item.  
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware.

### 2026-05-11 (session 38)
**Status:** Phase 3 in progress. Created `tests/test_tasks_integration.py` — two integration tests verifying "add oat milk to my list" routes to the correct per-user task list (Owner → Owner list, Emily → Emily list); both auto-skip without Google credentials; 32 smoke tests still pass.  
**Next task:** Phase 3 — Google Tasks — Test: "What's on my list?" → reads back incomplete items.  
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware.

### 2026-05-11 (session 37)
**Status:** Phase 3 in progress. Implemented per-user Google Tasks list routing — `_user_tasklist_id(service, user)` finds a task list by user name (case-insensitive), creates one if not found ("Owner", "Emily"), falls back to first list for unknown; all 3 tools updated; 9 new tests + 32 total pass.  
**Next task:** Phase 3 — Google Tasks — Test: "Add oat milk to my list" → added to correct user's list.  
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware.

### 2026-05-11 (session 36)
**Status:** Phase 3 in progress. Implemented `server/tools/tasks.py` — `AddTaskTool` (add item to default task list), `ListTasksTool` (list incomplete items, LLM narration with user-name injection), `CompleteTaskTool` (case-insensitive name match, patch status to completed); `_default_tasklist_id` + `_find_task_by_title` helpers; 23 smoke tests all pass.  
**Next task:** Phase 3 — Google Tasks — Separate task lists per user ("Owner", "Emily").  
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware.

### 2026-05-11 (session 35)
**Status:** Phase 3 in progress. Added integration test `test_emily_dentist_appointment_created_as_emily_dentist` — verifies Emily dentist flow end-to-end: real dateparser parses "Thursday at 3" → hour=15; Emily prefix applied → summary="Emily Dentist"; mocked Google Calendar insert captures event body for assertions; 29 smoke tests pass, 3 integration tests all skip without credentials.  
**Next task:** Phase 3 — Google Tasks — `server/tools/tasks.py` (add item, list incomplete items, complete item by name).  
**Blockers:** Google Auth blocked on manual Google Cloud Console setup; CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware.

### 2026-05-11 (session 34)
**Status:** Phase 3 in progress. Implemented "reads events for speaking user" — `CalendarTool.run()` now injects the speaker's name into the LLM system prompt for personalized narration; 2 new smoke tests; `tests/test_calendar_integration.py` created with 2 integration tests (owner + Emily, auto-skip without Google credentials); 29 total calendar smoke tests pass.  
**Next task:** Phase 3 — Google Calendar — Test: Emily says "I have a dentist appointment Thursday at 3" → event created as "Emily Dentist".  
**Blockers:** Google Auth blocked on manual Google Cloud Console setup (create project, enable Calendar+Tasks APIs, download OAuth2 Desktop credentials JSON); CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware.

### 2026-05-10 (session 33)
**Status:** Phase 3 in progress. Implemented Emily event auto-prefix in `AddCalendarEventTool.run()` — title prefixed with "Emily " when user is emily and title doesn't already start with "Emily "; 3 new smoke tests (Emily prefix, no-double-prefix, owner no-prefix); 27 total tests pass.  
**Next task:** Phase 3 — Google Calendar — Test: "What do I have tomorrow?" → reads events for speaking user.  
**Blockers:** Google Auth blocked on manual Google Cloud Console setup (create project, enable Calendar+Tasks APIs, download OAuth2 Desktop credentials JSON); CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware.

### 2026-05-10 (session 32)
**Status:** Phase 3 in progress. Implemented `AddCalendarEventTool` in `server/tools/calendar.py` — `add_calendar_event` intent; `_parse_natural_date` via `dateparser` (future-preferring, Chicago TZ); creates event via Calendar API; guards no-title + unparseable-date; 24 smoke tests pass.  
**Next task:** Phase 3 — Google Calendar — Emily events auto-prefixed with "Emily ".  
**Blockers:** Google Auth blocked on manual Google Cloud Console setup (create project, enable Calendar+Tasks APIs, download OAuth2 Desktop credentials JSON); CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware.

### 2026-05-10 (session 31)
**Status:** Phase 3 in progress. Implemented `server/tools/calendar.py` — `CalendarTool` reads events for today/tomorrow/this_week from Google Calendar primary calendar; narrates results via LLM; guards CHANGE_ME/unconfigured states; 14 smoke tests pass.  
**Next task:** Phase 3 — Google Calendar — Add event with natural language date parsing.  
**Blockers:** Google Auth blocked on manual Google Cloud Console setup (create project, enable Calendar+Tasks APIs, download OAuth2 Desktop credentials JSON); CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware.

### 2026-05-10 (session 30)
**Status:** Phase 3 in progress. Implemented Google Auth — `config/google_credentials.json` placeholder skeleton with step-by-step setup instructions; `GoogleConfig` extended with `token_file` + `scopes`; `server/tools/google_auth.py` with `is_configured()`, `get_credentials()`, `build_service()`; added google-auth packages to requirements; 8 smoke tests pass.  
**Next task:** Phase 3 — Google Calendar — `server/tools/calendar.py` (read events for today / date range).  
**Blockers:** Google Auth blocked on manual Google Cloud Console setup (create project, enable Calendar+Tasks APIs, download OAuth2 Desktop credentials JSON); CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware.

### 2026-05-10 (session 29)
**Status:** Phase 3 in progress. Wrote `tests/test_cta_integration.py` — two integration tests (both-direction + O'Hare-only) that auto-skip without a real CTA key; verify live API response structure and direction-aware LLM system prompt. All 11 CTA smoke tests pass.  
**Next task:** Phase 3 — Google Auth — Set up Google Cloud project, enable Calendar API + Tasks API.  
**Blockers:** CTA/Weather integration tests skip until real API keys set; Phase 2 enrollment needs physical Pi hardware.

### 2026-05-09 (session 28)
**Status:** Phase 3 in progress. Registered CTA API key in config — confirmed `CtaConfig` (api_key + stop_id_ohare/forest_park) fully wired; added API registration URL comment to `config/settings.yaml`; all 11 CTA smoke tests pass.  
**Next task:** Phase 3 — "When's the next Blue Line?" integration test (`tests/test_cta_integration.py`).  
**Blockers:** CTA integration test auto-skips until real CTA API key set in config; Phase 2 enrollment needs physical Pi hardware.

### 2026-05-09 (session 27)
**Status:** Processed inbox — created `docs/parts-list.md` (Pi 5 8 GB + ReSpeaker 2-Mic Pi HAT + accessories ~$130–140; server RTX 4060 Ti 16 GB GPU upgrade ~$500–550; ReSpeaker driver install notes included). Item moved from Phase 6 to top of plan and completed.  
**Next task:** Phase 3 — Register CTA API key in config.  
**Blockers:** CTA/Weather integration tests need real API keys; Phase 2 enrollment needs physical Pi hardware.

### 2026-05-08 (session 26)
**Status:** Phase 3 in progress. Enhanced CTA directional handling — `CtaTool.run()` now injects direction-specific context into the LLM system prompt so narration focuses on O'Hare-bound, Forest Park-bound, or both. Added 3 new tests (Forest Park path + system prompt assertions); 11 CTA tests pass.  
**Next task:** Phase 3 — Register CTA API key in config.  
**Blockers:** CTA integration tests need real CTA API key; Phase 2 enrollment/tests need physical Pi hardware.

### 2026-05-08 (session 25)
**Status:** Phase 3 in progress. Implemented `server/tools/cta.py` — `CtaTool` for CTA Blue Line arrivals at Western & Milwaukee; direction param (ohare/forest_park/both); guards CHANGE_ME key; narrates via LLM; 8 smoke tests pass. Also extended `CtaConfig` with `stop_id_ohare`/`stop_id_forest_park` fields.  
**Next task:** Phase 3 — Handle directional queries (O'Hare vs Forest Park) — the `direction` param is already wired; next plan item is to verify/enhance the directional routing logic.  
**Blockers:** CTA tests require real CTA API key; Phase 2 enrollment/tests need physical Pi hardware.

### 2026-05-08 (session 24)
**Status:** Phase 3 in progress. Wrote `tests/test_weather_integration.py` — two integration tests (`test_weather_today_real_api`, `test_weather_forecast_real_api`) that auto-skip when OWM key is CHANGE_ME and exercise the real OWM HTTP layer (mocked LLM) when a real key is present. Existing 5 smoke tests still pass.  
**Next task:** Phase 3 — `server/tools/cta.py` — CTA Train Tracker API, Blue Line, Western & Milwaukee stop.  
**Blockers:** Integration tests skip until real OWM key is set; Phase 2 enrollment/tests need physical Pi hardware.

### 2026-05-08 (session 23)
**Status:** Phase 3 in progress. Completed weather config registration — `WeatherConfig` gains `units` field wired from YAML; `WeatherTool.run()` now uses `cfg.weather.units` and guards `CHANGE_ME` placeholder; `tests/test_weather.py` smoke tests all pass (5/5).  
**Next task:** Phase 3 — "What's the weather today?" integration test (requires real OWM API key in `config/settings.yaml`).  
**Blockers:** Phase 2 enrollment/tests need physical Pi hardware.

### 2026-05-08 (session 22)
**Status:** Phase 3 in progress. Implemented `server/tools/weather.py` — `WeatherTool` fetches current + forecast JSON from OpenWeatherMap in parallel, passes both to LLM for natural narration; registered automatically by `ToolRegistry`.  
**Next task:** Phase 3 — Register OpenWeatherMap API key in config (placeholder already in `config/settings.yaml`; next step is confirming the config key path and writing a smoke test).  
**Blockers:** Phase 2 enrollment/tests need physical Pi hardware.

### 2026-05-07 (session 21)
**Status:** Phase 3 in progress. Updated `server/main.py` — WebSocket handler now wires `ToolRegistry` + `ToolRouter`; `_handle_transcript` tries `_router.route()` first, runs matched tool via `tool.run()`, falls back to plain LLM if no tool selected or found.  
**Next task:** Phase 3 — `server/tools/weather.py` — fetch OpenWeatherMap data, pass raw JSON to LLM for natural narration.  
**Blockers:** Phase 2 enrollment/tests need physical Pi hardware.

### 2026-05-07 (session 20)
**Status:** Phase 3 in progress. Implemented `server/llm/router.py` — `ToolCall` dataclass + `ToolRouter.route()` uses Ollama function calling to select a tool and extract params; added `chat_with_tools` to `OllamaClient`.  
**Next task:** Phase 3 — Update WebSocket handler to run tool router and return tool result.  
**Blockers:** Phase 2 enrollment/tests need physical Pi hardware.

### 2026-05-07 (session 19)
**Status:** Phase 3 in progress. Implemented `server/tools/base.py` — `BaseTool` ABC + `ToolRegistry` with auto-discovery via `pkgutil.iter_modules` and hot-reload support.  
**Next task:** Phase 3 — `server/llm/router.py` — LLM function calling: given transcript + user, select tool + extract params.  
**Blockers:** Phase 2 enrollment/tests still need physical Pi hardware.

### 2026-05-07 (session 18)
**Status:** Phase 2 hardware-blocked. All Phase 2 code is complete; remaining tasks (enroll Owner, enroll Emily, two hardware tests) require physical Pi + microphone and cannot run here. Logged all four in Blockers Log.  
**Next task:** Phase 3 — `server/tools/base.py` (`BaseTool` abstract class + `ToolRegistry`).  
**Blockers:** Phase 2 enrollment/tests need physical Pi hardware.

### 2026-05-07 (session 17)
**Status:** Phase 2 in progress. Updated `server/llm/prompts.py` — `build_system_prompt(user)` injects speaker name when identified (LLM addresses them by name) or unknown-user suffix (ask who they are if personal request). `server/main.py` passes `transcript.user`.  
**Next task:** Enrollment — run enrollment script for Owner (requires Pi hardware; will log as blocker if hardware not available).  
**Blockers:** None.

### 2026-05-06 (session 16)
**Status:** Phase 2 in progress. Integrated speaker ID into `pi/main.py` — PCM buffered during capture, `identify()` runs in executor concurrent with server STT, result attached to Transcript via `model_copy` before sending. Also added `user: str = "unknown"` to `Transcript` in `shared/models.py`.  
**Next task:** Update `server/llm/prompts.py` — inject user name into system prompt for personalization.  
**Blockers:** None.

### 2026-05-06 (session 15)
**Status:** Phase 2 in progress. Implemented `pi/speaker_id/identify.py` — `identify(pcm_bytes, sample_rate)` + `identify_embedding(embedding)`; cosine similarity vs all enrolled profiles; returns best-match name or "unknown" below 0.75 threshold.  
**Next task:** Integrate speaker ID into `pi/main.py` — identify speaker before sending transcript to server.  
**Blockers:** None.

### 2026-05-06 (session 14)
**Status:** Phase 1 complete. Implemented `tests/test_e2e.py` — end-to-end pipeline test; real uvicorn server + real WebSocket client; STT + LLM mocked; `AudioChunk` → `Transcript` → `AssistantResponse` round-trip verified; 1 passed in 0.48 s.  
**Next task:** Phase 2 / `pi/speaker_id/embeddings.py` — generate and save voice embeddings using resemblyzer.  
**Blockers:** None.

### 2026-05-05 (session 13)
**Status:** Phase 1 Pi complete. Implemented `pi/main.py` — async main loop; WakeWordDetector start/stop per utterance; VoiceCapture.stream() bridged to async via background thread + asyncio.Queue; streams AudioChunk to server; receives Transcript, sends for LLM, receives AssistantResponse; TTS + play via run_in_executor.  
**Next task:** End-to-end test: wake word → "what is 2 plus 2" → spoken response.  
**Blockers:** None.

### 2026-05-05 (session 12)
**Status:** Phase 1 Pi in progress. Implemented `pi/client.py` — `AssistantClient` WebSocket client; sends `AudioChunk`/`Transcript`, receives `Transcript`/`AssistantResponse` via per-session `asyncio.Queue`; background listener task; async context manager.  
**Next task:** `pi/main.py` — main loop: wake word → capture → send to server → receive response → TTS → play.  
**Blockers:** None.

### 2026-05-05 (session 11)
**Status:** Phase 1 Pi in progress. Implemented `pi/wake_word/detector.py` — `WakeWordDetector` background thread; 80ms PyAudio frames → openWakeWord scoring → callback on threshold exceeded; `WakeWordConfig` added to shared config.  
**Next task:** `pi/client.py` — WebSocket client connecting to server `/ws`.  
**Blockers:** None.

### 2026-05-05 (session 10)
**Status:** Phase 1 Pi in progress. Implemented `pi/tts/piper.py` — `PiperTTS` wrapping Piper TTS; `synthesize(text) -> bytes` returns raw int16 PCM; `PiperConfig` added to shared config and settings.yaml.  
**Next task:** `pi/wake_word/detector.py` — openWakeWord listener, fires callback on detection.  
**Blockers:** None.

### 2026-05-04 (session 9)
**Status:** Phase 1 Pi in progress. Processed inbox: parts list triaged into plan.md Phase 6.  
**Next task:** `pi/tts/piper.py` — wrap Piper TTS (text in → audio bytes out).  
**Blockers:** None.

### 2026-05-04 (session 7)
**Status:** Phase 1 Pi in progress. Implemented `pi/audio/capture.py` — `VoiceCapture` with PyAudio + webrtcvad; 30ms/16kHz frames; 300ms pre-speech ring; 900ms silence ring; yields `AudioChunk` per frame, final chunk is_final=True.  
**Next task:** `pi/audio/playback.py` — play audio bytes through HDMI output (sounddevice).  
**Blockers:** None.

### 2026-05-04 (session 6)
**Status:** Phase 1 server-side complete. Implemented `_handle_transcript` — Transcript feeds into `_llm.complete(build_system_prompt(), text)` and returns `AssistantResponse`. Full server pipeline is live.  
**Next task:** `pi/audio/capture.py` — mic input with WebRTC VAD.  
**Blockers:** None.

### 2026-05-03 (session 5)
**Status:** Phase 1 in progress. Implemented STT handler — `server/stt/transcriber.py` (WhisperTranscriber) + `_handle_audio_chunk` in main.py buffers AudioChunk stream and transcribes on is_final.  
**Next task:** WebSocket handler: receive `Transcript` → run LLM → return `AssistantResponse`.  
**Blockers:** None.

### 2026-05-03 (session 2)
**Status:** Phase 1 in progress. Created `server/llm/client.py` — async Ollama client wrapper.  
**Next task:** `server/llm/prompts.py` — system prompt for the assistant persona.  
**Blockers:** None.

### 2026-05-03
**Status:** Phase 1 in progress. Created `config/settings.yaml` skeleton with placeholder values for all integrations.  
**Next task:** `server/llm/client.py` — Ollama client wrapper.  
**Blockers:** None.

### 2026-05-02
**Status:** Phase 1 in progress. Processed inbox item: agent startup write-back added to Phase 6 and implemented now.  
**Next task:** `config/settings.yaml` — skeleton config file (no real secrets).  
**Blockers:** None.
