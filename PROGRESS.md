# Agent Progress Log

Most recent run at top.

---

## [2026-05-07 00:00 UTC]
**Completed:** Updated `server/llm/prompts.py` — `build_system_prompt(user)` appends a personalized suffix: known speaker gets "address them by name naturally", unknown speaker gets "ask who they are if they request something personal"; `server/main.py` passes `transcript.user`
**Files changed:** server/llm/prompts.py, server/main.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Enrollment — run enrollment script for Owner (requires Pi hardware)
**Blockers:** None
---

## [2026-05-06 11:00 UTC]
**Completed:** Integrated speaker ID into `pi/main.py` — buffers PCM bytes during audio capture, runs `identify()` in executor concurrently with `receive_transcript()` to hide latency, attaches speaker name via `model_copy(update={"user": user})` before sending Transcript to server; also added `user: str = "unknown"` to `Transcript` in `shared/models.py`
**Files changed:** pi/main.py, shared/models.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Update `server/llm/prompts.py` — inject user name into system prompt for personalization
**Blockers:** None
---

## [2026-05-06 10:00 UTC]
**Completed:** Implemented `pi/speaker_id/identify.py` — `identify(pcm_bytes, sample_rate)` and `identify_embedding(embedding)`; cosine similarity (dot product of unit vectors) vs all enrolled `config/voice_profiles/*.npy`; returns best-match name or "unknown" if below 0.75 threshold
**Files changed:** pi/speaker_id/identify.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Integrate speaker ID into `pi/main.py` — identify before sending transcript to server
**Blockers:** None
---

## [2026-05-06 08:20 UTC]
**Completed:** Implemented `pi/speaker_id/enroll.py` — CLI enrollment script; records 30s of raw int16 PCM at 16kHz via PyAudio; prints live countdown; calls `embed_audio` + `save_embedding`; run as `python -m pi.speaker_id.enroll <name> [--device INDEX]`
**Files changed:** pi/speaker_id/enroll.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md
**Next up:** `pi/speaker_id/identify.py` — compare incoming audio embedding against enrolled profiles, return user name or "unknown"
**Blockers:** None
---

## [2026-05-06 05:00 UTC]
**Completed:** Implemented `pi/speaker_id/embeddings.py` — `embed_audio(pcm_bytes, sample_rate)` converts raw int16 PCM to 256-d numpy embedding via resemblyzer `VoiceEncoder.embed_utterance`; `save_embedding`/`load_embedding`/`list_profiles` manage `config/voice_profiles/*.npy` files
**Files changed:** pi/speaker_id/embeddings.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md
**Next up:** `pi/speaker_id/enroll.py` — enrollment script: record 30s of speech, save embedding to `config/voice_profiles/`
**Blockers:** None
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


