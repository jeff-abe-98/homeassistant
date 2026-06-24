# Setup Guide — First-Time Pi Configuration

This guide walks through a complete first-time setup of the home assistant on a fresh Raspberry Pi 5 with AI HAT+ 2. Follow the steps in order.

**Estimated time:** 30–60 minutes (not counting model download time).

---

## Prerequisites

- Raspberry Pi 5 (8 GB RAM)
- AI HAT+ 2 (Hailo-10H) attached via PCIe FPC connector
- USB microphone plugged in
- HDMI cable connected to TV (for audio output)
- MicroSD card (64 GB A2-rated, e.g. SanDisk Extreme)
- Internet connection (Wi-Fi or Ethernet during setup)
- A computer to flash the SD card

See `docs/parts-list.md` for the full hardware list and purchasing notes.

---

## Step 1 — Flash Raspberry Pi OS

1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/).
2. Insert the microSD card into your computer.
3. In Imager, choose:
   - **Device:** Raspberry Pi 5
   - **OS:** Raspberry Pi OS Lite (64-bit) — the headless variant is sufficient
   - **Storage:** your microSD card
4. Open the OS customization settings (gear icon) and set:
   - Hostname (e.g. `homeassistant`)
   - Username and password
   - Wi-Fi SSID and password
   - Enable SSH
5. Write the image, then insert the card into the Pi and power on.
6. SSH into the Pi once it boots:
   ```bash
   ssh pi@homeassistant.local
   ```

---

## Step 2 — Install HailoRT Drivers

The AI HAT+ 2 requires a PCIe driver and a PCIe Gen 3 mode flag. The project ships an install script for this.

```bash
sudo bash install-hailo-drivers.sh
```

The script:
1. Runs `apt install hailo-h10-all`
2. Adds `dtparam=pciex1_gen=3` to `/boot/firmware/config.txt`
3. Reboots automatically after 5 seconds

After reboot, verify the HAT is detected:

```bash
hailortcli fw-control identify
```

Expected output includes a line like `Hailo-10H firmware version ...`. If the command is not found, HailoRT is not installed — check `apt` output from the install script.

---

## Step 3 — Clone the Repository

```bash
cd ~
git clone https://github.com/jeff-abe-98/homeassistant.git
cd homeassistant
```

---

## Step 4 — Install Python Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements-pi.txt
```

> **Note:** `hailort` and `hailo-tappas` are not on PyPI. They are installed as system packages by `hailo-h10-all` (Step 2). The `requirements-pi.txt` file contains a comment for these; the rest of the dependencies install normally via pip.

---

## Step 5 — Download Hailo-Compiled Models

The Hailo NPU requires models compiled to `.hef` format. These are served directly from Hailo's public CDN — no account required.

> **Note on package availability:** The `hailo-genai` and `hailo-gen-ai-model-zoo` apt packages referenced in older guides are **not** in the Raspberry Pi apt repository (as of June 2026). `hailo-download-resources` is therefore unavailable. Use the direct CDN downloads below instead. The `hailo_platform.genai` Python API (LLM and Speech2Text classes) **is** already included in the `python3-h10-hailort` package installed by `hailo-h10-all`.

> **Note on model availability:** No 3B or larger LLM model exists for Hailo-10H. The largest available model is 1.7B. `Qwen2.5-1.5B-Instruct` is the recommended general-purpose model. See `.project/research/hailo-llm.md` for model comparison notes.

```bash
mkdir -p pi/llm/models pi/stt/models

# LLM model (~2.4 GB)
wget -O pi/llm/models/qwen2.5-instruct-1.5b.hef \
  https://dev-public.hailo.ai/v5.1.1/blob/Qwen2.5-1.5B-Instruct.hef

# STT model (~137 MB)
wget -O pi/stt/models/whisper-base.hef \
  https://dev-public.hailo.ai/v5.1.1/blob/Whisper-Base.hef
```

The default config (`config/settings.yaml`) expects:
- `pi/llm/models/qwen2.5-instruct-1.5b.hef`
- `pi/stt/models/whisper-base.hef`

---

## Step 6 — Download Piper TTS Voice Model

Piper needs a voice model for text-to-speech output.

1. Browse voices at https://github.com/rhasspy/piper/blob/master/VOICES.md
2. Download the `.onnx` and `.onnx.json` files for your preferred voice (default: `en_US-lessac-medium`):

```bash
mkdir -p pi/tts/models
cd pi/tts/models
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
cd ~/homeassistant
```

---

## Step 7 — Configure settings.yaml

Copy the example config and fill in your values:

```bash
cp config/settings.yaml config/settings.yaml.bak   # keep a backup
nano config/settings.yaml
```

Replace every `CHANGE_ME` placeholder. Key fields:

| Field | What to put |
|-------|-------------|
| `hailo.llm_model_path` | Path to your LLM `.hef` file |
| `hailo.stt_model_path` | Path to your STT `.hef` file |
| `tts.model_path` | Path to your Piper `.onnx` file |
| `weather.api_key` | OpenWeatherMap API key (see `docs/api-keys-setup.md`) |
| `cta.api_key` | CTA Train Tracker API key (see `docs/api-keys-setup.md`) |
| `spotify.owner.*` | Spotify app credentials for the owner account |
| `spotify.emily.*` | Spotify app credentials for Emily's account |
| `androidtv.host` | Local IP address of the Android TV (e.g. `192.168.1.42`) |
| `users.owner.name` | Replace with the owner's actual first name |

See `docs/api-keys-setup.md` for step-by-step instructions on obtaining each credential.

`config/settings.yaml` is gitignored — your real credentials will never be committed.

---

## Step 8 — Set Up Google OAuth (Calendar + Tasks)

Google Calendar and Google Tasks share a single OAuth2 credential. The first time either tool is invoked, a browser-based authorization flow runs.

1. Follow `docs/api-keys-setup.md` → Google section to create credentials and download `google_credentials.json`.
2. Place the file at `config/google_credentials.json`.
3. Run the auth flow once from the Pi:
   ```bash
   source venv/bin/activate
   python -c "from pi.tools.google_auth import get_credentials; get_credentials()"
   ```
   This opens a browser URL — paste it into a browser, approve access, then paste the resulting code back into the terminal.
4. The token is saved to `config/google_token.json`. Subsequent runs use this token silently.

---

## Step 9 — Enroll Voice Profiles

Voice enrollment records 30 seconds of speech to build a speaker embedding. Run once per person.

```bash
source venv/bin/activate

# Enroll the owner (replace "owner" with the name set in settings.yaml → users.owner.name)
python -m pi.speaker_id.enroll owner

# Enroll Emily
python -m pi.speaker_id.enroll emily
```

When prompted, speak naturally for 30 seconds — tell a story or describe your day. Good variety improves identification accuracy. Profiles are saved to `config/voice_profiles/`.

If the Pi has multiple audio input devices, find the USB mic's device index:

```bash
python -c "import pyaudio; pa=pyaudio.PyAudio(); [print(i, pa.get_device_info_by_index(i)['name']) for i in range(pa.get_device_count())]"
```

Then pass `--device <index>` to the enroll command.

---

## Step 10 — Enable Systemd Services

The install script creates a service user, copies the project to `/opt/homeassistant`, creates a Python venv, and installs + enables the systemd units.

```bash
sudo bash deploy/install-pi-service.sh
```

This enables and starts:
- **`homeassistant-pi.service`** — the main assistant process (auto-restarts on failure)
- **`homeassistant-scheduler.timer`** — daily activation heatmap writer (drives remote tool builder schedule)

Check that everything is running:

```bash
systemctl status homeassistant-pi
systemctl status homeassistant-scheduler.timer
journalctl -u homeassistant-pi -f
```

The assistant is ready when you see `Wake word detector started` in the logs.

---

## Step 11 — Test It

Say the wake word ("Hey Jarvis") and ask something simple:

- "What's the weather today?"
- "What's on my calendar tomorrow?"
- "When's the next Blue Line toward O'Hare?"

If a question hits something the assistant doesn't know how to do yet, it will say so and queue a tool-creation request for the remote agent to fulfill.

---

## Troubleshooting

See `docs/troubleshooting.md` for common issues: HailoRT not found, USB mic not detected, wake word not triggering, tool errors, and GitHub sync failures.

---

## Optional — Custom Wake Word

The default wake word is "Hey Jarvis" (openWakeWord). To train a custom wake word:

```bash
# Record positive samples
python -m pi.wake_word.record_samples --label hey_clanker --count 50

# Train the model
python -m pi.wake_word.train_model --wake-word hey_clanker
```

Then update `config/settings.yaml`:

```yaml
wake_word:
  model: hey_clanker
```
