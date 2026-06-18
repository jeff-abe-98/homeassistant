"""Smoke tests for server/tools/music_profile.py."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sp(track_name="Test Track", artist_name="Test Artist", artist_id="art1",
             genres=None, audio_features=None):
    """Build a minimal spotipy mock matching calls made by record_play."""
    if genres is None:
        genres = ["indie pop", "pop"]
    if audio_features is None:
        audio_features = {
            "acousticness": 0.3,
            "danceability": 0.7,
            "energy": 0.8,
            "valence": 0.6,
            "tempo": 125.0,
        }
    sp = MagicMock()
    sp.track.return_value = {
        "name": track_name,
        "artists": [{"name": artist_name, "id": artist_id}],
    }
    sp.artist.return_value = {"genres": genres}
    sp.audio_features.return_value = [audio_features]
    return sp


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------


def test_init_db_creates_plays_table(tmp_path):
    from pi.tools.music_profile import init_db

    db = tmp_path / "test.db"
    init_db(db)
    with sqlite3.connect(db) as conn:
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert "plays" in tables


def test_init_db_idempotent(tmp_path):
    from pi.tools.music_profile import init_db

    db = tmp_path / "test.db"
    init_db(db)
    init_db(db)  # second call must not raise


def test_init_db_creates_parent_dirs(tmp_path):
    from pi.tools.music_profile import init_db

    db = tmp_path / "nested" / "dir" / "test.db"
    init_db(db)
    assert db.exists()


# ---------------------------------------------------------------------------
# record_play
# ---------------------------------------------------------------------------


def test_record_play_inserts_row(tmp_path):
    from pi.tools.music_profile import init_db, record_play

    db = tmp_path / "h.db"
    init_db(db)
    sp = _make_sp()

    record_play("owner", "spotify:track:abc123", sp, db_path=db)

    with sqlite3.connect(db) as conn:
        rows = conn.execute("SELECT * FROM plays").fetchall()
    assert len(rows) == 1
    row = rows[0]
    assert row[1] == "owner"          # user
    assert row[2] == "spotify:track:abc123"  # track_id
    assert row[3] == "Test Track"    # track_name
    assert row[4] == "Test Artist"   # artist
    assert json.loads(row[5]) == ["indie pop", "pop"]  # genres
    assert row[6] == 0.3             # acousticness
    assert row[13] == 0              # skipped


def test_record_play_uses_play_source(tmp_path):
    from pi.tools.music_profile import init_db, record_play

    db = tmp_path / "h.db"
    init_db(db)
    sp = _make_sp()

    record_play("emily", "spotify:track:xyz", sp, db_path=db, play_source="recommendation")

    with sqlite3.connect(db) as conn:
        row = conn.execute("SELECT play_source FROM plays").fetchone()
    assert row[0] == "recommendation"


def test_record_play_silently_ignores_api_errors(tmp_path):
    from pi.tools.music_profile import init_db, record_play

    db = tmp_path / "h.db"
    init_db(db)
    sp = MagicMock()
    sp.track.side_effect = RuntimeError("network error")

    # Must not raise
    record_play("owner", "spotify:track:bad", sp, db_path=db)

    with sqlite3.connect(db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM plays").fetchone()[0]
    assert count == 0


def test_record_play_tolerates_missing_audio_features(tmp_path):
    from pi.tools.music_profile import init_db, record_play

    db = tmp_path / "h.db"
    init_db(db)
    sp = _make_sp()
    sp.audio_features.return_value = [None]  # Spotify sometimes returns None

    record_play("owner", "spotify:track:abc", sp, db_path=db)

    with sqlite3.connect(db) as conn:
        row = conn.execute("SELECT energy FROM plays").fetchone()
    assert row[0] is None


# ---------------------------------------------------------------------------
# record_skip
# ---------------------------------------------------------------------------


def test_record_skip_marks_recent_play_as_skipped(tmp_path):
    from pi.tools.music_profile import init_db, record_play, record_skip

    db = tmp_path / "h.db"
    init_db(db)
    sp = _make_sp()
    record_play("owner", "spotify:track:abc", sp, db_path=db)

    record_skip("owner", "spotify:track:abc", db_path=db)

    with sqlite3.connect(db) as conn:
        row = conn.execute("SELECT skipped FROM plays").fetchone()
    assert row[0] == 1


def test_record_skip_does_not_skip_old_play(tmp_path):
    from pi.tools.music_profile import init_db, record_skip

    db = tmp_path / "h.db"
    init_db(db)
    # Insert a play with a timestamp 10 minutes ago (outside the 5-min window)
    old_ts = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    with sqlite3.connect(db) as conn:
        conn.execute(
            "INSERT INTO plays (user, track_id, track_name, artist, genres, "
            "timestamp, play_source, skipped) VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
            ("owner", "spotify:track:abc", "T", "A", "[]", old_ts, "request"),
        )

    record_skip("owner", "spotify:track:abc", db_path=db)

    with sqlite3.connect(db) as conn:
        row = conn.execute("SELECT skipped FROM plays").fetchone()
    assert row[0] == 0  # unchanged


def test_record_skip_silently_ignores_missing_db(tmp_path):
    from pi.tools.music_profile import record_skip

    # DB doesn't exist — must not raise
    record_skip("owner", "spotify:track:abc", db_path=tmp_path / "nope.db")


# ---------------------------------------------------------------------------
# build_profile
# ---------------------------------------------------------------------------


def _insert_play(conn, user, track_id, artist, genres, energy=0.7, dance=0.6,
                 valence=0.5, tempo=120.0, skipped=0, days_ago=1):
    ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    conn.execute(
        "INSERT INTO plays (user, track_id, track_name, artist, genres, "
        "energy, danceability, valence, tempo, timestamp, play_source, skipped) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'request', ?)",
        (user, track_id, "T", artist, json.dumps(genres),
         energy, dance, valence, tempo, ts, skipped),
    )


def test_build_profile_returns_default_for_missing_db(tmp_path):
    from pi.tools.music_profile import TasteProfile, build_profile

    profile = build_profile("owner", db_path=tmp_path / "nope.db")
    assert isinstance(profile, TasteProfile)
    assert profile.user == "owner"
    assert profile.genre_weights == {}


def test_build_profile_returns_default_for_fewer_than_5_plays(tmp_path):
    from pi.tools.music_profile import build_profile, init_db

    db = tmp_path / "h.db"
    init_db(db)
    with sqlite3.connect(db) as conn:
        for i in range(3):
            _insert_play(conn, "owner", f"t{i}", "Artist A", ["rock"])

    profile = build_profile("owner", db_path=db)
    assert profile.genre_weights == {}


def test_build_profile_computes_genre_weights(tmp_path):
    from pi.tools.music_profile import build_profile, init_db

    db = tmp_path / "h.db"
    init_db(db)
    with sqlite3.connect(db) as conn:
        for i in range(6):
            _insert_play(conn, "owner", f"t{i}", "Artist A", ["indie pop", "rock"])

    profile = build_profile("owner", db_path=db)
    assert "indie pop" in profile.genre_weights
    assert "rock" in profile.genre_weights
    total = sum(profile.genre_weights.values())
    assert abs(total - 1.0) < 1e-9  # normalized to 1.0


def test_build_profile_skips_reduce_artist_weight(tmp_path):
    from pi.tools.music_profile import build_profile, init_db

    db = tmp_path / "h.db"
    init_db(db)
    with sqlite3.connect(db) as conn:
        # 3 skipped plays for "Bad Artist" and 3 good plays for "Good Artist"
        for i in range(3):
            _insert_play(conn, "owner", f"bad{i}", "Bad Artist", ["genre"], skipped=1)
        for i in range(3):
            _insert_play(conn, "owner", f"good{i}", "Good Artist", ["genre"])

    profile = build_profile("owner", db_path=db)
    assert "Bad Artist" not in profile.artist_weights
    assert "Good Artist" in profile.artist_weights


def test_build_profile_audio_targets_are_means_of_completed_plays(tmp_path):
    from pi.tools.music_profile import build_profile, init_db

    db = tmp_path / "h.db"
    init_db(db)
    with sqlite3.connect(db) as conn:
        for i in range(5):
            _insert_play(conn, "owner", f"t{i}", "A", [], energy=0.8, dance=0.6,
                         valence=0.4, tempo=130.0, skipped=0)

    profile = build_profile("owner", db_path=db)
    assert abs(profile.audio_targets.target_energy - 0.8) < 0.01
    assert abs(profile.audio_targets.target_danceability - 0.6) < 0.01
    assert abs(profile.audio_targets.target_valence - 0.4) < 0.01
    assert abs(profile.audio_targets.target_tempo - 130.0) < 0.1


def test_build_profile_ignores_other_users(tmp_path):
    from pi.tools.music_profile import build_profile, init_db

    db = tmp_path / "h.db"
    init_db(db)
    with sqlite3.connect(db) as conn:
        for i in range(6):
            _insert_play(conn, "emily", f"t{i}", "Emily Artist", ["jazz"])

    profile = build_profile("owner", db_path=db)
    assert profile.genre_weights == {}  # no owner plays → default


# ---------------------------------------------------------------------------
# spotify.py integration — record_play wired into _search_and_play
# ---------------------------------------------------------------------------


def test_search_and_play_calls_record_play_for_track(tmp_path):
    """_search_and_play records a play when a single track URI is returned."""
    import sys
    from unittest.mock import patch

    sys.modules.setdefault("spotipy", MagicMock())

    from pi.tools.spotify import _search_and_play

    sp = MagicMock()
    sp.search.return_value = {
        "tracks": {"items": [{"uri": "spotify:track:t1", "name": "Hit", "artists": [{"name": "Pop Star"}]}]},
        "playlists": {"items": []},
    }

    with patch("pi.tools.music_profile.record_play") as mock_record:
        _search_and_play(sp, "hit song by pop star", "device123", user="owner")

    mock_record.assert_called_once()
    call_args = mock_record.call_args
    assert call_args[0][0] == "owner"
    assert "spotify:track:t1" in call_args[0][1]


def test_search_and_play_skips_record_for_playlist(tmp_path):
    """_search_and_play does not record plays for playlist context URIs."""
    import sys
    from unittest.mock import patch

    sys.modules.setdefault("spotipy", MagicMock())

    from pi.tools.spotify import _search_and_play

    sp = MagicMock()
    sp.search.return_value = {
        "playlists": {"items": [{"uri": "spotify:playlist:p1", "name": "Jazz Vibes"}]},
        "tracks": {"items": []},
    }

    with patch("pi.tools.music_profile.record_play") as mock_record:
        _search_and_play(sp, "jazz", "device123", user="owner")

    mock_record.assert_not_called()
