"""Audio playback through HDMI/sounddevice output.

Accepts raw PCM bytes (as produced by Piper TTS) and plays them
synchronously through the configured output device.
"""
from __future__ import annotations

import numpy as np
import sounddevice as sd
from scipy.signal import resample_poly
from math import gcd


class AudioPlayer:
    """Play raw PCM audio bytes through a sounddevice output device.

    Args:
        sample_rate: Sample rate matching the incoming audio (Piper TTS default: 22050).
        channels: 1 for mono, 2 for stereo.
        device: sounddevice device index or substring of device name (e.g. "hdmi",
            "HDMI"). None uses the system default output device.
        dtype: numpy dtype string for the PCM samples ('int16', 'float32', etc.).
    """

    def __init__(
        self,
        sample_rate: int = 22050,
        channels: int = 1,
        device: int | str | None = None,
        dtype: str = "int16",
        output_sample_rate: int = 48000,
    ) -> None:
        self._sample_rate = sample_rate
        self._output_sample_rate = output_sample_rate
        self._channels = channels
        self._device = device
        self._dtype = dtype

    def play(self, audio_bytes: bytes) -> None:
        """Play raw PCM audio, blocking until playback finishes.

        Args:
            audio_bytes: Raw PCM data matching sample_rate, channels, and dtype.
                         Empty bytes are silently ignored.
        """
        if not audio_bytes:
            return
        samples = np.frombuffer(audio_bytes, dtype=self._dtype).astype(np.float32) / 32768.0
        if self._sample_rate != self._output_sample_rate:
            g = gcd(self._sample_rate, self._output_sample_rate)
            samples = resample_poly(samples, self._output_sample_rate // g, self._sample_rate // g).astype(np.float32)
        if self._channels > 1:
            samples = np.stack([samples] * self._channels, axis=-1)
        sd.play(samples, samplerate=self._output_sample_rate, device=self._device)
        sd.wait()

    def stop(self) -> None:
        """Stop any currently playing audio immediately."""
        sd.stop()
