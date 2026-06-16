"""Smoke tests for HailoTranscriber.

All tests mock hailo_platform so they run without Hailo hardware.
Run with: pytest tests/test_hailo_stt.py -v
"""
from __future__ import annotations

import asyncio
import struct
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from shared.config import HailoConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pcm(n_samples: int = 1600, value: int = 1000) -> bytes:
    """Return n_samples int16 samples all set to `value`."""
    return struct.pack(f"<{n_samples}h", *([value] * n_samples))


def _make_transcriber(model_path: str = "/models/whisper.hef"):
    """Return a HailoTranscriber with hailo_platform fully mocked."""
    from pi.stt.hailo_transcriber import HailoTranscriber

    mock_vdevice = MagicMock()
    mock_stt_instance = MagicMock()

    with (
        patch("pi.stt.hailo_transcriber._HAILO_AVAILABLE", True),
        patch("pi.stt.hailo_transcriber._VDevice", return_value=mock_vdevice),
        patch("pi.stt.hailo_transcriber._HailoSTT", return_value=mock_stt_instance),
    ):
        cfg = HailoConfig(stt_model_path=model_path)
        tr = HailoTranscriber(cfg)
        # Pre-wire lazy-init so tests can configure mock_stt_instance directly
        tr._vdevice = mock_vdevice
        tr._stt = mock_stt_instance

    return tr, mock_stt_instance


# ---------------------------------------------------------------------------
# Import / availability guard
# ---------------------------------------------------------------------------


def test_module_imports_without_hardware() -> None:
    """HailoTranscriber can be imported even when hailo_platform is absent."""
    with patch("pi.stt.hailo_transcriber._HAILO_AVAILABLE", False):
        from pi.stt.hailo_transcriber import HailoTranscriber  # noqa: F401


def test_transcribe_empty_bytes_returns_empty_string_no_hardware() -> None:
    """Empty pcm_bytes returns '' immediately even without Hailo hardware."""
    with patch("pi.stt.hailo_transcriber._HAILO_AVAILABLE", False):
        from pi.stt.hailo_transcriber import HailoTranscriber

        cfg = HailoConfig()
        tr = HailoTranscriber(cfg)
        result = asyncio.run(tr.transcribe(b""))
        assert result == ""


def test_transcribe_returns_empty_when_hailo_unavailable() -> None:
    """Non-empty bytes + unavailable hardware → returns '' (never crashes).

    _ensure_loaded raises RuntimeError when _HAILO_AVAILABLE=False; the
    except block in transcribe() catches it and returns ''.
    """
    from pi.stt.hailo_transcriber import HailoTranscriber

    with patch("pi.stt.hailo_transcriber._HAILO_AVAILABLE", False):
        cfg = HailoConfig()
        tr = HailoTranscriber(cfg)
        result = asyncio.run(tr.transcribe(_make_pcm()))
        assert result == ""


# ---------------------------------------------------------------------------
# Normal transcription
# ---------------------------------------------------------------------------


def test_transcribe_returns_model_output() -> None:
    """transcribe() returns the string produced by Speech2Text.transcribe()."""
    tr, mock_stt = _make_transcriber()
    mock_stt.transcribe.return_value = "Turn on the lights."

    result = asyncio.run(tr.transcribe(_make_pcm(), sample_rate=16000))

    assert result == "Turn on the lights."
    mock_stt.transcribe.assert_called_once()


def test_transcribe_strips_whitespace() -> None:
    """Leading/trailing whitespace in the model output is stripped."""
    tr, mock_stt = _make_transcriber()
    mock_stt.transcribe.return_value = "  What's the weather?  "

    result = asyncio.run(tr.transcribe(_make_pcm()))

    assert result == "What's the weather?"


def test_transcribe_passes_sample_rate() -> None:
    """The sample_rate argument is forwarded to Speech2Text.transcribe()."""
    tr, mock_stt = _make_transcriber()
    mock_stt.transcribe.return_value = "hello"

    asyncio.run(tr.transcribe(_make_pcm(), sample_rate=16000))

    call_kwargs = mock_stt.transcribe.call_args[1]
    assert call_kwargs.get("sample_rate") == 16000


def test_transcribe_empty_bytes_returns_early() -> None:
    """Empty bytes skips the NPU call entirely."""
    tr, mock_stt = _make_transcriber()

    result = asyncio.run(tr.transcribe(b""))

    assert result == ""
    mock_stt.transcribe.assert_not_called()


# ---------------------------------------------------------------------------
# PCM → float32 conversion
# ---------------------------------------------------------------------------


def test_pcm_to_float32_normalises_range() -> None:
    """_pcm_to_float32: int16 max/min maps to ±1.0 (approximately)."""
    import numpy as np
    from pi.stt.hailo_transcriber import _pcm_to_float32

    # int16 max = 32767 → just under 1.0; int16 min = -32768 → -1.0
    max_sample = struct.pack("<h", 32767)
    min_sample = struct.pack("<h", -32768)

    out_max = _pcm_to_float32(max_sample)
    out_min = _pcm_to_float32(min_sample)

    assert out_max.dtype == np.float32
    assert abs(float(out_max[0]) - 1.0) < 0.001
    assert abs(float(out_min[0]) - (-1.0)) < 0.001


def test_pcm_to_float32_output_shape() -> None:
    """_pcm_to_float32 returns array with same sample count as input."""
    from pi.stt.hailo_transcriber import _pcm_to_float32

    n = 200
    audio = _pcm_to_float32(_make_pcm(n))
    assert len(audio) == n


def test_transcribe_passes_float32_to_stt() -> None:
    """The argument passed to Speech2Text.transcribe is a float32 numpy array."""
    import numpy as np
    from pi.stt.hailo_transcriber import _pcm_to_float32

    tr, mock_stt = _make_transcriber()
    mock_stt.transcribe.return_value = "ok"

    asyncio.run(tr.transcribe(_make_pcm(1600)))

    positional = mock_stt.transcribe.call_args[0]
    assert len(positional) == 1
    audio_arg = positional[0]
    assert isinstance(audio_arg, np.ndarray)
    assert audio_arg.dtype == np.float32


# ---------------------------------------------------------------------------
# Error / resilience
# ---------------------------------------------------------------------------


def test_transcribe_returns_empty_on_runtime_error() -> None:
    """NPU errors return '' instead of propagating."""
    tr, mock_stt = _make_transcriber()
    mock_stt.transcribe.side_effect = RuntimeError("NPU crash")

    result = asyncio.run(tr.transcribe(_make_pcm()))

    assert result == ""


def test_transcribe_returns_empty_when_model_returns_none() -> None:
    """If model returns non-string, transcriber returns ''."""
    tr, mock_stt = _make_transcriber()
    mock_stt.transcribe.return_value = None

    result = asyncio.run(tr.transcribe(_make_pcm()))

    assert result == ""


# ---------------------------------------------------------------------------
# Lazy loading
# ---------------------------------------------------------------------------


def test_ensure_loaded_called_on_first_transcribe() -> None:
    """Model is loaded on the first transcription call."""
    mock_vdevice = MagicMock()
    mock_stt_instance = MagicMock()
    mock_stt_instance.transcribe.return_value = "hi"

    with (
        patch("pi.stt.hailo_transcriber._HAILO_AVAILABLE", True),
        patch("pi.stt.hailo_transcriber._VDevice", return_value=mock_vdevice) as mock_vdev_cls,
        patch("pi.stt.hailo_transcriber._HailoSTT", return_value=mock_stt_instance) as mock_stt_cls,
    ):
        from pi.stt.hailo_transcriber import HailoTranscriber

        cfg = HailoConfig(stt_model_path="/models/whisper.hef")
        tr = HailoTranscriber(cfg)

        # Before first call: not loaded
        assert tr._stt is None

        asyncio.run(tr.transcribe(_make_pcm()))

        # After first call: loaded
        mock_vdev_cls.assert_called_once()
        mock_stt_cls.assert_called_once_with(
            vdevice=mock_vdevice,
            model="/models/whisper.hef",
        )


def test_model_loaded_only_once() -> None:
    """_ensure_loaded does not reload model on subsequent calls."""
    tr, mock_stt = _make_transcriber()
    mock_stt.transcribe.return_value = "hello"

    asyncio.run(tr.transcribe(_make_pcm()))
    asyncio.run(tr.transcribe(_make_pcm()))

    # VDevice and STT constructors must not be called again
    # (they're already set on tr by _make_transcriber)
    assert tr._stt is mock_stt


# ---------------------------------------------------------------------------
# Resource cleanup
# ---------------------------------------------------------------------------


def test_close_releases_stt_and_vdevice() -> None:
    """close() calls .release() on both Speech2Text and VDevice."""
    tr, mock_stt = _make_transcriber()
    mock_vdevice = tr._vdevice

    tr.close()

    mock_stt.release.assert_called_once()
    mock_vdevice.release.assert_called_once()
    assert tr._stt is None
    assert tr._vdevice is None


def test_close_is_safe_when_never_loaded() -> None:
    """close() on a never-used transcriber does not raise."""
    with patch("pi.stt.hailo_transcriber._HAILO_AVAILABLE", True):
        from pi.stt.hailo_transcriber import HailoTranscriber

        cfg = HailoConfig()
        tr = HailoTranscriber(cfg)
        tr.close()  # should not raise


def test_close_is_safe_on_release_error() -> None:
    """close() swallows exceptions from .release() calls."""
    tr, mock_stt = _make_transcriber()
    mock_stt.release.side_effect = RuntimeError("already released")
    tr._vdevice.release.side_effect = RuntimeError("already released")

    tr.close()  # must not raise

    assert tr._stt is None
    assert tr._vdevice is None
