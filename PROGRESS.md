# Agent Progress Log

Most recent run at top.

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

## [2026-05-08 02:00 UTC]
**Completed:** Weather integration test — `tests/test_weather_integration.py` with two async tests: `test_weather_today_real_api` (current conditions query) and `test_weather_forecast_real_api` (rain forecast query); both auto-skip when `weather.api_key` is CHANGE_ME; when real key is set they call live OWM API and verify payload structure passed to LLM; all 5 existing smoke tests still pass
**Files changed:** tests/test_weather_integration.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 3 — `server/tools/cta.py` — CTA Train Tracker API, Blue Line, Western & Milwaukee stop
**Blockers:** Integration tests skip until real OpenWeatherMap API key is set in config/settings.yaml
---

## [2026-05-08 01:00 UTC]
**Completed:** Registered OpenWeatherMap API key in config — added `units` field to `WeatherConfig` and wired from YAML; updated `WeatherTool.run()` to use `cfg.weather.units` (was hardcoded "imperial") and guard against `CHANGE_ME` placeholder; wrote `tests/test_weather.py` (5 smoke tests: config defaults, YAML loading, missing key, placeholder key, happy path — all pass)
**Files changed:** shared/config.py, server/tools/weather.py, tests/test_weather.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 3 — Test: "What's the weather today?" → natural spoken forecast (requires real OWM API key in settings.yaml)
**Blockers:** None
---

## [2026-05-08 00:00 UTC]
**Completed:** Implemented `server/tools/weather.py` — `WeatherTool` fetches current conditions (`/data/2.5/weather`) and 5-day/3-hour forecast (`/data/2.5/forecast`) in parallel via httpx; passes both JSON payloads to OllamaClient for natural narration; lazy-loads its own OllamaClient; returns error string if API key missing; auto-discovered by ToolRegistry
**Files changed:** server/tools/weather.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 3 — Register OpenWeatherMap API key in config
**Blockers:** None
---

## [2026-05-07 04:00 UTC]
**Completed:** Updated `server/main.py` — WebSocket handler wires `ToolRegistry` + `ToolRouter`; `_handle_transcript` tries `_router.route()` first, executes matched `tool.run(params, user)`, falls back to plain LLM completion when no tool is selected or found
**Files changed:** server/main.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 3 — `server/tools/weather.py` — fetch OpenWeatherMap data, pass raw JSON to LLM for natural narration
**Blockers:** None
---

## [2026-05-07 03:00 UTC]
**Completed:** Implemented `server/llm/router.py` — `ToolCall` dataclass (tool_name + params dict); `ToolRouter.route(transcript)` builds system-prompted messages, calls Ollama with all registered function schemas via new `chat_with_tools`, returns `ToolCall` if LLM picks a tool or `None` for conversational fallback; added `chat_with_tools(messages, tools) -> Message` to `OllamaClient`
**Files changed:** server/llm/router.py, server/llm/client.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 3 — Update WebSocket handler to run tool router and return tool result
**Blockers:** None
---

## [2026-05-07 02:00 UTC]
**Completed:** Implemented `server/tools/base.py` — `BaseTool` ABC (`name`, `description`, `parameters`, abstract `run`); `ToolRegistry.load()` auto-discovers concrete subclasses in `server.tools` + `server.tools.generated` via `pkgutil.iter_modules`, supports hot-reload; `function_schemas()` for Ollama function calling; `register()` for installer
**Files changed:** server/tools/base.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 3 — `server/llm/router.py` — LLM function calling: given transcript + user, select tool + extract params
**Blockers:** None
---

## [2026-05-07 01:00 UTC]
**Completed:** Logged Phase 2 hardware blockers — enrollment + hardware tests for Owner/Emily require physical Pi + mic; all four items added to Blockers Log; Phase 3 is next actionable work
**Files changed:** plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 3 — `server/tools/base.py` (`BaseTool` abstract class + `ToolRegistry`)
**Blockers:** Phase 2 enrollment/tests require physical Pi hardware (logged)
---

## [2026-05-07 00:00 UTC]
**Completed:** Updated `server/llm/prompts.py` — `build_system_prompt(user)` appends a personalized suffix: known speaker gets "address them by name naturally", unknown speaker gets "ask who they are if they request something personal"; `server/main.py` passes `transcript.user`
**Files changed:** server/llm/prompts.py, server/main.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Enrollment — run enrollment script for Owner (requires Pi hardware)
**Blockers:** None
---

## [2026-05-06 11:00 UTC]
**Completed:** Integrated speaker ID into `pi/main.py` — buffers PCM bytes during audio capture, runs `identify()` in executor concurrently with `receive_transcript()` to hide latency, attaches speaker name via `model_copy(update={"user": user})` before sending Transcript to server; also added `user: str = "unknown"` to `Transcript` in `shared/models.py`
**Files changed:** pi/main.py, shared/models.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Update `server/llm/prompts.py` — inject user name into system prompt for personalization
**Blockers:** None
---

## [2026-05-06 10:00 UTC]
**Completed:** Implemented `pi/speaker_id/identify.py` — `identify(pcm_bytes, sample_rate)` and `identify_embedding(embedding)`; cosine similarity (dot product of unit vectors) vs all enrolled `config/voice_profiles/*.npy`; returns best-match name or "unknown" if below 0.75 threshold
**Files changed:** pi/speaker_id/identify.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Integrate speaker ID into `pi/main.py` — identify before sending transcript to server
**Blockers:** None
---

## [2026-05-06 08:20 UTC]
**Completed:** Implemented `pi/speaker_id/enroll.py` — CLI enrollment script; records 30s of raw int16 PCM at 16kHz via PyAudio; prints live countdown; calls `embed_audio` + `save_embedding`; run as `python -m pi.speaker_id.enroll <name> [--device INDEX]`
**Files changed:** pi/speaker_id/enroll.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md
**Next up:** `pi/speaker_id/identify.py` — compare incoming audio embedding against enrolled profiles, return user name or "unknown"
**Blockers:** None
---

## [2026-05-06 05:00 UTC]
**Completed:** Implemented `pi/speaker_id/embeddings.py` — `embed_audio(pcm_bytes, sample_rate)` converts raw int16 PCM to 256-d numpy embedding via resemblyzer `VoiceEncoder.embed_utterance`; `save_embedding`/`load_embedding`/`list_profiles` manage `config/voice_profiles/*.npy` files
**Files changed:** pi/speaker_id/embeddings.py, plan.md, .project/CURRENT_WORK.md, PROGRESS.md
**Next up:** `pi/speaker_id/enroll.py` — enrollment script: record 30s of speech, save embedding to `config/voice_profiles/`
**Blockers:** None
---

## [2026-05-06 UTC (session 14)]
**Completed:** Implemented end-to-end pipeline test — `tests/test_e2e.py`; real uvicorn server + real WebSocket client; STT + LLM mocked via unittest.mock; AudioChunk → Transcript → AssistantResponse round-trip; 1 passed in 0.48 s. Phase 1 is now complete.
**Files changed:** tests/__init__.py, tests/test_e2e.py, conftest.py, pytest.ini, requirements-test.txt, plan.md, .project/CURRENT_WORK.md, PROGRESS.md, INBOX.md
**Next up:** Phase 2 / `pi/speaker_id/embeddings.py` — generate and save voice embeddings using resemblyzer
**Blockers:** None
---


