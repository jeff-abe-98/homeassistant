# Current Work

**Last updated:** 2026-05-11  
**Phase:** Phase 3 — Core Tool Integrations (in progress)

---

## Status

Implemented `server/tools/tasks.py` — three Google Tasks tools:
- `AddTaskTool` (`add_task`) — inserts a task into the default task list
- `ListTasksTool` (`list_tasks`) — reads incomplete tasks, narrates via LLM with user-name injection
- `CompleteTaskTool` (`complete_task`) — finds task by case-insensitive name match and patches status to "completed"
- `_default_tasklist_id` helper gets the first task list; `_find_task_by_title` does case-insensitive search
- 23 smoke tests in `tests/test_tasks.py` — all pass

Still blocked: Google Auth requires manual Google Cloud Console setup before Tasks/Calendar tools can make live API calls.

Next task: Phase 3 — Google Tasks — Separate task lists per user ("Owner", "Emily").

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
