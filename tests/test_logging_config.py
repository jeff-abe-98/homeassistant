from __future__ import annotations

import logging
import logging.handlers

import pytest

from shared.config import AppConfig, LoggingConfig
from server.logging_config import setup_logging


@pytest.fixture(autouse=True)
def restore_root_logger():
    """Restore the root logger's handlers and level after each test."""
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level
    yield
    root.handlers[:] = original_handlers
    root.setLevel(original_level)


def _make_cfg(tmp_path, **kwargs) -> AppConfig:
    cfg = AppConfig()
    cfg.logging = LoggingConfig(log_dir=str(tmp_path / "logs"), **kwargs)
    return cfg


def test_creates_log_directory_and_file(tmp_path):
    cfg = _make_cfg(tmp_path, log_file="test.log")
    setup_logging(cfg)
    assert (tmp_path / "logs" / "test.log").exists()


def test_adds_rotating_file_handler(tmp_path):
    cfg = _make_cfg(tmp_path, max_bytes=5_000_000, backup_count=3)
    setup_logging(cfg)
    root = logging.getLogger()
    fh = next(
        (h for h in root.handlers if isinstance(h, logging.handlers.RotatingFileHandler)),
        None,
    )
    assert fh is not None
    assert fh.maxBytes == 5_000_000
    assert fh.backupCount == 3


def test_adds_stream_handler(tmp_path):
    cfg = _make_cfg(tmp_path)
    setup_logging(cfg)
    root = logging.getLogger()
    sh = next(
        (h for h in root.handlers if type(h) is logging.StreamHandler),
        None,
    )
    assert sh is not None


def test_log_message_written_to_file(tmp_path):
    cfg = _make_cfg(tmp_path, log_file="ha.log")
    setup_logging(cfg)
    logging.getLogger("test.structured").info("hello structured world")
    content = (tmp_path / "logs" / "ha.log").read_text()
    assert "hello structured world" in content
    assert "test.structured" in content


def test_log_format_includes_level_and_name(tmp_path):
    cfg = _make_cfg(tmp_path, log_file="fmt.log")
    setup_logging(cfg)
    logging.getLogger("fmt.check").warning("format test")
    content = (tmp_path / "logs" / "fmt.log").read_text()
    assert "WARNING" in content
    assert "fmt.check" in content


def test_log_level_respected(tmp_path):
    cfg = _make_cfg(tmp_path, level="WARNING")
    setup_logging(cfg)
    assert logging.getLogger().level == logging.WARNING


def test_debug_suppressed_when_level_is_info(tmp_path):
    cfg = _make_cfg(tmp_path, log_file="info.log", level="INFO")
    setup_logging(cfg)
    logging.getLogger("debug.check").debug("should not appear")
    content = (tmp_path / "logs" / "info.log").read_text()
    assert "should not appear" not in content


def test_rotation_creates_backup(tmp_path):
    cfg = _make_cfg(tmp_path, log_file="rotate.log", max_bytes=200, backup_count=2)
    setup_logging(cfg)
    logger = logging.getLogger("rotation.test")
    for i in range(30):
        logger.info("line %04d padding padding padding padding padding padding", i)
    logs = list((tmp_path / "logs").iterdir())
    assert len(logs) > 1, "Expected at least one rotated backup file"


def test_setup_logging_wires_to_config_file(tmp_path, monkeypatch):
    """setup_logging reads from AppConfig, not hardcoded paths."""
    import os
    import tempfile
    import yaml

    settings = {
        "logging": {
            "log_dir": str(tmp_path / "cfg_logs"),
            "log_file": "from_yaml.log",
            "max_bytes": 1_000_000,
            "backup_count": 2,
            "level": "INFO",
        }
    }
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        yaml.dump(settings, f)
        yaml_path = f.name

    monkeypatch.setenv("SETTINGS_PATH", yaml_path)
    import shared.config as cfg_module
    cfg = cfg_module.load()
    setup_logging(cfg)
    assert (tmp_path / "cfg_logs" / "from_yaml.log").exists()
    os.unlink(yaml_path)
