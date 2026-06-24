# Audio Capture Pipeline — Latency Profiling

**Status:** Instrumentation complete. Measurements require physical Pi 5 + AI HAT+ 2 hardware.

## How to Collect Measurements

Enable DEBUG logging by setting `LOG_LEVEL=DEBUG` before running, or change
`logging.basicConfig(level=logging.INFO)` in `pi/main.py` to `DEBUG`. Then run
10 real utterances and grep the output:

```bash
python -m pi.main 2>&1 | grep "LATENCY" | tee /tmp/latency-audio.log
```

Key log lines emitted (all prefixed `LATENCY`):

| Log key | Source | Meaning |
|---------|--------|---------|
| `wake_to_capture_start` | `pi/main.py` | Time from wake event callback to `_capture_utterance()` entry |
| `vad_stream_open` | `pi/audio/capture.py` | Time for `PyAudio.open()` to return |
| `capture_stream_first_chunk` | `pi/main.py` | Time from `_capture_utterance()` entry to first audio chunk received in asyncio loop |
| `vad_trigger_fired` (`stream_age`) | `pi/audio/capture.py` | Time from stream open to VAD speech-trigger |
| `utterance_end` | `pi/audio/capture.py` | Per-frame read/VAD stats + silence tail for each utterance |
| `resample_48k_to_16k` | `pi/main.py` | Time for `scipy.signal.resample_poly` 48→16 kHz |
| `capture_total` | `pi/main.py` | Total time from `_capture_utterance()` entry to PCM ready |

## Measurement Tables

Run 10 utterances and record each `LATENCY` value. Report min / median / max.

### Stage 1 — Wake Event to Capture Start (`wake_to_capture_start`)

> Covers: asyncio event dispatch + `detector.stop()` thread join + function call overhead.

| Run | ms |
|-----|----|
| 1   |    |
| 2   |    |
| 3   |    |
| 4   |    |
| 5   |    |
| 6   |    |
| 7   |    |
| 8   |    |
| 9   |    |
| 10  |    |

**min:** — ms  **median:** — ms  **max:** — ms

---

### Stage 2 — VAD Stream Open (`vad_stream_open`)

> Covers: `PyAudio.open()` which allocates ALSA resources and starts the audio stream.

| Run | ms |
|-----|----|
| 1   |    |
| 2   |    |
| 3   |    |
| 4   |    |
| 5   |    |
| 6   |    |
| 7   |    |
| 8   |    |
| 9   |    |
| 10  |    |

**min:** — ms  **median:** — ms  **max:** — ms

---

### Stage 3 — First Chunk Latency (`capture_stream_first_chunk`)

> Covers: thread spawn + pa.open() + first `stream.read()` block + asyncio queue put/get.
> This is the total delay from `_capture_utterance()` entry to receiving the first 10ms frame.

| Run | ms |
|-----|----|
| 1   |    |
| 2   |    |
| 3   |    |
| 4   |    |
| 5   |    |
| 6   |    |
| 7   |    |
| 8   |    |
| 9   |    |
| 10  |    |

**min:** — ms  **median:** — ms  **max:** — ms

---

### Stage 4 — Per-Frame Loop Stats (`utterance_end`)

> Recorded once per utterance. Shows how long each `stream.read()` blocks (should be ~10ms
> at 48 kHz / 480 samples) and how long `webrtcvad.is_speech()` takes.

#### Frame read time (`stream.read()`)

| Run | frames | avg (ms) | min (ms) | max (ms) |
|-----|--------|----------|----------|----------|
| 1   |        |          |          |          |
| 2   |        |          |          |          |
| 3   |        |          |          |          |
| 4   |        |          |          |          |
| 5   |        |          |          |          |
| 6   |        |          |          |          |
| 7   |        |          |          |          |
| 8   |        |          |          |          |
| 9   |        |          |          |          |
| 10  |        |          |          |          |

Expected: avg ≈ 10ms (frame duration); max spikes may indicate ALSA underrun or scheduling jitter.

#### VAD classification time (`webrtcvad.is_speech()`)

| Run | avg (ms) | min (ms) | max (ms) |
|-----|----------|----------|----------|
| 1   |          |          |          |
| 2   |          |          |          |
| 3   |          |          |          |
| 4   |          |          |          |
| 5   |          |          |          |
| 6   |          |          |          |
| 7   |          |          |          |
| 8   |          |          |          |
| 9   |          |          |          |
| 10  |          |          |          |

Expected: < 1ms (purely computational, no I/O).

#### Silence tail estimate

| Run | audio_ms | total_triggered_ms | silence_tail_ms |
|-----|----------|--------------------|-----------------|
| 1   |          |                    |                 |
| 2   |          |                    |                 |
| 3   |          |                    |                 |
| 4   |          |                    |                 |
| 5   |          |                    |                 |
| 6   |          |                    |                 |
| 7   |          |                    |                 |
| 8   |          |                    |                 |
| 9   |          |                    |                 |
| 10  |          |                    |                 |

Note: `silence_tail` = `total_triggered_ms - audio_ms`. Default `silence_duration_ms=1200` means
≈1200ms of silence is appended to every utterance. This dominates perceived latency.

---

### Stage 5 — Resample 48 kHz → 16 kHz (`resample_48k_to_16k`)

> Covers: `np.frombuffer` + `.astype(float32)` + `scipy.signal.resample_poly` + `.astype(int16)` + `.tobytes()`.

| Run | ms | output_bytes |
|-----|----|--------------|
| 1   |    |              |
| 2   |    |              |
| 3   |    |              |
| 4   |    |              |
| 5   |    |              |
| 6   |    |              |
| 7   |    |              |
| 8   |    |              |
| 9   |    |              |
| 10  |    |              |

**min:** — ms  **median:** — ms  **max:** — ms

Hypothesis: `resample_poly` may be slow on Pi 5 ARM without SIMD optimisation.
Alternative: simple decimation `audio[::3]` (48/16=3), which is an integer ratio and
may be orders of magnitude faster with negligible quality loss for speech.

---

### Stage 6 — Total Capture Time (`capture_total`)

> Total from `_capture_utterance()` entry to PCM bytes ready (includes VAD wait + resample).

| Run | ms | utterance_audio_s |
|-----|----|--------------------|
| 1   |    |                    |
| 2   |    |                    |
| 3   |    |                    |
| 4   |    |                    |
| 5   |    |                    |
| 6   |    |                    |
| 7   |    |                    |
| 8   |    |                    |
| 9   |    |                    |
| 10  |    |                    |

**min:** — ms  **median:** — ms  **max:** — ms

---

## Summary Budget (to fill in)

| Stage | Median (ms) | % of total capture |
|-------|-------------|-------------------|
| wake_to_capture_start |  |  |
| vad_stream_open |  |  |
| speech detection wait (VAD trigger) |  |  |
| utterance audio duration |  |  |
| silence tail (~1200ms default) |  |  |
| resample_48k_to_16k |  |  |
| **Total capture** |  | 100% |

## Expected Findings (Hypotheses)

Based on the design, these are the likely bottlenecks:

1. **Silence tail dominates** (~1200ms by default). Every utterance waits for this even for short
   commands. Reducing `silence_duration_ms` to 800ms would save ~400ms with minimal UX impact.
2. **VAD stream open** may take 50–200ms (ALSA resource allocation). Could be kept open permanently
   (open once at startup, share stream between detector and capture).
3. **resample_poly overhead** may be significant for 3–5s utterances on Pi 5. At 48kHz, a 3s
   utterance = 144,000 samples × 2 bytes = 288KB. Simple integer decimation `[::3]` should be
   measured as an alternative.
4. **wake_to_capture_start** should be < 50ms (pure Python overhead). If it's higher, `detector.stop()`
   thread join is the culprit.
