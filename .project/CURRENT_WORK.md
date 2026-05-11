# Current Work

**Last updated:** 2026-05-11  
**Phase:** Phase 3 — Core Tool Integrations (in progress)

---

## Status

Implemented "reads events for speaking user" — calendar narration personalized by user:
- `server/tools/calendar.py` — `CalendarTool.run()` injects user name into LLM system prompt when user is a known speaker (not "unknown"); LLM can now address them by name in narration
- `tests/test_calendar.py` — 2 new smoke tests: known user name appears in system prompt, "unknown" does not; 29 total tests pass
- `tests/test_calendar_integration.py` — 2 integration tests (owner + Emily) for "What do I have tomorrow?" hitting real Google Calendar API; auto-skip when credentials not configured

Still blocked: Google Auth requires manual Google Cloud Console setup before Calendar tool can make live API calls.

Next task: Phase 3 — Google Calendar — Test: Emily says "I have a dentist appointment Thursday at 3" → event created as "Emily Dentist".

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
