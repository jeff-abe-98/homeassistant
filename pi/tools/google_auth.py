"""Shared Google OAuth2 helper — used by calendar.py and tasks.py."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import shared.config as cfg_module


def is_configured() -> bool:
    """Return True if credentials file exists and contains non-placeholder values."""
    cfg = cfg_module.load()
    creds_path = Path(cfg.google.credentials_file)
    if not creds_path.exists():
        return False
    try:
        data = json.loads(creds_path.read_text())
        installed = data.get("installed", data.get("web", {}))
        client_id = installed.get("client_id", "CHANGE_ME")
        return client_id != "CHANGE_ME" and not client_id.startswith("CHANGE_ME")
    except (json.JSONDecodeError, AttributeError):
        return False


def get_credentials() -> Any | None:
    """Load, refresh, or obtain Google OAuth2 credentials.

    Returns a Credentials object, or None if not configured or google-auth
    packages are not installed.  On first call after credentials are set up,
    opens a browser window to complete the OAuth flow and saves the token.
    """
    if not is_configured():
        return None

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        return None

    cfg = cfg_module.load()
    google = cfg.google
    creds_path = Path(google.credentials_file)
    token_path = Path(google.token_file)
    scopes = google.scopes

    creds: Credentials | None = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), scopes)
            creds = flow.run_local_server(port=8888, open_browser=False)
        token_path.write_text(creds.to_json())

    return creds


def build_service(api_name: str, version: str) -> Any | None:
    """Return an authenticated Google API service client, or None if not configured."""
    creds = get_credentials()
    if creds is None:
        return None

    try:
        from googleapiclient.discovery import build
    except ImportError:
        return None

    return build(api_name, version, credentials=creds)
