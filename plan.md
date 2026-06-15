# Implementation Plan — Pi-Only Redesign

**Last updated:** 2026-06-07
**Spec:** `.project/active/pi-redesign/spec.md`
**Agent instructions:** Read this file at the start of every session. Find the first unchecked item in the current phase. Implement it. Check it off with a brief note. Stop when the phase is complete or you hit a blocker.

---

## Phase 1 — Documentation & Repo Restructure
*Goal: Update all docs and restructure the repo before writing new code. No implementation yet.*

- [x] Update `docs/parts-list.md` — replace old hardware list with: Pi 5 8GB (~$80), AI HAT+ 2 (~$130), USB microphone (~$20), A2-rated microSD 64GB (~$15), 27W USB-C PSU + case (~$25); total ~$270; note PCIe conflict prevents ReSpeaker HAT + AI HAT+ 2 simultaneously *(done 2026-06-15 — server section removed, Hailo setup notes added)*
- [ ] Update `docs/technical-stack.md` — HailoRT replaces Ollama + Faster Whisper; unified Pi process replaces server+client split; remove all server-specific stack entries; add HailoRT, Hailo GenAI suite, Hailo-compiled Whisper base
- [ ] Archive `server/` — move entire `server/` directory to `archive/server/` so existing tool implementations are preserved for reference during migration; update `.gitignore` if needed
- [ ] Create `pi/llm/`, `pi/stt/`, `pi/memory/`, `pi/tool_requests/`, `pi/scheduler/` directories with `__init__.py` files
- [ ] Update `requirements-pi.txt` — add `hailort`, `hailo-tappas`, remove `websockets` client dep; keep all tool deps (spotipy, googleapiclient, androidtvremote2, etc.)
- [ ] Update `shared/config.py` — remove `WhisperConfig` and any server-only config; add `HailoConfig` (model paths for LLM and STT), `MemoryConfig` (session timeout, context turns), `ToolRequestConfig` (queue db path, github sync interval)
- [ ] Update `config/settings.yaml` — add `hailo:` section (llm_model_path, stt_model_path), `memory:` section (session_timeout_seconds, context_turns), `tool_requests:` section (db_path, sync_interval_seconds); remove server-only keys
- [ ] Create `tool_requests/pending/` and `tool_requests/complete/` directories in repo root with `.gitkeep` files; add `tool_requests/pending/*.json` to `.gitignore` except `.gitkeep`

---

## Phase 2 — HailoRT LLM Client
*Goal: Replace Ollama with a HailoRT-based LLM client that exposes the same interface.*

- [ ] Research Hailo GenAI Python API for LLM inference — read Hailo docs/GitHub, document findings in `.project/research/hailo-llm.md`: import path, model loading, chat completion API, streaming support, available compiled models (Llama 3.2 1B/3B, Qwen3 1.7B), recommended model for tool routing on 3B
- [ ] `pi/llm/hailo_client.py` — `HailoLLMClient` with `async chat(messages: list) -> str` and `async complete(system: str, user: str) -> str` matching the old `OllamaClient` interface; loads Hailo-compiled model from path in config; handles runtime errors gracefully
- [ ] `pi/llm/router.py` — `ToolRouter` using `HailoLLMClient`; `route(transcript, user) -> tuple[ToolCall | None, str]` returns tool call + fallback text (same contract as existing `server/llm/router.py`); uses tool `function_schemas()` from ToolRegistry
- [ ] `pi/llm/prompts.py` — `build_system_prompt(user, context_turns, tool_instructions)`: injects speaker name, recent memory turns, and any loaded `_instructions.md` content from generated tools; tuned for 3B model (concise, structured)
- [ ] Smoke tests for `HailoLLMClient` and `ToolRouter` with mocked HailoRT runtime

---

## Phase 3 — HailoRT STT Client
*Goal: Replace Faster Whisper with Hailo-compiled Whisper base.*

- [ ] Research Hailo Whisper Python API — read `hailo-ai/hailo-whisper` GitHub; document in `.project/research/hailo-whisper.md`: import path, model loading, transcribe API, expected input format (16kHz PCM), output format
- [ ] `pi/stt/hailo_transcriber.py` — `HailoTranscriber` with `transcribe(pcm_bytes: bytes, sample_rate: int) -> str` matching old `WhisperTranscriber` interface; loads Hailo-compiled Whisper base from config path; returns empty string on failure
- [ ] Smoke tests for `HailoTranscriber` with mocked HailoRT runtime

---

## Phase 4 — Conversation Memory
*Goal: SQLite-backed session memory with context injection into LLM prompt.*

- [ ] `pi/memory/db.py` — `init_db(path)`: creates `sessions` (id, started_at, ended_at, speaker), `turns` (id, session_id, speaker, transcript, response, timestamp), `activations` (id, timestamp, wake_word) tables; returns connection
- [ ] `pi/memory/session.py` — `Session` class: `start(speaker)`, `add_turn(transcript, response)`, `end()`, `get_context_turns(n) -> list[dict]`; session ended by silence timeout or explicit call; auto-commits to SQLite
- [ ] Wire activation logging: every wake word detection writes a row to `activations` table with timestamp
- [ ] Context injection: `get_context_turns(n)` output formatted as `[{"role": "user", "content": ...}, {"role": "assistant", "content": ...}]` and passed into `build_system_prompt`
- [ ] Smoke tests: session lifecycle (start/turn/end), context retrieval, persistence across simulated restart, activation logging

---

## Phase 5 — Unified Main Loop
*Goal: Single `pi/main.py` replaces both old `pi/main.py` and `server/main.py`.*

- [ ] `pi/main.py` — unified async main loop: load config → init HailoRT (LLM + STT) → load ToolRegistry → start WakeWordDetector → on detection: log activation, start session, capture audio (VAD), run STT, load memory context, route via LLM, execute tool or use LLM response, save turn, run TTS + playback → check new-tool announcement queue before responding
- [ ] New-tool announcement: on each wake word activation, check SQLite for unannounced completed tools; if any, prepend "By the way, I can now [X] — want to try it?" to response
- [ ] Failed-tool notification: check for failed tool builds; notify user once then mark notified
- [ ] Remove WebSocket client (`pi/client.py`) — delete or archive
- [ ] End-to-end smoke test: mocked STT + LLM + mocked tool → verify full loop runs without error

---

## Phase 6 — Tool Request Queue
*Goal: Local SQLite queue for tool creation requests, with GitHub sync and offline resilience.*

- [ ] `pi/tool_requests/models.py` — `ToolRequest` Pydantic model: `id` (UUID), `timestamp` (ISO-8601), `intent` (str), `user_query` (str), `speaker` (str), `priority` (Literal["low","mid","high"]), `status` (Literal["pending","pushed","complete","failed"]), `context` (list[str]), `error` (str | None)
- [ ] `pi/tool_requests/queue.py` — `ToolRequestQueue`: SQLite-backed; `enqueue(request)`, `get_pending() -> list[ToolRequest]`, `get_highest_priority() -> ToolRequest | None`, `mark_pushed(id)`, `mark_complete(id)`, `mark_failed(id, error)`, `get_unannounced_complete() -> list[ToolRequest]`, `mark_announced(id)`
- [ ] `pi/tool_requests/github_sync.py` — `sync()`: git pull to check for completed tools, write pending requests as JSON files to `tool_requests/pending/`, git add + commit + push; `is_online() -> bool` (attempt DNS lookup); retry loop for offline state
- [ ] Integrate into `pi/main.py`: when LLM detects no tool match → check queue for highest priority → ask user relative priority if queue non-empty → `queue.enqueue()` → `sync()` (or defer if offline, set reminder)
- [ ] User priority dialogue: LLM asks "Is this more or less urgent than [highest priority item description]?" → user responds → set priority accordingly
- [ ] Offline message: "I'll remember that for when I'm back online" when `is_online()` returns False
- [ ] Smoke tests: enqueue/dequeue, offline detection, sync logic with mocked git

---

## Phase 7 — Usage Heatmap & Schedule System
*Goal: Pi drives the remote agent's schedule based on real activation history.*

- [ ] `pi/scheduler/heatmap.py` — `build_heatmap(db_path) -> dict`: query `activations` table, aggregate by (day_of_week 0-6, hour 0-23), return count matrix; `find_low_usage_windows(heatmap) -> dict[int, int]`: for each day of week return the hour with lowest activation count (minimum 2h window)
- [ ] `pi/scheduler/schedule_writer.py` — `write_schedule(windows, repo_path)`: serialise windows to `schedule.json` in repo root, git add + commit + push only if content changed; `has_enough_data(db_path) -> bool`: True if 14+ days of activations exist
- [ ] Default schedule: if `has_enough_data()` is False, write `schedule.json` with `{"default": true, "hour": 3, "minute": 0}` (3am daily)
- [ ] Daily cron on Pi: systemd timer or cron job that runs `python -m pi.scheduler.schedule_writer` once per day
- [ ] Smoke tests: heatmap aggregation, window finding, default before data, schedule.json format

---

## Phase 8 — Remote Tool Builder Agent
*Goal: Define the Claude Code scheduled agent that builds tools from queue requests.*

- [ ] Create `.claude/agents/tool-builder.md` — agent definition with full instructions:
  - Clone/pull repo at start of run
  - Read `schedule.json`; call CronDelete + CronCreate to reschedule self for next optimal window
  - Read all JSON files in `tool_requests/pending/` sorted by priority (high→mid→low), FIFO within same priority
  - For each request: generate `tools/generated/{tool_name}.py` (BaseTool subclass) + `tools/generated/{tool_name}_instructions.md` (when to use, parameters, response style for small LLM)
  - Mark request complete: move JSON to `tool_requests/complete/`, update status field
  - On failure: set status=failed + error field, move to `tool_requests/complete/`
  - git add + commit + push all changes
- [ ] Instruction prompt format spec in `.claude/agents/tool-builder.md`: each `_instructions.md` MUST include: trigger phrases, required parameters, optional parameters, example user queries, suggested response style (concise spoken language)
- [ ] `pi/tool_requests/github_sync.py` — add `pull_completed_tools()`: git pull, scan `tools/generated/` for new `.py` files, register with ToolRegistry, add to announcement queue in SQLite
- [ ] Smoke tests: announcement queue, new file detection, instruction prompt loading into system prompt

---

## Phase 9 — Tool Migration & Hardening
*Goal: All existing tools verified in new architecture; deploy updated.*

- [ ] Copy tools from `archive/server/tools/` to `server/tools/` (or `pi/tools/` — follow whatever path ToolRegistry scans after restructure); verify imports work in new layout
- [ ] Verify weather tool end-to-end (mocked OpenWeatherMap)
- [ ] Verify CTA tool end-to-end (mocked CTA API)
- [ ] Verify Google Calendar tool end-to-end (mocked Google API)
- [ ] Verify Google Tasks tool end-to-end (mocked Google API)
- [ ] Verify Android TV tool end-to-end (mocked androidtvremote2)
- [ ] Verify Spotify tool end-to-end (mocked spotipy)
- [ ] Verify music recommendations tool end-to-end (mocked Spotify + SQLite)
- [ ] Update `deploy/homeassistant-pi.service` — point ExecStart to unified `python -m pi.main`; add systemd timer unit for daily schedule writer
- [ ] Update `deploy/install-pi-service.sh` — remove server install steps; add AI HAT+ 2 driver setup notes; add HailoRT install steps
- [ ] Update `CLAUDE.md` — revise any workflow steps that reference server/ or old architecture
- [ ] Full end-to-end smoke test: wake word → STT (mocked) → LLM routing (mocked) → tool execution → TTS (mocked) → all assertions pass

---

## Blockers Log

| Date | Phase | Blocker | Status |
|------|-------|---------|--------|
| 2026-06-07 | Phase 2 | HailoRT Python API details require research before implementation — agent must read Hailo GenAI GitHub before writing hailo_client.py | Pending research |
| 2026-06-07 | Phase 3 | Hailo Whisper Python API requires research — agent must read hailo-ai/hailo-whisper before writing hailo_transcriber.py | Pending research |
| 2026-06-07 | All | Physical Pi + AI HAT+ 2 not yet purchased — all Hailo runtime code must be written against mocked HailoRT; real hardware testing deferred | Hardware not yet ordered |
