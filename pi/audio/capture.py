"""Microphone capture with WebRTC VAD gating.

Yields AudioChunk objects while voice is active. Each detected utterance gets a
fresh session_id and sequence starting at 0. A final chunk with is_final=True
and empty audio_bytes signals end of utterance.
"""
from __future__ import annotations

import collections
import logging
import statistics
import threading
import time
import uuid
from typing import Generator

import pyaudio
import webrtcvad

from shared.models import AudioChunk

logger = logging.getLogger(__name__)

SAMPLE_RATE = 48000   # native USB mic rate; caller resamples to 16 kHz for STT
CHANNELS = 1
FRAME_DURATION_MS = 10  # WebRTC VAD supports 10 ms frames at 48 kHz
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)  # 480 samples @ 48 kHz


class VoiceCapture:
    """Open mic stream, gate output on WebRTC VAD.

    Args:
        vad_aggressiveness: 0–3; higher = more aggressive non-speech filtering.
        pre_speech_padding_ms: audio buffered before speech onset (avoids clipping
            the first phoneme). Must be a multiple of FRAME_DURATION_MS.
        silence_duration_ms: consecutive silence required to end an utterance.
        min_speech_ms: minimum post-trigger recording time before silence detection
            begins; prevents the wake word itself from immediately ending the session.
        speech_ratio: fraction of pre-speech ring that must be voiced to trigger.
        silence_ratio: fraction of silence ring that must be unvoiced to end.
        device_index: PyAudio input device index, or None for system default.
    """

    def __init__(
        self,
        vad_aggressiveness: int = 1,
        pre_speech_padding_ms: int = 300,
        silence_duration_ms: int = 800,
        min_speech_ms: int = 1500,
        speech_ratio: float = 0.6,
        silence_ratio: float = 0.75,
        device_index: int | None = None,
    ) -> None:
        self._vad = webrtcvad.Vad(vad_aggressiveness)
        self._pa = pyaudio.PyAudio()
        self._device_index = device_index
        self._pre_frames = pre_speech_padding_ms // FRAME_DURATION_MS
        self._sil_frames = silence_duration_ms // FRAME_DURATION_MS
        self._min_speech_frames = max(0, min_speech_ms // FRAME_DURATION_MS)
        self._speech_ratio = speech_ratio
        self._silence_ratio = silence_ratio
        self._stream: pyaudio.Stream | None = None
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def open_stream(self) -> "pyaudio.Stream":
        """Open the 48 kHz capture stream and keep it alive across utterances.

        Idempotent — returns the existing stream if already open.
        Call close() to release the stream and PyAudio.
        """
        if self._stream is None:
            t = time.perf_counter()
            self._stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                input_device_index=self._device_index,
                frames_per_buffer=FRAME_SIZE,
            )
            logger.debug("LATENCY vad_stream_open=%.1fms", (time.perf_counter() - t) * 1000)
        return self._stream

    def capture_from_stream(
        self,
        stream: "pyaudio.Stream",
        t_stream_open: float = 0.0,
    ) -> Generator[AudioChunk, None, None]:
        """Yield AudioChunks for exactly one utterance from an already-open stream.

        Resets all VAD state on each call. Returns after yielding is_final=True.
        Does not open or close the stream — caller manages its lifecycle.
        """
        pre_ring: collections.deque[tuple[bytes, bool]] = collections.deque(
            maxlen=self._pre_frames
        )
        sil_ring: collections.deque[bool] = collections.deque(
            maxlen=self._sil_frames
        )
        triggered = False
        post_trigger_frames = 0
        session_id = ""
        sequence = 0

        _frame_read_ms: list[float] = []
        _frame_vad_ms: list[float] = []
        _t_triggered: float = 0.0

        while not self._stop_event.is_set():
            _t0 = time.perf_counter()
            try:
                frame = stream.read(FRAME_SIZE, exception_on_overflow=False)
            except OSError:
                break
            _t1 = time.perf_counter()
            is_speech = self._vad.is_speech(frame, SAMPLE_RATE)
            _t2 = time.perf_counter()

            if not triggered:
                pre_ring.append((frame, is_speech))
                if len(pre_ring) == pre_ring.maxlen:
                    voiced = sum(1 for _, v in pre_ring if v)
                    if voiced / pre_ring.maxlen >= self._speech_ratio:
                        triggered = True
                        _t_triggered = time.perf_counter()
                        logger.debug(
                            "LATENCY vad_trigger_fired stream_age=%.1fms",
                            (_t_triggered - t_stream_open) * 1000,
                        )
                        _frame_read_ms.clear()
                        _frame_vad_ms.clear()
                        post_trigger_frames = 0
                        session_id = str(uuid.uuid4())
                        sequence = 0
                        sil_ring.clear()
                        for f, _ in pre_ring:
                            yield AudioChunk(
                                session_id=session_id,
                                sequence=sequence,
                                audio_bytes=f,
                                sample_rate=SAMPLE_RATE,
                                is_final=False,
                            )
                            sequence += 1
                        pre_ring.clear()
            else:
                _frame_read_ms.append((_t1 - _t0) * 1000)
                _frame_vad_ms.append((_t2 - _t1) * 1000)
                yield AudioChunk(
                    session_id=session_id,
                    sequence=sequence,
                    audio_bytes=frame,
                    sample_rate=SAMPLE_RATE,
                    is_final=False,
                )
                sequence += 1
                post_trigger_frames += 1
                # Don't start silence detection until min_speech_ms of audio
                # has been captured — prevents wake word tail from ending session.
                if post_trigger_frames >= self._min_speech_frames:
                    sil_ring.append(is_speech)
                    if len(sil_ring) == sil_ring.maxlen:
                        unvoiced = sum(1 for v in sil_ring if not v)
                        if unvoiced / sil_ring.maxlen >= self._silence_ratio:
                            if _frame_read_ms:
                                logger.debug(
                                    "LATENCY utterance_end frames=%d "
                                    "read_avg=%.2fms read_min=%.2fms read_max=%.2fms "
                                    "vad_avg=%.3fms vad_min=%.3fms vad_max=%.3fms "
                                    "total_triggered=%.1fms audio_ms=%d silence_tail≈%.1fms",
                                    len(_frame_read_ms),
                                    statistics.mean(_frame_read_ms),
                                    min(_frame_read_ms),
                                    max(_frame_read_ms),
                                    statistics.mean(_frame_vad_ms),
                                    min(_frame_vad_ms),
                                    max(_frame_vad_ms),
                                    (time.perf_counter() - _t_triggered) * 1000,
                                    len(_frame_read_ms) * FRAME_DURATION_MS,
                                    (time.perf_counter() - _t_triggered) * 1000
                                    - len(_frame_read_ms) * FRAME_DURATION_MS,
                                )
                            yield AudioChunk(
                                session_id=session_id,
                                sequence=sequence,
                                audio_bytes=b"",
                                sample_rate=SAMPLE_RATE,
                                is_final=True,
                            )
                            return  # One utterance complete; stream stays open

    def drain(self, stream: "pyaudio.Stream", n_frames: int = 50) -> None:
        """Discard buffered mic audio so the next capture_from_stream() begins fresh.

        Reads and discards frames until the ALSA buffer catches up to real-time
        (a read taking close to a full frame duration means no backlog remains)
        or n_frames are consumed. Call this after playing the wake-word ack chime
        so its own audio (and any backlog built up while it played) isn't fed
        into VAD as part of the user's utterance.
        """
        t0 = time.perf_counter()
        caught_up_threshold_s = (FRAME_DURATION_MS / 1000) * 0.5
        for _ in range(n_frames):
            t_read = time.perf_counter()
            try:
                stream.read(FRAME_SIZE, exception_on_overflow=False)
            except OSError:
                break
            if (time.perf_counter() - t_read) > caught_up_threshold_s:
                break
        logger.debug("LATENCY capture_stream_drain=%.1fms", (time.perf_counter() - t0) * 1000)

    def stream(self) -> Generator[AudioChunk, None, None]:
        """Yield AudioChunks indefinitely; one utterance at a time.

        The generator never returns on its own — stop it by calling close() or
        by using GeneratorExit (e.g. break out of the for-loop).
        """
        t_open_start = time.perf_counter()
        self._stream = self._pa.open(
            format=pyaudio.paInt16,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            input_device_index=self._device_index,
            frames_per_buffer=FRAME_SIZE,
        )
        t_stream_open = time.perf_counter()
        logger.debug("LATENCY vad_stream_open=%.1fms", (t_stream_open - t_open_start) * 1000)

        self._stop_event.clear()
        try:
            while not self._stop_event.is_set():
                yield from self.capture_from_stream(self._stream, t_stream_open)
        finally:
            self.close()

    def stop(self) -> None:
        """Signal the stream loop to exit after the current frame (thread-safe)."""
        self._stop_event.set()

    def close(self) -> None:
        """Stop and release the PyAudio stream and terminate PyAudio."""
        self._stop_event.set()
        if self._stream is not None:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None
        self._pa.terminate()
