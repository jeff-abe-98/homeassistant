# Agent Progress Log

Most recent run at top.

---

## [2026-05-11 04:00 UTC]
**Completed:** Integration tests for Google Tasks "add oat milk to my list" — `tests/test_tasks_integration.py` with 2 tests (owner + Emily per-user routing); auto-skip without Google credentials; 32 smoke tests pass, 2 skip
**Files changed:** tests/test_tasks_integration.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 3 — Google Tasks — Test: "What's on my list?" → reads back incomplete items
**Blockers:** None
---

## [2026-05-11 03:00 UTC]
**Completed:** Per-user Google Tasks list routing — replaced `_default_tasklist_id` with `_user_tasklist_id(service, user)` that finds a list matching the user's name, creates it if absent, falls back to first list for unknown users; all 3 tasks tools updated; 9 new tests (7 unit + 2 e2e owner/emily routing); 32 total pass
**Files changed:** server/tools/tasks.py, tests/test_tasks.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 3 — Google Tasks — Test: "Add oat milk to my list" → added to correct user's list
**Blockers:** Google Auth needs manual Google Cloud Console setup before Tasks/Calendar tools can make live API calls
---

## [2026-05-11 02:00 UTC]
**Completed:** `server/tools/tasks.py` — `AddTaskTool`, `ListTasksTool`, `CompleteTaskTool`; uses Google Tasks API v1 via shared `build_service`; `_default_tasklist_id` helper; case-insensitive `_find_task_by_title`; 23 smoke tests in `tests/test_tasks.py` all pass
**Files changed:** server/tools/tasks.py, tests/test_tasks.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 3 — Google Tasks — Separate task lists per user ("Owner", "Emily")
**Blockers:** Google Auth needs manual Google Cloud Console setup before Tasks/Calendar tools can make live API calls
---

## [2026-05-11 01:00 UTC]
**Completed:** Integration test for Emily dentist appointment — `test_emily_dentist_appointment_created_as_emily_dentist` added to `tests/test_calendar_integration.py`; uses real `dateparser` ("Thursday at 3" → hour=15); mocks Google Calendar insert to capture event body; asserts summary="Emily Dentist", hour=15, timeZone=America/Chicago; confirmation includes "Emily Dentist"; skips without credentials; 29 smoke tests still pass
**Files changed:** tests/test_calendar_integration.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 3 — Google Tasks — `server/tools/tasks.py` (add item, list incomplete items, complete item by name)
**Blockers:** Google Auth needs manual Google Cloud Console setup before Calendar/Tasks tools can make live API calls
---

## [2026-05-11 00:00 UTC]
**Completed:** Calendar "reads events for speaking user" — `CalendarTool.run()` injects speaker name into LLM system prompt; 2 new smoke tests (known-user name in prompt, unknown-user not in prompt); `tests/test_calendar_integration.py` with 2 integration tests (owner + Emily, auto-skip without Google credentials); 29 smoke tests pass
**Files changed:** server/tools/calendar.py, tests/test_calendar.py, tests/test_calendar_integration.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 3 — Google Calendar — Test: Emily says "I have a dentist appointment Thursday at 3" → event created as "Emily Dentist"
**Blockers:** Google Auth needs manual Google Cloud Console setup before Calendar can make live API calls
---

## [2026-05-10 04:00 UTC]
**Completed:** Emily event auto-prefix — `AddCalendarEventTool.run()` in `server/tools/calendar.py` prefixes title with "Emily " when user is emily (case-insensitive, no double-prefix guard); 3 new smoke tests; 27 total pass
**Files changed:** server/tools/calendar.py, tests/test_calendar.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 3 — Google Calendar — Test: "What do I have tomorrow?" → reads events for speaking user
**Blockers:** Google Auth needs manual Google Cloud Console setup before Calendar can make live API calls
---

## [2026-05-10 03:00 UTC]
**Completed:** `AddCalendarEventTool` added to `server/tools/calendar.py` — `add_calendar_event` intent; `_parse_natural_date` uses `dateparser` (future-preferring, Chicago TZ, tz-aware); creates event via `service.events().insert()`; guards missing title + unparseable date + unconfigured auth; custom `duration_minutes` (default 60); `dateparser>=1.2.0` added to requirements; 10 new smoke tests (24 total pass)
**Files changed:** server/tools/calendar.py, requirements-server.txt, tests/test_calendar.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 3 — Google Calendar — Emily events auto-prefixed with "Emily "
**Blockers:** Google Auth needs manual Google Cloud Console setup before Calendar can make live API calls
---

## [2026-05-10 02:00 UTC]
**Completed:** `server/tools/calendar.py` — `CalendarTool` reads Google Calendar events for today/tomorrow/this_week; narrates via LLM; guards unconfigured state; 14 smoke tests pass
**Files changed:** server/tools/calendar.py, tests/test_calendar.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 3 — Google Calendar — Add event with natural language date parsing
**Blockers:** Google Auth needs manual Google Cloud Console setup before Calendar can make live API calls
---

## [2026-05-10 01:00 UTC]
**Completed:** Google Auth module — `config/google_credentials.json` skeleton with setup instructions; `GoogleConfig` extended with `token_file` + `scopes` fields; `server/tools/google_auth.py` (`is_configured`, `get_credentials`, `build_service`); google-auth packages added to requirements; 8 smoke tests pass
**Files changed:** config/google_credentials.json, shared/config.py, server/tools/google_auth.py, tests/test_google_auth.py, requirements-server.txt, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 3 — Google Calendar — `server/tools/calendar.py` (read events for today / date range)
**Blockers:** Google Auth needs manual Google Cloud Console setup (create project, enable Calendar+Tasks APIs, download OAuth2 Desktop credentials JSON)
---

## [2026-05-10 00:00 UTC]
**Completed:** Wrote `tests/test_cta_integration.py` — two async integration tests (`test_cta_next_blue_line_real_api`, `test_cta_ohare_direction_real_api`) that auto-skip when cta.api_key is CHANGE_ME; verify parsed arrivals structure and direction-aware system prompt when real key is set; 11 existing CTA smoke tests still pass
**Files changed:** tests/test_cta_integration.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 3 — Google Auth — Set up Google Cloud project, enable Calendar API + Tasks API
**Blockers:** CTA integration tests skip until real CTA API key set in config/settings.yaml; Phase 2 enrollment needs physical Pi hardware
---

## [2026-05-09 01:00 UTC]
**Completed:** Registered CTA API key in config — confirmed `CtaConfig` (api_key + stop_id_ohare/forest_park) fully wired in `shared/config.py` and `config/settings.yaml`; added API registration URL comment to `settings.yaml` (transitchicago.com/developers/traintrackerapply); all 11 CTA smoke tests pass
**Files changed:** config/settings.yaml, plan.md, .project/CURRENT_WORK.md, PROGRESS.md
**Next up:** Phase 3 — Test: "When's the next Blue Line?" → arrival times (tests/test_cta_integration.py)
**Blockers:** CTA integration test will skip until real CTA API key is set in config/settings.yaml
---

## [2026-05-09 00:00 UTC]
**Completed:** Created `docs/parts-list.md` — Pi section (Pi 5 8 GB + ReSpeaker 2-Mic Pi HAT + PSU + MicroSD + case, ~$130–140) and server section (RTX 4060 Ti 16 GB + 650 W PSU upgrade, ~$500–550); includes ReSpeaker Pi 5 driver install notes. Item moved from Phase 6 to top of plan and completed.
**Files changed:** docs/parts-list.md, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 3 — Register CTA API key in config
**Blockers:** None
---

## [2026-05-08 04:00 UTC]
**Completed:** Enhanced CTA directional query handling — `CtaTool.run()` now injects direction-specific context into the LLM system prompt (O'Hare-only, Forest Park-only, or group-both); added 3 new tests (Forest Park happy path, O'Hare system prompt assertion, both-direction system prompt assertion); 11 tests pass
**Files changed:** server/tools/cta.py, tests/test_cta.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 3 — Register CTA API key in config
**Blockers:** None
---

## [2026-05-08 03:00 UTC]
**Completed:** Implemented `server/tools/cta.py` — `CtaTool` fetches Blue Line arrivals from CTA Train Tracker API for Western & Milwaukee stop; `direction` param routes to O'Hare stop (30238), Forest Park stop (30239), or both; LLM narrates arrival times naturally; guards CHANGE_ME key. Extended `CtaConfig` with `stop_id_ohare`/`stop_id_forest_park` fields wired from YAML. 8 smoke tests pass.
**Files changed:** server/tools/cta.py, tests/test_cta.py, shared/config.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 3 — Handle directional queries (O'Hare vs Forest Park) — next plan item
**Blockers:** CTA integration tests need real CTA API key; Phase 2 enrollment needs physical Pi hardware
---


