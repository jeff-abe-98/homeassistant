# Implementation Plan — Pi-Only Redesign

**Last updated:** 2026-06-15
**Spec:** `.project/active/pi-redesign/spec.md`
**Agent instructions:** Read this file at the start of every session. Find the first unchecked item in the current phase. Implement it. Check it off with a brief note. Stop when the phase is complete or you hit a blocker.

---

## Phase 1 — Documentation & Repo Restructure
*Goal: Update all docs and restructure the repo before writing new code. No implementation yet.*

- [x] Update `docs/parts-list.md` — replace old hardware list with: Pi 5 8GB (~$80), AI HAT+ 2 (~$130), USB microphone (~$20), A2-rated microSD 64GB (~$15), 27W USB-C PSU + case (~$25); total ~$270; note PCIe conflict prevents ReSpeaker HAT + AI HAT+ 2 simultaneously *(done 2026-06-15 — server section removed, Hailo setup notes added)*
- [x] Update `docs/technical-stack.md` — HailoRT replaces Ollama + Faster Whisper; unified Pi process replaces server+client split; remove all server-specific stack entries; add HailoRT, Hailo GenAI suite, Hailo-compiled Whisper base *(done 2026-06-15 — server section removed, HailoRT + remote agent sections added, project structure updated)*
- [x] Archive `server/` — move entire `server/` directory to `archive/server/` so existing tool implementations are preserved for reference during migration; update `.gitignore` if needed *(done 2026-06-15 — git mv preserves history; gitignore updated)*
- [x] Create `pi/llm/`, `pi/stt/`, `pi/memory/`, `pi/tool_requests/`, `pi/scheduler/` directories with `__init__.py` files *(done 2026-06-15)*
- [x] Update `requirements-pi.txt` — add `hailort`, `hailo-tappas`, remove `websockets` client dep; keep all tool deps (spotipy, googleapiclient, androidtvremote2, etc.) *(done 2026-06-15 — hailo packages noted as comments since not on PyPI; all tool deps added from requirements-server.txt)*
- [x] Update `shared/config.py` — remove `WhisperConfig` and any server-only config; add `HailoConfig` (model paths for LLM and STT), `MemoryConfig` (session timeout, context turns), `ToolRequestConfig` (queue db path, github sync interval) *(done 2026-06-15 — ServerConfig, OllamaConfig, WhisperConfig removed; HailoConfig, MemoryConfig, ToolRequestConfig added)*
- [x] Update `config/settings.yaml` — add `hailo:` section (llm_model_path, stt_model_path), `memory:` section (session_timeout_seconds, context_turns), `tool_requests:` section (db_path, sync_interval_seconds); remove server-only keys *(done 2026-06-15)*
- [x] Create `tool_requests/pending/` and `tool_requests/complete/` directories in repo root with `.gitkeep` files; add `tool_requests/pending/*.json` to `.gitignore` except `.gitkeep` *(done 2026-06-15)*

---

## Phase 2 — HailoRT LLM Client
*Goal: Replace Ollama with a HailoRT-based LLM client that exposes the same interface.*

- [x] Install Hailo AI HAT+ 2 PCIe driver (`hailo-h10-all`) on Pi; enable PCIe Gen 3 in `/boot/firmware/config.txt` *(done 2026-06-15 — `install-hailo-drivers.sh` created; hardware confirmed detected via lspci)*
- [x] Research Hailo GenAI Python API for LLM inference — read Hailo docs/GitHub, document findings in `.project/research/hailo-llm.md`: import path, model loading, chat completion API, streaming support, available compiled models (Llama 3.2 1B/3B, Qwen3 1.7B), recommended model for tool routing on 3B *(done 2026-06-15 — `.project/research/hailo-llm.md` written; direct hailo_platform.genai API documented; no 3B model available on Hailo-10H — max is Qwen3-1.7B; Qwen2-1.5B-Instruct-Function-Calling-v1 recommended for tool routing)*
- [x] `pi/llm/hailo_client.py` — `HailoLLMClient` with `async chat(messages: list) -> str` and `async complete(system: str, user: str) -> str` matching the old `OllamaClient` interface; loads Hailo-compiled model from path in config; handles runtime errors gracefully *(done 2026-06-15 — lazy hailo_platform import; LLMError/LLMTimeoutError; ToolMessage/ToolCallItem/ToolFunction mirror Ollama Message interface; tool schemas injected into system prompt for Qwen2 function-calling format)*
- [x] `pi/llm/router.py` — `ToolRouter` using `HailoLLMClient`; `route(transcript, user) -> tuple[ToolCall | None, str]` returns tool call + fallback text (same contract as existing `server/llm/router.py`); uses tool `function_schemas()` from ToolRegistry *(done 2026-06-15 — ToolRegistryLike Protocol; accepts optional context_turns for memory injection)*
- [x] `pi/llm/prompts.py` — `build_system_prompt(user, context_turns, tool_instructions)`: injects speaker name, recent memory turns, and any loaded `_instructions.md` content from generated tools; tuned for 3B model (concise, structured) *(done 2026-06-15 — loads tools/generated/*_instructions.md; concise persona tuned for 1.5B model)*
- [x] Smoke tests for `HailoLLMClient` and `ToolRouter` with mocked HailoRT runtime *(done 2026-06-15 — 20 tests pass in tests/test_hailo_llm.py)*

---

## Phase 3 — HailoRT STT Client
*Goal: Replace Faster Whisper with Hailo-compiled Whisper base.*

- [x] Research Hailo Whisper Python API (`hailo-ai/hailo-whisper` GitHub) + implement `pi/stt/hailo_transcriber.py` (`HailoTranscriber` with `transcribe(pcm_bytes: bytes, sample_rate: int) -> str`, lazy hailo_platform import, empty string on failure) + smoke tests with mocked HailoRT; document findings in `.project/research/hailo-whisper.md` *(done 2026-06-16 — uses hailo_platform.genai.Speech2Text; lazy VDevice+STT load; PCM int16→float32 via numpy; 17 smoke tests pass; numpy added to requirements-pi.txt; conftest.py updated to allow real numpy)*

---

## Phase 4 — Conversation Memory
*Goal: SQLite-backed session memory with context injection into LLM prompt.*

- [x] `pi/memory/db.py` + `pi/memory/session.py` + activation logging + context injection — `init_db(path)` creates `sessions`, `turns`, `activations` tables; `Session` class with `start(speaker)`, `add_turn(transcript, response)`, `end()`, `get_context_turns(n) -> list[dict]`; activation rows written on every wake word detection; `get_context_turns` output wired into `build_system_prompt` *(done 2026-06-16 — WAL SQLite; log_activation(); Session lifecycle; get_context_turns returns chronological role/content dicts compatible with ToolRouter.route() context_turns param)*
- [x] Smoke tests: session lifecycle (start/turn/end), context retrieval, persistence across simulated restart, activation logging *(done 2026-06-16 — 20 tests pass in tests/test_memory.py; covers init_db, WAL, session start/turn/end, context ordering/limit/most-recent, cross-restart persistence, activation logging)*

---

## Phase 5 — Unified Main Loop
*Goal: Single `pi/main.py` replaces both old `pi/main.py` and `server/main.py`.*

- [x] `pi/main.py` — unified async main loop: load config → init HailoRT (LLM + STT) → load ToolRegistry → start WakeWordDetector → on detection: log activation, start session, capture audio (VAD), run STT, load memory context, route via LLM, execute tool or LLM response, save turn, TTS + playback; include new-tool announcement ("By the way, I can now [X]") and failed-tool notification on each activation; delete `pi/client.py` *(done 2026-06-16 — tools/generated/ package created; pi/tools/base.py with BaseTool+ToolRegistry; pi/client.py deleted; 57 tests pass)*
- [x] End-to-end smoke test: mocked STT + LLM + mocked tool → verify full loop runs without error *(done 2026-06-16 — 10 tests in tests/test_main_e2e.py cover tool call path, fallback path, empty transcript short-circuit, broken tool recovery, unknown tool fallback, new tool announcement, memory persistence, activation logging, and per-speaker identity; conftest.py updated with pyaudio/webrtcvad/sounddevice/resemblyzer/openwakeword/piper stubs)*

---

## Phase 6 — Tool Request Queue
*Goal: Local SQLite queue for tool creation requests, with GitHub sync and offline resilience.*

- [x] `pi/tool_requests/models.py` + `pi/tool_requests/queue.py` — `ToolRequest` Pydantic model (id UUID, timestamp, intent, user_query, speaker, priority low/mid/high, status pending/pushed/complete/failed, context list, error); `ToolRequestQueue` SQLite-backed with `enqueue`, `get_pending`, `get_highest_priority`, `mark_pushed/complete/failed`, `get_unannounced_complete`, `mark_announced` *(done 2026-06-16 — 20 smoke tests pass in tests/test_tool_requests.py)*
- [x] `pi/tool_requests/github_sync.py` + integrate into `pi/main.py` — `sync()` writes pending JSON files, git push; `is_online()` DNS check; wire into main: no-tool-match → priority dialogue ("Is this more or less urgent than [X]?") → enqueue → sync or queue offline reminder ("I'll remember that for when I'm back online") *(done 2026-06-17 — github_sync.py: is_online() TCP DNS check, sync() writes {id}.json + git add/commit/push, marks pushed; main.py: _is_capability_gap() heuristic, _handle_capability_gap() priority dialogue + enqueue + sync, ToolRequestQueue wired into _handle_activation and main())*
- [x] Smoke tests: enqueue/dequeue, priority ordering, offline detection, sync with mocked git *(done 2026-06-17 — 19 tests in tests/test_github_sync.py: is_online success/failure/timeout/custom-args, sync empty queue, writes JSON, content matches, marks pushed, returns count, multiple files, git call order, rollback on add/commit/push failure, rollback on timeout, only syncs pending)*

---

## Phase 7 — Usage Heatmap & Schedule System
*Goal: Pi drives the remote agent's schedule based on real activation history.*

- [x] `pi/scheduler/heatmap.py` + `pi/scheduler/schedule_writer.py` + default schedule + systemd timer — `build_heatmap` aggregates activations by (day_of_week, hour); `find_low_usage_windows` returns lowest-count hour per day; `write_schedule` serialises to `schedule.json` and git pushes if changed; `has_enough_data` gates on 14+ days; default `{"default": true, "hour": 3, "minute": 0}` before enough data; systemd timer unit runs `python -m pi.scheduler.schedule_writer` daily *(done 2026-06-17 — heatmap.py: build_heatmap, find_low_usage_windows, has_enough_data; schedule_writer.py: write_schedule + _git_push + main(); deploy/homeassistant-scheduler.service + .timer created)*
- [x] Smoke tests: heatmap aggregation, window finding, default before data, schedule.json format *(done 2026-06-17 — 27 tests in tests/test_scheduler.py; covers has_enough_data, build_heatmap counts/conversion/aggregation, find_low_usage_windows 7 entries/tie-break, write_schedule default+windows JSON format, unchanged skip, git push gating)*
- [ ] `pi/scheduler/prewarm.py` — `PrewarmScheduler` reads `schedule.json` heatmap to identify high-usage windows (top 3 by activation count per day); schedules `asyncio` callbacks to call `HailoLLMClient._ensure_loaded()` and `HailoTranscriber._ensure_loaded()` ~5 minutes before each window so first-interaction latency is negligible; no-op before 14 days of data (defers to lazy load); integrate into `pi/main.py` startup

---

## Phase 8 — Remote Tool Builder Agent
*Goal: Define the Claude Code scheduled agent that builds tools from queue requests.*

- [ ] `.claude/agents/tool-builder.md` — complete agent definition: pull repo; read `schedule.json` and reschedule self via CronDelete + CronCreate; process `tool_requests/pending/` sorted by priority (high→mid→low, FIFO within priority); for each request generate `tools/generated/{name}.py` (BaseTool subclass) + `tools/generated/{name}_instructions.md` (trigger phrases, required/optional params, example queries, spoken response style); move JSON to `tool_requests/complete/` marking complete or failed; git push all changes
- [ ] `pi/tool_requests/github_sync.py` — add `pull_completed_tools()`: git pull, scan `tools/generated/` for new `.py` files, register with ToolRegistry, enqueue announcements in SQLite; smoke tests for announcement queue, new file detection, instruction loading into system prompt

---

## Phase 9 — Tool Migration & Hardening
*Goal: All existing tools verified in new architecture; deploy updated.*

- [ ] Copy tools from `archive/server/tools/` into `pi/tools/` (create directory + `__init__.py`); update imports and ToolRegistry scan path; verify all tools import cleanly
- [ ] Verify all 7 tools end-to-end with mocked external APIs: weather (OpenWeatherMap), CTA, Google Calendar, Google Tasks, Android TV, Spotify, music recommendations — all existing smoke tests must pass under new import paths
- [ ] Update deploy files: `deploy/homeassistant-pi.service` (ExecStart → `python -m pi.main`; add systemd timer for schedule writer), `deploy/install-pi-service.sh` (remove server steps; add HailoRT + AI HAT+ 2 driver notes), `CLAUDE.md` (remove server/ references)
- [ ] Full end-to-end smoke test: wake word → STT (mocked) → LLM routing (mocked) → tool execution → TTS (mocked) → all assertions pass

---

## Blockers Log

| Date | Phase | Blocker | Status |
|------|-------|---------|--------|
| 2026-06-07 | Phase 2 | HailoRT Python API details require research before implementation — agent must read Hailo GenAI GitHub before writing hailo_client.py | Resolved 2026-06-15 — research complete, hailo_client.py implemented |
| 2026-06-07 | Phase 3 | Hailo Whisper Python API requires research — agent must read hailo-ai/hailo-whisper before writing hailo_transcriber.py | Resolved 2026-06-15 — research complete, hailo_transcriber.py implemented |
| 2026-06-07 | All | Physical Pi + AI HAT+ 2 not yet purchased — all Hailo runtime code must be written against mocked HailoRT; real hardware testing deferred | Resolved 2026-06-15 — hardware arrived, drivers installed |
