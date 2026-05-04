"""Audio playback through HDMI/sounddevice output.

Accepts raw PCM bytes (as produced by Piper TTS) and plays them
synchronously through the configured output device.
"""
from __future__ import annotations

import numpy as np
import sounddevice as sd


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
    ) -> None:
        self._sample_rate = sample_rate
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
        samples = np.frombuffer(audio_bytes, dtype=self._dtype)
        if self._channels > 1:
            samples = samples.reshape(-1, self._channels)
        sd.play(samples, samplerate=self._sample_rate, device=self._device)
        sd.wait()

    def stop(self) -> None:
        """Stop any currently playing audio immediately."""
        sd.stop()
