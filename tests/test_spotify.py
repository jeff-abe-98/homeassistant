"""Smoke tests for SpotifyTool and SpotifyConfig wiring.

Run with: pytest tests/test_spotify.py -v
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

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
