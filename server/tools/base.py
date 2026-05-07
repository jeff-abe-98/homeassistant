"""Tool plugin interface and registry for server-side tools."""

from __future__ import annotations

import importlib
import importlib.util
import pkgutil
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from types import ModuleType
from typing import Iterator


class BaseTool(ABC):
    """Every tool — built-in or AI-generated — must subclass this."""

    name: str
    description: str
    parameters: dict  # JSON Schema used by LLM for function calling

    @abstractmethod
    async def run(self, params: dict, user: str) -> str:
        """Execute the tool and return a natural-language response string."""


class ToolRegistry:
    """Discovers and holds all registered tools.

    At startup, call `load()` to scan the `server/tools/` package and
    `server/tools/generated/` for any `BaseTool` subclasses.  Call
    `load()` again at any time to pick up newly written tool files without
    restarting the server.
    """

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Scan tool packages and register all BaseTool subclasses found."""
        tools_pkg = _import_package("server.tools")
        generated_pkg = _import_package("server.tools.generated")

        for pkg in (tools_pkg, generated_pkg):
            if pkg is None:
                continue
            for tool in _discover_tools(pkg):
                self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def all(self) -> list[BaseTool]:
        return list(self._tools.values())

    def function_schemas(self) -> list[dict]:
        """Return Ollama-compatible function-calling schemas for all tools."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self._tools.values()
        ]

    def register(self, tool: BaseTool) -> None:
        """Manually register a tool instance (used by installer)."""
        self._tools[tool.name] = tool


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _import_package(dotted_name: str) -> ModuleType | None:
    try:
        return importlib.import_module(dotted_name)
    except ModuleNotFoundError:
        return None


def _discover_tools(pkg: ModuleType) -> Iterator[BaseTool]:
    """Yield one instantiated BaseTool per concrete subclass found in *pkg*."""
    pkg_path = getattr(pkg, "__path__", None)
    if pkg_path is None:
        return

    for finder, module_name, _is_pkg in pkgutil.iter_modules(pkg_path):
        full_name = f"{pkg.__name__}.{module_name}"

        # Skip base module itself to avoid circular discovery
        if full_name == "server.tools.base":
            continue

        # Reload if already imported so hot-reload picks up file changes
        if full_name in sys.modules:
            mod = importlib.reload(sys.modules[full_name])
        else:
            try:
                mod = importlib.import_module(full_name)
            except Exception:
                continue

        yield from _tools_from_module(mod)


def _tools_from_module(mod: ModuleType) -> Iterator[BaseTool]:
    for attr_name in dir(mod):
        obj = getattr(mod, attr_name)
        if (
            isinstance(obj, type)
            and issubclass(obj, BaseTool)
            and obj is not BaseTool
            and not getattr(obj, "__abstractmethods__", None)
        ):
            try:
                yield obj()
            except Exception:
                pass
