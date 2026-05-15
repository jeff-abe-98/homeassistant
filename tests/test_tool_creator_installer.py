"""Smoke tests for server/tool_creator/installer.py."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

from server.tool_creator.installer import (
    InstallResult,
    _safe_module_name,
    install,
)
from server.tools.base import ToolRegistry

_GENERATED_DIR = Path(__file__).resolve().parents[1] / "server" / "tools" / "generated"

_VALID_TOOL_SOURCE = """\
from server.tools.base import BaseTool

class GreetTool(BaseTool):
    name = "greet"
    description = "Greets the user by name."
    parameters = {{"type": "object", "properties": {{}}}}

    async def run(self, params: dict, user: str) -> str:
        return f"Hello, {{user}}!"
"""

_VALID_TOOL_SOURCE = """\
from server.tools.base import BaseTool

class GreetTool(BaseTool):
    name = "greet"
    description = "Greets the user by name."
    parameters = {"type": "object", "properties": {}}

    async def run(self, params: dict, user: str) -> str:
        return f"Hello, {user}!"
"""

_ANOTHER_TOOL_SOURCE = """\
from server.tools.base import BaseTool

class PingTool(BaseTool):
    name = "ping"
    description = "Returns pong."
    parameters = {"type": "object", "properties": {}}

    async def run(self, params: dict, user: str) -> str:
        return "pong"
"""

_NO_SUBCLASS_SOURCE = "x = 1 + 2\n"


# ---------------------------------------------------------------------------
# InstallResult dataclass
# ---------------------------------------------------------------------------


def test_install_result_success_defaults():
    r = InstallResult(success=True)
    assert r.tool_name == ""
    assert r.path == ""
    assert r.error == ""


def test_install_result_failure_fields():
    r = InstallResult(success=False, error="something went wrong")
    assert not r.success
    assert r.error == "something went wrong"


# ---------------------------------------------------------------------------
# _safe_module_name
# ---------------------------------------------------------------------------


def test_safe_module_name_snake_case():
    assert _safe_module_name("my_tool") == "my_tool"


def test_safe_module_name_spaces_become_underscores():
    assert _safe_module_name("my tool") == "my_tool"


def test_safe_module_name_hyphens_become_underscores():
    assert _safe_module_name("my-tool") == "my_tool"


def test_safe_module_name_uppercased_lowered():
    assert _safe_module_name("MyTool") == "mytool"


def test_safe_module_name_empty_string():
    assert _safe_module_name("") == ""


def test_safe_module_name_special_chars_stripped():
    assert _safe_module_name("tool!@#name") == "tool_name"


# ---------------------------------------------------------------------------
# install() — success paths
# ---------------------------------------------------------------------------


def _cleanup(module_stem: str) -> None:
    """Remove test-generated file and sys.modules entry."""
    dest = _GENERATED_DIR / f"{module_stem}.py"
    if dest.exists():
        dest.unlink()
    full = f"server.tools.generated.{module_stem}"
    sys.modules.pop(full, None)


def test_install_writes_file_to_generated_dir():
    registry = ToolRegistry()
    _cleanup("greet")
    try:
        result = install(_VALID_TOOL_SOURCE, "greet", registry)
        assert result.success, result.error
        assert (_GENERATED_DIR / "greet.py").exists()
    finally:
        _cleanup("greet")


def test_install_registers_tool_in_registry():
    registry = ToolRegistry()
    _cleanup("greet")
    try:
        result = install(_VALID_TOOL_SOURCE, "greet", registry)
        assert result.success, result.error
        tool = registry.get("greet")
        assert tool is not None
        assert tool.name == "greet"
    finally:
        _cleanup("greet")


def test_install_result_contains_tool_name_and_path():
    registry = ToolRegistry()
    _cleanup("greet")
    try:
        result = install(_VALID_TOOL_SOURCE, "greet", registry)
        assert result.success
        assert result.tool_name == "greet"
        assert "greet.py" in result.path
    finally:
        _cleanup("greet")


def test_install_second_tool_both_registered():
    registry = ToolRegistry()
    _cleanup("greet")
    _cleanup("ping")
    try:
        r1 = install(_VALID_TOOL_SOURCE, "greet", registry)
        r2 = install(_ANOTHER_TOOL_SOURCE, "ping", registry)
        assert r1.success
        assert r2.success
        assert registry.get("greet") is not None
        assert registry.get("ping") is not None
    finally:
        _cleanup("greet")
        _cleanup("ping")


def test_install_overwrites_existing_file():
    registry = ToolRegistry()
    _cleanup("greet")
    try:
        install(_VALID_TOOL_SOURCE, "greet", registry)
        # Install again — should succeed (overwrite + reload)
        result = install(_VALID_TOOL_SOURCE, "greet", registry)
        assert result.success
    finally:
        _cleanup("greet")


# ---------------------------------------------------------------------------
# install() — failure paths
# ---------------------------------------------------------------------------


def test_install_invalid_tool_name_returns_failure():
    registry = ToolRegistry()
    result = install(_VALID_TOOL_SOURCE, "!!!###", registry)
    assert not result.success
    assert "Cannot derive" in result.error


def test_install_no_basetool_subclass_returns_failure():
    registry = ToolRegistry()
    _cleanup("no_subclass_tool")
    try:
        result = install(_NO_SUBCLASS_SOURCE, "no_subclass_tool", registry)
        assert not result.success
        assert "BaseTool" in result.error or "No concrete" in result.error
    finally:
        _cleanup("no_subclass_tool")
