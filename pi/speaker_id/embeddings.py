from __future__ import annotations

from pathlib import Path

import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav

_PROFILES_DIR = Path(__file__).parent.parent.parent / "config" / "voice_profiles"

_encoder: VoiceEncoder | None = None


def _get_encoder() -> VoiceEncoder:
    global _encoder
    if _encoder is None:
        _encoder = VoiceEncoder()
    return _encoder


def embed_audio(pcm_bytes: bytes, sample_rate: int = 16000) -> np.ndarray:
    """Convert raw PCM int16 bytes to a 256-d speaker embedding."""
    wav = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    wav = preprocess_wav(wav, source_sr=sample_rate)
    return _get_encoder().embed_utterance(wav)


def save_embedding(name: str, embedding: np.ndarray, profiles_dir: Path = _PROFILES_DIR) -> Path:
    """Save embedding to config/voice_profiles/{name}.npy. Returns the saved path."""
    profiles_dir.mkdir(parents=True, exist_ok=True)
    path = profiles_dir / f"{name}.npy"
    np.save(path, embedding)
    return path


def load_embedding(name: str, profiles_dir: Path = _PROFILES_DIR) -> np.ndarray:
    """Load a saved embedding. Raises FileNotFoundError if profile doesn't exist."""
    path = profiles_dir / f"{name}.npy"
    if not path.exists():
        raise FileNotFoundError(f"No voice profile for {name!r} at {path}")
    return np.load(path)


def list_profiles(profiles_dir: Path = _PROFILES_DIR) -> list[str]:
    """Return names of all saved voice profiles (stems of .npy files)."""
    if not profiles_dir.exists():
        return []
    return [p.stem for p in sorted(profiles_dir.glob("*.npy"))]
