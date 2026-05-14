# Agent Progress Log

Most recent run at top.

---

## [2026-05-14 00:00 UTC]
**Completed:** Phase 4 Spotify — controls: `pause` (`sp.pause_playback()`), `skip` (`sp.next_track()`), `previous` (`sp.previous_track()`), `volume` (`sp.volume(level)`, clamped 0–100, error if level missing); 7 new smoke tests; 61 spotify tests, 170 total pass
**Files changed:** server/tools/spotify.py, tests/test_spotify.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 4 — Spotify — Test: Owner says "Play some jazz" → plays on TV through Owner's account
**Blockers:** None

---

## [2026-05-13 04:00 UTC]
**Completed:** Phase 4 Spotify — play by song/artist/playlist/mood query; `_find_user_playlist` (pagination, "my " strip, case-insensitive), `_search_spotify` (personal hints→user playlists, ≤3-word vague→playlist, specific "by" query→track), `_search_and_play` (`sp.start_playback`); `_ensure_tv_ready` factored from `_ensure_playing_on_tv`; `play` action dispatches to search when `query` present; 19 new tests; 54 spotify tests, 163 total pass
**Files changed:** server/tools/spotify.py, tests/test_spotify.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 4 — Spotify — Controls: pause, skip, volume
**Blockers:** None

---

## [2026-05-13 03:00 UTC]
**Completed:** Phase 4 Spotify — combined TV launch flow; `_find_tv_device_id(sp)` (fresh sp.devices() every call, never cached), `_launch_spotify_on_tv(atv_cfg)` (androidtvremote2 LEANBACK_LAUNCHER intent), `_ensure_playing_on_tv(sp, cfg)` (launch best-effort → poll 1s/15s → transfer_playback force_play=True); `play` action wired; "never cache device ID" constraint satisfied; 15 new smoke tests; 35 spotify tests, 144 total pass
**Files changed:** server/tools/spotify.py, tests/test_spotify.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 4 — Spotify — Play by song / artist / playlist / mood query
**Blockers:** None
---

## [2026-05-13 02:00 UTC]
**Completed:** Phase 4 Spotify — `server/tools/spotify.py` OAuth2 per user; `SpotifyUserConfig` extended with `redirect_uri`+`token_file`; `_is_configured()`, `_get_spotify()` (SpotifyOAuth token cache), `SpotifyTool` per-user routing + `now_playing`; `spotipy>=2.24.0` in requirements; spotipy stubbed in conftest; pytest env fixed (httpx + pytest-asyncio via uv); 20 new tests; 129 total pass
**Files changed:** server/tools/spotify.py, shared/config.py, requirements-server.txt, tests/test_spotify.py, conftest.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 4 — Spotify — Combined launch flow (androidtv launches Spotify app → poll `sp.devices()` → transfer playback to TV)
**Blockers:** None
---

## [2026-05-13 01:00 UTC]
**Completed:** Phase 4 Android TV — "Put on Netflix" integration tests; `tests/test_androidtv_integration.py` with 3 tests (correct Netflix package, case-insensitive, disconnect-on-error); auto-skip when androidtv.host is placeholder; 24 smoke tests + 3 skipped pass
**Files changed:** tests/test_androidtv_integration.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 4 — Spotify — `server/tools/spotify.py` (spotipy OAuth2 per user)
**Blockers:** None
---

## [2026-05-13 00:00 UTC]
**Completed:** Phase 4 Android TV — media key events; `_KEYCODE_MEDIA_PLAY/PAUSE/NEXT/PREVIOUS` constants; `play`, `pause`, `next`, `previous` actions in `AndroidTvTool`; 4 new smoke tests; 24 androidtv tests pass
**Files changed:** server/tools/androidtv.py, tests/test_androidtv.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 4 — Test: "Put on Netflix" → Netflix opens on TV
**Blockers:** None
---

## [2026-05-12 03:00 UTC]
**Completed:** Phase 4 Android TV — launch app by package name; `_APP_PACKAGES` dict (10 apps), `_resolve_package()`, `_launch_intent()` (LEANBACK_LAUNCHER intent URI); `launch_app` action added to `AndroidTvTool`; 11 new smoke tests; 105 total pass
**Files changed:** server/tools/androidtv.py, tests/test_androidtv.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 4 — Send media key events (play, pause, next, previous)
**Blockers:** None
---

## [2026-05-12 02:00 UTC]
**Completed:** Phase 4 Android TV — `server/tools/androidtv.py` with `androidtvremote2` connection infrastructure; `_connect()` helper (cert auto-generate + async_connect); `AndroidTvTool` power_on/power_off; `AndroidTvConfig` extended with cert/key paths; 9 new smoke tests; 94 total pass
**Files changed:** server/tools/androidtv.py, tests/test_androidtv.py, shared/config.py, config/settings.yaml, requirements-server.txt, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 4 — Launch app by package name (Spotify: `com.spotify.tv.android`, Netflix, YouTube, etc.)
**Blockers:** None
---

## [2026-05-12 01:00 UTC]
**Completed:** Integration tests for Google Tasks "Mark oat milk as done" — 2 new tests in `tests/test_tasks_integration.py` (owner + Emily); verify `tasks().patch()` called with correct per-user list ID, task ID, and `body={"status": "completed"}`; auto-skip without Google credentials; 85 smoke tests pass; Phase 3 fully complete
**Files changed:** tests/test_tasks_integration.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 4 — Android TV — `server/tools/androidtv.py` (`androidtvremote2` connection)
**Blockers:** None
---

## [2026-05-12 00:00 UTC]
**Completed:** Integration tests for Google Tasks "What's on my list?" — added 2 tests to `tests/test_tasks_integration.py` (owner + Emily); verify correct list ID used in `tasks().list()` and `showCompleted=False`; LLM mocked; auto-skip without credentials; 32 smoke tests pass
**Files changed:** tests/test_tasks_integration.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 3 — Google Tasks — Test: "Mark oat milk as done" → completes the item
**Blockers:** None
---

## [2026-05-11 04:00 UTC]
**Completed:** Integration tests for Google Tasks "add oat milk to my list" — `tests/test_tasks_integration.py` with 2 tests (owner + Emily per-user routing); auto-skip without Google credentials; 32 smoke tests pass, 2 skip
**Files changed:** tests/test_tasks_integration.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 3 — Google Tasks — Test: "What's on my list?" → reads back incomplete items
**Blockers:** None
---

## [2026-05-11 03:00 UTC]
**Completed:** Per-user Google Tasks list routing — replaced `_default_tasklist_id` with `_user_tasklist_id(service, user)` that finds a list matching the user's name, creates it if absent, falls back to first list for unknown users; all 3 tasks tools updated; 9 new tests (7 unit + 2 e2e owner/emily routing); 32 total pass
**Files changed:** server/tools/tasks.py, tests/test_tasks.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 3 — Google Tasks — Test: "Add oat milk to my list" → added to correct user's list
**Blockers:** Google Auth needs manual Google Cloud Console setup before Tasks/Calendar tools can make live API calls
---

## [2026-05-11 02:00 UTC]
**Completed:** `server/tools/tasks.py` — `AddTaskTool`, `ListTasksTool`, `CompleteTaskTool`; uses Google Tasks API v1 via shared `build_service`; `_default_tasklist_id` helper; case-insensitive `_find_task_by_title`; 23 smoke tests in `tests/test_tasks.py` all pass
**Files changed:** server/tools/tasks.py, tests/test_tasks.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 3 — Google Tasks — Separate task lists per user ("Owner", "Emily")
**Blockers:** Google Auth needs manual Google Cloud Console setup before Tasks/Calendar tools can make live API calls
---

## [2026-05-11 01:00 UTC]
**Completed:** Integration test for Emily dentist appointment — `test_emily_dentist_appointment_created_as_emily_dentist` added to `tests/test_calendar_integration.py`; uses real `dateparser` ("Thursday at 3" → hour=15); mocks Google Calendar insert to capture event body; asserts summary="Emily Dentist", hour=15, timeZone=America/Chicago; confirmation includes "Emily Dentist"; skips without credentials; 29 smoke tests still pass
**Files changed:** tests/test_calendar_integration.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 3 — Google Tasks — `server/tools/tasks.py` (add item, list incomplete items, complete item by name)
**Blockers:** Google Auth needs manual Google Cloud Console setup before Calendar/Tasks tools can make live API calls
---

