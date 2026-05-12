# Current Work

**Last updated:** 2026-05-12  
**Phase:** Phase 4 — Android TV (in progress)

---

## Status

Implemented `server/tools/androidtv.py` — Phase 4 Android TV connection task:
- `_connect(atv_cfg)` — instantiates `AndroidTVRemote`, calls `async_generate_cert_if_missing()` + `async_connect()`; cert pair stored at `config/androidtv_cert.pem` / `config/androidtv_key.pem`
- `AndroidTvTool` — `power_on` (KEYCODE_WAKEUP) and `power_off` (KEYCODE_SLEEP); guards unconfigured host; friendly messages for CannotConnect / InvalidAuth errors; `disconnect()` in finally block
- `AndroidTvConfig` extended with `cert_file` / `key_file` fields; wired in `load()`
- `androidtvremote2>=0.1.1` added to `requirements-server.txt`
- 9 smoke tests all pass; full suite: 94 passed, 13 skipped

Next: Phase 4 — Launch app by package name (Spotify, Netflix, YouTube).

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
