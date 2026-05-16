# Current Work

**Last updated:** 2026-05-16  
**Phase:** Phase 6 — Hardening & Quality (in progress)

---

## Status

Phase 6 in progress.

Done this session:
- `shared/config.py` — `LoggingConfig` dataclass (log_dir, log_file, max_bytes, backup_count, level) added; wired into `AppConfig` and `load()`
- `server/logging_config.py` — `setup_logging(cfg)` configures root logger: `RotatingFileHandler` (10 MB / 5 backups by default) + `StreamHandler`; consistent format: `timestamp | LEVEL | logger_name | message`
- `server/main.py` — `setup_logging(_config)` called first in lifespan (before OllamaClient init); removed bare `logging.basicConfig` call
- `config/settings.yaml` — `logging:` section added with all four fields
- `tests/test_logging_config.py` — 9 smoke tests (dir creation, file handler, stream handler, message written, format, level, debug suppression, rotation backup, config-file wiring)

Next: Phase 6 — Wake word false positive rate (tune sensitivity).

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
