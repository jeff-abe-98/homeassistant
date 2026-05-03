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
- [ ] WebSocket handler: receive `Transcript` → run LLM → return `AssistantResponse`

### Pi
- [ ] `pi/audio/capture.py` — mic input with WebRTC VAD (start/stop on voice activity)
- [ ] `pi/audio/playback.py` — play audio bytes through HDMI output
- [ ] `pi/tts/piper.py` — wrap Piper TTS (text in → audio bytes out)
- [ ] `pi/wake_word/detector.py` — openWakeWord listener, fires callback on detection
- [ ] `pi/client.py` — WebSocket client connecting to server `/ws`
- [ ] `pi/main.py` — main loop: wake word → capture → send to server → receive response → TTS → play

### Testing Phase 1
- [ ] End-to-end test: say wake word → ask "what is 2 plus 2" → assistant responds via speaker

---

## Phase 2 — Speaker Identification
*Goal: Assistant knows who is talking and personalizes responses. Voice enrollment for Owner and Emily.*

- [ ] `pi/speaker_id/embeddings.py` — generate and save voice embeddings using resemblyzer
- [ ] `pi/speaker_id/enroll.py` — enrollment script: record 30s of speech, save embedding to `config/voice_profiles/`
- [ ] `pi/speaker_id/identify.py` — compare incoming audio embedding against enrolled profiles, return user name or "unknown"
- [ ] Integrate speaker ID into `pi/main.py` — identify before sending transcript to server
- [ ] Update `shared/models.py` — add `user: str` field to `Transcript`
- [ ] Update `server/llm/prompts.py` — inject user name into system prompt for personalization
- [ ] Enrollment: run enrollment script for Owner
- [ ] Enrollment: run enrollment script for Emily
- [ ] Test: Owner speaks → response addresses Owner; Emily speaks → response addresses Emily
- [ ] Test: Unknown speaker asks generic question → answered normally; asks personal question → "Who's this?"

---

## Phase 3 — Core Tool Integrations
*Goal: Weather, CTA, Google Calendar, Google Tasks all working.*

### Tool System Foundation
- [ ] `server/tools/base.py` — `BaseTool` abstract class and `ToolRegistry` (auto-discovers tools in `tools/`)
- [ ] `server/llm/router.py` — LLM function calling: given transcript + user, select tool + extract params
- [ ] Update WebSocket handler to run tool router and return tool result

### Weather
- [ ] `server/tools/weather.py` — fetch OpenWeatherMap data, pass raw JSON to LLM for natural narration
- [ ] Register OpenWeatherMap API key in config
- [ ] Test: "What's the weather today?" → natural spoken forecast

### CTA L Train
- [ ] `server/tools/cta.py` — CTA Train Tracker API, Blue Line, Western & Milwaukee stop
- [ ] Handle directional queries (O'Hare vs Forest Park)
- [ ] Register CTA API key in config
- [ ] Test: "When's the next Blue Line?" → arrival times

### Google Auth
- [ ] Set up Google Cloud project, enable Calendar API + Tasks API
- [ ] `config/google_credentials.json` — OAuth2 client credentials
- [ ] `server/tools/google_auth.py` — OAuth2 flow, token refresh, shared by Calendar and Tasks

### Google Calendar
- [ ] `server/tools/calendar.py` — read events for today / date range
- [ ] Add event with natural language date parsing
- [ ] Emily events auto-prefixed with "Emily "
- [ ] Test: "What do I have tomorrow?" → reads events for speaking user
- [ ] Test: Emily says "I have a dentist appointment Thursday at 3" → event created as "Emily Dentist"

### Google Tasks
- [ ] `server/tools/tasks.py` — add item, list incomplete items, complete item by name
- [ ] Separate task lists per user ("Owner", "Emily")
- [ ] Test: "Add oat milk to my list" → added to correct user's list
- [ ] Test: "What's on my list?" → reads back incomplete items
- [ ] Test: "Mark oat milk as done" → completes the item

---

## Phase 4 — Entertainment
*Goal: Spotify playback and Android TV control working.*

### Android TV
- [ ] `server/tools/androidtv.py` — `androidtvremote2` connection to TV (port 6466, no ADB debug needed)
- [ ] Launch app by package name (Spotify: `com.spotify.tv.android`, Netflix, YouTube, etc.)
- [ ] Send media key events (play, pause, next, previous)
- [ ] Test: "Put on Netflix" → Netflix opens on TV

### Spotify
- [ ] `server/tools/spotify.py` — spotipy OAuth2 per user (Owner + Emily separate accounts, both need Premium)
- [ ] Combined launch flow: androidtv launches Spotify app → poll `sp.devices()` → transfer playback to TV
- [ ] Never cache device ID — resolve fresh from `sp.devices()` each time
- [ ] Play by song / artist / playlist / mood query
- [ ] Controls: pause, skip, volume
- [ ] Test: Owner says "Play some jazz" → plays on TV through Owner's account
- [ ] Test: Emily says "Play my Discover Weekly" → plays on TV through Emily's account

---

## Phase 5 — Autonomous Tool Creation
*Goal: Assistant can build new tools when asked to do something it can't do.*

- [ ] `server/tool_creator/generator.py` — LLM prompt to generate a `BaseTool` Python implementation
- [ ] `server/tool_creator/sandbox.py` — subprocess runner with resource limits and import allowlist
- [ ] `server/tool_creator/validator.py` — run generated tool with test inputs, check for errors
- [ ] `server/tool_creator/installer.py` — write validated tool to `tools/generated/`, register it
- [ ] Integrate into main request flow: if no tool matches intent → trigger tool creator
- [ ] User notification: "I don't know how to do that yet, but I'll figure it out. I'll let you know when I can."
- [ ] Completion notification: "I can do that now — want to try?"
- [ ] Test: ask for something novel → tool is created and works on second request

---

## Phase 6 — Hardening & Quality
*Goal: Reliable, always-on operation.*

- [ ] Systemd service for server (auto-start, auto-restart)
- [ ] Systemd service for Pi client (auto-start on boot)
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
| — | — | — | — |
