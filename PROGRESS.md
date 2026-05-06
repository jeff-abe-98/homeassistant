# Agent Progress Log

Most recent run at top.

---

## [2026-05-06 UTC (session 14)]
**Completed:** Implemented end-to-end pipeline test — `tests/test_e2e.py`; real uvicorn server + real WebSocket client; STT + LLM mocked via unittest.mock; AudioChunk → Transcript → AssistantResponse round-trip; 1 passed in 0.48 s. Phase 1 is now complete.
**Files changed:** tests/__init__.py, tests/test_e2e.py, conftest.py, pytest.ini, requirements-test.txt, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 2 / `pi/speaker_id/embeddings.py` — generate and save voice embeddings using resemblyzer
**Blockers:** None
---

## [2026-05-05 UTC (session 13)]
**Completed:** Implemented `pi/main.py` — async main loop; WakeWordDetector start/stop around each utterance; VoiceCapture.stream() bridged to async via background thread + asyncio.Queue; streams AudioChunk frames to server; awaits receive_transcript → send_transcript → receive_response; TTS synthesis + playback via run_in_executor; exception-safe utterance retry
**Files changed:** pi/main.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** End-to-end test: say wake word → ask "what is 2 plus 2" → assistant responds via speaker
**Blockers:** None
---

## [2026-05-05 UTC (session 12)]
**Completed:** Implemented `pi/client.py` — `AssistantClient` WebSocket client; async context manager (`connect`/`disconnect`/`__aenter__`/`__aexit__`); `send_audio_chunk`, `send_transcript`, `receive_transcript`, `receive_response`; background listener routes server messages into per-session `asyncio.Queue`; optional async `on_transcript`/`on_response` callbacks
**Files changed:** pi/client.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** `pi/main.py` — main loop: wake word → capture → send to server → receive response → TTS → play
**Blockers:** None
---

## [2026-05-05 UTC (session 11)]
**Completed:** Implemented `pi/wake_word/detector.py` — `WakeWordDetector` class; background thread reads 80ms PyAudio frames at 16kHz; openWakeWord `Model.predict()` checked against threshold; fires `on_detection()` callback then stops; `WakeWordConfig` added to `shared/config.py`
**Files changed:** pi/wake_word/detector.py, shared/config.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** `pi/client.py` — WebSocket client connecting to server `/ws`
**Blockers:** None
---

## [2026-05-05 UTC (session 10)]
**Completed:** Implemented `pi/tts/piper.py` — `PiperTTS` class wrapping Piper TTS; `synthesize(text) -> bytes` returns raw int16 PCM; `sample_rate` from model config; deferred `PiperVoice` import; `PiperConfig` added to `shared/config.py` and `config/settings.yaml`; `piper-tts>=2.0.0` added to `requirements-pi.txt`
**Files changed:** pi/tts/piper.py, shared/config.py, config/settings.yaml, requirements-pi.txt, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** `pi/wake_word/detector.py` — openWakeWord listener, fires callback on detection
**Blockers:** None
---

## [2026-05-04 UTC (session 9)]
**Completed:** Processed inbox — triaged "Add a parts list (Pi + server)" into plan.md Phase 6 as `docs/parts-list.md` task
**Files changed:** plan.md, INBOX.md, .project/CURRENT_WORK.md, PROGRESS.md
**Next up:** `pi/tts/piper.py` — wrap Piper TTS (text in → audio bytes out)
**Blockers:** None
---

## [2026-05-04 UTC (session 8)]
**Completed:** Implemented `pi/audio/playback.py` — `AudioPlayer` wrapping sounddevice; 22050 Hz mono int16 defaults (Piper TTS format); `play()` blocks until done; `stop()` interrupts
**Files changed:** pi/audio/playback.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md
**Next up:** `pi/tts/piper.py` — wrap Piper TTS (text in → audio bytes out)
**Blockers:** None
---

## [2026-05-04 UTC (session 7)]
**Completed:** Implemented `pi/audio/capture.py` — `VoiceCapture` class with PyAudio mic input, WebRTC VAD gating; 30ms frames at 16kHz; 300ms pre-speech ring buffer + 900ms silence ring; new UUID session_id per utterance; yields `AudioChunk` stream with is_final=True on silence
**Files changed:** pi/audio/capture.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** `pi/audio/playback.py` — play audio bytes through HDMI output
**Blockers:** None
---

## [2026-05-04 UTC]
**Completed:** Implemented `_handle_transcript` in `server/main.py` — wires Transcript through LLM, returns AssistantResponse; server voice pipeline now fully end-to-end
**Files changed:** server/main.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** `pi/audio/capture.py` — mic input with WebRTC VAD (start/stop on voice activity)
**Blockers:** None
---

## [2026-05-03 (session 5) UTC]
**Completed:** Implemented STT WebSocket handler — `server/stt/transcriber.py` (WhisperTranscriber wrapping faster-whisper); buffers AudioChunk stream per session_id; transcribes on is_final via run_in_executor; WhisperConfig added to shared/config.py
**Files changed:** server/stt/__init__.py, server/stt/transcriber.py, server/main.py, shared/config.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** WebSocket handler: receive `Transcript` → run LLM → return `AssistantResponse`
**Blockers:** None
---

## [2026-05-03 (session 4) UTC]
**Completed:** Created `server/main.py` — FastAPI app with lifespan, OllamaClient init, and `/ws` WebSocket endpoint dispatching AudioChunk/Transcript messages
**Files changed:** server/main.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md
**Next up:** WebSocket handler: receive `AudioChunk` stream → run STT → return `Transcript`
**Blockers:** None
---

## [2026-05-03 (session 3) UTC]
**Completed:** Created `server/llm/prompts.py` — base system prompt constant and `build_system_prompt()` function for the assistant persona
**Files changed:** server/llm/prompts.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md
**Next up:** `server/main.py` — FastAPI app with a single `/ws` WebSocket endpoint
**Blockers:** None
---

## [2026-05-03 (session 2) UTC]
**Completed:** Created `server/llm/client.py` — async Ollama client wrapper with `chat()` and `complete()` methods
**Files changed:** server/llm/client.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** `server/llm/prompts.py` — system prompt for the assistant persona
**Blockers:** None
---

