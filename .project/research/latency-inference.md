# Inference Pipeline — Latency Profiling

**Status:** Instrumentation complete. Measurements require physical Pi 5 + AI HAT+ 2 hardware.

## How to Collect Measurements

Enable DEBUG logging, then run 5 queries per tool type and capture the `LATENCY` log lines:

```bash
LOG_LEVEL=DEBUG python -m pi.main 2>&1 | grep "LATENCY" | tee /tmp/latency-inference.log
```

Or set the log level in `pi/main.py`:
```python
logging.basicConfig(level=logging.DEBUG, ...)
```

To separate cold-start from warm, record the **first** activation in a session (cold) and runs 2–5 (warm).

## Log Keys Reference

All lines are prefixed `LATENCY`. Below is every key emitted by the inference pipeline.

| Log key | Source file | Meaning |
|---------|------------|---------|
| `identify_stt_parallel` | `pi/main.py` | Wall-clock time for `asyncio.gather(identify, stt.transcribe)` — the longer of the two branches |
| `speaker_id_embed_cold` | `pi/speaker_id/identify.py` | First-call `VoiceEncoder()` load + `embed_utterance` |
| `speaker_id_embed_warm` | `pi/speaker_id/identify.py` | Subsequent `embed_utterance` calls |
| `speaker_id_match` | `pi/speaker_id/identify.py` | Cosine similarity against all enrolled profiles |
| `stt_cold_load` | `pi/stt/hailo_transcriber.py` | Hailo Whisper model load (first call only) |
| `stt_pcm_to_float32` | `pi/stt/hailo_transcriber.py` | `np.frombuffer` + scale to float32 |
| `stt_transcribe_cold` | `pi/stt/hailo_transcriber.py` | `generate_all_text` on first call (Hailo NPU) |
| `stt_transcribe_warm` | `pi/stt/hailo_transcriber.py` | `generate_all_text` on subsequent calls |
| `llm_route` | `pi/main.py` | Total `router.route()` call (prompt-build + generate) |
| `llm_prompt_build` | `pi/llm/hailo_client.py` | Tool schema injection into system prompt |
| `llm_cold_load` | `pi/llm/hailo_client.py` | Hailo LLM model load (first call only) |
| `llm_generate_cold` | `pi/llm/hailo_client.py` | `generate_all` on first call (Hailo NPU) |
| `llm_generate_warm` | `pi/llm/hailo_client.py` | `generate_all` on subsequent calls |
| `tool_run` | `pi/main.py` | `tool.run()` including HTTP fetch for weather/CTA/calendar |
| `tts_synthesize` | `pi/main.py` | Piper TTS `synthesize_wav` call |
| `tts_resample_22050to48000` | `pi/audio/playback.py` | `scipy.signal.resample_poly` 22050→48000 Hz |
| `audio_playback` | `pi/audio/playback.py` | `sd.play + sd.wait` (actual speaker output) |
| `audio_play_total` | `pi/main.py` | Total executor round-trip for `player.play` |

## Measurement Tables

Run 5 queries per category and record values from the log. Report min / median / max.

---

### Stage 1 — Parallel Speaker-ID + STT (`identify_stt_parallel`)

> This is the wall-clock time for `asyncio.gather(identify, stt.transcribe)`.
> The bottleneck is whichever of the two takes longer.

#### Cold start (first activation in session)

| Run | ms |
|-----|----|
| 1   |    |

**cold total:** — ms

#### Warm (runs 2–5)

| Run | ms |
|-----|----|
| 2   |    |
| 3   |    |
| 4   |    |
| 5   |    |

**warm min:** — ms  **median:** — ms  **max:** — ms

---

### Stage 1a — Speaker-ID Embed (`speaker_id_embed_cold` / `speaker_id_embed_warm`)

> `VoiceEncoder` is a global singleton; cold = first ever call (model load + embed).
> Warm = just `embed_utterance` (forward pass through resemblyzer GE2E model on CPU).

| Label | ms |
|-------|----|
| cold  |    |
| warm run 2 |    |
| warm run 3 |    |
| warm run 4 |    |
| warm run 5 |    |

**warm min:** — ms  **median:** — ms  **max:** — ms

---

### Stage 1b — Speaker-ID Profile Match (`speaker_id_match`)

> Cosine dot-product against each enrolled `.npy` profile. Should be sub-millisecond.

| Run | ms |
|-----|----|
| 1   |    |
| 2   |    |
| 3   |    |
| 4   |    |
| 5   |    |

**min:** — ms  **median:** — ms  **max:** — ms

---

### Stage 1c — STT PCM Conversion (`stt_pcm_to_float32`)

> `np.frombuffer` + scale. Should be < 1 ms even for a 5s utterance.

| Run | ms | samples |
|-----|----|---------|
| 1   |    |         |
| 2   |    |         |
| 3   |    |         |
| 4   |    |         |
| 5   |    |         |

---

### Stage 1d — STT Transcription (`stt_transcribe_cold` / `stt_transcribe_warm`)

> Hailo Whisper `generate_all_text` on the NPU.
> Cold = includes any NPU context setup; warm = model already resident.

| Label | ms |
|-------|----|
| cold (run 1) |    |
| warm (run 2) |    |
| warm (run 3) |    |
| warm (run 4) |    |
| warm (run 5) |    |

**warm min:** — ms  **median:** — ms  **max:** — ms

**Prewarm value** (cold − warm median): — ms saved per first activation

---

### Stage 2 — LLM Route Total (`llm_route`)

> Total `router.route()` call: build system prompt + inject tool schemas + `generate_all`.

#### Simple conversational query (no tool)

| Run | ms |
|-----|----|
| 1 (cold) |    |
| 2        |    |
| 3        |    |
| 4        |    |
| 5        |    |

**warm min:** — ms  **median:** — ms  **max:** — ms

#### Tool-selecting query (e.g. "What's the weather?")

| Run | ms |
|-----|----|
| 1 (cold) |    |
| 2        |    |
| 3        |    |
| 4        |    |
| 5        |    |

**warm min:** — ms  **median:** — ms  **max:** — ms

---

### Stage 2a — LLM Prompt Build (`llm_prompt_build`)

> Injecting tool schemas into system prompt (string concatenation only — no NPU).

| Run | ms | system_chars |
|-----|----|--------------|
| 1   |    |              |
| 2   |    |              |
| 3   |    |              |
| 4   |    |              |
| 5   |    |              |

Expected: < 1 ms (pure string ops). Large number of tools or long instructions increase this.

---

### Stage 2b — LLM Generation (`llm_generate_cold` / `llm_generate_warm`)

> `generate_all` on Hailo-10H NPU. Cold = first model call per session.
> `tokens_out` is approximate (word count of output string).

| Label | ms | tokens_out |
|-------|----|------------|
| cold (run 1) |    |    |
| warm (run 2) |    |    |
| warm (run 3) |    |    |
| warm (run 4) |    |    |
| warm (run 5) |    |    |

**warm min:** — ms  **median:** — ms  **max:** — ms

**Tokens/second (warm):** — tok/s  (= tokens_out / ms × 1000)

**Prewarm value** (cold − warm median): — ms saved per first activation

---

### Stage 3 — Tool Execution (`tool_run`)

> `tool.run()` including any HTTP I/O. Run 5 queries per tool type.

#### Weather (`get_weather` via OpenWeatherMap)

| Run | ms |
|-----|----|
| 1   |    |
| 2   |    |
| 3   |    |
| 4   |    |
| 5   |    |

**min:** — ms  **median:** — ms  **max:** — ms

#### CTA (`cta_arrivals` via CTA Train Tracker API)

| Run | ms |
|-----|----|
| 1   |    |
| 2   |    |
| 3   |    |
| 4   |    |
| 5   |    |

**min:** — ms  **median:** — ms  **max:** — ms

#### Google Calendar (`get_calendar_events` via Google Calendar API)

| Run | ms |
|-----|----|
| 1   |    |
| 2   |    |
| 3   |    |
| 4   |    |
| 5   |    |

**min:** — ms  **median:** — ms  **max:** — ms

Note: Tool run time for weather/CTA/calendar includes an LLM narration call
(`llm.complete(system, json_data)`) in addition to the HTTP fetch — the `tool_run`
latency will therefore include one additional `llm_generate_warm` cycle.

---

### Stage 4 — TTS Synthesis (`tts_synthesize`)

> Piper TTS `synthesize_wav` call (ONNX on CPU, or CUDA if `use_cuda=true`).

| Run | ms | bytes | response_chars |
|-----|----|----|----------------|
| 1   |    |    |                |
| 2   |    |    |                |
| 3   |    |    |                |
| 4   |    |    |                |
| 5   |    |    |                |

**min:** — ms  **median:** — ms  **max:** — ms

**Throughput:** (bytes / 2 / 22050) / (ms / 1000) = audio_seconds / synthesis_seconds
A ratio > 1 means synthesis is faster than real-time.

---

### Stage 5 — TTS Resample (`tts_resample_22050to48000`)

> `scipy.signal.resample_poly` 22050 → 48000 Hz inside `AudioPlayer.play()`.

| Run | ms | out_samples |
|-----|----|----|
| 1   |    |    |
| 2   |    |    |
| 3   |    |    |
| 4   |    |    |
| 5   |    |    |

**min:** — ms  **median:** — ms  **max:** — ms

---

### Stage 6 — Playback (`audio_playback`)

> `sd.play + sd.wait` — should be ≈ audio duration (real-time playback).
> `audio_play_total` in main.py adds the executor overhead on top.

| Run | ms | audio_s |
|-----|----|----|
| 1   |    |    |
| 2   |    |    |
| 3   |    |    |
| 4   |    |    |
| 5   |    |    |

Expected: `audio_playback` ≈ `audio_s × 1000` ms. Large deviation = sounddevice buffering issue.

---

## End-to-End Budget Template

Fill in once measurements are collected (warm path, weather query as representative example):

| Stage | Median (ms) | % of total |
|-------|-------------|-----------|
| `identify_stt_parallel` (warm) | | |
| `llm_route` (warm) | | |
| `tool_run` (weather, warm) | | |
| `tts_synthesize` (warm) | | |
| `tts_resample_22050to48000` | | |
| `audio_playback` | | |
| **Total (excl. capture)** | | 100% |

Note: Capture pipeline total is tracked separately in `latency-audio.md`.

---

## Expected Findings (Hypotheses)

1. **LLM generation dominates** — Qwen2-1.5B on Hailo-10H at ~13 TOPS is estimated at
   50–200 tok/s with `max_tokens=200`. At 50 tok/s, 200 tokens = 4000ms. Reducing
   `max_tokens` from 200 → 80 could halve LLM latency for short tool-selected responses.

2. **Tool run includes a second LLM call** — weather, CTA, and calendar tools all call
   `llm.complete()` internally for narration. This doubles LLM time for tool queries.
   Measuring `tool_run` will expose this.

3. **STT is fast for short utterances** — Whisper on Hailo is designed for ~30s chunks
   but most commands are < 5s. Expect 300–800ms warm.

4. **Prewarm is high-value** — Cold LLM load on Hailo may take 2–5s (model deserialization).
   PrewarmScheduler firing 5 minutes before expected usage would eliminate this from the
   perceived latency budget entirely.

5. **TTS resample may be significant** — `resample_poly` at 22050→48000 for a 2s response
   is ~44100 samples in, ~96000 out. Could take 10–50ms on ARM. An alternative is to
   configure Piper to output at 48000 Hz directly (if the model supports it).

6. **Speaker-ID warm path is cheap** — resemblyzer GE2E is a small LSTM; warm embed
   expected 50–200ms on Pi 5 ARM. Cold may be 500ms+ (model load from disk).
