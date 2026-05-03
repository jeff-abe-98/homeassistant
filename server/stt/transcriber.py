from __future__ import annotations

import numpy as np
from faster_whisper import WhisperModel


class WhisperTranscriber:
    def __init__(self, model: str = "large-v3", device: str = "auto", compute_type: str = "auto") -> None:
        self._model = WhisperModel(model, device=device, compute_type=compute_type)

    def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> str:
        # PCM bytes from Pi are 16-bit signed integers; normalize to float32 [-1, 1]
        audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _ = self._model.transcribe(audio, language="en", beam_size=5)
        return " ".join(seg.text.strip() for seg in segments).strip()
