"""Root conftest: pre-install stubs for ML/audio packages unavailable in CI."""
import sys
from unittest.mock import MagicMock

# Server-side packages that require compiled binaries or large models:
# numpy is now installed (required by HailoTranscriber for PCM conversion)
for _name in ("ollama", "faster_whisper"):
    sys.modules.setdefault(_name, MagicMock())

# Spotify SDK — not installed in CI test environment:
for _name in ("spotipy", "spotipy.oauth2"):
    sys.modules.setdefault(_name, MagicMock())
