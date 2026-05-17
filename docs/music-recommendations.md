# Music Recommendations — Design

**Phase:** 7  
**Status:** Design complete — ready for implementation

---

## Goal

Build a per-user taste model that learns from listening history and powers "Play something I'd like" recommendations, without any cloud AI or external recommendation service.

---

## Data Collected

### Listening History

Every track play is recorded with enough signal to learn preferences:

| Field | Type | Notes |
|-------|------|-------|
| `user` | str | "owner" or "emily" |
| `track_id` | str | Spotify track URI |
| `track_name` | str | Human-readable for debugging |
| `artist` | str | Primary artist name |
| `genres` | list[str] | From `sp.artist(artist_id)["genres"]` |
| `acousticness` | float | Spotify audio feature, 0–1 |
| `danceability` | float | Spotify audio feature, 0–1 |
| `energy` | float | Spotify audio feature, 0–1 |
| `valence` | float | Spotify audio feature (mood), 0–1 |
| `tempo` | float | BPM |
| `timestamp` | datetime | UTC play start time |
| `play_source` | str | "request", "recommendation", "queue" |
| `skipped` | bool | True if user skipped before 30s |

Skips are negative signal. Completing a play (not skipped) is positive signal.

### Storage

SQLite database at `config/listening_history.db` — one file per installation, gitignored.

Schema:

```sql
CREATE TABLE plays (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user        TEXT NOT NULL,
    track_id    TEXT NOT NULL,
    track_name  TEXT NOT NULL,
    artist      TEXT NOT NULL,
    genres      TEXT NOT NULL,       -- JSON array
    acousticness REAL,
    danceability REAL,
    energy      REAL,
    valence     REAL,
    tempo       REAL,
    timestamp   TEXT NOT NULL,       -- ISO 8601 UTC
    play_source TEXT NOT NULL,
    skipped     INTEGER NOT NULL DEFAULT 0  -- 0 or 1
);

CREATE INDEX idx_plays_user ON plays(user);
CREATE INDEX idx_plays_timestamp ON plays(timestamp);
```

---

## Taste Model

The model lives entirely in `server/tools/music_profile.py`. It is a lightweight in-memory summary rebuilt from the plays table on demand (no training loop, no model file).

### Per-User Profile

```python
@dataclass
class TasteProfile:
    user: str
    genre_weights: dict[str, float]   # genre → affinity score
    artist_weights: dict[str, float]  # artist → affinity score
    audio_targets: AudioTargets       # preferred audio feature ranges
    updated_at: datetime
```

### AudioTargets

```python
@dataclass
class AudioTargets:
    target_energy: float      # mean of non-skipped plays
    target_danceability: float
    target_valence: float
    target_tempo: float
    # Tolerances are ±0.2 for each float feature, ±30 BPM for tempo
```

### Affinity Score Calculation

For each genre or artist seen in the plays table:

```
score = Σ weight(play) for all plays featuring this genre/artist
```

Where:
```
weight(play) = recency_factor(play.timestamp) × sentiment(play.skipped)
recency_factor = exp(-days_ago / 60)   # half-life ~42 days
sentiment = -1.0 if skipped else +1.0
```

Genre weights sum-normalized to 1.0 before use as Spotify seed weights. Artists with negative net score are excluded from seeds.

---

## Recommendation Query

When the user says "Play something I'd like":

1. **Build profile** from plays in the last 90 days (or all plays if fewer than 20 rows).
2. **Select seeds**: top-3 genres by weight + top-2 artists by weight (Spotify allows up to 5 seeds total).
3. **Call** `sp.recommendations(seed_genres=..., seed_artists=..., target_energy=..., target_danceability=..., target_valence=..., target_tempo=..., limit=20)`.
4. **Filter** out tracks already played in the last 7 days.
5. **Shuffle** and start playback of the filtered list as a queue on the TV.
6. **Record** each track played with `play_source="recommendation"`.

If fewer than 5 plays exist for a user, fall back to `sp.featured_playlists()` and note: "I'm still learning your taste — I'll get better as you listen more."

---

## Voice Interface

New intent: `music_recommendation`

Trigger phrases (handled by LLM router via tool description):
- "Play something I'd like"
- "Play something good"
- "Surprise me"
- "Play something for me"

Parameters: none (user identity comes from speaker ID as usual).

The tool returns a natural-language confirmation string after queuing tracks, e.g.:
> "Queuing 15 tracks based on your listening history — enjoy."

---

## File Layout

```
server/tools/
├── music_profile.py        # TasteProfile, AudioTargets, profile builder, DB writer
└── music_recommendations.py  # RecommendationTool (BaseTool)

config/
└── listening_history.db    # SQLite, gitignored
```

`music_profile.py` is imported by both `spotify.py` (to record plays) and `music_recommendations.py` (to build profile and query).

---

## Integration Points

### Recording Plays

`SpotifyTool._search_and_play()` calls `record_play(user, track_id, sp)` after each successful `start_playback`. `record_play` fetches audio features from `sp.audio_features([track_id])` and `sp.artist()` for genres, then inserts into the `plays` table.

### Skip Detection

`SpotifyTool` already handles `skip` action. When a skip is triggered, call `record_skip(user, track_id)` — updates the most recent play row for that track (within last 5 minutes) to set `skipped=1`.

### Cold Start

New users with no history get genre prompts on first "surprise me" request:
> "I don't know your taste yet. What genres do you usually like?"

The LLM extracts genre names from the reply and seeds 10 "virtual plays" (weight 0.5 each, `play_source="seed"`) to bootstrap the profile.

---

## Privacy

- All data stays local in `config/listening_history.db`.
- No data leaves the home network.
- DB is gitignored — never committed.
- Users can say "Forget my music history" to delete their rows.

---

## Constraints & Non-Goals

- No collaborative filtering between Owner and Emily — separate profiles, no cross-contamination.
- No neural embeddings or training loop — the affinity score math is the model.
- No model persistence file — the profile is always recomputed from raw plays (fast enough for <10k rows).
- Spotify Premium required for `sp.recommendations()` (same constraint as all other Spotify features).
