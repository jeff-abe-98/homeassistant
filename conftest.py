"""Root conftest: pre-install stubs for ML/audio packages unavailable in CI."""
import sys
from unittest.mock import MagicMock

# Server-side packages that require compiled binaries or large models:
for _name in ("ollama", "faster_whisper", "numpy"):
    sys.modules.setdefault(_name, MagicMock())
