# Current Work

**Last updated:** 2026-05-10  
**Phase:** Phase 3 — Core Tool Integrations (in progress)

---

## Status

Wrote `tests/test_cta_integration.py` — two async integration tests (`test_cta_next_blue_line_real_api` + `test_cta_ohare_direction_real_api`) that auto-skip when `cta.api_key` is CHANGE_ME. When a real key is set they call the live CTA Train Tracker API, verify the parsed arrivals list structure (destination, arrival_time, is_delayed fields), and assert the LLM system prompt contains correct direction context. All 11 existing CTA smoke tests still pass.

Next task: Phase 3 — Google Auth — Set up Google Cloud project, enable Calendar API + Tasks API.

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
