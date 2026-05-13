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
# Personal playlist hints that trigger user-playlist lookup before catalog search
_PERSONAL_PLAYLIST_HINTS = frozenset(
    {"discover weekly", "release radar", "daily mix", "time capsule", "on repeat"}
)


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


async def _ensure_tv_ready(sp, cfg) -> str:
    """Launch Spotify on TV and wait for it to appear in sp.devices().

    Returns the Spotify Connect device ID.
    Raises RuntimeError if the TV device never appears within the timeout.
    """
    if cfg.androidtv.host not in _UNCONFIGURED_TV_HOSTS:
        try:
            await _launch_spotify_on_tv(cfg.androidtv)
        except Exception:
            pass

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
    return device_id


async def _ensure_playing_on_tv(sp, cfg) -> str:
    """Launch Spotify on TV, poll until device appears, transfer playback.

    Returns the Spotify Connect device ID of the TV.
    Raises RuntimeError if the TV device never appears within the timeout.
    """
    device_id = await _ensure_tv_ready(sp, cfg)
    sp.transfer_playback(device_id=device_id, force_play=True)
    return device_id


def _find_user_playlist(sp, query: str) -> str | None:
    """Search the user's own playlists for one whose name contains query.

    Strips a leading "my " from query before matching.
    Returns the Spotify URI of the first match, or None.
    """
    target = query.lower().removeprefix("my ").strip()
    offset = 0
    while True:
        resp = sp.current_user_playlists(limit=50, offset=offset)
        for item in (resp.get("items") or []):
            if item and target in item.get("name", "").lower():
                return item["uri"]
        if resp.get("next") is None:
            break
        offset += 50
    return None


def _search_spotify(sp, query: str):
    """Search Spotify for query; return (context_uri, track_uris, description).

    Strategy:
    - Personal playlist hints (my ..., Discover Weekly, etc.) → user playlists first.
    - Short/vague query (≤3 words, no " by ") → prefer Spotify-curated playlist.
    - Specific query (song + artist) → prefer track.

    Returns (None, None, None) if nothing is found.
    """
    query_lower = query.lower()
    is_personal = query_lower.startswith("my ") or any(
        hint in query_lower for hint in _PERSONAL_PLAYLIST_HINTS
    )
    if is_personal:
        uri = _find_user_playlist(sp, query)
        if uri:
            return uri, None, query

    results = sp.search(q=query, type="track,playlist", limit=5)
    playlists = [p for p in ((results.get("playlists") or {}).get("items") or []) if p]
    tracks = [t for t in ((results.get("tracks") or {}).get("items") or []) if t]

    # Short/vague query → mood/genre → prefer playlist
    prefer_playlist = len(query.strip().split()) <= 3 and " by " not in query_lower

    if prefer_playlist and playlists:
        pl = playlists[0]
        return pl["uri"], None, pl.get("name", query)

    if tracks:
        track = tracks[0]
        name = track.get("name", "")
        artist = ", ".join(a["name"] for a in (track.get("artists") or []))
        desc = f"{name} by {artist}" if artist else name
        return None, [track["uri"]], desc

    if playlists:
        pl = playlists[0]
        return pl["uri"], None, pl.get("name", query)

    return None, None, None


def _search_and_play(sp, query: str, device_id: str) -> str:
    """Search for query and call sp.start_playback on device_id.

    Returns a natural language description of what started playing.
    """
    context_uri, track_uris, description = _search_spotify(sp, query)
    if context_uri is None and track_uris is None:
        return f"I couldn't find anything on Spotify for \"{query}\"."
    sp.start_playback(device_id=device_id, context_uri=context_uri, uris=track_uris)
    return f"Playing {description} on the TV."


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
        query = (params.get("query") or "").strip()
        if query:
            device_id = await _ensure_tv_ready(sp, cfg)
            return _search_and_play(sp, query, device_id)
        await _ensure_playing_on_tv(sp, cfg)
        return f"Playing on the TV for {display}."
    else:
        return (
            f"Spotify is connected for {display}, "
            "but that action isn't wired up yet — it's coming in the next update."
        )
