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
- [x] `pi/scheduler/prewarm.py` — `PrewarmScheduler` reads `schedule.json` heatmap to identify high-usage windows (top 3 by activation count per day); schedules `asyncio` callbacks to call `HailoLLMClient._ensure_loaded()` and `HailoTranscriber._ensure_loaded()` ~5 minutes before each window so first-interaction latency is negligible; no-op before 14 days of data (defers to lazy load); integrate into `pi/main.py` startup *(done 2026-06-18 — PrewarmScheduler: _is_default_schedule checks schedule.json, _top_windows builds heatmap + returns top-3 (day,hour), _schedule_one uses call_later + weekly reschedule, _do_prewarm calls _ensure_loaded sequentially; pi/main.py: loop retrieved at startup, PrewarmScheduler created + started before while loop, cancel() in finally; 17 smoke tests pass)*

---

## Phase 8 — Remote Tool Builder Agent
*Goal: Define the Claude Code scheduled agent that builds tools from queue requests.*

- [x] `.claude/agents/tool-builder.md` — complete agent definition: pull repo; read `schedule.json` and reschedule self via CronDelete + CronCreate; process `tool_requests/pending/` sorted by priority (high→mid→low, FIFO within priority); for each request generate `tools/generated/{name}.py` (BaseTool subclass) + `tools/generated/{name}_instructions.md` (trigger phrases, required/optional params, example queries, spoken response style); move JSON to `tool_requests/complete/` marking complete or failed; git push all changes *(done 2026-06-18 — `.claude/agents/tool-builder.md` created; 5-step run order: git pull → reschedule via CronList/CronDelete/CronCreate from schedule.json → sort pending requests high→mid→low FIFO → generate {name}.py + {name}_instructions.md per request → move JSONs to complete/ → git push)*
- [x] `pi/tool_requests/github_sync.py` — add `pull_completed_tools()`: git pull, scan `tools/generated/` for new `.py` files, register with ToolRegistry, enqueue announcements in SQLite; smoke tests for announcement queue, new file detection, instruction loading into system prompt *(done 2026-06-18 — pull_completed_tools(): git pull --ff-only → scan tool_requests/complete/*.json → mark_complete/failed in queue → registry.load() → return new tool names; 13 new smoke tests, 32 total pass)*

---

## Phase 9 — Tool Migration & Hardening
*Goal: All existing tools verified in new architecture; deploy updated.*

- [x] Copy tools from `archive/server/tools/` into `pi/tools/` (create directory + `__init__.py`); update imports and ToolRegistry scan path; verify all tools import cleanly *(done 2026-06-18 — 9 tool files copied; server.tools.* → pi.tools.*, server.llm.client.OllamaClient → pi.llm.hailo_client.HailoLLMClient, cfg.ollama → cfg.hailo; ToolRegistry.load() updated to scan pi.tools + tools.generated; base module skip added; all 10 files parse cleanly; 136 existing tests pass)*
- [x] Verify all 7 tools end-to-end with mocked external APIs: weather (OpenWeatherMap), CTA, Google Calendar, Google Tasks, Android TV, Spotify, music recommendations — all existing smoke tests must pass under new import paths *(done 2026-06-18 — updated 9 test files: server.tools.* → pi.tools.*, OllamaClient → HailoLLMClient in patch targets; fixed calendar_integration + tasks_integration imports; added collect_ignore for 9 archived-server tests; installed httpx, pydantic, numpy; 386 pass, 18 skipped)*
- [x] Update deploy files: `deploy/homeassistant-pi.service` (ExecStart → `python -m pi.main`; add systemd timer for schedule writer), `deploy/install-pi-service.sh` (remove server steps; add HailoRT + AI HAT+ 2 driver notes), `CLAUDE.md` (remove server/ references) *(done 2026-06-18 — pi.service: Wants=homeassistant-scheduler.timer added; install-pi-service.sh: HailoRT/PCIe prerequisites + write_unit() for all 3 unit files + scheduler timer enable; CLAUDE.md: Pi-only + HailoRT description, archive/server/ note)*
- [x] Full end-to-end smoke test: wake word → STT (mocked) → LLM routing (mocked) → tool execution → TTS (mocked) → all assertions pass *(done 2026-06-18 — `tests/test_phase9_e2e.py`: 4 tests — ToolRegistry discovers all 10 tools, WeatherTool e2e via mocked httpx+LLM, CTATool e2e via mocked httpx+LLM, main() loop single activation with one-shot WakeWordDetector; 390 pass, 18 skipped)*

---

## Phase 10 — Documentation & Setup
*Goal: Make the repository easy to set up for a new Pi from scratch.*

- [x] `README.md` — project overview (what it is, hardware required, quick-start command), links to detailed docs; replace or create top-level README *(done 2026-06-19 — created README.md: overview, hardware table, quick-start, feature table, project structure, doc links, autonomous tool creation explainer, config snippet)*
- [x] `docs/setup-guide.md` — step-by-step first-time Pi setup: flash OS → run `install-hailo-drivers.sh` → clone repo → `pip install -r requirements-pi.txt` → copy and fill out `config/settings.yaml` → enroll voice profiles → enable systemd services via `install-pi-service.sh` *(done 2026-06-19 — 11-step guide: OS flash, HailoRT install, clone, pip, model downloads for LLM+STT+Piper, settings.yaml config table, Google OAuth flow, voice enrollment with device-index tip, systemd install, test phrases, optional custom wake word)*
- [x] `docs/api-keys-setup.md` — where to obtain and how to configure each credential: CTA API key, OpenWeatherMap key, Google OAuth (Calendar + Tasks), Spotify app credentials, Android TV pairing *(done 2026-06-19 — step-by-step for all 5 credentials; credential file summary table; Google OAuth 4-part walkthrough; Spotify dual-user auth flow; Android TV pairing notes)*
- [x] `scripts/first-run-check.sh` — prints a checklist of what's ready vs. missing: HailoRT installed, no CHANGE_ME values in settings.yaml, voice profiles present, systemd units active; exits non-zero if anything is missing *(done 2026-06-19 — 7 check sections: hailortcli+PCIe, CHANGE_ME+androidtv IP, LLM/STT/TTS model files, Google OAuth creds+token, Spotify per-user tokens, voice profiles ≥2, systemd units; exits non-zero on any failure)*
- [x] `docs/troubleshooting.md` — common issues: HailoRT not found, USB mic not detected, wake word not triggering, tool errors, GitHub sync failures *(done 2026-06-20 — 6 sections: HailoRT not found, USB mic not detected, wake word not triggering, tool errors per-integration, GitHub sync failures, general debugging tips)*

---

## Phase 11 — Latency Profiling & Speedup
*Goal: Measure end-to-end response latency, identify the biggest bottlenecks across every stage of the pipeline, and produce a prioritised list of implementation tasks. No code changes until the analysis item.*

- [x] **Profile the audio capture pipeline** — add `time.perf_counter()` timestamps (log at DEBUG level) around: wake-word-event → VAD stream open, each VAD frame loop iteration (capture + is_speech call), VAD silence detection firing, 48 kHz → 16 kHz resample in `_capture_utterance`, total time from wake-word event to returning PCM bytes. Run 10 real utterances and record min/median/max for each stage. Note how much of the 12-second limit is silence at the end vs. actual speech, and how long scipy `resample_poly` takes on the Pi. Document results in `.project/research/latency-audio.md`. *(done 2026-06-24 — timing instrumentation added to `pi/audio/capture.py` and `pi/main.py`; 7 LATENCY log lines emitted at DEBUG level; `.project/research/latency-audio.md` created with measurement tables and procedure; actual measurements require physical Pi hardware)*

- [x] **Profile the inference pipeline** — add timestamps around: speaker-ID (`identify()` in executor), STT `transcribe()` call, LLM `chat_with_tools()` call (distinguish prompt-build vs. generate), tool `run()` call (for weather, CTA, calendar individually), TTS `synthesize()` call, 22050 → 48000 resample inside `AudioPlayer.play()`. Run 5 queries per tool type. Separately measure cold-start (first call per session) vs. warm (subsequent calls) to quantify prewarm value. Document results in `.project/research/latency-inference.md`. *(done 2026-06-24 — 17 LATENCY log lines added across `pi/main.py`, `pi/llm/hailo_client.py`, `pi/stt/hailo_transcriber.py`, `pi/audio/playback.py`, `pi/speaker_id/identify.py`; cold vs warm labelling in LLM, STT, and speaker-ID; `.project/research/latency-inference.md` created with 6-stage measurement tables and expected findings; physical Pi needed for actual timings)*

- [x] **Audit third-party and system overhead** — measure time spent on: PyAudio stream open/close per activation (could be kept open), `scipy.signal.resample_poly` CPU time vs. simple integer decimation (`audio[::3]`) for wake-word and capture resamples, `asyncio.run_in_executor` thread-pool overhead for blocking calls, model `.generate_all()` token budget impact (current `max_tokens=200` — try 100 and 50), Piper TTS model load (it may re-load per call if not cached). Document findings in `.project/research/latency-overhead.md`. *(done 2026-06-24 — 8 new LATENCY log lines across `pi/wake_word/detector.py` (wakeword_stream_open/close), `pi/main.py` (decimation_48k_to_16k, executor_queue_wait ×3), `pi/tts/piper.py` (tts_model_load, tts_synthesize_internal), `pi/llm/hailo_client.py` (max_tokens added to generate log); `_executor_timed()` helper added; `.project/research/latency-overhead.md` created with 5-section measurement tables and hypotheses; physical Pi needed for actual timings)*

- [x] **Analyse findings and rank bottlenecks** — read all three research docs; compute an end-to-end latency budget table (stage → median ms → % of total); rank stages by impact; for each top-5 bottleneck, assess feasibility: is there a drop-in fix, does it require architecture change, or is it hardware-limited? Cross-reference against what users actually perceive (silence timeout dominates perceived wait even if STT is fast). Write conclusions in `.project/research/latency-analysis.md`. No code changes in this item. *(done 2026-06-25 — `.project/research/latency-analysis.md` written; top-5 bottlenecks ranked: silence tail 1200ms #1, tool narration double-LLM #2/#3, STT #4, PyAudio stream open #5; Phase B latency est. 2970ms conversational / 4170ms tool; fixes 1–4 would bring to ~1670ms / ~2470ms; fix order table appended for Phase 12)*

- [x] **Add implementation tasks to plan** — translate the analysis into concrete, sequenced action items and append them as Phase 12 in `plan.md`. Each item must name the specific file(s) to change, the change (e.g. "reduce `silence_duration_ms` from 1200 → 800 in VoiceCapture default", "replace `resample_poly` with `audio[::3]` in detector.py", "stream Piper TTS output to AudioPlayer chunk-by-chunk"), and the expected latency saving from the analysis. Items should be ordered fastest-win-first. *(done 2026-06-25 — Phase 12 appended with 6 tasks ordered fastest-win-first)*

---

## Phase 12 — Latency Speedup Implementation
*Goal: Apply the prioritised fixes from `latency-analysis.md` to bring Phase B latency from ~4170ms → ~2470ms (tool queries) and ~2970ms → ~1670ms (conversational). Ordered fastest-win-first.*

- [x] **Reduce silence tail: `silence_duration_ms` 1200→800** — in `pi/audio/capture.py`, change the `silence_duration_ms` default in `VoiceCapture.__init__()` from 1200 to 800; add `silence_duration_ms` key to `config/settings.yaml` under an `audio:` section and wire it into `AudioConfig` in `shared/config.py` and through to `VoiceCapture`. Expected saving: ~400ms per activation (~17% of Phase B conversational, 10% of tool query). Risk: very short pauses in longer utterances may truncate; 800ms is the safe midpoint. *(done 2026-06-25 — default changed in capture.py; AudioConfig.silence_duration_ms added to shared/config.py and wired in load(); audio.silence_duration_ms: 800 added to settings.yaml; _capture_utterance() and _handle_capability_gap() accept silence_duration_ms param; config.audio.silence_duration_ms passed from _handle_activation)*

- [ ] **Reduce LLM `max_tokens` 200→100** — in `pi/llm/hailo_client.py`, change `max_tokens=200` to `max_tokens=100` in `_generate_sync()`. Tool routing responses are ≤40 tokens; conversational responses rarely exceed 80. Eliminates worst-case generation ceiling at zero quality risk. Expected saving: 0–500ms on long responses; typical saving ~100ms.

- [ ] **Replace `resample_poly` with integer decimation** — in `pi/main.py`, replace `scipy.signal.resample_poly(pcm_48k, 1, 3)` with `pcm_48k[::3]` (simple stride downsample, 48→16 kHz, factor-of-3). Add a one-line comment noting that integer decimation is adequate for Whisper speech input. Expected saving: 10–50ms per activation (minor, but free).

- [ ] **Keep PyAudio streams open permanently** — `pi/wake_word/detector.py`: remove `stream.stop_stream()` + `stream.close()` on wake event; instead drain the ALSA read buffer (read and discard frames) during the VAD capture phase so the buffer doesn't overflow. `pi/audio/capture.py`: add `capture_from_stream(stream, ...)` method (or an optional `stream=` parameter in `_capture_utterance`) that reads from an already-open PyAudio stream instead of calling `PyAudio.open()` each time. `pi/main.py`: open the 48 kHz capture stream once at startup and pass it through to `_capture_utterance`. Expected saving: 100–300ms per activation (fully deterministic ALSA open cost eliminated).

- [ ] **Eliminate second LLM call for tool narration** — `pi/tools/weather.py`, `pi/tools/cta.py`, `pi/tools/calendar.py`: remove the internal `self._llm.complete()` narration call; instead return the raw structured data (plain text or JSON string with facts) from `tool.run()` so the caller can pass it to the LLM. `pi/llm/router.py`: add a `narrate(tool_name: str, raw_data: str, user: str) -> str` method that generates the spoken response in a single continuation of the routing conversation (appending the tool result as a `tool` message). `pi/main.py`: after `tool.run()`, call `router.narrate()` instead of using the tool's own LLM call. Smoke tests: mock the tool result and assert only one `generate_all` call is made. Expected saving: ~900ms per tool query (entire second NPU inference pass eliminated).

- [ ] **Pass VAD-trimmed buffer to Whisper (not full 30s)** — `pi/stt/hailo_transcriber.py`: add optional `max_seconds: float = 30.0` parameter to `transcribe()`; truncate PCM buffer to `pcm[:int(max_seconds * sample_rate)]` before passing to `generate_all_text` (zero-padding is already handled by Hailo). `pi/main.py`: compute actual utterance duration from PCM length and pass `max_seconds=min(10, actual_seconds + 1)`. Expected saving: TBD — requires measurement on physical hardware; potentially 100–400ms if Hailo Whisper processes proportionally to chunk length rather than always running full 30s context.

---

## Blockers Log

| Date | Phase | Blocker | Status |
|------|-------|---------|--------|
| 2026-06-07 | Phase 2 | HailoRT Python API details require research before implementation — agent must read Hailo GenAI GitHub before writing hailo_client.py | Resolved 2026-06-15 — research complete, hailo_client.py implemented |
| 2026-06-07 | Phase 3 | Hailo Whisper Python API requires research — agent must read hailo-ai/hailo-whisper before writing hailo_transcriber.py | Resolved 2026-06-15 — research complete, hailo_transcriber.py implemented |
| 2026-06-07 | All | Physical Pi + AI HAT+ 2 not yet purchased — all Hailo runtime code must be written against mocked HailoRT; real hardware testing deferred | Resolved 2026-06-15 — hardware arrived, drivers installed |
