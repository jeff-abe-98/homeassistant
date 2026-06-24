# Current Work

**Last updated:** 2026-06-24
**Phase:** Phase 11 — Latency Profiling & Speedup (items 1–2 complete)

---

## Status

Full architectural redesign and documentation complete (Phases 1–10). Phase 11 in progress.

**Phase 11 item 2 (done 2026-06-24):**
- Added 17 LATENCY DEBUG log lines across 5 files covering every inference stage.
- `pi/main.py`: `identify_stt_parallel` (total wall-clock for concurrent speaker-ID + STT gather), `llm_route` (full router.route() call with selected tool name), `tool_run` (per-tool timing with tool name label), `tts_synthesize` (Piper synthesis with byte count), `audio_play_total` (executor round-trip for playback).
- `pi/llm/hailo_client.py`: `llm_cold_load` (model load from disk), `llm_prompt_build` (tool schema injection into system prompt), `llm_generate_cold/warm` (generate_all on NPU with cold/warm label and approx token count).
- `pi/stt/hailo_transcriber.py`: `stt_cold_load` (model load), `stt_pcm_to_float32` (PCM conversion), `stt_transcribe_cold/warm` (generate_all_text with cold/warm label).
- `pi/audio/playback.py`: `tts_resample_22050to48000` (scipy resample with sample count), `audio_playback` (sd.play+wait with audio_s).
- `pi/speaker_id/identify.py`: `speaker_id_embed_cold/warm` (resemblyzer embed_utterance with cold/warm), `speaker_id_match` (cosine similarity with result name).
- Created `.project/research/latency-inference.md`: 6-stage measurement tables (5 runs each), cold vs warm columns, end-to-end budget template, and expected findings. Physical Pi needed for actual timings.

**Phase 11 item 1 (done 2026-06-24):**
- Added `time.perf_counter()` timing instrumentation (DEBUG level) to `pi/audio/capture.py` and `pi/main.py`.
- `pi/audio/capture.py`: logs `vad_stream_open` (PyAudio.open() duration), `vad_trigger_fired` (stream age when speech detected), and `utterance_end` (per-frame read/VAD stats with min/avg/max + silence tail estimate).
- `pi/main.py`: logs `wake_to_capture_start` (wake event → _capture_utterance entry), `capture_stream_first_chunk` (first audio chunk latency), `resample_48k_to_16k` (scipy resample duration), `capture_total` (full capture duration + utterance audio length). Added `t_wake` param through `_handle_activation` → `_capture_utterance`.
- Created `.project/research/latency-audio.md`: full measurement procedure, 6 measurement tables ready to fill with 10-utterance data, expected findings/hypotheses. Physical Pi needed to collect actual timings.

**Phase 10 item 4 (done 2026-06-19):**
- Created `scripts/first-run-check.sh`: 7-section preflight script — (1) hailortcli installed + AI HAT+ 2 PCIe detected, (2) no CHANGE_ME placeholders + androidtv IP configured, (3) LLM/STT/TTS model .hef/.onnx files present, (4) Google OAuth credentials + token files, (5) Spotify per-user token files, (6) ≥2 voice profiles enrolled, (7) systemd homeassistant-pi.service + scheduler.timer active. Exits non-zero on any failure; PASS/FAIL lines guide the user to the right docs section.

**Phase 10 item 3 (done 2026-06-19):**
- Created `docs/api-keys-setup.md`: step-by-step instructions for all 5 external credentials — CTA (registration URL + field mapping), OpenWeatherMap (free tier key, 10-min activation note), Google OAuth (4-part guide: Cloud project → enable APIs → OAuth consent + credentials → first-run token flow), Spotify (create app once, dual-user auth, Emily test-user note), Android TV (IP finding, static DHCP, first-time pairing flow). Credential file summary table at the end.

**Phase 10 item 2 (done 2026-06-19):**
- Created `docs/setup-guide.md`: 11-step first-time setup covering OS flash, HailoRT driver install + verification, repo clone, pip install, LLM/STT/TTS model downloads, settings.yaml configuration table, Google OAuth first-run flow, voice enrollment for both users (with device-index tip), systemd service install, test phrases, and optional custom wake word training.

**Phase 10 item 1 (done 2026-06-19):**
- Created `README.md`: project overview, hardware table (~$270 total), quick-start commands, feature table, project structure, doc links, autonomous tool creation walkthrough, config reference.

**Next:** Phase 11 item 3 — audit third-party and system overhead (`latency-overhead.md`).

## Documents

| File | Purpose |
|------|---------|
| `requirements.md` | Full project requirements (still valid) |
| `.project/active/pi-redesign/spec.md` | New architecture spec — read before implementing anything |
| `plan.md` | New phased implementation plan — agent works from here |
| `docs/technical-stack.md` | Updated stack decisions |
| `docs/parts-list.md` | Updated hardware list |

## Key Architecture Decisions

- **Single unified process** on Pi — no WebSocket client/server split
- **HailoRT** for LLM + STT inference on Hailo-10H NPU (replaces Ollama + Faster Whisper)
- **Wake word:** "Clanker" (openWakeWord, unchanged)
- **Tool creation:** Claude Code remote scheduled agent reads/writes via GitHub repo — Pi never calls Claude API directly
- **Tool requests:** Local SQLite queue → push to GitHub when online → agent builds → Pi pulls + loads
- **Scheduling:** Pi usage heatmap drives when the remote agent runs; agent self-reschedules via CronDelete + CronCreate
- **Conversation memory:** SQLite, session-scoped, recent turns injected into LLM prompt
- **Android TV:** `androidtvremote2` (confirmed correct)
- **All existing tools preserved**

## Agent Instructions

1. Read `.project/active/pi-redesign/spec.md` fully before starting any phase
2. Read `plan.md` — find first unchecked item in Phase 1
3. Read `docs/technical-stack.md` for stack context
4. Implement the item
5. Check it off in `plan.md` with a brief note
6. Continue until phase is complete or blocker hit

## Open Questions

None — spec is approved, plan is ready.

## Hardware Notes

- Pi 5 8GB + AI HAT+ 2 + USB mic + A2 SD card + PSU/case ≈ $270
- Hardware arrived 2026-06-15 — Hailo-10H detected on PCIe
- Physical Pi + AI HAT+ 2 needed for real inference (enrollment, Hailo validation)
