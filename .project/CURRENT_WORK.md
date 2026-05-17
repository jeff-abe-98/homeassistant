# Current Work

**Last updated:** 2026-05-17  
**Phase:** Phase 7 — Music Recommendations (in progress)

---

## Status

Phase 7 in progress.

Done this session:
- `docs/music-recommendations.md` created — full design for the per-user taste model: SQLite plays table schema (genre/artist/audio features/skip signal), recency-weighted affinity score calculation, Spotify `recommendations()` API integration seeded by top genres+artists, `TasteProfile` + `AudioTargets` dataclasses, `music_profile.py` + `music_recommendations.py` file layout, cold-start flow, skip detection, privacy notes.

Next: Phase 7 — "Listening history collection from Spotify API" — implement `server/tools/music_profile.py` (`record_play`, `record_skip`, `build_profile`, SQLite DB).

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
