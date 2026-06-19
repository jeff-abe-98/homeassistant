# Home Assistant

A voice-activated, locally-hosted AI home assistant for a Chicago apartment. It runs entirely on a Raspberry Pi 5 with an AI HAT+ 2 — no external server, no cloud inference. Say the wake word ("Clanker"), speak your request, and the Pi handles everything: speech recognition, LLM routing, tool execution, and spoken response.

When asked to do something it doesn't yet know how to do, it queues the request and a remote Claude Code agent builds the capability automatically.

---

## Hardware Required

| Part | Est. Price |
|------|-----------|
| Raspberry Pi 5 (8 GB) | ~$80 |
| AI HAT+ 2 (Hailo-10H NPU) | ~$130 |
| USB Microphone | ~$20 |
| MicroSD card — 64 GB A2 (e.g. SanDisk Extreme) | ~$15 |
| Official Raspberry Pi 27W USB-C Power Supply + case | ~$25 |
| **Total** | **~$270** |

See [docs/parts-list.md](docs/parts-list.md) for details and setup notes.

---

## Quick Start

```bash
# 1. Flash Raspberry Pi OS (64-bit) to the microSD card, boot, and SSH in.

# 2. Install Hailo drivers (run once; reboots automatically)
bash install-hailo-drivers.sh

# 3. Clone the repo
git clone https://github.com/jeff-abe-98/homeassistant.git
cd homeassistant

# 4. Install Python dependencies
pip install -r requirements-pi.txt

# 5. Copy and fill in your configuration
cp config/settings.yaml.example config/settings.yaml
# Edit config/settings.yaml — fill in all CHANGE_ME values

# 6. Enroll voice profiles (requires USB mic plugged in)
python -m pi.speaker_id.enroll --user owner
python -m pi.speaker_id.enroll --user emily

# 7. Install and start the systemd service (auto-starts on boot)
sudo bash deploy/install-pi-service.sh
```

After installation the assistant listens for the wake word "Clanker" and starts responding.

---

## What It Can Do

| Capability | How to ask |
|------------|-----------|
| Weather | "What's the weather today?" / "Will it rain this week?" |
| CTA Blue Line (Western & Milwaukee) | "When's the next train to O'Hare?" |
| Google Calendar | "What do I have tomorrow?" / "Add a dentist appointment Friday at 3" |
| Google Tasks | "Add oat milk to my list" / "What's on my list?" / "Mark oat milk as done" |
| Spotify (Owner + Emily, separate accounts) | "Play some jazz" / "Play my Discover Weekly" / "Pause" / "Skip" |
| Android TV (Hisense) | "Put on Netflix" / "Turn on the TV" |
| Music recommendations | "Play something I'd like" |
| New capabilities | Ask for anything — it queues a request and the agent builds the tool |

---

## Project Structure

```
pi/             Voice assistant process (runs on Pi)
tools/          Built-in and AI-generated tools
tool_requests/  Queued capability requests (pending → complete)
shared/         Config dataclasses and shared models
config/         settings.yaml and OAuth credential files (gitignored)
deploy/         Systemd service and install scripts
docs/           Hardware list, setup guide, API key setup, troubleshooting
archive/server/ Old server-based architecture (preserved for reference)
```

---

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/setup-guide.md](docs/setup-guide.md) | Step-by-step first-time Pi setup |
| [docs/api-keys-setup.md](docs/api-keys-setup.md) | Where to get and how to configure each credential |
| [docs/parts-list.md](docs/parts-list.md) | Hardware parts list with prices and Hailo setup notes |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Common issues and fixes |
| [docs/technical-stack.md](docs/technical-stack.md) | Stack decisions and architecture notes |

---

## First-Run Check

After setup, verify everything is configured correctly:

```bash
bash scripts/first-run-check.sh
```

This prints a checklist of what's ready vs. missing (HailoRT, config values, voice profiles, systemd units).

---

## How Autonomous Tool Creation Works

1. You ask for something no built-in tool handles
2. The assistant says "I don't know how to do that yet" and asks if it's urgent
3. A request JSON is written to `tool_requests/pending/` and pushed to GitHub
4. A scheduled Claude Code agent (runs during low-usage hours) builds a `BaseTool` implementation
5. On the next wake word activation, the Pi pulls and loads the new tool
6. The assistant announces: "By the way, I can now [X] — want to try it?"

All existing tools continue working offline. Requests queue locally and sync when connectivity is restored.

---

## Configuration

All secrets live in `config/settings.yaml` (gitignored — never committed). See [docs/api-keys-setup.md](docs/api-keys-setup.md) for where to obtain each credential.

Key sections:

```yaml
hailo:
  llm_model_path: /path/to/llama3.2-3b.hef
  stt_model_path: /path/to/whisper-base.hef

google:
  credentials_file: config/google_credentials.json

spotify:
  owner:
    client_id: CHANGE_ME
    client_secret: CHANGE_ME

cta:
  api_key: CHANGE_ME

weather:
  api_key: CHANGE_ME

androidtv:
  host: CHANGE_ME
```
