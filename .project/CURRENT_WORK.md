# Current Work

**Last updated:** 2026-05-16  
**Phase:** Phase 6 — Hardening & Quality (in progress)

---

## Status

Phase 6 in progress.

Done this session:
- `server/llm/client.py` — `LLMError`/`LLMTimeoutError` exception types; `OllamaClient` wraps all `_client.chat()` calls in `asyncio.wait_for` (default 30s, configurable via `ollama.timeout`); raises `LLMTimeoutError` on timeout, `LLMError` on connection errors
- `shared/config.py` — `OllamaConfig.timeout: float = 30.0` added, wired through `load()`
- `server/main.py` — all critical paths now wrapped in try/except: router failure → falls back to LLM; tool.run() failure → friendly "ran into a problem" message; LLM timeout/error → friendly "trouble connecting" message; STT failure → returns None; WebSocket loop handles JSONDecodeError; active session tracking cleans up orphaned audio buffers on disconnect
- `tests/test_error_handling.py` — 15 new tests covering all error paths (LLM timeout, connection error, tool API failure, router failure, STT failure, buffer cleanup)

Next: Phase 6 — Logging: structured logs to file with rotation.

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
