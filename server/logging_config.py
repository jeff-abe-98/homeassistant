from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from shared.config import AppConfig

_FMT = "%(asctime)s | %(levelname)-8s | %(name)-35s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"


def setup_logging(cfg: AppConfig) -> None:
    """Configure root logger: rotating file + console, format, level."""
    log_dir = Path(cfg.logging.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / cfg.logging.log_file

    root = logging.getLogger()
    root.setLevel(cfg.logging.level.upper())
    root.handlers.clear()

    formatter = logging.Formatter(_FMT, datefmt=_DATEFMT)

    fh = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=cfg.logging.max_bytes,
        backupCount=cfg.logging.backup_count,
        encoding="utf-8",
    )
    fh.setFormatter(formatter)
    root.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    root.addHandler(ch)
