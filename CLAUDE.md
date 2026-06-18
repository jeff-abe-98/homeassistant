# Agent Instructions

This project is a Pi-only home assistant running on a Raspberry Pi 5 with Hailo AI HAT+ 2. It uses HailoRT for on-device LLM and STT inference, with no server component. Read `requirements.md` and `docs/technical-stack.md` before writing any code; follow the tech stack exactly. The `archive/server/` directory contains the old server+client split architecture and should not be modified or referenced.

## Every Session — In Order

### Step 0 — Git push access
```
git remote set-url origin https://<GITHUB_PAT>@github.com/jeff-abe-98/homeassistant.git
git config user.email "jeff@homeassistant"
git config user.name "Jeff"
```
The PAT is provided in the session's system prompt — use the value given there, not a literal placeholder.

### Step 1 — Read context
Read in order: `INBOX.md`, `plan.md`, `.project/CURRENT_WORK.md`, `docs/technical-stack.md`, `requirements.md`

### Step 2 — Write startup check-in
Prepend a new entry to the **Agent Startup Log** section of `INBOX.md`:

```
### YYYY-MM-DD (session N)
**Status:** <one sentence: current phase + what was last done>
**Next task:** <first unchecked item in plan.md>
**Blockers:** <active blockers or "None">
```

Session number = previous entry's number + 1.

### Step 3 — Process inbox
Check `INBOX.md` for unchecked items (`- [ ]`):
- **Open Questions**: resolve and check off, or add to Blockers Log and leave unchecked.
- **Ideas & Improvements**: triage into `plan.md` and check off with a note like `*(added to plan.md Phase N)*.`
- **Notes**: read for context only.

If there are inbox items to process, that counts as the session task — skip Step 4.

### Step 4 — Implement next plan item
Find the first unchecked item (`- [ ]`) in the earliest incomplete phase of `plan.md`. Implement it. Do exactly what the task says — nothing more, nothing less.

When done:
- Check off the item in `plan.md` with a brief inline note.
- Update `.project/CURRENT_WORK.md` with what was done and what's next.

### Step 5 — Update PROGRESS.md
Prepend a new entry at the top (keep last 10, drop older ones):

```
## [DATE TIME UTC]
**Completed:** <one-line description>
**Files changed:** <comma-separated list>
**Next up:** <first unchecked item remaining in plan.md>
**Blockers:** <new blockers or "None">
---
```

### Step 6 — Commit and push
Stage all changed files, commit with a descriptive message, push to main.

## Rules

- One task per session (inbox processing counts as the task).
- Do not skip phases or add unrequested features.
- Never commit real secrets — `config/settings.yaml` uses placeholder values only.
- If a task needs external API keys or OAuth setup, create the config skeleton with placeholder comments and log it as a blocker.
- If you cannot complete a task, add a row to the Blockers Log in `plan.md`, update `PROGRESS.md`, commit, and push.
