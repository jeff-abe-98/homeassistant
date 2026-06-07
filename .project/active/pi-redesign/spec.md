# Spec: Pi-Only Redesign

**Status:** Draft
**Owner:** Jeff
**Created:** 2026-06-07
**Complexity:** HIGH
**Branch:** N/A — full architectural redesign, new plan required before implementation

---

## Business Goals

### Why This Matters

The original architecture requires a separate home server running GPU-accelerated inference. That dependency is being dropped entirely. The Raspberry Pi AI HAT+ 2 (Hailo-10H) makes it possible to run LLM inference and STT locally on the Pi at usable speeds, eliminating the server cost (~$500 GPU upgrade), reducing setup complexity, and keeping all personal data on a single device.

The redesign also replaces the existing autonomous tool creation approach (local LLM generates code — unreliable at small model sizes) with a Claude Code remote scheduled agent. Claude handles tool generation during low-usage windows, controlled by a usage heatmap the Pi builds from its own activation history. This gives better tool quality while keeping Claude API token usage efficient and predictable.

### Success Criteria

- [ ] Clanker responds to the wake word "Clanker" and completes a full voice request cycle on the Pi alone, with no server involved
- [ ] Speaker identification correctly distinguishes Owner from Emily
- [ ] All existing tools (weather, CTA, calendar, tasks, Spotify, Android TV, music recommendations) work on the Pi
- [ ] When asked for something it can't do, Clanker queues a tool request, and on the next interaction after the tool is built announces "By the way, I can now [do X] — want to try it?"
- [ ] Tool requests survive a reboot and a loss of internet connectivity
- [ ] The remote Claude agent runs during low-usage windows derived from real activation data, not a fixed schedule
- [ ] Claude API is never called during a normal request — only during scheduled tool creation runs

### Priority

Blocks all further development. The existing server-based plan is superseded by this spec.

---

## Problem Statement

### Current State

The system is split: a Raspberry Pi runs wake word, speaker ID, and TTS as a WebSocket client; a separate home server runs STT, LLM inference, tool routing, and tool creation. The server requires a GPU upgrade (~$500) that the user has decided not to pursue. The autonomous tool creation module (`server/tool_creator/generator.py`) uses the local Ollama LLM to write Python code — acceptable at 8B but unreliable at the smaller model sizes that run on edge hardware. The project has been hardware-blocked for months waiting on physical Pi setup.

### Desired Outcome

A single Raspberry Pi 5 (8GB RAM + AI HAT+ 2) runs the complete assistant. LLM inference and STT run on the Hailo-10H NPU. All other components run on the Pi CPU. Tool creation is delegated to a Claude Code remote scheduled agent that reads and writes via the existing GitHub repo. The Pi never calls the Claude API directly — it only writes request files and pulls completed tools.

---

## Scope

### In Scope

- Full replacement of the server + Pi client split with a single unified Pi process
- HailoRT runtime for LLM and STT (replaces Ollama + Faster Whisper)
- Wake word "Clanker" via openWakeWord (unchanged)
- Speaker ID via resemblyzer (unchanged)
- Piper TTS (unchanged)
- Conversation memory: SQLite, session-scoped, recent turns injected into LLM prompt
- Tool request queue: local SQLite queue with GitHub sync when online
- Offline resilience: requests queued locally, synced when connectivity restored
- Priority system: user-set verbally, default mid, LLM asks relative priority against existing queue
- Remote Claude Code scheduled agent: reads pending requests from GitHub, builds tools + instruction prompts, pushes back
- Usage heatmap: Pi logs every wake word activation → daily process finds low-usage windows → writes `schedule.json` to repo → agent self-reschedules
- Default schedule before 14 days of activation data: 3–5am daily
- Proactive new-tool announcement on next wake word interaction
- Instruction prompt created alongside every new tool
- All existing tools preserved: weather, CTA, Google Calendar, Google Tasks, Spotify, Android TV, music recommendations
- Updated parts list and hardware documentation

### Out of Scope

- Server infrastructure (eliminated)
- GPU upgrade
- Smart home device control (lights, thermostat)
- Multi-room audio / multiple microphones
- Mobile app interface
- Guest persistent profiles
- Non-English language support

### Edge Cases & Considerations

- **No internet at request time:** Tool request written to local SQLite queue. Pi retries push on connectivity restore. User told "I'll remember that for when I'm back online."
- **No internet for extended period:** Queue accumulates locally without data loss. All entries pushed in order when connectivity returns.
- **Tool build fails (Claude can't build it):** Agent marks request as `failed` with an error note, pushes status back. Pi notifies user on next interaction.
- **Multiple pending requests when agent runs:** Agent processes all pending requests in a single run, ordered by priority (high → mid → low), FIFO within same priority level.
- **New tool announced but user doesn't want it:** User can decline. Tool stays registered and available for future requests.
- **Not enough activation data for heatmap:** Default to 3–5am daily until 14 days of data accumulated.
- **Hailo NPU busy during STT + LLM overlap:** STT runs first (blocking), LLM runs after transcript is ready — sequential, no contention.
- **Session timeout:** Session ends after configurable silence period. Memory for that session is committed to SQLite.

---

## Requirements

### Functional Requirements

**FR-1:** The system MUST run entirely on a Raspberry Pi 5 (8GB RAM) with an AI HAT+ 2, with no dependency on a separate server.

**FR-2:** LLM inference and STT MUST run on the Hailo-10H NPU via HailoRT runtime.

**FR-3:** The wake word MUST be "Clanker", detected via openWakeWord running on CPU.

**FR-4:** Speaker identification MUST distinguish Owner from Emily using resemblyzer voice profiles. Unknown speakers MUST be handled per the existing behavior (ask identity on personal requests, answer generically otherwise).

**FR-5:** The system MUST maintain conversation memory within a session (wake word activation through silence/timeout). Recent turns MUST be injected into the LLM's context window.

**FR-6:** Conversation memory MUST persist across reboots via SQLite on the microSD card.

**FR-7:** When the local LLM cannot route a user request to any known tool, it MUST:
  - Tell the user it doesn't know how to do that yet
  - If other tool requests are already queued, ask the user whether this request is more or less urgent than the current highest-priority item
  - If the queue is empty, assign default mid priority
  - Write a tool request record (see FR-9) to the local queue

**FR-8:** Tool requests MUST survive a reboot. The local queue MUST be stored in SQLite.

**FR-9:** Each tool request record MUST contain: unique ID, timestamp, intent summary, exact user query, speaker, priority (low/mid/high), status (pending/in_progress/complete/failed), and recent conversation context turns.

**FR-10:** When internet connectivity is available, the Pi MUST push pending tool requests to the GitHub repo (committing the request JSON files to `tool_requests/pending/`). When connectivity is unavailable, requests MUST remain in the local SQLite queue and be pushed when connectivity is restored. The user MUST be told "I'll remember that for when I'm back online" when offline.

**FR-11:** The Pi MUST periodically pull from GitHub and load any new tool files that appear in `tools/generated/`.

**FR-12:** When a new tool is loaded that the user has not yet been told about, Clanker MUST announce it on the next wake word interaction: *"By the way, I can now [do X] — want to try it?"*

**FR-13:** Each new tool created by the remote agent MUST include two files:
  - `tools/generated/{tool_name}.py` — the `BaseTool` subclass implementation
  - `tools/generated/{tool_name}_instructions.md` — an instruction prompt for the local LLM describing when to use the tool, what parameters it accepts, and how to phrase responses to the user

**FR-14:** The Pi MUST log every wake word activation with a timestamp to a SQLite `activations` table.

**FR-15:** A daily process MUST build a day-of-week × time-of-day usage heatmap from the activations table and identify the lowest-usage 2-hour windows for each day of the week.

**FR-16:** The heatmap output MUST be written as `schedule.json` to the GitHub repo, committing and pushing whenever the calculated optimal windows change.

**FR-17:** The remote Claude Code scheduled agent MUST, at the start of each run: read `schedule.json`, reschedule itself (CronDelete + CronCreate) for the next optimal low-usage window, then process pending tool requests.

**FR-18:** Before 14 days of activation data are available, the default schedule MUST be 3–5am daily.

**FR-19:** The remote agent MUST process all pending requests in a single run, in priority order (high → mid → low), FIFO within the same priority level.

**FR-20:** If the agent cannot build a requested tool, it MUST mark the request as `failed` with an error description and push the status back to GitHub. The Pi MUST notify the user on the next interaction.

**FR-21:** All existing tools MUST be preserved and functional: weather (OpenWeatherMap), CTA Blue Line, Google Calendar, Google Tasks, Spotify (per-user), Android TV (`androidtvremote2`), and music recommendations.

**FR-22:** The Claude API MUST NOT be called during a normal user request. Claude is only invoked by the remote scheduled agent.

**FR-23:** The system MUST use `androidtvremote2` for TV control (not ADB). The existing `server/tools/androidtv.py` implementation is correct.

### Non-Functional Requirements

- **Privacy:** All AI inference (LLM, STT, speaker ID) runs locally on the Pi. No user audio or transcripts are sent to external services except during scheduled tool creation (where only intent/query text is sent, not audio).
- **Resilience:** The assistant MUST continue to handle known tool requests even when GitHub is unreachable.
- **Token efficiency:** Claude API tokens are consumed only during scheduled tool creation runs, not during normal operation.
- **Parts budget:** Hardware MUST fit within approximately $270 total (Pi 5 8GB ~$80, AI HAT+ 2 ~$130, USB mic ~$20, PSU + case + A2 SD card ~$40).

---

## Acceptance Criteria

### Core Voice Pipeline
- [ ] "Clanker" wake word triggers voice capture on Pi with no server
- [ ] STT produces accurate transcripts via Hailo NPU
- [ ] LLM routes requests to correct tools via Hailo NPU
- [ ] Piper TTS produces spoken response through USB audio
- [ ] Full round-trip latency feels conversational

### Speaker Identification
- [ ] Owner voice correctly identified and responses personalized
- [ ] Emily voice correctly identified and responses personalized
- [ ] Unknown speaker handled gracefully per existing behavior

### Conversation Memory
- [ ] LLM correctly uses prior turns from the same session (e.g., "add *that* to my list")
- [ ] Memory resets between sessions
- [ ] SQLite persists across reboot

### Tool Routing — Existing Tools
- [ ] "What's the weather?" → OpenWeatherMap result
- [ ] "When's the next Blue Line?" → CTA result
- [ ] "What do I have tomorrow?" → Google Calendar result (per user)
- [ ] "Add oat milk to my list" → correct user's Google Tasks list
- [ ] "Play some jazz" → Spotify on Android TV (owner account)
- [ ] "Put on Netflix" → Netflix launches on Android TV
- [ ] "Play something I'd like" → music recommendation result

### Tool Creation
- [ ] Unknown request → local queue written, user told "I don't know how to do that yet"
- [ ] Queue entry survives reboot
- [ ] Queue entry pushed to GitHub when online
- [ ] "I'll remember that for when I'm back online" when offline
- [ ] Remote agent builds tool + instruction prompt and pushes to GitHub
- [ ] Pi loads new tool without restart
- [ ] Next interaction: "By the way, I can now [X] — want to try it?"
- [ ] Failed build notified to user on next interaction

### Scheduling
- [ ] Activations logged to SQLite on every wake word
- [ ] `schedule.json` updated daily and pushed to GitHub
- [ ] Remote agent reschedules itself at the start of each run
- [ ] Default 3–5am schedule used before 14 days of data

### Offline Resilience
- [ ] Tool request queued locally when GitHub unreachable
- [ ] Queue pushed when connectivity restored
- [ ] All existing tool functionality continues when GitHub unreachable

---

## Hardware

| Component | Purpose | Est. Cost |
|---|---|---|
| Raspberry Pi 5 8GB | Main compute, runs all CPU-based components | ~$80 |
| AI HAT+ 2 (Hailo-10H) | LLM + STT inference, 8GB dedicated RAM | ~$130 |
| USB microphone | Voice input (replaces ReSpeaker HAT — PCIe conflict) | ~$20 |
| A2-rated microSD (64GB) | OS + SQLite + model storage | ~$15 |
| PSU (27W USB-C) + case | Power + housing | ~$25 |
| **Total** | | **~$270** |

---

## What Changes vs Current Codebase

### Removed
- `server/main.py` — FastAPI WebSocket server
- `pi/client.py` — WebSocket client
- `server/llm/` — Ollama-based LLM client and router (replaced by HailoRT)
- `server/stt/` — Faster Whisper (replaced by Hailo Whisper)
- `server/tool_creator/generator.py` — local LLM code generation (replaced by remote agent)
- `server/tool_creator/sandbox.py`, `validator.py`, `installer.py` — still relevant but will be re-evaluated during design

### Preserved (unchanged or minor config updates)
- `server/tools/` — all existing tools
- `server/tools/base.py` — BaseTool, ToolRegistry
- `shared/models.py` — Pydantic models
- `shared/config.py` — config loading
- `config/settings.yaml` — config values
- `pi/speaker_id/` — resemblyzer
- `pi/audio/` — capture, playback
- `pi/tts/` — Piper
- `pi/wake_word/` — openWakeWord
- `deploy/` — systemd service files (update for new unified process)
- `docs/parts-list.md` — update for new hardware

### New
- `pi/llm/` — HailoRT-based LLM client
- `pi/stt/` — HailoRT-based Whisper client
- `pi/memory/` — SQLite conversation memory (session management, context injection)
- `pi/tool_requests/` — local queue management, GitHub sync, offline retry
- `pi/scheduler/` — activation logging, heatmap calculation, `schedule.json` generation
- `pi/main.py` — unified main loop (replaces both old `pi/main.py` and `server/main.py`)
- `.claude/agents/tool-builder.md` — remote agent definition and instructions
- `tool_requests/pending/` — repo directory for pending tool request JSON files
- `tool_requests/complete/` — repo directory for completed/failed request records
- `tools/generated/` — already exists, now populated by remote agent

---

## Related Artifacts

- **Current plan:** `plan.md` (superseded — new plan required after spec approval)
- **Requirements:** `requirements.md` (still valid, hardware section updated)
- **Technical stack:** `docs/technical-stack.md` (to be updated during design)
- **Parts list:** `docs/parts-list.md` (to be updated)
- **Current work:** `.project/CURRENT_WORK.md`

---

**Next Steps:** After approval, proceed to `/_my_design` to produce a technical design, then `/_my_plan` to replace `plan.md` with a new phased implementation plan.
