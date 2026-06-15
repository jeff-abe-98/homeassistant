# Hardware Parts List

**Last updated:** 2026-06-15
*Prices are USD estimates. Links are suggestions — shop around for best price.*

---

## Pi (Complete Voice Assistant)

The Pi 5 runs the entire assistant — wake word detection, STT, LLM inference, speaker identification, tool execution, TTS, and audio playback. No separate server is required.

> **PCIe conflict note:** The AI HAT+ 2 uses the Pi 5's PCIe FPC connector. The ReSpeaker 2-Mic Pi HAT also requires PCIe (via Seeed's driver). These two HATs **cannot be used simultaneously**. Use a USB microphone instead.

| Part | Notes | Est. Price |
|------|-------|-----------|
| **Raspberry Pi 5 (8 GB)** | 8 GB required — LLM inference via Hailo NPU; resemblyzer and openWakeWord run on CPU alongside | ~$80 |
| **AI HAT+ 2 (Hailo-10H)** | Hailo-10H NPU; 8 TOPS; runs LLM (Llama 3.2 3B or Qwen3 1.7B) + Whisper base for STT; connects via PCIe FPC | ~$130 |
| **USB Microphone** | Any USB cardioid mic; replaces the ReSpeaker HAT (PCIe conflict with AI HAT+ 2) | ~$20 |
| **MicroSD card — 64 GB A2 (e.g. SanDisk Extreme)** | A2-rated for better random I/O; holds OS, SQLite DBs, and Hailo-compiled model files | ~$15 |
| **Official Raspberry Pi 27W USB-C Power Supply + Case** | Pi 5 requires the official 27W PSU to avoid throttling; case must clear the AI HAT+ 2 form factor | ~$25 |

**Total: ~$270**

---

## Not Listed (already owned or not hardware)

- TV with HDMI input and Android TV (for Spotify / Netflix via `androidtvremote2`)
- Home router / Wi-Fi (Pi connects wirelessly)
- HDMI cable Pi → TV (if using Pi HDMI for display or debug)
- USB keyboard + monitor (for initial Pi OS setup only)

---

## Hailo Setup Notes

After installing Pi OS and attaching the AI HAT+ 2:

1. Install HailoRT runtime following the [Hailo Developer Zone](https://developer.hailo.ai/) instructions for Raspberry Pi 5.
2. Confirm the HAT is detected:

```bash
hailortcli fw-control identify
```

3. Download Hailo-compiled models (Llama 3.2 3B / Qwen3 1.7B for LLM, Whisper base for STT) from Hailo's model zoo.
4. Set model paths in `config/settings.yaml` under the `hailo:` section.

Audio playback goes through HDMI to the TV via `sounddevice`. The USB microphone is the sole audio input.
