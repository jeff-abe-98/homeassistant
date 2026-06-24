# Third-Party & System Overhead — Latency Audit

**Status:** Instrumentation complete. Measurements require physical Pi 5 + AI HAT+ 2 hardware.

## How to Collect Measurements

Enable DEBUG logging and run the assistant, then grep for the new overhead keys:

```bash
LOG_LEVEL=DEBUG python -m pi.main 2>&1 | grep "LATENCY" | tee /tmp/latency-overhead.log
```

Run at least 5 activations for each measurement category. For token-budget tests,
temporarily edit `_generate_sync` in `pi/llm/hailo_client.py` and change the default
`max_tokens` argument, then re-run 5 queries each.

---

## 1 — PyAudio Stream Open / Close per Activation

**Context:** Both `WakeWordDetector` and `VoiceCapture` open a PyAudio stream at the start
of each activation and close it when done. Opening a stream requires ALSA device enumeration
and DMA buffer allocation — this is the hardware-level cost paid on every wake word.

**Log keys (all prefixed `LATENCY`):**

| Key | Source | What it covers |
|-----|--------|---------------|
| `wakeword_stream_open` | `pi/wake_word/detector.py` | `PyAudio.open()` for the 16 kHz wake-word mic stream |
| `wakeword_stream_close` | `pi/wake_word/detector.py` | `stream.stop_stream()` + `stream.close()` |
| `vad_stream_open` | `pi/audio/capture.py` | `PyAudio.open()` for the 48 kHz VAD capture stream |

**Measurement table (5 activations):**

| Activation | wakeword_stream_open (ms) | wakeword_stream_close (ms) | vad_stream_open (ms) |
|------------|--------------------------|---------------------------|----------------------|
| 1          |                          |                           |                      |
| 2          |                          |                           |                      |
| 3          |                          |                           |                      |
| 4          |                          |                           |                      |
| 5          |                          |                           |                      |

**min / median / max per key:**

| Key | min (ms) | median (ms) | max (ms) |
|-----|----------|-------------|----------|
| wakeword_stream_open |  |  |  |
| wakeword_stream_close |  |  |  |
| vad_stream_open |  |  |  |
| **combined open per activation** |  |  |  |

**Expected:** Each `PyAudio.open()` call on Pi 5 with a USB microphone typically takes
50–150 ms due to ALSA device probing and buffer setup. Combined (wake-word open + VAD open)
may total 100–300 ms per activation. Stream close is faster (5–30 ms).

**Optimisation candidate:** Keep both streams open permanently (open at startup, reuse across
activations). Wake-word detector would drain-and-ignore frames during the VAD capture phase
rather than reopening. Expected saving: 100–300 ms per activation.

---

## 2 — resample_poly vs Integer Decimation (48 kHz → 16 kHz)

**Context:** After VAD capture, `_capture_utterance()` in `pi/main.py` resamples 48 kHz
PCM to the 16 kHz required by Whisper STT. The current code uses `scipy.signal.resample_poly`
which applies a polyphase anti-aliasing filter. An alternative is simple 3:1 integer
decimation (`audio[::3]`) which is much faster but skips anti-aliasing.

The wake-word detector already samples at 16 kHz natively (PyAudio stream at `_SAMPLE_RATE=16000`)
so there is no resample in the wake-word path.

The TTS playback path (22050 Hz → 48 kHz) uses a non-integer ratio (147:80), so `audio[::3]`
is not applicable there.

**Log keys:**

| Key | Source | What it covers |
|-----|--------|---------------|
| `decimation_48k_to_16k` | `pi/main.py` | `audio_int16[::3]` numpy slice — reference timing only, result discarded |
| `resample_48k_to_16k` | `pi/main.py` | `astype(float32)` + `resample_poly` + `astype(int16)` |

**Measurement table (5 activations, ~2s utterances each):**

| Activation | utterance_audio_s | decimation_48k_to_16k (ms) | resample_48k_to_16k (ms) | speedup ratio |
|------------|--------------------|---------------------------|--------------------------|---------------|
| 1          |                    |                           |                          |               |
| 2          |                    |                           |                          |               |
| 3          |                    |                           |                          |               |
| 4          |                    |                           |                          |               |
| 5          |                    |                           |                          |               |

**Expected:**
- `resample_poly` on Pi 5: ~5–30 ms for a 2s utterance (scipy uses BLAS internally; Pi 5 ARM
  with NEON SIMD should be reasonably fast, but no GPU acceleration)
- `audio[::3]` decimation: <1 ms (pure numpy slice, no computation beyond memory copy)
- Speedup: 10–50× in favour of decimation

**Quality trade-off:** Simple decimation introduces aliasing above 8 kHz. Whisper's training
data is voice-band (< 8 kHz), so aliasing at higher frequencies is unlikely to degrade
transcription accuracy meaningfully. Recommend measuring Word Error Rate (WER) with both
approaches using a small test set of 20 utterances before switching.

---

## 3 — asyncio.run_in_executor Thread-Pool Queue Wait

**Context:** Three calls in `_handle_activation()` use `loop.run_in_executor()` to run
blocking code in a thread pool: `identify()`, `tts.synthesize()`, and `player.play()`.
The queue-wait is the gap between submitting the task to the pool and the thread actually
starting execution. With Python's default `ThreadPoolExecutor`, idle threads respond quickly,
but if all threads are busy the task queues behind them.

**Log key:** `executor_queue_wait` with a `task=` label (`identify`, `tts_synthesize`,
`audio_play`). Emitted at the very first line of the wrapper that runs inside the thread.

**Measurement table (5 activations):**

| Activation | executor_queue_wait identify (ms) | executor_queue_wait tts_synthesize (ms) | executor_queue_wait audio_play (ms) |
|------------|-----------------------------------|-----------------------------------------|--------------------------------------|
| 1          |                                   |                                         |                                      |
| 2          |                                   |                                         |                                      |
| 3          |                                   |                                         |                                      |
| 4          |                                   |                                         |                                      |
| 5          |                                   |                                         |                                      |

**Expected:** < 1 ms in the common case (thread pool idle, single activation at a time).
If > 5 ms, the default pool may be saturated — consider `asyncio.ThreadPoolExecutor(max_workers=4)`
in `main()`. The identify and STT calls run concurrently via `asyncio.gather`, so the executor
must have at least 2 threads free simultaneously.

**Derived metric — executor overhead per activation:**
- outer `tts_synthesize` (ms) − `tts_synthesize_internal` (ms from `pi/tts/piper.py`) = executor overhead
- outer `audio_play_total` (ms) − `audio_playback` (ms from `pi/audio/playback.py`) = executor overhead

---

## 4 — LLM Token Budget Impact (max_tokens = 200 / 100 / 50)

**Context:** `HailoLLMClient._generate_sync()` passes `max_tokens=200` to
`llm.generate_all()`. On the Hailo NPU, generation is token-by-token and the model
runs until it emits EOS or reaches `max_tokens`. Reducing this cap stops generation earlier
if the model happens to produce long output.

**Log key:** `llm_generate_cold` / `llm_generate_warm` now includes `max_tokens=<N>`
so the budget can be correlated with generation time.

**Test procedure:** Change the default in `_generate_sync(max_tokens=...)` to 200, 100, and 50
in turn; run 5 typical queries (weather, CTA, conversational) for each.

**Measurement table — weather query ("What's the weather like?"):**

| max_tokens | run | llm_generate_warm (ms) | tokens_out |
|------------|-----|------------------------|------------|
| 200        | 1   |                        |            |
| 200        | 2   |                        |            |
| 200        | 3   |                        |            |
| 100        | 1   |                        |            |
| 100        | 2   |                        |            |
| 100        | 3   |                        |            |
| 50         | 1   |                        |            |
| 50         | 2   |                        |            |
| 50         | 3   |                        |            |

**Measurement table — conversational query ("What time is it?"):**

| max_tokens | run | llm_generate_warm (ms) | tokens_out |
|------------|-----|------------------------|------------|
| 200        | 1   |                        |            |
| 200        | 2   |                        |            |
| 100        | 1   |                        |            |
| 100        | 2   |                        |            |
| 50         | 1   |                        |            |
| 50         | 2   |                        |            |

**Expected:**
- Qwen2-1.5B on Hailo-10H: approximately 30–60 tokens/sec
- Tool-routing response (short `<tool_call>…</tool_call>` block): ~20–30 tokens → ~0.4–1s at 50 tokens/sec
- Conversational response: ~30–80 tokens → ~0.5–1.5s
- EOS fires before `max_tokens` for typical responses → max_tokens=100 vs 200 makes no
  difference until a response exceeds 100 tokens (uncommon in practice)
- max_tokens=50 risks truncating longer weather narration or calendar summaries — check WER
  before adopting

**Recommendation:** Lower to 100 as a safe default; monitor for truncation. Only reduce to 50
for tool-routing-only paths.

---

## 5 — Piper TTS Model Load

**Context:** `PiperTTS.__init__()` calls `PiperVoice.load()` which loads an ONNX voice model
from disk and initialises an ONNX Runtime session. This happens once at startup in `main()`.
`synthesize()` reuses `self._voice` — it does NOT re-load the model on each call.

**Log keys:**

| Key | Source | What it covers |
|-----|--------|---------------|
| `tts_model_load` | `pi/tts/piper.py` `__init__` | `PiperVoice.load()` (one-time startup cost) |
| `tts_synthesize_internal` | `pi/tts/piper.py` `synthesize()` | `synthesize_wav()` + WAV decode (pure inference, no model reload) |
| `tts_synthesize` | `pi/main.py` | Outer executor wall-clock (includes queue wait) |

**Model load measurement (once per session):**

| Session start | tts_model_load (ms) |
|---------------|---------------------|
| 1             |                     |
| 2             |                     |
| 3             |                     |

**Per-call synthesis measurement (5 typical responses, ~50 chars each):**

| Call | chars | tts_synthesize_internal (ms) | tts_synthesize outer (ms) | executor overhead (ms) |
|------|-------|------------------------------|---------------------------|------------------------|
| 1    |       |                              |                           |                        |
| 2    |       |                              |                           |                        |
| 3    |       |                              |                           |                        |
| 4    |       |                              |                           |                        |
| 5    |       |                              |                           |                        |

**Expected:**
- `tts_model_load`: 500–2000 ms (ONNX Runtime initialisation on Pi 5 CPU; first call may
  trigger JIT compilation, subsequent startups use cached ONNX plan)
- `tts_synthesize_internal`: 150–500 ms per 50-character response (CPU ONNX inference;
  Piper's en_US-lessac-medium model runs in real-time or faster on Pi 5)
- Confirms: model is NOT re-loaded per call — `self._voice` is cached in the instance

**Optimisation note:** If `tts_model_load` exceeds 1s, consider loading Piper lazily after
the first wake word (not at startup) so the assistant announces readiness sooner. Alternatively,
load it in a background thread concurrently with STT/LLM model loading.

---

## Summary Budget Template

Fill in after collecting all measurements (medians):

| Overhead | Median (ms) | Notes |
|----------|-------------|-------|
| `wakeword_stream_open` |  | Per activation |
| `wakeword_stream_close` |  | Per activation |
| `vad_stream_open` |  | Per activation |
| `decimation_48k_to_16k` (reference) |  | If switched from resample_poly |
| `resample_48k_to_16k` (current) |  | Per activation |
| `executor_queue_wait` identify |  | Per activation |
| `executor_queue_wait` tts_synthesize |  | Per activation |
| `executor_queue_wait` audio_play |  | Per activation |
| `tts_model_load` |  | One-time startup |
| `tts_synthesize_internal` per 50 chars |  | Per activation |
| **Total avoidable per-activation overhead** |  | Excludes model load |

## Hypotheses

1. **PyAudio open dominates** (100–300 ms per activation). Keeping streams open would be the
   single biggest quick win — no code quality trade-off.
2. **resample_poly is measurably slower than decimation** (10–50×) but the absolute saving
   is small if total resample is < 30 ms. Only worth switching if WER stays flat.
3. **executor overhead is negligible** (< 1 ms) since the assistant runs one activation at a
   time and the thread pool is never saturated.
4. **max_tokens budget rarely binds** — typical responses fit in < 100 tokens. Setting
   max_tokens=100 is safe and avoids worst-case generation time.
5. **Piper does not re-load per call** — `tts_model_load` is a one-time cost; `synthesize()`
   is pure ONNX inference and scales linearly with text length.
