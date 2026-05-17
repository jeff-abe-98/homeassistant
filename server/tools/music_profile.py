"""Listening history collection and per-user taste profile builder.

Storage: SQLite at config/listening_history.db (gitignored).
"""

from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

_DEFAULT_DB = Path(__file__).parent.parent.parent / "config" / "listening_history.db"

_CREATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS plays (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user         TEXT NOT NULL,
    track_id     TEXT NOT NULL,
    track_name   TEXT NOT NULL,
    artist       TEXT NOT NULL,
    genres       TEXT NOT NULL,
    acousticness REAL,
    danceability REAL,
    energy       REAL,
    valence      REAL,
    tempo        REAL,
    timestamp    TEXT NOT NULL,
    play_source  TEXT NOT NULL,
    skipped      INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_plays_user      ON plays(user);
CREATE INDEX IF NOT EXISTS idx_plays_timestamp ON plays(timestamp);
"""


@dataclass
class AudioTargets:
    target_energy: float = 0.5
    target_danceability: float = 0.5
    target_valence: float = 0.5
    target_tempo: float = 120.0


@dataclass
class TasteProfile:
    user: str
    genre_weights: dict[str, float] = field(default_factory=dict)
    artist_weights: dict[str, float] = field(default_factory=dict)
    audio_targets: AudioTargets = field(default_factory=AudioTargets)
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def init_db(db_path: Path | str = _DEFAULT_DB) -> None:
    """Create the plays table and indexes if they don't already exist."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(_CREATE_SCHEMA)


def record_play(
    user: str,
    track_id: str,
    sp,
    db_path: Path | str = _DEFAULT_DB,
    play_source: str = "request",
) -> None:
    """Insert a play event into the listening history database.

    Fetches track metadata, audio features, and artist genres from Spotify.
    Silently swallows all errors — never interrupt playback on DB/API failures.
    """
    try:
        _record_play_impl(user, track_id, sp, Path(db_path), play_source)
    except Exception:
        pass


def _record_play_impl(user: str, track_id: str, sp, db_path: Path, play_source: str) -> None:
    init_db(db_path)

    track = sp.track(track_id)
    track_name: str = track.get("name", "")
    artists = track.get("artists") or []
    artist_name: str = artists[0]["name"] if artists else ""
    artist_id: str | None = artists[0]["id"] if artists else None

    genres: list[str] = []
    if artist_id:
        try:
            genres = sp.artist(artist_id).get("genres") or []
        except Exception:
            pass

    features: dict = {}
    try:
        feats = sp.audio_features([track_id])
        if feats and feats[0]:
            features = feats[0]
    except Exception:
        pass

    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO plays
                (user, track_id, track_name, artist, genres,
                 acousticness, danceability, energy, valence, tempo,
                 timestamp, play_source, skipped)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                user,
                track_id,
                track_name,
                artist_name,
                json.dumps(genres),
                features.get("acousticness"),
                features.get("danceability"),
                features.get("energy"),
                features.get("valence"),
                features.get("tempo"),
                now,
                play_source,
            ),
        )


def record_skip(
    user: str,
    track_id: str,
    db_path: Path | str = _DEFAULT_DB,
) -> None:
    """Mark the most recent play of track_id (within 5 minutes) as skipped.

    Silently swallows all errors.
    """
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        with sqlite3.connect(Path(db_path)) as conn:
            conn.execute(
                """
                UPDATE plays SET skipped = 1
                WHERE user = ? AND track_id = ? AND timestamp >= ?
                  AND skipped = 0
                  AND id = (
                      SELECT id FROM plays
                      WHERE user = ? AND track_id = ? AND timestamp >= ? AND skipped = 0
                      ORDER BY timestamp DESC
                      LIMIT 1
                  )
                """,
                (user, track_id, cutoff, user, track_id, cutoff),
            )
    except Exception:
        pass


def build_profile(
    user: str,
    db_path: Path | str = _DEFAULT_DB,
    days: int = 90,
) -> TasteProfile:
    """Return a TasteProfile for *user* from the last *days* of listening history.

    Returns a default profile if the database doesn't exist or has fewer than 5 plays.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        return TasteProfile(user=user)

    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=days)).isoformat()

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM plays WHERE user = ? AND timestamp >= ?",
            (user, cutoff),
        ).fetchall()

    if len(rows) < 5:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM plays WHERE user = ?", (user,)
            ).fetchall()
        if len(rows) < 5:
            return TasteProfile(user=user)

    genre_scores: dict[str, float] = {}
    artist_scores: dict[str, float] = {}
    energy_vals: list[float] = []
    dance_vals: list[float] = []
    valence_vals: list[float] = []
    tempo_vals: list[float] = []

    for row in rows:
        ts = datetime.fromisoformat(row["timestamp"])
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        days_ago = (now - ts).total_seconds() / 86400
        recency = math.exp(-days_ago / 60)
        sentiment = -1.0 if row["skipped"] else 1.0
        weight = recency * sentiment

        artist = row["artist"]
        if artist:
            artist_scores[artist] = artist_scores.get(artist, 0.0) + weight

        try:
            genres = json.loads(row["genres"])
        except (json.JSONDecodeError, TypeError):
            genres = []
        for genre in genres:
            genre_scores[genre] = genre_scores.get(genre, 0.0) + weight

        if not row["skipped"]:
            if row["energy"] is not None:
                energy_vals.append(row["energy"])
            if row["danceability"] is not None:
                dance_vals.append(row["danceability"])
            if row["valence"] is not None:
                valence_vals.append(row["valence"])
            if row["tempo"] is not None:
                tempo_vals.append(row["tempo"])

    total_genre = sum(v for v in genre_scores.values() if v > 0)
    if total_genre > 0:
        genre_weights = {g: s / total_genre for g, s in genre_scores.items() if s > 0}
    else:
        genre_weights = {}

    artist_weights = {a: s for a, s in artist_scores.items() if s > 0}

    def _mean(vals: list[float], default: float = 0.5) -> float:
        return sum(vals) / len(vals) if vals else default

    audio = AudioTargets(
        target_energy=_mean(energy_vals),
        target_danceability=_mean(dance_vals),
        target_valence=_mean(valence_vals),
        target_tempo=_mean(tempo_vals, default=120.0),
    )

    return TasteProfile(
        user=user,
        genre_weights=genre_weights,
        artist_weights=artist_weights,
        audio_targets=audio,
        updated_at=now,
    )
