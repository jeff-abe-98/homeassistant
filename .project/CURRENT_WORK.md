# Current Work

**Last updated:** 2026-05-14  
**Phase:** Phase 4 — Spotify complete → Phase 5 next

---

## Status

Phase 4 Spotify is complete. Last item: created `tests/test_spotify_integration.py`:
- `test_owner_play_jazz_uses_owner_account_and_starts_playback` — verifies Owner credentials used, "jazz" search returns playlist, `start_playback` called with TV device ID
- `test_emily_play_discover_weekly_uses_emily_account_and_user_playlist` — verifies Emily credentials used, `current_user_playlists` called, `start_playback` called with Emily's Discover Weekly URI
- Both tests skip when credentials are CHANGE_ME; 170 smoke pass, 2 new skipped
- Also fixed pytest environment: added pyyaml and httpx to `uv tool install` so all 170 tests run correctly

Next: Phase 5 — Autonomous Tool Creation — `server/tool_creator/generator.py`.

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
