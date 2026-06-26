"""BaseTool ABC and ToolRegistry for the unified Pi assistant."""
from __future__ import annotations

import importlib
import pkgutil
import sys
from abc import ABC, abstractmethod
from types import ModuleType
from typing import Iterator


class BaseTool(ABC):
    """Every tool — built-in or AI-generated — must subclass this."""

    name: str
    description: str
    parameters: dict  # JSON Schema for LLM function calling
    needs_narration: bool = False  # True → run() returns raw data; caller calls router.narrate()

    @abstractmethod
    async def run(self, params: dict, user: str) -> str:
        """Execute the tool and return a natural-language response string."""


class ToolRegistry:
    """Discovers and holds all registered tools.

    Scans ``tools.generated`` (repo root) for BaseTool subclasses on each
    ``load()`` call.  Hot-reload is supported: call ``load()`` again to pick up
    files written by the remote agent without restarting the process.
    """

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def load(self) -> None:
        """Scan tool packages and register all concrete BaseTool subclasses."""
        builtin_pkg = _import_package("pi.tools")
        if builtin_pkg is not None:
            for tool in _discover_tools(builtin_pkg):
                self._tools[tool.name] = tool
        generated_pkg = _import_package("tools.generated")
        if generated_pkg is not None:
            for tool in _discover_tools(generated_pkg):
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
        """Manually register a tool instance (used by the installer)."""
        self._tools[tool.name] = tool


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


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

    for _finder, module_name, _is_pkg in pkgutil.iter_modules(pkg_path):
        if module_name == "base":
            continue
        full_name = f"{pkg.__name__}.{module_name}"

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
