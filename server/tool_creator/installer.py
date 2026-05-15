"""Installer for validated AI-generated BaseTool modules."""

from __future__ import annotations

import importlib
import importlib.util
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

from server.tools.base import BaseTool, ToolRegistry

_GENERATED_DIR = Path(__file__).resolve().parents[1] / "tools" / "generated"


@dataclass
class InstallResult:
    success: bool
    tool_name: str = ""
    path: str = ""
    error: str = ""


def install(source: str, tool_name: str, registry: ToolRegistry) -> InstallResult:
    """Write a validated tool to tools/generated/ and register it.

    Derives the filename from *tool_name* (sanitised to snake_case).  If a
    file for this tool already exists it is overwritten and the module is
    reloaded so the registry always reflects the latest version.

    Returns an InstallResult with success=True and the file path on success,
    or success=False and an error message on failure.
    """
    module_name = _safe_module_name(tool_name)
    if not module_name:
        return InstallResult(
            success=False,
            tool_name=tool_name,
            error=f"Cannot derive a valid module name from tool name {tool_name!r}",
        )

    dest = _GENERATED_DIR / f"{module_name}.py"

    try:
        _GENERATED_DIR.mkdir(parents=True, exist_ok=True)
        dest.write_text(source, encoding="utf-8")
    except OSError as exc:
        return InstallResult(
            success=False,
            tool_name=tool_name,
            error=f"Failed to write tool file: {exc}",
        )

    full_module = f"server.tools.generated.{module_name}"
    try:
        mod = _load_module(full_module, dest)
    except Exception as exc:
        return InstallResult(
            success=False,
            tool_name=tool_name,
            path=str(dest),
            error=f"Failed to import tool module: {exc}",
        )

    tool = _find_tool(mod)
    if tool is None:
        return InstallResult(
            success=False,
            tool_name=tool_name,
            path=str(dest),
            error="No concrete BaseTool subclass found in installed module",
        )

    registry.register(tool)
    return InstallResult(success=True, tool_name=tool.name, path=str(dest))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _safe_module_name(tool_name: str) -> str:
    """Convert a tool name to a valid Python module filename stem."""
    sanitised = re.sub(r"[^a-zA-Z0-9]+", "_", tool_name).strip("_").lower()
    return sanitised


def _load_module(full_module: str, path: Path) -> ModuleType:
    """Import or reload a module by dotted name from *path*."""
    if full_module in sys.modules:
        # Force reload so that an updated source file is picked up.
        spec = importlib.util.spec_from_file_location(full_module, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[full_module] = mod
        spec.loader.exec_module(mod)
        return mod
    return importlib.import_module(full_module)


def _find_tool(mod: ModuleType) -> BaseTool | None:
    """Return the first concrete BaseTool subclass instance found in *mod*."""
    for attr_name in dir(mod):
        obj = getattr(mod, attr_name)
        if (
            isinstance(obj, type)
            and issubclass(obj, BaseTool)
            and obj is not BaseTool
            and not getattr(obj, "__abstractmethods__", None)
        ):
            try:
                return obj()
            except Exception:
                pass
    return None
