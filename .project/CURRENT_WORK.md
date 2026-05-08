# Current Work

**Last updated:** 2026-05-08  
**Phase:** Phase 3 — Core Tool Integrations (in progress)

---

## Status

Implemented `server/tools/cta.py` — `CtaTool` fetches upcoming Blue Line arrivals from CTA Train Tracker API for Western & Milwaukee stop (stop IDs 30238 / 30239). Accepts a `direction` param (`ohare`, `forest_park`, `both`); fetches the appropriate stop ID(s); parses arrival time, destination, and delay fields; passes structured data to LLM for natural narration. Guards against CHANGE_ME placeholder key. `CtaConfig` updated with `stop_id_ohare` and `stop_id_forest_park` fields wired from YAML. 8 smoke tests pass (2 config, 2 error-path, 3 happy-path, 1 parse helper).

Next task: Phase 3 — Handle directional queries (O'Hare vs Forest Park).

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
