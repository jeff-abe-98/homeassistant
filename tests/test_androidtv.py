"""Smoke tests for AndroidTvTool and AndroidTvConfig wiring.

Run with: pytest tests/test_androidtv.py -v
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Config wiring
# ---------------------------------------------------------------------------


def test_androidtv_config_defaults() -> None:
    from shared.config import AndroidTvConfig, AppConfig

    cfg = AppConfig()
    assert cfg.androidtv.host == ""
    assert cfg.androidtv.port == 6466
    assert cfg.androidtv.cert_file == "config/androidtv_cert.pem"
    assert cfg.androidtv.key_file == "config/androidtv_key.pem"


def test_androidtv_config_loaded_from_yaml(tmp_path) -> None:
    settings = tmp_path / "settings.yaml"
    settings.write_text(
        "androidtv:\n"
        "  host: 192.168.1.50\n"
        "  port: 6466\n"
        "  cert_file: config/my_cert.pem\n"
        "  key_file: config/my_key.pem\n"
    )
    import shared.config as cfg_module

    cfg = cfg_module.load(str(settings))
    assert cfg.androidtv.host == "192.168.1.50"
    assert cfg.androidtv.port == 6466
    assert cfg.androidtv.cert_file == "config/my_cert.pem"
    assert cfg.androidtv.key_file == "config/my_key.pem"


# ---------------------------------------------------------------------------
# AndroidTvTool.run() — unconfigured host
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unconfigured_host_returns_error() -> None:
    from server.tools.androidtv import AndroidTvTool

    tool = AndroidTvTool()
    mock_cfg = MagicMock()
    mock_cfg.androidtv.host = ""

    with patch("server.tools.androidtv.cfg_module.load", return_value=mock_cfg):
        result = await tool.run({"action": "power_on"}, user="owner")

    assert "set up" in result.lower() or "ip" in result.lower()


@pytest.mark.asyncio
async def test_placeholder_host_returns_error() -> None:
    from server.tools.androidtv import AndroidTvTool

    tool = AndroidTvTool()
    mock_cfg = MagicMock()
    mock_cfg.androidtv.host = "192.168.x.x"

    with patch("server.tools.androidtv.cfg_module.load", return_value=mock_cfg):
        result = await tool.run({"action": "power_on"}, user="owner")

    assert "set up" in result.lower() or "ip" in result.lower()


# ---------------------------------------------------------------------------
# AndroidTvTool.run() — connection failures
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cannot_connect_returns_friendly_message() -> None:
    from server.tools.androidtv import AndroidTvTool

    tool = AndroidTvTool()
    mock_cfg = MagicMock()
    mock_cfg.androidtv.host = "192.168.1.50"
    mock_cfg.androidtv.port = 6466
    mock_cfg.androidtv.cert_file = "config/androidtv_cert.pem"
    mock_cfg.androidtv.key_file = "config/androidtv_key.pem"

    class FakeCannotConnect(Exception):
        pass

    FakeCannotConnect.__name__ = "CannotConnect"

    with (
        patch("server.tools.androidtv.cfg_module.load", return_value=mock_cfg),
        patch("server.tools.androidtv._connect", side_effect=FakeCannotConnect("refused")),
    ):
        result = await tool.run({"action": "power_on"}, user="owner")

    assert "reach" in result.lower() or "connect" in result.lower()


@pytest.mark.asyncio
async def test_invalid_auth_returns_pairing_message() -> None:
    from server.tools.androidtv import AndroidTvTool

    tool = AndroidTvTool()
    mock_cfg = MagicMock()
    mock_cfg.androidtv.host = "192.168.1.50"
    mock_cfg.androidtv.port = 6466
    mock_cfg.androidtv.cert_file = "config/androidtv_cert.pem"
    mock_cfg.androidtv.key_file = "config/androidtv_key.pem"

    class FakeInvalidAuth(Exception):
        pass

    FakeInvalidAuth.__name__ = "InvalidAuth"

    with (
        patch("server.tools.androidtv.cfg_module.load", return_value=mock_cfg),
        patch("server.tools.androidtv._connect", side_effect=FakeInvalidAuth("rejected")),
    ):
        result = await tool.run({"action": "power_on"}, user="owner")

    assert "pair" in result.lower() or "rejected" in result.lower()


# ---------------------------------------------------------------------------
# AndroidTvTool.run() — happy path (mocked androidtvremote2)
# ---------------------------------------------------------------------------


def _make_mock_cfg(host: str = "192.168.1.50") -> MagicMock:
    mock_cfg = MagicMock()
    mock_cfg.androidtv.host = host
    mock_cfg.androidtv.port = 6466
    mock_cfg.androidtv.cert_file = "config/androidtv_cert.pem"
    mock_cfg.androidtv.key_file = "config/androidtv_key.pem"
    return mock_cfg


def _make_mock_atv() -> MagicMock:
    atv = MagicMock()
    atv.send_key_command = MagicMock()
    atv.disconnect = MagicMock()
    return atv


@pytest.mark.asyncio
async def test_power_on_sends_wakeup_keycode() -> None:
    from server.tools.androidtv import AndroidTvTool, _KEYCODE_POWER_ON

    tool = AndroidTvTool()
    mock_atv = _make_mock_atv()

    with (
        patch("server.tools.androidtv.cfg_module.load", return_value=_make_mock_cfg()),
        patch("server.tools.androidtv._connect", new_callable=AsyncMock, return_value=mock_atv),
    ):
        result = await tool.run({"action": "power_on"}, user="owner")

    mock_atv.send_key_command.assert_called_once_with(_KEYCODE_POWER_ON)
    mock_atv.disconnect.assert_called_once()
    assert "on" in result.lower()


@pytest.mark.asyncio
async def test_power_off_sends_sleep_keycode() -> None:
    from server.tools.androidtv import AndroidTvTool, _KEYCODE_POWER_OFF

    tool = AndroidTvTool()
    mock_atv = _make_mock_atv()

    with (
        patch("server.tools.androidtv.cfg_module.load", return_value=_make_mock_cfg()),
        patch("server.tools.androidtv._connect", new_callable=AsyncMock, return_value=mock_atv),
    ):
        result = await tool.run({"action": "power_off"}, user="owner")

    mock_atv.send_key_command.assert_called_once_with(_KEYCODE_POWER_OFF)
    mock_atv.disconnect.assert_called_once()
    assert "off" in result.lower()


@pytest.mark.asyncio
async def test_disconnect_called_even_on_send_error() -> None:
    """disconnect() must run in the finally block even if send_key_command raises."""
    from server.tools.androidtv import AndroidTvTool

    tool = AndroidTvTool()
    mock_atv = _make_mock_atv()
    mock_atv.send_key_command.side_effect = RuntimeError("send failed")

    with (
        patch("server.tools.androidtv.cfg_module.load", return_value=_make_mock_cfg()),
        patch("server.tools.androidtv._connect", new_callable=AsyncMock, return_value=mock_atv),
    ):
        with pytest.raises(RuntimeError, match="send failed"):
            await tool.run({"action": "power_on"}, user="owner")

    mock_atv.disconnect.assert_called_once()


# ---------------------------------------------------------------------------
# _resolve_package — friendly name + passthrough
# ---------------------------------------------------------------------------


def test_resolve_package_friendly_spotify() -> None:
    from server.tools.androidtv import _resolve_package

    assert _resolve_package("spotify") == "com.spotify.tv.android"


def test_resolve_package_friendly_netflix() -> None:
    from server.tools.androidtv import _resolve_package

    assert _resolve_package("Netflix") == "com.netflix.ninja"


def test_resolve_package_friendly_youtube() -> None:
    from server.tools.androidtv import _resolve_package

    assert _resolve_package("youtube") == "com.google.android.youtube.tv"


def test_resolve_package_passthrough_raw_package() -> None:
    from server.tools.androidtv import _resolve_package

    pkg = "com.example.myapp"
    assert _resolve_package(pkg) == pkg


def test_resolve_package_unknown_name_raises() -> None:
    from server.tools.androidtv import _resolve_package

    with pytest.raises(ValueError, match="Unknown app"):
        _resolve_package("totallyfakeapp")


# ---------------------------------------------------------------------------
# _launch_intent — intent URI format
# ---------------------------------------------------------------------------


def test_launch_intent_contains_package() -> None:
    from server.tools.androidtv import _launch_intent

    intent = _launch_intent("com.netflix.ninja")
    assert "com.netflix.ninja" in intent
    assert "LEANBACK_LAUNCHER" in intent
    assert "launchFlags" in intent


# ---------------------------------------------------------------------------
# AndroidTvTool.run() — launch_app action
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_launch_app_no_app_param_returns_prompt() -> None:
    from server.tools.androidtv import AndroidTvTool

    tool = AndroidTvTool()

    with patch("server.tools.androidtv.cfg_module.load", return_value=_make_mock_cfg()):
        result = await tool.run({"action": "launch_app"}, user="owner")

    assert "app" in result.lower() or "open" in result.lower()


@pytest.mark.asyncio
async def test_launch_app_unknown_name_returns_error() -> None:
    from server.tools.androidtv import AndroidTvTool

    tool = AndroidTvTool()

    with patch("server.tools.androidtv.cfg_module.load", return_value=_make_mock_cfg()):
        result = await tool.run({"action": "launch_app", "app": "totallyfakeapp"}, user="owner")

    assert "unknown app" in result.lower() or "known apps" in result.lower()


@pytest.mark.asyncio
async def test_launch_app_netflix_calls_send_launch_app() -> None:
    from server.tools.androidtv import AndroidTvTool

    tool = AndroidTvTool()
    mock_atv = _make_mock_atv()
    mock_atv.send_launch_app = MagicMock()

    with (
        patch("server.tools.androidtv.cfg_module.load", return_value=_make_mock_cfg()),
        patch("server.tools.androidtv._connect", new_callable=AsyncMock, return_value=mock_atv),
    ):
        result = await tool.run({"action": "launch_app", "app": "netflix"}, user="owner")

    mock_atv.send_launch_app.assert_called_once()
    intent_arg = mock_atv.send_launch_app.call_args[0][0]
    assert "com.netflix.ninja" in intent_arg
    assert "netflix" in result.lower() or "opening" in result.lower()
    mock_atv.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_launch_app_raw_package_calls_send_launch_app() -> None:
    from server.tools.androidtv import AndroidTvTool

    tool = AndroidTvTool()
    mock_atv = _make_mock_atv()
    mock_atv.send_launch_app = MagicMock()

    with (
        patch("server.tools.androidtv.cfg_module.load", return_value=_make_mock_cfg()),
        patch("server.tools.androidtv._connect", new_callable=AsyncMock, return_value=mock_atv),
    ):
        result = await tool.run(
            {"action": "launch_app", "app": "com.spotify.tv.android"}, user="owner"
        )

    mock_atv.send_launch_app.assert_called_once()
    intent_arg = mock_atv.send_launch_app.call_args[0][0]
    assert "com.spotify.tv.android" in intent_arg
    mock_atv.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_launch_app_disconnect_called_on_send_error() -> None:
    from server.tools.androidtv import AndroidTvTool

    tool = AndroidTvTool()
    mock_atv = _make_mock_atv()
    mock_atv.send_launch_app = MagicMock(side_effect=RuntimeError("launch failed"))

    with (
        patch("server.tools.androidtv.cfg_module.load", return_value=_make_mock_cfg()),
        patch("server.tools.androidtv._connect", new_callable=AsyncMock, return_value=mock_atv),
    ):
        with pytest.raises(RuntimeError, match="launch failed"):
            await tool.run({"action": "launch_app", "app": "netflix"}, user="owner")

    mock_atv.disconnect.assert_called_once()
