# Current Work

**Last updated:** 2026-05-02  
**Phase:** Phase 1 — Core Voice Pipeline (in progress)

---

## Status

Repo structure initialized. All directories (`pi/`, `server/`, `shared/`, `config/`) created with `__init__.py` files. Ready to create requirements files.

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

- Phase 1 / Shared: `shared/config.py` — `AppConfig` dataclass tree (`ServerConfig`, `OllamaConfig`, `GoogleConfig`, `SpotifyConfig`, `CtaConfig`, `WeatherConfig`, `AndroidTvConfig`) with `load()` function; reads `config/settings.yaml`, falls back to defaults if missing, respects `SETTINGS_PATH` env var

## Next Task

- Phase 1 / Shared: `config/settings.yaml` — skeleton config file (no real secrets yet)

## Open Questions

1. **Wake word name** — TBD, not blocking Phase 1
2. **Tool sandboxing** — design decision for Phase 5, not blocking now
3. **Voice enrollment UX** — needed for Phase 2

## Hardware Notes

- Server GPU upgrade pending: RTX 4060 Ti 16GB + 650W PSU (~$500)
- Until then: CPU inference with Llama 3.1 8B Q4
- After upgrade: switch Ollama model to Llama 3.1 13B Q4 in `config/settings.yaml`
