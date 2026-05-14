"""Smoke tests for server/tool_creator/validator.py."""

from __future__ import annotations

import pytest

from server.tool_creator.validator import ValidationResult, validate

# ---------------------------------------------------------------------------
# Minimal tool sources used across multiple tests
# ---------------------------------------------------------------------------

_VALID_TOOL = """\
from server.tools.base import BaseTool

class EchoTool(BaseTool):
    name = "echo"
    description = "Echoes the query back."
    parameters = {"type": "object", "properties": {}}

    async def run(self, params: dict, user: str) -> str:
        return "echo: ok"
"""

_RAISING_TOOL = """\
from server.tools.base import BaseTool

class BrokenTool(BaseTool):
    name = "broken"
    description = "Always raises."
    parameters = {"type": "object", "properties": {}}

    async def run(self, params: dict, user: str) -> str:
        raise RuntimeError("intentional failure")
"""

_NON_STRING_TOOL = """\
from server.tools.base import BaseTool

class BadReturnTool(BaseTool):
    name = "bad_return"
    description = "Returns an int instead of str."
    parameters = {"type": "object", "properties": {}}

    async def run(self, params: dict, user: str) -> str:
        return 42  # type: ignore[return-value]
"""

_NO_SUBCLASS_SOURCE = "x = 1 + 2\n"

_SLOW_TOOL = """\
import asyncio
from server.tools.base import BaseTool

class SlowTool(BaseTool):
    name = "slow"
    description = "Sleeps forever."
    parameters = {"type": "object", "properties": {}}

    async def run(self, params: dict, user: str) -> str:
        await asyncio.sleep(999)
        return "done"
"""


# ---------------------------------------------------------------------------
# ValidationResult dataclass
# ---------------------------------------------------------------------------


def test_validation_result_success_defaults():
    r = ValidationResult(success=True)
    assert r.tool_name == ""
    assert r.tool_description == ""
    assert r.error == ""


def test_validation_result_failure_fields():
    r = ValidationResult(success=False, error="something went wrong")
    assert not r.success
    assert r.error == "something went wrong"


def test_validation_result_success_fields():
    r = ValidationResult(success=True, tool_name="echo", tool_description="Echoes.")
    assert r.success
    assert r.tool_name == "echo"
    assert r.tool_description == "Echoes."


# ---------------------------------------------------------------------------
# Static checks (no subprocess spawned)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_syntax_error_returns_failure():
    result = await validate("def broken(:")
    assert not result.success
    assert "SyntaxError" in result.error


@pytest.mark.asyncio
async def test_validate_disallowed_import_returns_failure():
    result = await validate("import subprocess\nfrom server.tools.base import BaseTool")
    assert not result.success
    assert "subprocess" in result.error


# ---------------------------------------------------------------------------
# Subprocess-based tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_valid_tool_returns_success():
    result = await validate(_VALID_TOOL)
    assert result.success
    assert result.tool_name == "echo"
    assert result.tool_description == "Echoes the query back."
    assert result.error == ""


@pytest.mark.asyncio
async def test_validate_no_basetool_subclass_returns_failure():
    result = await validate(_NO_SUBCLASS_SOURCE)
    assert not result.success
    assert "BaseTool" in result.error or "no" in result.error.lower()


@pytest.mark.asyncio
async def test_validate_run_raises_returns_failure():
    result = await validate(_RAISING_TOOL)
    assert not result.success


@pytest.mark.asyncio
async def test_validate_run_returns_non_string_returns_failure():
    result = await validate(_NON_STRING_TOOL)
    assert not result.success


@pytest.mark.asyncio
async def test_validate_timeout_returns_failure():
    result = await validate(_SLOW_TOOL, timeout=0.5)
    assert not result.success
    assert "Timeout" in result.error


@pytest.mark.asyncio
async def test_validate_tool_that_returns_error_string_is_valid():
    # Tools returning error strings (e.g. "API key not configured") are valid —
    # they ran without raising.
    source = """\
from server.tools.base import BaseTool

class ConfiguredTool(BaseTool):
    name = "configured"
    description = "Returns a config-missing message."
    parameters = {"type": "object", "properties": {}}

    async def run(self, params: dict, user: str) -> str:
        return "API key not configured"
"""
    result = await validate(source)
    assert result.success
    assert result.tool_name == "configured"
