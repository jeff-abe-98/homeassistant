# Technical Stack

**Last updated:** 2026-06-15
**Status:** Decided — Pi-only redesign (AI HAT+ 2 / HailoRT)

---

## Language & Runtime

**Python 3.11+** across all components.

---

## System Components

### Pi (Unified Voice Assistant Process)

All components run on the Raspberry Pi 5 (8GB RAM + AI HAT+ 2). No separate server.

| Concern | Library | Rationale |
|---------|---------|-----------|
| Wake word detection | [openWakeWord](https://github.com/dscripka/openWakeWord) | Fully open source, no API key, runs on Pi CPU, customizable |
| Audio capture | `pyaudio` + `webrtcvad` | PyAudio for USB mic input; WebRTC VAD for voice activity detection |
| Speech-to-Text | HailoRT + Hailo-compiled Whisper base | Runs on Hailo-10H NPU via AI HAT+ 2; replaces faster-whisper |
| LLM inference | HailoRT + Hailo GenAI suite | Llama 3.2 3B or Qwen3 1.7B compiled for Hailo-10H; replaces Ollama |
| LLM model | Llama 3.2 3B (or Qwen3 1.7B) | Best fit for Hailo-10H at 8 TOPS; handles tool routing + conversational replies |
| Speaker identification | [resemblyzer](https://github.com/resemble-ai/Resemblyzer) | Lightweight speaker embeddings, easy voice enrollment, runs on CPU |
| Text-to-Speech | [Piper TTS](https://github.com/rhasspy/piper) | Fast, local, high quality, designed for Pi-class hardware |
| Audio output | `sounddevice` | Play TTS audio through HDMI to TV |
| Conversation memory | SQLite (stdlib `sqlite3`) | Session-scoped; recent turns injected into LLM prompt; persists across reboots |
| Tool request queue | SQLite | Local queue for requests the LLM can't fulfill; pushed to GitHub when online |
| Usage scheduler | SQLite + `schedule.json` | Activation heatmap drives when the remote tool-builder agent runs |

### Integrations

| Feature | Library / API | Notes |
|---------|--------------|-------|
| Google Calendar | `google-api-python-client` | OAuth2, scope: `calendar` |
| Google Tasks | `google-api-python-client` | Same OAuth2 credentials as Calendar, scope: `tasks` |
| Weather | `httpx` → OpenWeatherMap API | Free tier sufficient; LLM narrates |
| CTA L Train | `httpx` → CTA Train Tracker API | Free API key from transitchicago.com |
| Spotify (both users) | [spotipy](https://spotipy.readthedocs.io/) | OAuth2 per user; Spotify Connect to target Android TV device. **Requires Spotify Premium.** |
| Android TV (Hisense) | `androidtvremote2` | Android TV Remote Service protocol over Wi-Fi port 6466 — no ADB required |

### Remote Tool Builder (Cloud Agent)

| Concern | Tool | Notes |
|---------|------|-------|
| Tool generation | Claude Code scheduled agent | Runs in Anthropic cloud during low-usage windows; reads/writes via GitHub |
| Schedule | `schedule.json` in repo root | Written by Pi's daily heatmap process; agent self-reschedules via CronDelete + CronCreate |
| Tool delivery | GitHub repo (`tools/generated/`) | Pi pulls new tools on each wake word activation; no direct Claude API calls during normal operation |

---

## Project Structure

```
homeassistant/
├── pi/                         # Single unified process — runs entirely on Pi
│   ├── main.py                 # Entry point — unified wake word + request loop
│   ├── wake_word/              # openWakeWord detection (CPU)
│   ├── audio/                  # Capture (USB mic + VAD), playback (HDMI)
│   ├── stt/                    # HailoRT Whisper client
│   ├── tts/                    # Piper TTS
│   ├── speaker_id/             # resemblyzer voice profiles
│   ├── llm/                    # HailoRT LLM client, tool router, prompt builder
│   ├── memory/                 # SQLite session memory, context injection
│   ├── tool_requests/          # Local queue, GitHub sync, offline retry
│   └── scheduler/              # Activation heatmap, schedule.json writer
│
├── tools/
│   └── generated/              # AI-created tools (built by remote agent, pulled by Pi)
│
├── tool_requests/
│   ├── pending/                # JSON files pushed to GitHub for remote agent
│   └── complete/               # Processed request records (complete or failed)
│
├── shared/                     # Shared across pi/ and tools/
│   ├── config.py               # Config dataclasses
│   └── models.py               # Shared Pydantic models
│
├── config/
│   ├── settings.yaml           # All runtime config (gitignored)
│   └── voice_profiles/         # Enrolled speaker embeddings
│
├── archive/
│   └── server/                 # Old server-side code (preserved for reference)
│
├── .claude/
│   └── agents/
│       └── tool-builder.md     # Remote agent definition and instructions
│
├── schedule.json               # Low-usage windows — read by remote agent
├── requirements-pi.txt
└── plan.md
```

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

Tools in `tools/generated/` are loaded at startup and on each wake word activation (to pick up newly pulled tools). Each generated tool also has a companion `{tool_name}_instructions.md` that the LLM uses to understand when and how to invoke it.

---

## Autonomous Tool Creation — Design

1. User requests something no known tool handles
2. Pi LLM detects no tool match → tells user "I don't know how to do that yet"
3. Pi asks relative priority if queue is non-empty; assigns priority; writes request to local SQLite queue
4. When online: Pi pushes request JSON to `tool_requests/pending/` in GitHub repo
5. Remote Claude Code scheduled agent builds `BaseTool` implementation + `_instructions.md`, pushes to `tools/generated/`
6. Pi pulls on next wake word activation → loads tool into registry
7. Pi announces on next interaction: "By the way, I can now [X] — want to try it?"
8. On failure: agent marks request as `failed`, Pi notifies user on next interaction

**Offline resilience:** Requests are queued in local SQLite and pushed when connectivity is restored. All existing tools continue to work offline.

---

## Integration Notes & Gotchas

### Hailo NPU — Sequential STT + LLM
The Hailo-10H NPU handles one inference task at a time. STT (Whisper) runs first on the captured audio; LLM routing runs after the transcript is ready. No contention.

### Spotify on Android TV — Combined Flow
1. Use `androidtvremote2` to launch `com.spotify.tv.android` on the TV
2. Poll `sp.devices()` until the TV device appears (typically 2–5 seconds)
3. Call `sp.transfer_playback(device_id=tv_device_id, force_play=True)`

**Never cache the device ID** — it changes across Spotify sessions.

### Spotify Premium Required
Spotify Connect API commands silently fail or return 403 on free accounts. Both Owner and Emily must have Spotify Premium.

### Android TV Remote — No ADB Needed
`androidtvremote2` uses the Android TV Remote Service protocol over port 6466. ADB debugging does not need to be enabled.

### Google OAuth — One Setup for Calendar + Tasks
Both Calendar and Tasks APIs share the same OAuth2 credentials. Request both scopes together: `https://www.googleapis.com/auth/calendar` and `https://www.googleapis.com/auth/tasks`.

---

## Configuration

All secrets in `config/settings.yaml` (gitignored):

```yaml
hailo:
  llm_model_path: /path/to/llama3.2-3b.hef
  stt_model_path: /path/to/whisper-base.hef

memory:
  session_timeout_seconds: 30
  context_turns: 6

tool_requests:
  db_path: /home/pi/homeassistant/tool_requests.db
  sync_interval_seconds: 300

google:
  credentials_file: config/google_credentials.json
  token_file: config/google_token.json

spotify:
  owner:
    client_id: CHANGE_ME
    client_secret: CHANGE_ME
    redirect_uri: http://localhost:8888/callback
    token_file: config/spotify_owner_token.json
  emily:
    client_id: CHANGE_ME
    client_secret: CHANGE_ME
    redirect_uri: http://localhost:8888/callback
    token_file: config/spotify_emily_token.json

cta:
  api_key: CHANGE_ME
  stop_id_ohare: 30171
  stop_id_forest_park: 30170

weather:
  api_key: CHANGE_ME
  location: "Chicago, IL"
  units: imperial

androidtv:
  host: CHANGE_ME
  port: 6466
```
