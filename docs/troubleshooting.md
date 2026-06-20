# Troubleshooting

Common issues and how to fix them.

Run `scripts/first-run-check.sh` first — it checks the most common failure points automatically.

---

## HailoRT Not Found

**Symptom:** `ImportError: No module named 'hailo_platform'` or `hailortcli: command not found`.

**Cause:** The Hailo PCIe driver and SDK are not installed, or the service failed to start.

**Fix:**

1. Verify the AI HAT+ 2 is physically seated on the PCIe FPC connector and that the ribbon cable is fully clipped in on both ends.

2. Run the driver install script (if you haven't already):
   ```bash
   sudo bash install-hailo-drivers.sh
   sudo reboot
   ```

3. After reboot, verify the device is detected:
   ```bash
   hailortcli scan
   ```
   You should see a line like `[HailoRT] [info] Device: PCIe:0000:01:00.0`. If not, check:
   ```bash
   lspci | grep Hailo
   ```
   If the PCIe device isn't listed at all, the HAT is not making contact — reseat it.

4. If `hailortcli` is found but the Python import still fails, the `hailo_platform` package isn't installed in your venv:
   ```bash
   source venv/bin/activate
   pip install hailo_platform  # or install from the Hailo .whl you downloaded
   ```
   See `docs/setup-guide.md` Step 5 for model download instructions.

5. Check that PCIe Gen 3 is enabled in `/boot/firmware/config.txt`:
   ```
   dtparam=pciex1_gen=3
   ```
   If this line is missing, add it and reboot.

---

## USB Microphone Not Detected

**Symptom:** No audio input, `pi/audio/capture.py` raises a PyAudio error, or the assistant never leaves the wake word listening loop.

**Fix:**

1. Confirm the mic is plugged in and visible to the OS:
   ```bash
   arecord -l
   ```
   You should see a `card N: ...USB Audio...` entry. If not, try a different USB port or a different cable.

2. Find the card and device numbers from `arecord -l`, then test a 5-second recording:
   ```bash
   arecord -D hw:N,0 -r 16000 -c 1 -f S16_LE -d 5 /tmp/test.wav
   aplay /tmp/test.wav
   ```
   If you hear silence or get a ALSA error, the mic or sample-rate isn't compatible — try `-D plughw:N,0` to let ALSA resample.

3. If you have multiple audio devices and the wrong one is selected, set the correct card index in `config/settings.yaml`:
   ```yaml
   audio:
     input_device_index: 1   # check `arecord -l` for the right number
   ```

4. Check that the service user (created by `install-pi-service.sh`) is in the `audio` group:
   ```bash
   groups homeassistant
   ```
   If `audio` is not listed:
   ```bash
   sudo usermod -aG audio homeassistant
   sudo systemctl restart homeassistant-pi.service
   ```

---

## Wake Word Not Triggering

**Symptom:** The assistant never activates even when you say "Clanker" clearly.

**Fix:**

1. Check that the mic is working first (see **USB Microphone Not Detected** above).

2. Verify the openWakeWord model file is present. The model path is printed at startup:
   ```bash
   journalctl -u homeassistant-pi.service -n 50 | grep wake
   ```
   If the model file is missing, re-run the model download from `docs/setup-guide.md` Step 5.

3. Speak loudly and clearly within 1–2 metres of the mic. Background noise (TV, music) can suppress detection.

4. If false negatives are frequent, lower the detection threshold in `config/settings.yaml`:
   ```yaml
   wake_word:
     threshold: 0.4          # default 0.5 — lower = more sensitive
     min_activation_count: 2  # default 3 — fewer consecutive frames required
   ```
   Note: lowering the threshold increases false positives. Tune with real-world testing.

5. If false positives are too frequent (activates without "Clanker"), raise the threshold or increase `min_activation_count`:
   ```yaml
   wake_word:
     threshold: 0.6
     min_activation_count: 4
     cooldown_seconds: 3.0
   ```

6. To retrain on your own voice, see `pi/wake_word/train_model.py` — a custom model trained on your household's recordings will perform significantly better than the default.

---

## Tool Errors

**Symptom:** The assistant says "Something went wrong" or repeats the fallback phrase instead of executing a tool.

### Weather / CTA tools failing

1. Check the API key in `config/settings.yaml` — run `scripts/first-run-check.sh` which reports `CHANGE_ME` placeholders.
2. Test the key directly:
   ```bash
   curl "https://api.openweathermap.org/data/2.5/weather?q=Chicago&appid=YOUR_KEY"
   curl "http://lapi.transitchicago.com/api/1.0/ttarrivals.aspx?key=YOUR_KEY&stpid=30171&outputType=JSON"
   ```
3. New OWM keys can take up to 10 minutes to activate after registration.

### Google Calendar / Tasks failing

1. Confirm `config/google_credentials.json` exists and is the Desktop app OAuth client (not a service account).
2. Check that the token file exists for the relevant user:
   ```bash
   ls -la config/google_token_*.json
   ```
   If a token file is missing, run the first-time auth flow described in `docs/api-keys-setup.md`.
3. If you see `Token has been expired or revoked`, delete the token file and re-run the auth flow:
   ```bash
   rm config/google_token_owner.json
   python -c "from pi.tools.google_auth import get_credentials; get_credentials('owner')"
   ```

### Spotify failing

1. Confirm the token files exist:
   ```bash
   ls -la config/spotify_token_*.json
   ```
2. Spotify tokens expire after 1 hour but are refreshed automatically by spotipy. If auto-refresh fails (e.g. the client secret changed), delete the token file and re-run:
   ```bash
   rm config/spotify_token_owner.json
   python -c "from pi.tools.spotify import SpotifyTool; SpotifyTool().run({'action': 'now_playing'}, 'owner')"
   ```
   Follow the browser prompt to re-authorize.
3. Spotify playback requires an active Spotify Premium account. Free-tier accounts cannot use `start_playback`.

### Android TV failing

1. Confirm the TV IP address is not a placeholder:
   ```bash
   grep androidtv config/settings.yaml
   ```
2. Test reachability:
   ```bash
   ping -c 3 YOUR_TV_IP
   ```
3. If the Pi and TV are on the same LAN but ping fails, the TV may have gone to sleep. Power it on manually and retry.
4. On first connection, the TV shows a pairing prompt. The assistant must connect once interactively — run:
   ```bash
   python -c "
   import asyncio
   from androidtvremote2 import AndroidTVRemote
   async def pair():
       atv = AndroidTVRemote('home-assistant', 'config/atv_client.pem', 'config/atv_client.crt', 'YOUR_TV_IP')
       await atv.async_connect()
   asyncio.run(pair())
   "
   ```
   Accept the pairing dialog on the TV.

### Generated tool failing

1. Check the tool file exists in `tools/generated/`:
   ```bash
   ls tools/generated/
   ```
2. Run the tool's built-in test manually:
   ```bash
   python -c "
   from tools.generated.YOUR_TOOL import YourTool
   import asyncio
   result = asyncio.run(YourTool().run({}, 'owner'))
   print(result)
   "
   ```
3. If the tool file is corrupt, delete it and re-request the capability. The Pi will push a new tool request to GitHub on the next activation.

---

## GitHub Sync Failures

**Symptom:** Tool requests accumulate locally but are never pushed to GitHub, so the tool builder agent never sees them. The assistant may say "I'll remember that for when I'm back online" repeatedly.

**Fix:**

1. Verify internet connectivity:
   ```bash
   curl -s https://github.com > /dev/null && echo "online" || echo "offline"
   ```

2. Check the git remote URL includes a valid PAT:
   ```bash
   git remote get-url origin
   ```
   The URL should be `https://<PAT>@github.com/jeff-abe-98/homeassistant.git`. If the PAT has expired, generate a new one at GitHub → Settings → Developer settings → Personal access tokens, then update:
   ```bash
   git remote set-url origin https://NEW_PAT@github.com/jeff-abe-98/homeassistant.git
   ```

3. Test the push manually:
   ```bash
   git fetch origin main
   git push origin main
   ```
   If push fails with `403 Forbidden`, the PAT is invalid or has insufficient scopes. The PAT needs at minimum: `repo` (read + write contents).

4. Check the service journal for sync errors:
   ```bash
   journalctl -u homeassistant-pi.service -n 100 | grep -i sync
   ```

5. If the Pi is offline frequently, pending requests pile up. They are pushed in batch on the next successful sync. No data is lost — the SQLite queue persists across reboots.

6. If `tool_requests/pending/` has stale JSON files that are already complete (tool file exists in `tools/generated/`), clean them up:
   ```bash
   python -c "from pi.tool_requests.github_sync import GithubSync; import asyncio; asyncio.run(GithubSync().pull_completed_tools())"
   ```

---

## General Debugging Tips

**Read the service log:**
```bash
journalctl -u homeassistant-pi.service -f
```

**Run directly (not as a service) for verbose output:**
```bash
sudo systemctl stop homeassistant-pi.service
source venv/bin/activate
python -m pi.main
```

**Check all preflight conditions at once:**
```bash
bash scripts/first-run-check.sh
```

**Restart the service after changing config:**
```bash
sudo systemctl restart homeassistant-pi.service
```

**Persistent issues?** File a GitHub issue at `https://github.com/jeff-abe-98/homeassistant/issues` with the output of `journalctl -u homeassistant-pi.service -n 200` and `bash scripts/first-run-check.sh`.
