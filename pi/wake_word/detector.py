from __future__ import annotations

import threading
from typing import Callable

import numpy as np
import pyaudio

from shared.config import WakeWordConfig

_SAMPLE_RATE = 16000
_CHANNELS = 1
_FORMAT = pyaudio.paInt16
# openWakeWord expects 80ms frames at 16kHz
_CHUNK_SAMPLES = 1280


class WakeWordDetector:
    """Listens to mic audio continuously; calls on_detection() when wake word is heard."""

    def __init__(self, config: WakeWordConfig, on_detection: Callable[[], None]) -> None:
        from openwakeword.model import Model  # deferred — not installed on server

        self._config = config
        self._on_detection = on_detection
        self._model = Model(wakeword_models=[config.model], inference_framework="onnx")
        self._pa = pyaudio.PyAudio()
        self._stream: pyaudio.Stream | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._stream = self._pa.open(
            rate=_SAMPLE_RATE,
            channels=_CHANNELS,
            format=_FORMAT,
            input=True,
            frames_per_buffer=_CHUNK_SAMPLES,
        )
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._stream is not None:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _listen(self) -> None:
        while self._running:
            try:
                raw = self._stream.read(_CHUNK_SAMPLES, exception_on_overflow=False)
            except OSError:
                break
            audio = np.frombuffer(raw, dtype=np.int16)
            scores = self._model.predict(audio)
            for score in scores.values():
                if score >= self._config.threshold:
                    self._running = False
                    self._on_detection()
                    return

    def __enter__(self) -> "WakeWordDetector":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()
