# Current Work

**Last updated:** 2026-05-14  
**Phase:** Phase 5 — Autonomous Tool Creation

---

## Status

Phase 5 in progress. Implemented `server/tool_creator/sandbox.py`:
- `ALLOWED_IMPORTS` — frozenset of allowed top-level module names (stdlib + httpx, pydantic, yaml, shared, server)
- `check_imports(source)` — static AST walk; returns list of disallowed module names; raises SyntaxError on invalid Python
- `SandboxResult` — dataclass with `success`, `stdout`, `stderr`, `exit_code`
- `run_in_sandbox(source, timeout)` — static import check → write to temp file → spawn subprocess with CPU time + address-space limits via `preexec_fn` (`resource.setrlimit`) → wall-clock timeout via `asyncio.wait_for`; kills process on timeout; cleans up temp file
- `_apply_resource_limits()` — POSIX preexec_fn; RLIMIT_CPU=5s, RLIMIT_AS=256MB; no-op on non-POSIX
- `tests/test_tool_creator_sandbox.py` — 18 smoke tests; 203 total pass

Next: Phase 5 — `server/tool_creator/validator.py` — run generated tool with test inputs, check for errors.

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
