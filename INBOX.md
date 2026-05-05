# Inbox

Edit this file directly in GitHub to communicate with the development agent.
The agent reads this at the start of every run.

---

## Open Questions
*Decisions or info needed before the agent can proceed. Agent will check these off when resolved, or note why it's blocked.*

<!-- Example: - [ ] What should the wake word be? -->

## Ideas & Improvements
*New features, changes to existing features, or improvements. Agent will triage these into plan.md and check them off.*
 - [x] Make sure that when you are reading this at start up, you are also writing here. *(added to plan.md Phase 6)*
 - [x] Add a parts list. this should be split into parts for the Pi, and parts for the server. *(added to plan.md Phase 6)*

## Notes
*Anything else — reminders, context, thoughts.*

<!-- Example: Emily's Spotify account is premium, mine is not yet -->

---

## Agent Startup Log
*The agent writes a brief status note here at the start of each session.*

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
