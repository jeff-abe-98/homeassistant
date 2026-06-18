"""Smoke tests for server/tools/google_auth.py."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import shared.config as cfg_module
from pi.tools.google_auth import build_service, get_credentials, is_configured


def _mock_google_cfg(credentials_file: str, token_file: str = "config/google_token.json"):
    mock_cfg = MagicMock()
    mock_cfg.google.credentials_file = credentials_file
    mock_cfg.google.token_file = token_file
    mock_cfg.google.scopes = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/tasks",
    ]
    return mock_cfg


class TestIsConfigured:
    def test_missing_file(self, tmp_path):
        with patch.object(cfg_module, "load", return_value=_mock_google_cfg(str(tmp_path / "no.json"))):
            assert is_configured() is False

    def test_placeholder_client_id(self, tmp_path):
        creds = tmp_path / "creds.json"
        creds.write_text(json.dumps({"installed": {"client_id": "CHANGE_ME", "client_secret": "x"}}))
        with patch.object(cfg_module, "load", return_value=_mock_google_cfg(str(creds))):
            assert is_configured() is False

    def test_real_credentials(self, tmp_path):
        creds = tmp_path / "creds.json"
        creds.write_text(json.dumps({
            "installed": {
                "client_id": "123456.apps.googleusercontent.com",
                "client_secret": "secret",
            }
        }))
        with patch.object(cfg_module, "load", return_value=_mock_google_cfg(str(creds))):
            assert is_configured() is True

    def test_malformed_json(self, tmp_path):
        creds = tmp_path / "creds.json"
        creds.write_text("not json {{{")
        with patch.object(cfg_module, "load", return_value=_mock_google_cfg(str(creds))):
            assert is_configured() is False


class TestGetCredentials:
    def test_returns_none_when_not_configured(self, tmp_path):
        with patch.object(cfg_module, "load", return_value=_mock_google_cfg(str(tmp_path / "no.json"))):
            assert get_credentials() is None

    def test_returns_none_with_placeholder(self, tmp_path):
        creds = tmp_path / "creds.json"
        creds.write_text(json.dumps({"installed": {"client_id": "CHANGE_ME"}}))
        with patch.object(cfg_module, "load", return_value=_mock_google_cfg(str(creds))):
            assert get_credentials() is None


class TestBuildService:
    def test_returns_none_when_not_configured(self, tmp_path):
        with patch.object(cfg_module, "load", return_value=_mock_google_cfg(str(tmp_path / "no.json"))):
            assert build_service("calendar", "v3") is None

    def test_returns_none_with_placeholder(self, tmp_path):
        creds = tmp_path / "creds.json"
        creds.write_text(json.dumps({"installed": {"client_id": "CHANGE_ME"}}))
        with patch.object(cfg_module, "load", return_value=_mock_google_cfg(str(creds))):
            assert build_service("tasks", "v1") is None
