# Current Work

**Last updated:** 2026-05-10  
**Phase:** Phase 3 — Core Tool Integrations (in progress)

---

## Status

Implemented Google Auth module — all three Google Auth plan items completed:
- `config/google_credentials.json` skeleton created with step-by-step setup instructions
- `shared/config.py` `GoogleConfig` extended with `token_file` + `scopes` fields, wired from YAML
- `server/tools/google_auth.py` — `is_configured()`, `get_credentials()` (load/refresh/new browser OAuth flow), `build_service(api_name, version)`; guards CHANGE_ME placeholder; lazy google-auth imports
- `requirements-server.txt` — added `google-api-python-client`, `google-auth-httplib2`, `google-auth-oauthlib`
- `tests/test_google_auth.py` — 8 smoke tests pass

Blocked: Google Auth requires manual Google Cloud Console setup before Calendar/Tasks tools can use it.

Next task: Phase 3 — Google Calendar — `server/tools/calendar.py` (read events for today / date range).

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
