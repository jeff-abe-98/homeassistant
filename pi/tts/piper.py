"""Piper TTS wrapper — converts text to raw 16-bit PCM audio bytes."""
from __future__ import annotations

import io
import logging
import time
import wave
from pathlib import Path

logger = logging.getLogger(__name__)


class PiperTTS:
    """Synthesize text to raw 16-bit PCM bytes using a local Piper voice model.

    Args:
        model_path: Path to the .onnx voice model file.
        config_path: Path to the model JSON config. Defaults to <model_path>.json.
        use_cuda: Use CUDA for inference (requires onnxruntime-gpu).
    """

    def __init__(
        self,
        model_path: str | Path,
        config_path: str | Path | None = None,
        use_cuda: bool = False,
    ) -> None:
        from piper.voice import PiperVoice  # deferred: piper-tts not installed server-side

        model_path = Path(model_path)
        if config_path is None:
            config_path = Path(str(model_path) + ".json")

        t0 = time.perf_counter()
        self._voice = PiperVoice.load(
            str(model_path),
            config_path=str(config_path),
            use_cuda=use_cuda,
        )
        logger.debug("LATENCY tts_model_load=%.1fms model=%s", (time.perf_counter() - t0) * 1000, model_path.name)

    @property
    def sample_rate(self) -> int:
        """Sample rate of the loaded voice model (typically 22050 Hz)."""
        return self._voice.config.sample_rate

    def synthesize(self, text: str) -> bytes:
        """Convert text to raw 16-bit mono PCM audio bytes.

        Args:
            text: Text to synthesize. Whitespace-only input returns empty bytes.

        Returns:
            Raw int16 PCM at self.sample_rate Hz, suitable for AudioPlayer.play().
        """
        text = text.strip()
        if not text:
            return b""
        t0 = time.perf_counter()
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            self._voice.synthesize_wav(text, wf)
        buf.seek(0)
        with wave.open(buf, "rb") as wf:
            result = wf.readframes(wf.getnframes())
        logger.debug(
            "LATENCY tts_synthesize_internal=%.1fms chars=%d bytes=%d",
            (time.perf_counter() - t0) * 1000, len(text), len(result),
        )
        return result
