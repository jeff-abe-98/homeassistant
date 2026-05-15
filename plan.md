# Implementation Plan

**Last updated:** 2026-05-02  
**Agent instructions:** Read this file at the start of every session. Find the first unchecked item in the current phase. Implement it. Check it off. Add a brief implementation note. Stop when the phase is complete or you hit a blocker — note the blocker and stop.

---

## Phase 1 — Core Voice Pipeline
*Goal: Wake word → speech captured → transcript returned → spoken response. No tools, no personalization. Just a working voice loop.*

### Server
- [x] Initialize repo structure (`pi/`, `server/`, `shared/`, `config/`) — created all dirs with `__init__.py`; `config/voice_profiles/` with `.gitkeep`
- [x] `requirements-server.txt` with: fastapi, uvicorn, ollama, websockets, faster-whisper, pydantic, httpx, pyyaml — created with pinned minimum versions
- [x] `requirements-pi.txt` with: openWakeWord, pyaudio, webrtcvad, resemblyzer, sounddevice, websockets, pydantic, pyyaml — created with pinned minimum versions
- [x] `shared/models.py` — Pydantic models: `AudioChunk`, `Transcript`, `SpeakerResult`, `AssistantResponse` — created with session_id + sequence/audio_bytes/sample_rate/is_final for AudioChunk; text for Transcript; user+confidence for SpeakerResult; text for AssistantResponse
- [x] `shared/config.py` — load `config/settings.yaml` into dataclasses — `AppConfig` dataclass tree with `load()` function; falls back to defaults if file missing; respects `SETTINGS_PATH` env var
- [x] `config/settings.yaml` — skeleton config file (no real secrets yet) — created with placeholder values for all integrations (Ollama, Whisper, wake word, Google, Spotify x2, CTA, weather, Android TV, users)
- [x] `server/llm/client.py` — Ollama client wrapper (send prompt, return response string) — `OllamaClient` with async `chat(messages)` and `complete(system, user)` methods using `ollama.AsyncClient`
- [x] `server/llm/prompts.py` — system prompt for the assistant persona — `_BASE` constant + `build_system_prompt()` function; plain spoken language, concise, no markdown
- [x] `server/main.py` — FastAPI app with a single `/ws` WebSocket endpoint — FastAPI app with lifespan (loads config, initializes OllamaClient); `/ws` dispatches AudioChunk→`_handle_audio_chunk` and Transcript→`_handle_transcript` stubs
- [x] WebSocket handler: receive `AudioChunk` stream → run STT → return `Transcript` — `server/stt/transcriber.py` (WhisperTranscriber); buffers chunks by session_id, runs on executor on is_final; WhisperConfig added to shared/config.py
- [x] WebSocket handler: receive `Transcript` → run LLM → return `AssistantResponse` — `_handle_transcript` calls `_llm.complete(build_system_prompt(), transcript.text)` and returns `AssistantResponse`

### Pi
- [x] `pi/audio/capture.py` — mic input with WebRTC VAD (start/stop on voice activity) — `VoiceCapture` class; pre-speech ring buffer (300ms), silence ring (900ms); yields `AudioChunk` per 30ms frame; new UUID session_id per utterance; final chunk is_final=True with empty bytes
- [x] `pi/audio/playback.py` — play audio bytes through HDMI output — `AudioPlayer` class wrapping sounddevice; configurable sample_rate/channels/device/dtype; `play()` blocks until done, `stop()` for interruption; 22050 Hz mono int16 default (Piper TTS output format)
- [x] `pi/tts/piper.py` — wrap Piper TTS (text in → audio bytes out) — `PiperTTS` class; deferred `PiperVoice` import; `synthesize(text) -> bytes` returns raw int16 PCM; `sample_rate` property from model config; `PiperConfig` added to shared/config.py and settings.yaml
- [x] `pi/wake_word/detector.py` — openWakeWord listener, fires callback on detection — `WakeWordDetector` class; background thread reads 80ms PyAudio frames at 16kHz; calls `on_detection()` when openWakeWord score >= threshold; `WakeWordConfig` added to `shared/config.py` and wired into `load()`
- [x] `pi/client.py` — WebSocket client connecting to server `/ws` — `AssistantClient` async context manager; `send_audio_chunk`, `send_transcript`, `receive_transcript`, `receive_response`; background listener routes server messages into per-session asyncio queues; optional `on_transcript`/`on_response` callbacks
- [x] `pi/main.py` — main loop: wake word → capture → send to server → receive response → TTS → play — async main(); `WakeWordDetector` starts/stops around each utterance; `VoiceCapture.stream()` fed to server via background thread + asyncio.Queue; `receive_transcript` → `send_transcript` → `receive_response`; TTS + playback via `run_in_executor`

### Testing Phase 1
- [x] End-to-end test: say wake word → ask "what is 2 plus 2" → assistant responds via speaker — `tests/test_e2e.py`; real uvicorn server + real WebSocket client; STT + LLM mocked; verifies AudioChunk→Transcript→AssistantResponse round-trip; 1 passed in 0.48 s

---

## Phase 2 — Speaker Identification
*Goal: Assistant knows who is talking and personalizes responses. Voice enrollment for Owner and Emily.*

- [x] `pi/speaker_id/embeddings.py` — generate and save voice embeddings using resemblyzer — `embed_audio(pcm_bytes, sample_rate)` → 256-d numpy array via `VoiceEncoder.embed_utterance`; `save_embedding`/`load_embedding`/`list_profiles` manage `config/voice_profiles/*.npy`
- [x] `pi/speaker_id/enroll.py` — enrollment script: record 30s of speech, save embedding to `config/voice_profiles/` — CLI script (`enroll <name> [--device INDEX]`); records 30s of raw PCM at 16kHz; prints countdown; calls `embed_audio` + `save_embedding`; run as `python -m pi.speaker_id.enroll owner`
- [x] `pi/speaker_id/identify.py` — compare incoming audio embedding against enrolled profiles, return user name or "unknown" — `identify(pcm_bytes, sample_rate)` + `identify_embedding(embedding)`; cosine similarity (dot product of unit vectors) against all `config/voice_profiles/*.npy`; returns best match name or "unknown" if below threshold (0.75)
- [x] Integrate speaker ID into `pi/main.py` — identify before sending transcript to server — buffers PCM, runs `identify()` in executor concurrently with `receive_transcript()`, attaches result via `model_copy(update={"user": user})` before sending to server
- [x] Update `shared/models.py` — add `user: str` field to `Transcript` — added `user: str = "unknown"` (default "unknown"; Pi overwrites after speaker ID)
- [x] Update `server/llm/prompts.py` — inject user name into system prompt for personalization — `build_system_prompt(user)` appends a known-user line (address by name) or unknown-user line (ask who they are); `server/main.py` passes `transcript.user`
- [ ] Enrollment: run enrollment script for Owner
- [ ] Enrollment: run enrollment script for Emily
- [ ] Test: Owner speaks → response addresses Owner; Emily speaks → response addresses Emily
- [ ] Test: Unknown speaker asks generic question → answered normally; asks personal question → "Who's this?"

---

## Phase 3 — Core Tool Integrations
*Goal: Weather, CTA, Google Calendar, Google Tasks all working.*

### Tool System Foundation
- [x] `server/tools/base.py` — `BaseTool` abstract class and `ToolRegistry` (auto-discovers tools in `tools/`) — `BaseTool` ABC with `name`/`description`/`parameters`/`run`; `ToolRegistry.load()` scans `server.tools` + `server.tools.generated` via `pkgutil.iter_modules`, reloads on hot-reload; `function_schemas()` returns Ollama-compatible dicts; `register()` for installer use
- [x] `server/llm/router.py` — LLM function calling: given transcript + user, select tool + extract params — `ToolCall` dataclass (tool_name + params); `ToolRouter.route(transcript)` builds messages + calls `chat_with_tools` with all registered schemas; returns `ToolCall` if LLM picks a tool, `None` for plain chat fallback; added `chat_with_tools` to `OllamaClient`
- [x] Update WebSocket handler to run tool router and return tool result — `server/main.py`: `ToolRegistry.load()` + `ToolRouter` initialized in lifespan; `_handle_transcript` tries `_router.route()` first, runs matched `tool.run(params, user)`, falls back to plain LLM on no-tool path

### Weather
- [x] `server/tools/weather.py` — fetch OpenWeatherMap data, pass raw JSON to LLM for natural narration — `WeatherTool` fetches `/data/2.5/weather` + `/data/2.5/forecast` in parallel via httpx; both payloads passed to OllamaClient for natural narration; returns error string if API key missing
- [x] Register OpenWeatherMap API key in config — `WeatherConfig` gains `units` field wired from YAML; `weather.py` uses `cfg.weather.units` (was hardcoded "imperial") and guards against `CHANGE_ME` placeholder; `tests/test_weather.py` smoke tests config loading + error path + happy path (5 passed)
- [x] Test: "What's the weather today?" → natural spoken forecast — `tests/test_weather_integration.py`; two tests (current + forecast query) skip automatically when key is CHANGE_ME; exercise real OWM HTTP + mocked LLM when real key is set

### Parts List (moved up from Phase 6 — user priority)
- [x] `docs/parts-list.md` — hardware parts list split into Pi section and server section — Pi 5 (8 GB) + ReSpeaker 2-Mic Pi HAT + PSU + MicroSD + case (~$130–140); server GPU upgrade RTX 4060 Ti 16 GB + 650 W PSU (~$500–550); includes ReSpeaker driver install notes and post-GPU config change

### CTA L Train
- [x] `server/tools/cta.py` — CTA Train Tracker API, Blue Line, Western & Milwaukee stop — `CtaTool` fetches arrivals from CTA Train Tracker API for Western & Milwaukee stop; direction param (ohare/forest_park/both); parses eta list; narrates via LLM; guards CHANGE_ME key; 8 smoke tests pass
- [x] Handle directional queries (O'Hare vs Forest Park) — `run()` injects direction-specific context into LLM system prompt (ohare focuses on O'Hare, forest_park focuses on Forest Park, both groups by direction); 3 new tests cover Forest Park path + system prompt content; 11 tests pass
- [x] Register CTA API key in config — `CtaConfig` (api_key + stop_id_ohare/forest_park) fully wired; `settings.yaml` updated with registration URL comment (transitchicago.com/developers/traintrackerapply); all 11 smoke tests pass
- [x] Test: "When's the next Blue Line?" → arrival times — `tests/test_cta_integration.py`; two async integration tests (both-direction + O'Hare direction) auto-skip when key is CHANGE_ME; when real key is set they call live CTA API, verify parsed arrivals structure (destination, arrival_time, is_delayed), and assert system prompt reflects direction; 11 smoke tests still pass

### Google Auth
- [x] Set up Google Cloud project, enable Calendar API + Tasks API — requires manual Google Cloud Console setup; skeleton + instructions provided; logged as blocker
- [x] `config/google_credentials.json` — OAuth2 client credentials — placeholder skeleton with step-by-step setup instructions created; replace with real OAuth2 Desktop client JSON from Google Cloud Console
- [x] `server/tools/google_auth.py` — OAuth2 flow, token refresh, shared by Calendar and Tasks — `is_configured()`, `get_credentials()` (load/refresh/new flow + token save), `build_service(api_name, version)`; guards CHANGE_ME placeholder; lazy google-auth import; 8 smoke tests pass

### Google Calendar
- [x] `server/tools/calendar.py` — read events for today / date range — `CalendarTool` queries primary calendar via Google API; supports today/tomorrow/this_week windows; narrates events via LLM; guards unconfigured state; 14 smoke tests pass
- [x] Add event with natural language date parsing — `AddCalendarEventTool` in `calendar.py`; `_parse_natural_date` via `dateparser` (future-preferring, Chicago TZ); creates event via Calendar API; guards no-title + unparseable-date; custom duration support; `dateparser>=1.2.0` added to requirements; 10 new smoke tests (24 total pass)
- [x] Emily events auto-prefixed with "Emily " — `AddCalendarEventTool.run()` prefixes title when `user.lower() == "emily"` and title doesn't already start with "Emily "; 3 new smoke tests (Emily prefix, no-double-prefix, owner no-prefix); 27 total pass
- [x] Test: "What do I have tomorrow?" → reads events for speaking user — `CalendarTool.run()` injects user name into system prompt when user is known; 2 new smoke tests (known-user name in prompt, unknown-user not in prompt); `tests/test_calendar_integration.py` with 2 integration tests (owner + Emily, real Google Calendar API, auto-skip without credentials); 29 smoke tests pass
- [x] Test: Emily says "I have a dentist appointment Thursday at 3" → event created as "Emily Dentist" — `tests/test_calendar_integration.py::test_emily_dentist_appointment_created_as_emily_dentist`; skips without credentials; uses real dateparser + mocked Google insert; asserts summary="Emily Dentist", hour=15, timeZone=America/Chicago, and confirmation string; 29 smoke tests still pass

### Google Tasks
- [x] `server/tools/tasks.py` — add item, list incomplete items, complete item by name — `AddTaskTool`, `ListTasksTool`, `CompleteTaskTool`; uses `build_service("tasks","v1")`; `_default_tasklist_id` helper; `_find_task_by_title` for case-insensitive complete; 23 smoke tests pass
- [x] Separate task lists per user ("Owner", "Emily") — `_user_tasklist_id(service, user)` finds list by name (case-insensitive), creates it if not found, falls back to first list for "unknown"; all 3 tools updated; 9 new tests (7 unit + 2 e2e owner/emily routing); 32 total pass
- [x] Test: "Add oat milk to my list" → added to correct user's list — `tests/test_tasks_integration.py`; 2 integration tests (owner + Emily, both verifying correct list ID used for insert); auto-skip without Google credentials; 32 smoke tests still pass
- [x] Test: "What's on my list?" → reads back incomplete items — `tests/test_tasks_integration.py`; 2 new integration tests (owner + Emily per-user routing for reads); verify `tasks().list()` uses correct list ID and `showCompleted=False`; mocked LLM; auto-skip without Google credentials; 32 smoke tests still pass
- [x] Test: "Mark oat milk as done" → completes the item — `tests/test_tasks_integration.py`; 2 new integration tests (owner + emily) verifying `tasks().patch()` called with correct list ID, task ID, and `body={"status": "completed"}`; auto-skip without Google credentials; 85 smoke tests pass

---

## Phase 4 — Entertainment
*Goal: Spotify playback and Android TV control working.*

### Android TV
- [x] `server/tools/androidtv.py` — `androidtvremote2` connection to TV (port 6466, no ADB debug needed) — `_connect()` helper (cert auto-generate, async_connect); `AndroidTvTool` with power_on/power_off; guards CHANGE_ME host; `AndroidTvConfig` extended with cert_file/key_file; `androidtvremote2>=0.1.1` added to requirements; 9 smoke tests pass
- [x] Launch app by package name (Spotify: `com.spotify.tv.android`, Netflix, YouTube, etc.) — `_APP_PACKAGES` dict + `_resolve_package()` (friendly name or raw package passthrough) + `_launch_intent()` (LEANBACK_LAUNCHER intent URI); `launch_app` action added to `AndroidTvTool`; calls `atv.send_launch_app()`; 11 new smoke tests; 20 androidtv tests, 105 total pass
- [x] Send media key events (play, pause, next, previous) — `_KEYCODE_MEDIA_PLAY/PAUSE/NEXT/PREVIOUS` constants; `play`, `pause`, `next`, `previous` added to action enum; 4 new smoke tests; 24 androidtv tests pass
- [x] Test: "Put on Netflix" → Netflix opens on TV — `tests/test_androidtv_integration.py`; 3 integration tests (correct package, case-insensitive, disconnect-on-error); skip when androidtv.host is still placeholder; 24 smoke + 3 skipped pass

### Spotify
- [x] `server/tools/spotify.py` — spotipy OAuth2 per user (Owner + Emily separate accounts, both need Premium) — `_is_configured()`, `_get_spotify()` (SpotifyOAuth with cache_path token file, open_browser=False), `SpotifyTool` with per-user routing (emily→emily config, else→owner); `now_playing` action functional; `SpotifyUserConfig` gains `redirect_uri`+`token_file`; `spotipy>=2.24.0` added to requirements; 20 smoke tests pass; spotipy stubbed in conftest
- [x] Combined launch flow: androidtv launches Spotify app → poll `sp.devices()` → transfer playback to TV — `_find_tv_device_id(sp)` (always fresh), `_launch_spotify_on_tv(atv_cfg)` (androidtvremote2), `_ensure_playing_on_tv(sp, cfg)` (launch best-effort → poll → transfer_playback force_play=True); 15 new smoke tests; 35 spotify tests pass
- [x] Never cache device ID — resolve fresh from `sp.devices()` each time — `_find_tv_device_id` always calls `sp.devices()` on every invocation; no module-level or instance cache
- [x] Play by song / artist / playlist / mood query — `_find_user_playlist` (pagination, strips "my " prefix), `_search_spotify` (mood→playlist, specific→track, personal hints→user playlists first), `_search_and_play` (calls `sp.start_playback`); `_ensure_tv_ready` factored out; `play` action uses search when `query` present; 19 new tests; 54 spotify tests, 163 total pass
- [x] Controls: pause, skip, volume — `pause_playback()`, `next_track()`, `previous_track()`, `volume(level)` in `_run_action`; volume clamps 0–100; 7 new smoke tests; 61 spotify tests, 170 total pass
- [x] Test: Owner says "Play some jazz" → plays on TV through Owner's account — `tests/test_spotify_integration.py::test_owner_play_jazz_uses_owner_account_and_starts_playback`; skips without real credentials; verifies owner config used, search called with "jazz", start_playback called with TV device ID and jazz playlist URI; 170 smoke pass, 2 new skipped
- [x] Test: Emily says "Play my Discover Weekly" → plays on TV through Emily's account — `tests/test_spotify_integration.py::test_emily_play_discover_weekly_uses_emily_account_and_user_playlist`; skips without real credentials; verifies emily config used, current_user_playlists called, start_playback with TV device ID and Emily's playlist URI; 170 smoke pass, 2 new skipped

---

## Phase 5 — Autonomous Tool Creation
*Goal: Assistant can build new tools when asked to do something it can't do.*

- [x] `server/tool_creator/generator.py` — LLM prompt to generate a `BaseTool` Python implementation — `ToolGenerator.generate(intent, existing_tool_names)` uses OllamaClient with a strict system prompt; strips markdown fences; validates syntax via `ast.parse`; retries up to 3×; raises ValueError after max retries; 15 smoke tests pass; 185 total pass
- [x] `server/tool_creator/sandbox.py` — subprocess runner with resource limits and import allowlist — `ALLOWED_IMPORTS` frozenset; `check_imports(source)` static AST walk; `SandboxResult` dataclass; `run_in_sandbox(source, timeout)` writes to temp file, spawns subprocess with CPU+memory limits via `preexec_fn` (`resource.setrlimit`), wall-clock timeout via `asyncio.wait_for`; 18 new smoke tests; 203 total pass
- [x] `server/tool_creator/validator.py` — run generated tool with test inputs, check for errors — `ValidationResult` dataclass (success, tool_name, tool_description, error); `validate(source, timeout)` static-import-checks then spawns subprocess that loads the tool, instantiates it, verifies name/description/parameters attrs, calls `run({}, "test_user")`, confirms str return; 11 smoke tests; 214 total pass
- [x] `server/tool_creator/installer.py` — write validated tool to `tools/generated/`, register it — `InstallResult` dataclass; `install(source, tool_name, registry)` sanitises name→snake_case module, writes to `server/tools/generated/<name>.py`, imports/reloads module, finds concrete BaseTool subclass, calls `registry.register(tool)`; handles overwrite + reload; 15 smoke tests pass
- [x] Integrate into main request flow: if no tool matches intent → trigger tool creator — `_needs_new_tool(text)` LLM binary classifier; `_create_and_notify(transcript, websocket)` background coroutine (generate → validate → install); `_handle_transcript` takes websocket param; `_generator` initialized in lifespan; 13 smoke tests pass
- [x] User notification: "I don't know how to do that yet, but I'll figure it out. I'll let you know when I can." — returned immediately when `_needs_new_tool` is True, before background creation starts
- [x] Completion notification: "I can do that now — want to try?" — sent via `websocket.send_text` by `_create_and_notify` after successful install; WebSocket send errors are suppressed with a warning
- [x] Test: ask for something novel → tool is created and works on second request — `tests/test_tool_creator_e2e.py`; mocks generator to return pre-written valid tool source; runs real validator (subprocess) + real installer (file write); asserts first response is "I don't know…"; asserts tool appears in registry + file on disk + WebSocket completion notification; second request routed to new tool returns expected string; 1 new test, 55 tool-creator tests pass

---

## Phase 6 — Hardening & Quality
*Goal: Reliable, always-on operation.*

- [x] Systemd service for server (auto-start, auto-restart) — `deploy/homeassistant-server.service` (Type=simple, Restart=on-failure, RestartSec=5s, StartLimitBurst=5); `deploy/install-server-service.sh` creates service user, copies project, creates venv, installs requirements, writes unit file (path + user substituted), enables + starts service
- [x] Systemd service for Pi client (auto-start on boot) — `deploy/homeassistant-pi.service` (Type=simple, After=network-online.target sound.target, Restart=on-failure, RestartSec=5s, StartLimitBurst=5, journald logging); `deploy/install-pi-service.sh` creates service user, adds it to the audio group (PyAudio/sounddevice access), rsyncs project, creates venv + installs requirements-pi.txt, substitutes install path + user into unit file, enables + starts service
- [ ] Error handling: graceful recovery from LLM timeout, API failures, network drop
- [ ] Logging: structured logs to file with rotation
- [ ] Wake word false positive rate — tune sensitivity
- [ ] Latency profiling — identify and fix slow spots in the pipeline
- [ ] Agent startup check-in: agent writes a brief status note to `INBOX.md` (Agent Startup Log section) at the start of each session

---

## Future — Phase 7 (Music Recommendations)
*Per-user recommendation models trained on listening history. Deferred to after core system is stable.*

- [ ] Design per-user taste model
- [ ] Listening history collection from Spotify API
- [ ] Recommendation engine (collaborative filtering or embedding-based)
- [ ] Voice interface: "Play something I'd like" → recommendation-driven playlist

---

## Blockers Log

*Record blockers here so the next agent session knows what was stuck and why.*

| Date | Phase | Blocker | Status |
|------|-------|---------|--------|
| 2026-05-07 | Phase 2 | Enrollment (Owner + Emily) and speaker-ID hardware tests require physical Pi + microphone — cannot run in dev environment | Blocked; proceed to Phase 3 |
| 2026-05-08 | Phase 3 | `tests/test_weather_integration.py` integration tests skip until `weather.api_key` in `config/settings.yaml` is set to a real OpenWeatherMap key (currently CHANGE_ME) | Tests written; blocked on real key |
| 2026-05-09 | Phase 3 | CTA integration test (`tests/test_cta_integration.py`) will skip until `cta.api_key` in `config/settings.yaml` is set to a real CTA Train Tracker key — register free at transitchicago.com/developers/traintrackerapply | Tests to be written next session |
| 2026-05-10 | Phase 3 | Google Auth requires manual setup: (1) create project in Google Cloud Console, (2) enable Calendar + Tasks APIs, (3) create OAuth2 Desktop client credential, (4) download JSON to `config/google_credentials.json`, (5) run server once to complete browser OAuth flow (token saved to `config/google_token.json`) | Blocked on manual Google Cloud setup |
