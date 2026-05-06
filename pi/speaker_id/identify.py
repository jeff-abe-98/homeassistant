from __future__ import annotations

from pathlib import Path

import numpy as np

from pi.speaker_id.embeddings import embed_audio, list_profiles, load_embedding

_PROFILES_DIR = Path(__file__).parent.parent.parent / "config" / "voice_profiles"

# Cosine similarity threshold below which the speaker is "unknown".
# Resemblyzer embeddings are unit vectors, so dot product == cosine similarity.
_DEFAULT_THRESHOLD = 0.75


def identify_embedding(
    embedding: np.ndarray,
    threshold: float = _DEFAULT_THRESHOLD,
    profiles_dir: Path = _PROFILES_DIR,
) -> str:
    """Compare a 256-d embedding against all enrolled profiles.

    Returns the name of the best matching profile, or "unknown" if no profile
    scores at or above *threshold*.
    """
    names = list_profiles(profiles_dir)
    if not names:
        return "unknown"

    best_name = "unknown"
    best_score = -1.0

    for name in names:
        profile = load_embedding(name, profiles_dir)
        score = float(np.dot(embedding, profile))
        if score > best_score:
            best_score = score
            best_name = name

    return best_name if best_score >= threshold else "unknown"


def identify(
    pcm_bytes: bytes,
    sample_rate: int = 16000,
    threshold: float = _DEFAULT_THRESHOLD,
    profiles_dir: Path = _PROFILES_DIR,
) -> str:
    """Embed raw PCM audio and identify the speaker.

    Returns the enrolled profile name with the highest cosine similarity, or
    "unknown" if no profile meets *threshold*.
    """
    embedding = embed_audio(pcm_bytes, sample_rate)
    return identify_embedding(embedding, threshold=threshold, profiles_dir=profiles_dir)
