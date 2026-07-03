"""Audio playback through HDMI/sounddevice output.

Accepts raw PCM bytes (as produced by Piper TTS) and plays them
synchronously through the configured output device.
"""
from __future__ import annotations

import logging
import time
from math import gcd

import numpy as np
import sounddevice as sd
from scipy.signal import resample_poly

log = logging.getLogger(__name__)


def _generate_ack_chime(sample_rate: int) -> np.ndarray:
    """Synthesize a short two-note ascending chime (~180ms) acknowledging wake-word detection.

    Generated in code (no bundled audio asset). Each note is faded in/out over 5ms
    to avoid clicks at the sample boundaries.
    """
    note_s = 0.08
    gap_s = 0.02
    fade_s = 0.005
    amplitude = 0.3

    parts: list[np.ndarray] = []
    for freq in (880.0, 1320.0):
        n = int(sample_rate * note_s)
        t = np.arange(n) / sample_rate
        tone = (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.float32)
        fade_n = int(sample_rate * fade_s)
        if fade_n > 0:
            envelope = np.ones(n, dtype=np.float32)
            envelope[:fade_n] = np.linspace(0.0, 1.0, fade_n, dtype=np.float32)
            envelope[-fade_n:] = np.linspace(1.0, 0.0, fade_n, dtype=np.float32)
            tone *= envelope
        parts.append(tone)
        parts.append(np.zeros(int(sample_rate * gap_s), dtype=np.float32))
    return np.concatenate(parts[:-1])  # drop the trailing gap after the last note


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
            t_resample = time.perf_counter()
            g = gcd(self._sample_rate, self._output_sample_rate)
            samples = resample_poly(samples, self._output_sample_rate // g, self._sample_rate // g).astype(np.float32)
            log.debug(
                "LATENCY tts_resample_%dto%d=%.1fms out_samples=%d",
                self._sample_rate, self._output_sample_rate,
                (time.perf_counter() - t_resample) * 1000,
                len(samples),
            )
        if self._channels > 1:
            samples = np.stack([samples] * self._channels, axis=-1)
        t_play = time.perf_counter()
        sd.play(samples, samplerate=self._output_sample_rate, device=self._device)
        sd.wait()
        log.debug("LATENCY audio_playback=%.1fms audio_s=%.2f", (time.perf_counter() - t_play) * 1000, len(samples) / self._output_sample_rate)

    def play_ack_chime(self) -> None:
        """Play a short synthesized tone acknowledging wake-word detection, blocking until done.

        Generated at the output sample rate directly, so no resampling is needed.
        Callers should wait for this to return before starting to capture the
        user's utterance, so the chime itself is not picked up by the mic.
        """
        samples = _generate_ack_chime(self._output_sample_rate)
        t_play = time.perf_counter()
        sd.play(samples, samplerate=self._output_sample_rate, device=self._device)
        sd.wait()
        log.debug("LATENCY ack_chime_playback=%.1fms", (time.perf_counter() - t_play) * 1000)

    def stop(self) -> None:
        """Stop any currently playing audio immediately."""
        sd.stop()
