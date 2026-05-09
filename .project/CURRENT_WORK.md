# Current Work

**Last updated:** 2026-05-09  
**Phase:** Phase 3 — Core Tool Integrations (in progress)

---

## Status

Created `docs/parts-list.md` — hardware parts list moved up from Phase 6 per user request. Pi section: Raspberry Pi 5 (8 GB), ReSpeaker 2-Mic Pi HAT, official PSU, 64 GB A2 MicroSD, HAT-compatible case (~$130–140 total). Server section: RTX 4060 Ti 16 GB + 650 W PSU GPU upgrade (~$500–550). Includes ReSpeaker driver install notes for Pi 5 and post-GPU config change.

Next task: Phase 3 — Register CTA API key in config.

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
