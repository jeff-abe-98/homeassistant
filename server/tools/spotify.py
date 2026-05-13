"""Spotify playback tool — spotipy OAuth2 per user (Owner + Emily)."""

from __future__ import annotations

import shared.config as cfg_module
from server.tools.base import BaseTool

_CHANGE_ME = {"", "CHANGE_ME"}
_SCOPES = (
    "user-read-playback-state "
    "user-modify-playback-state "
    "user-read-currently-playing"
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
                    "play: search and play music (requires query); "
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
            return await _run_action(sp, action, params, display)
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


async def _run_action(sp, action: str, params: dict, display: str) -> str:
    if action == "now_playing":
        current = sp.current_playback()
        if not current or not current.get("item"):
            return "Nothing is playing on Spotify right now."
        item = current["item"]
        track = item.get("name", "Unknown")
        artists = ", ".join(a["name"] for a in item.get("artists", []))
        return f"Now playing: {track} by {artists}."
    else:
        return (
            f"Spotify is connected for {display}, "
            "but that action isn't wired up yet — it's coming in the next update."
        )
