# API Keys & Credentials Setup

This guide covers where to obtain and how to configure every external credential used by the home assistant. Each section maps to a field in `config/settings.yaml`.

**`config/settings.yaml` is gitignored** — your real credentials are never committed to the repository.

---

## CTA Train Tracker API Key

Used by the "When's the next Blue Line?" feature.

**`settings.yaml` field:** `cta.api_key`

### Steps

1. Go to **https://www.transitchicago.com/developers/traintrackerapply/**
2. Fill out the short registration form (name, email, intended use).
3. You will receive the API key by email within a few minutes.
4. Open `config/settings.yaml` and replace `CHANGE_ME` under `cta:`:
   ```yaml
   cta:
     api_key: YOUR_KEY_HERE
   ```

The `stop_id_ohare` and `stop_id_forest_park` values are pre-filled with the correct Blue Line / Western & Milwaukee stop IDs and do not need to change.

---

## OpenWeatherMap API Key

Used by the "What's the weather?" feature.

**`settings.yaml` field:** `weather.api_key`

### Steps

1. Create a free account at **https://openweathermap.org/api**
2. After signing in, go to **My API Keys** (top-right menu → API keys).
3. A default key is created automatically, or click **Generate** to create a named one.
4. Copy the key and paste it into `config/settings.yaml`:
   ```yaml
   weather:
     api_key: YOUR_KEY_HERE
     location: "Chicago, IL"   # Change to your city if needed
     units: imperial            # imperial = °F, metric = °C
   ```

> **Note:** Free tier keys activate within 10 minutes of account creation. The assistant uses the "Current Weather" and "3-hour Forecast" endpoints, both included in the free tier (1,000 calls/day).

---

## Google OAuth — Calendar & Tasks

Google Calendar and Google Tasks share one OAuth2 credential file (`google_credentials.json`). The first-run flow requires a browser and only needs to be run once.

**`settings.yaml` fields:** `google.credentials_file`, `google.token_file`

### Part A — Create a Google Cloud Project

1. Go to **https://console.cloud.google.com/**
2. Click the project dropdown at the top → **New Project**.
3. Name it (e.g. `homeassistant`) and click **Create**.
4. Make sure the new project is selected in the dropdown.

### Part B — Enable the APIs

1. In the left sidebar, go to **APIs & Services → Library**.
2. Search for and enable each of the following:
   - **Google Calendar API**
   - **Tasks API**

### Part C — Create OAuth2 Credentials

1. Go to **APIs & Services → Credentials**.
2. Click **Create Credentials → OAuth client ID**.
3. If prompted, configure the **OAuth consent screen** first:
   - User type: **External** (or Internal if using Google Workspace)
   - Fill in the app name (e.g. `Home Assistant`) and your email
   - Add the following scopes (click **Add or Remove Scopes**):
     - `https://www.googleapis.com/auth/calendar`
     - `https://www.googleapis.com/auth/tasks`
   - Add your Gmail address as a **Test user**
   - Save and return to Credentials
4. Back on **Create OAuth client ID**:
   - Application type: **Desktop app**
   - Name: anything (e.g. `homeassistant-pi`)
   - Click **Create**
5. Click **Download JSON** on the confirmation dialog.
6. Rename the downloaded file to `google_credentials.json` and copy it to the Pi:
   ```bash
   scp google_credentials.json pi@homeassistant.local:~/homeassistant/config/
   ```

### Part D — Run the First-Time Auth Flow

SSH into the Pi and run:

```bash
cd ~/homeassistant
source venv/bin/activate
python -c "from pi.tools.google_auth import get_credentials; get_credentials()"
```

The script prints a URL. Open it in any browser (the Pi does not need a display):
- Sign in with your Google account
- Click **Allow** to grant Calendar and Tasks access
- Copy the authorization code from the browser URL bar

Paste the code back into the terminal. The token is saved to `config/google_token.json`. All future runs use this token silently.

---

## Spotify App Credentials

Used to play music, control playback, and transfer audio to the Android TV.

**`settings.yaml` fields:** `spotify.owner.*`, `spotify.emily.*`

Both users need **Spotify Premium** for the Connect (playback transfer) API.

### Steps — Create a Spotify App (once, shared by both users)

1. Go to **https://developer.spotify.com/dashboard**
2. Log in with the **owner's** Spotify account.
3. Click **Create App**.
4. Fill in:
   - **App name:** anything (e.g. `Home Assistant`)
   - **App description:** anything
   - **Redirect URIs:** add both:
     - `http://localhost:8888/callback`
     - `http://localhost:8889/callback`
   - **Which API/SDKs are you planning to use?** → check **Web API**
5. Click **Save**.
6. On the app dashboard, click **Settings**.
7. Copy the **Client ID** and **Client Secret**.

### Fill in settings.yaml

```yaml
spotify:
  owner:
    client_id: PASTE_CLIENT_ID_HERE
    client_secret: PASTE_CLIENT_SECRET_HERE
    redirect_uri: http://localhost:8888/callback
  emily:
    client_id: PASTE_CLIENT_ID_HERE      # same app, same ID
    client_secret: PASTE_CLIENT_SECRET_HERE  # same app, same secret
    redirect_uri: http://localhost:8889/callback
```

### Authorize Each User Account

The first time either user asks to play music, the assistant triggers an OAuth flow in the background. To pre-authorize before first use:

**Owner account:**
```bash
source venv/bin/activate
python -c "
from pi.tools.spotify import SpotifyTool
tool = SpotifyTool()
sp = tool._get_spotify('owner')
print(sp.current_user())
"
```

**Emily's account:**
```bash
python -c "
from pi.tools.spotify import SpotifyTool
tool = SpotifyTool()
sp = tool._get_spotify('emily')
print(sp.current_user())
"
```

Each command opens a browser URL for that user's Spotify login. After approving, the token is saved to the file named in `users.owner.spotify_token_file` / `users.emily.spotify_token_file`.

> **Note:** Emily's Spotify account must be added as a user on the Spotify app dashboard (under **Users and Access**) while the app is in development mode. Alternatively, request Quota Extension to remove this requirement.

---

## Android TV Pairing

Used to power the TV on/off, launch apps (Netflix, Spotify, YouTube), and control playback.

**`settings.yaml` field:** `androidtv.host`

### Find the TV's IP Address

1. On the Android TV, go to **Settings → Network & Internet → (your network)**.
2. Note the **IP address** (e.g. `192.168.1.42`).

Alternatively, check your router's DHCP client list and find the entry for your Android TV.

### Set a Static IP (Recommended)

To prevent the IP from changing after a router reboot, assign a static (reserved) DHCP lease for the TV's MAC address in your router settings.

### Update settings.yaml

```yaml
androidtv:
  host: 192.168.1.42   # replace with your TV's IP
  port: 6466
```

### First-Time Pairing

The `androidtvremote2` library handles TLS certificate generation and pairing automatically on first connection. When the assistant first tries to control the TV, a pairing dialog will appear on the TV screen asking you to confirm the connection. Accept it once — the certificates are saved to `config/androidtv_cert.pem` and `config/androidtv_key.pem` and reused automatically afterward.

If the pairing dialog does not appear, try:
1. On the TV: **Settings → Device Preferences → Security & Restrictions → Unknown Sources** (allow)
2. Restart the assistant and try again

> **Note:** The Android TV must be on the same local network as the Pi. `port: 6466` is the standard Android TV Remote Service port and does not require ADB to be enabled.

---

## Credential File Summary

| Credential | Location in repo | Gitignored? |
|-----------|-----------------|-------------|
| All API keys | `config/settings.yaml` | Yes |
| Google OAuth app credentials | `config/google_credentials.json` | Yes |
| Google OAuth token | `config/google_token.json` | Yes |
| Spotify owner token | `config/spotify_token_owner.json` | Yes |
| Spotify Emily token | `config/spotify_token_emily.json` | Yes |
| Android TV TLS cert | `config/androidtv_cert.pem` | Yes |
| Android TV TLS key | `config/androidtv_key.pem` | Yes |

None of these files are committed. The `config/` directory in the repo contains only placeholder skeleton files and `google_credentials.json.example`.
