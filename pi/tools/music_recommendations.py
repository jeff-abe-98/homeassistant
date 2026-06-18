"""Music recommendation tool — "Play something I'd like"."""

from __future__ import annotations

import random

import shared.config as cfg_module
from pi.tools.base import BaseTool
from pi.tools.music_profile import build_profile, recently_played_ids, record_play
from pi.tools.spotify import (
    _ensure_tv_ready,
    _get_spotify,
    _is_configured,
    _user_cfg_and_display,
)


class MusicRecommendationTool(BaseTool):
    name = "music_recommendation"
    description = (
        "Play personalized music recommendations based on listening history. "
        "Use for: 'play something I'd like', 'play something good', "
        "'surprise me', 'play something for me', 'play music I like'."
    )
    parameters = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    async def run(self, params: dict, user: str) -> str:
        cfg = cfg_module.load()
        user_cfg, display = _user_cfg_and_display(cfg, user)

        if not _is_configured(user_cfg):
            return (
                f"Spotify isn't set up for {display} yet. "
                "Add your client_id and client_secret to config/settings.yaml."
            )

        try:
            sp = _get_spotify(user_cfg)
        except Exception as exc:
            return f"Couldn't initialize Spotify for {display}: {exc}"

        try:
            return await _recommend(sp, user, display, cfg)
        except Exception as exc:
            err = str(exc)
            if "premium" in err.lower() or "403" in err:
                return (
                    f"Spotify returned a Premium error for {display}. "
                    "Playback controls require Spotify Premium."
                )
            return f"Recommendation error: {err}"


async def _recommend(sp, user: str, display: str, cfg) -> str:
    profile = build_profile(user)

    if not profile.genre_weights and not profile.artist_weights:
        return await _cold_start(sp, user, display, cfg)

    top_genres = sorted(
        profile.genre_weights, key=profile.genre_weights.__getitem__, reverse=True
    )[:3]
    top_artists = sorted(
        profile.artist_weights, key=profile.artist_weights.__getitem__, reverse=True
    )[:2]

    seed_artist_ids = _resolve_artist_ids(sp, top_artists)

    at = profile.audio_targets
    kwargs: dict = dict(
        target_energy=at.target_energy,
        target_danceability=at.target_danceability,
        target_valence=at.target_valence,
        target_tempo=at.target_tempo,
        limit=20,
    )
    if top_genres:
        kwargs["seed_genres"] = top_genres
    if seed_artist_ids:
        kwargs["seed_artists"] = seed_artist_ids

    if not top_genres and not seed_artist_ids:
        return await _cold_start(sp, user, display, cfg)

    results = sp.recommendations(**kwargs)
    tracks = [t for t in (results.get("tracks") or []) if t]

    if not tracks:
        return await _cold_start(sp, user, display, cfg)

    recent = recently_played_ids(user, days=7)
    tracks = [t for t in tracks if t.get("uri") not in recent]

    if not tracks:
        return await _cold_start(sp, user, display, cfg)

    random.shuffle(tracks)
    uris = [t["uri"] for t in tracks]

    device_id = await _ensure_tv_ready(sp, cfg)
    sp.start_playback(device_id=device_id, uris=uris)

    for uri in uris:
        record_play(user, uri, sp, play_source="recommendation")

    return f"Queuing {len(uris)} tracks based on your listening history — enjoy."


def _resolve_artist_ids(sp, artist_names: list[str]) -> list[str]:
    """Search Spotify for each artist name and return their IDs."""
    ids: list[str] = []
    for name in artist_names:
        try:
            results = sp.search(q=name, type="artist", limit=1)
            items = ((results.get("artists") or {}).get("items") or [])
            if items:
                ids.append(items[0]["id"])
        except Exception:
            pass
    return ids


async def _cold_start(sp, user: str, display: str, cfg) -> str:
    """Fall back to a Spotify featured playlist when history is too thin."""
    try:
        featured = sp.featured_playlists(limit=5)
        playlists = ((featured.get("playlists") or {}).get("items") or [])
        playlists = [p for p in playlists if p]
    except Exception:
        playlists = []

    if not playlists:
        return (
            "I'm still learning your taste — I don't have enough history yet. "
            "Listen to some music first and I'll start making recommendations."
        )

    playlist = playlists[0]
    pl_uri = playlist.get("uri")
    pl_name = playlist.get("name", "a featured playlist")

    device_id = await _ensure_tv_ready(sp, cfg)
    sp.start_playback(device_id=device_id, context_uri=pl_uri)

    return (
        f"I'm still learning your taste — playing {pl_name} for now. "
        "I'll get better as you listen more."
    )
