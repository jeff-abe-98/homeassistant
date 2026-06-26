"""HailoRT-backed Whisper STT client — same transcribe interface as the old WhisperTranscriber."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import numpy as np

from shared.config import HailoConfig

log = logging.getLogger(__name__)

# Lazy import — module loads fine on machines without Hailo hardware (tests mock it).
try:
    from hailo_platform import VDevice as _VDevice
    from hailo_platform.genai import Speech2Text as _HailoSTT

    _HAILO_AVAILABLE = True
except ImportError:
    _HAILO_AVAILABLE = False
    _VDevice = None  # type: ignore[assignment]
    _HailoSTT = None  # type: ignore[assignment]


def _pcm_to_float32(pcm_bytes: bytes) -> np.ndarray:
    """Convert raw int16 PCM bytes to float32 numpy array in [-1, 1]."""
    samples = np.frombuffer(pcm_bytes, dtype=np.int16)
    return samples.astype(np.float32) / 32768.0


class HailoTranscriber:
    """STT client backed by hailo_platform.genai.Speech2Text (Hailo-10H only).

    Model is loaded lazily on first call. Returns empty string on any failure
    so the calling main loop can skip the LLM step when no speech is detected.
    """

    def __init__(self, cfg: HailoConfig, vdevice: Any = None) -> None:
        self._cfg = cfg
        self._vdevice: Any = vdevice
        self._owns_vdevice: bool = vdevice is None
        self._stt: Any = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        """Load model on first call (lazy init avoids blocking __init__)."""
        if self._stt is not None:
            return
        if not _HAILO_AVAILABLE:
            raise RuntimeError(
                "hailo_platform is not installed. On Pi run: sudo apt install hailo-all hailo-genai"
            )
        t0 = time.perf_counter()
        if self._vdevice is None:
            self._vdevice = _VDevice()
        self._stt = _HailoSTT(
            vdevice=self._vdevice,
            model_path=self._cfg.stt_model_path,
        )
        log.info("HailoTranscriber: loaded model from %s", self._cfg.stt_model_path)
        log.debug("LATENCY stt_cold_load=%.1fms", (time.perf_counter() - t0) * 1000)

    def _transcribe_sync(self, pcm_bytes: bytes, sample_rate: int, max_seconds: float = 30.0) -> str:
        """Blocking transcription call — run in executor to keep async loop free."""
        is_cold = self._stt is None
        self._ensure_loaded()

        t_conv = time.perf_counter()
        audio = _pcm_to_float32(pcm_bytes)
        log.debug("LATENCY stt_pcm_to_float32=%.2fms samples=%d", (time.perf_counter() - t_conv) * 1000, len(audio))

        max_samples = int(max_seconds * sample_rate)
        if len(audio) > max_samples:
            log.debug("LATENCY stt_trim samples=%d→%d (%.2fs cap)", len(audio), max_samples, max_seconds)
            audio = audio[:max_samples]

        t_gen = time.perf_counter()
        result = self._stt.generate_all_text(audio)
        label = "cold" if is_cold else "warm"
        log.debug("LATENCY stt_transcribe_%s=%.1fms", label, (time.perf_counter() - t_gen) * 1000)

        if isinstance(result, str):
            return result.strip()
        return ""

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def transcribe(
        self,
        pcm_bytes: bytes,
        sample_rate: int = 16000,
        max_seconds: float = 30.0,
    ) -> str:
        """Transcribe raw int16 PCM audio. Returns empty string on any failure.

        Args:
            pcm_bytes: Raw 16-bit PCM audio bytes (mono, little-endian).
            sample_rate: Sample rate in Hz (default 16000, required by Whisper).
            max_seconds: Truncate audio to this many seconds before inference.
                Whisper zero-pads shorter buffers, so passing the actual
                utterance length avoids wasted NPU computation on silence.
                Default 30.0 (Whisper's native context window).

        Returns:
            Transcribed text, or empty string if audio is silent/empty or an
            error occurs (hardware unavailable, NPU error, etc.).
        """
        if not pcm_bytes:
            return ""
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                None, lambda: self._transcribe_sync(pcm_bytes, sample_rate, max_seconds)
            )
        except Exception:
            log.exception("HailoTranscriber: transcription failed")
            return ""

    def close(self) -> None:
        """Release Hailo NPU resources."""
        if self._stt is not None:
            try:
                self._stt.release()
            except Exception:
                pass
        if self._owns_vdevice and self._vdevice is not None:
            try:
                self._vdevice.release()
            except Exception:
                pass
        self._stt = None
        self._vdevice = None
