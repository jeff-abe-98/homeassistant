# Current Work

**Last updated:** 2026-05-13  
**Phase:** Phase 4 — Spotify (in progress)

---

## Status

Created `server/tools/spotify.py` — spotipy OAuth2 per user:
- `_is_configured(user_cfg)` — guards CHANGE_ME credentials
- `_get_spotify(user_cfg)` — returns `spotipy.Spotify` via `SpotifyOAuth` (token cache file, `open_browser=False`)
- `_user_cfg_and_display(cfg, user)` — routes emily→emily config, all others→owner config
- `SpotifyTool` — BaseTool with `now_playing` action (functional); other actions return "not wired yet" stub
- `SpotifyUserConfig` extended with `redirect_uri` and `token_file` fields; `load()` reads from `users` YAML section for token paths
- `spotipy>=2.24.0` added to `requirements-server.txt`; spotipy stubbed in `conftest.py`
- 20 smoke tests in `tests/test_spotify.py`; 129 total pass, 16 skipped

Next: Phase 4 — Spotify — Combined launch flow (androidtv launches Spotify app → poll `sp.devices()` → transfer playback to TV).

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
