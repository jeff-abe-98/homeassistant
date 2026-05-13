# Current Work

**Last updated:** 2026-05-13  
**Phase:** Phase 4 — Android TV (in progress)

---

## Status

Created `tests/test_androidtv_integration.py` — "Put on Netflix" integration tests:
- `test_put_on_netflix_sends_correct_package`: verifies `send_launch_app()` called with `com.netflix.ninja` LEANBACK_LAUNCHER intent using real config (not mocked cfg); `_connect` is mocked
- `test_put_on_netflix_case_insensitive`: title-cased "Netflix" works the same
- `test_put_on_netflix_disconnect_called_even_on_error`: disconnect runs in finally even on launch error
- All 3 skip when `androidtv.host` is still placeholder (192.168.x.x); 24 smoke tests + 3 skipped pass

Next: Phase 4 — Spotify — `server/tools/spotify.py` (spotipy OAuth2 per user).

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
