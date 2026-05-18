"""Smoke tests for server/tools/music_recommendations.py."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sp(tracks=None, featured_name="Featured Mix"):
    sp = MagicMock()
    if tracks is None:
        tracks = [
            {"uri": f"spotify:track:{i}", "name": f"Track {i}"}
            for i in range(5)
        ]
    sp.recommendations.return_value = {"tracks": tracks}
    sp.devices.return_value = {"devices": [{"type": "TV", "id": "tv-device-id"}]}
    sp.featured_playlists.return_value = {
        "playlists": {"items": [{"uri": "spotify:playlist:feat1", "name": featured_name}]}
    }
    sp.search.return_value = {"artists": {"items": [{"id": "artist-id-1"}]}}
    sp.start_playback.return_value = None
    # record_play internals
    sp.track.return_value = {
        "name": "Track",
        "artists": [{"name": "Artist", "id": "art1"}],
    }
    sp.artist.return_value = {"genres": ["pop"]}
    sp.audio_features.return_value = [{"acousticness": 0.3, "danceability": 0.7,
                                        "energy": 0.8, "valence": 0.6, "tempo": 120.0}]
    return sp


def _make_profile(has_history=True):
    from server.tools.music_profile import AudioTargets, TasteProfile

    if not has_history:
        return TasteProfile(user="owner")
    return TasteProfile(
        user="owner",
        genre_weights={"pop": 0.5, "indie": 0.3, "rock": 0.2},
        artist_weights={"Artist A": 0.8, "Artist B": 0.5},
        audio_targets=AudioTargets(
            target_energy=0.7,
            target_danceability=0.6,
            target_valence=0.65,
            target_tempo=125.0,
        ),
    )


def _cfg():
    import shared.config as cfg_module
    cfg = cfg_module.AppConfig()
    cfg.spotify.owner.client_id = "real_id"
    cfg.spotify.owner.client_secret = "real_secret"
    cfg.androidtv.host = "192.168.x.x"  # unconfigured → skip TV launch
    return cfg


# ---------------------------------------------------------------------------
# _resolve_artist_ids
# ---------------------------------------------------------------------------


def test_resolve_artist_ids_returns_ids():
    from server.tools.music_recommendations import _resolve_artist_ids

    sp = MagicMock()
    sp.search.return_value = {"artists": {"items": [{"id": "id123"}]}}
    ids = _resolve_artist_ids(sp, ["Artist A"])
    assert ids == ["id123"]


def test_resolve_artist_ids_skips_empty_results():
    from server.tools.music_recommendations import _resolve_artist_ids

    sp = MagicMock()
    sp.search.return_value = {"artists": {"items": []}}
    ids = _resolve_artist_ids(sp, ["Unknown Artist"])
    assert ids == []


def test_resolve_artist_ids_swallows_exceptions():
    from server.tools.music_recommendations import _resolve_artist_ids

    sp = MagicMock()
    sp.search.side_effect = RuntimeError("network error")
    ids = _resolve_artist_ids(sp, ["Artist A"])
    assert ids == []


def test_resolve_artist_ids_multiple():
    from server.tools.music_recommendations import _resolve_artist_ids

    sp = MagicMock()
    sp.search.return_value = {"artists": {"items": [{"id": "some-id"}]}}
    ids = _resolve_artist_ids(sp, ["A", "B"])
    assert len(ids) == 2


# ---------------------------------------------------------------------------
# _cold_start
# ---------------------------------------------------------------------------


def test_cold_start_plays_featured_playlist():
    from server.tools.music_recommendations import _cold_start

    sp = _make_sp()
    cfg = _cfg()

    async def run():
        return await _cold_start(sp, "owner", "Owner", cfg)

    result = asyncio.run(run())
    assert "Featured Mix" in result
    sp.start_playback.assert_called_once()


def test_cold_start_no_playlists_returns_message():
    from server.tools.music_recommendations import _cold_start

    sp = _make_sp()
    sp.featured_playlists.return_value = {"playlists": {"items": []}}
    cfg = _cfg()

    async def run():
        return await _cold_start(sp, "owner", "Owner", cfg)

    result = asyncio.run(run())
    assert "don't have enough history" in result
    sp.start_playback.assert_not_called()


def test_cold_start_featured_playlists_exception():
    from server.tools.music_recommendations import _cold_start

    sp = _make_sp()
    sp.featured_playlists.side_effect = RuntimeError("api error")
    cfg = _cfg()

    async def run():
        return await _cold_start(sp, "owner", "Owner", cfg)

    result = asyncio.run(run())
    assert "don't have enough history" in result


# ---------------------------------------------------------------------------
# _recommend — normal path
# ---------------------------------------------------------------------------


def test_recommend_calls_recommendations_with_seeds():
    from server.tools.music_recommendations import _recommend

    sp = _make_sp()
    cfg = _cfg()
    profile = _make_profile(has_history=True)

    with patch("server.tools.music_recommendations.build_profile", return_value=profile), \
         patch("server.tools.music_recommendations.recently_played_ids", return_value=set()), \
         patch("server.tools.music_recommendations.record_play"):
        result = asyncio.run(_recommend(sp, "owner", "Owner", cfg))

    assert "Queuing" in result
    sp.recommendations.assert_called_once()
    call_kwargs = sp.recommendations.call_args.kwargs
    assert "seed_genres" in call_kwargs
    assert len(call_kwargs["seed_genres"]) <= 3


def test_recommend_filters_recently_played():
    from server.tools.music_recommendations import _recommend

    tracks = [{"uri": f"spotify:track:{i}"} for i in range(3)]
    sp = _make_sp(tracks=tracks)
    cfg = _cfg()
    profile = _make_profile(has_history=True)
    # Filter all but one track as recently played
    recent = {"spotify:track:0", "spotify:track:1"}

    with patch("server.tools.music_recommendations.build_profile", return_value=profile), \
         patch("server.tools.music_recommendations.recently_played_ids", return_value=recent), \
         patch("server.tools.music_recommendations.record_play"):
        result = asyncio.run(_recommend(sp, "owner", "Owner", cfg))

    assert "Queuing 1" in result
    uris_played = sp.start_playback.call_args.kwargs.get("uris") or \
                  sp.start_playback.call_args[1].get("uris", [])
    assert "spotify:track:2" in uris_played


def test_recommend_cold_start_when_no_profile():
    from server.tools.music_recommendations import _recommend

    sp = _make_sp()
    cfg = _cfg()
    from server.tools.music_profile import TasteProfile
    empty_profile = TasteProfile(user="owner")

    with patch("server.tools.music_recommendations.build_profile", return_value=empty_profile):
        result = asyncio.run(_recommend(sp, "owner", "Owner", cfg))

    assert "learning your taste" in result
    sp.recommendations.assert_not_called()


def test_recommend_cold_start_when_all_recent():
    from server.tools.music_recommendations import _recommend

    tracks = [{"uri": "spotify:track:x"}]
    sp = _make_sp(tracks=tracks)
    cfg = _cfg()
    profile = _make_profile(has_history=True)

    with patch("server.tools.music_recommendations.build_profile", return_value=profile), \
         patch("server.tools.music_recommendations.recently_played_ids",
               return_value={"spotify:track:x"}), \
         patch("server.tools.music_recommendations.record_play"):
        result = asyncio.run(_recommend(sp, "owner", "Owner", cfg))

    # Falls through to cold start
    assert "learning your taste" in result


def test_recommend_cold_start_when_no_tracks_returned():
    from server.tools.music_recommendations import _recommend

    sp = _make_sp(tracks=[])
    cfg = _cfg()
    profile = _make_profile(has_history=True)

    with patch("server.tools.music_recommendations.build_profile", return_value=profile), \
         patch("server.tools.music_recommendations.recently_played_ids", return_value=set()):
        result = asyncio.run(_recommend(sp, "owner", "Owner", cfg))

    assert "learning your taste" in result


def test_recommend_records_plays():
    from server.tools.music_recommendations import _recommend

    tracks = [{"uri": "spotify:track:abc"}]
    sp = _make_sp(tracks=tracks)
    cfg = _cfg()
    profile = _make_profile(has_history=True)

    with patch("server.tools.music_recommendations.build_profile", return_value=profile), \
         patch("server.tools.music_recommendations.recently_played_ids", return_value=set()), \
         patch("server.tools.music_recommendations.record_play") as mock_record:
        asyncio.run(_recommend(sp, "owner", "Owner", cfg))

    mock_record.assert_called_once_with("owner", "spotify:track:abc", sp,
                                        play_source="recommendation")


def test_recommend_audio_targets_passed_to_spotify():
    from server.tools.music_recommendations import _recommend

    sp = _make_sp()
    cfg = _cfg()
    profile = _make_profile(has_history=True)

    with patch("server.tools.music_recommendations.build_profile", return_value=profile), \
         patch("server.tools.music_recommendations.recently_played_ids", return_value=set()), \
         patch("server.tools.music_recommendations.record_play"):
        asyncio.run(_recommend(sp, "owner", "Owner", cfg))

    kwargs = sp.recommendations.call_args.kwargs
    assert kwargs["target_energy"] == profile.audio_targets.target_energy
    assert kwargs["target_danceability"] == profile.audio_targets.target_danceability
    assert kwargs["target_valence"] == profile.audio_targets.target_valence
    assert kwargs["target_tempo"] == profile.audio_targets.target_tempo


# ---------------------------------------------------------------------------
# MusicRecommendationTool.run — unconfigured
# ---------------------------------------------------------------------------


def test_tool_run_unconfigured_returns_message():
    from server.tools.music_recommendations import MusicRecommendationTool

    tool = MusicRecommendationTool()
    with patch("server.tools.music_recommendations.cfg_module.load") as mock_load:
        cfg = MagicMock()
        cfg.spotify.owner.client_id = ""
        cfg.spotify.owner.client_secret = ""
        mock_load.return_value = cfg
        result = asyncio.run(tool.run({}, "owner"))

    assert "Spotify isn't set up" in result


def test_tool_run_premium_error():
    from server.tools.music_recommendations import MusicRecommendationTool

    tool = MusicRecommendationTool()
    with patch("server.tools.music_recommendations.cfg_module.load") as mock_load, \
         patch("server.tools.music_recommendations._get_spotify") as mock_get_sp, \
         patch("server.tools.music_recommendations._is_configured", return_value=True), \
         patch("server.tools.music_recommendations._recommend",
               side_effect=Exception("403 premium required")):
        mock_load.return_value = MagicMock()
        mock_get_sp.return_value = MagicMock()
        result = asyncio.run(tool.run({}, "owner"))

    assert "Premium" in result


def test_tool_has_correct_name():
    from server.tools.music_recommendations import MusicRecommendationTool

    assert MusicRecommendationTool.name == "music_recommendation"


def test_tool_description_contains_trigger_phrases():
    from server.tools.music_recommendations import MusicRecommendationTool

    desc = MusicRecommendationTool.description.lower()
    assert "surprise me" in desc
    assert "i'd like" in desc


# ---------------------------------------------------------------------------
# Voice interface — ToolRegistry discovery + end-to-end routing
# ---------------------------------------------------------------------------


def test_music_recommendation_tool_discovered_by_registry():
    """ToolRegistry.load() must find MusicRecommendationTool automatically."""
    from server.tools.base import ToolRegistry

    registry = ToolRegistry()
    registry.load()
    tool = registry.get("music_recommendation")
    assert tool is not None
    assert tool.name == "music_recommendation"


def test_voice_play_something_i_would_like_returns_recommendation():
    """'Play something I'd like' → MusicRecommendationTool.run() → recommendation response."""
    from server.tools.music_recommendations import MusicRecommendationTool

    sp = _make_sp()
    cfg = _cfg()
    profile = _make_profile(has_history=True)

    tool = MusicRecommendationTool()

    with patch("server.tools.music_recommendations.cfg_module.load", return_value=cfg), \
         patch("server.tools.music_recommendations._is_configured", return_value=True), \
         patch("server.tools.music_recommendations._get_spotify", return_value=sp), \
         patch("server.tools.music_recommendations.build_profile", return_value=profile), \
         patch("server.tools.music_recommendations.recently_played_ids", return_value=set()), \
         patch("server.tools.music_recommendations.record_play"):
        result = asyncio.run(tool.run({}, "owner"))

    # Should queue tracks, not cold-start
    assert "Queuing" in result
    sp.start_playback.assert_called_once()


def test_voice_surprise_me_cold_start_response():
    """'Surprise me' with no history → friendly 'still learning' message."""
    from server.tools.music_recommendations import MusicRecommendationTool
    from server.tools.music_profile import TasteProfile

    sp = _make_sp()
    cfg = _cfg()
    empty_profile = TasteProfile(user="owner")

    tool = MusicRecommendationTool()

    with patch("server.tools.music_recommendations.cfg_module.load", return_value=cfg), \
         patch("server.tools.music_recommendations._is_configured", return_value=True), \
         patch("server.tools.music_recommendations._get_spotify", return_value=sp), \
         patch("server.tools.music_recommendations.build_profile", return_value=empty_profile):
        result = asyncio.run(tool.run({}, "owner"))

    assert "learning your taste" in result or "Featured Mix" in result
