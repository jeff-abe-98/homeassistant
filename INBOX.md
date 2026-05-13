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
