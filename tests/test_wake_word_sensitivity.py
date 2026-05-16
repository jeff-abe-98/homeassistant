"""Tests for wake-word false-positive-reduction knobs.

WakeWordDetector is a Pi-only component (requires pyaudio + openwakeword),
so we mock both libraries and drive _listen() directly.
"""
from __future__ import annotations

import sys
import time
import types
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub out Pi-only libraries before importing the detector
# ---------------------------------------------------------------------------

_pyaudio_stub = types.ModuleType("pyaudio")
_pyaudio_stub.paInt16 = 8
_pyaudio_stub.PyAudio = MagicMock
sys.modules.setdefault("pyaudio", _pyaudio_stub)

_oww_model_stub = types.ModuleType("openwakeword.model")
_oww_model_stub.Model = MagicMock
sys.modules.setdefault("openwakeword", types.ModuleType("openwakeword"))
sys.modules.setdefault("openwakeword.model", _oww_model_stub)

import numpy as np  # noqa: E402  (after stub registration)

from pi.wake_word.detector import WakeWordDetector  # noqa: E402
from shared.config import WakeWordConfig, load  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_detector(
    threshold: float = 0.5,
    min_activation_count: int = 3,
    cooldown_seconds: float = 2.0,
    callback=None,
) -> tuple[WakeWordDetector, MagicMock]:
    """Return (detector, mock_model). Bypasses PyAudio completely."""
    cfg = WakeWordConfig(
        model="test_model",
        threshold=threshold,
        min_activation_count=min_activation_count,
        cooldown_seconds=cooldown_seconds,
    )
    if callback is None:
        callback = MagicMock()
    mock_model = MagicMock()
    with patch("openwakeword.model.Model", return_value=mock_model):
        with patch("pyaudio.PyAudio"):
            det = WakeWordDetector(cfg, callback)
    det._model = mock_model
    return det, mock_model


def _feed_scores(detector: WakeWordDetector, score_sequence: list[float]) -> None:
    """Drive _listen() by replacing stream.read with fake frames."""
    frame = np.zeros(1280, dtype=np.int16).tobytes()
    call_index = 0

    def fake_read(n, exception_on_overflow=False):
        return frame

    scores_iter = iter(score_sequence)

    def fake_predict(audio):
        try:
            s = next(scores_iter)
        except StopIteration:
            detector._running = False
            return {"model": 0.0}
        return {"model": s}

    detector._model.predict.side_effect = fake_predict
    mock_stream = MagicMock()
    mock_stream.read.side_effect = fake_read
    detector._stream = mock_stream
    detector._running = True
    detector._listen()


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------

class TestWakeWordConfigDefaults:
    def test_default_min_activation_count(self):
        cfg = WakeWordConfig()
        assert cfg.min_activation_count == 3

    def test_default_cooldown_seconds(self):
        cfg = WakeWordConfig()
        assert cfg.cooldown_seconds == 2.0

    def test_custom_values(self):
        cfg = WakeWordConfig(min_activation_count=5, cooldown_seconds=3.5)
        assert cfg.min_activation_count == 5
        assert cfg.cooldown_seconds == 3.5


class TestWakeWordConfigLoad:
    def test_new_fields_loaded_from_yaml(self, tmp_path):
        yaml_text = """\
wake_word:
  model: hey_jarvis
  threshold: 0.6
  min_activation_count: 5
  cooldown_seconds: 3.0
"""
        p = tmp_path / "settings.yaml"
        p.write_text(yaml_text)
        cfg = load(str(p))
        assert cfg.wake_word.min_activation_count == 5
        assert cfg.wake_word.cooldown_seconds == 3.0

    def test_defaults_when_fields_absent(self, tmp_path):
        yaml_text = "wake_word:\n  model: hey_jarvis\n"
        p = tmp_path / "settings.yaml"
        p.write_text(yaml_text)
        cfg = load(str(p))
        assert cfg.wake_word.min_activation_count == 3
        assert cfg.wake_word.cooldown_seconds == 2.0


# ---------------------------------------------------------------------------
# min_activation_count tests
# ---------------------------------------------------------------------------

class TestMinActivationCount:
    def test_single_frame_does_not_trigger(self):
        callback = MagicMock()
        det, _ = _make_detector(
            threshold=0.5, min_activation_count=3, cooldown_seconds=0.0, callback=callback
        )
        # Only 1 frame above threshold (count never reaches 3)
        _feed_scores(det, [0.9, 0.1, 0.1, 0.1])
        callback.assert_not_called()

    def test_two_frames_does_not_trigger(self):
        callback = MagicMock()
        det, _ = _make_detector(
            threshold=0.5, min_activation_count=3, cooldown_seconds=0.0, callback=callback
        )
        # 2 frames above, then drops below — never reaches 3
        _feed_scores(det, [0.9, 0.9, 0.1, 0.1])
        callback.assert_not_called()

    def test_exactly_n_frames_triggers(self):
        callback = MagicMock()
        det, _ = _make_detector(
            threshold=0.5, min_activation_count=3, cooldown_seconds=0.0, callback=callback
        )
        _feed_scores(det, [0.9, 0.9, 0.9, 0.1])
        callback.assert_called_once()

    def test_more_than_n_frames_triggers_once(self):
        callback = MagicMock()
        det, _ = _make_detector(
            threshold=0.5, min_activation_count=2, cooldown_seconds=0.0, callback=callback
        )
        _feed_scores(det, [0.9, 0.9, 0.9, 0.9, 0.9])
        callback.assert_called_once()

    def test_interrupted_run_resets_counter(self):
        """High frames interrupted by a low frame should not trigger."""
        callback = MagicMock()
        det, _ = _make_detector(
            threshold=0.5, min_activation_count=3, cooldown_seconds=0.0, callback=callback
        )
        # Two high, one low, two high — never 3 in a row
        _feed_scores(det, [0.9, 0.9, 0.1, 0.9, 0.9])
        callback.assert_not_called()

    def test_min_activation_count_1_triggers_immediately(self):
        callback = MagicMock()
        det, _ = _make_detector(
            threshold=0.5, min_activation_count=1, cooldown_seconds=0.0, callback=callback
        )
        _feed_scores(det, [0.9])
        callback.assert_called_once()


# ---------------------------------------------------------------------------
# Cooldown tests
# ---------------------------------------------------------------------------

class TestCooldown:
    def test_second_detection_within_cooldown_suppressed(self):
        """After triggering, a second run within cooldown should not fire."""
        callback = MagicMock()
        det, _ = _make_detector(
            threshold=0.5, min_activation_count=1, cooldown_seconds=60.0, callback=callback
        )
        # First detection
        _feed_scores(det, [0.9])
        callback.assert_called_once()

        # Re-arm (simulate start() resetting running flag without clearing last_triggered)
        det._running = True
        det._consecutive = 0
        # Second detection — still within 60s cooldown
        _feed_scores(det, [0.9])
        callback.assert_called_once()  # still only once

    def test_detection_fires_after_cooldown_expires(self):
        """After cooldown has passed, the next detection should fire."""
        callback = MagicMock()
        det, _ = _make_detector(
            threshold=0.5, min_activation_count=1, cooldown_seconds=0.001, callback=callback
        )
        # First detection
        _feed_scores(det, [0.9])
        callback.assert_called_once()

        # Wait for cooldown to expire
        time.sleep(0.05)

        # Re-arm
        det._running = True
        det._consecutive = 0
        _feed_scores(det, [0.9])
        assert callback.call_count == 2

    def test_no_cooldown_triggers_each_run(self):
        callback = MagicMock()
        det, _ = _make_detector(
            threshold=0.5, min_activation_count=1, cooldown_seconds=0.0, callback=callback
        )
        for _ in range(3):
            det._running = True
            det._consecutive = 0
            _feed_scores(det, [0.9])
        assert callback.call_count == 3
