#!/usr/bin/env python3
"""
Train a custom openWakeWord model from positive recordings.

Produces an ONNX model compatible with the openWakeWord runtime:
  input:  (1, 16, 96)  — 16 embedding frames, 96 dims each
  output: (1, 1)       — detection score 0.0–1.0

Usage:
    python -m pi.wake_word.train_model \
        --positives ~/wakeword_samples \
        --name hey_clanker \
        --out pi/wake_word/models

The script auto-downloads negative speech samples from the
google/speech_commands dataset (streaming, no full download needed).
Alternatively, point --negatives at a directory of WAV files.
"""
from __future__ import annotations

import argparse
import os
import sys
import wave
from pathlib import Path

import numpy as np
import scipy.io.wavfile
import scipy.signal
import torch
import torch.nn as nn
from tqdm import tqdm

_SAMPLE_RATE = 16000
_CLIP_SAMPLES = 2 * _SAMPLE_RATE   # 2-second clips
_EMBEDDING_DIM = 96
_WINDOW_FRAMES = 16
_NEG_TARGET = 500  # negative examples to collect


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------

def _load_wav_16k_mono(path: Path) -> np.ndarray | None:
    """Load a WAV file as int16 mono at 16 kHz. Returns None on failure."""
    try:
        sr, data = scipy.io.wavfile.read(str(path))
        if data.ndim > 1:
            data = data[:, 0]
        if data.dtype != np.int16:
            data = data.astype(np.int16)
        if sr != _SAMPLE_RATE:
            n_samples = int(len(data) * _SAMPLE_RATE / sr)
            data = scipy.signal.resample(data.astype(np.float32), n_samples).astype(np.int16)
        return data
    except Exception as e:
        print(f"  [skip] {path.name}: {e}")
        return None


def _pad_or_trim(clip: np.ndarray, length: int = _CLIP_SAMPLES) -> np.ndarray:
    """Pad or trim to exactly `length` samples, preserving dtype."""
    if len(clip) >= length:
        return clip[:length]
    return np.pad(clip, (0, length - len(clip)))


def _load_positives(pos_dir: Path) -> np.ndarray:
    clips = []
    files = sorted(pos_dir.glob("*.wav"))
    print(f"Loading {len(files)} positive clips from {pos_dir} ...")
    for f in tqdm(files):
        data = _load_wav_16k_mono(f)
        if data is not None:
            clips.append(_pad_or_trim(data))
    # Keep int16 — embed_clips requires it
    if not clips:
        return np.empty((0, _CLIP_SAMPLES), dtype=np.int16)
    arr = np.stack(clips)
    print(f"  Loaded {len(arr)} positive clips.")
    return arr


def _load_negatives_from_dir(neg_dir: Path, n: int) -> np.ndarray:
    clips = []
    files = sorted(neg_dir.glob("**/*.wav"))[:n * 4]
    print(f"Loading negatives from {neg_dir} ...")
    for f in tqdm(files):
        if len(clips) >= n:
            break
        data = _load_wav_16k_mono(f)
        if data is not None and len(data) >= _SAMPLE_RATE // 2:
            clips.append(_pad_or_trim(data))
    print(f"  Loaded {len(clips)} negative clips.")
    if not clips:
        return np.empty((0, _CLIP_SAMPLES), dtype=np.int16)
    return np.stack(clips)


def _download_negatives(n: int) -> np.ndarray:
    """Stream negative examples from google/speech_commands via HuggingFace."""
    print(f"Downloading {n} negative examples from google/speech_commands (streaming)...")
    print("  This may take a minute on first run.")
    from datasets import load_dataset
    import io

    ds = load_dataset(
        "speech_commands",
        "v0.01",
        split="train",
        streaming=True,
        trust_remote_code=True,
    )

    clips = []
    for example in tqdm(ds, total=n):
        if len(clips) >= n:
            break
        try:
            audio = example["audio"]
            data = np.array(audio["array"], dtype=np.float32)
            sr = audio["sampling_rate"]
            # Convert float32 → int16
            data_i16 = (data * 32767).clip(-32768, 32767).astype(np.int16)
            if sr != _SAMPLE_RATE:
                n_samples = int(len(data_i16) * _SAMPLE_RATE / sr)
                data_i16 = scipy.signal.resample(data_i16.astype(np.float32), n_samples).astype(np.int16)
            if len(data_i16) >= _SAMPLE_RATE // 4:
                clips.append(_pad_or_trim(data_i16))
        except Exception:
            continue

    print(f"  Downloaded {len(clips)} negative clips.")
    if not clips:
        return np.empty((0, _CLIP_SAMPLES), dtype=np.int16)
    return np.stack(clips)


# ---------------------------------------------------------------------------
# Embedding extraction
# ---------------------------------------------------------------------------

def _compute_embeddings(clips: np.ndarray) -> np.ndarray:
    """
    Run the openWakeWord embedding pipeline on a batch of clips.
    Returns shape (N, frames, 96).
    """
    import openwakeword.utils as oww_utils

    print(f"Computing embeddings for {len(clips)} clips ...")
    featuriser = oww_utils.AudioFeatures()
    embeddings = featuriser.embed_clips(clips, batch_size=32)
    print(f"  Embeddings shape: {embeddings.shape}")
    return embeddings


# ---------------------------------------------------------------------------
# Training window extraction
# ---------------------------------------------------------------------------

def _extract_windows(embeddings: np.ndarray, positive: bool) -> np.ndarray:
    """
    Extract _WINDOW_FRAMES-frame windows from embedding sequences.

    For positives: take the center window (where the wake word likely lives).
    For negatives: take up to 3 random non-overlapping windows per clip.
    """
    windows = []
    n_frames = embeddings.shape[1]

    for emb in embeddings:
        if n_frames < _WINDOW_FRAMES:
            # Pad if clip is very short
            pad = np.zeros((_WINDOW_FRAMES - n_frames, _EMBEDDING_DIM), dtype=np.float32)
            emb = np.concatenate([emb, pad], axis=0)
            windows.append(emb)
        elif positive:
            # Centre window — wake word is typically in the middle of a 2s recording
            mid = n_frames // 2
            start = max(0, mid - _WINDOW_FRAMES // 2)
            start = min(start, n_frames - _WINDOW_FRAMES)
            windows.append(emb[start : start + _WINDOW_FRAMES])
        else:
            # Up to 3 random windows per negative clip
            max_start = n_frames - _WINDOW_FRAMES
            starts = np.random.choice(max_start + 1, size=min(3, max_start + 1), replace=False)
            for s in starts:
                windows.append(emb[s : s + _WINDOW_FRAMES])

    return np.array(windows, dtype=np.float32)


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class WakeWordMLP(nn.Module):
    def __init__(self, input_dim: int = _WINDOW_FRAMES * _EMBEDDING_DIM):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, 16, 96) — flatten to (batch, 1536)
        return self.net(x.flatten(start_dim=1))


def _train(pos_windows: np.ndarray, neg_windows: np.ndarray, epochs: int = 150) -> WakeWordMLP:
    print(f"\nTraining: {len(pos_windows)} positive, {len(neg_windows)} negative windows.")

    # Balance classes by oversampling the minority
    if len(pos_windows) < len(neg_windows):
        idx = np.random.choice(len(pos_windows), size=len(neg_windows), replace=True)
        pos_windows = pos_windows[idx]
    elif len(neg_windows) < len(pos_windows):
        idx = np.random.choice(len(neg_windows), size=len(pos_windows), replace=True)
        neg_windows = neg_windows[idx]

    X = np.concatenate([pos_windows, neg_windows], axis=0)
    y = np.array([1.0] * len(pos_windows) + [0.0] * len(neg_windows), dtype=np.float32)

    # Shuffle
    perm = np.random.permutation(len(X))
    X, y = X[perm], y[perm]

    X_t = torch.from_numpy(X)
    y_t = torch.from_numpy(y).unsqueeze(1)

    model = WakeWordMLP()
    optimiser = torch.optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.BCELoss()

    dataset = torch.utils.data.TensorDataset(X_t, y_t)
    loader = torch.utils.data.DataLoader(dataset, batch_size=64, shuffle=True)

    best_loss = float("inf")
    best_state = {k: v.clone() for k, v in model.state_dict().items()}
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        for xb, yb in loader:
            optimiser.zero_grad()
            loss = criterion(model(xb), yb)
            loss.backward()
            optimiser.step()
            total_loss += loss.item()
        avg = total_loss / len(loader)
        if avg < best_loss:
            best_loss = avg
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
        if epoch % 25 == 0 or epoch == 1:
            print(f"  Epoch {epoch:3d}/{epochs}  loss={avg:.4f}")

    model.load_state_dict(best_state)
    print(f"\n  Best loss: {best_loss:.4f}")
    return model


# ---------------------------------------------------------------------------
# ONNX export
# ---------------------------------------------------------------------------

def _export_onnx(model: WakeWordMLP, out_path: Path) -> None:
    model.eval()
    dummy = torch.zeros(1, _WINDOW_FRAMES, _EMBEDDING_DIM)
    torch.onnx.export(
        model,
        dummy,
        str(out_path),
        input_names=["x.1"],
        output_names=["53"],
        dynamic_axes={"x.1": {0: "batch"}},
        opset_version=12,
    )
    print(f"\n  Saved ONNX model → {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Train a custom openWakeWord model.")
    parser.add_argument("--positives", default="~/wakeword_samples",
                        help="Directory of positive WAV recordings")
    parser.add_argument("--negatives", default=None,
                        help="Directory of negative WAV recordings (auto-download if omitted)")
    parser.add_argument("--name", default="hey_clanker",
                        help="Model name (also the output filename stem)")
    parser.add_argument("--out", default="pi/wake_word/models",
                        help="Output directory for the .onnx model")
    parser.add_argument("--epochs", type=int, default=150)
    parser.add_argument("--neg-count", type=int, default=_NEG_TARGET,
                        help="Number of negative examples to use")
    args = parser.parse_args()

    pos_dir = Path(args.positives).expanduser().resolve()
    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.name}.onnx"

    # 1. Load data
    pos_clips = _load_positives(pos_dir)
    if len(pos_clips) == 0:
        print("ERROR: No positive clips found. Check --positives path.")
        sys.exit(1)

    if args.negatives:
        neg_clips = _load_negatives_from_dir(Path(args.negatives).expanduser(), args.neg_count)
    else:
        neg_clips = _download_negatives(args.neg_count)

    if len(neg_clips) == 0:
        print("ERROR: No negative clips. Provide --negatives or check internet connection.")
        sys.exit(1)

    # 2. Compute embeddings
    pos_emb = _compute_embeddings(pos_clips)
    neg_emb = _compute_embeddings(neg_clips)

    # 3. Extract windows
    pos_windows = _extract_windows(pos_emb, positive=True)
    neg_windows = _extract_windows(neg_emb, positive=False)

    # 4. Train
    model = _train(pos_windows, neg_windows, epochs=args.epochs)

    # 5. Export
    _export_onnx(model, out_path)

    # 6. Remind user to update settings.yaml
    print(f"\nNext step: update config/settings.yaml:")
    print(f"  wake_word:")
    print(f"    model: {out_path}")
    print()


if __name__ == "__main__":
    main()
