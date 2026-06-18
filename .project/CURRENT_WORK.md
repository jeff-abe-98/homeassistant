# Current Work

**Last updated:** 2026-06-18
**Phase:** Phase 8 — item 1 done (.claude/agents/tool-builder.md)

---

## Status

Full architectural redesign in progress. The original server+Pi split architecture has been superseded. A new spec and plan have been written for a fully Pi-based system (Pi 5 8GB + AI HAT+ 2).

**Spec:** `.project/active/pi-redesign/spec.md`
**Plan:** `plan.md` (completely replaced — all old phases 1-7 complete and archived)

Phase 8 item 1 is complete:

**Item 1:** `.claude/agents/tool-builder.md` — remote scheduled agent definition:
- 5-step run order: git pull → reschedule self → process pending requests → git push
- **Step 2 (reschedule):** CronList to find existing job, CronDelete it, read `schedule.json` (default: `7 3 * * *`; window-based: pick most-common low-usage hour), CronCreate recurring durable job
- **Step 3 (sort):** glob `tool_requests/pending/*.json`, sort by priority rank (high→mid→low) then timestamp (FIFO)
- **Step 4 (generate):** for each request — snake_case tool name from `intent`; read `pi/tools/base.py`; write `tools/generated/{name}.py` (BaseTool subclass, httpx for HTTP, config guards, spoken-English output); write `tools/generated/{name}_instructions.md` (trigger phrases, params, response style); move JSON to `tool_requests/complete/{id}.json` with status=complete or failed
- Includes full tool generation reference with two skeleton examples and config key guide

**Next:** Phase 8 item 2 — `pi/tool_requests/github_sync.py` add `pull_completed_tools()`: git pull, scan `tools/generated/` for new `.py` files, register with ToolRegistry, enqueue announcements.

## Documents

| File | Purpose |
|------|---------|
| `requirements.md` | Full project requirements (still valid) |
| `.project/active/pi-redesign/spec.md` | New architecture spec — read before implementing anything |
| `plan.md` | New phased implementation plan — agent works from here |
| `docs/technical-stack.md` | Updated stack decisions |
| `docs/parts-list.md` | Updated hardware list |

## Key Architecture Decisions

- **Single unified process** on Pi — no WebSocket client/server split
- **HailoRT** for LLM + STT inference on Hailo-10H NPU (replaces Ollama + Faster Whisper)
- **Wake word:** "Clanker" (openWakeWord, unchanged)
- **Tool creation:** Claude Code remote scheduled agent reads/writes via GitHub repo — Pi never calls Claude API directly
- **Tool requests:** Local SQLite queue → push to GitHub when online → agent builds → Pi pulls + loads
- **Scheduling:** Pi usage heatmap drives when the remote agent runs; agent self-reschedules via CronDelete + CronCreate
- **Conversation memory:** SQLite, session-scoped, recent turns injected into LLM prompt
- **Android TV:** `androidtvremote2` (confirmed correct)
- **All existing tools preserved**

## Agent Instructions

1. Read `.project/active/pi-redesign/spec.md` fully before starting any phase
2. Read `plan.md` — find first unchecked item in Phase 1
3. Read `docs/technical-stack.md` for stack context
4. Implement the item
5. Check it off in `plan.md` with a brief note
6. Continue until phase is complete or blocker hit

## Open Questions

None — spec is approved, plan is ready.

## Hardware Notes

- Pi 5 8GB + AI HAT+ 2 + USB mic + A2 SD card + PSU/case ≈ $270
- Hardware arrived 2026-06-15 — Hailo-10H detected on PCIe
- Physical Pi + AI HAT+ 2 needed for real inference (enrollment, Hailo validation)
