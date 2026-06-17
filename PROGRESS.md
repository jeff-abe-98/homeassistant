# Agent Progress Log

Most recent run at top.

---

## [2026-06-17 UTC]
**Completed:** Phase 7 item 1 — `pi/scheduler/heatmap.py` (build_heatmap, find_low_usage_windows, has_enough_data) + `pi/scheduler/schedule_writer.py` (write_schedule + _git_push + main entry point) + systemd timer pair (`deploy/homeassistant-scheduler.service` + `deploy/homeassistant-scheduler.timer`)
**Files changed:** pi/scheduler/heatmap.py, pi/scheduler/schedule_writer.py, deploy/homeassistant-scheduler.service, deploy/homeassistant-scheduler.timer, plan.md, PROGRESS.md, .project/CURRENT_WORK.md, INBOX.md
**Next up:** Phase 7 item 2 — Smoke tests: heatmap aggregation, window finding, default before data, schedule.json format
**Blockers:** None
---

## [2026-06-17 UTC]
**Completed:** Phase 6 item 3 — smoke tests for offline detection + sync with mocked git (`tests/test_github_sync.py`): 19 tests covering is_online (TCP success/OSError/timeout/custom args) and sync (empty queue, JSON content, marks pushed, count, multiple files, git call ordering, rollback on add/commit/push failure and timeout, pending-only filter); Phase 6 fully complete
**Files changed:** tests/test_github_sync.py, plan.md, PROGRESS.md, .project/CURRENT_WORK.md, INBOX.md
**Next up:** Phase 7 item 1 — `pi/scheduler/heatmap.py` + `pi/scheduler/schedule_writer.py` + default schedule + systemd timer
**Blockers:** None
---

## [2026-06-17 UTC]
**Completed:** Phase 6 item 2 — `pi/tool_requests/github_sync.py` (is_online() TCP DNS check, sync() writes {id}.json files, git add/commit/push, marks pushed, rolls back on failure) + `pi/main.py` integration (_is_capability_gap() heuristic, _handle_capability_gap() priority dialogue → enqueue → sync/offline reminder, ToolRequestQueue wired into main loop); 30 tests pass
**Files changed:** pi/tool_requests/github_sync.py, pi/main.py, plan.md, PROGRESS.md, .project/CURRENT_WORK.md, INBOX.md
**Next up:** Phase 6 item 3 — Smoke tests: offline detection, sync with mocked git
**Blockers:** None
---

## [2026-06-16 UTC]
**Completed:** Phase 6 item 1 — `pi/tool_requests/models.py` (ToolRequest Pydantic model: UUID id, timestamp, intent, user_query, speaker, priority, status, context, error) + `pi/tool_requests/queue.py` (ToolRequestQueue: SQLite WAL, enqueue, get_pending priority-sorted, get_highest_priority, mark_pushed/complete/failed, get_unannounced_complete, mark_announced); 20 smoke tests pass
**Files changed:** pi/tool_requests/models.py, pi/tool_requests/queue.py, tests/test_tool_requests.py, plan.md, PROGRESS.md, .project/CURRENT_WORK.md, INBOX.md
**Next up:** Phase 6 item 2 — `pi/tool_requests/github_sync.py` + integrate into `pi/main.py`
**Blockers:** None
---

## [2026-06-16 UTC]
**Completed:** Phase 5 item 2 — End-to-end smoke tests for unified main loop: 10 tests in `tests/test_main_e2e.py` (tool call, fallback, empty transcript, broken tool, unknown tool, new tool announcement, memory persistence, activation logging, per-speaker identity); `conftest.py` updated with hardware stubs (pyaudio, webrtcvad, sounddevice, resemblyzer, openwakeword, piper) so all Pi modules load without hardware
**Files changed:** tests/test_main_e2e.py, conftest.py, plan.md, PROGRESS.md, .project/CURRENT_WORK.md, INBOX.md
**Next up:** Phase 6 item 1 — `pi/tool_requests/models.py` + `pi/tool_requests/queue.py`
**Blockers:** None
---

## [2026-06-16 UTC]
**Completed:** Phase 5 item 1 — Unified `pi/main.py`: wake-word loop → capture → STT+speaker_id concurrent → log_activation → Session → LLM route → tool/fallback → new-tool announcement → save turn → TTS+play; `pi/tools/base.py` (BaseTool+ToolRegistry scanning tools.generated); `tools/__init__.py` + `tools/generated/__init__.py` created; `pi/client.py` deleted; 57 tests pass
**Files changed:** pi/main.py, pi/tools/__init__.py, pi/tools/base.py, tools/__init__.py, tools/generated/__init__.py, plan.md, PROGRESS.md, .project/CURRENT_WORK.md, INBOX.md
**Next up:** Phase 5 item 2 — End-to-end smoke test (mocked STT + LLM + tool → full loop)
**Blockers:** None
---

## [2026-06-16 UTC]
**Completed:** Phase 4 item 2 — Smoke tests for memory module: 20 tests covering init_db, WAL mode, Session lifecycle (start/turn/end), get_context_turns ordering/limit/most-recent, persistence across simulated restart, activation logging
**Files changed:** tests/test_memory.py, plan.md, PROGRESS.md, .project/CURRENT_WORK.md, INBOX.md
**Next up:** Phase 5 item 1 — `pi/main.py` unified async main loop
**Blockers:** None
---

## [2026-06-16 UTC]
**Completed:** Phase 4 item 1 — Conversation Memory: init_db() (sessions/turns/activations tables, WAL mode), Session class (start/add_turn/end/get_context_turns), log_activation(); context turns format compatible with ToolRouter.route() context_turns param
**Files changed:** pi/memory/db.py, pi/memory/session.py, plan.md, PROGRESS.md, .project/CURRENT_WORK.md, INBOX.md
**Next up:** Phase 4 item 2 — Smoke tests: session lifecycle, context retrieval, persistence across simulated restart, activation logging
**Blockers:** None
---

## [2026-06-16 UTC]
**Completed:** Phase 3 — HailoRT STT Client: research doc + hailo_transcriber.py (hailo_platform.genai.Speech2Text; PCM int16→float32; lazy load; empty string on failure) + 17 smoke tests passing
**Files changed:** .project/research/hailo-whisper.md, pi/stt/hailo_transcriber.py, tests/test_hailo_stt.py, requirements-pi.txt, conftest.py, plan.md, PROGRESS.md, .project/CURRENT_WORK.md, INBOX.md
**Next up:** Phase 4 item 1 — pi/memory/db.py + pi/memory/session.py + activation logging + context injection
**Blockers:** None
---

## [2026-06-15 UTC]
**Completed:** Phase 2 complete — HailoRT LLM Client: research doc + hailo_client.py + router.py + prompts.py + 20 smoke tests all passing
**Files changed:** .project/research/hailo-llm.md, pi/llm/hailo_client.py, pi/llm/router.py, pi/llm/prompts.py, tests/test_hailo_llm.py, plan.md, PROGRESS.md, .project/CURRENT_WORK.md, INBOX.md
**Next up:** Phase 3 item 1 — Research Hailo Whisper Python API (hailo-ai/hailo-whisper)
**Blockers:** None
---

## [2026-06-15 UTC]
**Completed:** Phase 2 prerequisite — created `install-hailo-drivers.sh` (installs `hailo-h10-all`, enables PCIe Gen 3); Hailo-10H confirmed detected on PCIe; hardware blocker resolved
**Files changed:** install-hailo-drivers.sh, plan.md
**Next up:** Run install script + reboot, then Phase 2 item 1 — Research Hailo GenAI Python API
**Blockers:** None (driver install pending reboot)
---

## [2026-06-15 UTC]
**Completed:** Phase 1 complete — items 6/7/8: shared/config.py (HailoConfig, MemoryConfig, ToolRequestConfig; removed server-only configs), config/settings.yaml (hailo/memory/tool_requests sections; removed server/ollama/whisper), tool_requests/ directories + .gitignore rules
**Files changed:** shared/config.py, config/settings.yaml, tool_requests/pending/.gitkeep, tool_requests/complete/.gitkeep, .gitignore, plan.md
**Next up:** Phase 2 item 1 — Research Hailo GenAI Python API for LLM inference
**Blockers:** Hailo research required before implementation; physical AI HAT+ 2 not yet purchased
---

## [2026-06-15 UTC]
**Completed:** Phase 1 item 5 — updated requirements-pi.txt: removed websockets, added hailo runtime entries (commented — not on PyPI), added all tool deps from requirements-server.txt
**Files changed:** requirements-pi.txt, plan.md
**Next up:** Phase 1 item 6 — Update `shared/config.py`
**Blockers:** None
---

## [2026-06-15 UTC]
**Completed:** Phase 1 item 4 — created pi/llm/, pi/stt/, pi/memory/, pi/tool_requests/, pi/scheduler/ with __init__.py files
**Files changed:** pi/llm/__init__.py, pi/stt/__init__.py, pi/memory/__init__.py, pi/tool_requests/__init__.py, pi/scheduler/__init__.py, plan.md
**Next up:** Phase 1 item 5 — Update `requirements-pi.txt`
**Blockers:** None
---

## [2026-06-15 UTC]
**Completed:** Phase 1 item 3 — archived `server/` to `archive/server/` via git mv (history preserved); updated .gitignore
**Files changed:** archive/server/* (26 files renamed), .gitignore, plan.md
**Next up:** Phase 1 item 4 — Create `pi/llm/`, `pi/stt/`, `pi/memory/`, `pi/tool_requests/`, `pi/scheduler/` directories with `__init__.py` files
**Blockers:** None
---

## [2026-06-15 UTC]
**Completed:** Phase 1 item 2 — updated `docs/technical-stack.md` for Pi-only architecture (HailoRT + Hailo GenAI replaces Ollama + faster-whisper; server section removed; remote tool-builder agent section added; project structure updated)
**Files changed:** docs/technical-stack.md, plan.md
**Next up:** Phase 1 item 3 — Archive `server/` to `archive/server/`
**Blockers:** None
---

## [2026-06-15 UTC]
**Completed:** Phase 1 item 1 — updated `docs/parts-list.md` for Pi-only architecture (Pi 5 + AI HAT+ 2 + USB mic, ~$270 total; server section removed; PCIe conflict note + Hailo setup notes added)
**Files changed:** docs/parts-list.md, plan.md, INBOX.md, .project/CURRENT_WORK.md
**Next up:** Phase 1 item 2 — Update `docs/technical-stack.md` (HailoRT replaces Ollama + Faster Whisper; remove server stack entries)
**Blockers:** None
---

## [2026-06-01 06:00 UTC]
**Completed:** Session check-in (session 130) — all phases 1–7 complete; inbox empty; no actionable plan items; startup log written
**Files changed:** INBOX.md, PROGRESS.md
**Next up:** Awaiting new user instructions (Phase 2 hardware items blocked on physical Pi)
**Blockers:** Phase 2 enrollment/tests require physical Pi + microphone; Google Auth needs manual Cloud Console setup; CTA/Weather integration tests skip until real API keys set
---

## [2026-06-01 00:00 UTC]
**Completed:** Session check-in (session 129) — all phases 1–7 complete; inbox empty; no actionable plan items; startup log written
**Files changed:** INBOX.md, PROGRESS.md
**Next up:** Awaiting new user instructions (Phase 2 hardware items blocked on physical Pi)
**Blockers:** Phase 2 enrollment/tests require physical Pi + microphone; Google Auth needs manual Cloud Console setup; CTA/Weather integration tests skip until real API keys set
---

## [2026-05-31 21:00 UTC]
**Completed:** Session check-in (session 128) — all phases 1–7 complete; inbox empty; no actionable plan items; startup log written
**Files changed:** INBOX.md, PROGRESS.md
**Next up:** Awaiting new user instructions (Phase 2 hardware items blocked on physical Pi)
**Blockers:** Phase 2 enrollment/tests require physical Pi + microphone; Google Auth needs manual Cloud Console setup; CTA/Weather integration tests skip until real API keys set
---

## [2026-05-31 18:00 UTC]
**Completed:** Session check-in (session 127) — all phases 1–7 complete; inbox empty; no actionable plan items; startup log written
**Files changed:** INBOX.md, PROGRESS.md
**Next up:** Awaiting new user instructions (Phase 2 hardware items blocked on physical Pi)
**Blockers:** Phase 2 enrollment/tests require physical Pi + microphone; Google Auth needs manual Cloud Console setup; CTA/Weather integration tests skip until real API keys set
---

## [2026-05-31 12:00 UTC]
**Completed:** Session check-in (session 126) — all phases 1–7 complete; inbox empty; no actionable plan items; startup log written
**Files changed:** INBOX.md, PROGRESS.md
**Next up:** Awaiting new user instructions (Phase 2 hardware items blocked on physical Pi)
**Blockers:** Phase 2 enrollment/tests require physical Pi + microphone; Google Auth needs manual Cloud Console setup; CTA/Weather integration tests skip until real API keys set
---

## [2026-05-31 06:00 UTC]
**Completed:** Session check-in (session 125) — all phases 1–7 complete; inbox empty; no actionable plan items; startup log written
**Files changed:** INBOX.md, PROGRESS.md
**Next up:** Awaiting new user instructions (Phase 2 hardware items blocked on physical Pi)
**Blockers:** Phase 2 enrollment/tests require physical Pi + microphone; Google Auth needs manual Cloud Console setup; CTA/Weather integration tests skip until real API keys set
---

## [2026-05-31 00:00 UTC]
**Completed:** Session check-in (session 124) — all phases 1–7 complete; inbox empty; no actionable plan items; startup log written
**Files changed:** INBOX.md, PROGRESS.md
**Next up:** Awaiting new user instructions (Phase 2 hardware items blocked on physical Pi)
**Blockers:** Phase 2 enrollment/tests require physical Pi + microphone; Google Auth needs manual Cloud Console setup; CTA/Weather integration tests skip until real API keys set
---

## [2026-05-30 18:00 UTC]
**Completed:** Session check-in (session 123) — all phases 1–7 complete; inbox empty; no actionable plan items; startup log written
**Files changed:** INBOX.md, PROGRESS.md
**Next up:** Awaiting new user instructions (Phase 2 hardware items blocked on physical Pi)
**Blockers:** Phase 2 enrollment/tests require physical Pi + microphone; Google Auth needs manual Cloud Console setup; CTA/Weather integration tests skip until real API keys set
---

## [2026-05-30 12:00 UTC]
**Completed:** Session check-in (session 122) — all phases 1–7 complete; inbox empty; no actionable plan items; startup log written
**Files changed:** INBOX.md, PROGRESS.md
**Next up:** Awaiting new user instructions (Phase 2 hardware items blocked on physical Pi)
**Blockers:** Phase 2 enrollment/tests require physical Pi + microphone; Google Auth needs manual Cloud Console setup; CTA/Weather integration tests skip until real API keys set
---

## [2026-05-30 06:00 UTC]
**Completed:** Session check-in (session 121) — all phases 1–7 complete; inbox empty; no actionable plan items; startup log written
**Files changed:** INBOX.md, PROGRESS.md
**Next up:** Awaiting new user instructions (Phase 2 hardware items blocked on physical Pi)
**Blockers:** Phase 2 enrollment/tests require physical Pi + microphone; Google Auth needs manual Cloud Console setup; CTA/Weather integration tests skip until real API keys set
---

