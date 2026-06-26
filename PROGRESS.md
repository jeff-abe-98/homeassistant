# Agent Progress Log

Most recent run at top.

---

## [2026-06-26 UTC]
**Completed:** Phase 12 item 6 — pass VAD-trimmed buffer to Whisper. `hailo_transcriber.py`: `transcribe()` and `_transcribe_sync()` accept `max_seconds: float = 30.0`; float32 array truncated to `int(max_seconds * sample_rate)` samples before `generate_all_text`; LATENCY log when trimmed. `main.py`: computes `actual_utterance_seconds` from PCM length; passes `max_seconds=min(10.0, actual_seconds + 1.0)` to both `stt.transcribe()` call sites. 4 new smoke tests pass. Phase 12 complete.
**Files changed:** pi/stt/hailo_transcriber.py, pi/main.py, tests/test_hailo_stt.py, plan.md, .project/CURRENT_WORK.md, INBOX.md, PROGRESS.md
**Next up:** Phase 12 complete — all latency-speedup items done; next work awaits new inbox items or Pi deployment
**Blockers:** Physical Pi needed to validate latency savings with real measurements
---

## [2026-06-26 UTC]
**Completed:** Phase 12 item 5 — eliminate second LLM call for tool narration. Added `needs_narration: bool = False` to `BaseTool`; `WeatherTool`/`CtaTool`/`CalendarTool` set `needs_narration = True` and return raw data blocks (no internal LLM call). `router.narrate()` stores question from `route()` and calls LLM once. `main.py` calls `router.narrate()` for flagged tools. 12 new tests in `test_narration.py`; 61 targeted tests pass. Expected saving: ~900ms per tool query.
**Files changed:** pi/tools/base.py, pi/tools/weather.py, pi/tools/cta.py, pi/tools/calendar.py, pi/llm/router.py, pi/main.py, tests/test_narration.py, tests/test_weather.py, tests/test_cta.py, tests/test_calendar.py, tests/test_phase9_e2e.py, plan.md, .project/CURRENT_WORK.md, INBOX.md, PROGRESS.md
**Next up:** Phase 12 item 6 — pass VAD-trimmed buffer to Whisper
**Blockers:** Physical Pi needed to validate latency savings with real measurements
---

## [2026-06-25 UTC]
**Completed:** Phase 12 item 4 — keep PyAudio streams open permanently. `detector.py`: `start()` reuses open stream, `stop()` thread-only, new `drain()` + `close()`. `capture.py`: `open_stream()` + `capture_from_stream()` added; `stream()` refactored to call them. `main.py`: both streams opened once at startup; `capture=`/`capture_stream=` threaded through; `detector.drain()` + `detector.start()` per activation cycle. `conftest.py`: added numpy/scipy/hailo_platform stubs + openwakeword `__file__`. 365 tests pass. Expected saving: 100–300ms per activation.
**Files changed:** pi/wake_word/detector.py, pi/audio/capture.py, pi/main.py, tests/test_phase9_e2e.py, conftest.py, plan.md, .project/CURRENT_WORK.md, INBOX.md, PROGRESS.md
**Next up:** Phase 12 item 5 — eliminate second LLM call for tool narration
**Blockers:** Physical Pi needed to validate latency savings with real measurements
---

## [2026-06-25 UTC]
**Completed:** Phase 12 item 3 — replaced `scipy.signal.resample_poly` with stride-3 integer decimation (`audio_int16[::3]`) in `pi/main.py`; removed unused `resample_poly` and `gcd` imports. Adds comment noting decimation is adequate for Whisper speech input. Expected saving: 10–50ms per activation.
**Files changed:** pi/main.py, plan.md, .project/CURRENT_WORK.md, INBOX.md, PROGRESS.md
**Next up:** Phase 12 item 4 — keep PyAudio streams open permanently (`pi/wake_word/detector.py`, `pi/audio/capture.py`, `pi/main.py`)
**Blockers:** Physical Pi needed to validate latency savings with real measurements
---

## [2026-06-25 UTC]
**Completed:** Phase 12 item 2 — reduce LLM `max_tokens` default 200→100 in `_generate_sync()` in `pi/llm/hailo_client.py`. Tool responses ≤40 tokens; conversational ≤80; 100 eliminates worst-case ceiling with zero quality risk. Expected saving: 0–500ms, typical ~100ms.
**Files changed:** pi/llm/hailo_client.py, plan.md, .project/CURRENT_WORK.md, INBOX.md, PROGRESS.md
**Next up:** Phase 12 item 3 — replace `resample_poly` with `pcm_48k[::3]` in `pi/main.py`
**Blockers:** Physical Pi needed to validate latency savings with real measurements
---

## [2026-06-25 UTC]
**Completed:** Phase 12 item 1 — reduce silence tail: `silence_duration_ms` default 1200→800 in `pi/audio/capture.py`; `AudioConfig.silence_duration_ms` added to `shared/config.py` and wired in `load()`; `audio.silence_duration_ms: 800` added to `config/settings.yaml`; `_capture_utterance()` and `_handle_capability_gap()` in `pi/main.py` wired to pass config value. Expected saving: ~400ms per activation.
**Files changed:** pi/audio/capture.py, shared/config.py, config/settings.yaml, pi/main.py, plan.md, .project/CURRENT_WORK.md, INBOX.md, PROGRESS.md
**Next up:** Phase 12 item 2 — reduce LLM `max_tokens` 200→100 in `pi/llm/hailo_client.py`
**Blockers:** Physical Pi needed to validate latency savings with real measurements
---

## [2026-06-25 UTC]
**Completed:** Phase 11 item 5 — appended Phase 12 to plan.md with 6 concrete latency-speedup tasks ordered fastest-win-first: (1) silence_duration_ms 1200→800 (~400ms), (2) max_tokens 200→100 (0–500ms), (3) resample_poly → pcm[::3] (10–50ms), (4) keep PyAudio streams open (100–300ms), (5) eliminate second LLM call for tools (~900ms), (6) VAD-trimmed Whisper buffer (TBD hardware)
**Files changed:** plan.md, .project/CURRENT_WORK.md, INBOX.md, PROGRESS.md
**Next up:** Phase 12 item 1 — reduce `silence_duration_ms` from 1200 to 800 in `pi/audio/capture.py`
**Blockers:** Physical Pi needed to validate latency savings with real measurements
---

## [2026-06-25 UTC]
**Completed:** Phase 11 item 4 — latency analysis: synthesised all three profiling docs into `.project/research/latency-analysis.md`; end-to-end budget tables for conversational (~2970ms) and tool-query (~4170ms) warm paths; top-5 bottlenecks ranked with feasibility assessment; Phase B target after fixes 1–4: ~1670ms / ~2470ms; fix-order table written for Phase 12
**Files changed:** .project/research/latency-analysis.md, plan.md, .project/CURRENT_WORK.md, INBOX.md, PROGRESS.md
**Next up:** Phase 11 item 5 — add implementation tasks as Phase 12 in plan.md
**Blockers:** Physical Pi needed to validate latency estimates with real measurements
---

## [2026-06-24 UTC]
**Completed:** Phase 11 item 3 — third-party/system overhead audit: 8 new LATENCY log lines in detector.py (wakeword_stream_open/close), piper.py (tts_model_load, tts_synthesize_internal), main.py (decimation comparison, executor_queue_wait ×3); max_tokens added to LLM generate log; `_executor_timed()` helper; `.project/research/latency-overhead.md` created with 5-section tables and hypotheses
**Files changed:** pi/wake_word/detector.py, pi/tts/piper.py, pi/llm/hailo_client.py, pi/main.py, .project/research/latency-overhead.md, plan.md, .project/CURRENT_WORK.md, INBOX.md, PROGRESS.md
**Next up:** Phase 11 item 4 — analyse findings and rank bottlenecks (`latency-analysis.md`)
**Blockers:** Physical Pi needed to collect actual timing measurements
---

## [2026-06-24 UTC]
**Completed:** Phase 11 item 2 — inference pipeline profiling instrumentation: 17 LATENCY log lines added across 5 files (main, hailo_client, hailo_transcriber, playback, identify); cold/warm labelling for LLM/STT/speaker-ID; `.project/research/latency-inference.md` created
**Files changed:** pi/main.py, pi/llm/hailo_client.py, pi/stt/hailo_transcriber.py, pi/audio/playback.py, pi/speaker_id/identify.py, .project/research/latency-inference.md, plan.md, .project/CURRENT_WORK.md, INBOX.md, PROGRESS.md
**Next up:** Phase 11 item 3 — audit third-party and system overhead (`latency-overhead.md`)
**Blockers:** Physical Pi needed to collect actual timing measurements
---

## [2026-06-24 UTC]
**Completed:** Phase 11 item 1 — audio capture pipeline profiling instrumentation added to `pi/audio/capture.py` and `pi/main.py`; measurement template created at `.project/research/latency-audio.md`
**Files changed:** pi/audio/capture.py, pi/main.py, .project/research/latency-audio.md, plan.md, .project/CURRENT_WORK.md, INBOX.md, PROGRESS.md
**Next up:** Phase 11 item 2 — profile the inference pipeline (speaker-ID, STT, LLM, tool, TTS, playback)
**Blockers:** Phase 11 actual measurements require physical Pi hardware; instrumentation code is complete and will emit LATENCY lines at DEBUG log level
---

## [2026-06-24 UTC]
**Completed:** Routine check-in (session 183) — inbox empty, all 10 phases complete; no new work; updated startup log
**Files changed:** INBOX.md, PROGRESS.md
**Next up:** All phases complete — awaiting physical Pi deployment or new inbox items
**Blockers:** None
---

## [2026-06-24 UTC]
**Completed:** Routine check-in (session 182) — inbox empty, all 10 phases complete; no new work; updated startup log
**Files changed:** INBOX.md, PROGRESS.md
**Next up:** All phases complete — awaiting physical Pi deployment or new inbox items
**Blockers:** None
---

## [2026-06-24 UTC]
**Completed:** Routine check-in (session 181) — inbox empty, all 10 phases complete; no new work; updated startup log
**Files changed:** INBOX.md, PROGRESS.md
**Next up:** All phases complete — awaiting physical Pi deployment or new inbox items
**Blockers:** None
---

## [2026-06-23 UTC]
**Completed:** Routine check-in (session 180) — inbox empty, all 10 phases complete; no new work; updated startup log
**Files changed:** INBOX.md, PROGRESS.md
**Next up:** All phases complete — awaiting physical Pi deployment or new inbox items
**Blockers:** None
---

## [2026-06-23 UTC]
**Completed:** Routine check-in (session 179) — inbox empty, all 10 phases complete; no new work; updated startup log
**Files changed:** INBOX.md, PROGRESS.md
**Next up:** All phases complete — awaiting physical Pi deployment or new inbox items
**Blockers:** None
---

## [2026-06-23 UTC]
**Completed:** Routine check-in (session 178) — inbox empty, all 10 phases complete; no new work; updated startup log
**Files changed:** INBOX.md, PROGRESS.md
**Next up:** All phases complete — awaiting physical Pi deployment or new inbox items
**Blockers:** None
---

## [2026-06-23 UTC]
**Completed:** Routine check-in (session 177) — inbox empty, all 10 phases complete; no new work; updated startup log
**Files changed:** INBOX.md, PROGRESS.md
**Next up:** All phases complete — awaiting physical Pi deployment or new inbox items
**Blockers:** None
---

## [2026-06-23 UTC]
**Completed:** Routine check-in (session 176) — inbox empty, all 10 phases complete; no new work; updated startup log
**Files changed:** INBOX.md, PROGRESS.md
**Next up:** All phases complete — awaiting physical Pi deployment or new inbox items
**Blockers:** None
---

## [2026-06-23 UTC]
**Completed:** Routine check-in (session 175) — inbox empty, all 10 phases complete; no new work; updated startup log
**Files changed:** INBOX.md, PROGRESS.md
**Next up:** All phases complete — awaiting physical Pi deployment or new inbox items
**Blockers:** None
---

## [2026-06-22 UTC]
**Completed:** Routine check-in (session 174) — inbox empty, all 10 phases complete; no new work; updated startup log
**Files changed:** INBOX.md, PROGRESS.md
**Next up:** All phases complete — awaiting physical Pi deployment or new inbox items
**Blockers:** None
---


