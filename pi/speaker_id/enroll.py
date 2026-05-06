"""Voice enrollment script.

Records 30 seconds of speech and saves a speaker embedding to
config/voice_profiles/{name}.npy.

Usage:
    python -m pi.speaker_id.enroll <name>
    python pi/speaker_id/enroll.py <name>
"""
from __future__ import annotations

import argparse
import sys
import time

import pyaudio

from pi.speaker_id.embeddings import embed_audio, save_embedding

SAMPLE_RATE = 16000
CHANNELS = 1
FRAME_DURATION_MS = 30
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)  # 480 samples
RECORD_SECONDS = 30


def record(duration: int = RECORD_SECONDS, device_index: int | None = None) -> bytes:
    """Record `duration` seconds of raw int16 PCM. Returns concatenated bytes."""
    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=pyaudio.paInt16,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        input_device_index=device_index,
        frames_per_buffer=FRAME_SIZE,
    )

    total_frames = int(SAMPLE_RATE / FRAME_SIZE * duration)
    chunks: list[bytes] = []

    print(f"Recording {duration}s — speak naturally now...")
    start = time.monotonic()
    for i in range(total_frames):
        chunks.append(stream.read(FRAME_SIZE, exception_on_overflow=False))
        elapsed = time.monotonic() - start
        remaining = duration - int(elapsed)
        if (i + 1) % (1000 // FRAME_DURATION_MS) == 0:
            print(f"  {remaining}s remaining...", end="\r", flush=True)

    print()  # newline after progress line
    stream.stop_stream()
    stream.close()
    pa.terminate()
    return b"".join(chunks)


def enroll(name: str, device_index: int | None = None) -> None:
    if not name.strip():
        print("Error: name must not be empty.", file=sys.stderr)
        sys.exit(1)

    print(f"\nEnrolling voice profile for: {name!r}")
    print("Talk naturally for 30 seconds — tell a story, describe your day, etc.")
    print("Good variety of speech gives the best identification accuracy.\n")

    pcm = record(RECORD_SECONDS, device_index=device_index)

    print("Generating embedding...")
    embedding = embed_audio(pcm, sample_rate=SAMPLE_RATE)

    path = save_embedding(name, embedding)
    print(f"Saved profile to: {path}")
    print(f"Profile shape: {embedding.shape}  (256-d unit vector)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Enroll a voice profile.")
    parser.add_argument("name", help="Profile name (e.g. 'owner' or 'emily')")
    parser.add_argument(
        "--device",
        type=int,
        default=None,
        metavar="INDEX",
        help="PyAudio input device index (default: system default)",
    )
    args = parser.parse_args()
    enroll(args.name, device_index=args.device)


if __name__ == "__main__":
    main()
