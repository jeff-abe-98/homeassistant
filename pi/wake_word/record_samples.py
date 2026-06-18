#!/usr/bin/env python3
"""
Wake word sample recorder.

Records positive training samples for openWakeWord custom model training.
Saves 16kHz mono WAV files to a target directory.

Usage:
    python -m pi.wake_word.record_samples --phrase "hey pi" --out ~/wakeword_samples --target 150
    python -m pi.wake_word.record_samples --phrase "hey pi"   # uses defaults

Controls:
    Enter       — record the next sample
    p + Enter   — play back the last recording
    d + Enter   — delete the last recording
    q + Enter   — quit (saves progress)
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

_SAMPLE_RATE = 16000
_CHANNELS = 1
_DURATION = 2.0      # seconds per recording
_PRE_BEEP_HZ = 880   # A5 — "ready" tone
_POST_BEEP_HZ = 523  # C5 — "got it" tone
_BEEP_DURATION = 0.12  # seconds
_BEEP_AMPLITUDE = 0.4


def _beep(freq: float, duration: float = _BEEP_DURATION, amplitude: float = _BEEP_AMPLITUDE) -> None:
    t = np.linspace(0, duration, int(_SAMPLE_RATE * duration), endpoint=False)
    # Soft envelope to avoid clicks
    envelope = np.ones_like(t)
    fade = int(0.01 * _SAMPLE_RATE)
    envelope[:fade] = np.linspace(0, 1, fade)
    envelope[-fade:] = np.linspace(1, 0, fade)
    tone = (amplitude * np.sin(2 * np.pi * freq * t) * envelope).astype(np.float32)
    sd.play(tone, samplerate=_SAMPLE_RATE, blocking=True)


def _record() -> np.ndarray:
    """Record _DURATION seconds; return int16 samples."""
    samples = sd.rec(
        int(_SAMPLE_RATE * _DURATION),
        samplerate=_SAMPLE_RATE,
        channels=_CHANNELS,
        dtype="int16",
    )
    sd.wait()
    return samples.flatten()


def _save_wav(path: Path, samples: np.ndarray) -> None:
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(_CHANNELS)
        wf.setsampwidth(2)  # int16 = 2 bytes
        wf.setframerate(_SAMPLE_RATE)
        wf.writeframes(samples.tobytes())


def _play_wav(path: Path) -> None:
    with wave.open(str(path), "r") as wf:
        data = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
    sd.play(data.astype(np.float32) / 32768.0, samplerate=_SAMPLE_RATE, blocking=True)


def _count_existing(out_dir: Path) -> int:
    return len(list(out_dir.glob("*.wav")))


def _next_path(out_dir: Path, index: int) -> Path:
    return out_dir / f"sample_{index:04d}.wav"


def _print_status(done: int, target: int, phrase: str) -> None:
    bar_width = 30
    filled = int(bar_width * done / target) if target else 0
    bar = "#" * filled + "-" * (bar_width - filled)
    pct = int(100 * done / target) if target else 0
    print(f"\r  [{bar}] {done}/{target} ({pct}%)  — say \"{phrase}\"   ", end="", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Record wake word training samples.")
    parser.add_argument("--phrase", default="hey pi", help="Wake phrase to display as a prompt")
    parser.add_argument("--out", default="~/wakeword_samples", help="Output directory for WAV files")
    parser.add_argument("--target", type=int, default=150, help="Target number of samples")
    parser.add_argument("--duration", type=float, default=_DURATION, help="Recording duration in seconds")
    args = parser.parse_args()

    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    duration = args.duration
    phrase = args.phrase
    target = args.target

    existing = _count_existing(out_dir)
    index = existing + 1

    print()
    print(f"  Wake word sample recorder")
    print(f"  Phrase   : \"{phrase}\"")
    print(f"  Output   : {out_dir}")
    print(f"  Target   : {target} samples")
    print(f"  Existing : {existing} samples already saved")
    print(f"  Duration : {duration:.1f}s per clip  |  16 kHz mono WAV")
    print()
    print("  Controls: Enter=record  p=playback last  d=delete last  q=quit")
    print()

    last_path: Path | None = None

    while index <= target + 1:  # allow going slightly over target
        _print_status(index - 1, target, phrase)
        try:
            cmd = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if cmd == "q":
            break

        if cmd == "p":
            if last_path and last_path.exists():
                print(f"\n  Playing back {last_path.name}...")
                _play_wav(last_path)
            else:
                print("\n  Nothing to play back yet.")
            continue

        if cmd == "d":
            if last_path and last_path.exists():
                last_path.unlink()
                print(f"\n  Deleted {last_path.name}.")
                index -= 1
                last_path = None
            else:
                print("\n  Nothing to delete.")
            continue

        if cmd != "":
            print(f"\n  Unknown command '{cmd}'. Enter=record  p=play  d=delete  q=quit")
            continue

        # Record
        _beep(_PRE_BEEP_HZ)
        samples = _record()
        _beep(_POST_BEEP_HZ)

        path = _next_path(out_dir, index)
        _save_wav(path, samples)
        last_path = path
        index += 1

        if index - 1 >= target:
            print(f"\n\n  Target reached! {target} samples saved to {out_dir}")
            print(f"  You can keep going (press Enter) or quit (q + Enter).\n")

    done = index - 1
    print(f"\n\n  Session complete. {done} samples in {out_dir}")
    if done < target:
        print(f"  Still need {target - done} more to hit your target of {target}.")
    print()


if __name__ == "__main__":
    main()
