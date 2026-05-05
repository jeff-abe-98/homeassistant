# Current Work

**Last updated:** 2026-05-05 (session 12)  
**Phase:** Phase 1 — Core Voice Pipeline (Pi in progress)

---

## Status

WebSocket client complete. `pi/client.py` implements `AssistantClient`: async context manager connecting to `ws://{host}:{port}/ws`. Exposes `send_audio_chunk()`, `send_transcript()`, `receive_transcript(session_id)`, and `receive_response(session_id)`. A background asyncio task listens for server messages and routes them into per-session `asyncio.Queue` objects. Optional `on_transcript` and `on_response` async callbacks supported.

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

## Last Completed

- `pi/client.py` — `AssistantClient` async context manager; sends AudioChunk/Transcript, receives Transcript/AssistantResponse via per-session asyncio queues

## Next Task

- Phase 1 / Pi: `pi/main.py` — main loop: wake word → capture → send to server → receive response → TTS → play

## Open Questions

1. **Wake word name** — TBD, not blocking Phase 1
2. **Tool sandboxing** — design decision for Phase 5, not blocking now
3. **Voice enrollment UX** — needed for Phase 2

## Hardware Notes

- Server GPU upgrade pending: RTX 4060 Ti 16GB + 650W PSU (~$500)
- Until then: CPU inference with Llama 3.1 8B Q4
- After upgrade: switch Ollama model to Llama 3.1 13B Q4 in `config/settings.yaml`
