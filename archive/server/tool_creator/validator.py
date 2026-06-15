"""Validator for LLM-generated BaseTool implementations."""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from server.tool_creator.sandbox import check_imports

_DEFAULT_TIMEOUT = 20.0
_PROJECT_ROOT = str(Path(__file__).resolve().parents[2])

# Runner script injected into the subprocess.  It adds the project root to
# sys.path, loads the tool module from a temp file, locates the concrete
# BaseTool subclass, verifies required attributes, then calls run({}, "test_user")
# and confirms the return type is str.  Prints "OK:<name>:<description>" on success.
_VALIDATION_RUNNER = """\
import sys, asyncio
sys.path.insert(0, {root!r})

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("_validated_tool", {path!r})
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

from server.tools.base import BaseTool

_cls = None
for _n in dir(_mod):
    _o = getattr(_mod, _n)
    if (
        isinstance(_o, type)
        and issubclass(_o, BaseTool)
        and _o is not BaseTool
        and not getattr(_o, "__abstractmethods__", None)
    ):
        _cls = _o
        break

if _cls is None:
    print("ERROR:no BaseTool subclass found", file=sys.stderr)
    sys.exit(1)

_tool = _cls()

if not getattr(_tool, "name", ""):
    print("ERROR:tool.name is empty", file=sys.stderr)
    sys.exit(1)
if not getattr(_tool, "description", ""):
    print("ERROR:tool.description is empty", file=sys.stderr)
    sys.exit(1)
if not isinstance(getattr(_tool, "parameters", None), dict):
    print("ERROR:tool.parameters is not a dict", file=sys.stderr)
    sys.exit(1)

async def _run():
    result = await _tool.run({{}}, "test_user")
    if not isinstance(result, str):
        print("ERROR:run() did not return str", file=sys.stderr)
        sys.exit(1)

asyncio.run(_run())
print("OK:" + _tool.name + ":" + _tool.description)
"""


@dataclass
class ValidationResult:
    success: bool
    tool_name: str = ""
    tool_description: str = ""
    error: str = ""


async def validate(source: str, timeout: float = _DEFAULT_TIMEOUT) -> ValidationResult:
    """Validate a generated BaseTool source string.

    Steps:
    1. Static import allowlist check via check_imports().
    2. Subprocess test: load the module, instantiate the class, call run({}, 'test_user'),
       and confirm the return value is a str.

    A tool that returns an error string (e.g. "API key not configured") is
    considered valid — it ran without raising.  A tool that raises an exception
    is invalid.

    Returns a ValidationResult with success=True and the tool's name/description
    on success, or success=False and an error message on failure.
    """
    try:
        disallowed = check_imports(source)
    except SyntaxError as exc:
        return ValidationResult(success=False, error=f"SyntaxError: {exc}")

    if disallowed:
        return ValidationResult(
            success=False,
            error=f"Disallowed imports: {', '.join(sorted(disallowed))}",
        )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(source)
        tmp_path = f.name

    try:
        runner = _VALIDATION_RUNNER.format(root=_PROJECT_ROOT, path=tmp_path)
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            runner,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return ValidationResult(
                success=False,
                error=f"Timeout: validation exceeded {timeout:.0f}s",
            )

        code = proc.returncode or 0
        if code != 0:
            stderr_text = err.decode(errors="replace").strip()
            return ValidationResult(
                success=False,
                error=stderr_text or "Validation subprocess failed",
            )

        stdout = out.decode(errors="replace").strip()
        if stdout.startswith("OK:"):
            parts = stdout[3:].split(":", 1)
            tool_name = parts[0] if parts else ""
            tool_description = parts[1] if len(parts) > 1 else ""
            return ValidationResult(
                success=True,
                tool_name=tool_name,
                tool_description=tool_description,
            )

        return ValidationResult(
            success=False,
            error=f"Unexpected subprocess output: {stdout!r}",
        )
    finally:
        os.unlink(tmp_path)
