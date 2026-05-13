# Current Work

**Last updated:** 2026-05-13  
**Phase:** Phase 4 — Spotify (in progress)

---

## Status

Implemented Spotify search-and-play in `server/tools/spotify.py`:
- `_ensure_tv_ready(sp, cfg)` — factored from `_ensure_playing_on_tv`; launches Spotify on TV via androidtv, polls `sp.devices()` until TV appears, returns device ID
- `_ensure_playing_on_tv(sp, cfg)` — thin wrapper: `_ensure_tv_ready` + `sp.transfer_playback(force_play=True)` (behavior unchanged)
- `_find_user_playlist(sp, query)` — scans user's own playlists with pagination; strips leading "my "; case-insensitive substring match; returns first matching URI
- `_search_spotify(sp, query)` — searches `track,playlist` catalog; personal hints (my ..., Discover Weekly, Release Radar, etc.) → user playlists first; vague ≤3-word queries → prefer playlist; specific queries (contains " by ") → prefer track; returns `(context_uri, track_uris, description)`
- `_search_and_play(sp, query, device_id)` — calls `_search_spotify`, then `sp.start_playback(device_id, context_uri, uris)`
- `play` action: if `query` present → `_ensure_tv_ready` + `_search_and_play`; otherwise → `_ensure_playing_on_tv` (resume)
- 19 new smoke tests; 54 spotify tests, 163 total pass

Next: Phase 4 — Spotify — Controls: pause, skip, volume.

## Documents

| File | Purpose |
|------|---------|
| `requirements.md` | Full project requirements |
| `docs/architecture.md` | System design, hardware, resolved decisions |
| `docs/technical-stack.md` | Full stack with library choices and rationale |
| `docs/features.md` | Per-feature behavior specs |
| `plan.md` | **Phased implementation plan with checkboxes — agents work from here** |

## Agent Instructions

1. Read `plan.md`
2. Find the first unchecked item in the current active phase
3. Read `docs/technical-stack.md` for stack decisions before writing any code
4. Implement the item
5. Check it off in `plan.md` with a brief note
6. Continue until the phase is complete or a blocker is hit
7. Log blockers in the Blockers Log table at the bottom of `plan.md`

## Open Questions

1. **Wake word name** — TBD, not blocking Phase 1
2. **Tool sandboxing** — design decision for Phase 5, not blocking now
3. **Voice enrollment UX** — enrollment scripts exist; physical enrollment deferred until Pi hardware is set up

## Hardware Notes

- Server GPU upgrade pending: RTX 4060 Ti 16GB + 650W PSU (~$500)
- Until then: CPU inference with Llama 3.1 8B Q4
- After upgrade: switch Ollama model to Llama 3.1 13B Q4 in `config/settings.yaml`
