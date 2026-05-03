# Inbox

Edit this file directly in GitHub to communicate with the development agent.
The agent reads this at the start of every run.

---

## Open Questions
*Decisions or info needed before the agent can proceed. Agent will check these off when resolved, or note why it's blocked.*

<!-- Example: - [ ] What should the wake word be? -->

## Ideas & Improvements
*New features, changes to existing features, or improvements. Agent will triage these into plan.md and check them off.*
 - [x] Make sure that when you are reading this at start up, you are also writing here. *(added to plan.md Phase 6)*

## Notes
*Anything else — reminders, context, thoughts.*

<!-- Example: Emily's Spotify account is premium, mine is not yet -->

---

## Agent Startup Log
*The agent writes a brief status note here at the start of each session.*

### 2026-05-03 (session 2)
**Status:** Phase 1 in progress. Created `server/llm/client.py` — async Ollama client wrapper.  
**Next task:** `server/llm/prompts.py` — system prompt for the assistant persona.  
**Blockers:** None.

### 2026-05-03
**Status:** Phase 1 in progress. Created `config/settings.yaml` skeleton with placeholder values for all integrations.  
**Next task:** `server/llm/client.py` — Ollama client wrapper.  
**Blockers:** None.

### 2026-05-02
**Status:** Phase 1 in progress. Processed inbox item: agent startup write-back added to Phase 6 and implemented now.  
**Next task:** `config/settings.yaml` — skeleton config file (no real secrets).  
**Blockers:** None.
