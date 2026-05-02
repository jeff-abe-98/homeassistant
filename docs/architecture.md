# Architecture Overview

**Last updated:** 2026-05-02  
**Status:** Pre-implementation — hardware path decided, software stack TBD

---

## High-Level Design

```
[Raspberry Pi — Living Room]
  Microphone (always listening)
      │
  Wake Word Detection (local, lightweight)
      │
  Audio Capture → Voice Activity Detection
      │
  Speaker Identification (local model)
      │
  Speech-to-Text (STT)
      │
  ──────────────────────────────────────────
  [Home Server — AI/Logic Layer]
      │
  Intent Classification (local LLM)
      │
  Tool Router ──→ [Tool Plugins]
      │                  ├── Weather
      │                  ├── CTA/L Train
      │                  ├── Google Calendar
      │                  ├── Todo List (TBD service)
      │                  ├── Spotify (Emily)
      │                  ├── Music — Owner (TBD service)
      │                  ├── Amazon Fire TV
      │                  └── [AI-generated tools]
      │
  Response Generation (local LLM)
      │
  Text-to-Speech (TTS)
      │
  ──────────────────────────────────────────
  [Raspberry Pi]
      │
  Audio Output → Hisense TV (HDMI / Bluetooth)
```

---

## Hardware

### Home Server (confirmed specs)

| Component | Spec |
|-----------|------|
| CPU | Intel Xeon E-2246G @ 3.60GHz (6 cores / 12 threads) |
| RAM | 32GB |
| Storage | 932GB NVMe SSD (WD Black SN850X) |
| GPU (current) | Intel UHD P630 integrated — CPU inference only |
| Case | Mid tower |
| PSU (current) | 260W — insufficient for a dedicated GPU |

### Planned Hardware Upgrade

| Item | Choice | Estimated Cost |
|------|--------|----------------|
| PSU | 650W 80+ Gold (standard ATX, fits mid tower) | ~$70 |
| GPU | NVIDIA RTX 4060 Ti 16GB | ~$430 |
| **Total** | | **~$500** |

**Why this combination:**
- RTX 4060 Ti 16GB draws only 165W TDP — well within a 650W PSU budget
- 16GB VRAM fits Llama 3.1 13B entirely on-GPU with room to spare
- Inference speed goes from ~5–10 tokens/sec (CPU) to ~80–120 tokens/sec (GPU)
- Enables reliable autonomous tool generation — 13B models are qualitatively better at code than 7B

**Until the GPU upgrade is done:** Run Ollama with Llama 3.1 8B Q4 on CPU. Slower, but functional for development and testing.

---

## Component Decisions (TBD)

### Local AI / LLM
- **Stack:** Ollama (model serving) — easy setup, broad model support, GPU acceleration automatic
- **Pre-upgrade (CPU only):** Llama 3.1 8B Q4_K_M — fits in RAM, reasonable CPU speed
- **Post-upgrade (RTX 4060 Ti 16GB):** Llama 3.1 13B Q4_K_M — fits fully in VRAM, fast inference
- **Decision:** Ollama confirmed; model version locked to above path

### Wake Word Detection
- **Options to evaluate:**
  - [Porcupine (Picovoice)](https://picovoice.ai/platform/porcupine/) — custom wake words, runs on Pi, free tier available
  - [openWakeWord](https://github.com/dscripka/openWakeWord) — fully open source
- **Wake word:** TBD (custom word/phrase to be chosen)

### Speech-to-Text (STT)
- **Options to evaluate:**
  - [Whisper (OpenAI, local)](https://github.com/openai/whisper) — high quality, runs locally; whisper.cpp for Pi
  - Whisper.cpp — optimized C++ port, better for constrained hardware

### Speaker Identification
- **Options to evaluate:**
  - [SpeechBrain](https://speechbrain.github.io/) — speaker verification models
  - [resemblyzer](https://github.com/resemble-ai/Resemblyzer) — speaker embedding comparison
- Must enroll voice profiles for Owner and Emily during setup

### Text-to-Speech (TTS)
- **Options to evaluate:**
  - [Piper TTS](https://github.com/rhasspy/piper) — fast, local, good quality, runs on Pi
  - Coqui TTS — more voices, higher resource use

### Tool Plugin System
- Plugin-based architecture where each feature is an independent module
- AI-generated tools should follow the same plugin interface
- Tools are loaded dynamically so new ones can be added without restart

### TV Audio Output
- Raspberry Pi → HDMI → Hisense TV (preferred path)
- Alternatively: Bluetooth speaker output if HDMI audio routing is complex

### TV Control (Amazon Fire TV OS 11)
- TV runs Amazon Fire TV OS 11 — confirmed
- Control options (in priority order):
  1. **ADB over network** — Fire TV supports ADB debugging over local network; can launch apps, send key events, control playback
  2. **Amazon Fire TV Remote API** — official SDK for remote control integration
  3. **HDMI-CEC** via Pi as fallback for basic power/input switching

---

## Data Flow: Personal Request Example

```
"Hey [wake word], add milk to my list"
  → Wake word detected (Pi)
  → Audio captured
  → Speaker identified: Emily
  → STT: "add milk to my list"
  → Intent: add_todo, user=Emily, item="milk"
  → Tool: Apple Notes → Emily TODO note → append "milk"
  → Response: "Added milk to your list, Emily."
  → TTS → TV speakers
```

---

## Deployment

- Raspberry Pi runs: wake word detection, audio I/O, STT, TTS, speaker ID
- Home server runs: LLM inference, tool execution, external API calls
- Communication between Pi and server: local network (REST or WebSocket)
- Server must be always-on; Pi restarts automatically on boot

---

## Open Questions

1. **Wake word name** — TBD, not blocking
2. **Tool sandboxing design** — how autonomous tool creation runs safely (Docker, subprocess, etc.)
3. **Voice enrollment process** — how Owner and Emily record their voice profiles during initial setup

## Resolved Decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Todo list service | Google Tasks | Reuses Google OAuth already needed for Calendar |
| Music service | Spotify for both users | One integration, separate accounts per user |
| TV OS | Amazon Fire TV OS 11 | ADB over network for control |
| LLM stack | Ollama | Easy setup, GPU acceleration, broad model support |
| LLM model (pre-GPU) | Llama 3.1 8B Q4_K_M | Fits in 32GB RAM for CPU inference |
| LLM model (post-GPU) | Llama 3.1 13B Q4_K_M | Fits in 16GB VRAM on RTX 4060 Ti |
| GPU upgrade | RTX 4060 Ti 16GB + 650W PSU | ~$500, 165W TDP, transformative inference speed |
