"""Microphone capture with WebRTC VAD gating.

Yields AudioChunk objects while voice is active. Each detected utterance gets a
fresh session_id and sequence starting at 0. A final chunk with is_final=True
and empty audio_bytes signals end of utterance.
"""
from __future__ import annotations

import collections
import uuid
from typing import Generator

import pyaudio
import webrtcvad

from shared.models import AudioChunk

SAMPLE_RATE = 16000
CHANNELS = 1
FRAME_DURATION_MS = 30
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)  # 480 samples @ 16 kHz


class VoiceCapture:
    """Open mic stream, gate output on WebRTC VAD.

    Args:
        vad_aggressiveness: 0–3; higher = more aggressive non-speech filtering.
        pre_speech_padding_ms: audio buffered before speech onset (avoids clipping
            the first phoneme). Must be a multiple of FRAME_DURATION_MS.
        silence_duration_ms: consecutive silence required to end an utterance.
        speech_ratio: fraction of pre-speech ring that must be voiced to trigger.
        silence_ratio: fraction of silence ring that must be unvoiced to end.
        device_index: PyAudio input device index, or None for system default.
    """

    def __init__(
        self,
        vad_aggressiveness: int = 2,
        pre_speech_padding_ms: int = 300,
        silence_duration_ms: int = 900,
        speech_ratio: float = 0.9,
        silence_ratio: float = 0.9,
        device_index: int | None = None,
    ) -> None:
        self._vad = webrtcvad.Vad(vad_aggressiveness)
        self._pa = pyaudio.PyAudio()
        self._device_index = device_index
        self._pre_frames = pre_speech_padding_ms // FRAME_DURATION_MS
        self._sil_frames = silence_duration_ms // FRAME_DURATION_MS
        self._speech_ratio = speech_ratio
        self._silence_ratio = silence_ratio
        self._stream: pyaudio.Stream | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def stream(self) -> Generator[AudioChunk, None, None]:
        """Yield AudioChunks indefinitely; one utterance at a time.

        The generator never returns on its own — stop it by calling close() or
        by using GeneratorExit (e.g. break out of the for-loop).
        """
        self._stream = self._pa.open(
            format=pyaudio.paInt16,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            input_device_index=self._device_index,
            frames_per_buffer=FRAME_SIZE,
        )

        pre_ring: collections.deque[tuple[bytes, bool]] = collections.deque(
            maxlen=self._pre_frames
        )
        sil_ring: collections.deque[bool] = collections.deque(
            maxlen=self._sil_frames
        )
        triggered = False
        session_id = ""
        sequence = 0

        try:
            while True:
                frame = self._stream.read(FRAME_SIZE, exception_on_overflow=False)
                is_speech = self._vad.is_speech(frame, SAMPLE_RATE)

                if not triggered:
                    pre_ring.append((frame, is_speech))
                    if len(pre_ring) == pre_ring.maxlen:
                        voiced = sum(1 for _, v in pre_ring if v)
                        if voiced / pre_ring.maxlen >= self._speech_ratio:
                            triggered = True
                            session_id = str(uuid.uuid4())
                            sequence = 0
                            sil_ring.clear()
                            # Flush pre-speech buffer to give context
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
                    yield AudioChunk(
                        session_id=session_id,
                        sequence=sequence,
                        audio_bytes=frame,
                        sample_rate=SAMPLE_RATE,
                        is_final=False,
                    )
                    sequence += 1
                    sil_ring.append(is_speech)
                    if len(sil_ring) == sil_ring.maxlen:
                        unvoiced = sum(1 for v in sil_ring if not v)
                        if unvoiced / sil_ring.maxlen >= self._silence_ratio:
                            yield AudioChunk(
                                session_id=session_id,
                                sequence=sequence,
                                audio_bytes=b"",
                                sample_rate=SAMPLE_RATE,
                                is_final=True,
                            )
                            sequence += 1
                            pre_ring.clear()
                            sil_ring.clear()
                            triggered = False
        finally:
            self.close()

    def close(self) -> None:
        """Stop and release the PyAudio stream and terminate PyAudio."""
        if self._stream is not None:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None
        self._pa.terminate()
