# Technical Stack

**Last updated:** 2026-05-02  
**Status:** Decided — ready for implementation

---

## Language & Runtime

**Python 3.11+** across all components.
- Best ecosystem for audio processing, ML models, and API integrations
- Consistent language across Pi and server simplifies shared code

---

## System Components

### Pi (Voice Interface)

| Concern | Library | Rationale |
|---------|---------|-----------|
| Wake word detection | [openWakeWord](https://github.com/dscripka/openWakeWord) | Fully open source, no API key, runs on Pi, customizable |
| Audio capture | `pyaudio` + `webrtcvad` | PyAudio for mic input; WebRTC VAD for voice activity detection |
| Speech-to-Text | [faster-whisper](https://github.com/guillaumekientz/faster-whisper) | Optimized Whisper port; small model on Pi, large model offloaded to server |
| Speaker identification | [resemblyzer](https://github.com/resemble-ai/Resemblyzer) | Lightweight speaker embeddings, easy voice enrollment, pure Python |
| Text-to-Speech | [Piper TTS](https://github.com/rhasspy/piper) | Fast, local, high quality, designed for Pi-class hardware |
| Audio output | `sounddevice` | Play TTS audio through HDMI to TV |
| Server communication | `websockets` | Streams audio and receives responses in real-time |

### Server (AI & Logic)

| Concern | Library | Rationale |
|---------|---------|-----------|
| Web framework | [FastAPI](https://fastapi.tiangolo.com/) | Async, WebSocket support, fast, great for tool APIs |
| LLM inference | [Ollama](https://ollama.ai) + `ollama` Python client | Local model serving, automatic GPU acceleration, simple API |
| LLM model (pre-GPU) | `llama3.1:8b-instruct-q4_K_M` | Fits in 32GB RAM, CPU inference |
| LLM model (post-GPU) | `llama3.1:13b-instruct-q4_K_M` | Fits in 16GB VRAM (RTX 4060 Ti), fast GPU inference |
| Tool function calling | Ollama structured output / JSON mode | Route intent to correct tool plugin |
| Task queue | `asyncio` + in-process queue | Sufficient for single-household load |

### Integrations

| Feature | Library / API | Notes |
|---------|--------------|-------|
| Google Calendar | `google-api-python-client` | OAuth2, scope: `calendar` |
| Google Tasks | `google-api-python-client` | Same OAuth2 credentials as Calendar, scope: `tasks` |
| Weather | `httpx` → OpenWeatherMap API | Free tier sufficient; AI layer parses and narrates |
| CTA L Train | `httpx` → CTA Train Tracker API | Free API key from transitchicago.com |
| Spotify (both users) | [spotipy](https://spotipy.readthedocs.io/) | OAuth2 per user; Spotify Connect to target Android TV device. **Requires Spotify Premium.** Scopes: `user-read-playback-state`, `user-modify-playback-state`, `user-read-currently-playing` |
| Android TV (Hisense) | `androidtvremote2` (primary) | Android TV Remote Service protocol over Wi-Fi port 6466 — no ADB debug required. Used by Home Assistant's official integration. Handles app launch, media keys, power. |

---

## Project Structure

```
homeassistant/
├── pi/                         # Runs on Raspberry Pi
│   ├── main.py                 # Entry point — wake word loop
│   ├── wake_word/              # openWakeWord detection
│   ├── audio/                  # Capture, VAD, playback
│   ├── stt/                    # faster-whisper (small model)
│   ├── tts/                    # Piper TTS
│   ├── speaker_id/             # resemblyzer voice profiles
│   └── client.py               # WebSocket client → server
│
├── server/                     # Runs on home server
│   ├── main.py                 # FastAPI app entry point
│   ├── llm/                    # Ollama client, prompt templates
│   ├── tools/                  # Tool plugin system
│   │   ├── base.py             # Tool interface / registry
│   │   ├── weather.py
│   │   ├── cta.py
│   │   ├── calendar.py
│   │   ├── tasks.py
│   │   ├── spotify.py
│   │   ├── androidtv.py        # androidtvremote2
│   │   └── generated/          # AI-created tools (sandboxed)
│   └── tool_creator/           # Autonomous tool generation system
│
├── shared/                     # Shared across Pi and server
│   ├── config.py               # Config dataclasses
│   └── models.py               # Shared message types (Pydantic)
│
├── config/
│   ├── settings.yaml           # All runtime config (gitignored)
│   └── voice_profiles/         # Enrolled speaker embeddings
│
├── requirements-pi.txt
├── requirements-server.txt
└── plan.md
```

---

## Communication Protocol (Pi ↔ Server)

```
Pi                                    Server
 │                                       │
 │── WebSocket connect ─────────────────>│
 │                                       │
 │── AudioChunk (raw PCM stream) ───────>│  STT (large Whisper model)
 │<─ Transcript confirmed ───────────────│
 │                                       │
 │── SpeakerID result + transcript ─────>│  LLM intent → tool execution
 │<─ ResponseText ────────────────────── │
 │                                       │
 │  TTS locally → audio output           │
```

- Pi handles: wake word, audio I/O, speaker ID, TTS, playback
- Server handles: STT (large model), LLM, all tool execution
- Messages are JSON-framed Pydantic models over WebSocket

---

## Tool Plugin Interface

Every tool (built-in or AI-generated) implements the same interface:

```python
class BaseTool:
    name: str                    # e.g. "cta_arrivals"
    description: str             # Used by LLM to decide when to call it
    parameters: dict             # JSON Schema for LLM function calling

    async def run(self, params: dict, user: str) -> str:
        ...                      # Returns natural language response string
```

Tools are registered at startup and dynamically loadable — a new `.py` file in `tools/` is picked up without restart.

---

## Autonomous Tool Creation — Design

1. User requests something the assistant can't do
2. LLM generates a `BaseTool` implementation in Python
3. Tool written to `tools/generated/<name>.py`
4. Sandboxed test run (subprocess, restricted imports, timeout)
5. If passes: registered, user notified ("I can do that now")
6. If fails: LLM retries up to 3 times, then reports failure

**Sandboxing:** `subprocess` with `resource` limits (CPU time, memory) and import allowlist. Docker as a later hardening option.

---

## Integration Notes & Gotchas

### Spotify on Android TV — Combined Flow
Spotify Connect and the TV remote protocol must work together:
1. Use `androidtvremote2` to launch `com.spotify.tv.android` on the TV
2. Poll `sp.devices()` until the TV device appears (typically 2–5 seconds)
3. Call `sp.transfer_playback(device_id=tv_device_id, force_play=True)`
4. Use `spotipy` for play/pause/skip/search going forward

**Never cache the device ID** — it changes across Spotify sessions. Always resolve it fresh from `sp.devices()`.

### Spotify Premium Required
Spotify Connect API commands (play, pause, skip, transfer) silently fail or return 403 on free accounts. Both Owner and Emily must have Spotify Premium.

### Android TV Remote — No ADB Needed
`androidtvremote2` uses the Android TV Remote Service protocol (same as Google's official remote app) over port 6466. ADB debugging does not need to be enabled on the TV. Handles: power, app launch by package name, media keys, volume, deep-link URLs.

### Google OAuth — One Setup for Calendar + Tasks
Both Calendar and Tasks APIs share the same OAuth2 client credentials and token. Set up once in `config/google_credentials.json`, request both scopes together: `https://www.googleapis.com/auth/calendar` and `https://www.googleapis.com/auth/tasks`.

---

## Configuration

All secrets in `config/settings.yaml` (gitignored):

```yaml
server:
  host: 0.0.0.0
  port: 8000

ollama:
  host: http://localhost:11434
  model: llama3.1:8b-instruct-q4_K_M

google:
  credentials_file: config/google_credentials.json

spotify:
  owner:
    client_id: ...
    client_secret: ...
  emily:
    client_id: ...
    client_secret: ...

cta:
  api_key: ...

weather:
  api_key: ...
  location: "Chicago, IL"

androidtv:
  host: 192.168.x.x
  port: 6466           # androidtvremote2 protocol (not ADB)
```
