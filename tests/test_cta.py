"""Smoke tests for CtaTool and CtaConfig wiring.

Run with: pytest tests/test_cta.py -v
"""
from __future__ import annotations

import json
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
    from server.tools.cta import CtaTool

    tool = CtaTool()
    mock_cfg = MagicMock()
    mock_cfg.cta.api_key = ""

    with patch("server.tools.cta.cfg_module.load", return_value=mock_cfg):
        result = await tool.run({"query": "next Blue Line?"}, user="owner")

    assert "set up" in result.lower() or "api key" in result.lower()


@pytest.mark.asyncio
async def test_cta_placeholder_key_returns_error() -> None:
    from server.tools.cta import CtaTool

    tool = CtaTool()
    mock_cfg = MagicMock()
    mock_cfg.cta.api_key = "CHANGE_ME"

    with patch("server.tools.cta.cfg_module.load", return_value=mock_cfg):
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
async def test_cta_happy_path_both_directions() -> None:
    from server.tools.cta import CtaTool

    tool = CtaTool()

    mock_cfg = MagicMock()
    mock_cfg.cta.api_key = "real-key"
    mock_cfg.cta.stop_id_ohare = 30238
    mock_cfg.cta.stop_id_forest_park = 30239
    mock_cfg.ollama.host = "http://localhost:11434"
    mock_cfg.ollama.model = "llama3.1:8b-instruct-q4_K_M"

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value=_FAKE_ETA_RESPONSE)

    mock_http_client = AsyncMock()
    mock_http_client.get = AsyncMock(return_value=mock_resp)
    mock_http_ctx = MagicMock()
    mock_http_ctx.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(
        return_value="The next Blue Line toward O'Hare arrives in 3 minutes, toward Forest Park in 6 minutes."
    )

    with (
        patch("server.tools.cta.cfg_module.load", return_value=mock_cfg),
        patch("server.tools.cta.httpx.AsyncClient", return_value=mock_http_ctx),
        patch("server.tools.cta.OllamaClient", return_value=mock_llm),
    ):
        result = await tool.run({"query": "when's the next Blue Line?"}, user="owner")

    assert "Blue Line" in result or "minute" in result.lower()
    mock_llm.complete.assert_awaited_once()
    call_args = mock_llm.complete.call_args
    user_msg = call_args[0][1]
    payload = json.loads(user_msg.split("Arrival data:\n")[1])
    assert len(payload) == 2
    assert payload[0]["destination"] == "O'Hare"
    assert payload[1]["destination"] == "Forest Park"


@pytest.mark.asyncio
async def test_cta_happy_path_ohare_direction() -> None:
    from server.tools.cta import CtaTool

    tool = CtaTool()

    mock_cfg = MagicMock()
    mock_cfg.cta.api_key = "real-key"
    mock_cfg.cta.stop_id_ohare = 30238
    mock_cfg.cta.stop_id_forest_park = 30239
    mock_cfg.ollama.host = "http://localhost:11434"
    mock_cfg.ollama.model = "llama3.1:8b-instruct-q4_K_M"

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

    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(
        return_value="The next Blue Line toward O'Hare arrives in 4 minutes."
    )

    with (
        patch("server.tools.cta.cfg_module.load", return_value=mock_cfg),
        patch("server.tools.cta.httpx.AsyncClient", return_value=mock_http_ctx),
        patch("server.tools.cta.OllamaClient", return_value=mock_llm),
    ):
        result = await tool.run(
            {"query": "next train toward O'Hare", "direction": "ohare"}, user="owner"
        )

    # Verify only the O'Hare stop ID was requested
    get_call = mock_http_client.get.call_args
    assert get_call[1]["params"]["stpid"] == "30238"
    assert "O'Hare" in result or "minute" in result.lower()


@pytest.mark.asyncio
async def test_cta_happy_path_forest_park_direction() -> None:
    from server.tools.cta import CtaTool

    tool = CtaTool()

    mock_cfg = MagicMock()
    mock_cfg.cta.api_key = "real-key"
    mock_cfg.cta.stop_id_ohare = 30238
    mock_cfg.cta.stop_id_forest_park = 30239
    mock_cfg.ollama.host = "http://localhost:11434"
    mock_cfg.ollama.model = "llama3.1:8b-instruct-q4_K_M"

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

    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(
        return_value="The next Blue Line toward Forest Park arrives in 5 minutes."
    )

    with (
        patch("server.tools.cta.cfg_module.load", return_value=mock_cfg),
        patch("server.tools.cta.httpx.AsyncClient", return_value=mock_http_ctx),
        patch("server.tools.cta.OllamaClient", return_value=mock_llm),
    ):
        result = await tool.run(
            {"query": "next train toward Forest Park", "direction": "forest_park"},
            user="owner",
        )

    # Verify only the Forest Park stop ID was requested
    get_call = mock_http_client.get.call_args
    assert get_call[1]["params"]["stpid"] == "30239"
    assert "Forest Park" in result or "minute" in result.lower()

    # Verify direction note was passed to LLM system prompt
    complete_call = mock_llm.complete.call_args
    system_prompt = complete_call[0][0]
    assert "Forest Park" in system_prompt


@pytest.mark.asyncio
async def test_cta_direction_note_in_system_prompt_ohare() -> None:
    """Direction-specific context must appear in the system prompt sent to the LLM."""
    from server.tools.cta import CtaTool

    tool = CtaTool()

    mock_cfg = MagicMock()
    mock_cfg.cta.api_key = "real-key"
    mock_cfg.cta.stop_id_ohare = 30238
    mock_cfg.cta.stop_id_forest_park = 30239
    mock_cfg.ollama.host = "http://localhost:11434"
    mock_cfg.ollama.model = "llama3.1:8b-instruct-q4_K_M"

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value=_FAKE_ETA_RESPONSE)

    mock_http_client = AsyncMock()
    mock_http_client.get = AsyncMock(return_value=mock_resp)
    mock_http_ctx = MagicMock()
    mock_http_ctx.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value="Next O'Hare train in 3 minutes.")

    with (
        patch("server.tools.cta.cfg_module.load", return_value=mock_cfg),
        patch("server.tools.cta.httpx.AsyncClient", return_value=mock_http_ctx),
        patch("server.tools.cta.OllamaClient", return_value=mock_llm),
    ):
        await tool.run({"query": "next O'Hare train", "direction": "ohare"}, user="owner")

    complete_call = mock_llm.complete.call_args
    system_prompt = complete_call[0][0]
    assert "O'Hare" in system_prompt
    assert "Forest Park" not in system_prompt


@pytest.mark.asyncio
async def test_cta_direction_note_in_system_prompt_both() -> None:
    """When direction is 'both', system prompt should mention grouping by direction."""
    from server.tools.cta import CtaTool

    tool = CtaTool()

    mock_cfg = MagicMock()
    mock_cfg.cta.api_key = "real-key"
    mock_cfg.cta.stop_id_ohare = 30238
    mock_cfg.cta.stop_id_forest_park = 30239
    mock_cfg.ollama.host = "http://localhost:11434"
    mock_cfg.ollama.model = "llama3.1:8b-instruct-q4_K_M"

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(return_value=_FAKE_ETA_RESPONSE)

    mock_http_client = AsyncMock()
    mock_http_client.get = AsyncMock(return_value=mock_resp)
    mock_http_ctx = MagicMock()
    mock_http_ctx.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value="O'Hare in 3 min, Forest Park in 6 min.")

    with (
        patch("server.tools.cta.cfg_module.load", return_value=mock_cfg),
        patch("server.tools.cta.httpx.AsyncClient", return_value=mock_http_ctx),
        patch("server.tools.cta.OllamaClient", return_value=mock_llm),
    ):
        await tool.run({"query": "next Blue Line train"}, user="owner")

    complete_call = mock_llm.complete.call_args
    system_prompt = complete_call[0][0]
    assert "direction" in system_prompt.lower() or "group" in system_prompt.lower()


# ---------------------------------------------------------------------------
# _parse_arrivals helper
# ---------------------------------------------------------------------------


def test_parse_arrivals_empty() -> None:
    from server.tools.cta import _parse_arrivals

    assert _parse_arrivals({}) == []
    assert _parse_arrivals({"ctatt": {}}) == []
    assert _parse_arrivals({"ctatt": {"eta": None}}) == []


def test_parse_arrivals_fields() -> None:
    from server.tools.cta import _parse_arrivals

    result = _parse_arrivals(_FAKE_ETA_RESPONSE)
    assert len(result) == 2
    assert result[0]["destination"] == "O'Hare"
    assert result[0]["is_approaching"] is False
    assert result[0]["is_delayed"] is False
    assert result[1]["destination"] == "Forest Park"
