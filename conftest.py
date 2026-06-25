"""Root conftest: pre-install stubs for ML/audio packages unavailable in CI."""
import sys
import types
from unittest.mock import MagicMock

# Tests for the old server/ architecture (now archived to archive/server/).
# These reference server.main, server.tool_creator.*, server.logging_config, etc.
# Excluded from collection since that code no longer lives in the active tree.
collect_ignore = [
    "tests/test_e2e.py",
    "tests/test_logging_config.py",
    "tests/test_error_handling.py",
    "tests/test_main_tool_creator.py",
    "tests/test_tool_creator_e2e.py",
    "tests/test_tool_creator_generator.py",
    "tests/test_tool_creator_installer.py",
    "tests/test_tool_creator_sandbox.py",
    "tests/test_tool_creator_validator.py",
]

# Server-side packages that require compiled binaries or large models:
for _name in ("ollama", "faster_whisper"):
    sys.modules.setdefault(_name, MagicMock())

# numpy / scipy — not available in the uv-tools pytest Python; stub so that
# modules importing them at the top level can be collected.  Real calls occur
# only in mocked code paths during CI tests.
import types as _types  # noqa: E402 — already imported above, re-binding fine

_numpy_stub = _types.ModuleType("numpy")
_numpy_stub.__version__ = "1.26.0"
_numpy_stub.frombuffer = MagicMock(return_value=MagicMock())
_numpy_stub.int16 = MagicMock()
_numpy_stub.float32 = MagicMock()
_numpy_stub.ndarray = MagicMock
sys.modules.setdefault("numpy", _numpy_stub)

_scipy_stub = _types.ModuleType("scipy")
_scipy_signal_stub = _types.ModuleType("scipy.signal")
_scipy_signal_stub.resample_poly = MagicMock(return_value=MagicMock())
sys.modules.setdefault("scipy", _scipy_stub)
sys.modules.setdefault("scipy.signal", _scipy_signal_stub)

# Spotify SDK — not installed in CI test environment:
for _name in ("spotipy", "spotipy.oauth2"):
    sys.modules.setdefault(_name, MagicMock())

# Pi hardware / audio packages — not available in CI:

# pyaudio — used by pi.audio.capture and pi.wake_word.detector
_pyaudio_stub = types.ModuleType("pyaudio")
_pyaudio_stub.paInt16 = 8
_pyaudio_stub.PyAudio = MagicMock
_pyaudio_stub.Stream = MagicMock
sys.modules.setdefault("pyaudio", _pyaudio_stub)

# webrtcvad — used by pi.audio.capture
_vad_stub = types.ModuleType("webrtcvad")
_vad_stub.Vad = MagicMock
sys.modules.setdefault("webrtcvad", _vad_stub)

# sounddevice — used by pi.audio.playback
_sd_stub = types.ModuleType("sounddevice")
_sd_stub.play = MagicMock()
_sd_stub.wait = MagicMock()
sys.modules.setdefault("sounddevice", _sd_stub)

# resemblyzer — used by pi.speaker_id.embeddings
_resemblyzer_stub = types.ModuleType("resemblyzer")
_resemblyzer_stub.VoiceEncoder = MagicMock
_resemblyzer_stub.preprocess_wav = MagicMock(return_value=MagicMock())
sys.modules.setdefault("resemblyzer", _resemblyzer_stub)

# openwakeword — used by pi.wake_word.detector (deferred import, but stub it anyway)
_oww_stub = types.ModuleType("openwakeword")
_oww_stub.__file__ = "/stub/openwakeword/__init__.py"
_oww_model_stub = types.ModuleType("openwakeword.model")
_oww_model_stub.Model = MagicMock
sys.modules.setdefault("openwakeword", _oww_stub)
sys.modules.setdefault("openwakeword.model", _oww_model_stub)

# piper — used by pi.tts.piper (deferred import inside PiperTTS.__init__)
_piper_stub = types.ModuleType("piper")
_piper_stub.PiperVoice = MagicMock
sys.modules.setdefault("piper", _piper_stub)

# hailo_platform — Hailo NPU SDK; only available on Pi hardware
_hailo_stub = types.ModuleType("hailo_platform")
_hailo_stub.VDevice = MagicMock
sys.modules.setdefault("hailo_platform", _hailo_stub)
