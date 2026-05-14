"""Smoke tests for SpotifyTool and SpotifyConfig wiring.

Run with: pytest tests/test_spotify.py -v
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Config wiring
# ---------------------------------------------------------------------------


def test_spotify_config_defaults() -> None:
    from shared.config import AppConfig

    cfg = AppConfig()
    assert cfg.spotify.owner.client_id == ""
    assert cfg.spotify.owner.client_secret == ""
    assert cfg.spotify.owner.redirect_uri == "http://localhost:8888/callback"
    assert cfg.spotify.emily.client_id == ""


def test_spotify_token_file_default_via_load(tmp_path) -> None:
    """load() with empty YAML supplies default token file paths from users section fallback."""
    settings = tmp_path / "settings.yaml"
    settings.write_text("{}\n")
    import shared.config as cfg_module

    cfg = cfg_module.load(str(settings))
    assert cfg.spotify.owner.token_file == "config/spotify_token_owner.json"
    assert cfg.spotify.emily.token_file == "config/spotify_token_emily.json"


def test_spotify_config_loaded_from_yaml(tmp_path) -> None:
    settings = tmp_path / "settings.yaml"
    settings.write_text(
        "spotify:\n"
        "  owner:\n"
        "    client_id: owner_id\n"
        "    client_secret: owner_secret\n"
        "    redirect_uri: http://localhost:8888/callback\n"
        "  emily:\n"
        "    client_id: emily_id\n"
        "    client_secret: emily_secret\n"
        "    redirect_uri: http://localhost:8889/callback\n"
        "users:\n"
        "  owner:\n"
        "    spotify_token_file: config/spotify_token_owner.json\n"
        "  emily:\n"
        "    spotify_token_file: config/spotify_token_emily.json\n"
    )
    import shared.config as cfg_module

    cfg = cfg_module.load(str(settings))
    assert cfg.spotify.owner.client_id == "owner_id"
    assert cfg.spotify.owner.client_secret == "owner_secret"
    assert cfg.spotify.owner.redirect_uri == "http://localhost:8888/callback"
    assert cfg.spotify.owner.token_file == "config/spotify_token_owner.json"
    assert cfg.spotify.emily.client_id == "emily_id"
    assert cfg.spotify.emily.redirect_uri == "http://localhost:8889/callback"
    assert cfg.spotify.emily.token_file == "config/spotify_token_emily.json"


def test_token_file_falls_back_to_default_when_users_section_absent(tmp_path) -> None:
    settings = tmp_path / "settings.yaml"
    settings.write_text(
        "spotify:\n"
        "  owner:\n"
        "    client_id: some_id\n"
    )
    import shared.config as cfg_module

    cfg = cfg_module.load(str(settings))
    assert cfg.spotify.owner.token_file == "config/spotify_token_owner.json"
    assert cfg.spotify.emily.token_file == "config/spotify_token_emily.json"


# ---------------------------------------------------------------------------
# _is_configured
# ---------------------------------------------------------------------------


def test_is_configured_with_real_credentials() -> None:
    from server.tools.spotify import _is_configured

    user_cfg = MagicMock()
    user_cfg.client_id = "real_client_id"
    user_cfg.client_secret = "real_client_secret"
    assert _is_configured(user_cfg) is True


def test_is_configured_with_change_me() -> None:
    from server.tools.spotify import _is_configured

    user_cfg = MagicMock()
    user_cfg.client_id = "CHANGE_ME"
    user_cfg.client_secret = "CHANGE_ME"
    assert _is_configured(user_cfg) is False


def test_is_configured_with_empty_string() -> None:
    from server.tools.spotify import _is_configured

    user_cfg = MagicMock()
    user_cfg.client_id = ""
    user_cfg.client_secret = ""
    assert _is_configured(user_cfg) is False


def test_is_configured_with_empty_secret_only() -> None:
    from server.tools.spotify import _is_configured

    user_cfg = MagicMock()
    user_cfg.client_id = "real_id"
    user_cfg.client_secret = ""
    assert _is_configured(user_cfg) is False


# ---------------------------------------------------------------------------
# SpotifyTool.run() — unconfigured state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unconfigured_owner_returns_setup_message() -> None:
    from server.tools.spotify import SpotifyTool

    tool = SpotifyTool()
    mock_cfg = MagicMock()
    mock_cfg.spotify.owner.client_id = "CHANGE_ME"
    mock_cfg.spotify.owner.client_secret = "CHANGE_ME"

    with patch("server.tools.spotify.cfg_module.load", return_value=mock_cfg):
        result = await tool.run({"action": "now_playing"}, user="owner")

    assert "set up" in result.lower()
    assert "owner" in result.lower()


@pytest.mark.asyncio
async def test_unconfigured_emily_returns_emily_in_message() -> None:
    from server.tools.spotify import SpotifyTool

    tool = SpotifyTool()
    mock_cfg = MagicMock()
    mock_cfg.spotify.emily.client_id = "CHANGE_ME"
    mock_cfg.spotify.emily.client_secret = "CHANGE_ME"

    with patch("server.tools.spotify.cfg_module.load", return_value=mock_cfg):
        result = await tool.run({"action": "now_playing"}, user="emily")

    assert "emily" in result.lower()
    assert "set up" in result.lower()


# ---------------------------------------------------------------------------
# SpotifyTool.run() — user routing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_emily_routes_to_emily_config() -> None:
    from server.tools.spotify import SpotifyTool

    tool = SpotifyTool()
    mock_cfg = MagicMock()
    mock_cfg.spotify.emily.client_id = "emily_id"
    mock_cfg.spotify.emily.client_secret = "emily_secret"

    mock_sp = MagicMock()
    mock_sp.current_playback.return_value = None

    with patch("server.tools.spotify.cfg_module.load", return_value=mock_cfg), \
         patch("server.tools.spotify._get_spotify", return_value=mock_sp) as mock_get:
        await tool.run({"action": "now_playing"}, user="emily")

    mock_get.assert_called_once_with(mock_cfg.spotify.emily)


@pytest.mark.asyncio
async def test_owner_routes_to_owner_config() -> None:
    from server.tools.spotify import SpotifyTool

    tool = SpotifyTool()
    mock_cfg = MagicMock()
    mock_cfg.spotify.owner.client_id = "owner_id"
    mock_cfg.spotify.owner.client_secret = "owner_secret"

    mock_sp = MagicMock()
    mock_sp.current_playback.return_value = None

    with patch("server.tools.spotify.cfg_module.load", return_value=mock_cfg), \
         patch("server.tools.spotify._get_spotify", return_value=mock_sp) as mock_get:
        await tool.run({"action": "now_playing"}, user="owner")

    mock_get.assert_called_once_with(mock_cfg.spotify.owner)


@pytest.mark.asyncio
async def test_unknown_user_routes_to_owner_config() -> None:
    from server.tools.spotify import SpotifyTool

    tool = SpotifyTool()
    mock_cfg = MagicMock()
    mock_cfg.spotify.owner.client_id = "owner_id"
    mock_cfg.spotify.owner.client_secret = "owner_secret"

    mock_sp = MagicMock()
    mock_sp.current_playback.return_value = None

    with patch("server.tools.spotify.cfg_module.load", return_value=mock_cfg), \
         patch("server.tools.spotify._get_spotify", return_value=mock_sp) as mock_get:
        await tool.run({"action": "now_playing"}, user="unknown")

    mock_get.assert_called_once_with(mock_cfg.spotify.owner)


# ---------------------------------------------------------------------------
# SpotifyTool.run() — now_playing action
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_now_playing_returns_track_and_artist() -> None:
    from server.tools.spotify import SpotifyTool

    tool = SpotifyTool()
    mock_cfg = MagicMock()
    mock_cfg.spotify.owner.client_id = "owner_id"
    mock_cfg.spotify.owner.client_secret = "owner_secret"

    mock_sp = MagicMock()
    mock_sp.current_playback.return_value = {
        "item": {
            "name": "Blue in Green",
            "artists": [{"name": "Miles Davis"}],
        }
    }

    with patch("server.tools.spotify.cfg_module.load", return_value=mock_cfg), \
         patch("server.tools.spotify._get_spotify", return_value=mock_sp):
        result = await tool.run({"action": "now_playing"}, user="owner")

    assert "Blue in Green" in result
    assert "Miles Davis" in result


@pytest.mark.asyncio
async def test_now_playing_multiple_artists() -> None:
    from server.tools.spotify import SpotifyTool

    tool = SpotifyTool()
    mock_cfg = MagicMock()
    mock_cfg.spotify.owner.client_id = "owner_id"
    mock_cfg.spotify.owner.client_secret = "owner_secret"

    mock_sp = MagicMock()
    mock_sp.current_playback.return_value = {
        "item": {
            "name": "Fela in London",
            "artists": [{"name": "Fela Kuti"}, {"name": "Roy Ayers"}],
        }
    }

    with patch("server.tools.spotify.cfg_module.load", return_value=mock_cfg), \
         patch("server.tools.spotify._get_spotify", return_value=mock_sp):
        result = await tool.run({"action": "now_playing"}, user="owner")

    assert "Fela Kuti" in result
    assert "Roy Ayers" in result


@pytest.mark.asyncio
async def test_now_playing_nothing_returns_nothing_message() -> None:
    from server.tools.spotify import SpotifyTool

    tool = SpotifyTool()
    mock_cfg = MagicMock()
    mock_cfg.spotify.owner.client_id = "owner_id"
    mock_cfg.spotify.owner.client_secret = "owner_secret"

    mock_sp = MagicMock()
    mock_sp.current_playback.return_value = None

    with patch("server.tools.spotify.cfg_module.load", return_value=mock_cfg), \
         patch("server.tools.spotify._get_spotify", return_value=mock_sp):
        result = await tool.run({"action": "now_playing"}, user="owner")

    assert "nothing" in result.lower()


@pytest.mark.asyncio
async def test_now_playing_empty_item_returns_nothing_message() -> None:
    from server.tools.spotify import SpotifyTool

    tool = SpotifyTool()
    mock_cfg = MagicMock()
    mock_cfg.spotify.owner.client_id = "owner_id"
    mock_cfg.spotify.owner.client_secret = "owner_secret"

    mock_sp = MagicMock()
    mock_sp.current_playback.return_value = {"item": None}

    with patch("server.tools.spotify.cfg_module.load", return_value=mock_cfg), \
         patch("server.tools.spotify._get_spotify", return_value=mock_sp):
        result = await tool.run({"action": "now_playing"}, user="owner")

    assert "nothing" in result.lower()


# ---------------------------------------------------------------------------
# SpotifyTool.run() — error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_premium_error_returns_friendly_message() -> None:
    from server.tools.spotify import SpotifyTool

    tool = SpotifyTool()
    mock_cfg = MagicMock()
    mock_cfg.spotify.owner.client_id = "owner_id"
    mock_cfg.spotify.owner.client_secret = "owner_secret"

    mock_sp = MagicMock()
    mock_sp.current_playback.side_effect = Exception("403 Forbidden: Premium required")

    with patch("server.tools.spotify.cfg_module.load", return_value=mock_cfg), \
         patch("server.tools.spotify._get_spotify", return_value=mock_sp):
        result = await tool.run({"action": "now_playing"}, user="owner")

    assert "premium" in result.lower()


@pytest.mark.asyncio
async def test_auth_error_returns_oauth_message() -> None:
    from server.tools.spotify import SpotifyTool

    tool = SpotifyTool()
    mock_cfg = MagicMock()
    mock_cfg.spotify.owner.client_id = "owner_id"
    mock_cfg.spotify.owner.client_secret = "owner_secret"

    mock_sp = MagicMock()
    mock_sp.current_playback.side_effect = Exception("No token in cache: oauth flow needed")

    with patch("server.tools.spotify.cfg_module.load", return_value=mock_cfg), \
         patch("server.tools.spotify._get_spotify", return_value=mock_sp):
        result = await tool.run({"action": "now_playing"}, user="owner")

    assert "authorized" in result.lower() or "oauth" in result.lower()


@pytest.mark.asyncio
async def test_get_spotify_init_error_is_caught() -> None:
    from server.tools.spotify import SpotifyTool

    tool = SpotifyTool()
    mock_cfg = MagicMock()
    mock_cfg.spotify.owner.client_id = "owner_id"
    mock_cfg.spotify.owner.client_secret = "owner_secret"

    with patch("server.tools.spotify.cfg_module.load", return_value=mock_cfg), \
         patch("server.tools.spotify._get_spotify", side_effect=Exception("init failed")):
        result = await tool.run({"action": "now_playing"}, user="owner")

    assert "couldn't" in result.lower() or "error" in result.lower()


# ---------------------------------------------------------------------------
# _find_tv_device_id — always resolves fresh from sp.devices()
# ---------------------------------------------------------------------------


def test_find_tv_device_id_returns_tv_device() -> None:
    from server.tools.spotify import _find_tv_device_id

    sp = MagicMock()
    sp.devices.return_value = {
        "devices": [{"id": "tv-device-abc", "type": "TV", "name": "Hisense TV"}]
    }
    assert _find_tv_device_id(sp) == "tv-device-abc"


def test_find_tv_device_id_returns_none_when_no_tv() -> None:
    from server.tools.spotify import _find_tv_device_id

    sp = MagicMock()
    sp.devices.return_value = {
        "devices": [{"id": "phone-id", "type": "Smartphone", "name": "Jeff's Phone"}]
    }
    assert _find_tv_device_id(sp) is None


def test_find_tv_device_id_returns_none_when_no_devices() -> None:
    from server.tools.spotify import _find_tv_device_id

    sp = MagicMock()
    sp.devices.return_value = {"devices": []}
    assert _find_tv_device_id(sp) is None


def test_find_tv_device_id_skips_non_tv_types() -> None:
    from server.tools.spotify import _find_tv_device_id

    sp = MagicMock()
    sp.devices.return_value = {
        "devices": [
            {"id": "comp-id", "type": "Computer", "name": "Laptop"},
            {"id": "tv-id", "type": "TV", "name": "Living Room TV"},
        ]
    }
    assert _find_tv_device_id(sp) == "tv-id"


def test_find_tv_device_id_case_insensitive_type() -> None:
    from server.tools.spotify import _find_tv_device_id

    sp = MagicMock()
    sp.devices.return_value = {
        "devices": [{"id": "tv-id", "type": "tv", "name": "TV"}]
    }
    assert _find_tv_device_id(sp) == "tv-id"


def test_find_tv_device_id_calls_devices_each_time() -> None:
    """Must call sp.devices() fresh each invocation — never use a cache."""
    from server.tools.spotify import _find_tv_device_id

    sp = MagicMock()
    sp.devices.return_value = {"devices": [{"id": "tv-id", "type": "TV", "name": "TV"}]}
    _find_tv_device_id(sp)
    _find_tv_device_id(sp)
    assert sp.devices.call_count == 2


# ---------------------------------------------------------------------------
# _ensure_playing_on_tv — combined launch flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ensure_playing_on_tv_transfers_when_tv_found_immediately() -> None:
    from server.tools.spotify import _ensure_playing_on_tv

    sp = MagicMock()
    sp.devices.return_value = {"devices": [{"id": "tv-123", "type": "TV", "name": "TV"}]}

    mock_cfg = MagicMock()
    mock_cfg.androidtv.host = "192.168.x.x"  # unconfigured → skip launch

    with patch("asyncio.sleep", new_callable=AsyncMock):
        device_id = await _ensure_playing_on_tv(sp, mock_cfg)

    assert device_id == "tv-123"
    sp.transfer_playback.assert_called_once_with(device_id="tv-123", force_play=True)


@pytest.mark.asyncio
async def test_ensure_playing_on_tv_polls_until_tv_appears() -> None:
    from server.tools.spotify import _ensure_playing_on_tv

    sp = MagicMock()
    # First call: no devices; second call: TV appears
    sp.devices.side_effect = [
        {"devices": []},
        {"devices": [{"id": "tv-456", "type": "TV", "name": "TV"}]},
    ]

    mock_cfg = MagicMock()
    mock_cfg.androidtv.host = "192.168.x.x"  # skip TV launch

    with patch("asyncio.sleep", new_callable=AsyncMock):
        device_id = await _ensure_playing_on_tv(sp, mock_cfg)

    assert device_id == "tv-456"
    assert sp.devices.call_count == 2
    sp.transfer_playback.assert_called_once_with(device_id="tv-456", force_play=True)


@pytest.mark.asyncio
async def test_ensure_playing_on_tv_raises_on_timeout() -> None:
    from server.tools.spotify import _ensure_playing_on_tv

    sp = MagicMock()
    sp.devices.return_value = {"devices": []}  # TV never appears

    mock_cfg = MagicMock()
    mock_cfg.androidtv.host = "192.168.x.x"

    with patch("server.tools.spotify._TV_POLL_TIMEOUT", 0), \
         patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(RuntimeError, match="TV didn't appear"):
            await _ensure_playing_on_tv(sp, mock_cfg)

    sp.transfer_playback.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_playing_on_tv_launches_spotify_app_when_tv_configured() -> None:
    from server.tools.spotify import _ensure_playing_on_tv

    sp = MagicMock()
    sp.devices.return_value = {"devices": [{"id": "tv-789", "type": "TV", "name": "TV"}]}

    mock_cfg = MagicMock()
    mock_cfg.androidtv.host = "192.168.1.50"  # real host → launch should be called

    mock_launch = AsyncMock()
    with patch("server.tools.spotify._launch_spotify_on_tv", mock_launch), \
         patch("asyncio.sleep", new_callable=AsyncMock):
        await _ensure_playing_on_tv(sp, mock_cfg)

    mock_launch.assert_called_once_with(mock_cfg.androidtv)


@pytest.mark.asyncio
async def test_ensure_playing_on_tv_skips_launch_when_tv_unconfigured() -> None:
    from server.tools.spotify import _ensure_playing_on_tv

    sp = MagicMock()
    sp.devices.return_value = {"devices": [{"id": "tv-id", "type": "TV", "name": "TV"}]}

    mock_cfg = MagicMock()
    mock_cfg.androidtv.host = "192.168.x.x"  # placeholder → skip launch

    mock_launch = AsyncMock()
    with patch("server.tools.spotify._launch_spotify_on_tv", mock_launch), \
         patch("asyncio.sleep", new_callable=AsyncMock):
        await _ensure_playing_on_tv(sp, mock_cfg)

    mock_launch.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_playing_on_tv_continues_if_launch_fails() -> None:
    from server.tools.spotify import _ensure_playing_on_tv

    sp = MagicMock()
    sp.devices.return_value = {"devices": [{"id": "tv-id", "type": "TV", "name": "TV"}]}

    mock_cfg = MagicMock()
    mock_cfg.androidtv.host = "192.168.1.50"

    # TV launch raises — should be swallowed; playback transfer still happens
    mock_launch = AsyncMock(side_effect=RuntimeError("TV unreachable"))
    with patch("server.tools.spotify._launch_spotify_on_tv", mock_launch), \
         patch("asyncio.sleep", new_callable=AsyncMock):
        device_id = await _ensure_playing_on_tv(sp, mock_cfg)

    assert device_id == "tv-id"
    sp.transfer_playback.assert_called_once_with(device_id="tv-id", force_play=True)


# ---------------------------------------------------------------------------
# SpotifyTool.run() — play action (combined launch flow)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_play_action_calls_ensure_playing_on_tv() -> None:
    from server.tools.spotify import SpotifyTool

    tool = SpotifyTool()
    mock_cfg = MagicMock()
    mock_cfg.spotify.owner.client_id = "owner_id"
    mock_cfg.spotify.owner.client_secret = "owner_secret"

    mock_sp = MagicMock()
    mock_ensure = AsyncMock(return_value="tv-device-id")

    with patch("server.tools.spotify.cfg_module.load", return_value=mock_cfg), \
         patch("server.tools.spotify._get_spotify", return_value=mock_sp), \
         patch("server.tools.spotify._ensure_playing_on_tv", mock_ensure):
        result = await tool.run({"action": "play"}, user="owner")

    mock_ensure.assert_called_once_with(mock_sp, mock_cfg)
    assert "playing" in result.lower() or "tv" in result.lower()


@pytest.mark.asyncio
async def test_play_action_for_emily_routes_to_emily_spotify() -> None:
    from server.tools.spotify import SpotifyTool

    tool = SpotifyTool()
    mock_cfg = MagicMock()
    mock_cfg.spotify.emily.client_id = "emily_id"
    mock_cfg.spotify.emily.client_secret = "emily_secret"

    mock_sp = MagicMock()
    mock_ensure = AsyncMock(return_value="tv-device-id")

    with patch("server.tools.spotify.cfg_module.load", return_value=mock_cfg), \
         patch("server.tools.spotify._get_spotify", return_value=mock_sp) as mock_get, \
         patch("server.tools.spotify._ensure_playing_on_tv", mock_ensure):
        result = await tool.run({"action": "play"}, user="emily")

    mock_get.assert_called_once_with(mock_cfg.spotify.emily)
    assert "emily" in result.lower()


@pytest.mark.asyncio
async def test_play_action_timeout_returns_spotify_error() -> None:
    from server.tools.spotify import SpotifyTool

    tool = SpotifyTool()
    mock_cfg = MagicMock()
    mock_cfg.spotify.owner.client_id = "owner_id"
    mock_cfg.spotify.owner.client_secret = "owner_secret"

    mock_sp = MagicMock()
    mock_ensure = AsyncMock(side_effect=RuntimeError("TV didn't appear in Spotify"))

    with patch("server.tools.spotify.cfg_module.load", return_value=mock_cfg), \
         patch("server.tools.spotify._get_spotify", return_value=mock_sp), \
         patch("server.tools.spotify._ensure_playing_on_tv", mock_ensure):
        result = await tool.run({"action": "play"}, user="owner")

    assert "spotify error" in result.lower() or "tv" in result.lower()


# ---------------------------------------------------------------------------
# _find_user_playlist
# ---------------------------------------------------------------------------


def test_find_user_playlist_returns_matching_uri() -> None:
    from server.tools.spotify import _find_user_playlist

    sp = MagicMock()
    sp.current_user_playlists.return_value = {
        "items": [
            {"name": "Discover Weekly", "uri": "spotify:playlist:discover"},
            {"name": "Rock Classics", "uri": "spotify:playlist:rock"},
        ],
        "next": None,
    }
    uri = _find_user_playlist(sp, "Discover Weekly")
    assert uri == "spotify:playlist:discover"


def test_find_user_playlist_strips_my_prefix() -> None:
    from server.tools.spotify import _find_user_playlist

    sp = MagicMock()
    sp.current_user_playlists.return_value = {
        "items": [{"name": "Discover Weekly", "uri": "spotify:playlist:dw"}],
        "next": None,
    }
    uri = _find_user_playlist(sp, "my Discover Weekly")
    assert uri == "spotify:playlist:dw"


def test_find_user_playlist_case_insensitive() -> None:
    from server.tools.spotify import _find_user_playlist

    sp = MagicMock()
    sp.current_user_playlists.return_value = {
        "items": [{"name": "DISCOVER WEEKLY", "uri": "spotify:playlist:dw"}],
        "next": None,
    }
    uri = _find_user_playlist(sp, "discover weekly")
    assert uri == "spotify:playlist:dw"


def test_find_user_playlist_returns_none_when_no_match() -> None:
    from server.tools.spotify import _find_user_playlist

    sp = MagicMock()
    sp.current_user_playlists.return_value = {
        "items": [{"name": "Rock Classics", "uri": "spotify:playlist:rock"}],
        "next": None,
    }
    uri = _find_user_playlist(sp, "Discover Weekly")
    assert uri is None


def test_find_user_playlist_paginates() -> None:
    from server.tools.spotify import _find_user_playlist

    sp = MagicMock()
    sp.current_user_playlists.side_effect = [
        {
            "items": [{"name": "Rock Classics", "uri": "spotify:playlist:rock"}],
            "next": "page2_url",
        },
        {
            "items": [{"name": "Discover Weekly", "uri": "spotify:playlist:dw"}],
            "next": None,
        },
    ]
    uri = _find_user_playlist(sp, "Discover Weekly")
    assert uri == "spotify:playlist:dw"
    assert sp.current_user_playlists.call_count == 2


# ---------------------------------------------------------------------------
# _search_spotify
# ---------------------------------------------------------------------------


def test_search_spotify_prefers_playlist_for_mood_query() -> None:
    from server.tools.spotify import _search_spotify

    sp = MagicMock()
    sp.search.return_value = {
        "playlists": {"items": [{"uri": "spotify:playlist:jazz", "name": "Jazz Vibes"}]},
        "tracks": {"items": [{"uri": "spotify:track:t1", "name": "Jazz Song", "artists": [{"name": "A"}]}]},
    }
    context_uri, track_uris, description = _search_spotify(sp, "jazz")
    assert context_uri == "spotify:playlist:jazz"
    assert track_uris is None
    assert description == "Jazz Vibes"


def test_search_spotify_prefers_track_for_specific_query() -> None:
    from server.tools.spotify import _search_spotify

    sp = MagicMock()
    sp.search.return_value = {
        "playlists": {"items": [{"uri": "spotify:playlist:p1", "name": "Some Playlist"}]},
        "tracks": {"items": [{
            "uri": "spotify:track:bohemian",
            "name": "Bohemian Rhapsody",
            "artists": [{"name": "Queen"}],
        }]},
    }
    context_uri, track_uris, description = _search_spotify(sp, "Bohemian Rhapsody by Queen")
    assert context_uri is None
    assert track_uris == ["spotify:track:bohemian"]
    assert "Bohemian Rhapsody" in description
    assert "Queen" in description


def test_search_spotify_checks_user_playlists_for_personal_my_prefix() -> None:
    from server.tools.spotify import _search_spotify
    from unittest.mock import patch

    sp = MagicMock()
    with patch("server.tools.spotify._find_user_playlist", return_value="spotify:playlist:dw") as mock_find:
        context_uri, track_uris, description = _search_spotify(sp, "my Discover Weekly")

    mock_find.assert_called_once()
    assert context_uri == "spotify:playlist:dw"
    assert track_uris is None
    sp.search.assert_not_called()


def test_search_spotify_checks_user_playlists_for_discover_weekly_hint() -> None:
    from server.tools.spotify import _search_spotify
    from unittest.mock import patch

    sp = MagicMock()
    with patch("server.tools.spotify._find_user_playlist", return_value="spotify:playlist:dw"):
        context_uri, _, _ = _search_spotify(sp, "Discover Weekly")

    assert context_uri == "spotify:playlist:dw"


def test_search_spotify_falls_back_to_catalog_if_user_playlist_not_found() -> None:
    from server.tools.spotify import _search_spotify
    from unittest.mock import patch

    sp = MagicMock()
    sp.search.return_value = {
        "playlists": {"items": [{"uri": "spotify:playlist:p1", "name": "Weekly Mix"}]},
        "tracks": {"items": []},
    }
    with patch("server.tools.spotify._find_user_playlist", return_value=None):
        context_uri, track_uris, _ = _search_spotify(sp, "my Discover Weekly")

    assert context_uri == "spotify:playlist:p1"
    assert track_uris is None


def test_search_spotify_returns_none_triple_when_no_results() -> None:
    from server.tools.spotify import _search_spotify

    sp = MagicMock()
    sp.search.return_value = {"playlists": {"items": []}, "tracks": {"items": []}}
    result = _search_spotify(sp, "xyzzy obscure query no results")
    assert result == (None, None, None)


def test_search_spotify_falls_back_to_track_when_no_playlist_for_specific_query() -> None:
    from server.tools.spotify import _search_spotify

    sp = MagicMock()
    sp.search.return_value = {
        "playlists": {"items": []},
        "tracks": {"items": [{"uri": "spotify:track:t1", "name": "Song", "artists": [{"name": "Artist"}]}]},
    }
    context_uri, track_uris, description = _search_spotify(sp, "Song by Artist")
    assert context_uri is None
    assert track_uris == ["spotify:track:t1"]


# ---------------------------------------------------------------------------
# _search_and_play
# ---------------------------------------------------------------------------


def test_search_and_play_starts_context_playback() -> None:
    from server.tools.spotify import _search_and_play
    from unittest.mock import patch

    sp = MagicMock()
    with patch(
        "server.tools.spotify._search_spotify",
        return_value=("spotify:playlist:jazz", None, "Jazz Vibes"),
    ):
        result = _search_and_play(sp, "jazz", "device-123")

    sp.start_playback.assert_called_once_with(
        device_id="device-123",
        context_uri="spotify:playlist:jazz",
        uris=None,
    )
    assert "Jazz Vibes" in result


def test_search_and_play_starts_track_playback() -> None:
    from server.tools.spotify import _search_and_play
    from unittest.mock import patch

    sp = MagicMock()
    with patch(
        "server.tools.spotify._search_spotify",
        return_value=(None, ["spotify:track:bohemian"], "Bohemian Rhapsody by Queen"),
    ):
        result = _search_and_play(sp, "Bohemian Rhapsody by Queen", "device-123")

    sp.start_playback.assert_called_once_with(
        device_id="device-123",
        context_uri=None,
        uris=["spotify:track:bohemian"],
    )
    assert "Bohemian Rhapsody" in result


def test_search_and_play_returns_not_found_when_no_results() -> None:
    from server.tools.spotify import _search_and_play
    from unittest.mock import patch

    sp = MagicMock()
    with patch("server.tools.spotify._search_spotify", return_value=(None, None, None)):
        result = _search_and_play(sp, "xyzzy", "device-123")

    sp.start_playback.assert_not_called()
    assert "xyzzy" in result or "couldn't find" in result.lower()


# ---------------------------------------------------------------------------
# SpotifyTool.run() — play with query
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_play_with_query_calls_ensure_tv_ready_and_search_and_play() -> None:
    from server.tools.spotify import SpotifyTool

    tool = SpotifyTool()
    mock_cfg = MagicMock()
    mock_cfg.spotify.owner.client_id = "owner_id"
    mock_cfg.spotify.owner.client_secret = "owner_secret"

    mock_sp = MagicMock()
    mock_ensure_ready = AsyncMock(return_value="tv-device-id")
    mock_search_play = MagicMock(return_value="Playing Jazz Vibes on the TV.")

    with patch("server.tools.spotify.cfg_module.load", return_value=mock_cfg), \
         patch("server.tools.spotify._get_spotify", return_value=mock_sp), \
         patch("server.tools.spotify._ensure_tv_ready", mock_ensure_ready), \
         patch("server.tools.spotify._search_and_play", mock_search_play):
        result = await tool.run({"action": "play", "query": "jazz"}, user="owner")

    mock_ensure_ready.assert_called_once_with(mock_sp, mock_cfg)
    mock_search_play.assert_called_once_with(mock_sp, "jazz", "tv-device-id")
    assert "Jazz Vibes" in result


@pytest.mark.asyncio
async def test_play_with_query_for_emily_routes_to_emily_account() -> None:
    from server.tools.spotify import SpotifyTool

    tool = SpotifyTool()
    mock_cfg = MagicMock()
    mock_cfg.spotify.emily.client_id = "emily_id"
    mock_cfg.spotify.emily.client_secret = "emily_secret"

    mock_sp = MagicMock()

    with patch("server.tools.spotify.cfg_module.load", return_value=mock_cfg), \
         patch("server.tools.spotify._get_spotify", return_value=mock_sp) as mock_get, \
         patch("server.tools.spotify._ensure_tv_ready", AsyncMock(return_value="tv-id")), \
         patch("server.tools.spotify._search_and_play", MagicMock(return_value="Playing Discover Weekly on the TV.")):
        result = await tool.run({"action": "play", "query": "my Discover Weekly"}, user="emily")

    mock_get.assert_called_once_with(mock_cfg.spotify.emily)
    assert "Discover Weekly" in result


@pytest.mark.asyncio
async def test_play_without_query_uses_ensure_playing_on_tv() -> None:
    from server.tools.spotify import SpotifyTool

    tool = SpotifyTool()
    mock_cfg = MagicMock()
    mock_cfg.spotify.owner.client_id = "owner_id"
    mock_cfg.spotify.owner.client_secret = "owner_secret"

    mock_sp = MagicMock()
    mock_ensure = AsyncMock(return_value="tv-device-id")

    with patch("server.tools.spotify.cfg_module.load", return_value=mock_cfg), \
         patch("server.tools.spotify._get_spotify", return_value=mock_sp), \
         patch("server.tools.spotify._ensure_playing_on_tv", mock_ensure):
        result = await tool.run({"action": "play"}, user="owner")

    mock_ensure.assert_called_once_with(mock_sp, mock_cfg)
    assert "playing" in result.lower()


@pytest.mark.asyncio
async def test_play_with_empty_string_query_uses_ensure_playing_on_tv() -> None:
    from server.tools.spotify import SpotifyTool

    tool = SpotifyTool()
    mock_cfg = MagicMock()
    mock_cfg.spotify.owner.client_id = "owner_id"
    mock_cfg.spotify.owner.client_secret = "owner_secret"

    mock_sp = MagicMock()
    mock_ensure = AsyncMock(return_value="tv-device-id")

    with patch("server.tools.spotify.cfg_module.load", return_value=mock_cfg), \
         patch("server.tools.spotify._get_spotify", return_value=mock_sp), \
         patch("server.tools.spotify._ensure_playing_on_tv", mock_ensure):
        result = await tool.run({"action": "play", "query": ""}, user="owner")

    mock_ensure.assert_called_once_with(mock_sp, mock_cfg)
    assert "playing" in result.lower()


# ---------------------------------------------------------------------------
# SpotifyTool.run() — pause, skip, previous, volume controls
# ---------------------------------------------------------------------------


def _configured_mock():
    mock_cfg = MagicMock()
    mock_cfg.spotify.owner.client_id = "owner_id"
    mock_cfg.spotify.owner.client_secret = "owner_secret"
    mock_cfg.spotify.emily.client_id = "emily_id"
    mock_cfg.spotify.emily.client_secret = "emily_secret"
    return mock_cfg


@pytest.mark.asyncio
async def test_pause_action_calls_pause_playback() -> None:
    from server.tools.spotify import SpotifyTool

    tool = SpotifyTool()
    mock_sp = MagicMock()

    with patch("server.tools.spotify.cfg_module.load", return_value=_configured_mock()), \
         patch("server.tools.spotify._get_spotify", return_value=mock_sp):
        result = await tool.run({"action": "pause"}, user="owner")

    mock_sp.pause_playback.assert_called_once()
    assert "paused" in result.lower()


@pytest.mark.asyncio
async def test_skip_action_calls_next_track() -> None:
    from server.tools.spotify import SpotifyTool

    tool = SpotifyTool()
    mock_sp = MagicMock()

    with patch("server.tools.spotify.cfg_module.load", return_value=_configured_mock()), \
         patch("server.tools.spotify._get_spotify", return_value=mock_sp):
        result = await tool.run({"action": "skip"}, user="owner")

    mock_sp.next_track.assert_called_once()
    assert "skip" in result.lower() or "next" in result.lower()


@pytest.mark.asyncio
async def test_previous_action_calls_previous_track() -> None:
    from server.tools.spotify import SpotifyTool

    tool = SpotifyTool()
    mock_sp = MagicMock()

    with patch("server.tools.spotify.cfg_module.load", return_value=_configured_mock()), \
         patch("server.tools.spotify._get_spotify", return_value=mock_sp):
        result = await tool.run({"action": "previous"}, user="owner")

    mock_sp.previous_track.assert_called_once()
    assert "previous" in result.lower() or "back" in result.lower()


@pytest.mark.asyncio
async def test_volume_action_calls_sp_volume() -> None:
    from server.tools.spotify import SpotifyTool

    tool = SpotifyTool()
    mock_sp = MagicMock()

    with patch("server.tools.spotify.cfg_module.load", return_value=_configured_mock()), \
         patch("server.tools.spotify._get_spotify", return_value=mock_sp):
        result = await tool.run({"action": "volume", "level": 60}, user="owner")

    mock_sp.volume.assert_called_once_with(60)
    assert "60" in result


@pytest.mark.asyncio
async def test_volume_action_clamps_level_above_100() -> None:
    from server.tools.spotify import SpotifyTool

    tool = SpotifyTool()
    mock_sp = MagicMock()

    with patch("server.tools.spotify.cfg_module.load", return_value=_configured_mock()), \
         patch("server.tools.spotify._get_spotify", return_value=mock_sp):
        result = await tool.run({"action": "volume", "level": 150}, user="owner")

    mock_sp.volume.assert_called_once_with(100)
    assert "100" in result


@pytest.mark.asyncio
async def test_volume_action_clamps_level_below_0() -> None:
    from server.tools.spotify import SpotifyTool

    tool = SpotifyTool()
    mock_sp = MagicMock()

    with patch("server.tools.spotify.cfg_module.load", return_value=_configured_mock()), \
         patch("server.tools.spotify._get_spotify", return_value=mock_sp):
        result = await tool.run({"action": "volume", "level": -10}, user="owner")

    mock_sp.volume.assert_called_once_with(0)
    assert "0" in result


@pytest.mark.asyncio
async def test_volume_action_without_level_returns_error() -> None:
    from server.tools.spotify import SpotifyTool

    tool = SpotifyTool()
    mock_sp = MagicMock()

    with patch("server.tools.spotify.cfg_module.load", return_value=_configured_mock()), \
         patch("server.tools.spotify._get_spotify", return_value=mock_sp):
        result = await tool.run({"action": "volume"}, user="owner")

    mock_sp.volume.assert_not_called()
    assert "level" in result.lower() or "specify" in result.lower()
