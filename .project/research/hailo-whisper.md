# Hailo Whisper STT Python API — Research Notes

**Researched:** 2026-06-16
**Hardware target:** Hailo-10H (AI HAT+ 2, 40 TOPS)

---

## Two Implementation Approaches

### A — GenAI API (`hailo_platform.genai.Speech2Text`) ← Chosen
Part of the same `hailo-genai` apt package used for LLM inference. Hailo-10H only.

```python
from hailo_platform import VDevice
from hailo_platform.genai import Speech2Text

vdevice = VDevice()
stt = Speech2Text(vdevice=vdevice, model="/path/to/whisper-base.hef")

# Audio must be float32 numpy array in [-1, 1], mono, 16 kHz
import numpy as np
audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
text = stt.transcribe(audio, sample_rate=16000)

# Release when done
stt.release()
vdevice.release()
```

`Speech2Text` mirrors the `LLM` class structure:
- Constructor: `Speech2Text(vdevice, model)` — same args as `LLM`
- `transcribe(audio: np.ndarray, sample_rate: int) -> str` — blocking, returns transcript string
- `release()` — free NPU resources

The model receives the full audio clip at once (not streaming). For voice assistant use, we capture a complete utterance (VAD-terminated) then transcribe.

### B — Low-level HailoRT InferModel API
Available in `hailo_apps.python.standalone_apps.speech_recognition`. Uses separate encoder and decoder HEF files and works on Hailo-8, Hailo-8L, and Hailo-10H. More complex pipeline (mel spectrogram preprocessing → encoder → autoregressive decoder).

**We use Approach A** (GenAI API) because:
- Single `.hef` file — matches our config structure (one `stt_model_path`)
- Same interface pattern as our `HailoLLMClient`
- Simpler code; mel preprocessing handled internally by the SDK
- Hailo-10H only — acceptable, since that's our target hardware

---

## Hailo-10H NPU Sequencing

The Hailo-10H handles one inference task at a time. In the main loop:
1. Wake word fires (CPU, openWakeWord)
2. Audio captured (VAD-terminated)
3. `HailoTranscriber.transcribe()` runs on NPU (STT)
4. `HailoLLMClient` runs on NPU (routing + response)

No contention — STT finishes before LLM starts.

---

## Available STT Model (Hailo-10H)

| Model | Notes |
|-------|-------|
| `whisper-base` | 74M parameters; sufficient quality for home assistant; ~0.5s on Hailo-10H |

Download:
```bash
hailo-download-resources --group asr --arch hailo10h
# Outputs: /usr/share/hailo/models/whisper-base-encoder.hef
#          /usr/share/hailo/models/whisper-base.hef  (GenAI single-file variant)
```

The GenAI single-file model packages encoder + decoder in one `.hef`. Our `stt_model_path` config key points at this file.

---

## Audio Preprocessing

The GenAI `Speech2Text.transcribe()` expects:
- **dtype:** `numpy.float32`
- **range:** `[-1.0, 1.0]` (normalized from int16)
- **sample rate:** 16000 Hz (pass as `sample_rate=16000`)
- **channels:** mono

Convert raw int16 PCM bytes (from `pi/audio/capture.py`) before calling:
```python
import numpy as np
audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
```

The model handles mel spectrogram generation, padding, and decoding internally.

---

## `HailoTranscriber` Design

```python
class HailoTranscriber:
    async def transcribe(self, pcm_bytes: bytes, sample_rate: int = 16000) -> str:
        ...  # Returns "" on any failure
    def close(self) -> None:
        ...  # Releases VDevice + Speech2Text
```

Error policy: **always return `""` on failure** — unlike `HailoLLMClient` (which raises), STT failures should silently produce no transcript. The caller (main loop) will skip the LLM call if transcript is empty.

Model loading is lazy (first call). `Speech2Text.transcribe()` is synchronous (blocking), so we wrap it in `asyncio.run_in_executor(None, ...)`.

---

## Installation Path (on Pi)

```bash
sudo apt install hailo-all hailo-genai hailo-gen-ai-model-zoo
hailo-download-resources --group asr --arch hailo10h
```

---

## Sources

- [Hailo ASR with Whisper base — product page](https://hailo.ai/products/hailo-software/model-explorer/generative-ai/whisper-base/)
- [hailo-ai/hailo-apps — speech_recognition standalone app README](https://github.com/hailo-ai/hailo-apps/blob/main/hailo_apps/python/standalone_apps/speech_recognition/README.md)
- [hailo-ai/hailo-apps — GenAI apps README](https://github.com/hailo-ai/hailo-apps/blob/main/hailo_apps/python/gen_ai_apps/README.md)
- [DeepWiki hailo-apps GenAI applications](https://deepwiki.com/hailo-ai/hailo-apps/6-genai-applications)
- [hailocs/hailo-whisper — export and evaluate scripts](https://github.com/hailocs/hailo-whisper)
- [Hailo Community — ASR Pipeline thread](https://community.hailo.ai/t/automatic-speech-recognition-pipeline-with-whisper-model/13127/39)
