from __future__ import annotations

import logging
import threading
import time
from typing import Callable

import numpy as np
import pyaudio

from shared.config import WakeWordConfig

log = logging.getLogger(__name__)

_SAMPLE_RATE = 16000
_CHANNELS = 1
_FORMAT = pyaudio.paInt16
# openWakeWord expects 80ms frames at 16kHz
_CHUNK_SAMPLES = 1280


class WakeWordDetector:
    """Listens to mic audio continuously; calls on_detection() when wake word is heard.

    False-positive reduction:
      - min_activation_count: requires N consecutive frames above threshold
        (~80ms each) before the callback fires.
      - cooldown_seconds: suppresses the callback for this many seconds after
        a detection so the same utterance cannot trigger twice.
    """

    def __init__(self, config: WakeWordConfig, on_detection: Callable[[], None]) -> None:
        import os
        from openwakeword.model import Model  # deferred — not installed on server

        self._config = config
        self._on_detection = on_detection

        model_path = config.model
        if not os.path.isfile(model_path):
            import openwakeword
            resources = os.path.join(os.path.dirname(openwakeword.__file__), "resources", "models")
            candidate = os.path.join(resources, f"{model_path}_v0.1.onnx")
            if os.path.isfile(candidate):
                model_path = candidate

        self._model = Model(wakeword_model_paths=[model_path])
        self._pa = pyaudio.PyAudio()
        self._stream: pyaudio.Stream | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._consecutive = 0
        self._last_triggered: float = 0.0

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._consecutive = 0
        self._last_triggered = 0.0
        t_open = time.perf_counter()
        self._stream = self._pa.open(
            rate=_SAMPLE_RATE,
            channels=_CHANNELS,
            format=_FORMAT,
            input=True,
            frames_per_buffer=_CHUNK_SAMPLES,
        )
        log.debug("LATENCY wakeword_stream_open=%.1fms", (time.perf_counter() - t_open) * 1000)
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        t_close = time.perf_counter()
        if self._stream is not None:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None
        log.debug("LATENCY wakeword_stream_close=%.1fms", (time.perf_counter() - t_close) * 1000)
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._pa.terminate()

    def _listen(self) -> None:
        while self._running:
            try:
                raw = self._stream.read(_CHUNK_SAMPLES, exception_on_overflow=False)
            except OSError:
                break
            audio = np.frombuffer(raw, dtype=np.int16)
            scores = self._model.predict(audio)

            above_threshold = any(
                score >= self._config.threshold for score in scores.values()
            )

            if above_threshold:
                self._consecutive += 1
            else:
                self._consecutive = 0

            if self._consecutive >= self._config.min_activation_count:
                now = time.monotonic()
                if now - self._last_triggered >= self._config.cooldown_seconds:
                    self._consecutive = 0
                    self._last_triggered = now
                    self._running = False
                    self._on_detection()
                    return
                else:
                    # Within cooldown — reset counter so we need N fresh frames
                    self._consecutive = 0

    def __enter__(self) -> "WakeWordDetector":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()
