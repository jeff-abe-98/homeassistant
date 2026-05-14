"""Integration tests for SpotifyTool — end-to-end playback flows.

Skips automatically when Spotify credentials are still placeholders.
When real credentials are configured, these tests verify the complete
playback routing:
  - config loads and credentials are recognised as configured
  - correct per-user Spotify account is selected
  - search strategy routes correctly (mood→playlist, personal→user playlist)
  - sp.start_playback() is called with the TV device ID and search result

The spotipy network calls (search, start_playback, devices, current_user_playlists)
are mocked — the tests do not require active Spotify sessions or a physical TV.

Run with: pytest tests/test_spotify_integration.py -v -s
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import shared.config as cfg_module

_CHANGE_ME = {"", "CHANGE_ME"}


def _owner_credentials_configured() -> bool:
    cfg = cfg_module.load()
    return (
        cfg.spotify.owner.client_id not in _CHANGE_ME
        and cfg.spotify.owner.client_secret not in _CHANGE_ME
    )


def _emily_credentials_configured() -> bool:
    cfg = cfg_module.load()
    return (
        cfg.spotify.emily.client_id not in _CHANGE_ME
        and cfg.spotify.emily.client_secret not in _CHANGE_ME
    )


_REQUIRES_OWNER_SPOTIFY = pytest.mark.skipif(
    not _owner_credentials_configured(),
    reason=(
        "No real Owner Spotify credentials configured — set spotify.owner.client_id "
        "and spotify.owner.client_secret in config/settings.yaml"
    ),
)

_REQUIRES_EMILY_SPOTIFY = pytest.mark.skipif(
    not _emily_credentials_configured(),
    reason=(
        "No real Emily Spotify credentials configured — set spotify.emily.client_id "
        "and spotify.emily.client_secret in config/settings.yaml"
    ),
)


def _make_mock_sp_with_jazz_playlist() -> MagicMock:
    """Mock spotipy instance that returns a jazz playlist from search."""
    sp = MagicMock()
    sp.devices.return_value = {"devices": []}  # TV not yet in devices list
    sp.search.return_value = {
        "playlists": {
            "items": [{"uri": "spotify:playlist:jazz_vibes", "name": "Jazz Vibes"}]
        },
        "tracks": {"items": []},
    }
    sp.start_playback.return_value = None
    return sp


def _make_mock_sp_with_discover_weekly() -> MagicMock:
    """Mock spotipy instance where Emily has Discover Weekly in her playlists."""
    sp = MagicMock()
    sp.devices.return_value = {"devices": []}
    sp.current_user_playlists.return_value = {
        "items": [
            {"name": "Discover Weekly", "uri": "spotify:playlist:emily_dw"},
            {"name": "Liked Songs", "uri": "spotify:playlist:emily_liked"},
        ],
        "next": None,
    }
    sp.start_playback.return_value = None
    return sp


@_REQUIRES_OWNER_SPOTIFY
@pytest.mark.asyncio
async def test_owner_play_jazz_uses_owner_account_and_starts_playback() -> None:
    """Owner says 'Play some jazz' → searches Spotify, plays jazz playlist on TV.

    Verifies:
    - Owner's credentials are used (not Emily's)
    - 'jazz' (short mood query) triggers a catalog playlist search
    - sp.start_playback() is called with the TV device ID and jazz playlist URI
    - tool returns a confirmation mentioning jazz or 'Playing'
    """
    from server.tools.spotify import SpotifyTool

    tool = SpotifyTool()
    cfg = cfg_module.load()
    mock_sp = _make_mock_sp_with_jazz_playlist()

    with patch("server.tools.spotify._get_spotify", return_value=mock_sp) as mock_get, \
         patch("server.tools.spotify._ensure_tv_ready", AsyncMock(return_value="tv-device-123")):
        result = await tool.run({"action": "play", "query": "jazz"}, user="owner")

    mock_get.assert_called_once_with(cfg.spotify.owner)

    mock_sp.search.assert_called_once()
    search_query = mock_sp.search.call_args[1].get("q") or mock_sp.search.call_args[0][0]
    assert "jazz" in search_query.lower(), (
        f"search() must be called with 'jazz'; got query={search_query!r}"
    )

    mock_sp.start_playback.assert_called_once()
    call_kwargs = mock_sp.start_playback.call_args[1]
    assert call_kwargs.get("device_id") == "tv-device-123", (
        f"start_playback must target the TV device; got device_id={call_kwargs.get('device_id')!r}"
    )
    assert call_kwargs.get("context_uri") == "spotify:playlist:jazz_vibes", (
        f"Jazz playlist URI should be used as context_uri; got {call_kwargs.get('context_uri')!r}"
    )

    assert "jazz" in result.lower() or "playing" in result.lower(), (
        f"Response should confirm jazz playback; got: {result!r}"
    )


@_REQUIRES_EMILY_SPOTIFY
@pytest.mark.asyncio
async def test_emily_play_discover_weekly_uses_emily_account_and_user_playlist() -> None:
    """Emily says 'Play my Discover Weekly' → finds her personal playlist, plays on TV.

    Verifies:
    - Emily's credentials are used (not Owner's)
    - 'my Discover Weekly' triggers user-playlist lookup (current_user_playlists)
    - sp.start_playback() is called with the TV device ID and Emily's Discover Weekly URI
    - tool returns a confirmation mentioning Discover Weekly or 'Playing'
    """
    from server.tools.spotify import SpotifyTool

    tool = SpotifyTool()
    cfg = cfg_module.load()
    mock_sp = _make_mock_sp_with_discover_weekly()

    with patch("server.tools.spotify._get_spotify", return_value=mock_sp) as mock_get, \
         patch("server.tools.spotify._ensure_tv_ready", AsyncMock(return_value="tv-device-456")):
        result = await tool.run(
            {"action": "play", "query": "my Discover Weekly"}, user="emily"
        )

    mock_get.assert_called_once_with(cfg.spotify.emily)

    mock_sp.current_user_playlists.assert_called(), (
        "current_user_playlists() must be called to find Emily's personal playlist"
    )

    mock_sp.start_playback.assert_called_once()
    call_kwargs = mock_sp.start_playback.call_args[1]
    assert call_kwargs.get("device_id") == "tv-device-456", (
        f"start_playback must target the TV device; got device_id={call_kwargs.get('device_id')!r}"
    )
    assert call_kwargs.get("context_uri") == "spotify:playlist:emily_dw", (
        f"Emily's Discover Weekly URI should be used; got {call_kwargs.get('context_uri')!r}"
    )
    assert call_kwargs.get("uris") is None, (
        f"context_uri path should not pass uris; got uris={call_kwargs.get('uris')!r}"
    )

    assert "discover weekly" in result.lower() or "playing" in result.lower(), (
        f"Response should confirm Discover Weekly playback; got: {result!r}"
    )
