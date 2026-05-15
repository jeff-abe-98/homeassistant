# Current Work

**Last updated:** 2026-05-15  
**Phase:** Phase 5 — Autonomous Tool Creation

---

## Status

Phase 5 in progress. Integrated tool creator into `server/main.py`:
- `_needs_new_tool(text)` — LLM binary classifier: sends the request to the LLM with a system prompt asking if external capability is required; returns True only if reply starts with "yes"
- `_create_and_notify(transcript, websocket)` — background coroutine: runs generate → validate → install pipeline; sends "I can do that now — want to try?" over WebSocket on success; suppresses WebSocket errors if connection already closed
- `_handle_transcript(transcript, websocket)` — updated signature (now takes websocket); when router returns None and `_needs_new_tool` is True, returns immediate "I don't know how to do that yet…" response and fires `_create_and_notify` as a background asyncio task; falls back to plain LLM for conversational requests
- `_generator` global initialized in lifespan
- `tests/test_main_tool_creator.py` — 13 smoke tests pass

Next: Phase 5 — Test: ask for something novel → tool is created and works on second request.

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
