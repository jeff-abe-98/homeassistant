"""Spotify playback tool — spotipy OAuth2 per user (Owner + Emily)."""

from __future__ import annotations

import asyncio

import shared.config as cfg_module
from server.tools.base import BaseTool

_CHANGE_ME = {"", "CHANGE_ME"}
_SCOPES = (
    "user-read-playback-state "
    "user-modify-playback-state "
    "user-read-currently-playing"
)
_UNCONFIGURED_TV_HOSTS = {"", "192.168.x.x"}
_TV_POLL_INTERVAL = 1.0   # seconds between sp.devices() polls
_TV_POLL_TIMEOUT = 15.0   # total seconds to wait for TV to appear in Spotify


def _is_configured(user_cfg) -> bool:
    """Return True if the user's Spotify credentials are not placeholders."""
    return (
        user_cfg.client_id not in _CHANGE_ME
        and user_cfg.client_secret not in _CHANGE_ME
    )


def _get_spotify(user_cfg):
    """Return an authenticated spotipy.Spotify instance for *user_cfg*.

    Uses SpotifyOAuth with a token cache file so the OAuth flow only needs to
    run once.  open_browser=False so the server doesn't try to pop a browser.
    """
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth

    auth_manager = SpotifyOAuth(
        client_id=user_cfg.client_id,
        client_secret=user_cfg.client_secret,
        redirect_uri=user_cfg.redirect_uri,
        scope=_SCOPES,
        cache_path=user_cfg.token_file,
        open_browser=False,
    )
    return spotipy.Spotify(auth_manager=auth_manager)


def _user_cfg_and_display(cfg, user: str):
    """Return (SpotifyUserConfig, display_name) for *user*."""
    if user.lower() == "emily":
        return cfg.spotify.emily, "Emily"
    return cfg.spotify.owner, "Owner"


def _find_tv_device_id(sp) -> str | None:
    """Return the Spotify Connect device ID for the TV, or None if not found.

    Always resolves fresh from sp.devices() — never cached, because the device
    ID changes across Spotify sessions.
    """
    resp = sp.devices()
    for dev in resp.get("devices", []):
        if dev.get("type", "").upper() == "TV":
            return dev["id"]
    return None


async def _launch_spotify_on_tv(atv_cfg) -> None:
    """Open com.spotify.tv.android on the Android TV via androidtvremote2."""
    from androidtvremote2 import AndroidTVRemote  # lazy — not installed on Pi

    atv = AndroidTVRemote(
        client_name="HomeAssistant",
        certfile=atv_cfg.cert_file,
        keyfile=atv_cfg.key_file,
        host=atv_cfg.host,
        port=atv_cfg.port,
    )
    await atv.async_generate_cert_if_missing()
    await atv.async_connect()
    try:
        atv.send_launch_app(
            "intent:#Intent;"
            "action=android.intent.action.MAIN;"
            "category=android.intent.category.LEANBACK_LAUNCHER;"
            "launchFlags=0x10000000;"
            "package=com.spotify.tv.android;end"
        )
    finally:
        atv.disconnect()


async def _ensure_playing_on_tv(sp, cfg) -> str:
    """Launch Spotify on TV and transfer Spotify playback to it.

    Steps:
      1. Launch com.spotify.tv.android via androidtvremote2 (best-effort).
      2. Poll sp.devices() until the TV device appears (up to _TV_POLL_TIMEOUT).
      3. Transfer playback to the TV with force_play=True.

    Returns the Spotify Connect device ID of the TV.
    Raises RuntimeError if the TV device never appears within the timeout.
    """
    # Launch Spotify on TV if androidtv is configured; swallow errors so a
    # TV that's already showing Spotify doesn't block playback transfer.
    if cfg.androidtv.host not in _UNCONFIGURED_TV_HOSTS:
        try:
            await _launch_spotify_on_tv(cfg.androidtv)
        except Exception:
            pass

    # Poll sp.devices() until the TV appears.  The device ID must never be
    # cached — it changes every time Spotify on the TV restarts.
    elapsed = 0.0
    device_id: str | None = None
    while elapsed < _TV_POLL_TIMEOUT:
        device_id = _find_tv_device_id(sp)
        if device_id:
            break
        await asyncio.sleep(_TV_POLL_INTERVAL)
        elapsed += _TV_POLL_INTERVAL

    if not device_id:
        raise RuntimeError(
            f"TV didn't appear in Spotify within {int(_TV_POLL_TIMEOUT)} seconds. "
            "Make sure the TV is on and the Spotify app is open."
        )

    sp.transfer_playback(device_id=device_id, force_play=True)
    return device_id


class SpotifyTool(BaseTool):
    name = "spotify_control"
    description = (
        "Play music on Spotify through the living room TV. "
        "Can play songs, artists, playlists, or mood queries, and control playback. "
        "Use for: 'play some jazz', 'play my Discover Weekly', 'pause the music', "
        "'skip this song', 'play Taylor Swift', 'what's playing', 'turn the volume up'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["play", "pause", "skip", "previous", "volume", "now_playing"],
                "description": (
                    "play: launch Spotify on TV and start/resume playback; "
                    "pause: pause playback; "
                    "skip: skip to next track; "
                    "previous: go back to previous track; "
                    "volume: set volume (requires level 0–100); "
                    "now_playing: describe what is currently playing."
                ),
            },
            "query": {
                "type": "string",
                "description": (
                    "Search query for play — song, artist, playlist, or mood. "
                    "e.g. 'jazz', 'Taylor Swift Midnights', 'my Discover Weekly'."
                ),
            },
            "level": {
                "type": "integer",
                "description": "Volume level 0–100. Only used with the volume action.",
            },
        },
        "required": ["action"],
    }

    async def run(self, params: dict, user: str) -> str:
        cfg = cfg_module.load()
        user_cfg, display = _user_cfg_and_display(cfg, user)

        if not _is_configured(user_cfg):
            return (
                f"Spotify isn't set up for {display} yet. "
                "Add your client_id and client_secret to config/settings.yaml "
                "under spotify. Both users need Spotify Premium for playback controls."
            )

        action = params.get("action", "now_playing")

        try:
            sp = _get_spotify(user_cfg)
        except Exception as exc:
            return f"Couldn't initialize Spotify for {display}: {exc}"

        try:
            return await _run_action(sp, action, params, display, cfg)
        except Exception as exc:
            err = str(exc)
            if "premium" in err.lower() or "403" in err:
                return (
                    f"Spotify returned a Premium error for {display}. "
                    "Playback controls require Spotify Premium."
                )
            if "token" in err.lower() or "oauth" in err.lower() or "auth" in err.lower():
                return (
                    f"Spotify isn't authorized for {display} yet. "
                    "Complete the OAuth flow to grant access."
                )
            return f"Spotify error: {err}"


async def _run_action(sp, action: str, params: dict, display: str, cfg) -> str:
    if action == "now_playing":
        current = sp.current_playback()
        if not current or not current.get("item"):
            return "Nothing is playing on Spotify right now."
        item = current["item"]
        track = item.get("name", "Unknown")
        artists = ", ".join(a["name"] for a in item.get("artists", []))
        return f"Now playing: {track} by {artists}."
    elif action == "play":
        await _ensure_playing_on_tv(sp, cfg)
        return f"Playing on the TV for {display}."
    else:
        return (
            f"Spotify is connected for {display}, "
            "but that action isn't wired up yet — it's coming in the next update."
        )
