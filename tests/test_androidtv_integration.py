"""Integration test for AndroidTvTool — 'Put on Netflix' flow.

Skips automatically when androidtv.host is still a placeholder.
When a real TV host is set, this verifies the complete Netflix launch flow:
  - config loads correctly and host is recognised as configured
  - "netflix" resolves to com.netflix.ninja package
  - a valid LEANBACK_LAUNCHER intent URI is built
  - send_launch_app() is called with that intent
  - the tool returns a confirmation string mentioning Netflix

The TCP/TLS connection to the TV (_connect) is mocked — the test does not
require the physical device to be powered on or paired.

Run with: pytest tests/test_androidtv_integration.py -v -s
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import shared.config as cfg_module


def _tv_host() -> str:
    """Return configured TV host, or empty string if still a placeholder."""
    cfg = cfg_module.load()
    host = cfg.androidtv.host
    if not host or host in {"192.168.x.x", "CHANGE_ME"}:
        return ""
    return host


_REQUIRES_TV_HOST = pytest.mark.skipif(
    not _tv_host(),
    reason=(
        "No real Android TV host configured — set androidtv.host in config/settings.yaml "
        "to a real IP address"
    ),
)


def _make_mock_atv() -> MagicMock:
    atv = MagicMock()
    atv.send_launch_app = MagicMock()
    atv.send_key_command = MagicMock()
    atv.disconnect = MagicMock()
    return atv


@_REQUIRES_TV_HOST
@pytest.mark.asyncio
async def test_put_on_netflix_sends_correct_package() -> None:
    """'Put on Netflix' → send_launch_app called with com.netflix.ninja LEANBACK_LAUNCHER intent.

    Verifies the complete flow with real config:
    - TV host is recognised as configured (not a placeholder)
    - 'netflix' friendly name resolves to com.netflix.ninja
    - LEANBACK_LAUNCHER intent URI is built and passed to send_launch_app
    - tool returns a confirmation string mentioning Netflix or 'opening'
    """
    from server.tools.androidtv import AndroidTvTool

    tool = AndroidTvTool()
    mock_atv = _make_mock_atv()

    with patch("server.tools.androidtv._connect", new_callable=AsyncMock, return_value=mock_atv):
        result = await tool.run({"action": "launch_app", "app": "netflix"}, user="owner")

    mock_atv.send_launch_app.assert_called_once()
    intent_arg = mock_atv.send_launch_app.call_args[0][0]
    assert "com.netflix.ninja" in intent_arg, (
        f"Intent must include Netflix package (com.netflix.ninja); got: {intent_arg!r}"
    )
    assert "LEANBACK_LAUNCHER" in intent_arg, (
        f"Intent must use LEANBACK_LAUNCHER category; got: {intent_arg!r}"
    )
    mock_atv.disconnect.assert_called_once()
    assert "netflix" in result.lower() or "opening" in result.lower(), (
        f"Response should confirm Netflix launch; got: {result!r}"
    )


@_REQUIRES_TV_HOST
@pytest.mark.asyncio
async def test_put_on_netflix_case_insensitive() -> None:
    """App name matching is case-insensitive — 'Netflix' (title case) works like 'netflix'."""
    from server.tools.androidtv import AndroidTvTool

    tool = AndroidTvTool()
    mock_atv = _make_mock_atv()

    with patch("server.tools.androidtv._connect", new_callable=AsyncMock, return_value=mock_atv):
        result = await tool.run({"action": "launch_app", "app": "Netflix"}, user="owner")

    mock_atv.send_launch_app.assert_called_once()
    intent_arg = mock_atv.send_launch_app.call_args[0][0]
    assert "com.netflix.ninja" in intent_arg
    mock_atv.disconnect.assert_called_once()
    assert "netflix" in result.lower() or "opening" in result.lower()


@_REQUIRES_TV_HOST
@pytest.mark.asyncio
async def test_put_on_netflix_disconnect_called_even_on_error() -> None:
    """disconnect() must be called even if send_launch_app raises."""
    from server.tools.androidtv import AndroidTvTool

    tool = AndroidTvTool()
    mock_atv = _make_mock_atv()
    mock_atv.send_launch_app.side_effect = RuntimeError("TV rejected the launch")

    with patch("server.tools.androidtv._connect", new_callable=AsyncMock, return_value=mock_atv):
        with pytest.raises(RuntimeError, match="TV rejected the launch"):
            await tool.run({"action": "launch_app", "app": "netflix"}, user="owner")

    mock_atv.disconnect.assert_called_once()
