# Current Work

**Last updated:** 2026-05-17  
**Phase:** Phase 6 — Hardening & Quality (COMPLETE)

---

## Status

Phase 6 complete.

Done this session:
- `CLAUDE.md` created — formalizes all agent workflow steps: Step 0 git config, Step 1 read context, Step 2 startup check-in (prepend to INBOX.md Agent Startup Log with session #/status/next/blockers), Step 3 inbox processing, Step 4 plan item implementation, Step 5 PROGRESS.md update, Step 6 commit+push

Next: Phase 7 (Music Recommendations) — first item: "Design per-user taste model".

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
