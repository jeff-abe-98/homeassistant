"""Root conftest: pre-install stubs for ML/audio packages unavailable in CI."""
import sys
import types
from unittest.mock import MagicMock

# Server-side packages that require compiled binaries or large models:
# numpy is now installed (required by HailoTranscriber for PCM conversion)
for _name in ("ollama", "faster_whisper"):
    sys.modules.setdefault(_name, MagicMock())

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
_oww_model_stub = types.ModuleType("openwakeword.model")
_oww_model_stub.Model = MagicMock
sys.modules.setdefault("openwakeword", _oww_stub)
sys.modules.setdefault("openwakeword.model", _oww_model_stub)

# piper — used by pi.tts.piper (deferred import inside PiperTTS.__init__)
_piper_stub = types.ModuleType("piper")
_piper_stub.PiperVoice = MagicMock
sys.modules.setdefault("piper", _piper_stub)
