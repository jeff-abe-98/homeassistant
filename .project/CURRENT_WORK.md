# Current Work

**Last updated:** 2026-05-15  
**Phase:** Phase 6 — Hardening & Quality (in progress)

---

## Status

Phase 6 in progress.

Done this session:
- `deploy/homeassistant-pi.service` — systemd unit (Type=simple, After=network-online.target sound.target, Restart=on-failure, RestartSec=5s, StartLimitBurst=5, SyslogIdentifier=homeassistant-pi); entry point is `python -m pi.main`
- `deploy/install-pi-service.sh` — install script: creates service user, adds it to the `audio` group (required for PyAudio mic + sounddevice output), rsyncs project, creates venv + installs `requirements-pi.txt`, substitutes install path + user into unit file, `systemctl enable + restart`

Next: Phase 6 — Error handling: graceful recovery from LLM timeout, API failures, network drop.

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
