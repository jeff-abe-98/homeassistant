"""Smoke tests for CtaTool and CtaConfig wiring.

Run with: pytest tests/test_cta.py -v
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.config import AppConfig, CtaConfig


# ---------------------------------------------------------------------------
# Config wiring
# ---------------------------------------------------------------------------


def test_cta_config_defaults() -> None:
    cfg = AppConfig()
    assert cfg.cta.api_key == ""
    assert cfg.cta.stop_id_ohare == 30238
    assert cfg.cta.stop_id_forest_park == 30239


def test_cta_config_loaded_from_yaml(tmp_path) -> None:
    settings = tmp_path / "settings.yaml"
    settings.write_text(
        "cta:\n"
        "  api_key: test-cta-key\n"
        "  stop_id_ohare: 11111\n"
        "  stop_id_forest_park: 22222\n"
    )
    import shared.config as cfg_module

    cfg = cfg_module.load(str(settings))
    assert cfg.cta.api_key == "test-cta-key"
    assert cfg.cta.stop_id_ohare == 11111
    assert cfg.cta.stop_id_forest_park == 22222


# ---------------------------------------------------------------------------
# CtaTool.run() — missing / placeholder key
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cta_missing_key_returns_error() -> None:
    from pi.tools.cta import CtaTool

    tool = CtaTool()
    mock_cfg = MagicMock()
    mock_cfg.cta.api_key = ""

    with patch("pi.tools.cta.cfg_module.load", return_value=mock_cfg):
        result = await tool.run({"query": "next Blue Line?"}, user="owner")

    assert "set up" in result.lower() or "api key" in result.lower()


@pytest.mark.asyncio
async def test_cta_placeholder_key_returns_error() -> None:
    from pi.tools.cta import CtaTool

    tool = CtaTool()
    mock_cfg = MagicMock()
    mock_cfg.cta.api_key = "CHANGE_ME"

    with patch("pi.tools.cta.cfg_module.load", return_value=mock_cfg):
        result = await tool.run({"query": "when's the next Blue Line?"}, user="owner")

    assert "set up" in result.lower() or "api key" in result.lower()


# ---------------------------------------------------------------------------
# CtaTool.run() — happy path (mocked HTTP + LLM)
# ---------------------------------------------------------------------------

_FAKE_ETA_RESPONSE = {
    "ctatt": {
        "tmst": "20260508 12:00:00",
        "errCd": "0",
        "errNm": None,
        "eta": [
            {
                "destNm": "O'Hare",
                "stpDe": "Service toward O'Hare",
                "arrT": "20260508 12:03:00",
                "prdt": "20260508 12:00:30",
                "isApp": "0",
                "isDly": "0",
                "isSch": "0",
            },
            {
                "destNm": "Forest Park",
                "stpDe": "Service toward Forest Park",
                "arrT": "20260508 12:06:00",
                "prdt": "20260508 12:00:30",
                "isApp": "0",
                "isDly": "0",
                "isSch": "0",
            },
        ],
    }
}


@pytest.mark.asyncio
async def test_cta_happy_path_both_directions_returns_raw_data() -> None:
    """run() returns raw arrivals data; no internal LLM call."""
    from pi.tools.cta import CtaTool

    tool = CtaTool()
    assert tool.needs_narration is True

    mock_cfg = MagicMock()
    mock_cfg.cta.api_key = "real-key"
    mock_cfg.cta.stop_id_ohare = 30238
    mock_cfg.cta.stop_id_forest_park = 30239

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value=_FAKE_ETA_RESPONSE)

    mock_http_client = AsyncMock()
    mock_http_client.get = AsyncMock(return_value=mock_resp)
    mock_http_ctx = MagicMock()
    mock_http_ctx.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_ctx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("pi.tools.cta.cfg_module.load", return_value=mock_cfg),
        patch("pi.tools.cta.httpx.AsyncClient", return_value=mock_http_ctx),
    ):
        result = await tool.run({"query": "when's the next Blue Line?"}, user="owner")

    # Result is raw arrivals data for both destinations
    assert "O'Hare" in result
    assert "Forest Park" in result
    assert "User question:" in result


@pytest.mark.asyncio
async def test_cta_happy_path_ohare_direction() -> None:
    from pi.tools.cta import CtaTool

    tool = CtaTool()

    mock_cfg = MagicMock()
    mock_cfg.cta.api_key = "real-key"
    mock_cfg.cta.stop_id_ohare = 30238
    mock_cfg.cta.stop_id_forest_park = 30239

    ohare_only_response = {
        "ctatt": {
            "tmst": "20260508 12:00:00",
            "errCd": "0",
            "errNm": None,
            "eta": [
                {
                    "destNm": "O'Hare",
                    "stpDe": "Service toward O'Hare",
                    "arrT": "20260508 12:04:00",
                    "prdt": "20260508 12:00:30",
                    "isApp": "0",
                    "isDly": "0",
                    "isSch": "0",
                }
            ],
        }
    }

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value=ohare_only_response)

    mock_http_client = AsyncMock()
    mock_http_client.get = AsyncMock(return_value=mock_resp)
    mock_http_ctx = MagicMock()
    mock_http_ctx.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_ctx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("pi.tools.cta.cfg_module.load", return_value=mock_cfg),
        patch("pi.tools.cta.httpx.AsyncClient", return_value=mock_http_ctx),
    ):
        result = await tool.run(
            {"query": "next train toward O'Hare", "direction": "ohare"}, user="owner"
        )

    # Verify only the O'Hare stop ID was requested
    get_call = mock_http_client.get.call_args
    assert get_call[1]["params"]["stpid"] == "30238"
    assert "O'Hare" in result


@pytest.mark.asyncio
async def test_cta_happy_path_forest_park_direction() -> None:
    from pi.tools.cta import CtaTool

    tool = CtaTool()

    mock_cfg = MagicMock()
    mock_cfg.cta.api_key = "real-key"
    mock_cfg.cta.stop_id_ohare = 30238
    mock_cfg.cta.stop_id_forest_park = 30239

    forest_park_only_response = {
        "ctatt": {
            "tmst": "20260508 12:00:00",
            "errCd": "0",
            "errNm": None,
            "eta": [
                {
                    "destNm": "Forest Park",
                    "stpDe": "Service toward Forest Park",
                    "arrT": "20260508 12:05:00",
                    "prdt": "20260508 12:00:30",
                    "isApp": "0",
                    "isDly": "0",
                    "isSch": "0",
                }
            ],
        }
    }

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value=forest_park_only_response)

    mock_http_client = AsyncMock()
    mock_http_client.get = AsyncMock(return_value=mock_resp)
    mock_http_ctx = MagicMock()
    mock_http_ctx.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_ctx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("pi.tools.cta.cfg_module.load", return_value=mock_cfg),
        patch("pi.tools.cta.httpx.AsyncClient", return_value=mock_http_ctx),
    ):
        result = await tool.run(
            {"query": "next train toward Forest Park", "direction": "forest_park"},
            user="owner",
        )

    # Verify only the Forest Park stop ID was requested
    get_call = mock_http_client.get.call_args
    assert get_call[1]["params"]["stpid"] == "30239"
    assert "Forest Park" in result


@pytest.mark.asyncio
async def test_cta_direction_in_raw_data_ohare() -> None:
    """Direction label must appear in the raw data block returned by run()."""
    from pi.tools.cta import CtaTool

    tool = CtaTool()

    mock_cfg = MagicMock()
    mock_cfg.cta.api_key = "real-key"
    mock_cfg.cta.stop_id_ohare = 30238
    mock_cfg.cta.stop_id_forest_park = 30239

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value=_FAKE_ETA_RESPONSE)

    mock_http_client = AsyncMock()
    mock_http_client.get = AsyncMock(return_value=mock_resp)
    mock_http_ctx = MagicMock()
    mock_http_ctx.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_ctx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("pi.tools.cta.cfg_module.load", return_value=mock_cfg),
        patch("pi.tools.cta.httpx.AsyncClient", return_value=mock_http_ctx),
    ):
        result = await tool.run({"query": "next O'Hare train", "direction": "ohare"}, user="owner")

    assert "O'Hare" in result
    assert "Direction filter:" in result


@pytest.mark.asyncio
async def test_cta_direction_in_raw_data_both() -> None:
    """When direction is 'both', raw data should include both-directions label."""
    from pi.tools.cta import CtaTool

    tool = CtaTool()

    mock_cfg = MagicMock()
    mock_cfg.cta.api_key = "real-key"
    mock_cfg.cta.stop_id_ohare = 30238
    mock_cfg.cta.stop_id_forest_park = 30239

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value=_FAKE_ETA_RESPONSE)

    mock_http_client = AsyncMock()
    mock_http_client.get = AsyncMock(return_value=mock_resp)
    mock_http_ctx = MagicMock()
    mock_http_ctx.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_ctx.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("pi.tools.cta.cfg_module.load", return_value=mock_cfg),
        patch("pi.tools.cta.httpx.AsyncClient", return_value=mock_http_ctx),
    ):
        result = await tool.run({"query": "next Blue Line train"}, user="owner")

    assert "both directions" in result.lower() or "Direction filter:" in result


# ---------------------------------------------------------------------------
# _parse_arrivals helper
# ---------------------------------------------------------------------------


def test_parse_arrivals_empty() -> None:
    from pi.tools.cta import _parse_arrivals

    assert _parse_arrivals({}) == []
    assert _parse_arrivals({"ctatt": {}}) == []
    assert _parse_arrivals({"ctatt": {"eta": None}}) == []


def test_parse_arrivals_fields() -> None:
    from pi.tools.cta import _parse_arrivals

    result = _parse_arrivals(_FAKE_ETA_RESPONSE)
    assert len(result) == 2
    assert result[0]["destination"] == "O'Hare"
    assert result[0]["is_approaching"] is False
    assert result[0]["is_delayed"] is False
    assert result[1]["destination"] == "Forest Park"
