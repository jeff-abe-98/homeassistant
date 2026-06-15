"""Subprocess runner with resource limits and import allowlist for sandboxed tool execution."""

from __future__ import annotations

import ast
import asyncio
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

_CPU_TIME_LIMIT = 5           # seconds
_MEMORY_LIMIT = 256 * 1024 * 1024  # 256 MB
_DEFAULT_TIMEOUT = 15.0       # wall-clock seconds

# sandbox.py lives at server/tool_creator/sandbox.py → project root is 2 levels up
_PROJECT_ROOT = str(Path(__file__).resolve().parents[2])

ALLOWED_IMPORTS: frozenset[str] = frozenset({
    # Standard library
    "abc", "asyncio", "base64", "collections", "contextlib", "copy",
    "dataclasses", "datetime", "enum", "functools", "hashlib", "io",
    "itertools", "json", "math", "operator", "os", "pathlib", "re",
    "string", "textwrap", "time", "typing", "uuid",
    # Third-party (from generator allowlist)
    "httpx", "pydantic", "yaml",
    # Project packages
    "shared", "server",
})

# Runner snippet passed to `python -c`. Adds project root to sys.path so
# generated tools can import shared/server, then imports the temp module.
_RUNNER = """\
import sys
sys.path.insert(0, {root!r})

import importlib.util as _ilu

_spec = _ilu.spec_from_file_location("_sandbox_tool", {path!r})
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
print("OK")
"""


@dataclass
class SandboxResult:
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1


def check_imports(source: str) -> list[str]:
    """Return list of disallowed top-level module names found in *source*.

    Returns [] when all imports are from ALLOWED_IMPORTS.
    Raises SyntaxError if *source* is not valid Python.
    """
    tree = ast.parse(source)
    disallowed: list[str] = []
    seen: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            root = _root_module(node)
            if root and root not in ALLOWED_IMPORTS and root not in seen:
                disallowed.append(root)
                seen.add(root)
    return disallowed


async def run_in_sandbox(source: str, timeout: float = _DEFAULT_TIMEOUT) -> SandboxResult:
    """Execute *source* in a restricted subprocess.

    Steps:
    1. Statically check imports — return early without spawning a process if
       any disallowed module is found.
    2. Write *source* to a temp file.
    3. Spawn a subprocess that imports the temp file; CPU and memory limits are
       applied via preexec_fn before user code runs.
    4. Return a SandboxResult with success/stdout/stderr/exit_code.
    """
    try:
        disallowed = check_imports(source)
    except SyntaxError as exc:
        return SandboxResult(success=False, stderr=f"SyntaxError: {exc}", exit_code=1)

    if disallowed:
        return SandboxResult(
            success=False,
            stderr=f"Disallowed imports: {', '.join(sorted(disallowed))}",
            exit_code=1,
        )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(source)
        tmp_path = f.name

    try:
        runner = _RUNNER.format(root=_PROJECT_ROOT, path=tmp_path)
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            runner,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=_apply_resource_limits,
        )
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return SandboxResult(
                success=False,
                stderr=f"Timeout: execution exceeded {timeout:.0f}s",
                exit_code=-1,
            )
        code = proc.returncode or 0
        return SandboxResult(
            success=code == 0,
            stdout=out.decode(errors="replace"),
            stderr=err.decode(errors="replace"),
            exit_code=code,
        )
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _apply_resource_limits() -> None:
    """Set CPU-time and address-space limits in the child process (POSIX only)."""
    try:
        import resource  # noqa: PLC0415
        resource.setrlimit(resource.RLIMIT_CPU, (_CPU_TIME_LIMIT, _CPU_TIME_LIMIT))
        resource.setrlimit(resource.RLIMIT_AS, (_MEMORY_LIMIT, _MEMORY_LIMIT))
    except Exception:
        pass


def _root_module(node: ast.Import | ast.ImportFrom) -> str | None:
    """Extract the top-level module name from an Import or ImportFrom node."""
    if isinstance(node, ast.Import):
        return node.names[0].name.split(".")[0] if node.names else None
    return node.module.split(".")[0] if node.module else None
