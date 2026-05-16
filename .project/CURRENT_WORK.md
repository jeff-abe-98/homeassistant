# Current Work

**Last updated:** 2026-05-16  
**Phase:** Phase 6 — Hardening & Quality (in progress)

---

## Status

Phase 6 in progress.

Done this session:
- `server/llm/router.py` — `ToolRouter.route()` now returns `tuple[ToolCall | None, str]`; when no tool is selected, `message.content` from `chat_with_tools` is returned as fallback text; when no schemas registered, calls `_llm.complete()` and returns the content
- `server/main.py` — added `import time`; removed `_NEEDS_TOOL_SYSTEM` and `_needs_new_tool()` LLM classifier; added `_CANNOT_HELP_PHRASES` frozenset and `_heuristic_needs_tool(text)` keyword check; `_handle_transcript` uses single LLM call (router), reuses fallback text for conversational reply, falls back to direct `_llm.complete` only when router raises; `time.perf_counter()` timing logs added for STT, routing, and tool steps
- Tests updated: `test_main_tool_creator.py` (heuristic tests replace `_needs_new_tool` LLM tests; router mocks updated to return tuples), `test_error_handling.py` (LLM failure tests updated for new flow; all tool tests return tuples), `test_tool_creator_e2e.py` (router mocks updated to tuple form); 282 total pass

Next: Phase 6 — Agent startup check-in (last unchecked Phase 6 item).

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
