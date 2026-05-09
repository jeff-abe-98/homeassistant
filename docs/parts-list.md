# Hardware Parts List

**Last updated:** 2026-05-09  
*Prices are USD estimates. Links are suggestions — shop around for best price.*

---

## Pi (Voice Interface Node)

The Pi runs wake-word detection, audio capture, speaker identification, TTS, and audio playback. It connects to the server over Wi-Fi via WebSocket.

| Part | Notes | Est. Price |
|------|-------|-----------|
| **Raspberry Pi 5 (8 GB)** | 8 GB recommended — resemblyzer embeddings and openWakeWord fit comfortably; 4 GB is workable but tight | ~$80 |
| **Official Raspberry Pi 27W USB-C Power Supply** | Pi 5 draws more current than Pi 4; the official PSU is required to avoid throttling | ~$12 |
| **ReSpeaker 2-Mic Pi HAT** | Seeed Studio; WM8960 codec; 2× MEMS mics (good omnidirectional pickup for a living room); 3.5mm line-out and JST speaker connector | ~$15 |
| **MicroSD card — 64 GB A2 (e.g. SanDisk Extreme)** | A2-rated for better random I/O; 32 GB minimum, 64 GB comfortable | ~$10 |
| **HAT-compatible Pi 5 case** | Must accommodate the 40-pin HAT with standoffs — cases with a removable top or open GPIO area work best (e.g. Argon NEO 5, or a simple open-frame) | ~$10–20 |
| **GPIO standoffs / 11 mm M2.5 hex spacers** | Keep the HAT clear of the Pi board; usually 4× included with the ReSpeaker HAT | included or ~$2 |

**Pi subtotal: ~$130–140**

### ReSpeaker 2-Mic Pi HAT — compatibility note

The ReSpeaker 2-Mic Pi HAT uses I²S over the standard 40-pin GPIO and should fit Pi 5 physically. Driver installation follows Seeed Studio's Pi 5 branch:

```bash
git clone --depth=1 https://github.com/HinTak/seeed-voicecard
cd seeed-voicecard
sudo ./install.sh
sudo reboot
```

Verify after reboot:

```bash
arecord -l   # should show "seeed-2mic-voicecard"
```

The HAT's 3.5mm output is unused in this build — audio playback goes through HDMI to the TV via `sounddevice`.

---

## Server (AI & Logic)

The server runs FastAPI + Ollama (LLM), Whisper STT, and all tool integrations. It needs to be on the same LAN as the Pi.

### Current server (already in place)

| Component | Notes |
|-----------|-------|
| CPU | Any modern multi-core (6+ cores ideal for CPU-only Ollama inference) |
| RAM | 32 GB — required for llama3.1:8b-instruct-q4_K_M in CPU mode |
| Storage | 50 GB free for Ollama model cache |
| OS | Linux (Ubuntu 22.04+ recommended) |

### Pending GPU upgrade

| Part | Notes | Est. Price |
|------|-------|-----------|
| **NVIDIA RTX 4060 Ti 16 GB** | 16 GB VRAM fits llama3.1:13b-instruct-q4_K_M; enables fast GPU inference via Ollama's CUDA backend | ~$420–450 |
| **650 W PSU** | Replace existing PSU if under 550 W; 650 W gives headroom for CPU + RTX 4060 Ti under load | ~$80–100 |

**Server upgrade subtotal: ~$500–550**

After the GPU is installed, update `config/settings.yaml`:

```yaml
ollama:
  model: llama3.1:13b-instruct-q4_K_M
```

---

## Total Estimated Cost

| Section | Est. |
|---------|------|
| Pi node | ~$130–140 |
| Server GPU upgrade | ~$500–550 |
| **Total** | **~$630–690** |

---

## Not Listed (already owned or not hardware)

- TV with HDMI input and Android TV (for audio output + Spotify / Netflix)
- Home router / Wi-Fi (Pi connects wirelessly)
- HDMI cable Pi → TV (if using Pi's HDMI for display/debug; not needed in production)
- USB keyboard + monitor (for initial Pi OS setup only)
