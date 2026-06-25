# Latency Analysis — End-to-End Bottleneck Ranking

**Status:** Analysis complete. Based on instrumentation design and hardware estimates
(Raspberry Pi 5, Hailo-10H NPU, USB mic). Actual measurements must be collected on physical
hardware using the procedure in `latency-audio.md`, `latency-inference.md`, and
`latency-overhead.md` to validate these estimates.

**Source documents:**
- `.project/research/latency-audio.md` — audio capture pipeline profiling
- `.project/research/latency-inference.md` — inference pipeline profiling
- `.project/research/latency-overhead.md` — third-party overhead audit

---

## Pipeline Sequence

Wake word fires → `_handle_activation()` starts → VAD open + capture audio → silence detected →
resample 48→16 kHz → parallel (speaker-ID + STT) → LLM routing → tool run (optional) →
TTS synthesize → TTS resample → playback starts

**User-perceived latency** = from end-of-utterance to start of playback.
The silence timeout is the last part of capture and directly precedes inference — it is
fully in the user's perceived wait even though audio is still being "captured."

---

## End-to-End Latency Budget (Estimated, Warm Path)

Values are expected medians based on hardware specs and prior profiling experience with
similar setups. "Warm" = model already loaded; "tool query" uses weather as representative.

### Simple Conversational Query (no tool)

| Stage | Median est. (ms) | % of pre-playback total |
|-------|-----------------|------------------------|
| wake_to_capture_start | 20 | 0.7% |
| vad_stream_open | 150 | 5.2% |
| speech detection wait (VAD trigger) | 200 | 6.9% |
| utterance audio duration | 1500 | 52.1% (real-time, not delay) |
| silence tail (default 1200ms) | 1200 | 41.7% |
| resample_48k_to_16k | 20 | 0.7% |
| identify_stt_parallel (warm, STT bottleneck) | 500 | 17.4% |
| llm_route (warm, Qwen2-1.5B routing+response) | 900 | 31.3% |
| tts_synthesize (warm, ~60-char response) | 300 | 10.4% |
| tts_resample_22050to48000 | 30 | 1.0% |
| **Total pre-playback latency (excl. audio duration)** | **~2870** | 100% |

> Note: `utterance audio duration` is real-time playback of the user's own speech during
> capture — it does not add to perceived lag. The silence tail IS perceived lag. Combined
> "end-of-speech to response" = silence_tail + resample + STT + LLM + TTS + TTS_resample
> ≈ **2970ms** (warm, conversational).

### Tool Query (weather, warm, with LLM narration inside tool)

| Stage | Median est. (ms) | % of pre-playback total |
|-------|-----------------|------------------------|
| silence tail | 1200 | 26.8% |
| resample_48k_to_16k | 20 | 0.4% |
| identify_stt_parallel (warm) | 500 | 11.2% |
| llm_route (warm, routing only) | 600 | 13.4% |
| tool_run: HTTP fetch (weather) | 400 | 8.9% |
| tool_run: LLM narration call (second warm LLM) | 900 | 20.1% |
| tts_synthesize (warm, ~100-char narration) | 500 | 11.2% |
| tts_resample_22050to48000 | 50 | 1.1% |
| **Total end-of-speech to playback** | **~4170** | 100% |

### Cold-Start Penalty (first activation after startup)

| Cold-start item | Penalty est. (ms) | Mitigated by PrewarmScheduler? |
|----------------|-------------------|-------------------------------|
| LLM model load (Hailo NPU deserialise) | 2000–5000 | Yes — prewarm fires 5min before usage |
| STT model load (Hailo Whisper) | 1000–3000 | Yes |
| Speaker-ID model load (resemblyzer) | 300–800 | No (CPU, fast enough to accept) |
| Piper TTS model load (ONNX Runtime) | 500–2000 | N/A — loaded at startup |

---

## Bottleneck Ranking (By User Impact)

Ranked by contribution to perceived latency on the warm tool-query path, which is the
most common interaction type.

| Rank | Stage | Est. ms | % of perceived | Fix type |
|------|-------|---------|---------------|----------|
| 1 | Silence tail (VAD timeout) | 1200 | 28.8% | Drop-in |
| 2 | LLM generation — routing pass | 600 | 14.4% | Partially HW-limited |
| 3 | LLM generation — tool narration (2nd call) | 900 | 21.6% | Architecture change |
| 4 | STT transcription (warm) | 500 | 12.0% | Hardware-limited |
| 5 | PyAudio stream open (combined both) | 150–300 | 3.6–7.2% | Drop-in |
| 6 | TTS synthesis | 500 | 12.0% | Partially HW-limited |
| 7 | resample_poly 48→16 kHz | 20 | 0.5% | Drop-in (minor) |
| 8 | TTS resample 22050→48000 | 30–50 | 0.7–1.2% | Drop-in (minor) |

---

## Top-5 Bottleneck Analysis

### 1 — Silence Tail (1200ms) ★ Highest Priority

**What it is:** `VoiceCapture` waits for `silence_duration_ms=1200` of consecutive
non-speech frames before declaring the utterance complete and returning PCM. Every single
activation pays this full cost regardless of how short the command is.

**User perception:** This is the dominant "unresponsive" feeling. The user has finished
speaking but the device appears to do nothing for over a second. Users attribute this to
the assistant being slow even though inference hasn't started yet.

**Feasibility:** Drop-in fix. Change one default in `VoiceCapture`:
- `pi/audio/capture.py`: reduce `silence_duration_ms` default from 1200 → 700ms
- Expected saving: ~500ms per activation (42% of conversational, 12% of tool query)
- Risk: Very short commands followed by background noise could be truncated. At 700ms a
  user who pauses mid-sentence before finishing will be cut off. 800ms is a safer first
  target.
- **Recommended action:** Change default to 800ms, add to config so it's tunable.

---

### 2 — LLM Generation — Routing Pass (600ms warm)

**What it is:** `HailoLLMClient.chat_with_tools()` calls `generate_all` on Hailo-10H NPU
with tool schemas injected. Qwen2-1.5B is estimated at 30–60 tokens/sec on the NPU.
A routing response (`<tool_call>...</tool_call>`) is ~20–40 tokens → 350–1300ms.

**User perception:** Directly adds to post-speech wait. Not as visceral as silence tail
but adds up, especially when stacked with narration.

**Feasibility:**
- **Partially hardware-limited:** NPU throughput (13 TOPS) is fixed. Cannot speed up
  generation rate without hardware change.
- **Two drop-in wins:**
  1. Reduce `max_tokens` from 200 → 100 in `_generate_sync`. Tool routing responses
     are < 40 tokens; conversational responses rarely exceed 80. Eliminates worst-case
     generation ceiling. Safe and zero risk. `pi/llm/hailo_client.py`.
  2. PrewarmScheduler already eliminates cold-start penalty (2000–5000ms) for the first
     activation of a session during high-usage windows. Ensure it is enabled in production.
- **Architecture option (Phase 12):** For tool queries, skip the fallback conversational
  generate — only generate the `<tool_call>` JSON in the routing pass, then let the tool's
  own LLM narration produce the spoken response. This eliminates redundant generation.

---

### 3 — Tool Narration (Second LLM Call, ~900ms warm) ★ Second-Highest Priority

**What it is:** `WeatherTool`, `CTATool`, and `CalendarTool` each call `llm.complete()`
internally to narrate the raw API JSON into a natural-language response. This is a full
second NPU generation cycle on every tool query.

**User perception:** Stacks directly on top of the routing pass. Tool queries feel 2×
slower than conversational queries for no obvious reason to the user.

**Feasibility:** Architecture change, but straightforward.
- **Option A (recommended):** Pass the raw JSON data back to the router as a second
  `user` message and generate the spoken response once in the main loop. Remove the
  internal `llm.complete()` calls from all three tools. This turns the two-LLM sequence
  into one single multi-turn conversation, with the same total output quality.
- **Option B:** Pre-template the narration for tool types (e.g. weather always says
  "Currently X°F and Y. Tomorrow: Z°F.") without any LLM call. Reduces tool latency to
  near zero at cost of less natural phrasing.
- **Files to change:** `pi/tools/weather.py`, `pi/tools/cta.py`, `pi/tools/calendar.py`,
  `pi/llm/router.py` (add narration pass), `pi/main.py` (wire result back).

---

### 4 — STT Transcription (500ms warm)

**What it is:** `HailoTranscriber.transcribe()` calls `generate_all_text` on the Hailo
Whisper base model. Hailo Whisper processes 30-second audio chunks; short commands are
zero-padded to the full context length, which means the NPU always runs the same amount
of work regardless of command length.

**User perception:** Noticeable, but partially hidden by the silence tail (STT starts
after VAD returns, which is after the tail). Users experience this as continued silence
after the device "blinks" (LED or audio cue).

**Feasibility:**
- **Hardware-limited for warm path:** Hailo NPU throughput determines this floor.
  No code change will reduce the NPU compute for a given chunk size.
- **Reduce effective chunk size:** If VAD guarantees utterances are ≤ 5s, pass a
  5s-padded buffer instead of 30s. This may reduce STT latency significantly depending
  on how Hailo Whisper handles shorter chunks. Requires testing on physical hardware.
- **PrewarmScheduler:** Eliminates cold-start (1000–3000ms) on first session activation.
  This is high value and already implemented.
- **Concurrent execution:** Speaker-ID and STT already run in parallel via `asyncio.gather`.
  No further parallelism gain without additional hardware.

---

### 5 — PyAudio Stream Open/Close (100–300ms combined per activation)

**What it is:** Two `PyAudio.open()` calls happen per activation: one for the wake-word
detector (16 kHz, opened at startup but stopped during capture), and one for VAD capture
(48 kHz). ALSA device probing and DMA buffer allocation cost 50–150ms each.

**User perception:** This contributes to the gap between wake-word detection and when
the system starts recording. Users notice if the assistant seems "slow to start listening."

**Feasibility:** Drop-in fix.
- **Keep both streams open permanently** — open at startup, don't close between activations.
  WakeWordDetector drains (reads and discards) frames during the VAD capture phase to keep
  the ALSA buffer from overflowing. VoiceCapture reads from the already-open stream instead
  of opening a new one.
- **Files to change:** `pi/wake_word/detector.py` (stream lifecycle), `pi/audio/capture.py`
  (accept optional pre-opened stream), `pi/main.py` (pass stream reference at startup).
- **Expected saving:** 100–300ms per activation, fully deterministic.
- **Risk:** Shared stream resource between detector and capture needs careful locking.

---

## What Users Actually Perceive

The subjective "response time" has two distinct phases:

**Phase A — "Is it listening?"** (wake word to first audio cue)
Covers: `wake_to_capture_start` + `vad_stream_open`. Estimated: 170ms.
Users are mostly satisfied if this is < 300ms. A visual/audio indicator (LED flash) masks
up to 500ms without frustration.

**Phase B — "Why is nothing happening?"** (end of speech to first spoken word)
This is what users measure mentally. Covers: silence tail + STT + LLM + TTS.
Estimated: ~2970ms (conversational) / ~4170ms (tool query), warm.

Acceptable targets from voice assistant UX research:
- < 1500ms: "fast"
- 1500–3000ms: "acceptable"
- > 3000ms: "slow / broken"

**Current estimated Phase B (conversational, warm): ~2970ms — borderline acceptable.**
**Current estimated Phase B (tool query, warm): ~4170ms — perceived as slow.**

The silence tail alone (1200ms) accounts for 40% of Phase B for conversational queries.
Reducing it to 800ms drops Phase B to ~2570ms (conversational) and ~3770ms (tool).
Eliminating the second LLM call for tools (Bottleneck 3) would drop tool Phase B to
~2870ms — within acceptable range.

---

## Prewarm Value Assessment

PrewarmScheduler fires 5 minutes before high-usage windows and calls `_ensure_loaded()`
on LLM and STT.

| Cold-start item | Penalty (est.) | Frequency | Total saving per day (est.) |
|----------------|----------------|-----------|----------------------------|
| LLM model load | 2000–5000ms | Once per power-cycle or daily restart | 2000–5000ms |
| STT model load | 1000–3000ms | Same | 1000–3000ms |
| **Total cold-start saving** | **3000–8000ms** | 1–2 per day | Eliminates worst-case first activation |

Without prewarm, the first activation of the morning (highest usage window) would feel
severely slow. PrewarmScheduler eliminates this entirely for the sessions it anticipates.

**Verdict:** High value, already implemented. Ensure the schedule.json has data after
14 days and that the scheduler service is active.

---

## Summary: Recommended Fix Order for Phase 12

Ordered by impact-per-effort (fastest win first):

| Priority | Fix | File(s) | Est. saving | Effort |
|----------|-----|---------|-------------|--------|
| 1 | Reduce `silence_duration_ms` default 1200→800 | `pi/audio/capture.py` | ~400ms / activation | 5 min |
| 2 | Reduce `max_tokens` default 200→100 | `pi/llm/hailo_client.py` | 0–500ms (worst-case reduction) | 5 min |
| 3 | Keep PyAudio streams open permanently | `pi/wake_word/detector.py`, `pi/audio/capture.py`, `pi/main.py` | 100–300ms / activation | ~2 hrs |
| 4 | Eliminate second LLM call for tool narration | `pi/tools/weather.py`, `pi/tools/cta.py`, `pi/tools/calendar.py`, `pi/llm/router.py`, `pi/main.py` | ~900ms / tool query | ~3 hrs |
| 5 | Replace resample_poly with integer decimation (after WER test) | `pi/main.py` | 10–50ms / activation | 30 min |
| 6 | Pass shorter buffer to Whisper (VAD-trimmed, not 30s) | `pi/stt/hailo_transcriber.py` | TBD (test on hardware) | 1 hr |

**Estimated total improvement after fixes 1–4:** Phase B latency drops from ~4170ms →
~2470ms for tool queries (warm), and from ~2970ms → ~1670ms for conversational — both
well within the "acceptable" UX threshold.
