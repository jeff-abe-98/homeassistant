"""Smoke tests for server/tool_creator/sandbox.py."""

from __future__ import annotations

import pytest

from server.tool_creator.sandbox import (
    ALLOWED_IMPORTS,
    SandboxResult,
    check_imports,
    run_in_sandbox,
)

# ---------------------------------------------------------------------------
# check_imports
# ---------------------------------------------------------------------------


def test_check_imports_stdlib_allowed():
    assert check_imports("import os") == []


def test_check_imports_httpx_allowed():
    assert check_imports("import httpx") == []


def test_check_imports_subprocess_disallowed():
    result = check_imports("import subprocess")
    assert result == ["subprocess"]


def test_check_imports_from_import_disallowed():
    result = check_imports("from subprocess import run")
    assert result == ["subprocess"]


def test_check_imports_dotted_stdlib_allowed():
    # "import os.path" → root is "os" which is allowed
    assert check_imports("import os.path") == []


def test_check_imports_no_imports_returns_empty():
    assert check_imports("x = 1 + 2") == []


def test_check_imports_syntax_error_raises():
    with pytest.raises(SyntaxError):
        check_imports("def broken(:")


def test_check_imports_multiple_disallowed():
    source = "import subprocess\nimport requests"
    result = check_imports(source)
    assert "subprocess" in result
    assert "requests" in result


def test_check_imports_deduplicates_repeated_module():
    source = "import subprocess\nimport subprocess"
    result = check_imports(source)
    assert result.count("subprocess") == 1


def test_check_imports_shared_allowed():
    assert check_imports("import shared.config") == []


def test_check_imports_server_allowed():
    assert check_imports("from server.tools.base import BaseTool") == []


# ---------------------------------------------------------------------------
# SandboxResult
# ---------------------------------------------------------------------------


def test_sandbox_result_defaults():
    r = SandboxResult(success=True)
    assert r.stdout == ""
    assert r.stderr == ""
    assert r.exit_code == -1


def test_sandbox_result_failure_fields():
    r = SandboxResult(success=False, stderr="bad thing", exit_code=1)
    assert not r.success
    assert r.stderr == "bad thing"
    assert r.exit_code == 1


# ---------------------------------------------------------------------------
# run_in_sandbox — async (no subprocess spawned for static-check failures)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_in_sandbox_disallowed_import_fails_without_subprocess():
    result = await run_in_sandbox("import subprocess\nx = 1")
    assert not result.success
    assert "subprocess" in result.stderr


@pytest.mark.asyncio
async def test_run_in_sandbox_syntax_error_fails_without_subprocess():
    result = await run_in_sandbox("def broken(:")
    assert not result.success
    assert "SyntaxError" in result.stderr


# ---------------------------------------------------------------------------
# run_in_sandbox — subprocess-spawning tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_in_sandbox_valid_source_succeeds():
    result = await run_in_sandbox("x = 1 + 2")
    assert result.success
    assert result.exit_code == 0


@pytest.mark.asyncio
async def test_run_in_sandbox_runtime_error_fails():
    result = await run_in_sandbox("raise ValueError('boom')")
    assert not result.success
    assert result.exit_code != 0


@pytest.mark.asyncio
async def test_run_in_sandbox_timeout_kills_process():
    result = await run_in_sandbox("import time\ntime.sleep(999)", timeout=0.5)
    assert not result.success
    assert "Timeout" in result.stderr
